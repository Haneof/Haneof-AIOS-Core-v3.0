#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

OPERATOR_VERSION = "c14-blind-release-operator-v2"
STATE_VERSION = "c14-release-state-v2"
FIXTURE_VERSION = "c14-resident-fixture-v2"
SCHEMA_VERSION = "c14-resident-event-v2"
CONTRACT_VERSION = "c14-sequential-release-v2"
PHASE_A_MAX = 24
PHASE_B_START = 25
ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "fixture" / "sealed_fixture.json"
MANIFEST_PATH = ROOT / "fixture" / "fixture_manifest.json"
VISIBLE_KEYS = (
    "event_id",
    "sequence",
    "occurred_at",
    "dimension",
    "source_kind",
    "source_class",
    "modality",
    "resident_visible_payload",
)
INGEST_REF_RE = re.compile(r"^[A-Za-z0-9_.:/-]+@[1-9][0-9]*$")


class ReleaseError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReleaseError(f"required file missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseError(f"invalid JSON: {path}") from exc


def _sha256_file(path: Path) -> str:
    try:
        data = path.read_bytes()
    except FileNotFoundError as exc:
        raise ReleaseError(f"required file missing: {path}") from exc
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _parse_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ReleaseError(f"invalid occurred_at: {value}") from exc


def _load_bundle() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    fixture = _read_json(FIXTURE_PATH)
    manifest = _read_json(MANIFEST_PATH)
    digest = _sha256_file(FIXTURE_PATH)
    if manifest.get("fixture_sha256") != digest:
        raise ReleaseError("fixture digest mismatch")
    for key, expected in (
        ("fixture_version", FIXTURE_VERSION),
        ("schema_version", SCHEMA_VERSION),
        ("release_contract_version", CONTRACT_VERSION),
    ):
        if fixture.get(key) != expected:
            raise ReleaseError(f"fixture {key} mismatch")
        if manifest.get(key) != expected:
            raise ReleaseError(f"manifest {key} mismatch")
    if manifest.get("release_operator_version") != OPERATOR_VERSION:
        raise ReleaseError("release operator version mismatch")
    events = fixture.get("events")
    if not isinstance(events, list) or not events:
        raise ReleaseError("fixture events missing")
    if manifest.get("event_count") != len(events):
        raise ReleaseError("manifest event_count mismatch")
    ids = [event.get("event_id") for event in events]
    if len(ids) != len(set(ids)):
        raise ReleaseError("duplicate event id")
    previous = None
    for index, event in enumerate(events, start=1):
        if event.get("sequence") != index:
            raise ReleaseError("non-contiguous event sequence")
        if event.get("phase") not in {"A", "B"}:
            raise ReleaseError("invalid phase")
        current = _parse_time(str(event.get("occurred_at")))
        if current.tzinfo is None:
            raise ReleaseError("occurred_at missing timezone")
        if previous is not None and current <= previous:
            raise ReleaseError("event time is not strictly increasing")
        previous = current
    phase_a = [e for e in events if e["phase"] == "A"]
    phase_b = [e for e in events if e["phase"] == "B"]
    if len(phase_a) != manifest.get("phase_a_count") or len(phase_b) != manifest.get("phase_b_count"):
        raise ReleaseError("phase count mismatch")
    handoff = manifest.get("handoff") or {}
    if handoff.get("phase_a_final_cursor") != PHASE_A_MAX or handoff.get("phase_b_first_cursor") != PHASE_B_START:
        raise ReleaseError("handoff cursor mismatch")
    if events[PHASE_A_MAX - 1]["phase"] != "A" or events[PHASE_B_START - 1]["phase"] != "B":
        raise ReleaseError("phase boundary mismatch")
    if any(e["phase"] != "A" for e in events[:PHASE_A_MAX]) or any(e["phase"] != "B" for e in events[PHASE_B_START - 1:]):
        raise ReleaseError("non-contiguous phase layout")
    return fixture, manifest, events


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _load_state(path: Path, manifest: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    state = _read_json(path)
    if state.get("state_version") != STATE_VERSION:
        raise ReleaseError("state version mismatch")
    if state.get("fixture_version") != FIXTURE_VERSION:
        raise ReleaseError("state fixture version mismatch")
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ReleaseError("state schema version mismatch")
    if state.get("release_contract_version") != CONTRACT_VERSION:
        raise ReleaseError("state contract version mismatch")
    if state.get("fixture_sha256") != manifest.get("fixture_sha256"):
        raise ReleaseError("state fixture digest mismatch")
    phase = state.get("active_phase")
    if phase not in {"A", "B"}:
        raise ReleaseError("invalid active phase")
    last = state.get("last_acked_sequence")
    nxt = state.get("next_sequence")
    if not isinstance(last, int) or not isinstance(nxt, int) or nxt != last + 1:
        raise ReleaseError("invalid cursor state")
    receipts = state.get("receipts")
    if not isinstance(receipts, list) or len(receipts) != last:
        raise ReleaseError("release receipt chain mismatch")
    for expected, receipt in enumerate(receipts, start=1):
        if receipt.get("sequence") != expected:
            raise ReleaseError("release receipt sequence mismatch")
        event = events[expected - 1]
        if receipt.get("event_id") != event["event_id"]:
            raise ReleaseError("release receipt event mismatch")
        if receipt.get("fixture_sha256") != manifest.get("fixture_sha256"):
            raise ReleaseError("release receipt digest mismatch")
        if not INGEST_REF_RE.fullmatch(str(receipt.get("ingest_ref", ""))):
            raise ReleaseError("invalid durable ingest reference in receipt")
    if last == 0:
        if state.get("last_acked_event_id") is not None:
            raise ReleaseError("invalid initial last event")
    else:
        if last > len(events) or state.get("last_acked_event_id") != events[last - 1]["event_id"]:
            raise ReleaseError("last acked event mismatch")
    pending = state.get("pending_reveal")
    if pending is not None:
        if not isinstance(pending, dict):
            raise ReleaseError("invalid pending reveal")
        if pending.get("sequence") != nxt:
            raise ReleaseError("pending reveal cursor mismatch")
        if nxt > len(events) or pending.get("event_id") != events[nxt - 1]["event_id"]:
            raise ReleaseError("pending reveal event mismatch")
    if phase == "A" and nxt > PHASE_B_START:
        raise ReleaseError("Phase A cursor exceeded sealed handoff")
    if phase == "B" and nxt < PHASE_B_START:
        raise ReleaseError("Phase B cannot access Phase A cursor")
    return state


def _emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def _projection(event: dict[str, Any]) -> dict[str, Any]:
    return {key: event[key] for key in VISIBLE_KEYS}


def _phase_guard(phase_arg: str, state: dict[str, Any], events: list[dict[str, Any]]) -> int:
    if phase_arg != state["active_phase"]:
        raise ReleaseError("requested phase does not match active state")
    nxt = state["next_sequence"]
    if nxt > len(events):
        raise ReleaseError("fixture release already complete")
    if phase_arg == "A":
        if nxt > PHASE_A_MAX:
            raise ReleaseError("Phase A sealed handoff reached; cursor 25 is forbidden")
        if events[nxt - 1]["phase"] != "A":
            raise ReleaseError("Phase A event boundary mismatch")
    else:
        if nxt < PHASE_B_START:
            raise ReleaseError("Phase B cannot release Phase A events")
        if events[nxt - 1]["phase"] != "B":
            raise ReleaseError("Phase B event boundary mismatch")
    return nxt


def cmd_init(args: argparse.Namespace) -> None:
    _, manifest, events = _load_bundle()
    state_path = Path(args.state)
    if args.phase == "A":
        if state_path.exists():
            raise ReleaseError("state already exists")
        state = {
            "state_version": STATE_VERSION,
            "fixture_version": FIXTURE_VERSION,
            "schema_version": SCHEMA_VERSION,
            "release_contract_version": CONTRACT_VERSION,
            "fixture_sha256": manifest["fixture_sha256"],
            "active_phase": "A",
            "last_acked_sequence": 0,
            "last_acked_event_id": None,
            "next_sequence": 1,
            "pending_reveal": None,
            "receipts": [],
        }
        _atomic_write(state_path, state)
        _emit({"status": "initialized", "phase": "A", "next_sequence": 1, "fixture_sha256": manifest["fixture_sha256"]})
        return
    if not state_path.exists():
        raise ReleaseError("Phase B requires existing Phase-A handoff state")
    state = _load_state(state_path, manifest, events)
    if state["active_phase"] != "A":
        raise ReleaseError("Phase B initialization requires active Phase A handoff state")
    if state["pending_reveal"] is not None:
        raise ReleaseError("cannot enter Phase B with unacknowledged reveal")
    if state["last_acked_sequence"] != PHASE_A_MAX or state["next_sequence"] != PHASE_B_START:
        raise ReleaseError("Phase B must start exactly at cursor 25 after ack 24")
    state["active_phase"] = "B"
    _atomic_write(state_path, state)
    _emit({"status": "initialized", "phase": "B", "next_sequence": PHASE_B_START, "fixture_sha256": manifest["fixture_sha256"]})


def cmd_reveal(args: argparse.Namespace) -> None:
    _, manifest, events = _load_bundle()
    state_path = Path(args.state)
    if not state_path.exists():
        raise ReleaseError("release state does not exist")
    state = _load_state(state_path, manifest, events)
    nxt = _phase_guard(args.phase, state, events)
    event = events[nxt - 1]
    pending = state.get("pending_reveal")
    if pending is None:
        state["pending_reveal"] = {
            "sequence": event["sequence"],
            "event_id": event["event_id"],
            "occurred_at": event["occurred_at"],
            "fixture_sha256": manifest["fixture_sha256"],
        }
        _atomic_write(state_path, state)
    else:
        if pending.get("sequence") != event["sequence"] or pending.get("event_id") != event["event_id"]:
            raise ReleaseError("pending reveal does not match current cursor")
    _emit(_projection(event))


def _validate_ingest_ref(value: str) -> None:
    if not INGEST_REF_RE.fullmatch(value):
        raise ReleaseError("ack requires durable ingest reference in object_id@revision form")


def cmd_ack(args: argparse.Namespace) -> None:
    _, manifest, events = _load_bundle()
    state_path = Path(args.state)
    if not state_path.exists():
        raise ReleaseError("release state does not exist")
    state = _load_state(state_path, manifest, events)
    nxt = _phase_guard(args.phase, state, events)
    _validate_ingest_ref(args.ingest_ref)
    pending = state.get("pending_reveal")
    if pending is None:
        raise ReleaseError("no pending reveal to acknowledge")
    if args.sequence != nxt or args.sequence != pending.get("sequence"):
        raise ReleaseError("ack sequence is not the current revealed event")
    if args.event_id != pending.get("event_id"):
        raise ReleaseError("ack event id is not the current revealed event")
    event = events[nxt - 1]
    receipt = {
        "fixture_sha256": manifest["fixture_sha256"],
        "sequence": event["sequence"],
        "event_id": event["event_id"],
        "occurred_at": event["occurred_at"],
        "ingest_ref": args.ingest_ref,
    }
    state["receipts"].append(receipt)
    state["last_acked_sequence"] = event["sequence"]
    state["last_acked_event_id"] = event["event_id"]
    state["next_sequence"] = event["sequence"] + 1
    state["pending_reveal"] = None
    _atomic_write(state_path, state)
    _emit({"status": "acked", **receipt, "next_sequence": state["next_sequence"]})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Blind sequential release operator for C14 Resident fixture v2.")
    sub = parser.add_subparsers(dest="command", required=True)
    init_p = sub.add_parser("init")
    init_p.add_argument("--phase", choices=("A", "B"), required=True)
    init_p.add_argument("--state", required=True)
    init_p.set_defaults(func=cmd_init)
    reveal_p = sub.add_parser("reveal")
    reveal_p.add_argument("--phase", choices=("A", "B"), required=True)
    reveal_p.add_argument("--state", required=True)
    reveal_p.set_defaults(func=cmd_reveal)
    ack_p = sub.add_parser("ack")
    ack_p.add_argument("--phase", choices=("A", "B"), required=True)
    ack_p.add_argument("--state", required=True)
    ack_p.add_argument("--sequence", type=int, required=True)
    ack_p.add_argument("--event-id", required=True)
    ack_p.add_argument("--ingest-ref", required=True)
    ack_p.set_defaults(func=cmd_ack)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except ReleaseError as exc:
        sys.stderr.write(f"release-operator-error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
