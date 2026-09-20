from __future__ import annotations

import json
from pathlib import Path

from .evaluation import ORACLE_SCHEMA_V1, oracle_criteria
from .io import load_fixture_bundle, load_resident_events_jsonl


FIXTURES = Path(__file__).parent / "fixtures"
RESIDENT = FIXTURES / "resident" / "learning_independence_v1.jsonl"
ORACLE = FIXTURES / "oracle" / "learning_independence_v1.json"
MANIFEST = FIXTURES / "learning_independence_v1.manifest.json"


def test_resident_fixture_contains_only_deliverable_life_events() -> None:
    resident_text = RESIDENT.read_text(encoding="utf-8")
    events = load_resident_events_jsonl(resident_text)

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


def test_catalog_scenarios_have_separate_resident_and_oracle_files() -> None:
    catalog = json.loads((FIXTURES / "catalog.json").read_text(encoding="utf-8"))
    entries = catalog["scenarios"]

    scenario_ids = [entry["scenario_id"] for entry in entries]
    assert len(scenario_ids) == len(set(scenario_ids))
    assert len(entries) >= 4

    for entry in entries:
        manifest_path = FIXTURES / entry["manifest"]
        assert manifest_path.exists()

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["scenario_id"] == entry["scenario_id"]
        assert manifest["resident_stream"].startswith("resident/")
        assert manifest["evaluator_oracle"].startswith("oracle/")
        assert isinstance(manifest.get("end_at"), str)

        resident_path = FIXTURES / manifest["resident_stream"]
        oracle_path = FIXTURES / manifest["evaluator_oracle"]
        assert resident_path.exists()
        assert oracle_path.exists()
        assert resident_path != oracle_path

        events = load_resident_events_jsonl(resident_path.read_text(encoding="utf-8"))
        assert events
        assert all(event.deliver_to_resident for event in events)
        assert all(not event.hidden_oracle for event in events)

        oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
        assert oracle["scenario_id"] == entry["scenario_id"]
        assert oracle["latent_truth"]["evaluation_only"] is True
        assert oracle["evaluation_schema"] == ORACLE_SCHEMA_V1
        assert isinstance(oracle["criteria"], list)
        assert oracle["criteria"]
        assert len(oracle["criteria"]) == len(set(oracle["criteria"]))


def test_catalog_focuses_on_behavior_not_expected_response_strings() -> None:
    catalog_text = (FIXTURES / "catalog.json").read_text(encoding="utf-8")
    catalog = json.loads(catalog_text)

    assert "expected_response" not in catalog_text
    assert "expected_answer" not in catalog_text
    assert all(entry["focus"] for entry in catalog["scenarios"])


def test_resident_subject_ids_are_opaque_and_non_semantic() -> None:
    catalog = json.loads((FIXTURES / "catalog.json").read_text(encoding="utf-8"))
    expected = {
        "synthetic-user-001",
        "synthetic-user-002",
        "synthetic-user-003",
        "synthetic-user-004",
    }

    subject_ids = set()
    for entry in catalog["scenarios"]:
        manifest = json.loads(
            (FIXTURES / entry["manifest"]).read_text(encoding="utf-8")
        )
        subject_ids.add(manifest["subject_id"])

    assert subject_ids == expected
    assert all(
        token not in subject_id
        for subject_id in subject_ids
        for token in ("learning", "continuity", "revision", "uncertainty")
    )


def test_every_catalog_fixture_bundle_has_matching_resident_and_oracle_identity() -> None:
    catalog = json.loads((FIXTURES / "catalog.json").read_text(encoding="utf-8"))

    for entry in catalog["scenarios"]:
        loaded = load_fixture_bundle(FIXTURES, entry["manifest"])
        manifest = loaded.manifest
        scenario = loaded.scenario

        assert scenario.scenario_id == manifest.scenario_id
        assert scenario.scenario_version == manifest.scenario_version
        assert scenario.seed == manifest.seed
        assert scenario.subject_id == manifest.subject_id
        assert scenario.end_at == manifest.end_at
        assert scenario.end_at is not None
        assert scenario.end_at >= max(event.occurred_at for event in scenario.events)
        assert scenario.hidden_oracle["scenario_id"] == manifest.scenario_id
        assert scenario.hidden_oracle["scenario_version"] == manifest.scenario_version
        assert scenario.hidden_oracle["seed"] == manifest.seed
        assert scenario.hidden_oracle["subject_id"] == manifest.subject_id
        assert oracle_criteria(scenario)
        assert all(not event.hidden_oracle for event in scenario.events)


def test_fixture_bundle_rejects_manifest_path_traversal(tmp_path) -> None:
    import pytest

    with pytest.raises(ValueError, match="stay under fixture root"):
        load_fixture_bundle(tmp_path, "../outside.manifest.json")
