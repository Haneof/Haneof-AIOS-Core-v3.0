"""Integration tests for C15 CognitionEvidencePolicy evidence closure.

Verifies:
1. Reality leaf closure is required for all Claim creation and revision.
2. Self-confirmation cycles (Claim -> Summary -> Claim, Claim -> Claim) are rejected.
3. Ordinary user turns, Periodic Review, Cognitive Derivation, and direct cognition
   writeback/revision services all enforce the exact same mechanical resolver.
"""

from datetime import datetime, timedelta, timezone

import pytest

from aios_core.ai_world import (
    AI_SELF_SUBJECT_ID,
    AIWorldClaimRequest,
    AIWorldCognitionService,
    AIWorldDomain,
)
from aios_core.contracts.enums import (
    ActionStatus,
    AttentionClass,
    MaintenanceClass,
    ObjectType,
    SourceClass,
    SummaryStatus,
    WakeSource,
    WakeState,
)
from aios_core.contracts.models import (
    Action,
    Claim,
    Dependency,
    EvidenceSet,
    Observation,
    Outcome,
    Summary,
    Wake,
)
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef, SourceRef
from aios_core.events.service import EventDimensionService, EventWriteRequest
from aios_core.contracts.time import TemporalExtent, TimePrecision
from aios_core.policy.evidence import (
    CognitionEvidencePolicy,
    DerivedLineageClass,
    EvidencePolicyResolver,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.review import (
    PeriodicReviewRequest,
    PeriodicReviewService,
)
from aios_core.revision.service import ClaimRevisionRequest, CognitionRevisionService
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService


NOW = datetime(2026, 9, 22, 10, 0, tzinfo=timezone.utc)


def _seed_observation(
    store: SQLiteWorldStore,
    *,
    object_id: str,
    source_class: SourceClass = SourceClass.USER,
    subject_id: str = "user_1",
    value: str = "seed user observation",
    offset_hours: int = 1,
) -> ObjectRef:
    obs = Observation(
        object_id=object_id,
        subject_id=subject_id,
        occurred=TemporalExtent.point(NOW - timedelta(hours=offset_hours)),
        learned_at=NOW - timedelta(hours=offset_hours),
        recorded_at=NOW - timedelta(hours=offset_hours),
        created_by="test:c15",
        source_kind="chat",
        modality="text",
        value=value,
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    store.commit(
        [obs],
        OperationRequest(
            operation_name="test.seed.observation",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed observation",
            idempotency_key=f"seed-obs-{object_id}",
            source_class=source_class,
        ),
    )
    return ObjectRef(object_id=object_id, revision=1)


def _seed_summary(
    store: SQLiteWorldStore,
    *,
    object_id: str,
    source_refs: tuple[ObjectRef, ...] = (),
    claim_refs: tuple[ObjectRef, ...] = (),
    subject_id: str = "user_1",
) -> ObjectRef:
    summary = Summary(
        object_id=object_id,
        subject_id=subject_id,
        occurred=TemporalExtent(
            start=NOW - timedelta(days=1),
            end=NOW,
            precision=TimePrecision.DAY,
        ),
        learned_at=NOW,
        recorded_at=NOW,
        source_refs=[
            SourceRef(object_id=r.object_id, revision=r.revision)
            for r in source_refs
        ],
        claim_refs=[
            ObjectRef(object_id=r.object_id, revision=r.revision)
            for r in claim_refs
        ],
        created_by="test:c15:summary",
        status=SummaryStatus.CURRENT,
        summary_time=TemporalExtent(
            start=NOW - timedelta(days=1),
            end=NOW,
            precision=TimePrecision.DAY,
        ),
        granularity="day",
        content="Summary content",
        source_world_revision=int(store.current_world_revision()),
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    store.commit(
        [summary],
        OperationRequest(
            operation_name="test.seed.summary",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed summary",
            idempotency_key=f"seed-summary-{object_id}",
            source_class=SourceClass.MAINTENANCE,
            maintenance_class=MaintenanceClass.SUMMARY_REBUILD,
        ),
    )
    return ObjectRef(object_id=object_id, revision=1)


def _seed_claim(
    store: SQLiteWorldStore,
    index: WorldSearchIndex,
    *,
    evidence_refs: tuple[ObjectRef, ...],
    content: str = "Initial claim content",
    subject_id: str = "user_1",
) -> ObjectRef:
    wb = CognitionWritebackService(store=store, index=index, subject_id=subject_id)
    receipt = wb.commit_claim(
        ClaimWriteRequest(
            content=content,
            evidence_refs=evidence_refs,
            confidence=0.85,
            dimension="dim:user_ai_interaction",
        ),
        learned_at=NOW,
    )
    return ObjectRef(object_id=receipt.claim_id, revision=1)


def test_evidence_policy_accepts_reality_observation(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs_ref = _seed_observation(store, object_id="obs_real_1")
    index = WorldSearchIndex(db, store=store)
    policy = CognitionEvidencePolicy(store=store, index=index)

    lineage = policy.validate([obs_ref], operation="test_obs")
    assert lineage.classification == DerivedLineageClass.REALITY
    assert obs_ref in lineage.grounding_leaf_refs
    assert not lineage.unresolved_refs
    assert not lineage.issues


def test_evidence_policy_rejects_direct_claim_evidence(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs_ref = _seed_observation(store, object_id="obs_real_1")
    index = WorldSearchIndex(db, store=store)
    claim_ref = _seed_claim(store, index, evidence_refs=(obs_ref,))
    policy = CognitionEvidencePolicy(store=store, index=index)

    # Claim -> Claim without independent reality leaf is rejected
    with pytest.raises(ValueError, match="leaf-grounded evidence closure rejected"):
        policy.validate([claim_ref], operation="direct_claim_evidence")


def test_evidence_policy_rejects_claim_summary_claim_cycle(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs_ref = _seed_observation(store, object_id="obs_real_1")
    index = WorldSearchIndex(db, store=store)
    claim_1 = _seed_claim(store, index, evidence_refs=(obs_ref,), content="Claim 1")
    # Summary references Claim 1 only (no reality observation)
    summary_ref = _seed_summary(store, object_id="sum_ungrounded", claim_refs=(claim_1,))
    policy = CognitionEvidencePolicy(store=store, index=index)

    # Claim 1 -> Summary -> Claim 2 cycle is rejected
    with pytest.raises(ValueError, match="leaf-grounded evidence closure rejected"):
        policy.validate([summary_ref], operation="claim_summary_claim_cycle")


def test_evidence_policy_accepts_observation_through_summary(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs_ref = _seed_observation(store, object_id="obs_real_1")
    # Summary references reality Observation
    summary_ref = _seed_summary(store, object_id="sum_grounded", source_refs=(obs_ref,))
    index = WorldSearchIndex(db, store=store)
    policy = CognitionEvidencePolicy(store=store, index=index)

    lineage = policy.validate([summary_ref], operation="grounded_summary")
    assert lineage.classification == DerivedLineageClass.REALITY
    assert obs_ref in lineage.grounding_leaf_refs


def test_evidence_policy_rejects_chained_summaries_without_reality(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    s1 = _seed_summary(store, object_id="sum_chain_1", source_refs=(), claim_refs=())
    s2 = _seed_summary(store, object_id="sum_chain_2", source_refs=(s1,))
    policy = CognitionEvidencePolicy(store=store, index=index)

    with pytest.raises(ValueError, match="leaf-grounded evidence closure rejected"):
        policy.validate([s2], operation="chained_ungrounded_summary")


def test_ordinary_turn_enforces_reality_grounding_and_blocks_cycles(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs_ref = _seed_observation(store, object_id="obs_turn_1", value="User prefers green tea")
    obs_new = _seed_observation(store, object_id="obs_turn_2", value="User confirmed black tea")
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    old_claim = _seed_claim(store, index, evidence_refs=(obs_ref,), content="User likes tea")
    ungrounded_summary = _seed_summary(store, object_id="sum_cycle", claim_refs=(old_claim,))

    def model_attempting_loop(snapshot):
        history_len = len(snapshot.capability_history)

        if history_len == 0:
            # 1. Attempt Claim -> Summary -> Claim self-confirmation loop
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_claim",
                        arguments={
                            "content": "Self confirmed claim",
                            "evidence_refs": [{"object_id": ungrounded_summary.object_id, "revision": 1}],
                            "confidence": 0.9,
                            "dimension": "dim:user_ai_interaction",
                        },
                    ),
                )
            )

        if history_len == 1:
            # Verify the self-confirmation loop was rejected
            first_call = snapshot.capability_history[0]
            assert first_call.ok is False
            assert first_call.error_code == "CAPABILITY_EXECUTION_ERROR"
            assert "leaf-grounded evidence closure rejected" in first_call.error_message

            # 2. Attempt Claim -> Claim directly
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_claim",
                        arguments={
                            "content": "Direct claim on claim",
                            "evidence_refs": [{"object_id": old_claim.object_id, "revision": 1}],
                            "confidence": 0.9,
                            "dimension": "dim:user_ai_interaction",
                        },
                    ),
                )
            )

        if history_len == 2:
            # Verify Claim -> Claim was rejected
            second_call = snapshot.capability_history[1]
            assert second_call.ok is False
            assert second_call.error_code == "CAPABILITY_EXECUTION_ERROR"
            assert "leaf-grounded evidence closure rejected" in second_call.error_message

            # 3. Legitimate Reality Observation -> Claim
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_claim",
                        arguments={
                            "content": "Grounded claim from reality",
                            "evidence_refs": [{"object_id": obs_new.object_id, "revision": 1}],
                            "confidence": 0.95,
                            "dimension": "dim:user_ai_interaction",
                        },
                    ),
                )
            )

        if history_len == 3:
            # Verify grounded Claim succeeded
            third_call = snapshot.capability_history[2]
            assert third_call.ok is True
            return ModelDirective(response="done")

        raise AssertionError(f"Unexpected round with history length {history_len}")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model_attempting_loop)
    result = runtime.run_turn(
        session_id="session_1",
        turn_index=1,
        user_input="Hello tea",
        current_topic=None,
        occurred_at=NOW + timedelta(seconds=1),
    )

    assert result.runtime.termination_reason == "responded"
    assert len(result.runtime.capability_history) == 3
    assert result.runtime.capability_history[0].ok is False
    assert result.runtime.capability_history[1].ok is False
    assert result.runtime.capability_history[2].ok is True


