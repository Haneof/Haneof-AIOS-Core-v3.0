"""Scenario I/O and leak-safe artifact serialization for P16 benchmarks."""

from __future__ import annotations

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


def _required_string(raw: Mapping[str, Any], field_name: str) -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _optional_mapping(raw: Mapping[str, Any], field_name: str) -> dict[str, Any]:
    value = raw.get(field_name)
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return dict(value)


def _optional_bool(
    raw: Mapping[str, Any],
    field_name: str,
    *,
    default: bool,
) -> bool:
    value = raw.get(field_name, default)
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _event_from_mapping(raw: Mapping[str, Any]) -> LifeEvent:
    if not isinstance(raw, Mapping):
        raise ValueError("event must be an object")

    occurred_raw = raw.get("occurred_at")
    if not isinstance(occurred_raw, str):
        raise ValueError("occurred_at must be an ISO-8601 string")

    return LifeEvent(
        event_id=_required_string(raw, "event_id"),
        occurred_at=_parse_datetime(occurred_raw),
        channel=_required_string(raw, "channel"),
        payload=raw.get("payload"),
        metadata=_optional_mapping(raw, "metadata"),
        hidden_oracle=_optional_mapping(raw, "hidden_oracle"),
        deliver_to_resident=_optional_bool(
            raw,
            "deliver_to_resident",
            default=True,
        ),
    )


def load_scenario_json(text: str) -> HabitationScenario:
    """Load one sealed evaluator-side scenario from JSON."""

    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("scenario JSON must contain one object")

    events_raw = raw.get("events")
    if not isinstance(events_raw, list):
        raise ValueError("scenario events must be a list")

    tags_raw = raw.get("tags", ())
    if not isinstance(tags_raw, (list, tuple)):
        raise ValueError("tags must be an array")
    if not all(isinstance(tag, str) and tag.strip() for tag in tags_raw):
        raise ValueError("tags must contain non-empty strings")

    seed_raw = raw.get("seed", 0)
    if not isinstance(seed_raw, int) or isinstance(seed_raw, bool):
        raise ValueError("seed must be an integer")

    version_raw = raw.get("scenario_version", "1")
    if not isinstance(version_raw, str) or not version_raw.strip():
        raise ValueError("scenario_version must be a non-empty string")

    return HabitationScenario(
        scenario_id=_required_string(raw, "scenario_id"),
        subject_id=_required_string(raw, "subject_id"),
        events=tuple(_event_from_mapping(item) for item in events_raw),
        hidden_oracle=_optional_mapping(raw, "hidden_oracle"),
        tags=tuple(tags_raw),
        scenario_version=version_raw,
        seed=seed_raw,
    )


def load_events_jsonl(text: str) -> tuple[LifeEvent, ...]:
    """Load and validate a chronological resident/evaluator event stream."""

    events: list[LifeEvent] = []
    seen_ids: set[str] = set()
    previous: datetime | None = None

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        raw = json.loads(stripped)
        if not isinstance(raw, dict):
            raise ValueError(f"JSONL line {line_number} must contain an object")

        event = _event_from_mapping(raw)
        if event.event_id in seen_ids:
            raise ValueError(
                f"duplicate event_id at JSONL line {line_number}: {event.event_id}"
            )
        if previous is not None and event.occurred_at < previous:
            raise ValueError(
                f"events must be chronological at JSONL line {line_number}"
            )

        seen_ids.add(event.event_id)
        previous = event.occurred_at
        events.append(event)

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

    Hidden oracle fields and evaluator-only events are excluded. Visible payloads
    must be JSON serializable; silently stringifying arbitrary Python objects would
    make cross-machine reproducibility unreliable.
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
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def run_artifact(
    *,
    scenario: HabitationScenario,
    run: HabitationRun,
) -> dict[str, Any]:
    """Create a persistable per-model artifact with no scenario oracle fields."""

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
