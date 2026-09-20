"""Periodic review and evidence-grounded operational learning for AIOS v3.0.

The scheduler in this module is deliberately mechanical: it decides whether enough
time has passed and which committed world revisions have not yet been reviewed.
Meaning, strategy and cognition remain model decisions executed through the existing
CognitiveRuntime and Claim/Revision machinery.

Review checkpoints are MAINTENANCE summaries in the same WorldStore. They are process
audit/index objects, not a second truth store and not cognition Claims.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import (
    ErrorCode,
    MaintenanceClass,
    ObjectType,
    SourceClass,
    SummaryStatus,
)
from aios_core.contracts.models import Dependency, OperationExperience, Summary
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError


REVIEW_CHECKPOINT_KIND = "periodic_review_checkpoint"
OPERATION_EXPERIENCE_DIMENSION = "dim:ai_operation_experience"

# Mechanical graph objects are still available through inspect_world_object when the
# model needs them, but do not need to dominate the periodic review input package.
_REVIEW_INPUT_SKIP_TYPES = {
    ObjectType.DEPENDENCY,
}

# Experience must be grounded in real observed/result evidence. A Claim, Goal or
# proposed Action alone cannot prove that a method worked or failed.
_OPERATION_EXPERIENCE_EVIDENCE_TYPES = {
    ObjectType.OBSERVATION,
    ObjectType.OUTCOME,
    ObjectType.COMMUNICATION_EXPERIENCE,
}


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _parse_time(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return as_utc(value, field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be an aware datetime")
    return as_utc(
        datetime.fromisoformat(value.strip().replace("Z", "+00:00")),
        field_name,
    )


def _compact_salient(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Expose deterministic high-signal fields; exact payload remains inspectable."""

    object_type = str(payload.get("object_type") or "")
    metadata = payload.get("metadata")
    dimension = (
        metadata.get("dimension")
        if isinstance(metadata, Mapping)
        else None
    )
    common: dict[str, Any] = {
        "status": payload.get("status"),
        "dimension": dimension,
    }

    if object_type == ObjectType.OBSERVATION.value:
        common.update(
            {
                "source_kind": payload.get("source_kind"),
                "modality": payload.get("modality"),
                "value": payload.get("value"),
                "unit": payload.get("unit"),
            }
        )
    elif object_type == ObjectType.CLAIM.value:
        common.update(
            {
                "content": payload.get("content"),
                "confidence": payload.get("confidence"),
                "knowledge_state": payload.get("knowledge_state"),
                "claim_type": payload.get("claim_type"),
            }
        )
    elif object_type == ObjectType.GOAL.value:
        common.update(
            {
                "title": payload.get("title"),
                "description": payload.get("description"),
                "goal_status": payload.get("goal_status"),
            }
        )
    elif object_type == ObjectType.TASK.value:
        common.update(
            {
                "title": payload.get("title"),
                "task_state": payload.get("task_state"),
                "next_step": payload.get("next_step"),
                "outcome_refs": payload.get("outcome_refs"),
            }
        )
    elif object_type == ObjectType.ACTION.value:
        common.update(
            {
                "action_type": payload.get("action_type"),
                "action_status": payload.get("action_status"),
                "expected_outcome": payload.get("expected_outcome"),
            }
        )
    elif object_type == ObjectType.OUTCOME.value:
        common.update(
            {
                "outcome_state": payload.get("outcome_state"),
                "payload": payload.get("payload"),
                "action_ref": payload.get("action_ref"),
            }
        )
    elif object_type == ObjectType.OPERATION_EXPERIENCE.value:
        common.update(
            {
                "problem_type": payload.get("problem_type"),
                "result_summary": payload.get("result_summary"),
                "experience_state": payload.get("experience_state"),
            }
        )
    elif object_type == ObjectType.SUMMARY.value:
        common.update(
            {
                "granularity": payload.get("granularity"),
                "content": payload.get("content"),
                "summary_status": payload.get("summary_status"),
            }
        )
    elif object_type == ObjectType.EVENT.value:
        common.update(
            {
                "title": payload.get("title"),
                "interpretation": payload.get("interpretation"),
                "event_status": payload.get("event_status"),
                "confidence": payload.get("confidence"),
            }
        )
    else:
        # Keep this mechanical. Unknown/new object types remain inspectable by ref.
        for key in ("name", "title", "description", "lifecycle"):
            if key in payload:
                common[key] = payload.get(key)

    return common


class PeriodicReviewPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum_interval_seconds: int = Field(default=86_400, ge=0)
    max_source_objects: int = Field(default=200, ge=1, le=2000)
    max_triggerable_commits: int = Field(default=500, ge=1, le=5000)


class PeriodicReviewItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    object_ref: ObjectRef
    object_type: ObjectType
    subject_id: str = Field(min_length=1)
    world_revision: int = Field(ge=1)
    source_class: SourceClass
    learned_at: datetime
    salient: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_item(self) -> "PeriodicReviewItem":
        if self.object_ref.revision is None:
            raise ValueError("review items require pinned object revisions")
        as_utc(self.learned_at, "learned_at")
        return self


class PeriodicReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject_id: str = Field(min_length=1)
    from_world_revision_exclusive: int = Field(ge=0)
    reviewed_through_world_revision: int = Field(ge=1)
    prepared_at: datetime
    items: tuple[PeriodicReviewItem, ...] = Field(min_length=1)
    triggerable_commit_count: int = Field(ge=1)
    truncated: bool = False
    instruction: str = (
        "Review these pinned world changes and decide what, if anything, should "
        "change in current cognition or strategy. Use capabilities to inspect exact "
        "objects when needed. Do not invent outcomes, do not turn correlations into "
        "causes, and do not create a strategy merely because an experience exists. "
        "It is valid to make no durable cognition change."
    )

    @model_validator(mode="after")
    def validate_input(self) -> "PeriodicReviewInput":
        as_utc(self.prepared_at, "prepared_at")
        if self.reviewed_through_world_revision <= self.from_world_revision_exclusive:
            raise ValueError("reviewed_through_world_revision must advance the checkpoint")
        if any(
            item.world_revision > self.reviewed_through_world_revision
            for item in self.items
        ):
            raise ValueError("review item escaped reviewed_through_world_revision")
        return self

    @property
    def source_refs(self) -> tuple[ObjectRef, ...]:
        return tuple(item.object_ref for item in self.items)

    def as_cockpit(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


@dataclass(frozen=True, slots=True)
class ReviewCheckpointCommit:
    object_id: str
    revision: int
    reviewed_through_world_revision: int
    world_revision: int
    reused_existing: bool


class OperationExperienceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    problem_type: str = Field(min_length=1)
    method_path: tuple[str, ...] = Field(min_length=1)
    result_summary: str = Field(min_length=1)
    applicability: dict[str, Any] = Field(default_factory=dict)
    cost: dict[str, float] = Field(default_factory=dict)
    misses: tuple[str, ...] = ()
    positive_case_refs: tuple[ObjectRef, ...] = ()
    negative_case_refs: tuple[ObjectRef, ...] = ()

    @model_validator(mode="after")
    def validate_request(self) -> "OperationExperienceRequest":
        if not self.problem_type.strip() or not self.result_summary.strip():
            raise ValueError("problem_type/result_summary must not be blank")
        if any(not step.strip() for step in self.method_path):
            raise ValueError("method_path must not contain blank steps")
        if any(not miss.strip() for miss in self.misses):
            raise ValueError("misses must not contain blank values")
        refs = (*self.positive_case_refs, *self.negative_case_refs)
        if not refs:
            raise ValueError(
                "operation experience requires at least one real result evidence ref"
            )
        positive_keys = {
            (ref.object_id, ref.revision) for ref in self.positive_case_refs
        }
        negative_keys = {
            (ref.object_id, ref.revision) for ref in self.negative_case_refs
        }
        if positive_keys.intersection(negative_keys):
            raise ValueError(
                "the same evidence ref cannot be both a positive and negative case"
            )
        for ref in refs:
            if ref.revision is None:
                raise ValueError("operation experience requires pinned evidence revisions")
        return self


@dataclass(frozen=True, slots=True)
class OperationExperienceCommit:
    object_id: str
    world_revision: int
    reused_existing: bool


class OperationExperienceService:
    """Persist model-selected lessons without auto-promoting them into strategy."""

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

    def _expected_revision_for_retry(self, operation_id: str) -> int:
        expected = int(self.store.current_world_revision())
        try:
            previous = self.store.operation_record(operation_id)
        except StoreError as exc:
            if exc.code == ErrorCode.NOT_FOUND:
                return expected
            raise
        return int(previous["expected_world_revision"])

    def commit(
        self,
        request: OperationExperienceRequest,
        *,
        learned_at: datetime,
    ) -> OperationExperienceCommit:
        request = OperationExperienceRequest.model_validate(
            request.model_dump(mode="python", round_trip=True)
        )
        learned = as_utc(learned_at, "learned_at")
        positive = tuple(request.positive_case_refs)
        negative = tuple(request.negative_case_refs)
        all_refs = (*positive, *negative)

        for ref in all_refs:
            payload = self.store.get_payload(ref.object_id, revision=ref.revision)
            if payload.get("subject_id") != self.subject_id:
                raise ValueError("operation experience evidence belongs to another subject")
            try:
                object_type = ObjectType(str(payload["object_type"]))
            except (KeyError, ValueError) as exc:
                raise ValueError("operation experience evidence has invalid object type") from exc
            if object_type not in _OPERATION_EXPERIENCE_EVIDENCE_TYPES:
                raise ValueError(
                    "operation experience requires real result evidence: "
                    "Observation, Outcome or CommunicationExperience"
                )

        identity = {
            "subject_id": self.subject_id,
            "problem_type": request.problem_type.strip(),
            "method_path": [item.strip() for item in request.method_path],
            "result_summary": request.result_summary.strip(),
            "applicability": request.applicability,
            "cost": request.cost,
            "misses": [item.strip() for item in request.misses],
            "positive_case_refs": [
                [ref.object_id, ref.revision] for ref in positive
            ],
            "negative_case_refs": [
                [ref.object_id, ref.revision] for ref in negative
            ],
        }
        object_id = _stable_id("opx", identity)
        try:
            existing = self.store.get_payload(object_id, revision=1)
        except StoreError as exc:
            if exc.code == ErrorCode.NOT_FOUND:
                existing = None
            else:
                raise
        if existing is not None:
            if self.index is not None:
                self.index.catch_up()
            return OperationExperienceCommit(
                object_id=object_id,
                world_revision=int(self.store.current_world_revision()),
                reused_existing=True,
            )

        experience = OperationExperience(
            object_id=object_id,
            subject_id=self.subject_id,
            learned_at=learned,
            recorded_at=learned,
            source_refs=[
                SourceRef(object_id=ref.object_id, revision=ref.revision)
                for ref in all_refs
            ],
            created_by="periodic_review:resident_ai",
            problem_type=request.problem_type.strip(),
            method_path=[item.strip() for item in request.method_path],
            applicability=dict(request.applicability),
            cost=dict(request.cost),
            result_summary=request.result_summary.strip(),
            misses=[item.strip() for item in request.misses],
            positive_case_refs=list(positive),
            negative_case_refs=list(negative),
            experience_state="candidate",
            metadata={
                "dimension": OPERATION_EXPERIENCE_DIMENSION,
                "review_generated": True,
                "auto_promoted_to_strategy": False,
            },
        )
        experience_ref = ObjectRef(object_id=object_id, revision=1)
        dependencies = [
            Dependency(
                object_id=_stable_id(
                    "dep_opx",
                    object_id,
                    1,
                    ref.object_id,
                    ref.revision,
                    "positive" if ref in positive else "negative",
                ),
                subject_id=self.subject_id,
                learned_at=learned,
                recorded_at=learned,
                created_by="periodic_review:experience_dependency",
                dependent_ref=experience_ref,
                dependency_ref=ref,
                dependency_type=(
                    "operation_experience_positive_case"
                    if ref in positive
                    else "operation_experience_negative_case"
                ),
            )
            for ref in all_refs
        ]
        operation_id = _stable_id("op_commit_experience", object_id)
        result = self.store.commit(
            [experience, *dependencies],
            OperationRequest(
                operation_id=operation_id,
                operation_name="review.commit_operation_experience",
                arguments={
                    "problem_type": request.problem_type.strip(),
                    "positive_case_count": len(positive),
                    "negative_case_count": len(negative),
                    "experience_state": "candidate",
                },
                expected_world_revision=self._expected_revision_for_retry(operation_id),
                reason=(
                    "persist resident-AI operational lesson grounded in real result evidence"
                ),
                idempotency_key=f"operation-experience:{object_id}",
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        if self.index is not None:
            self.index.catch_up()
        return OperationExperienceCommit(
            object_id=object_id,
            world_revision=result.world_revision,
            reused_existing=result.idempotent_replay,
        )


class PeriodicReviewService:
    """Mechanical due-check, review input selection and durable review checkpoint."""

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

    @property
    def checkpoint_object_id(self) -> str:
        return _stable_id("sum_periodic_review", self.subject_id)

    def _latest_checkpoint(self) -> dict[str, Any] | None:
        try:
            return self.store.get_payload(self.checkpoint_object_id)
        except StoreError as exc:
            if exc.code == ErrorCode.NOT_FOUND:
                return None
            raise

    def _expected_revision_for_retry(self, operation_id: str) -> int:
        expected = int(self.store.current_world_revision())
        try:
            previous = self.store.operation_record(operation_id)
        except StoreError as exc:
            if exc.code == ErrorCode.NOT_FOUND:
                return expected
            raise
        return int(previous["expected_world_revision"])

    def prepare_if_due(
        self,
        *,
        reviewed_at: datetime,
        policy: PeriodicReviewPolicy | None = None,
    ) -> PeriodicReviewInput | None:
        policy = policy or PeriodicReviewPolicy()
        reviewed = as_utc(reviewed_at, "reviewed_at")
        checkpoint = self._latest_checkpoint()

        from_revision = 0
        if checkpoint is not None:
            metadata = checkpoint.get("metadata")
            if not isinstance(metadata, Mapping):
                raise ValueError("periodic review checkpoint metadata is invalid")
            from_revision = int(metadata.get("reviewed_through_world_revision", -1))
            if from_revision < 0:
                raise ValueError("periodic review checkpoint is missing reviewed-through revision")
            last_completed = _parse_time(
                checkpoint.get("learned_at"),
                "checkpoint.learned_at",
            )
            next_due = last_completed + timedelta(
                seconds=policy.minimum_interval_seconds
            )
            if reviewed < next_due:
                return None

        commits = self.store.triggerable_commits_after(
            from_revision,
            limit=policy.max_triggerable_commits + 1,
        )
        if not commits:
            return None

        commit_limit_hit = len(commits) > policy.max_triggerable_commits
        commits = commits[: policy.max_triggerable_commits]
        commit_revisions = [int(item["world_revision"]) for item in commits]
        source_class_by_revision = {
            int(item["world_revision"]): SourceClass(str(item["source_class"]))
            for item in commits
        }

        # This read is intentionally much wider than the model package cap. We group
        # by world commit and never checkpoint through a partially included commit.
        rows = self.store.revisions_after(
            from_revision,
            limit=max(5000, policy.max_source_objects * 50),
        )
        grouped: dict[int, list[PeriodicReviewItem]] = {}
        allowed_revisions = set(commit_revisions)
        for row in rows:
            world_revision = int(row["world_revision"])
            if world_revision not in allowed_revisions:
                continue
            object_type = ObjectType(str(row["object_type"]))
            if object_type in _REVIEW_INPUT_SKIP_TYPES:
                continue
            payload = self.store.get_payload(
                str(row["object_id"]),
                revision=int(row["revision"]),
            )
            grouped.setdefault(world_revision, []).append(
                PeriodicReviewItem(
                    object_ref=ObjectRef(
                        object_id=str(row["object_id"]),
                        revision=int(row["revision"]),
                    ),
                    object_type=object_type,
                    subject_id=str(payload["subject_id"]),
                    world_revision=world_revision,
                    source_class=source_class_by_revision[world_revision],
                    learned_at=_parse_time(payload.get("learned_at"), "learned_at"),
                    salient=_compact_salient(payload),
                )
            )

        selected: list[PeriodicReviewItem] = []
        reviewed_through = from_revision
        included_commits = 0
        for world_revision in commit_revisions:
            group = grouped.get(world_revision, [])
            # A non-maintenance commit with only skipped graph objects is still a
            # mechanically processed commit. Advance through it, but do not pretend
            # it contributed semantic review items.
            if not group:
                reviewed_through = world_revision
                included_commits += 1
                continue

            if selected and len(selected) + len(group) > policy.max_source_objects:
                break
            selected.extend(group)
            reviewed_through = world_revision
            included_commits += 1
            if len(selected) >= policy.max_source_objects:
                break

        if not selected:
            # Do not create a model review with no semantic input. In the unlikely
            # case of graph-only triggerable commits, leave them for a later commit
            # carrying an inspectable semantic object.
            return None

        truncated = (
            commit_limit_hit
            or included_commits < len(commit_revisions)
            or reviewed_through < commit_revisions[-1]
        )
        return PeriodicReviewInput(
            subject_id=self.subject_id,
            from_world_revision_exclusive=from_revision,
            reviewed_through_world_revision=reviewed_through,
            prepared_at=reviewed,
            items=tuple(selected),
            triggerable_commit_count=included_commits,
            truncated=truncated,
        )

    def commit_checkpoint(
        self,
        prepared: PeriodicReviewInput,
        *,
        review_note: str,
        completed_at: datetime,
        model_silenced: bool = False,
    ) -> ReviewCheckpointCommit:
        prepared = PeriodicReviewInput.model_validate(
            prepared.model_dump(mode="python", round_trip=True)
        )
        if prepared.subject_id != self.subject_id:
            raise ValueError("review input belongs to another subject")
        note = review_note.strip()
        if not note:
            raise ValueError("review checkpoint note must not be blank")
        completed = as_utc(completed_at, "completed_at")

        latest = self._latest_checkpoint()
        expected_refs = [
            [ref.object_id, int(ref.revision or 0)]
            for ref in prepared.source_refs
        ]
        if latest is not None:
            metadata = latest.get("metadata")
            latest_through = (
                int(metadata.get("reviewed_through_world_revision", -1))
                if isinstance(metadata, Mapping)
                else -1
            )
            if latest_through == prepared.reviewed_through_world_revision:
                latest_refs = [
                    [str(ref["object_id"]), int(ref["revision"])]
                    for ref in latest.get("source_refs") or []
                ]
                if latest_refs != expected_refs or str(latest.get("content") or "") != note:
                    raise ValueError(
                        "same periodic-review range already checkpointed with different content"
                    )
                return ReviewCheckpointCommit(
                    object_id=self.checkpoint_object_id,
                    revision=int(latest["revision"]),
                    reviewed_through_world_revision=latest_through,
                    world_revision=int(self.store.current_world_revision()),
                    reused_existing=True,
                )

        revision = 1 if latest is None else int(latest["revision"]) + 1
        checkpoint_time = TemporalExtent.point(completed)
        summary = Summary(
            object_id=self.checkpoint_object_id,
            subject_id=self.subject_id,
            revision=revision,
            occurred=checkpoint_time,
            learned_at=completed,
            recorded_at=completed,
            source_refs=[
                SourceRef(object_id=ref.object_id, revision=ref.revision)
                for ref in prepared.source_refs
            ],
            created_by="periodic_review:checkpoint",
            summary_time=checkpoint_time,
            granularity="periodic_review",
            content=note,
            source_world_revision=prepared.reviewed_through_world_revision,
            coverage={
                "from_world_revision_exclusive": prepared.from_world_revision_exclusive,
                "reviewed_through_world_revision": (
                    prepared.reviewed_through_world_revision
                ),
                "source_count": len(prepared.items),
                "triggerable_commit_count": prepared.triggerable_commit_count,
                "truncated": prepared.truncated,
            },
            summary_status=SummaryStatus.CURRENT,
            metadata={
                "dimension": "dim:ai_periodic_review",
                "summary_kind": REVIEW_CHECKPOINT_KIND,
                "reviewed_from_world_revision_exclusive": (
                    prepared.from_world_revision_exclusive
                ),
                "reviewed_through_world_revision": (
                    prepared.reviewed_through_world_revision
                ),
                "model_silenced": bool(model_silenced),
                "review_checkpoint_only": True,
                "not_cognition_truth": True,
            },
        )
        checkpoint_ref = ObjectRef(
            object_id=self.checkpoint_object_id,
            revision=revision,
        )
        dependencies = [
            Dependency(
                object_id=_stable_id(
                    "dep_review_checkpoint",
                    self.checkpoint_object_id,
                    revision,
                    ref.object_id,
                    ref.revision,
                ),
                subject_id=self.subject_id,
                learned_at=completed,
                recorded_at=completed,
                created_by="periodic_review:checkpoint_dependency",
                dependent_ref=checkpoint_ref,
                dependency_ref=ref,
                dependency_type="periodic_review_checkpoint_inspected_source",
            )
            for ref in prepared.source_refs
        ]
        operation_id = _stable_id(
            "op_review_checkpoint",
            self.subject_id,
            prepared.from_world_revision_exclusive,
            prepared.reviewed_through_world_revision,
            expected_refs,
        )
        result = self.store.commit(
            [summary, *dependencies],
            OperationRequest(
                operation_id=operation_id,
                operation_name="review.commit_checkpoint",
                arguments={
                    "from_world_revision_exclusive": (
                        prepared.from_world_revision_exclusive
                    ),
                    "reviewed_through_world_revision": (
                        prepared.reviewed_through_world_revision
                    ),
                    "source_count": len(prepared.items),
                    "truncated": prepared.truncated,
                },
                expected_world_revision=self._expected_revision_for_retry(operation_id),
                reason="persist mechanical periodic-review completion checkpoint",
                idempotency_key=f"periodic-review-checkpoint:{operation_id}",
                source_class=SourceClass.MAINTENANCE,
                maintenance_class=MaintenanceClass.SUMMARY_REBUILD,
            ),
        )
        if self.index is not None:
            self.index.catch_up()
        return ReviewCheckpointCommit(
            object_id=self.checkpoint_object_id,
            revision=revision,
            reviewed_through_world_revision=prepared.reviewed_through_world_revision,
            world_revision=result.world_revision,
            reused_existing=result.idempotent_replay,
        )
