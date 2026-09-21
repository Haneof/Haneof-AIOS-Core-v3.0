#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RELEASE_DIR = Path(__file__).resolve().parent
V2_ROOT = RELEASE_DIR.parent
def _bootstrap_repo_src() -> None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "src"
        if (candidate / "aios_core").is_dir():
            sys.path.insert(0, str(candidate))
            return


_bootstrap_repo_src()

from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError

OPERATOR_VERSION = "c14-blind-release-operator-v3"
STATE_VERSION = "c14-release-state-v3"
FIXTURE_VERSION = "c14-resident-fixture-v2"
FIXTURE_SHA256 = "sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253"
SCHEMA_VERSION = "c14-resident-event-v2"
CONTRACT_VERSION = "c14-sequential-release-v2"
INGEST_ADAPTER_VERSION = "c14-mechanical-ingest-adapter-v1"
BINDING_VERSION = "c14-fixture-event-binding-v1"
PHASE_A_MAX = 24
PHASE_B_START = 25
ROOT = V2_ROOT
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
INGEST_REF_RE = re.compile(
    r"^(?P<object_id>[A-Za-z0-9_.:/-]+)@(?P<revision>[1-9][0-9]*)$"
)


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


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _projection_sha256(event: dict[str, Any]) -> str:
    projection = {key: event[key] for key in VISIBLE_KEYS}
    return _sha256_text(_canonical_json(projection))


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ReleaseError(f"invalid occurred_at: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReleaseError("occurred_at missing timezone")
    return parsed


def _same_instant(left: str, right: str) -> bool:
    try:
        return _parse_time(left).astimezone(timezone.utc) == _parse_time(right).astimezone(timezone.utc)
    except ReleaseError:
        return False


def _load_bundle() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    fixture = _read_json(FIXTURE_PATH)
    manifest = _read_json(MANIFEST_PATH)
    digest = _sha256_file(FIXTURE_PATH)
    if digest != FIXTURE_SHA256 or manifest.get("fixture_sha256") != FIXTURE_SHA256:
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
    if manifest.get("ingest_adapter_version") != INGEST_ADAPTER_VERSION:
        raise ReleaseError("ingest adapter version mismatch")
    if manifest.get("fixture_binding_version") != BINDING_VERSION:
        raise ReleaseError("fixture binding version mismatch")
    if manifest.get("subject_id") != fixture.get("subject_id"):
        raise ReleaseError("fixture subject mismatch")
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
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temp, path)


def _parse_ingest_ref(value: str) -> tuple[str, int]:
    match = INGEST_REF_RE.fullmatch(value)
    if match is None:
        raise ReleaseError(
            "ack requires durable ingest reference in object_id@revision form"
        )
    return match.group("object_id"), int(match.group("revision"))


