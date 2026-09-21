from datetime import datetime, timedelta, timezone

from aios_core.contracts.enums import ObjectType, SourceClass, WakeSource
from aios_core.ingest import SourceAdapterSpec
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.wake import ObservationWakeRule

from .current_core import (
    CurrentCoreHabitationTarget,
    CurrentCoreHabitationTargetFactory,
)
from .harness import (
    HabitationRunner,
    HabitationScenario,
    LifeEvent,
    ResidentScenarioDescriptor,
)


NOW = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)


def _silent_model(_snapshot):
    return ModelDirective(silence=True)


def _target(tmp_path, name: str):
    return CurrentCoreHabitationTarget(
        model_id=name,
        subject_id="synthetic-user-1",
        db_path=tmp_path / f"{name}.sqlite",
        model_handler=_silent_model,
        source_specs={
            "calendar": SourceAdapterSpec(
                adapter_id="habitation.calendar.v1",
                source_kind="calendar",
                dimension="dim:calendar",
                source_class=SourceClass.USER,
                default_modality="structured_record",
            )
        },
    )


def test_current_core_target_ingests_visible_life_into_private_world(tmp_path):
    scenario = HabitationScenario(
        scenario_id="plumbing-only",
        subject_id="synthetic-user-1",
        events=(
            LifeEvent(
                event_id="chat-1",
                occurred_at=NOW,
                channel="conversation",
                payload="明天要去出差。",
                metadata={"session": "s1"},
            ),
            LifeEvent(
                event_id="calendar-1",
                occurred_at=NOW + timedelta(hours=1),
                channel="calendar",
                payload={"title": "出差", "city": "Seattle"},
            ),
        ),
    )
    target = _target(tmp_path, "model-a")
    run = HabitationRunner().run(
        scenario=scenario,
        model_id="model-a",
        target=target,
    )

    assert run.delivered_count == 2
    assert run.steps[0].response["kind"] == "conversation"
    assert run.steps[0].response["silenced"] is True
    assert run.steps[1].response["kind"] == "reality"

    snapshot = run.final_snapshot
    assert snapshot["world_revision"] > 0
    assert snapshot["object_counts"]["observation"] >= 3
    assert all(
        item["subject_id"] == "synthetic-user-1"
        for item in snapshot["objects"]
    )


def test_current_core_targets_are_real_world_isolated(tmp_path):
    scenario = HabitationScenario(
        scenario_id="isolation",
        subject_id="synthetic-user-1",
        events=(
            LifeEvent(
                event_id="chat-1",
                occurred_at=NOW,
                channel="conversation",
                payload="只让各模型独立看到同一段人生。",
                metadata={"session": "s1"},
            ),
        ),
    )
    a = _target(tmp_path, "model-a")
    b = _target(tmp_path, "model-b")

    result = HabitationRunner().run_models(
        scenario=scenario,
        targets={"model-a": a, "model-b": b},
    )

    assert a.isolation_key != b.isolation_key
    assert result.runs["model-a"].final_snapshot["world_revision"] > 0
    assert result.runs["model-b"].final_snapshot["world_revision"] > 0

    a_ids = {
        item["object_id"]
        for item in result.runs["model-a"].final_snapshot["objects"]
    }
    b_ids = {
        item["object_id"]
        for item in result.runs["model-b"].final_snapshot["objects"]
    }
    # Same synthetic user/life yields the same canonical fact IDs, but the stores
    # are private and mutations never cross between them.
    assert a_ids == b_ids

    a.runtime.ai_world.commit
    # Prove isolation by writing only to A after both runs.
    from aios_core.contracts.refs import ObjectRef
    from aios_core.ai_world import (
        AIWorldClaimRequest,
        AIWorldDomain,
    )
    first_obs = next(
        item for item in result.runs["model-a"].final_snapshot["objects"]
        if item["object_type"] == "observation"
    )
    a.runtime.ai_world.commit(
        AIWorldClaimRequest(
            domain=AIWorldDomain.USER_UNDERSTANDING,
            statement="仅用于验证私有世界隔离，不是认知能力测试。",
            evidence_refs=(
                ObjectRef(
                    object_id=first_obs["object_id"],
                    revision=first_obs["revision"],
                ),
            ),
            confidence=0.5,
            scope_key="p16.isolation_test",
        ),
        learned_at=NOW + timedelta(minutes=1),
    )
    assert any(
        item["object_type"] == "claim"
        for item in a.audit_snapshot()["objects"]
    )
    assert not any(
        item["object_type"] == "claim"
        for item in b.audit_snapshot()["objects"]
    )


