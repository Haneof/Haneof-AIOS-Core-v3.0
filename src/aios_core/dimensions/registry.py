"""AI-proposed dimension registration and lifecycle for AIOS v3.0.

The resident model decides whether a new observation axis is meaningful. This module
only enforces durable evidence, exact identity, legal lifecycle transitions and
resource-safe bookkeeping. It deliberately contains no "2 domains / 3 days / 70%"
semantic promotion gate.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import (
    DimensionLifecycle,
    MaintenanceClass,
    ObjectType,
    SourceClass,
)
from aios_core.contracts.models import (
    Dependency,
    DimensionDefinition,
    DimensionDerivation,
    EvidenceCoverage,
    EvidenceSet,
)
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import KnowledgeWindow, TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore


_TERMINAL = {
    DimensionLifecycle.MERGED,
    DimensionLifecycle.SPLIT,
    DimensionLifecycle.REJECTED,
    DimensionLifecycle.ARCHIVED,
}

_ALLOWED_TRANSITIONS: Mapping[DimensionLifecycle, frozenset[DimensionLifecycle]] = {
    DimensionLifecycle.CANDIDATE: frozenset({
        DimensionLifecycle.TRIAL,
        DimensionLifecycle.REVISED,
        DimensionLifecycle.REJECTED,
    }),
    DimensionLifecycle.TRIAL: frozenset({
        DimensionLifecycle.ACTIVE,
        DimensionLifecycle.REVISED,
        DimensionLifecycle.REJECTED,
        DimensionLifecycle.DORMANT,
    }),
    DimensionLifecycle.ACTIVE: frozenset({
        DimensionLifecycle.LOW_ACTIVITY,
        DimensionLifecycle.DORMANT,
        DimensionLifecycle.MERGED,
        DimensionLifecycle.SPLIT,
        DimensionLifecycle.REVISED,
        DimensionLifecycle.ARCHIVED,
    }),
    DimensionLifecycle.LOW_ACTIVITY: frozenset({
        DimensionLifecycle.ACTIVE,
        DimensionLifecycle.DORMANT,
        DimensionLifecycle.MERGED,
        DimensionLifecycle.REVISED,
        DimensionLifecycle.ARCHIVED,
    }),
    DimensionLifecycle.DORMANT: frozenset({
        DimensionLifecycle.REACTIVATED,
        DimensionLifecycle.MERGED,
        DimensionLifecycle.ARCHIVED,
    }),
    DimensionLifecycle.REACTIVATED: frozenset({
        DimensionLifecycle.ACTIVE,
        DimensionLifecycle.DORMANT,
    }),
    DimensionLifecycle.REVISED: frozenset({
        DimensionLifecycle.TRIAL,
        DimensionLifecycle.ACTIVE,
        DimensionLifecycle.DORMANT,
        DimensionLifecycle.ARCHIVED,
    }),
    DimensionLifecycle.MERGED: frozenset(),
    DimensionLifecycle.SPLIT: frozenset(),
    DimensionLifecycle.REJECTED: frozenset(),
    DimensionLifecycle.ARCHIVED: frozenset(),
}


class DimensionProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension_key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    data_shape: str = Field(min_length=1)
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    why_existing_dimensions_are_insufficient: str = Field(min_length=1)
    continuity_rationale: str = Field(min_length=1)
    user_value_rationale: str = Field(min_length=1)
    maintenance_cost_rationale: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    update_method: str | None = None
    expected_value: str | None = None

    @model_validator(mode="after")
    def validate_request(self) -> "DimensionProposalRequest":
        for name in (
            "dimension_key",
            "name",
            "description",
            "data_shape",
            "why_existing_dimensions_are_insufficient",
            "continuity_rationale",
            "user_value_rationale",
            "maintenance_cost_rationale",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be blank")
        if not self.dimension_key.startswith("dim:"):
            raise ValueError("dimension_key must start with 'dim:'")
        for ref in self.evidence_refs:
            if ref.revision is None:
                raise ValueError("dimension proposal evidence must pin exact revisions")
        return self


class DimensionTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension_ref: ObjectRef
    new_lifecycle: DimensionLifecycle
    reason: str = Field(min_length=1)
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    related_dimension_refs: tuple[ObjectRef, ...] = ()

    @model_validator(mode="after")
    def validate_request(self) -> "DimensionTransitionRequest":
        if self.dimension_ref.revision is None:
            raise ValueError("dimension_ref must pin an exact revision")
        if not self.reason.strip():
            raise ValueError("reason must not be blank")
        for ref in (*self.evidence_refs, *self.related_dimension_refs):
            if ref.revision is None:
                raise ValueError("transition references must pin exact revisions")
        if self.new_lifecycle in {
            DimensionLifecycle.MERGED,
            DimensionLifecycle.SPLIT,
        } and not self.related_dimension_refs:
            raise ValueError(
                f"{self.new_lifecycle.value} transition requires related_dimension_refs"
            )
        return self


@dataclass(frozen=True, slots=True)
class DimensionProposalReceipt:
    dimension_id: str
    dimension_key: str
    lifecycle: str
    evidence_set_id: str
    derivation_id: str
    world_revision: int


@dataclass(frozen=True, slots=True)
class DimensionTransitionReceipt:
    dimension_id: str
    previous_revision: int
    new_revision: int
    previous_lifecycle: str
    new_lifecycle: str
    evidence_set_id: str
    world_revision: int


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _source_refs(refs: Sequence[ObjectRef]) -> list[SourceRef]:
    return [
        SourceRef(object_id=ref.object_id, revision=ref.revision)
        for ref in refs
    ]


class DimensionRegistryService:
    """Durable dimension proposal + lifecycle state machine."""

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

    def current_dimensions(
        self,
        *,
        include_terminal: bool = True,
    ) -> tuple[DimensionDefinition, ...]:
        items: list[DimensionDefinition] = []
        for payload in self.store.list_payloads(
            object_type=ObjectType.DIMENSION_DEFINITION,
            subject_id=self.subject_id,
        ):
            item = DimensionDefinition.model_validate(payload)
            if not include_terminal and item.lifecycle in _TERMINAL:
                continue
            items.append(item)
        items.sort(
            key=lambda item: (
                str(item.metadata.get("dimension_key") or ""),
                item.object_id,
            )
        )
        return tuple(items)

    def find_by_key(self, dimension_key: str) -> DimensionDefinition | None:
        clean = dimension_key.strip()
        for item in self.current_dimensions(include_terminal=True):
            if item.metadata.get("dimension_key") == clean:
                return item
        return None

    def _validate_refs_exist(self, refs: Sequence[ObjectRef]) -> None:
        for ref in refs:
            payload = self.store.get_payload(ref.object_id, revision=ref.revision)
            ref_subject = str(payload.get("subject_id") or "")
            if ref_subject != self.subject_id:
                raise ValueError(
                    "dimension evidence/reference crosses the runtime subject scope: "
                    f"{ref.object_id}@{ref.revision} belongs to {ref_subject!r}"
                )

    def _evidence_set(
        self,
        *,
        purpose: str,
        refs: Sequence[ObjectRef],
        learned_at: datetime,
        dimension_key: str,
        mode: str,
    ) -> EvidenceSet:
        current_world_revision = int(self.store.current_world_revision())
        evidence_id = _stable_id(
            "evs_dim",
            purpose,
            tuple((r.object_id, r.revision) for r in refs),
            learned_at.isoformat(),
        )
        return EvidenceSet(
            object_id=evidence_id,
            subject_id=self.subject_id,
            learned_at=learned_at,
            recorded_at=learned_at,
            created_by="dimension_registry:evidence",
            purpose=purpose,
            knowledge_window=KnowledgeWindow(
                knowledge_cutoff=learned_at,
                world_revision=current_world_revision,
            ),
            member_refs=list(refs),
            support_refs=list(refs),
            selection_method="resident_model_selected_dimension_evidence",
            coverage=EvidenceCoverage(
                expected_count=len(refs),
                observed_count=len(refs),
                coverage_ratio=1.0,
            ),
            metadata={
                "dimension": dimension_key,
                "dimension_registry_mode": mode,
            },
        )

    def propose(
        self,
        request: DimensionProposalRequest,
        *,
        proposed_at: datetime,
    ) -> DimensionProposalReceipt:
        proposed = as_utc(proposed_at, "proposed_at")
        key = request.dimension_key.strip()
        if self.find_by_key(key) is not None:
            raise ValueError(f"dimension_key already exists: {key}")

        self._validate_refs_exist(request.evidence_refs)

        dimension_id = _stable_id("dimdef", self.subject_id, key)
        evidence = self._evidence_set(
            purpose=f"support dimension proposal {key}",
            refs=request.evidence_refs,
            learned_at=proposed,
            dimension_key=key,
            mode="proposal",
        )
        evidence_ref = ObjectRef(object_id=evidence.object_id, revision=1)

        definition = DimensionDefinition(
            object_id=dimension_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(proposed),
            learned_at=proposed,
            recorded_at=proposed,
            source_refs=_source_refs(request.evidence_refs),
            created_by="dimension_registry:resident_ai",
            name=request.name.strip(),
            description=request.description.strip(),
            data_shape=request.data_shape.strip(),
            lifecycle=DimensionLifecycle.CANDIDATE,
            update_method=(
                request.update_method.strip()
                if request.update_method and request.update_method.strip()
                else None
            ),
            expected_value=(
                request.expected_value.strip()
                if request.expected_value and request.expected_value.strip()
                else None
            ),
            maintenance_policy={},
            metadata={
                "dimension_key": key,
                "proposal": {
                    "why_existing_dimensions_are_insufficient": request.why_existing_dimensions_are_insufficient.strip(),
                    "continuity_rationale": request.continuity_rationale.strip(),
                    "user_value_rationale": request.user_value_rationale.strip(),
                    "maintenance_cost_rationale": request.maintenance_cost_rationale.strip(),
                    "confidence": request.confidence,
                },
                "proposal_evidence_set_ref": {
                    "object_id": evidence.object_id,
                    "revision": 1,
                },
            },
        )
        definition_ref = ObjectRef(object_id=dimension_id, revision=1)

        derivation_id = _stable_id("dimder", dimension_id, 1)
        derivation = DimensionDerivation(
            object_id=derivation_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(proposed),
            learned_at=proposed,
            recorded_at=proposed,
            source_refs=_source_refs(request.evidence_refs),
            created_by="dimension_registry:resident_ai",
            output_dimension_ref=definition_ref,
            input_refs=list(request.evidence_refs),
            derivation_description=(
                request.why_existing_dimensions_are_insufficient.strip()
                + " | "
                + request.continuity_rationale.strip()
                + " | "
                + request.user_value_rationale.strip()
            ),
            applicable_scope={"dimension_key": key},
            applicable_time=TemporalExtent.unknown_time(),
            evidence_set_refs=[evidence_ref],
            confidence=request.confidence,
            metadata={"dimension_key": key},
        )

        dependencies: list[Dependency] = [
            Dependency(
                object_id=_stable_id("dep", dimension_id, 1, evidence.object_id, 1),
                subject_id=self.subject_id,
                learned_at=proposed,
                recorded_at=proposed,
                created_by="dimension_registry:dependency",
                dependent_ref=definition_ref,
                dependency_ref=evidence_ref,
                dependency_type="dimension_definition_uses_evidence_set",
            ),
            Dependency(
                object_id=_stable_id("dep", derivation_id, 1, evidence.object_id, 1),
                subject_id=self.subject_id,
                learned_at=proposed,
                recorded_at=proposed,
                created_by="dimension_registry:dependency",
                dependent_ref=ObjectRef(object_id=derivation_id, revision=1),
                dependency_ref=evidence_ref,
                dependency_type="dimension_derivation_uses_evidence_set",
            ),
        ]
        for ref in request.evidence_refs:
            dependencies.append(
                Dependency(
                    object_id=_stable_id(
                        "dep", evidence.object_id, 1, ref.object_id, ref.revision
                    ),
                    subject_id=self.subject_id,
                    learned_at=proposed,
                    recorded_at=proposed,
                    created_by="dimension_registry:dependency",
                    dependent_ref=evidence_ref,
                    dependency_ref=ref,
                    dependency_type="dimension_evidence_set_contains_source",
                )
            )

        current = int(self.store.current_world_revision())
        result = self.store.commit(
            [evidence, definition, derivation, *dependencies],
            OperationRequest(
                operation_name="dimension.propose",
                arguments={
                    "dimension_key": key,
                    "lifecycle": DimensionLifecycle.CANDIDATE.value,
                },
                expected_world_revision=current,
                reason="resident AI proposed a new evidence-grounded observation axis",
                idempotency_key=f"dimension-proposal:{dimension_id}:1",
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        if self.index is not None:
            self.index.catch_up()

        return DimensionProposalReceipt(
            dimension_id=dimension_id,
            dimension_key=key,
            lifecycle=DimensionLifecycle.CANDIDATE.value,
            evidence_set_id=evidence.object_id,
            derivation_id=derivation_id,
            world_revision=result.world_revision,
        )

    def transition(
        self,
        request: DimensionTransitionRequest,
        *,
        changed_at: datetime,
    ) -> DimensionTransitionReceipt:
        changed = as_utc(changed_at, "changed_at")
        payload = self.store.get_payload(
            request.dimension_ref.object_id,
            revision=request.dimension_ref.revision,
        )
        if payload.get("object_type") != ObjectType.DIMENSION_DEFINITION.value:
            raise ValueError("dimension_ref must point to DimensionDefinition")

        current_payload = self.store.get_payload(request.dimension_ref.object_id)
        if int(current_payload["revision"]) != int(request.dimension_ref.revision):
            raise ValueError("only the current DimensionDefinition revision may transition")

        current = DimensionDefinition.model_validate(payload)
        if current.subject_id != self.subject_id:
            raise ValueError(
                "dimension transition target crosses the runtime subject scope"
            )
        target = DimensionLifecycle(request.new_lifecycle)
        if target not in _ALLOWED_TRANSITIONS.get(current.lifecycle, frozenset()):
            raise ValueError(
                f"illegal dimension lifecycle transition: "
                f"{current.lifecycle.value} -> {target.value}"
            )

        self._validate_refs_exist(request.evidence_refs)
        for related_ref in request.related_dimension_refs:
            related = self.store.get_payload(
                related_ref.object_id,
                revision=related_ref.revision,
            )
            if related.get("object_type") != ObjectType.DIMENSION_DEFINITION.value:
                raise ValueError("related_dimension_refs must point to dimensions")

        key = str(current.metadata.get("dimension_key") or "").strip()
        if not key:
            raise ValueError("dimension definition is missing dimension_key metadata")

        evidence = self._evidence_set(
            purpose=(
                f"support dimension transition {key}: "
                f"{current.lifecycle.value}->{target.value}"
            ),
            refs=request.evidence_refs,
            learned_at=changed,
            dimension_key=key,
            mode="transition",
        )
        evidence_ref = ObjectRef(object_id=evidence.object_id, revision=1)

        metadata = dict(current.metadata)
        transitions = list(metadata.get("lifecycle_history") or [])
        transitions.append(
            {
                "from": current.lifecycle.value,
                "to": target.value,
                "reason": request.reason.strip(),
                "changed_at": changed.isoformat(),
                "evidence_set_ref": {
                    "object_id": evidence.object_id,
                    "revision": 1,
                },
                "related_dimension_refs": [
                    {
                        "object_id": ref.object_id,
                        "revision": ref.revision,
                    }
                    for ref in request.related_dimension_refs
                ],
            }
        )
        metadata["lifecycle_history"] = transitions

        new_revision = int(current.revision) + 1
        new_definition = DimensionDefinition.model_validate(
            {
                **current.model_dump(mode="python", round_trip=True),
                "revision": new_revision,
                "occurred": TemporalExtent.point(changed),
                "learned_at": changed,
                "recorded_at": changed,
                "source_refs": _source_refs(request.evidence_refs),
                "lifecycle": target,
                "status": (
                    target.value
                    if target in _TERMINAL
                    else "active"
                ),
                "metadata": metadata,
            }
        )
        definition_ref = ObjectRef(
            object_id=new_definition.object_id,
            revision=new_revision,
        )

        dependencies: list[Dependency] = [
            Dependency(
                object_id=_stable_id(
                    "dep",
                    new_definition.object_id,
                    new_revision,
                    evidence.object_id,
                    1,
                ),
                subject_id=self.subject_id,
                learned_at=changed,
                recorded_at=changed,
                created_by="dimension_registry:dependency",
                dependent_ref=definition_ref,
                dependency_ref=evidence_ref,
                dependency_type="dimension_lifecycle_uses_evidence_set",
            )
        ]
        for ref in request.evidence_refs:
            dependencies.append(
                Dependency(
                    object_id=_stable_id(
                        "dep", evidence.object_id, 1, ref.object_id, ref.revision
                    ),
                    subject_id=self.subject_id,
                    learned_at=changed,
                    recorded_at=changed,
                    created_by="dimension_registry:dependency",
                    dependent_ref=evidence_ref,
                    dependency_ref=ref,
                    dependency_type="dimension_transition_evidence_contains_source",
                )
            )

        current_world_revision = int(self.store.current_world_revision())
        result = self.store.commit(
            [evidence, new_definition, *dependencies],
            OperationRequest(
                operation_name="dimension.transition",
                arguments={
                    "dimension_key": key,
                    "from": current.lifecycle.value,
                    "to": target.value,
                },
                expected_world_revision=current_world_revision,
                reason=request.reason.strip(),
                idempotency_key=(
                    f"dimension-transition:{new_definition.object_id}:"
                    f"{new_revision}:{target.value}"
                ),
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        if self.index is not None:
            self.index.catch_up()

        return DimensionTransitionReceipt(
            dimension_id=new_definition.object_id,
            previous_revision=int(current.revision),
            new_revision=new_revision,
            previous_lifecycle=current.lifecycle.value,
            new_lifecycle=target.value,
            evidence_set_id=evidence.object_id,
            world_revision=result.world_revision,
        )
