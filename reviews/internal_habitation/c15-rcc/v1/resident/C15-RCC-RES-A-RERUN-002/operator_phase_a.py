#!/usr/bin/env python3
"""Mechanical Phase A operator for C15-RCC-RES-A-RERUN-002.

This program transports bytes and executes legal AIOS / release commands.
It does not interpret life events, choose Claims, search queries, answers,
or silence. Whenever CognitiveRuntime or a summary scheduler needs a model
decision, it writes a mailbox request and waits for the Resident.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from aios_core.headless.core import HeadlessConfig, HeadlessCore
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall, CapabilityResult
from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot
from aios_core.storage.sqlite_store import SQLiteWorldStore


REPO = Path("/home/user/Haneof-AIOS-Core-v3.0")
RUN = REPO / "reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002"
PYTHON = Path("/tmp/aios-venv/bin/python")
RELEASE_OPERATOR = REPO / "reviews/internal_habitation/c15-rcc/v1/release/release_operator.py"
MECHANICAL_INGEST = REPO / "reviews/internal_habitation/c15-rcc/v1/release/mechanical_ingest_adapter.py"
CANONICAL_INGEST = REPO / "reviews/internal_habitation/c15-rcc/v1/release/canonical_conversation_ingest.py"

WORLD = RUN / "private_world.sqlite"
INDEX = RUN / "world_index.sqlite"
RELEASE_STATE = RUN / "release_state.json"
IDENTITY_PATH = RUN / "identity.json"
STATUS_PATH = RUN / "STATUS.json"
MAILBOX = RUN / "mailbox"
PENDING = MAILBOX / "PENDING.json"
PENDING_REPLY = MAILBOX / "PENDING.reply.json"
STOP_SEQUENCE = 13
POLL_SECONDS = 0.4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return jsonable(value.value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(v) for v in value]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    text = json.dumps(jsonable(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(jsonable(value), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_iso(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError(f"timezone-naive datetime is not legal: {value}")
    return moment.astimezone(timezone.utc)


class MailboxResident:
    """Transport-only model adapter. Cognition stays in the Resident mailbox replies."""

    def __init__(self, operator: "PhaseAOperator") -> None:
        self.operator = operator

    def __call__(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        payload = {
            "user_input": snapshot.user_input,
            "wake_reason": snapshot.wake_reason,
            "cockpit": jsonable(snapshot.cockpit),
            "capability_catalog": jsonable(snapshot.capability_catalog),
            "capability_history": jsonable(snapshot.capability_history),
            "round_index": snapshot.round_index,
            "remaining_tool_rounds": snapshot.remaining_tool_rounds,
        }
        output = self.operator.ask_resident("runtime", payload)
        return self._directive(output)

    def round_summary(self, request: Any) -> str:
        payload = jsonable(request)
        output = self.operator.ask_resident("round_summary", payload)
        return self._summary_text(output)

    def dimension_summary(self, request: Any) -> str:
        payload = jsonable(request)
        output = self.operator.ask_resident("dimension_summary", payload)
        return self._summary_text(output)

    @staticmethod
    def _directive(output: Any) -> ModelDirective:
        if not isinstance(output, dict) or len(output) != 1:
            raise ValueError("runtime output must be exactly one of response/silence/capability_calls")
        if "response" in output:
            text = output["response"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("response must be non-blank")
            return ModelDirective(response=text)
        if output.get("silence") is True:
            return ModelDirective(silence=True)
        calls = output.get("capability_calls")
        if not isinstance(calls, list) or not calls:
            raise ValueError("capability_calls must be a non-empty list")
        parsed: list[CapabilityCall] = []
        for call in calls:
            if not isinstance(call, dict):
                raise ValueError("invalid capability call")
            name = call.get("name")
            arguments = call.get("arguments")
            if not isinstance(name, str) or not name.strip() or not isinstance(arguments, dict):
                raise ValueError("invalid capability name/arguments")
            kwargs: dict[str, Any] = {"name": name, "arguments": arguments}
            if "call_id" in call:
                kwargs["call_id"] = call["call_id"]
            parsed.append(CapabilityCall(**kwargs))
        return ModelDirective(capability_calls=tuple(parsed))

    @staticmethod
    def _summary_text(output: Any) -> str:
        if not isinstance(output, dict) or set(output) != {"text"}:
            raise ValueError("summary output must be {\"text\": non-blank}")
        text = output["text"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError("summary text must be non-blank")
        return text


class PhaseAOperator:
    def __init__(self) -> None:
        self.identity = json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))
        self.subject_id = str(self.identity["subject_id"])
        self.session_id = str(self.identity["session_id"])
        self.next_turn = 1
        self.clock: datetime | None = None
        self.mailbox_seq = 0
        self.resident = MailboxResident(self)
        self.log_path = RUN / "logs" / "operator.jsonl"

    def log(self, event: str, **data: Any) -> None:
        record = {
            "at": utcnow().isoformat(),
            "event": event,
            "pid": os.getpid(),
            **data,
        }
        append_jsonl(self.log_path, record)
        print(f"[{event}] {json.dumps(jsonable(data), ensure_ascii=False, sort_keys=True)}", flush=True)

    def set_status(self, **fields: Any) -> None:
        payload = {
            "task": "C15-RCC-RES-A-RERUN-002",
            "updated_at": utcnow().isoformat(),
            "pid": os.getpid(),
            "subject_id": self.subject_id,
            "session_id": self.session_id,
            "next_turn": self.next_turn,
            "clock": None if self.clock is None else self.clock.isoformat(),
            **fields,
        }
        atomic_json(STATUS_PATH, payload)

    def ask_resident(self, kind: str, payload: Any) -> Any:
        self.mailbox_seq += 1
        request_id = f"{self.mailbox_seq:04d}-{uuid4().hex[:12]}"
        request = {
            "protocol": "c15-rcc-res-a-rerun-002-mailbox-v1",
            "request_id": request_id,
            "seq": self.mailbox_seq,
            "kind": kind,
            "cursor": self._status_cursor(),
            "stage": self._status_stage(),
            "session_id": self.session_id,
            "subject_id": self.subject_id,
            "clock": None if self.clock is None else self.clock.isoformat(),
            "input": payload,
        }
        inbox_path = MAILBOX / "inbox" / f"{request_id}.request.json"
        atomic_json(inbox_path, request)
        if PENDING_REPLY.exists():
            PENDING_REPLY.unlink()
        atomic_json(PENDING, request)
        self.set_status(
            state="WAITING_RESIDENT",
            mailbox_request_id=request_id,
            mailbox_kind=kind,
            pending_path=str(PENDING),
            reply_path=str(PENDING_REPLY),
        )
        self.log("mailbox_request", request_id=request_id, mailbox_kind=kind, path=str(PENDING))
        print(
            f"MAILBOX_WAITING request_id={request_id} kind={kind} path={PENDING}",
            flush=True,
        )
        started = time.time()
        while True:
            if PENDING_REPLY.is_file():
                try:
                    raw = PENDING_REPLY.read_text(encoding="utf-8").strip()
                    reply = json.loads(raw)
                except (OSError, json.JSONDecodeError):
                    time.sleep(POLL_SECONDS)
                    continue
                if reply.get("request_id") != request_id:
                    time.sleep(POLL_SECONDS)
                    continue
                if reply.get("kind") != kind:
                    raise ValueError(f"reply kind mismatch for {request_id}")
                if "output" not in reply:
                    raise ValueError(f"reply missing output for {request_id}")
                archive = {
                    "request": request,
                    "reply": reply,
                    "answered_at": utcnow().isoformat(),
                    "wait_seconds": round(time.time() - started, 3),
                }
                atomic_json(MAILBOX / "archive" / f"{request_id}.json", archive)
                try:
                    PENDING.unlink()
                except FileNotFoundError:
                    pass
                try:
                    PENDING_REPLY.unlink()
                except FileNotFoundError:
                    pass
                self.log("mailbox_reply", request_id=request_id, mailbox_kind=kind)
                return reply["output"]
            time.sleep(POLL_SECONDS)

    def _status_cursor(self) -> int | None:
        if STATUS_PATH.exists():
            try:
                return json.loads(STATUS_PATH.read_text(encoding="utf-8")).get("cursor")
            except (OSError, json.JSONDecodeError):
                return None
        return None

    def _status_stage(self) -> str | None:
        if STATUS_PATH.exists():
            try:
                return json.loads(STATUS_PATH.read_text(encoding="utf-8")).get("stage")
            except (OSError, json.JSONDecodeError):
                return None
        return None

    def run_cmd(self, args: list[str], *, stdin_text: str | None = None) -> dict[str, Any]:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO / "src")
        completed = subprocess.run(
            args,
            cwd=str(REPO),
            env=env,
            input=stdin_text,
            text=True,
            capture_output=True,
            check=False,
        )
        record = {
            "argv": args,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        if completed.returncode != 0:
            self.log("command_failed", **record)
            raise RuntimeError(
                f"command failed ({completed.returncode}): {args}\n{completed.stderr}\n{completed.stdout}"
            )
        stdout = completed.stdout.strip()
        parsed: Any = None
        if stdout:
            try:
                parsed = json.loads(stdout)
            except json.JSONDecodeError:
                lines = [line for line in stdout.splitlines() if line.strip()]
                if lines:
                    try:
                        parsed = json.loads(lines[-1])
                    except json.JSONDecodeError:
                        parsed = None
        record["parsed"] = parsed
        return record

    def ensure_fresh_world(self) -> None:
        if WORLD.exists() or INDEX.exists() or RELEASE_STATE.exists():
            raise RuntimeError("refusing to reuse existing world/index/release-state")
        store = SQLiteWorldStore(WORLD)
        index = WorldSearchIndex(INDEX, store=store)
        rebuilt = index.rebuild()
        revision = int(store.current_world_revision())
        if revision != 0 or index.watermark() != 0:
            raise RuntimeError("fresh world is not empty")
        self.log("fresh_world", world_revision=revision, index_watermark=index.watermark(), rebuilt=rebuilt)

    def init_release(self) -> None:
        result = self.run_cmd(
            [
                str(PYTHON),
                str(RELEASE_OPERATOR),
                "init",
                "--phase",
                "A",
                "--state",
                str(RELEASE_STATE),
            ]
        )
        atomic_json(RUN / "receipts" / "release_init.json", result)
        state = json.loads(RELEASE_STATE.read_text(encoding="utf-8"))
        self.log("release_init", state=state, stdout=result.get("parsed"))

    def open_core(self) -> HeadlessCore:
        core = HeadlessCore(
            config=HeadlessConfig(
                world_path=WORLD,
                index_path=INDEX,
                subject_id=self.subject_id,
            ),
            model_handler=self.resident,
            round_summary_handler=self.resident.round_summary,
            dimension_summary_handler=self.resident.dimension_summary,
        )
        core.start()
        assert core.index is not None
        core.index.catch_up()
        return core

    def due_work(self, core: HeadlessCore, *, now: datetime, label: str) -> dict[str, Any]:
        assert core.runtime is not None
        assert core.index is not None
        wakes_out: list[Any] = []
        for _ in range(24):
            batch = core.process_due_work(
                now=now,
                max_wakes=8,
                include_periodic_review=False,
            )
            if not batch.wakes:
                break
            for item in batch.wakes:
                wakes_out.append(
                    {
                        "wake_id": item.wake.wake_id,
                        "revision": item.wake.revision,
                        "state": item.wake.state,
                        "delivery_response": item.delivery_response,
                        "delivery_suppressed": item.delivery_suppressed,
                        "termination_reason": (
                            None if item.runtime is None else item.runtime.termination_reason
                        ),
                    }
                )
        summaries = None
        try:
            summary_result = core.runtime.run_due_dimension_summaries(now=now, max_jobs=64)
            summaries = {
                "attempted_jobs": len(summary_result.attempted_jobs),
                "commits": jsonable(summary_result.commits),
                "skipped_unchanged": len(summary_result.skipped_unchanged),
                "skipped_empty": len(summary_result.skipped_empty),
                "truncated": summary_result.truncated,
            }
        except Exception as exc:
            summaries = {"error": f"{type(exc).__name__}: {exc}"}
            self.log("dimension_summary_error", error=str(exc), label=label)
        post_wakes: list[Any] = []
        review = None
        for _ in range(16):
            batch = core.process_due_work(
                now=now,
                max_wakes=8,
                include_periodic_review=False,
            )
            if not batch.wakes:
                break
            for item in batch.wakes:
                post_wakes.append(
                    {
                        "wake_id": item.wake.wake_id,
                        "revision": item.wake.revision,
                        "state": item.wake.state,
                        "delivery_response": item.delivery_response,
                        "delivery_suppressed": item.delivery_suppressed,
                        "termination_reason": (
                            None if item.runtime is None else item.runtime.termination_reason
                        ),
                    }
                )
        review_batch = core.process_due_work(
            now=now,
            max_wakes=0,
            include_periodic_review=True,
        )
        if review_batch.periodic_review is not None:
            item = review_batch.periodic_review
            review = {
                "review_id": item.request.review_id,
                "wake_id": item.wake.wake_id,
                "revision": item.wake.revision,
                "state": item.wake.state,
                "termination_reason": (
                    None if item.runtime is None else item.runtime.termination_reason
                ),
            }
        core.index.catch_up()
        status = core.status()
        result = {
            "label": label,
            "now": now.isoformat(),
            "wakes": wakes_out,
            "post_summary_wakes": post_wakes,
            "summaries": summaries,
            "periodic_review": review,
            "world_revision": status["world_revision"],
            "index_watermark": status["index_watermark"],
        }
        append_jsonl(RUN / "receipts" / "due_work.jsonl", result)
        self.log("due_work", label=label, world_revision=status["world_revision"], wakes=len(wakes_out) + len(post_wakes))
        return result

    def reveal(self) -> dict[str, Any]:
        result = self.run_cmd(
            [
                str(PYTHON),
                str(RELEASE_OPERATOR),
                "reveal",
                "--phase",
                "A",
                "--state",
                str(RELEASE_STATE),
            ]
        )
        event = result["parsed"]
        if not isinstance(event, dict):
            raise RuntimeError(f"reveal did not return JSON object: {result['stdout']}")
        return event

    def is_user_conversation(self, event: dict[str, Any]) -> bool:
        key = (
            event.get("dimension"),
            event.get("source_kind"),
            event.get("source_class"),
            event.get("modality"),
        )
        if key == ("dim:conversation", "conversation", "USER", "text"):
            return True
        # Canonical conversation path is required for USER conversation events.
        # Additional exact Resident-visible conversation shapes, if released:
        if (
            event.get("source_class") == "USER"
            and event.get("modality") == "text"
            and str(event.get("source_kind") or "") in {"conversation", "user_ai_interaction"}
        ):
            return True
        return False

    def event_time(self, event: dict[str, Any]) -> datetime:
        for key in ("occurred_at", "event_time", "recorded_at", "t"):
            raw = event.get(key)
            if isinstance(raw, str) and raw.strip():
                return parse_iso(raw)
        record = event.get("record")
        if isinstance(record, dict):
            raw = record.get("occurred_at")
            if isinstance(raw, str) and raw.strip():
                return parse_iso(raw)
        raise RuntimeError(f"released event has no occurred_at: {sorted(event)}")

    def user_text(self, event: dict[str, Any]) -> str:
        for key in (
            "resident_visible_payload",
            "text",
            "value",
            "user_input",
            "content",
        ):
            raw = event.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw
        record = event.get("record")
        if isinstance(record, dict):
            for key in ("resident_visible_payload", "value", "text"):
                raw = record.get(key)
                if isinstance(raw, str) and raw.strip():
                    return raw
        raise RuntimeError("USER conversation event has no text")

    def ingest_ref_from(self, parsed: Any, event: dict[str, Any]) -> str:
        if isinstance(parsed, dict):
            for key in ("ingest_ref", "observation_id", "user_observation_id", "durable_ref"):
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    return value
                if isinstance(value, dict) and value.get("object_id"):
                    object_id = str(value["object_id"])
                    revision = value.get("revision")
                    return object_id if revision is None else f"{object_id}:{revision}"
            receipt = parsed.get("receipt")
            if isinstance(receipt, dict):
                return self.ingest_ref_from(receipt, event)
        raise RuntimeError(f"could not extract ingest_ref from ingest output: {parsed}")

    def ingest(self, event: dict[str, Any], event_path: Path) -> dict[str, Any]:
        if self.is_user_conversation(event):
            result = self.run_cmd(
                [
                    str(PYTHON),
                    str(CANONICAL_INGEST),
                    "--world-db",
                    str(WORLD),
                    "--session-id",
                    self.session_id,
                    "--turn-index",
                    str(self.next_turn),
                    "--event-file",
                    str(event_path),
                ]
            )
            result["path"] = "canonical_conversation"
            result["turn_index"] = self.next_turn
        else:
            result = self.run_cmd(
                [
                    str(PYTHON),
                    str(MECHANICAL_INGEST),
                    "--world-db",
                    str(WORLD),
                    "--event-file",
                    str(event_path),
                ]
            )
            result["path"] = "mechanical"
        return result

    def ack(self, event: dict[str, Any], ingest_ref: str, *, user: bool) -> dict[str, Any]:
        args = [
            str(PYTHON),
            str(RELEASE_OPERATOR),
            "ack",
            "--phase",
            "A",
            "--state",
            str(RELEASE_STATE),
            "--world-db",
            str(WORLD),
            "--sequence",
            str(event["sequence"]),
            "--event-id",
            str(event["event_id"]),
            "--ingest-ref",
            ingest_ref,
        ]
        if user:
            args.extend(
                [
                    "--conversation-session-id",
                    self.session_id,
                    "--conversation-turn-index",
                    str(self.next_turn),
                ]
            )
        return self.run_cmd(args)

    def run_turn(self, core: HeadlessCore, event: dict[str, Any]) -> dict[str, Any]:
        assert core.runtime is not None
        text = self.user_text(event)
        occurred_at = self.event_time(event)
        result = core.submit_user_turn(
            session_id=self.session_id,
            turn_index=self.next_turn,
            user_input=text,
            occurred_at=occurred_at,
        )
        payload = {
            "session_id": self.session_id,
            "turn_index": self.next_turn,
            "occurred_at": occurred_at.isoformat(),
            "response": result.runtime.response,
            "silenced": result.runtime.silenced,
            "termination_reason": result.runtime.termination_reason,
            "model_rounds": result.runtime.model_rounds,
            "user_observation_id": result.conversation_commit.user_observation_id,
            "assistant_observation_id": result.conversation_commit.assistant_observation_id,
            "idempotent_replay": result.conversation_commit.idempotent_replay,
            "world_revision": result.conversation_commit.world_revision,
            "summary_error": result.continuity_summary_error,
            "capability_history": jsonable(result.runtime.capability_history),
        }
        atomic_json(RUN / "receipts" / f"turn_{self.next_turn:02d}.json", payload)
        return payload

    def checkpoint(self, cursor: int, extra: dict[str, Any]) -> None:
        payload = {
            "cursor": cursor,
            "at": utcnow().isoformat(),
            "clock": None if self.clock is None else self.clock.isoformat(),
            "next_turn": self.next_turn,
            "world_sha256": sha256_file(WORLD) if WORLD.exists() else None,
            "index_sha256": sha256_file(INDEX) if INDEX.exists() else None,
            "release_sha256": sha256_file(RELEASE_STATE) if RELEASE_STATE.exists() else None,
            **extra,
        }
        atomic_json(RUN / "checkpoints" / f"cursor_{cursor:02d}.json", payload)

    def process_cursor(self, cursor: int) -> None:
        self.set_status(state="RUNNING", stage="pre_event_due", cursor=cursor)
        event_probe_dir = RUN / "events"
        # Reveal first so we know event time, but do not ingest yet.
        self.set_status(state="RUNNING", stage="reveal", cursor=cursor)
        event = self.reveal()
        event_path = event_probe_dir / f"cursor_{cursor:02d}.json"
        atomic_json(event_path, event)
        sequence = event.get("sequence")
        if sequence != cursor:
            raise RuntimeError(f"revealed sequence {sequence} != cursor {cursor}")
        occurred_at = self.event_time(event)
        user = self.is_user_conversation(event)
        self.log(
            "revealed",
            cursor=cursor,
            sequence=sequence,
            event_id=event.get("event_id"),
            user_conversation=user,
            occurred_at=occurred_at.isoformat(),
            dimension=event.get("dimension"),
            source_kind=event.get("source_kind"),
            source_class=event.get("source_class"),
            modality=event.get("modality"),
        )

        if self.clock is not None and occurred_at > self.clock:
            pre_time = occurred_at - timedelta(microseconds=1)
            if pre_time > self.clock:
                self.set_status(state="RUNNING", stage="pre_event_due", cursor=cursor)
                core = self.open_core()
                try:
                    self.due_work(core, now=pre_time, label=f"cursor_{cursor:02d}_pre")
                finally:
                    core.stop()

        self.set_status(state="RUNNING", stage="ingest", cursor=cursor, user_conversation=user)
        ingest_result = self.ingest(event, event_path)
        atomic_json(RUN / "receipts" / f"ingest_{cursor:02d}.json", ingest_result)
        ingest_ref = self.ingest_ref_from(ingest_result.get("parsed"), event)
        self.log("ingested", cursor=cursor, path=ingest_result.get("path"), ingest_ref=ingest_ref)

        self.set_status(state="RUNNING", stage="ack", cursor=cursor, ingest_ref=ingest_ref)
        ack_result = self.ack(event, ingest_ref, user=user)
        atomic_json(RUN / "receipts" / f"ack_{cursor:02d}.json", ack_result)
        self.log("acked", cursor=cursor, parsed=ack_result.get("parsed"))

        core = self.open_core()
        try:
            assert core.index is not None
            core.index.catch_up()
            turn_payload = None
            if user:
                self.set_status(
                    state="RUNNING",
                    stage="run_turn",
                    cursor=cursor,
                    turn_index=self.next_turn,
                )
                turn_payload = self.run_turn(core, event)
                self.next_turn += 1
            self.clock = occurred_at
            self.set_status(state="RUNNING", stage="post_event_due", cursor=cursor)
            due = self.due_work(core, now=occurred_at, label=f"cursor_{cursor:02d}_post")
            status = core.status()
        finally:
            core.stop()

        self.checkpoint(
            cursor,
            {
                "event_id": event.get("event_id"),
                "user_conversation": user,
                "ingest_ref": ingest_ref,
                "turn": turn_payload,
                "due": {
                    "wakes": len(due.get("wakes") or []),
                    "post_summary_wakes": len(due.get("post_summary_wakes") or []),
                    "periodic_review": due.get("periodic_review"),
                },
                "world_revision": status["world_revision"],
                "index_watermark": status["index_watermark"],
            },
        )
        self.set_status(
            state="CURSOR_COMPLETE",
            stage="cursor_complete",
            cursor=cursor,
            world_revision=status["world_revision"],
            index_watermark=status["index_watermark"],
        )

    def run(self) -> None:
        self.set_status(state="STARTING", stage="fresh_init", cursor=0)
        self.ensure_fresh_world()
        self.init_release()
        self.set_status(state="READY", stage="initialized", cursor=0)
        for cursor in range(1, STOP_SEQUENCE + 1):
            self.process_cursor(cursor)
        self.set_status(
            state="RUN_COMPLETE_AWAITING_FREEZE",
            stage="phase_a_complete",
            cursor=STOP_SEQUENCE,
        )
        self.log("phase_a_complete", stop_sequence=STOP_SEQUENCE)


def main() -> int:
    operator = PhaseAOperator()
    try:
        operator.run()
        return 0
    except Exception as exc:
        tb = traceback.format_exc()
        operator.log("operator_crash", error=f"{type(exc).__name__}: {exc}", traceback=tb)
        operator.set_status(state="CRASHED", stage="crash", error=f"{type(exc).__name__}: {exc}")
        print(tb, file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
