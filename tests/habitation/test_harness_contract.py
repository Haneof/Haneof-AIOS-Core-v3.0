from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from .harness import (
    HabitationRunner,
    HabitationScenario,
    LifeEvent,
    ResidentEvent,
    evaluate_run,
    scenario_channels,
    visible_events,
)


BASE = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)


class RecordingTarget:
    def __init__(self, label: str, *, isolation_key: str | None = None) -> None:
        self.label = label
        self._isolation_key = isolation_key or f"world:{label}:{id(self)}"
        self.events: list[ResidentEvent] = []

    @property
    def isolation_key(self) -> str:
        return self._isolation_key

    def handle_event(self, event: ResidentEvent):
        self.events.append(event)
        return {
            "model": self.label,
            "event_id": event.event_id,
            "free_form_response": f"{self.label} observed {event.channel}",
        }


class OracleAwareEvaluator:
    def evaluate(self, *, scenario, run):
        return {
            "model_id": run.model_id,
            "latent_change": scenario.hidden_oracle["latent_change"],
            "event_truth": scenario.events[0].hidden_oracle["truth"],
            "delivered_count": run.delivered_count,
        }


def _scenario() -> HabitationScenario:
    return HabitationScenario(
        scenario_id="hidden-life-001",
        subject_id="user_1",
        hidden_oracle={
            "latent_change": "the user's study confidence improves over several weeks"
        },
        events=(
            LifeEvent(
                event_id="day-01-conversation",
                occurred_at=BASE,
                channel="conversation",
                payload="今天这道题我还是需要你带着我做。",
                metadata={"session": "s1"},
                hidden_oracle={"truth": "low_initial_independence"},
            ),
            LifeEvent(
                event_id="day-07-calendar",
                occurred_at=BASE + timedelta(days=7),
                channel="calendar",
                payload={"title": "独立复习", "duration_minutes": 90},
                metadata={"source": "calendar"},
                hidden_oracle={"importance": "supports longitudinal pattern"},
            ),
            LifeEvent(
                event_id="day-21-private-oracle-only",
                occurred_at=BASE + timedelta(days=21),
                channel="oracle",
                payload="not delivered",
                hidden_oracle={"truth": "external evaluator-only evidence"},
                deliver_to_resident=False,
            ),
        ),
    )


def test_hidden_oracle_never_enters_resident_event() -> None:
    scenario = _scenario()
    target = RecordingTarget("model-a")

    run = HabitationRunner().run(
        scenario=scenario,
        model_id="vendor/model-a",
        target=target,
    )

    assert run.delivered_count == 2
    assert len(run.steps) == 2
    assert len(target.events) == 2
    assert all(step.delivered for step in run.steps)
    assert all(not hasattr(event, "hidden_oracle") for event in target.events)
    assert target.events[0].metadata == {"session": "s1"}
    assert "truth" not in target.events[0].metadata
    assert "day-21-private-oracle-only" not in {step.event_id for step in run.steps}


def test_runner_does_not_require_a_fixed_expected_answer() -> None:
    scenario = _scenario()

    class FreeFormTarget:
        isolation_key = "world:free-form"

        def handle_event(self, event: ResidentEvent):
            if event.channel == "conversation":
                return "I may need more evidence before changing my understanding."
            return {"tool_calls": [], "notes": ["calendar event stored"]}

    run = HabitationRunner().run(
        scenario=scenario,
        model_id="vendor/free-form-model",
        target=FreeFormTarget(),
    )

    assert run.delivered_count == 2
    assert run.steps[0].response.startswith("I may need more evidence")
    assert isinstance(run.steps[1].response, dict)


def test_different_models_run_independently_without_shared_state() -> None:
    scenario = _scenario()
    runner = HabitationRunner()
    target_a = RecordingTarget("model-a")
    target_b = RecordingTarget("model-b")

    result = runner.run_models(
        scenario=scenario,
        targets={
            "vendor/model-a": target_a,
            "other/model-b": target_b,
        },
    )

    assert set(result.runs) == {"vendor/model-a", "other/model-b"}
    assert result.runs["vendor/model-a"].steps[0].response["model"] == "model-a"
    assert result.runs["other/model-b"].steps[0].response["model"] == "model-b"
    assert target_a.events is not target_b.events

    shared = RecordingTarget("shared")
    with pytest.raises(ValueError, match="independent AIOS target instance"):
        runner.run_models(
            scenario=scenario,
            targets={
                "vendor/model-a": shared,
                "other/model-b": shared,
            },
        )


