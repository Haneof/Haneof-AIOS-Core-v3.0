"""ALL_DIMENSIONS world projection for AIOS v3.0.

This module builds a transient cross-dimension observation view over one time
window. It preserves each source object's type and provenance. It never writes a
parent dimension, never fabricates a causal narrative, and never changes world truth.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.time import as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore


class ProjectionItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    object_id: str
    revision: int = Field(ge=1)
    object_type: str
    dimension: str
    occurred_at: datetime | None = None
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_time(self) -> "ProjectionItem":
        if self.occurred_at is not None:
            as_utc(self.occurred_at, "occurred_at")
        return self


class DimensionProjectionSlice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension: str = Field(min_length=1)
    items: tuple[ProjectionItem, ...] = ()
    truncated: bool = False


class AllDimensionsProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    window_start: datetime
    window_end: datetime
    world_revision: int = Field(ge=0)
    index_watermark: int = Field(ge=0)
    slices: tuple[DimensionProjectionSlice, ...]
    query: str | None = None

    @model_validator(mode="after")
    def validate_window(self) -> "AllDimensionsProjection":
        start = as_utc(self.window_start, "window_start")
        end = as_utc(self.window_end, "window_end")
        if end < start:
            raise ValueError("window_end must not be before window_start")
        return self

    def as_model_context(self) -> dict[str, Any]:
        """Return a model-facing view that contains observations, not conclusions."""
        return self.model_dump(mode="python")


def _text(payload: dict[str, Any]) -> str:
    object_type = str(payload.get("object_type") or "")
    if object_type == "summary":
        return str(payload.get("content") or "")
    if object_type == "event":
        parts = [
            str(payload.get("title") or "").strip(),
            str(payload.get("interpretation") or "").strip(),
        ]
        return " | ".join(part for part in parts if part)
    if object_type == "claim":
        return str(payload.get("content") or "")
    if object_type == "observation":
        value = payload.get("value")
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if object_type == "relation":
        return str(payload.get("relation_type") or "")
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)[:2000]


def _occurred(payload: dict[str, Any]) -> datetime | None:
    for key in ("summary_time", "event_time", "valid_time", "occurred"):
        extent = payload.get(key)
        if isinstance(extent, dict):
            raw = extent.get("start")
            if isinstance(raw, str):
                try:
                    return as_utc(datetime.fromisoformat(raw), f"{key}.start")
                except ValueError:
                    pass
    raw = payload.get("recorded_at")
    if isinstance(raw, str):
        try:
            return as_utc(datetime.fromisoformat(raw), "recorded_at")
        except ValueError:
            pass
    return None


class AllDimensionsProjectionService:
    """Build a cross-dimension observation window without producing cognition."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex,
        subject_id: str = "user_1",
        max_items_per_dimension: int = 12,
    ) -> None:
        if max_items_per_dimension < 1:
            raise ValueError("max_items_per_dimension must be >= 1")
        self.store = store
        self.index = index
        self.subject_id = subject_id
        self.max_items_per_dimension = max_items_per_dimension

    def project(
        self,
        *,
        dimensions: Sequence[str],
        window_start: datetime,
        window_end: datetime,
        query: str | None = None,
        object_types: Sequence[str] = ("summary", "event", "claim", "observation"),
    ) -> AllDimensionsProjection:
        start = as_utc(window_start, "window_start")
        end = as_utc(window_end, "window_end")
        if end < start:
            raise ValueError("window_end must not be before window_start")

        clean_dimensions = tuple(dict.fromkeys(d.strip() for d in dimensions if d.strip()))
        if not clean_dimensions:
            raise ValueError("ALL_DIMENSIONS projection requires at least one explicit dimension")

        slices: list[DimensionProjectionSlice] = []
        max_watermark = self.index.watermark()
        world_revision = int(self.store.current_world_revision())

        for dimension in clean_dimensions:
            # Search is used only as a world locator. The projection keeps original
            # object types and does not turn co-occurrence into meaning.
            if query and query.strip():
                page = self.index.recall_candidates(
                    query.strip(),
                    subject=self.subject_id,
                    dimension=dimension,
                    object_types=object_types,
                    time_range=(start, end),
                    limit=self.max_items_per_dimension * 4,
                )
            else:
                page = self.index.search_mind(
                    dimension=dimension,
                    object_types=object_types,
                    time_range=(start, end),
                    include_annotations=True,
                    limit=self.max_items_per_dimension * 4,
                )

            max_watermark = max(max_watermark, page.index_watermark)
            world_revision = max(world_revision, page.world_revision)

            latest_by_id: dict[str, Any] = {}
            for hit in page.hits:
                current = latest_by_id.get(hit.object_id)
                if current is None or hit.revision > current.revision:
                    latest_by_id[hit.object_id] = hit

            candidates = list(latest_by_id.values())
            # Prefer coarse summaries when they exist, then events/claims, while
            # retaining observations for drill-down and evidence.
            type_rank = {"summary": 0, "event": 1, "claim": 2, "reinterpretation": 2, "observation": 3}
            candidates.sort(
                key=lambda hit: (
                    type_rank.get(hit.object_type, 4),
                    -hit.revision,
                    hit.object_id,
                )
            )

            truncated = len(candidates) > self.max_items_per_dimension
            items: list[ProjectionItem] = []
            for hit in candidates[: self.max_items_per_dimension]:
                try:
                    payload = self.store.get_payload(hit.object_id, revision=hit.revision)
                except Exception:
                    # Projection-only annotations may not exist in world storage.
                    payload = {
                        "object_type": hit.object_type,
                        "metadata": {},
                        "recorded_at": None,
                    }
                metadata = payload.get("metadata")
                items.append(
                    ProjectionItem(
                        object_id=hit.object_id,
                        revision=hit.revision,
                        object_type=hit.object_type,
                        dimension=dimension,
                        occurred_at=_occurred(payload),
                        text=_text(payload) or hit.excerpt,
                        metadata=dict(metadata) if isinstance(metadata, dict) else {},
                    )
                )

            slices.append(
                DimensionProjectionSlice(
                    dimension=dimension,
                    items=tuple(items),
                    truncated=truncated,
                )
            )

        return AllDimensionsProjection(
            window_start=start,
            window_end=end,
            world_revision=world_revision,
            index_watermark=max_watermark,
            slices=tuple(slices),
            query=(query or "").strip() or None,
        )
