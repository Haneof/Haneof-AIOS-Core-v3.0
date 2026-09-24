from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import (
    BudgetOnExceed,
    BudgetScope,
    ObjectType,
    SourceClass,
    WakeSource,
)
from aios_core.contracts.models import BudgetPolicy, Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    BackgroundModelAttemptBlocked,
    BackgroundModelExecutionInDoubt,
    BackgroundModelResponsePending,
)
from aios_core.runtime.cognitive_runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelDispatchNotSubmitted,
    ModelUsage,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import WakeSignalRequest


NOW = datetime(2026, 9, 24, 6, 0, tzinfo=timezone.utc)


def _world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def _seed_review_fact(store: SQLiteWorldStore) -> None:
    fact = Observation(
        object_id="obs_gap_fix_002_review_fact",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=1)),
        learned_at=NOW - timedelta(hours=1),
        recorded_at=NOW - timedelta(hours=1),
        created_by="test:core-gap-fix-002",
        source_kind="conversation",
        modality="text",
        value="A durable fact eligible for periodic review.",
        metadata={"dimension": "dim:test"},
    )
    store.commit(
        [fact],
        OperationRequest(
            operation_name="test.core_gap_fix_002.seed_review_fact",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed periodic review fact",
            idempotency_key="core-gap-fix-002:seed-review-fact",
            source_class=SourceClass.USER,
        ),
    )


def _commit_budget(store: SQLiteWorldStore, *, max_model_calls: int) -> None:
    policy = BudgetPolicy(
        object_id="budget_gap_fix_002",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="test:core-gap-fix-002",
        scope=BudgetScope.BACKGROUND_DAY,
        max_model_calls=max_model_calls,
        on_exceed=BudgetOnExceed.CHECKPOINT,
    )
    store.commit(
        [policy],
        OperationRequest(
            operation_name="test.core_gap_fix_002.seed_budget",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed background budget",
            idempotency_key="core-gap-fix-002:seed-budget",
            source_class=SourceClass.PLATFORM,
        ),
    )


def _emit_wake(
    runtime: FusedTurnRuntime,
    *,
    source: WakeSource = WakeSource.SAFETY,
    observed_at: datetime = NOW,
    key: str = "gap-fix-002",
):
    return runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=source,
            rule_id=f"core-gap-fix-002.{key}",
            observed_at=observed_at,
            dedupe_key=f"core-gap-fix-002:{key}",
        )
    )


def _running_periodic_review_id(store: SQLiteWorldStore) -> str:
    running = [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.WAKE,
            subject_id="user_1",
        )
        if payload.get("wake_state") == "running"
        and payload.get("wake_source") == WakeSource.PERIODIC_REVIEW.value
    ]
    assert len(running) == 1
    return str(running[0]["object_id"])


def _directive(request_id: str) -> ModelDirective:
    provenance = ModelCallProvenance(
        provider="test-provider",
        model="test-model",
        request_id=request_id,
    )
    return ModelDirective(
        silence=True,
        usage=ModelUsage(
            input_tokens=4,
            output_tokens=1,
            total_tokens=5,
            provider=provenance.provider,
            model=provenance.model,
            request_id=provenance.request_id,
        ),
        provenance=provenance,
    )


def test_wake_ambiguous_failure_is_in_doubt_and_restart_does_not_reinvoke_provider(tmp_path):
    store, index = _world(tmp_path)
    calls = []

    def ambiguous_provider(snapshot):
        calls.append(("first", snapshot.round_index, snapshot.model_attempt_id))
        raise TimeoutError("provider may already have accepted the request")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=ambiguous_provider)
    signal = _emit_wake(runtime, key="wake-ambiguous")

    with pytest.raises(TimeoutError, match="may already have accepted"):
        runtime.run_wake(
            wake_ref=ObjectRef(object_id=signal.wake_id, revision=signal.revision),
            now=NOW,
        )

    attempt = runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert attempt is not None
    assert attempt.state == "in_doubt"
    assert attempt.recovery_disposition == "in_doubt"
    assert calls[0][2] == attempt.attempt_id
    assert runtime.wake_bus.current_wake(signal.wake_id).wake_state.value == "running"

    reopened = SQLiteWorldStore(tmp_path / "world.db")
    reopened_index = WorldSearchIndex(tmp_path / "world.db", store=reopened)
    reopened_index.rebuild()

    def must_not_reinvoke(_snapshot):
        raise AssertionError("IN_DOUBT Wake must not call provider again")

    restarted = FusedTurnRuntime(
        store=reopened,
        index=reopened_index,
        model_handler=must_not_reinvoke,
    )
    with pytest.raises(BackgroundModelExecutionInDoubt) as blocked:
        restarted.run_wake(
            wake_ref=ObjectRef(object_id=signal.wake_id, revision=signal.revision),
            now=NOW + timedelta(minutes=5),
        )
    assert blocked.value.attempt.attempt_id == attempt.attempt_id
    assert len(calls) == 1


