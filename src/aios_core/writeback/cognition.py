"""Evidence-grounded cognition writeback for AIOS v3.0.

This service lets the resident AI persist revisable cognition without confusing it
with observed fact. A Claim must be backed by pinned world evidence. The write is
atomic: EvidenceSet + Claim + explicit Dependency edges enter one world revision.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.enums import ClaimType, ErrorCode, KnowledgeState, ObjectType, SourceClass
from aios_core.contracts.models import Claim, Dependency, EvidenceCoverage, EvidenceSet
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import KnowledgeWindow, TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError


class ClaimWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str = Field(min_length=1)
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    dimension: str = Field(min_length=1)
    claim_type: ClaimType = ClaimType.INFERENCE
    knowledge_state: KnowledgeState = KnowledgeState.INFERRED
    claimant_id: str = "resident_ai"
    metadata: dict[str, Any] = Field(default_factory=dict)
    valid_time: TemporalExtent = Field(default_factory=TemporalExtent.unknown_time)
    unknown_items: tuple[str, ...] = ()
    counter_evidence_refs: tuple[ObjectRef, ...] = ()

    @model_validator(mode="after")
    def validate_refs(self) -> "ClaimWriteRequest":
        if not self.content.strip() or not self.dimension.strip() or not self.claimant_id.strip():
            raise ValueError("content/dimension/claimant_id must not be blank")
        for ref in self.evidence_refs:
            if ref.revision is None:
                raise ValueError("cognitive writeback requires pinned evidence revisions")
        for ref in self.counter_evidence_refs:
            if ref.revision is None:
                raise ValueError("cognitive writeback requires pinned counter evidence revisions")
        if any(not item.strip() for item in self.unknown_items):
            raise ValueError("unknown_items must not contain blank values")
        return self


@dataclass(frozen=True, slots=True)
class ClaimWriteReceipt:
    claim_id: str
    evidence_set_id: str
    dependency_ids: tuple[str, ...]
    world_revision: int
    reused_existing: bool = False


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


class CognitionWritebackService:
    """Commit evidence-grounded AI cognition into the unified world."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex | None = None,
        subject_id: str = "user_1",
        evidence_subject_ids: Sequence[str] | None = None,
    ) -> None:
        self.store = store
        self.index = index
        self.subject_id = subject_id
        allowed = tuple(evidence_subject_ids or (subject_id,))
        self.evidence_subject_ids = frozenset(
            str(item).strip() for item in allowed if str(item).strip()
        )
        if not self.evidence_subject_ids:
            raise ValueError("evidence_subject_ids must contain at least one subject")

    def commit_claim(
        self,
        request: ClaimWriteRequest,
        *,
        learned_at: datetime,
    ) -> ClaimWriteReceipt:
        learned = as_utc(learned_at, "learned_at")
        pinned = tuple(
            sorted(
                request.evidence_refs,
                key=lambda ref: (ref.object_id, int(ref.revision or 0)),
            )
        )

        # Evidence must already exist in the same private-world subject scope at
        # exactly the pinned revision. AI-self cognition may explicitly opt into
        # both the user subject and AI-self subject; unrelated user subjects may not.
        for ref in pinned:
            payload = self.store.get_payload(ref.object_id, revision=ref.revision)
            evidence_subject = str(payload.get("subject_id") or "")
            if evidence_subject not in self.evidence_subject_ids:
                raise ValueError(
                    "cognitive writeback evidence crosses the allowed subject scope: "
                    f"{ref.object_id}@{ref.revision} belongs to {evidence_subject!r}"
                )

        counter_pinned = tuple(
            sorted(
                request.counter_evidence_refs,
                key=lambda ref: (ref.object_id, int(ref.revision or 0)),
            )
        )
        for ref in counter_pinned:
            payload = self.store.get_payload(ref.object_id, revision=ref.revision)
            evidence_subject = str(payload.get("subject_id") or "")
            if evidence_subject not in self.evidence_subject_ids:
                raise ValueError(
                    "cognitive writeback counter evidence crosses the allowed subject scope: "
                    f"{ref.object_id}@{ref.revision} belongs to {evidence_subject!r}"
                )

        evidence_key = tuple((ref.object_id, ref.revision) for ref in pinned)
        evidence_set_id = _stable_id(
            "evs",
            self.subject_id,
            request.dimension,
            evidence_key,
            learned.isoformat(),
        )
        counter_evidence_set_id = (
            _stable_id(
                "evs_counter",
                self.subject_id,
                request.dimension,
                tuple((ref.object_id, ref.revision) for ref in counter_pinned),
                learned.isoformat(),
            )
            if counter_pinned
            else None
        )
        claim_id = _stable_id(
            "clm",
            request.claimant_id,
            request.claim_type.value,
            request.knowledge_state.value,
            request.dimension,
            request.content.strip(),
            request.confidence,
            request.metadata,
            evidence_set_id,
            counter_evidence_set_id,
            request.valid_time.model_dump(mode="json"),
            list(request.unknown_items),
            learned.isoformat(),
        )

        dependency_ids = [
            _stable_id("dep", claim_id, 1, evidence_set_id, 1),
            *[
                _stable_id("dep", evidence_set_id, 1, ref.object_id, ref.revision)
                for ref in pinned
            ],
        ]
        if counter_evidence_set_id is not None:
            dependency_ids.append(_stable_id("dep", claim_id, 1, counter_evidence_set_id, 1))
            for ref in counter_pinned:
                dependency_ids.append(
                    _stable_id("dep", counter_evidence_set_id, 1, ref.object_id, ref.revision)
                )

        # Exact retry: atomic commit guarantees that if the claim exists, the whole
        # evidence/dependency bundle exists too.
        try:
            existing = self.store.get_payload(claim_id, revision=1)
        except StoreError as exc:
            if exc.code is not ErrorCode.NOT_FOUND:
                raise
            existing = None
        if existing is not None:
            return ClaimWriteReceipt(
                claim_id=claim_id,
                evidence_set_id=evidence_set_id,
                dependency_ids=tuple(dependency_ids),
                world_revision=int(self.store.current_world_revision()),
                reused_existing=True,
            )

        current_world_revision = int(self.store.current_world_revision())
        evidence_set = EvidenceSet(
            object_id=evidence_set_id,
            subject_id=self.subject_id,
            learned_at=learned,
            recorded_at=learned,
            created_by="cognition_writeback:evidence",
            purpose="support resident AI cognition writeback",
            knowledge_window=KnowledgeWindow(
                knowledge_cutoff=learned,
                world_revision=current_world_revision,
            ),
            member_refs=list(pinned),
            support_refs=list(pinned),
            selection_method="resident_model_selected_pinned_world_evidence",
            coverage=EvidenceCoverage(
                expected_count=len(pinned),
                observed_count=len(pinned),
                coverage_ratio=1.0,
            ),
            metadata={
                **request.metadata,
                "dimension": request.dimension,
                "writeback_kind": "cognition_evidence",
            },
        )
        evidence_ref = ObjectRef(object_id=evidence_set_id, revision=1)
        objects_to_commit: list[Any] = [evidence_set]

        counter_evidence_ref = None
        if counter_evidence_set_id is not None:
            counter_evidence_set = EvidenceSet(
                object_id=counter_evidence_set_id,
                subject_id=self.subject_id,
                learned_at=learned,
                recorded_at=learned,
                created_by="cognition_writeback:counter_evidence",
                purpose="support resident AI cognition counter evidence",
                knowledge_window=KnowledgeWindow(
                    knowledge_cutoff=learned,
                    world_revision=current_world_revision,
                ),
                member_refs=list(counter_pinned),
                counter_refs=list(counter_pinned),
                selection_method="resident_model_selected_pinned_world_evidence",
                coverage=EvidenceCoverage(
                    expected_count=len(counter_pinned),
                    observed_count=len(counter_pinned),
                    coverage_ratio=1.0,
                ),
                metadata={
                    **request.metadata,
                    "dimension": request.dimension,
                    "writeback_kind": "cognition_counter_evidence",
                },
            )
            counter_evidence_ref = ObjectRef(object_id=counter_evidence_set_id, revision=1)
            objects_to_commit.append(counter_evidence_set)

        counter_evidence_set_refs = (
            [counter_evidence_ref] if counter_evidence_ref is not None else []
        )
        claim = Claim(
            object_id=claim_id,
            subject_id=self.subject_id,
            learned_at=learned,
            recorded_at=learned,
            created_by="cognition_writeback:model",
            claimant_id=request.claimant_id,
            claim_type=request.claim_type,
            content=request.content.strip(),
            occurred=TemporalExtent.point(learned),
            valid_time=request.valid_time,
            asserted_at=learned,
            knowledge_state=request.knowledge_state,
            confidence=request.confidence,
            support_evidence_set_refs=[evidence_ref],
            counter_evidence_set_refs=counter_evidence_set_refs,
            unknown_items=list(request.unknown_items),
            metadata={
                **request.metadata,
                "dimension": request.dimension,
                "writeback_kind": "revisable_cognition",
            },
        )
        objects_to_commit.append(claim)

        dependency_objects: list[Dependency] = [
            Dependency(
                object_id=dependency_ids[0],
                subject_id=self.subject_id,
                learned_at=learned,
                recorded_at=learned,
                created_by="cognition_writeback:dependency",
                dependent_ref=ObjectRef(object_id=claim_id, revision=1),
                dependency_ref=evidence_ref,
                dependency_type="claim_uses_evidence_set",
            )
        ]
        for dep_id, ref in zip(dependency_ids[1 : 1 + len(pinned)], pinned):
            dependency_objects.append(
                Dependency(
                    object_id=dep_id,
                    subject_id=self.subject_id,
                    learned_at=learned,
                    recorded_at=learned,
                    created_by="cognition_writeback:dependency",
                    dependent_ref=evidence_ref,
                    dependency_ref=ref,
                    dependency_type="evidence_set_contains_source",
                )
            )

        if counter_evidence_ref is not None:
            c_offset = 1 + len(pinned)
            dependency_objects.append(
                Dependency(
                    object_id=dependency_ids[c_offset],
                    subject_id=self.subject_id,
                    learned_at=learned,
                    recorded_at=learned,
                    created_by="cognition_writeback:dependency",
                    dependent_ref=ObjectRef(object_id=claim_id, revision=1),
                    dependency_ref=counter_evidence_ref,
                    dependency_type="claim_uses_evidence_set",
                )
            )
            for dep_id, ref in zip(dependency_ids[c_offset + 1 :], counter_pinned):
                dependency_objects.append(
                    Dependency(
                        object_id=dep_id,
                        subject_id=self.subject_id,
                        learned_at=learned,
                        recorded_at=learned,
                        created_by="cognition_writeback:dependency",
                        dependent_ref=counter_evidence_ref,
                        dependency_ref=ref,
                        dependency_type="evidence_set_contains_source",
                    )
                )

        objects_to_commit.extend(dependency_objects)

        op_key = _stable_id("write", claim_id, evidence_set_id)
        operation = OperationRequest(
            operation_id=f"op_{op_key}",
            operation_name="cognition.commit_claim",
            arguments={
                "claim_id": claim_id,
                "dimension": request.dimension,
                "evidence_count": len(pinned),
                "counter_evidence_count": len(counter_pinned),
            },
            expected_world_revision=current_world_revision,
            reason="commit revisable evidence-grounded AI cognition",
            idempotency_key=f"cognition:{op_key}",
            source_class=SourceClass.AI_COGNITION,
        )
        result = self.store.commit(
            objects_to_commit,
            operation,
        )
        if self.index is not None:
            self.index.catch_up()

        return ClaimWriteReceipt(
            claim_id=claim_id,
            evidence_set_id=evidence_set_id,
            dependency_ids=tuple(dependency_ids),
            world_revision=result.world_revision,
            reused_existing=result.idempotent_replay,
        )
