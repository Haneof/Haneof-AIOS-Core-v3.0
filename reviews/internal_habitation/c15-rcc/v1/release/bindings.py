#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

RELEASE_DIR = Path(__file__).resolve().parent
C15_ROOT = RELEASE_DIR.parent
FIXTURE_VERSION = "c15-rcc-fixture-v1"
FIXTURE_SHA256 = "sha256:7ccb309d207cb6ee240fbc008ee4f535e25571f04ba7ca1b7c95bf9afb5ebf46"
SCHEMA_VERSION = "c15-rcc-event-v1"
CONTRACT_VERSION = "c15-rcc-sequential-release-v1"
OPERATOR_VERSION = "c15-rcc-three-phase-release-v1"
STATE_VERSION = "c15-rcc-release-state-v1"
INGEST_ADAPTER_VERSION = "c15-rcc-mechanical-ingest-adapter-v1"
BINDING_VERSION = "c15-rcc-fixture-event-binding-v1"
CANONICAL_ADAPTER_VERSION = "c15-rcc-canonical-conversation-adapter-v1"
CANONICAL_BINDING_VERSION = "c15-rcc-canonical-conversation-binding-v1"
SUBJECT_ID = "user_1"
PHASE_RANGES = {"A": (1, 13), "B": (14, 22), "C": (23, 30)}
PHASE_COUNTS = {"A": 13, "B": 9, "C": 8}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (
            (parent / "src" / "aios_core").is_dir()
            and (parent / "reviews" / "internal_habitation" / "c14-resident" / "v2" / "release").is_dir()
        ):
            return parent
    raise RuntimeError("repository root not found")


REPO_ROOT = _repo_root()
V2_RELEASE = REPO_ROOT / "reviews" / "internal_habitation" / "c14-resident" / "v2" / "release"


