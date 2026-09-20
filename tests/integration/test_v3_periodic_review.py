from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import ActionStatus, ObjectType, SourceClass, WakeState
from aios_core.contracts.models import Action, Observation, Outcome, Wake
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.review import (
    OperationExperienceRequest,
    PeriodicReviewService,
    ReviewSchedulePolicy,
)
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.writeback.cognition import ClaimWriteRequest, CognitionWritebackService


NOW = datetime(2026, 9, 20, 16, 30, tzinfo=timezone.utc)


def _seed_real_outcome(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    observation = Observation(
        object_id="obs_user_requested_team_message",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=2)),
        learned_at=NOW - timedelta(hours=2),
        recorded_at=NOW - timedelta(hours=2),
        created_by="p15-test",
        source_kind="conversation",
        modality="text",
        value="把确认后的周报发给团队。",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    action = Action(
        object_id="action_team_message_p15",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=1)),
        learned_at=NOW - timedelta(hours=1),
        recorded_at=NOW - timedelta(hours=1),
        created_by="p15-test",
        execution_id="exec-team-message-p15",
        action_type="send_team_message",
        action_status=ActionStatus.COMPLETED,
        payload={"channel": "team", "document": "weekly-report"},
        expected_outcome="团队频道收到确认后的项目周报",
    )
    outcome = Outcome(
        object_id="outcome_team_message_p15",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(minutes=30)),
        learned_at=NOW - timedelta(minutes=30),
        recorded_at=NOW - timedelta(minutes=30),
        created_by="p15-test",
        action_ref=ObjectRef(object_id=action.object_id, revision=1),
        outcome_state="completed",
        payload={"provider_message_id": "msg-15", "delivery": "accepted"},
        evidence_refs=(
            [ObjectRef(object_id=observation.object_id, revision=1)]
        ),
    )
    store.commit(
        [observation, action, outcome],
        OperationRequest(
            operation_name="test.seed.p15.real_outcome",
            expected_world_revision=0,
            reason="seed real world result for periodic review",
            idempotency_key="seed-p15-real-outcome",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index, observation, action, outcome


def test_scheduler_only_creates_review_wake_and_never_semantic_growth_claim(tmp_path):
    store, index, _, _, outcome = _seed_real_outcome(tmp_path)
    service = PeriodicReviewService(store=store, index=index)

    request = service.prepare_due_review(now=NOW)

    assert request is not None
    assert any(
        anchor.object_ref.object_id == outcome.object_id
        for anchor in request.anchors
    )
    payloads = store.list_payloads()
    assert any(item["object_type"] == "wake" for item in payloads)
    assert not any(item["object_type"] == "claim" for item in payloads)
    assert not any(
        item["object_type"] == "operation_experience"
        for item in payloads
    )


def test_periodic_review_uses_same_resident_runtime_and_writes_grounded_growth(tmp_path):
    store, index, _, _, outcome = _seed_real_outcome(tmp_path)
    model_calls = 0

    def model(snapshot):
        nonlocal model_calls
        model_calls += 1
        assert snapshot.wake_reason == "periodic_review"
        review = snapshot.cockpit["task_context"]["periodic_review"]
        assert review["anchor_count"] >= 1
        # Full anchor payloads are not shoved into the fixed cockpit budget.
        assert "anchors" not in review

        history = snapshot.capability_history
        if not history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="read_periodic_review_anchors",
                        arguments={"offset": 0, "limit": 20},
                    ),
                )
            )

        if len(history) == 1:
            anchors = history[-1]
            assert anchors.ok is True
            outcome_anchor = next(
                item
                for item in anchors.data
                if item["object_ref"]["object_id"] == outcome.object_id
            )
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_operation_experience",
                        arguments={
                            "problem_type": "发送团队消息",
                            "method_path": [
                                "形成Action提案",
                                "经过独立授权",
                                "平台执行并等待Outcome",
                            ],
                            "result_summary": "该次发送路径获得真实completed Outcome。",
                            "positive_case_refs": [
                                outcome_anchor["object_ref"]
                            ],
                            "applicability": {
                                "requires_real_outcome": True
                            },
                            "cost": {"tool_rounds": 1.0},
                        },
                    ),
                )
            )

        if len(history) == 2:
            experience = history[-1]
            assert experience.ok is True
            exp_ref = {
                "object_id": experience.data["experience_id"],
                "revision": experience.data["revision"],
            }
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="commit_ai_world_claim",
                        arguments={
                            "domain": "calibration",
                            "statement": (
                                "当外部发送动作经过独立授权并收到真实Outcome后，"
                                "再把执行路径视为已验证经验。"
                            ),
                            "evidence_refs": [exp_ref],
                            "confidence": 0.9,
                            "scope_key": "external_action.outcome_calibration",
                            "tags": ["periodic_review"],
                        },
                    ),
                )
            )

        assert history[-1].ok is True
        return ModelDirective(response="周期复盘完成。")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
        max_tool_rounds=5,
    )
    before_observations = len(
        store.list_payloads(object_type=ObjectType.OBSERVATION)
    )
    result = runtime.run_periodic_review(now=NOW)

    assert result is not None
    assert result.runtime.response == "周期复盘完成。"
    assert [
        item.name for item in result.runtime.capability_history
    ] == [
        "read_periodic_review_anchors",
        "commit_operation_experience",
        "commit_ai_world_claim",
    ]
    assert result.wake.state == "completed"
    assert result.wake.revision == 3
    assert model_calls == 4

    # A review wake is not fabricated into the user conversation dimension.
    assert len(store.list_payloads(object_type=ObjectType.OBSERVATION)) == before_observations

    experiences = store.list_payloads(
        object_type=ObjectType.OPERATION_EXPERIENCE
    )
    assert len(experiences) == 1
    assert experiences[0]["positive_case_refs"] == [
        {"object_id": outcome.object_id, "revision": 1}
    ]

    calibration_claims = [
        item
        for item in store.list_payloads(object_type=ObjectType.CLAIM)
        if (item.get("metadata") or {}).get("ai_domain") == "calibration"
    ]
    assert len(calibration_claims) == 1

    page = index.recall_candidates(
        "发送路径",
        object_types=["operation_experience"],
    )
    assert experiences[0]["object_id"] in {
        hit.object_id for hit in page.hits
    }


