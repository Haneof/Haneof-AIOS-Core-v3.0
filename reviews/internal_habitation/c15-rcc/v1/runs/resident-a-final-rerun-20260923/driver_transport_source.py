#!/usr/bin/env python3
"""C15-RCC-RES-A-RERUN-001 canonical Phase-A driver (mechanical transport only).

This process is transport infrastructure. It:
- executes the frozen three-phase release commands by path,
- advances virtual time and runs only normally-due Core work,
- writes every RuntimeSnapshot / summary request that needs a model decision to
  the run directory as immutable checkpoint evidence,
- blocks until the Resident model authors a decision file,
- mechanically executes exactly the chosen legal capability calls.

It never decides cognition, never classifies meaning, never fabricates refs.
"""
from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import sys
import time
import traceback
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

REPO = Path("/home/user/Haneof-AIOS-Core-v3.0")
sys.path.insert(0, str(REPO / "src"))

from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import as_utc
from aios_core.contracts.enums import WakeSource
from aios_core.query.search import WorldSearchIndex
from aios_core.review import ReviewSchedulePolicy
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake.service import WakeBus

RELEASE_DIR = REPO / "reviews/internal_habitation/c15-rcc/v1/release"
RELEASE_OP = RELEASE_DIR / "release_operator.py"
MECH_INGEST = RELEASE_DIR / "mechanical_ingest_adapter.py"
CONV_INGEST = RELEASE_DIR / "canonical_conversation_ingest.py"

RUN_DIR = REPO / "reviews/internal_habitation/c15-rcc/v1/runs/resident-a-final-rerun-20260923"
WORLD_DB = RUN_DIR / "private_world.sqlite"
INDEX_DB = RUN_DIR / "world_index.sqlite"
RELEASE_STATE = RUN_DIR / "release_state.json"
CURRENT_EVENT = RUN_DIR / "current-event.json"
EVENTS_DIR = RUN_DIR / "cursor_events"
CKPT_DIR = RUN_DIR / "checkpoints"
DECISIONS_DIR = RUN_DIR / "decisions"
STAGES_DIR = RUN_DIR / "stages"
MAILBOX = Path("/tmp/c15r/mailbox")
PENDING_PTR = MAILBOX / "pending.json"
DECISION_FILE = MAILBOX / "decision.json"
LOG = Path("/tmp/c15r/driver.log")

PY = "/tmp/venv311/bin/python"
PHASE = "A"
SESSION_ID = "resident-a-final-rerun-20260923-001"
SUBJECT_ID = "user_1"
STOP_AFTER_CURSOR = 13

_seq = 0

def log(msg: str) -> None:
    line = f"[{datetime.utcnow().isoformat()}Z] {msg}"
    with LOG.open("a") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


def _jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=repr))
    tmp.replace(path)


def _await_decision(kind: str, ckpt_path: Path, tag: str) -> dict:
    _write(PENDING_PTR, {"kind": kind, "checkpoint": str(ckpt_path), "tag": tag})
    log(f"AWAITING-DECISION kind={kind} tag={tag} ckpt={ckpt_path}")
    while True:
        if DECISION_FILE.exists():
            try:
                raw = DECISION_FILE.read_text()
                payload = json.loads(raw)
            except json.JSONDecodeError:
                time.sleep(0.5)
                continue
            consumed = DECISIONS_DIR / f"{tag}.json"
            _write(consumed, payload)
            try:
                DECISION_FILE.unlink()
            except OSError:
                pass
            if PENDING_PTR.exists():
                try:
                    PENDING_PTR.unlink()
                except OSError:
                    pass
            log(f"DECISION-RECEIVED tag={tag}")
            return payload
        time.sleep(0.5)