def _load_module(name: str, filename: str) -> ModuleType:
    path = V2_RELEASE / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen v2 release module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_release_operator() -> ModuleType:
    module = _load_module("_c15_rcc_v2_release_operator", "release_operator.py")
    module.OPERATOR_VERSION = OPERATOR_VERSION
    module.LEGACY_HANDOFF_OPERATOR_VERSION = "__c15_no_legacy_handoff__"
    module.STATE_VERSION = STATE_VERSION
    module.FIXTURE_VERSION = FIXTURE_VERSION
    module.FIXTURE_SHA256 = FIXTURE_SHA256
    module.SCHEMA_VERSION = SCHEMA_VERSION
    module.CONTRACT_VERSION = CONTRACT_VERSION
    module.INGEST_ADAPTER_VERSION = INGEST_ADAPTER_VERSION
    module.BINDING_VERSION = BINDING_VERSION
    module.CANONICAL_CONVERSATION_ADAPTER_VERSION = CANONICAL_ADAPTER_VERSION
    module.CANONICAL_CONVERSATION_BINDING_VERSION = CANONICAL_BINDING_VERSION
    module.ROOT = C15_ROOT
    module.FIXTURE_PATH = C15_ROOT / "fixture" / "sealed_fixture.json"
    module.MANIFEST_PATH = C15_ROOT / "fixture" / "fixture_manifest.json"

    def load_bundle():
        fixture = module._read_json(module.FIXTURE_PATH)
        manifest = module._read_json(module.MANIFEST_PATH)
        digest = module._sha256_file(module.FIXTURE_PATH)
        if digest != FIXTURE_SHA256 or manifest.get("fixture_sha256") != FIXTURE_SHA256:
            raise module.ReleaseError("fixture digest mismatch")
        for key, expected in (
            ("fixture_version", FIXTURE_VERSION),
            ("schema_version", SCHEMA_VERSION),
            ("release_contract_version", CONTRACT_VERSION),
        ):
            if fixture.get(key) != expected or manifest.get(key) != expected:
                raise module.ReleaseError(f"{key} mismatch")
        expected_manifest = {
            "release_operator_version": OPERATOR_VERSION,
            "ingest_adapter_version": INGEST_ADAPTER_VERSION,
            "fixture_binding_version": BINDING_VERSION,
            "canonical_conversation_adapter_version": CANONICAL_ADAPTER_VERSION,
            "canonical_conversation_binding_version": CANONICAL_BINDING_VERSION,
            "subject_id": fixture.get("subject_id"),
            "event_count": 30,
            "phase_a_count": PHASE_COUNTS["A"],
            "phase_b_count": PHASE_COUNTS["B"],
            "phase_c_count": PHASE_COUNTS["C"],
        }
        for key, expected in expected_manifest.items():
            if manifest.get(key) != expected:
                raise module.ReleaseError(f"manifest {key} mismatch")
        events = fixture.get("events")
        if not isinstance(events, list) or len(events) != 30:
            raise module.ReleaseError("fixture events missing or wrong count")
        ids = [event.get("event_id") for event in events]
        if len(ids) != len(set(ids)):
            raise module.ReleaseError("duplicate event id")
        previous = None
        for index, event in enumerate(events, start=1):
            if event.get("sequence") != index:
                raise module.ReleaseError("non-contiguous event sequence")
            phase = event.get("phase")
            if phase not in PHASE_RANGES:
                raise module.ReleaseError("invalid phase")
            lo, hi = PHASE_RANGES[phase]
            if index < lo or index > hi:
                raise module.ReleaseError("non-contiguous phase layout")
            current = module._parse_time(str(event.get("occurred_at")))
            if previous is not None and current <= previous:
                raise module.ReleaseError("event time is not strictly increasing")
            previous = current
        handoffs = manifest.get("handoffs") or {}
        a_to_b = handoffs.get("a_to_b") or {}
        b_to_c = handoffs.get("b_to_c") or {}
        if (a_to_b.get("phase_a_final_cursor"), a_to_b.get("phase_b_first_cursor")) != (13, 14):
            raise module.ReleaseError("A/B handoff mismatch")
        if (b_to_c.get("phase_b_final_cursor"), b_to_c.get("phase_c_first_cursor")) != (22, 23):
            raise module.ReleaseError("B/C handoff mismatch")
        return fixture, manifest, events

    def load_state(path, manifest, events, *, allow_legacy_handoff=False):
        state = module._read_json(path)
        expected = {
            "state_version": STATE_VERSION,
            "fixture_version": FIXTURE_VERSION,
            "schema_version": SCHEMA_VERSION,
            "release_contract_version": CONTRACT_VERSION,
            "release_operator_version": OPERATOR_VERSION,
            "fixture_sha256": manifest.get("fixture_sha256"),
        }
        for key, value in expected.items():
            if state.get(key) != value:
                raise module.ReleaseError(f"state {key} mismatch")
        phase = state.get("active_phase")
        if phase not in PHASE_RANGES:
            raise module.ReleaseError("invalid active phase")
        last = state.get("last_acked_sequence")
        nxt = state.get("next_sequence")
        if not isinstance(last, int) or not isinstance(nxt, int) or nxt != last + 1:
            raise module.ReleaseError("invalid cursor state")
        receipts = state.get("receipts")
        if not isinstance(receipts, list) or len(receipts) != last:
            raise module.ReleaseError("release receipt chain mismatch")
        for expected_sequence, receipt in enumerate(receipts, start=1):
            if not isinstance(receipt, dict):
                raise module.ReleaseError("invalid release receipt")
            module._validate_receipt_shape(
                receipt,
                event=events[expected_sequence - 1],
                manifest=manifest,
            )
        if last == 0:
            if state.get("last_acked_event_id") is not None:
                raise module.ReleaseError("invalid initial last event")
        else:
            if last > len(events) or state.get("last_acked_event_id") != events[last - 1]["event_id"]:
                raise module.ReleaseError("last acked event mismatch")
        pending = state.get("pending_reveal")
        if pending is not None:
            if not isinstance(pending, dict):
                raise module.ReleaseError("invalid pending reveal")
            if pending.get("sequence") != nxt:
                raise module.ReleaseError("pending reveal cursor mismatch")
            if nxt > len(events) or pending.get("event_id") != events[nxt - 1]["event_id"]:
                raise module.ReleaseError("pending reveal event mismatch")
        lo, hi = PHASE_RANGES[phase]
        if nxt < lo or nxt > hi + 1:
            raise module.ReleaseError("cursor outside active sealed phase")
        return state

    def phase_guard(phase_arg, state, events):
        if phase_arg != state["active_phase"]:
            raise module.ReleaseError("requested phase does not match active state")
        nxt = state["next_sequence"]
        if nxt > len(events):
            raise module.ReleaseError("fixture release already complete")
        lo, hi = PHASE_RANGES[phase_arg]
        if nxt < lo or nxt > hi:
            raise module.ReleaseError(f"Phase {phase_arg} sealed boundary reached")
        if events[nxt - 1]["phase"] != phase_arg:
            raise module.ReleaseError("phase event boundary mismatch")
        return nxt

    def is_canonical_user_event(state, event):
        return (
            event.get("phase") == state.get("active_phase")
            and event.get("dimension") == "dim:conversation"
            and event.get("source_kind") == "conversation"
            and event.get("source_class") == "USER"
            and event.get("modality") == "text"
        )

    def cmd_init(args):
        _, manifest, events = load_bundle()
        state_path = Path(args.state)
        phase = args.phase
        if phase == "A":
            if state_path.exists():
                raise module.ReleaseError("state already exists")
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
            module._atomic_write(state_path, state)
            module._emit({"status": "initialized", "phase": "A", "next_sequence": 1, "fixture_sha256": manifest["fixture_sha256"]})
            return
        if not state_path.exists():
            raise module.ReleaseError(f"Phase {phase} requires existing handoff state")
        state = load_state(state_path, manifest, events)
        previous = "A" if phase == "B" else "B"
        prev_lo, prev_hi = PHASE_RANGES[previous]
        cur_lo, _ = PHASE_RANGES[phase]
        if state["active_phase"] != previous:
            raise module.ReleaseError(f"Phase {phase} initialization requires active Phase {previous} handoff state")
        if state["pending_reveal"] is not None:
            raise module.ReleaseError("cannot cross phase boundary with unacknowledged reveal")
        if state["last_acked_sequence"] != prev_hi or state["next_sequence"] != cur_lo:
            raise module.ReleaseError(f"Phase {phase} must start exactly at cursor {cur_lo} after ack {prev_hi}")
        state["active_phase"] = phase
        state["release_operator_version"] = OPERATOR_VERSION
        module._atomic_write(state_path, state)
        module._emit({"status": "initialized", "phase": phase, "next_sequence": cur_lo, "fixture_sha256": manifest["fixture_sha256"]})

    def cmd_reveal(args):
        _, manifest, events = load_bundle()
        state_path = Path(args.state)
        if not state_path.exists():
            raise module.ReleaseError("release state does not exist")
        state = load_state(state_path, manifest, events)
        nxt = phase_guard(args.phase, state, events)
        if state.get("pending_reveal") is not None:
            raise module.ReleaseError("duplicate reveal before durable ack is forbidden")
        event = events[nxt - 1]
        state["pending_reveal"] = {
            "sequence": event["sequence"],
            "event_id": event["event_id"],
            "occurred_at": event["occurred_at"],
            "fixture_sha256": manifest["fixture_sha256"],
        }
        module._atomic_write(state_path, state)
        module._emit(module._projection(event))

    def build_parser():
        parser = argparse.ArgumentParser(description="Blind three-phase sequential release operator for C15 RCC fixture.")
        sub = parser.add_subparsers(dest="command", required=True)
        init_p = sub.add_parser("init")
        init_p.add_argument("--phase", choices=("A", "B", "C"), required=True)
        init_p.add_argument("--state", required=True)
        init_p.set_defaults(func=cmd_init)
        reveal_p = sub.add_parser("reveal")
        reveal_p.add_argument("--phase", choices=("A", "B", "C"), required=True)
        reveal_p.add_argument("--state", required=True)
        reveal_p.set_defaults(func=cmd_reveal)
        ack_p = sub.add_parser("ack")
        ack_p.add_argument("--phase", choices=("A", "B", "C"), required=True)
        ack_p.add_argument("--state", required=True)
        ack_p.add_argument("--world-db", required=True)
        ack_p.add_argument("--sequence", type=int, required=True)
        ack_p.add_argument("--event-id", required=True)
        ack_p.add_argument("--ingest-ref", required=True)
        ack_p.add_argument("--conversation-session-id")
        ack_p.add_argument("--conversation-turn-index", type=int)
        ack_p.set_defaults(func=module.cmd_ack)
        return parser

    module._load_bundle = load_bundle
    module._load_state = load_state
    module._phase_guard = phase_guard
    module._is_phase_b_canonical_conversation_event = is_canonical_user_event
    module.cmd_init = cmd_init
    module.cmd_reveal = cmd_reveal
    module.build_parser = build_parser
    return module