def test_no_inter_model_communication_channel_exists_in_runner() -> None:
    scenario = _scenario()
    target_a = RecordingTarget("a")
    target_b = RecordingTarget("b")

    result = HabitationRunner().run_models(
        scenario=scenario,
        targets={"a": target_a, "b": target_b},
    )

    assert result.runs["a"].model_id == "a"
    assert result.runs["b"].model_id == "b"
    assert target_a.events == target_b.events
    assert all(step.response["model"] == "a" for step in result.runs["a"].steps if step.delivered)
    assert all(step.response["model"] == "b" for step in result.runs["b"].steps if step.delivered)


def test_evaluator_gets_oracle_only_after_model_run() -> None:
    scenario = _scenario()
    target = RecordingTarget("resident-model")

    run = HabitationRunner().run(
        scenario=scenario,
        model_id="vendor/resident-model",
        target=target,
    )
    report = evaluate_run(
        evaluator=OracleAwareEvaluator(),
        scenario=scenario,
        run=run,
    )

    assert report["model_id"] == "vendor/resident-model"
    assert report["latent_change"].startswith("the user's study confidence")
    assert report["event_truth"] == "low_initial_independence"
    assert report["delivered_count"] == 2


def test_scenario_rejects_time_travel_and_duplicate_event_ids() -> None:
    later = LifeEvent(
        event_id="same",
        occurred_at=BASE + timedelta(days=2),
        channel="conversation",
        payload="later",
    )
    earlier = LifeEvent(
        event_id="earlier",
        occurred_at=BASE,
        channel="conversation",
        payload="earlier",
    )
    duplicate = LifeEvent(
        event_id="same",
        occurred_at=BASE + timedelta(days=3),
        channel="conversation",
        payload="duplicate",
    )

    with pytest.raises(ValueError, match="chronological"):
        HabitationScenario(
            scenario_id="bad-time",
            subject_id="u",
            events=(later, earlier),
        )

    with pytest.raises(ValueError, match="duplicate event_id"):
        HabitationScenario(
            scenario_id="bad-id",
            subject_id="u",
            events=(later, duplicate),
        )


def test_visible_projection_and_channel_report_cannot_leak_oracle() -> None:
    scenario = _scenario()

    projected = visible_events(scenario)

    assert [event.event_id for event in projected] == [
        "day-01-conversation",
        "day-07-calendar",
    ]
    assert scenario_channels(scenario) == ("conversation", "calendar")
    assert all(not hasattr(event, "hidden_oracle") for event in projected)


def test_factory_path_creates_fresh_world_per_model_candidate() -> None:
    scenario = _scenario()
    created: list[RecordingTarget] = []

    descriptors = []

    class Factory:
        def __call__(self, *, model_id: str, scenario):
            descriptors.append(scenario)
            target = RecordingTarget(model_id)
            created.append(target)
            return target

    result = HabitationRunner().run_model_factories(
        scenario=scenario,
        factories={
            "provider/model-a": Factory(),
            "provider/model-b": Factory(),
            "provider/model-c": Factory(),
        },
    )

    assert len(created) == 3
    assert all(not hasattr(item, "hidden_oracle") for item in descriptors)
    assert all(not hasattr(item, "scenario_id") for item in descriptors)
    assert all(not hasattr(item, "scenario_version") for item in descriptors)
    assert all(item.visible_event_count == 2 for item in descriptors)
    assert len({id(target) for target in created}) == 3
    assert set(result.runs) == {
        "provider/model-a",
        "provider/model-b",
        "provider/model-c",
    }
    assert all(run.delivered_count == 2 for run in result.runs.values())


def test_factory_path_rejects_factory_that_reuses_one_world() -> None:
    scenario = _scenario()
    shared = RecordingTarget("shared")

    class BadFactory:
        def __call__(self, *, model_id: str, scenario):
            return shared

    with pytest.raises(ValueError, match="independent AIOS target instance"):
        HabitationRunner().run_model_factories(
            scenario=scenario,
            factories={
                "provider/model-a": BadFactory(),
                "provider/model-b": BadFactory(),
            },
        )


def test_distinct_target_wrappers_cannot_share_one_world_store_identity() -> None:
    scenario = _scenario()
    first = RecordingTarget("a", isolation_key="sqlite:/tmp/shared-world.db")
    second = RecordingTarget("b", isolation_key="sqlite:/tmp/shared-world.db")

    with pytest.raises(ValueError, match="independent AIOS world/store"):
        HabitationRunner().run_models(
            scenario=scenario,
            targets={
                "provider/model-a": first,
                "provider/model-b": second,
            },
        )


