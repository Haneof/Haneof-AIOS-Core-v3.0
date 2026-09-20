"""Topic-gated proactive memory recommendation for AIOS v3.0.

The recommender is a consumer of the public world index. It never owns search
truth and never injects history when the current conversation has no valid topic.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aios_core.contracts.enums import ErrorCode
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError


class MemoryCard(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    object_id: str
    revision: int = Field(ge=1)
    object_type: str
    dimension: str
    excerpt: str
    retrieval_score: int = Field(ge=0)
    match_reason: str = "current_topic_index_overlap"


class RecommendationBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    current_topic: str | None = None
    topic_gate_open: bool = False
    world_revision: int = Field(ge=0)
    index_watermark: int = Field(ge=0)
    cards: tuple[MemoryCard, ...] = ()
    reason: str


class ProactiveMemoryRecommender:
    """Prepare a small historical memory bundle before model inference."""

    def __init__(
        self,
        *,
        index: WorldSearchIndex,
        store: SQLiteWorldStore,
        default_limit: int = 5,
    ) -> None:
        if default_limit < 1:
            raise ValueError("default_limit must be >= 1")
        self.index = index
        self.store = store
        self.default_limit = default_limit

    def recommend(
        self,
        *,
        current_topic: str | None,
        subject_id: str | None = None,
        exclude_session_id: str | None = None,
        limit: int | None = None,
        history_needed: bool | None = None,
    ) -> RecommendationBundle:
        topic = (current_topic or "").strip()
        current_world_revision = int(self.store.current_world_revision())

        if not topic:
            return RecommendationBundle(
                current_topic=None,
                topic_gate_open=False,
                world_revision=current_world_revision,
                index_watermark=self.index.watermark(),
                cards=(),
                reason="no_current_topic",
            )
        if history_needed is False:
            return RecommendationBundle(
                current_topic=topic,
                topic_gate_open=True,
                world_revision=current_world_revision,
                index_watermark=self.index.watermark(),
                cards=(),
                reason="current_topic_does_not_need_history",
            )


        take = self.default_limit if limit is None else max(1, int(limit))
        page = self.index.recall_candidates(
            topic,
            subject=subject_id,
            limit=max(take * 4, take),
        )

        cards: list[MemoryCard] = []
        for hit in page.hits:
            try:
                payload = self.store.get_payload(hit.object_id, revision=hit.revision)
            except StoreError as exc:
                if exc.code is not ErrorCode.NOT_FOUND:
                    raise
                # A rebuildable projection can briefly retain a stale locator. Missing
                # projected objects are skipped; durable storage failures are not hidden.
                continue

            metadata = payload.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}

            if exclude_session_id is not None and metadata.get("session_id") == exclude_session_id:
                continue

            cards.append(
                MemoryCard(
                    object_id=hit.object_id,
                    revision=hit.revision,
                    object_type=hit.object_type,
                    dimension=hit.dimension,
                    excerpt=hit.excerpt,
                    retrieval_score=hit.score,
                )
            )
            if len(cards) >= take:
                break

        return RecommendationBundle(
            current_topic=topic,
            topic_gate_open=True,
            world_revision=page.world_revision,
            index_watermark=page.index_watermark,
            cards=tuple(cards),
            reason="topic_matched_history" if cards else "topic_has_no_matching_history",
        )
