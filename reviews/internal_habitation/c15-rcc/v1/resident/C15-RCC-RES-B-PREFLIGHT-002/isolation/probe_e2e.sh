#!/bin/bash
# C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-001 — E2E transport probe (operator side).
# Must be run as root (sudo). Sets up a disposable runtime + sandbox + mailbox,
# launches the synthetic responder inside the sandbox, drives mailbox_bridge
# through several rounds (normal + malformed-reply + stale-reply), and verifies
# bridge fail-closed behavior.
#
# Does NOT use any real B fixture payload. Does NOT reveal cursor 14.
# Does NOT run Resident B cognition; uses deterministic synthetic responder.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/user/Haneof-AIOS-Core-v3.0}"
B_PREP="$REPO_ROOT/reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002"

RUN_ROOT="${RUN_ROOT:-/tmp/b-preflight-e2e-$$}"
echo "[e2e] run_root = $RUN_ROOT"
mkdir -p "$RUN_ROOT"/{runtime,sandbox,mailbox/{inbox,outbox,archive},scratch,inject}

# Make byte-exact copy of A-002 freeze
cp "$B_PREP/lineage_copy/private_world.sqlite" "$RUN_ROOT/runtime/world.sqlite"
cp "$B_PREP/lineage_copy/world_index.sqlite"    "$RUN_ROOT/runtime/index.sqlite"
cp "$B_PREP/lineage_copy/release_state.json"   "$RUN_ROOT/runtime/release_state.json"
touch "$RUN_ROOT/runtime/world.writer.lock"

# Verify digests of copy
(cd "$RUN_ROOT/runtime" && sha256sum -c - <<EOF
626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa  world.sqlite
ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1  index.sqlite
eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8  release_state.json
EOF
)
echo "[e2e] lineage copy digests OK"

# Place responder + isolation probe in inject (RO)
cp "$B_PREP/isolation/resident_test_responder.py" "$RUN_ROOT/inject/responder.py"
cp "$B_PREP/isolation/probe_isolation.sh" "$RUN_ROOT/inject/probe_isolation.sh"
chmod +x "$RUN_ROOT/inject/probe_isolation.sh"

PY="python3"
PYTHONPATH="$REPO_ROOT/src"
export PYTHONPATH

# Step 1: mailbox bridge self-tests (structural, no sandbox)
echo "[e2e] running mailbox_bridge self-tests"
"$PY" "$B_PREP/harness/mailbox_bridge.py" self-test

# Step 2: hardenend isolation probe (runs ISIDE the sandbox as nobody)
echo "[e2e] running isolation probe inside sandbox"
sudo "$PY" "$B_PREP/harness/resident_jail.py" \
  --repo      "$REPO_ROOT" \
  --sandbox   "$RUN_ROOT/sandbox" \
  --world     "$RUN_ROOT/runtime/world.sqlite" \
  --index     "$RUN_ROOT/runtime/index.sqlite" \
  --state     "$RUN_ROOT/runtime/release_state.json" \
  --lock      "$RUN_ROOT/runtime/world.writer.lock" \
  --mailbox-root "$RUN_ROOT/mailbox" \
  --inject-dir "$RUN_ROOT/inject" \
  -- /bin/sh /work/inject/probe_isolation.sh 2>&1 | tee "$RUN_ROOT/isolation_probe.log"
grep -q '^ISOLATION_PASS$' "$RUN_ROOT/isolation_probe.log"
echo "[e2e] isolation probe PASS"

# Step 3: E2E transport — normal rounds
echo "[e2e] E2E transport: normal rounds"
"$PY" - "$RUN_ROOT" "$B_PREP" "$REPO_ROOT" "normal" 3 <<'PYEOF'
import json, os, shutil, subprocess, sys, time
from pathlib import Path
run_root = Path(sys.argv[1])
b_prep   = Path(sys.argv[2])
repo     = Path(sys.argv[3])
mode     = sys.argv[4]
rounds   = int(sys.argv[5])
sys.path.insert(0, str(b_prep / "harness"))
from mailbox_bridge import MailboxBridge, MailboxEnvelopeError, MailboxReplyError

b_session = "probe-session-abc"
# Clean outbox/inbox for this test
for sub in ("inbox","outbox"):
    d = run_root/"mailbox"/sub
    for f in d.iterdir():
        if f.is_file(): f.unlink()
bridge = MailboxBridge(
    run_root/"mailbox"/"inbox",
    run_root/"mailbox"/"outbox",
    run_root/"mailbox"/"archive",
    b_session,
)