def test_current_core_target_rejects_delivery_before_clock_advance(tmp_path):
    target = _target(tmp_path, "model-a")
    event = LifeEvent(
        event_id="chat-1",
        occurred_at=NOW,
        channel="conversation",
        payload="test",
    ).resident_view()

    import pytest

    with pytest.raises(ValueError, match="advance virtual clock"):
        target.handle_event(event)



def test_virtual_clock_dispatches_due_task_through_c09(tmp_path):
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
                                    NOW + timedelta(hours=2)
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

    target = CurrentCoreHabitationTarget(
        model_id="model-task",
        subject_id="synthetic-user-task",
        db_path=tmp_path / "task.sqlite",
        model_handler=model,
    )
    target.advance_to(NOW)
    target.handle_event(
        LifeEvent(
            event_id="task-chat",
            occurred_at=NOW,
            channel="conversation",
            payload="两个小时后再确认一次。",
            metadata={"session": "s1"},
        ).resident_view()
    )

    advanced = target.advance_to(NOW + timedelta(hours=3))

    assert created["task_id"]
    task_cycles = advanced["task_cycles"]
    assert task_cycles
    dispatches = [
        wake_run
        for cycle in task_cycles
        for wake_run in cycle["wake_runs"]
        if wake_run["wake_source"] == WakeSource.TASK_DUE.value
    ]
    assert len(dispatches) == 1
    assert dispatches[0]["runtime"]["capabilities"] == [
        "inspect_world_object",
        "transition_task",
    ]
    assert target.store.get_payload(created["task_id"])["task_state"] == "waiting_user"


def test_end_at_advances_past_last_event_and_runs_periodic_review(tmp_path):
    wake_reasons: list[str] = []

    def model(snapshot):
        wake_reasons.append(snapshot.wake_reason)
        if snapshot.wake_reason == "user_interaction":
            return ModelDirective(response="记录。")
        return ModelDirective(silence=True)

    scenario = HabitationScenario(
        scenario_id="final-horizon",
        subject_id="synthetic-user-review",
        events=(
            LifeEvent(
                event_id="chat-1",
                occurred_at=NOW,
                channel="conversation",
                payload="今天开始执行新安排。",
                metadata={"session": "s1"},
            ),
        ),
        end_at=NOW + timedelta(hours=25),
    )
    target = CurrentCoreHabitationTarget(
        model_id="model-review",
        subject_id=scenario.subject_id,
        db_path=tmp_path / "review.sqlite",
        model_handler=model,
    )

    run = HabitationRunner().run(
        scenario=scenario,
        model_id="model-review",
        target=target,
    )

    assert run.final_time_advance_result is not None
    reviews = run.final_time_advance_result["periodic_reviews"]
    assert len(reviews) == 1
    assert reviews[0]["invoked"] is True
    assert wake_reasons == ["user_interaction", "periodic_review"]
    assert run.final_snapshot["clock"] == scenario.end_at.isoformat()