def model_handler(snapshot: RuntimeSnapshot) -> ModelDirective:
    global _seq
    _seq += 1
    tag = f"dec-{_seq:04d}"
    cockpit_view = _jsonable(snapshot.cockpit)
    history = _jsonable(snapshot.capability_history)
    payload = {
        "user_input": snapshot.user_input,
        "wake_reason": snapshot.wake_reason,
        "cockpit": cockpit_view,
        "capability_catalog": _jsonable(snapshot.capability_catalog),
        "capability_history": history,
        "round_index": snapshot.round_index,
        "remaining_tool_rounds": snapshot.remaining_tool_rounds,
    }
    ckpt = CKPT_DIR / f"{tag}.json"
    _write(ckpt, payload)
    decision = _await_decision("model_directive", ckpt, tag)

    calls_raw = decision.get("capability_calls") or []
    if calls_raw:
        calls = tuple(
            CapabilityCall(
                name=str(item["name"]),
                arguments=dict(item.get("arguments") or {}),
            )
            for item in calls_raw
        )
        return ModelDirective(capability_calls=calls)
    if decision.get("silence") is True:
        return ModelDirective(silence=True)
    response = decision.get("response")
    if isinstance(response, str) and response.strip():
        return ModelDirective(response=response)
    raise ValueError(f"malformed decision payload at tag={tag}: keys={sorted(decision)}")


def dimension_summary_handler(inp: Any) -> str:
    global _seq
    _seq += 1
    tag = f"sum-{_seq:04d}"
    payload = _jsonable(getattr(inp, "model_dump", lambda **_: repr(inp))(mode="json"))
    ckpt = CKPT_DIR / f"{tag}.json"
    _write(ckpt, payload)
    decision = _await_decision("dimension_summary", ckpt, tag)
    text = decision.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"dimension summary decision must carry non-blank text (tag={tag})")
    return text


