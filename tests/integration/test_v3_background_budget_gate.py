from datetime import datetime, timedelta, timezone

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
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
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
        "background_token_budget_requires_provider_usage_telemetry"
        in result.step0.reasons
    )
    assert model_calls == 0


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