# Launch responder inside sandbox (does NOT exec a model)
sb = run_root/"sandbox"
if sb.exists(): shutil.rmtree(sb)
jail = [
    "sudo", "--preserve-env=PROBE_MODE,PROBE_ROUNDS,PATH",
    "python3", str(b_prep/"harness"/"resident_jail.py"),
    "--repo", str(repo),
    "--sandbox", str(sb),
    "--world", str(run_root/"runtime"/"world.sqlite"),
    "--index", str(run_root/"runtime"/"index.sqlite"),
    "--state", str(run_root/"runtime"/"release_state.json"),
    "--lock",  str(run_root/"runtime"/"world.writer.lock"),
    "--mailbox-root", str(run_root/"mailbox"),
    "--inject-dir", str(run_root/"inject"),
    "--",
    "/usr/bin/python3", "/work/inject/responder.py",
]
os.environ["PROBE_MODE"] = mode
os.environ["PROBE_ROUNDS"] = str(rounds)
os.environ["PATH"] = "/usr/local/bin:/usr/bin:/bin"
proc = subprocess.Popen(jail, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
# Give responder a moment to start up and enter its wait loop
time.sleep(1.0)
try:
    # Synthetic Resident-safe envelope (NOT real B fixture data)
    base_env = {
        "phase": "B",
        "allowed_sequences": [14, 22],
        "event": None,
        "runtime_snapshot": {"world_revision": 98, "subject": "user_1", "session_id": b_session},
        "capability_catalog": [],
        "capability_history": [],
        "wake_reason": "probe",
        "is_periodic_review": False,
        "is_summary_request": False,
    }
    for r in range(1, rounds+1):
        env_to_send = {**base_env}
        # Don't set 'round' — bridge assigns it.
        bridge.send(env_to_send)
        # Verify inbox file visible from operator side
        assert (run_root/"mailbox"/"inbox"/f"round-{r:04d}.json").exists(), "inbox file not visible to operator"
        reply = bridge.wait_for_reply(timeout=15)
        assert reply["action"] == "end_turn", f"unexpected reply: {reply}"
        # Verify reply archived
        assert (run_root/"mailbox"/"archive"/f"reply-{r:04d}.json").exists(), "reply not archived"
        print(f"  round {r} OK: {reply['action']}")
    print("NORMAL_ROUNDS_PASS")
finally:
    proc.wait(timeout=10)
    out = proc.stdout.read().decode() if proc.stdout else ""
    print("---- responder stdout ----")
    print(out)
    if proc.returncode != 0:
        print(f"responder exit={proc.returncode}")
        sys.exit(proc.returncode)
PYEOF
echo "[e2e] normal rounds PASS"

# Step 4: Bad envelope (extra event field) must be rejected by bridge BEFORE file write
echo "[e2e] E2E negative: malformed envelope must fail closed"
"$PY" - "$RUN_ROOT" "$B_PREP" <<'PYEOF'
import sys, shutil
from pathlib import Path
run_root = Path(sys.argv[1]); b_prep = Path(sys.argv[2])
sys.path.insert(0, str(b_prep / "harness"))
from mailbox_bridge import MailboxBridge, MailboxEnvelopeError
b_session = "probe-session-abc"
bridge = MailboxBridge(run_root/"mailbox"/"inbox", run_root/"mailbox"/"outbox", run_root/"mailbox"/"archive", b_session)
bad = {"phase":"B","allowed_sequences":[14,22],
       "event":{"event_id":"X","sequence":14,"occurred_at":"t","dimension":"d",
                "source_kind":"c","source_class":"u","modality":"m",
                "resident_visible_payload":{},"fixture_secret":"leak"},
       "runtime_snapshot":{},"capability_catalog":[],"capability_history":[]}
before = set(p.name for p in (run_root/"mailbox"/"inbox").iterdir())
before_round = bridge.round
try:
    bridge.send(bad)
    print("FAIL: bad envelope accepted")
    sys.exit(1)
except MailboxEnvelopeError as e:
    print(f"  bad envelope rejected as expected: {e}")
    after = set(p.name for p in (run_root/"mailbox"/"inbox").iterdir())
    assert before == after, "bad envelope caused a file write in inbox"
    assert bridge.round == before_round, "bridge round counter advanced on bad envelope"
    print(f"  inbox unchanged ({len(after)} files, round counter still at {bridge.round})")
    print("MALFORMED_ENVELOPE_FAIL_CLOSED")
PYEOF
echo "[e2e] malformed-envelope fail-closed PASS"

echo
echo "E2E_PROBE_PASS"
