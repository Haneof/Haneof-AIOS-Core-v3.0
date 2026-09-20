from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from aios_core.contracts.enums import ObjectType, SourceClass, TaskState, TaskType, WakeSource
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.execution import TaskCreateRequest
from aios_core.ingest import (
    MechanicalSeriesPolicy,
    NumericSample,
    RealityIngestService,
    SourceAdapterSpec,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.review import ReviewSchedulePolicy
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import (
    ObservationTriggerService,
    ObservationWakeRule,
    Step0GateInput,
    WakeBus,
    WakeSignalRequest,
)


NOW = datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc)


def _seed_observation(
    store: SQLiteWorldStore,
    *,
    object_id: str,
    value: object,
    occurred_at: datetime,
) -> ObjectRef:
    observation = Observation(
        object_id=object_id,
        subject_id="user_1",
        occurred=TemporalExtent.point(occurred_at),
        learned_at=occurred_at,
        recorded_at=occurred_at,
        created_by="test:c09",
        source_kind="sensor",
        modality="structured_record",
        value=value,
        metadata={"dimension": "dim:test"},
    )
    store.commit(
        [observation],
        OperationRequest(
            operation_name=f"test.seed.{object_id}",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed C09 evidence",
            idempotency_key=f"seed:{object_id}",
            source_class=SourceClass.SENSOR,
        ),
    )
    return ObjectRef(object_id=object_id, revision=1)


def _world(tmp_path):
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def test_registered_numeric_change_marker_can_mechanically_create_wake(tmp_path) -> None:
    store, index = _world(tmp_path)
    ingest = RealityIngestService(store=store, index=index)
    heart_rate = SourceAdapterSpec(
        adapter_id="sensor.heart_rate.c09",
        source_kind="heart_rate",
        dimension="dim:heart_rate",
        source_class=SourceClass.SENSOR,
        default_modality="numeric",
    )
    receipt = ingest.ingest_numeric_series(
        heart_rate,
        series_id="c09-hr-window",
        samples=(
            NumericSample(
                external_record_id="hr-a",
                occurred_at=NOW,
                value=80.0,
            ),
            NumericSample(
                external_record_id="hr-b",
                occurred_at=NOW + timedelta(minutes=1),
                value=105.0,
            ),
        ),
        policy=MechanicalSeriesPolicy(
            tolerance=3.0,
            change_threshold=15.0,
            max_gap_seconds=120.0,
        ),
        unit="bpm",
        received_at=NOW + timedelta(minutes=2),
    )
    assert len(receipt.change_observation_ids) == 1
    change_ref = ObjectRef(
        object_id=receipt.change_observation_ids[0],
        revision=1,
    )

    bus = WakeBus(store=store, index=index)
    trigger = ObservationTriggerService(
        store=store,
        wake_bus=bus,
    )
    rules = (
        ObservationWakeRule(
            rule_id="heart-rate.numeric-change.registered",
            wake_source=WakeSource.MECHANICAL_CHANGE,
            source_kind="heart_rate",
            modality="numeric_change",
            metadata_equals={"mechanical_threshold_event": True},
            dedupe_metadata_keys=("adapter_id", "series_id"),
            priority=70,
            cooldown_seconds=300,
        ),
    )
    wakes = trigger.evaluate_observation(change_ref, rules=rules)

    assert len(wakes) == 1
    wake = bus.current_wake(wakes[0].wake_id)
    assert wake.wake_source is WakeSource.MECHANICAL_CHANGE
    assert wake.evidence_refs == [change_ref]
    assert wake.first_hit_at == NOW + timedelta(minutes=2)
    assert wake.metadata["trigger_kind"] == "registered_observation_rule"

    # The trigger layer produces no semantic cognition.
    assert not store.list_payloads(object_type=ObjectType.CLAIM)


def test_wake_signal_contract_has_no_semantic_conclusion_field() -> None:
    with pytest.raises(ValidationError):
        WakeSignalRequest.model_validate(
            {
                "wake_source": "mechanical_change",
                "rule_id": "activity.delta",
                "observed_at": NOW,
                "dedupe_key": "activity:user_1",
                "meaning": "用户今天情绪低落",
            }
        )


