#!/usr/bin/env python3
"""Thin synchronous interactive bridge for the C14 Resident-B run.

Mechanical responsibilities only:
  * instantiate the real AIOS runtime (SQLiteWorldStore / WorldSearchIndex /
    FusedTurnRuntime) over the private Resident-B working World;
  * serialize each exact RuntimeSnapshot / DimensionSummaryInput /
    RoundSummaryRequest to a file and pause;
  * receive the Resident's own directive / summary text from a file;
  * execute exactly the requested capability calls through the real runtime;
  * persist job results and an append-only log.

It contains no semantic rules, no keyword logic, no expected answers, and it
never decides anything on the Resident's behalf. All semantics live in the
Resident AI (the model) responding through the response files.
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
import time
import traceback
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RUN_ROOT = HERE.parent
REPO_ROOT = RUN_ROOT.parents[5]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aios_core.context.continuity import RoundSummaryRequest
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall, CapabilityResult
from aios_core.runtime.cognitive_runtime import (
    ModelDirective,
    RuntimeSnapshot,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries import DimensionSummaryInput

WORLD_DB = RUN_ROOT / "world" / "aios_world.db"
JOBS_DIR = HERE / "jobs"
IO_DIR = HERE / "io"
RESULTS_DIR = HERE / "results"
LOG_PATH = HERE / "log.jsonl"

RESPONSE_TIMEOUT_SECONDS = 7200
POLL_INTERVAL_SECONDS = 0.4

JOBS_DIR.mkdir(parents=True, exist_ok=True)
IO_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def log(event: str, **payload: Any) -> None:
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **payload}
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def to_jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return to_jsonable(dataclasses.asdict(obj))
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(item) for item in obj]
    if isinstance(obj, dict):
        return {str(key): to_jsonable(value) for key, value in obj.items()}
    if hasattr(obj, "model_dump"):
        try:
            return to_jsonable(obj.model_dump(mode="json"))
        except Exception:
            pass
    if hasattr(obj, "asdict"):
        try:
            return to_jsonable(obj.asdict())
        except Exception:
            pass
    return str(obj)


class FileBridge:
    def __init__(self) -> None:
        self._io_counter = self._max_existing_io_id()

    @staticmethod
    def _max_existing_io_id() -> int:
        best = 0
        for path in IO_DIR.glob("req_*.json"):
            try:
                best = max(best, int(path.stem.split("_")[1]))
            except (IndexError, ValueError):
                continue
        return best

    def _next_id(self) -> int:
        self._io_counter += 1
        return self._io_counter

    @staticmethod
    def _wait_response(io_id: int) -> dict[str, Any]:
        resp_path = IO_DIR / f"resp_{io_id}.json"
        deadline = time.monotonic() + RESPONSE_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if resp_path.is_file():
                for _ in range(50):
                    try:
                        return json.loads(resp_path.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, OSError):
                        time.sleep(0.1)
                raise RuntimeError(f"response file {resp_path} unreadable")
            time.sleep(POLL_INTERVAL_SECONDS)
        raise RuntimeError(f"bridge response timeout waiting for {resp_path}")

    # ---- pause point 1: model directive ----
    def model_handler(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        io_id = self._next_id()
        request = {
            "io_id": io_id,
            "kind": "model_directive",
            "context": to_jsonable(self.current_context),
            "snapshot": {
                "user_input": snapshot.user_input,
                "wake_reason": snapshot.wake_reason,
                "cockpit": to_jsonable(dict(snapshot.cockpit)),
                "capability_catalog": to_jsonable(list(snapshot.capability_catalog)),
                "capability_history": [
                    to_jsonable(
                        {
                            "name": item.name,
                            "ok": item.ok,
                            "data": item.data,
                            "error_code": item.error_code,
                            "error_message": item.error_message,
                            "call_id": item.call_id,
                        }
                    )
                    for item in snapshot.capability_history
                ],
                "round_index": snapshot.round_index,
                "remaining_tool_rounds": snapshot.remaining_tool_rounds,
            },
        }
        (IO_DIR / f"req_{io_id}.json").write_text(
            json.dumps(request, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        log("model_request", io_id=io_id, context=to_jsonable(self.current_context))
        response = self._wait_response(io_id)
        log("model_response", io_id=io_id, response=response)
        calls = []
        for index, raw in enumerate(response.get("capability_calls") or []):
            calls.append(
                CapabilityCall(
                    name=str(raw["name"]),
                    arguments=dict(raw.get("arguments") or {}),
                    call_id=str(raw.get("call_id") or f"io{io_id}-{index}"),
                )
            )
        directive = ModelDirective(
            capability_calls=tuple(calls),
            response=response.get("response"),
            silence=bool(response.get("silence") or False),
        )
        return directive

    # ---- pause point 2: dimension summary text ----
    def dimension_summary_handler(self, prepared: DimensionSummaryInput) -> str:
        io_id = self._next_id()
        request = {
            "io_id": io_id,
            "kind": "dimension_summary",
            "context": to_jsonable(self.current_context),
            "summary_input": to_jsonable(prepared.model_dump(mode="json")),
        }
        (IO_DIR / f"req_{io_id}.json").write_text(
            json.dumps(request, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        log("dimension_summary_request", io_id=io_id, context=to_jsonable(self.current_context))
        response = self._wait_response(io_id)
        log("dimension_summary_response", io_id=io_id, length=len(str(response.get("text") or "")))
        text = str(response.get("text") or "")
        if not text.strip():
            raise RuntimeError("dimension summary response text is blank")
        return text

    # ---- pause point 3: round summary text ----
    def round_summary_handler(self, request: RoundSummaryRequest) -> str:
        io_id = self._next_id()
        payload = {
            "io_id": io_id,
            "kind": "round_summary",
            "context": to_jsonable(self.current_context),
            "summary_input": to_jsonable(request.model_dump(mode="json")),
        }
        (IO_DIR / f"req_{io_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        log("round_summary_request", io_id=io_id, context=to_jsonable(self.current_context))
        response = self._wait_response(io_id)
        log("round_summary_response", io_id=io_id, length=len(str(response.get("text") or "")))
        text = str(response.get("text") or "")
        if not text.strip():
            raise RuntimeError("round summary response text is blank")
        return text


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def serialize_runtime_result(runtime) -> dict[str, Any]:
    return {
        "response": runtime.response,
        "silenced": runtime.silenced,
        "termination_reason": runtime.termination_reason,
        "model_rounds": runtime.model_rounds,
        "capability_history": [
            {
                "name": item.name,
                "ok": item.ok,
                "data": to_jsonable(item.data),
                "error_code": item.error_code,
                "error_message": item.error_message,
                "call_id": item.call_id,
            }
            for item in runtime.capability_history
        ],
        "model_input_tokens": runtime.model_input_tokens,
        "model_output_tokens": runtime.model_output_tokens,
        "model_total_tokens": runtime.model_total_tokens,
        "model_usage_complete": runtime.model_usage_complete,
    }


def main() -> int:
    bridge = FileBridge()
    store = SQLiteWorldStore(WORLD_DB)
    index = WorldSearchIndex(WORLD_DB, store=store)
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=bridge.model_handler,
        subject_id="user_1",
        round_summary_handler=bridge.round_summary_handler,
        dimension_summary_handler=bridge.dimension_summary_handler,
    )
    bridge.current_context = {"job": "startup"}
    log("bridge_started", world_revision=store.current_world_revision(), index_watermark=index.watermark())

    processed: set[str] = set()
    while True:
        job_files = sorted(
            path for path in JOBS_DIR.glob("*.json") if path.stem not in processed
        )
        if not job_files:
            time.sleep(0.3)
            continue
        job_path = job_files[0]
        job_id = job_path.stem
        try:
            job = json.loads(job_path.read_text(encoding="utf-8"))
        except Exception as exc:  # unreadable job: report and skip
            processed.add(job_id)
            (RESULTS_DIR / f"{job_id}.json").write_text(
                json.dumps({"job_id": job_id, "status": "error", "error": f"unreadable job: {exc}"}, indent=2),
                encoding="utf-8",
            )
            log("job_error", job_id=job_id, error=str(exc))
            continue
        processed.add(job_id)
        job_type = str(job.get("type") or "")
        args = dict(job.get("args") or {})
        bridge.current_context = {"job_id": job_id, "job_type": job_type, "args": to_jsonable(args)}
        log("job_start", job_id=job_id, job_type=job_type, args=to_jsonable(args))
        try:
            if job_type == "shutdown":
                result = {"status": "ok", "result": {"shutdown": True}}
                (RESULTS_DIR / f"{job_id}.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8",
                )
                log("job_done", job_id=job_id, job_type=job_type, status="ok")
                log("bridge_stopped")
                return 0
            if job_type == "status":
                result = {
                    "status": "ok",
                    "result": {
                        "world_revision": store.current_world_revision(),
                        "index_watermark": index.watermark(),
                    },
                }
            elif job_type == "catchup":
                rows = index.catch_up()
                result = {
                    "status": "ok",
                    "result": {
                        "catch_up_rows": rows,
                        "world_revision": store.current_world_revision(),
                        "index_watermark": index.watermark(),
                    },
                }
            elif job_type == "turn":
                occurred = parse_iso(args["occurred_at"])
                turn = runtime.run_turn(
                    session_id=str(args["session_id"]),
                    turn_index=int(args["turn_index"]),
                    user_input=str(args["user_text"]),
                    occurred_at=occurred,
                )
                result = {
                    "status": "ok",
                    "result": {
                        "runtime": serialize_runtime_result(turn.runtime),
                        "recommendation": {
                            "current_topic": turn.recommendation.current_topic,
                            "topic_gate_open": turn.recommendation.topic_gate_open,
                            "card_count": len(turn.recommendation.cards),
                            "reason": turn.recommendation.reason,
                        },
                        "conversation_commit": to_jsonable(turn.conversation_commit),
                        "continuity_summary_commits": to_jsonable(
                            turn.continuity_summary_commits
                        ),
                        "continuity_summary_error": turn.continuity_summary_error,
                        "world_revision": store.current_world_revision(),
                        "index_watermark": index.watermark(),
                    },
                }
            elif job_type == "summaries":
                now = parse_iso(args["now"])
                schedule = runtime.run_due_dimension_summaries(now=now)
                result = {
                    "status": "ok",
                    "result": {
                        "commits": to_jsonable(schedule.commits),
                        "attempted_job_count": len(schedule.attempted_jobs),
                        "attempted_jobs": to_jsonable(schedule.attempted_jobs),
                        "skipped_unchanged": to_jsonable(schedule.skipped_unchanged),
                        "skipped_empty": to_jsonable(schedule.skipped_empty),
                        "truncated": schedule.truncated,
                        "world_revision": store.current_world_revision(),
                        "index_watermark": index.watermark(),
                    },
                }
            elif job_type == "wake":
                now = parse_iso(args["now"])
                dispatch = runtime.dispatch_next_pending_wake(now=now)
                if dispatch is None:
                    result = {
                        "status": "ok",
                        "result": {"dispatched": False},
                    }
                else:
                    result = {
                        "status": "ok",
                        "result": {
                            "dispatched": True,
                            "wake_ref": to_jsonable(dispatch.wake_ref),
                            "step0": to_jsonable(dispatch.step0),
                            "wake": to_jsonable(dispatch.wake),
                            "delivery_response": dispatch.delivery_response,
                            "delivery_suppressed": dispatch.delivery_suppressed,
                            "runtime": serialize_runtime_result(dispatch.runtime)
                            if dispatch.runtime is not None
                            else None,
                            "world_revision": store.current_world_revision(),
                            "index_watermark": index.watermark(),
                        },
                    }
            elif job_type == "review":
                now = parse_iso(args["now"])
                review = runtime.run_periodic_review(now=now)
                if review is None:
                    result = {"status": "ok", "result": {"review": None}}
                else:
                    result = {
                        "status": "ok",
                        "result": {
                            "review": {
                                "review_id": review.request.review_id,
                                "wake_ref": to_jsonable(review.request.wake_ref),
                                "window_start": review.request.window_start.isoformat(),
                                "window_end": review.request.window_end.isoformat(),
                                "anchor_count": len(review.request.anchors),
                                "instruction": review.request.instruction,
                            },
                            "runtime": serialize_runtime_result(review.runtime)
                            if review.runtime is not None
                            else None,
                            "wake": to_jsonable(review.wake),
                            "budget": to_jsonable(review.budget),
                            "world_revision": store.current_world_revision(),
                            "index_watermark": index.watermark(),
                        },
                    }
            else:
                raise RuntimeError(f"unknown job type: {job_type}")
        except Exception as exc:
            result = {
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            }
            log("job_error", job_id=job_id, job_type=job_type, error=f"{type(exc).__name__}: {exc}")
        (RESULTS_DIR / f"{job_id}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        log(
            "job_done",
            job_id=job_id,
            job_type=job_type,
            status=str(result.get("status")),
            world_revision=store.current_world_revision(),
            index_watermark=index.watermark(),
        )
        if job_type == "shutdown":
            log("bridge_stopped")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
