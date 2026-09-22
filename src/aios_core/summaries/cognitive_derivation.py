"""C14 deterministic Summary -> cognition-opportunity scheduling.

This module only decides whether a durable, auditable Resident inspection
opportunity is legally routable. It never interprets Summary prose and never
creates cognition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from pydantic import ValidationError

from aios_core.contracts.enums import (
    AttentionClass,
    ObjectType,
    SummaryStatus,
    WakeSource,
)
from aios_core.contracts.models import Summary
from aios_core.contracts.refs import ObjectRef
from aios_core.policy.evidence import (
    CognitionEvidencePolicy,
    DerivedLineageClass,
    DerivedLineageView,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError
from aios_core.wake.service import WakeBus, WakeSignalReceipt, WakeSignalRequest

# Backward-compatibility re-exports
__all__ = [
    "CognitiveDerivationReconcileResult",
    "CognitiveDerivationScheduleReceipt",
    "CognitiveDerivationScheduler",
    "DerivedLineageClass",
    "DerivedLineageView",
]


@dataclass(frozen=True, slots=True)
class CognitiveDerivationScheduleReceipt:
    summary_ref: ObjectRef
    eligible: bool
    reason: str
    lineage: DerivedLineageView
    wake: WakeSignalReceipt | None = None


@dataclass(frozen=True, slots=True)
class CognitiveDerivationReconcileResult:
    examined: int
    scheduled: tuple[CognitiveDerivationScheduleReceipt, ...]


class CognitiveDerivationScheduler:
    """Mechanically ensure one durable C14 opportunity per eligible Summary revision."""

    RULE_ID = "c14.summary_revision.cognitive_derivation"

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        index: WorldSearchIndex | None = None,
        wake_bus: WakeBus | None = None,
        subject_id: str = "user_1",
        allowed_subject_ids: Sequence[str] | None = None,
        evidence_policy: CognitionEvidencePolicy | None = None,
    ) -> None:
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must not be blank")
        self.store = store
        self.index = index
        self.subject_id = subject_id.strip()
        allowed_subjects = {self.subject_id}
        allowed_subjects.update(
            str(item).strip()
            for item in (allowed_subject_ids or ())
            if str(item).strip()
        )
        self.allowed_subject_ids = frozenset(allowed_subjects)
        self.wake_bus = wake_bus or WakeBus(
            store=store,
            index=index,
            subject_id=self.subject_id,
        )
        self.evidence_policy = evidence_policy or CognitionEvidencePolicy(
            store=store,
            index=index,
            subject_id=self.subject_id,
            allowed_subject_ids=self.allowed_subject_ids,
        )

    def _support_dependencies(self) -> dict[tuple[str, int], tuple[ObjectRef, ...]]:
        return self.evidence_policy._support_dependencies()

    def derive_lineage_for_refs(
        self,
        refs: Sequence[ObjectRef],
        *,
        support_dependencies: Mapping[
            tuple[str, int],
            tuple[ObjectRef, ...],
        ] | None = None,
    ) -> DerivedLineageView:
        """Resolve exact support closure for arbitrary pinned cognition evidence.

        Delegates to CognitionEvidencePolicy without duplicating lineage traversal code.
        """
        return self.evidence_policy.derive_lineage_for_refs(
            refs,
            support_dependencies=support_dependencies,
        )

    def derive_lineage(self, summary_ref: ObjectRef) -> DerivedLineageView:
        return self.derive_lineage_for_refs((summary_ref,))

    def _current_eligible_summary(
        self,
        summary_ref: ObjectRef,
    ) -> tuple[Summary | None, str]:
        if summary_ref.revision is None:
            return None, "summary_ref_unpinned"
        try:
            record = self.store.object_revision_record(
                summary_ref.object_id,
                revision=summary_ref.revision,
            )
            payload = self.store.get_payload(
                summary_ref.object_id,
                revision=summary_ref.revision,
            )
        except (StoreError, TypeError, ValueError):
            return None, "summary_missing_or_corrupt"

        if str(record.get("subject_id") or "") != self.subject_id:
            return None, "summary_cross_subject"
        if str(record.get("object_type") or "") != ObjectType.SUMMARY.value:
            return None, "not_summary"
        if str(record.get("revision_kind") or "content") != "content":
            return None, "summary_tombstoned"
        if not bool(record.get("is_latest")):
            return None, "summary_revision_superseded"

        try:
            summary = Summary.model_validate(payload)
        except ValidationError:
            return None, "summary_invalid"
        if summary.summary_status is not SummaryStatus.CURRENT:
            return None, f"summary_{summary.summary_status.value}"
        if str(summary.status or "").strip().lower() != "active":
            return None, "summary_inactive"
        if bool(summary.coverage.get("truncated")):
            return None, "summary_incomplete"
        dimension = summary.metadata.get("dimension") or summary.coverage.get("dimension")
        if not isinstance(dimension, str) or not dimension.strip():
            return None, "summary_dimension_missing"
        return summary, "eligible_state"

    def ensure(
        self,
        summary_ref: ObjectRef,
        *,
        support_dependencies: Mapping[
            tuple[str, int],
            tuple[ObjectRef, ...],
        ] | None = None,
    ) -> CognitiveDerivationScheduleReceipt:
        summary, state_reason = self._current_eligible_summary(summary_ref)
        lineage = self.derive_lineage_for_refs(
            (summary_ref,),
            support_dependencies=support_dependencies,
        )
        if summary is None:
            return CognitiveDerivationScheduleReceipt(
                summary_ref=summary_ref,
                eligible=False,
                reason=state_reason,
                lineage=lineage,
            )
        if lineage.classification not in {
            DerivedLineageClass.REALITY,
            DerivedLineageClass.MIXED,
        }:
            return CognitiveDerivationScheduleReceipt(
                summary_ref=summary_ref,
                eligible=False,
                reason=f"lineage_{lineage.classification.value.lower()}",
                lineage=lineage,
            )
        if not lineage.grounding_leaf_refs:
            return CognitiveDerivationScheduleReceipt(
                summary_ref=summary_ref,
                eligible=False,
                reason="lineage_no_direct_reality_grounding",
                lineage=lineage,
            )

        dimension = str(
            summary.metadata.get("dimension")
            or summary.coverage.get("dimension")
        ).strip()
        dedupe_key = (
            f"c14:cognitive-derivation:"
            f"{summary.object_id}:{summary.revision}"
        )
        wake = self.wake_bus.emit(
            WakeSignalRequest(
                wake_source=WakeSource.COGNITIVE_DERIVATION,
                rule_id=self.RULE_ID,
                observed_at=summary.recorded_at,
                evidence_refs=(summary_ref,),
                priority=50,
                dedupe_key=dedupe_key,
                cooldown_seconds=0,
                attention_class=AttentionClass.BACKGROUND,
                metadata={
                    "trigger_kind": "dimension_summary_cognitive_derivation",
                    "summary_ref": summary_ref.model_dump(mode="json"),
                    "summary_dimension": dimension,
                    "granularity": summary.granularity,
                    "summary_window": summary.summary_time.model_dump(mode="json"),
                    "derived_lineage": lineage.audit_payload(),
                    "semantic_conclusions": False,
                    "routing_only": True,
                },
            )
        )
        return CognitiveDerivationScheduleReceipt(
            summary_ref=summary_ref,
            eligible=True,
            reason="scheduled",
            lineage=lineage,
            wake=wake,
        )

    def reconcile(self) -> CognitiveDerivationReconcileResult:
        """Recover eligible current Summary revisions that missed their Wake.

        The World Summary revision and deterministic Wake identity are the durable
        recovery ledger. No second scheduler database or cursor is required.
        """
        receipts: list[CognitiveDerivationScheduleReceipt] = []
        examined = 0
        support_dependencies = self._support_dependencies()
        for payload in self.store.list_payloads(
            object_type=ObjectType.SUMMARY,
            subject_id=self.subject_id,
        ):
            object_id = payload.get("object_id")
            revision = payload.get("revision")
            if not isinstance(object_id, str) or not isinstance(revision, int):
                continue
            examined += 1
            receipt = self.ensure(
                ObjectRef(object_id=object_id, revision=revision),
                support_dependencies=support_dependencies,
            )
            if receipt.eligible:
                receipts.append(receipt)
        return CognitiveDerivationReconcileResult(
            examined=examined,
            scheduled=tuple(receipts),
        )