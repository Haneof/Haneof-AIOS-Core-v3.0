"""Replay-driven self-resident probe for P16.

This test-only driver lets a human/current ChatGPT session inhabit the real AIOS
Current-Core without an external provider API. It replays previously committed
model directives deterministically. At the first missing resident decision it emits
the exact RuntimeSnapshot and stops. The next directive can then be appended and the
run replayed from a fresh world.

The process loads only the resident fixture; it never opens the evaluator oracle.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot

from .current_core import CurrentCoreHabitationTarget
from .harness import HabitationRunner
from .io import load_resident_fixture, run_artifact, scenario_public_fingerprint


class ManualInputRequired(RuntimeError):
    pass


def _safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value):
        return _safe(asdict(value))
    if hasattr(value, "model_dump"):
        try:
            return _safe(value.model_dump(mode="json"))
        except TypeError:
            return _safe(value.model_dump())
    if isinstance(value, Mapping):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_safe(v) for v in value]
    return str(value)


def _canonical(value: Any) -> str:
    return json.dumps(
        _safe(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_safe(payload), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


class ReplayResident:
    def __init__(self, responses: list[dict[str, Any]], output_dir: Path) -> None:
        self.responses = responses
        self.output_dir = output_dir
        self.index = 0
        self.model_id = "manual:gpt-5.6-sol"

    def _snapshot_payload(self, snapshot: RuntimeSnapshot) -> dict[str, Any]:
        return {
            "kind": "resident",
            "decision_index": self.index,
            "user_input": snapshot.user_input,
            "wake_reason": snapshot.wake_reason,
            "cockpit": snapshot.cockpit,
            "capability_catalog": snapshot.capability_catalog,
            "capability_history": snapshot.capability_history,
            "round_index": snapshot.round_index,
            "remaining_tool_rounds": snapshot.remaining_tool_rounds,
        }

    def __call__(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        payload = _safe(self._snapshot_payload(snapshot))
        signature = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
        packet = {
            "artifact_schema": "aios.p16.manual-resident-prompt.v1",
            "model_id": self.model_id,
            "signature": signature,
            **payload,
        }

        if self.index >= len(self.responses):
            _write_json(self.output_dir / "next_prompt.json", packet)
            print("AIOS_MANUAL_PROMPT_BEGIN")
            print(json.dumps(packet, ensure_ascii=False, sort_keys=True))
            print("AIOS_MANUAL_PROMPT_END")
            raise ManualInputRequired(
                f"resident directive required at index {self.index} signature {signature}"
            )

        entry = self.responses[self.index]
        expected = entry.get("snapshot_signature")
        if expected != signature:
            _write_json(
                self.output_dir / "replay_mismatch.json",
                {
                    "decision_index": self.index,
                    "expected_signature": expected,
                    "actual_signature": signature,
                    "snapshot": packet,
                    "entry": entry,
                },
            )
            raise RuntimeError(
                f"manual replay drift at index {self.index}: "
                f"expected {expected!r}, got {signature!r}"
            )

        self.index += 1
        kind = entry.get("type")
        if kind == "response":
            return ModelDirective(response=str(entry["text"]))
        if kind == "silence":
            return ModelDirective(silence=True)
        if kind == "capability_calls":
            calls = []
            for item in entry.get("calls", []):
                calls.append(
                    CapabilityCall(
                        name=str(item["name"]),
                        arguments=dict(item.get("arguments", {})),
                        call_id=item.get("call_id"),
                    )
                )
            if not calls:
                raise ValueError("capability_calls entry must contain at least one call")
            return ModelDirective(capability_calls=tuple(calls))
        raise ValueError(f"unsupported manual directive type: {kind!r}")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--fixture-root", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--responses", required=True)
    p.add_argument("--output-dir", required=True)
    return p


def run(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    responses_path = Path(args.responses)
    responses = json.loads(responses_path.read_text(encoding="utf-8"))
    if not isinstance(responses, list):
        raise ValueError("responses must be a JSON list")

    loaded = load_resident_fixture(args.fixture_root, args.manifest)
    scenario = loaded.scenario
    resident = ReplayResident(responses, output_dir)

    _write_json(
        output_dir / "launch.json",
        {
            "artifact_schema": "aios.p16.manual-resident-launch.v1",
            "scenario_id": scenario.scenario_id,
            "scenario_version": scenario.scenario_version,
            "scenario_public_fingerprint": scenario_public_fingerprint(scenario),
            "subject_id": scenario.subject_id,
            "manifest_name": args.manifest,
            "resident_stream": loaded.manifest.resident_stream,
            "oracle_loaded": False,
            "model_id": resident.model_id,
            "replayed_directives": len(responses),
        },
    )

    target = CurrentCoreHabitationTarget(
        model_id=resident.model_id,
        subject_id=scenario.subject_id,
        db_path=output_dir / "world.sqlite",
        model_handler=resident,
        round_summary_handler=None,
        dimension_summary_handler=None,
        require_fresh=True,
    )

    try:
        result = HabitationRunner().run(
            scenario=scenario,
            model_id=resident.model_id,
            target=target,
        )
    except ManualInputRequired as exc:
        print(f"AIOS manual resident paused: {exc}", file=sys.stderr)
        return 3

    artifact = run_artifact(scenario=scenario, run=result)
    artifact["oracle_loaded"] = False
    artifact["manual_replay_directives"] = resident.index
    _write_json(output_dir / "run.json", artifact)
    print(str(output_dir / "run.json"))
    return 0


def main() -> int:
    args = _parser().parse_args()
    try:
        return run(args)
    except Exception as exc:
        print(f"manual resident failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
