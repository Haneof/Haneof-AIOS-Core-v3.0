from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest

from .harness import HabitationRunner, HabitationScenario, LifeEvent, ResidentEvent
from .io import (
    comparison_manifest,
    load_events_jsonl,
    load_resident_events_jsonl,
    load_scenario_json,
    run_artifact,
    run_artifact_json,
    scenario_public_fingerprint,
)


BASE = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)


class EchoTarget:
    def __init__(self, model: str) -> None:
        self.model = model
        self.isolation_key = f"world:{model}:{id(self)}"
        self.clock: list[datetime] = []
        self.seen: list[str] = []

    def advance_to(self, instant: datetime):
        self.clock.append(instant)
        return {"advanced_to": instant.isoformat()}

    def handle_event(self, event: ResidentEvent):
        self.seen.append(event.event_id)
        return {
            "model": self.model,
            "observed_event": event.event_id,
            "channel": event.channel,
        }

    def audit_snapshot(self):
        return {
            "seen": list(self.seen),
            "clock": [instant.isoformat() for instant in self.clock],
        }


def _scenario(
    *,
    hidden_label: str = "secret-a",
    visible_text: str = "今天开始复习",
    scenario_id: str = "life-io-001",
    scenario_version: str = "3",
    seed: int = 20260920,
    end_at: datetime | None = None,
) -> HabitationScenario:
    return HabitationScenario(
        scenario_id=scenario_id,
        scenario_version=scenario_version,
        seed=seed,
        subject_id="user_1",
        hidden_oracle={"latent_truth": hidden_label},
        end_at=end_at,
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


def test_public_fingerprint_ignores_evaluator_identity_metadata() -> None:
    baseline = _scenario()
    renamed = _scenario(
        scenario_id="different-evaluator-label",
        scenario_version="99",
        seed=999999,
    )

    assert scenario_public_fingerprint(baseline) == scenario_public_fingerprint(renamed)


def test_public_fingerprint_includes_final_execution_horizon() -> None:
    baseline = _scenario()
    extended = _scenario(end_at=BASE + timedelta(days=5))

    assert scenario_public_fingerprint(baseline) != scenario_public_fingerprint(extended)


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
    assert artifact["steps"][0]["time_advance_result"]["advanced_to"] == BASE.isoformat()
    assert artifact["final_snapshot"]["seen"] == ["e1", "e2"]
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
            "end_at": "2026-09-22T08:00:00+00:00",
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
    assert scenario.end_at == datetime(2026, 9, 22, 8, 0, tzinfo=timezone.utc)
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


def test_jsonl_rejects_string_boolean_and_non_chronological_events() -> None:
    with pytest.raises(ValueError, match="deliver_to_resident must be a boolean"):
        load_events_jsonl(
            '{"event_id":"a","occurred_at":"2026-09-20T08:00:00Z","channel":"x","payload":"x","deliver_to_resident":"false"}'
        )

    with pytest.raises(ValueError, match="events must be chronological"):
        load_events_jsonl(
            """{"event_id":"later","occurred_at":"2026-09-21T08:00:00Z","channel":"x","payload":"later"}
{"event_id":"earlier","occurred_at":"2026-09-20T08:00:00Z","channel":"x","payload":"earlier"}"""
        )


def test_jsonl_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="duplicate event_id"):
        load_events_jsonl(
            """{"event_id":"same","occurred_at":"2026-09-20T08:00:00Z","channel":"x","payload":"a"}
{"event_id":"same","occurred_at":"2026-09-21T08:00:00Z","channel":"x","payload":"b"}"""
        )


def test_scenario_json_rejects_type_coercion_for_identity_and_seed() -> None:
    with pytest.raises(ValueError, match="scenario_id must be a non-empty string"):
        load_scenario_json(
            '{"scenario_id":null,"subject_id":"u","events":[{"event_id":"e","occurred_at":"2026-09-20T08:00:00Z","channel":"x"}]}'
        )

    with pytest.raises(ValueError, match="seed must be an integer"):
        load_scenario_json(
            '{"scenario_id":"s","subject_id":"u","seed":"42","events":[{"event_id":"e","occurred_at":"2026-09-20T08:00:00Z","channel":"x"}]}'
        )


def test_public_fingerprint_rejects_non_json_visible_payload() -> None:
    scenario = HabitationScenario(
        scenario_id="non-json",
        subject_id="u",
        events=(
            LifeEvent(
                event_id="e1",
                occurred_at=BASE,
                channel="conversation",
                payload={"bad": {1, 2, 3}},
            ),
        ),
    )

    with pytest.raises(TypeError):
        scenario_public_fingerprint(scenario)


def test_run_artifact_json_rejects_non_json_response_instead_of_stringifying() -> None:
    scenario = _scenario()

    class NonJsonTarget(EchoTarget):
        def handle_event(self, event: ResidentEvent):
            return {"bad": {1, 2, 3}}

    run = HabitationRunner().run(
        scenario=scenario,
        model_id="provider/non-json",
        target=NonJsonTarget("non-json"),
    )

    with pytest.raises(TypeError):
        run_artifact_json(scenario=scenario, run=run)


def test_comparison_manifest_requires_at_least_one_run() -> None:
    with pytest.raises(ValueError, match="at least one run is required"):
        comparison_manifest(scenario=_scenario(), runs=())


def test_resident_loader_rejects_embedded_oracle_and_hidden_events() -> None:
    with pytest.raises(ValueError, match="must not contain hidden_oracle"):
        load_resident_events_jsonl(
            '{"event_id":"e1","occurred_at":"2026-09-20T08:00:00Z","channel":"x","payload":"x","hidden_oracle":{"answer":"secret"}}'
        )

    with pytest.raises(ValueError, match="must be deliverable"):
        load_resident_events_jsonl(
            '{"event_id":"e1","occurred_at":"2026-09-20T08:00:00Z","channel":"x","payload":"x","deliver_to_resident":false}'
        )


def test_resident_loader_accepts_clean_stream() -> None:
    events = load_resident_events_jsonl(
        '{"event_id":"e1","occurred_at":"2026-09-20T08:00:00Z","channel":"conversation","payload":"hello"}'
    )

    assert len(events) == 1
    assert events[0].event_id == "e1"
