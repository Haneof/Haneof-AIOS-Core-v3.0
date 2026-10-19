"""ToolProposalPipeline: Full lifecycle management for self-evolving AIOS tools.

Fulfills AIOS 3.0 tool self-proposal and evolution mechanisms:
- Supports proposal lifecycle state machine:
  DRAFT -> SUBMITTED -> UNDER_REVIEW -> APPROVED / REJECTED -> EXECUTED -> RETIRED
- Complies with Constitution & Iron Rule #2: all state transitions append forward revisions;
  past proposal revisions are byte-level immutable.
- Provides native self-proposal strategy `propose_index_acceleration_tool` to remediate query latency.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Sequence

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.ids import new_object_id
from aios_core.contracts.models import ObjectRef, ToolProposal
from aios_core.contracts.refs import SourceRef
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.storage.sqlite_store import SQLiteWorldStore


class ToolProposalStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    RETIRED = "retired"


_VALID_TRANSITIONS: dict[ToolProposalStatus, set[ToolProposalStatus]] = {
    ToolProposalStatus.DRAFT: {ToolProposalStatus.SUBMITTED, ToolProposalStatus.RETIRED},
    ToolProposalStatus.SUBMITTED: {
        ToolProposalStatus.UNDER_REVIEW,
        ToolProposalStatus.APPROVED,
        ToolProposalStatus.REJECTED,
        ToolProposalStatus.RETIRED,
    },
    ToolProposalStatus.UNDER_REVIEW: {
        ToolProposalStatus.APPROVED,
        ToolProposalStatus.REJECTED,
        ToolProposalStatus.RETIRED,
    },
    ToolProposalStatus.APPROVED: {ToolProposalStatus.EXECUTED, ToolProposalStatus.RETIRED},
    ToolProposalStatus.REJECTED: {ToolProposalStatus.DRAFT, ToolProposalStatus.RETIRED},
    ToolProposalStatus.EXECUTED: {ToolProposalStatus.RETIRED},
    ToolProposalStatus.RETIRED: set(),
}


@dataclass(frozen=True, slots=True)
class ToolProposalReceipt:
    proposal_id: str
    revision: int
    status: ToolProposalStatus
    capability_gap: str
    world_revision: int


class ToolProposalPipeline:
    """Manages the drafting, review, execution, and retirement of dynamic tool proposals."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        subject_id: str = "user_1",
    ) -> None:
        self.store = store
        self.subject_id = subject_id

    def _get_status_from_payload(self, payload: dict) -> ToolProposalStatus:
        raw = payload.get("status") or (payload.get("metadata") or {}).get("proposal_status", ToolProposalStatus.DRAFT.value)
        try:
            return ToolProposalStatus(str(raw))
        except ValueError:
            return ToolProposalStatus.DRAFT

    def get_proposal(self, proposal_id: str) -> ToolProposal:
        """Fetch the latest visible revision of a ToolProposal."""
        payload = self.store.get_payload(proposal_id)
        if str(payload.get("subject_id") or "") != self.subject_id:
            raise ValueError(f"{proposal_id} crosses runtime subject scope")
        return ToolProposal.model_validate(payload)

    def get_proposal_status(self, proposal_id: str) -> ToolProposalStatus:
        """Fetch current status of a proposal."""
        payload = self.store.get_payload(proposal_id)
        return self._get_status_from_payload(payload)

    def list_proposals(
        self,
        *,
        status: ToolProposalStatus | None = None,
    ) -> list[ToolProposal]:
        """List active proposals, optionally filtered by status."""
        payloads = self.store.list_payloads(
            object_type=ObjectType.TOOL_PROPOSAL,
            subject_id=self.subject_id,
        )
        proposals: list[ToolProposal] = []
        for p in payloads:
            if p.get("deleted_at") is not None:
                continue
            if status is not None:
                cur_status = self._get_status_from_payload(p)
                if cur_status != status:
                    continue
            proposals.append(ToolProposal.model_validate(p))
        return proposals

    def draft_proposal(
        self,
        *,
        capability_gap: str,
        use_cases: Sequence[str],
        current_limitations: Sequence[str],
        proposed_interface: dict[str, Any],
        expected_benefit: str,
        validation_plan: str,
        created_by: str = "ai_cognition",
        created_at: datetime | None = None,
        custom_metadata: dict[str, Any] | None = None,
    ) -> ToolProposalReceipt:
        """Draft a new ToolProposal in DRAFT status."""
        if not capability_gap.strip():
            raise ValueError("capability_gap must not be blank")
        if not use_cases:
            raise ValueError("at least one use_case must be declared")
        if not expected_benefit.strip():
            raise ValueError("expected_benefit must not be blank")
        if not validation_plan.strip():
            raise ValueError("validation_plan must not be blank")

        dt = as_utc(created_at or datetime.now(timezone.utc), "created_at")
        proposal_id = new_object_id(ObjectType.TOOL_PROPOSAL)

        meta = dict(custom_metadata or {})
        meta["status_updated_at"] = dt.isoformat()

        proposal = ToolProposal(
            object_id=proposal_id,
            subject_id=self.subject_id,
            occurred=TemporalExtent.point(dt),
            learned_at=dt,
            recorded_at=dt,
            created_by=created_by,
            status=ToolProposalStatus.DRAFT.value,
            capability_gap=capability_gap.strip(),
            use_cases=list(use_cases),
            current_limitations=list(current_limitations),
            proposed_interface=dict(proposed_interface),
            expected_benefit=expected_benefit.strip(),
            validation_plan=validation_plan.strip(),
            metadata=meta,
        )

        expected_rev = self.store.current_world_revision()
        op = OperationRequest(
            operation_name="tools.draft_proposal",
            expected_world_revision=expected_rev,
            reason="Draft self-evolving tool proposal",
            idempotency_key=f"draft_{proposal_id}_{expected_rev}",
            source_class=SourceClass.AI_COGNITION,
        )
        commit_res = self.store.commit([proposal], op)

        return ToolProposalReceipt(
            proposal_id=proposal_id,
            revision=1,
            status=ToolProposalStatus.DRAFT,
            capability_gap=proposal.capability_gap,
            world_revision=commit_res.world_revision,
        )

    def submit_proposal(
        self,
        *,
        proposal_ref: ObjectRef,
        submitted_by: str = "ai_cognition",
        submitted_at: datetime | None = None,
    ) -> ToolProposalReceipt:
        """Submit a drafted proposal for formal architectural review."""
        if proposal_ref.revision is None or proposal_ref.revision < 1:
            raise ValueError("proposal_ref requires pinned revision")

        payload = self.store.get_payload(proposal_ref.object_id, revision=proposal_ref.revision)
        cur_status = self._get_status_from_payload(payload)

        if ToolProposalStatus.SUBMITTED not in _VALID_TRANSITIONS.get(cur_status, set()):
            raise ValueError(
                f"Invalid proposal status transition from {cur_status.value} to {ToolProposalStatus.SUBMITTED.value}"
            )

        dt = as_utc(submitted_at or datetime.now(timezone.utc), "submitted_at")
        old_proposal = ToolProposal.model_validate(payload)

        meta = dict(old_proposal.metadata)
        meta["submitted_by"] = submitted_by
        meta["submitted_at"] = dt.isoformat()
        meta["supersedes_revision"] = old_proposal.revision

        rec_at = max(dt, old_proposal.recorded_at)
        lrn_at = max(dt, old_proposal.learned_at)
        if rec_at < lrn_at:
            rec_at = lrn_at

        new_proposal = ToolProposal(
            object_id=old_proposal.object_id,
            revision=old_proposal.revision + 1,
            subject_id=old_proposal.subject_id,
            occurred=old_proposal.occurred,
            learned_at=lrn_at,
            recorded_at=rec_at,
            created_by=submitted_by,
            source_refs=[SourceRef(object_id=old_proposal.object_id, revision=old_proposal.revision)],
            status=ToolProposalStatus.SUBMITTED.value,
            capability_gap=old_proposal.capability_gap,
            use_cases=old_proposal.use_cases,
            current_limitations=old_proposal.current_limitations,
            proposed_interface=old_proposal.proposed_interface,
            expected_benefit=old_proposal.expected_benefit,
            validation_plan=old_proposal.validation_plan,
            metadata=meta,
        )

        expected_rev = self.store.current_world_revision()
        op = OperationRequest(
            operation_name="tools.submit_proposal",
            expected_world_revision=expected_rev,
            reason=f"Submit proposal {old_proposal.object_id} for review",
            idempotency_key=f"submit_{old_proposal.object_id}_{new_proposal.revision}_{expected_rev}",
            source_class=SourceClass.AI_COGNITION,
        )
        commit_res = self.store.commit([new_proposal], op)

        return ToolProposalReceipt(
            proposal_id=new_proposal.object_id,
            revision=new_proposal.revision,
            status=ToolProposalStatus.SUBMITTED,
            capability_gap=new_proposal.capability_gap,
            world_revision=commit_res.world_revision,
        )

    def review_proposal(
        self,
        *,
        proposal_ref: ObjectRef,
        decision: ToolProposalStatus,  # APPROVED or REJECTED
        reviewer: str,
        review_comments: str,
        risk_level: str = "LOW",
        reviewed_at: datetime | None = None,
    ) -> ToolProposalReceipt:
        """Perform architectural review, advancing proposal to APPROVED or REJECTED."""
        if proposal_ref.revision is None or proposal_ref.revision < 1:
            raise ValueError("proposal_ref requires pinned revision")

        if decision not in {ToolProposalStatus.APPROVED, ToolProposalStatus.REJECTED}:
            raise ValueError(f"Decision must be APPROVED or REJECTED, got {decision}")

        payload = self.store.get_payload(proposal_ref.object_id, revision=proposal_ref.revision)
        cur_status = self._get_status_from_payload(payload)

        # Allow review directly from SUBMITTED or UNDER_REVIEW
        allowed_targets = _VALID_TRANSITIONS.get(cur_status, set())
        if decision not in allowed_targets:
            raise ValueError(
                f"Invalid proposal status transition from {cur_status.value} to {decision.value}"
            )

        dt = as_utc(reviewed_at or datetime.now(timezone.utc), "reviewed_at")
        old_proposal = ToolProposal.model_validate(payload)

        meta = dict(old_proposal.metadata)
        meta["reviewer"] = reviewer
        meta["review_comments"] = review_comments
        meta["risk_level"] = risk_level
        meta["reviewed_at"] = dt.isoformat()
        meta["supersedes_revision"] = old_proposal.revision

        rec_at = max(dt, old_proposal.recorded_at)
        lrn_at = max(dt, old_proposal.learned_at)
        if rec_at < lrn_at:
            rec_at = lrn_at

        new_proposal = ToolProposal(
            object_id=old_proposal.object_id,
            revision=old_proposal.revision + 1,
            subject_id=old_proposal.subject_id,
            occurred=old_proposal.occurred,
            learned_at=lrn_at,
            recorded_at=rec_at,
            created_by=reviewer,
            source_refs=[SourceRef(object_id=old_proposal.object_id, revision=old_proposal.revision)],
            status=decision.value,
            capability_gap=old_proposal.capability_gap,
            use_cases=old_proposal.use_cases,
            current_limitations=old_proposal.current_limitations,
            proposed_interface=old_proposal.proposed_interface,
            expected_benefit=old_proposal.expected_benefit,
            validation_plan=old_proposal.validation_plan,
            metadata=meta,
        )

        expected_rev = self.store.current_world_revision()
        op = OperationRequest(
            operation_name="tools.review_proposal",
            expected_world_revision=expected_rev,
            reason=f"Review proposal {old_proposal.object_id} -> {decision.value}",
            idempotency_key=f"review_{old_proposal.object_id}_{new_proposal.revision}_{expected_rev}",
            source_class=SourceClass.AI_COGNITION,
        )
        commit_res = self.store.commit([new_proposal], op)

        return ToolProposalReceipt(
            proposal_id=new_proposal.object_id,
            revision=new_proposal.revision,
            status=decision,
            capability_gap=new_proposal.capability_gap,
            world_revision=commit_res.world_revision,
        )

    def execute_proposal(
        self,
        *,
        proposal_ref: ObjectRef,
        executor: str = "runtime_kernel",
        execution_context: dict[str, Any] | None = None,
        executed_at: datetime | None = None,
    ) -> ToolProposalReceipt:
        """Mark an approved tool proposal as EXECUTED (mounted in runtime)."""
        if proposal_ref.revision is None or proposal_ref.revision < 1:
            raise ValueError("proposal_ref requires pinned revision")

        payload = self.store.get_payload(proposal_ref.object_id, revision=proposal_ref.revision)
        cur_status = self._get_status_from_payload(payload)

        if cur_status != ToolProposalStatus.APPROVED:
            raise ValueError(
                f"Cannot execute proposal in status {cur_status.value}; must be approved"
            )

        dt = as_utc(executed_at or datetime.now(timezone.utc), "executed_at")
        old_proposal = ToolProposal.model_validate(payload)

        meta = dict(old_proposal.metadata)
        meta["executor"] = executor
        meta["execution_context"] = execution_context or {}
        meta["executed_at"] = dt.isoformat()
        meta["supersedes_revision"] = old_proposal.revision

        rec_at = max(dt, old_proposal.recorded_at)
        lrn_at = max(dt, old_proposal.learned_at)
        if rec_at < lrn_at:
            rec_at = lrn_at

        new_proposal = ToolProposal(
            object_id=old_proposal.object_id,
            revision=old_proposal.revision + 1,
            subject_id=old_proposal.subject_id,
            occurred=old_proposal.occurred,
            learned_at=lrn_at,
            recorded_at=rec_at,
            created_by=executor,
            source_refs=[SourceRef(object_id=old_proposal.object_id, revision=old_proposal.revision)],
            status=ToolProposalStatus.EXECUTED.value,
            capability_gap=old_proposal.capability_gap,
            use_cases=old_proposal.use_cases,
            current_limitations=old_proposal.current_limitations,
            proposed_interface=old_proposal.proposed_interface,
            expected_benefit=old_proposal.expected_benefit,
            validation_plan=old_proposal.validation_plan,
            metadata=meta,
        )

        expected_rev = self.store.current_world_revision()
        op = OperationRequest(
            operation_name="tools.execute_proposal",
            expected_world_revision=expected_rev,
            reason=f"Execute tool proposal {old_proposal.object_id}",
            idempotency_key=f"execute_{old_proposal.object_id}_{new_proposal.revision}_{expected_rev}",
            source_class=SourceClass.AI_COGNITION,
        )
        commit_res = self.store.commit([new_proposal], op)

        return ToolProposalReceipt(
            proposal_id=new_proposal.object_id,
            revision=new_proposal.revision,
            status=ToolProposalStatus.EXECUTED,
            capability_gap=new_proposal.capability_gap,
            world_revision=commit_res.world_revision,
        )

    def retire_proposal(
        self,
        *,
        proposal_ref: ObjectRef,
        reason: str,
        retired_by: str = "runtime_kernel",
        retired_at: datetime | None = None,
    ) -> ToolProposalReceipt:
        """Retire a proposal."""
        if proposal_ref.revision is None or proposal_ref.revision < 1:
            raise ValueError("proposal_ref requires pinned revision")

        payload = self.store.get_payload(proposal_ref.object_id, revision=proposal_ref.revision)
        cur_status = self._get_status_from_payload(payload)

        if ToolProposalStatus.RETIRED not in _VALID_TRANSITIONS.get(cur_status, set()):
            raise ValueError(
                f"Cannot retire proposal in status {cur_status.value}"
            )

        dt = as_utc(retired_at or datetime.now(timezone.utc), "retired_at")
        old_proposal = ToolProposal.model_validate(payload)

        meta = dict(old_proposal.metadata)
        meta["retirement_reason"] = reason
        meta["retired_by"] = retired_by
        meta["retired_at"] = dt.isoformat()
        meta["supersedes_revision"] = old_proposal.revision

        rec_at = max(dt, old_proposal.recorded_at)
        lrn_at = max(dt, old_proposal.learned_at)
        if rec_at < lrn_at:
            rec_at = lrn_at

        new_proposal = ToolProposal(
            object_id=old_proposal.object_id,
            revision=old_proposal.revision + 1,
            subject_id=old_proposal.subject_id,
            occurred=old_proposal.occurred,
            learned_at=lrn_at,
            recorded_at=rec_at,
            created_by=retired_by,
            source_refs=[SourceRef(object_id=old_proposal.object_id, revision=old_proposal.revision)],
            status=ToolProposalStatus.RETIRED.value,
            capability_gap=old_proposal.capability_gap,
            use_cases=old_proposal.use_cases,
            current_limitations=old_proposal.current_limitations,
            proposed_interface=old_proposal.proposed_interface,
            expected_benefit=old_proposal.expected_benefit,
            validation_plan=old_proposal.validation_plan,
            metadata=meta,
        )

        expected_rev = self.store.current_world_revision()
        op = OperationRequest(
            operation_name="tools.retire_proposal",
            expected_world_revision=expected_rev,
            reason=f"Retire tool proposal {old_proposal.object_id}: {reason}",
            idempotency_key=f"retire_{old_proposal.object_id}_{new_proposal.revision}_{expected_rev}",
            source_class=SourceClass.AI_COGNITION,
        )
        commit_res = self.store.commit([new_proposal], op)

        return ToolProposalReceipt(
            proposal_id=new_proposal.object_id,
            revision=new_proposal.revision,
            status=ToolProposalStatus.RETIRED,
            capability_gap=new_proposal.capability_gap,
            world_revision=commit_res.world_revision,
        )

    def propose_index_acceleration_tool(
        self,
        *,
        observed_latency_ms: float,
        latency_threshold_ms: float = 100.0,
        target_index: str = "world_search_index",
        proposed_by: str = "ai_cognition",
        created_at: datetime | None = None,
    ) -> ToolProposalReceipt:
        """Native self-proposal strategy: Formulates and submits an index acceleration tool."""
        if observed_latency_ms <= latency_threshold_ms:
            raise ValueError(
                f"Observed latency {observed_latency_ms:.1f}ms does not exceed threshold {latency_threshold_ms:.1f}ms"
            )

        draft = self.draft_proposal(
            capability_gap=(
                f"Associative memory query latency on '{target_index}' ({observed_latency_ms:.1f}ms) "
                f"exceeds the real-time threshold ({latency_threshold_ms:.1f}ms)."
            ),
            use_cases=[
                "Sub-50ms conversational memory recall",
                "Non-blocking background cognitive projection replay",
            ],
            current_limitations=[
                "Single-column index causes secondary table scan on complex joins",
                "Lock contention during concurrent writeback operations",
            ],
            proposed_interface={
                "tool_name": "accelerate_search_index",
                "action": "CREATE_COMPOSITE_INDEX",
                "target_table": "object_revisions",
                "index_columns": ["object_type", "subject_id", "recorded_at"],
                "index_name": f"idx_composite_{target_index}",
            },
            expected_benefit=f"Reduces query latency by >= 60% (from {observed_latency_ms:.1f}ms to < 30ms)",
            validation_plan="Benchmark 100 synthetic associative queries before and after index application; verify latency reduction.",
            created_by=proposed_by,
            created_at=created_at,
            custom_metadata={"observed_latency_ms": observed_latency_ms, "target_index": target_index},
        )

        # Directly advance to SUBMITTED
        return self.submit_proposal(
            proposal_ref=ObjectRef(object_id=draft.proposal_id, revision=draft.revision),
            submitted_by=proposed_by,
            submitted_at=created_at,
        )
