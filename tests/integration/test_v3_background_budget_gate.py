from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import (
    AttentionClass,
    BudgetOnExceed,
    BudgetScope,
    SourceClass,
    WakeSource,
)
from aios_core.contracts.models import BudgetPolicy, Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.review import ReviewSchedulePolicy
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective, ModelUsage
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import WakeSignalRequest


NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def _world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def _commit_budget(
    store,
    *,
    object_id="budget_background_day",
    max_wakes=None,
    max_model_calls=None,
    max_tokens=None,
    on_exceed=BudgetOnExceed.CHECKPOINT,
):
    policy = BudgetPolicy(
        object_id=object_id,
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="c13-budget-test",
        scope=BudgetScope.BACKGROUND_DAY,
        max_wakes=max_wakes,
        max_model_calls=max_model_calls,
        max_tokens=max_tokens,
        on_exceed=on_exceed,
    )
    store.commit(
        [policy],
        OperationRequest(
            operation_name="test.seed.background.budget",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed C13 background budget",
            idempotency_key=f"seed-{object_id}",
            source_class=SourceClass.PLATFORM,
        ),
    )
    return policy


def _commit_evidence(store, *, object_id="obs_budget_evidence"):
    observation = Observation(
        object_id=object_id,
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="c13-budget-test",
        source_kind="system",
        modality="marker",
        value={"changed": True},
        metadata={"dimension": "dim:test"},
    )
    store.commit(
        [observation],
        OperationRequest(
            operation_name="test.seed.background.budget.evidence",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed C13 budget evidence",
            idempotency_key=f"seed-{object_id}",
            source_class=SourceClass.USER,
        ),
    )
    return ObjectRef(object_id=object_id, revision=1)


def _emit_background(runtime, ref, *, key, observed_at):
    return runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.WATCH_MATCH,
            rule_id=key,
            observed_at=observed_at,
            evidence_refs=(ref,),
            dedupe_key=key,
            attention_class=AttentionClass.BACKGROUND,
        )
    )


def test_background_day_max_wakes_blocks_second_resident_invocation(tmp_path):
    store, index = _world(tmp_path)
    _commit_budget(store, max_wakes=1)
    ref = _commit_evidence(store)

    model_calls = []

    def model(snapshot):
        model_calls.append(snapshot.wake_reason)
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    first = _emit_background(
        runtime,
        ref,
        key="budget.max-wakes.first",
        observed_at=NOW + timedelta(minutes=1),
    )
    second = _emit_background(
        runtime,
        ref,
        key="budget.max-wakes.second",
        observed_at=NOW + timedelta(minutes=3),
    )

    first_result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=first.wake_id, revision=1),
        now=NOW + timedelta(minutes=2),
    )
    assert first_result.runtime is not None
    assert first_result.runtime.silenced is True
    assert model_calls == ["watch_match"]

    second_result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=second.wake_id, revision=1),
        now=NOW + timedelta(minutes=4),
    )
    assert second_result.runtime is None
    assert second_result.wake.state == "queued"
    assert any(
        item.startswith("background_wake_budget_exhausted:1/1")
        for item in second_result.step0.reasons
    )
    assert "model_budget_unavailable" in second_result.step0.reasons
    assert model_calls == ["watch_match"]


def test_background_model_call_budget_caps_tool_loop_before_extra_model_call(tmp_path):
    store, index = _world(tmp_path)
    _commit_budget(store, max_model_calls=1)
    ref = _commit_evidence(store)

    model_calls = 0

    def model(snapshot):
        nonlocal model_calls
        model_calls += 1
        return ModelDirective(
            capability_calls=(
                CapabilityCall(
                    name="inspect_world_object",
                    arguments={
                        "object_id": ref.object_id,
                        "revision": ref.revision,
                    },
                ),
            )
        )

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    wake = _emit_background(
        runtime,
        ref,
        key="budget.max-model-calls.first",
        observed_at=NOW + timedelta(minutes=1),
    )

    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=wake.wake_id, revision=1),
        now=NOW + timedelta(minutes=2),
    )
    assert result.runtime is not None
    assert result.runtime.model_rounds == 1
    assert result.runtime.termination_reason == "model_round_budget_exhausted"
    assert result.runtime.capability_history == ()
    assert model_calls == 1

    second = _emit_background(
        runtime,
        ref,
        key="budget.max-model-calls.second",
        observed_at=NOW + timedelta(minutes=3),
    )
    blocked = runtime.run_wake(
        wake_ref=ObjectRef(object_id=second.wake_id, revision=1),
        now=NOW + timedelta(minutes=4),
    )
    assert blocked.runtime is None
    assert any(
        item.startswith("background_model_call_budget_exhausted:1/1")
        for item in blocked.step0.reasons
    )
    assert model_calls == 1


