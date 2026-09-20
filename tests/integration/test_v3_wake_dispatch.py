from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import SourceClass, TaskState, TaskType
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.execution import GoalTaskActionService, TaskCreateRequest
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import WakeStep0Decision, WakeStep0Outcome


NOW = datetime(2026, 9, 20, 16, 0, tzinfo=timezone.utc)


def _due_task(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    evidence = Observation(
        object_id="obs_p16_due_task",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW),
        learned_at=NOW,
        recorded_at=NOW,
        created_by="p16-wake-test",
        source_kind="conversation",
        modality="text",
        value="两个小时后提醒我继续处理 P16 入住测试。",
        metadata={"dimension": "dim:user_ai_interaction"},
    )
    store.commit(
        [evidence],
        OperationRequest(
            operation_name="test.seed.p16-wake",
            expected_world_revision=0,
            reason="seed a real task reason",
            idempotency_key="seed-p16-wake",
            source_class=SourceClass.USER,
        ),
    )
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    execution = GoalTaskActionService(store=store, index=index)
    task = execution.create_task(
        TaskCreateRequest(
            title="继续处理 P16 入住测试",
            task_type=TaskType.SCHEDULED,
            reason_refs=(ObjectRef(object_id=evidence.object_id, revision=1),),
            initial_state=TaskState.WAITING_TIME,
            priority=70,
            next_wake_at=NOW + timedelta(hours=2),
            timezone_name="UTC",
            next_step="检查长期入住跑数与失败样本。",
        ),
        created_at=NOW,
    )
    receipts = execution.wake_due_tasks(now=NOW + timedelta(hours=2, seconds=1))
    assert len(receipts) == 1
    return store, index, evidence, task, receipts[0]


def test_task_due_wake_enters_same_resident_runtime(tmp_path):
    store, index, _evidence, task, wake_receipt = _due_task(tmp_path)
    model_snapshots = []

    def model(snapshot):
        model_snapshots.append(snapshot)
        assert snapshot.wake_reason == "task_due"
        wake_context = snapshot.cockpit["task_context"]["wake"]
        assert wake_context["wake_source"] == "task_due"
        assert wake_context["step0"]["outcome"] == "ok"
        assert wake_context["step0"]["delivery_allowed"] is True
        assert wake_context["trigger_hints"][0]["current_state"]["task_state"] == "ready"
        if not snapshot.capability_history:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="inspect_world_object",
                        arguments={"object_id": task.task_id},
                    ),
                )
            )
        inspected = snapshot.capability_history[-1]
        assert inspected.ok is True
        assert inspected.data["task_state"] == "ready"
        return ModelDirective(silence=True)

    gate_calls = []

    def step0_gate(wake, now):
        gate_calls.append((wake.object_id, now))
        return WakeStep0Decision(
            outcome=WakeStep0Outcome.OK,
            audit={
                "safety": "clear",
                "convenience": "clear",
                "channel": "open",
                "budget": "ok",
            },
        )

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=wake_receipt.wake_id, revision=1),
        now=NOW + timedelta(hours=2, seconds=2),
        step0_gate=step0_gate,
    )

    assert len(gate_calls) == 1
    assert len(model_snapshots) == 2
    assert result.runtime.silenced is True
    assert result.delivery_allowed is True
    assert result.wake.state == "completed"
    latest = store.get_payload(wake_receipt.wake_id)
    assert latest["revision"] == 3
    assert latest["wake_state"] == "completed"
    assert latest["hit_count"] == 1
    assert latest["metadata"]["dispatch_step0"]["outcome"] == "ok"
    assert latest["metadata"]["termination_reason"] == "silence"

    # Scheduler created exactly one durable task Wake and the runtime consumed it;
    # the dispatch path did not fabricate a Conversation Observation.
    assert store.get_payload(task.task_id)["task_state"] == "ready"
    observations = store.list_payloads(subject_id="user_1")
    conversation_values = [
        payload.get("value")
        for payload in observations
        if payload.get("object_type") == "observation"
    ]
    assert conversation_values == ["两个小时后提醒我继续处理 P16 入住测试。"]


def test_quiet_step0_still_allows_background_cognition_but_blocks_delivery(tmp_path):
    store, index, _evidence, _task, wake_receipt = _due_task(tmp_path)
    seen = []

    def model(snapshot):
        seen.append(snapshot.wake_reason)
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=wake_receipt.wake_id, revision=1),
        now=NOW + timedelta(hours=2, seconds=2),
        step0_gate=lambda _wake, _now: WakeStep0Decision(
            outcome=WakeStep0Outcome.QUIET,
            audit={"convenience": "sleep_window", "channel": "blocked"},
        ),
    )

    assert seen == ["task_due"]
    assert result.delivery_allowed is False
    assert result.runtime.silenced is True
    assert result.context.task_context["wake"]["step0"]["outcome"] == "quiet"
    assert store.get_payload(wake_receipt.wake_id)["wake_state"] == "completed"


def test_running_wake_resumes_without_recomputing_step0(tmp_path):
    store, index, _evidence, _task, wake_receipt = _due_task(tmp_path)

    def failing_model(_snapshot):
        raise RuntimeError("synthetic process crash")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=failing_model)
    gate_calls = []

    def first_gate(_wake, _now):
        gate_calls.append("called")
        return WakeStep0Decision(
            outcome=WakeStep0Outcome.HARD_BLOCK,
            audit={"channel": "no_epoch"},
        )

    with pytest.raises(RuntimeError, match="synthetic process crash"):
        runtime.run_wake(
            wake_ref=ObjectRef(object_id=wake_receipt.wake_id, revision=1),
            now=NOW + timedelta(hours=2, seconds=2),
            step0_gate=first_gate,
        )

    running = store.get_payload(wake_receipt.wake_id)
    assert running["revision"] == 2
    assert running["wake_state"] == "running"
    assert running["metadata"]["dispatch_step0"]["outcome"] == "hard_block"
    assert gate_calls == ["called"]

    resumed = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: ModelDirective(silence=True),
    )

    def must_not_run(_wake, _now):
        raise AssertionError("Step-0 must not be recomputed for a resumed RUNNING wake")

    result = resumed.run_wake(
        wake_ref=ObjectRef(object_id=wake_receipt.wake_id, revision=1),
        now=NOW + timedelta(hours=2, seconds=5),
        step0_gate=must_not_run,
    )
    assert result.request.step0.outcome is WakeStep0Outcome.HARD_BLOCK
    assert result.delivery_allowed is False
    assert store.get_payload(wake_receipt.wake_id)["wake_state"] == "completed"


def test_specialized_wake_sources_cannot_bypass_their_runtime_paths(tmp_path):
    store, index, _evidence, _task, _wake_receipt = _due_task(tmp_path)
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: ModelDirective(silence=True),
    )

    # No specialized Wake is manufactured here; the assertion protects the public
    # generic source set itself from accidentally swallowing safety/review/user turns.
    from aios_core.contracts.enums import WakeSource
    from aios_core.wake import GENERIC_RESIDENT_WAKE_SOURCES

    assert WakeSource.USER_INTERACTION not in GENERIC_RESIDENT_WAKE_SOURCES
    assert WakeSource.PERIODIC_REVIEW not in GENERIC_RESIDENT_WAKE_SOURCES
    assert WakeSource.SAFETY not in GENERIC_RESIDENT_WAKE_SOURCES
    assert WakeSource.TASK_DUE in GENERIC_RESIDENT_WAKE_SOURCES
    assert runtime.wake_dispatch.subject_id == "user_1"