def test_sensor_numeric_path_generates_registered_mechanical_wake(tmp_path):
    reasons: list[str] = []

    def model(snapshot):
        reasons.append(snapshot.wake_reason)
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
    event_time = NOW + timedelta(minutes=2)
    target = CurrentCoreHabitationTarget(
        model_id="model-sensor",
        subject_id="synthetic-user-sensor",
        db_path=tmp_path / "sensor.sqlite",
        model_handler=model,
        observation_wake_rules=(rule,),
    )

    target.advance_to(event_time)
    result = target.handle_event(
        LifeEvent(
            event_id="sensor-batch",
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
                        "occurred_at": NOW.isoformat(),
                        "value": 80.0,
                    },
                    {
                        "external_record_id": "hr-b",
                        "occurred_at": (
                            NOW + timedelta(minutes=1)
                        ).isoformat(),
                        "value": 110.0,
                    },
                ],
                "policy": {
                    "tolerance": 3.0,
                    "change_threshold": 15.0,
                    "max_gap_seconds": 120.0,
                },
            },
        ).resident_view()
    )

    assert result["kind"] == "numeric_series"
    assert len(result["change_observation_ids"]) == 1
    mechanical = [
        item
        for item in result["wake_runs"]
        if item["wake_source"] == WakeSource.MECHANICAL_CHANGE.value
    ]
    assert len(mechanical) == 1
    assert mechanical[0]["runtime"]["invoked"] is True
    assert reasons == ["mechanical_change"]
    assert target.store.list_payloads(
        object_type=ObjectType.CLAIM,
        subject_id=target.subject_id,
    ) == []


def test_sensor_numeric_rejects_future_sample_leak(tmp_path):
    target = CurrentCoreHabitationTarget(
        model_id="model-future-sensor",
        subject_id="synthetic-user-future-sensor",
        db_path=tmp_path / "future-sensor.sqlite",
        model_handler=_silent_model,
    )
    event_time = NOW + timedelta(minutes=2)
    target.advance_to(event_time)

    import pytest

    with pytest.raises(ValueError, match="future samples would leak future information"):
        target.handle_event(
            LifeEvent(
                event_id="future-sensor-batch",
                occurred_at=event_time,
                channel="sensor_numeric",
                payload={
                    "source_kind": "heart_rate",
                    "dimension": "dim:heart_rate",
                    "series_id": "future-window",
                    "samples": [
                        {
                            "external_record_id": "future",
                            "occurred_at": (
                                event_time + timedelta(minutes=1)
                            ).isoformat(),
                            "value": 100.0,
                        }
                    ],
                    "policy": {
                        "tolerance": 3.0,
                        "change_threshold": 15.0,
                        "max_gap_seconds": 120.0,
                    },
                },
            ).resident_view()
        )


def test_photo_description_uses_media_descriptor_boundary(tmp_path):
    target = _target(tmp_path, "model-photo")
    at = NOW + timedelta(minutes=5)
    target.advance_to(at)
    result = target.handle_event(
        LifeEvent(
            event_id="photo-1",
            occurred_at=at,
            channel="photo_description",
            payload="公园里和朋友喝咖啡。",
            metadata={"source": "gallery_summary"},
        ).resident_view()
    )

    assert result["kind"] == "media_descriptor"
    ref = result["observation_refs"][0]
    payload = target.store.get_payload(
        ref["object_id"],
        revision=ref["revision"],
    )
    assert payload["modality"] == "image_caption"
    assert payload["metadata"]["provenance"]["raw_media_retained"] is False


def test_current_core_factory_creates_fresh_private_worlds(tmp_path):
    def handler_factory(model_id: str):
        def model(_snapshot):
            return ModelDirective(response=f"{model_id}:ok")
        return model

    factory = CurrentCoreHabitationTargetFactory(
        root_dir=tmp_path / "worlds",
        model_handler_factory=handler_factory,
    )
    descriptor = ResidentScenarioDescriptor(subject_id="synthetic-user-factory")
    first = factory(model_id="provider/model-a", scenario=descriptor)
    second = factory(model_id="provider/model-b", scenario=descriptor)

    assert first.isolation_key != second.isolation_key
    assert first.store.current_world_revision() == 0
    assert second.store.current_world_revision() == 0