def test_ordinary_turn_claim_revision_requires_new_reality(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs_1 = _seed_observation(store, object_id="obs_pref_1", value="Prefers tea", offset_hours=10)
    obs_2 = _seed_observation(store, object_id="obs_pref_2", value="Switched to coffee", offset_hours=1)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    initial_claim = _seed_claim(store, index, evidence_refs=(obs_1,), content="User prefers tea")
    ungrounded_sum = _seed_summary(store, object_id="sum_ungrounded_rev", claim_refs=(initial_claim,))

    def model_revise(snapshot):
        history_len = len(snapshot.capability_history)

        if history_len == 0:
            # 1. Attempt revise with ungrounded summary
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="revise_claim",
                        arguments={
                            "target_ref": {"object_id": initial_claim.object_id, "revision": 1},
                            "reason": "unsupported revision",
                            "evidence_refs": [{"object_id": ungrounded_sum.object_id, "revision": 1}],
                            "replacement_content": "Revised without reality",
                        },
                    ),
                )
            )

        if history_len == 1:
            first_call = snapshot.capability_history[0]
            assert first_call.ok is False
            assert "leaf-grounded evidence closure rejected" in first_call.error_message

            # 2. Legitimate revise with new reality observation
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="revise_claim",
                        arguments={
                            "target_ref": {"object_id": initial_claim.object_id, "revision": 1},
                            "reason": "user explicitly switched to coffee",
                            "evidence_refs": [{"object_id": obs_2.object_id, "revision": 1}],
                            "replacement_content": "User prefers coffee now",
                        },
                    ),
                )
            )

        if history_len == 2:
            second_call = snapshot.capability_history[1]
            assert second_call.ok is True
            return ModelDirective(response="revised")

        raise AssertionError(f"Unexpected round with history length {history_len}")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model_revise)
    result = runtime.run_turn(
        session_id="session_rev",
        turn_index=1,
        user_input="I only drink coffee now",
        current_topic=None,
        occurred_at=NOW + timedelta(seconds=1),
    )
    assert result.runtime.termination_reason == "responded"
    assert result.runtime.capability_history[0].ok is False
    assert result.runtime.capability_history[1].ok is True
    assert store.get_payload(initial_claim.object_id)["content"] == "User prefers coffee now"


