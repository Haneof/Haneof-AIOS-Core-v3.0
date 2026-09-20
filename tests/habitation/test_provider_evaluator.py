from __future__ import annotations

from argparse import Namespace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from .evaluation import ORACLE_SCHEMA_V1, evaluate_with_oracle
from .harness import HabitationRunner, HabitationScenario, LifeEvent, ResidentEvent
from .io import (
    load_resident_fixture,
    load_run_artifact_json,
    run_artifact_json,
)
from .provider_evaluator import ProviderOracleEvaluator
from .provider_runtime import ProviderClient, ProviderConfig, ProviderProtocolError
from . import run_provider_evaluator


BASE = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)


class Target:
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.isolation_key = f"world:{model_id}"
        self.clock = []

    def advance_to(self, instant: datetime):
        self.clock.append(instant)
        return {"to": instant.isoformat()}

    def handle_event(self, event: ResidentEvent):
        return {"response": f"handled {event.event_id}"}

    def audit_snapshot(self):
        return {
            "model_id": self.model_id,
            "clock": self.clock[-1].isoformat(),
            "objects": [],
        }


class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, url, headers, payload, timeout):
        self.calls.append({"payload": json.loads(json.dumps(payload))})
        return self.response


def scenario_with_oracle() -> HabitationScenario:
    return HabitationScenario(
        scenario_id="provider-evaluator-life",
        scenario_version="2",
        subject_id="synthetic-evaluator-user",
        hidden_oracle={
            "evaluation_schema": ORACLE_SCHEMA_V1,
            "criteria": ["continuity", "epistemic_restraint"],
            "latent_truth": {
                "evaluation_only": True,
                "description": "The second statement updates the first.",
            },
        },
        events=(
            LifeEvent(
                event_id="e1",
                occurred_at=BASE,
                channel="conversation",
                payload="Earlier plan.",
                metadata={"session": "s1"},
            ),
            LifeEvent(
                event_id="e2",
                occurred_at=BASE + timedelta(days=1),
                channel="conversation",
                payload="Plan changed.",
                metadata={"session": "s2"},
            ),
        ),
    )


def resident_run(scenario: HabitationScenario):
    return HabitationRunner().run(
        scenario=scenario,
        model_id="resident/test-model",
        target=Target("resident/test-model"),
    )


def evaluator_response():
    text = json.dumps(
        {
            "findings": [
                {
                    "criterion_id": "continuity",
                    "status": "pass",
                    "summary": "Both visible events were preserved.",
                    "evidence_event_ids": ["e1", "e2"],
                    "measurements": {"visible_events": 2},
                },
                {
                    "criterion_id": "epistemic_restraint",
                    "status": "observe",
                    "summary": "No unsupported conclusion was required.",
                    "evidence_event_ids": ["e2"],
                    "measurements": {},
                },
            ]
        }
    )
    return {
        "id": "eval_resp_1",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
        "usage": {"input_tokens": 100, "output_tokens": 80},
    }


def test_provider_evaluator_returns_exact_criteria_with_provenance() -> None:
    scenario = scenario_with_oracle()
    run = resident_run(scenario)
    transport = FakeTransport(evaluator_response())
    client = ProviderClient(
        ProviderConfig(provider="openai", model="judge-test"),
        transport=transport,
        api_key="never-serialize-judge-key",
    )
    evaluator = ProviderOracleEvaluator(client, evaluator_id="judge-test-v1")

    report = evaluate_with_oracle(
        scenario=scenario,
        run=run,
        evaluator_provenance=evaluator.provenance,
        handler=evaluator,
    )

    assert [item.criterion_id for item in report.findings] == [
        "continuity",
        "epistemic_restraint",
    ]
    assert report.evaluator_provenance.provider == "openai"
    assert report.evaluator_provenance.model == "judge-test"
    provenance = evaluator.provider_provenance_snapshot()
    assert provenance["requests"][0]["purpose"] == "oracle_evaluation"
    assert "never-serialize-judge-key" not in json.dumps(provenance)
    assert "latent_truth" in json.dumps(transport.calls[0]["payload"])


def test_provider_evaluator_rejects_non_json_output() -> None:
    scenario = scenario_with_oracle()
    run = resident_run(scenario)
    transport = FakeTransport(
        {
            "id": "eval_bad",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "NOT JSON"}],
                }
            ],
        }
    )
    evaluator = ProviderOracleEvaluator(
        ProviderClient(
            ProviderConfig(provider="openai", model="judge-test"),
            transport=transport,
            api_key="test-key",
        ),
        evaluator_id="judge-test-v1",
    )

    with pytest.raises(ProviderProtocolError, match="strict JSON"):
        evaluate_with_oracle(
            scenario=scenario,
            run=run,
            evaluator_provenance=evaluator.provenance,
            handler=evaluator,
        )


def test_run_artifact_round_trips_for_separate_evaluator() -> None:
    scenario = scenario_with_oracle()
    run = resident_run(scenario)
    loaded = load_run_artifact_json(
        run_artifact_json(scenario=scenario, run=run)
    )

    assert loaded.scenario_id == scenario.scenario_id
    assert loaded.scenario_version == scenario.scenario_version
    assert loaded.model_id == run.model_id
    assert [step.event_id for step in loaded.run.steps] == ["e1", "e2"]


