"""Resident-authored mechanical attention watches and wake batching.

The resident model decides *what deserves future attention*.  This module stores
that intent as a constrained observation Task and evaluates only mechanical
predicates over later Observation facts.  It never infers semantic meaning.

The AttentionRouter batches already-created non-safety Wake objects so bursts of
related low-level changes can invoke the Resident once rather than once per signal.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import (
    AttentionClass,
    MaintenanceClass,
    ObjectType,
    SourceClass,
    TaskState,
    TaskType,
    WakeSource,
    WakeState,
)
from aios_core.contracts.models import Dependency, Observation, Task, Wake
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.execution import GoalTaskActionService, TaskCreateRequest
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore

from .service import WakeBus, WakeSignalReceipt, WakeSignalRequest


NumericOperator = Literal["gt", "gte", "lt", "lte", "eq", "ne"]


class NumericPredicate(BaseModel):
    """Purely mechanical numeric comparison against Observation.value."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operator: NumericOperator
    threshold: float
    path: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_path(self) -> "NumericPredicate":
        if any(not str(item).strip() for item in self.path):
            raise ValueError("numeric predicate path parts must be non-blank")
        return self


class AttentionWatchRequest(BaseModel):
    """Resident-authored future-attention intent compiled to a mechanical predicate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1)
    dimensions: tuple[str, ...] = Field(min_length=1)
    reason_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    goal_ref: ObjectRef | None = None
    source_kind: str | None = None
    modality: str | None = None
    metadata_equals: Mapping[str, Any] = Field(default_factory=dict)
    numeric: NumericPredicate | None = None
    priority: int = Field(default=50, ge=0, le=100)
    cooldown_seconds: int = Field(default=0, ge=0)
    attention_class: AttentionClass = AttentionClass.BACKGROUND
    mode: Literal["recurring", "one_shot"] = "recurring"
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_request(self) -> "AttentionWatchRequest":
        if not self.title.strip():
            raise ValueError("title must not be blank")
        clean_dims = [str(item).strip() for item in self.dimensions]
        if any(not item or not item.startswith("dim:") for item in clean_dims):
            raise ValueError("attention watch dimensions must start with 'dim:'")
        if len(set(clean_dims)) != len(clean_dims):
            raise ValueError("attention watch dimensions must be unique")
        if self.source_kind is not None and not self.source_kind.strip():
            raise ValueError("source_kind must not be blank")
        if self.modality is not None and not self.modality.strip():
            raise ValueError("modality must not be blank")
        if any(not str(key).strip() for key in self.metadata_equals):
            raise ValueError("metadata predicate keys must be non-blank")
        if self.expires_at is not None:
            as_utc(self.expires_at, "expires_at")
        for ref in self.reason_refs:
            if ref.revision is None:
                raise ValueError("attention watch reason_refs must pin revisions")
        if self.goal_ref is not None and self.goal_ref.revision is None:
            raise ValueError("attention watch goal_ref must pin a revision")
        return self


@dataclass(frozen=True, slots=True)
class AttentionWatchReceipt:
    task_id: str
    revision: int
    state: str
    world_revision: int


@dataclass(frozen=True, slots=True)
class AttentionBundleReceipt:
    wake_id: str
    revision: int
    member_count: int
    member_wake_ids: tuple[str, ...]
    world_revision: int


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    import hashlib

    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _extract_numeric(value: Any, path: Sequence[str]) -> float | None:
    current = value
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    if isinstance(current, bool) or not isinstance(current, (int, float)):
        return None
    return float(current)


def _numeric_matches(actual: float, predicate: NumericPredicate) -> bool:
    threshold = float(predicate.threshold)
    if predicate.operator == "gt":
        return actual > threshold
    if predicate.operator == "gte":
        return actual >= threshold
    if predicate.operator == "lt":
        return actual < threshold
    if predicate.operator == "lte":
        return actual <= threshold
    if predicate.operator == "eq":
        return actual == threshold
    if predicate.operator == "ne":
        return actual != threshold
    raise AssertionError("unreachable numeric operator")


class AttentionWatchService:
    """Compile Resident attention intent to durable Task + mechanical matching."""

    CONDITION_KIND = "attention_watch_v1"

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex,
        execution_world: GoalTaskActionService,
        wake_bus: WakeBus,
        subject_id: str = "user_1",
    ) -> None:
        self.store = store
        self.index = index
        self.execution_world = execution_world
        self.wake_bus = wake_bus
        self.subject_id = subject_id.strip()

    def create(
        self,
        request: AttentionWatchRequest,
        *,
        created_at: datetime,
    ) -> AttentionWatchReceipt:
        created = as_utc(created_at, "created_at")
        if request.expires_at is not None and as_utc(
            request.expires_at, "expires_at"
        ) <= created:
            raise ValueError("attention watch expires_at must be after created_at")

        condition = {
            "kind": self.CONDITION_KIND,
            "dimensions": [str(item).strip() for item in request.dimensions],
            "source_kind": (
                None if request.source_kind is None else request.source_kind.strip()
            ),
            "modality": (
                None if request.modality is None else request.modality.strip()
            ),
            "metadata_equals": dict(request.metadata_equals),
            "numeric": (
                None if request.numeric is None else request.numeric.model_dump(mode="json")
            ),
            "cooldown_seconds": int(request.cooldown_seconds),
            "attention_class": request.attention_class.value,
            "watch_mode": request.mode,
            "predicate_semantics": "mechanical_only",
        }
        receipt = self.execution_world.create_task(
            TaskCreateRequest(
                title=request.title.strip(),
                task_type=TaskType.OBSERVATION,
                reason_refs=request.reason_refs,
                goal_ref=request.goal_ref,
                initial_state=TaskState.WAITING_EVIDENCE,
                priority=request.priority,
                deadline=request.expires_at,
                next_step=(
                    "Mechanically watch matching Observation facts; "
                    "Resident interprets meaning only after Wake."
                ),
                completion_condition=condition,
            ),
            created_at=created,
        )
        return AttentionWatchReceipt(
            task_id=receipt.task_id,
            revision=receipt.revision,
            state=receipt.state,
            world_revision=receipt.world_revision,
        )

    def _transition_watch_mechanically(
        self,
        task: Task,
        *,
        target: TaskState,
        changed_at: datetime,
        metadata_update: Mapping[str, Any],
        source_ref: ObjectRef | None = None,
    ) -> Task:
        """Advance watch lifecycle from objective time/match facts only."""

        if task.task_state is not TaskState.WAITING_EVIDENCE:
            raise ValueError("only WAITING_EVIDENCE attention watch may auto-transition")
        if target not in {TaskState.READY, TaskState.EXPIRED}:
            raise ValueError("mechanical attention transition must target READY or EXPIRED")

        changed = as_utc(changed_at, "changed_at")
        metadata = dict(task.metadata)
        metadata.update(dict(metadata_update))
        history = list(metadata.get("task_state_history") or [])
        history.append(
            {
                "from": TaskState.WAITING_EVIDENCE.value,
                "to": target.value,
                "reason": "mechanical_attention_lifecycle",
                "changed_at": changed.isoformat(),
            }
        )
        metadata["task_state_history"] = history

        revision = task.revision + 1
        revised = Task.model_validate(
            {
                **task.model_dump(mode="python", round_trip=True),
                "revision": revision,
                "occurred": TemporalExtent.point(changed),
                "learned_at": changed,
                "recorded_at": changed,
                "source_refs": (
                    []
                    if source_ref is None
                    else [
                        SourceRef(
                            object_id=source_ref.object_id,
                            revision=source_ref.revision,
                        )
                    ]
                ),
                "task_state": target,
                "status": (
                    TaskState.EXPIRED.value
                    if target is TaskState.EXPIRED
                    else "active"
                ),
                "metadata": metadata,
            }
        )
        dependencies: list[Dependency] = []
        if source_ref is not None:
            dependencies.append(
                Dependency(
                    object_id=_stable_id(
                        "dep",
                        revised.object_id,
                        revised.revision,
                        source_ref.object_id,
                        source_ref.revision,
                    ),
                    subject_id=self.subject_id,
                    learned_at=changed,
                    recorded_at=changed,
                    created_by="wake:attention_dependency",
                    dependent_ref=ObjectRef(
                        object_id=revised.object_id,
                        revision=revised.revision,
                    ),
                    dependency_ref=source_ref,
                    dependency_type="attention_watch_transition_uses_evidence",
                )
            )

        self.store.commit(
            [revised, *dependencies],
            OperationRequest(
                operation_name="wake.attention.watch_transition",
                arguments={
                    "task_id": task.object_id,
                    "from": task.task_state.value,
                    "to": target.value,
                    "source_ref": (
                        None
                        if source_ref is None
                        else source_ref.model_dump(mode="json")
                    ),
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason="mechanical attention-watch lifecycle transition",
                idempotency_key=(
                    f"attention-watch-transition:{task.object_id}:"
                    f"{revision}:{target.value}"
                ),
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.WAKE_SCHEDULER,
            ),
        )
        self.index.catch_up()
        return revised

    def expire_due(self, *, now: datetime) -> tuple[ObjectRef, ...]:
        moment = as_utc(now, "now")
        expired: list[ObjectRef] = []
        for task in self.current():
            if task.deadline is None:
                continue
            if as_utc(task.deadline, "deadline") > moment:
                continue
            revised = self._transition_watch_mechanically(
                task,
                target=TaskState.EXPIRED,
                changed_at=moment,
                metadata_update={
                    "attention_watch_expired_at": moment.isoformat(),
                },
            )
            expired.append(
                ObjectRef(
                    object_id=revised.object_id,
                    revision=revised.revision,
                )
            )
        return tuple(expired)

    def current(self) -> tuple[Task, ...]:
        watches: list[Task] = []
        for task in self.execution_world.current_tasks():
            if task.task_type is not TaskType.OBSERVATION:
                continue
            if task.task_state is not TaskState.WAITING_EVIDENCE:
                continue
            condition = task.completion_condition
            if condition.get("kind") != self.CONDITION_KIND:
                continue
            watches.append(task)
        watches.sort(key=lambda item: (-item.priority, item.object_id))
        return tuple(watches)

    @staticmethod
    def _matches(task: Task, observation: Observation) -> bool:
        condition = task.completion_condition
        dimensions = tuple(str(item) for item in condition.get("dimensions") or ())
        dimension = str(observation.metadata.get("dimension") or "")
        if dimension not in dimensions:
            return False

        source_kind = condition.get("source_kind")
        if source_kind is not None and observation.source_kind != source_kind:
            return False
        modality = condition.get("modality")
        if modality is not None and observation.modality != modality:
            return False

        metadata_equals = condition.get("metadata_equals") or {}
        if not isinstance(metadata_equals, Mapping):
            return False
        for key, expected in metadata_equals.items():
            if observation.metadata.get(str(key)) != expected:
                return False

        numeric_raw = condition.get("numeric")
        if numeric_raw is not None:
            predicate = NumericPredicate.model_validate(numeric_raw)
            actual = _extract_numeric(observation.value, predicate.path)
            if actual is None or not _numeric_matches(actual, predicate):
                return False

        return True

    def evaluate_observation(
        self,
        observation_ref: ObjectRef,
    ) -> tuple[WakeSignalReceipt, ...]:
        if observation_ref.revision is None:
            raise ValueError("observation_ref must pin an exact revision")
        payload = self.store.get_payload(
            observation_ref.object_id,
            revision=observation_ref.revision,
        )
        if payload.get("object_type") != ObjectType.OBSERVATION.value:
            raise ValueError("attention watches evaluate Observation objects only")
        observation = Observation.model_validate(payload)
        if observation.subject_id != self.subject_id:
            raise ValueError("Observation belongs to another subject")

        self.expire_due(now=observation.recorded_at)
        receipts: list[WakeSignalReceipt] = []
        for task in self.current():
            if task.deadline is not None and as_utc(
                task.deadline, "deadline"
            ) < as_utc(observation.recorded_at, "recorded_at"):
                continue
            if not self._matches(task, observation):
                continue

            condition = task.completion_condition
            task_ref = ObjectRef(object_id=task.object_id, revision=task.revision)
            receipt = self.wake_bus.emit(
                WakeSignalRequest(
                    wake_source=WakeSource.WATCH_MATCH,
                    rule_id=f"attention_watch:{task.object_id}",
                    observed_at=observation.recorded_at,
                    evidence_refs=(task_ref, observation_ref),
                    priority=task.priority,
                    dedupe_key=f"attention_watch:{task.object_id}",
                    cooldown_seconds=int(
                        condition.get("cooldown_seconds") or 0
                    ),
                    attention_class=AttentionClass(
                        str(
                            condition.get("attention_class")
                            or AttentionClass.BACKGROUND.value
                        )
                    ),
                    metadata={
                        "trigger_kind": "resident_attention_watch",
                        "watch_task_ref": task_ref.model_dump(mode="json"),
                        "matched_dimension": observation.metadata.get("dimension"),
                        "watch_mode": str(
                            condition.get("watch_mode") or "recurring"
                        ),
                        "predicate_semantics": "mechanical_only",
                    },
                )
            )
            receipts.append(receipt)

            if str(condition.get("watch_mode") or "recurring") == "one_shot":
                self._transition_watch_mechanically(
                    task,
                    target=TaskState.READY,
                    changed_at=observation.recorded_at,
                    metadata_update={
                        "attention_watch_matched_at": observation.recorded_at.isoformat(),
                        "attention_watch_match_observation_ref": (
                            observation_ref.model_dump(mode="json")
                        ),
                        "attention_watch_match_wake_ref": {
                            "object_id": receipt.wake_id,
                            "revision": receipt.revision,
                        },
                    },
                    source_ref=observation_ref,
                )
        return tuple(receipts)


class AttentionRouter:
    """Mechanically batch a short burst of pending non-safety Wakes into one Wake."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        wake_bus: WakeBus,
        subject_id: str = "user_1",
    ) -> None:
        self.store = store
        self.wake_bus = wake_bus
        self.subject_id = subject_id.strip()

    def next_dispatchable(
        self,
        *,
        now: datetime | None = None,
        background_batch_window_seconds: int = 60,
    ) -> Wake | None:
        """Choose the next non-conversation Wake by mechanical routing class.

        INTERRUPT always dispatches immediately and precedes BACKGROUND.
        REVIEW_QUEUE is deliberately invisible here and can only be consumed by
        periodic review.

        When now is supplied, BACKGROUND wakes are held for one short mechanical
        coalescing window measured from the oldest pending BACKGROUND wake. This gives
        sibling world changes time to accumulate before one Resident invocation. The
        wait is scheduling only; it never infers whether a change is important.
        """

        if background_batch_window_seconds < 0:
            raise ValueError("background_batch_window_seconds must be >= 0")

        candidates = [
            wake
            for wake in self.wake_bus.pending_wakes()
            if wake.wake_source
            not in {
                WakeSource.PERIODIC_REVIEW,
                WakeSource.USER_INTERACTION,
            }
            and self.wake_bus.attention_class_for_wake(wake)
            is not AttentionClass.REVIEW_QUEUE
        ]
        if not candidates:
            return None

        interrupts = [
            wake
            for wake in candidates
            if self.wake_bus.attention_class_for_wake(wake)
            is AttentionClass.INTERRUPT
        ]
        if interrupts:
            interrupts.sort(
                key=lambda wake: (
                    -wake.priority,
                    as_utc(wake.first_hit_at, "first_hit_at"),
                    wake.object_id,
                )
            )
            return interrupts[0]

        backgrounds = [
            wake
            for wake in candidates
            if self.wake_bus.attention_class_for_wake(wake)
            is AttentionClass.BACKGROUND
        ]
        if not backgrounds:
            return None

        if now is None or background_batch_window_seconds == 0:
            backgrounds.sort(
                key=lambda wake: (
                    -wake.priority,
                    as_utc(wake.first_hit_at, "first_hit_at"),
                    wake.object_id,
                )
            )
            return backgrounds[0]

        moment = as_utc(now, "now")
        backgrounds.sort(
            key=lambda wake: (
                as_utc(wake.first_hit_at, "first_hit_at"),
                -wake.priority,
                wake.object_id,
            )
        )
        oldest = backgrounds[0]
        ready_at = as_utc(oldest.first_hit_at, "first_hit_at") + timedelta(
            seconds=background_batch_window_seconds
        )
        if moment < ready_at:
            return None
        return oldest

    def pending_review_queue(self) -> tuple[Wake, ...]:
        """Return durable low-urgency Wakes reserved for periodic Resident review."""

        queued = [
            wake
            for wake in self.wake_bus.pending_wakes()
            if str(wake.metadata.get("attention_class") or "")
            == AttentionClass.REVIEW_QUEUE.value
        ]
        queued.sort(
            key=lambda item: (
                as_utc(item.first_hit_at, "first_hit_at"),
                item.object_id,
            )
        )
        return tuple(queued)

    def complete_review_queue(
        self,
        wake_ids: Sequence[str],
        *,
        completed_at: datetime,
    ) -> tuple[str, ...]:
        completed: list[str] = []
        for wake_id in wake_ids:
            wake = self.wake_bus.current_wake(str(wake_id))
            if wake.wake_state not in {WakeState.NEW, WakeState.QUEUED}:
                continue
            self.wake_bus.complete(
                wake.object_id,
                completed_at=completed_at,
                termination_reason="periodic_review_consumed",
                model_rounds=0,
                capability_names=(),
                delivery_allowed=False,
                step0_state="review_queue",
            )
            completed.append(wake.object_id)
        return tuple(completed)

    def bundle_pending(
        self,
        *,
        now: datetime,
        window_seconds: int = 60,
        max_wakes: int = 16,
        anchor_wake_id: str | None = None,
    ) -> AttentionBundleReceipt | None:
        moment = as_utc(now, "now")
        if window_seconds < 0:
            raise ValueError("window_seconds must be >= 0")
        if max_wakes < 2:
            raise ValueError("max_wakes must be >= 2")

        pending_background = [
            wake
            for wake in self.wake_bus.pending_wakes()
            if wake.wake_source
            not in {
                WakeSource.SAFETY,
                WakeSource.PERIODIC_REVIEW,
                WakeSource.USER_INTERACTION,
                WakeSource.ATTENTION_BUNDLE,
            }
            and self.wake_bus.attention_class_for_wake(wake)
            is AttentionClass.BACKGROUND
            and as_utc(wake.first_hit_at, "first_hit_at") <= moment
        ]
        pending_background.sort(
            key=lambda wake: (
                as_utc(wake.first_hit_at, "first_hit_at"),
                -wake.priority,
                wake.object_id,
            )
        )

        if anchor_wake_id is None:
            cutoff = moment - timedelta(seconds=window_seconds)
            eligible = [
                wake
                for wake in pending_background
                if cutoff <= as_utc(wake.last_hit_at, "last_hit_at") <= moment
            ][:max_wakes]
        else:
            anchor = next(
                (
                    wake
                    for wake in pending_background
                    if wake.object_id == str(anchor_wake_id)
                ),
                None,
            )
            if anchor is None:
                return None
            window_start = as_utc(anchor.first_hit_at, "first_hit_at")
            window_end = window_start + timedelta(seconds=window_seconds)
            if moment < window_end:
                return None
            eligible = [
                wake
                for wake in pending_background
                if window_start
                <= as_utc(wake.first_hit_at, "first_hit_at")
                <= window_end
            ][:max_wakes]

        if len(eligible) < 2:
            return None

        member_refs = [
            ObjectRef(object_id=wake.object_id, revision=wake.revision)
            for wake in eligible
        ]
        evidence_refs: list[ObjectRef] = []
        for wake in eligible:
            for ref in wake.evidence_refs:
                if ref not in evidence_refs:
                    evidence_refs.append(ref)
            ref = ObjectRef(object_id=wake.object_id, revision=wake.revision)
            if ref not in evidence_refs:
                evidence_refs.append(ref)

        bundle_id = _stable_id(
            "wake_bundle",
            self.subject_id,
            tuple((ref.object_id, ref.revision) for ref in member_refs),
        )
        bundle = Wake(
            object_id=bundle_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(moment),
            learned_at=moment,
            recorded_at=moment,
            source_refs=[
                SourceRef(object_id=ref.object_id, revision=ref.revision)
                for ref in evidence_refs
            ],
            created_by="attention_router:bundle",
            wake_source=WakeSource.ATTENTION_BUNDLE,
            wake_state=WakeState.NEW,
            rule_id="attention.router.bundle",
            first_hit_at=min(
                as_utc(item.first_hit_at, "first_hit_at") for item in eligible
            ),
            last_hit_at=max(
                as_utc(item.last_hit_at, "last_hit_at") for item in eligible
            ),
            hit_count=sum(item.hit_count for item in eligible),
            evidence_refs=evidence_refs,
            priority=max(item.priority for item in eligible),
            dedupe_key=f"attention_bundle:{bundle_id}",
            metadata={
                "attention_bundle": {
                    "member_count": len(eligible),
                    "members": [
                        {
                            "wake_ref": {
                                "object_id": item.object_id,
                                "revision": item.revision,
                            },
                            "wake_source": item.wake_source.value,
                            "rule_id": item.rule_id,
                            "priority": item.priority,
                            "hit_count": item.hit_count,
                        }
                        for item in eligible
                    ],
                },
                "semantic_conclusions": False,
                "routing_only": True,
                "attention_class": AttentionClass.BACKGROUND.value,
            },
        )

        merged_children: list[Wake] = []
        for wake in eligible:
            metadata = dict(wake.metadata)
            metadata["merged_into_attention_bundle"] = {
                "object_id": bundle_id,
                "revision": 1,
            }
            merged_children.append(
                Wake.model_validate(
                    {
                        **wake.model_dump(mode="python", round_trip=True),
                        "revision": wake.revision + 1,
                        "occurred": TemporalExtent.point(moment),
                        "learned_at": moment,
                        "recorded_at": moment,
                        "wake_state": WakeState.MERGED,
                        "status": WakeState.MERGED.value,
                        "metadata": metadata,
                    }
                )
            )

        result = self.store.commit(
            [bundle, *merged_children],
            OperationRequest(
                operation_name="wake.attention.bundle",
                arguments={
                    "bundle_id": bundle_id,
                    "member_wake_ids": [item.object_id for item in eligible],
                    "window_seconds": int(window_seconds),
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason="mechanically batch pending non-safety Wakes before Resident invocation",
                idempotency_key=f"attention-bundle:{bundle_id}",
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.WAKE_SCHEDULER,
            ),
        )
        self.wake_bus._catch_up()
        return AttentionBundleReceipt(
            wake_id=bundle_id,
            revision=1,
            member_count=len(eligible),
            member_wake_ids=tuple(item.object_id for item in eligible),
            world_revision=result.world_revision,
        )