def test_background_token_budget_fails_closed_without_provider_usage_telemetry(tmp_path):
    store, index = _world(tmp_path)
    _commit_budget(store, max_tokens=100)
    ref = _commit_evidence(store)

    model_calls = 0

    def model(snapshot):
        nonlocal model_calls
        model_calls += 1
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    wake = _emit_background(
        runtime,
        ref,
        key="budget.tokens.no-telemetry",
        observed_at=NOW + timedelta(minutes=1),
    )
    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=wake.wake_id, revision=1),
        now=NOW + timedelta(minutes=2),
    )

    assert result.runtime is None
    assert result.wake.state == "queued"
    assert (
        "background_token_budget_requires_preflight_token_bound"
        in result.step0.reasons
    )
    assert model_calls == 0


def test_completed_background_wake_exposes_exact_token_usage_in_budget_status(tmp_path):
    store, index = _world(tmp_path)
    _commit_budget(store, max_wakes=3, max_model_calls=4)
    ref = _commit_evidence(store, object_id="obs_exact_token_usage")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda snapshot: ModelDirective(
            silence=True,
            usage=ModelUsage(
                input_tokens=21,
                output_tokens=9,
                total_tokens=30,
            ),
        ),
    )
    wake = _emit_background(
        runtime,
        ref,
        key="budget.exact-token-usage",
        observed_at=NOW + timedelta(minutes=1),
    )
    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=wake.wake_id, revision=1),
        now=NOW + timedelta(minutes=2),
    )

    assert result.runtime is not None
    assert result.runtime.model_usage_complete is True
    assert result.runtime.model_total_tokens == 30

    current = runtime.wake_bus.current_wake(result.wake.wake_id)
    assert "model_usage_complete" not in current.metadata
    assert "model_total_tokens" not in current.metadata

    meter_rows = runtime.metering.list_model_calls(
        subject_id="user_1",
        wake_id=result.wake.wake_id,
    )
    assert len(meter_rows) == 1
    assert meter_rows[0].usage_complete is True
    assert meter_rows[0].input_tokens == 21
    assert meter_rows[0].output_tokens == 9
    assert meter_rows[0].total_tokens == 30

    status = runtime.background_budget_gate.status(
        now=NOW + timedelta(minutes=3),
    )
    assert status["used_wakes"] == 1
    assert status["used_model_calls"] == 1
    assert status["used_tokens"] == 30
    assert status["token_usage_available"] is True
    assert status["remaining_tokens"] is None


def test_budget_hard_deny_suppresses_background_wake(tmp_path):
    store, index = _world(tmp_path)
    _commit_budget(
        store,
        max_wakes=0,
        on_exceed=BudgetOnExceed.HARD_DENY,
    )
    ref = _commit_evidence(store)

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda snapshot: ModelDirective(silence=True),
    )
    wake = _emit_background(
        runtime,
        ref,
        key="budget.hard-deny",
        observed_at=NOW + timedelta(minutes=1),
    )
    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=wake.wake_id, revision=1),
        now=NOW + timedelta(minutes=2),
    )

    assert result.runtime is None
    assert result.wake.state == "suppressed"
    assert any(
        item.startswith("background_wake_budget_exhausted:0/0")
        for item in result.step0.reasons
    )


def test_safety_wake_bypasses_background_day_budget(tmp_path):
    store, index = _world(tmp_path)
    _commit_budget(
        store,
        max_wakes=0,
        max_model_calls=0,
        max_tokens=0,
        on_exceed=BudgetOnExceed.HARD_DENY,
    )
    ref = _commit_evidence(store)

    model_calls = []

    def model(snapshot):
        model_calls.append(snapshot.wake_reason)
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    safety = runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id="safety.budget-bypass",
            observed_at=NOW + timedelta(minutes=1),
            evidence_refs=(ref,),
            dedupe_key="safety-budget-bypass",
            priority=100,
            attention_class=AttentionClass.INTERRUPT,
        )
    )

    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=safety.wake_id, revision=1),
        now=NOW + timedelta(minutes=2),
    )
    assert result.runtime is not None
    assert result.runtime.silenced is True
    assert result.step0.model_allowed is True
    assert result.context is not None
    assert result.context.task_context["wake"]["budget"]["applies"] is False
    assert model_calls == ["safety"]