def test_evaluator_cli_rejects_wrong_visible_life_before_provider_call(
    tmp_path,
    monkeypatch,
) -> None:
    root = tmp_path / "fixtures"
    (root / "resident").mkdir(parents=True)
    (root / "oracle").mkdir(parents=True)

    (root / "resident" / "life.jsonl").write_text(
        json.dumps(
            {
                "event_id": "e1",
                "occurred_at": BASE.isoformat(),
                "channel": "conversation",
                "payload": "visible",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "oracle" / "life.json").write_text(
        json.dumps(
            {
                "scenario_id": "life",
                "scenario_version": "1",
                "seed": 1,
                "subject_id": "u1",
                "evaluation_schema": ORACLE_SCHEMA_V1,
                "criteria": ["continuity"],
                "latent_truth": {"evaluation_only": True},
            }
        ),
        encoding="utf-8",
    )
    (root / "life.manifest.json").write_text(
        json.dumps(
            {
                "scenario_id": "life",
                "scenario_version": "1",
                "seed": 1,
                "subject_id": "u1",
                "resident_stream": "resident/life.jsonl",
                "evaluator_oracle": "oracle/life.json",
                "end_at": BASE.isoformat(),
            }
        ),
        encoding="utf-8",
    )

    wrong_scenario = HabitationScenario(
        scenario_id="life",
        scenario_version="1",
        seed=1,
        subject_id="u1",
        events=(
            LifeEvent(
                event_id="e1",
                occurred_at=BASE,
                channel="conversation",
                payload="different visible input",
            ),
        ),
        end_at=BASE,
    )
    wrong_run = HabitationRunner().run(
        scenario=wrong_scenario,
        model_id="resident/model",
        target=Target("resident/model"),
    )
    run_path = tmp_path / "wrong-run.json"
    run_path.write_text(
        run_artifact_json(scenario=wrong_scenario, run=wrong_run),
        encoding="utf-8",
    )

    called = False

    class MustNotCreateClient:
        def __init__(self, config):
            nonlocal called
            called = True

    monkeypatch.setattr(run_provider_evaluator, "ProviderClient", MustNotCreateClient)

    with pytest.raises(ValueError, match="visible-life fingerprint"):
        run_provider_evaluator.run(
            Namespace(
                fixture_root=str(root),
                manifest="life.manifest.json",
                run_artifact=str(run_path),
                provider="openai",
                model="judge",
                evaluator_id="judge-v1",
                output_dir=str(tmp_path / "out"),
                max_output_tokens=256,
                timeout_seconds=10.0,
                temperature=None,
                endpoint=None,
                api_key_env=None,
                api_version=None,
            )
        )
    assert called is False


def test_evaluator_cli_writes_report_for_matching_completed_run(
    tmp_path,
    monkeypatch,
) -> None:
    fixture_root = Path(__file__).parent / "fixtures"
    manifest_name = "uncertainty_restraint_v1.manifest.json"
    resident = load_resident_fixture(fixture_root, manifest_name)
    scenario = resident.scenario
    run = HabitationRunner().run(
        scenario=scenario,
        model_id="resident/model",
        target=Target("resident/model"),
    )
    run_path = tmp_path / "run.json"
    run_path.write_text(
        run_artifact_json(scenario=scenario, run=run),
        encoding="utf-8",
    )

    class FakeClient:
        def __init__(self, config):
            self.config = config
            self.requests = 0

        def complete_text(self, *, system_instruction, input_text, purpose):
            self.requests += 1
            payload = json.loads(input_text)
            event_id = payload["resident_run"]["steps"][0]["event_id"]
            return json.dumps(
                {
                    "findings": [
                        {
                            "criterion_id": criterion,
                            "status": "observe",
                            "summary": "independent evaluator observation",
                            "evidence_event_ids": [event_id],
                            "measurements": {},
                        }
                        for criterion in payload["criteria"]
                    ]
                }
            )

        def provenance_snapshot(self):
            return {
                "artifact_schema": "aios.p16.provider-provenance.v1",
                **self.config.public_config(),
                "config_fingerprint": self.config.config_fingerprint,
                "requests": [
                    {
                        "sequence": 1,
                        "purpose": "oracle_evaluation",
                    }
                ],
            }

    monkeypatch.setattr(run_provider_evaluator, "ProviderClient", FakeClient)

    output_dir = tmp_path / "evaluation"
    result_path = run_provider_evaluator.run(
        Namespace(
            fixture_root=str(fixture_root),
            manifest=manifest_name,
            run_artifact=str(run_path),
            provider="openai",
            model="judge-model",
            evaluator_id="judge-v1",
            output_dir=str(output_dir),
            max_output_tokens=1024,
            timeout_seconds=10.0,
            temperature=None,
            endpoint=None,
            api_key_env=None,
            api_version=None,
        )
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["oracle_loaded"] is True
    assert payload["resident_model_id"] == "resident/model"
    assert payload["report"]["evaluator_id"] == "judge-v1"
    assert len(payload["report"]["findings"]) > 0
    assert payload["provider_request_provenance"]["requests"][0][
        "purpose"
    ] == "oracle_evaluation"