def test_completed_review_does_not_immediately_or_self_trigger_again(tmp_path):
    store, index, _, _, _ = _seed_real_outcome(tmp_path)
    model_calls = 0

    def model(snapshot):
        nonlocal model_calls
        model_calls += 1
        return ModelDirective(response="检查完成，无需形成新的长期认知。")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    first = runtime.run_periodic_review(now=NOW)
    assert first is not None
    assert model_calls == 1

    assert runtime.run_periodic_review(
        now=NOW + timedelta(hours=1)
    ) is None
    assert model_calls == 1

    # After the interval there are no new external/reality anchors. The previous
    # review's own completion boundary must not mechanically trigger another model run.
    assert runtime.run_periodic_review(
        now=NOW + timedelta(hours=25)
    ) is None
    assert model_calls == 1

    review_wakes = [
        Wake.model_validate(item)
        for item in store.list_payloads(object_type=ObjectType.WAKE)
        if (item.get("metadata") or {}).get("review_kind")
    ]
    assert any(wake.wake_state is WakeState.SUPPRESSED for wake in review_wakes)


def test_running_review_is_resumable_after_process_restart(tmp_path):
    store, index, _, _, _ = _seed_real_outcome(tmp_path)
    scheduler = PeriodicReviewService(store=store, index=index)

    pending = scheduler.prepare_due_review(now=NOW)
    assert pending is not None
    running = scheduler.begin_review(pending, started_at=NOW)
    assert running.wake_ref.revision == 2
    assert store.get_payload(running.wake_ref.object_id)["wake_state"] == "running"

    calls = 0

    def model(snapshot):
        nonlocal calls
        calls += 1
        assert snapshot.wake_reason == "periodic_review"
        return ModelDirective(response="恢复未完成复盘并结束。")

    restarted = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    result = restarted.run_periodic_review(
        now=NOW + timedelta(minutes=5),
        policy=ReviewSchedulePolicy(interval_hours=24),
    )

    assert result is not None
    assert calls == 1
    assert result.request.wake_ref.revision == 2
    assert result.wake.revision == 3
    assert result.wake.state == "completed"


