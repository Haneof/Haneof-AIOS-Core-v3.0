"""Periodic evidence-grounded review for AIOS v3.0.

The scheduler is deterministic: it decides only *when* a review is due and which
recent world anchors are mechanically eligible for inspection. The resident model
decides what those anchors mean and may use the existing cognition capabilities to
revise/retract claims or write new calibration/strategy/self cognition.

No benchmark answer, user-growth label, or strategy conclusion is computed here.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from aios_core.contracts.enums import (
    MaintenanceClass,
    ObjectType,
    SourceClass,
    WakeSource,
    WakeState,
)
from aios_core.contracts.models import Dependency, OperationExperience, Wake
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore


REVIEW_KIND = "periodic_ai_growth_review"

_REVIEWABLE_TYPES: tuple[ObjectType, ...] = (
    ObjectType.OBSERVATION,
    ObjectType.SUMMARY,
    ObjectType.CLAIM,
    ObjectType.GOAL,
    ObjectType.TASK,
    ObjectType.ACTION,
    ObjectType.OUTCOME,
    ObjectType.OPERATION_EXPERIENCE,
    ObjectType.COMMUNICATION_EXPERIENCE,
    ObjectType.PREDICTION,
)


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _parse_time(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is missing")
    return as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")), field_name)


def _excerpt(payload: Mapping[str, Any]) -> str:
    object_type = str(payload.get("object_type") or "")
    if object_type == ObjectType.OBSERVATION.value:
        value = payload.get("value")
        return str(value)[:600]
    if object_type == ObjectType.SUMMARY.value:
        return str(payload.get("content") or "")[:600]
    if object_type == ObjectType.CLAIM.value:
        return str(payload.get("content") or "")[:600]
    if object_type == ObjectType.GOAL.value:
        return (
            f"{payload.get('goal_status')}: {payload.get('title')} | "
            f"{payload.get('description')}"
        )[:600]
    if object_type == ObjectType.TASK.value:
        return (
            f"{payload.get('task_state')}: {payload.get('title')} | "
            f"next={payload.get('next_step')}"
        )[:600]
    if object_type == ObjectType.ACTION.value:
        return (
            f"{payload.get('action_status')}: {payload.get('action_type')} | "
            f"expected={payload.get('expected_outcome')}"
        )[:600]
    if object_type == ObjectType.OUTCOME.value:
        return (
            f"{payload.get('outcome_state')} | {payload.get('payload')}"
        )[:600]
    if object_type == ObjectType.OPERATION_EXPERIENCE.value:
        return (
            f"{payload.get('problem_type')} | {payload.get('result_summary')} | "
            f"misses={payload.get('misses')}"
        )[:600]
    if object_type == ObjectType.COMMUNICATION_EXPERIENCE.value:
        return (
            f"{payload.get('scenario')} | style={payload.get('style')} | "
            f"reaction={payload.get('user_reaction')}"
        )[:600]
    if object_type == ObjectType.PREDICTION.value:
        return (
            f"{payload.get('verification_state')}: "
            f"{payload.get('expected_change')}"
        )[:600]
    return str(payload)[:600]


class ReviewSchedulePolicy(BaseModel):
    """Engineering scheduling parameters, not cognitive truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    interval_hours: FiniteFloat = Field(default=24.0, gt=0.0)
    lookback_hours: FiniteFloat = Field(default=72.0, gt=0.0)
    max_candidates: int = Field(default=80, ge=1, le=500)
    max_per_object_type: int = Field(default=20, ge=1, le=100)


class ReviewAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    object_ref: ObjectRef
    object_type: str
    recorded_at: datetime
    excerpt: str

    @model_validator(mode="after")
    def validate_anchor(self) -> "ReviewAnchor":
        if self.object_ref.revision is None:
            raise ValueError("review anchor must pin exact revision")
        as_utc(self.recorded_at, "recorded_at")
        return self


