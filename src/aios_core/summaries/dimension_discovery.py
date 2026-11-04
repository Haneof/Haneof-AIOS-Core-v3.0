"""New-axis discovery: the summary / periodic-review AI proposes observation axes.

Why a service, not a clause in the summary prompt. 《维度注册宪法》十四 assigns
discovery + registration to the summary / review AI, explicitly off the live chat
tool surface. The judgement ("does the world need another axis?") is a separate
task (``TaskKind.DISCOVER_DIMENSION``) whose output is a JSON array of proposals,
each carrying a 注册门 gate block. The system only checks *structure*; the
recurrence / novelty call is the AI's (宪法二/五 forbid a fixed numeric threshold,
and 五 allows a single evidence to form a Candidate).

The committed product is a Candidate ``DimensionDefinition``, written through
``DimensionRegistryService.propose`` — the same durable machinery any proposal
uses. Discovery never writes an axis directly; it *proposes*, and the proposal
carries its gate block so the decision is auditable (宪法四/十四).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import ObjectType
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import as_utc
from aios_core.dimensions import (
    DimensionProposalGate,
    DimensionProposalRequest,
    DimensionRegistryService,
)
from aios_core.prompts.contracts import DimensionProfile, PromptRenderParams
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore

UTC = timezone.utc

# Object types whose durable text is the recurring signal discovery reads. The
# scheduler runs summaries + digest *before* discovery in the same sweep, so raw
# observations have already been lifted into these by the time discovery looks.
_SIGNAL_TYPES = frozenset({ObjectType.CLAIM, ObjectType.SUMMARY})


class EvidenceRef(BaseModel):
    """A pinned reference to one record the proposer cited as evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    object_id: str
    revision: int = Field(ge=1)


class DiscoveryGate(BaseModel):
    """The 注册门 block the model must fill for every proposal."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    duplicate_checked_keys: tuple[str, ...] = ()
    recurrence_rationale: str = Field(min_length=1)
    is_novel_axis_reason: str = Field(min_length=1)


class DimensionDiscoveryItem(BaseModel):
    """One validated new-axis proposal as it will be committed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension_key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    data_shape: str = Field(min_length=1)
    evidence_record_ids: tuple[EvidenceRef, ...] = Field(min_length=1)
    why_existing_dimensions_are_insufficient: str = Field(min_length=1)
    continuity_rationale: str = Field(min_length=1)
    user_value_rationale: str = Field(min_length=1)
    maintenance_cost_rationale: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    # 宪法四「未来如何更新」：registry 一直支持 update_method，但 discovery
    # 路径此前没收，导致经本路径立案的 Candidate 永远缺这一项。
    update_method: str = Field(min_length=1)
    gate: DiscoveryGate

    @model_validator(mode="after")
    def _validate(self) -> "DimensionDiscoveryItem":
        if not self.dimension_key.startswith("dim:"):
            raise ValueError("dimension_key must start with 'dim:'")
        return self


class DiscoverySignalRecord(BaseModel):
    """One fact/claim/summary offered to the model as recurring signal material."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    object_id: str
    revision: int = Field(ge=1)
    object_type: str
    dimension: str
    text: str
    occurred_at: datetime | None = None


class DimensionDiscoveryInput(BaseModel):
    """One prepared discovery batch: the catalogue plus the signal material."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    subject_id: str
    window_start: datetime
    window_end: datetime
    source_world_revision: int = Field(ge=0)
    catalogue: tuple[DimensionProfile, ...] = ()
    signals: tuple[DiscoverySignalRecord, ...] = ()
    max_proposals: int = Field(default=8, ge=1)

    def to_render_params(self) -> PromptRenderParams:
        return PromptRenderParams(
            dimensions=tuple(self.catalogue),
            records=tuple(self.signals),
            extra={"max_proposals": self.max_proposals},
        )


@dataclass(frozen=True, slots=True)
class DimensionDiscoveryCommit:
    proposal_receipts: tuple[dict[str, Any], ...]
    reused_dimension_keys: tuple[str, ...]
    failed: tuple[tuple[str, str], ...]  # (dimension_key, error)
    world_revision: int


