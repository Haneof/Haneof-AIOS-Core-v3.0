"""Topic-gated proactive memory recommendation for AIOS v3.0.

The recommender is a consumer of the public world index. It never owns search
truth and never injects history when the current conversation has no valid topic.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aios_core.contracts.enums import ErrorCode, ObjectType
from aios_core.ingest.conversation import INTERACTION_DIMENSION
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
        antecedent_fallback: bool = False,
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

        used = {(card.object_id, card.revision) for card in cards}
        antecedent_added = False
        if antecedent_fallback and len(cards) < take:
            # Deictic/elliptical follow-ups can have zero lexical overlap with the
            # antecedent. Expose only a small set of current/recent world candidates;
            # do not choose which one the user means.
            recent = self.index.recent_candidates(
                subject=subject_id,
                object_types=(
                    ObjectType.OBSERVATION.value,
                    ObjectType.EVENT.value,
                    ObjectType.GOAL.value,
                    ObjectType.TASK.value,
                    ObjectType.CLAIM.value,
                    ObjectType.ENTITY.value,
                    ObjectType.RELATION.value,
                ),
                limit=max(take * 8, 24),
            )
            external_or_structured: list[MemoryCard] = []
            prior_user_dialogue: list[MemoryCard] = []
            for hit in recent.hits:
                ref = (hit.object_id, hit.revision)
                if ref in used:
                    continue
                try:
                    payload = self.store.get_payload(
                        hit.object_id,
                        revision=hit.revision,
                    )
                except StoreError as exc:
                    if exc.code is not ErrorCode.NOT_FOUND:
                        raise
                    continue

                metadata = payload.get("metadata")
                if not isinstance(metadata, dict):
                    metadata = {}
                session_id = metadata.get("session_id")
                if (
                    exclude_session_id is not None
                    and session_id == exclude_session_id
                ):
                    continue

                match_reason = "cross_session_antecedent_candidate"
                if hit.object_type == ObjectType.OBSERVATION.value:
                    dimension = str(metadata.get("dimension") or "")
                    source_kind = str(
                        payload.get("source_kind") or ""
                    ).strip().casefold()
                    is_dialogue = (
                        dimension == INTERACTION_DIMENSION
                        or source_kind in {"conversation", "user_ai_interaction"}
                    )
                    if is_dialogue:
                        # Assistant echoes are not independent antecedent evidence.
                        if str(metadata.get("role") or "") != "user":
                            continue
                        if not session_id:
                            continue
                        card = MemoryCard(
                            object_id=hit.object_id,
                            revision=hit.revision,
                            object_type=hit.object_type,
                            dimension=hit.dimension,
                            excerpt=hit.excerpt,
                            retrieval_score=0,
                            match_reason=match_reason,
                        )
                        prior_user_dialogue.append(card)
                        continue

                external_or_structured.append(
                    MemoryCard(
                        object_id=hit.object_id,
                        revision=hit.revision,
                        object_type=hit.object_type,
                        dimension=hit.dimension,
                        excerpt=hit.excerpt,
                        retrieval_score=0,
                        match_reason=match_reason,
                    )
                )

            # Favor current structured/external facts, then at most two prior user
            # utterances. The list stays small and ambiguity remains visible.
            for card in [
                *external_or_structured[: max(1, take - 2)],
                *prior_user_dialogue[:2],
                *external_or_structured[max(1, take - 2) :],
            ]:
                ref = (card.object_id, card.revision)
                if ref in used:
                    continue
                cards.append(card)
                used.add(ref)
                antecedent_added = True
                if len(cards) >= take:
                    break

        if antecedent_added:
            reason = (
                "topic_matched_history_with_antecedent_candidates"
                if any(card.retrieval_score > 0 for card in cards)
                else "cross_session_antecedent_candidates"
            )
        else:
            reason = "topic_matched_history" if cards else "topic_has_no_matching_history"

        return RecommendationBundle(
            current_topic=topic,
            topic_gate_open=True,
            world_revision=page.world_revision,
            index_watermark=page.index_watermark,
            cards=tuple(cards),
            reason=reason,
        )