def test_periodic_review_enforces_evidence_policy_closure(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)

    # Seed real outcome for periodic review
    observation = Observation(
        object_id="obs_pr_msg",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=2)),
        learned_at=NOW - timedelta(hours=2),
        recorded_at=NOW - timedelta(hours=2),
        created_by="p15-test",
        source_kind="conversation",
        modality="text",
        value="send report",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    action = Action(
        object_id="action_pr_msg",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=1)),
        learned_at=NOW - timedelta(hours=1),
        recorded_at=NOW - timedelta(hours=1),
        created_by="p15-test",
        execution_id="exec-pr-msg",
        action_type="send_team_message",
        action_status=ActionStatus.COMPLETED,
        payload={"channel": "team"},
        expected_outcome="delivery accepted",
    )
    outcome = Outcome(
        object_id="outcome_pr_msg",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(minutes=30)),
        learned_at=NOW - timedelta(minutes=30),
        recorded_at=NOW - timedelta(minutes=30),
        created_by="p15-test",
        action_ref=ObjectRef(object_id=action.object_id, revision=1),
        outcome_state="completed",
        payload={"delivery": "accepted"},
        evidence_refs=([ObjectRef(object_id=observation.object_id, revision=1)]),
    )
    store.commit(
        [observation, action, outcome],
        OperationRequest(
            operation_name="test.seed.outcome",
            expected_world_revision=0,
            reason="seed outcome for periodic review",
            idempotency_key="seed-outcome-pr",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    old_claim = _seed_claim(store, index, evidence_refs=(ObjectRef(object_id=observation.object_id, revision=1),))
    cycle_summary = _seed_summary(store, object_id="sum_review_cycle", claim_refs=(old_claim,))

    def model_review(snapshot):
        history_len = len(snapshot.capability_history)

        if history_len == 0:
            # 1. Attempt self-confirming loop during periodic review
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_claim",
                        arguments={
                            "content": "Loop claim in periodic review",
                            "evidence_refs": [{"object_id": cycle_summary.object_id, "revision": 1}],
                            "confidence": 0.88,
                            "dimension": "dim:user_ai_interaction",
                        },
                    ),
                )
            )

        if history_len == 1:
            first_call = snapshot.capability_history[0]
            assert first_call.ok is False
            assert "leaf-grounded evidence closure rejected" in first_call.error_message

            # 2. Legitimate commit using reality anchor
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_claim",
                        arguments={
                            "content": "Real review claim",
                            "evidence_refs": [{"object_id": observation.object_id, "revision": 1}],
                            "confidence": 0.92,
                            "dimension": "dim:user_ai_interaction",
                        },
                    ),
                )
            )

        if history_len == 2:
            second_call = snapshot.capability_history[1]
            assert second_call.ok is True
            return ModelDirective(response="review complete")

        raise AssertionError(f"Unexpected round with history length {history_len}")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model_review,
        max_tool_rounds=5,
    )
    result = runtime.run_periodic_review(now=NOW + timedelta(seconds=1))
    assert result is not None
    assert len(result.runtime.capability_history) == 2
    assert result.runtime.capability_history[0].ok is False
    assert result.runtime.capability_history[1].ok is True