def test_operation_experience_requires_pinned_real_case_refs():
    with pytest.raises(ValueError, match="at least one real case ref"):
        OperationExperienceRequest(
            problem_type="发送团队消息",
            method_path=("形成Action", "等待Outcome"),
            result_summary="不能没有真实案例就宣称经验成立。",
        )

    with pytest.raises(ValueError, match="pin exact revisions"):
        OperationExperienceRequest(
            problem_type="发送团队消息",
            method_path=("形成Action", "等待Outcome"),
            result_summary="浮动引用不能作为长期经验依据。",
            positive_case_refs=(
                ObjectRef(object_id="outcome-x"),
            ),
        )


def test_periodic_review_can_revise_old_cognition_from_new_world_evidence(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    old_fact = Observation(
        object_id="obs_old_drink_p15",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=4)),
        learned_at=NOW - timedelta(hours=4),
        recorded_at=NOW - timedelta(hours=4),
        created_by="p15-revision-test",
        source_kind="conversation",
        modality="text",
        value="我现在每天喝茶。",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    correction = Observation(
        object_id="obs_new_drink_p15",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(minutes=30)),
        learned_at=NOW - timedelta(minutes=30),
        recorded_at=NOW - timedelta(minutes=30),
        created_by="p15-revision-test",
        source_kind="conversation",
        modality="text",
        value="我已经不每天喝茶了，现在每天喝咖啡。",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    store.commit(
        [old_fact, correction],
        OperationRequest(
            operation_name="test.seed.p15.revision",
            expected_world_revision=0,
            reason="seed old cognition and new correcting evidence",
            idempotency_key="seed-p15-revision",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    writeback = CognitionWritebackService(store=store, index=index)
    old_claim = writeback.commit_claim(
        ClaimWriteRequest(
            content="用户当前每天喝茶。",
            evidence_refs=(
                ObjectRef(object_id=old_fact.object_id, revision=1),
            ),
            confidence=0.8,
            dimension="dim:ai_user_understanding",
        ),
        learned_at=NOW - timedelta(hours=3),
    )

    def model(snapshot):
        history = snapshot.capability_history
        if not history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="read_periodic_review_anchors",
                        arguments={"offset": 0, "limit": 20},
                    ),
                )
            )
        if len(history) == 1:
            anchors = history[-1].data
            claim_anchor = next(
                item
                for item in anchors
                if item["object_ref"]["object_id"] == old_claim.claim_id
            )
            correction_anchor = next(
                item
                for item in anchors
                if item["object_ref"]["object_id"] == correction.object_id
            )
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="revise_claim",
                        arguments={
                            "target_ref": claim_anchor["object_ref"],
                            "reason": "用户提供了更新后的当前饮品事实。",
                            "evidence_refs": [correction_anchor["object_ref"]],
                            "replacement_content": "用户当前每天喝咖啡。",
                            "confidence": 0.95,
                        },
                    ),
                )
            )
        assert history[-1].ok is True
        return ModelDirective(response="已根据新证据修正旧认知。")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
        max_tool_rounds=4,
    )
    result = runtime.run_periodic_review(
        now=NOW,
        policy=ReviewSchedulePolicy(
            lookback_hours=12,
            interval_hours=24,
        ),
    )

    assert result is not None
    assert [
        item.name for item in result.runtime.capability_history
    ] == ["read_periodic_review_anchors", "revise_claim"]
    assert store.get_payload(old_claim.claim_id, revision=1)["content"] == "用户当前每天喝茶。"
    latest = store.get_payload(old_claim.claim_id)
    assert latest["revision"] == 2
    assert latest["content"] == "用户当前每天喝咖啡。"
    assert latest["status"] == "active"