def test_one_models_payload_mutation_cannot_change_later_models_life() -> None:
    scenario = HabitationScenario(
        scenario_id="mutation-isolation",
        subject_id="u",
        events=(
            LifeEvent(
                event_id="e1",
                occurred_at=BASE,
                channel="app",
                payload={"items": ["original"]},
                metadata={"nested": {"value": 1}},
            ),
        ),
    )

    class MutatingTarget(RecordingTarget):
        def handle_event(self, event: ResidentEvent):
            event.payload["items"].append("mutated")
            event.metadata["nested"]["value"] = 999
            return {"seen": event.payload}

    first = MutatingTarget("mutator")
    second = RecordingTarget("observer")

    result = HabitationRunner().run_models(
        scenario=scenario,
        targets={"model-a": first, "model-b": second},
    )

    assert result.runs["model-a"].steps[0].response["seen"]["items"] == [
        "original",
        "mutated",
    ]
    assert second.events[0].payload == {"items": ["original"]}
    assert second.events[0].metadata == {"nested": {"value": 1}}
    assert scenario.events[0].payload == {"items": ["original"]}
    assert scenario.events[0].metadata == {"nested": {"value": 1}}


def test_run_snapshots_mutable_target_response() -> None:
    scenario = _scenario()

    class ReusingResponseTarget(RecordingTarget):
        def __init__(self):
            super().__init__("snapshot")
            self.shared_response = {"values": []}

        def handle_event(self, event: ResidentEvent):
            self.shared_response["values"].append(event.event_id)
            return self.shared_response

    target = ReusingResponseTarget()
    run = HabitationRunner().run(
        scenario=scenario,
        model_id="snapshot-model",
        target=target,
    )

    assert run.steps[0].response["values"] == ["day-01-conversation"]
    assert run.steps[1].response["values"] == [
        "day-01-conversation",
        "day-07-calendar",
    ]


def test_direct_contracts_reject_type_coercion() -> None:
    with pytest.raises(ValueError, match="deliver_to_resident must be a boolean"):
        LifeEvent(
            event_id="e",
            occurred_at=BASE,
            channel="x",
            payload="x",
            deliver_to_resident="false",  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="seed must be an integer"):
        HabitationScenario(
            scenario_id="s",
            subject_id="u",
            events=(
                LifeEvent(
                    event_id="e",
                    occurred_at=BASE,
                    channel="x",
                    payload="x",
                ),
            ),
            seed=True,  # type: ignore[arg-type]
        )


def test_target_isolation_key_must_be_explicit_string() -> None:
    scenario = _scenario()

    class BadTarget(RecordingTarget):
        @property
        def isolation_key(self):
            return None

    with pytest.raises(ValueError, match="isolation_key must be a non-empty string"):
        HabitationRunner().run_models(
            scenario=scenario,
            targets={"model": BadTarget("bad")},
        )


def test_factory_does_not_receive_invalid_model_id() -> None:
    scenario = _scenario()
    called = False

    class Factory:
        def __call__(self, *, model_id: str, scenario):
            nonlocal called
            called = True
            return RecordingTarget("should-not-run")

    with pytest.raises(ValueError, match="model_id must be a non-empty string"):
        HabitationRunner().run_model_factories(
            scenario=scenario,
            factories={"": Factory()},
        )

    assert called is False


def test_scenario_requires_tuple_and_at_least_one_visible_event() -> None:
    visible = LifeEvent(
        event_id="visible",
        occurred_at=BASE,
        channel="conversation",
        payload="x",
    )
    hidden = LifeEvent(
        event_id="hidden",
        occurred_at=BASE,
        channel="oracle",
        payload="secret",
        deliver_to_resident=False,
    )

    with pytest.raises(ValueError, match="events must be a non-empty tuple"):
        HabitationScenario(
            scenario_id="list-events",
            subject_id="u",
            events=[visible],  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="at least one resident-visible event"):
        HabitationScenario(
            scenario_id="hidden-only",
            subject_id="u",
            events=(hidden,),
        )


def test_event_time_must_be_datetime_not_string() -> None:
    with pytest.raises(ValueError, match="occurred_at must be a datetime"):
        LifeEvent(
            event_id="e",
            occurred_at="2026-09-20T08:00:00Z",  # type: ignore[arg-type]
            channel="x",
            payload="x",
        )