def test_direct_writeback_and_revision_services_enforce_policy(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs_1 = _seed_observation(store, object_id="obs_direct_1", value="Direct observation 1")
    obs_2 = _seed_observation(store, object_id="obs_direct_2", value="Direct observation 2")
    index = WorldSearchIndex(db, store=store)
    policy = CognitionEvidencePolicy(store=store, index=index)

    wb = CognitionWritebackService(store=store, index=index, evidence_policy=policy)
    rev = CognitionRevisionService(store=store, index=index, evidence_policy=policy)

    # 1. Valid commit with reality leaf
    receipt = wb.commit_claim(
        ClaimWriteRequest(
            content="Grounded direct claim",
            evidence_refs=(obs_1,),
            confidence=0.8,
            dimension="dim:user_ai_interaction",
        ),
        learned_at=NOW,
    )
    claim_ref = ObjectRef(object_id=receipt.claim_id, revision=1)

    # 2. Ungrounded summary created from claim
    ungrounded_sum = _seed_summary(store, object_id="sum_direct_cycle", claim_refs=(claim_ref,))

    # 3. Direct commit with ungrounded summary rejected
    with pytest.raises(ValueError, match="leaf-grounded evidence closure rejected"):
        wb.commit_claim(
            ClaimWriteRequest(
                content="Ungrounded direct write",
                evidence_refs=(ungrounded_sum,),
                confidence=0.8,
                dimension="dim:user_ai_interaction",
            ),
            learned_at=NOW,
        )

    # 4. Direct revision with ungrounded summary rejected
    with pytest.raises(ValueError, match="leaf-grounded evidence closure rejected"):
        rev.apply(
            ClaimRevisionRequest(
                target_ref=claim_ref,
                mode="revise",
                reason="attempt ungrounded revision",
                evidence_refs=(ungrounded_sum,),
                replacement_content="Revision without reality",
            ),
            changed_at=NOW,
        )

    # 5. Direct revision with valid reality observation accepted
    rev_receipt = rev.apply(
        ClaimRevisionRequest(
            target_ref=claim_ref,
            mode="revise",
            reason="valid reality revision",
            evidence_refs=(obs_2,),
            replacement_content="Revised with reality",
        ),
        changed_at=NOW,
    )
    assert rev_receipt.new_revision == 2

# ---------------------------------------------------------------------------
# C15-RCC-EVIDENCE-POLICY-001 — legal grounding paths per evidence object type.
#
# These positive controls exist to prove the unified policy is not over-tight:
# every one of these is an ordinary, legal cognition opportunity that existed
# before the policy layer and must keep forming afterwards.
# ---------------------------------------------------------------------------


def _seed_action_outcome(
    store: SQLiteWorldStore,
    *,
    obs_ref: ObjectRef,
    action_id: str = "act_legal",
    outcome_id: str = "out_legal",
) -> tuple[ObjectRef, ObjectRef]:
    """Seed a real platform Action + Outcome supported by a real user Observation."""
    action = Action(
        object_id=action_id,
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=2)),
        learned_at=NOW - timedelta(hours=2),
        recorded_at=NOW - timedelta(hours=2),
        created_by="test:c15",
        execution_id=f"exec-{action_id}",
        action_type="send_report",
        action_status=ActionStatus.COMPLETED,
        payload={"channel": "team"},
        expected_outcome="delivery accepted",
    )
    outcome = Outcome(
        object_id=outcome_id,
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(minutes=30)),
        learned_at=NOW - timedelta(minutes=30),
        recorded_at=NOW - timedelta(minutes=30),
        created_by="test:c15",
        action_ref=ObjectRef(object_id=action_id, revision=1),
        outcome_state="completed",
        payload={"delivery": "accepted"},
        evidence_refs=[obs_ref],
    )
    store.commit(
        [action, outcome],
        OperationRequest(
            operation_name="test.seed.action_outcome",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed real platform action/outcome",
            idempotency_key=f"seed-ao-{action_id}",
            source_class=SourceClass.PLATFORM,
        ),
    )
    return (
        ObjectRef(object_id=action_id, revision=1),
        ObjectRef(object_id=outcome_id, revision=1),
    )


