from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aios_core.contracts.enums import ObjectType, WakeSource
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.wake import ObservationWakeRule

from .core_target import CoreHabitationTarget, CoreHabitationTargetFactory
from .harness import HabitationRunner, HabitationScenario, LifeEvent, ResidentEvent


BASE = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)


def test_core_target_routes_conversation_and_reality_into_one_world(tmp_path) -> None:
    seen_wake_reasons: list[str] = []

    def model(snapshot):
        seen_wake_reasons.append(snapshot.wake_reason)
        if snapshot.wake_reason == "user_interaction":
            return ModelDirective(response="收到。")
        return ModelDirective(silence=True)

    target = CoreHabitationTarget(
        db_path=tmp_path / "world.db",
        subject_id="synthetic-user-001",
        model_id="provider/model-a",
        model_handler=model,
    )

    target.advance_to(BASE)
    conversation = target.handle_event(
        ResidentEvent(
            event_id="chat-1",
            occurred_at=BASE,
            channel="conversation",
            payload="下周要出差。",
            metadata={"session": "s1"},
        )
    )

    target.advance_to(BASE + timedelta(hours=1))
    calendar = target.handle_event(
        ResidentEvent(
            event_id="calendar-1",
            occurred_at=BASE + timedelta(hours=1),
            channel="calendar",
            payload={"title": "Seattle trip"},
            metadata={"source": "calendar"},
        )
    )

    target.advance_to(BASE + timedelta(hours=2))
    media = target.handle_event(
        ResidentEvent(
            event_id="photo-1",
            occurred_at=BASE + timedelta(hours=2),
            channel="photo_description",
            payload="机场候机区，人很多。",
            metadata={"source": "gallery_summary"},
        )
    )

    assert conversation["kind"] == "conversation"
    assert calendar["kind"] == "reality"
    assert media["kind"] == "media_descriptor"

    snapshot = target.audit_snapshot()
    assert snapshot["subject_id"] == "synthetic-user-001"
    assert snapshot["object_counts"][ObjectType.OBSERVATION.value] >= 4
    assert "hidden_oracle" not in str(snapshot)
    assert seen_wake_reasons == ["user_interaction"]


def test_virtual_clock_runs_task_due_wake_through_same_resident_runtime(tmp_path) -> None:
    created: dict[str, str] = {}

    def model(snapshot):
        history = snapshot.capability_history

        if snapshot.wake_reason == "user_interaction":
            if not history:
                reason_ref = snapshot.cockpit["task_context"][
                    "current_user_observation_ref"
                ]
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="create_task",
                            arguments={
                                "title": "两小时后复核",
                                "task_type": "follow_up",
                                "reason_refs": [reason_ref],
                                "initial_state": "waiting_time",
                                "priority": 60,
                                "next_wake_at": (
                                    BASE + timedelta(hours=2)
                                ).isoformat(),
                                "next_step": "到期后再次检查。",
                            },
                        ),
                    )
                )
            created["task_id"] = history[-1].data["task_id"]
            return ModelDirective(response="已建立后续复核。")

        if snapshot.wake_reason == "task_due":
            if not history:
                task_ref = snapshot.cockpit["task_context"]["wake"][
                    "evidence_refs"
                ][0]
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="inspect_world_object",
                            arguments={"object_id": task_ref["object_id"]},
                        ),
                    )
                )
            if len(history) == 1:
                task = history[-1].data
                return ModelDirective(
                    capability_calls=(
                        CapabilityCall(
                            name="transition_task",
                            arguments={
                                "task_ref": {
                                    "object_id": task["object_id"],
                                    "revision": task["revision"],
                                },
                                "new_state": "waiting_user",
                                "reason": "到期后需要用户补充现实状态。",
                                "evidence_refs": task["reason_refs"],
                                "next_step": "等待用户补充。",
                            },
                        ),
                    )
                )
            return ModelDirective(response="到复核时间了，需要补充当前情况。")

        return ModelDirective(silence=True)

    target = CoreHabitationTarget(
        db_path=tmp_path / "world.db",
        subject_id="synthetic-user-002",
        model_id="provider/model-a",
        model_handler=model,
    )

    target.advance_to(BASE)
    target.handle_event(
        ResidentEvent(
            event_id="chat-task",
            occurred_at=BASE,
            channel="conversation",
            payload="两个小时后提醒我再确认一次。",
            metadata={"session": "s1"},
        )
    )
    advanced = target.advance_to(BASE + timedelta(hours=3))

    assert created["task_id"]
    assert len(advanced["task_wakes"]) == 1
    dispatch = advanced["task_wakes"][0]["dispatch"]
    assert dispatch["wake_source"] == WakeSource.TASK_DUE.value
    assert dispatch["runtime"]["invoked"] is True
    assert dispatch["runtime"]["capability_names"] == [
        "inspect_world_object",
        "transition_task",
    ]

    task = target.store.get_payload(created["task_id"])
    assert task["task_state"] == "waiting_user"


