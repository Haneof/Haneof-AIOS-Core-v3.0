from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot
from habitation.current_core import CurrentCoreHabitationTarget
from habitation.harness import HabitationRunner
from habitation.io import load_resident_fixture, run_artifact


class ManualDecisionRequired(RuntimeError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def snapshot_payload(snapshot: RuntimeSnapshot) -> dict[str, Any]:
    return {
        "user_input": snapshot.user_input,
        "wake_reason": snapshot.wake_reason,
        "cockpit": snapshot.cockpit,
        "capability_catalog": list(snapshot.capability_catalog),
        "capability_history": [asdict(item) for item in snapshot.capability_history],
        "round_index": snapshot.round_index,
        "remaining_tool_rounds": snapshot.remaining_tool_rounds,
    }


def decision_key(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()


def portable_payload(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except TypeError:
            return value.model_dump()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(k): portable_payload(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [portable_payload(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "__dict__"):
        return {
            str(k): portable_payload(v)
            for k, v in vars(value).items()
            if not str(k).startswith("_")
        }
    return str(value)


def directive_from_json(raw: dict[str, Any]) -> ModelDirective:
    kind = raw.get("kind")
    if kind == "response":
        return ModelDirective(response=str(raw["response"]))
    if kind == "silence":
        return ModelDirective(silence=True)
    if kind == "capability_calls":
        calls = []
        for index, item in enumerate(raw.get("calls") or []):
            calls.append(
                CapabilityCall(
                    name=str(item["name"]),
                    arguments=dict(item.get("arguments") or {}),
                    call_id=str(item.get("call_id") or f"manual-{index+1}"),
                )
            )
        return ModelDirective(capability_calls=tuple(calls))
    raise ValueError(f"unknown manual directive kind: {kind!r}")


class ManualSummaryResident:
    """Interactive GPT-5.6 Sol handler for both conversation and dimension summaries."""

    model_id = "gpt-5.6-sol-interactive-resident"

    def __init__(self, decisions: dict[str, Any]) -> None:
        self.decisions = decisions
        self.live_calls = 0
        self.replayed_calls = 0

    def __call__(self, request: Any) -> str:
        payload = {
            "summary_request_type": type(request).__name__,
            "request": portable_payload(request),
        }
        key = decision_key(payload)
        raw = self.decisions.get(key)
        if raw is not None:
            if not isinstance(raw, dict) or raw.get("kind") != "summary":
                raise ValueError(
                    f"decision {key} exists but is not a summary directive"
                )
            summary = str(raw.get("summary") or "").strip()
            if not summary:
                raise ValueError(f"summary decision {key} is blank")
            self.replayed_calls += 1
            return summary

        self.live_calls += 1
        envelope = {
            "schema": "aios.manual-summary.pending.v1",
            "decision_key": key,
            "resident_model": "GPT-5.6 Sol (interactive ChatGPT resident)",
            "rule": (
                "This Summary is not precomputed. The same resident model must inspect "
                "this exact Summary request and author the semantic compression."
            ),
            "summary_request": payload,
        }
        print("MANUAL_SUMMARY_PENDING_BEGIN")
        print(json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2, default=str))
        print("MANUAL_SUMMARY_PENDING_END")
        raise ManualDecisionRequired(key)


class ManualResident:
    def __init__(self, decisions: dict[str, Any]) -> None:
        self.decisions = decisions
        self.live_calls = 0
        self.replayed_calls = 0

    def __call__(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        payload = snapshot_payload(snapshot)
        key = decision_key(payload)
        if key in self.decisions:
            self.replayed_calls += 1
            return directive_from_json(dict(self.decisions[key]))

        self.live_calls += 1
        envelope = {
            "schema": "aios.manual-resident.pending.v1",
            "decision_key": key,
            "resident_model": "GPT-5.6 Sol (interactive ChatGPT resident)",
            "rule": "This decision is not precomputed. The reviewer must inspect this exact snapshot and then commit one directive keyed by decision_key.",
            "snapshot": payload,
        }
        print("MANUAL_RESIDENT_PENDING_BEGIN")
        print(json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2, default=str))
        print("MANUAL_RESIDENT_PENDING_END")
        raise ManualDecisionRequired(key)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--decisions", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    fixture_root = Path(args.fixture_root)
    decisions_path = Path(args.decisions)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
    if not isinstance(decisions, dict):
        raise ValueError("decisions file must be an object keyed by decision hash")

    loaded = load_resident_fixture(fixture_root, args.manifest)
    resident = ManualResident(decisions)
    summarizer = ManualSummaryResident(decisions)
    target = CurrentCoreHabitationTarget(
        model_id="gpt-5.6-sol-interactive-resident",
        subject_id=loaded.scenario.subject_id,
        db_path=output_dir / "world.sqlite",
        model_handler=resident,
        round_summary_handler=summarizer,
        dimension_summary_handler=summarizer,
        require_fresh=True,
    )

    try:
        run = HabitationRunner().run(
            scenario=loaded.scenario,
            model_id="gpt-5.6-sol-interactive-resident",
            target=target,
        )
    except ManualDecisionRequired as exc:
        print(f"MANUAL_RESIDENT_STATUS=pending decision_key={exc}")
        print(f"MANUAL_RESIDENT_REPLAYED_CALLS={resident.replayed_calls}")
        print(f"MANUAL_SUMMARY_REPLAYED_CALLS={summarizer.replayed_calls}")
        return 42

    artifact = run_artifact(scenario=loaded.scenario, run=run)
    (output_dir / "run.json").write_text(
        json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print("MANUAL_RESIDENT_STATUS=completed")
    print(f"MANUAL_RESIDENT_REPLAYED_CALLS={resident.replayed_calls}")
    print(f"MANUAL_SUMMARY_REPLAYED_CALLS={summarizer.replayed_calls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
