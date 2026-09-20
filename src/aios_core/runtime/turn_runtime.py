"""First runnable fused AIOS v3.0 turn loop.

This module connects proactive recommendation, context assembly, model-driven
capabilities and unified-world conversation writeback. It is intentionally small:
advanced summaries, AI-self writeback and policy learning are layered on after this
vertical slice stays green.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable, Mapping, Sequence

from aios_core.ai_world import (
    AIWorldClaimRequest,
    AIWorldCognitionService,
    AIWorldDomain,
)
from aios_core.context.continuity import (
    ConversationContinuityService,
    RoundSummaryCommit,
    RoundSummaryRequest,
)
from aios_core.context.controller import ContextController, ModelContextBundle
from aios_core.dimensions import (
    DimensionProposalRequest,
    DimensionRegistryService,
    DimensionTransitionRequest,
)
from aios_core.execution import (
    ActionProposalRequest,
    GoalCreateRequest,
    GoalTaskActionService,
    GoalTransitionRequest,
    TaskCreateRequest,
    TaskTransitionRequest,
)
from aios_core.ingest.conversation import ConversationCommit, ConversationIngestor
from aios_core.projections.all_dimensions import AllDimensionsProjectionService
from aios_core.query.search import WorldSearchIndex
from aios_core.recommendation.proactive import (
    ProactiveMemoryRecommender,
    RecommendationBundle,
)
from aios_core.revision.service import ClaimRevisionRequest, CognitionRevisionService
from aios_core.review import (
    OperationExperienceRequest,
    PeriodicReviewRequest,
    PeriodicReviewService,
    ReviewSchedulePolicy,
    ReviewWakeReceipt,
)
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService
from aios_core.wake import (
    GENERIC_RESIDENT_WAKE_SOURCES,
    WakeDispatchReceipt,
    WakeDispatchRequest,
    WakeDispatchService,
    WakeStep0Gate,
)
from aios_core.contracts.refs import ObjectRef

from .capabilities import CapabilityKind, CapabilityRegistry, CapabilitySpec
from .cognitive_runtime import CognitiveRuntime, ModelHandler, RuntimeTurnResult


@dataclass(frozen=True, slots=True)
class FusedTurnResult:
    runtime: RuntimeTurnResult
    recommendation: RecommendationBundle
    context: ModelContextBundle
    conversation_commit: ConversationCommit
    continuity_summary_commits: tuple[RoundSummaryCommit, ...] = ()
    continuity_summary_error: str | None = None


@dataclass(frozen=True, slots=True)
class PeriodicReviewRunResult:
    request: PeriodicReviewRequest
    runtime: RuntimeTurnResult
    context: ModelContextBundle
    wake: ReviewWakeReceipt


@dataclass(frozen=True, slots=True)
class WakeRunResult:
    request: WakeDispatchRequest
    runtime: RuntimeTurnResult
    context: ModelContextBundle
    wake: WakeDispatchReceipt
    delivery_allowed: bool


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
        round_summary_handler: Callable[[RoundSummaryRequest], str] | None = None,
        recent_turn_limit: int = 8,
        summary_chunk_turns: int = 12,
        max_round_summaries_per_turn: int = 1,
    ) -> None:
        if recent_turn_limit < 0:
            raise ValueError("recent_turn_limit must be >= 0")
        if summary_chunk_turns < 1:
            raise ValueError("summary_chunk_turns must be >= 1")
        if max_round_summaries_per_turn < 0:
            raise ValueError("max_round_summaries_per_turn must be >= 0")
        self.store = store
        self.index = index
        self.subject_id = subject_id.strip()
        self.ingestor = ConversationIngestor(store, subject_id=self.subject_id)
        self.continuity = ConversationContinuityService(
            store=store,
            index=index,
            subject_id=self.subject_id,
        )
        self.round_summary_handler = round_summary_handler
        self.recent_turn_limit = int(recent_turn_limit)
        self.summary_chunk_turns = int(summary_chunk_turns)
        self.max_round_summaries_per_turn = int(max_round_summaries_per_turn)
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
        self.dimensions = DimensionRegistryService(
            store=store,
            index=index,
            subject_id=subject_id,
        )
        self.execution_world = GoalTaskActionService(
            store=store,
            index=index,
            subject_id=subject_id,
        )
        self.periodic_review = PeriodicReviewService(
            store=store,
            index=index,
            subject_id=self.subject_id,
        )
        self.wake_dispatch = WakeDispatchService(
            store=store,
            index=index,
            subject_id=self.subject_id,
        )
        self._active_turn_time: datetime | None = None
        self._active_session_id: str | None = None
        self._active_review_request: PeriodicReviewRequest | None = None

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
                name="read_periodic_review_anchors",
                description=(
                    "Read a bounded page of the evidence anchors selected for the "
                    "currently active periodic review. Available only during review."
                ),
                kind=CapabilityKind.READ,
                input_schema={
                    "offset": "integer?",
                    "limit": "integer?",
                },
            ),
            self._read_periodic_review_anchors,
        )
        registry.register(
            CapabilitySpec(
                name="list_conversation_summaries",
                description=(
                    "List same-session continuity summary windows on demand. Use this "
                    "when token budgeting omitted summary content from the cockpit."
                ),
                kind=CapabilityKind.READ,
                input_schema={
                    "session_id": "string?",
                    "limit": "integer?",
                },
            ),
            self._list_conversation_summaries,
        )
        registry.register(
            CapabilitySpec(
                name="drill_down_conversation",
                description=(
                    "Read exact pinned raw dialogue behind a same-session round summary, "
                    "or an explicit turn range. Round summaries are indexes, not truth."
                ),
                kind=CapabilityKind.READ,
                input_schema={
                    "summary_id": "string?",
                    "revision": "integer?",
                    "session_id": "string?",
                    "turn_start": "integer?",
                    "turn_end": "integer?",
                },
            ),
            self._drill_down_conversation,
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
                name="list_dimensions",
                description=(
                    "List current registered dimension definitions so the resident AI "
                    "can check whether an existing observation axis already serves the need."
                ),
                kind=CapabilityKind.READ,
                input_schema={"include_terminal": "boolean?"},
            ),
            self._list_dimensions,
        )
        registry.register(
            CapabilitySpec(
                name="read_execution_world",
                description=(
                    "Read current Goals, Tasks and proposed/executed Actions from the "
                    "unified world. This is a read-only planning view."
                ),
                kind=CapabilityKind.READ,
                input_schema={},
            ),
            self._read_execution_world,
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
                name="propose_dimension",
                description=(
                    "Submit an evidence-grounded candidate observation axis. "
                    "The system validates structure; the model supplies semantic rationale."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "dimension_key": "string starting dim:",
                    "name": "string",
                    "description": "string",
                    "data_shape": "string",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "why_existing_dimensions_are_insufficient": "string",
                    "continuity_rationale": "string",
                    "user_value_rationale": "string",
                    "maintenance_cost_rationale": "string",
                    "confidence": "number[0,1]",
                    "update_method": "string?",
                    "expected_value": "string?",
                },
            ),
            self._propose_dimension,
        )
        registry.register(
            CapabilitySpec(
                name="transition_dimension",
                description=(
                    "Move the current dimension revision through a legal lifecycle "
                    "transition using pinned evidence and an AI-supplied reason."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "dimension_ref": "{object_id:string,revision:integer}",
                    "new_lifecycle": "candidate|trial|active|low_activity|dormant|merged|split|revised|rejected|reactivated|archived",
                    "reason": "string",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "related_dimension_refs": "array[{object_id:string,revision:integer}]?",
                },
            ),
            self._transition_dimension,
        )
        registry.register(
            CapabilitySpec(
                name="propose_goal",
                description=(
                    "Create an evidence-grounded Goal proposal in the unified world. "
                    "A proposal does not grant external-action authorization."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "source_type": "user_explicit|user_inferred|ai_self|app|external",
                    "title": "string",
                    "description": "string",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "confidence": "number[0,1]",
                    "success_criteria": "array[string]?",
                },
            ),
            self._propose_goal,
        )
        registry.register(
            CapabilitySpec(
                name="transition_goal",
                description=(
                    "Move the current Goal revision through a legal evidence-backed state transition."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "goal_ref": "{object_id:string,revision:integer}",
                    "new_status": "proposed|active|paused|achieved|abandoned|unknown",
                    "reason": "string",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                },
            ),
            self._transition_goal,
        )
        registry.register(
            CapabilitySpec(
                name="create_task",
                description=(
                    "Create a concrete evidence-grounded Task, optionally under a current Goal."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "title": "string",
                    "task_type": "string",
                    "reason_refs": "array[{object_id:string,revision:integer}]",
                    "goal_ref": "{object_id:string,revision:integer}?",
                    "initial_state": "string?",
                    "priority": "integer?",
                    "next_wake_at": "ISO-8601 datetime?",
                    "deadline": "ISO-8601 datetime?",
                    "timezone_name": "string?",
                    "next_step": "string?",
                },
            ),
            self._create_task,
        )
        registry.register(
            CapabilitySpec(
                name="transition_task",
                description=(
                    "Move the current Task revision through a legal state transition. "
                    "COMPLETED/FAILED requires real Outcome refs."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "task_ref": "{object_id:string,revision:integer}",
                    "new_state": "string",
                    "reason": "string",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "execution_refs": "array[{object_id:string,revision:integer}]?",
                    "outcome_refs": "array[{object_id:string,revision:integer}]?",
                    "next_wake_at": "ISO-8601 datetime?",
                    "next_step": "string?",
                },
            ),
            self._transition_task,
        )
        registry.register(
            CapabilitySpec(
                name="propose_action",
                description=(
                    "Create a PROPOSED external Action for a RUNNING Task. "
                    "This capability never executes the side effect and cannot authorize itself."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "task_ref": "{object_id:string,revision:integer}",
                    "action_type": "string",
                    "payload": "object",
                    "expected_outcome": "string?",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                },
            ),
            self._propose_action,
        )
        registry.register(
            CapabilitySpec(
                name="commit_operation_experience",
                description=(
                    "During an active periodic review, persist a model-authored "
                    "operation experience grounded in pinned real case refs."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "problem_type": "string",
                    "method_path": "array[string]",
                    "result_summary": "string",
                    "positive_case_refs": "array[{object_id:string,revision:integer}]?",
                    "negative_case_refs": "array[{object_id:string,revision:integer}]?",
                    "applicability": "object?",
                    "cost": "object[number]?",
                    "misses": "array[string]?",
                    "experience_state": "string?",
                },
            ),
            self._commit_operation_experience,
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

    def _read_periodic_review_anchors(
        self,
        offset: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        request = self._active_review_request
        if request is None:
            raise RuntimeError(
                "read_periodic_review_anchors is only available during periodic review"
            )
        start = max(0, int(offset))
        take = max(1, min(int(limit), 50))
        return [
            anchor.model_dump(mode="json")
            for anchor in request.anchors[start : start + take]
        ]

    def _list_conversation_summaries(
        self,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        active_session = (
            str(session_id).strip()
            if session_id is not None and str(session_id).strip()
            else self._active_session_id
        )
        if active_session is None:
            raise ValueError(
                "session_id is required outside an active turn"
            )
        bounded = max(1, min(int(limit), 200))
        summaries = self.continuity.round_summaries(
            session_id=active_session,
        )
        return [dict(item) for item in summaries[-bounded:]]

    def _drill_down_conversation(
        self,
        summary_id: str | None = None,
        revision: int | None = None,
        session_id: str | None = None,
        turn_start: int | None = None,
        turn_end: int | None = None,
    ) -> list[dict[str, Any]]:
        if summary_id is not None:
            return [
                dict(item)
                for item in self.continuity.drill_down_summary(
                    str(summary_id),
                    revision=(None if revision is None else int(revision)),
                )
            ]

        active_session = (
            str(session_id).strip()
            if session_id is not None and str(session_id).strip()
            else self._active_session_id
        )
        if active_session is None:
            raise ValueError(
                "session_id is required outside an active turn when summary_id is absent"
            )
        if turn_start is None or turn_end is None:
            raise ValueError(
                "turn_start and turn_end are required when summary_id is absent"
            )
        return [
            dict(item)
            for item in self.continuity.drill_down_range(
                session_id=active_session,
                turn_start=int(turn_start),
                turn_end=int(turn_end),
            )
        ]

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
    def _list_dimensions(
        self,
        include_terminal: bool = False,
    ) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in self.dimensions.current_dimensions(
                include_terminal=bool(include_terminal)
            )
        ]

    def _read_execution_world(self) -> dict[str, Any]:
        return {
            "goals": [
                item.model_dump(mode="json")
                for item in self.execution_world.current_goals()
            ],
            "tasks": [
                item.model_dump(mode="json")
                for item in self.execution_world.current_tasks()
            ],
            "actions": [
                item.model_dump(mode="json")
                for item in self.execution_world.current_actions()
            ],
        }

    @staticmethod
    def _optional_datetime(value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    def _propose_goal(
        self,
        source_type: str,
        title: str,
        description: str,
        evidence_refs: Sequence[Mapping[str, Any]],
        confidence: float,
        success_criteria: Sequence[str] = (),
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("propose_goal is only available during an active AIOS turn")
        receipt = self.execution_world.create_goal(
            GoalCreateRequest(
                source_type=source_type,
                title=title,
                description=description,
                evidence_refs=self._coerce_refs(evidence_refs),
                confidence=float(confidence),
                success_criteria=tuple(success_criteria),
            ),
            created_at=self._active_turn_time,
        )
        return asdict(receipt)

    def _transition_goal(
        self,
        goal_ref: Mapping[str, Any],
        new_status: str,
        reason: str,
        evidence_refs: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("transition_goal is only available during an active AIOS turn")
        receipt = self.execution_world.transition_goal(
            GoalTransitionRequest(
                goal_ref=ObjectRef(
                    object_id=str(goal_ref["object_id"]),
                    revision=int(goal_ref["revision"]),
                ),
                new_status=new_status,
                reason=reason,
                evidence_refs=self._coerce_refs(evidence_refs),
            ),
            changed_at=self._active_turn_time,
        )
        return asdict(receipt)

    def _create_task(
        self,
        title: str,
        task_type: str,
        reason_refs: Sequence[Mapping[str, Any]],
        goal_ref: Mapping[str, Any] | None = None,
        initial_state: str = "draft",
        priority: int = 50,
        next_wake_at: str | None = None,
        deadline: str | None = None,
        timezone_name: str | None = None,
        next_step: str | None = None,
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("create_task is only available during an active AIOS turn")
        parsed_goal = (
            None
            if goal_ref is None
            else ObjectRef(
                object_id=str(goal_ref["object_id"]),
                revision=int(goal_ref["revision"]),
            )
        )
        receipt = self.execution_world.create_task(
            TaskCreateRequest(
                title=title,
                task_type=task_type,
                reason_refs=self._coerce_refs(reason_refs),
                goal_ref=parsed_goal,
                initial_state=initial_state,
                priority=int(priority),
                next_wake_at=self._optional_datetime(next_wake_at),
                deadline=self._optional_datetime(deadline),
                timezone_name=timezone_name,
                next_step=next_step,
            ),
            created_at=self._active_turn_time,
        )
        return asdict(receipt)

    def _transition_task(
        self,
        task_ref: Mapping[str, Any],
        new_state: str,
        reason: str,
        evidence_refs: Sequence[Mapping[str, Any]],
        execution_refs: Sequence[Mapping[str, Any]] = (),
        outcome_refs: Sequence[Mapping[str, Any]] = (),
        next_wake_at: str | None = None,
        next_step: str | None = None,
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("transition_task is only available during an active AIOS turn")
        receipt = self.execution_world.transition_task(
            TaskTransitionRequest(
                task_ref=ObjectRef(
                    object_id=str(task_ref["object_id"]),
                    revision=int(task_ref["revision"]),
                ),
                new_state=new_state,
                reason=reason,
                evidence_refs=self._coerce_refs(evidence_refs),
                execution_refs=self._coerce_refs(execution_refs),
                outcome_refs=self._coerce_refs(outcome_refs),
                next_wake_at=self._optional_datetime(next_wake_at),
                next_step=next_step,
            ),
            changed_at=self._active_turn_time,
        )
        return asdict(receipt)

    def _propose_action(
        self,
        task_ref: Mapping[str, Any],
        action_type: str,
        payload: Mapping[str, Any],
        evidence_refs: Sequence[Mapping[str, Any]],
        expected_outcome: str | None = None,
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("propose_action is only available during an active AIOS turn")
        receipt = self.execution_world.propose_action(
            ActionProposalRequest(
                task_ref=ObjectRef(
                    object_id=str(task_ref["object_id"]),
                    revision=int(task_ref["revision"]),
                ),
                action_type=action_type,
                payload=dict(payload),
                expected_outcome=expected_outcome,
                evidence_refs=self._coerce_refs(evidence_refs),
            ),
            proposed_at=self._active_turn_time,
        )
        return asdict(receipt)


    def _propose_dimension(
        self,
        dimension_key: str,
        name: str,
        description: str,
        data_shape: str,
        evidence_refs: Sequence[Mapping[str, Any]],
        why_existing_dimensions_are_insufficient: str,
        continuity_rationale: str,
        user_value_rationale: str,
        maintenance_cost_rationale: str,
        confidence: float,
        update_method: str | None = None,
        expected_value: str | None = None,
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("propose_dimension is only available during an active AIOS turn")
        receipt = self.dimensions.propose(
            DimensionProposalRequest(
                dimension_key=dimension_key,
                name=name,
                description=description,
                data_shape=data_shape,
                evidence_refs=self._coerce_refs(evidence_refs),
                why_existing_dimensions_are_insufficient=why_existing_dimensions_are_insufficient,
                continuity_rationale=continuity_rationale,
                user_value_rationale=user_value_rationale,
                maintenance_cost_rationale=maintenance_cost_rationale,
                confidence=float(confidence),
                update_method=update_method,
                expected_value=expected_value,
            ),
            proposed_at=self._active_turn_time,
        )
        return asdict(receipt)

    def _transition_dimension(
        self,
        dimension_ref: Mapping[str, Any],
        new_lifecycle: str,
        reason: str,
        evidence_refs: Sequence[Mapping[str, Any]],
        related_dimension_refs: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError(
                "transition_dimension is only available during an active AIOS turn"
            )
        receipt = self.dimensions.transition(
            DimensionTransitionRequest(
                dimension_ref=ObjectRef(
                    object_id=str(dimension_ref["object_id"]),
                    revision=int(dimension_ref["revision"]),
                ),
                new_lifecycle=new_lifecycle,
                reason=reason,
                evidence_refs=self._coerce_refs(evidence_refs),
                related_dimension_refs=self._coerce_refs(related_dimension_refs),
            ),
            changed_at=self._active_turn_time,
        )
        return asdict(receipt)


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
            "propose_dimension",
            "transition_dimension",
            "propose_goal",
            "transition_goal",
            "create_task",
            "transition_task",
            "propose_action",
            "commit_operation_experience",
            "revise_claim",
            "retract_claim",
        }

    def _commit_operation_experience(
        self,
        problem_type: str,
        method_path: Sequence[str],
        result_summary: str,
        positive_case_refs: Sequence[Mapping[str, Any]] = (),
        negative_case_refs: Sequence[Mapping[str, Any]] = (),
        applicability: Mapping[str, Any] | None = None,
        cost: Mapping[str, float] | None = None,
        misses: Sequence[str] = (),
        experience_state: str = "candidate",
    ) -> dict[str, Any]:
        if self._active_turn_time is None or self._active_review_request is None:
            raise RuntimeError(
                "commit_operation_experience is only available during active periodic review"
            )
        receipt = self.periodic_review.commit_operation_experience(
            OperationExperienceRequest(
                problem_type=problem_type,
                method_path=tuple(method_path),
                result_summary=result_summary,
                positive_case_refs=self._coerce_refs(positive_case_refs),
                negative_case_refs=self._coerce_refs(negative_case_refs),
                applicability=dict(applicability or {}),
                cost=dict(cost or {}),
                misses=tuple(misses),
                experience_state=experience_state,
            ),
            learned_at=self._active_turn_time,
        )
        return asdict(receipt)

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
        session = session_id.strip()
        if not session:
            raise ValueError("session_id must not be blank")
        if recent_turns:
            raise ValueError(
                "P14 derives recent_turns from WorldStore; callers must not inject "
                "an externally maintained conversation history"
            )

        # The current user utterance enters the world before model inference. The
        # continuity view deliberately excludes this incomplete current turn and
        # rebuilds prior dialogue from canonical observations.
        user_commit = self.ingestor.commit_user_input(
            session_id=session,
            turn_index=turn_index,
            user_text=user_input,
            occurred_at=occurred_at,
        )
        self.index.catch_up()

        continuity_snapshot = self.continuity.snapshot(
            session_id=session,
            before_turn=turn_index,
            recent_turn_limit=self.recent_turn_limit,
            summary_chunk_turns=self.summary_chunk_turns,
        )

        recommendation = self.recommender.recommend(
            current_topic=current_topic,
            subject_id=self.subject_id,
            exclude_session_id=session,
        )

        continuity_context = (
            dict(ai_identity)
            if ai_identity is not None
            else self.ai_world.core_context(per_domain=3)
        )

        current_task_context = dict(task_context or {})
        current_task_context["current_user_observation_ref"] = {
            "object_id": user_commit.observation_id,
            "revision": 1,
        }
        current_task_context["conversation_continuity"] = {
            "session_id": session,
            "recent_turn_count": len(continuity_snapshot.recent_turns),
            "round_summary_count": len(continuity_snapshot.round_summaries),
            "summary_index_capability": "list_conversation_summaries",
            "raw_drill_down_capability": "drill_down_conversation",
            "pending_round_summary": (
                None
                if continuity_snapshot.pending_summary is None
                else {
                    "turn_start": continuity_snapshot.pending_summary.turn_start,
                    "turn_end": continuity_snapshot.pending_summary.turn_end,
                    "source_count": len(
                        continuity_snapshot.pending_summary.sources
                    ),
                }
            ),
        }

        context = self.context_controller.assemble(
            user_input=user_input,
            current_topic=current_topic,
            recommendation=recommendation,
            recent_turns=continuity_snapshot.recent_turns,
            conversation_summaries=continuity_snapshot.round_summaries,
            ai_identity=continuity_context,
            task_context=current_task_context,
            capability_catalog=self.registry.catalog(),
            token_budget=token_budget,
        )

        self._active_turn_time = occurred_at
        self._active_session_id = session
        try:
            runtime_result = self.cognitive_runtime.run_turn(
                user_input,
                wake_reason="user_interaction",
                cockpit=context.as_cockpit(),
            )
        finally:
            self._active_turn_time = None
            self._active_session_id = None

        assistant_text = runtime_result.response or ""
        assistant_commit = self.ingestor.commit_assistant_output(
            session_id=session,
            turn_index=turn_index,
            assistant_text=assistant_text,
            occurred_at=occurred_at,
        )
        commit = ConversationCommit(
            world_revision=assistant_commit.world_revision,
            user_observation_id=user_commit.observation_id,
            assistant_observation_id=assistant_commit.observation_id,
            idempotent_replay=(
                user_commit.idempotent_replay
                and assistant_commit.idempotent_replay
            ),
            user_world_revision=user_commit.world_revision,
            assistant_world_revision=assistant_commit.world_revision,
        )
        self.index.catch_up()

        # Summarization is maintenance after the user-visible turn. Deterministic
        # code decides when a closed range needs summarization; an injected real
        # model handler supplies only the descriptive text. Failure never rewrites
        # or deletes raw dialogue, and is surfaced to the caller for audit/repair.
        summary_commits: list[RoundSummaryCommit] = []
        summary_error: str | None = None
        if (
            self.round_summary_handler is not None
            and self.max_round_summaries_per_turn > 0
        ):
            try:
                for _ in range(self.max_round_summaries_per_turn):
                    request = self.continuity.prepare_next_round_summary(
                        session_id=session,
                        before_turn=turn_index + 1,
                        recent_turn_limit=self.recent_turn_limit,
                        summary_chunk_turns=self.summary_chunk_turns,
                    )
                    if request is None:
                        break
                    content = self.round_summary_handler(request)
                    summary_commits.append(
                        self.continuity.commit_round_summary(
                            request,
                            content=content,
                            generated_at=occurred_at,
                        )
                    )
            except Exception as exc:
                summary_error = f"{type(exc).__name__}: {exc}"

        self.index.catch_up()
        return FusedTurnResult(
            runtime=runtime_result,
            recommendation=recommendation,
            context=context,
            conversation_commit=commit,
            continuity_summary_commits=tuple(summary_commits),
            continuity_summary_error=summary_error,
        )



    def run_wake(
        self,
        *,
        wake_ref: ObjectRef,
        now: datetime,
        step0_gate: WakeStep0Gate,
        token_budget: int | None = None,
    ) -> WakeRunResult:
        """Dispatch one ordinary durable Wake through the same resident runtime.

        This is the C09/R5 bridge from a durable Wake to the resident model. It does
        not create a synthetic Conversation Observation and it does not encode a
        cognitive conclusion. Specialized USER_INTERACTION, PERIODIC_REVIEW and
        SAFETY paths are intentionally rejected here.
        """
        pinned = self.wake_dispatch.resolve(wake_ref)
        if pinned.wake_source not in GENERIC_RESIDENT_WAKE_SOURCES:
            raise ValueError(
                f"wake source {pinned.wake_source.value!r} requires its specialized "
                "runtime path"
            )

        request = self.wake_dispatch.claim(
            wake_ref,
            started_at=now,
            step0_gate=step0_gate,
        )
        self.index.catch_up()

        trigger_hints: list[dict[str, Any]] = []
        for ref in request.evidence_refs:
            pinned_payload = self.store.get_payload(
                ref.object_id,
                revision=ref.revision,
            )
            latest_payload = self.store.get_payload(ref.object_id)
            hint_keys = (
                "object_id",
                "revision",
                "object_type",
                "status",
                "title",
                "task_state",
                "goal_status",
                "action_status",
                "next_step",
            )
            trigger_hints.append(
                {
                    "trigger_ref": ref.model_dump(mode="json"),
                    "trigger_revision": {
                        key: pinned_payload.get(key)
                        for key in hint_keys
                        if key in pinned_payload
                    },
                    "current_ref": {
                        "object_id": str(latest_payload["object_id"]),
                        "revision": int(latest_payload["revision"]),
                    },
                    "current_state": {
                        key: latest_payload.get(key)
                        for key in hint_keys
                        if key in latest_payload
                    },
                }
            )

        empty_recommendation = RecommendationBundle(
            current_topic=None,
            topic_gate_open=False,
            world_revision=int(self.store.current_world_revision()),
            index_watermark=self.index.watermark(),
            cards=(),
            reason="durable_wake_uses_trigger_refs_not_proactive_topic_injection",
        )
        wake_context = {
            "wake_ref": request.wake_ref.model_dump(mode="json"),
            "wake_source": request.wake_source.value,
            "rule_id": request.rule_id,
            "priority": request.priority,
            "evidence_refs": [
                ref.model_dump(mode="json") for ref in request.evidence_refs
            ],
            "trigger_hints": trigger_hints,
            "step0": request.step0.as_dict(),
            "instruction": (
                "Orient around this Wake Reason first. Inspect or search the world "
                "when needed, then independently decide whether to act, respond, "
                "write cognition, reschedule work, or remain silent. Trigger data "
                "is evidence, not a semantic conclusion."
            ),
        }
        wake_input = (
            f"Durable wake: {request.wake_source.value}. "
            "Inspect the trigger and decide what, if anything, should happen now."
        )
        context = self.context_controller.assemble(
            user_input=wake_input,
            current_topic=None,
            recommendation=empty_recommendation,
            recent_turns=(),
            conversation_summaries=(),
            ai_identity=self.ai_world.core_context(per_domain=3),
            task_context={"wake": wake_context},
            capability_catalog=self.registry.catalog(),
            token_budget=token_budget,
        )

        self._active_turn_time = now
        self._active_session_id = None
        try:
            runtime_result = self.cognitive_runtime.run_turn(
                wake_input,
                wake_reason=request.wake_source.value,
                cockpit=context.as_cockpit(),
            )
        finally:
            self._active_turn_time = None
            self._active_session_id = None

        wake = self.wake_dispatch.complete(
            request,
            completed_at=now,
            termination_reason=runtime_result.termination_reason,
            model_rounds=runtime_result.model_rounds,
            capability_names=tuple(
                result.name for result in runtime_result.capability_history
            ),
        )
        self.index.catch_up()
        return WakeRunResult(
            request=request,
            runtime=runtime_result,
            context=context,
            wake=wake,
            delivery_allowed=request.step0.delivery_allowed,
        )


    def run_periodic_review(
        self,
        *,
        now: datetime,
        policy: ReviewSchedulePolicy | None = None,
        token_budget: int | None = None,
    ) -> PeriodicReviewRunResult | None:
        """Run one due evidence-grounded background review through the resident model.

        This path does not create a synthetic Conversation Observation. The Wake and
        any cognition/experience written by model capabilities are the durable audit.
        """
        request = self.periodic_review.prepare_due_review(
            now=now,
            policy=policy,
        )
        if request is None:
            return None

        request = self.periodic_review.begin_review(
            request,
            started_at=now,
        )
        self.index.catch_up()

        empty_recommendation = RecommendationBundle(
            current_topic=None,
            topic_gate_open=False,
            world_revision=int(self.store.current_world_revision()),
            index_watermark=self.index.watermark(),
            cards=(),
            reason="periodic_review_does_not_use_proactive_memory_injection",
        )
        continuity_context = self.ai_world.core_context(per_domain=3)
        review_context = {
            "review_id": request.review_id,
            "wake_ref": request.wake_ref.model_dump(mode="json"),
            "window_start": request.window_start.isoformat(),
            "window_end": request.window_end.isoformat(),
            "anchor_count": len(request.anchors),
            "anchor_reader": "read_periodic_review_anchors",
            "instruction": request.instruction,
        }
        review_input = (
            "Periodic review wake. Inspect the selected world anchors, then decide "
            "whether any evidence-grounded cognition or operation experience should "
            "be revised, created, or left unchanged."
        )
        context = self.context_controller.assemble(
            user_input=review_input,
            current_topic=None,
            recommendation=empty_recommendation,
            recent_turns=(),
            conversation_summaries=(),
            ai_identity=continuity_context,
            task_context={"periodic_review": review_context},
            capability_catalog=self.registry.catalog(),
            token_budget=token_budget,
        )

        self._active_turn_time = now
        self._active_session_id = None
        self._active_review_request = request
        try:
            runtime_result = self.cognitive_runtime.run_turn(
                review_input,
                wake_reason="periodic_review",
                cockpit=context.as_cockpit(),
            )
        finally:
            self._active_review_request = None
            self._active_turn_time = None
            self._active_session_id = None

        wake = self.periodic_review.complete_review(
            request,
            completed_at=now,
            termination_reason=runtime_result.termination_reason,
            model_rounds=runtime_result.model_rounds,
            capability_names=[
                result.name for result in runtime_result.capability_history
            ],
        )
        self.index.catch_up()
        return PeriodicReviewRunResult(
            request=request,
            runtime=runtime_result,
            context=context,
            wake=wake,
        )