def test_periodic_review_ambiguous_failure_is_in_doubt_and_restart_does_not_reinvoke_provider(tmp_path):
    store, index = _world(tmp_path)
    _seed_review_fact(store)
    index.catch_up()
    calls = []

    def ambiguous_provider(snapshot):
        calls.append(("first", snapshot.round_index, snapshot.model_attempt_id))
        raise TimeoutError("review provider may already have accepted the request")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=ambiguous_provider)
    with pytest.raises(TimeoutError, match="may already have accepted"):
        runtime.run_periodic_review(now=NOW)

    wake_id = _running_periodic_review_id(store)
    attempt = runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="periodic_review",
        work_id=wake_id,
        model_round_index=0,
    )
    assert attempt is not None
    assert attempt.state == "in_doubt"
    assert calls[0][2] == attempt.attempt_id

    reopened = SQLiteWorldStore(tmp_path / "world.db")
    reopened_index = WorldSearchIndex(tmp_path / "world.db", store=reopened)
    reopened_index.rebuild()

    def must_not_reinvoke(_snapshot):
        raise AssertionError("IN_DOUBT Review must not call provider again")

    restarted = FusedTurnRuntime(
        store=reopened,
        index=reopened_index,
        model_handler=must_not_reinvoke,
    )
    with pytest.raises(BackgroundModelExecutionInDoubt) as blocked:
        restarted.run_periodic_review(now=NOW + timedelta(minutes=5))
    assert blocked.value.attempt.attempt_id == attempt.attempt_id
    assert len(calls) == 1


def test_crash_before_dispatch_keeps_admitted_attempt_safe_to_retry_on_restart(
    tmp_path,
    monkeypatch,
):
    store, index = _world(tmp_path)
    first_runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: pytest.fail(
            "provider must not be reached before dispatch admission is durable"
        ),
    )
    signal = _emit_wake(first_runtime, key="crash-before-dispatch")

    def crash_before_dispatch(_attempt_id, *, dispatched_at):
        raise RuntimeError("simulated crash before provider dispatch")

    monkeypatch.setattr(
        first_runtime.background_model_attempts,
        "mark_dispatching",
        crash_before_dispatch,
    )
    with pytest.raises(RuntimeError, match="before provider dispatch"):
        first_runtime.run_wake(
            wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
            now=NOW,
        )

    admitted = first_runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert admitted is not None
    assert admitted.state == "admitted"
    assert admitted.recovery_disposition == "safe_to_retry"

    reopened = SQLiteWorldStore(tmp_path / "world.db")
    reopened_index = WorldSearchIndex(tmp_path / "world.db", store=reopened)
    reopened_index.rebuild()
    seen_ids = []

    def provider(snapshot):
        seen_ids.append(snapshot.model_attempt_id)
        return _directive("req_after_pre_dispatch_crash")

    restarted = FusedTurnRuntime(
        store=reopened,
        index=reopened_index,
        model_handler=provider,
    )
    completed = restarted.run_wake(
        wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
        now=NOW + timedelta(minutes=1),
    )

    assert completed.wake.state == "completed"
    assert seen_ids == [admitted.attempt_id]
    durable = restarted.background_model_attempts.get(admitted.attempt_id)
    assert durable is not None
    assert durable.state == "metered"


def test_definitely_not_submitted_can_retry_same_attempt_identity(tmp_path):
    store, index = _world(tmp_path)
    seen_attempt_ids = []
    calls = 0

    def provider(snapshot):
        nonlocal calls
        calls += 1
        seen_attempt_ids.append(snapshot.model_attempt_id)
        if calls == 1:
            raise ModelDispatchNotSubmitted("socket failed before request write")
        return _directive("req_safe_retry")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=provider)
    signal = _emit_wake(runtime, key="safe-retry")

    with pytest.raises(ModelDispatchNotSubmitted):
        runtime.run_wake(
            wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
            now=NOW,
        )
    first = runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert first is not None
    assert first.state == "not_submitted"
    assert first.recovery_disposition == "safe_to_retry"

    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
        now=NOW + timedelta(minutes=1),
    )
    assert result.wake.state == "completed"
    final = runtime.background_model_attempts.get(first.attempt_id)
    assert final is not None
    assert final.state == "metered"
    assert seen_attempt_ids == [first.attempt_id, first.attempt_id]


