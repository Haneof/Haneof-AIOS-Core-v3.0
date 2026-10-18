"""A-004 Phase A mechanical runner — transport/plumbing only.

This program may:
  - open the fresh private World/index created for this run;
  - catch the index up;
  - advance virtual/runtime time and execute DUE mechanical scheduling
    (tasks / wakes / periodic review / dimension summaries) through the
    real FusedTurnRuntime;
  - serialize RuntimeSnapshot / summary requests to files and execute the
    ModelDirective / summary text that the resident model session writes back;
  - persist checkpoints and audit logs.

This program may NOT:
  - decide semantics for the resident (no keyword rules, no scripted answers,
    no default directive, no fabricated usage/provenance/receipts);
  - reveal or inspect any fixture/future content.

Model/summary callbacks block on file handshakes:
  decision_requests/<id>.json  written by this runner (request)
  decision_responses/<id>.json written by the resident model session (response)
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

RUN_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[7]  # .../a004-rc
sys.path.insert(0, str(REPO_ROOT / "src"))

from aios_core.contracts.enums import TaskState, WakeState  # noqa: E402
from aios_core.contracts.refs import ObjectRef  # noqa: E402
from aios_core.contracts.time import as_utc  # noqa: E402
from aios_core.query.search import WorldSearchIndex  # noqa: E402
from aios_core.review import ReviewSchedulePolicy  # noqa: E402
from aios_core.runtime.capabilities import CapabilityCall  # noqa: E402
from aios_core.runtime.cognitive_runtime import ModelDirective  # noqa: E402
from aios_core.runtime.turn_execution import TurnAlreadyCompleted  # noqa: E402
from aios_core.runtime.turn_runtime import FusedTurnRuntime  # noqa: E402
from aios_core.storage.sqlite_store import SQLiteWorldStore  # noqa: E402

WORLD_DB = RUN_DIR / "world.db"
INDEX_DB = RUN_DIR / "index.db"
STATE_FILE = RUN_DIR / "runtime_state.json"
REQUESTS_DIR = RUN_DIR / "decision_requests"
RESPONSES_DIR = RUN_DIR / "decision_responses"
LOG_DIR = RUN_DIR / "logs"
CHECKPOINT_DIR = RUN_DIR / "checkpoints"

REVIEW_POLICY = ReviewSchedulePolicy()  # default interval_hours=24

REPLY_TIMEOUT_S = float(os.environ.get("A004_REPLY_TIMEOUT_S", "3600"))
REPLY_POLL_S = 0.5
MAX_DISPATCH_PASSES = 5


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(line: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / "runner.log"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{_now()} {line}\n")
        handle.flush()
        os.fsync(handle.fileno())


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _write_json(path: Path, payload: Any) -> str:
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False).encode("utf-8")
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)
    return _sha256_bytes(data)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _append_chain(entry: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / "decision_chain.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        handle.flush()


def _load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {
            "clock": None,
            "next_review_at": None,
            "last_cursor": 0,
            "session_turns": {},
            "world_revision_at_init": 0,
        }
    return _read_json(STATE_FILE)


def _save_state(state: dict[str, Any]) -> None:
    _write_json(STATE_FILE, state)


class ResidentBridge:
    """File-based request/response bridge to the resident model session."""

    def __init__(self) -> None:
        REQUESTS_DIR.mkdir(parents=True, exist_ok=True)
        RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
        existing = sorted(REQUESTS_DIR.glob("req-*.json"))
        self._seq = len(existing)
        self._handshake_log: list[dict[str, Any]] = []

    def _exchange(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._seq += 1
        request_id = f"req-{self._seq:04d}-{kind}-{uuid.uuid4().hex[:8]}"
        request = {
            "request_id": request_id,
            "kind": kind,
            "created_at": _now(),
            "payload": payload,
        }
        request_path = REQUESTS_DIR / f"{request_id}.json"
        request_sha = _write_json(request_path, request)
        _append_chain({
            "event": "request_written",
            "at": _now(),
            "request_id": request_id,
            "kind": kind,
            "request_sha256": request_sha,
        })
        _log(f"decision request written {request_id} kind={kind}")

        response_path = RESPONSES_DIR / f"{request_id}.json"
        deadline = time.time() + REPLY_TIMEOUT_S
        response: dict[str, Any] | None = None
        response_raw = b""
        while response is None:
            if response_path.exists():
                try:
                    candidate_raw = response_path.read_bytes()
                    candidate = json.loads(candidate_raw.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # The writer may still be mid-write; wait for a complete,
                    # parseable response instead of failing the model round.
                    candidate = None
                    candidate_raw = b""
                if isinstance(candidate, dict):
                    response = candidate
                    response_raw = candidate_raw
            if response is None and time.time() > deadline:
                raise TimeoutError(
                    f"resident model session did not answer {request_id} "
                    f"within {REPLY_TIMEOUT_S}s"
                )
            if response is None:
                time.sleep(REPLY_POLL_S)
        if response.get("request_id") != request_id:
            raise ValueError("response request_id mismatch")
        response_sha = _sha256_bytes(response_raw)
        _append_chain({
            "event": "response_read",
            "at": _now(),
            "request_id": request_id,
            "kind": kind,
            "response_sha256": response_sha,
        })
        _log(f"decision response read {request_id}")
        self._handshake_log.append(
            {
                "request_id": request_id,
                "kind": kind,
                "request_sha256": request_sha,
                "response_sha256": response_sha,
            }
        )
        return response

    # ---- Core callbacks -------------------------------------------------
    def model_handler(self, snapshot: Any) -> ModelDirective:
        payload = {
            "user_input": snapshot.user_input,
            "wake_reason": snapshot.wake_reason,
            "cockpit": _json_safe(snapshot.cockpit),
            "capability_catalog": _json_safe(snapshot.capability_catalog),
            "capability_history": [
                _json_safe(dataclasses.asdict(item))
                for item in snapshot.capability_history
            ],
            "round_index": snapshot.round_index,
            "remaining_tool_rounds": snapshot.remaining_tool_rounds,
            "model_attempt_id": snapshot.model_attempt_id,
        }
        response = self._exchange("model_directive", payload)
        directive = response.get("directive")
        if not isinstance(directive, dict):
            raise ValueError("response must contain object 'directive'")
        calls_raw = directive.get("capability_calls") or []
        calls: list[CapabilityCall] = []
        for item in calls_raw:
            if not isinstance(item, dict) or not str(item.get("name", "")).strip():
                raise ValueError("capability_calls entries need a non-blank name")
            args = item.get("arguments") or {}
            if not isinstance(args, dict):
                raise ValueError("capability call arguments must be an object")
            call_id = item.get("call_id")
            calls.append(
                CapabilityCall(
                    name=str(item["name"]),
                    arguments=dict(args),
                    call_id=str(call_id) if call_id else None,
                )
            )
        response_text = directive.get("response")
        silence = bool(directive.get("silence", False))
        # No usage, no provenance: this is a local resident model session, not a
        # provider call. Fabricating meter/receipt identity is forbidden.
        return ModelDirective(
            capability_calls=tuple(calls),
            response=response_text if response_text is not None else None,
            silence=silence,
            usage=None,
            provenance=None,
        )

    def round_summary_handler(self, request: Any) -> str:
        response = self._exchange(
            "round_summary",
            {"request": _json_safe(request.model_dump(mode="json"))},
        )
        text = response.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("round_summary response must contain non-blank 'text'")
        return text

    def dimension_summary_handler(self, inp: Any) -> str:
        response = self._exchange(
            "dimension_summary",
            {"input": _json_safe(inp.model_dump(mode="json"))},
        )
        text = response.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("dimension_summary response must contain non-blank 'text'")
        return text


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return json.loads(json.dumps(value, default=str, ensure_ascii=False))


class Runner:
    def __init__(self, subject_id: str) -> None:
        self.subject_id = subject_id
        self.bridge = ResidentBridge()
        self.store = SQLiteWorldStore(WORLD_DB)
        self.index = WorldSearchIndex(INDEX_DB, store=self.store)
        self.index.rebuild()
        self.runtime = FusedTurnRuntime(
            store=self.store,
            index=self.index,
            model_handler=self.bridge.model_handler,
            subject_id=subject_id,
            round_summary_handler=self.bridge.round_summary_handler,
            dimension_summary_handler=self.bridge.dimension_summary_handler,
            max_tool_rounds=8,
        )
        self.state = _load_state()

    def _next_due_task_at(self, limit: datetime) -> datetime | None:
        candidates: list[datetime] = []
        for task in self.runtime.execution_world.current_tasks():
            if task.task_state is not TaskState.WAITING_TIME:
                continue
            if task.next_wake_at is None:
                continue
            due = as_utc(task.next_wake_at, "next_wake_at")
            if due <= limit:
                clock = self._clock_dt()
                if clock is not None and due < clock:
                    due = clock
                candidates.append(due)
        return min(candidates) if candidates else None

    def _clock_dt(self) -> datetime | None:
        raw = self.state.get("clock")
        return None if raw is None else as_utc(datetime.fromisoformat(raw), "clock")

    # ---- attention-watch evaluation (mechanical replay of Core's own
    #      observation listener at step boundaries, since this run ingests
    #      through the release/mechanical adapter rather than through
    #      FusedTurnRuntime.reality_ingest) -------------------------------
    def _new_observations_after(self, world_revision: int) -> list[tuple[str, int]]:
        conn = sqlite3.connect(str(self.store.db_path), timeout=30.0)
        try:
            rows = conn.execute(
                "SELECT object_id, revision FROM object_revisions "
                "WHERE object_type = 'observation' AND world_revision > ? "
                "ORDER BY world_revision, rowid",
                (int(world_revision),),
            ).fetchall()
        finally:
            conn.close()
        return [(str(row[0]), int(row[1])) for row in rows]

    def _evaluate_attention_watches(self, note: str) -> list[dict[str, Any]]:
        watermark = int(self.state.get("watch_watermark", 0))
        receipts: list[dict[str, Any]] = []
        for object_id, revision in self._new_observations_after(watermark):
            ref = ObjectRef(object_id=object_id, revision=revision)
            produced = self.runtime.attention_watches.evaluate_observation(ref)
            for receipt in produced:
                receipts.append(
                    {
                        "note": note,
                        "observation_ref": {
                            "object_id": object_id,
                            "revision": revision,
                        },
                        "receipt": (
                            dataclasses.asdict(receipt)
                            if dataclasses.is_dataclass(receipt)
                            else str(receipt)
                        ),
                    }
                )
        self.state["watch_watermark"] = int(self.store.current_world_revision())
        if receipts:
            _log(
                f"attention watch evaluation ({note}) emitted {len(receipts)} wake(s)"
            )
        return receipts

    def _dispatch_pending_wakes(self, now: datetime) -> list[dict[str, Any]]:
        from aios_core.contracts.enums import WakeSource

        results: list[dict[str, Any]] = []
        for wake in self.runtime.wake_bus.pending_wakes():
            if wake.wake_source in {
                WakeSource.PERIODIC_REVIEW,
                WakeSource.USER_INTERACTION,
            }:
                continue
            current = self.runtime.wake_bus.current_wake(wake.object_id)
            if current.wake_state.value not in {"new", "queued"}:
                continue
            result = self.runtime.run_wake(
                wake_ref=ObjectRef(object_id=current.object_id, revision=current.revision),
                now=now,
                step0=None,
                token_budget=None,
            )
            results.append(
                {
                    "wake_id": result.wake_ref.object_id,
                    "wake_revision": result.wake_ref.revision,
                    "wake_source": wake.wake_source.value,
                    "wake_state": result.wake.state,
                    "delivery_response": result.delivery_response,
                    "delivery_suppressed": result.delivery_suppressed,
                    "runtime": _runtime_view(result.runtime),
                }
            )
        return results

    def _process_due_tasks(self, now: datetime) -> dict[str, Any]:
        task_wakes = self.runtime.execution_world.wake_due_tasks(now=now)
        wake_runs = self._dispatch_pending_wakes(now)
        return {
            "at": now.isoformat(),
            "task_wakes": [dataclasses.asdict(item) for item in task_wakes],
            "wake_runs": wake_runs,
        }

    def _run_periodic_review(self, now: datetime) -> dict[str, Any]:
        review = self.runtime.run_periodic_review(
            now=now,
            policy=REVIEW_POLICY,
            token_budget=None,
        )
        if review is None:
            return {
                "at": now.isoformat(),
                "invoked": False,
                "reason": "not_due_or_suppressed_without_model_call",
            }
        return {
            "at": now.isoformat(),
            "invoked": True,
            "review_id": review.request.review_id,
            "wake_id": review.wake.wake_id,
            "anchor_count": len(review.request.anchors),
            "runtime": _runtime_view(review.runtime),
        }

    def _run_dimension_summaries(self, now: datetime) -> dict[str, Any]:
        if self.runtime.dimension_summary_scheduler is None:
            return {"at": now.isoformat(), "invoked": False, "reason": "not_configured"}
        result = self.runtime.run_due_dimension_summaries(now=now, max_jobs=64)
        return {
            "at": now.isoformat(),
            "invoked": True,
            "attempted_jobs": len(result.attempted_jobs),
            "commits": [dataclasses.asdict(item) for item in result.commits],
            "skipped_unchanged": len(result.skipped_unchanged),
            "skipped_empty": len(result.skipped_empty),
            "truncated": result.truncated,
        }

    def advance_to(self, instant: datetime) -> dict[str, Any]:
        target = as_utc(instant, "instant")
        start = self._clock_dt()
        task_cycles: list[dict[str, Any]] = []
        review_runs: list[dict[str, Any]] = []
        wake_runs_final: list[dict[str, Any]] = []
        cycles = 0

        if start is None:
            self.state["clock"] = target.isoformat()
            self.state["next_review_at"] = (
                target + timedelta(hours=float(REVIEW_POLICY.interval_hours))
            ).isoformat()
        else:
            if target < start:
                raise ValueError("virtual clock cannot move backwards")
            while True:
                task_at = self._next_due_task_at(target)
                raw_review = self.state.get("next_review_at")
                review_at = None
                if raw_review is not None:
                    candidate = as_utc(datetime.fromisoformat(raw_review), "next_review_at")
                    if candidate <= target:
                        review_at = candidate
                candidates = [v for v in (task_at, review_at) if v is not None]
                if not candidates:
                    break
                tick = min(candidates)
                clock = self._clock_dt()
                if clock is not None and tick < clock:
                    tick = clock
                self.state["clock"] = tick.isoformat()
                cycles += 1
                if cycles > 10_000:
                    raise RuntimeError("virtual scheduler exceeded safety guard")
                if task_at is not None and task_at <= tick:
                    cycle = self._process_due_tasks(tick)
                    if cycle["task_wakes"] or cycle["wake_runs"]:
                        task_cycles.append(cycle)
                if review_at is not None and review_at <= tick:
                    review_runs.append(self._run_periodic_review(tick))
                    self.state["next_review_at"] = (
                        review_at + timedelta(hours=float(REVIEW_POLICY.interval_hours))
                    ).isoformat()
                follow_up = self._process_due_tasks(tick)
                if follow_up["task_wakes"] or follow_up["wake_runs"]:
                    task_cycles.append(follow_up)

        # Wake work genuinely due at the target timestamp (bounded passes).
        for _pass in range(MAX_DISPATCH_PASSES):
            cycle = self._process_due_tasks(target)
            if cycle["task_wakes"] or cycle["wake_runs"]:
                wake_runs_final.append(cycle)
            else:
                break

        summaries = self._run_dimension_summaries(target)
        self.state["clock"] = target.isoformat()
        return {
            "from": None if start is None else start.isoformat(),
            "to": target.isoformat(),
            "task_cycles": task_cycles,
            "periodic_reviews": review_runs,
            "wake_passes": wake_runs_final,
            "dimension_summaries": summaries,
            "background_cycles": cycles,
            "world_revision": int(self.store.current_world_revision()),
        }

    # ---- commands -------------------------------------------------------
    def step(self, args: argparse.Namespace) -> None:
        event_payload = _read_json(Path(args.event_file))
        occurred_raw = None
        for key in ("occurred_at", "occurredAt"):
            if isinstance(event_payload, dict) and event_payload.get(key):
                occurred_raw = event_payload[key]
                break
        if occurred_raw is None and isinstance(event_payload, dict):
            # fall back to a nested envelope
            inner = event_payload.get("event") or event_payload.get("projection") or {}
            if isinstance(inner, dict):
                occurred_raw = inner.get("occurred_at")
        if not isinstance(occurred_raw, str):
            raise ValueError("cannot mechanically determine event occurred_at")
        occurred_at = as_utc(datetime.fromisoformat(occurred_raw.replace("Z", "+00:00")), "occurred_at")

        _log(f"step cursor={args.cursor} start occurred_at={occurred_at.isoformat()}")
        self.index.catch_up()

        watch_receipts: list[dict[str, Any]] = []
        watch_receipts.extend(
            self._evaluate_attention_watches(note=f"cursor_{int(args.cursor):02d}:pre_advance")
        )

        advance = self.advance_to(occurred_at)

        turn_result = None
        if args.turn_index is not None:
            session = args.session_id
            turn_index = int(args.turn_index)
            text = Path(args.turn_text_file).read_text(encoding="utf-8")
            if not text.strip():
                raise ValueError("turn text file is blank")
            try:
                turn_result = self.runtime.run_turn(
                    session_id=session,
                    turn_index=turn_index,
                    user_input=text,
                    occurred_at=occurred_at,
                )
                turn_view = {
                    "session_id": session,
                    "turn_index": turn_index,
                    "runtime": _runtime_view(turn_result.runtime),
                    "world_revision": int(self.store.current_world_revision()),
                }
            except TurnAlreadyCompleted as exc:
                # Durable assistant output already exists for this turn identity;
                # re-admission completed the claim mechanically and no model round
                # may be re-applied.
                ref = exc.assistant_ref
                assistant_text = None
                if ref is not None:
                    payload = self.store.get_payload(
                        ref.object_id, revision=ref.revision
                    )
                    assistant_text = payload.get("value")
                turn_view = {
                    "session_id": session,
                    "turn_index": turn_index,
                    "idempotent_replay": True,
                    "assistant_ref": (
                        None
                        if ref is None
                        else {"object_id": ref.object_id, "revision": ref.revision}
                    ),
                    "assistant_text_sha256": (
                        hashlib.sha256(assistant_text.encode("utf-8")).hexdigest()
                        if isinstance(assistant_text, str)
                        else None
                    ),
                    "world_revision": int(self.store.current_world_revision()),
                }
            self.state["session_turns"][session] = max(
                int(self.state["session_turns"].get(session, 0)), turn_index
            )
        else:
            turn_view = None

        watch_receipts.extend(
            self._evaluate_attention_watches(note=f"cursor_{int(args.cursor):02d}:post_turn")
        )

        self.index.catch_up()

        # Any wake created during this step's processing at/ before target that is
        # still pending gets one more bounded dispatch opportunity at target.
        extra_passes = []
        for _pass in range(MAX_DISPATCH_PASSES):
            cycle = self._process_due_tasks(occurred_at)
            if cycle["task_wakes"] or cycle["wake_runs"]:
                extra_passes.append(cycle)
            else:
                break
        self.index.catch_up()

        self.state["last_cursor"] = int(args.cursor)
        _save_state(self.state)

        pending = [
            {
                "wake_id": w.object_id,
                "revision": w.revision,
                "source": w.wake_source.value,
                "state": w.wake_state.value,
            }
            for w in self.runtime.wake_bus.pending_wakes()
        ]

        checkpoint = {
            "cursor": int(args.cursor),
            "occurred_at": occurred_at.isoformat(),
            "advance": advance,
            "user_turn": turn_view,
            "extra_wake_passes": extra_passes,
            "clock": self.state.get("clock"),
            "next_review_at": self.state.get("next_review_at"),
            "world_revision": int(self.store.current_world_revision()),
            "index_watermark": int(self.index.watermark()),
            "index_lag": int(self.index.lag()),
            "attention_watch_receipts": watch_receipts,
            "pending_wakes_after_step": pending,
            "handshake_log": self.bridge._handshake_log,
            "completed_at": _now(),
        }
        sha = _write_json(CHECKPOINT_DIR / f"checkpoint_cursor_{int(args.cursor):02d}.json", checkpoint)
        result_sha = _write_json(
            RUN_DIR / f"step_{int(args.cursor):02d}_result.json", checkpoint
        )
        _log(
            f"step cursor={args.cursor} done world_revision={checkpoint['world_revision']} "
            f"watermark={checkpoint['index_watermark']} pending_wakes={len(pending)} "
            f"checkpoint={sha} result={result_sha}"
        )
        print(json.dumps({
            "status": "ok",
            "cursor": int(args.cursor),
            "world_revision": checkpoint["world_revision"],
            "index_watermark": checkpoint["index_watermark"],
            "pending_wakes": len(pending),
            "model_decisions": len(self.bridge._handshake_log),
        }, ensure_ascii=False))

    def status(self, _args: argparse.Namespace) -> None:
        self.index.catch_up()
        pending = [
            {
                "wake_id": w.object_id,
                "revision": w.revision,
                "source": w.wake_source.value,
                "state": w.wake_state.value,
            }
            for w in self.runtime.wake_bus.pending_wakes()
        ]
        payloads = self.store.list_payloads(subject_id=self.subject_id)
        by_type: dict[str, int] = {}
        for payload in payloads:
            key = str(payload.get("object_type") or "?")
            by_type[key] = by_type.get(key, 0) + 1
        print(json.dumps({
            "world_revision": int(self.store.current_world_revision()),
            "index_watermark": int(self.index.watermark()),
            "index_lag": int(self.index.lag()),
            "clock": self.state.get("clock"),
            "next_review_at": self.state.get("next_review_at"),
            "last_cursor": self.state.get("last_cursor"),
            "object_counts": dict(sorted(by_type.items())),
            "pending_wakes": pending,
        }, ensure_ascii=False, indent=2))


def _runtime_view(result: Any) -> dict[str, Any] | None:
    if result is None:
        return {"invoked": False}
    return {
        "invoked": True,
        "response": result.response,
        "silenced": result.silenced,
        "model_rounds": result.model_rounds,
        "termination_reason": result.termination_reason,
        "capabilities": [item.name for item in result.capability_history],
        "model_usage_complete": result.model_usage_complete,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="A-004 mechanical Phase A runner")
    parser.add_argument("--subject", required=True, help="subject id from the revealed envelope")
    sub = parser.add_subparsers(dest="command", required=True)

    step_p = sub.add_parser("step")
    step_p.add_argument("--cursor", type=int, required=True)
    step_p.add_argument("--event-file", required=True)
    step_p.add_argument("--session-id", default=None)
    step_p.add_argument("--turn-index", type=int, default=None)
    step_p.add_argument("--turn-text-file", default=None)
    step_p.set_defaults(func="step")

    status_p = sub.add_parser("status")
    status_p.set_defaults(func="status")

    args = parser.parse_args()
    if args.func == "step" and (args.turn_index is None) != (args.turn_text_file is None):
        parser.error("--turn-index and --turn-text-file must be provided together")
    if args.func == "step" and args.turn_index is not None and not args.session_id:
        parser.error("--session-id required for user turns")

    runner = Runner(subject_id=args.subject)
    getattr(runner, args.func)(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
