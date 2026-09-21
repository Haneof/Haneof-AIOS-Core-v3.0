"""Goal / Task / Action / Outcome execution world for AIOS v3.0.

The resident AI may propose and manage internal goals/tasks and may propose an
external Action. It never receives direct authority to perform an external side
effect. A trusted platform layer must authorize a proposed Action, receives a
dispatch envelope, performs the side effect outside Core, and writes the real
Outcome back into the same WorldStore.

All state changes are forward revisions. Nothing is silently deleted.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Literal, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import (
    ActionStatus,
    GoalSourceType,
    GoalStatus,
    ObjectType,
    SourceClass,
    TaskState,
    TaskType,
    WakeSource,
    WakeState,
)
from aios_core.contracts.models import (
    Action,
    Dependency,
    EvidenceCoverage,
    EvidenceSet,
    Goal,
    Outcome,
    Task,
    Wake,
)
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import KnowledgeWindow, TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore


OutcomeState = Literal["completed", "failed", "outcome_unknown"]
CompletionMode = Literal["world_evidence", "action_outcome", "mixed"]
ActionAuthorizer = Callable[[Action, tuple[ObjectRef, ...]], bool]

_COMPLETION_MODES = frozenset({"world_evidence", "action_outcome", "mixed"})
_WORLD_EVIDENCE_TYPES = frozenset(
    {
        ObjectType.OBSERVATION,
        ObjectType.EVIDENCE_SET,
        ObjectType.CLAIM,
        ObjectType.SUMMARY,
        ObjectType.COMMUNICATION_EXPERIENCE,
    }
)
_DEFAULT_WORLD_EVIDENCE_TYPES = frozenset(
    {ObjectType.OBSERVATION, ObjectType.EVIDENCE_SET}
)
_INACTIVE_EVIDENCE_STATUSES = frozenset(
    {
        "retracted",
        "superseded",
        "stale_review_required",
        "stale",
        "archived",
        "rejected",
        "merged",
        "split",
    }
)


_GOAL_TRANSITIONS: Mapping[GoalStatus, frozenset[GoalStatus]] = {
    GoalStatus.PROPOSED: frozenset(
        {GoalStatus.ACTIVE, GoalStatus.ABANDONED, GoalStatus.UNKNOWN}
    ),
    GoalStatus.ACTIVE: frozenset(
        {
            GoalStatus.PAUSED,
            GoalStatus.ACHIEVED,
            GoalStatus.ABANDONED,
            GoalStatus.UNKNOWN,
        }
    ),
    GoalStatus.PAUSED: frozenset(
        {GoalStatus.ACTIVE, GoalStatus.ABANDONED, GoalStatus.UNKNOWN}
    ),
    GoalStatus.UNKNOWN: frozenset(
        {GoalStatus.ACTIVE, GoalStatus.PAUSED, GoalStatus.ABANDONED}
    ),
    GoalStatus.ACHIEVED: frozenset(),
    GoalStatus.ABANDONED: frozenset(),
}

_TASK_TRANSITIONS: Mapping[TaskState, frozenset[TaskState]] = {
    TaskState.DRAFT: frozenset(
        {
            TaskState.READY,
            TaskState.WAITING_TIME,
            TaskState.WAITING_EVIDENCE,
            TaskState.WAITING_USER,
            TaskState.CANCELLED,
        }
    ),
    TaskState.READY: frozenset(
        {
            TaskState.RUNNING,
            TaskState.WAITING_TIME,
            TaskState.WAITING_EVIDENCE,
            TaskState.WAITING_USER,
            TaskState.CANCELLED,
            TaskState.EXPIRED,
        }
    ),
    TaskState.RUNNING: frozenset(
        {
            TaskState.WAITING_TIME,
            TaskState.WAITING_EVIDENCE,
            TaskState.WAITING_USER,
            TaskState.WAITING_RESULT,
            TaskState.BLOCKED,
            TaskState.COMPLETED,
            TaskState.FAILED,
            TaskState.CANCELLED,
        }
    ),
    TaskState.WAITING_TIME: frozenset(
        {TaskState.READY, TaskState.CANCELLED, TaskState.EXPIRED}
    ),
    TaskState.WAITING_EVIDENCE: frozenset(
        {TaskState.READY, TaskState.CANCELLED, TaskState.EXPIRED}
    ),
    TaskState.WAITING_USER: frozenset(
        {TaskState.READY, TaskState.CANCELLED, TaskState.EXPIRED}
    ),
    TaskState.WAITING_RESULT: frozenset(
        {
            TaskState.READY,
            TaskState.COMPLETED,
            TaskState.FAILED,
            TaskState.CANCELLED,
        }
    ),
    TaskState.BLOCKED: frozenset(
        {TaskState.READY, TaskState.FAILED, TaskState.CANCELLED}
    ),
    TaskState.COMPLETED: frozenset(),
    TaskState.FAILED: frozenset(),
    TaskState.EXPIRED: frozenset(),
    TaskState.CANCELLED: frozenset(),
}

_TERMINAL_TASK_STATES = {
    TaskState.COMPLETED,
    TaskState.FAILED,
    TaskState.EXPIRED,
    TaskState.CANCELLED,
}

_TERMINAL_ACTION_STATUSES = {
    ActionStatus.COMPLETED,
    ActionStatus.FAILED,
    ActionStatus.OUTCOME_UNKNOWN,
    ActionStatus.CANCELLED,
}


class GoalCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_type: GoalSourceType
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    success_criteria: tuple[str, ...] = ()
    related_dimension_refs: tuple[ObjectRef, ...] = ()
    related_event_refs: tuple[ObjectRef, ...] = ()
    app_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_request(self) -> "GoalCreateRequest":
        if not self.title.strip() or not self.description.strip():
            raise ValueError("title/description must not be blank")
        for criterion in self.success_criteria:
            if not criterion.strip():
                raise ValueError("success_criteria must not contain blank values")
        _require_pinned(
            (
                *self.evidence_refs,
                *self.related_dimension_refs,
                *self.related_event_refs,
            ),
            "goal references",
        )
        return self


class GoalTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    goal_ref: ObjectRef
    new_status: GoalStatus
    reason: str = Field(min_length=1)
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_request(self) -> "GoalTransitionRequest":
        _require_pinned((self.goal_ref, *self.evidence_refs), "goal transition")
        if not self.reason.strip():
            raise ValueError("reason must not be blank")
        return self


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1)
    task_type: TaskType
    reason_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    goal_ref: ObjectRef | None = None
    initial_state: TaskState = TaskState.DRAFT
    priority: int = Field(default=50, ge=0, le=100)
    next_wake_at: datetime | None = None
    deadline: datetime | None = None
    recurrence: dict[str, Any] | None = None
    timezone_name: str | None = None
    dependency_refs: tuple[ObjectRef, ...] = ()
    next_step: str | None = None
    completion_condition: dict[str, Any] = Field(default_factory=dict)
    cancel_condition: dict[str, Any] = Field(default_factory=dict)
    related_entity_refs: tuple[ObjectRef, ...] = ()
    app_id: str | None = None

    @model_validator(mode="after")
    def validate_request(self) -> "TaskCreateRequest":
        if not self.title.strip():
            raise ValueError("title must not be blank")
        if self.initial_state not in {
            TaskState.DRAFT,
            TaskState.READY,
            TaskState.WAITING_TIME,
            TaskState.WAITING_EVIDENCE,
            TaskState.WAITING_USER,
        }:
            raise ValueError("initial task state is not valid for task creation")
        if self.initial_state is TaskState.WAITING_TIME and self.next_wake_at is None:
            raise ValueError("WAITING_TIME task requires next_wake_at")
        _completion_mode_from_condition(self.completion_condition)
        _completion_result_object_types(self.completion_condition)
        refs: list[ObjectRef] = [
            *self.reason_refs,
            *self.dependency_refs,
            *self.related_entity_refs,
        ]
        if self.goal_ref is not None:
            refs.append(self.goal_ref)
        _require_pinned(refs, "task references")
        return self


class TaskTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_ref: ObjectRef
    new_state: TaskState
    reason: str = Field(min_length=1)
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    execution_refs: tuple[ObjectRef, ...] = ()
    outcome_refs: tuple[ObjectRef, ...] = ()
    next_wake_at: datetime | None = None
    next_step: str | None = None

    @model_validator(mode="after")
    def validate_request(self) -> "TaskTransitionRequest":
        _require_pinned(
            (
                self.task_ref,
                *self.evidence_refs,
                *self.execution_refs,
                *self.outcome_refs,
            ),
            "task transition references",
        )
        if not self.reason.strip():
            raise ValueError("reason must not be blank")
        if self.new_state is TaskState.WAITING_TIME and self.next_wake_at is None:
            raise ValueError("WAITING_TIME transition requires next_wake_at")
        return self


class ActionProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_ref: ObjectRef
    action_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    expected_outcome: str | None = None
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_request(self) -> "ActionProposalRequest":
        _require_pinned(
            (self.task_ref, *self.evidence_refs),
            "action proposal references",
        )
        if not self.action_type.strip():
            raise ValueError("action_type must not be blank")
        return self


class ActionOutcomeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_ref: ObjectRef
    outcome_state: OutcomeState
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: tuple[ObjectRef, ...] = ()

    @model_validator(mode="after")
    def validate_request(self) -> "ActionOutcomeRequest":
        _require_pinned((self.action_ref, *self.evidence_refs), "outcome references")
        return self


@dataclass(frozen=True, slots=True)
class GoalReceipt:
    goal_id: str
    revision: int
    status: str
    world_revision: int


@dataclass(frozen=True, slots=True)
class TaskReceipt:
    task_id: str
    revision: int
    state: str
    world_revision: int


@dataclass(frozen=True, slots=True)
class ActionProposalReceipt:
    action_id: str
    revision: int
    execution_id: str
    world_revision: int


@dataclass(frozen=True, slots=True)
class ActionDispatchEnvelope:
    action_id: str
    revision: int
    execution_id: str
    action_type: str
    payload: dict[str, Any]
    expected_outcome: str | None
    authorization_refs: tuple[ObjectRef, ...]
    authorized_by: str
    world_revision: int


@dataclass(frozen=True, slots=True)
class OutcomeReceipt:
    action_id: str
    action_revision: int
    outcome_id: str
    outcome_state: str
    world_revision: int


@dataclass(frozen=True, slots=True)
class TaskWakeReceipt:
    task_id: str
    previous_revision: int
    new_revision: int
    new_state: str
    wake_id: str
    world_revision: int


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _require_pinned(refs: Sequence[ObjectRef], field_name: str) -> None:
    for ref in refs:
        if ref.revision is None:
            raise ValueError(f"{field_name} must pin exact revisions")


def _source_refs(refs: Sequence[ObjectRef]) -> list[SourceRef]:
    return [
        SourceRef(object_id=ref.object_id, revision=ref.revision)
        for ref in refs
    ]


def _completion_mode_from_condition(
    condition: Mapping[str, Any],
) -> CompletionMode | None:
    raw = condition.get("mode")
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("completion_condition.mode must be a non-blank string")
    mode = raw.strip().lower()
    if mode not in _COMPLETION_MODES:
        raise ValueError(
            "completion_condition.mode must be world_evidence, action_outcome, or mixed"
        )
    return mode  # type: ignore[return-value]


def _completion_result_object_types(
    condition: Mapping[str, Any],
) -> frozenset[ObjectType]:
    raw = condition.get("result_object_types")
    if raw is None:
        return _DEFAULT_WORLD_EVIDENCE_TYPES
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise ValueError(
            "completion_condition.result_object_types must be an array of object types"
        )
    parsed: set[ObjectType] = set()
    for value in raw:
        try:
            object_type = ObjectType(str(value).strip().lower())
        except ValueError as exc:
            raise ValueError(
                f"unsupported completion result object type: {value!r}"
            ) from exc
        if object_type not in _WORLD_EVIDENCE_TYPES:
            raise ValueError(
                "completion result object types are limited to durable non-execution "
                "evidence objects"
            )
        parsed.add(object_type)
    if not parsed:
        raise ValueError(
            "completion_condition.result_object_types must not be empty when supplied"
        )
    return frozenset(parsed)


def _ref_key(ref: ObjectRef) -> tuple[str, int]:
    return (ref.object_id, int(ref.revision or 0))


class GoalTaskActionService:
    """Single-world planning and action-envelope service."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex | None = None,
        subject_id: str = "user_1",
    ) -> None:
        self.store = store
        self.index = index
        self.subject_id = subject_id

    def _validate_refs_exist(self, refs: Sequence[ObjectRef]) -> None:
        for ref in refs:
            payload = self.store.get_payload(ref.object_id, revision=ref.revision)
            ref_subject = str(payload.get("subject_id") or "")
            if ref_subject != self.subject_id:
                raise ValueError(
                    "execution-world reference crosses the runtime subject scope: "
                    f"{ref.object_id}@{ref.revision} belongs to {ref_subject!r}"
                )

    def _current_exact(
        self,
        ref: ObjectRef,
        *,
        object_type: ObjectType,
    ) -> dict[str, Any]:
        payload = self.store.get_payload(ref.object_id, revision=ref.revision)
        if payload.get("object_type") != object_type.value:
            raise ValueError(
                f"{ref.object_id}@{ref.revision} is not {object_type.value}"
            )
        if str(payload.get("subject_id") or "") != self.subject_id:
            raise ValueError(
                f"{object_type.value} reference crosses the runtime subject scope"
            )
        latest = self.store.get_payload(ref.object_id)
        if int(latest["revision"]) != int(ref.revision or 0):
            raise ValueError(
                f"{object_type.value} reference is not current: "
                f"{ref.object_id}@{ref.revision}"
            )
        return payload

    def _evidence_set(
        self,
        *,
        purpose: str,
        refs: Sequence[ObjectRef],
        learned_at: datetime,
        metadata: Mapping[str, Any] | None = None,
    ) -> EvidenceSet:
        evidence_id = _stable_id(
            "evs_exec",
            purpose,
            tuple((ref.object_id, ref.revision) for ref in refs),
            learned_at.isoformat(),
        )
        return EvidenceSet(
            object_id=evidence_id,
            subject_id=self.subject_id,
            learned_at=learned_at,
            recorded_at=learned_at,
            created_by="execution_world:evidence",
            purpose=purpose,
            knowledge_window=KnowledgeWindow(
                knowledge_cutoff=learned_at,
                world_revision=int(self.store.current_world_revision()),
            ),
            member_refs=list(refs),
            support_refs=list(refs),
            selection_method="resident_or_platform_selected_pinned_evidence",
            coverage=EvidenceCoverage(
                expected_count=len(refs),
                observed_count=len(refs),
                coverage_ratio=1.0,
            ),
            metadata=dict(metadata or {}),
        )

    def _evidence_dependencies(
        self,
        *,
        evidence: EvidenceSet,
        refs: Sequence[ObjectRef],
        learned_at: datetime,
        dependency_type: str,
    ) -> list[Dependency]:
        evidence_ref = ObjectRef(object_id=evidence.object_id, revision=1)
        return [
            Dependency(
                object_id=_stable_id(
                    "dep",
                    evidence.object_id,
                    1,
                    ref.object_id,
                    ref.revision,
                ),
                subject_id=self.subject_id,
                learned_at=learned_at,
                recorded_at=learned_at,
                created_by="execution_world:dependency",
                dependent_ref=evidence_ref,
                dependency_ref=ref,
                dependency_type=dependency_type,
            )
            for ref in refs
        ]

    def _catch_up(self) -> None:
        if self.index is not None:
            self.index.catch_up()

    def _current_evidence_payload(self, ref: ObjectRef) -> dict[str, Any]:
        payload = self.store.get_payload(ref.object_id, revision=ref.revision)
        if str(payload.get("subject_id") or "") != self.subject_id:
            raise ValueError(
                "completion evidence crosses the runtime subject scope: "
                f"{ref.object_id}@{ref.revision}"
            )
        latest = self.store.get_payload(ref.object_id)
        if int(latest.get("revision") or 0) != int(ref.revision or 0):
            raise ValueError(
                "completion evidence is not current: "
                f"{ref.object_id}@{ref.revision}"
            )
        status = str(payload.get("status") or "active").strip().lower()
        if status in _INACTIVE_EVIDENCE_STATUSES:
            raise ValueError(
                f"completion evidence is inactive: {ref.object_id}@{ref.revision}"
            )
        return payload

    def _dependency_exists(
        self,
        *,
        dependent_ref: ObjectRef,
        dependency_ref: ObjectRef,
        dependency_type: str,
    ) -> bool:
        for payload in self.store.list_payloads(
            object_type=ObjectType.DEPENDENCY,
            subject_id=self.subject_id,
        ):
            if str(payload.get("dependency_type") or "") != dependency_type:
                continue
            dependent = payload.get("dependent_ref") or {}
            dependency = payload.get("dependency_ref") or {}
            if (
                str(dependent.get("object_id") or "") == dependent_ref.object_id
                and int(dependent.get("revision") or 0)
                == int(dependent_ref.revision or 0)
                and str(dependency.get("object_id") or "") == dependency_ref.object_id
                and int(dependency.get("revision") or 0)
                == int(dependency_ref.revision or 0)
            ):
                return True
        return False

    def _task_has_action_lineage(self, task_id: str) -> bool:
        return any(
            action.task_ref is not None and action.task_ref.object_id == task_id
            for action in self.current_actions()
        )

    def _effective_completion_mode(self, task: Task) -> CompletionMode:
        explicit = _completion_mode_from_condition(task.completion_condition)
        if explicit is not None:
            return explicit
        if (
            task.task_type in {TaskType.VERIFICATION, TaskType.OBSERVATION}
            and not self._task_has_action_lineage(task.object_id)
        ):
            return "world_evidence"
        return "action_outcome"

    def _validate_world_evidence_ref(
        self,
        *,
        task: Task,
        ref: ObjectRef,
        allowed_types: frozenset[ObjectType],
        seen: set[tuple[str, int]] | None = None,
    ) -> dict[str, Any]:
        stack = set() if seen is None else set(seen)
        key = _ref_key(ref)
        if key in stack:
            raise ValueError("completion evidence contains a circular reference")
        stack.add(key)

        payload = self._current_evidence_payload(ref)
        try:
            object_type = ObjectType(str(payload.get("object_type") or ""))
        except ValueError as exc:
            raise ValueError("completion evidence has an invalid object type") from exc
        if object_type not in allowed_types:
            raise ValueError(
                f"{object_type.value} is not permitted by this Task completion contract"
            )

        if object_type is ObjectType.OBSERVATION:
            metadata = payload.get("metadata")
            role = (
                str(metadata.get("role") or "").strip().lower()
                if isinstance(metadata, Mapping)
                else ""
            )
            created_by = str(payload.get("created_by") or "").strip().lower()
            source_kind = str(payload.get("source_kind") or "").strip().lower()
            if (
                role == "assistant"
                or source_kind == "assistant"
                or created_by == "conversation_ingest:assistant"
            ):
                raise ValueError(
                    "assistant raw dialogue cannot be completion evidence"
                )
            return payload

        if object_type is ObjectType.EVIDENCE_SET:
            if bool(payload.get("stale")):
                raise ValueError("stale EvidenceSet cannot complete a Task")
            member_refs = tuple(
                ObjectRef.model_validate(item)
                for item in (payload.get("member_refs") or ())
            )
            if not member_refs:
                raise ValueError(
                    "terminal completion requires a pinned EvidenceSet with concrete members"
                )
            coverage = payload.get("coverage")
            if isinstance(coverage, Mapping):
                expected = coverage.get("expected_count")
                observed = coverage.get("observed_count")
                ratio = coverage.get("coverage_ratio")
                missing = coverage.get("missing_description") or ()
                if (
                    expected is not None
                    and observed is not None
                    and int(observed) < int(expected)
                ):
                    raise ValueError("incomplete EvidenceSet cannot complete a Task")
                if ratio is not None and float(ratio) < 1.0:
                    raise ValueError("partial EvidenceSet cannot complete a Task")
                if missing:
                    raise ValueError(
                        "EvidenceSet with missing coverage cannot complete a Task"
                    )
            nested_allowed = frozenset(
                set(allowed_types)
                | {ObjectType.OBSERVATION, ObjectType.EVIDENCE_SET}
            )
            for member_ref in member_refs:
                self._validate_world_evidence_ref(
                    task=task,
                    ref=member_ref,
                    allowed_types=nested_allowed,
                    seen=stack,
                )
            return payload

        if object_type is ObjectType.CLAIM:
            if object_type not in _completion_result_object_types(
                task.completion_condition
            ):
                raise ValueError(
                    "Claim completion evidence must be explicitly allowed by the Task contract"
                )
            for source in payload.get("source_refs") or ():
                if str(source.get("object_id") or "") == task.object_id:
                    raise ValueError(
                        "Task self-reference cannot ground a completion Claim"
                    )
            support_refs = tuple(
                ObjectRef.model_validate(item)
                for item in (payload.get("support_evidence_set_refs") or ())
            )
            if not support_refs:
                raise ValueError(
                    "unsupported Claim cannot be completion evidence"
                )
            nested_allowed = frozenset(
                set(allowed_types)
                | {ObjectType.OBSERVATION, ObjectType.EVIDENCE_SET}
            )
            for support_ref in support_refs:
                support_payload = self._validate_world_evidence_ref(
                    task=task,
                    ref=support_ref,
                    allowed_types=nested_allowed,
                    seen=stack,
                )
                if support_payload.get("object_type") != ObjectType.EVIDENCE_SET.value:
                    raise ValueError(
                        "Claim support must resolve to current EvidenceSet objects"
                    )
            return payload

        if object_type is ObjectType.SUMMARY:
            if object_type not in _completion_result_object_types(
                task.completion_condition
            ):
                raise ValueError(
                    "Summary completion evidence must be explicitly allowed by the Task contract"
                )
            if str(payload.get("summary_status") or "").strip().lower() != "current":
                raise ValueError("non-current Summary cannot complete a Task")
            evidence_ref_raw = payload.get("evidence_set_ref")
            if not isinstance(evidence_ref_raw, Mapping):
                raise ValueError(
                    "Summary completion evidence requires a pinned EvidenceSet"
                )
            nested_allowed = frozenset(
                set(allowed_types)
                | {ObjectType.OBSERVATION, ObjectType.EVIDENCE_SET}
            )
            support_payload = self._validate_world_evidence_ref(
                task=task,
                ref=ObjectRef.model_validate(evidence_ref_raw),
                allowed_types=nested_allowed,
                seen=stack,
            )
            if support_payload.get("object_type") != ObjectType.EVIDENCE_SET.value:
                raise ValueError(
                    "Summary evidence_set_ref must resolve to an EvidenceSet"
                )
            return payload

        if object_type is ObjectType.COMMUNICATION_EXPERIENCE:
            if object_type not in _completion_result_object_types(
                task.completion_condition
            ):
                raise ValueError(
                    "CommunicationExperience must be explicitly allowed by the Task contract"
                )
            return payload

        raise ValueError(
            f"{object_type.value} is not eligible completion evidence"
        )

    def _validate_real_outcome_ref(
        self,
        *,
        task: Task,
        ref: ObjectRef,
        target: TaskState,
    ) -> Outcome:
        payload = self._current_evidence_payload(ref)
        if payload.get("object_type") != ObjectType.OUTCOME.value:
            raise ValueError("outcome_refs must point to Outcome objects")
        outcome = Outcome.model_validate(payload)
        expected_state = (
            "completed" if target is TaskState.COMPLETED else "failed"
        )
        if outcome.outcome_state != expected_state:
            raise ValueError(
                f"{target.value} Task requires a {expected_state} Outcome"
            )
        if str(outcome.created_by).strip() != "execution_world:platform_result":
            raise ValueError(
                "synthetic Outcome is not a trusted external execution result"
            )

        action_payload = self._current_evidence_payload(outcome.action_ref)
        if action_payload.get("object_type") != ObjectType.ACTION.value:
            raise ValueError("Outcome action_ref must point to an Action")
        action = Action.model_validate(action_payload)
        expected_action_status = (
            ActionStatus.COMPLETED
            if target is TaskState.COMPLETED
            else ActionStatus.FAILED
        )
        if action.action_status is not expected_action_status:
            raise ValueError(
                "Outcome does not match the terminal Action state"
            )
        if (
            action.task_ref is None
            or action.task_ref.object_id != task.object_id
        ):
            raise ValueError("Outcome Action does not belong to this Task")
        parent_payload = self.store.get_payload(
            action.task_ref.object_id,
            revision=action.task_ref.revision,
        )
        if (
            parent_payload.get("object_type") != ObjectType.TASK.value
            or parent_payload.get("task_state") != TaskState.RUNNING.value
        ):
            raise ValueError(
                "Outcome Action is not rooted in a RUNNING Task revision"
            )
        metadata = action.metadata
        if (
            not str(metadata.get("authorized_by") or "").strip()
            or not str(metadata.get("authorized_at") or "").strip()
            or not metadata.get("authorization_refs")
        ):
            raise ValueError(
                "Outcome Action lacks trusted authorization provenance"
            )
        if str(outcome.metadata.get("execution_id") or "") != action.execution_id:
            raise ValueError(
                "Outcome execution provenance does not match its Action"
            )
        if not self._dependency_exists(
            dependent_ref=ObjectRef(
                object_id=outcome.object_id,
                revision=outcome.revision,
            ),
            dependency_ref=outcome.action_ref,
            dependency_type="outcome_reports_action",
        ):
            raise ValueError(
                "Outcome lacks the durable Action-result dependency"
            )
        return outcome

    def _terminal_transition_key(
        self,
        request: TaskTransitionRequest,
        *,
        mode: CompletionMode,
    ) -> str:
        return _stable_id(
            "task_terminal",
            request.task_ref.object_id,
            request.task_ref.revision,
            request.new_state.value,
            request.reason.strip(),
            mode,
            tuple(_ref_key(ref) for ref in request.evidence_refs),
            tuple(_ref_key(ref) for ref in request.execution_refs),
            tuple(_ref_key(ref) for ref in request.outcome_refs),
        )

    def _terminal_retry_receipt(
        self,
        request: TaskTransitionRequest,
    ) -> TaskReceipt | None:
        if request.new_state not in {TaskState.COMPLETED, TaskState.FAILED}:
            return None
        exact = self.store.get_payload(
            request.task_ref.object_id,
            revision=request.task_ref.revision,
        )
        if exact.get("object_type") != ObjectType.TASK.value:
            return None
        latest_payload = self.store.get_payload(request.task_ref.object_id)
        if str(latest_payload.get("subject_id") or "") != self.subject_id:
            raise ValueError("Task reference crosses the runtime subject scope")
        if int(latest_payload.get("revision") or 0) == int(
            request.task_ref.revision or 0
        ):
            return None
        latest = Task.model_validate(latest_payload)
        if (
            int(latest.revision) != int(request.task_ref.revision or 0) + 1
            or latest.task_state is not request.new_state
        ):
            return None
        mode_raw = latest.metadata.get("terminal_completion_mode")
        key_raw = latest.metadata.get("terminal_transition_key")
        if not isinstance(mode_raw, str) or not isinstance(key_raw, str):
            return None
        mode = mode_raw.strip().lower()
        if mode not in _COMPLETION_MODES:
            return None
        if key_raw != self._terminal_transition_key(
            request,
            mode=mode,  # type: ignore[arg-type]
        ):
            return None
        return TaskReceipt(
            task_id=latest.object_id,
            revision=latest.revision,
            state=latest.task_state.value,
            world_revision=int(self.store.current_world_revision()),
        )

    def _validate_terminal_transition(
        self,
        *,
        task: Task,
        request: TaskTransitionRequest,
        target: TaskState,
    ) -> CompletionMode:
        mode = self._effective_completion_mode(task)
        action_lineage = self._task_has_action_lineage(task.object_id)
        if mode == "world_evidence":
            if action_lineage or request.execution_refs or request.outcome_refs:
                raise ValueError(
                    "WORLD_EVIDENCE Task cannot bypass or absorb an Action/Outcome lineage; "
                    "use ACTION_OUTCOME or MIXED"
                )
            allowed = _completion_result_object_types(task.completion_condition)
            if not request.evidence_refs:
                raise ValueError(
                    "WORLD_EVIDENCE terminal transition requires evidence_refs"
                )
            for ref in request.evidence_refs:
                self._validate_world_evidence_ref(
                    task=task,
                    ref=ref,
                    allowed_types=allowed,
                )
            return mode

        if not request.outcome_refs:
            raise ValueError(
                f"{mode.upper()} terminal transition requires real outcome_refs"
            )
        for ref in request.outcome_refs:
            self._validate_real_outcome_ref(
                task=task,
                ref=ref,
                target=target,
            )

        if mode == "mixed":
            outcome_keys = {_ref_key(ref) for ref in request.outcome_refs}
            world_refs = tuple(
                ref
                for ref in request.evidence_refs
                if _ref_key(ref) not in outcome_keys
            )
            if not world_refs:
                raise ValueError(
                    "MIXED terminal transition requires independent WORLD_EVIDENCE refs"
                )
            allowed = _completion_result_object_types(task.completion_condition)
            for ref in world_refs:
                self._validate_world_evidence_ref(
                    task=task,
                    ref=ref,
                    allowed_types=allowed,
                )
        return mode

    def _require_action_parent_eligible(self, action: Action) -> Task:
        if action.task_ref is None:
            raise ValueError("external Action requires a parent Task")
        payload = self.store.get_payload(action.task_ref.object_id)
        if payload.get("object_type") != ObjectType.TASK.value:
            raise ValueError("Action parent reference is not a Task")
        if str(payload.get("subject_id") or "") != self.subject_id:
            raise ValueError("Action parent Task crosses the runtime subject scope")
        task = Task.model_validate(payload)
        if (
            int(task.revision) != int(action.task_ref.revision or 0)
            or task.task_state is not TaskState.RUNNING
        ):
            raise ValueError(
                "Action parent Task is no longer the current RUNNING revision"
            )
        return task

    def current_goals(self) -> tuple[Goal, ...]:
        return tuple(
            Goal.model_validate(payload)
            for payload in self.store.list_payloads(
                object_type=ObjectType.GOAL,
                subject_id=self.subject_id,
            )
        )

    def current_tasks(self) -> tuple[Task, ...]:
        return tuple(
            Task.model_validate(payload)
            for payload in self.store.list_payloads(
                object_type=ObjectType.TASK,
                subject_id=self.subject_id,
            )
        )

    def current_actions(self) -> tuple[Action, ...]:
        return tuple(
            Action.model_validate(payload)
            for payload in self.store.list_payloads(
                object_type=ObjectType.ACTION,
                subject_id=self.subject_id,
            )
        )

    def create_goal(
        self,
        request: GoalCreateRequest,
        *,
        created_at: datetime,
    ) -> GoalReceipt:
        created = as_utc(created_at, "created_at")
        all_refs = (
            *request.evidence_refs,
            *request.related_dimension_refs,
            *request.related_event_refs,
        )
        self._validate_refs_exist(all_refs)

        goal_id = _stable_id(
            "goal",
            self.subject_id,
            request.source_type.value,
            request.title.strip(),
            request.description.strip(),
            tuple((r.object_id, r.revision) for r in request.evidence_refs),
            created.isoformat(),
        )
        evidence = self._evidence_set(
            purpose=f"support goal proposal {goal_id}",
            refs=request.evidence_refs,
            learned_at=created,
            metadata={"goal_id": goal_id},
        )
        evidence_ref = ObjectRef(object_id=evidence.object_id, revision=1)
        goal = Goal(
            object_id=goal_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(created),
            learned_at=created,
            recorded_at=created,
            source_refs=_source_refs(request.evidence_refs),
            created_by="execution_world:resident_ai",
            owner_id=self.subject_id,
            source_type=request.source_type,
            title=request.title.strip(),
            description=request.description.strip(),
            goal_status=GoalStatus.PROPOSED,
            success_criteria=[x.strip() for x in request.success_criteria],
            related_dimension_refs=list(request.related_dimension_refs),
            related_event_refs=list(request.related_event_refs),
            app_ids=[x for x in request.app_ids if x.strip()],
            confidence=request.confidence,
            metadata={
                "proposal_evidence_set_ref": {
                    "object_id": evidence.object_id,
                    "revision": 1,
                }
            },
        )
        goal_ref = ObjectRef(object_id=goal_id, revision=1)
        dependencies = [
            Dependency(
                object_id=_stable_id(
                    "dep", goal_id, 1, evidence.object_id, 1
                ),
                subject_id=self.subject_id,
                learned_at=created,
                recorded_at=created,
                created_by="execution_world:dependency",
                dependent_ref=goal_ref,
                dependency_ref=evidence_ref,
                dependency_type="goal_uses_evidence_set",
            ),
            *self._evidence_dependencies(
                evidence=evidence,
                refs=request.evidence_refs,
                learned_at=created,
                dependency_type="goal_evidence_set_contains_source",
            ),
        ]

        current = int(self.store.current_world_revision())
        result = self.store.commit(
            [evidence, goal, *dependencies],
            OperationRequest(
                operation_name="execution.goal.propose",
                arguments={"goal_id": goal_id, "title": goal.title},
                expected_world_revision=current,
                reason="create evidence-grounded goal proposal",
                idempotency_key=f"goal-propose:{goal_id}:1",
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        self._catch_up()
        return GoalReceipt(
            goal_id=goal_id,
            revision=1,
            status=goal.goal_status.value,
            world_revision=result.world_revision,
        )

    def transition_goal(
        self,
        request: GoalTransitionRequest,
        *,
        changed_at: datetime,
    ) -> GoalReceipt:
        changed = as_utc(changed_at, "changed_at")
        current_payload = self._current_exact(
            request.goal_ref,
            object_type=ObjectType.GOAL,
        )
        current = Goal.model_validate(current_payload)
        target = GoalStatus(request.new_status)
        if target not in _GOAL_TRANSITIONS[current.goal_status]:
            raise ValueError(
                f"illegal goal transition: {current.goal_status.value} -> {target.value}"
            )
        self._validate_refs_exist(request.evidence_refs)
        evidence = self._evidence_set(
            purpose=(
                f"support goal transition {current.object_id}: "
                f"{current.goal_status.value}->{target.value}"
            ),
            refs=request.evidence_refs,
            learned_at=changed,
            metadata={"goal_id": current.object_id},
        )
        evidence_ref = ObjectRef(object_id=evidence.object_id, revision=1)

        metadata = dict(current.metadata)
        history = list(metadata.get("goal_status_history") or [])
        history.append(
            {
                "from": current.goal_status.value,
                "to": target.value,
                "reason": request.reason.strip(),
                "changed_at": changed.isoformat(),
                "evidence_set_ref": {
                    "object_id": evidence.object_id,
                    "revision": 1,
                },
            }
        )
        metadata["goal_status_history"] = history
        new_revision = int(current.revision) + 1
        new_goal = Goal.model_validate(
            {
                **current.model_dump(mode="python", round_trip=True),
                "revision": new_revision,
                "occurred": TemporalExtent.point(changed),
                "learned_at": changed,
                "recorded_at": changed,
                "source_refs": _source_refs(request.evidence_refs),
                "goal_status": target,
                "status": (
                    target.value
                    if target in {GoalStatus.ACHIEVED, GoalStatus.ABANDONED}
                    else "active"
                ),
                "metadata": metadata,
            }
        )
        new_ref = ObjectRef(object_id=new_goal.object_id, revision=new_revision)
        dependencies = [
            Dependency(
                object_id=_stable_id(
                    "dep",
                    new_goal.object_id,
                    new_revision,
                    evidence.object_id,
                    1,
                ),
                subject_id=self.subject_id,
                learned_at=changed,
                recorded_at=changed,
                created_by="execution_world:dependency",
                dependent_ref=new_ref,
                dependency_ref=evidence_ref,
                dependency_type="goal_transition_uses_evidence_set",
            ),
            *self._evidence_dependencies(
                evidence=evidence,
                refs=request.evidence_refs,
                learned_at=changed,
                dependency_type="goal_transition_evidence_contains_source",
            ),
        ]
        result = self.store.commit(
            [evidence, new_goal, *dependencies],
            OperationRequest(
                operation_name="execution.goal.transition",
                arguments={
                    "goal_id": current.object_id,
                    "from": current.goal_status.value,
                    "to": target.value,
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason=request.reason.strip(),
                idempotency_key=(
                    f"goal-transition:{current.object_id}:{new_revision}:{target.value}"
                ),
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        self._catch_up()
        return GoalReceipt(
            goal_id=new_goal.object_id,
            revision=new_revision,
            status=target.value,
            world_revision=result.world_revision,
        )

    def create_task(
        self,
        request: TaskCreateRequest,
        *,
        created_at: datetime,
    ) -> TaskReceipt:
        created = as_utc(created_at, "created_at")
        refs: list[ObjectRef] = [
            *request.reason_refs,
            *request.dependency_refs,
            *request.related_entity_refs,
        ]
        if request.goal_ref is not None:
            goal_payload = self._current_exact(
                request.goal_ref,
                object_type=ObjectType.GOAL,
            )
            goal = Goal.model_validate(goal_payload)
            if goal.goal_status in {GoalStatus.ACHIEVED, GoalStatus.ABANDONED}:
                raise ValueError("cannot create a task under a terminal Goal")
            refs.append(request.goal_ref)
        self._validate_refs_exist(refs)

        task_id = _stable_id(
            "task",
            self.subject_id,
            request.title.strip(),
            request.task_type.value,
            (
                None
                if request.goal_ref is None
                else (request.goal_ref.object_id, request.goal_ref.revision)
            ),
            tuple((r.object_id, r.revision) for r in request.reason_refs),
            created.isoformat(),
        )
        task = Task(
            object_id=task_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(created),
            learned_at=created,
            recorded_at=created,
            source_refs=_source_refs(request.reason_refs),
            created_by="execution_world:resident_ai",
            task_type=request.task_type,
            task_state=request.initial_state,
            goal_ref=request.goal_ref,
            title=request.title.strip(),
            reason_refs=list(request.reason_refs),
            priority=request.priority,
            next_wake_at=request.next_wake_at,
            deadline=request.deadline,
            recurrence=request.recurrence,
            timezone_name=request.timezone_name,
            dependency_refs=list(request.dependency_refs),
            next_step=(
                request.next_step.strip()
                if request.next_step is not None and request.next_step.strip()
                else None
            ),
            completion_condition={
                **dict(request.completion_condition),
                **(
                    {}
                    if _completion_mode_from_condition(
                        request.completion_condition
                    )
                    is None
                    else {
                        "mode": _completion_mode_from_condition(
                            request.completion_condition
                        )
                    }
                ),
                **(
                    {}
                    if "result_object_types"
                    not in request.completion_condition
                    else {
                        "result_object_types": [
                            item.value
                            for item in sorted(
                                _completion_result_object_types(
                                    request.completion_condition
                                ),
                                key=lambda value: value.value,
                            )
                        ]
                    }
                ),
            },
            cancel_condition=dict(request.cancel_condition),
            related_entity_refs=list(request.related_entity_refs),
            app_id=request.app_id,
            metadata={"task_origin": "resident_ai"},
        )
        task_ref = ObjectRef(object_id=task_id, revision=1)
        dependencies: list[Dependency] = []
        for ref in refs:
            dependencies.append(
                Dependency(
                    object_id=_stable_id(
                        "dep", task_id, 1, ref.object_id, ref.revision
                    ),
                    subject_id=self.subject_id,
                    learned_at=created,
                    recorded_at=created,
                    created_by="execution_world:dependency",
                    dependent_ref=task_ref,
                    dependency_ref=ref,
                    dependency_type=(
                        "task_implements_goal"
                        if request.goal_ref is not None
                        and ref == request.goal_ref
                        else "task_uses_reason_or_dependency"
                    ),
                )
            )

        result = self.store.commit(
            [task, *dependencies],
            OperationRequest(
                operation_name="execution.task.create",
                arguments={
                    "task_id": task_id,
                    "title": task.title,
                    "initial_state": task.task_state.value,
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason="create evidence-grounded task",
                idempotency_key=f"task-create:{task_id}:1",
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        self._catch_up()
        return TaskReceipt(
            task_id=task_id,
            revision=1,
            state=task.task_state.value,
            world_revision=result.world_revision,
        )

    def transition_task(
        self,
        request: TaskTransitionRequest,
        *,
        changed_at: datetime,
    ) -> TaskReceipt:
        changed = as_utc(changed_at, "changed_at")
        retry_receipt = self._terminal_retry_receipt(request)
        if retry_receipt is not None:
            return retry_receipt
        payload = self._current_exact(
            request.task_ref,
            object_type=ObjectType.TASK,
        )
        current = Task.model_validate(payload)
        target = TaskState(request.new_state)
        if target not in _TASK_TRANSITIONS[current.task_state]:
            raise ValueError(
                f"illegal task transition: {current.task_state.value} -> {target.value}"
            )
        refs = tuple(
            {
                (ref.object_id, int(ref.revision or 0)): ref
                for ref in (
                    *request.evidence_refs,
                    *request.execution_refs,
                    *request.outcome_refs,
                )
            }.values()
        )
        self._validate_refs_exist(refs)
        for ref in request.execution_refs:
            if self.store.get_payload(ref.object_id, revision=ref.revision).get(
                "object_type"
            ) != ObjectType.ACTION.value:
                raise ValueError("execution_refs must point to Action objects")
        for ref in request.outcome_refs:
            if self.store.get_payload(ref.object_id, revision=ref.revision).get(
                "object_type"
            ) != ObjectType.OUTCOME.value:
                raise ValueError("outcome_refs must point to Outcome objects")

        terminal_mode: CompletionMode | None = None
        if target in {TaskState.COMPLETED, TaskState.FAILED}:
            terminal_mode = self._validate_terminal_transition(
                task=current,
                request=request,
                target=target,
            )

        metadata = dict(current.metadata)
        history = list(metadata.get("task_state_history") or [])
        history.append(
            {
                "from": current.task_state.value,
                "to": target.value,
                "reason": request.reason.strip(),
                "changed_at": changed.isoformat(),
            }
        )
        if terminal_mode is not None:
            transition_key = self._terminal_transition_key(
                request,
                mode=terminal_mode,
            )
            history[-1].update(
                {
                    "completion_mode": terminal_mode,
                    "evidence_refs": [
                        {
                            "object_id": ref.object_id,
                            "revision": ref.revision,
                        }
                        for ref in request.evidence_refs
                    ],
                    "execution_refs": [
                        {
                            "object_id": ref.object_id,
                            "revision": ref.revision,
                        }
                        for ref in request.execution_refs
                    ],
                    "outcome_refs": [
                        {
                            "object_id": ref.object_id,
                            "revision": ref.revision,
                        }
                        for ref in request.outcome_refs
                    ],
                    "terminal_transition_key": transition_key,
                }
            )
            metadata["terminal_completion_mode"] = terminal_mode
            metadata["terminal_transition_key"] = transition_key
        metadata["task_state_history"] = history

        new_revision = int(current.revision) + 1
        execution_refs = list(current.execution_refs)
        for ref in request.execution_refs:
            if ref not in execution_refs:
                execution_refs.append(ref)
        outcome_refs = list(current.outcome_refs)
        for ref in request.outcome_refs:
            if ref not in outcome_refs:
                outcome_refs.append(ref)

        new_task = Task.model_validate(
            {
                **current.model_dump(mode="python", round_trip=True),
                "revision": new_revision,
                "occurred": TemporalExtent.point(changed),
                "learned_at": changed,
                "recorded_at": changed,
                "source_refs": _source_refs(request.evidence_refs),
                "task_state": target,
                "next_wake_at": (
                    request.next_wake_at
                    if target is TaskState.WAITING_TIME
                    else (
                        None
                        if current.task_state is TaskState.WAITING_TIME
                        and target is TaskState.READY
                        else current.next_wake_at
                    )
                ),
                "next_step": (
                    request.next_step.strip()
                    if request.next_step is not None and request.next_step.strip()
                    else current.next_step
                ),
                "attempts": (
                    current.attempts + 1
                    if target is TaskState.RUNNING
                    else current.attempts
                ),
                "execution_refs": execution_refs,
                "outcome_refs": outcome_refs,
                "status": (
                    target.value if target in _TERMINAL_TASK_STATES else "active"
                ),
                "metadata": metadata,
            }
        )
        new_ref = ObjectRef(object_id=new_task.object_id, revision=new_revision)
        evidence_keys = {_ref_key(ref) for ref in request.evidence_refs}
        execution_keys = {_ref_key(ref) for ref in request.execution_refs}
        outcome_keys = {_ref_key(ref) for ref in request.outcome_refs}
        dependencies = []
        for ref in refs:
            ref_key = _ref_key(ref)
            if terminal_mode is not None and ref_key in outcome_keys:
                dependency_type = "task_terminal_uses_outcome"
            elif terminal_mode is not None and ref_key in execution_keys:
                dependency_type = "task_terminal_uses_execution"
            elif terminal_mode is not None and ref_key in evidence_keys:
                dependency_type = "task_terminal_uses_world_evidence"
            else:
                dependency_type = "task_transition_uses_evidence"
            dependencies.append(
                Dependency(
                    object_id=_stable_id(
                        "dep",
                        new_task.object_id,
                        new_revision,
                        ref.object_id,
                        ref.revision,
                    ),
                    subject_id=self.subject_id,
                    learned_at=changed,
                    recorded_at=changed,
                    created_by="execution_world:dependency",
                    dependent_ref=new_ref,
                    dependency_ref=ref,
                    dependency_type=dependency_type,
                )
            )

        invalidated_actions: list[Action] = []
        if target is TaskState.CANCELLED:
            for action in self.current_actions():
                if action.action_status is not ActionStatus.PROPOSED:
                    continue
                if (
                    action.task_ref is None
                    or action.task_ref.object_id != current.object_id
                ):
                    continue
                action_revision = int(action.revision) + 1
                action_metadata = dict(action.metadata)
                action_metadata.update(
                    {
                        "invalidated_by_parent_task": {
                            "object_id": new_task.object_id,
                            "revision": new_revision,
                        },
                        "invalidation_reason": "parent_task_cancelled",
                        "invalidated_at": changed.isoformat(),
                    }
                )
                invalidated = Action.model_validate(
                    {
                        **action.model_dump(mode="python", round_trip=True),
                        "revision": action_revision,
                        "occurred": TemporalExtent.point(changed),
                        "learned_at": changed,
                        "recorded_at": changed,
                        "source_refs": _source_refs(request.evidence_refs),
                        "action_status": ActionStatus.CANCELLED,
                        "status": ActionStatus.CANCELLED.value,
                        "metadata": action_metadata,
                    }
                )
                invalidated_ref = ObjectRef(
                    object_id=invalidated.object_id,
                    revision=action_revision,
                )
                invalidated_actions.append(invalidated)
                dependencies.append(
                    Dependency(
                        object_id=_stable_id(
                            "dep",
                            invalidated.object_id,
                            action_revision,
                            new_task.object_id,
                            new_revision,
                        ),
                        subject_id=self.subject_id,
                        learned_at=changed,
                        recorded_at=changed,
                        created_by="execution_world:dependency",
                        dependent_ref=invalidated_ref,
                        dependency_ref=new_ref,
                        dependency_type="action_invalidated_by_task_cancellation",
                    )
                )

        result = self.store.commit(
            [new_task, *invalidated_actions, *dependencies],
            OperationRequest(
                operation_name="execution.task.transition",
                arguments={
                    "task_id": current.object_id,
                    "from": current.task_state.value,
                    "to": target.value,
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason=request.reason.strip(),
                idempotency_key=(
                    f"task-transition:{current.object_id}:{new_revision}:{target.value}"
                ),
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        self._catch_up()
        return TaskReceipt(
            task_id=new_task.object_id,
            revision=new_revision,
            state=target.value,
            world_revision=result.world_revision,
        )

    def wake_due_tasks(
        self,
        *,
        now: datetime,
    ) -> tuple[TaskWakeReceipt, ...]:
        current_time = as_utc(now, "now")
        receipts: list[TaskWakeReceipt] = []
        for task in self.current_tasks():
            if task.task_state is not TaskState.WAITING_TIME:
                continue
            if task.next_wake_at is None:
                continue
            if as_utc(task.next_wake_at, "next_wake_at") > current_time:
                continue

            task_ref = ObjectRef(object_id=task.object_id, revision=task.revision)
            target = (
                TaskState.EXPIRED
                if task.deadline is not None
                and as_utc(task.deadline, "deadline") < current_time
                else TaskState.READY
            )
            wake_id = _stable_id(
                "wake",
                task.object_id,
                task.revision,
                task.next_wake_at.isoformat(),
            )
            wake = Wake(
                object_id=wake_id,
                subject_id=self.subject_id,
                occurred=TemporalExtent.point(current_time),
                learned_at=current_time,
                recorded_at=current_time,
                source_refs=[
                    SourceRef(
                        object_id=task.object_id,
                        revision=task.revision,
                    )
                ],
                created_by="execution_world:scheduler",
                wake_source=WakeSource.TASK_DUE,
                wake_state=WakeState.NEW,
                rule_id="task.next_wake_at",
                first_hit_at=current_time,
                last_hit_at=current_time,
                evidence_refs=[task_ref],
                priority=task.priority,
                dedupe_key=(
                    f"task_due:{task.object_id}:{task.revision}:"
                    f"{task.next_wake_at.isoformat()}"
                ),
            )
            wake_ref = ObjectRef(object_id=wake_id, revision=1)

            metadata = dict(task.metadata)
            metadata["last_wake_ref"] = {
                "object_id": wake_id,
                "revision": 1,
            }
            new_revision = int(task.revision) + 1
            new_task = Task.model_validate(
                {
                    **task.model_dump(mode="python", round_trip=True),
                    "revision": new_revision,
                    "occurred": TemporalExtent.point(current_time),
                    "learned_at": current_time,
                    "recorded_at": current_time,
                    "task_state": target,
                    "next_wake_at": None,
                    "status": (
                        target.value
                        if target in _TERMINAL_TASK_STATES
                        else "active"
                    ),
                    "metadata": metadata,
                }
            )
            new_task_ref = ObjectRef(
                object_id=new_task.object_id,
                revision=new_revision,
            )
            dependencies = [
                Dependency(
                    object_id=_stable_id(
                        "dep",
                        new_task.object_id,
                        new_revision,
                        wake_id,
                        1,
                    ),
                    subject_id=self.subject_id,
                    learned_at=current_time,
                    recorded_at=current_time,
                    created_by="execution_world:scheduler",
                    dependent_ref=new_task_ref,
                    dependency_ref=wake_ref,
                    dependency_type="task_woken_by",
                ),
                Dependency(
                    object_id=_stable_id(
                        "dep",
                        wake_id,
                        1,
                        task.object_id,
                        task.revision,
                    ),
                    subject_id=self.subject_id,
                    learned_at=current_time,
                    recorded_at=current_time,
                    created_by="execution_world:scheduler",
                    dependent_ref=wake_ref,
                    dependency_ref=task_ref,
                    dependency_type="wake_due_to_task_schedule",
                ),
            ]
            result = self.store.commit(
                [wake, new_task, *dependencies],
                OperationRequest(
                    operation_name="execution.task.wake_due",
                    arguments={
                        "task_id": task.object_id,
                        "target_state": target.value,
                    },
                    expected_world_revision=int(
                        self.store.current_world_revision()
                    ),
                    reason="deterministic task schedule reached",
                    idempotency_key=f"task-wake:{wake_id}",
                    source_class=SourceClass.AI_COGNITION,
                ),
            )
            receipts.append(
                TaskWakeReceipt(
                    task_id=task.object_id,
                    previous_revision=task.revision,
                    new_revision=new_revision,
                    new_state=target.value,
                    wake_id=wake_id,
                    world_revision=result.world_revision,
                )
            )
        self._catch_up()
        return tuple(receipts)

    def propose_action(
        self,
        request: ActionProposalRequest,
        *,
        proposed_at: datetime,
    ) -> ActionProposalReceipt:
        proposed = as_utc(proposed_at, "proposed_at")
        task_payload = self._current_exact(
            request.task_ref,
            object_type=ObjectType.TASK,
        )
        task = Task.model_validate(task_payload)
        if task.task_state is not TaskState.RUNNING:
            raise ValueError("external Action may only be proposed for a RUNNING Task")
        if self._effective_completion_mode(task) == "world_evidence":
            raise ValueError(
                "WORLD_EVIDENCE Task cannot propose an external Action; "
                "use ACTION_OUTCOME or MIXED completion mode"
            )
        self._validate_refs_exist(request.evidence_refs)

        action_id = _stable_id(
            "action",
            request.task_ref.object_id,
            request.task_ref.revision,
            request.action_type.strip(),
            request.payload,
            proposed.isoformat(),
        )
        execution_id = _stable_id("exec", action_id)
        evidence = self._evidence_set(
            purpose=f"support Action proposal {action_id}",
            refs=request.evidence_refs,
            learned_at=proposed,
            metadata={"action_id": action_id},
        )
        evidence_ref = ObjectRef(object_id=evidence.object_id, revision=1)
        action = Action(
            object_id=action_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(proposed),
            learned_at=proposed,
            recorded_at=proposed,
            source_refs=_source_refs(request.evidence_refs),
            created_by="execution_world:resident_ai",
            execution_id=execution_id,
            action_type=request.action_type.strip(),
            action_status=ActionStatus.PROPOSED,
            task_ref=request.task_ref,
            payload=dict(request.payload),
            expected_outcome=(
                request.expected_outcome.strip()
                if request.expected_outcome
                and request.expected_outcome.strip()
                else None
            ),
            metadata={
                "authorization_required": True,
                "proposal_evidence_set_ref": {
                    "object_id": evidence.object_id,
                    "revision": 1,
                },
            },
        )
        action_ref = ObjectRef(object_id=action_id, revision=1)
        dependencies = [
            Dependency(
                object_id=_stable_id(
                    "dep",
                    action_id,
                    1,
                    request.task_ref.object_id,
                    request.task_ref.revision,
                ),
                subject_id=self.subject_id,
                learned_at=proposed,
                recorded_at=proposed,
                created_by="execution_world:dependency",
                dependent_ref=action_ref,
                dependency_ref=request.task_ref,
                dependency_type="action_implements_task",
            ),
            Dependency(
                object_id=_stable_id(
                    "dep", action_id, 1, evidence.object_id, 1
                ),
                subject_id=self.subject_id,
                learned_at=proposed,
                recorded_at=proposed,
                created_by="execution_world:dependency",
                dependent_ref=action_ref,
                dependency_ref=evidence_ref,
                dependency_type="action_uses_evidence_set",
            ),
            *self._evidence_dependencies(
                evidence=evidence,
                refs=request.evidence_refs,
                learned_at=proposed,
                dependency_type="action_evidence_set_contains_source",
            ),
        ]
        result = self.store.commit(
            [evidence, action, *dependencies],
            OperationRequest(
                operation_name="execution.action.propose",
                arguments={
                    "action_id": action_id,
                    "action_type": action.action_type,
                    "task_id": request.task_ref.object_id,
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason="resident AI proposed external side effect",
                idempotency_key=f"action-propose:{action_id}:1",
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        self._catch_up()
        return ActionProposalReceipt(
            action_id=action_id,
            revision=1,
            execution_id=execution_id,
            world_revision=result.world_revision,
        )

    def authorize_action(
        self,
        *,
        action_ref: ObjectRef,
        authorization_refs: Sequence[ObjectRef],
        authorized_by: str,
        authorized_at: datetime,
        authorizer: ActionAuthorizer,
    ) -> ActionDispatchEnvelope:
        authorized = as_utc(authorized_at, "authorized_at")
        _require_pinned((action_ref, *authorization_refs), "authorization references")
        if not authorization_refs:
            raise ValueError("external Action authorization requires authorization_refs")
        if not authorized_by.strip():
            raise ValueError("authorized_by must not be blank")

        payload = self._current_exact(
            action_ref,
            object_type=ObjectType.ACTION,
        )
        action = Action.model_validate(payload)
        if action.action_status is not ActionStatus.PROPOSED:
            raise ValueError("only a PROPOSED Action may be authorized")
        self._require_action_parent_eligible(action)
        self._validate_refs_exist(authorization_refs)

        refs = tuple(authorization_refs)
        if not bool(authorizer(action, refs)):
            raise PermissionError("external Action authorization denied")

        # Freeze the optimistic-concurrency boundary before the final
        # eligibility revalidation. Any Task/Action/world write that races
        # after this point makes the commit fail closed with VERSION_CONFLICT.
        expected_world_revision = int(self.store.current_world_revision())
        payload = self._current_exact(
            action_ref,
            object_type=ObjectType.ACTION,
        )
        action = Action.model_validate(payload)
        if action.action_status is not ActionStatus.PROPOSED:
            raise ValueError("only a PROPOSED Action may be authorized")
        self._require_action_parent_eligible(action)

        new_revision = int(action.revision) + 1
        metadata = dict(action.metadata)
        metadata.update(
            {
                "authorized_by": authorized_by.strip(),
                "authorized_at": authorized.isoformat(),
                "authorization_refs": [
                    {
                        "object_id": ref.object_id,
                        "revision": ref.revision,
                    }
                    for ref in refs
                ],
            }
        )
        submitted = Action.model_validate(
            {
                **action.model_dump(mode="python", round_trip=True),
                "revision": new_revision,
                "occurred": TemporalExtent.point(authorized),
                "learned_at": authorized,
                "recorded_at": authorized,
                "source_refs": _source_refs(refs),
                "action_status": ActionStatus.SUBMITTED,
                "metadata": metadata,
            }
        )
        submitted_ref = ObjectRef(
            object_id=submitted.object_id,
            revision=new_revision,
        )
        dependencies = [
            Dependency(
                object_id=_stable_id(
                    "dep",
                    submitted.object_id,
                    new_revision,
                    ref.object_id,
                    ref.revision,
                ),
                subject_id=self.subject_id,
                learned_at=authorized,
                recorded_at=authorized,
                created_by="execution_world:authorization",
                dependent_ref=submitted_ref,
                dependency_ref=ref,
                dependency_type="action_authorized_by",
            )
            for ref in refs
        ]

        result = self.store.commit(
            [submitted, *dependencies],
            OperationRequest(
                operation_name="execution.action.authorize",
                arguments={
                    "action_id": submitted.object_id,
                    "execution_id": submitted.execution_id,
                    "authorized_by": authorized_by.strip(),
                },
                expected_world_revision=expected_world_revision,
                reason="trusted platform authorization accepted external Action",
                idempotency_key=(
                    f"action-authorize:{submitted.object_id}:{new_revision}"
                ),
                source_class=SourceClass.PLATFORM,
            ),
        )
        self._catch_up()
        return ActionDispatchEnvelope(
            action_id=submitted.object_id,
            revision=new_revision,
            execution_id=submitted.execution_id,
            action_type=submitted.action_type,
            payload=dict(submitted.payload),
            expected_outcome=submitted.expected_outcome,
            authorization_refs=refs,
            authorized_by=authorized_by.strip(),
            world_revision=result.world_revision,
        )

    def record_outcome(
        self,
        request: ActionOutcomeRequest,
        *,
        recorded_at: datetime,
    ) -> OutcomeReceipt:
        recorded = as_utc(recorded_at, "recorded_at")
        payload = self._current_exact(
            request.action_ref,
            object_type=ObjectType.ACTION,
        )
        action = Action.model_validate(payload)
        if action.action_status not in {
            ActionStatus.SUBMITTED,
            ActionStatus.ACKNOWLEDGED,
            ActionStatus.OUTCOME_UNKNOWN,
        }:
            raise ValueError(
                "Outcome may only attach to a submitted/acknowledged/unknown Action"
            )
        self._validate_refs_exist(request.evidence_refs)

        status_map = {
            "completed": ActionStatus.COMPLETED,
            "failed": ActionStatus.FAILED,
            "outcome_unknown": ActionStatus.OUTCOME_UNKNOWN,
        }
        target_status = status_map[request.outcome_state]
        new_revision = int(action.revision) + 1
        metadata = dict(action.metadata)
        metadata["last_outcome_state"] = request.outcome_state
        metadata["last_outcome_recorded_at"] = recorded.isoformat()
        final_action = Action.model_validate(
            {
                **action.model_dump(mode="python", round_trip=True),
                "revision": new_revision,
                "occurred": TemporalExtent.point(recorded),
                "learned_at": recorded,
                "recorded_at": recorded,
                "source_refs": _source_refs(request.evidence_refs),
                "action_status": target_status,
                "status": target_status.value,
                "metadata": metadata,
            }
        )
        final_ref = ObjectRef(
            object_id=final_action.object_id,
            revision=new_revision,
        )
        outcome_id = _stable_id(
            "outcome",
            final_action.object_id,
            final_action.execution_id,
            new_revision,
            request.outcome_state,
        )
        outcome = Outcome(
            object_id=outcome_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(recorded),
            learned_at=recorded,
            recorded_at=recorded,
            source_refs=_source_refs(request.evidence_refs),
            created_by="execution_world:platform_result",
            action_ref=final_ref,
            outcome_state=request.outcome_state,
            payload=dict(request.payload),
            evidence_refs=list(request.evidence_refs),
            metadata={
                "execution_id": final_action.execution_id,
                "task_ref": (
                    None
                    if final_action.task_ref is None
                    else {
                        "object_id": final_action.task_ref.object_id,
                        "revision": final_action.task_ref.revision,
                    }
                ),
            },
        )
        outcome_ref = ObjectRef(object_id=outcome_id, revision=1)
        dependencies = [
            Dependency(
                object_id=_stable_id(
                    "dep", outcome_id, 1, final_ref.object_id, final_ref.revision
                ),
                subject_id=self.subject_id,
                learned_at=recorded,
                recorded_at=recorded,
                created_by="execution_world:platform_result",
                dependent_ref=outcome_ref,
                dependency_ref=final_ref,
                dependency_type="outcome_reports_action",
            ),
            *[
                Dependency(
                    object_id=_stable_id(
                        "dep", outcome_id, 1, ref.object_id, ref.revision
                    ),
                    subject_id=self.subject_id,
                    learned_at=recorded,
                    recorded_at=recorded,
                    created_by="execution_world:platform_result",
                    dependent_ref=outcome_ref,
                    dependency_ref=ref,
                    dependency_type="outcome_uses_evidence",
                )
                for ref in request.evidence_refs
            ],
        ]

        result = self.store.commit(
            [final_action, outcome, *dependencies],
            OperationRequest(
                operation_name="execution.action.record_outcome",
                arguments={
                    "action_id": final_action.object_id,
                    "execution_id": final_action.execution_id,
                    "outcome_state": request.outcome_state,
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason="record real platform Action outcome",
                idempotency_key=(
                    f"action-outcome:{final_action.object_id}:"
                    f"{new_revision}:{request.outcome_state}"
                ),
                source_class=SourceClass.PLATFORM,
            ),
        )
        self._catch_up()
        return OutcomeReceipt(
            action_id=final_action.object_id,
            action_revision=new_revision,
            outcome_id=outcome_id,
            outcome_state=request.outcome_state,
            world_revision=result.world_revision,
        )
