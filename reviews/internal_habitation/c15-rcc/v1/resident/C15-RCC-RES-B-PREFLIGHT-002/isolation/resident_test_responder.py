#!/usr/bin/env python3
"""
C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-002 — Synthetic Resident responder (binding-aware).

Runs inside sandbox as nobody. Watches /work/inbox/round-NNNN.json and writes
deterministic reply to /work/outbox/reply-NNNN.json with exact binding fields
(round/request_id/request_digest) echoed from the request.

Supports modes:
  normal    - correct binding, action end_turn
  malformed - first round writes malformed JSON (no binding)
  stale     - first round writes reply with previous round's binding (stale)
  genuine   - two-round: round1 invoke search_world, round2 silence (for Core path)
  binding   - alias for normal (used for binding E2E)

No semantic reasoning.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

INBOX = Path("/work/inbox")
OUTBOX = Path("/work/outbox")


def wait_round(n: int, timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    p = INBOX / f"round-{n:04d}.json"
    while time.monotonic() < deadline:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                time.sleep(0.1)
                continue
        time.sleep(0.1)
    raise TimeoutError(f"timed out waiting for round {n}")


def reply(n: int, payload: dict) -> None:
    out = OUTBOX / f"reply-{n:04d}.json"
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(tmp, 0o644)
    except Exception:
        pass
    os.replace(tmp, out)


def main() -> int:
    global INBOX, OUTBOX
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default=os.environ.get("PROBE_MODE", "normal"))
    ap.add_argument("--rounds", type=int, default=int(os.environ.get("PROBE_ROUNDS", "3")))
    ap.add_argument("--inbox", type=Path, default=Path("/work/inbox"))
    ap.add_argument("--outbox", type=Path, default=Path("/work/outbox"))
    args = ap.parse_args()

    mode = args.mode
    rounds = args.rounds
    inbox = args.inbox
    outbox = args.outbox

    INBOX = inbox
    OUTBOX = outbox

    print(f"[test-responder] starting mode={mode} rounds={rounds} uid={os.getuid()} pid={os.getpid()} inbox={INBOX} outbox={OUTBOX}")

    if os.getuid() != 65534:
        print(f"[test-responder] FAIL expected uid 65534, got {os.getuid()}")
        return 2
    if Path("/work/archive").exists():
        print("[test-responder] FAIL /work/archive visible inside sandbox")
        return 3
    # Verify PID != 1 (init is PID 1)
    pid = os.getpid()
    try:
        ppid_comm = Path("/proc/1/comm").read_text().strip()
        print(f"[test-responder] pid={pid} proc1_comm={ppid_comm}")
        if pid == 1:
            print("[test-responder] FAIL responder is PID 1, must be >=2 (PID1 is supervisor)")
            return 10
        if ppid_comm not in ("sandbox-init", "sandbox_init", "python3", "python"):
            # Allow python3 as fallback but we expect sandbox-init
            print(f"[test-responder] WARN proc1_comm={ppid_comm!r} not sandbox-init but continuing")
            # Not fail if init comm is python3 due to fallback? But we require sandbox-init
            if ppid_comm == "sh":
                print("[test-responder] FAIL pid1 comm is sh (means resident is pid1)")
                return 11
        if ppid_comm == "sandbox-init":
            print("[test-responder] PASS PID1 is sandbox-init")
    except Exception as e:
        print(f"[test-responder] proc1 check error: {e}")
        return 12

    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect(("140.82.114.4", 443))
        print("[test-responder] FAIL network not sealed")
        s.close()
        return 4
    except OSError:
        s.close()

    # Cache first envelope for stale test
    first_env = None

    for r in range(1, rounds + 1):
        try:
            env = wait_round(r)
        except TimeoutError as e:
            print(f"[test-responder] timeout waiting round {r}: {e}")
            return 5
        if env.get("round") != r:
            print(f"[test-responder] FAIL round mismatch: expected {r}, got {env.get('round')}")
            return 5
        # Validate envelope has binding
        if "request_id" not in env or "request_digest" not in env:
            print(f"[test-responder] FAIL envelope missing binding fields: {env.keys()}")
            return 5

        if first_env is None:
            first_env = dict(env)

        print(f"[test-responder] round {r} received request_id={env['request_id'][:8]}... digest={env['request_digest'][:8]}...")

        if mode == "normal" or mode == "binding":
            payload = {"round": r, "request_id": env["request_id"], "request_digest": env["request_digest"], "action": "end_turn"}
            reply(r, payload)
        elif mode == "malformed":
            if r == 1:
                # Write invalid JSON
                out = OUTBOX / f"reply-{r:04d}.json"
                out.write_text("not json{{{", encoding="utf-8")
            else:
                payload = {"round": r, "request_id": env["request_id"], "request_digest": env["request_digest"], "action": "end_turn"}
                reply(r, payload)
        elif mode == "stale":
            # Write reply with previous round's binding but file name is current round
            # For r=1, stale means use wrong round number 0
            if r == 1:
                payload = {"round": 99, "request_id": "a"*32, "request_digest": "b"*64, "action": "end_turn"}
                reply(r, payload)
            else:
                # For r>=2, use first round's binding
                payload = {"round": first_env["round"], "request_id": first_env["request_id"], "request_digest": first_env["request_digest"], "action": "end_turn"}
                reply(r, payload)
        elif mode == "genuine":
            # Two-round genuine simulation: first round capability (Atlas), second silence.
            # Atlas query returns 2 non-empty legal results including obs_c14_fixture_* which is
            # explicitly LEGAL durable World data (BLOCKER 2 fix: path-aware guard, bare fixture allowed).
            # The second envelope's capability_history will contain those ids and must NOT be rejected.
            if r == 1:
                payload = {
                    "round": r,
                    "request_id": env["request_id"],
                    "request_digest": env["request_digest"],
                    "action": "invoke_capability",
                    "capability": "search_world",
                    "arguments": {"query": "Atlas", "limit": 2}
                }
                reply(r, payload)
                print(f"[test-responder] genuine round1 invoke search_world Atlas limit2 (non-empty legal)")
            else:
                payload = {"round": r, "request_id": env["request_id"], "request_digest": env["request_digest"], "action": "silence"}
                reply(r, payload)
                print(f"[test-responder] genuine round{r} silence")
        else:
            print(f"[test-responder] unknown mode {mode}")
            return 6
        # Small delay to avoid race
        time.sleep(0.1)

    print(f"[test-responder] OK mode={mode} rounds={rounds} pid={os.getpid()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
