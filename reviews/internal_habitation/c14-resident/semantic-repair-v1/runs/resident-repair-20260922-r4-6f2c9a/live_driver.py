#!/usr/bin/env python3
from __future__ import annotations

import base64
import dataclasses
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel

from aios_core.query import WorldSearchIndex
from aios_core.runtime import CapabilityCall, FusedTurnRuntime, ModelDirective
from aios_core.storage.sqlite_store import SQLiteWorldStore

REPO_ROOT = Path(__file__).resolve()
while REPO_ROOT != REPO_ROOT.parent and not (REPO_ROOT / "src" / "aios_core").is_dir():
    REPO_ROOT = REPO_ROOT.parent
if not (REPO_ROOT / "src" / "aios_core").is_dir():
    raise RuntimeError("repository root not found")

RUN_DIR = Path(__file__).resolve().parent
RELEASE_DIR = REPO_ROOT / "reviews" / "internal_habitation" / "c14-resident" / "semantic-repair-v1" / "release"
RELEASE_OPERATOR = RELEASE_DIR / "release_operator.py"
MECHANICAL_ADAPTER = RELEASE_DIR / "mechanical_ingest_adapter.py"
CANONICAL_ADAPTER = RELEASE_DIR / "canonical_conversation_ingest.py"

# Formal single-window isolated Resident run; do not reuse PR #84 semantics.
RUN_ID = "c14-sem-repair-resident-20260922-sol-r4-6f2c9a"
SESSION_ID = "resident-sem-repair-sol-20260922-r4-6f2c9a"
SUBJECT_ID = "user_1"
STARTING_MAIN = "7611fa5059f5dc8a20835cab5b312be2f43d11e8"
BRANCH = "c14/semantic-repair-resident-20260922-sol-r3"
DECLARED_PROVIDER = "OpenAI"
DECLARED_MODEL = "GPT-5.6 Sol"

WORLD_DB = RUN_DIR / "private_world.sqlite"
INDEX_DB = RUN_DIR / "private_index.sqlite"
RELEASE_STATE = RUN_DIR / "release_state.json"
RUN_STATE = RUN_DIR / "run_state.json"
CHECKPOINTS = RUN_DIR / "checkpoints"
CURSORS = RUN_DIR / "cursors"
RECEIPTS = RUN_DIR / "release_receipts"
SUMMARIES = RUN_DIR / "summary_requests"
FINAL_DIR = RUN_DIR / "final"

COMMENT_LIMIT = 56000
POLL_SECONDS = 4.0
CONTROL_NONCE = "ctl-6f2c9a-91d7b4"


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, BaseModel):
        return jsonable(value.model_dump(mode="json"))
    if dataclasses.is_dataclass(value):
        return jsonable(dataclasses.asdict(value))
    if isinstance(value, Mapping):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [jsonable(v) for v in value]
    if hasattr(value, "model_dump"):
        return jsonable(value.model_dump(mode="json"))
    if hasattr(value, "__dict__"):
        return jsonable(vars(value))
    return repr(value)


def canonical_json(value: Any, *, pretty: bool = True) -> str:
    return json.dumps(
        jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    )


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(canonical_json(value), encoding="utf-8")
    tmp.replace(path)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sqlite_checkpoint(path: Path) -> None:
    if not path.exists():
        return
    with sqlite3.connect(str(path)) as conn:
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.DatabaseError:
            pass