def _revise_budget(store, policy, *, changed_at, max_wakes=None, max_model_calls=None):
    revised = policy.model_copy(
        update={
            "revision": policy.revision + 1,
            "occurred": TemporalExtent.point(changed_at),
            "learned_at": changed_at,
            "recorded_at": changed_at,
            "max_wakes": max_wakes,
            "max_model_calls": max_model_calls,
            "max_tokens": None,
        }
    )
    store.commit(
        [revised],
        OperationRequest(
            operation_name="test.revise.background.budget",
            expected_world_revision=int(store.current_world_revision()),
            reason="revise C13 background budget for recovery test",
            idempotency_key=f"revise-{policy.object_id}-{revised.revision}",
            source_class=SourceClass.PLATFORM,
        ),
    )
    return revised


def test_provider_usage_is_durable_even_if_wake_completion_crashes(tmp_path, monkeypatch):
    store, index = _world(tmp_path)
    _commit_budget(store, max_model_calls=5)
    ref = _commit_evidence(store, object_id="obs_meter_crash")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda snapshot: ModelDirective(
            silence=True,
            usage=ModelUsage(
                input_tokens=17,
                output_tokens=5,
                total_tokens=22,
                provider="openai",
                model="test-model",
                request_id="resp_before_completion_crash",
            ),
        ),
    )
    signal = _emit_background(
        runtime,
        ref,
        key="budget.meter-before-complete",
        observed_at=NOW + timedelta(minutes=1),
    )

    def crash_complete(*args, **kwargs):
        raise RuntimeError("simulated crash before Wake completion")

    monkeypatch.setattr(runtime.wake_bus, "complete", crash_complete)

    with pytest.raises(RuntimeError, match="simulated crash"):
        runtime.run_wake(
            wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
            now=NOW + timedelta(minutes=2),
        )

    current = runtime.wake_bus.current_wake(signal.wake_id)
    assert current.wake_state.value == "running"
    assert "model_total_tokens" not in current.metadata

    rows = runtime.metering.list_model_calls(
        subject_id="user_1",
        wake_id=signal.wake_id,
    )
    assert len(rows) == 1
    assert rows[0].usage_complete is True
    assert rows[0].total_tokens == 22
    assert rows[0].provider_request_id == "resp_before_completion_crash"

    # Metering is not a World write: after the claim, the failed completion adds no
    # extra world revision even though the provider call is durably accounted.
    assert rows[0].world_revision == int(store.current_world_revision())


def test_running_budget_reservation_is_not_a_free_same_day_retry(tmp_path):
    store, index = _world(tmp_path)
    _commit_budget(store, max_model_calls=5)
    ref = _commit_evidence(store)

    model_calls = 0

    def model(snapshot):
        nonlocal model_calls
        model_calls += 1
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    signal = _emit_background(
        runtime,
        ref,
        key="budget.running-recovery",
        observed_at=NOW + timedelta(minutes=1),
    )
    wake = runtime.wake_bus.current_wake(signal.wake_id)
    decision = runtime.background_budget_gate.evaluate(
        wake,
        now=NOW + timedelta(minutes=2),
        max_model_rounds=runtime.cognitive_runtime.max_tool_rounds + 1,
    )
    assert decision.available is True
    runtime.wake_bus.claim(
        wake.object_id,
        started_at=NOW + timedelta(minutes=2),
        expected_world_revision=decision.world_revision,
        metadata_update=decision.reservation_metadata(),
    )

    same_day = runtime.run_wake(
        wake_ref=ObjectRef(object_id=wake.object_id, revision=2),
        now=NOW + timedelta(hours=1),
    )
    assert same_day.runtime is None
    assert same_day.wake.state == "running"
    assert "background_budget_reservation_already_running" in same_day.step0.reasons
    assert model_calls == 0

    next_day = runtime.run_wake(
        wake_ref=ObjectRef(object_id=wake.object_id, revision=2),
        now=NOW + timedelta(days=1, minutes=5),
    )
    assert next_day.runtime is not None
    assert next_day.runtime.silenced is True
    assert next_day.wake.state == "completed"
    assert model_calls == 1
    latest = runtime.wake_bus.current_wake(wake.object_id)
    assert latest.metadata["budget_window_start"].startswith("2026-09-22")