def load_mechanical_adapter() -> ModuleType:
    module = _load_module("_c15_rcc_v2_mechanical_adapter", "mechanical_ingest_adapter.py")
    module.FIXTURE_VERSION = FIXTURE_VERSION
    module.FIXTURE_SHA256 = FIXTURE_SHA256
    module.INGEST_ADAPTER_VERSION = INGEST_ADAPTER_VERSION
    module.BINDING_VERSION = BINDING_VERSION
    module.SUBJECT_ID = SUBJECT_ID
    module.V2_ROOT = C15_ROOT
    module.MANIFEST_PATH = C15_ROOT / "fixture" / "fixture_manifest.json"
    original_validate = module._validate_projection

    def validate_projection(raw):
        event = original_validate(raw)
        if (
            event.get("dimension") == "dim:conversation"
            and event.get("source_kind") == "conversation"
            and event.get("source_class") == "USER"
            and event.get("modality") == "text"
        ):
            raise module.IngestAdapterError(
                "C15 USER conversation must use canonical_conversation_ingest.py"
            )
        return event

    module._validate_projection = validate_projection
    return module


def load_canonical_adapter() -> ModuleType:
    module = _load_module("_c15_rcc_v2_canonical_adapter", "canonical_conversation_ingest.py")
    module.FIXTURE_VERSION = FIXTURE_VERSION
    module.FIXTURE_SHA256 = FIXTURE_SHA256
    module.ADAPTER_VERSION = CANONICAL_ADAPTER_VERSION
    module.BINDING_VERSION = CANONICAL_BINDING_VERSION
    module.V2_ROOT = C15_ROOT
    module.MANIFEST_PATH = C15_ROOT / "fixture" / "fixture_manifest.json"
    return module
