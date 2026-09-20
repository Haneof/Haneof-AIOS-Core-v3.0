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
    def __init__(self, label: str) -> None:
        self.label = label
        self.events: list[ResidentEvent] = []

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
    assert len(target.events) == 2
    assert all(not hasattr(event, "hidden_oracle") for event in target.events)
    assert target.events[0].metadata == {"session": "s1"}
    assert "truth" not in target.events[0].metadata
    assert run.steps[-1].delivered is False
    assert run.steps[-1].response is None


def test_runner_does_not_require_a_fixed_expected_answer() -> None:
    scenario = _scenario()

    class FreeFormTarget:
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
    assert scenario_channels(scenario) == ("conversation", "calendar", "oracle")
    assert all(not hasattr(event, "hidden_oracle") for event in projected)


def test_factory_path_creates_fresh_world_per_model_candidate() -> None:
    scenario = _scenario()
    created: list[RecordingTarget] = []

    class Factory:
        def __call__(self, *, model_id: str, scenario: HabitationScenario):
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
        def __call__(self, *, model_id: str, scenario: HabitationScenario):
            return shared

    with pytest.raises(ValueError, match="independent AIOS target instance"):
        HabitationRunner().run_model_factories(
            scenario=scenario,
            factories={
                "provider/model-a": BadFactory(),
                "provider/model-b": BadFactory(),
            },
        )