def test_periodic_review_budget_defers_then_resumes_same_anchors(tmp_path):
    store, index = _world(tmp_path)
    policy = _commit_budget(store, max_wakes=0)
    ref = _commit_evidence(store, object_id="obs_periodic_budget_anchor")

    model_calls = []

    def model(snapshot):
        model_calls.append(snapshot.wake_reason)
        review = snapshot.cockpit["task_context"]["periodic_review"]
        assert review["budget"]["available"] is True
        return ModelDirective(
            silence=True,
            usage=ModelUsage(
                input_tokens=31,
                output_tokens=13,
                total_tokens=44,
            ),
        )

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    schedule = ReviewSchedulePolicy(
        interval_hours=24,
        lookback_hours=72,
        max_candidates=80,
        max_per_object_type=20,
    )
    deferred = runtime.run_periodic_review(
        now=NOW + timedelta(hours=25),
        policy=schedule,
    )
    assert deferred is not None
    assert deferred.runtime is None
    assert deferred.context is None
    assert deferred.wake.state == "queued"
    assert deferred.budget is not None
    assert deferred.budget.available is False
    assert model_calls == []

    queued_ref = deferred.request.wake_ref
    queued_anchor_refs = tuple(
        (item.object_ref.object_id, item.object_ref.revision)
        for item in deferred.request.anchors
    )
    assert (ref.object_id, ref.revision) in queued_anchor_refs

    _revise_budget(
        store,
        policy,
        changed_at=NOW + timedelta(hours=26),
        max_wakes=1,
    )
    resumed = runtime.run_periodic_review(
        now=NOW + timedelta(hours=27),
        policy=schedule,
    )
    assert resumed is not None
    assert resumed.runtime is not None
    assert resumed.runtime.silenced is True
    assert resumed.wake.state == "completed"
    assert resumed.request.wake_ref.object_id == queued_ref.object_id
    resumed_anchor_refs = tuple(
        (item.object_ref.object_id, item.object_ref.revision)
        for item in resumed.request.anchors
    )
    assert resumed_anchor_refs == queued_anchor_refs
    assert model_calls == ["periodic_review"]

    completed_payload = store.get_payload(
        resumed.wake.wake_id,
        revision=resumed.wake.revision,
    )
    assert "model_usage_complete" not in completed_payload["metadata"]
    assert "model_total_tokens" not in completed_payload["metadata"]
    review_meter_rows = runtime.metering.list_model_calls(
        subject_id="user_1",
        wake_id=resumed.wake.wake_id,
    )
    assert len(review_meter_rows) == 1
    assert review_meter_rows[0].total_tokens == 44
    assert review_meter_rows[0].execution_class == "periodic_review"
    assert review_meter_rows[0].recorded_at == NOW + timedelta(hours=27)
    status = runtime.background_budget_gate.status(
        now=NOW + timedelta(hours=28),
    )
    assert status["used_tokens"] == 44
    assert status["token_usage_available"] is True


def test_periodic_review_requires_full_model_round_budget(tmp_path):
    store, index = _world(tmp_path)
    _commit_budget(store, max_model_calls=1)
    _commit_evidence(store, object_id="obs_periodic_full_budget_anchor")

    model_calls = 0

    def model(snapshot):
        nonlocal model_calls
        model_calls += 1
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    result = runtime.run_periodic_review(
        now=NOW + timedelta(hours=25),
        policy=ReviewSchedulePolicy(
            interval_hours=24,
            lookback_hours=72,
            max_candidates=80,
            max_per_object_type=20,
        ),
    )
    assert result is not None
    assert result.runtime is None
    assert result.wake.state == "queued"
    assert result.budget is not None
    assert (
        "background_model_call_budget_insufficient_for_full_run:1/5"
        in result.budget.reasons
    )
    assert model_calls == 0