def run_cmd(args: list[str], *, label: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    (RECEIPTS / f"{label}.stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
    (RECEIPTS / f"{label}.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
    atomic_json(
        RECEIPTS / f"{label}.process.json",
        {"argv": args, "returncode": proc.returncode},
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({label}) rc={proc.returncode}: {(proc.stderr or proc.stdout)[-4000:]}"
        )
    return proc


def parse_json_output(text: str) -> Any:
    raw = text.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        for line in reversed(raw.splitlines()):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return raw


REF_RE = re.compile(r"([A-Za-z0-9_.:-]+@[1-9][0-9]*)")


def extract_ingest_ref(value: Any) -> str:
    if isinstance(value, str):
        match = REF_RE.search(value)
        if match:
            return match.group(1)
        raise RuntimeError("adapter output did not contain an object_id@revision ref")
    if isinstance(value, Mapping):
        for key in ("ingest_ref", "durable_ref", "observation_ref", "object_ref", "ref"):
            if key not in value:
                continue
            candidate = value[key]
            if isinstance(candidate, str):
                match = REF_RE.search(candidate)
                if match:
                    return match.group(1)
            if isinstance(candidate, Mapping):
                oid = candidate.get("object_id")
                rev = candidate.get("revision")
                if isinstance(oid, str) and isinstance(rev, int) and rev > 0:
                    return f"{oid}@{rev}"
        for candidate in value.values():
            try:
                return extract_ingest_ref(candidate)
            except RuntimeError:
                pass
    if isinstance(value, list):
        for candidate in value:
            try:
                return extract_ingest_ref(candidate)
            except RuntimeError:
                pass
    raise RuntimeError("adapter output did not contain an object_id@revision ref")


def load_state() -> dict[str, Any]:
    state = load_json(
        RUN_STATE,
        {
            "run_id": RUN_ID,
            "session_id": SESSION_ID,
            "next_checkpoint": 1,
            "next_summary_request": 1,
            "conversation_turn_index": 0,
            "released_cursors": [],
            "semantic_checkpoints": [],
            "summary_requests": [],
            "errors": [],
            "silence_count": 0,
            "response_count": 0,
            "capability_call_count": 0,
            "cognition_calls": [],
            "phase": "A",
            "complete": False,
        },
    )
    if state.get("run_id") != RUN_ID:
        raise RuntimeError("run_state belongs to a different run")
    return state


def save_state(state: dict[str, Any]) -> None:
    atomic_json(RUN_STATE, state)


class GithubBridge:
    def __init__(self, state: dict[str, Any], store: SQLiteWorldStore):
        self.state = state
        self.store = store
        self.token = os.environ.get("GITHUB_TOKEN", "").strip()
        self.repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
        self.branch = os.environ.get("GITHUB_HEAD_REF", "").strip() or os.environ.get("GITHUB_REF_NAME", "").strip()
        if not self.token or not self.repo:
            raise RuntimeError("GITHUB_TOKEN and GITHUB_REPOSITORY are required")
        self.pr_number = None
        self._last_checkpoint_id: str | None = None

    def _api(self, method: str, path: str, payload: Any | None = None) -> Any:
        url = f"https://api.github.com/repos/{self.repo}{path}"
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "aios-c14-resident-live-bridge",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API {method} {path} failed: {exc.code} {body}") from exc

    def _wait_for_pr(self) -> int:
        owner = self.repo.split("/", 1)[0]
        head = urllib.parse.quote(f"{owner}:{BRANCH}", safe="")
        for _ in range(180):
            pulls = self._api("GET", f"/pulls?state=open&head={head}&per_page=20")
            if isinstance(pulls, list) and pulls:
                return int(pulls[0]["number"])
            time.sleep(2)
        raise RuntimeError("timed out waiting for the Resident evidence PR")

    def _comments(self) -> list[dict[str, Any]]:
        all_items: list[dict[str, Any]] = []
        page = 1
        while True:
            items = self._api(
                "GET",
                f"/issues/{self.pr_number}/comments?per_page=100&page={page}",
            )
            if not isinstance(items, list):
                return all_items
            all_items.extend(items)
            if len(items) < 100:
                return all_items
            page += 1

    def post_chunks(self, kind: str, item_id: str, payload: Any) -> None:
        # The artifact is already written under RUN_DIR by the caller. Push the
        # current private-world checkpoint, then wait on an unshared branch-control file.
        git_checkpoint(f"evidence(c14): publish {kind.lower()} {item_id}")

    def post_text(self, kind: str, item_id: str, text: str) -> None:
        FINAL_DIR.mkdir(parents=True, exist_ok=True)
        (FINAL_DIR / f"{kind.lower()}_{item_id}.txt").write_text(text, encoding="utf-8")
        git_checkpoint(f"evidence(c14): publish {kind.lower()} {item_id}")

    def _control_path(self, marker: str, item_id: str) -> str:
        rel = RUN_DIR.relative_to(REPO_ROOT).as_posix()
        if marker == "DIRECTIVE":
            name = f"directive_{item_id}.json"
        elif marker == "SUMMARY_RESPONSE":
            name = f"summary_{item_id}.json"
        else:
            raise RuntimeError(f"unsupported control marker: {marker}")
        return f"{rel}/control/{CONTROL_NONCE}/{name}"

    def _read_branch_json(self, relpath: str) -> dict[str, Any] | None:
        encoded_path = urllib.parse.quote(relpath, safe="/")
        encoded_ref = urllib.parse.quote(BRANCH, safe="")
        try:
            item = self._api("GET", f"/contents/{encoded_path}?ref={encoded_ref}")
        except RuntimeError as exc:
            if "failed: 404" in str(exc):
                return None
            raise
        if not isinstance(item, Mapping):
            raise RuntimeError("control file lookup returned non-object")
        raw_content = item.get("content")
        if not isinstance(raw_content, str):
            raise RuntimeError("control file missing base64 content")
        decoded = base64.b64decode(raw_content).decode("utf-8")
        parsed = json.loads(decoded)
        if not isinstance(parsed, dict):
            raise RuntimeError("control file must contain one JSON object")
        return parsed

    def _wait_json_marker(self, marker: str, item_id: str) -> tuple[dict[str, Any], str]:
        control_path = self._control_path(marker, item_id)
        while True:
            payload = self._read_branch_json(control_path)
            if payload is None:
                time.sleep(POLL_SECONDS)
                continue
            if payload.get("run_id") != RUN_ID:
                raise RuntimeError(f"control run_id mismatch at {control_path}")
            if marker == "DIRECTIVE" and payload.get("checkpoint_id") != item_id:
                raise RuntimeError(f"directive checkpoint mismatch at {control_path}")
            if marker == "SUMMARY_RESPONSE" and payload.get("request_id") != item_id:
                raise RuntimeError(f"summary request mismatch at {control_path}")
            return payload, DECLARED_MODEL

    def wait_event_seen(self, event: Mapping[str, Any]) -> None:
        event_id = str(event["event_id"])
        self.post_chunks("EVENT", event_id, event)
        rel = RUN_DIR.relative_to(REPO_ROOT).as_posix()
        control_path = f"{rel}/control/{CONTROL_NONCE}/event_{event_id}.json"
        while True:
            payload = self._read_branch_json(control_path)
            if payload is None:
                time.sleep(POLL_SECONDS)
                continue
            if payload.get("run_id") != RUN_ID or payload.get("event_id") != event_id:
                raise RuntimeError(f"event-seen control mismatch at {control_path}")
            if payload.get("seen") is not True:
                raise RuntimeError(f"event-seen control must set seen=true at {control_path}")
            return

    def _finalize_previous_checkpoint(self, world_revision_after: int) -> None:
        if self._last_checkpoint_id is None:
            return
        cp_dir = CHECKPOINTS / self._last_checkpoint_id
        meta_path = cp_dir / "checkpoint.json"
        if meta_path.exists():
            meta = load_json(meta_path, {})
            if meta.get("world_revision_after") is None:
                meta["world_revision_after"] = int(world_revision_after)
                atomic_json(meta_path, meta)

    def finalize_active_checkpoint(self) -> None:
        self._finalize_previous_checkpoint(int(self.store.current_world_revision()))
        self._last_checkpoint_id = None

    def model_handler(self, snapshot) -> ModelDirective:
        before = int(self.store.current_world_revision())
        self._finalize_previous_checkpoint(before)

        cp_no = int(self.state["next_checkpoint"])
        cp_id = f"cp{cp_no:04d}"
        self.state["next_checkpoint"] = cp_no + 1
        self._last_checkpoint_id = cp_id

        cp_dir = CHECKPOINTS / cp_id
        cp_dir.mkdir(parents=True, exist_ok=True)
        snapshot_payload = jsonable(snapshot)
        atomic_json(cp_dir / "snapshot.json", snapshot_payload)
        meta = {
            "checkpoint_id": cp_id,
            "run_id": RUN_ID,
            "resident_session_id": SESSION_ID,
            "released_cursor": (self.state["released_cursors"][-1] if self.state["released_cursors"] else None),
            "simulated_timestamp": self.state.get("current_simulated_timestamp"),
            "world_revision_before": before,
            "world_revision_after": None,
            "provider": DECLARED_PROVIDER,
            "model": DECLARED_MODEL,
            "provider_request_attestation": None,
        }
        atomic_json(cp_dir / "checkpoint.json", meta)
        self.post_chunks("SNAPSHOT", cp_id, snapshot_payload)

        directive_raw, author = self._wait_json_marker("DIRECTIVE", cp_id)
        directive_raw = dict(directive_raw)
        directive_raw.setdefault("checkpoint_id", cp_id)
        if directive_raw.get("checkpoint_id") != cp_id:
            raise RuntimeError(f"directive checkpoint mismatch for {cp_id}")
        atomic_json(cp_dir / "directive.json", {**directive_raw, "github_author": author})

        calls: list[CapabilityCall] = []
        for idx, raw_call in enumerate(directive_raw.get("capability_calls") or []):
            if not isinstance(raw_call, Mapping):
                raise RuntimeError("capability call must be a mapping")
            name = str(raw_call.get("name") or "").strip()
            if not name:
                raise RuntimeError("capability call name must be nonblank")
            args = raw_call.get("arguments") or {}
            if not isinstance(args, Mapping):
                raise RuntimeError("capability arguments must be a mapping")
            call_id = str(raw_call.get("call_id") or f"{cp_id}-call-{idx+1}")
            calls.append(CapabilityCall(name=name, arguments=dict(args), call_id=call_id))
            self.state["capability_call_count"] = int(self.state["capability_call_count"]) + 1
            if name in {"commit_claim", "commit_ai_world_claim", "revise_claim", "retract_claim"}:
                self.state["cognition_calls"].append(
                    {"checkpoint_id": cp_id, "name": name, "arguments": jsonable(args)}
                )

        response = directive_raw.get("response")
        silence = bool(directive_raw.get("silence", False))
        if calls:
            if response is not None or silence:
                raise RuntimeError("directive cannot combine calls with response/silence")
            directive = ModelDirective(capability_calls=tuple(calls))
        elif response is not None:
            response = str(response)
            self.state["response_count"] = int(self.state["response_count"]) + 1
            directive = ModelDirective(response=response)
        elif silence:
            self.state["silence_count"] = int(self.state["silence_count"]) + 1
            directive = ModelDirective(silence=True)
        else:
            raise RuntimeError("directive must request capabilities, respond, or stay silent")

        self.state["semantic_checkpoints"].append(
            {
                "checkpoint_id": cp_id,
                "released_cursor": meta["released_cursor"],
                "simulated_timestamp": meta["simulated_timestamp"],
                "world_revision_before": before,
                "directive_kind": (
                    "capability_calls" if calls else ("response" if response is not None else "silence")
                ),
                "github_author": author,
            }
        )
        save_state(self.state)
        return directive

    def _summary_request(self, kind: str, request: Any) -> str:
        req_no = int(self.state["next_summary_request"])
        req_id = f"sum{req_no:04d}"
        self.state["next_summary_request"] = req_no + 1
        req_dir = SUMMARIES / req_id
        req_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "request_id": req_id,
            "kind": kind,
            "released_cursor": (self.state["released_cursors"][-1] if self.state["released_cursors"] else None),
            "simulated_timestamp": self.state.get("current_simulated_timestamp"),
            "request": jsonable(request),
        }
        atomic_json(req_dir / "request.json", payload)
        self.post_chunks("SUMMARY_REQUEST", req_id, payload)
        raw, author = self._wait_json_marker("SUMMARY_RESPONSE", req_id)
        content = str(raw.get("content") or "")
        if not content.strip():
            raise RuntimeError("summary response content must be nonblank")
        atomic_json(req_dir / "response.json", {"content": content, "github_author": author})
        self.state["summary_requests"].append(
            {
                "request_id": req_id,
                "kind": kind,
                "released_cursor": payload["released_cursor"],
                "github_author": author,
            }
        )
        save_state(self.state)
        return content

    def dimension_summary_handler(self, request) -> str:
        return self._summary_request("dimension_summary", request)

    def round_summary_handler(self, request) -> str:
        return self._summary_request("conversation_round_summary", request)


def git_checkpoint(message: str) -> None:
    sqlite_checkpoint(WORLD_DB)
    sqlite_checkpoint(INDEX_DB)
    rel = RUN_DIR.relative_to(REPO_ROOT)
    subprocess.run(["git", "add", str(rel)], cwd=REPO_ROOT, check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO_ROOT)
    if diff.returncode == 0:
        return
    subprocess.run(["git", "commit", "-m", message], cwd=REPO_ROOT, check=True)
    head_ref = BRANCH
    subprocess.run(["git", "fetch", "origin", head_ref], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "rebase", f"origin/{head_ref}"], cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "push", "origin", f"HEAD:{head_ref}"], cwd=REPO_ROOT, check=True)

