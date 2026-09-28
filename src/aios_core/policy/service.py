"""R6 adaptive cognitive policy implemented as ordinary versioned world objects.

This replaces the legacy parallel policy SQLite database. Policy history lives in the
same WorldStore as facts, cognition, outcomes and experience. Deterministic code only
enforces authorization, ranges, versions and rollback integrity; the resident model
supplies the evidence-grounded reason for a cognitive-policy change.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import ErrorCode, MaintenanceClass, ObjectType, PolicyClass, SourceClass
from aios_core.contracts.models import CognitivePolicy, Dependency, EvidenceCoverage, EvidenceSet
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import KnowledgeWindow, TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import (
    canonical_json_dumps,
    canonical_request_identity,
)
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError

POLICY_DIMENSION = "dim:ai_cognitive_policy"

_REAL_POLICY_CASE_TYPES: frozenset[ObjectType] = frozenset({
    ObjectType.OBSERVATION,
    ObjectType.OUTCOME,
    ObjectType.OPERATION_EXPERIENCE,
    ObjectType.COMMUNICATION_EXPERIENCE,
})
_EVALUATION_WINDOW_RE = re.compile(r"^(?P<value>[1-9][0-9]*)(?P<unit>[mhdw])$")


def evaluation_due_at(changed_at: datetime, evaluation_window: str) -> datetime:
    """Resolve the bounded R6 evaluation window into a deterministic due instant."""

    changed = as_utc(changed_at, "changed_at")
    raw = evaluation_window.strip().lower()
    match = _EVALUATION_WINDOW_RE.fullmatch(raw)
    if match is None:
        raise ValueError(
            "evaluation_window must use a bounded duration such as 30m, 24h, 7d, or 4w"
        )
    value = int(match.group("value"))
    unit = match.group("unit")
    delta = {
        "m": timedelta(minutes=value),
        "h": timedelta(hours=value),
        "d": timedelta(days=value),
        "w": timedelta(weeks=value),
    }[unit]
    return changed + delta


def _policy_arguments(
    policy_id: str,
    version: int,
    scope: str,
    policy_class: str,
    canonical_request_sha256: str | None,
) -> dict[str, Any]:
    """Single source of truth for the durable policy operation arguments.

    A policy update/rollback idempotency key is derived from the complete
    canonical request, so this digest is what separates an identical recovered
    replay from a changed change under the same key. ``version`` and ``scope``
    are left out of the fingerprinted arguments whenever a canonical digest is
    present: for an update or a rollback they are read from the *current* policy
    revision, so embedding them would make a mechanically identical recovered
    replay fingerprint differently from the original application.
    """

    if canonical_request_sha256 is not None:
        return {
            "policy_id": policy_id,
            "policy_class": policy_class,
            "canonical_request_sha256": canonical_request_sha256,
        }
    return {
        "policy_id": policy_id,
        "version": version,
        "scope": scope,
        "policy_class": policy_class,
    }


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _require_pinned(refs: Sequence[ObjectRef]) -> None:
    for ref in refs:
        if ref.revision is None:
            raise ValueError("policy evidence refs must pin exact revisions")


class CognitivePolicyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_id: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    policy_class: PolicyClass
    default_value: Any
    current_value: Any
    allowed_range_or_choices: Any = None
    mutable_by_ai: bool = False
    reason: str = Field(min_length=1)
    evidence_refs: tuple[ObjectRef, ...] = ()
    changed_by: str = Field(min_length=1)
    evaluation_window: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_request(self) -> "CognitivePolicyCreateRequest":
        _require_pinned(self.evidence_refs)
        return self


class CognitivePolicyUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_id: str = Field(min_length=1)
    current_value: Any
    reason: str = Field(min_length=1)
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    changed_by: str = Field(default="resident_ai", min_length=1)
    evaluation_window: str | None = None

    @model_validator(mode="after")
    def validate_request(self) -> "CognitivePolicyUpdateRequest":
        _require_pinned(self.evidence_refs)
        return self


@dataclass(frozen=True, slots=True)
class PolicyReceipt:
    policy_id: str
    object_id: str
    revision: int
    previous_version: int | None
    rollback_pointer: int | None
    world_revision: int


class CognitivePolicyRegistry:
    """Append-forward R6 policy ledger over the canonical WorldStore."""

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

    def _object_id(self, policy_id: str) -> str:
        return _stable_id("policy", self.subject_id, policy_id.strip())

    def _validate_refs(
        self,
        refs: Sequence[ObjectRef],
        *,
        require_real_result: bool = False,
    ) -> None:
        _require_pinned(refs)
        for ref in refs:
            payload = self.store.get_payload(ref.object_id, revision=ref.revision)
            ref_subject = str(payload.get("subject_id") or "")
            if ref_subject != self.subject_id:
                raise ValueError(
                    "policy evidence crosses the runtime subject scope: "
                    f"{ref.object_id}@{ref.revision} belongs to {ref_subject!r}"
                )
            latest = self.store.get_payload(ref.object_id)
            if (int(latest["revision"]) != ref.revision
                    or str(latest.get("status") or "active") != "active"):
                raise ValueError("policy learning requires current, active real-result evidence")
            if not require_real_result:
                continue
            object_type = str(payload.get("object_type") or "")
            if object_type not in {item.value for item in _REAL_POLICY_CASE_TYPES}:
                raise ValueError(
                    "AI policy changes require real-result evidence; "
                    f"{object_type!r} is not an allowed policy case type"
                )
            if object_type == ObjectType.OBSERVATION.value:
                metadata = payload.get("metadata")
                if not isinstance(metadata, dict):
                    metadata = {}
                role = str(metadata.get("role") or "").strip().lower()
                created_by = str(payload.get("created_by") or "").strip().lower()
                if role == "assistant" or created_by == "conversation_ingest:assistant":
                    raise ValueError(
                        "assistant-generated conversation output is not real-result "
                        "evidence for CognitivePolicy learning"
                    )

    def _evidence_set(
        self,
        *,
        policy_id: str,
        version: int,
        refs: Sequence[ObjectRef],
        changed_at: datetime,
        purpose: str,
    ) -> EvidenceSet | None:
        if not refs:
            return None
        evidence_id = _stable_id(
            "evs_policy", self.subject_id, policy_id, version,
            tuple((r.object_id, r.revision) for r in refs), changed_at.isoformat(),
        )
        return EvidenceSet(
            object_id=evidence_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(changed_at),
            learned_at=changed_at,
            recorded_at=changed_at,
            source_refs=[SourceRef(object_id=r.object_id, revision=r.revision) for r in refs],
            created_by="cognitive_policy:evidence",
            purpose=purpose,
            knowledge_window=KnowledgeWindow(
                knowledge_cutoff=changed_at,
                world_revision=int(self.store.current_world_revision()),
            ),
            member_refs=list(refs),
            support_refs=list(refs),
            selection_method="policy_change_pinned_world_evidence",
            coverage=EvidenceCoverage(
                expected_count=len(refs),
                observed_count=len(refs),
                coverage_ratio=1.0,
            ),
            metadata={"dimension": POLICY_DIMENSION, "policy_id": policy_id},
        )

    def _commit(
        self,
        policy: CognitivePolicy,
        *,
        evidence: EvidenceSet | None,
        actor_is_ai: bool,
        operation_name: str,
        expected_world_revision: int,
        idempotency_key: str | None = None,
        canonical_request_sha256: str | None = None,
    ) -> PolicyReceipt:
        objects: list[Any] = [policy]
        policy_ref = ObjectRef(object_id=policy.object_id, revision=policy.revision)
        if evidence is not None:
            evidence_ref = ObjectRef(object_id=evidence.object_id, revision=1)
            objects.insert(0, evidence)
            objects.append(
                Dependency(
                    object_id=_stable_id("dep", policy.object_id, policy.revision, evidence.object_id, 1),
                    subject_id=self.subject_id,
                    learned_at=policy.changed_at,
                    recorded_at=policy.changed_at,
                    created_by="cognitive_policy:dependency",
                    dependent_ref=policy_ref,
                    dependency_ref=evidence_ref,
                    dependency_type="policy_version_uses_evidence_set",
                )
            )
            for ref in policy.evidence_refs:
                objects.append(
                    Dependency(
                        object_id=_stable_id("dep", evidence.object_id, 1, ref.object_id, ref.revision),
                        subject_id=self.subject_id,
                        learned_at=policy.changed_at,
                        recorded_at=policy.changed_at,
                        created_by="cognitive_policy:dependency",
                        dependent_ref=evidence_ref,
                        dependency_ref=ref,
                        dependency_type="policy_evidence_set_contains_source",
                    )
                )

        source_class = SourceClass.AI_COGNITION if actor_is_ai else SourceClass.MAINTENANCE
        op = OperationRequest(
            operation_name=operation_name,
            arguments=_policy_arguments(
                policy.policy_id,
                policy.version,
                policy.scope,
                policy.policy_class.value,
                canonical_request_sha256,
            ),
            expected_world_revision=expected_world_revision,
            reason=policy.reason,
            idempotency_key=idempotency_key
            or f"policy:{policy.object_id}:{policy.revision}",
            source_class=source_class,
            maintenance_class=(None if actor_is_ai else MaintenanceClass.POLICY_SYNC),
        )
        result = self.store.commit_or_replay(objects, op)
        if self.index is not None:
            self.index.catch_up()
        receipt_policy = policy
        if result.idempotent_replay:
            # An exact recovered replay reports the ORIGINAL durable identity,
            # never the freshly computed next version.
            replayed = next(
                (
                    int(revision)
                    for object_id, revision in result.object_refs
                    if str(object_id) == policy.object_id
                ),
                None,
            )
            if replayed is not None:
                receipt_policy = CognitivePolicy.model_validate(
                    self.store.get_payload(policy.object_id, revision=replayed)
                )
        return PolicyReceipt(
            policy_id=receipt_policy.policy_id,
            object_id=receipt_policy.object_id,
            revision=receipt_policy.revision,
            previous_version=receipt_policy.previous_version,
            rollback_pointer=receipt_policy.rollback_pointer,
            world_revision=result.world_revision,
        )

    def _exact_replay_receipt(
        self,
        *,
        object_id: str,
        revision: int,
        operation_name: str,
        idempotency_key: str,
        actor_is_ai: bool,
        request_identity: str,
        scope: str,
        policy_class: str,
        reason: str,
    ) -> PolicyReceipt | None:
        """Return the original receipt when ``idempotency_key`` already holds this
        exact request.

        The durable store verifies the unchanged request fingerprint before any
        receipt is returned, so a changed request under the same key stays a hard
        conflict and ``None`` is returned instead.
        """
        probe = OperationRequest(
            operation_name=operation_name,
            arguments=_policy_arguments(
                str(self.store.get_payload(object_id).get("policy_id") or ""),
                revision,
                scope,
                policy_class,
                request_identity,
            ),
            expected_world_revision=int(self.store.current_world_revision()),
            reason=reason,
            idempotency_key=idempotency_key,
            source_class=(
                SourceClass.AI_COGNITION if actor_is_ai else SourceClass.MAINTENANCE
            ),
        )
        try:
            result = self.store.replay_exact_operation(probe)
        except StoreError as exc:
            # A different registration of an existing policy_id keeps raising the
            # domain error in `register`; corrupt or skewed durable state does not.
            if exc.code is not ErrorCode.IDEMPOTENCY_CONFLICT:
                raise
            return None
        if result is None:
            return None
        if self.index is not None:
            self.index.catch_up()
        durable = CognitivePolicy.model_validate(
            self.store.get_payload(object_id, revision=revision)
        )
        return PolicyReceipt(
            policy_id=durable.policy_id,
            object_id=durable.object_id,
            revision=durable.revision,
            previous_version=durable.previous_version,
            rollback_pointer=durable.rollback_pointer,
            world_revision=result.world_revision,
        )

    def register(
        self,
        request: CognitivePolicyCreateRequest,
        *,
        changed_at: datetime,
        actor_is_ai: bool = False,
    ) -> PolicyReceipt:
        expected_world_revision = int(self.store.current_world_revision())
        changed = as_utc(changed_at, "changed_at")
        if actor_is_ai:
            if (
                request.policy_class is not PolicyClass.COGNITIVE_POLICY
                or not request.mutable_by_ai
            ):
                raise PermissionError(
                    "resident AI may register only AI-mutable cognitive policies"
                )
            if not request.evidence_refs:
                raise PermissionError(
                    "resident AI policy registration requires real-result evidence"
                )
        policy_id = request.policy_id.strip()
        object_id = self._object_id(policy_id)
        register_identity = canonical_request_identity(
            "policy.register",
            request.model_dump(mode="json"),
            changed.isoformat(),
        )
        try:
            self.store.get_payload(object_id)
        except StoreError as exc:
            if exc.code is not ErrorCode.NOT_FOUND:
                raise
        else:
            replay = self._exact_replay_receipt(
                object_id=object_id,
                revision=1,
                operation_name="policy.register",
                idempotency_key=f"policy:{object_id}:1",
                actor_is_ai=actor_is_ai,
                request_identity=register_identity,
                scope=request.scope.strip(),
                policy_class=request.policy_class.value,
                reason=request.reason.strip(),
            )
            if replay is None:
                raise ValueError(f"policy already registered: {policy_id}")
            return replay
        self._validate_refs(
            request.evidence_refs,
            require_real_result=actor_is_ai,
        )
        next_evaluation_at = evaluation_due_at(
            changed,
            request.evaluation_window,
        )
        evidence = self._evidence_set(
            policy_id=policy_id,
            version=1,
            refs=request.evidence_refs,
            changed_at=changed,
            purpose=f"register policy {policy_id}",
        )
        policy = CognitivePolicy(
            object_id=object_id,
            subject_id=self.subject_id,
            revision=1,
            occurred=TemporalExtent.point(changed),
            learned_at=changed,
            recorded_at=changed,
            source_refs=[SourceRef(object_id=r.object_id, revision=r.revision) for r in request.evidence_refs],
            created_by=f"cognitive_policy:{request.changed_by.strip()}",
            policy_id=policy_id,
            scope=request.scope.strip(),
            policy_class=request.policy_class,
            default_value=request.default_value,
            current_value=request.current_value,
            allowed_range_or_choices=request.allowed_range_or_choices,
            mutable_by_ai=request.mutable_by_ai,
            reason=request.reason.strip(),
            evidence_refs=list(request.evidence_refs),
            changed_by=request.changed_by.strip(),
            changed_at=changed,
            version=1,
            previous_version=None,
            rollback_pointer=None,
            evaluation_window=request.evaluation_window.strip(),
            metadata={
                "dimension": POLICY_DIMENSION,
                "next_evaluation_at": next_evaluation_at.isoformat(),
            },
        )
        return self._commit(
            policy,
            evidence=evidence,
            actor_is_ai=actor_is_ai,
            operation_name="policy.register",
            expected_world_revision=expected_world_revision,
            canonical_request_sha256=register_identity,
        )

    def latest(self, policy_id: str) -> CognitivePolicy | None:
        object_id = self._object_id(policy_id)
        try:
            payload = self.store.get_payload(object_id)
        except StoreError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            raise
        return CognitivePolicy.model_validate(payload)

    def get(self, policy_id: str, version: int) -> CognitivePolicy | None:
        object_id = self._object_id(policy_id)
        try:
            payload = self.store.get_payload(object_id, revision=int(version))
        except StoreError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return None
            raise
        return CognitivePolicy.model_validate(payload)

    def history(self, policy_id: str) -> tuple[CognitivePolicy, ...]:
        latest = self.latest(policy_id)
        if latest is None:
            return ()
        return tuple(
            CognitivePolicy.model_validate(
                self.store.get_payload(latest.object_id, revision=revision)
            )
            for revision in range(1, latest.revision + 1)
        )

    def list_current(self) -> tuple[CognitivePolicy, ...]:
        items = [
            CognitivePolicy.model_validate(payload)
            for payload in self.store.list_payloads(
                object_type=ObjectType.COGNITIVE_POLICY,
                subject_id=self.subject_id,
            )
        ]
        items.sort(key=lambda item: (item.scope, item.policy_id))
        return tuple(items)

    def is_effective(self, policy: CognitivePolicy) -> bool:
        valid = policy.status == "active"
        if valid:
            try:
                self._validate_refs(policy.evidence_refs)
            except (ValueError, StoreError):
                valid = False
        if not valid and policy.policy_class is not PolicyClass.COGNITIVE_POLICY:
            raise PermissionError("non-cognitive policy requires independent review")
        return valid

    def effective_value(self, policy_id: str, default: Any = None) -> Any:
        current = self.latest(policy_id)
        if current is None:
            return default
        if not self.is_effective(current):
            return default
        return current.current_value

    def due_for_evaluation(self, *, now: datetime) -> tuple[CognitivePolicy, ...]:
        moment = as_utc(now, "now")
        due: list[CognitivePolicy] = []
        for item in self.list_current():
            raw_due = item.metadata.get("next_evaluation_at")
            try:
                due_at = (
                    as_utc(
                        datetime.fromisoformat(str(raw_due).replace("Z", "+00:00")),
                        "next_evaluation_at",
                    )
                    if raw_due is not None
                    else evaluation_due_at(item.changed_at, item.evaluation_window)
                )
            except (TypeError, ValueError):
                # Invalid policy evaluation metadata is not silently accepted.
                raise ValueError(
                    f"invalid evaluation schedule for policy {item.policy_id!r}"
                )
            if due_at <= moment:
                due.append(item)
        due.sort(key=lambda item: (item.changed_at, item.policy_id))
        return tuple(due)

    def update(
        self,
        request: CognitivePolicyUpdateRequest,
        *,
        changed_at: datetime,
        actor_is_ai: bool = True,
    ) -> PolicyReceipt:
        expected_world_revision = int(self.store.current_world_revision())
        changed = as_utc(changed_at, "changed_at")
        current = self.latest(request.policy_id)
        if current is None:
            raise KeyError(f"unknown policy: {request.policy_id}")
        if actor_is_ai:
            if current.policy_class is not PolicyClass.COGNITIVE_POLICY or not current.mutable_by_ai:
                raise PermissionError(f"policy is not AI-mutable: {request.policy_id}")
            if not request.evidence_refs:
                raise PermissionError("AI policy changes require pinned evidence")
        self._validate_refs(
            request.evidence_refs,
            require_real_result=actor_is_ai,
        )
        version = current.revision + 1
        object_id = self._object_id(request.policy_id)
        update_identity = canonical_request_identity(
            "policy.update",
            request.model_dump(mode="json"),
            changed.isoformat(),
        )
        evaluation_window = (
            request.evaluation_window.strip()
            if request.evaluation_window is not None and request.evaluation_window.strip()
            else current.evaluation_window
        )
        next_evaluation_at = evaluation_due_at(changed, evaluation_window)
        evidence = self._evidence_set(
            policy_id=current.policy_id,
            version=version,
            refs=request.evidence_refs,
            changed_at=changed,
            purpose=f"support policy update {current.policy_id}@{version}",
        )
        policy = CognitivePolicy.model_validate(
            {
                **current.model_dump(mode="python", round_trip=True),
                "revision": version,
                "occurred": TemporalExtent.point(changed),
                "learned_at": changed,
                "recorded_at": changed,
                "source_refs": [SourceRef(object_id=r.object_id, revision=r.revision) for r in request.evidence_refs],
                "created_by": f"cognitive_policy:{request.changed_by.strip()}",
                "current_value": request.current_value,
                "reason": request.reason.strip(),
                "evidence_refs": list(request.evidence_refs),
                "changed_by": request.changed_by.strip(),
                "changed_at": changed,
                "version": version,
                "previous_version": current.version,
                "rollback_pointer": current.version,
                "evaluation_window": evaluation_window,
                "status": "active",
                "metadata": {
                    **dict(current.metadata),
                    "dimension": POLICY_DIMENSION,
                    "next_evaluation_at": next_evaluation_at.isoformat(),
                },
            }
        )
        return self._commit(
            policy,
            evidence=evidence,
            actor_is_ai=actor_is_ai,
            operation_name="policy.update",
            expected_world_revision=expected_world_revision,
            # The old key pinned the state-derived next revision, which made an
            # identical recovered replay mint a second policy version. Keying on
            # the complete canonical request keeps the key stable across replay
            # while a changed change under the same key still fails closed.
            idempotency_key=f"policy-update:{object_id}:{update_identity[:24]}",
            canonical_request_sha256=update_identity,
        )

    def rollback(
        self,
        policy_id: str,
        target_version: int,
        *,
        reason: str,
        evidence_refs: Sequence[ObjectRef],
        changed_by: str,
        changed_at: datetime,
        actor_is_ai: bool = True,
    ) -> PolicyReceipt:
        expected_world_revision = int(self.store.current_world_revision())
        current = self.latest(policy_id)
        target = self.get(policy_id, target_version)
        if current is None or target is None:
            raise KeyError(f"unknown policy/version: {policy_id}@{target_version}")
        if target.version >= current.version:
            raise ValueError("rollback target must be older than current policy")
        if actor_is_ai and (
            current.policy_class is not PolicyClass.COGNITIVE_POLICY
            or not current.mutable_by_ai
        ):
            raise PermissionError(f"policy is not AI-mutable: {policy_id}")
        refs = tuple(evidence_refs)
        if actor_is_ai and not refs:
            raise PermissionError("AI policy rollback requires pinned evidence")
        self._validate_refs(refs, require_real_result=actor_is_ai)
        changed = as_utc(changed_at, "changed_at")
        version = current.revision + 1
        object_id = self._object_id(policy_id)
        # Keyed on the complete canonical request instead of the state-derived
        # next revision, so an identical recovered replay cannot mint a second
        # rollback version while a changed rollback still fails closed.
        rollback_identity = canonical_request_identity(
            "policy.rollback",
            {
                "policy_id": policy_id,
                "target_version": int(target_version),
                "reason": reason.strip(),
                "evidence_refs": [
                    {"object_id": r.object_id, "revision": r.revision} for r in refs
                ],
                "changed_by": changed_by.strip(),
                "actor_is_ai": bool(actor_is_ai),
            },
            changed.isoformat(),
        )
        next_evaluation_at = evaluation_due_at(
            changed,
            current.evaluation_window,
        )
        evidence = self._evidence_set(
            policy_id=current.policy_id,
            version=version,
            refs=refs,
            changed_at=changed,
            purpose=f"support rollback {current.policy_id}@{current.version}->{target.version}",
        )
        policy = CognitivePolicy.model_validate(
            {
                **current.model_dump(mode="python", round_trip=True),
                "revision": version,
                "occurred": TemporalExtent.point(changed),
                "learned_at": changed,
                "recorded_at": changed,
                "source_refs": [
                    SourceRef(object_id=r.object_id, revision=r.revision)
                    for r in refs
                ],
                "created_by": f"cognitive_policy:{changed_by.strip()}",
                "current_value": target.current_value,
                "reason": reason.strip(),
                "evidence_refs": list(refs),
                "changed_by": changed_by.strip(),
                "changed_at": changed,
                "version": version,
                "previous_version": current.version,
                "rollback_pointer": target.version,
                "evaluation_window": current.evaluation_window,
                "status": "active",
                "metadata": {
                    **dict(current.metadata),
                    "dimension": POLICY_DIMENSION,
                    "next_evaluation_at": next_evaluation_at.isoformat(),
                },
            }
        )
        return self._commit(
            policy,
            evidence=evidence,
            actor_is_ai=actor_is_ai,
            operation_name="policy.rollback",
            expected_world_revision=expected_world_revision,
            idempotency_key=f"policy-rollback:{object_id}:{rollback_identity[:24]}",
            canonical_request_sha256=rollback_identity,
        )
