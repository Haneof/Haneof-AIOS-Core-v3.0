"""Long-lived Resident runner: the real AIOS runtime stays in memory.

Why a daemon instead of one process per step
--------------------------------------------
Core mints a fresh opaque Observation id for the current utterance inside
``run_turn``. A step-level restore+replay harness therefore invalidates any
evidence ref the Resident pinned to that utterance (observed as
``StoreError: object not found`` while trying to ``propose_entity``). Keeping the
runtime alive while the Resident thinks preserves Core's real behaviour and lets
the Resident pin live evidence.

Crash recovery is explicit and lossy-by-design: if this process dies mid-step the
step's partial writes are rolled back from the pre-step backup and the step is
re-opened from its first checkpoint, i.e. the Resident is asked again. Authored
but never-executed decisions are dropped rather than replayed against stale ids.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .driver import (
    BASE_DIR,
    MODEL_ID,
    RUN_ID,
    RunState,
    _append_jsonl,
    _find_event,
    _pending_fingerprint,
    _read_json,
    _read_jsonl,
    _shrink_advance,
    _write_json,
    backup_db,
    build_steps,
    build_target,
    decisions_path,
    ingest_decoy,
    load_life,
    parse_instant,
    restore_db,
    step_key,
)
from .bridge import BlockingDecisionSource, ResidentBridge


def _log(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--segment", required=True)
    parser.add_argument("--roll-hour", type=int, default=4)
    parser.add_argument("--roll-minute", type=int, default=0)
    args = parser.parse_args()

    state = RunState(BASE_DIR)
    (BASE_DIR / "run" / "DONE").unlink(missing_ok=True)
    segment_id = args.segment
    segment_dir = BASE_DIR / "life" / segment_id

    events = load_life(segment_dir)
    steps = build_steps(events, args.roll_hour, args.roll_minute)
    existing = state.load()

    fresh = not state.db_path.exists()
    target, holder = build_target(state, require_fresh=fresh)
    _log({"phase": "start", "fresh_world": fresh, "steps": len(steps),
          "clock": None if target.clock is None else target.clock.isoformat()})

    cursor_step = 0
    if existing.get("segment_id") == segment_id:
        wanted = existing.get("next_step_key")
        if wanted is None and "next_step_key" in existing:
            cursor_step = len(steps)
        else:
            for candidate in steps:
                if step_key(segment_id, candidate) == wanted:
                    cursor_step = candidate["index"]
                    break
            else:
                raise RuntimeError(f"durable cursor {wanted!r} not in regenerated steps")

    if cursor_step == 0:
        decoy_path = segment_dir / "decoy.jsonl"
        if decoy_path.exists():
            receipts = ingest_decoy(state, _read_jsonl(decoy_path))
            _log({"phase": "decoy_ingest", "receipts": receipts})
            target, holder = build_target(state, require_fresh=False)

    if existing.get("clock"):
        cursor_time = parse_instant(existing["clock"])
        current = target.clock
        if current is None:
            target.advance_to(cursor_time)
        elif current < cursor_time:
            _log({"phase": "clock_regap", "restored_clock": current.isoformat(),
                  "cursor": cursor_time.isoformat()})
            target.advance_to(cursor_time)

    def _mark_pending(record: Mapping[str, Any]) -> None:
        current_state = state.load()
        current_state["pending"] = record
        current_state["clock"] = current_state.get("clock") or record["simulated_at"]
        state.save(current_state)

    while cursor_step < len(steps):
        step = steps[cursor_step]
        key = step_key(segment_id, step)
        journal = decisions_path(state, key)

        stale = existing.get("pending")
        if isinstance(stale, Mapping) and stale.get("step_key") == key:
            restore_db(state.db_path, state.backup_path)
            if journal.exists():
                dropped = len(_read_jsonl(journal))
                journal.unlink()
                _log({"phase": "crash_recovery", "step_key": key,
                      "dropped_unexecuted_decisions": dropped})
            else:
                _log({"phase": "crash_recovery", "step_key": key})
            (state.run_dir / "pending.json").unlink(missing_ok=True)
        else:
            backup_db(state.db_path, state.backup_path)

        bridge = ResidentBridge(
            model_id=MODEL_ID,
            step_key=key,
            source=BlockingDecisionSource(
                journal,
                state.pending_path,
                on_announce=_mark_pending,
            ),
            snapshots_dir=state.snapshots_dir,
            segment_id=segment_id,
            simulated_at=step["at"],
            world_revision_reader=target.store.current_world_revision,
            run_id=RUN_ID,
        )
        holder.current = bridge

        if step["kind"] == "advance":
            result = target.advance_to(parse_instant(step["at"]))
            record: dict[str, Any] = {
                "phase": "advance", "at": step["at"], "result": _shrink_advance(result)
            }
        else:
            from tests.habitation.harness import ResidentEvent

            life_event = _find_event(events, step["event_id"])
            result = target.handle_event(
                ResidentEvent(
                    event_id=life_event.event_id,
                    occurred_at=life_event.occurred_at,
                    channel=life_event.channel,
                    payload=life_event.payload,
                    metadata=life_event.metadata,
                )
            )
            record = {
                "phase": "event",
                "event_id": life_event.event_id,
                "channel": life_event.channel,
                "result": result,
            }

        for entry in bridge.served:
            _append_jsonl(
                state.trace_path,
                {
                    "run_id": RUN_ID,
                    "segment_id": segment_id,
                    "step_key": key,
                    "checkpoint_id": entry["checkpoint_id"],
                    "kind": entry["kind"],
                    "simulated_at": step["at"],
                    "model_id": MODEL_ID,
                    "input_fingerprint": entry["input_fingerprint"],
                    "input_fingerprint_at_pending": _pending_fingerprint(
                        state, entry["checkpoint_id"]
                    ),
                    "world_revision_before": entry["world_revision_before"],
                    "world_revision_after": int(target.store.current_world_revision()),
                    "decision": entry["decision"],
                },
            )

        record["checkpoints"] = len(bridge.served)
        record["world_revision"] = int(target.store.current_world_revision())
        _log(record)

        cursor_step += 1
        existing = {
            **existing,
            "run_id": RUN_ID,
            "segment_id": segment_id,
            "cursor_step": cursor_step,
            "next_step_key": (
                step_key(segment_id, steps[cursor_step])
                if cursor_step < len(steps)
                else None
            ),
            "clock": step["at"],
            "pending": None,
            "world_revision": int(target.store.current_world_revision()),
            "index_watermark": int(target.index.watermark()),
        }
        state.save(existing)

    _log({"phase": "segment_complete", "steps": len(steps),
          "world_revision": int(target.store.current_world_revision()),
          "clock": step["at"]})
    (BASE_DIR / "run" / "DONE").write_text(
        datetime.now().isoformat() + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
