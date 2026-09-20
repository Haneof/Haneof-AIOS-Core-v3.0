from datetime import datetime, timedelta, timezone

import pytest

from aios_core.ai_world import AIWorldDomain
from aios_core.contracts.enums import ObjectType
from aios_core.contracts.refs import ObjectRef
from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.review import (
    OperationExperienceRequest,
    OperationExperienceService,
    PeriodicReviewPolicy,
    PeriodicReviewService,
)
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService


NOW = datetime(2026, 9, 20, 17, 0, tzinfo=timezone.utc)


def _world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def _user_fact(
    store,
    *,
    session_id: str,
    turn_index: int,
    text: str,
    at: datetime,
):
    ingest = ConversationIngestor(store)
    return ingest.commit_user_input(
        session_id=session_id,
        turn_index=turn_index,
        user_text=text,
        occurred_at=at,
    )


def test_noop_review_checkpoints_world_and_maintenance_does_not_retrigger(tmp_path):
    store, index = _world(tmp_path)
    fact = _user_fact(
        store,
        session_id="review",
        turn_index=1,
        text="Please keep deployment notes concise.",
        at=NOW,
    )
    service = PeriodicReviewService(store=store, index=index)

    prepared = service.prepare_if_due(
        reviewed_at=NOW + timedelta(hours=1),
        policy=PeriodicReviewPolicy(minimum_interval_seconds=86_400),
    )
    assert prepared is not None
    assert prepared.from_world_revision_exclusive == 0
    assert prepared.reviewed_through_world_revision == fact.world_revision
    assert any(
        item.object_ref.object_id == fact.observation_id
        for item in prepared.items
    )

    checkpoint = service.commit_checkpoint(
        prepared,
        review_note="No durable cognition change is warranted from this evidence yet.",
        completed_at=NOW + timedelta(hours=1),
    )
    payload = store.get_payload(
        checkpoint.object_id,
        revision=checkpoint.revision,
    )

    assert payload["object_type"] == ObjectType.SUMMARY.value
    assert payload["metadata"]["summary_kind"] == "periodic_review_checkpoint"
    assert payload["metadata"]["not_cognition_truth"] is True
    assert (
        payload["metadata"]["reviewed_through_world_revision"]
        == fact.world_revision
    )
    assert store.commit_source_class(checkpoint.world_revision) == "maintenance"

    # The checkpoint itself is maintenance and cannot wake another review.
    restarted = PeriodicReviewService(store=store, index=index)
    assert (
        restarted.prepare_if_due(
            reviewed_at=NOW + timedelta(days=3),
            policy=PeriodicReviewPolicy(minimum_interval_seconds=0),
        )
        is None
    )


def test_review_interval_blocks_new_world_changes_until_due(tmp_path):
    store, index = _world(tmp_path)
    _user_fact(
        store,
        session_id="review",
        turn_index=1,
        text="first fact",
        at=NOW,
    )
    service = PeriodicReviewService(store=store, index=index)
    first = service.prepare_if_due(
        reviewed_at=NOW + timedelta(hours=1),
        policy=PeriodicReviewPolicy(minimum_interval_seconds=86_400),
    )
    assert first is not None
    service.commit_checkpoint(
        first,
        review_note="first review complete",
        completed_at=NOW + timedelta(hours=1),
    )

    second_fact = _user_fact(
        store,
        session_id="review",
        turn_index=2,
        text="new fact after checkpoint",
        at=NOW + timedelta(hours=2),
    )

    assert (
        service.prepare_if_due(
            reviewed_at=NOW + timedelta(hours=2),
            policy=PeriodicReviewPolicy(minimum_interval_seconds=86_400),
        )
        is None
    )

    due = service.prepare_if_due(
        reviewed_at=NOW + timedelta(days=2),
        policy=PeriodicReviewPolicy(minimum_interval_seconds=86_400),
    )
    assert due is not None
    assert due.from_world_revision_exclusive == first.reviewed_through_world_revision
    assert due.reviewed_through_world_revision == second_fact.world_revision


