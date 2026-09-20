from __future__ import annotations

import json
from pathlib import Path

from .io import load_events_jsonl


FIXTURES = Path(__file__).parent / "fixtures"
RESIDENT = FIXTURES / "resident" / "learning_independence_v1.jsonl"
ORACLE = FIXTURES / "oracle" / "learning_independence_v1.json"
MANIFEST = FIXTURES / "learning_independence_v1.manifest.json"


def test_resident_fixture_contains_only_deliverable_life_events() -> None:
    resident_text = RESIDENT.read_text(encoding="utf-8")
    events = load_events_jsonl(resident_text)

    assert len(events) == 5
    assert all(event.deliver_to_resident for event in events)
    assert all(not event.hidden_oracle for event in events)
    assert "latent_truth" not in resident_text
    assert "event_annotations" not in resident_text
    assert "evaluation_only" not in resident_text
    assert "anti_leak_rule" not in resident_text


def test_oracle_fixture_is_physically_separate_from_resident_stream() -> None:
    resident_text = RESIDENT.read_text(encoding="utf-8")
    oracle_text = ORACLE.read_text(encoding="utf-8")
    oracle = json.loads(oracle_text)

    assert oracle["latent_truth"]["evaluation_only"] is True
    assert oracle["event_annotations"]["d35-chat"]["role"] == "noise_or_temporary_setback"
    assert oracle["latent_truth"]["description"] not in resident_text
    assert "noise_or_temporary_setback" not in resident_text


def test_manifest_requires_fresh_world_and_evaluator_only_oracle() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["resident_stream"].startswith("resident/")
    assert manifest["evaluator_oracle"].startswith("oracle/")
    assert "fresh AIOS world" in manifest["rule"]
    assert "evaluator-only" in manifest["rule"]