class PeriodicReviewRequest(BaseModel):
    """Compact, evidence-grounded input shown to the same resident model runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    wake_ref: ObjectRef
    window_start: datetime
    window_end: datetime
    anchors: tuple[ReviewAnchor, ...] = Field(min_length=1)
    instruction: str = (
        "Review the supplied world anchors and decide whether any previous AI "
        "understanding, strategy, calibration, self-understanding, goal handling, "
        "or operation method should be revised. Use existing search/inspect tools "
        "when needed. Do not invent user growth, causal meaning, success, failure, "
        "or policy changes that are not supported by world evidence."
    )

    @model_validator(mode="after")
    def validate_request(self) -> "PeriodicReviewRequest":
        if self.wake_ref.revision is None:
            raise ValueError("wake_ref must pin exact revision")
        start = as_utc(self.window_start, "window_start")
        end = as_utc(self.window_end, "window_end")
        if end < start:
            raise ValueError("window_end must not be before window_start")
        return self


class OperationExperienceRequest(BaseModel):
    """Model-authored experience grounded in real case refs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    problem_type: str = Field(min_length=1)
    method_path: tuple[str, ...] = Field(min_length=1)
    result_summary: str = Field(min_length=1)
    positive_case_refs: tuple[ObjectRef, ...] = ()
    negative_case_refs: tuple[ObjectRef, ...] = ()
    applicability: dict[str, Any] = Field(default_factory=dict)
    cost: dict[str, FiniteFloat] = Field(default_factory=dict)
    misses: tuple[str, ...] = ()
    experience_state: str = Field(default="candidate", min_length=1)

    @model_validator(mode="after")
    def validate_request(self) -> "OperationExperienceRequest":
        if not self.problem_type.strip() or not self.result_summary.strip():
            raise ValueError("problem_type/result_summary must not be blank")
        if any(not item.strip() for item in self.method_path):
            raise ValueError("method_path must not contain blank steps")
        if any(not item.strip() for item in self.misses):
            raise ValueError("misses must not contain blank values")
        refs = (*self.positive_case_refs, *self.negative_case_refs)
        if not refs:
            raise ValueError("operation experience requires at least one real case ref")
        if any(ref.revision is None for ref in refs):
            raise ValueError("operation experience case refs must pin exact revisions")
        return self


@dataclass(frozen=True, slots=True)
class ReviewWakeReceipt:
    wake_id: str
    revision: int
    state: str
    world_revision: int


@dataclass(frozen=True, slots=True)
class OperationExperienceReceipt:
    experience_id: str
    revision: int
    world_revision: int