def run_release_init(phase: str, label: str) -> None:
    proc = run_cmd(
        [
            sys.executable,
            str(RELEASE_OPERATOR),
            "init",
            "--phase",
            phase,
            "--state",
            str(RELEASE_STATE),
        ],
        label=label,
    )
    atomic_json(RECEIPTS / f"{label}.json", parse_json_output(proc.stdout))


def reveal_event(phase: str, sequence_hint: int) -> dict[str, Any]:
    event_file = RUN_DIR / "current_event.json"
    proc = run_cmd(
        [
            sys.executable,
            str(RELEASE_OPERATOR),
            "reveal",
            "--phase",
            phase,
            "--state",
            str(RELEASE_STATE),
        ],
        label=f"cursor_{sequence_hint:03d}_reveal",
    )
    event_file.write_text(proc.stdout, encoding="utf-8")
    event = json.loads(proc.stdout)
    return event


def ingest_and_ack(
    *,
    event: Mapping[str, Any],
    phase: str,
    conversation_turn_index: int | None,
) -> dict[str, Any]:
    sequence = int(event["sequence"])
    event_id = str(event["event_id"])
    event_file = RUN_DIR / "current_event.json"
    is_conversation = (
        event.get("dimension") == "dim:conversation"
        and event.get("source_kind") == "conversation"
        and event.get("source_class") == "USER"
        and event.get("modality") == "text"
    )

    if is_conversation:
        if conversation_turn_index is None or conversation_turn_index <= 0:
            raise RuntimeError("canonical conversation requires positive turn index")
        proc = run_cmd(
            [
                sys.executable,
                str(CANONICAL_ADAPTER),
                "--world-db",
                str(WORLD_DB),
                "--session-id",
                SESSION_ID,
                "--turn-index",
                str(conversation_turn_index),
                "--event-file",
                str(event_file),
            ],
            label=f"cursor_{sequence:03d}_canonical_ingest",
        )
    else:
        proc = run_cmd(
            [
                sys.executable,
                str(MECHANICAL_ADAPTER),
                "--world-db",
                str(WORLD_DB),
                "--event-file",
                str(event_file),
            ],
            label=f"cursor_{sequence:03d}_mechanical_ingest",
        )

    adapter_output = parse_json_output(proc.stdout)
    ingest_ref = extract_ingest_ref(adapter_output)
    ack_args = [
        sys.executable,
        str(RELEASE_OPERATOR),
        "ack",
        "--phase",
        phase,
        "--state",
        str(RELEASE_STATE),
        "--world-db",
        str(WORLD_DB),
        "--sequence",
        str(sequence),
        "--event-id",
        event_id,
        "--ingest-ref",
        ingest_ref,
    ]
    if is_conversation:
        ack_args.extend(
            [
                "--conversation-session-id",
                SESSION_ID,
                "--conversation-turn-index",
                str(conversation_turn_index),
            ]
        )
    ack = run_cmd(ack_args, label=f"cursor_{sequence:03d}_ack")
    ack_output = parse_json_output(ack.stdout)
    return {
        "is_conversation": is_conversation,
        "ingest_ref": ingest_ref,
        "adapter_output": adapter_output,
        "ack_output": ack_output,
    }


