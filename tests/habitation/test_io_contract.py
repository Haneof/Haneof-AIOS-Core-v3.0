from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest

from .harness import HabitationRunner, HabitationScenario, LifeEvent, ResidentEvent
from .io import (
    comparison_manifest,
    load_events_jsonl,
    load_scenario_json,
    run_artifact,
    run_artifact_json,
    scenario_public_fingerprint,
)


BASE = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)


class EchoTarget:
    def __init__(self, model: str) -> None:
        self.model = model

    def handle_event(self, event: ResidentEvent):
        return {
            "model": self.model,
            "observed_event": event.event_id,
            "channel": event.channel,
        }


def _scenario(*, hidden_label: str = "secret-a", visible_text: str = "今天开始复习") -> HabitationScenario:
    return HabitationScenario(
        scenario_id="life-io-001",
        scenario_version="3",
        seed=20260920,
        subject_id="user_1",
        hidden_oracle={"latent_truth": hidden_label},
        events=(
            LifeEvent(
                event_id="e1",
                occurred_at=BASE,
                channel="conversation",
                payload=visible_text,
                metadata={"session": "morning"},
                hidden_oracle={"meaning": hidden_label},
            ),
            LifeEvent(
                event_id="e2",
                occurred_at=BASE + timedelta(days=1),
                channel="calendar",
                payload={"title": "复习"},
            ),
            LifeEvent(
                event_id="oracle-only",
                occurred_at=BASE + timedelta(days=2),
                channel="oracle",
                payload="evaluator-only",
                hidden_oracle={"secret": hidden_label},
                deliver_to_resident=False,
            ),
        ),
    )


def test_public_fingerprint_is_stable_and_ignores_hidden_oracle() -> None:
    first = _scenario(hidden_label="secret-a")
    second = _scenario(hidden_label="secret-b")

    assert scenario_public_fingerprint(first) == scenario_public_fingerprint(second)

    changed_visible = _scenario(hidden_label="secret-a", visible_text="今天不复习")
    assert scenario_public_fingerprint(first) != scenario_public_fingerprint(changed_visible)


def test_per_model_artifact_never_serializes_hidden_oracle() -> None:
    scenario = _scenario(hidden_label="NEVER_LEAK_THIS")
    run = HabitationRunner().run(
        scenario=scenario,
        model_id="provider/model-a",
        target=EchoTarget("model-a"),
    )

    artifact = run_artifact(scenario=scenario, run=run)
    encoded = run_artifact_json(scenario=scenario, run=run)

    assert artifact["model_id"] == "provider/model-a"
    assert artifact["scenario_version"] == "3"
    assert artifact["scenario_seed"] == 20260920
    assert artifact["delivered_count"] == 2
    assert "hidden_oracle" not in encoded
    assert "NEVER_LEAK_THIS" not in encoded
    assert "evaluator-only" not in encoded


def test_comparison_manifest_only_proves_same_visible_life() -> None:
    scenario = _scenario()
    runner = HabitationRunner()
    a = runner.run(
        scenario=scenario,
        model_id="provider/model-a",
        target=EchoTarget("a"),
    )
    b = runner.run(
        scenario=scenario,
        model_id="provider/model-b",
        target=EchoTarget("b"),
    )

    manifest = comparison_manifest(scenario=scenario, runs=(a, b))

    assert manifest["models"] == ["provider/model-a", "provider/model-b"]
    assert manifest["run_count"] == 2
    assert manifest["scenario_public_fingerprint"] == scenario_public_fingerprint(scenario)
    assert "latent_truth" not in json.dumps(manifest)


def test_comparison_manifest_rejects_duplicate_model_identity() -> None:
    scenario = _scenario()
    runner = HabitationRunner()
    first = runner.run(
        scenario=scenario,
        model_id="same/model",
        target=EchoTarget("a"),
    )
    second = runner.run(
        scenario=scenario,
        model_id="same/model",
        target=EchoTarget("b"),
    )

    with pytest.raises(ValueError, match="unique model_id"):
        comparison_manifest(scenario=scenario, runs=(first, second))


def test_load_scenario_json_preserves_version_seed_and_sealed_truth() -> None:
    source = json.dumps(
        {
            "scenario_id": "json-life",
            "scenario_version": "7",
            "seed": 42,
            "subject_id": "user-x",
            "hidden_oracle": {"latent": "judge-only"},
            "events": [
                {
                    "event_id": "chat-1",
                    "occurred_at": "2026-09-20T08:00:00+00:00",
                    "channel": "conversation",
                    "payload": "hello",
                    "metadata": {"session": "s1"},
                    "hidden_oracle": {"meaning": "judge-only"},
                }
            ],
        },
        ensure_ascii=False,
    )

    scenario = load_scenario_json(source)

    assert scenario.scenario_id == "json-life"
    assert scenario.scenario_version == "7"
    assert scenario.seed == 42
    assert scenario.hidden_oracle["latent"] == "judge-only"
    assert scenario.events[0].hidden_oracle["meaning"] == "judge-only"
    assert not hasattr(scenario.events[0].resident_view(), "hidden_oracle")


def test_load_events_jsonl_accepts_comments_and_requires_aware_time() -> None:
    events = load_events_jsonl(
        """
# synthetic-life stream
{"event_id":"a","occurred_at":"2026-09-20T08:00:00+00:00","channel":"conversation","payload":"a"}
{"event_id":"b","occurred_at":"2026-09-21T08:00:00Z","channel":"calendar","payload":{"title":"b"}}
"""
    )

    assert [event.event_id for event in events] == ["a", "b"]
    assert all(event.occurred_at.tzinfo is not None for event in events)

    with pytest.raises(ValueError, match="timezone-aware"):
        load_events_jsonl(
            '{"event_id":"bad","occurred_at":"2026-09-20T08:00:00","channel":"x","payload":"x"}'
        )
