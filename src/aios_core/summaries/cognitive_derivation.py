"""C14 deterministic Summary -> cognition-opportunity scheduling.

This module only decides whether a durable, auditable Resident inspection
opportunity is legally routable.  It never interprets Summary prose and never
creates cognition.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

from pydantic import ValidationError

from aios_core.contracts.enums import (
    AttentionClass,
    ObjectType,
    SourceClass,
    SummaryStatus,
    WakeSource,
)
from aios_core.contracts.models import Dependency, EvidenceSet, Summary, Wake
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError
from aios_core.wake.service import WakeBus, WakeSignalReceipt, WakeSignalRequest


class DerivedLineageClass(StrEnum):
    """Mechanically-derived routing view; never persisted as source truth."""

    REALITY = "REALITY"
    AI_COGNITION_ONLY = "AI_COGNITION_ONLY"
    MAINTENANCE_ONLY = "MAINTENANCE_ONLY"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class DerivedLineageView:
    classification: DerivedLineageClass
    leaf_refs: tuple[ObjectRef, ...]
    unresolved_refs: tuple[ObjectRef, ...]
    issues: tuple[str, ...]
    has_reality: bool
    has_ai_cognition: bool
    has_maintenance: bool

    def audit_payload(self) -> dict[str, Any]:
        return {
            "classification": self.classification.value,
            "leaf_refs": [ref.model_dump(mode="json") for ref in self.leaf_refs],
            "unresolved_refs": [
                ref.model_dump(mode="json") for ref in self.unresolved_refs
            ],
            "issues": list(self.issues),
            "has_reality": self.has_reality,
            "has_ai_cognition": self.has_ai_cognition,
            "has_maintenance": self.has_maintenance,
        }


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


@dataclass(slots=True)
class _TraversalState:
    leaves: dict[tuple[str, int], ObjectRef]
    unresolved: dict[tuple[str, int | None], ObjectRef]
    issues: set[str]
    has_reality: bool = False
    has_ai_cognition: bool = False
    has_maintenance: bool = False


# These edges already exist in the unified World and express support/source
# provenance.  Operational ordering/cancellation edges are deliberately absent.
_SUPPORT_DEPENDENCY_TYPES = frozenset(
    {
        "summary_uses_source",
        "stale_summary_preserves_source",
        "claim_uses_evidence_set",
        "claim_revise_uses_evidence_set",
        "claim_retract_uses_evidence_set",
        "evidence_set_contains_source",
        "revision_evidence_set_contains_source",
        "goal_uses_evidence_set",
        "goal_evidence_set_contains_source",
        "goal_transition_uses_evidence_set",
        "goal_transition_evidence_contains_source",
        "task_transition_uses_evidence",
        "task_terminal_uses_world_evidence",
        "action_uses_evidence_set",
        "action_evidence_set_contains_source",
        "outcome_reports_action",
        "outcome_uses_evidence",
    }
)

_REALITY_SOURCE_CLASSES = frozenset(
    {
        SourceClass.USER,
        SourceClass.SENSOR,
        SourceClass.PLATFORM,
        SourceClass.SAFETY,
    }
)


def _pinned_object_ref(ref: ObjectRef | SourceRef) -> ObjectRef | None:
    if ref.revision is None:
        return None
    return ObjectRef(object_id=ref.object_id, revision=ref.revision)


def _unique_refs(refs: list[ObjectRef]) -> tuple[ObjectRef, ...]:
    by_key: dict[tuple[str, int], ObjectRef] = {}
    for ref in refs:
        if ref.revision is None:
            continue
        by_key[(ref.object_id, ref.revision)] = ref
    return tuple(by_key[key] for key in sorted(by_key))


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
    ) -> None:
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id must not be blank")
        self.store = store
        self.index = index
        self.subject_id = subject_id.strip()
        self.wake_bus = wake_bus or WakeBus(
            store=store,
            index=index,
            subject_id=self.subject_id,
        )

    def _support_dependencies(self) -> dict[tuple[str, int], tuple[ObjectRef, ...]]:
        grouped: dict[tuple[str, int], list[ObjectRef]] = {}
        for payload in self.store.list_payloads(
            object_type=ObjectType.DEPENDENCY,
            subject_id=self.subject_id,
        ):
            try:
                dep = Dependency.model_validate(payload)
            except (ValidationError, TypeError, ValueError):
                continue
            if dep.dependency_type not in _SUPPORT_DEPENDENCY_TYPES:
                continue
            if (
                dep.dependent_ref.revision is None
                or dep.dependency_ref.revision is None
            ):
                continue
            key = (dep.dependent_ref.object_id, dep.dependent_ref.revision)
            grouped.setdefault(key, []).append(dep.dependency_ref)
        return {
            key: _unique_refs(value)
            for key, value in grouped.items()
        }

    @staticmethod
    def _record_unresolved(
        state: _TraversalState,
        ref: ObjectRef,
        reason: str,
    ) -> None:
        state.unresolved[(ref.object_id, ref.revision)] = ref
        state.issues.add(reason)

    @staticmethod
    def _record_atomic_source(
        state: _TraversalState,
        ref: ObjectRef,
        source_class: SourceClass,
    ) -> None:
        if ref.revision is None:
            return
        state.leaves[(ref.object_id, ref.revision)] = ref
        if source_class in _REALITY_SOURCE_CLASSES:
            state.has_reality = True
        elif source_class is SourceClass.AI_COGNITION:
            state.has_ai_cognition = True
        elif source_class is SourceClass.MAINTENANCE:
            state.has_maintenance = True

    @staticmethod
    def _payload_source_refs(
        payload: Mapping[str, Any],
        *,
        state: _TraversalState,
        owner_ref: ObjectRef,
    ) -> list[ObjectRef]:
        raw_refs = payload.get("source_refs") or []
        if not isinstance(raw_refs, list):
            CognitiveDerivationScheduler._record_unresolved(
                state,
                owner_ref,
                "invalid_source_refs",
            )
            return []

        refs: list[ObjectRef] = []
        for raw in raw_refs:
            try:
                parsed = SourceRef.model_validate(raw)
            except (ValidationError, TypeError, ValueError):
                CognitiveDerivationScheduler._record_unresolved(
                    state,
                    owner_ref,
                    "invalid_source_ref",
                )
                continue
            pinned = _pinned_object_ref(parsed)
            if pinned is None:
                CognitiveDerivationScheduler._record_unresolved(
                    state,
                    ObjectRef(object_id=parsed.object_id),
                    "unpinned_source_ref",
                )
                continue
            refs.append(pinned)
        return refs

    @staticmethod
    def _conversation_source_override(
        payload: Mapping[str, Any],
    ) -> SourceClass | None:
        """Preserve user/assistant provenance for legacy combined turn commits.

        Older commit_turn() revisions persisted both messages in one USER commit,
        but each Observation already contains an exact mechanical role marker.
        This uses that durable marker only; no text or semantic inference.
        """

        if str(payload.get("object_type") or "") != ObjectType.OBSERVATION.value:
            return None
        if str(payload.get("source_kind") or "") != "user_ai_interaction":
            return None
        metadata = payload.get("metadata")
        if not isinstance(metadata, Mapping):
            return None
        role = str(metadata.get("role") or "").strip()
        if role == "assistant":
            return SourceClass.AI_COGNITION
        if role == "user":
            return SourceClass.USER
        return None

    def _walk(
        self,
        ref: ObjectRef,
        *,
        state: _TraversalState,
        dependencies: Mapping[tuple[str, int], tuple[ObjectRef, ...]],
        active_stack: set[tuple[str, int]],
        completed: set[tuple[str, int]],
    ) -> None:
        if ref.revision is None:
            self._record_unresolved(state, ref, "unpinned_ref")
            return
        key = (ref.object_id, ref.revision)
        if key in active_stack:
            self._record_unresolved(state, ref, "lineage_cycle")
            return
        if key in completed:
            return

        try:
            record = self.store.object_revision_record(
                ref.object_id,
                revision=ref.revision,
            )
            payload = self.store.get_payload(
                ref.object_id,
                revision=ref.revision,
            )
        except (StoreError, TypeError, ValueError):
            self._record_unresolved(state, ref, "missing_or_corrupt_ref")
            return

        if str(record.get("subject_id") or "") != self.subject_id:
            self._record_unresolved(state, ref, "cross_subject_ref")
            return
        if str(record.get("revision_kind") or "content") != "content":
            self._record_unresolved(state, ref, "non_content_revision")
            return

        try:
            object_type = ObjectType(str(record.get("object_type") or ""))
            source_class = SourceClass(str(record.get("source_class") or ""))
        except ValueError:
            self._record_unresolved(state, ref, "invalid_durable_provenance")
            return

        active_stack.add(key)
        try:
            children = self._payload_source_refs(
                payload,
                state=state,
                owner_ref=ref,
            )
            children.extend(dependencies.get(key, ()))

            if object_type is ObjectType.SUMMARY:
                try:
                    summary = Summary.model_validate(payload)
                except ValidationError:
                    self._record_unresolved(state, ref, "invalid_summary_payload")
                    return
                if summary.evidence_set_ref is not None:
                    pinned = _pinned_object_ref(summary.evidence_set_ref)
                    if pinned is None:
                        self._record_unresolved(
                            state,
                            ObjectRef(object_id=summary.evidence_set_ref.object_id),
                            "unpinned_summary_evidence_ref",
                        )
                    else:
                        children.append(pinned)
                for item in summary.claim_refs:
                    pinned = _pinned_object_ref(item)
                    if pinned is None:
                        self._record_unresolved(
                            state,
                            ObjectRef(object_id=item.object_id),
                            "unpinned_summary_claim_ref",
                        )
                    else:
                        children.append(pinned)
                # Summary's MAINTENANCE commit is scaffolding, never its lineage truth.
                if not children:
                    self._record_unresolved(state, ref, "summary_has_no_pinned_lineage")
                    return

            elif object_type is ObjectType.EVIDENCE_SET:
                try:
                    evidence = EvidenceSet.model_validate(payload)
                except ValidationError:
                    self._record_unresolved(state, ref, "invalid_evidence_set_payload")
                    return
                for item in (
                    *evidence.member_refs,
                    *evidence.support_refs,
                    *evidence.counter_refs,
                    *evidence.context_refs,
                ):
                    pinned = _pinned_object_ref(item)
                    if pinned is None:
                        self._record_unresolved(
                            state,
                            ObjectRef(object_id=item.object_id),
                            "unpinned_evidence_ref",
                        )
                    else:
                        children.append(pinned)
                if evidence.selector is not None and not (
                    evidence.member_refs
                    or evidence.support_refs
                    or evidence.counter_refs
                    or evidence.context_refs
                ):
                    self._record_unresolved(
                        state,
                        ref,
                        "selector_only_evidence_set_has_no_pinned_closure",
                    )
                # EvidenceSet is a support container, not terminal source truth.

            elif object_type is ObjectType.DEPENDENCY:
                try:
                    dependency = Dependency.model_validate(payload)
                except ValidationError:
                    self._record_unresolved(state, ref, "invalid_dependency_payload")
                    return
                pinned = _pinned_object_ref(dependency.dependency_ref)
                if pinned is None:
                    self._record_unresolved(
                        state,
                        ObjectRef(object_id=dependency.dependency_ref.object_id),
                        "unpinned_dependency_ref",
                    )
                else:
                    children.append(pinned)

            elif object_type is ObjectType.WAKE:
                try:
                    wake = Wake.model_validate(payload)
                except ValidationError:
                    self._record_unresolved(state, ref, "invalid_wake_payload")
                    return
                for item in wake.evidence_refs:
                    pinned = _pinned_object_ref(item)
                    if pinned is None:
                        self._record_unresolved(
                            state,
                            ObjectRef(object_id=item.object_id),
                            "unpinned_wake_evidence_ref",
                        )
                    else:
                        children.append(pinned)
                # Wake is routing state, never terminal reality evidence.

            else:
                override = self._conversation_source_override(payload)
                if (
                    str(payload.get("object_type") or "")
                    == ObjectType.OBSERVATION.value
                    and str(payload.get("source_kind") or "") == "user_ai_interaction"
                    and override is None
                ):
                    self._record_unresolved(
                        state,
                        ref,
                        "conversation_observation_role_unknown",
                    )
                    return
                self._record_atomic_source(
                    state,
                    ref,
                    override or source_class,
                )

                # Known support EvidenceSet fields are structural refs, not prose.
                for field_name in (
                    "support_evidence_set_refs",
                    "counter_evidence_set_refs",
                    "evidence_set_refs",
                ):
                    raw_items = payload.get(field_name) or []
                    if not isinstance(raw_items, list):
                        self._record_unresolved(
                            state,
                            ref,
                            f"invalid_{field_name}",
                        )
                        continue
                    for raw in raw_items:
                        try:
                            item = ObjectRef.model_validate(raw)
                        except (ValidationError, TypeError, ValueError):
                            self._record_unresolved(
                                state,
                                ref,
                                f"invalid_{field_name}_ref",
                            )
                            continue
                        pinned = _pinned_object_ref(item)
                        if pinned is None:
                            self._record_unresolved(
                                state,
                                ObjectRef(object_id=item.object_id),
                                f"unpinned_{field_name}_ref",
                            )
                        else:
                            children.append(pinned)

            for child in _unique_refs(children):
                self._walk(
                    child,
                    state=state,
                    dependencies=dependencies,
                    active_stack=active_stack,
                    completed=completed,
                )
        finally:
            active_stack.discard(key)
            completed.add(key)

    def derive_lineage(self, summary_ref: ObjectRef) -> DerivedLineageView:
        state = _TraversalState(
            leaves={},
            unresolved={},
            issues=set(),
        )
        if summary_ref.revision is None:
            self._record_unresolved(state, summary_ref, "summary_ref_unpinned")
        else:
            self._walk(
                summary_ref,
                state=state,
                dependencies=self._support_dependencies(),
                active_stack=set(),
                completed=set(),
            )

        if state.unresolved or state.issues:
            classification = DerivedLineageClass.UNKNOWN
        elif state.has_reality and state.has_ai_cognition:
            classification = DerivedLineageClass.MIXED
        elif state.has_reality:
            classification = DerivedLineageClass.REALITY
        elif state.has_ai_cognition:
            classification = DerivedLineageClass.AI_COGNITION_ONLY
        elif state.has_maintenance:
            classification = DerivedLineageClass.MAINTENANCE_ONLY
        else:
            classification = DerivedLineageClass.UNKNOWN

        leaves = tuple(state.leaves[key] for key in sorted(state.leaves))
        unresolved = tuple(
            state.unresolved[key]
            for key in sorted(
                state.unresolved,
                key=lambda item: (item[0], -1 if item[1] is None else item[1]),
            )
        )
        return DerivedLineageView(
            classification=classification,
            leaf_refs=leaves,
            unresolved_refs=unresolved,
            issues=tuple(sorted(state.issues)),
            has_reality=state.has_reality,
            has_ai_cognition=state.has_ai_cognition,
            has_maintenance=state.has_maintenance,
        )

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
    ) -> CognitiveDerivationScheduleReceipt:
        summary, state_reason = self._current_eligible_summary(summary_ref)
        lineage = self.derive_lineage(summary_ref)
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
        recovery ledger.  No second scheduler database or cursor is required.
        """

        receipts: list[CognitiveDerivationScheduleReceipt] = []
        examined = 0
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
                ObjectRef(object_id=object_id, revision=revision)
            )
            if receipt.eligible:
                receipts.append(receipt)
        return CognitiveDerivationReconcileResult(
            examined=examined,
            scheduled=tuple(receipts),
        )