def test_wake_response_is_durable_before_meter_and_restart_blocks_reinvocation(
    tmp_path,
    monkeypatch,
):
    store, index = _world(tmp_path)
    calls = 0

    def provider(_snapshot):
        nonlocal calls
        calls += 1
        return _directive("req_response_before_meter")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=provider)
    signal = _emit_wake(runtime, key="response-before-meter")

    def fail_meter(**_kwargs):
        raise RuntimeError("simulated crash before meter commit")

    monkeypatch.setattr(runtime.metering, "record_model_call", fail_meter)
    with pytest.raises(RuntimeError, match="before meter"):
        runtime.run_wake(
            wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
            now=NOW,
        )

    attempt = runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert attempt is not None
    assert attempt.state == "response_returned"
    assert attempt.provider_request_id == "req_response_before_meter"

    reopened = SQLiteWorldStore(tmp_path / "world.db")
    reopened_index = WorldSearchIndex(tmp_path / "world.db", store=reopened)
    reopened_index.rebuild()
    restarted = FusedTurnRuntime(
        store=reopened,
        index=reopened_index,
        model_handler=lambda _snapshot: pytest.fail("provider reinvoked"),
    )
    with pytest.raises(BackgroundModelResponsePending):
        restarted.run_wake(
            wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
            now=NOW + timedelta(minutes=1),
        )
    assert calls == 1


def test_wake_metered_before_completion_stays_blocked_without_synthetic_success(
    tmp_path,
    monkeypatch,
):
    store, index = _world(tmp_path)
    calls = 0

    def provider(_snapshot):
        nonlocal calls
        calls += 1
        return _directive("req_metered_before_complete")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=provider)
    signal = _emit_wake(runtime, key="metered-before-complete")

    monkeypatch.setattr(
        runtime.wake_bus,
        "complete",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("simulated crash before Wake completion")
        ),
    )
    with pytest.raises(RuntimeError, match="Wake completion"):
        runtime.run_wake(
            wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
            now=NOW,
        )

    attempt = runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert attempt is not None
    assert attempt.state == "metered"
    meter_rows = runtime.metering.list_model_calls(
        subject_id="user_1",
        wake_id=signal.wake_id,
    )
    assert len(meter_rows) == 1
    assert meter_rows[0].background_attempt_id == attempt.attempt_id
    assert attempt.meter_record_id == meter_rows[0].record_id

    reopened = SQLiteWorldStore(tmp_path / "world.db")
    reopened_index = WorldSearchIndex(tmp_path / "world.db", store=reopened)
    reopened_index.rebuild()
    restarted = FusedTurnRuntime(
        store=reopened,
        index=reopened_index,
        model_handler=lambda _snapshot: pytest.fail("provider reinvoked"),
    )
    with pytest.raises(BackgroundModelAttemptBlocked) as blocked:
        restarted.run_wake(
            wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
            now=NOW + timedelta(minutes=1),
        )
    assert blocked.value.attempt.state == "metered"
    assert calls == 1