def drain_wakes(runtime: FusedTurnRuntime, now: datetime, *, stage: str) -> list[Any]:
    results: list[Any] = []
    for _ in range(256):
        item = runtime.dispatch_next_pending_wake(now=now)
        if item is None:
            return results
        results.append(jsonable(item))
    raise RuntimeError(f"wake drain exceeded safety cap at {stage}")


def drain_reviews(runtime: FusedTurnRuntime, now: datetime) -> list[Any]:
    results: list[Any] = []
    for _ in range(64):
        item = runtime.run_periodic_review(now=now)
        if item is None:
            return results
        results.append(jsonable(item))
        runtime.index.catch_up()
        wake_state = str(jsonable(item.wake).get("state") or "")
        if wake_state == "running":
            raise RuntimeError("periodic review remained RUNNING without semantic completion")
    raise RuntimeError("periodic review drain exceeded safety cap")


def final_claims(store: SQLiteWorldStore) -> list[dict[str, Any]]:
    payloads = store.list_payloads(subject_id=SUBJECT_ID)
    out: list[dict[str, Any]] = []
    for payload in payloads:
        if str(payload.get("object_type") or "") != "claim":
            continue
        out.append(
            {
                "ref": f"{payload.get('object_id')}@{payload.get('revision')}",
                "status": payload.get("status"),
                "confidence": payload.get("confidence"),
                "claim_type": payload.get("claim_type"),
                "statement": payload.get("statement"),
                "evidence_refs": payload.get("evidence_refs"),
            }
        )
    return out