class DimensionDiscoveryService:
    """Prepare, validate and persist new-axis proposals behind the 注册门 gate."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex,
        dimension_registry: DimensionRegistryService,
        subject_id: str = "user_1",
        max_proposals: int = 8,
        max_signal_objects: int = 300,
        signal_lookback_days: int = 14,
    ) -> None:
        if max_proposals < 1:
            raise ValueError("max_proposals must be >= 1")
        if max_signal_objects < 1:
            raise ValueError("max_signal_objects must be >= 1")
        self.store = store
        self.index = index
        self.registry = dimension_registry
        self.subject_id = subject_id
        self.max_proposals = max_proposals
        self.max_signal_objects = max_signal_objects
        self.signal_lookback_days = signal_lookback_days

    # -------------------------------------------------------------- prepare

    def prepare(
        self,
        *,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
    ) -> DimensionDiscoveryInput:
        """Collect the existing axis catalogue and recent cross-dimension signal.

        The catalogue is every known axis (active or terminal — a proposal must
        not re-open an archived one either). The signal is recent Claims
        (cross-links + inferences) and Summaries (incl. the daily digest), which
        is where a recurring pattern becomes visible after the scheduler has run
        the summaries for this sweep.
        """

        end = as_utc(window_end or datetime.now(UTC), "window_end")
        start = as_utc(
            window_start or (end - timedelta(days=self.signal_lookback_days)),
            "window_start",
        )
        if end < start:
            raise ValueError("window_end must not be before window_start")

        self.index.catch_up()
        world_revision = int(self.store.current_world_revision())

        catalogue = self._catalogue()
        signals = self._collect_signals(start, end)

        return DimensionDiscoveryInput(
            subject_id=self.subject_id,
            window_start=start,
            window_end=end,
            source_world_revision=world_revision,
            catalogue=tuple(catalogue),
            signals=tuple(signals),
            max_proposals=self.max_proposals,
        )

    def _catalogue(self) -> list[DimensionProfile]:
        profiles: list[DimensionProfile] = []
        for definition in self.registry.current_dimensions(include_terminal=True):
            meta = definition.metadata or {}
            key = str(meta.get("dimension_key") or "").strip()
            if not key:
                continue
            profiles.append(
                DimensionProfile(
                    dimension_key=key,
                    name=str(getattr(definition, "name", "") or "").strip(),
                    data_shape=str(getattr(definition, "data_shape", "") or "").strip(),
                )
            )
        return profiles

    def _collect_signals(
        self, start: datetime, end: datetime
    ) -> list[DiscoverySignalRecord]:
        seen: set[tuple[str, int]] = set()
        out: list[DiscoverySignalRecord] = []
        for payload in self.store.list_payloads(subject_id=self.subject_id):
            object_type = str(payload.get("object_type") or "")
            if object_type not in _SIGNAL_TYPES:
                continue
            if payload.get("deleted_at") is not None:
                continue
            at = _payload_time(payload)
            if at is None or at < start or at > end:
                continue
            object_id = str(payload.get("object_id") or "")
            revision = int(payload.get("revision") or 1)
            key = (object_id, revision)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                DiscoverySignalRecord(
                    object_id=object_id,
                    revision=revision,
                    object_type=object_type,
                    dimension=_signal_dimension(payload),
                    text=_signal_text(payload),
                    occurred_at=at,
                )
            )
            if len(out) >= self.max_signal_objects:
                break
        out.sort(key=lambda item: (item.occurred_at, item.object_id))
        return out

    # --------------------------------------------------------------- parse

    def parse_items(
        self, prepared: DimensionDiscoveryInput, raw: Any
    ) -> tuple[DimensionDiscoveryItem, ...]:
        """Turn the model's JSON array into validated, gate-checked proposals.

        Rejection is deliberate. A proposal whose gate is missing, whose key
        collides with an existing axis, or whose evidence ids are fabricated
        cannot be applied without inventing something; dropping it quietly would
        report success while losing the model's actual answer.
        """

        if raw is None:
            raise ValueError("discovery response was empty")
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            raise ValueError("discovery response must be a JSON array")

        catalogue_keys = {profile.dimension_key for profile in prepared.catalogue}
        signal_keys = {
            (item.object_id, item.revision) for item in prepared.signals
        }
        items: list[DimensionDiscoveryItem] = []
        used_keys: set[str] = set()

        for entry in raw:
            if not isinstance(entry, Mapping):
                raise ValueError("discovery entry is not an object")
            item = DimensionDiscoveryItem.model_validate(entry)

            if item.dimension_key in catalogue_keys:
                raise ValueError(
                    f"proposed dimension_key {item.dimension_key!r} already exists"
                )
            if item.dimension_key in used_keys:
                raise ValueError(
                    f"duplicate dimension_key in batch: {item.dimension_key!r}"
                )
            used_keys.add(item.dimension_key)

            # 宪法八 / 十四：目录非空时，提案必须列出自己逐一核对过的现有轴，
            # 且只能列目录里真实存在的 key（防伪造，与证据 id 校验同构）。这
            # 是结构校验，不是语义相似度裁决。目录为空时无可核对，由 AI 在
            # is_novel_axis_reason 里如实说明，系统不替它否决。
            if catalogue_keys:
                checked = tuple(
                    str(k).strip() for k in item.gate.duplicate_checked_keys
                    if str(k).strip()
                )
                if not checked:
                    raise ValueError(
                        "registration gate must list the existing axes reviewed"
                    )
                unknown = tuple(k for k in checked if k not in catalogue_keys)
                if unknown:
                    raise ValueError(
                        f"duplicate_checked_keys not in the catalogue: {unknown}"
                    )

            # Evidence must come from the supplied signal, never an invented id.
            for ref in item.evidence_record_ids:
                if (ref.object_id, ref.revision) not in signal_keys:
                    raise ValueError(
                        f"evidence id {ref.object_id}@{ref.revision} not in this batch's signal"
                    )

            items.append(item)

        if len(items) > prepared.max_proposals:
            raise ValueError(
                f"discovery count {len(items)} exceeds cap {prepared.max_proposals}"
            )
        return tuple(items)

    # -------------------------------------------------------------- commit

    def commit(
        self,
        prepared: DimensionDiscoveryInput,
        items: Sequence[DimensionDiscoveryItem],
        *,
        generated_at: datetime,
    ) -> DimensionDiscoveryCommit:
        if prepared.subject_id != self.subject_id:
            raise ValueError("discovery input must be bound to this subject")

        generated = as_utc(generated_at, "generated_at")
        receipts: list[dict[str, Any]] = []
        reused: list[str] = []
        failed: list[tuple[str, str]] = []

        for item in items:
            request = DimensionProposalRequest(
                dimension_key=item.dimension_key.strip(),
                name=item.name.strip(),
                description=item.description.strip(),
                data_shape=item.data_shape.strip(),
                evidence_refs=tuple(
                    ObjectRef(object_id=ref.object_id, revision=ref.revision)
                    for ref in item.evidence_record_ids
                ),
                why_existing_dimensions_are_insufficient=(
                    item.why_existing_dimensions_are_insufficient.strip()
                ),
                continuity_rationale=item.continuity_rationale.strip(),
                user_value_rationale=item.user_value_rationale.strip(),
                maintenance_cost_rationale=item.maintenance_cost_rationale.strip(),
                confidence=float(item.confidence),
                update_method=item.update_method.strip(),
                registration_gate=DimensionProposalGate(
                    duplicate_checked_keys=tuple(
                        str(k).strip() for k in item.gate.duplicate_checked_keys
                    ),
                    recurrence_rationale=item.gate.recurrence_rationale.strip(),
                    is_novel_axis_reason=item.gate.is_novel_axis_reason.strip(),
                ),
            )
            try:
                receipt = self.registry.propose(request, proposed_at=generated)
            except ValueError as exc:
                # A different proposal of an existing key is a genuine conflict,
                # not corruption: record it and keep the batch moving.
                failed.append((item.dimension_key, f"{type(exc).__name__}: {exc}"))
                continue
            if receipt is None:
                reused.append(item.dimension_key)
                continue
            receipts.append(
                {
                    "dimension_id": receipt.dimension_id,
                    "dimension_key": receipt.dimension_key,
                    "lifecycle": receipt.lifecycle,
                    "world_revision": receipt.world_revision,
                }
            )

        return DimensionDiscoveryCommit(
            proposal_receipts=tuple(receipts),
            reused_dimension_keys=tuple(reused),
            failed=tuple(failed),
            world_revision=int(self.store.current_world_revision()),
        )


# ----------------------------------------------------------------- helpers


def _payload_time(payload: Mapping[str, Any]) -> datetime | None:
    raw = payload.get("recorded_at") or payload.get("learned_at")
    if isinstance(raw, str):
        try:
            return as_utc(
                datetime.fromisoformat(raw.replace("Z", "+00:00")), "recorded_at"
            )
        except ValueError:
            pass
    return None


def _signal_dimension(payload: Mapping[str, Any]) -> str:
    metadata = payload.get("metadata") or {}
    for candidate in (
        metadata.get("dimension"),
        metadata.get("source_dimension"),
        payload.get("dimension"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return "dim_unclassified"


def _signal_text(payload: Mapping[str, Any]) -> str:
    for key in ("content", "summary", "body", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


__all__ = [
    "DimensionDiscoveryCommit",
    "DimensionDiscoveryInput",
    "DimensionDiscoveryItem",
    "DimensionDiscoveryService",
    "DiscoveryGate",
    "DiscoverySignalRecord",
    "EvidenceRef",
]
