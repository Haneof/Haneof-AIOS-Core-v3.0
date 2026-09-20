"""Evidence-grounded Entity / Relation world graph for AIOS v3.0.

The resident model decides identity semantics and relationship meaning. Deterministic
Core only enforces explicit keys, pinned evidence, subject isolation, current-revision
endpoints, append-forward revisions, and durable dependency provenance.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import ErrorCode, ObjectType, SourceClass
from aios_core.contracts.models import (
    Dependency,
    Entity,
    EvidenceCoverage,
    EvidenceSet,
    Relation,
)
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.contracts.time import KnowledgeWindow, TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError

ENTITY_DIMENSION = "dim:entities"
RELATION_DIMENSION = "dim:relations"


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _require_pinned(refs: Sequence[ObjectRef], label: str) -> None:
    for ref in refs:
        if ref.revision is None:
            raise ValueError(f"{label} requires pinned revisions")


class EntityProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_key: str = Field(min_length=1)
    entity_kind: str = Field(min_length=1)
    canonical_name: str | None = None
    aliases: tuple[str, ...] = ()
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    identity_claim_refs: tuple[ObjectRef, ...] = ()

    @model_validator(mode="after")
    def validate_request(self) -> "EntityProposalRequest":
        if not self.entity_key.startswith("entity:"):
            raise ValueError("entity_key must start with 'entity:'")
        if not self.entity_kind.strip():
            raise ValueError("entity_kind must not be blank")
        if self.canonical_name is not None and not self.canonical_name.strip():
            raise ValueError("canonical_name must be non-blank when provided")
        if any(not item.strip() for item in self.aliases):
            raise ValueError("aliases must not contain blank values")
        if self.canonical_name is None and not self.aliases:
            raise ValueError("entity requires canonical_name or at least one alias")
        _require_pinned(
            (*self.evidence_refs, *self.identity_claim_refs),
            "entity refs",
        )
        return self


class EntityRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_ref: ObjectRef
    reason: str = Field(min_length=1)
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    canonical_name: str | None = None
    aliases: tuple[str, ...] | None = None
    identity_claim_refs: tuple[ObjectRef, ...] | None = None

    @model_validator(mode="after")
    def validate_request(self) -> "EntityRevisionRequest":
        if self.entity_ref.revision is None:
            raise ValueError("entity_ref must pin the current revision")
        if not self.reason.strip():
            raise ValueError("entity revision reason must not be blank")
        refs: list[ObjectRef] = list(self.evidence_refs)
        if self.identity_claim_refs is not None:
            refs.extend(self.identity_claim_refs)
        _require_pinned(refs, "entity revision refs")
        if self.canonical_name is not None and not self.canonical_name.strip():
            raise ValueError("canonical_name must be non-blank when provided")
        if self.aliases is not None and any(not item.strip() for item in self.aliases):
            raise ValueError("aliases must not contain blank values")
        return self


class RelationUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    left_ref: ObjectRef
    relation_type: str = Field(min_length=1)
    right_ref: ObjectRef
    valid_time: TemporalExtent = Field(default_factory=TemporalExtent.unknown_time)
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_request(self) -> "RelationUpsertRequest":
        if not self.relation_type.strip() or not self.reason.strip():
            raise ValueError("relation_type/reason must not be blank")
        _require_pinned(
            (self.left_ref, self.right_ref, *self.evidence_refs),
            "relation refs",
        )
        if self.left_ref.object_id == self.right_ref.object_id:
            raise ValueError("relation endpoints must be distinct entities")
        return self


@dataclass(frozen=True, slots=True)
class EntityReceipt:
    entity_id: str
    revision: int
    entity_key: str
    world_revision: int


@dataclass(frozen=True, slots=True)
class RelationReceipt:
    relation_id: str
    revision: int
    world_revision: int
    reused_existing: bool = False


class EntityRelationService:
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

    def _validate_ref(
        self,
        ref: ObjectRef,
        *,
        object_type: ObjectType | None = None,
        require_current: bool = False,
    ) -> dict[str, Any]:
        payload = self.store.get_payload(ref.object_id, revision=ref.revision)
        if str(payload.get("subject_id") or "") != self.subject_id:
            raise ValueError("world-graph reference crosses the runtime subject scope")
        if object_type is not None and payload.get("object_type") != object_type.value:
            raise ValueError(
                f"{ref.object_id}@{ref.revision} is not {object_type.value}"
            )
        if require_current:
            latest = self.store.get_payload(ref.object_id)
            if int(latest.get("revision") or 0) != int(ref.revision or 0):
                raise ValueError(
                    f"{ref.object_id}@{ref.revision} is not the current revision"
                )
        return payload

    def _validate_evidence(self, refs: Sequence[ObjectRef]) -> None:
        _require_pinned(refs, "world-graph evidence")
        for ref in refs:
            self._validate_ref(ref)

    def _evidence_set(
        self,
        *,
        purpose: str,
        refs: Sequence[ObjectRef],
        at: datetime,
        dimension: str,
        identity_parts: Sequence[object],
    ) -> EvidenceSet:
        evidence_id = _stable_id(
            "evs_graph",
            self.subject_id,
            *identity_parts,
            tuple((ref.object_id, ref.revision) for ref in refs),
            at.isoformat(),
        )
        return EvidenceSet(
            object_id=evidence_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(at),
            learned_at=at,
            recorded_at=at,
            source_refs=[
                SourceRef(object_id=ref.object_id, revision=ref.revision)
                for ref in refs
            ],
            created_by="world_graph:evidence",
            purpose=purpose,
            knowledge_window=KnowledgeWindow(
                knowledge_cutoff=at,
                world_revision=int(self.store.current_world_revision()),
            ),
            member_refs=list(refs),
            support_refs=list(refs),
            selection_method="resident_model_selected_graph_evidence",
            coverage=EvidenceCoverage(
                expected_count=len(refs),
                observed_count=len(refs),
                coverage_ratio=1.0,
            ),
            metadata={"dimension": dimension},
        )

    def _deps(
        self,
        *,
        dependent_ref: ObjectRef,
        evidence: EvidenceSet,
        refs: Sequence[ObjectRef],
        at: datetime,
        prefix: str,
    ) -> list[Dependency]:
        evidence_ref = ObjectRef(object_id=evidence.object_id, revision=1)
        deps = [
            Dependency(
                object_id=_stable_id(
                    "dep",
                    dependent_ref.object_id,
                    dependent_ref.revision,
                    evidence.object_id,
                    1,
                    prefix,
                ),
                subject_id=self.subject_id,
                learned_at=at,
                recorded_at=at,
                created_by="world_graph:dependency",
                dependent_ref=dependent_ref,
                dependency_ref=evidence_ref,
                dependency_type=f"{prefix}_uses_evidence_set",
            )
        ]
        for ref in refs:
            deps.append(
                Dependency(
                    object_id=_stable_id(
                        "dep",
                        evidence.object_id,
                        1,
                        ref.object_id,
                        ref.revision,
                        prefix,
                    ),
                    subject_id=self.subject_id,
                    learned_at=at,
                    recorded_at=at,
                    created_by="world_graph:dependency",
                    dependent_ref=evidence_ref,
                    dependency_ref=ref,
                    dependency_type=f"{prefix}_evidence_contains_source",
                )
            )
        return deps

    def current_entities(self) -> tuple[Entity, ...]:
        entities = [
            Entity.model_validate(payload)
            for payload in self.store.list_payloads(
                object_type=ObjectType.ENTITY,
                subject_id=self.subject_id,
            )
        ]
        entities.sort(
            key=lambda item: (
                str(item.metadata.get("entity_key") or ""),
                item.object_id,
            )
        )
        return tuple(entities)

    def find_entity_by_key(self, entity_key: str) -> Entity | None:
        clean = entity_key.strip()
        for entity in self.current_entities():
            if entity.metadata.get("entity_key") == clean:
                return entity
        return None

    def propose_entity(
        self,
        request: EntityProposalRequest,
        *,
        proposed_at: datetime,
    ) -> EntityReceipt:
        proposed = as_utc(proposed_at, "proposed_at")
        key = request.entity_key.strip()
        if self.find_entity_by_key(key) is not None:
            raise ValueError(f"entity_key already exists: {key}")
        self._validate_evidence(
            (*request.evidence_refs, *request.identity_claim_refs)
        )
        for ref in request.identity_claim_refs:
            self._validate_ref(ref, object_type=ObjectType.CLAIM)

        entity_id = _stable_id("entity", self.subject_id, key)
        evidence = self._evidence_set(
            purpose=f"support entity proposal {key}",
            refs=request.evidence_refs,
            at=proposed,
            dimension=ENTITY_DIMENSION,
            identity_parts=(entity_id, 1),
        )
        entity = Entity(
            object_id=entity_id,
            subject_id=self.subject_id,
            revision=1,
            occurred=TemporalExtent.point(proposed),
            learned_at=proposed,
            recorded_at=proposed,
            source_refs=[
                SourceRef(object_id=ref.object_id, revision=ref.revision)
                for ref in request.evidence_refs
            ],
            created_by="world_graph:resident_ai",
            entity_kind=request.entity_kind.strip(),
            canonical_name=(
                request.canonical_name.strip()
                if request.canonical_name is not None
                else None
            ),
            aliases=list(dict.fromkeys(item.strip() for item in request.aliases)),
            identity_claim_refs=list(request.identity_claim_refs),
            metadata={
                "dimension": ENTITY_DIMENSION,
                "entity_key": key,
                "evidence_set_ref": {
                    "object_id": evidence.object_id,
                    "revision": 1,
                },
            },
        )
        entity_ref = ObjectRef(object_id=entity_id, revision=1)
        objects: list[Any] = [
            evidence,
            entity,
            *self._deps(
                dependent_ref=entity_ref,
                evidence=evidence,
                refs=request.evidence_refs,
                at=proposed,
                prefix="entity",
            ),
        ]
        result = self.store.commit(
            objects,
            OperationRequest(
                operation_name="world_graph.propose_entity",
                arguments={"entity_id": entity_id, "entity_key": key},
                expected_world_revision=int(self.store.current_world_revision()),
                reason=f"resident AI proposed entity {key}",
                idempotency_key=f"entity-propose:{entity_id}:1",
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        if self.index is not None:
            self.index.catch_up()
        return EntityReceipt(entity_id, 1, key, result.world_revision)

    def revise_entity(
        self,
        request: EntityRevisionRequest,
        *,
        changed_at: datetime,
    ) -> EntityReceipt:
        changed = as_utc(changed_at, "changed_at")
        payload = self._validate_ref(
            request.entity_ref,
            object_type=ObjectType.ENTITY,
            require_current=True,
        )
        current = Entity.model_validate(payload)
        refs = (
            *request.evidence_refs,
            *(request.identity_claim_refs or ()),
        )
        self._validate_evidence(refs)
        if request.identity_claim_refs is not None:
            for ref in request.identity_claim_refs:
                self._validate_ref(ref, object_type=ObjectType.CLAIM)

        revision = current.revision + 1
        evidence = self._evidence_set(
            purpose=f"support entity revision {current.object_id}@{revision}",
            refs=request.evidence_refs,
            at=changed,
            dimension=ENTITY_DIMENSION,
            identity_parts=(current.object_id, revision),
        )
        metadata = {
            **dict(current.metadata),
            "dimension": ENTITY_DIMENSION,
            "revision_reason": request.reason.strip(),
            "supersedes_revision": current.revision,
            "evidence_set_ref": {
                "object_id": evidence.object_id,
                "revision": 1,
            },
        }
        revised = Entity.model_validate({
            **current.model_dump(mode="python", round_trip=True),
            "revision": revision,
            "occurred": current.occurred,
            "learned_at": changed,
            "recorded_at": changed,
            "source_refs": [
                SourceRef(object_id=ref.object_id, revision=ref.revision)
                for ref in request.evidence_refs
            ],
            "canonical_name": (
                current.canonical_name
                if request.canonical_name is None
                else request.canonical_name.strip()
            ),
            "aliases": (
                current.aliases
                if request.aliases is None
                else list(dict.fromkeys(item.strip() for item in request.aliases))
            ),
            "identity_claim_refs": (
                current.identity_claim_refs
                if request.identity_claim_refs is None
                else list(request.identity_claim_refs)
            ),
            "metadata": metadata,
        })
        if revised.canonical_name is None and not revised.aliases:
            raise ValueError("entity revision cannot remove all names")

        revised_ref = ObjectRef(object_id=revised.object_id, revision=revision)
        result = self.store.commit(
            [
                evidence,
                revised,
                *self._deps(
                    dependent_ref=revised_ref,
                    evidence=evidence,
                    refs=request.evidence_refs,
                    at=changed,
                    prefix="entity_revision",
                ),
            ],
            OperationRequest(
                operation_name="world_graph.revise_entity",
                arguments={
                    "entity_id": revised.object_id,
                    "revision": revision,
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason=request.reason.strip(),
                idempotency_key=f"entity-revise:{revised.object_id}:{revision}",
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        if self.index is not None:
            self.index.catch_up()
        return EntityReceipt(
            revised.object_id,
            revision,
            str(revised.metadata.get("entity_key") or ""),
            result.world_revision,
        )

    def upsert_relation(
        self,
        request: RelationUpsertRequest,
        *,
        changed_at: datetime,
    ) -> RelationReceipt:
        changed = as_utc(changed_at, "changed_at")
        self._validate_ref(
            request.left_ref,
            object_type=ObjectType.ENTITY,
            require_current=True,
        )
        self._validate_ref(
            request.right_ref,
            object_type=ObjectType.ENTITY,
            require_current=True,
        )
        self._validate_evidence(request.evidence_refs)

        relation_type = request.relation_type.strip()
        relation_id = _stable_id(
            "relation",
            self.subject_id,
            request.left_ref.object_id,
            relation_type,
            request.right_ref.object_id,
        )
        current: Relation | None = None
        try:
            latest = self.store.get_payload(relation_id)
        except StoreError as exc:
            if exc.code is not ErrorCode.NOT_FOUND:
                raise
        else:
            current = Relation.model_validate(latest)
            if current.subject_id != self.subject_id:
                raise ValueError("relation identity collides across subject scope")

        revision = 1 if current is None else current.revision + 1
        evidence = self._evidence_set(
            purpose=f"support relation {relation_id}@{revision}",
            refs=request.evidence_refs,
            at=changed,
            dimension=RELATION_DIMENSION,
            identity_parts=(relation_id, revision),
        )
        evidence_ref = ObjectRef(object_id=evidence.object_id, revision=1)
        relation = Relation(
            object_id=relation_id,
            subject_id=self.subject_id,
            revision=revision,
            occurred=request.valid_time,
            learned_at=changed,
            recorded_at=changed,
            source_refs=[
                SourceRef(object_id=ref.object_id, revision=ref.revision)
                for ref in request.evidence_refs
            ],
            created_by="world_graph:resident_ai",
            left=request.left_ref,
            relation_type=relation_type,
            right=request.right_ref,
            valid_time=request.valid_time,
            evidence_set_refs=[evidence_ref],
            confidence=request.confidence,
            metadata={
                "dimension": RELATION_DIMENSION,
                "reason": request.reason.strip(),
                "supersedes_revision": (
                    None if current is None else current.revision
                ),
            },
        )
        relation_ref = ObjectRef(object_id=relation_id, revision=revision)
        deps = self._deps(
            dependent_ref=relation_ref,
            evidence=evidence,
            refs=request.evidence_refs,
            at=changed,
            prefix="relation",
        )
        for endpoint_name, endpoint_ref in (
            ("left", request.left_ref),
            ("right", request.right_ref),
        ):
            deps.append(
                Dependency(
                    object_id=_stable_id(
                        "dep",
                        relation_id,
                        revision,
                        endpoint_name,
                        endpoint_ref.object_id,
                        endpoint_ref.revision,
                    ),
                    subject_id=self.subject_id,
                    learned_at=changed,
                    recorded_at=changed,
                    created_by="world_graph:dependency",
                    dependent_ref=relation_ref,
                    dependency_ref=endpoint_ref,
                    dependency_type=f"relation_{endpoint_name}_entity",
                )
            )

        result = self.store.commit(
            [evidence, relation, *deps],
            OperationRequest(
                operation_name="world_graph.upsert_relation",
                arguments={
                    "relation_id": relation_id,
                    "revision": revision,
                    "relation_type": relation_type,
                },
                expected_world_revision=int(self.store.current_world_revision()),
                reason=request.reason.strip(),
                idempotency_key=f"relation-upsert:{relation_id}:{revision}",
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        if self.index is not None:
            self.index.catch_up()
        return RelationReceipt(
            relation_id,
            revision,
            result.world_revision,
            reused_existing=result.idempotent_replay,
        )