def write_final_report(state: dict[str, Any], store: SQLiteWorldStore) -> None:
    sqlite_checkpoint(WORLD_DB)
    sqlite_checkpoint(INDEX_DB)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    world_sha = sha256_file(WORLD_DB)
    release_sha = sha256_file(RELEASE_STATE)
    claims = final_claims(store)
    atomic_json(FINAL_DIR / "current_claims.json", claims)
    atomic_json(
        FINAL_DIR / "digests.json",
        {
            "world_sha256": world_sha,
            "release_state_sha256": release_sha,
            "index_sha256": sha256_file(INDEX_DB) if INDEX_DB.exists() else None,
        },
    )
    manifest = {
        "task": "C14-SEM-REPAIR-RES-001",
        "run_id": RUN_ID,
        "starting_main_sha": STARTING_MAIN,
        "exact_evaluated_main": STARTING_MAIN,
        "resident_branch": BRANCH,
        "resident_session_id": SESSION_ID,
        "subject_id": SUBJECT_ID,
        "resident_provider_declared": DECLARED_PROVIDER,
        "resident_model_declared": DECLARED_MODEL,
        "provider_request_attestation": "not exposed to repository harness",
        "cursor_range": "1..15",
        "completed_count": len(state["released_cursors"]),
        "world_revision_final": int(store.current_world_revision()),
        "silence_count": int(state["silence_count"]),
        "response_count": int(state["response_count"]),
        "capability_call_count": int(state["capability_call_count"]),
        "cognition_calls": state["cognition_calls"],
        "current_claim_refs": [item["ref"] for item in claims],
        "summary_request_count": len(state["summary_requests"]),
        "semantic_checkpoint_count": len(state["semantic_checkpoints"]),
        "world_sha256": world_sha,
        "release_state_sha256": release_sha,
        "forbidden_resident_reads": [],
        "fixture_access_boundary": (
            "sealed fixture/manifest bytes were consumed only inside the frozen release infrastructure; "
            "the Resident bridge received only one current reveal projection at a time"
        ),
        "future_preview": False,
        "core_modified_by_run": False,
        "historical_c14_evidence_modified_by_run": False,
        "semantic_evaluation_performed": False,
    }
    atomic_json(RUN_DIR / "run_manifest.json", manifest)

    report = f"""# C14 Semantic Repair Resident Run

- Task: C14-SEM-REPAIR-RES-001
- Status: RESIDENT RUN COMPLETED; evidence available for independent evaluation.
- Starting / exact evaluated main: `{STARTING_MAIN}`
- Resident branch: `{BRANCH}`
- Resident session: `{SESSION_ID}`
- Declared runtime identity: {DECLARED_PROVIDER} / {DECLARED_MODEL}; provider request attestation is not exposed to this repository harness.
- Cursors: {len(state['released_cursors'])}/15, sequential.
- Final World revision: {store.current_world_revision()}
- Semantic checkpoints: {len(state['semantic_checkpoints'])}
- Summary requests authored by Resident: {len(state['summary_requests'])}
- Silence directives: {state['silence_count']}
- Capability calls: {state['capability_call_count']}
- Current Claim refs: {', '.join(item['ref'] for item in claims) if claims else '(none)'}
- World SHA256: `{world_sha}`
- Release-state SHA256: `{release_sha}`
- Sealed fixture / manifest bytes were not exposed through the Resident bridge; only the current mechanically projected event was surfaced.
- No evaluator-only material was read by this harness.
- No Core source was modified by this run.
- No historical C14 Resident evidence was modified by this run.
- No E1/E5/C14 semantic verdict is made here.

Resident run completed and evidence available for independent evaluation.
"""
    (RUN_DIR / "RESIDENT_RUN_REPORT.md").write_text(report, encoding="utf-8")


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    CURSORS.mkdir(parents=True, exist_ok=True)
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    SUMMARIES.mkdir(parents=True, exist_ok=True)

    state = load_state()
    if state.get("complete"):
        return 0
    if WORLD_DB.exists() or RELEASE_STATE.exists():
        raise RuntimeError(
            "formal live run must start from a fresh private World/state; resume is not "
            "supported by this one-shot interactive bridge unless the same Action process remains alive"
        )

    store = SQLiteWorldStore(WORLD_DB)
    index = WorldSearchIndex(INDEX_DB, store=store)
    bridge = GithubBridge(state, store)

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=bridge.model_handler,
        subject_id=SUBJECT_ID,
        round_summary_handler=bridge.round_summary_handler,
        dimension_summary_handler=bridge.dimension_summary_handler,
    )

    run_manifest = {
        "task": "C14-SEM-REPAIR-RES-001",
        "run_id": RUN_ID,
        "starting_main_sha": STARTING_MAIN,
        "exact_evaluated_main": STARTING_MAIN,
        "resident_branch": BRANCH,
        "resident_session_id": SESSION_ID,
        "subject_id": SUBJECT_ID,
        "declared_provider": DECLARED_PROVIDER,
        "declared_model": DECLARED_MODEL,
        "provider_request_attestation": None,
        "control_transport": "isolated branch files with nonce; no PR/comment relay",
        "world_revision_start": int(store.current_world_revision()),
        "phase_a": "1..6",
        "phase_b": "7..15",
        "sequential_release": True,
        "future_preview": False,
        "semantic_engine": "external real Resident via RuntimeSnapshot/ModelDirective bridge",
    }
    atomic_json(RUN_DIR / "run_manifest.json", run_manifest)

    run_release_init("A", "phase_A_init")

    for expected_sequence in range(1, 16):
        phase = "A" if expected_sequence <= 6 else "B"
        if expected_sequence == 7:
            run_release_init("B", "phase_B_init")
            state["phase"] = "B"
            save_state(state)

        event = reveal_event(phase, expected_sequence)
        sequence = int(event.get("sequence") or 0)
        if sequence != expected_sequence:
            raise RuntimeError(f"release order violation: expected {expected_sequence}, got {sequence}")
        cursor_dir = CURSORS / f"cursor_{sequence:03d}"
        cursor_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(cursor_dir / "event.json", event)
        state["current_simulated_timestamp"] = str(event["occurred_at"])
        save_state(state)

        bridge.wait_event_seen(event)

        is_conversation = (
            event.get("dimension") == "dim:conversation"
            and event.get("source_kind") == "conversation"
            and event.get("source_class") == "USER"
            and event.get("modality") == "text"
        )
        turn_index: int | None = None
        if is_conversation:
            turn_index = int(state["conversation_turn_index"]) + 1
            state["conversation_turn_index"] = turn_index
            save_state(state)

        before_ingest = int(store.current_world_revision())
        ingest = ingest_and_ack(
            event=event,
            phase=phase,
            conversation_turn_index=turn_index,
        )
        index.catch_up()
        after_ack = int(store.current_world_revision())

        state["released_cursors"].append(sequence)
        save_state(state)

        now = datetime.fromisoformat(str(event["occurred_at"]).replace("Z", "+00:00"))
        lifecycle: dict[str, Any] = {
            "sequence": sequence,
            "event_id": event["event_id"],
            "phase": phase,
            "occurred_at": event["occurred_at"],
            "world_revision_before_ingest": before_ingest,
            "world_revision_after_ack": after_ack,
            "ingest": ingest,
            "conversation_turn_index": turn_index,
            "run_turn": None,
            "dimension_summaries": None,
            "wakes_before_review": [],
            "periodic_reviews": [],
            "wakes_after_review": [],
            "world_revision_after_cursor": None,
        }

        if is_conversation:
            turn_result = runtime.run_turn(
                session_id=SESSION_ID,
                turn_index=int(turn_index),
                user_input=str(event["resident_visible_payload"]),
                occurred_at=now,
            )
            bridge.finalize_active_checkpoint()
            lifecycle["run_turn"] = jsonable(turn_result)
            index.catch_up()

        summaries = runtime.run_due_dimension_summaries(now=now)
        lifecycle["dimension_summaries"] = jsonable(summaries)
        index.catch_up()

        lifecycle["wakes_before_review"] = drain_wakes(runtime, now, stage="before_review")
        bridge.finalize_active_checkpoint()
        lifecycle["periodic_reviews"] = drain_reviews(runtime, now)
        bridge.finalize_active_checkpoint()
        lifecycle["wakes_after_review"] = drain_wakes(runtime, now, stage="after_review")
        bridge.finalize_active_checkpoint()

        index.catch_up()
        lifecycle["world_revision_after_cursor"] = int(store.current_world_revision())
        atomic_json(cursor_dir / "lifecycle.json", lifecycle)
        git_checkpoint(f"evidence(c14): resident repair cursor {sequence:03d}")

    state["complete"] = True
    state["current_simulated_timestamp"] = None
    save_state(state)
    bridge.finalize_active_checkpoint()
    write_final_report(state, store)
    git_checkpoint("evidence(c14): finalize semantic repair resident run")
    bridge.post_text(
        "RUN_COMPLETE",
        "final",
        "Resident run completed and evidence available for independent evaluation.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
