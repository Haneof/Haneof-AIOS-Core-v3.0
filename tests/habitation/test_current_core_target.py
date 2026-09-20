from datetime import datetime, timedelta, timezone

from aios_core.contracts.enums import SourceClass
from aios_core.ingest import SourceAdapterSpec
from aios_core.runtime.cognitive_runtime import ModelDirective

from .current_core import CurrentCoreHabitationTarget
from .harness import (
    HabitationRunner,
    HabitationScenario,
    LifeEvent,
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
