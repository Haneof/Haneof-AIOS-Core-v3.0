from datetime import datetime, timezone

from aios_core.runtime.cognitive_runtime import ModelDirective

from .aios_target import AIOSHabitationTargetFactory
from .harness import HabitationRunner, HabitationScenario, LifeEvent


def test_habitation_target_uses_real_core_surfaces_and_virtual_background_ticks(tmp_path):
    wake_reasons: list[str] = []

    def model_factory(_model_id):
        def model(snapshot):
            wake_reasons.append(snapshot.wake_reason)
            return ModelDirective(silence=True)
        return model

    scenario = HabitationScenario(
        scenario_id="opaque-evaluator-only-id",
        subject_id="resident-user-1",
        events=(
            LifeEvent(
                event_id="e1",
                occurred_at=datetime(2026, 1, 1, 9, tzinfo=timezone.utc),
                channel="conversation",
                payload="下周要处理一件重要的项目事情。",
                metadata={"session": "s1"},
                hidden_oracle={"meaning": "must never reach resident"},
            ),
            LifeEvent(
                event_id="e2",
                occurred_at=datetime(2026, 1, 3, 12, tzinfo=timezone.utc),
                channel="calendar",
                payload={"title": "项目节点", "duration_minutes": 30},
                metadata={"source": "calendar"},
            ),
        ),
        hidden_oracle={"latent": "evaluator only"},
    )

    factory = AIOSHabitationTargetFactory(
        root=tmp_path / "worlds",
        model_handler_factory=model_factory,
    )
    result = HabitationRunner().run_model_factories(
        scenario=scenario,
        factories={"resident-model-a": factory},
    )
    run = result.runs["resident-model-a"]

    assert len(run.steps) == 2
    assert run.steps[0].response["kind"] == "conversation"
    assert run.steps[1].response["kind"] == "reality_ingest"

    objects = run.final_snapshot["current_objects"]
    observations = [
        item for item in objects
        if item.get("object_type") == "observation"
    ]
    assert any(item.get("value") == "下周要处理一件重要的项目事情。" for item in observations)
    assert any(
        isinstance(item.get("value"), dict)
        and item["value"].get("title") == "项目节点"
        for item in observations
    )

    # The two-day gap is not skipped. P15 gets a background review opportunity
    # even though no resident-visible event occurred on Jan 2.
    assert "periodic_review" in wake_reasons
    assert "user_interaction" in wake_reasons

    # The hidden oracle never enters the AIOS world.
    serialized = repr(run.final_snapshot)
    assert "must never reach resident" not in serialized
    assert "evaluator only" not in serialized


def test_factory_gives_each_model_a_private_world(tmp_path):
    def model_factory(_model_id):
        return lambda _snapshot: ModelDirective(silence=True)

    factory = AIOSHabitationTargetFactory(
        root=tmp_path / "worlds",
        model_handler_factory=model_factory,
    )
    descriptor = type("Descriptor", (), {"subject_id": "resident-user-1"})()

    a = factory(model_id="model-a", scenario=descriptor)
    b = factory(model_id="model-b", scenario=descriptor)

    assert a is not b
    assert a.isolation_key != b.isolation_key
    assert a.store.current_world_revision() == 0
    assert b.store.current_world_revision() == 0