def test_periodic_review_response_before_meter_and_meter_before_completion_are_fail_closed(
    tmp_path,
    monkeypatch,
):
    store, index = _world(tmp_path)
    _seed_review_fact(store)
    index.catch_up()

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: _directive("req_review_response_before_meter"),
    )
    real_meter = runtime.metering.record_model_call

    def fail_meter(**_kwargs):
        raise RuntimeError("simulated review meter crash")

    monkeypatch.setattr(runtime.metering, "record_model_call", fail_meter)
    with pytest.raises(RuntimeError, match="review meter crash"):
        runtime.run_periodic_review(now=NOW)
    wake_id = _running_periodic_review_id(store)
    response_attempt = runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="periodic_review",
        work_id=wake_id,
        model_round_index=0,
    )
    assert response_attempt is not None
    assert response_attempt.state == "response_returned"

    monkeypatch.setattr(runtime.metering, "record_model_call", real_meter)
    reopened = SQLiteWorldStore(tmp_path / "world.db")
    reopened_index = WorldSearchIndex(tmp_path / "world.db", store=reopened)
    reopened_index.rebuild()
    restarted = FusedTurnRuntime(
        store=reopened,
        index=reopened_index,
        model_handler=lambda _snapshot: pytest.fail("review provider reinvoked"),
    )
    with pytest.raises(BackgroundModelResponsePending):
        restarted.run_periodic_review(now=NOW + timedelta(minutes=1))

    # A separate World proves the post-meter / pre-completion window.
    store2 = SQLiteWorldStore(tmp_path / "world2.db")
    index2 = WorldSearchIndex(tmp_path / "world2.db", store=store2)
    index2.rebuild()
    _seed_review_fact(store2)
    index2.catch_up()
    runtime2 = FusedTurnRuntime(
        store=store2,
        index=index2,
        model_handler=lambda _snapshot: _directive("req_review_metered_before_complete"),
    )
    monkeypatch.setattr(
        runtime2.periodic_review,
        "complete_review",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("simulated review completion crash")
        ),
    )
    with pytest.raises(RuntimeError, match="review completion crash"):
        runtime2.run_periodic_review(now=NOW)
    wake_id2 = _running_periodic_review_id(store2)
    metered = runtime2.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="periodic_review",
        work_id=wake_id2,
        model_round_index=0,
    )
    assert metered is not None
    assert metered.state == "metered"

    reopened2 = SQLiteWorldStore(tmp_path / "world2.db")
    reopened_index2 = WorldSearchIndex(tmp_path / "world2.db", store=reopened2)
    reopened_index2.rebuild()
    restarted2 = FusedTurnRuntime(
        store=reopened2,
        index=reopened_index2,
        model_handler=lambda _snapshot: pytest.fail("review provider reinvoked"),
    )
    with pytest.raises(BackgroundModelAttemptBlocked) as blocked:
        restarted2.run_periodic_review(now=NOW + timedelta(minutes=1))
    assert blocked.value.attempt.state == "metered"


def test_budget_rollover_does_not_erase_in_doubt(tmp_path):
    store, index = _world(tmp_path)
    _commit_budget(store, max_model_calls=5)
    calls = 0

    def ambiguous_provider(_snapshot):
        nonlocal calls
        calls += 1
        raise TimeoutError("possibly submitted")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=ambiguous_provider)
    signal = _emit_wake(
        runtime,
        source=WakeSource.WATCH_MATCH,
        observed_at=NOW + timedelta(minutes=1),
        key="budget-in-doubt",
    )
    with pytest.raises(TimeoutError, match="possibly submitted"):
        runtime.run_wake(
            wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
            now=NOW + timedelta(minutes=2),
        )

    same_day = runtime.run_wake(
        wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
        now=NOW + timedelta(hours=1),
    )
    assert same_day.runtime is None
    assert same_day.wake.state == "running"
    assert "background_budget_reservation_already_running" in same_day.step0.reasons

    with pytest.raises(BackgroundModelExecutionInDoubt):
        runtime.run_wake(
            wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
            now=NOW + timedelta(days=1, minutes=5),
        )
    assert calls == 1


def test_normal_successful_wake_and_review_close_attempts_as_metered(tmp_path):
    store, index = _world(tmp_path)
    wake_runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: _directive("req_normal_wake"),
    )
    signal = _emit_wake(wake_runtime, key="normal-success")
    wake_result = wake_runtime.run_wake(
        wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
        now=NOW,
    )
    assert wake_result.wake.state == "completed"
    wake_attempt = wake_runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert wake_attempt is not None
    assert wake_attempt.state == "metered"

    store2 = SQLiteWorldStore(tmp_path / "review-normal.db")
    index2 = WorldSearchIndex(tmp_path / "review-normal.db", store=store2)
    index2.rebuild()
    _seed_review_fact(store2)
    index2.catch_up()
    review_runtime = FusedTurnRuntime(
        store=store2,
        index=index2,
        model_handler=lambda _snapshot: _directive("req_normal_review"),
    )
    review_result = review_runtime.run_periodic_review(now=NOW)
    assert review_result is not None
    assert review_result.wake.state == "completed"
    review_attempt = review_runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="periodic_review",
        work_id=review_result.wake.wake_id,
        model_round_index=0,
    )
    assert review_attempt is not None
    assert review_attempt.state == "metered"
