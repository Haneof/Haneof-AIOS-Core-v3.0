"""Mechanical Resident A transport.

This process only moves bytes through the existing AIOS runtime. It does not
classify life meaning, choose claims, or map events to cognition. When the
runtime asks for a model decision or a summary text, it writes the exact
request and waits for a Resident-authored directive file.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from aios_core.contracts.refs import ObjectRef
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries.dimension_summary import DimensionSummaryInput


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: _jsonable(getattr(value, name))
            for name in value.__dataclass_fields__
        }
    return str(value)


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(_jsonable(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


class ResidentTransport:
    def __init__(self, run_dir: Path, job: dict[str, Any]) -> None:
        self.run_dir = run_dir
        self.job = job
        self.pending = run_dir / "pending"
        self.pending.mkdir(parents=True, exist_ok=True)
        self.request_path = self.pending / "request.json"
        self.ready_path = self.pending / "request.ready"
        self.directive_path = self.pending / "directive.json"
        self.status_path = self.pending / "status.json"
        self.checkpoint_seq = self._next_seq(run_dir / "checkpoints", "cp")
        self.summary_seq = self._next_seq(run_dir / "summary_requests", "sum")
        self.trace_seq = self._next_seq(run_dir / "capability_traces", "cap")
        self.open_checkpoint: dict[str, Any] | None = None
        self.errors: list[dict[str, Any]] = []
        self.world_path = run_dir / "private_world.sqlite"
        self.index_path = run_dir / "world_index.sqlite"
        self.store = SQLiteWorldStore(self.world_path)
        self.index = WorldSearchIndex(self.index_path, store=self.store)
        self.subject_id = str(job["subject_id"]).strip()
        self.cursor = int(job["cursor"])
        self.occurred_at = datetime.fromisoformat(str(job["occurred_at"]))
        self.reveal = _load(Path(job["reveal_file"]))
        self.runtime = FusedTurnRuntime(
            store=self.store,
            index=self.index,
            model_handler=self._model_handler,
            subject_id=self.subject_id,
            round_summary_handler=self._round_summary_handler,
            dimension_summary_handler=self._dimension_summary_handler,
        )
        self.index.catch_up()

    @staticmethod
    def _next_seq(directory: Path, prefix: str) -> int:
        directory.mkdir(parents=True, exist_ok=True)
        nums = []
        for path in directory.glob(f"{prefix}*.json"):
            stem = path.stem
            digits = "".join(ch for ch in stem if ch.isdigit())
            if digits:
                nums.append(int(digits))
        return (max(nums) + 1) if nums else 1

    def _checkpoint_id(self) -> str:
        value = f"cp{self.checkpoint_seq:04d}"
        self.checkpoint_seq += 1
        return value

    def _summary_id(self) -> str:
        value = f"sum{self.summary_seq:04d}"
        self.summary_seq += 1
        return value

    def _world_revision(self) -> int:
        return int(self.store.current_world_revision())

    def _close_open_checkpoint(self, *, capability_history: Any = None) -> None:
        if self.open_checkpoint is None:
            return
        self.open_checkpoint["world_revision_after"] = self._world_revision()
        if capability_history is not None:
            self.open_checkpoint["capability_results_after_directive"] = _jsonable(
                capability_history
            )
        path = (
            self.run_dir
            / "checkpoints"
            / f"{self.open_checkpoint['checkpoint_id']}.json"
        )
        _dump(path, self.open_checkpoint)
        self.open_checkpoint = None

    def _wait_directive(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.directive_path.exists():
            raise RuntimeError(
                "stale directive file present before a new Resident decision"
            )
        _dump(self.request_path, request)
        self.ready_path.write_text(request["checkpoint_id"] + "\n", encoding="utf-8")
        _dump(
            self.status_path,
            {
                "state": "awaiting_resident_directive",
                "checkpoint_id": request["checkpoint_id"],
                "kind": request["kind"],
                "cursor": self.cursor,
                "world_revision": self._world_revision(),
            },
        )
        print(
            f"DECISION_READY {request['checkpoint_id']} kind={request['kind']}",
            flush=True,
        )
        deadline = time.time() + float(os.environ.get("RESIDENT_DIRECTIVE_TIMEOUT", "7200"))
        while not self.directive_path.exists():
            if time.time() > deadline:
                raise TimeoutError(
                    f"Resident directive timed out for {request['checkpoint_id']}"
                )
            time.sleep(0.25)
        # Let the writer finish replacing the file.
        time.sleep(0.05)
        directive = _load(self.directive_path)
        archive = self.run_dir / "pending" / "consumed"
        archive.mkdir(parents=True, exist_ok=True)
        _dump(archive / f"{request['checkpoint_id']}_directive.json", directive)
        self.directive_path.unlink()
        if self.ready_path.exists():
            self.ready_path.unlink()
        return directive

    def _snapshot_payload(self, snapshot: RuntimeSnapshot) -> dict[str, Any]:
        return {
            "user_input": snapshot.user_input,
            "wake_reason": snapshot.wake_reason,
            "cockpit": _jsonable(snapshot.cockpit),
            "capability_catalog": _jsonable(snapshot.capability_catalog),
            "capability_history": _jsonable(snapshot.capability_history),
            "round_index": snapshot.round_index,
            "remaining_tool_rounds": snapshot.remaining_tool_rounds,
        }

    def _directive_from_resident(self, raw: dict[str, Any]) -> ModelDirective:
        calls = []
        for item in raw.get("capability_calls") or []:
            calls.append(
                CapabilityCall(
                    name=str(item["name"]),
                    arguments=dict(item.get("arguments") or {}),
                    call_id=(None if item.get("call_id") is None else str(item["call_id"])),
                )
            )
        response = raw.get("response")
        silence = bool(raw.get("silence", False))
        if response is not None:
            response = str(response)
        return ModelDirective(
            capability_calls=tuple(calls),
            response=response,
            silence=silence,
        )

    def _model_handler(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        history = list(snapshot.capability_history)
        self._close_open_checkpoint(capability_history=history)
        checkpoint_id = self._checkpoint_id()
        before = self._world_revision()
        request = {
            "kind": "runtime_snapshot",
            "checkpoint_id": checkpoint_id,
            "simulated_time": self.occurred_at.isoformat(),
            "current_released_cursor": self.cursor,
            "world_revision_before": before,
            "resident_visible_current_reality": self.reveal,
            "runtime_snapshot": self._snapshot_payload(snapshot),
        }
        raw = self._wait_directive(request)
        try:
            directive = self._directive_from_resident(raw)
        except Exception as exc:
            self.errors.append(
                {
                    "checkpoint_id": checkpoint_id,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            raise
        self.open_checkpoint = {
            "checkpoint_id": checkpoint_id,
            "simulated_time": self.occurred_at.isoformat(),
            "current_released_cursor": self.cursor,
            "world_revision_before": before,
            "world_revision_after": None,
            "resident_visible_current_reality": self.reveal,
            "runtime_snapshot": request["runtime_snapshot"],
            "model_directive": {
                "capability_calls": [
                    {
                        "name": call.name,
                        "arguments": dict(call.arguments),
                        "call_id": call.call_id,
                    }
                    for call in directive.capability_calls
                ],
                "response": directive.response,
                "silence": directive.silence,
            },
            "decision_rationale": raw.get("decision_rationale"),
            "silence_or_response": (
                "response"
                if directive.response is not None
                else "silence"
                if directive.silence
                else "capability_calls"
            ),
            "errors": [],
        }
        trace_id = f"cap{self.trace_seq:04d}"
        self.trace_seq += 1
        _dump(
            self.run_dir / "capability_traces" / f"{trace_id}.json",
            {
                "trace_id": trace_id,
                "checkpoint_id": checkpoint_id,
                "cursor": self.cursor,
                "directive": self.open_checkpoint["model_directive"],
                "history_before": _jsonable(history),
            },
        )
        return directive

    def _summary_wait(self, kind: str, request_payload: dict[str, Any]) -> str:
        summary_id = self._summary_id()
        request = {
            "kind": kind,
            "checkpoint_id": summary_id,
            "summary_id": summary_id,
            "simulated_time": self.occurred_at.isoformat(),
            "current_released_cursor": self.cursor,
            "world_revision_before": self._world_revision(),
            "request": request_payload,
        }
        raw = self._wait_directive(request)
        text = str(raw.get("summary_text") or "").strip()
        if not text:
            raise ValueError("Resident summary text must be non-blank")
        saved = {
            **request,
            "resident_authored_response": text,
            "decision_rationale": raw.get("decision_rationale"),
            "world_revision_after": None,
        }
        path = self.run_dir / "summary_requests" / f"{summary_id}.json"
        _dump(path, saved)
        pending = getattr(self, "_pending_summaries", None)
        if pending is None:
            pending = []
            self._pending_summaries = pending
        pending.append((path, saved))
        return text

    def _dimension_summary_handler(self, prepared: DimensionSummaryInput) -> str:
        return self._summary_wait(
            "dimension_summary",
            prepared.model_dump(mode="json"),
        )

    def _round_summary_handler(self, request: Any) -> str:
        payload = request.model_dump(mode="json") if hasattr(request, "model_dump") else _jsonable(request)
        return self._summary_wait("round_summary", payload)

    def _note_summary_commit(self) -> None:
        pending = getattr(self, "_pending_summaries", None) or []
        for path, saved in pending:
            saved["world_revision_after"] = self._world_revision()
            _dump(path, saved)
        self._pending_summaries = []

    def _evaluate_inlet_watches(self) -> list[dict[str, Any]]:
        """Match one already-ingested Observation against Resident watches.

        External ingest does not pass through the runtime observation listener.
        This only runs the mechanical predicate. It does not interpret the fact.
        """
        raw = self.job.get("evaluate_observation_ref")
        if not raw:
            return []
        ref = ObjectRef(
            object_id=str(raw["object_id"]),
            revision=int(raw["revision"]),
        )
        receipts = self.runtime.attention_watches.evaluate_observation(ref)
        return [_jsonable(item) for item in receipts]

    def _pending_background(self) -> list[dict[str, Any]]:
        wakes = []
        for wake in self.runtime.wake_bus.pending_wakes():
            attention = self.runtime.wake_bus.attention_class_for_wake(wake)
            wakes.append(
                {
                    "object_id": wake.object_id,
                    "revision": wake.revision,
                    "wake_source": wake.wake_source.value,
                    "wake_state": wake.wake_state.value,
                    "attention_class": attention.value,
                    "first_hit_at": wake.first_hit_at.isoformat(),
                    "last_hit_at": wake.last_hit_at.isoformat(),
                }
            )
        return wakes

    def run(self) -> dict[str, Any]:
        report: dict[str, Any] = {
            "cursor": self.cursor,
            "occurred_at": self.occurred_at.isoformat(),
            "world_revision_before_runtime": self._world_revision(),
            "index_watermark_before": self.index.watermark(),
        }
        self.index.catch_up()
        # Maintenance that matured before this released time runs first.
        # Background derivation is not forced inside its 60s window.
        summary = self.runtime.run_due_dimension_summaries(now=self.occurred_at)
        self._note_summary_commit()
        report["dimension_summaries"] = _jsonable(summary)
        reconcile = self.runtime.cognitive_derivation.reconcile()
        report["cognitive_derivation_reconcile"] = _jsonable(reconcile)
        self.index.catch_up()
        report["attention_watch_evaluations"] = self._evaluate_inlet_watches()

        wake_runs = []
        for _ in range(32):
            dispatched = self.runtime.dispatch_next_pending_wake(now=self.occurred_at)
            if dispatched is None:
                break
            if dispatched.runtime is not None:
                self._close_open_checkpoint(
                    capability_history=dispatched.runtime.capability_history
                )
            wake_runs.append(_jsonable(dispatched))
        else:
            raise RuntimeError("wake drain exceeded mechanical safety cap")
        report["wake_dispatches"] = wake_runs

        reviews = []
        for _ in range(8):
            review = self.runtime.run_periodic_review(now=self.occurred_at)
            if review is None:
                break
            if review.runtime is not None:
                self._close_open_checkpoint(
                    capability_history=review.runtime.capability_history
                )
            reviews.append(_jsonable(review))
            if review.runtime is None:
                break
            if review.runtime.termination_reason not in {"responded", "silence"}:
                break
        report["periodic_reviews"] = reviews
        self.index.catch_up()

        if self.job.get("run_turn"):
            reveal_text = self.reveal.get("resident_visible_payload")
            if not isinstance(reveal_text, str) or not reveal_text.strip():
                raise ValueError("released USER conversation payload is not exact text")
            occurred = datetime.fromisoformat(str(self.reveal["occurred_at"]))
            turn = self.runtime.run_turn(
                session_id=str(self.job["session_id"]),
                turn_index=int(self.job["turn_index"]),
                user_input=reveal_text,
                occurred_at=occurred,
            )
            self._close_open_checkpoint(
                capability_history=turn.runtime.capability_history
            )
            self._note_summary_commit()
            report["run_turn"] = {
                "termination_reason": turn.runtime.termination_reason,
                "silenced": turn.runtime.silenced,
                "response": turn.runtime.response,
                "model_rounds": turn.runtime.model_rounds,
                "capability_history": _jsonable(turn.runtime.capability_history),
                "conversation_commit": _jsonable(turn.conversation_commit),
                "continuity_summary_commits": _jsonable(
                    turn.continuity_summary_commits
                ),
                "continuity_summary_error": turn.continuity_summary_error,
                "user_observation_id": turn.conversation_commit.user_observation_id,
                "assistant_observation_id": turn.conversation_commit.assistant_observation_id,
                "idempotent_replay_flag": turn.conversation_commit.idempotent_replay,
                "user_world_revision": turn.conversation_commit.user_world_revision,
                "assistant_world_revision": turn.conversation_commit.assistant_world_revision,
            }
            reconcile_after_turn = self.runtime.cognitive_derivation.reconcile()
            report["cognitive_derivation_reconcile_after_turn"] = _jsonable(
                reconcile_after_turn
            )
            for _ in range(32):
                dispatched = self.runtime.dispatch_next_pending_wake(
                    now=self.occurred_at
                )
                if dispatched is None:
                    break
                if dispatched.runtime is not None:
                    self._close_open_checkpoint(
                        capability_history=dispatched.runtime.capability_history
                    )
                wake_runs.append(_jsonable(dispatched))
            else:
                raise RuntimeError("wake drain exceeded mechanical safety cap")

        self.index.catch_up()
        self._checkpoint_wal()
        report["world_revision_after"] = self._world_revision()
        report["index_watermark_after"] = self.index.watermark()
        report["index_lag"] = self.index.lag()
        report["pending_wakes_not_dispatched"] = self._pending_background()
        report["errors"] = self.errors
        return report

    def _checkpoint_wal(self) -> None:
        with self.store._connection() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        # Index uses its own connection.
        import sqlite3

        conn = sqlite3.connect(self.index_path)
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.commit()
        finally:
            conn.close()


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: resident_transport.py <run-dir> <job.json>", file=sys.stderr)
        return 2
    run_dir = Path(sys.argv[1]).resolve()
    job = _load(Path(sys.argv[2]).resolve())
    transport = ResidentTransport(run_dir, job)
    try:
        report = transport.run()
    except Exception:
        err = traceback.format_exc()
        _dump(
            run_dir / "pending" / "status.json",
            {"state": "error", "traceback": err, "cursor": job.get("cursor")},
        )
        print(err, file=sys.stderr, flush=True)
        return 1
    out = run_dir / "cursor_lifecycle" / f"cursor_{int(job['cursor']):04d}_runtime.json"
    _dump(out, report)
    _dump(run_dir / "pending" / "status.json", {"state": "event_runtime_complete", "cursor": job["cursor"]})
    print(f"EVENT_RUNTIME_COMPLETE cursor={job['cursor']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
