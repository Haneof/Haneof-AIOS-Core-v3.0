from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot
from habitation.current_core import CurrentCoreHabitationTarget
from habitation.io import load_scenario_json


class ManualDecisionRequired(RuntimeError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def portable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except TypeError:
            return value.model_dump()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(k): portable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [portable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "__dict__"):
        return {
            str(k): portable(v)
            for k, v in vars(value).items()
            if not str(k).startswith("_")
        }
    return str(value)


def snapshot_payload(snapshot: RuntimeSnapshot) -> dict[str, Any]:
    return {
        "user_input": snapshot.user_input,
        "wake_reason": snapshot.wake_reason,
        "cockpit": portable(snapshot.cockpit),
        "capability_catalog": list(snapshot.capability_catalog),
        "capability_history": [portable(x) for x in snapshot.capability_history],
        "round_index": snapshot.round_index,
        "remaining_tool_rounds": snapshot.remaining_tool_rounds,
    }


def decision_key(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()


def directive_from_json(raw: dict[str, Any]) -> ModelDirective:
    kind = raw.get("kind")
    if kind == "response":
        return ModelDirective(response=str(raw["response"]))
    if kind == "silence":
        return ModelDirective(silence=True)
    if kind == "capability_calls":
        calls = []
        for i, item in enumerate(raw.get("calls") or []):
            calls.append(
                CapabilityCall(
                    name=str(item["name"]),
                    arguments=dict(item.get("arguments") or {}),
                    call_id=str(item.get("call_id") or f"seg003-{i+1}"),
                )
            )
        return ModelDirective(capability_calls=tuple(calls))
    raise ValueError(f"unknown directive kind {kind!r}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def parse_dt(raw: str) -> datetime:
    value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("aware datetime required")
    return value


class ManualResident:
    model_id = "gpt-5.6-sol-interactive-resident"

    def __init__(self, decisions: dict[str, Any]):
        self.decisions = decisions
        self.replayed = 0
        self.pending = 0
        self.target = None

    def __call__(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        payload = snapshot_payload(snapshot)
        key = decision_key(payload)
        raw = self.decisions.get(key)
        if raw is not None:
            self.replayed += 1
            return directive_from_json(dict(raw))
        self.pending += 1
        envelope = {
            "schema": "aios.segment003.manual-resident.pending.v1",
            "decision_key": key,
            "resident_model": "GPT-5.6 Sol (interactive ChatGPT resident)",
            "simulated_clock": None
            if self.target is None or self.target.clock is None
            else self.target.clock.isoformat(),
            "world_revision_before": None
            if self.target is None
            else int(self.target.store.current_world_revision()),
            "snapshot": payload,
        }
        print("MANUAL_RESIDENT_PENDING_BEGIN")
        print(json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2, default=str))
        print("MANUAL_RESIDENT_PENDING_END")
        raise ManualDecisionRequired(key)


class ManualSummary:
    model_id = "gpt-5.6-sol-interactive-resident"

    def __init__(self, decisions: dict[str, Any]):
        self.decisions = decisions
        self.replayed = 0
        self.pending = 0
        self.target = None

    def __call__(self, request: Any) -> str:
        payload = {
            "summary_request_type": type(request).__name__,
            "request": portable(request),
        }
        key = decision_key(payload)
        raw = self.decisions.get(key)
        if raw is not None:
            if not isinstance(raw, dict) or raw.get("kind") != "summary":
                raise ValueError(f"decision {key} is not summary")
            text_value = str(raw.get("summary") or "").strip()
            if not text_value:
                raise ValueError("blank summary")
            self.replayed += 1
            return text_value
        self.pending += 1
        envelope = {
            "schema": "aios.segment003.manual-summary.pending.v1",
            "decision_key": key,
            "resident_model": "GPT-5.6 Sol (interactive ChatGPT resident)",
            "simulated_clock": None
            if self.target is None or self.target.clock is None
            else self.target.clock.isoformat(),
            "world_revision_before": None
            if self.target is None
            else int(self.target.store.current_world_revision()),
            "summary_request": payload,
        }
        print("MANUAL_SUMMARY_PENDING_BEGIN")
        print(json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2, default=str))
        print("MANUAL_SUMMARY_PENDING_END")
        raise ManualDecisionRequired(key)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", required=True)
    ap.add_argument("--source-world", required=True)
    ap.add_argument("--working-world", required=True)
    ap.add_argument("--after-event-id", required=True)
    ap.add_argument("--segment-end", required=True)
    ap.add_argument("--expected-world-sha256", required=True)
    ap.add_argument("--expected-revision", type=int, required=True)
    ap.add_argument("--expected-subject", required=True)
    ap.add_argument("--decisions", required=True)
    ap.add_argument("--state-out", required=True)
    ap.add_argument("--snapshot-out", required=True)
    ap.add_argument("--event-trace-out", required=True)
    args = ap.parse_args()

    source = Path(args.source_world).resolve()
    working = Path(args.working_world).resolve()
    working.parent.mkdir(parents=True, exist_ok=True)
    if sha256_file(source) != args.expected_world_sha256:
        raise RuntimeError("source world sha mismatch")
    shutil.copy2(source, working)

    decisions = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
    scenario = load_scenario_json(Path(args.fixture).read_text(encoding="utf-8"))
    if scenario.subject_id != args.expected_subject:
        raise RuntimeError("fixture subject mismatch")

    resident = ManualResident(decisions)
    summary = ManualSummary(decisions)
    target = CurrentCoreHabitationTarget(
        model_id=resident.model_id,
        subject_id=args.expected_subject,
        db_path=working,
        model_handler=resident,
        round_summary_handler=summary,
        dimension_summary_handler=summary,
        require_fresh=False,
    )
    resident.target = target
    summary.target = target

    if int(target.store.current_world_revision()) != args.expected_revision:
        raise RuntimeError(f"revision mismatch {target.store.current_world_revision()}")
    if int(target.index.watermark()) != args.expected_revision:
        raise RuntimeError(f"watermark mismatch {target.index.watermark()}")

    print(
        "RESTORE_OK "
        + json.dumps(
            {
                "subject_id": target.subject_id,
                "world_revision": int(target.store.current_world_revision()),
                "index_watermark": int(target.index.watermark()),
                "clock": None if target.clock is None else target.clock.isoformat(),
                "world_sha256": sha256_file(working),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    visible = [e for e in scenario.events if e.deliver_to_resident]
    ids = [e.event_id for e in visible]
    if args.after_event_id in ids:
        start = ids.index(args.after_event_id) + 1
    elif args.after_event_id == "d026-pos":
        # Segment 003 fixture intentionally contains only future events.
        # The source checkpoint proves d026-pos is already consumed.
        start = 0
    else:
        raise RuntimeError("cursor not found")
    end_at = parse_dt(args.segment_end)
    last = args.after_event_id
    delivered = 0
    event_trace = []

    def write_state(status: str):
        Path(args.state_out).write_text(
            json.dumps(
                {
                    "status": status,
                    "last_consumed_external_event_id": last,
                    "simulated_clock": None
                    if target.clock is None
                    else target.clock.isoformat(),
                    "world_revision": int(target.store.current_world_revision()),
                    "index_watermark": int(target.index.watermark()),
                    "world_sha256": sha256_file(working),
                    "resident_replayed_calls": resident.replayed,
                    "summary_replayed_calls": summary.replayed,
                    "delivered_external_events": delivered,
                },
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        Path(args.event_trace_out).write_text(
            json.dumps(event_trace, ensure_ascii=False, sort_keys=True, indent=2, default=str)
            + "\n",
            encoding="utf-8",
        )

    try:
        for event in visible[start:]:
            if event.occurred_at > end_at:
                break
            advance = target.advance_to(event.occurred_at)
            result = target.handle_event(event.resident_view())
            last = event.event_id
            delivered += 1
            event_trace.append(
                {
                    "event_id": event.event_id,
                    "occurred_at": event.occurred_at.isoformat(),
                    "channel": event.channel,
                    "world_revision": int(target.store.current_world_revision()),
                    "advance": portable(advance),
                    "result": portable(result),
                }
            )
        final_advance = target.advance_to(end_at)
        event_trace.append(
            {
                "segment_end": end_at.isoformat(),
                "world_revision": int(target.store.current_world_revision()),
                "advance": portable(final_advance),
            }
        )
    except ManualDecisionRequired as exc:
        write_state("pending")
        print(f"SEG003_STATUS=pending decision_key={exc}")
        print(f"SEG003_CURSOR={last}")
        print(f"SEG003_WORLD_REVISION={int(target.store.current_world_revision())}")
        print(f"SEG003_RESIDENT_REPLAYED={resident.replayed}")
        print(f"SEG003_SUMMARY_REPLAYED={summary.replayed}")
        return 42

    snapshot = target.audit_snapshot()
    Path(args.snapshot_out).write_text(
        json.dumps(portable(snapshot), ensure_ascii=False, sort_keys=True, indent=2, default=str)
        + "\n",
        encoding="utf-8",
    )
    write_state("segment_complete")
    print("SEG003_STATUS=completed")
    print(
        "SEG003_FINAL "
        + json.dumps(
            {
                "last_consumed_external_event_id": last,
                "world_revision": int(target.store.current_world_revision()),
                "index_watermark": int(target.index.watermark()),
                "world_sha256": sha256_file(working),
                "resident_calls": resident.replayed,
                "summary_calls": summary.replayed,
                "delivered_external_events": delivered,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