def test_operation_experience_requires_real_result_evidence_and_is_not_strategy(tmp_path):
    store, index = _world(tmp_path)
    fact = _user_fact(
        store,
        session_id="feedback",
        turn_index=1,
        text="The direct checklist worked and saved me time.",
        at=NOW,
    )
    fact_ref = ObjectRef(object_id=fact.observation_id, revision=1)
    service = OperationExperienceService(store=store, index=index)

    with pytest.raises(ValueError, match="at least one real result"):
        OperationExperienceRequest(
            problem_type="deployment_help",
            method_path=("give_checklist",),
            result_summary="worked",
        )

    valid = OperationExperienceRequest(
        problem_type="deployment_help",
        method_path=("identify blockers", "give_checklist"),
        result_summary="The concise checklist was explicitly reported as useful.",
        applicability={"scope": "deployment_help"},
        cost={"steps": 2.0},
        positive_case_refs=(fact_ref,),
    )
    receipt = service.commit(valid, learned_at=NOW + timedelta(hours=1))
    payload = store.get_payload(receipt.object_id)

    assert payload["object_type"] == ObjectType.OPERATION_EXPERIENCE.value
    assert payload["experience_state"] == "candidate"
    assert payload["metadata"]["auto_promoted_to_strategy"] is False
    assert payload["positive_case_refs"] == [
        {"object_id": fact.observation_id, "revision": 1}
    ]

    replay = service.commit(valid, learned_at=NOW + timedelta(days=1))
    assert replay.object_id == receipt.object_id
    assert replay.reused_existing is True

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda snapshot: ModelDirective(response="unused"),
    )
    assert runtime.ai_world.current(domains=[AIWorldDomain.STRATEGY]) == ()

    claim = CognitionWritebackService(
        store=store,
        index=index,
    ).commit_claim(
        ClaimWriteRequest(
            content="A hypothesis, not a real result.",
            evidence_refs=(fact_ref,),
            confidence=0.6,
            dimension="dim:test_hypothesis",
        ),
        learned_at=NOW + timedelta(hours=2),
    )
    with pytest.raises(ValueError, match="real result evidence"):
        service.commit(
            OperationExperienceRequest(
                problem_type="invalid_lesson",
                method_path=("guess",),
                result_summary="should not be accepted",
                positive_case_refs=(
                    ObjectRef(object_id=claim.claim_id, revision=1),
                ),
            ),
            learned_at=NOW + timedelta(hours=3),
        )


def test_periodic_review_model_can_form_experience_then_independent_strategy_claim(tmp_path):
    store, index = _world(tmp_path)
    feedback = _user_fact(
        store,
        session_id="feedback",
        turn_index=1,
        text="The direct checklist worked and saved me time.",
        at=NOW,
    )

    def model(snapshot):
        assert snapshot.wake_reason == "periodic_review"
        history = snapshot.capability_history
        if not history:
            items = snapshot.cockpit["periodic_review"]["items"]
            feedback_item = next(
                item
                for item in items
                if item["object_ref"]["object_id"] == feedback.observation_id
            )
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_operation_experience",
                        arguments={
                            "problem_type": "deployment_help",
                            "method_path": ["identify blockers", "give checklist"],
                            "result_summary": (
                                "The user explicitly reported the direct checklist "
                                "saved time."
                            ),
                            "applicability": {"scope": "deployment_help"},
                            "positive_case_refs": [feedback_item["object_ref"]],
                        },
                    ),
                )
            )
        if len(history) == 1:
            experience_ref = history[-1].data["object_ref"]
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_ai_world_claim",
                        arguments={
                            "domain": "strategy",
                            "statement": (
                                "For this user's deployment-help situations, a direct "
                                "step-by-step checklist may be more effective than a "
                                "long conceptual preamble."
                            ),
                            "evidence_refs": [experience_ref],
                            "confidence": 0.72,
                            "scope_key": "deployment_help",
                            "tags": ["review_derived"],
                        },
                    ),
                )
            )
        return ModelDirective(
            response=(
                "Reviewed the explicit outcome, recorded one candidate operational "
                "experience, and formed a separate evidence-grounded strategy claim."
            )
        )

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
        max_tool_rounds=4,
    )
    result = runtime.run_periodic_review(
        reviewed_at=NOW + timedelta(hours=2),
        policy=PeriodicReviewPolicy(minimum_interval_seconds=0),
    )

    assert result is not None
    assert [item.name for item in result.runtime.capability_history] == [
        "commit_operation_experience",
        "commit_ai_world_claim",
    ]

    experiences = store.list_payloads(
        object_type=ObjectType.OPERATION_EXPERIENCE
    )
    assert len(experiences) == 1
    experience_ref = {
        "object_id": experiences[0]["object_id"],
        "revision": experiences[0]["revision"],
    }

    strategies = runtime.ai_world.current(
        domains=[AIWorldDomain.STRATEGY],
        scope_key="deployment_help",
    )
    assert len(strategies) == 1
    strategy_payload = store.get_payload(strategies[0].object_id)
    evidence_set_ref = strategy_payload["support_evidence_set_refs"][0]
    evidence_set = store.get_payload(
        evidence_set_ref["object_id"],
        revision=evidence_set_ref["revision"],
    )
    assert experience_ref in evidence_set["member_refs"]

    checkpoint = store.get_payload(
        result.checkpoint.object_id,
        revision=result.checkpoint.revision,
    )
    assert checkpoint["metadata"]["review_checkpoint_only"] is True

    # Review-generated AI cognition is triggerable, but cannot recursively review
    # itself inside the configured interval.
    assert (
        runtime.run_periodic_review(
            reviewed_at=NOW + timedelta(hours=3),
            policy=PeriodicReviewPolicy(minimum_interval_seconds=86_400),
        )
        is None
    )