def test_observation_is_a_legal_grounding_path(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs_ref = _seed_observation(store, object_id="obs_legal_plain")
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    lineage = CognitionEvidencePolicy(store=store, index=index).validate(
        [obs_ref],
        operation="legal_observation",
    )
    assert lineage.classification is DerivedLineageClass.REALITY
    assert lineage.grounding_leaf_refs == (obs_ref,)

    receipt = CognitionWritebackService(store=store, index=index).commit_claim(
        ClaimWriteRequest(
            content="Observation-grounded claim",
            evidence_refs=(obs_ref,),
            confidence=0.8,
            dimension="dim:user_ai_interaction",
        ),
        learned_at=NOW,
    )
    assert store.get_payload(receipt.claim_id)["revision"] == 1


def test_action_is_a_legal_grounding_path(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs_ref = _seed_observation(store, object_id="obs_legal_action")
    action_ref, _ = _seed_action_outcome(
        store,
        obs_ref=obs_ref,
        action_id="act_legal_a",
        outcome_id="out_legal_a",
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    lineage = CognitionEvidencePolicy(store=store, index=index).validate(
        [action_ref],
        operation="legal_action",
    )
    assert lineage.classification is DerivedLineageClass.REALITY
    assert lineage.grounding_leaf_refs

    receipt = CognitionWritebackService(store=store, index=index).commit_claim(
        ClaimWriteRequest(
            content="Action-grounded claim",
            evidence_refs=(action_ref,),
            confidence=0.8,
            dimension="dim:user_ai_interaction",
        ),
        learned_at=NOW,
    )
    assert store.get_payload(receipt.claim_id)["revision"] == 1


def test_outcome_is_a_legal_grounding_path(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs_ref = _seed_observation(store, object_id="obs_legal_outcome")
    _, outcome_ref = _seed_action_outcome(
        store,
        obs_ref=obs_ref,
        action_id="act_legal_o",
        outcome_id="out_legal_o",
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    lineage = CognitionEvidencePolicy(store=store, index=index).validate(
        [outcome_ref],
        operation="legal_outcome",
    )
    # A PLATFORM-committed Outcome is itself a qualifying reality leaf.
    assert lineage.classification is DerivedLineageClass.REALITY
    assert outcome_ref in lineage.grounding_leaf_refs
    assert lineage.has_ai_cognition is False

    receipt = CognitionWritebackService(store=store, index=index).commit_claim(
        ClaimWriteRequest(
            content="Outcome-grounded strategy claim",
            evidence_refs=(outcome_ref,),
            confidence=0.8,
            dimension="dim:user_ai_interaction",
        ),
        learned_at=NOW,
    )
    assert store.get_payload(receipt.claim_id)["revision"] == 1


def test_event_anchor_is_a_legal_case_grounding_container(tmp_path):
    """EventAnchor is AI-authored but carries pinned reality evidence.

    Semantic decision C15-RCC-EVIDENCE-POLICY-001: EventAnchor is a legal case
    grounding container. It is never itself a grounding leaf, but it must not block
    the path to the real Observation underneath it.
    """
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs_ref = _seed_observation(
        store,
        object_id="obs_legal_event",
        value="user said he moved to Berlin",
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    events = EventDimensionService(store=store, index=index)
    event_receipt = events.form_event(
        EventWriteRequest(
            title="Moved to Berlin",
            interpretation="user relocated",
            dimension="dim:user_ai_interaction",
            event_time=TemporalExtent.point(NOW - timedelta(minutes=30)),
            evidence_refs=(obs_ref,),
            confidence=0.9,
        ),
        learned_at=NOW,
    )
    event_ref = ObjectRef(object_id=event_receipt.event_id, revision=1)

    lineage = CognitionEvidencePolicy(store=store, index=index).validate(
        [event_ref],
        operation="legal_event",
    )
    # The Event itself is AI-authored, so the lineage is MIXED, not pure REALITY.
    assert lineage.classification is DerivedLineageClass.MIXED
    assert lineage.has_ai_cognition is True
    # The real Observation underneath still closes the proof.
    assert obs_ref in lineage.grounding_leaf_refs
    # The Event is never itself a grounding leaf.
    assert event_ref not in lineage.grounding_leaf_refs

    receipt = CognitionWritebackService(store=store, index=index).commit_claim(
        ClaimWriteRequest(
            content="User lives in Berlin",
            evidence_refs=(event_ref,),
            confidence=0.8,
            dimension="dim:user_ai_interaction",
        ),
        learned_at=NOW,
    )
    assert store.get_payload(receipt.claim_id)["revision"] == 1


def test_event_anchor_over_ai_only_lineage_still_fails_closed(tmp_path):
    """Case-container status must not become a laundering route.

    An Event whose own evidence is an ungrounded Claim/Summary cannot manufacture
    grounding. Only real leaves underneath the Event may close the proof.
    """
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs_ref = _seed_observation(store, object_id="obs_event_launder")
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    claim_ref = _seed_claim(store, index, evidence_refs=(obs_ref,))
    ungrounded_summary = _seed_summary(
        store,
        object_id="sum_event_launder",
        claim_refs=(claim_ref,),
    )

    events = EventDimensionService(store=store, index=index)
    event_receipt = events.form_event(
        EventWriteRequest(
            title="Laundered event",
            interpretation="event built only on AI cognition",
            dimension="dim:user_ai_interaction",
            event_time=TemporalExtent.point(NOW - timedelta(minutes=10)),
            evidence_refs=(ungrounded_summary,),
            confidence=0.9,
        ),
        learned_at=NOW,
    )
    event_ref = ObjectRef(object_id=event_receipt.event_id, revision=1)

    policy = CognitionEvidencePolicy(store=store, index=index)
    with pytest.raises(ValueError, match="leaf-grounded evidence closure rejected"):
        policy.validate([event_ref], operation="laundered_event")


def test_event_grounded_cognition_forms_on_an_ordinary_user_turn(tmp_path):
    """End-to-end control for the ordinary-turn entrypoint, not just the policy."""
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs_ref = _seed_observation(store, object_id="obs_turn_event")
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    events = EventDimensionService(store=store, index=index)
    event_receipt = events.form_event(
        EventWriteRequest(
            title="Turn event",
            interpretation="event formed from real user observation",
            dimension="dim:user_ai_interaction",
            event_time=TemporalExtent.point(NOW - timedelta(minutes=5)),
            evidence_refs=(obs_ref,),
            confidence=0.9,
        ),
        learned_at=NOW,
    )
    event_arg = {"object_id": event_receipt.event_id, "revision": 1}

    def model(snapshot):
        if len(snapshot.capability_history) == 0:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_claim",
                        arguments={
                            "content": "Event-grounded claim on ordinary turn",
                            "evidence_refs": [event_arg],
                            "confidence": 0.8,
                            "dimension": "dim:user_ai_interaction",
                        },
                    ),
                )
            )
        assert snapshot.capability_history[0].ok is True, (
            snapshot.capability_history[0].error_message
        )
        return ModelDirective(response="done")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_turn(
        session_id="session_event",
        turn_index=1,
        user_input="hello",
        current_topic=None,
        occurred_at=NOW + timedelta(seconds=1),
    )
    assert result.runtime.capability_history[0].ok is True


def test_services_enforce_policy_without_explicit_injection(tmp_path):
    """Structural unification: no construction path can bypass the policy.

    Constructing the cognition services directly, with no evidence_policy argument,
    must still enforce leaf-grounded closure.
    """
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    obs_ref = _seed_observation(store, object_id="obs_default_policy")
    index = WorldSearchIndex(db, store=store)
    index.rebuild()

    writeback = CognitionWritebackService(store=store, index=index)
    revision = CognitionRevisionService(store=store, index=index)
    ai_world = AIWorldCognitionService(store=store, index=index)

    assert writeback.evidence_policy is not None
    assert revision.evidence_policy is not None
    assert ai_world.evidence_policy is not None

    claim_ref = _seed_claim(store, index, evidence_refs=(obs_ref,))
    ungrounded_summary = _seed_summary(
        store,
        object_id="sum_default_policy",
        claim_refs=(claim_ref,),
    )

    with pytest.raises(ValueError, match="leaf-grounded evidence closure rejected"):
        writeback.commit_claim(
            ClaimWriteRequest(
                content="bypass attempt",
                evidence_refs=(ungrounded_summary,),
                confidence=0.8,
                dimension="dim:user_ai_interaction",
            ),
            learned_at=NOW,
        )

    with pytest.raises(ValueError, match="leaf-grounded evidence closure rejected"):
        revision.apply(
            ClaimRevisionRequest(
                target_ref=claim_ref,
                mode="revise",
                reason="bypass attempt",
                evidence_refs=(ungrounded_summary,),
                replacement_content="revised without reality",
            ),
            changed_at=NOW,
        )

    with pytest.raises(ValueError, match="leaf-grounded evidence closure rejected"):
        ai_world.commit(
            AIWorldClaimRequest(
                domain=AIWorldDomain.USER_UNDERSTANDING,
                statement="bypass attempt",
                evidence_refs=(ungrounded_summary,),
                confidence=0.8,
            ),
            learned_at=NOW,
        )