def test_wake_bus_retry_merge_and_cooldown_are_mechanical(tmp_path) -> None:
    store, index = _world(tmp_path)
    ref1 = _seed_observation(
        store,
        object_id="obs_c09_1",
        value={"steps": 1000},
        occurred_at=NOW,
    )
    ref2 = _seed_observation(
        store,
        object_id="obs_c09_2",
        value={"steps": 2600},
        occurred_at=NOW + timedelta(minutes=1),
    )
    bus = WakeBus(store=store, index=index)

    first_request = WakeSignalRequest(
        wake_source=WakeSource.MECHANICAL_CHANGE,
        rule_id="activity.delta",
        observed_at=NOW,
        evidence_refs=(ref1,),
        priority=40,
        dedupe_key="activity:user_1:window-a",
        cooldown_seconds=600,
        metadata={"mechanical_metric": "steps_delta"},
    )
    first = bus.emit(first_request)
    exact_retry = bus.emit(first_request)

    assert exact_retry.wake_id == first.wake_id
    assert exact_retry.revision == 1
    assert bus.current_wake(first.wake_id).hit_count == 1

    second = bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.MECHANICAL_CHANGE,
            rule_id="activity.delta",
            observed_at=NOW + timedelta(minutes=1),
            evidence_refs=(ref2,),
            priority=55,
            dedupe_key="activity:user_1:window-a",
            cooldown_seconds=600,
            metadata={"mechanical_metric": "steps_delta"},
        )
    )
    merged = bus.current_wake(first.wake_id)
    assert second.merged is True
    assert second.revision == 2
    assert merged.hit_count == 2
    assert merged.priority == 55
    assert merged.evidence_refs == [ref1, ref2]

    claimed = bus.claim(first.wake_id, started_at=NOW + timedelta(minutes=2))
    assert claimed.state == "running"
    completed = bus.complete(
        first.wake_id,
        completed_at=NOW + timedelta(minutes=2),
        termination_reason="silence",
        model_rounds=1,
        capability_names=(),
        delivery_allowed=False,
        step0_state="quiet",
    )
    assert completed.state == "completed"

    suppressed = bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.MECHANICAL_CHANGE,
            rule_id="activity.delta",
            observed_at=NOW + timedelta(minutes=3),
            evidence_refs=(ref2,),
            priority=55,
            dedupe_key="activity:user_1:window-a",
            cooldown_seconds=600,
            metadata={"mechanical_metric": "steps_delta"},
        )
    )
    assert suppressed.suppressed is True
    assert bus.current_wake(suppressed.wake_id).wake_state.value == "suppressed"


def test_step0_budget_block_queues_wake_then_resumes(tmp_path) -> None:
    store, index = _world(tmp_path)
    ref = _seed_observation(
        store,
        object_id="obs_c09_budget",
        value={"coverage_gap_seconds": 900},
        occurred_at=NOW,
    )
    bus = WakeBus(store=store, index=index)
    signal = bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.NO_UPDATE,
            rule_id="source.no_update",
            observed_at=NOW,
            evidence_refs=(ref,),
            dedupe_key="no-update:user_1:sensor-a",
        )
    )

    model_calls = 0

    def model(snapshot):
        nonlocal model_calls
        model_calls += 1
        assert snapshot.wake_reason == "no_update"
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
    )

    blocked = runtime.run_wake(
        wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
        now=NOW + timedelta(minutes=1),
        step0=Step0GateInput(
            budget_available=False,
            reasons=("background budget exhausted",),
        ),
    )
    assert blocked.runtime is None
    assert blocked.wake.state == "queued"
    assert model_calls == 0

    resumed = runtime.run_wake(
        wake_ref=blocked.wake_ref,
        now=NOW + timedelta(minutes=5),
    )
    assert resumed.runtime is not None
    assert resumed.runtime.silenced is True
    assert resumed.wake.state == "completed"
    assert model_calls == 1