def run_cmd(args: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [PY, *args], capture_output=True, text=True, cwd=str(REPO)
    )
    if proc.returncode != 0:
        log(f"CMD-FAIL rc={proc.returncode} args={args}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        raise RuntimeError(f"command failed: {args}")
    return proc


def parse_ingest_ref(stdout: str) -> str:
    data = json.loads(stdout.strip().splitlines()[-1])
    if isinstance(data, dict):
        ref = data.get("ingest_ref") or data.get("ref") or data.get("observation_ref")
        if isinstance(ref, dict):
            return f"{ref['object_id']}@{int(ref['revision'])}"
        if isinstance(ref, str):
            return ref
    raise ValueError(f"cannot parse ingest ref from stdout: {stdout[-500:]}")


class Driver:
    def __init__(self) -> None:
        for path in (WORLD_DB, INDEX_DB):
            if path.exists():
                raise SystemExit(f"fresh-world violation: {path} already exists")
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        for d in (EVENTS_DIR, CKPT_DIR, DECISIONS_DIR, STAGES_DIR, MAILBOX):
            d.mkdir(parents=True, exist_ok=True)
        self.store = SQLiteWorldStore(WORLD_DB)
        self.index = WorldSearchIndex(INDEX_DB, store=self.store)
        self.index.rebuild()
        self.runtime = FusedTurnRuntime(
            store=self.store,
            index=self.index,
            model_handler=model_handler,
            subject_id=SUBJECT_ID,
            round_summary_handler=None,
            dimension_summary_handler=dimension_summary_handler,
            max_tool_rounds=8,
        )
        self.review_policy = ReviewSchedulePolicy()
        self.clock: datetime | None = None
        self.next_review_at: datetime | None = None
        self.turn_index = 0

    # ---- clock / due work -------------------------------------------------
    def _next_due_task_at(self, limit: datetime) -> datetime | None:
        from aios_core.contracts.enums import TaskState
        cands = []
        for task in self.runtime.execution_world.current_tasks():
            if task.task_state is not TaskState.WAITING_TIME or task.next_wake_at is None:
                continue
            due = as_utc(task.next_wake_at, "next_wake_at")
            if due <= limit:
                if self.clock is not None and due < self.clock:
                    due = self.clock
                cands.append(due)
        return min(cands) if cands else None

    def _dispatch_pending_wakes(self, now: datetime) -> list[dict]:
        results = []
        for wake in self.runtime.wake_bus.pending_wakes():
            if wake.wake_source in {WakeSource.PERIODIC_REVIEW, WakeSource.USER_INTERACTION}:
                continue
            current = self.runtime.wake_bus.current_wake(wake.object_id)
            if current.wake_state.value not in {"new", "queued"}:
                continue
            result = self.runtime.run_wake(
                wake_ref=ObjectRef(object_id=current.object_id, revision=current.revision),
                now=now,
                step0=None,
            )
            results.append({
                "wake_id": result.wake_ref.object_id,
                "wake_revision": result.wake_ref.revision,
                "wake_source": wake.wake_source.value,
                "wake_state": result.wake.state,
                "delivery_response": result.delivery_response,
                "delivery_suppressed": result.delivery_suppressed,
                "runtime": _jsonable(result.runtime) if result.runtime is not None else {"invoked": False},
            })
        return results

    def _process_due_tasks(self, now: datetime) -> dict:
        task_wakes = self.runtime.execution_world.wake_due_tasks(now=now)
        wake_runs = self._dispatch_pending_wakes(now)
        return {"at": now.isoformat(), "task_wakes": [dataclasses.asdict(t) for t in task_wakes], "wake_runs": wake_runs}

    def _run_periodic_review(self, now: datetime) -> dict:
        review = self.runtime.run_periodic_review(now=now, policy=self.review_policy)
        if review is None:
            return {"at": now.isoformat(), "invoked": False, "reason": "not_due_or_suppressed_without_model_call"}
        return {
            "at": now.isoformat(),
            "invoked": True,
            "review_id": review.request.review_id,
            "wake_id": review.wake.wake_id,
            "wake_revision": review.wake.revision,
            "anchor_count": len(review.request.anchors),
            "runtime": _jsonable(review.runtime) if review.runtime is not None else {"invoked": False},
        }

    def advance_to(self, instant: datetime) -> dict:
        target = as_utc(instant, "instant")
        start = self.clock
        if self.clock is None:
            self.clock = target
            self.next_review_at = target + timedelta(hours=float(self.review_policy.interval_hours))
            result = {
                "from": None, "to": target.isoformat(), "task_cycles": [],
                "periodic_reviews": [], "background_cycles": 0,
                "dimension_summaries": None,
                "world_revision": int(self.store.current_world_revision()),
            }
            log(f"advance(init) -> {target.isoformat()}")
            return result
        if target < self.clock:
            raise ValueError("virtual clock cannot move backwards")
        task_cycles, review_runs, cycles = [], [], 0
        while True:
            task_at = self._next_due_task_at(target)
            review_at = self.next_review_at if (self.next_review_at is not None and self.next_review_at <= target) else None
            cands = [v for v in (task_at, review_at) if v is not None]
            if not cands:
                break
            tick = min(cands)
            if tick < self.clock:
                tick = self.clock
            self.clock = tick
            cycles += 1
            if cycles > 10000:
                raise RuntimeError("virtual scheduler safety guard")
            if task_at is not None and task_at <= tick:
                cyc = self._process_due_tasks(tick)
                if cyc["task_wakes"] or cyc["wake_runs"]:
                    task_cycles.append(cyc)
            if review_at is not None and review_at <= tick:
                review_runs.append(self._run_periodic_review(tick))
                self.next_review_at = review_at + timedelta(hours=float(self.review_policy.interval_hours))
            follow = self._process_due_tasks(tick)
            if follow["task_wakes"] or follow["wake_runs"]:
                task_cycles.append(follow)
        summaries = self.runtime.run_due_dimension_summaries(now=target, max_jobs=64)
        self.index.catch_up()
        self.clock = target
        result = {
            "from": start.isoformat() if start else None, "to": target.isoformat(),
            "task_cycles": task_cycles, "periodic_reviews": review_runs,
            "background_cycles": cycles,
            "dimension_summaries": _jsonable(summaries),
            "world_revision": int(self.store.current_world_revision()),
        }
        log(f"advance -> {target.isoformat()} wr={result['world_revision']} cycles={cycles} reviews={len(review_runs)} summary_commits={len(summaries.commits)}")
        return result

    # ---- cursor execution --------------------------------------------------
    def process_cursor(self, sequence: int) -> dict:
        staged: dict[str, Any] = {"sequence": sequence}
        # 1. reveal current event (reuse legal pending reveal if already emitted;
        #    duplicate reveal before durable ack is forbidden by the operator)
        state = json.loads(RELEASE_STATE.read_text())
        pending = state.get("pending_reveal")
        if pending and int(pending.get("sequence")) == sequence:
            event = json.loads(CURRENT_EVENT.read_text())
            if int(event.get("sequence")) != sequence or event.get("event_id") != pending.get("event_id"):
                raise RuntimeError("pending reveal in state does not match saved current-event.json")
            staged["reveal_reused"] = True
        else:
            proc = run_cmd([str(RELEASE_OP), "reveal", "--phase", PHASE, "--state", str(RELEASE_STATE)])
            CURRENT_EVENT.write_text(proc.stdout)
            event = json.loads(proc.stdout)
        (EVENTS_DIR / f"cursor-{sequence:03d}.json").write_text(json.dumps(event, ensure_ascii=False, indent=1))
        event_time = datetime.fromisoformat(event["occurred_at"])
        staged["event"] = event
        is_conversation = event.get("source_kind") == "conversation"
        ingest_ref: str
        conv_args: dict[str, str] = {}
        # 2. ingest durably
        if is_conversation:
            self.turn_index += 1
            proc = run_cmd([
                str(CONV_INGEST), "--world-db", str(WORLD_DB),
                "--session-id", SESSION_ID, "--turn-index", str(self.turn_index),
                "--event-file", str(CURRENT_EVENT),
            ])
            ingest_ref = parse_ingest_ref(proc.stdout)
            conv_args = {
                "--conversation-session-id": SESSION_ID,
                "--conversation-turn-index": str(self.turn_index),
            }
        else:
            proc = run_cmd([
                str(MECH_INGEST), "--world-db", str(WORLD_DB),
                "--event-file", str(CURRENT_EVENT),
            ])
            ingest_ref = parse_ingest_ref(proc.stdout)
        log(f"cursor {sequence} ingested -> {ingest_ref}")
        staged["ingest_ref"] = ingest_ref
        # 3. ack exact durable ref
        ack_args = [
            str(RELEASE_OP), "ack", "--phase", PHASE, "--state", str(RELEASE_STATE),
            "--world-db", str(WORLD_DB),
            "--sequence", str(sequence), "--event-id", event["event_id"],
            "--ingest-ref", ingest_ref,
            *sum(([k, v] for k, v in conv_args.items()), []),
        ]
        proc = run_cmd(ack_args)
        staged["ack"] = proc.stdout.strip()[-400:]
        log(f"cursor {sequence} acked")
        self.index.catch_up()
        # 4. normal AIOS processing
        adv = self.advance_to(event_time)
        staged["advance"] = adv
        if is_conversation:
            result = self.runtime.run_turn(
                session_id=SESSION_ID,
                turn_index=self.turn_index,
                user_input=str(event["resident_visible_payload"]),
                occurred_at=event_time,
            )
            self.index.catch_up()
            staged["turn"] = {
                "response": result.runtime.response,
                "silenced": result.runtime.silenced,
                "termination_reason": result.runtime.termination_reason,
                "capabilities": [c.name for c in result.runtime.capability_history],
                "recommended_memory_count": len(result.recommendation.cards),
                "world_revision": int(self.store.current_world_revision()),
            }
            log(f"cursor {sequence} turn done: term={result.runtime.termination_reason} caps={staged['turn']['capabilities']}")
            # due work that became actionable at the same instant after the turn
            post = self.advance_to(event_time)
            staged["post_turn_advance"] = post
        staged["world_revision"] = int(self.store.current_world_revision())
        staged["index_watermark"] = int(self.index.watermark())
        _write(STAGES_DIR / f"cursor-{sequence:03d}.json", staged)
        return staged

    def run(self) -> None:
        log("driver start (canonical Phase A rerun on final anchor)")
        state = json.loads(RELEASE_STATE.read_text())
        seq = int(state["next_sequence"])
        log(f"starting at cursor {seq}")
        while seq <= STOP_AFTER_CURSOR:
            self.process_cursor(seq)
            state = json.loads(RELEASE_STATE.read_text())
            nxt = int(state["next_sequence"])
            if nxt != seq + 1:
                raise RuntimeError(f"release-state did not advance: {seq} -> {nxt}")
            seq = nxt
        final = {
            "final_world_revision": int(self.store.current_world_revision()),
            "final_index_watermark": int(self.index.watermark()),
            "done_at_cursor": STOP_AFTER_CURSOR,
        }
        _write(MAILBOX / "phase_a_complete.json", final)
        log(f"PHASE A COMPLETE: {final}")


if __name__ == "__main__":
    try:
        Driver().run()
    except Exception:
        log("DRIVER-CRASH\n" + traceback.format_exc())
        raise