def test_periodic_running_review_does_not_repeat_same_day_and_can_refresh_next_day(tmp_path):
    store, index = _world(tmp_path)
    _commit_budget(store, max_model_calls=5)
    ref = _commit_evidence(store, object_id="obs_periodic_running_budget")

    model_calls = 0

    def model(snapshot):
        nonlocal model_calls
        model_calls += 1
        if model_calls <= 5:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="inspect_world_object",
                        arguments={
                            "object_id": ref.object_id,
                            "revision": ref.revision,
                        },
                    ),
                )
            )
        return ModelDirective(
            silence=True,
            usage=ModelUsage(
                input_tokens=18,
                output_tokens=4,
                total_tokens=22,
                provider="openai",
                model="review-model",
                request_id="resp_resumed_review_next_day",
            ),
        )

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    schedule = ReviewSchedulePolicy(
        interval_hours=24,
        lookback_hours=72,
        max_candidates=80,
        max_per_object_type=20,
    )
    first = runtime.run_periodic_review(
        now=NOW + timedelta(hours=25),
        policy=schedule,
    )
    assert first is not None
    assert first.runtime is not None
    assert first.runtime.termination_reason == "tool_round_budget_exhausted"
    assert first.runtime.model_rounds == 5
    assert first.wake.state == "running"
    assert model_calls == 5
    first_running = store.get_payload(first.wake.wake_id)
    original_started_at = first_running["metadata"]["started_at"]
    assert original_started_at == (NOW + timedelta(hours=25)).isoformat()

    same_day = runtime.run_periodic_review(
        now=NOW + timedelta(hours=26),
        policy=schedule,
    )
    assert same_day is not None
    assert same_day.runtime is None
    assert same_day.wake.state == "running"
    assert same_day.budget is not None
    assert (
        "background_budget_reservation_already_running"
        in same_day.budget.reasons
    )
    assert model_calls == 5

    next_day = runtime.run_periodic_review(
        now=NOW + timedelta(hours=49),
        policy=schedule,
    )
    assert next_day is not None
    assert next_day.runtime is not None
    assert next_day.runtime.silenced is True
    assert next_day.wake.state == "completed"
    assert model_calls == 6

    completed = store.get_payload(
        next_day.wake.wake_id,
        revision=next_day.wake.revision,
    )
    # The review's cognition/write clock stays pinned to the original RUNNING
    # review start even though the provider call happened in the next budget day.
    assert completed["metadata"]["started_at"] == original_started_at

    meter_rows = runtime.metering.list_model_calls(
        subject_id="user_1",
        wake_id=next_day.wake.wake_id,
    )
    exact_rows = [row for row in meter_rows if row.usage_complete]
    assert len(exact_rows) == 1
    assert exact_rows[0].recorded_at == NOW + timedelta(hours=49)
    assert exact_rows[0].total_tokens == 22
    assert exact_rows[0].provider_request_id == "resp_resumed_review_next_day"



def test_resident_can_read_budget_and_attention_routing_contract(tmp_path):
    store, index = _world(tmp_path)
    _commit_budget(
        store,
        max_wakes=3,
        max_model_calls=4,
    )
    ref = _commit_evidence(store, object_id="obs_budget_awareness")

    phase = {"background_done": False}

    def model(snapshot):
        if snapshot.wake_reason == "watch_match":
            phase["background_done"] = True
            return ModelDirective(silence=True)

        assert snapshot.wake_reason == "user_interaction"
        spec = next(
            item
            for item in snapshot.capability_catalog
            if item["name"] == "create_attention_watch"
        )
        description = spec["description"]
        assert "interrupt" in description
        assert "background" in description
        assert "review_queue" in description
        assert "Core does not infer urgency for you" in description

        if not snapshot.capability_history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="read_background_budget",
                        arguments={},
                    ),
                )
            )

        budget = snapshot.capability_history[-1].data
        assert budget["applies"] is True
        assert budget["used_wakes"] == 1
        assert budget["used_model_calls"] == 1
        assert budget["remaining_wakes"] == 2
        assert budget["remaining_model_calls"] == 3
        assert budget["token_usage_available"] is False
        return ModelDirective(response="我会按当前预算和注意力档位自行决定后续关注方式。")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )
    signal = _emit_background(
        runtime,
        ref,
        key="budget.awareness.seed-use",
        observed_at=NOW + timedelta(minutes=1),
    )
    used = runtime.run_wake(
        wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
        now=NOW + timedelta(minutes=2),
    )
    assert used.runtime is not None
    assert phase["background_done"] is True

    turn = runtime.run_turn(
        session_id="budget-awareness",
        turn_index=1,
        user_input="以后如果世界发生变化，你自己判断什么时候值得叫醒。",
        current_topic=None,
        occurred_at=NOW + timedelta(minutes=3),
    )
    assert (
        turn.runtime.response
        == "我会按当前预算和注意力档位自行决定后续关注方式。"
    )