def test_step0_quiet_runs_background_cognition_but_suppresses_delivery(tmp_path) -> None:
    store, index = _world(tmp_path)
    ref = _seed_observation(
        store,
        object_id="obs_c09_quiet",
        value={"state": "registered-watch-hit"},
        occurred_at=NOW,
    )
    signal = WakeBus(store=store, index=index).emit(
        WakeSignalRequest(
            wake_source=WakeSource.WATCH_MATCH,
            rule_id="watch.registered-condition",
            observed_at=NOW,
            evidence_refs=(ref,),
            dedupe_key="watch:user_1:test",
        )
    )

    def model(snapshot):
        assert snapshot.wake_reason == "watch_match"
        assert snapshot.cockpit["task_context"]["wake"]["step0"]["state"] == "quiet"
        return ModelDirective(response="后台判断完成，但此刻不应打扰用户。")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=signal.wake_id, revision=1),
        now=NOW + timedelta(seconds=10),
        step0=Step0GateInput(convenience_allowed=False),
    )

    assert result.runtime is not None
    assert result.runtime.response == "后台判断完成，但此刻不应打扰用户。"
    assert result.delivery_response is None
    assert result.delivery_suppressed is True
    assert result.wake.state == "completed"


def test_due_task_wake_dispatches_into_same_resident_runtime(tmp_path) -> None:
    store, index = _world(tmp_path)
    reason_ref = _seed_observation(
        store,
        object_id="obs_c09_task_reason",
        value="下周复核家庭情况，再决定是否恢复周三活动。",
        occurred_at=NOW,
    )

    latest_task = {"object_id": None, "revision": None}

    def model(snapshot):
        assert snapshot.wake_reason == "task_due"
        wake_context = snapshot.cockpit["task_context"]["wake"]
        assert wake_context["wake_source"] == "task_due"
        history = snapshot.capability_history

        if not history:
            source_task_ref = wake_context["evidence_refs"][0]
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="inspect_world_object",
                        arguments={"object_id": source_task_ref["object_id"]},
                    ),
                )
            )

        if len(history) == 1:
            current_task = history[-1].data
            latest_task["object_id"] = current_task["object_id"]
            latest_task["revision"] = current_task["revision"]
            assert current_task["task_state"] == "ready"
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="transition_task",
                        arguments={
                            "task_ref": {
                                "object_id": current_task["object_id"],
                                "revision": current_task["revision"],
                            },
                            "new_state": "waiting_user",
                            "reason": "到期后仍需向用户确认家庭情况是否稳定。",
                            "evidence_refs": [
                                {
                                    "object_id": reason_ref.object_id,
                                    "revision": reason_ref.revision,
                                }
                            ],
                            "next_step": "询问用户当前家庭恢复情况，再决定是否恢复周三活动。",
                        },
                    ),
                )
            )

        return ModelDirective(response="到复核时间了；需要先确认当前情况再决定恢复安排。")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
        max_tool_rounds=4,
    )
    task = runtime.execution_world.create_task(
        TaskCreateRequest(
            title="复核并恢复周三活动",
            task_type=TaskType.FOLLOW_UP,
            reason_refs=(reason_ref,),
            initial_state=TaskState.WAITING_TIME,
            priority=60,
            next_wake_at=NOW + timedelta(days=7),
            next_step="到期时确认家庭恢复是否稳定。",
        ),
        created_at=NOW,
    )

    before_conversation_count = len(
        [
            item
            for item in store.list_payloads(object_type=ObjectType.OBSERVATION)
            if item.get("source_kind") == "conversation"
        ]
    )

    due = runtime.execution_world.wake_due_tasks(now=NOW + timedelta(days=7, minutes=1))
    assert len(due) == 1
    assert due[0].task_id == task.task_id
    assert store.get_payload(task.task_id)["task_state"] == "ready"

    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=due[0].wake_id, revision=1),
        now=NOW + timedelta(days=7, minutes=2),
    )

    assert [item.name for item in result.runtime.capability_history] == [
        "inspect_world_object",
        "transition_task",
    ]
    assert result.delivery_response is not None
    assert result.wake.state == "completed"
    assert store.get_payload(task.task_id)["task_state"] == "waiting_user"
    assert latest_task["revision"] == 2

    after_conversation_count = len(
        [
            item
            for item in store.list_payloads(object_type=ObjectType.OBSERVATION)
            if item.get("source_kind") == "conversation"
        ]
    )
    assert after_conversation_count == before_conversation_count