def test_scenario_end_at_runs_periodic_review_after_last_visible_event(tmp_path) -> None:
    wake_reasons: list[str] = []

    def model(snapshot):
        wake_reasons.append(snapshot.wake_reason)
        if snapshot.wake_reason == "user_interaction":
            return ModelDirective(response="记录。")
        if snapshot.wake_reason == "periodic_review":
            return ModelDirective(silence=True)
        return ModelDirective(silence=True)

    scenario = HabitationScenario(
        scenario_id="final-horizon-review",
        subject_id="synthetic-user-003",
        events=(
            LifeEvent(
                event_id="chat-1",
                occurred_at=BASE,
                channel="conversation",
                payload="今天开始执行新安排。",
                metadata={"session": "s1"},
            ),
        ),
        end_at=BASE + timedelta(hours=25),
    )
    target = CoreHabitationTarget(
        db_path=tmp_path / "world.db",
        subject_id=scenario.subject_id,
        model_id="provider/model-a",
        model_handler=model,
    )

    run = HabitationRunner().run(
        scenario=scenario,
        model_id="provider/model-a",
        target=target,
    )

    assert run.final_time_advance_result is not None
    reviews = run.final_time_advance_result["periodic_reviews"]
    assert len(reviews) == 1
    assert reviews[0]["invoked"] is True
    assert wake_reasons == ["user_interaction", "periodic_review"]
    assert run.final_snapshot["clock"] == scenario.end_at.isoformat()


def test_numeric_mechanical_marker_can_trigger_c09_inside_habitation(tmp_path) -> None:
    wake_reasons: list[str] = []

    def model(snapshot):
        wake_reasons.append(snapshot.wake_reason)
        return ModelDirective(silence=True)

    rule = ObservationWakeRule(
        rule_id="heart-rate.numeric-change.registered",
        wake_source=WakeSource.MECHANICAL_CHANGE,
        source_kind="heart_rate",
        modality="numeric_change",
        metadata_equals={"mechanical_threshold_event": True},
        dedupe_metadata_keys=("adapter_id", "series_id"),
        priority=70,
        cooldown_seconds=300,
    )
    event_time = BASE + timedelta(minutes=2)
    target = CoreHabitationTarget(
        db_path=tmp_path / "world.db",
        subject_id="synthetic-user-004",
        model_id="provider/model-a",
        model_handler=model,
        observation_wake_rules=(rule,),
    )

    target.advance_to(event_time)
    result = target.handle_event(
        ResidentEvent(
            event_id="sensor-batch-1",
            occurred_at=event_time,
            channel="sensor_numeric",
            payload={
                "source_kind": "heart_rate",
                "dimension": "dim:heart_rate",
                "series_id": "hr-window-1",
                "unit": "bpm",
                "samples": [
                    {
                        "external_record_id": "hr-a",
                        "occurred_at": BASE.isoformat(),
                        "value": 80.0,
                    },
                    {
                        "external_record_id": "hr-b",
                        "occurred_at": (BASE + timedelta(minutes=1)).isoformat(),
                        "value": 110.0,
                    },
                ],
                "policy": {
                    "tolerance": 3.0,
                    "change_threshold": 15.0,
                    "max_gap_seconds": 120.0,
                },
            },
        )
    )

    assert result["kind"] == "numeric_series"
    assert len(result["change_observation_ids"]) == 1
    assert len(result["wake_activity"]) == 1
    dispatches = result["wake_activity"][0]["dispatches"]
    assert len(dispatches) == 1
    assert dispatches[0]["wake_source"] == "mechanical_change"
    assert dispatches[0]["runtime"]["invoked"] is True
    assert wake_reasons == ["mechanical_change"]

    claims = target.store.list_payloads(
        object_type=ObjectType.CLAIM,
        subject_id=target.subject_id,
    )
    assert claims == []


def test_core_target_factory_creates_private_world_per_model(tmp_path) -> None:
    def handler_factory(model_id: str):
        def model(snapshot):
            return ModelDirective(response=f"{model_id}:ok")
        return model

    factory = CoreHabitationTargetFactory(
        root_dir=tmp_path / "worlds",
        model_handler_factory=handler_factory,
    )
    descriptor = type(
        "Descriptor",
        (),
        {"subject_id": "synthetic-user-005"},
    )()

    first = factory(model_id="provider/model-a", scenario=descriptor)
    second = factory(model_id="provider/model-b", scenario=descriptor)

    assert first.isolation_key != second.isolation_key
    assert first.store.current_world_revision() == 0
    assert second.store.current_world_revision() == 0
