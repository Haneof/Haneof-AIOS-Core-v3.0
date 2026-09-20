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

from aios_core.contracts.enums import ClaimType, KnowledgeState, ObjectType, SourceClass
from aios_core.contracts.models import Claim, Dependency, EvidenceCoverage, EvidenceSet
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import KnowledgeWindow, TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore


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

    @model_validator(mode="after")
    def validate_refs(self) -> "ClaimWriteRequest":
        if not self.content.strip() or not self.dimension.strip() or not self.claimant_id.strip():
            raise ValueError("content/dimension/claimant_id must not be blank")
        for ref in self.evidence_refs:
            if ref.revision is None:
                raise ValueError("cognitive writeback requires pinned evidence revisions")
        return self


@dataclass(frozen=True, slots=True)
class ClaimWriteReceipt:
    claim_id: str
    evidence_set_id: str
    dependency_ids: tuple[str, ...]
    world_revision: int
    reused_existing: bool = False


def _stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


class CognitionWritebackService:
    """Commit evidence-grounded AI cognition into the unified world."""

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

        # Evidence must already exist in the world at exactly the pinned revision.
        for ref in pinned:
            self.store.get_payload(ref.object_id, revision=ref.revision)

        evidence_key = tuple((ref.object_id, ref.revision) for ref in pinned)
        evidence_set_id = _stable_id(
            "evs",
            self.subject_id,
            request.dimension,
            evidence_key,
            learned.isoformat(),
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
            learned.isoformat(),
        )

        dependency_ids = [
            _stable_id("dep", claim_id, 1, evidence_set_id, 1),
            *[
                _stable_id("dep", evidence_set_id, 1, ref.object_id, ref.revision)
                for ref in pinned
            ],
        ]

        # Exact retry: atomic commit guarantees that if the claim exists, the whole
        # evidence/dependency bundle exists too.
        try:
            existing = self.store.get_payload(claim_id, revision=1)
        except Exception:
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
            valid_time=TemporalExtent.unknown_time(),
            asserted_at=learned,
            knowledge_state=request.knowledge_state,
            confidence=request.confidence,
            support_evidence_set_refs=[evidence_ref],
            metadata={
                **request.metadata,
                "dimension": request.dimension,
                "writeback_kind": "revisable_cognition",
            },
        )

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
        for dep_id, ref in zip(dependency_ids[1:], pinned):
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

        op_key = _stable_id("write", claim_id, evidence_set_id)
        operation = OperationRequest(
            operation_id=f"op_{op_key}",
            operation_name="cognition.commit_claim",
            arguments={
                "claim_id": claim_id,
                "dimension": request.dimension,
                "evidence_count": len(pinned),
            },
            expected_world_revision=current_world_revision,
            reason="commit revisable evidence-grounded AI cognition",
            idempotency_key=f"cognition:{op_key}",
            source_class=SourceClass.AI_COGNITION,
        )
        result = self.store.commit(
            [evidence_set, claim, *dependency_objects],
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
