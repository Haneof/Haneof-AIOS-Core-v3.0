"""R6 adaptive cognitive policy implemented as ordinary versioned world objects.

This replaces the legacy parallel policy SQLite database. Policy history lives in the
same WorldStore as facts, cognition, outcomes and experience. Deterministic code only
enforces authorization, ranges, versions and rollback integrity; the resident model
supplies the evidence-grounded reason for a cognitive-policy change.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import MaintenanceClass, ObjectType, PolicyClass, SourceClass
from aios_core.contracts.models import CognitivePolicy, Dependency, EvidenceCoverage, EvidenceSet
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import KnowledgeWindow, TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore

POLICY_DIMENSION = "dim:ai_cognitive_policy"


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

    def _validate_refs(self, refs: Sequence[ObjectRef]) -> None:
        _require_pinned(refs)
        for ref in refs:
            self.store.get_payload(ref.object_id, revision=ref.revision)

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
            arguments={
                "policy_id": policy.policy_id,
                "version": policy.version,
                "scope": policy.scope,
                "policy_class": policy.policy_class.value,
            },
            expected_world_revision=int(self.store.current_world_revision()),
            reason=policy.reason,
            idempotency_key=f"policy:{policy.object_id}:{policy.revision}",
            source_class=source_class,
            maintenance_class=(None if actor_is_ai else MaintenanceClass.POLICY_SYNC),
        )
        result = self.store.commit(objects, op)
        if self.index is not None:
            self.index.catch_up()
        return PolicyReceipt(
            policy_id=policy.policy_id,
            object_id=policy.object_id,
            revision=policy.revision,
            previous_version=policy.previous_version,
            rollback_pointer=policy.rollback_pointer,
            world_revision=result.world_revision,
        )

    def register(
        self,
        request: CognitivePolicyCreateRequest,
        *,
        changed_at: datetime,
    ) -> PolicyReceipt:
        changed = as_utc(changed_at, "changed_at")
        policy_id = request.policy_id.strip()
        object_id = self._object_id(policy_id)
        try:
            self.store.get_payload(object_id)
        except Exception:
            pass
        else:
            raise ValueError(f"policy already registered: {policy_id}")
        self._validate_refs(request.evidence_refs)
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
            metadata={"dimension": POLICY_DIMENSION},
        )
        return self._commit(
            policy,
            evidence=evidence,
            actor_is_ai=False,
            operation_name="policy.register",
        )

    def latest(self, policy_id: str) -> CognitivePolicy | None:
        object_id = self._object_id(policy_id)
        try:
            payload = self.store.get_payload(object_id)
        except Exception:
            return None
        return CognitivePolicy.model_validate(payload)

    def get(self, policy_id: str, version: int) -> CognitivePolicy | None:
        object_id = self._object_id(policy_id)
        try:
            payload = self.store.get_payload(object_id, revision=int(version))
        except Exception:
            return None
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

    def update(
        self,
        request: CognitivePolicyUpdateRequest,
        *,
        changed_at: datetime,
        actor_is_ai: bool = True,
    ) -> PolicyReceipt:
        changed = as_utc(changed_at, "changed_at")
        current = self.latest(request.policy_id)
        if current is None:
            raise KeyError(f"unknown policy: {request.policy_id}")
        if actor_is_ai:
            if current.policy_class is not PolicyClass.COGNITIVE_POLICY or not current.mutable_by_ai:
                raise PermissionError(f"policy is not AI-mutable: {request.policy_id}")
            if not request.evidence_refs:
                raise PermissionError("AI policy changes require pinned evidence")
        self._validate_refs(request.evidence_refs)
        version = current.revision + 1
        evaluation_window = (
            request.evaluation_window.strip()
            if request.evaluation_window is not None and request.evaluation_window.strip()
            else current.evaluation_window
        )
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
            }
        )
        return self._commit(
            policy,
            evidence=evidence,
            actor_is_ai=actor_is_ai,
            operation_name="policy.update",
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
        current = self.latest(policy_id)
        target = self.get(policy_id, target_version)
        if current is None or target is None:
            raise KeyError(f"unknown policy/version: {policy_id}@{target_version}")
        if target.version >= current.version:
            raise ValueError("rollback target must be older than current policy")
        refs = tuple(evidence_refs)
        request = CognitivePolicyUpdateRequest(
            policy_id=policy_id,
            current_value=target.current_value,
            reason=reason,
            evidence_refs=refs,
            changed_by=changed_by,
            evaluation_window=current.evaluation_window,
        )
        receipt = self.update(request, changed_at=changed_at, actor_is_ai=actor_is_ai)
        newest = self.latest(policy_id)
        assert newest is not None
        # update() points rollback_pointer at the immediately previous version. For an
        # explicit rollback, record the actual target in a final forward revision only
        # if it differs. This preserves append-only history and makes rollback auditable.
        if newest.rollback_pointer == target_version:
            return receipt
        changed = as_utc(changed_at, "changed_at")
        next_version = newest.revision + 1
        policy = CognitivePolicy.model_validate(
            {
                **newest.model_dump(mode="python", round_trip=True),
                "revision": next_version,
                "learned_at": changed,
                "recorded_at": changed,
                "changed_at": changed,
                "version": next_version,
                "previous_version": newest.version,
                "rollback_pointer": int(target_version),
                "reason": f"record explicit rollback target: {reason.strip()}",
            }
        )
        return self._commit(
            policy,
            evidence=None,
            actor_is_ai=actor_is_ai,
            operation_name="policy.rollback",
        )