def _validate_receipt_shape(
    receipt: dict[str, Any],
    *,
    event: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    object_id, revision = _parse_ingest_ref(str(receipt.get("ingest_ref", "")))
    if receipt.get("sequence") != event["sequence"]:
        raise ReleaseError("release receipt sequence mismatch")
    if receipt.get("event_id") != event["event_id"]:
        raise ReleaseError("release receipt event mismatch")
    if receipt.get("occurred_at") != event["occurred_at"]:
        raise ReleaseError("release receipt time mismatch")
    if receipt.get("fixture_sha256") != manifest.get("fixture_sha256"):
        raise ReleaseError("release receipt digest mismatch")
    if receipt.get("ingest_object_id") != object_id:
        raise ReleaseError("release receipt object id mismatch")
    if receipt.get("ingest_revision") != revision:
        raise ReleaseError("release receipt revision mismatch")
    if not isinstance(receipt.get("ingest_world_revision"), int) or receipt["ingest_world_revision"] < 1:
        raise ReleaseError("release receipt world revision invalid")
    if receipt.get("fixture_payload_sha256") != _sha256_text(event["resident_visible_payload"]):
        raise ReleaseError("release receipt payload digest mismatch")
    if receipt.get("fixture_projection_sha256") != _projection_sha256(event):
        raise ReleaseError("release receipt projection digest mismatch")


def _load_state(
    path: Path,
    manifest: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    state = _read_json(path)
    if state.get("state_version") != STATE_VERSION:
        raise ReleaseError("state version mismatch")
    if state.get("fixture_version") != FIXTURE_VERSION:
        raise ReleaseError("state fixture version mismatch")
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ReleaseError("state schema version mismatch")
    if state.get("release_contract_version") != CONTRACT_VERSION:
        raise ReleaseError("state contract version mismatch")
    if state.get("release_operator_version") != OPERATOR_VERSION:
        raise ReleaseError("state operator version mismatch")
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
        if not isinstance(receipt, dict):
            raise ReleaseError("invalid release receipt")
        _validate_receipt_shape(
            receipt,
            event=events[expected - 1],
            manifest=manifest,
        )
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
    sys.stdout.write(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )


def _projection(event: dict[str, Any]) -> dict[str, Any]:
    return {key: event[key] for key in VISIBLE_KEYS}


def _phase_guard(
    phase_arg: str,
    state: dict[str, Any],
    events: list[dict[str, Any]],
) -> int:
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


def _verify_durable_world_binding(
    *,
    world_db: str,
    ingest_ref: str,
    event: dict[str, Any],
    fixture: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    world_path = Path(world_db)
    if not world_path.is_file():
        raise ReleaseError("private World database does not exist")
    object_id, revision = _parse_ingest_ref(ingest_ref)
    try:
        store = SQLiteWorldStore(world_path)
        record = store.object_revision_record(object_id, revision=revision)
        payload = store.get_payload(object_id, revision=revision)
    except StoreError as exc:
        raise ReleaseError("exact durable ingest revision is missing or unreadable") from exc

    expected_subject = str(fixture.get("subject_id") or "")
    expected_source_class = str(event["source_class"]).lower()
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise ReleaseError("durable Observation metadata missing")

    if record.get("object_type") != "observation" or payload.get("object_type") != "observation":
        raise ReleaseError("durable ingest ref is not an Observation")
    if record.get("revision_kind") != "content":
        raise ReleaseError("durable ingest ref is not a content revision")
    if record.get("subject_id") != expected_subject or payload.get("subject_id") != expected_subject:
        raise ReleaseError("durable ingest subject mismatch")
    if record.get("source_class") != expected_source_class:
        raise ReleaseError("durable ingest source_class mismatch")
    if payload.get("object_id") != object_id or int(payload.get("revision", 0)) != revision:
        raise ReleaseError("durable payload exact revision mismatch")
    if payload.get("source_kind") != event["source_kind"]:
        raise ReleaseError("durable ingest source_kind mismatch")
    if payload.get("modality") != event["modality"]:
        raise ReleaseError("durable ingest modality mismatch")
    if payload.get("value") != event["resident_visible_payload"]:
        raise ReleaseError("durable ingest payload mismatch")

    occurred = payload.get("occurred")
    if not isinstance(occurred, dict):
        raise ReleaseError("durable ingest occurred time missing")
    start = occurred.get("start")
    end = occurred.get("end")
    if not isinstance(start, str) or not isinstance(end, str):
        raise ReleaseError("durable ingest point time missing")
    if not _same_instant(start, event["occurred_at"]) or not _same_instant(end, event["occurred_at"]):
        raise ReleaseError("durable ingest timestamp mismatch")

    payload_sha256 = _sha256_text(event["resident_visible_payload"])
    projection_sha256 = _projection_sha256(event)
    expected_metadata = {
        "dimension": event["dimension"],
        "fixture_version": FIXTURE_VERSION,
        "fixture_sha256": manifest["fixture_sha256"],
        "fixture_binding_version": BINDING_VERSION,
        "fixture_event_id": event["event_id"],
        "fixture_sequence": event["sequence"],
        "fixture_payload_sha256": payload_sha256,
        "fixture_projection_sha256": projection_sha256,
        "external_record_id": event["event_id"],
        "external_revision": "1",
        "occurred_at_original": event["occurred_at"],
        "mechanical_ingest": True,
    }
    for key, expected in expected_metadata.items():
        if metadata.get(key) != expected:
            raise ReleaseError(f"durable ingest binding mismatch: {key}")

    return {
        "ingest_ref": ingest_ref,
        "ingest_object_id": object_id,
        "ingest_revision": revision,
        "ingest_world_revision": int(record["world_revision"]),
        "ingest_source_class": str(record["source_class"]),
        "fixture_payload_sha256": payload_sha256,
        "fixture_projection_sha256": projection_sha256,
    }


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
            "release_operator_version": OPERATOR_VERSION,
            "fixture_sha256": manifest["fixture_sha256"],
            "active_phase": "A",
            "last_acked_sequence": 0,
            "last_acked_event_id": None,
            "next_sequence": 1,
            "pending_reveal": None,
            "receipts": [],
        }
        _atomic_write(state_path, state)
        _emit(
            {
                "status": "initialized",
                "phase": "A",
                "next_sequence": 1,
                "fixture_sha256": manifest["fixture_sha256"],
            }
        )
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
    _emit(
        {
            "status": "initialized",
            "phase": "B",
            "next_sequence": PHASE_B_START,
            "fixture_sha256": manifest["fixture_sha256"],
        }
    )


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
    elif pending.get("sequence") != event["sequence"] or pending.get("event_id") != event["event_id"]:
        raise ReleaseError("pending reveal does not match current cursor")
    _emit(_projection(event))


def cmd_ack(args: argparse.Namespace) -> None:
    fixture, manifest, events = _load_bundle()
    state_path = Path(args.state)
    if not state_path.exists():
        raise ReleaseError("release state does not exist")
    state = _load_state(state_path, manifest, events)
    nxt = _phase_guard(args.phase, state, events)
    pending = state.get("pending_reveal")
    if pending is None:
        raise ReleaseError("no pending reveal to acknowledge")
    if args.sequence != nxt or args.sequence != pending.get("sequence"):
        raise ReleaseError("ack sequence is not the current revealed event")
    if args.event_id != pending.get("event_id"):
        raise ReleaseError("ack event id is not the current revealed event")

    event = events[nxt - 1]
    durable = _verify_durable_world_binding(
        world_db=args.world_db,
        ingest_ref=args.ingest_ref,
        event=event,
        fixture=fixture,
        manifest=manifest,
    )
    receipt = {
        "fixture_sha256": manifest["fixture_sha256"],
        "sequence": event["sequence"],
        "event_id": event["event_id"],
        "occurred_at": event["occurred_at"],
        **durable,
    }
    state["receipts"].append(receipt)
    state["last_acked_sequence"] = event["sequence"]
    state["last_acked_event_id"] = event["event_id"]
    state["next_sequence"] = event["sequence"] + 1
    state["pending_reveal"] = None
    _atomic_write(state_path, state)
    _emit({"status": "acked", **receipt, "next_sequence": state["next_sequence"]})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Blind sequential release operator for C14 Resident fixture v2."
    )
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
    ack_p.add_argument("--world-db", required=True)
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
    except (ReleaseError, ValueError, TypeError) as exc:
        sys.stderr.write(f"release-operator-error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