def test_current_core_can_resume_same_world_with_replacement_model(tmp_path):
    db_path = tmp_path / "resume-world.sqlite"

    first = CurrentCoreHabitationTarget(
        model_id="provider/model-a",
        subject_id="synthetic-user-resume",
        db_path=db_path,
        model_handler=lambda snapshot: ModelDirective(response="model-a response"),
    )
    first.advance_to(NOW)
    first_result = first.handle_event(
        LifeEvent(
            event_id="resume-chat-1",
            occurred_at=NOW,
            channel="conversation",
            payload="第一天先记录这个安排。",
            metadata={"session": "same-session"},
        ).resident_view()
    )
    assert first_result["turn_index"] == 1
    assert first_result["response"] == "model-a response"

    wake_reasons: list[str] = []

    def replacement_model(snapshot):
        wake_reasons.append(snapshot.wake_reason)
        if snapshot.wake_reason == "periodic_review":
            return ModelDirective(silence=True)
        return ModelDirective(response="model-b continued from world")

    resumed = CurrentCoreHabitationTarget(
        model_id="provider/model-b",
        subject_id="synthetic-user-resume",
        db_path=db_path,
        model_handler=replacement_model,
        require_fresh=False,
    )

    restored = resumed.audit_snapshot()
    assert restored["resumed_from_world"] is True
    assert restored["session_turns"] == {"same-session": 1}
    assert restored["clock"] == NOW.isoformat()

    advanced = resumed.advance_to(NOW + timedelta(hours=25))
    assert len(advanced["periodic_reviews"]) == 1
    assert advanced["periodic_reviews"][0]["invoked"] is True
    assert "periodic_review" in wake_reasons

    second_result = resumed.handle_event(
        LifeEvent(
            event_id="resume-chat-2",
            occurred_at=NOW + timedelta(hours=25),
            channel="conversation",
            payload="继续昨天的安排。",
            metadata={"session": "same-session"},
        ).resident_view()
    )
    assert second_result["turn_index"] == 2
    assert second_result["response"] == "model-b continued from world"

    final = resumed.audit_snapshot()
    assert final["model_id"] == "provider/model-b"
    assert final["session_turns"] == {"same-session": 2}
    conversation_observations = [
        item
        for item in final["objects"]
        if item.get("object_type") == ObjectType.OBSERVATION.value
        and item.get("source_kind") == "user_ai_interaction"
    ]
    assert len(conversation_observations) == 4


def test_habitation_self_contained_demonstrative_does_not_import_old_session(tmp_path):
    checked = {"current": False}

    def model(snapshot):
        if "深蓝色" in snapshot.user_input:
            topic = snapshot.cockpit["task_context"]["topic_state"]
            assert topic["antecedent_recall_needed"] is False
            assert topic["history_may_help"] is False
            assert snapshot.cockpit["memory_cards"] == ()
            checked["current"] = True
        return ModelDirective(response="ok")

    scenario = HabitationScenario(
        scenario_id="t33-self-contained-recall-gate",
        subject_id="synthetic-user-t33",
        events=(
            LifeEvent(
                event_id="old-chat",
                occurred_at=NOW,
                channel="conversation",
                payload="我以前比较过红色和绿色的包装。",
                metadata={"session": "old"},
            ),
            LifeEvent(
                event_id="current-chat",
                occurred_at=NOW + timedelta(hours=1),
                channel="conversation",
                payload="我喜欢这个颜色：深蓝色。请把它作为当前偏好记录。",
                metadata={"session": "new"},
            ),
        ),
    )
    target = CurrentCoreHabitationTarget(
        model_id="model-t33",
        subject_id=scenario.subject_id,
        db_path=tmp_path / "t33.sqlite",
        model_handler=model,
    )

    run = HabitationRunner().run(
        scenario=scenario,
        model_id="model-t33",
        target=target,
    )

    assert run.delivered_count == 2
    assert checked["current"] is True
