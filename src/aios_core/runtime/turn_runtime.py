"""First runnable fused AIOS v3.0 turn loop.

This module connects proactive recommendation, context assembly, model-driven
capabilities and unified-world conversation writeback. It is intentionally small:
advanced summaries, AI-self writeback and policy learning are layered on after this
vertical slice stays green.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from aios_core.ai_world import (
    AIWorldClaimRequest,
    AIWorldCognitionService,
    AIWorldDomain,
)
from aios_core.context.controller import ContextController, ModelContextBundle
from aios_core.ingest.conversation import ConversationCommit, ConversationIngestor
from aios_core.projections.all_dimensions import AllDimensionsProjectionService
from aios_core.query.search import WorldSearchIndex
from aios_core.recommendation.proactive import (
    ProactiveMemoryRecommender,
    RecommendationBundle,
)
from aios_core.revision.service import ClaimRevisionRequest, CognitionRevisionService
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService
from aios_core.contracts.refs import ObjectRef

from .capabilities import CapabilityKind, CapabilityRegistry, CapabilitySpec
from .cognitive_runtime import CognitiveRuntime, ModelHandler, RuntimeTurnResult


@dataclass(frozen=True, slots=True)
class FusedTurnResult:
    runtime: RuntimeTurnResult
    recommendation: RecommendationBundle
    context: ModelContextBundle
    conversation_commit: ConversationCommit


class FusedTurnRuntime:
    """Minimal vertical slice: world -> recall -> model -> world."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex,
        model_handler: ModelHandler,
        subject_id: str = "user_1",
        context_controller: ContextController | None = None,
        recommendation_limit: int = 5,
        max_tool_rounds: int = 4,
    ) -> None:
        self.store = store
        self.index = index
        self.subject_id = subject_id
        self.ingestor = ConversationIngestor(store, subject_id=subject_id)
        self.recommender = ProactiveMemoryRecommender(
            index=index,
            store=store,
            default_limit=recommendation_limit,
        )
        self.context_controller = context_controller or ContextController()
        self.all_dimensions = AllDimensionsProjectionService(
            store=store,
            index=index,
            subject_id=subject_id,
        )
        self.writeback = CognitionWritebackService(
            store=store,
            index=index,
            subject_id=subject_id,
        )
        self.ai_world = AIWorldCognitionService(
            store=store,
            index=index,
            user_id=subject_id,
        )
        self.revision = CognitionRevisionService(
            store=store,
            index=index,
            subject_id=subject_id,
        )
        self._active_turn_time: datetime | None = None

        registry = CapabilityRegistry()
        registry.register(
            CapabilitySpec(
                name="search_world",
                description="Recall candidate world objects related to a query.",
                kind=CapabilityKind.READ,
                input_schema={"query": "string", "limit": "integer?"},
            ),
            self._search_world,
        )
        registry.register(
            CapabilitySpec(
                name="inspect_world_object",
                description="Read one pinned or latest world object by object id.",
                kind=CapabilityKind.READ,
                input_schema={"object_id": "string", "revision": "integer?"},
            ),
            self._inspect_world_object,
        )
        registry.register(
            CapabilitySpec(
                name="read_ai_world",
                description=(
                    "Read current evidence-grounded AI cognition across user understanding, "
                    "relationship, self, intent, strategy, boundary, personality and calibration."
                ),
                kind=CapabilityKind.READ,
                input_schema={
                    "domains": "array[string]?",
                    "scope_key": "string?",
                    "limit": "integer?",
                },
            ),
            self._read_ai_world,
        )
        registry.register(
            CapabilitySpec(
                name="request_all_dimensions_projection",
                description=(
                    "Observe several parallel dimensions in one time window without "
                    "turning co-occurrence into a causal conclusion."
                ),
                kind=CapabilityKind.READ,
                input_schema={
                    "dimensions": "array[string]",
                    "window_start": "ISO-8601 datetime",
                    "window_end": "ISO-8601 datetime",
                    "query": "string?",
                },
            ),
            self._request_all_dimensions_projection,
        )
        registry.register(
            CapabilitySpec(
                name="commit_claim",
                description=(
                    "Persist a revisable AI cognition Claim grounded in pinned world evidence. "
                    "This capability cannot create Observation facts."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "content": "string",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "confidence": "number[0,1]",
                    "dimension": "string",
                    "claim_type": "string?",
                    "knowledge_state": "string?",
                },
            ),
            self._commit_claim,
        )
        registry.register(
            CapabilitySpec(
                name="commit_ai_world_claim",
                description=(
                    "Persist a typed AI-world cognition using the unified "
                    "EvidenceSet + Claim + Dependency path."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "domain": "user_understanding|relationship|self|intent|strategy|cognitive_boundary|personality|calibration",
                    "statement": "string",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "confidence": "number[0,1]",
                    "knowledge_state": "string?",
                    "claim_type": "string?",
                    "scope_key": "string?",
                    "tags": "array[string]?",
                },
            ),
            self._commit_ai_world_claim,
        )
        registry.register(
            CapabilitySpec(
                name="revise_claim",
                description=(
                    "Create a forward-only new revision of the current Claim and mark "
                    "dependent cognition review-required."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "target_ref": "{object_id:string,revision:integer}",
                    "reason": "string",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "replacement_content": "string",
                    "confidence": "number[0,1]?",
                },
            ),
            self._revise_claim,
        )
        registry.register(
            CapabilitySpec(
                name="retract_claim",
                description=(
                    "Retract the current Claim using pinned contrary/correcting evidence "
                    "and propagate review-required state to dependents."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "target_ref": "{object_id:string,revision:integer}",
                    "reason": "string",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                },
            ),
            self._retract_claim,
        )
        self.registry = registry
        self.cognitive_runtime = CognitiveRuntime(
            registry=registry,
            model_handler=model_handler,
            max_tool_rounds=max_tool_rounds,
            side_effect_authorizer=self._authorize_side_effect,
        )

    def _search_world(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        page = self.index.recall_candidates(
            str(query),
            subject=self.subject_id,
            limit=max(1, min(int(limit), 50)),
        )
        return [
            {
                "object_id": hit.object_id,
                "revision": hit.revision,
                "object_type": hit.object_type,
                "dimension": hit.dimension,
                "excerpt": hit.excerpt,
                "retrieval_score": hit.score,
            }
            for hit in page.hits
        ]

    def _inspect_world_object(
        self,
        object_id: str,
        revision: int | None = None,
    ) -> dict[str, Any]:
        return self.store.get_payload(str(object_id), revision=revision)

    def _read_ai_world(
        self,
        domains: Sequence[str] | None = None,
        scope_key: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        parsed = (
            None
            if domains is None
            else [AIWorldDomain(str(domain)) for domain in domains]
        )
        return [
            item.model_dump(mode="json")
            for item in self.ai_world.current(
                domains=parsed,
                scope_key=scope_key,
                limit=max(1, min(int(limit), 200)),
            )
        ]

    def _request_all_dimensions_projection(
        self,
        dimensions: Sequence[str],
        window_start: str,
        window_end: str,
        query: str | None = None,
    ) -> dict[str, Any]:
        start = datetime.fromisoformat(str(window_start).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(window_end).replace("Z", "+00:00"))
        projection = self.all_dimensions.project(
            dimensions=dimensions,
            window_start=start,
            window_end=end,
            query=query,
        )
        return projection.model_dump(mode="json")

    def _authorize_side_effect(self, spec, call, snapshot) -> bool:
        # Internal cognition writeback is allowed because the handler itself enforces
        # pinned evidence and writes only revisable cognition. External actions stay
        # denied until a separate capability-specific authorization layer exists.
        return spec.name in {
            "commit_claim",
            "commit_ai_world_claim",
            "revise_claim",
            "retract_claim",
        }

    def _commit_ai_world_claim(
        self,
        domain: str,
        statement: str,
        evidence_refs: Sequence[Mapping[str, Any]],
        confidence: float,
        knowledge_state: str = "inferred",
        claim_type: str = "inference",
        scope_key: str | None = None,
        tags: Sequence[str] = (),
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError(
                "commit_ai_world_claim is only available during an active AIOS turn"
            )
        receipt = self.ai_world.commit(
            AIWorldClaimRequest(
                domain=AIWorldDomain(domain),
                statement=statement,
                evidence_refs=self._coerce_refs(evidence_refs),
                confidence=float(confidence),
                knowledge_state=knowledge_state,
                claim_type=claim_type,
                scope_key=scope_key,
                tags=tuple(tags),
            ),
            learned_at=self._active_turn_time,
        )
        return {
            "domain": receipt.domain.value,
            "dimension": receipt.dimension,
            "subject_id": receipt.subject_id,
            "claim": asdict(receipt.claim),
        }

    def _commit_claim(
        self,
        content: str,
        evidence_refs: Sequence[Mapping[str, Any]],
        confidence: float,
        dimension: str,
        claim_type: str = "inference",
        knowledge_state: str = "inferred",
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("commit_claim is only available during an active AIOS turn")
        refs = tuple(
            ObjectRef(
                object_id=str(item["object_id"]),
                revision=int(item["revision"]),
            )
            for item in evidence_refs
        )
        receipt = self.writeback.commit_claim(
            ClaimWriteRequest(
                content=content,
                evidence_refs=refs,
                confidence=float(confidence),
                dimension=dimension,
                claim_type=claim_type,
                knowledge_state=knowledge_state,
            ),
            learned_at=self._active_turn_time,
        )
        return asdict(receipt)

    def _coerce_refs(
        self,
        refs: Sequence[Mapping[str, Any]],
    ) -> tuple[ObjectRef, ...]:
        return tuple(
            ObjectRef(
                object_id=str(item["object_id"]),
                revision=int(item["revision"]),
            )
            for item in refs
        )

    def _revise_claim(
        self,
        target_ref: Mapping[str, Any],
        reason: str,
        evidence_refs: Sequence[Mapping[str, Any]],
        replacement_content: str,
        confidence: float | None = None,
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("revise_claim is only available during an active AIOS turn")
        receipt = self.revision.apply(
            ClaimRevisionRequest(
                target_ref=ObjectRef(
                    object_id=str(target_ref["object_id"]),
                    revision=int(target_ref["revision"]),
                ),
                mode="revise",
                reason=reason,
                evidence_refs=self._coerce_refs(evidence_refs),
                replacement_content=replacement_content,
                confidence=confidence,
            ),
            changed_at=self._active_turn_time,
        )
        return asdict(receipt)

    def _retract_claim(
        self,
        target_ref: Mapping[str, Any],
        reason: str,
        evidence_refs: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("retract_claim is only available during an active AIOS turn")
        receipt = self.revision.apply(
            ClaimRevisionRequest(
                target_ref=ObjectRef(
                    object_id=str(target_ref["object_id"]),
                    revision=int(target_ref["revision"]),
                ),
                mode="retract",
                reason=reason,
                evidence_refs=self._coerce_refs(evidence_refs),
            ),
            changed_at=self._active_turn_time,
        )
        return asdict(receipt)

    def run_turn(
        self,
        *,
        session_id: str,
        turn_index: int,
        user_input: str,
        current_topic: str | None,
        occurred_at: datetime,
        recent_turns: Sequence[Mapping[str, Any]] = (),
        ai_identity: Mapping[str, Any] | None = None,
        task_context: Mapping[str, Any] | None = None,
        token_budget: int | None = None,
    ) -> FusedTurnResult:
        recommendation = self.recommender.recommend(
            current_topic=current_topic,
            subject_id=self.subject_id,
            exclude_session_id=session_id,
        )

        continuity_context = (
            dict(ai_identity)
            if ai_identity is not None
            else self.ai_world.core_context(per_domain=3)
        )

        context = self.context_controller.assemble(
            user_input=user_input,
            current_topic=current_topic,
            recommendation=recommendation,
            recent_turns=recent_turns,
            ai_identity=continuity_context,
            task_context=task_context,
            capability_catalog=self.registry.catalog(),
            token_budget=token_budget,
        )

        self._active_turn_time = occurred_at
        try:
            runtime_result = self.cognitive_runtime.run_turn(
                user_input,
                wake_reason="user_interaction",
                cockpit=context.as_cockpit(),
            )
        finally:
            self._active_turn_time = None

        assistant_text = runtime_result.response or ""
        commit = self.ingestor.commit_turn(
            session_id=session_id,
            turn_index=turn_index,
            user_text=user_input,
            assistant_text=assistant_text,
            occurred_at=occurred_at,
        )
        # Keep the public search projection current for the next turn.
        self.index.catch_up()

        return FusedTurnResult(
            runtime=runtime_result,
            recommendation=recommendation,
            context=context,
            conversation_commit=commit,
        )
