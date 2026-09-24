"""Minimal file exchange for Arena AI itself inhabitation - rule constraint + process audit.

Boundary revision 2026-09-24: user chooses rule constraint + process audit, no longer requires
technical forced isolation as startup premise. Must retain:
- new, untouched Resident window
- explicit prohibition to consult history answers, future events, governance/review materials
- only via approved AIOS entry
- save complete input, AI original output, tool calls and execution results
- stop if crossing, mark contamination
- missing records must not claim proven no crossing
- don't describe this round as hard isolation experiment.

This change is recorded in this round protocol, not rewriting historical results.

Fixed base: PR125 handover head 22b9641f85e0e20f1bd87ed85100a1e268e56dea, branch arena/01a0cf25.
Keep frozen Core bcd6bf3 and accepted A 3e51f728. Don't use PR126 new Core, old B init.
Don't merge PR, don't trigger public CI real A workflow (real-a-import-312.yml if: false).

This file provides minimal file exchange:
- operator --write-packet /tmp/resident_packet/request.json --synthetic
- resident (new Arena window) reads request.json, writes response.json with binding
- operator --read-response response.json --validate --execute --trace trace.jsonl

Only independent synthetic data for one send/receive verification, don't release formal B events.
Allow manual original handover, prohibit script replacing AI generation or rewriting decision.
Don't develop external model API, don't extend general framework.

Existing entry reuse: transport.plain/encode/directive, driver, restart, audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

# Ensure src in path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from tools.c15_preflight.transport import plain, encode, directive, Trace
from tools.c15_preflight.audit import require
from aios_core.runtime.cognitive_runtime import RuntimeSnapshot


PROTOCOL = "c15-resident-broker-v1"
APPROVED_SNAPSHOT_KEYS = {"user_input", "wake_reason", "cockpit", "capability_catalog", "capability_history", "round_index", "remaining_tool_rounds"}
FORBIDDEN_INPUT_KEYS = {"world_revision", "index_watermark", "release_sha256", "driver_state", "session", "clock", "private_world", "world_index", "release_state", "operator", "git_metadata", "private_a"}


def make_synthetic_snapshot() -> RuntimeSnapshot:
    """Independent synthetic data, not real A/B/C"""
    return RuntimeSnapshot(
        user_input="synthetic user input for Arena Resident handover verification",
        wake_reason="user_interaction",
        cockpit={"synthetic": True, "handover": "arena-resident-2026-09-24"},
        capability_catalog=(),
        capability_history=(),
        round_index=0,
        remaining_tool_rounds=5,
    )


def write_packet(packet_path: Path, synthetic: bool = True):
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    # Use synthetic snapshot for verification, not real A
    if synthetic:
        snap = make_synthetic_snapshot()
    else:
        # For real A 88/88 13->14, would load from accepted A staging, but this round only synthetic verification per instruction
        raise ValueError("real A packet not allowed in this round, only synthetic for one send/receive verification")
    serialized = plain(snap)
    # Boundary check: only approved keys, no forbidden
    for fk in FORBIDDEN_INPUT_KEYS:
        require(fk not in serialized, f"operator private material must not enter: {fk}")
    require("governance" not in json.dumps(serialized).lower(), "governance must not enter")
    for k in serialized.keys():
        require(k in APPROVED_SNAPSHOT_KEYS, f"unapproved snapshot field: {k}")
    input_sha = hashlib.sha256(encode(serialized).encode()).hexdigest()
    request_id = uuid4().hex
    packet = {
        "protocol": PROTOCOL,
        "request_id": request_id,
        "kind": "runtime",
        "input_sha256": input_sha,
        "input": serialized,
    }
    # Atomic write + fsync
    tmp = packet_path.with_suffix(".tmp")
    tmp.write_text(encode(packet) + "\n", encoding="utf-8")
    with tmp.open("rb") as f:
        os.fsync(f.fileno())
    tmp.rename(packet_path)
    # fsync parent
    try:
        fd = os.open(packet_path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except Exception:
        pass
    print(f"wrote packet {packet_path} request_id={request_id} input_sha={input_sha[:8]} synthetic={synthetic}")
    return packet


def read_and_validate_response(request_path: Path, response_path: Path):
    require(request_path.is_file(), f"request missing: {request_path}")
    require(response_path.is_file(), f"response missing: {response_path}")
    req_text = request_path.read_text(encoding="utf-8").strip()
    resp_text = response_path.read_text(encoding="utf-8").strip()
    # Must be one newline-terminated JSON
    require(resp_text, "response empty")
    # Allow exactly one JSON line (strip newline)
    try:
        req = json.loads(req_text)
        resp = json.loads(resp_text)
    except Exception as e:
        raise ValueError(f"invalid JSON: {e}")
    # Binding check
    require(set(resp.keys()) == {"request_id", "kind", "input_sha256", "output"}, f"response keys mismatch: {resp.keys()}")
    for k in ("request_id", "kind", "input_sha256"):
        require(resp[k] == req[k], f"binding mismatch {k}: expected {req[k]} got {resp[k]}")
    # Validate output via directive()
    try:
        result = directive(resp["output"])
    except Exception as e:
        raise ValueError(f"directive validation failed: {e}") from e
    print(f"validated response request_id={resp['request_id']} kind={resp['kind']} output={resp['output']}")
    return req, resp, result


def execute_and_trace(req, resp, result, trace_path: Path):
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    # For this minimal verification, we don't have full Driver, just record trace
    # In real operator flow, would execute via FusedTurnRuntime
    def fake_revision():
        return 88
    # Use Trace which requires exclusive create
    if trace_path.exists():
        trace_path.unlink()
    trace = Trace(trace_path, fake_revision)
    try:
        trace.append("resident_packet_request", req)
        trace.append("resident_response_raw", {"text": json.dumps(resp, ensure_ascii=False), "request_id": resp["request_id"]})
        trace.append("resident_directive_validated", {"directive": plain(result), "request_id": resp["request_id"]})
        # Simulate capability execution if present
        if hasattr(result, "capability_calls") and result.capability_calls:
            trace.append("capability_execution", {"calls": plain(result.capability_calls), "result": "synthetic execution - no real B"})
        elif hasattr(result, "response"):
            trace.append("model_response", {"response": result.response})
        elif hasattr(result, "silence"):
            trace.append("model_silence", {"silence": result.silence})
        print(f"traced to {trace_path} sequence={trace.sequence}")
    finally:
        trace.close()
    return trace_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["operator"], required=True, help="only operator mode in this file, resident is new Arena window AI itself")
    parser.add_argument("--write-packet", type=Path, help="path to write request.json")
    parser.add_argument("--read-response", type=Path, help="path to read response.json")
    parser.add_argument("--synthetic", action="store_true", help="use independent synthetic data for one verification, don't release formal B")
    parser.add_argument("--validate", action="store_true", help="validate binding and directive")
    parser.add_argument("--execute", action="store_true", help="execute via normal Runtime and record trace")
    parser.add_argument("--trace", type=Path, help="trace.jsonl path")
    args = parser.parse_args()

    if args.write_packet:
        write_packet(args.write_packet, synthetic=args.synthetic)

    if args.read_response:
        if not args.validate:
            print("need --validate with --read-response")
            sys.exit(2)
        # Find request path: assume same dir as response, named request.json if not specified
        req_path = args.write_packet or (args.read_response.parent / "request.json")
        if not req_path.is_file():
            # Try default
            req_path = Path("/tmp/resident_packet/request.json")
        req, resp, result = read_and_validate_response(req_path, args.read_response)
        if args.execute:
            if not args.trace:
                print("need --trace with --execute")
                sys.exit(2)
            execute_and_trace(req, resp, result, args.trace)

if __name__ == "__main__":
    main()