class PeriodicReviewService:
    """Deterministic review scheduling + world-backed experience writeback."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex | None = None,
        subject_id: str = "user_1",
    ) -> None:
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must not be blank")
        self.store = store
        self.index = index
        self.subject_id = subject_id.strip()

    def _catch_up(self) -> None:
        if self.index is not None:
            self.index.catch_up()

    def _review_wakes(self) -> tuple[Wake, ...]:
        wakes: list[Wake] = []
        for payload in self.store.list_payloads(
            object_type=ObjectType.WAKE,
            subject_id=self.subject_id,
        ):
            metadata = payload.get("metadata")
            if not isinstance(metadata, Mapping):
                continue
            if metadata.get("review_kind") != REVIEW_KIND:
                continue
            wakes.append(Wake.model_validate(payload))
        wakes.sort(key=lambda item: as_utc(item.last_hit_at, "last_hit_at"))
        return tuple(wakes)

    def _latest_marker(self) -> Wake | None:
        wakes = self._review_wakes()
        return wakes[-1] if wakes else None

    def _collect_candidates(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
        policy: ReviewSchedulePolicy,
    ) -> tuple[ReviewAnchor, ...]:
        start = as_utc(window_start, "window_start")
        end = as_utc(window_end, "window_end")
        per_type: dict[str, list[ReviewAnchor]] = {}

        for object_type in _REVIEWABLE_TYPES:
            for payload in self.store.list_payloads(
                object_type=object_type,
                subject_id=self.subject_id,
            ):
                try:
                    recorded = _parse_time(payload.get("recorded_at"), "recorded_at")
                except ValueError:
                    continue
                if recorded < start or recorded > end:
                    continue

                # Review summaries may be useful as compressed evidence, but the
                # scheduler itself never treats their text as a semantic verdict.
                anchor = ReviewAnchor(
                    object_ref=ObjectRef(
                        object_id=str(payload["object_id"]),
                        revision=int(payload["revision"]),
                    ),
                    object_type=str(payload["object_type"]),
                    recorded_at=recorded,
                    excerpt=_excerpt(payload),
                )
                bucket = per_type.setdefault(anchor.object_type, [])
                bucket.append(anchor)

        selected: list[ReviewAnchor] = []
        for object_type in sorted(per_type):
            bucket = per_type[object_type]
            bucket.sort(key=lambda item: (item.recorded_at, item.object_ref.object_id))
            selected.extend(bucket[-policy.max_per_object_type :])

        selected.sort(
            key=lambda item: (
                item.recorded_at,
                item.object_type,
                item.object_ref.object_id,
            )
        )
        return tuple(selected[-policy.max_candidates :])

    def _create_wake(
        self,
        *,
        now: datetime,
        window_start: datetime,
        anchors: Sequence[ReviewAnchor],
        state: WakeState,
        reason: str,
    ) -> ReviewWakeReceipt:
        moment = as_utc(now, "now")
        start = as_utc(window_start, "window_start")
        wake_id = _stable_id(
            "wake_review",
            self.subject_id,
            start.isoformat(),
            moment.isoformat(),
        )
        refs = [anchor.object_ref for anchor in anchors]
        wake = Wake(
            object_id=wake_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(moment),
            learned_at=moment,
            recorded_at=moment,
            source_refs=[
                SourceRef(object_id=ref.object_id, revision=ref.revision)
                for ref in refs
            ],
            created_by="periodic_review:scheduler",
            wake_source=WakeSource.PERIODIC_REVIEW,
            wake_state=state,
            rule_id="periodic_review.interval",
            first_hit_at=moment,
            last_hit_at=moment,
            evidence_refs=list(refs),
            priority=10,
            dedupe_key=f"periodic-review:{self.subject_id}:{moment.isoformat()}",
            status=state.value,
            metadata={
                "review_kind": REVIEW_KIND,
                "window_start": start.isoformat(),
                "window_end": moment.isoformat(),
                "reason": reason,
                "candidate_count": len(refs),
            },
        )
        result = self.store.commit(
            [wake],
            OperationRequest(
                operation_name="review.schedule",
                arguments={
                    "wake_id": wake_id,
                    "window_start": start.isoformat(),
                    "window_end": moment.isoformat(),
                    "state": state.value,
                    "candidate_count": len(refs),
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason=reason,
                idempotency_key=f"review-schedule:{wake_id}",
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.PERIODIC_REVIEW,
            ),
        )
        self._catch_up()
        return ReviewWakeReceipt(
            wake_id=wake_id,
            revision=1,
            state=state.value,
            world_revision=result.world_revision,
        )

    def prepare_due_review(
        self,
        *,
        now: datetime,
        policy: ReviewSchedulePolicy | None = None,
    ) -> PeriodicReviewRequest | None:
        policy = policy or ReviewSchedulePolicy()
        moment = as_utc(now, "now")
        latest = self._latest_marker()

        if latest is not None and latest.wake_state is WakeState.NEW:
            metadata = latest.metadata
            start = _parse_time(metadata.get("window_start"), "window_start")
            anchors = []
            for ref in latest.evidence_refs:
                payload = self.store.get_payload(
                    ref.object_id,
                    revision=ref.revision,
                )
                anchors.append(
                    ReviewAnchor(
                        object_ref=ref,
                        object_type=str(payload["object_type"]),
                        recorded_at=_parse_time(payload["recorded_at"], "recorded_at"),
                        excerpt=_excerpt(payload),
                    )
                )
            if not anchors:
                return None
            return PeriodicReviewRequest(
                review_id=latest.object_id,
                subject_id=self.subject_id,
                wake_ref=ObjectRef(
                    object_id=latest.object_id,
                    revision=latest.revision,
                ),
                window_start=start,
                window_end=latest.last_hit_at,
                anchors=tuple(anchors),
            )

        if latest is not None:
            since = moment - as_utc(latest.last_hit_at, "last_hit_at")
            if since < timedelta(hours=float(policy.interval_hours)):
                return None
            window_start = as_utc(latest.last_hit_at, "last_hit_at")
        else:
            window_start = moment - timedelta(hours=float(policy.lookback_hours))

        anchors = self._collect_candidates(
            window_start=window_start,
            window_end=moment,
            policy=policy,
        )
        if not anchors:
            self._create_wake(
                now=moment,
                window_start=window_start,
                anchors=(),
                state=WakeState.SUPPRESSED,
                reason="periodic review checked; no eligible world changes",
            )
            return None

        wake = self._create_wake(
            now=moment,
            window_start=window_start,
            anchors=anchors,
            state=WakeState.NEW,
            reason="periodic review due with eligible world changes",
        )
        return PeriodicReviewRequest(
            review_id=wake.wake_id,
            subject_id=self.subject_id,
            wake_ref=ObjectRef(object_id=wake.wake_id, revision=1),
            window_start=window_start,
            window_end=moment,
            anchors=anchors,
        )

    def complete_review(
        self,
        request: PeriodicReviewRequest,
        *,
        completed_at: datetime,
        termination_reason: str,
        model_rounds: int,
        capability_names: Sequence[str],
    ) -> ReviewWakeReceipt:
        if request.subject_id != self.subject_id:
            raise ValueError("review request belongs to another subject")
        completed = as_utc(completed_at, "completed_at")
        payload = self.store.get_payload(
            request.wake_ref.object_id,
            revision=request.wake_ref.revision,
        )
        wake = Wake.model_validate(payload)
        latest = Wake.model_validate(self.store.get_payload(wake.object_id))
        if latest.revision != wake.revision:
            if latest.wake_state is WakeState.COMPLETED:
                return ReviewWakeReceipt(
                    wake_id=latest.object_id,
                    revision=latest.revision,
                    state=latest.wake_state.value,
                    world_revision=int(self.store.current_world_revision()),
                )
            raise ValueError("review wake is no longer current")
        if wake.wake_state is not WakeState.NEW:
            raise ValueError("only NEW periodic review wake may complete")

        metadata = dict(wake.metadata)
        metadata.update(
            {
                "completed_at": completed.isoformat(),
                "termination_reason": termination_reason,
                "model_rounds": int(model_rounds),
                "capability_names": list(capability_names),
            }
        )
        new_revision = wake.revision + 1
        completed_wake = Wake.model_validate(
            {
                **wake.model_dump(mode="python", round_trip=True),
                "revision": new_revision,
                "occurred": TemporalExtent.point(completed),
                "learned_at": completed,
                "recorded_at": completed,
                "wake_state": WakeState.COMPLETED,
                "last_hit_at": completed,
                "hit_count": wake.hit_count + 1,
                "status": WakeState.COMPLETED.value,
                "metadata": metadata,
            }
        )
        result = self.store.commit(
            [completed_wake],
            OperationRequest(
                operation_name="review.complete",
                arguments={
                    "wake_id": wake.object_id,
                    "revision": new_revision,
                    "termination_reason": termination_reason,
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason="record completion of model-driven periodic review",
                idempotency_key=f"review-complete:{wake.object_id}:{new_revision}",
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.PERIODIC_REVIEW,
            ),
        )
        self._catch_up()
        return ReviewWakeReceipt(
            wake_id=wake.object_id,
            revision=new_revision,
            state=WakeState.COMPLETED.value,
            world_revision=result.world_revision,
        )

    def commit_operation_experience(
        self,
        request: OperationExperienceRequest,
        *,
        learned_at: datetime,
    ) -> OperationExperienceReceipt:
        request = OperationExperienceRequest.model_validate(
            request.model_dump(mode="python", round_trip=True)
        )
        learned = as_utc(learned_at, "learned_at")
        refs = (*request.positive_case_refs, *request.negative_case_refs)
        for ref in refs:
            self.store.get_payload(ref.object_id, revision=ref.revision)

        experience_id = _stable_id(
            "opexp",
            self.subject_id,
            request.problem_type,
            request.method_path,
            [(ref.object_id, ref.revision) for ref in refs],
        )
        experience = OperationExperience(
            object_id=experience_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(learned),
            learned_at=learned,
            recorded_at=learned,
            source_refs=[
                SourceRef(object_id=ref.object_id, revision=ref.revision)
                for ref in refs
            ],
            created_by="periodic_review:resident_ai",
            problem_type=request.problem_type.strip(),
            method_path=[step.strip() for step in request.method_path],
            applicability=dict(request.applicability),
            cost={key: float(value) for key, value in request.cost.items()},
            result_summary=request.result_summary.strip(),
            misses=[item.strip() for item in request.misses],
            positive_case_refs=list(request.positive_case_refs),
            negative_case_refs=list(request.negative_case_refs),
            experience_state=request.experience_state.strip(),
            metadata={
                "review_kind": REVIEW_KIND,
                "evidence_grounded": True,
            },
        )
        exp_ref = ObjectRef(object_id=experience_id, revision=1)
        dependencies = [
            Dependency(
                object_id=_stable_id(
                    "dep_opexp",
                    experience_id,
                    ref.object_id,
                    ref.revision,
                ),
                subject_id=self.subject_id,
                learned_at=learned,
                recorded_at=learned,
                created_by="periodic_review:dependency",
                dependent_ref=exp_ref,
                dependency_ref=ref,
                dependency_type="operation_experience_uses_case",
            )
            for ref in refs
        ]
        result = self.store.commit(
            [experience, *dependencies],
            OperationRequest(
                operation_name="review.commit_operation_experience",
                arguments={
                    "experience_id": experience_id,
                    "problem_type": request.problem_type,
                    "positive_count": len(request.positive_case_refs),
                    "negative_count": len(request.negative_case_refs),
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason="persist model-authored experience grounded in real cases",
                idempotency_key=f"operation-experience:{experience_id}",
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        self._catch_up()
        return OperationExperienceReceipt(
            experience_id=experience_id,
            revision=1,
            world_revision=result.world_revision,
        )