def test_periodic_review_task_due_and_generic_wake_dispatch_form_one_loop(tmp_path) -> None:
    store, index = _world(tmp_path)
    note_ref = _seed_observation(
        store,
        object_id="obs_c09_cross_stage_note",
        value="如果情况继续稳定，下周再确认是否恢复周三固定活动。",
        occurred_at=NOW,
    )
    created_task = {"object_id": None}

    def model(snapshot):
        history = snapshot.capability_history

        if snapshot.wake_reason == "periodic_review":
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
                anchor = next(
                    item
                    for item in anchors
                    if item["object_ref"]["object_id"] == note_ref.object_id
                )
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="create_task",
                            arguments={
                                "title": "复核周三固定活动恢复条件",
                                "task_type": "follow_up",
                                "reason_refs": [anchor["object_ref"]],
                                "initial_state": "waiting_time",
                                "priority": 60,
                                "next_wake_at": (
                                    NOW + timedelta(days=7)
                                ).isoformat(),
                                "next_step": "到期后检查新世界证据，再决定是否询问用户。",
                            },
                        ),
                    )
                )
            created_task["object_id"] = history[-1].data["task_id"]
            return ModelDirective(response="已形成条件性后续复核任务。")

        if snapshot.wake_reason == "task_due":
            if not history:
                task_ref = snapshot.cockpit["task_context"]["wake"]["evidence_refs"][0]
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="inspect_world_object",
                            arguments={"object_id": task_ref["object_id"]},
                        ),
                    )
                )
            if len(history) == 1:
                current_task = history[-1].data
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="transition_task",
                            arguments={
                                "task_ref": {
                                    "object_id": current_task["object_id"],
                                    "revision": current_task["revision"],
                                },
                                "new_state": "waiting_user",
                                "reason": "到期后需要确认现实条件是否仍然稳定。",
                                "evidence_refs": [
                                    {
                                        "object_id": note_ref.object_id,
                                        "revision": note_ref.revision,
                                    }
                                ],
                                "next_step": "在合适时机询问用户当前情况。",
                            },
                        ),
                    )
                )
            return ModelDirective(response="条件性任务已到期，需要确认当前情况。")

        raise AssertionError(f"unexpected wake reason: {snapshot.wake_reason}")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
        max_tool_rounds=4,
    )

    review = runtime.run_periodic_review(
        now=NOW + timedelta(hours=1),
        policy=ReviewSchedulePolicy(
            interval_hours=24,
            lookback_hours=24,
            max_candidates=20,
            max_per_object_type=20,
        ),
    )
    assert review is not None
    assert review.wake.state == "completed"
    assert [item.name for item in review.runtime.capability_history] == [
        "read_periodic_review_anchors",
        "create_task",
    ]

    task_id = created_task["object_id"]
    assert isinstance(task_id, str)
    task_before_due = store.get_payload(task_id)
    assert task_before_due["task_state"] == "waiting_time"

    due = runtime.execution_world.wake_due_tasks(
        now=NOW + timedelta(days=7, minutes=1)
    )
    assert len(due) == 1
    assert due[0].task_id == task_id
    assert store.get_payload(task_id)["task_state"] == "ready"

    dispatched = runtime.run_wake(
        wake_ref=ObjectRef(object_id=due[0].wake_id, revision=1),
        now=NOW + timedelta(days=7, minutes=2),
    )
    assert [item.name for item in dispatched.runtime.capability_history] == [
        "inspect_world_object",
        "transition_task",
    ]
    assert dispatched.wake.state == "completed"
    assert store.get_payload(task_id)["task_state"] == "waiting_user"

    conversation_observations = [
        item
        for item in store.list_payloads(object_type=ObjectType.OBSERVATION)
        if item.get("source_kind") == "conversation"
    ]
    assert conversation_observations == []