def test_periodic_review_uses_existing_forward_revision_path(tmp_path):
    store, index = _world(tmp_path)
    first = _user_fact(
        store,
        session_id="preference",
        turn_index=1,
        text="Daily reminders are useful.",
        at=NOW,
    )
    first_ref = ObjectRef(object_id=first.observation_id, revision=1)
    writer = CognitionWritebackService(store=store, index=index)
    old_claim = writer.commit_claim(
        ClaimWriteRequest(
            content="The user currently prefers daily reminders.",
            evidence_refs=(first_ref,),
            confidence=0.8,
            dimension="dim:preference",
        ),
        learned_at=NOW + timedelta(minutes=5),
    )
    new_fact = _user_fact(
        store,
        session_id="preference",
        turn_index=2,
        text="Stop the daily reminders; weekly is enough.",
        at=NOW + timedelta(hours=1),
    )
    new_ref = {"object_id": new_fact.observation_id, "revision": 1}

    def model(snapshot):
        if not snapshot.capability_history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="revise_claim",
                        arguments={
                            "target_ref": {
                                "object_id": old_claim.claim_id,
                                "revision": 1,
                            },
                            "reason": "The user explicitly changed the reminder preference.",
                            "evidence_refs": [new_ref],
                            "replacement_content": (
                                "The user now prefers weekly reminders rather than daily."
                            ),
                            "confidence": 0.95,
                        },
                    ),
                )
            )
        return ModelDirective(response="Updated the stale preference using new evidence.")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    result = runtime.run_periodic_review(
        reviewed_at=NOW + timedelta(hours=2),
        policy=PeriodicReviewPolicy(minimum_interval_seconds=0),
    )

    assert result is not None
    assert [item.name for item in result.runtime.capability_history] == [
        "revise_claim"
    ]
    assert (
        store.get_payload(old_claim.claim_id, revision=1)["content"]
        == "The user currently prefers daily reminders."
    )
    current = store.get_payload(old_claim.claim_id)
    assert current["revision"] == 2
    assert (
        current["content"]
        == "The user now prefers weekly reminders rather than daily."
    )
    assert current["metadata"]["revision_mode"] == "revise"


def test_periodic_review_may_make_no_cognition_change(tmp_path):
    store, index = _world(tmp_path)
    _user_fact(
        store,
        session_id="neutral",
        turn_index=1,
        text="The weather changed this afternoon.",
        at=NOW,
    )

    def model(snapshot):
        assert snapshot.wake_reason == "periodic_review"
        return ModelDirective(
            response=(
                "Reviewed the new fact. There is not enough evidence for any durable "
                "cognition or strategy change."
            )
        )

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    result = runtime.run_periodic_review(
        reviewed_at=NOW + timedelta(hours=1),
        policy=PeriodicReviewPolicy(minimum_interval_seconds=0),
    )

    assert result is not None
    assert result.runtime.capability_history == ()
    assert store.list_payloads(object_type=ObjectType.OPERATION_EXPERIENCE) == []
    assert store.list_payloads(object_type=ObjectType.CLAIM) == []
    assert (
        store.get_payload(
            result.checkpoint.object_id,
            revision=result.checkpoint.revision,
        )["content"]
        .startswith("Reviewed the new fact.")
    )
