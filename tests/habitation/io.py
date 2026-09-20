"""Scenario I/O and leak-safe artifact serialization for P16 benchmarks."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .harness import HabitationRun, HabitationScenario, LifeEvent, ResidentEvent


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("occurred_at must be timezone-aware")
    return parsed


def _event_from_mapping(raw: Mapping[str, Any]) -> LifeEvent:
    return LifeEvent(
        event_id=str(raw["event_id"]),
        occurred_at=_parse_datetime(str(raw["occurred_at"])),
        channel=str(raw["channel"]),
        payload=raw.get("payload"),
        metadata=dict(raw.get("metadata") or {}),
        hidden_oracle=dict(raw.get("hidden_oracle") or {}),
        deliver_to_resident=bool(raw.get("deliver_to_resident", True)),
    )


def load_scenario_json(text: str) -> HabitationScenario:
    """Load one sealed scenario from JSON.

    hidden_oracle is accepted for evaluator-side fixtures but is never emitted by
    resident artifact serializers.
    """

    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("scenario JSON must contain one object")

    events_raw = raw.get("events")
    if not isinstance(events_raw, list):
        raise ValueError("scenario events must be a list")

    return HabitationScenario(
        scenario_id=str(raw["scenario_id"]),
        subject_id=str(raw["subject_id"]),
        events=tuple(_event_from_mapping(item) for item in events_raw),
        hidden_oracle=dict(raw.get("hidden_oracle") or {}),
        tags=tuple(str(tag) for tag in raw.get("tags") or ()),
        scenario_version=str(raw.get("scenario_version", "1")),
        seed=int(raw.get("seed", 0)),
    )


def load_events_jsonl(text: str) -> tuple[LifeEvent, ...]:
    """Load chronological event records from JSONL.

    This helper does not create a scenario by itself. Scenario identity, version,
    seed and hidden evaluator metadata stay in a separate manifest.
    """

    events: list[LifeEvent] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        raw = json.loads(stripped)
        if not isinstance(raw, dict):
            raise ValueError(f"JSONL line {line_number} must contain an object")
        events.append(_event_from_mapping(raw))
    return tuple(events)


def _resident_event_dict(event: ResidentEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "occurred_at": event.occurred_at.isoformat(),
        "channel": event.channel,
        "payload": event.payload,
        "metadata": dict(event.metadata),
    }


def scenario_public_fingerprint(scenario: HabitationScenario) -> str:
    """Hash exactly the life data visible to resident models.

    Hidden oracle fields and evaluator-only events are intentionally excluded.
    Matching fingerprints therefore prove candidates received the same visible
    life without publishing evaluator truth.
    """

    payload = {
        "scenario_id": scenario.scenario_id,
        "subject_id": scenario.subject_id,
        "scenario_version": scenario.scenario_version,
        "seed": scenario.seed,
        "events": [
            _resident_event_dict(event.resident_view())
            for event in scenario.events
            if event.deliver_to_resident
        ],
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def run_artifact(
    *,
    scenario: HabitationScenario,
    run: HabitationRun,
) -> dict[str, Any]:
    """Create a persistable per-model artifact with no hidden-oracle fields."""

    if run.scenario_id != scenario.scenario_id:
        raise ValueError("run and scenario do not match")
    if run.subject_id != scenario.subject_id:
        raise ValueError("run subject and scenario subject do not match")

    return {
        "artifact_schema": "aios.p16.habitation-run.v1",
        "scenario_id": scenario.scenario_id,
        "scenario_version": scenario.scenario_version,
        "scenario_seed": scenario.seed,
        "scenario_public_fingerprint": scenario_public_fingerprint(scenario),
        "subject_id": run.subject_id,
        "model_id": run.model_id,
        "delivered_count": run.delivered_count,
        "steps": [
            {
                "event_id": step.event_id,
                "occurred_at": step.occurred_at.isoformat(),
                "channel": step.channel,
                "delivered": step.delivered,
                "response": step.response,
            }
            for step in run.steps
        ],
    }


def run_artifact_json(
    *,
    scenario: HabitationScenario,
    run: HabitationRun,
) -> str:
    return json.dumps(
        run_artifact(scenario=scenario, run=run),
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        default=str,
    )


def write_run_artifact(
    path: str | Path,
    *,
    scenario: HabitationScenario,
    run: HabitationRun,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        run_artifact_json(scenario=scenario, run=run) + "\n",
        encoding="utf-8",
    )
    return destination


def comparison_manifest(
    *,
    scenario: HabitationScenario,
    runs: Sequence[HabitationRun],
) -> dict[str, Any]:
    """Build a model-comparison manifest without ranking or evaluator truth."""

    model_ids = [run.model_id for run in runs]
    if len(model_ids) != len(set(model_ids)):
        raise ValueError("comparison runs must have unique model_id values")

    for run in runs:
        if run.scenario_id != scenario.scenario_id:
            raise ValueError("all runs must use the same scenario")
        if run.subject_id != scenario.subject_id:
            raise ValueError("all runs must use the same subject")

    return {
        "artifact_schema": "aios.p16.comparison-manifest.v1",
        "scenario_id": scenario.scenario_id,
        "scenario_version": scenario.scenario_version,
        "scenario_seed": scenario.seed,
        "scenario_public_fingerprint": scenario_public_fingerprint(scenario),
        "models": sorted(model_ids),
        "run_count": len(runs),
    }
