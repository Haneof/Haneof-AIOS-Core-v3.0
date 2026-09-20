from __future__ import annotations

import json

import pytest

from .compare_provider_evaluations import compare
from .evaluation_io import load_evaluation_artifact


def _artifact(
    model_id: str,
    *,
    status: str,
    fingerprint: str = "visible-life-sha",
):
    provenance = {
        "evaluator_id": "judge-v1",
        "evaluator_kind": "model",
        "provider": "openai",
        "model": "judge-model",
        "version": None,
        "config_fingerprint": "sha256:judge-config",
    }
    return {
        "artifact_schema": "aios.p16.provider-evaluation-launch.v1",
        "scenario_id": "life-1",
        "scenario_version": "1",
        "scenario_public_fingerprint": fingerprint,
        "resident_model_id": model_id,
        "evaluator_id": "judge-v1",
        "evaluator_provider": "openai",
        "evaluator_model": "judge-model",
        "evaluator_config_fingerprint": "sha256:judge-config",
        "oracle_loaded": True,
        "report": {
            "artifact_schema": "aios.p16.model-evaluation.v2",
            "scenario_id": "life-1",
            "scenario_version": "1",
            "scenario_public_fingerprint": fingerprint,
            "model_id": model_id,
            "evaluator_id": "judge-v1",
            "evaluator_provenance": provenance,
            "findings": [
                {
                    "criterion_id": "continuity",
                    "status": status,
                    "summary": f"{model_id} continuity finding",
                    "evidence_event_ids": ["e1"],
                    "measurements": {},
                }
            ],
        },
        "provider_request_provenance": {
            "artifact_schema": "aios.p16.provider-provenance.v1",
            "provider": "openai",
            "model": "judge-model",
            "requests": [],
        },
    }


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_offline_comparison_aligns_models_without_ranking(tmp_path) -> None:
    a = _write(tmp_path / "a.json", _artifact("openai/model-a", status="pass"))
    b = _write(tmp_path / "b.json", _artifact("anthropic/model-b", status="fail"))

    result = compare([b, a])

    assert result["scenario_public_fingerprint"] == "visible-life-sha"
    models = result["comparison"]["models"]
    assert list(models) == ["anthropic/model-b", "openai/model-a"]
    assert models["openai/model-a"]["continuity"]["status"] == "pass"
    assert models["anthropic/model-b"]["continuity"]["status"] == "fail"
    serialized = json.dumps(result)
    assert '"winner"' not in serialized
    assert '"ranking"' not in serialized
    assert '"score"' not in serialized


def test_offline_comparison_rejects_different_visible_lives(tmp_path) -> None:
    a = _write(tmp_path / "a.json", _artifact("openai/model-a", status="pass"))
    b = _write(
        tmp_path / "b.json",
        _artifact(
            "anthropic/model-b",
            status="observe",
            fingerprint="different-life-sha",
        ),
    )

    with pytest.raises(ValueError, match="same visible scenario"):
        compare([a, b])


def test_evaluation_artifact_loader_rejects_model_identity_tamper(tmp_path) -> None:
    payload = _artifact("openai/model-a", status="pass")
    payload["resident_model_id"] = "openai/fake-label"
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="resident_model_id"):
        load_evaluation_artifact(path)


def test_offline_comparison_requires_two_evaluations(tmp_path) -> None:
    a = _write(tmp_path / "a.json", _artifact("openai/model-a", status="pass"))
    with pytest.raises(ValueError, match="at least two"):
        compare([a])
