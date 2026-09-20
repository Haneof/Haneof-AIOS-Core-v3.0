from __future__ import annotations

from argparse import Namespace
from datetime import datetime, timezone
import json

from aios_core.runtime.cognitive_runtime import ModelDirective

from . import run_provider_benchmark


NOW = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)


class FakeResident:
    model_id = "openai/test-model"

    def __call__(self, snapshot):
        return ModelDirective(response="provider resident completed")

    def provenance_snapshot(self):
        return {
            "artifact_schema": "aios.p16.provider-provenance.v1",
            "provider": "openai",
            "model": "test-model",
            "model_id": self.model_id,
            "config_fingerprint": "sha256:test",
            "requests": [{"sequence": 1, "purpose": "resident"}],
        }


class FakeSummary:
    model_id = "openai/test-model"

    def __call__(self, request):
        return "summary"

    def provenance_snapshot(self):
        return FakeResident().provenance_snapshot()


def test_provider_runner_never_requires_or_reads_oracle_file(tmp_path, monkeypatch):
    root = tmp_path / "fixtures"
    resident_dir = root / "resident"
    resident_dir.mkdir(parents=True)

    (resident_dir / "life.jsonl").write_text(
        json.dumps(
            {
                "event_id": "e1",
                "occurred_at": NOW.isoformat(),
                "channel": "conversation",
                "payload": "visible resident life",
                "metadata": {"session": "s1"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "life.manifest.json").write_text(
        json.dumps(
            {
                "scenario_id": "resident-only-life",
                "scenario_version": "1",
                "seed": 1,
                "subject_id": "synthetic-runner-user",
                "resident_stream": "resident/life.jsonl",
                "evaluator_oracle": "oracle/DOES_NOT_EXIST.json",
                "end_at": NOW.isoformat(),
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("OPENAI_API_KEY", "not-used-by-fake-handler")
    monkeypatch.setattr(
        run_provider_benchmark,
        "make_provider_handlers",
        lambda config: (FakeResident(), FakeSummary()),
    )

    output = tmp_path / "artifacts"
    artifact_path = run_provider_benchmark.run(
        Namespace(
            fixture_root=str(root),
            manifest="life.manifest.json",
            provider="openai",
            model="test-model",
            output_dir=str(output),
            max_output_tokens=256,
            timeout_seconds=5.0,
            temperature=None,
            endpoint=None,
            api_key_env=None,
            api_version=None,
        )
    )

    assert not (root / "oracle" / "DOES_NOT_EXIST.json").exists()
    launch = json.loads((output / "launch.json").read_text(encoding="utf-8"))
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert launch["oracle_loaded"] is False
    assert artifact["oracle_loaded"] is False
    assert artifact["scenario_public_fingerprint"] == launch[
        "scenario_public_fingerprint"
    ]
    assert artifact["provider_provenance"]["provider"] == "openai"
    assert artifact["model_id"] == "openai/test-model"
