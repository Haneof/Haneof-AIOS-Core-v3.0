"""Single-dimension temporal summaries for AIOS v3.0.

The system selects a time window and source objects. A real cognitive model produces
the descriptive summary text. This service validates provenance and commits the
result; it does not infer cross-dimensional meaning or causality.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import ErrorCode, MaintenanceClass, SourceClass, SummaryStatus
from aios_core.contracts.models import Dependency, Summary
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import TemporalExtent, TimePrecision, as_utc
from aios_core.query.search import WorldSearchIndex, derive_dimension
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError


class DimensionSummarySource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    object_id: str
    revision: int = Field(ge=1)
    object_type: str
    occurred_at: datetime | None = None
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_time(self) -> "DimensionSummarySource":
        if self.occurred_at is not None:
            as_utc(self.occurred_at, "occurred_at")
        return self


class DimensionSummaryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject_id: str = ""  # Legacy unbound inputs must be prepared again before commit.
    include_summary_sources: bool = False
    dimension: str = Field(min_length=1)
    granularity: str = Field(min_length=1)
    window_start: datetime
    window_end: datetime
    source_world_revision: int = Field(ge=0)
    sources: tuple[DimensionSummarySource, ...]
    truncated: bool = False

    @model_validator(mode="after")
    def validate_window(self) -> "DimensionSummaryInput":
        start = as_utc(self.window_start, "window_start")
        end = as_utc(self.window_end, "window_end")
        if end < start:
            raise ValueError("window_end must not be before window_start")
        return self


@dataclass(frozen=True, slots=True)
class SummaryCommit:
    object_id: str
    revision: int
    world_revision: int
    reused_existing: bool = False


def _stable_id(*parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _text_from_payload(payload: dict[str, Any]) -> str:
    object_type = str(payload.get("object_type") or "")
    if object_type == "observation":
        value = payload.get("value")
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if object_type == "event":
        return " | ".join(
            part for part in (
                str(payload.get("title") or "").strip(),
                str(payload.get("interpretation") or "").strip(),
            ) if part
        )
    if object_type == "claim":
        return str(payload.get("content") or "")
    if object_type == "summary":
        return str(payload.get("content") or "")
    if object_type == "entity":
        names = [payload.get("canonical_name"), *(payload.get("aliases") or [])]
        return " / ".join(str(x) for x in names if x)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)[:2000]


def _occurred_start(payload: dict[str, Any]) -> datetime | None:
    occurred = payload.get("occurred")
    if isinstance(occurred, dict):
        raw = occurred.get("start")
        if isinstance(raw, str):
            try:
                return as_utc(datetime.fromisoformat(raw), "occurred.start")
            except ValueError:
                pass
    raw = payload.get("recorded_at")
    if isinstance(raw, str):
        try:
            return as_utc(datetime.fromisoformat(raw), "recorded_at")
        except ValueError:
            pass
    return None


_SUMMARY_SCALE_RANK = {
    "day": 0,
    "week": 1,
    "month": 2,
    "quarter": 3,
    "half_year": 4,
    "year": 5,
    "multi_year": 6,
    "multi_year_3y": 6,
    "multi_year_5y": 7,
    "decade": 8,
}

_PRECISION = {
    "day": TimePrecision.DAY,
    "week": TimePrecision.WEEK,
    "month": TimePrecision.MONTH,
    "quarter": TimePrecision.QUARTER,
    "half_year": TimePrecision.HALF_YEAR,
    "year": TimePrecision.YEAR,
    "multi_year": TimePrecision.MULTI_YEAR,
    "multi_year_3y": TimePrecision.MULTI_YEAR,
    "multi_year_5y": TimePrecision.MULTI_YEAR,
    "decade": TimePrecision.MULTI_YEAR,
}


class DimensionSummaryService:
    """Prepare and persist a summary for one dimension and one time window."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex,
        subject_id: str = "user_1",
        max_source_objects: int = 500,
        source_subject_ids: Sequence[str] | None = None,
    ) -> None:
        if max_source_objects < 1:
            raise ValueError("max_source_objects must be >= 1")
        self.store = store
        self.index = index
        self.subject_id = subject_id
        self.source_subject_ids = tuple(dict.fromkeys((subject_id, *(source_subject_ids or ()))))
        self.max_source_objects = max_source_objects

    def _summary_id(self, dimension: str, granularity: str,
                    start: datetime, end: datetime) -> str:
        parts = (dimension, granularity, start.isoformat(), end.isoformat())
        scoped = "sum_" + _stable_id(self.subject_id, *parts)
        legacy = "sum_" + _stable_id(*parts)
        for candidate in (scoped, legacy):
            try:
                raw = self.store.get_payload(candidate)
            except StoreError as exc:
                if exc.code is ErrorCode.NOT_FOUND:
                    continue
                raise
            owned = raw.get("subject_id") == self.subject_id
            if not owned:
                if candidate == scoped:
                    raise ValueError("summary ID belongs to another subject")
                continue
            summary = Summary.model_validate(raw)
            if (summary.metadata.get("dimension") != dimension
                    or summary.granularity != granularity
                    or summary.summary_time.start != start
                    or summary.summary_time.end != end):
                raise ValueError("summary ID does not match its owner/window")
            return candidate
        return scoped

    def _check_owner(self, prepared: DimensionSummaryInput) -> None:
        if prepared.subject_id != self.subject_id:
            raise ValueError("summary input must be bound to this subject; prepare again")

    def _validate_sources(self, prepared: DimensionSummaryInput) -> None:
        self._check_owner(prepared)
        if prepared.truncated:
            raise ValueError("cannot publish a truncated summary as CURRENT")
        if prepared.source_world_revision > self.store.current_world_revision():
            raise ValueError("summary input refers to a future World revision")
        target_rank = _SUMMARY_SCALE_RANK.get(prepared.granularity)
        seen = set()
        for source in prepared.sources:
            raw = self.store.get_payload(source.object_id)
            # A caller must not label a newer source as belonging to an older cut.
            self.store.get_payload(
                source.object_id, revision=source.revision,
                as_of_world_revision=prepared.source_world_revision,
            )
            if (raw["subject_id"] not in self.source_subject_ids
                    or raw["revision"] != source.revision
                    or raw["object_type"] != source.object_type):
                raise ValueError("summary source must be current, typed and within scope")
            if (raw.get("status", "active") in WorldSearchIndex._INACTIVE_CURRENT_STATUSES
                    or raw.get("summary_status", "current") != "current"
                    or raw.get("event_status") in {"rejected", "merged", "split"}
                    or raw.get("stale", False)):
                raise ValueError("summary source is not current/admissible")
            if derive_dimension(raw, source.object_type) != prepared.dimension:
                raise ValueError("summary source belongs to a different dimension")
            if source.object_type == "summary":
                rank = _SUMMARY_SCALE_RANK.get(raw.get("granularity"))
                if (not prepared.include_summary_sources or rank is None
                        or target_rank is None or rank >= target_rank):
                    raise ValueError("summary sources must aggregate strictly bottom-up")
            if (source.text != _text_from_payload(raw)
                    or source.occurred_at != _occurred_start(raw)
                    or source.metadata != (raw.get("metadata") or {})):
                raise ValueError("summary source does not match its pinned revision")
            key = (source.object_id, source.revision)
            if key in seen:
                raise ValueError("duplicate summary source")
            seen.add(key)
        # A bounded input is not a completeness certificate by itself: new facts
        # may have arrived while the model was generating the summary. Recheck
        # selection as well as pinned revisions; the caller's CAS covers races
        # between this validation and publication.
        current = self.prepare(
            dimension=prepared.dimension, granularity=prepared.granularity,
            window_start=prepared.window_start, window_end=prepared.window_end,
            include_summary_sources=prepared.include_summary_sources,
        )
        current_refs = {(item.object_id, item.revision) for item in current.sources}
        if current.truncated or current_refs != seen:
            raise ValueError("summary source window changed or is incomplete; prepare again")

    def prepare(
        self,
        *,
        dimension: str,
        granularity: str,
        window_start: datetime,
        window_end: datetime,
        include_summary_sources: bool = False,
    ) -> DimensionSummaryInput:
        start = as_utc(window_start, "window_start")
        end = as_utc(window_end, "window_end")
        if end < start:
            raise ValueError("window_end must not be before window_start")

        self.index.catch_up()
        source_world_revision = int(self.store.current_world_revision())
        target_summary_id = self._summary_id(
            dimension,
            granularity,
            start,
            end,
        )
        target_rank = _SUMMARY_SCALE_RANK.get(granularity)

        # Fetch a bounded superset because same/higher-level Summary objects are
        # intentionally excluded below. Computing truncation before this filter can
        # both publish self-dependencies and hide valid lower-level sources.
        scan_limit = max(
            self.max_source_objects + 1,
            min(10_000, self.max_source_objects * 8 + 64),
        )
        hits = []
        saturated = self.index.lag() > 0
        for subject in self.source_subject_ids:
            page = self.index.search_mind(
                subject=subject, dimension=dimension,
                time_range=(start, end), limit=scan_limit,
            )
            hits.extend(page.hits)
            saturated |= len(page.hits) >= scan_limit

        eligible: list[tuple[Any, dict[str, Any]]] = []
        for hit in hits:
            if hit.object_id == target_summary_id:
                continue
            payload = self.store.get_payload(hit.object_id, revision=hit.revision)
            if hit.object_type == "summary":
                if not include_summary_sources:
                    continue
                source_granularity = str(payload.get("granularity") or "")
                source_rank = _SUMMARY_SCALE_RANK.get(source_granularity)
                # Summary aggregation is strictly bottom-up. Equal/higher scale
                # summaries can create direct self-dependency or inter-scale cycles.
                if (
                    target_rank is None
                    or source_rank is None
                    or source_rank >= target_rank
                ):
                    continue
            eligible.append((hit, payload))

        truncated = (saturated or len(eligible) > self.max_source_objects
                     or source_world_revision != self.store.current_world_revision())
        sources: list[DimensionSummarySource] = []
        for hit, payload in eligible[: self.max_source_objects]:
            metadata = payload.get("metadata")
            sources.append(
                DimensionSummarySource(
                    object_id=hit.object_id,
                    revision=hit.revision,
                    object_type=hit.object_type,
                    occurred_at=_occurred_start(payload),
                    text=_text_from_payload(payload),
                    metadata=dict(metadata) if isinstance(metadata, dict) else {},
                )
            )

        sources.sort(
            key=lambda item: (
                item.occurred_at.timestamp() if item.occurred_at is not None else float("-inf"),
                item.object_id,
            )
        )
        return DimensionSummaryInput(
            subject_id=self.subject_id,
            include_summary_sources=include_summary_sources,
            dimension=dimension,
            granularity=granularity,
            window_start=start,
            window_end=end,
            source_world_revision=source_world_revision,
            sources=tuple(sources),
            truncated=truncated,
        )

    def mark_stale_if_present(
        self,
        prepared: DimensionSummaryInput,
        *,
        changed_at: datetime,
        reason: str,
    ) -> SummaryCommit | None:
        """Forward-mark an existing window Summary stale when completeness is lost."""

        self._check_owner(prepared)
        expected_world_revision = int(self.store.current_world_revision())
        changed = as_utc(changed_at, "changed_at")
        object_id = self._summary_id(
            prepared.dimension, prepared.granularity,
            prepared.window_start, prepared.window_end,
        )
        try:
            latest_payload = self.store.get_payload(object_id)
        except StoreError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            raise

        latest = Summary.model_validate(latest_payload)
        if latest.summary_status is SummaryStatus.STALE:
            return SummaryCommit(
                object_id=latest.object_id,
                revision=latest.revision,
                world_revision=int(self.store.current_world_revision()),
                reused_existing=True,
            )

        revision = latest.revision + 1
        metadata = dict(latest.metadata)
        metadata.update(
            {
                "dimension": prepared.dimension,
                "summary_kind": "single_dimension_temporal",
                "stale_reason": reason.strip(),
                "stale_at": changed.isoformat(),
                "stale_due_to_incomplete_source_window": True,
            }
        )
        stale = Summary.model_validate(
            {
                **latest.model_dump(mode="python", round_trip=True),
                "revision": revision,
                "learned_at": changed,
                "recorded_at": changed,
                "source_world_revision": int(self.store.current_world_revision()),
                "summary_status": SummaryStatus.STALE,
                "coverage": {
                    **dict(latest.coverage),
                    "truncated": True,
                    "stale_reason": reason.strip(),
                },
                "metadata": metadata,
            }
        )

        dependencies: list[Dependency] = []
        for ref in stale.source_refs:
            dependencies.append(
                Dependency(
                    object_id="dep_" + _stable_id(
                        stale.object_id,
                        revision,
                        ref.object_id,
                        ref.revision,
                        "stale_source",
                    ),
                    subject_id=self.subject_id,
                    learned_at=changed,
                    recorded_at=changed,
                    created_by="dimension_summary:dependency",
                    dependent_ref=ObjectRef(
                        object_id=stale.object_id,
                        revision=revision,
                    ),
                    dependency_ref=ObjectRef(
                        object_id=ref.object_id,
                        revision=ref.revision,
                    ),
                    dependency_type="stale_summary_preserves_source",
                )
            )

        op_key = _stable_id(
            "stale",
            object_id,
            revision,
            int(self.store.current_world_revision()),
            reason.strip(),
        )
        result = self.store.commit(
            [stale, *dependencies],
            OperationRequest(
                operation_id=f"op_summary_stale_{op_key}",
                operation_name="summary.mark_stale",
                arguments={
                    "summary_id": object_id,
                    "revision": revision,
                    "dimension": prepared.dimension,
                    "granularity": prepared.granularity,
                },
                expected_world_revision=expected_world_revision,
                reason=reason.strip(),
                idempotency_key=f"summary-stale:{op_key}",
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.SUMMARY_REBUILD,
            ),
        )
        self.index.catch_up()
        return SummaryCommit(
            object_id=object_id,
            revision=revision,
            world_revision=result.world_revision,
            reused_existing=result.idempotent_replay,
        )

    def commit(
        self,
        prepared: DimensionSummaryInput,
        *,
        content: str,
        generated_at: datetime,
    ) -> SummaryCommit:
        expected_world_revision = int(self.store.current_world_revision())
        self._validate_sources(prepared)
        text = content.strip()
        if not text:
            raise ValueError("summary content must be non-blank")
        generated = as_utc(generated_at, "generated_at")

        object_id = self._summary_id(
            prepared.dimension, prepared.granularity,
            prepared.window_start, prepared.window_end,
        )

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
            if str(latest.get("content") or "") != text:
                raise ValueError(
                    "the same source world revision is already summarized with different content"
                )
            return SummaryCommit(
                object_id=object_id,
                revision=int(latest["revision"]),
                world_revision=int(self.store.current_world_revision()),
                reused_existing=True,
            )

        revision = 1 if latest is None else int(latest["revision"]) + 1
        precision = _PRECISION.get(prepared.granularity, TimePrecision.UNKNOWN)
        summary_time = TemporalExtent(
            start=prepared.window_start,
            end=prepared.window_end,
            precision=precision,
        )
        summary = Summary(
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
            created_by="dimension_summary:model",
            summary_time=summary_time,
            granularity=prepared.granularity,
            content=text,
            source_world_revision=prepared.source_world_revision,
            coverage={
                "dimension": prepared.dimension,
                "source_count": len(prepared.sources),
                "truncated": prepared.truncated,
            },
            summary_status=SummaryStatus.CURRENT,
            metadata={
                "dimension": prepared.dimension,
                "summary_kind": "single_dimension_temporal",
            },
        )

        op_key = _stable_id(
            object_id,
            revision,
            prepared.source_world_revision,
        )
        operation = OperationRequest(
            operation_id=f"op_summary_{op_key}",
            operation_name="summary.commit_dimension",
            arguments={
                "dimension": prepared.dimension,
                "granularity": prepared.granularity,
                "source_world_revision": prepared.source_world_revision,
            },
            expected_world_revision=expected_world_revision,
            reason="commit model-generated single-dimension temporal summary",
            idempotency_key=f"summary:{op_key}",
            source_class=SourceClass.MAINTENANCE,
            maintenance_class=MaintenanceClass.SUMMARY_REBUILD,
        )
        dependencies: list[Dependency] = []
        for item in prepared.sources:
            dep_id = "dep_" + _stable_id(
                object_id,
                revision,
                item.object_id,
                item.revision,
            )
            dependencies.append(
                Dependency(
                    object_id=dep_id,
                    subject_id=self.subject_id,
                    learned_at=generated,
                    recorded_at=generated,
                    created_by="dimension_summary:dependency",
                    dependent_ref=ObjectRef(object_id=object_id, revision=revision),
                    dependency_ref=ObjectRef(
                        object_id=item.object_id,
                        revision=item.revision,
                    ),
                    dependency_type="summary_uses_source",
                )
            )

        result = self.store.commit([summary, *dependencies], operation)
        self.index.catch_up()
        return SummaryCommit(
            object_id=object_id,
            revision=revision,
            world_revision=result.world_revision,
            reused_existing=result.idempotent_replay,
        )
