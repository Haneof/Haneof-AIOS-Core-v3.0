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

from aios_core.contracts.enums import MaintenanceClass, SourceClass, SummaryStatus
from aios_core.contracts.models import Dependency, Summary
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import TemporalExtent, TimePrecision, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore


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
    raw = "|".join(str(part) for part in parts)
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
    ) -> None:
        if max_source_objects < 1:
            raise ValueError("max_source_objects must be >= 1")
        self.store = store
        self.index = index
        self.subject_id = subject_id
        self.max_source_objects = max_source_objects

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

        source_world_revision = int(self.store.current_world_revision())
        page = self.index.search_mind(
            dimension=dimension,
            time_range=(start, end),
            limit=self.max_source_objects + 1,
        )

        truncated = len(page.hits) > self.max_source_objects
        sources: list[DimensionSummarySource] = []
        for hit in page.hits[: self.max_source_objects]:
            if hit.object_type == "summary" and not include_summary_sources:
                continue
            payload = self.store.get_payload(hit.object_id, revision=hit.revision)
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
            dimension=dimension,
            granularity=granularity,
            window_start=start,
            window_end=end,
            source_world_revision=source_world_revision,
            sources=tuple(sources),
            truncated=truncated,
        )

    def commit(
        self,
        prepared: DimensionSummaryInput,
        *,
        content: str,
        generated_at: datetime,
    ) -> SummaryCommit:
        text = content.strip()
        if not text:
            raise ValueError("summary content must be non-blank")
        generated = as_utc(generated_at, "generated_at")

        object_id = "sum_" + _stable_id(
            prepared.dimension,
            prepared.granularity,
            prepared.window_start.isoformat(),
            prepared.window_end.isoformat(),
        )

        latest: dict[str, Any] | None
        try:
            latest = self.store.get_payload(object_id)
        except Exception:
            latest = None

        if latest is not None and int(latest.get("source_world_revision", -1)) == prepared.source_world_revision:
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
            expected_world_revision=self.store.current_world_revision(),
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
