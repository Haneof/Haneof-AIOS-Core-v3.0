"""First runnable fused AIOS v3.0 turn loop.

This module connects proactive recommendation, context assembly, model-driven
capabilities and unified-world conversation writeback. It is intentionally small:
advanced summaries, AI-self writeback and policy learning are layered on after this
vertical slice stays green.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
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
from aios_core.communication import CommunicationExperienceRequest, CommunicationExperienceService
from aios_core.dimensions import (
    DimensionProposalRequest,
    DimensionRegistryService,
    DimensionTransitionRequest,
)
from aios_core.events import EventDimensionService, EventTransitionRequest, EventWriteRequest
from aios_core.execution import (
    ActionProposalRequest,
    GoalCreateRequest,
    GoalTaskActionService,
    GoalTransitionRequest,
    TaskCreateRequest,
    TaskTransitionRequest,
)
from aios_core.ingest import RealityIngestService
from aios_core.ingest.conversation import (
    INTERACTION_DIMENSION,
    ConversationCommit,
    ConversationIngestor,
)
from aios_core.policy import (
    CognitivePolicyCreateRequest,
    CognitivePolicyRegistry,
    CognitivePolicyUpdateRequest,
)
from aios_core.projections.all_dimensions import AllDimensionsProjectionService
from aios_core.query.search import WorldSearchIndex
from aios_core.recommendation.proactive import (
    ProactiveMemoryRecommender,
    RecommendationBundle,
)
from aios_core.recommendation.topic_state import TopicState, TopicStateService
from aios_core.revision.service import ClaimRevisionRequest, CognitionRevisionService
from aios_core.review import (
    OperationExperienceRequest,
    PeriodicReviewRequest,
    PeriodicReviewService,
    ReviewSchedulePolicy,
    ReviewWakeReceipt,
)
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries import DimensionSummaryInput, MultiScaleSummaryScheduler, SummaryScale, SummaryScheduleResult
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.contracts.enums import AttentionClass, ObjectType, PolicyClass, WakeSource
from aios_core.wake import (
    AttentionRouter,
    AttentionSchedulingPolicy,
    AttentionWatchRequest,
    AttentionWatchService,
    NumericPredicate,
    Step0GateInput,
    Step0GateResult,
    WakeBus,
    WakeStateReceipt,
)
from aios_core.world_graph import (
    EntityProposalRequest,
    EntityRelationService,
    EntityRevisionRequest,
    RelationUpsertRequest,
)

from .budget_gate import BackgroundBudgetDecision, BackgroundBudgetGate
from .capabilities import CapabilityKind, CapabilityRegistry, CapabilitySpec
from .cognitive_runtime import CognitiveRuntime, ModelHandler, RuntimeTurnResult


_AUTO_TOPIC = object()


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
    runtime: RuntimeTurnResult | None
    context: ModelContextBundle | None
    wake: ReviewWakeReceipt
    budget: BackgroundBudgetDecision | None = None


@dataclass(frozen=True, slots=True)
class WakeDispatchRunResult:
    wake_ref: ObjectRef
    runtime: RuntimeTurnResult | None
    context: ModelContextBundle | None
    step0: Step0GateResult
    wake: WakeStateReceipt
    delivery_response: str | None
    delivery_suppressed: bool


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
        dimension_summary_handler: Callable[[DimensionSummaryInput], str] | None = None,
        recent_turn_limit: int = 8,
        summary_chunk_turns: int = 12,
        max_round_summaries_per_turn: int = 1,
        attention_scheduling_policy: AttentionSchedulingPolicy | None = None,
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
        self.attention_scheduling_policy = (
            attention_scheduling_policy or AttentionSchedulingPolicy()
        )
        self.recommender = ProactiveMemoryRecommender(
            index=index,
            store=store,
            default_limit=recommendation_limit,
        )
        self.topic_state = TopicStateService()
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
        self.world_graph = EntityRelationService(
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
        self.events = EventDimensionService(
            store=store,
            index=index,
            subject_id=subject_id,
        )
        self.communication_experience = CommunicationExperienceService(
            store=store,
            index=index,
            subject_id=subject_id,
        )
        self.policies = CognitivePolicyRegistry(
            store=store,
            index=index,
            subject_id=subject_id,
        )
        self.dimension_summary_scheduler = (
            None
            if dimension_summary_handler is None
            else MultiScaleSummaryScheduler(
                store=store,
                index=index,
                summary_handler=dimension_summary_handler,
                subject_id=subject_id,
            )
        )
        self.periodic_review = PeriodicReviewService(
            store=store,
            index=index,
            subject_id=self.subject_id,
        )
        self.wake_bus = WakeBus(
            store=store,
            index=index,
            subject_id=self.subject_id,
        )
        self.attention_watches = AttentionWatchService(
            store=store,
            index=index,
            execution_world=self.execution_world,
            wake_bus=self.wake_bus,
            subject_id=self.subject_id,
        )
        self.attention_router = AttentionRouter(
            store=store,
            wake_bus=self.wake_bus,
            subject_id=self.subject_id,
        )
        self.metering = ModelMeteringLedger(store)
        self.background_budget_gate = BackgroundBudgetGate(
            store=store,
            subject_id=self.subject_id,
            metering_ledger=self.metering,
        )
        self.reality_ingest = RealityIngestService(
            store=store,
            index=index,
            subject_id=self.subject_id,
            observation_listener=self.attention_watches.evaluate_observation,
        )
        self._active_turn_time: datetime | None = None
        self._active_meter_time: datetime | None = None
        self._active_session_id: str | None = None
        self._active_wake_id: str | None = None
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
                name="search_conversation_summaries",
                description=(
                    "Search same-session round-summary indexes by topic/text, then "
                    "drill down to exact pinned raw dialogue when precision is needed."
                ),
                kind=CapabilityKind.READ,
                input_schema={
                    "query": "string",
                    "session_id": "string?",
                    "limit": "integer?",
                },
            ),
            self._search_conversation_summaries,
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
                name="read_world_map",
                description=(
                    "Refresh the compact L0 world-map directory. Returns dimension identity, "
                    "mechanical activity/count metadata and expansion capability names only; "
                    "it does not return dimension payloads or semantic conclusions."
                ),
                kind=CapabilityKind.READ,
                input_schema={},
            ),
            self._read_world_map,
        )
        registry.register(
            CapabilitySpec(
                name="list_attention_watches",
                description=(
                    "List Resident-authored active attention watches. Watches contain only "
                    "mechanical future-match predicates; the Resident interprets meaning after Wake."
                ),
                kind=CapabilityKind.READ,
                input_schema={},
            ),
            self._list_attention_watches,
        )
        registry.register(
            CapabilitySpec(
                name="read_background_budget",
                description=(
                    "Read the current mechanical BACKGROUND_DAY budget and durable usage. "
                    "This reports policy caps, Wake/model-call usage and remaining capacity only; "
                    "it does not decide which future fact is important."
                ),
                kind=CapabilityKind.READ,
                input_schema={},
            ),
            self._read_background_budget,
        )
        registry.register(
            CapabilitySpec(
                name="create_attention_watch",
                description=(
                    "Register future attention as a constrained mechanical Observation watch. "
                    "The Resident chooses the routing class: interrupt wakes cognition immediately "
                    "and may allow user delivery after Resident judgment; background waits for short "
                    "mechanical batching, invokes cognition, and is silent to the user by default; "
                    "review_queue does not invoke the Resident immediately and carries matched evidence "
                    "into Periodic Review. Choose the class from the future-attention intent and current "
                    "runtime facts; Core does not infer urgency for you. Do not encode emotion, intent, "
                    "diagnosis, or other semantic conclusions in the mechanical predicate."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "title": "string",
                    "dimensions": "array[string]",
                    "reason_refs": "array[{object_id:string,revision:integer}]",
                    "goal_ref": "{object_id:string,revision:integer}?",
                    "source_kind": "string?",
                    "modality": "string?",
                    "metadata_equals": "object?",
                    "numeric": "{operator:gt|gte|lt|lte|eq|ne,threshold:number,path:array[string]?}?",
                    "priority": "integer?",
                    "cooldown_seconds": "integer?",
                    "attention_class": "interrupt|background|review_queue?",
                    "mode": "recurring|one_shot?",
                    "expires_at": "ISO-8601 datetime?",
                },
            ),
            self._create_attention_watch,
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
                name="propose_entity",
                description=(
                    "Create a durable Entity anchor from pinned same-world evidence. "
                    "The resident supplies identity meaning; Core enforces explicit entity_key and provenance."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "entity_key": "string",
                    "entity_kind": "string",
                    "canonical_name": "string?",
                    "aliases": "array[string]?",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "identity_claim_refs": "array[{object_id:string,revision:integer}]?",
                },
            ),
            self._propose_entity,
        )
        registry.register(
            CapabilitySpec(
                name="revise_entity",
                description=(
                    "Append a new revision of the current Entity identity anchor using pinned evidence."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "entity_ref": "{object_id:string,revision:integer}",
                    "reason": "string",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "canonical_name": "string?",
                    "aliases": "array[string]?",
                    "identity_claim_refs": "array[{object_id:string,revision:integer}]?",
                },
            ),
            self._revise_entity,
        )
        registry.register(
            CapabilitySpec(
                name="upsert_relation",
                description=(
                    "Create or forward-revise an evidence-grounded Relation between current Entity revisions."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "left_ref": "{object_id:string,revision:integer}",
                    "relation_type": "string",
                    "right_ref": "{object_id:string,revision:integer}",
                    "valid_time": "TemporalExtent object?",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "confidence": "number[0,1]",
                    "reason": "string",
                },
            ),
            self._upsert_relation,
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
        registry.register(
            CapabilitySpec(
                name="focus_entity",
                description="Focus retrieval on one known Entity id without semantic reinterpretation.",
                kind=CapabilityKind.READ,
                input_schema={"entity_id": "string", "query": "string?", "limit": "integer?"},
            ),
            self._focus_entity,
        )
        registry.register(
            CapabilitySpec(
                name="search_timeline",
                description="Search the world inside an explicit time window, optionally bounded by dimension/type/query.",
                kind=CapabilityKind.READ,
                input_schema={
                    "window_start": "ISO-8601 datetime",
                    "window_end": "ISO-8601 datetime",
                    "dimension": "string?",
                    "object_types": "array[string]?",
                    "query": "string?",
                    "limit": "integer?",
                },
            ),
            self._search_timeline,
        )
        registry.register(
            CapabilitySpec(
                name="follow_relation",
                description="Follow one-hop explicit Relation objects connected to a world object.",
                kind=CapabilityKind.READ,
                input_schema={"object_id": "string", "limit": "integer?"},
            ),
            self._follow_relation,
        )
        registry.register(
            CapabilitySpec(
                name="compare_claims",
                description="Inspect multiple pinned Claims side by side with their evidence/status; the model decides meaning.",
                kind=CapabilityKind.READ,
                input_schema={"claim_refs": "array[{object_id:string,revision:integer}]"},
            ),
            self._compare_claims,
        )
        registry.register(
            CapabilitySpec(
                name="retrieve_original_observation",
                description="Retrieve an exact Observation fact by id/revision for evidence drill-down.",
                kind=CapabilityKind.READ,
                input_schema={"object_id": "string", "revision": "integer?"},
            ),
            self._retrieve_original_observation,
        )
        registry.register(
            CapabilitySpec(
                name="expand_recall",
                description="Request a broader bounded world recall after the initial recommendation/search was insufficient.",
                kind=CapabilityKind.READ,
                input_schema={
                    "query": "string",
                    "dimension": "string?",
                    "limit": "integer?",
                },
            ),
            self._expand_recall,
        )
        registry.register(
            CapabilitySpec(
                name="inspect_outcome",
                description="Inspect a pinned real Action Outcome and its Action reference.",
                kind=CapabilityKind.READ,
                input_schema={"outcome_ref": "{object_id:string,revision:integer}"},
            ),
            self._inspect_outcome,
        )
        registry.register(
            CapabilitySpec(
                name="read_cognitive_policies",
                description="Read current versioned R6 policy records from the unified world.",
                kind=CapabilityKind.READ,
                input_schema={"policy_id": "string?"},
            ),
            self._read_cognitive_policies,
        )
        registry.register(
            CapabilitySpec(
                name="propose_cognitive_policy",
                description=(
                    "Register a new evidence-grounded AI-mutable cognitive policy. "
                    "Only real user/world result evidence is accepted; hard boundaries "
                    "cannot be created by the resident AI."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "policy_id": "string",
                    "scope": "string",
                    "default_value": "json value",
                    "current_value": "json value",
                    "allowed_range_or_choices": "json value?",
                    "reason": "string",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "evaluation_window": "string",
                },
            ),
            self._propose_cognitive_policy,
        )
        registry.register(
            CapabilitySpec(
                name="form_event",
                description=(
                    "Form a revisable Event candidate from pinned world evidence. "
                    "The model supplies the event meaning; code only validates provenance."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "title": "string",
                    "interpretation": "string",
                    "event_time": "TemporalExtent object",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "participant_refs": "array[{object_id:string,revision:integer}]?",
                    "primary_claim_refs": "array[{object_id:string,revision:integer}]?",
                    "confidence": "number[0,1]",
                    "dimension": "string?",
                },
            ),
            self._form_event,
        )
        registry.register(
            CapabilitySpec(
                name="transition_event",
                description="Forward-revise/resolve/reject/merge/split the current Event using pinned evidence.",
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "event_ref": "{object_id:string,revision:integer}",
                    "new_status": "candidate|active|resolved|revised|rejected|merged|split",
                    "reason": "string",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "replacement_title": "string?",
                    "replacement_interpretation": "string?",
                    "confidence": "number[0,1]?",
                    "related_event_refs": "array[{object_id:string,revision:integer}]?",
                },
            ),
            self._transition_event,
        )
        registry.register(
            CapabilitySpec(
                name="record_communication_experience",
                description=(
                    "Record what communication style was used and the real user/world reaction. "
                    "This records evidence only and does not choose a future style."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "scenario": "string",
                    "style": "string",
                    "tone": "string?",
                    "user_reaction": "accepted|resisted|ignored|unknown",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "action_ref": "{object_id:string,revision:integer}?",
                    "applicable_conditions": "object?",
                    "counterexample_refs": "array[{object_id:string,revision:integer}]?",
                },
            ),
            self._record_communication_experience,
        )
        registry.register(
            CapabilitySpec(
                name="update_cognitive_policy",
                description=(
                    "Append an evidence-grounded value revision to an already-registered "
                    "AI-mutable cognitive policy. Cannot create or loosen hard boundaries."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "policy_id": "string",
                    "current_value": "json value",
                    "reason": "string",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                    "evaluation_window": "string?",
                },
            ),
            self._update_cognitive_policy,
        )
        registry.register(
            CapabilitySpec(
                name="rollback_cognitive_policy",
                description=(
                    "Forward-append a rollback to an earlier policy version using pinned evidence."
                ),
                kind=CapabilityKind.WRITE,
                side_effecting=True,
                input_schema={
                    "policy_id": "string",
                    "target_version": "integer",
                    "reason": "string",
                    "evidence_refs": "array[{object_id:string,revision:integer}]",
                },
            ),
            self._rollback_cognitive_policy,
        )
        self.registry = registry
        self.cognitive_runtime = CognitiveRuntime(
            registry=registry,
            model_handler=model_handler,
            max_tool_rounds=max_tool_rounds,
            side_effect_authorizer=self._authorize_side_effect,
            model_usage_recorder=self._record_model_usage,
        )

    def _record_model_usage(
        self,
        snapshot: RuntimeSnapshot,
        usage: ModelUsage | None,
    ) -> None:
        if self._active_meter_time is None:
            raise RuntimeError(
                "FusedTurnRuntime model invocation is missing active metering time"
            )

        wake_reason = snapshot.wake_reason
        if wake_reason == WakeSource.USER_INTERACTION.value:
            execution_class = "user_interaction"
        elif wake_reason == WakeSource.PERIODIC_REVIEW.value:
            execution_class = "periodic_review"
        elif wake_reason == WakeSource.SAFETY.value:
            execution_class = "safety"
        elif self._active_wake_id is not None:
            execution_class = "background"
        else:
            execution_class = "other"

        self.metering.record_model_call(
            subject_id=self.subject_id,
            world_revision=int(self.store.current_world_revision()),
            recorded_at=self._active_meter_time,
            execution_class=execution_class,
            wake_id=self._active_wake_id,
            session_id=self._active_session_id,
            wake_reason=wake_reason,
            model_round_index=snapshot.round_index,
            usage=usage,
        )

    def _cockpit_capability_catalog(self) -> tuple[dict[str, Any], ...]:
        """Compact capability awareness for context budgeting.

        CognitiveRuntime already supplies the full schemas/descriptions separately in
        RuntimeSnapshot.capability_catalog. Repeating the full tool schema inside the
        cockpit wastes context budget and can evict memory/continuity. The cockpit only
        needs enough information to tell the model which named abilities exist.
        """

        return tuple(
            {
                "name": item["name"],
                "kind": item["kind"],
                "side_effecting": bool(item.get("side_effecting", False)),
            }
            for item in self.registry.catalog()
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

    def _runtime_subject_scope(self) -> frozenset[str]:
        """Subjects that belong to this resident private user/AI world."""

        return frozenset({self.subject_id, self.ai_world.ai_subject_id})

    def _scoped_payload(
        self,
        object_id: str,
        revision: int | None = None,
    ) -> dict[str, Any]:
        payload = self.store.get_payload(str(object_id), revision=revision)
        payload_subject = str(payload.get("subject_id") or "")
        if payload_subject not in self._runtime_subject_scope():
            raise ValueError(
                "world object crosses the runtime private-world subject scope: "
                f"{payload_subject!r}"
            )
        return payload

    def _inspect_world_object(
        self,
        object_id: str,
        revision: int | None = None,
    ) -> dict[str, Any]:
        return self._scoped_payload(str(object_id), revision=revision)

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

    def _search_conversation_summaries(
        self,
        query: str,
        session_id: str | None = None,
        limit: int = 8,
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
        return [
            dict(item)
            for item in self.continuity.search_round_summaries(
                session_id=active_session,
                query=str(query),
                limit=max(1, min(int(limit), 20)),
            )
        ]

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
    def _world_map_context(self, as_of: datetime) -> dict[str, Any]:
        """Build the always-visible L0 world directory without injecting payload semantics."""

        directory = self.index.dimension_directory(
            subject=self.subject_id,
            as_of=as_of,
            include_inactive=False,
            limit=24,
        )
        rows_by_key = {
            str(item["dimension"]): dict(item)
            for item in directory["dimensions"]
        }

        for definition in self.dimensions.current_dimensions(include_terminal=False):
            key = str(definition.metadata.get("dimension_key") or "").strip()
            if not key:
                continue
            row = rows_by_key.setdefault(
                key,
                {
                    "dimension": key,
                    "current_object_count": 0,
                    "recent_24h_count": 0,
                    "recent_7d_count": 0,
                    "latest_activity_at": None,
                    "object_types": [],
                },
            )
            row.update(
                {
                    "registered": True,
                    "name": definition.name,
                    "lifecycle": definition.lifecycle.value,
                    "definition_ref": {
                        "object_id": definition.object_id,
                        "revision": definition.revision,
                    },
                }
            )

        dimensions: list[dict[str, Any]] = []
        for key, row in rows_by_key.items():
            normalized = dict(row)
            normalized.setdefault("registered", False)
            normalized.setdefault("name", None)
            normalized.setdefault("lifecycle", None)
            normalized.setdefault("definition_ref", None)
            normalized["object_types"] = list(normalized.get("object_types") or [])[:8]
            dimensions.append(normalized)

        dimensions.sort(
            key=lambda item: (
                -int(item.get("recent_24h_count") or 0),
                -int(item.get("recent_7d_count") or 0),
                str(item.get("dimension") or ""),
            )
        )

        return {
            "schema": "aios.world-map.l0.v1",
            "directory_only": True,
            "semantic_conclusions": False,
            "world_revision": int(directory["world_revision"]),
            "index_watermark": int(directory["index_watermark"]),
            "index_lag": int(directory["lag"]),
            "as_of": directory["as_of"],
            "dimension_count": len(dimensions),
            "dimensions": dimensions,
            "truncated": bool(directory["truncated"]),
            "expand_capabilities": {
                "multi_dimension_window": "request_all_dimensions_projection",
                "single_dimension_timeline": "search_timeline",
                "semantic_recall": "search_world",
                "broader_recall": "expand_recall",
                "exact_object": "inspect_world_object",
                "dimension_definitions": "list_dimensions",
                "refresh_directory": "read_world_map",
            },
        }

    def _read_world_map(self) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("read_world_map is only available during an active AIOS turn")
        return self._world_map_context(self._active_turn_time)

    def _list_attention_watches(self) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in self.attention_watches.current()
        ]

    def _read_background_budget(self) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError(
                "read_background_budget is only available during an active AIOS turn"
            )
        return self.background_budget_gate.status(now=self._active_turn_time)

    def _create_attention_watch(
        self,
        title: str,
        dimensions: Sequence[str],
        reason_refs: Sequence[Mapping[str, Any]],
        goal_ref: Mapping[str, Any] | None = None,
        source_kind: str | None = None,
        modality: str | None = None,
        metadata_equals: Mapping[str, Any] | None = None,
        numeric: Mapping[str, Any] | None = None,
        priority: int = 50,
        cooldown_seconds: int = 0,
        attention_class: str = "background",
        mode: str = "recurring",
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError(
                "create_attention_watch is only available during an active AIOS turn"
            )
        parsed_goal = (
            None
            if goal_ref is None
            else ObjectRef(
                object_id=str(goal_ref["object_id"]),
                revision=int(goal_ref["revision"]),
            )
        )
        parsed_numeric = (
            None
            if numeric is None
            else NumericPredicate.model_validate(dict(numeric))
        )
        receipt = self.attention_watches.create(
            AttentionWatchRequest(
                title=str(title),
                dimensions=tuple(str(item) for item in dimensions),
                reason_refs=self._coerce_refs(reason_refs),
                goal_ref=parsed_goal,
                source_kind=source_kind,
                modality=modality,
                metadata_equals=dict(metadata_equals or {}),
                numeric=parsed_numeric,
                priority=int(priority),
                cooldown_seconds=int(cooldown_seconds),
                attention_class=AttentionClass(str(attention_class)),
                mode=str(mode),
                expires_at=(
                    None
                    if expires_at is None
                    else datetime.fromisoformat(
                        str(expires_at).replace("Z", "+00:00")
                    )
                ),
            ),
            created_at=self._active_turn_time,
        )
        return asdict(receipt)

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


    def _propose_entity(
        self,
        entity_key: str,
        entity_kind: str,
        evidence_refs: Sequence[Mapping[str, Any]],
        canonical_name: str | None = None,
        aliases: Sequence[str] = (),
        identity_claim_refs: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("propose_entity is only available during an active AIOS turn")
        receipt = self.world_graph.propose_entity(
            EntityProposalRequest(
                entity_key=str(entity_key),
                entity_kind=str(entity_kind),
                canonical_name=canonical_name,
                aliases=tuple(str(item) for item in aliases),
                evidence_refs=self._coerce_refs(evidence_refs),
                identity_claim_refs=self._coerce_refs(identity_claim_refs),
            ),
            proposed_at=self._active_turn_time,
        )
        return asdict(receipt)

    def _revise_entity(
        self,
        entity_ref: Mapping[str, Any],
        reason: str,
        evidence_refs: Sequence[Mapping[str, Any]],
        canonical_name: str | None = None,
        aliases: Sequence[str] | None = None,
        identity_claim_refs: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("revise_entity is only available during an active AIOS turn")
        receipt = self.world_graph.revise_entity(
            EntityRevisionRequest(
                entity_ref=ObjectRef(
                    object_id=str(entity_ref["object_id"]),
                    revision=int(entity_ref["revision"]),
                ),
                reason=str(reason),
                evidence_refs=self._coerce_refs(evidence_refs),
                canonical_name=canonical_name,
                aliases=(
                    None
                    if aliases is None
                    else tuple(str(item) for item in aliases)
                ),
                identity_claim_refs=(
                    None
                    if identity_claim_refs is None
                    else self._coerce_refs(identity_claim_refs)
                ),
            ),
            changed_at=self._active_turn_time,
        )
        return asdict(receipt)

    def _upsert_relation(
        self,
        left_ref: Mapping[str, Any],
        relation_type: str,
        right_ref: Mapping[str, Any],
        evidence_refs: Sequence[Mapping[str, Any]],
        confidence: float,
        reason: str,
        valid_time: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("upsert_relation is only available during an active AIOS turn")
        receipt = self.world_graph.upsert_relation(
            RelationUpsertRequest(
                left_ref=ObjectRef(
                    object_id=str(left_ref["object_id"]),
                    revision=int(left_ref["revision"]),
                ),
                relation_type=str(relation_type),
                right_ref=ObjectRef(
                    object_id=str(right_ref["object_id"]),
                    revision=int(right_ref["revision"]),
                ),
                valid_time=(
                    TemporalExtent.unknown_time()
                    if valid_time is None
                    else TemporalExtent.model_validate(valid_time)
                ),
                evidence_refs=self._coerce_refs(evidence_refs),
                confidence=float(confidence),
                reason=str(reason),
            ),
            changed_at=self._active_turn_time,
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

    @staticmethod
    def _search_hit_payload(hit) -> dict[str, Any]:
        return {
            "object_id": hit.object_id,
            "revision": hit.revision,
            "object_type": hit.object_type,
            "dimension": hit.dimension,
            "excerpt": hit.excerpt,
            "retrieval_score": hit.score,
        }

    def _focus_entity(
        self,
        entity_id: str,
        query: str | None = None,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        page = self.index.search_by_entity(
            str(entity_id),
            keywords=(() if query is None or not str(query).strip() else (str(query),)),
            subject=self.subject_id,
            limit=max(1, min(int(limit), 50)),
        )
        return [self._search_hit_payload(hit) for hit in page.hits]

    def _search_timeline(
        self,
        window_start: str,
        window_end: str,
        dimension: str | None = None,
        object_types: Sequence[str] | None = None,
        query: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        start = datetime.fromisoformat(str(window_start).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(window_end).replace("Z", "+00:00"))
        page = self.index.search_mind(
            keywords=(() if query is None or not str(query).strip() else (str(query),)),
            subject=self.subject_id,
            dimension=(None if dimension is None else str(dimension)),
            object_types=(None if object_types is None else tuple(str(x) for x in object_types)),
            time_range=(start, end),
            limit=max(1, min(int(limit), 100)),
        )
        return [self._search_hit_payload(hit) for hit in page.hits]

    def _follow_relation(
        self,
        object_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        target = str(object_id)
        matched: list[dict[str, Any]] = []
        for payload in self.store.list_payloads(
            object_type=ObjectType.RELATION,
            subject_id=self.subject_id,
        ):
            left = payload.get("left") or {}
            right = payload.get("right") or {}
            if str(left.get("object_id") or "") != target and str(right.get("object_id") or "") != target:
                continue
            matched.append(payload)
            if len(matched) >= max(1, min(int(limit), 100)):
                break
        return matched

    def _compare_claims(
        self,
        claim_refs: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for ref in self._coerce_refs(claim_refs):
            payload = self._scoped_payload(
                ref.object_id,
                revision=ref.revision,
            )
            if payload.get("object_type") != ObjectType.CLAIM.value:
                raise ValueError("compare_claims accepts only Claim references")
            result.append(
                {
                    "claim": payload,
                    "support_evidence_sets": [
                        self._scoped_payload(
                            str(item["object_id"]),
                            revision=int(item["revision"]),
                        )
                        for item in payload.get("support_evidence_set_refs") or []
                    ],
                    "counter_evidence_sets": [
                        self._scoped_payload(
                            str(item["object_id"]),
                            revision=int(item["revision"]),
                        )
                        for item in payload.get("counter_evidence_set_refs") or []
                    ],
                }
            )
        return result

    def _retrieve_original_observation(
        self,
        object_id: str,
        revision: int | None = None,
    ) -> dict[str, Any]:
        payload = self._scoped_payload(str(object_id), revision=revision)
        if payload.get("object_type") != ObjectType.OBSERVATION.value:
            raise ValueError("requested object is not an Observation")
        return payload

    def _expand_recall(
        self,
        query: str,
        dimension: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        page = self.index.recall_candidates(
            str(query),
            subject=self.subject_id,
            dimension=(None if dimension is None else str(dimension)),
            limit=max(1, min(int(limit), 100)),
        )
        return [self._search_hit_payload(hit) for hit in page.hits]

    def _inspect_outcome(
        self,
        outcome_ref: Mapping[str, Any],
    ) -> dict[str, Any]:
        ref = ObjectRef(
            object_id=str(outcome_ref["object_id"]),
            revision=int(outcome_ref["revision"]),
        )
        payload = self._scoped_payload(
            ref.object_id,
            revision=ref.revision,
        )
        if payload.get("object_type") != ObjectType.OUTCOME.value:
            raise ValueError("outcome_ref must point to an Outcome")
        action_ref = payload.get("action_ref") or {}
        action = self._scoped_payload(
            str(action_ref["object_id"]),
            revision=int(action_ref["revision"]),
        )
        return {"outcome": payload, "action": action}

    def _read_cognitive_policies(
        self,
        policy_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if policy_id is not None and str(policy_id).strip():
            item = self.policies.latest(str(policy_id))
            return [] if item is None else [item.model_dump(mode="json")]
        return [
            item.model_dump(mode="json")
            for item in self.policies.list_current()
        ]

    def _propose_cognitive_policy(
        self,
        policy_id: str,
        scope: str,
        default_value: Any,
        current_value: Any,
        reason: str,
        evidence_refs: Sequence[Mapping[str, Any]],
        evaluation_window: str,
        allowed_range_or_choices: Any = None,
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError(
                "propose_cognitive_policy is only available during an active AIOS turn"
            )
        receipt = self.policies.register(
            CognitivePolicyCreateRequest(
                policy_id=str(policy_id),
                scope=str(scope),
                policy_class=PolicyClass.COGNITIVE_POLICY,
                default_value=default_value,
                current_value=current_value,
                allowed_range_or_choices=allowed_range_or_choices,
                mutable_by_ai=True,
                reason=str(reason),
                evidence_refs=self._coerce_refs(evidence_refs),
                changed_by="resident_ai",
                evaluation_window=str(evaluation_window),
            ),
            changed_at=self._active_turn_time,
            actor_is_ai=True,
        )
        return asdict(receipt)


    def _form_event(
        self,
        title: str,
        interpretation: str,
        event_time: Mapping[str, Any],
        evidence_refs: Sequence[Mapping[str, Any]],
        confidence: float,
        participant_refs: Sequence[Mapping[str, Any]] = (),
        primary_claim_refs: Sequence[Mapping[str, Any]] = (),
        dimension: str = "dim:events",
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("form_event is only available during an active AIOS turn")
        receipt = self.events.form_event(
            EventWriteRequest(
                title=title,
                interpretation=interpretation,
                event_time=dict(event_time),
                evidence_refs=self._coerce_refs(evidence_refs),
                participant_refs=self._coerce_refs(participant_refs),
                primary_claim_refs=self._coerce_refs(primary_claim_refs),
                confidence=float(confidence),
                dimension=dimension,
            ),
            learned_at=self._active_turn_time,
        )
        return asdict(receipt)

    def _transition_event(
        self,
        event_ref: Mapping[str, Any],
        new_status: str,
        reason: str,
        evidence_refs: Sequence[Mapping[str, Any]],
        replacement_title: str | None = None,
        replacement_interpretation: str | None = None,
        confidence: float | None = None,
        related_event_refs: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError("transition_event is only available during an active AIOS turn")
        receipt = self.events.transition(
            EventTransitionRequest(
                event_ref=ObjectRef(
                    object_id=str(event_ref["object_id"]),
                    revision=int(event_ref["revision"]),
                ),
                new_status=new_status,
                reason=reason,
                evidence_refs=self._coerce_refs(evidence_refs),
                replacement_title=replacement_title,
                replacement_interpretation=replacement_interpretation,
                confidence=confidence,
                related_event_refs=self._coerce_refs(related_event_refs),
            ),
            changed_at=self._active_turn_time,
        )
        return asdict(receipt)

    def _record_communication_experience(
        self,
        scenario: str,
        style: str,
        user_reaction: str,
        evidence_refs: Sequence[Mapping[str, Any]],
        tone: str | None = None,
        action_ref: Mapping[str, Any] | None = None,
        applicable_conditions: Mapping[str, Any] | None = None,
        counterexample_refs: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError(
                "record_communication_experience is only available during an active AIOS turn"
            )
        parsed_action = (
            None
            if action_ref is None
            else ObjectRef(
                object_id=str(action_ref["object_id"]),
                revision=int(action_ref["revision"]),
            )
        )
        receipt = self.communication_experience.record(
            CommunicationExperienceRequest(
                scenario=scenario,
                style=style,
                tone=tone,
                user_reaction=user_reaction,
                evidence_refs=self._coerce_refs(evidence_refs),
                action_ref=parsed_action,
                applicable_conditions=dict(applicable_conditions or {}),
                counterexample_refs=self._coerce_refs(counterexample_refs),
            ),
            recorded_at=self._active_turn_time,
        )
        return asdict(receipt)

    def _update_cognitive_policy(
        self,
        policy_id: str,
        current_value: Any,
        reason: str,
        evidence_refs: Sequence[Mapping[str, Any]],
        evaluation_window: str | None = None,
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError(
                "update_cognitive_policy is only available during an active AIOS turn"
            )
        receipt = self.policies.update(
            CognitivePolicyUpdateRequest(
                policy_id=policy_id,
                current_value=current_value,
                reason=reason,
                evidence_refs=self._coerce_refs(evidence_refs),
                changed_by="resident_ai",
                evaluation_window=evaluation_window,
            ),
            changed_at=self._active_turn_time,
            actor_is_ai=True,
        )
        return asdict(receipt)

    def _rollback_cognitive_policy(
        self,
        policy_id: str,
        target_version: int,
        reason: str,
        evidence_refs: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if self._active_turn_time is None:
            raise RuntimeError(
                "rollback_cognitive_policy is only available during an active AIOS turn"
            )
        receipt = self.policies.rollback(
            policy_id,
            int(target_version),
            reason=reason,
            evidence_refs=self._coerce_refs(evidence_refs),
            changed_by="resident_ai",
            changed_at=self._active_turn_time,
            actor_is_ai=True,
        )
        return asdict(receipt)

    def _cognitive_policy_context(self, *, limit: int = 32) -> dict[str, Any]:
        """Compact current policy view for every resident semantic entry point.

        Policies learned from direct evidence must become available to later cognition
        without requiring the model to guess a policy id first. Scope/class metadata is
        kept beside the convenience value map so a local policy is not silently treated
        as global. The full ledger remains available through read_cognitive_policies when
        this bounded context is truncated.
        """

        if limit < 1:
            raise ValueError("policy context limit must be >= 1")
        items = list(self.policies.list_current())
        values: dict[str, Any] = {}
        records: list[dict[str, Any]] = []
        for item in items[:limit]:
            values[item.policy_id] = item.current_value
            records.append(
                {
                    "policy_id": item.policy_id,
                    "scope": item.scope,
                    "policy_class": item.policy_class.value,
                    "default_value": item.default_value,
                    "current_value": item.current_value,
                    "allowed_range_or_choices": item.allowed_range_or_choices,
                    "mutable_by_ai": item.mutable_by_ai,
                    "evaluation_window": item.evaluation_window,
                    "version": item.revision,
                    "previous_version": item.previous_version,
                    "rollback_pointer": item.rollback_pointer,
                }
            )
        values["_policy_records"] = records
        values["_meta"] = {
            "total": len(items),
            "included": min(len(items), limit),
            "truncated": len(items) > limit,
            "reader": "read_cognitive_policies",
        }
        return values

    def _execution_context_for_topic(
        self,
        topic: str | None,
        *,
        limit: int = 6,
    ) -> dict[str, Any]:
        clean = "" if topic is None else str(topic).strip()
        if not clean:
            return {"related_execution_anchors": []}
        page = self.index.recall_candidates(
            clean,
            subject=self.subject_id,
            object_types=(
                ObjectType.GOAL.value,
                ObjectType.TASK.value,
                ObjectType.ACTION.value,
                ObjectType.OUTCOME.value,
            ),
            limit=max(1, min(int(limit), 20)),
        )
        return {
            "related_execution_anchors": [
                self._search_hit_payload(hit)
                for hit in page.hits
            ]
        }

    def _authorize_side_effect(self, spec, call, snapshot) -> bool:
        # Internal cognition writeback is allowed because the handler itself enforces
        # pinned evidence and writes only revisable cognition. External actions stay
        # denied until a separate capability-specific authorization layer exists.
        return spec.name in {
            "commit_claim",
            "commit_ai_world_claim",
            "propose_entity",
            "revise_entity",
            "upsert_relation",
            "propose_dimension",
            "transition_dimension",
            "propose_goal",
            "transition_goal",
            "create_task",
            "transition_task",
            "create_attention_watch",
            "propose_action",
            "commit_operation_experience",
            "revise_claim",
            "retract_claim",
            "form_event",
            "transition_event",
            "record_communication_experience",
            "propose_cognitive_policy",
            "update_cognitive_policy",
            "rollback_cognitive_policy",
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

    def run_due_dimension_summaries(
        self,
        *,
        now: datetime,
        scales: Sequence[str | SummaryScale] = tuple(SummaryScale),
        max_jobs: int = 64,
        dimensions: Sequence[str] | None = None,
    ) -> SummaryScheduleResult:
        """Run deterministic summary scheduling with model-generated content.

        This is maintenance, not resident cognition. The scheduler chooses only
        dimensions/windows/sources; the injected dimension_summary_handler writes the
        descriptive text and cannot alter raw facts.
        """

        if self.dimension_summary_scheduler is None:
            raise RuntimeError(
                "dimension_summary_handler is required for semantic dimension summaries"
            )
        parsed = tuple(SummaryScale(item) for item in scales)
        return self.dimension_summary_scheduler.run_due(
            now=now,
            scales=parsed,
            max_jobs=max_jobs,
            dimensions=dimensions,
        )

    def _structured_topic_history_signal(
        self,
        user_input: str,
    ) -> tuple[bool, str | None]:
        """Return mechanical current-world anchor signals without semantic guessing.

        Exact named anchors remain the strongest signal. When the user does not repeat
        an object's full title/name, Core may still open the history gate if the
        current utterance has at least two lexical-token overlaps with a *current*
        durable world anchor. This is candidate retrieval only: it decides whether
        historical context may help; it does not decide what the evidence means.

        Conversation Observations are deliberately excluded from this fallback so a
        long chat history cannot silently reopen proactive recall. Non-conversation
        Observations (calendar/sensor/platform/etc.) may act as factual world anchors.
        """

        current = " ".join(str(user_input).strip().split()).casefold()
        if not current:
            return False, None

        def mentioned(value: object) -> bool:
            text = " ".join(str(value or "").strip().split())
            # Single-character labels are too ambiguous for proactive injection.
            return len(text) >= 2 and text.casefold() in current

        for entity in self.world_graph.current_entities():
            labels = [entity.canonical_name, *entity.aliases]
            if any(mentioned(label) for label in labels if label):
                return True, "explicit_entity_anchor"

        for payload in self.store.list_payloads(
            object_type=ObjectType.EVENT,
            subject_id=self.subject_id,
        ):
            if mentioned(payload.get("title")):
                return True, "explicit_event_anchor"

        for goal in self.execution_world.current_goals():
            if mentioned(goal.title):
                return True, "explicit_goal_anchor"

        for task in self.execution_world.current_tasks():
            if mentioned(task.title):
                return True, "explicit_task_anchor"

        # P16 habitation exposed a false negative where a planning question depended
        # on a revised current Claim but did not repeat the later schedule/event title.
        # Use the same public lexical index as recommendation, restricted to current
        # visible structured anchors. A score >= 2 means at least two independent
        # index tokens overlap; Core still does not infer relevance or causality.
        structured_types = (
            ObjectType.CLAIM.value,
            ObjectType.EVENT.value,
            ObjectType.GOAL.value,
            ObjectType.TASK.value,
            ObjectType.ENTITY.value,
            ObjectType.RELATION.value,
        )
        structured_page = self.index.recall_candidates(
            current,
            subject=self.subject_id,
            object_types=structured_types,
            limit=8,
        )
        if any(hit.score >= 2 for hit in structured_page.hits):
            return True, "indexed_current_world_anchor"

        # External factual observations may also carry current state (for example a
        # calendar entry). Old conversation turns are intentionally not eligible here;
        # those remain available through explicit history cues or model deep search.
        observation_page = self.index.recall_candidates(
            current,
            subject=self.subject_id,
            object_types=(ObjectType.OBSERVATION.value,),
            limit=16,
        )
        for hit in observation_page.hits:
            if hit.score < 2:
                continue
            payload = self.store.get_payload(hit.object_id, revision=hit.revision)
            source_kind = str(payload.get("source_kind") or "").strip().casefold()
            metadata = payload.get("metadata")
            if not isinstance(metadata, Mapping):
                metadata = {}
            dimension = str(metadata.get("dimension") or "").strip()
            # ConversationIngestor uses source_kind="user_ai_interaction"; the
            # canonical interaction dimension is the stronger guard because it
            # survives compatible ingestors that choose a different source label.
            if (
                source_kind in {"conversation", "user_ai_interaction"}
                or dimension == INTERACTION_DIMENSION
            ):
                continue
            return True, "indexed_external_observation_anchor"

        return False, None

    def run_turn(
        self,
        *,
        session_id: str,
        turn_index: int,
        user_input: str,
        occurred_at: datetime,
        current_topic: str | None | object = _AUTO_TOPIC,
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

        self.attention_watches.expire_due(now=occurred_at)

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

        effective_token_budget = (
            self.context_controller.default_token_budget
            if token_budget is None
            else int(token_budget)
        )
        summary_trigger_tokens = max(
            128,
            int(effective_token_budget * 0.65),
        )
        continuity_snapshot = self.continuity.snapshot(
            session_id=session,
            before_turn=turn_index,
            recent_turn_limit=self.recent_turn_limit,
            summary_chunk_turns=self.summary_chunk_turns,
            summary_trigger_tokens=summary_trigger_tokens,
        )

        structured_history_signal, structured_signal_reason = (
            self._structured_topic_history_signal(user_input)
        )

        if current_topic is _AUTO_TOPIC:
            topic_state = self.topic_state.resolve(
                user_input=user_input,
                recent_turns=continuity_snapshot.recent_turns,
                explicit_topic=None,
                structured_history_signal=structured_history_signal,
                structured_signal_reason=structured_signal_reason,
            )
        elif current_topic is None:
            # Compatibility and explicit control: callers that deliberately pass
            # current_topic=None are closing the proactive-memory topic gate for
            # this turn. Callers that omit current_topic get Core-owned topic state.
            topic_state = TopicState(
                topic=None,
                gate_open=False,
                history_may_help=False,
                reason="explicit_no_topic_override",
            )
        else:
            topic_state = self.topic_state.resolve(
                user_input=user_input,
                recent_turns=continuity_snapshot.recent_turns,
                explicit_topic=str(current_topic),
                structured_history_signal=structured_history_signal,
                structured_signal_reason=structured_signal_reason,
            )
        raw_recommendation_limit = self.policies.effective_value(
            "memory.recommendation_limit",
            self.recommender.default_limit,
        )
        try:
            effective_recommendation_limit = max(
                1,
                min(int(raw_recommendation_limit), 20),
            )
        except (TypeError, ValueError):
            effective_recommendation_limit = self.recommender.default_limit

        recommendation = self.recommender.recommend(
            current_topic=topic_state.topic,
            subject_id=self.subject_id,
            exclude_session_id=session,
            limit=effective_recommendation_limit,
            history_needed=topic_state.history_may_help,
            antecedent_fallback=topic_state.antecedent_recall_needed,
        )

        continuity_context = (
            dict(ai_identity)
            if ai_identity is not None
            else self.ai_world.core_context(per_domain=3)
        )

        current_task_context = dict(task_context or {})
        current_task_context["topic_state"] = topic_state.model_dump(mode="json")
        current_task_context["cognitive_policy_context"] = (
            self._cognitive_policy_context()
        )
        current_task_context["cognitive_policy_context"][
            "memory.recommendation_limit"
        ] = effective_recommendation_limit
        current_task_context["cognitive_policy_context"].setdefault(
            "communication.detail_level",
            self.policies.effective_value(
                "communication.detail_level",
                None,
            ),
        )
        automatic_execution_context = self._execution_context_for_topic(topic_state.topic)
        current_task_context.setdefault(
            "related_execution_anchors",
            automatic_execution_context["related_execution_anchors"],
        )
        current_task_context["current_user_observation_ref"] = {
            "object_id": user_commit.observation_id,
            "revision": 1,
        }
        current_task_context["conversation_continuity"] = {
            "session_id": session,
            "recent_turn_count": len(continuity_snapshot.recent_turns),
            "round_summary_count": len(continuity_snapshot.round_summaries),
            "summary_index_capability": "list_conversation_summaries",
            "summary_search_capability": "search_conversation_summaries",
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
            current_topic=topic_state.topic,
            recommendation=recommendation,
            recent_turns=continuity_snapshot.recent_turns,
            conversation_summaries=continuity_snapshot.round_summaries,
            ai_identity=continuity_context,
            world_map=self._world_map_context(occurred_at),
            task_context=current_task_context,
            capability_catalog=self._cockpit_capability_catalog(),
            token_budget=token_budget,
        )

        self._active_turn_time = occurred_at
        self._active_meter_time = occurred_at
        self._active_session_id = session
        self._active_wake_id = None
        try:
            runtime_result = self.cognitive_runtime.run_turn(
                user_input,
                wake_reason="user_interaction",
                cockpit=context.as_cockpit(),
            )
        finally:
            self._active_turn_time = None
            self._active_meter_time = None
            self._active_session_id = None
            self._active_wake_id = None

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
                        summary_trigger_tokens=summary_trigger_tokens,
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



    def dispatch_next_pending_wake(
        self,
        *,
        now: datetime,
        step0: Step0GateInput | None = None,
        token_budget: int | None = None,
    ) -> WakeDispatchRunResult | None:
        """Advance mechanical timers and dispatch one eligible Resident Wake.

        This is the runtime-facing attention scheduler entrypoint. It expires stale
        watches, materializes due Task Wakes, then chooses exactly one pending Wake.
        REVIEW_QUEUE and conversation turns are intentionally excluded.
        """

        self.attention_watches.expire_due(now=now)
        self.execution_world.wake_due_tasks(now=now)

        wake = self.attention_router.next_dispatchable(
            now=now,
            background_batch_window_seconds=(
                self.attention_scheduling_policy.background_batch_window_seconds
            ),
        )
        if wake is None:
            return None

        return self.run_wake(
            wake_ref=ObjectRef(
                object_id=wake.object_id,
                revision=wake.revision,
            ),
            now=now,
            step0=step0,
            token_budget=token_budget,
        )


    def run_wake(
        self,
        *,
        wake_ref: ObjectRef | Mapping[str, Any],
        now: datetime,
        step0: Step0GateInput | None = None,
        token_budget: int | None = None,
    ) -> WakeDispatchRunResult:
        """Dispatch one durable non-conversation Wake through the resident runtime.

        This is the constitutional C09 bridge between deterministic Wake creation
        and semantic model judgment. It does not create a synthetic user
        Conversation Observation and it never interprets the trigger in code.
        """

        ref = (
            wake_ref
            if isinstance(wake_ref, ObjectRef)
            else ObjectRef(
                object_id=str(wake_ref["object_id"]),
                revision=int(wake_ref["revision"]),
            )
        )
        if ref.revision is None:
            raise ValueError("wake_ref must pin an exact revision")

        exact_payload = self.store.get_payload(
            ref.object_id,
            revision=ref.revision,
        )
        if exact_payload.get("object_type") != "wake":
            raise ValueError("wake_ref must point to a Wake object")

        initial_wake = self.wake_bus.current_wake(ref.object_id)
        initial_attention_class = self.wake_bus.attention_class_for_wake(
            initial_wake
        )
        bundle_excluded_sources = {
            WakeSource.SAFETY,
            WakeSource.PERIODIC_REVIEW,
            WakeSource.USER_INTERACTION,
            WakeSource.ATTENTION_BUNDLE,
        }
        if (
            initial_wake.wake_state.value in {"new", "queued"}
            and initial_wake.wake_source not in bundle_excluded_sources
            and initial_attention_class is AttentionClass.BACKGROUND
        ):
            bundle = self.attention_router.bundle_pending(
                now=now,
                window_seconds=(
                    self.attention_scheduling_policy.background_batch_window_seconds
                ),
                max_wakes=self.attention_scheduling_policy.background_bundle_max_wakes,
                anchor_wake_id=initial_wake.object_id,
            )
            if (
                bundle is not None
                and initial_wake.object_id in bundle.member_wake_ids
            ):
                ref = ObjectRef(
                    object_id=bundle.wake_id,
                    revision=bundle.revision,
                )

        wake = self.wake_bus.current_wake(ref.object_id)
        if wake.wake_source is WakeSource.PERIODIC_REVIEW:
            raise ValueError(
                "PERIODIC_REVIEW Wake must use run_periodic_review so review anchors remain intact"
            )
        if wake.wake_source is WakeSource.USER_INTERACTION:
            raise ValueError(
                "USER_INTERACTION must use run_turn so the user utterance enters the world"
            )

        budget_decision = self.background_budget_gate.evaluate(
            wake,
            now=now,
            max_model_rounds=self.cognitive_runtime.max_tool_rounds + 1,
        )
        effective_step0 = step0 or Step0GateInput()
        if budget_decision.applies:
            effective_step0 = effective_step0.model_copy(
                update={
                    "budget_available": (
                        effective_step0.budget_available
                        and budget_decision.available
                    ),
                    "reasons": tuple(
                        dict.fromkeys(
                            [
                                *effective_step0.reasons,
                                *budget_decision.reasons,
                            ]
                        )
                    ),
                }
            )

        gate_result = self.wake_bus.evaluate_step0(wake, effective_step0)
        if not gate_result.model_allowed:
            if wake.wake_state.value == "running" and not budget_decision.hard_deny:
                terminal = WakeStateReceipt(
                    wake_id=wake.object_id,
                    revision=wake.revision,
                    state=wake.wake_state.value,
                    world_revision=int(self.store.current_world_revision()),
                )
            else:
                terminal = (
                    self.wake_bus.suppress(
                        wake.object_id,
                        suppressed_at=now,
                        step0=gate_result,
                    )
                    if budget_decision.hard_deny
                    else self.wake_bus.defer(
                        wake.object_id,
                        deferred_at=now,
                        step0=gate_result,
                    )
                )
            return WakeDispatchRunResult(
                wake_ref=ObjectRef(
                    object_id=terminal.wake_id,
                    revision=terminal.revision,
                ),
                runtime=None,
                context=None,
                step0=gate_result,
                wake=terminal,
                delivery_response=None,
                delivery_suppressed=True,
            )

        claimed = self.wake_bus.claim(
            wake.object_id,
            started_at=now,
            expected_world_revision=(
                budget_decision.world_revision
                if budget_decision.requires_reservation
                else None
            ),
            metadata_update=budget_decision.reservation_metadata(),
        )
        running = self.wake_bus.current_wake(claimed.wake_id)
        running_ref = ObjectRef(
            object_id=running.object_id,
            revision=running.revision,
        )

        empty_recommendation = RecommendationBundle(
            current_topic=None,
            topic_gate_open=False,
            world_revision=int(self.store.current_world_revision()),
            index_watermark=self.index.watermark(),
            cards=(),
            reason="wake_dispatch_uses_wake_reason_as_first_pointer",
        )
        continuity_context = self.ai_world.core_context(per_domain=3)
        wake_context = {
            "wake_ref": running_ref.model_dump(mode="json"),
            "wake_source": running.wake_source.value,
            "rule_id": running.rule_id,
            "priority": running.priority,
            "attention_class": self.wake_bus.attention_class_for_wake(
                running
            ).value,
            "dedupe_key": running.dedupe_key,
            "first_hit_at": running.first_hit_at.isoformat(),
            "last_hit_at": running.last_hit_at.isoformat(),
            "hit_count": running.hit_count,
            "evidence_refs": [
                item.model_dump(mode="json")
                for item in running.evidence_refs
            ],
            "step0": gate_result.model_dump(mode="json"),
            "budget": budget_decision.context_payload(),
            "evidence_reader": "inspect_world_object",
            "attention_bundle": (
                running.metadata.get("attention_bundle")
                if running.wake_source is WakeSource.ATTENTION_BUNDLE
                else None
            ),
        }
        wake_input = (
            "System Wake. Start from the supplied Wake Reason and pinned evidence. "
            "Decide what, if anything, it means now. Search or inspect more world "
            "state when needed. You may respond, act through authorized capabilities, "
            "or remain silent. The trigger itself is not a semantic conclusion."
        )
        context = self.context_controller.assemble(
            user_input=wake_input,
            current_topic=None,
            recommendation=empty_recommendation,
            recent_turns=(),
            conversation_summaries=(),
            ai_identity=continuity_context,
            world_map=self._world_map_context(now),
            task_context={
                "wake": wake_context,
                "cognitive_policy_context": self._cognitive_policy_context(),
            },
            capability_catalog=self.registry.catalog(),
            token_budget=token_budget,
        )

        self._active_turn_time = now
        self._active_meter_time = now
        self._active_session_id = None
        self._active_wake_id = running.object_id
        self._active_review_request = None
        try:
            runtime_result = self.cognitive_runtime.run_turn(
                wake_input,
                wake_reason=running.wake_source.value,
                cockpit=context.as_cockpit(),
                max_model_rounds=budget_decision.model_round_limit,
            )
        finally:
            self._active_turn_time = None
            self._active_meter_time = None
            self._active_session_id = None
            self._active_wake_id = None
            self._active_review_request = None

        completed = self.wake_bus.complete(
            running.object_id,
            completed_at=now,
            termination_reason=runtime_result.termination_reason,
            model_rounds=runtime_result.model_rounds,
            capability_names=tuple(
                item.name for item in runtime_result.capability_history
            ),
            delivery_allowed=gate_result.delivery_allowed,
            step0_state=gate_result.state,
        )
        delivery_response = (
            runtime_result.response
            if gate_result.delivery_allowed
            else None
        )
        return WakeDispatchRunResult(
            wake_ref=ObjectRef(
                object_id=completed.wake_id,
                revision=completed.revision,
            ),
            runtime=runtime_result,
            context=context,
            step0=gate_result,
            wake=completed,
            delivery_response=delivery_response,
            delivery_suppressed=(
                runtime_result.response is not None
                and not gate_result.delivery_allowed
            ),
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
        self.attention_watches.expire_due(now=now)
        request = self.periodic_review.prepare_due_review(
            now=now,
            policy=policy,
        )
        if request is None:
            return None

        review_wake = self.wake_bus.current_wake(request.wake_ref.object_id)
        budget_decision = self.background_budget_gate.evaluate(
            review_wake,
            now=now,
            max_model_rounds=self.cognitive_runtime.max_tool_rounds + 1,
            require_full_model_round_budget=True,
        )
        if not budget_decision.available:
            if budget_decision.hard_deny:
                budget_wake = self.periodic_review.suppress_review(
                    request,
                    suppressed_at=now,
                    reasons=budget_decision.reasons,
                )
            elif review_wake.wake_state.value == "running":
                budget_wake = ReviewWakeReceipt(
                    wake_id=review_wake.object_id,
                    revision=review_wake.revision,
                    state=review_wake.wake_state.value,
                    world_revision=int(self.store.current_world_revision()),
                )
            else:
                budget_wake = self.periodic_review.defer_review(
                    request,
                    deferred_at=now,
                    reasons=budget_decision.reasons,
                )
            self.index.catch_up()
            return PeriodicReviewRunResult(
                request=request,
                runtime=None,
                context=None,
                wake=budget_wake,
                budget=budget_decision,
            )

        review_queue_wakes = self.attention_router.pending_review_queue()
        anchor_keys = {
            (
                item.object_ref.object_id,
                int(item.object_ref.revision or 0),
            )
            for item in request.anchors
        }
        review_queue_consumed_ids = tuple(
            wake.object_id
            for wake in review_queue_wakes
            if wake.evidence_refs
            and all(
                (ref.object_id, int(ref.revision or 0)) in anchor_keys
                for ref in wake.evidence_refs
            )
        )

        request = self.periodic_review.begin_review(
            request,
            started_at=now,
            expected_world_revision=(
                budget_decision.world_revision
                if budget_decision.requires_reservation
                else None
            ),
            metadata_update=budget_decision.reservation_metadata(),
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
            "review_queue_wake_count": len(review_queue_consumed_ids),
            "budget": budget_decision.context_payload(),
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
            world_map=self._world_map_context(now),
            task_context={
                "periodic_review": review_context,
                "cognitive_policy_context": self._cognitive_policy_context(),
            },
            capability_catalog=self.registry.catalog(),
            token_budget=token_budget,
        )

        running_payload = self.store.get_payload(
            request.wake_ref.object_id,
            revision=request.wake_ref.revision,
        )
        running_metadata = running_payload.get("metadata")
        raw_started_at = (
            running_metadata.get("started_at")
            if isinstance(running_metadata, Mapping)
            else None
        )
        review_write_time = (
            datetime.fromisoformat(str(raw_started_at).replace("Z", "+00:00"))
            if raw_started_at is not None
            else now
        )

        # A resumed RUNNING review keeps its original write time. This makes
        # model-authored writebacks deterministic across crash/budget retries instead
        # of creating a second "same lesson" merely because the worker restarted later.
        self._active_turn_time = review_write_time
        self._active_meter_time = now
        self._active_session_id = None
        self._active_wake_id = request.wake_ref.object_id
        self._active_review_request = request
        try:
            runtime_result = self.cognitive_runtime.run_turn(
                review_input,
                wake_reason="periodic_review",
                cockpit=context.as_cockpit(),
                max_model_rounds=budget_decision.model_round_limit,
            )
        finally:
            self._active_review_request = None
            self._active_turn_time = None
            self._active_meter_time = None
            self._active_session_id = None
            self._active_wake_id = None

        # Tool/capability budget exhaustion is not a completed semantic review.
        # Keep the durable Wake RUNNING so a later worker can resume the exact review.
        if runtime_result.termination_reason not in {"responded", "silence"}:
            self.index.catch_up()
            return PeriodicReviewRunResult(
                request=request,
                runtime=runtime_result,
                context=context,
                wake=ReviewWakeReceipt(
                    wake_id=request.wake_ref.object_id,
                    revision=int(request.wake_ref.revision or 0),
                    state="running",
                    world_revision=int(self.store.current_world_revision()),
                ),
                budget=budget_decision,
            )

        wake = self.periodic_review.complete_review(
            request,
            completed_at=now,
            termination_reason=runtime_result.termination_reason,
            model_rounds=runtime_result.model_rounds,
            capability_names=[
                result.name for result in runtime_result.capability_history
            ],
        )
        self.attention_router.complete_review_queue(
            review_queue_consumed_ids,
            completed_at=now,
        )
        self.index.catch_up()
        return PeriodicReviewRunResult(
            request=request,
            runtime=runtime_result,
            context=context,
            wake=wake,
            budget=budget_decision,
        )
