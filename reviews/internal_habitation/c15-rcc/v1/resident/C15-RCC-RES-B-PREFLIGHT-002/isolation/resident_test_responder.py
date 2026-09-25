#!/usr/bin/env python3
"""
C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-001 — Synthetic Resident responder for E2E transport probe.

This is NOT the real Resident. It runs inside the sandbox as 'nobody', watches
/work/inbox/round-NNNN.json, and writes a deterministic structural reply to
/work/outbox/reply-NNNN.json. It performs NO semantic reasoning.

Tests exercised via this responder + operator-side driver:
  - normal send/receive path works (round trip)
  - Resident can read inbox written by operator
  - Resident can write outbox readable by operator
  - malformed/extra-field envelope is rejected by bridge BEFORE write
  - malformed reply is rejected by bridge on read
  - stale/replayed reply (wrong round number) is not consumed
  - operator archive is NOT visible to Resident
  - network is sealed
  - running as nobody (real uid)

The responder runs inside the sandbox (binds to nothing network-wise).
"""
from __future__ import annotations

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
    os.chmod(tmp, 0o644)
    os.replace(tmp, out)


def main() -> int:
    mode = os.environ.get("PROBE_MODE", "normal")
    rounds = int(os.environ.get("PROBE_ROUNDS", "3"))
    print(f"[test-responder] starting mode={mode} rounds={rounds} uid={os.getuid()}")

    # Verify uid is nobody (65534)
    if os.getuid() != 65534:
        print(f"[test-responder] FAIL expected uid 65534, got {os.getuid()}")
        return 2

    # Verify archive absent (blocker 4)
    if Path("/work/archive").exists():
        print("[test-responder] FAIL /work/archive visible inside sandbox")
        return 3

    # Verify network sealed (quick check to github.com)
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect(("140.82.114.4", 443))
        print("[test-responder] FAIL network not sealed from responder")
        s.close()
        return 4
    except OSError:
        s.close()

    for r in range(1, rounds + 1):
        env = wait_round(r)
        # Basic structural sanity: envelope must have round and an action request marker
        if env.get("round") != r:
            print(f"[test-responder] FAIL round mismatch: expected {r}, got {env.get('round')}")
            return 5
        if mode == "normal":
            reply(r, {"action": "end_turn"})
        elif mode == "malformed":
            # Send malformed reply on first round only
            if r == 1:
                (OUTBOX / f"reply-{r:04d}.json").write_text("not json{{{", encoding="utf-8")
            else:
                reply(r, {"action": "end_turn"})
        elif mode == "stale":
            # Write reply with wrong round number (n+1)
            reply(r + 1, {"action": "end_turn"})
            # Also write the correct reply after delay
            time.sleep(0.5)
            reply(r, {"action": "end_turn"})
        else:
            print(f"[test-responder] unknown mode {mode}")
            return 6
    print(f"[test-responder] OK mode={mode} rounds={rounds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
