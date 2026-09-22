"""Forward-only cognition revision and dependency propagation for AIOS v3.0.

History is immutable. A correction creates a new revision of the same Claim object.
Objects that still depend on the exact superseded revision are not silently rewritten;
their current revisions are marked review-required so current retrieval cannot keep
treating the old cognition as settled truth.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aios_core.contracts.base import WorldObject
from aios_core.contracts.enums import (
    KnowledgeState,
    MaintenanceClass,
    ObjectType,
    SourceClass,
    SummaryStatus,
)
from aios_core.contracts.models import Claim, Dependency, EvidenceCoverage, EvidenceSet
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.registry import canonical_model_for_object_type
from aios_core.contracts.time import KnowledgeWindow, as_utc
from aios_core.dependency.graph import collect_impacted_dependents
from aios_core.policy.evidence import CognitionEvidencePolicy
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore

RevisionMode = Literal["revise", "retract"]

STATUS_ACTIVE = "active"
STATUS_RETRACTED = "retracted"
STATUS_REVIEW_REQUIRED = "stale_review_required"


class ClaimRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_ref: ObjectRef
    mode: RevisionMode
    reason: str = Field(min_length=1)
    evidence_refs: tuple[ObjectRef, ...] = Field(min_length=1)
    replacement_content: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_request(self) -> "ClaimRevisionRequest":
        if self.target_ref.revision is None:
            raise ValueError("target_ref must pin an exact Claim revision")
        if not self.reason.strip():
            raise ValueError("reason must not be blank")
        for ref in self.evidence_refs:
            if ref.revision is None:
                raise ValueError("revision evidence must pin exact revisions")
        if self.mode == "revise" and not (self.replacement_content or "").strip():
            raise ValueError("revise requires replacement_content")
        return self


@dataclass(frozen=True, slots=True)
class ClaimRevisionReceipt:
    claim_id: str
    previous_revision: int
    new_revision: int
    mode: str
    evidence_set_id: str
    stale_refs: tuple[tuple[str, int], ...]
    skipped_already_advanced_refs: tuple[tuple[str, int], ...]
    world_revision: int


def _stable_id(prefix: str, *parts: object) -> str:
    raw = canonical_json_dumps(list(parts))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


class CognitionRevisionService:
    """Revise/retract a Claim and propagate review-required state downstream."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex | None = None,
        subject_id: str = "user_1",
        evidence_subject_ids: Sequence[str] | None = None,
        evidence_policy: CognitionEvidencePolicy | None = None,
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
        # C15-RCC-EVIDENCE-POLICY-001: structural, never optional. See
        # CognitionWritebackService.__init__ for the same contract.
        self.evidence_policy = evidence_policy or CognitionEvidencePolicy(
            store=store,
            index=index,
            subject_id=self.subject_id,
            allowed_subject_ids=tuple(self.evidence_subject_ids),
        )

    def _current_dependencies(self) -> tuple[Dependency, ...]:
        payloads = self.store.list_payloads(object_type=ObjectType.DEPENDENCY)
        return tuple(
            Dependency.model_validate(item)
            for item in payloads
            if str(item.get("subject_id") or "") in self.evidence_subject_ids
        )

    def _mark_stale(
        self,
        ref: ObjectRef,
        *,
        changed_ref: ObjectRef,
        changed_at: datetime,
        reason: str,
    ) -> WorldObject | None:
        latest_payload = self.store.get_payload(ref.object_id)
        latest_revision = int(latest_payload["revision"])
        if latest_revision != int(ref.revision or 0):
            # The dependent has already moved on since this dependency edge was made.
            return None

        object_type = ObjectType(str(latest_payload["object_type"]))
        model = canonical_model_for_object_type(object_type)
        data = dict(latest_payload)
        data["revision"] = latest_revision + 1
        data["learned_at"] = changed_at
        data["recorded_at"] = changed_at
        data["status"] = STATUS_REVIEW_REQUIRED

        metadata = dict(data.get("metadata") or {})
        stale_due_to = list(metadata.get("stale_due_to_refs") or [])
        marker = {
            "object_id": changed_ref.object_id,
            "revision": changed_ref.revision,
        }
        if marker not in stale_due_to:
            stale_due_to.append(marker)
        metadata.update(
            {
                "stale_due_to_refs": stale_due_to,
                "stale_reason": reason,
                "stale_at": changed_at.isoformat(),
            }
        )
        data["metadata"] = metadata

        if object_type is ObjectType.EVIDENCE_SET:
            data["stale"] = True
        if object_type is ObjectType.SUMMARY:
            data["summary_status"] = SummaryStatus.STALE.value

        return model.model_validate(data)

    def apply(
        self,
        request: ClaimRevisionRequest,
        *,
        changed_at: datetime,
    ) -> ClaimRevisionReceipt:
        changed = as_utc(changed_at, "changed_at")
        target = request.target_ref
        old_payload = self.store.get_payload(
            target.object_id,
            revision=target.revision,
        )
        if old_payload.get("object_type") != ObjectType.CLAIM.value:
            raise ValueError("target_ref must point to a Claim")

        latest_payload = self.store.get_payload(target.object_id)
        if int(latest_payload["revision"]) != int(target.revision):
            raise ValueError(
                "only the current Claim revision may be revised/retracted; "
                "inspect the latest revision first"
            )
        old_claim = Claim.model_validate(old_payload)
        if old_claim.subject_id != self.subject_id:
            raise ValueError(
                "revision target crosses the runtime subject scope: "
                f"{old_claim.subject_id!r} != {self.subject_id!r}"
            )
        if old_claim.status == STATUS_RETRACTED:
            raise ValueError(f"Claim is already retracted: status={old_claim.status!r}")
        # stale_review_required is intentionally revisable: propagation marks a
        # dependent for model review, and the resident AI must be able to replace
        # that stale revision with a new active understanding.

        # Subject isolation is checked first so cross-user refs keep reporting the
        # precise isolation violation rather than a generic closure failure.
        for ref in request.evidence_refs:
            evidence_payload = self.store.get_payload(
                ref.object_id,
                revision=ref.revision,
            )
            evidence_subject = str(evidence_payload.get("subject_id") or "")
            if evidence_subject not in self.evidence_subject_ids:
                raise ValueError(
                    "revision evidence crosses the allowed subject scope: "
                    f"{ref.object_id}@{ref.revision} belongs to {evidence_subject!r}"
                )

        self.evidence_policy.validate(
            request.evidence_refs,
            operation=f"cognition_revision.{request.mode}",
        )

        current_world_revision = int(self.store.current_world_revision())
        evidence_set_id = _stable_id(
            "evs_revision",
            target.object_id,
            target.revision,
            request.mode,
            tuple((ref.object_id, ref.revision) for ref in request.evidence_refs),
            changed.isoformat(),
        )
        evidence_set = EvidenceSet(
            object_id=evidence_set_id,
            subject_id=old_claim.subject_id,
            learned_at=changed,
            recorded_at=changed,
            created_by="cognition_revision:evidence",
            purpose=f"{request.mode} Claim {target.object_id}@{target.revision}",
            knowledge_window=KnowledgeWindow(
                knowledge_cutoff=changed,
                world_revision=current_world_revision,
            ),
            member_refs=list(request.evidence_refs),
            support_refs=list(request.evidence_refs) if request.mode == "revise" else [],
            counter_refs=list(request.evidence_refs) if request.mode == "retract" else [],
            selection_method="resident_model_selected_revision_evidence",
            coverage=EvidenceCoverage(
                expected_count=len(request.evidence_refs),
                observed_count=len(request.evidence_refs),
                coverage_ratio=1.0,
            ),
            metadata={
                "dimension": old_claim.metadata.get("dimension"),
                "revision_mode": request.mode,
                "target_ref": {
                    "object_id": target.object_id,
                    "revision": target.revision,
                },
            },
        )
        evidence_ref = ObjectRef(object_id=evidence_set_id, revision=1)

        new_revision = int(old_claim.revision) + 1
        metadata = dict(old_claim.metadata)
        metadata.update(
            {
                "revision_mode": request.mode,
                "revision_reason": request.reason.strip(),
                "supersedes_revision": int(old_claim.revision),
                "revision_evidence_set_ref": {
                    "object_id": evidence_set_id,
                    "revision": 1,
                },
            }
        )

        if request.mode == "revise":
            new_claim = Claim(
                **{
                    **old_claim.model_dump(mode="python", round_trip=True),
                    "revision": new_revision,
                    "content": request.replacement_content.strip(),
                    "confidence": (
                        old_claim.confidence
                        if request.confidence is None
                        else request.confidence
                    ),
                    "status": STATUS_ACTIVE,
                    "knowledge_state": old_claim.knowledge_state,
                    "support_evidence_set_refs": [evidence_ref],
                    "learned_at": changed,
                    "recorded_at": changed,
                    "asserted_at": changed,
                    "metadata": metadata,
                }
            )
        else:
            new_claim = Claim(
                **{
                    **old_claim.model_dump(mode="python", round_trip=True),
                    "revision": new_revision,
                    "status": STATUS_RETRACTED,
                    "knowledge_state": KnowledgeState.CONFLICT,
                    "confidence": 0.0 if request.confidence is None else request.confidence,
                    "counter_evidence_set_refs": [
                        *old_claim.counter_evidence_set_refs,
                        evidence_ref,
                    ],
                    "learned_at": changed,
                    "recorded_at": changed,
                    "asserted_at": changed,
                    "metadata": metadata,
                }
            )

        objects: list[WorldObject] = [evidence_set, new_claim]

        claim_dep = Dependency(
            object_id=_stable_id(
                "dep",
                target.object_id,
                new_revision,
                evidence_set_id,
                1,
            ),
            subject_id=old_claim.subject_id,
            learned_at=changed,
            recorded_at=changed,
            created_by="cognition_revision:dependency",
            dependent_ref=ObjectRef(object_id=target.object_id, revision=new_revision),
            dependency_ref=evidence_ref,
            dependency_type=f"claim_{request.mode}_uses_evidence_set",
        )
        objects.append(claim_dep)

        for ref in request.evidence_refs:
            objects.append(
                Dependency(
                    object_id=_stable_id(
                        "dep",
                        evidence_set_id,
                        1,
                        ref.object_id,
                        ref.revision,
                    ),
                    subject_id=old_claim.subject_id,
                    learned_at=changed,
                    recorded_at=changed,
                    created_by="cognition_revision:dependency",
                    dependent_ref=evidence_ref,
                    dependency_ref=ref,
                    dependency_type="revision_evidence_set_contains_source",
                )
            )

        dependencies = self._current_dependencies()
        impacted = collect_impacted_dependents(
            dependencies,
            target,
            transitive=True,
        )
        stale_refs: list[tuple[str, int]] = []
        skipped: list[tuple[str, int]] = []

        for ref in impacted:
            stale_obj = self._mark_stale(
                ref,
                changed_ref=target,
                changed_at=changed,
                reason=(
                    f"upstream Claim {target.object_id}@{target.revision} "
                    f"was {request.mode}d: {request.reason.strip()}"
                ),
            )
            if stale_obj is None:
                skipped.append((ref.object_id, int(ref.revision or 0)))
                continue
            objects.append(stale_obj)
            stale_refs.append((ref.object_id, int(ref.revision or 0)))
            objects.append(
                Dependency(
                    object_id=_stable_id(
                        "dep_stale",
                        stale_obj.object_id,
                        stale_obj.revision,
                        target.object_id,
                        target.revision,
                    ),
                    subject_id=stale_obj.subject_id,
                    learned_at=changed,
                    recorded_at=changed,
                    created_by="cognition_revision:propagation",
                    dependent_ref=ObjectRef(
                        object_id=stale_obj.object_id,
                        revision=stale_obj.revision,
                    ),
                    dependency_ref=target,
                    dependency_type="stale_due_to_superseded_cognition",
                )
            )

        operation_key = _stable_id(
            "revision",
            target.object_id,
            target.revision,
            request.mode,
            changed.isoformat(),
        )
        result = self.store.commit(
            objects,
            OperationRequest(
                operation_id=f"op_{operation_key}",
                operation_name=f"cognition.{request.mode}_claim",
                arguments={
                    "target": {
                        "object_id": target.object_id,
                        "revision": target.revision,
                    },
                    "mode": request.mode,
                    "reason": request.reason,
                    "stale_count": len(stale_refs),
                },
                expected_world_revision=current_world_revision,
                reason=(
                    f"forward-only Claim {request.mode} with dependency propagation"
                ),
                idempotency_key=f"cognition-revision:{operation_key}",
                source_class=SourceClass.AI_COGNITION,
            ),
        )
        if self.index is not None:
            self.index.catch_up()

        return ClaimRevisionReceipt(
            claim_id=target.object_id,
            previous_revision=int(target.revision),
            new_revision=new_revision,
            mode=request.mode,
            evidence_set_id=evidence_set_id,
            stale_refs=tuple(stale_refs),
            skipped_already_advanced_refs=tuple(skipped),
            world_revision=result.world_revision,
        )
