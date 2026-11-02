"""Cross-dimension attribution: "this fact also belongs to another axis".

Why this is a service instead of a clause in the summary prompt
---------------------------------------------------------------
《维度总结宪法》二 draws the line: a summary answers *what happened in this
dimension over this window*, and does not answer *what it means*. 《全维投影宪法》
八 repeats it at the world level — "跨维观察属于世界访问，跨维意义属于 AI 认知" —
and its 禁止事项 4 forbids writing cross-dimension narrative as a factual
Summary. Attributing "this chat line is also social evidence" is meaning, not
description, so it cannot ride along inside SUMMARIZE or DIGEST. It gets its own
task (``TaskKind.CROSS_LINK``) and its own object type: a revisable ``Claim``.

Why the product is a Claim and not a copy of the record
-------------------------------------------------------
A relayed sentence ("我心脏跳得好快") is not a measurement. Copying it into the
health axis would let a joke enter the axis as physiological data, and once
there no later summary can tell it apart from a real reading. So the original
record never moves and is never rewritten (《证据宪法》二：事实不可回写). What
gets written is a *statement about the record*, pointing back at it with pinned
refs, carrying a confidence, and — because it is a Claim — correctable and
retractable later (《证据宪法》三/四).

Why no confidence threshold
---------------------------
《维度注册宪法》二 forbids the system from deciding semantic questions with fixed
numbers ("70% 准确率是否自动等于有效维度"). The same reasoning applies here: a
link that the model rated 0.4 is not the mechanism's call to delete. The
confidence is recorded and consumers weigh it themselves.

Why targets are a closed set
----------------------------
《维度注册宪法》 requires new axes to travel Candidate → … with evidence. A
one-line attribution may not skip that by inventing ``dim:friendship_feelings``.
So ``prepare`` fixes the set of legal targets before the call, and ``commit``
rejects anything outside it — a rejected link is a bug in the prompt, not data
to silently coerce.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import (
    ClaimType,
    ErrorCode,
    KnowledgeState,
    MaintenanceClass,
    ObjectType,
    SourceClass,
)
from aios_core.contracts.models import Claim, Dependency, EvidenceSet
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import (
    KnowledgeWindow,
    TemporalExtent,
    TimePrecision,
    as_utc,
)
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError

CROSS_LINK_CLAIMANT = "cross_link:model"
CROSS_LINK_EVIDENCE_PURPOSE = "cross_dimension_attribution"


def _stable_id(*parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


class CrossLinkSource(BaseModel):
    """One fact the model may attribute. Pinned by revision, never re-read."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    object_id: str
    revision: int = Field(ge=1)
    object_type: str
    dimension: str
    text: str
    occurred_at: datetime | None = None

    @model_validator(mode="after")
    def validate_time(self) -> "CrossLinkSource":
        if self.occurred_at is not None:
            as_utc(self.occurred_at, "occurred_at")
        return self


class CrossLinkInput(BaseModel):
    """One prepared attribution batch: the facts plus the only legal targets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    subject_id: str = Field(min_length=1)
    window_start: datetime
    window_end: datetime
    source_world_revision: int = Field(ge=0)
    sources: tuple[CrossLinkSource, ...] = ()
    target_dimensions: tuple[str, ...] = ()
    max_links: int = Field(default=20, ge=1)


class CrossLinkItem(BaseModel):
    """A validated attribution as it will be committed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_object_id: str = Field(min_length=1)
    source_revision: int = Field(ge=1)
    target_dimension: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""


@dataclass(frozen=True, slots=True)
class CrossLinkCommit:
    claim_ids: tuple[str, ...]
    reused_claim_ids: tuple[str, ...]
    world_revision: int


