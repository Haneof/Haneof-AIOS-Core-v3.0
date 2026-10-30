"""Cross-dimension daily digest for AIOS v3.0.

``dim:daily_digest`` is a first-class basic dimension whose DAY summary
aggregates the same-day DAY summaries of every other dimension. It gives the
user a single "what happened today" view without inventing cross-dimensional
causality: sources are pinned, current, single-dimension DAY summaries only.

Unlike DimensionSummaryService, digest sources are not discovered through the
search index (the digest dimension itself has no indexed observations), so
this service owns its own source selection, validation and idempotency. The
scheduler is responsible for excluding ``DIGEST_DIMENSION`` from dimension
discovery to prevent self-recursion.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from aios_core.contracts.enums import ErrorCode, MaintenanceClass, ObjectType, SourceClass, SummaryStatus
from aios_core.contracts.models import Dependency, Summary
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import TemporalExtent, TimePrecision, as_utc
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError

from .dimension_summary import DimensionSummaryInput, DimensionSummarySource

DIGEST_DIMENSION = "dim:daily_digest"
DIGEST_SUMMARY_KIND = "cross_dimension_daily_digest"


@dataclass(frozen=True, slots=True)
class DigestCommit:
    object_id: str
    revision: int
    world_revision: int
    reused_existing: bool = False


def _stable_id(*parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


class DailyDigestService:
    """Prepare and persist the cross-dimension digest for one closed DAY window."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: Any,
        subject_id: str = "user_1",
        max_source_objects: int = 64,
    ) -> None:
        if max_source_objects < 1:
            raise ValueError("max_source_objects must be >= 1")
        self.store = store
        self.index = index
        self.subject_id = subject_id
        self.max_source_objects = max_source_objects

    # ------------------------------------------------------------------ ids

    def _summary_id(self, start: datetime, end: datetime) -> str:
        parts = (DIGEST_DIMENSION, "day", start.isoformat(), end.isoformat())
        scoped = "sum_" + _stable_id(self.subject_id, *parts)
        legacy = "sum_" + _stable_id(*parts)
        for candidate in (scoped, legacy):
            try:
                raw = self.store.get_payload(candidate)
            except StoreError as exc:
                if exc.code is ErrorCode.NOT_FOUND:
                    continue
                raise
            if raw.get("subject_id") != self.subject_id:
                if candidate == scoped:
                    raise ValueError("digest summary ID belongs to another subject")
                continue
            if (raw.get("metadata") or {}).get("dimension") != DIGEST_DIMENSION:
                raise ValueError("digest summary ID does not match its owner")
            return candidate
        return scoped

    # -------------------------------------------------------------- prepare

    def prepare(self, *, window_start: datetime, window_end: datetime) -> DimensionSummaryInput:
        start = as_utc(window_start, "window_start")
        end = as_utc(window_end, "window_end")
        if end < start:
            raise ValueError("window_end must not be before window_start")

        self.index.catch_up()
        source_world_revision = int(self.store.current_world_revision())
        target_id = self._summary_id(start, end)

        sources: list[DimensionSummarySource] = []
        for payload in self.store.list_payloads(
            object_type=ObjectType.SUMMARY, subject_id=self.subject_id,
        ):
            if str(payload.get("granularity") or "") != "day":
                continue
            metadata = payload.get("metadata") or {}
            dimension = metadata.get("dimension")
            if not isinstance(dimension, str) or not dimension or dimension == DIGEST_DIMENSION:
                continue
            if payload.get("status", "active") != "active":
                continue
            if payload.get("summary_status") != "current":
                continue
            extent = payload.get("summary_time")
            if not isinstance(extent, dict):
                continue
            try:
                summary_start = as_utc(
                    datetime.fromisoformat(str(extent.get("start")).replace("Z", "+00:00")),
                    "summary_time.start",
                )
                summary_end = as_utc(
                    datetime.fromisoformat(str(extent.get("end")).replace("Z", "+00:00")),
                    "summary_time.end",
                )
            except ValueError:
                continue
            if summary_start < start or summary_end > end:
                continue
            if payload.get("object_id") == target_id:
                continue
            sources.append(
                DimensionSummarySource(
                    object_id=str(payload["object_id"]),
                    revision=int(payload["revision"]),
                    object_type=ObjectType.SUMMARY.value,
                    occurred_at=summary_start,
                    text=str(payload.get("content") or ""),
                    metadata=dict(metadata),
                )
            )
        if len(sources) > self.max_source_objects:
            raise ValueError(
                "daily digest source count exceeds cap; refusing a truncated digest"
            )
        sources.sort(key=lambda item: (item.occurred_at, item.object_id))
        return DimensionSummaryInput(
            subject_id=self.subject_id,
            dimension=DIGEST_DIMENSION,
            granularity="day",
            window_start=start,
            window_end=end,
            source_world_revision=source_world_revision,
            sources=tuple(sources),
            truncated=False,
            max_source_objects=self.max_source_objects,
        )

    # ------------------------------------------------------------ validation

    def _validate_sources(self, prepared: DimensionSummaryInput) -> None:
        if prepared.subject_id != self.subject_id:
            raise ValueError("digest input must be bound to this subject; prepare again")
        if prepared.dimension != DIGEST_DIMENSION or prepared.granularity != "day":
            raise ValueError("digest input must target the digest dimension at day scale")
        if prepared.truncated:
            raise ValueError("cannot publish a truncated digest as CURRENT")
        if prepared.source_world_revision > self.store.current_world_revision():
            raise ValueError("digest input refers to a future World revision")
        if len(prepared.sources) > self.max_source_objects:
            raise ValueError("digest source count exceeds cap")
        seen = set()
        for source in prepared.sources:
            raw = self.store.get_payload(
                source.object_id,
                revision=source.revision,
                as_of_world_revision=prepared.source_world_revision,
            )
            current = self.store.get_payload(source.object_id)
            if (current["subject_id"] != self.subject_id
                    or int(current["revision"]) != source.revision
                    or current.get("object_type") != ObjectType.SUMMARY.value):
                raise ValueError("digest source must be a current summary of this subject")
            metadata = current.get("metadata") or {}
            if (metadata.get("dimension") == DIGEST_DIMENSION
                    or str(current.get("granularity") or "") != "day"
                    or current.get("status", "active") != "active"
                    or current.get("summary_status") != "current"):
                raise ValueError("digest source is not a current single-dimension day summary")
            extent = current.get("summary_time") or {}
            if (extent.get("start") != prepared.window_start.isoformat()
                    or extent.get("end") != prepared.window_end.isoformat()):
                # _summary_time serialization may differ in formatting; compare semantically.
                try:
                    s = as_utc(datetime.fromisoformat(
                        str(extent.get("start")).replace("Z", "+00:00")), "s")
                    e = as_utc(datetime.fromisoformat(
                        str(extent.get("end")).replace("Z", "+00:00")), "e")
                except ValueError:
                    raise ValueError("digest source has malformed summary_time")
                if s != prepared.window_start or e != prepared.window_end:
                    raise ValueError("digest source window mismatch")
            if source.text != str(current.get("content") or ""):
                raise ValueError("digest source does not match its pinned revision")
            key = (source.object_id, source.revision)
            if key in seen:
                raise ValueError("duplicate digest source")
            seen.add(key)

    # ---------------------------------------------------------------- commit

    def commit(
        self,
        prepared: DimensionSummaryInput,
        *,
        content: str,
        generated_at: datetime,
    ) -> DigestCommit:
        expected_world_revision = int(self.store.current_world_revision())
        self._validate_sources(prepared)
        text = content.strip()
        if not text:
            raise ValueError("digest content must be non-blank")
        generated = as_utc(generated_at, "generated_at")

        object_id = self._summary_id(prepared.window_start, prepared.window_end)

        latest: dict[str, Any] | None
        try:
            latest = self.store.get_payload(object_id)
        except StoreError as exc:
            if exc.code is not ErrorCode.NOT_FOUND:
                raise
            latest = None

        if (latest is not None and latest.get("summary_status") == "current"
                and latest.get("status", "active") == "active"
                and int(latest.get("source_world_revision", -1)) == prepared.source_world_revision):
            existing_refs = tuple(
                (str(item.get("object_id")), int(item.get("revision") or 0))
                for item in (latest.get("source_refs") or [])
            )
            prepared_refs = tuple(
                (item.object_id, item.revision) for item in prepared.sources
            )
            if existing_refs == prepared_refs:
                if str(latest.get("content") or "") != text:
                    raise ValueError(
                        "the same digest sources are already summarized with different content"
                    )
                return DigestCommit(
                    object_id=object_id,
                    revision=int(latest["revision"]),
                    world_revision=int(self.store.current_world_revision()),
                    reused_existing=True,
                )

        revision = 1 if latest is None else int(latest["revision"]) + 1
        summary_time = TemporalExtent(
            start=prepared.window_start,
            end=prepared.window_end,
            precision=TimePrecision.DAY,
        )
        digest = Summary(
            object_id=object_id,
            subject_id=self.subject_id,
            revision=revision,
            occurred=summary_time,
            learned_at=generated,
            recorded_at=generated,
            source_refs=[
                SourceRef(object_id=item.object_id, revision=item.revision)
                for item in prepared.sources
            ],
            created_by="daily_digest:model",
            summary_time=summary_time,
            granularity="day",
            content=text,
            source_world_revision=prepared.source_world_revision,
            coverage={
                "dimension": DIGEST_DIMENSION,
                "source_count": len(prepared.sources),
                "truncated": False,
                "source_dimensions": sorted(
                    (item.metadata.get("dimension") or "?") for item in prepared.sources
                ),
            },
            summary_status=SummaryStatus.CURRENT,
            metadata={
                "dimension": DIGEST_DIMENSION,
                "summary_kind": DIGEST_SUMMARY_KIND,
            },
        )

        op_key = _stable_id(object_id, revision, prepared.source_world_revision)
        operation = OperationRequest(
            operation_id=f"op_digest_{op_key}",
            operation_name="summary.commit_daily_digest",
            arguments={
                "dimension": DIGEST_DIMENSION,
                "granularity": "day",
                "source_world_revision": prepared.source_world_revision,
            },
            expected_world_revision=expected_world_revision,
            reason="commit model-generated cross-dimension daily digest",
            idempotency_key=f"digest:{op_key}",
            source_class=SourceClass.MAINTENANCE,
            maintenance_class=MaintenanceClass.SUMMARY_REBUILD,
        )
        dependencies: list[Dependency] = []
        for item in prepared.sources:
            dependencies.append(
                Dependency(
                    object_id="dep_" + _stable_id(
                        object_id, revision, item.object_id, item.revision,
                    ),
                    subject_id=self.subject_id,
                    learned_at=generated,
                    recorded_at=generated,
                    created_by="daily_digest:dependency",
                    dependent_ref=ObjectRef(object_id=object_id, revision=revision),
                    dependency_ref=ObjectRef(
                        object_id=item.object_id, revision=item.revision,
                    ),
                    dependency_type="digest_uses_day_summary",
                )
            )

        result = self.store.commit([digest, *dependencies], operation)
        self.index.catch_up()
        return DigestCommit(
            object_id=object_id,
            revision=revision,
            world_revision=result.world_revision,
            reused_existing=result.idempotent_replay,
        )