class CrossLinkService:
    """Prepare, validate and persist cross-dimension attributions."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: Any,
        subject_id: str = "user_1",
        max_links: int = 20,
        max_source_objects: int = 200,
    ) -> None:
        if max_links < 1:
            raise ValueError("max_links must be >= 1")
        if max_source_objects < 1:
            raise ValueError("max_source_objects must be >= 1")
        self.store = store
        self.index = index
        self.subject_id = subject_id
        self.max_links = max_links
        self.max_source_objects = max_source_objects

    # -------------------------------------------------------------- prepare

    def prepare(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
        target_dimensions: Sequence[str] = (),
    ) -> CrossLinkInput:
        """Collect candidate facts and freeze the set of legal target axes.

        Only observations and events are offered as sources. Summaries and
        Claims are deliberately excluded: feeding last cycle's attributions back
        in would let one guess corroborate itself until it looks like a fact.
        """

        start = as_utc(window_start, "window_start")
        end = as_utc(window_end, "window_end")
        if end < start:
            raise ValueError("window_end must not be before window_start")

        self.index.catch_up()
        world_revision = int(self.store.current_world_revision())

        sources: list[CrossLinkSource] = []
        seen: set[tuple[str, int]] = set()
        page = self.index.search_mind(
            subject=self.subject_id,
            time_range=(start, end),
            object_types=("observation", "event"),
            limit=self.max_source_objects + 1,
        )
        if len(page.hits) > self.max_source_objects:
            raise ValueError(
                "cross-link source count exceeds cap; narrow the window instead "
                "of judging a truncated batch"
            )
        for hit in page.hits:
            payload = self.store.get_payload(hit.object_id, revision=hit.revision)
            if payload.get("subject_id") != self.subject_id:
                continue
            if payload.get("status", "active") != "active":
                continue
            key = (hit.object_id, int(hit.revision))
            if key in seen:
                continue
            seen.add(key)
            sources.append(
                CrossLinkSource(
                    object_id=hit.object_id,
                    revision=int(hit.revision),
                    object_type=str(payload.get("object_type") or hit.object_type),
                    dimension=_payload_dimension(payload),
                    text=_payload_text(payload),
                    occurred_at=_occurred_start(payload),
                )
            )
        sources.sort(key=lambda item: (item.occurred_at, item.object_id))

        declared = [key.strip() for key in target_dimensions if key.strip()]
        observed = sorted({item.dimension for item in sources})
        targets = tuple(dict.fromkeys([*declared, *observed]))

        return CrossLinkInput(
            subject_id=self.subject_id,
            window_start=start,
            window_end=end,
            source_world_revision=world_revision,
            sources=tuple(sources),
            target_dimensions=targets,
            max_links=self.max_links,
        )

    # --------------------------------------------------------------- parse

    def parse_items(
        self, prepared: CrossLinkInput, raw: Any
    ) -> tuple[CrossLinkItem, ...]:
        """Turn the model's JSON array into validated items, or raise.

        Rejection is deliberate. A link whose target is not in the catalogue, or
        whose source is not in this batch, cannot be applied without inventing
        something; dropping it quietly would report success while losing the
        model's actual answer.
        """

        if raw is None:
            raise ValueError("cross-link response was empty")
        if isinstance(raw, Mapping):
            raw = raw.get("links")
            if raw is None:
                raise ValueError("cross-link response object has no `links` array")
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            raise ValueError("cross-link response must be a JSON array")

        by_id = {item.object_id: item for item in prepared.sources}
        allowed = set(prepared.target_dimensions)
        items: list[CrossLinkItem] = []
        seen: set[tuple[str, str]] = set()

        for entry in raw:
            if not isinstance(entry, Mapping):
                raise ValueError("cross-link entry is not an object")
            source_id = str(entry.get("id") or entry.get("source_object_id") or "").strip()
            target = str(entry.get("target_dimension") or entry.get("target") or "").strip()
            statement = str(entry.get("statement") or "").strip()
            if not source_id or source_id not in by_id:
                raise ValueError(f"cross-link references unknown source: {source_id!r}")
            if not target:
                raise ValueError("cross-link entry has no target_dimension")
            if target not in allowed:
                raise ValueError(
                    f"cross-link targets an axis outside the catalogue: {target!r}"
                )
            if not statement:
                raise ValueError("cross-link entry has a blank statement")
            try:
                confidence = float(entry.get("confidence", 0.0))
            except (TypeError, ValueError) as exc:
                raise ValueError("cross-link confidence is not a number") from exc
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("cross-link confidence must be within [0, 1]")

            key = (source_id, target)
            if key in seen:
                # Same fact attributed to the same axis twice: keep the first.
                continue
            seen.add(key)
            source = by_id[source_id]
            items.append(
                CrossLinkItem(
                    source_object_id=source.object_id,
                    source_revision=source.revision,
                    target_dimension=target,
                    statement=statement,
                    confidence=confidence,
                    reason=str(entry.get("reason") or "").strip(),
                )
            )

        if len(items) > prepared.max_links:
            raise ValueError(
                f"cross-link count {len(items)} exceeds cap {prepared.max_links}"
            )
        return tuple(items)

    # -------------------------------------------------------------- commit

    def commit(
        self,
        prepared: CrossLinkInput,
        items: Sequence[CrossLinkItem],
        *,
        generated_at: datetime,
    ) -> CrossLinkCommit:
        if prepared.subject_id != self.subject_id:
            raise ValueError("cross-link input must be bound to this subject")
        if prepared.source_world_revision > self.store.current_world_revision():
            raise ValueError("cross-link input refers to a future World revision")
        if len(items) > prepared.max_links:
            raise ValueError("cross-link count exceeds cap")

        generated = as_utc(generated_at, "generated_at")
        by_id = {item.object_id: item for item in prepared.sources}
        allowed = set(prepared.target_dimensions)

        objects: list[Any] = []
        claim_ids: list[str] = []
        reused: list[str] = []
        operation_expected = int(self.store.current_world_revision())

        for item in items:
            source = by_id.get(item.source_object_id)
            if source is None or source.revision != item.source_revision:
                raise ValueError("cross-link source is not part of this batch")
            if item.target_dimension not in allowed:
                raise ValueError("cross-link target left the prepared catalogue")
            # The source must still be the current revision: attribution about a
            # superseded fact would silently describe a world that no longer is.
            current = self.store.get_payload(source.object_id)
            if int(current.get("revision", -1)) != source.revision:
                raise ValueError("cross-link source is no longer current; prepare again")

            claim_id = "claim_" + _stable_id(
                self.subject_id,
                source.object_id,
                source.revision,
                item.target_dimension,
            )
            existing = _maybe_payload(self.store, claim_id)
            if existing is not None:
                if str(existing.get("content") or "") != item.statement:
                    raise ValueError(
                        "the same fact/axis pair is already attributed differently"
                    )
                reused.append(claim_id)
                claim_ids.append(claim_id)
                continue

            evidence_id = "evs_" + _stable_id("crosslink", claim_id)
            source_ref = ObjectRef(object_id=source.object_id, revision=source.revision)
            evidence = EvidenceSet(
                object_id=evidence_id,
                subject_id=self.subject_id,
                occurred=TemporalExtent.point(generated),
                learned_at=generated,
                recorded_at=generated,
                source_refs=[SourceRef(object_id=source.object_id, revision=source.revision)],
                created_by="cross_link:evidence",
                purpose=CROSS_LINK_EVIDENCE_PURPOSE,
                knowledge_window=KnowledgeWindow(
                    knowledge_cutoff=generated,
                    world_revision=prepared.source_world_revision,
                ),
                member_refs=[source_ref],
                selection_method="explicit_batch_member",
                aggregation_method=None,
                coverage={"observed_count": 1},
            )
            evidence_ref = ObjectRef(object_id=evidence_id, revision=1)

            claim = Claim(
                object_id=claim_id,
                subject_id=self.subject_id,
                occurred=TemporalExtent.point(generated),
                learned_at=generated,
                recorded_at=generated,
                source_refs=[SourceRef(object_id=source.object_id, revision=source.revision)],
                created_by=CROSS_LINK_CLAIMANT,
                claimant_id=CROSS_LINK_CLAIMANT,
                claim_type=ClaimType.INFERENCE,
                content=item.statement,
                valid_time=TemporalExtent(
                    start=source.occurred_at or generated,
                    end=source.occurred_at or generated,
                    precision=TimePrecision.MINUTE,
                ),
                asserted_at=generated,
                knowledge_state=KnowledgeState.INFERRED,
                confidence=item.confidence,
                support_evidence_set_refs=[evidence_ref],
                metadata={
                    # The claim *lives in* the target axis: that is what makes it
                    # retrievable there without moving the original record.
                    "dimension": item.target_dimension,
                    "summary_kind": "cross_dimension_attribution",
                    "source_dimension": source.dimension,
                    "source_object_id": source.object_id,
                    "source_revision": source.revision,
                    "reason": item.reason,
                },
            )
            dependency = Dependency(
                object_id="dep_" + _stable_id(claim_id, source.object_id, source.revision),
                subject_id=self.subject_id,
                learned_at=generated,
                recorded_at=generated,
                created_by="cross_link:dependency",
                dependent_ref=ObjectRef(object_id=claim_id, revision=1),
                dependency_ref=source_ref,
                dependency_type="cross_link_uses_source_fact",
            )
            objects.extend([evidence, claim, dependency])
            claim_ids.append(claim_id)

        if not objects:
            return CrossLinkCommit(
                claim_ids=tuple(claim_ids),
                reused_claim_ids=tuple(reused),
                world_revision=int(self.store.current_world_revision()),
            )

        operation = OperationRequest(
            operation_id=f"op_crosslink_{_stable_id(*claim_ids)}",
            operation_name="cognition.commit_cross_dimension_links",
            arguments={
                "link_count": len(claim_ids),
                "source_world_revision": prepared.source_world_revision,
            },
            expected_world_revision=operation_expected,
            reason="commit model-attributed cross-dimension links as revisable claims",
            idempotency_key=f"crosslink:{_stable_id(*sorted(claim_ids))}",
            # A cognition write, not a maintenance write: no maintenance_class.
            source_class=SourceClass.AI_COGNITION,
        )
        result = self.store.commit(objects, operation)
        self.index.catch_up()
        return CrossLinkCommit(
            claim_ids=tuple(claim_ids),
            reused_claim_ids=tuple(reused),
            world_revision=result.world_revision,
        )


# ----------------------------------------------------------------- helpers


def _maybe_payload(store: SQLiteWorldStore, object_id: str) -> dict[str, Any] | None:
    try:
        return store.get_payload(object_id)
    except StoreError as exc:
        if exc.code is ErrorCode.NOT_FOUND:
            return None
        raise


def _payload_dimension(payload: Mapping[str, Any]) -> str:
    metadata = payload.get("metadata") or {}
    for candidate in (payload.get("dimension"), metadata.get("dimension")):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return "dim_unclassified"


def _payload_text(payload: Mapping[str, Any]) -> str:
    value = payload.get("value")
    if isinstance(value, Mapping):
        for key in ("text", "content", "transcript", "message"):
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                return text.strip()
    if isinstance(value, str) and value.strip():
        return value.strip()
    content = payload.get("content")
    return content.strip() if isinstance(content, str) else ""


def _occurred_start(payload: Mapping[str, Any]) -> datetime | None:
    extent = payload.get("occurred") or payload.get("summary_time")
    if isinstance(extent, Mapping):
        raw = extent.get("start")
    else:
        raw = extent
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return as_utc(
            datetime.fromisoformat(raw.replace("Z", "+00:00")), "occurred.start"
        )
    except ValueError:
        return None


def dimensions_from_index(index: Any, *, subject: str, limit: int = 64) -> tuple[str, ...]:
    """Return the axes that actually hold data, for use as the legal catalogue.

    This is a *mechanical* read of what exists, not a semantic judgement about
    what should exist — which is why it may run without the Resident AI.
    """

    directory = index.dimension_directory(subject=subject, limit=limit)
    keys: Iterable[str] = (
        str(entry.get("dimension"))
        for entry in (directory.get("dimensions") or [])
        if isinstance(entry, Mapping) and entry.get("dimension")
    )
    return tuple(dict.fromkeys(key for key in keys if key))


__all__ = [
    "CROSS_LINK_CLAIMANT",
    "CrossLinkCommit",
    "CrossLinkInput",
    "CrossLinkItem",
    "CrossLinkService",
    "CrossLinkSource",
    "dimensions_from_index",
]
