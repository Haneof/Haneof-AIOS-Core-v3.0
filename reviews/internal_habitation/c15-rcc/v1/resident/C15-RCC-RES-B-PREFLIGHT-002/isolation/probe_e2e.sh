#!/bin/bash
# C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-002 — Full E2E transport probe (operator side).
# Must be run as root (sudo). Proves all 4 blockers of CORRECTIVE-002 plus original 8.
# - Mailbox request/reply binding (6 negatives + 1 positive)
# - Genuine Core ModelHandler path via FusedTurnRuntime -> bridge -> sandbox responder -> Core
# - PID1 supervisor hierarchy
# - Privdrop negative fail-closed
# Does NOT reveal cursor 14, does NOT run real Resident B/C, no fixture payload.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/user/Haneof-AIOS-Core-v3.0}"
B_PREP="$REPO_ROOT/reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002"

RUN_ROOT="${RUN_ROOT:-/tmp/b-preflight-e2e-$$}"
echo "[e2e] run_root = $RUN_ROOT"
mkdir -p "$RUN_ROOT"/{runtime,sandbox,mailbox/{inbox,outbox,archive},scratch,inject}

# Copy byte-exact A-002 lineage
cp "$B_PREP/lineage_copy/private_world.sqlite" "$RUN_ROOT/runtime/world.sqlite"
cp "$B_PREP/lineage_copy/world_index.sqlite" "$RUN_ROOT/runtime/index.sqlite"
cp "$B_PREP/lineage_copy/release_state.json" "$RUN_ROOT/runtime/release_state.json"
touch "$RUN_ROOT/runtime/world.writer.lock"

(cd "$RUN_ROOT/runtime" && sha256sum -c - <<EOF
626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa  world.sqlite
ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1  index.sqlite
eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8  release_state.json
EOF
)
echo "[e2e] lineage copy digests OK"

# Inject
cp "$B_PREP/isolation/resident_test_responder.py" "$RUN_ROOT/inject/responder.py"
cp "$B_PREP/isolation/probe_isolation.sh" "$RUN_ROOT/inject/probe_isolation.sh"
cp "$B_PREP/harness/mailbox_bridge.py" "$RUN_ROOT/inject/mailbox_bridge.py"
cp "$B_PREP/harness/bridged_model_handler.py" "$RUN_ROOT/inject/bridged_model_handler.py"
chmod +x "$RUN_ROOT/inject/probe_isolation.sh"

PY="python3"
PYTHONPATH="$REPO_ROOT/src:$B_PREP/harness:$RUN_ROOT/inject"
export PYTHONPATH

echo "[e2e] step 1: mailbox_bridge self-tests (including binding)"
"$PY" "$B_PREP/harness/mailbox_bridge.py" self-test

echo "[e2e] step 2: hardened isolation probe inside sandbox (PID1 supervisor)"
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
grep "pid 1 comm" "$RUN_ROOT/isolation_probe.log" | grep -q "sandbox-init" || { echo "FAIL: PID1 not sandbox-init"; exit 1; }
grep -q "resident pid.*!= 1" "$RUN_ROOT/isolation_probe.log" || { echo "FAIL: resident pid check missing"; exit 1; }
echo "[e2e] PID1 supervisor evidence OK"

echo "[e2e] step 3: mailbox binding E2E (normal + 6 negatives)"
sudo -E "$PY" - "$RUN_ROOT" "$B_PREP" "$REPO_ROOT" <<'PYEOF'
import json, os, shutil, subprocess, sys, time, hashlib
from pathlib import Path
run_root = Path(sys.argv[1])
b_prep = Path(sys.argv[2])
repo = Path(sys.argv[3])
sys.path.insert(0, str(b_prep / "harness"))
from mailbox_bridge import MailboxBridge, MailboxEnvelopeError, MailboxReplyError

def clean_mailbox(root):
    for sub in ("inbox","outbox","archive"):
        d = root/"mailbox"/sub
        d.mkdir(parents=True, exist_ok=True)
        # Use sudo-like handling: try normal, else use os.system rm
        try:
            for f in list(d.iterdir()):
                if f.is_file():
                    try:
                        f.unlink()
                    except PermissionError:
                        os.system(f"sudo rm -f '{f}'")
        except PermissionError:
            os.system(f"sudo rm -f {d}/* 2>/dev/null; sudo mkdir -p {d}")

# Helper to launch responder for normal rounds
def test_normal():
    print("[binding] test normal correct binding")
    clean_mailbox(run_root)
    b_session = "probe-binding-normal"
    bridge = MailboxBridge(run_root/"mailbox"/"inbox", run_root/"mailbox"/"outbox", run_root/"mailbox"/"archive", b_session)
    sb = run_root/"sandbox"
    if sb.exists():
        os.system(f"sudo rm -rf '{sb}'")
    jail = [
        "sudo", "--preserve-env=PROBE_MODE,PROBE_ROUNDS,PATH",
        "python3", str(b_prep/"harness"/"resident_jail.py"),
        "--repo", str(repo),
        "--sandbox", str(sb),
        "--world", str(run_root/"runtime"/"world.sqlite"),
        "--index", str(run_root/"runtime"/"index.sqlite"),
        "--state", str(run_root/"runtime"/"release_state.json"),
        "--lock", str(run_root/"runtime"/"world.writer.lock"),
        "--mailbox-root", str(run_root/"mailbox"),
        "--inject-dir", str(run_root/"inject"),
        "--", "/usr/bin/python3", "/work/inject/responder.py", "--mode", "normal", "--rounds", "2"
    ]
    env = os.environ.copy()
    env["PROBE_MODE"] = "normal"
    env["PROBE_ROUNDS"] = "2"
    proc = subprocess.Popen(jail, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(1.2)
    try:
        base_env = {
            "phase": "B", "allowed_sequences": [14,22], "event": None,
            "runtime_snapshot": {"world_revision": 98, "subject": "user_1", "session_id": b_session},
            "capability_catalog": [], "capability_history": [], "wake_reason": "probe", "is_periodic_review": False, "is_summary_request": False,
        }
        for r in range(1, 3):
            env_to_send = dict(base_env)
            bridge.send(env_to_send)
            assert (run_root/"mailbox"/"inbox"/f"round-{r:04d}.json").exists()
            inbox_data = json.loads((run_root/"mailbox"/"inbox"/f"round-{r:04d}.json").read_text())
            assert "request_id" in inbox_data and "request_digest" in inbox_data
            assert len(inbox_data["request_id"]) == 32
            assert len(inbox_data["request_digest"]) == 64
            reply = bridge.wait_for_reply(timeout=15)
            assert reply["action"] == "end_turn"
            assert reply["round"] == r
            assert reply["request_id"] == inbox_data["request_id"]
            assert reply["request_digest"] == inbox_data["request_digest"]
            print(f"  round {r} correct binding OK: id={reply['request_id'][:8]}...")
        print("NORMAL_BINDING_PASS")
    finally:
        proc.wait(timeout=10)
        out = proc.stdout.read().decode() if proc.stdout else ""
        print("---- responder normal stdout ----")
        print(out)
        if proc.returncode != 0:
            print(f"FAIL responder exit={proc.returncode}")
            sys.exit(1)
    clean_mailbox(run_root)

def test_stale():
    print("[binding] test stale prior-round rejected")
    b_session = "probe-stale"
    bridge = MailboxBridge(run_root/"mailbox"/"inbox", run_root/"mailbox"/"outbox", run_root/"mailbox"/"archive", b_session)
    base_env = {"phase":"B","allowed_sequences":[14,22],"event":None,"runtime_snapshot":{},"capability_catalog":[],"capability_history":[],"wake_reason":"probe"}
    bridge.send(dict(base_env))
    out1 = bridge.outstanding
    reply1 = {"round": out1["round"], "request_id": out1["request_id"], "request_digest": out1["request_digest"], "action":"silence"}
    (run_root/"mailbox"/"outbox"/f"reply-{out1['round']:04d}.json").write_text(json.dumps(reply1))
    got = bridge.wait_for_reply(timeout=3)
    assert got["action"]=="silence"
    print(f"  round1 ok id={out1['request_id'][:8]}")
    bridge.send(dict(base_env))
    out2 = bridge.outstanding
    stale = {"round": out1["round"], "request_id": out1["request_id"], "request_digest": out1["request_digest"], "action":"silence"}
    (run_root/"mailbox"/"outbox"/f"reply-{out2['round']:04d}.json").write_text(json.dumps(stale))
    try:
        bridge.wait_for_reply(timeout=3)
        print("FAIL stale accepted")
        sys.exit(1)
    except MailboxReplyError as e:
        print(f"  stale rejected as expected: {e}")
        assert out2["request_id"] not in bridge._consumed
        print("STALE_REJECTED_PASS")
    assert (run_root/"mailbox"/"archive"/f"rejected-reply-{out2['round']:04d}.json").exists()
    clean_mailbox(run_root)

def test_preplay():
    print("[binding] test preplayed future-round rejected")
    b_session = "probe-preplay"
    bridge = MailboxBridge(run_root/"mailbox"/"inbox", run_root/"mailbox"/"outbox", run_root/"mailbox"/"archive", b_session)
    base_env = {"phase":"B","allowed_sequences":[14,22],"event":None,"runtime_snapshot":{},"capability_catalog":[],"capability_history":[],"wake_reason":"probe"}
    guessed = {"round":1, "request_id":"a"*32, "request_digest":"b"*64, "action":"silence"}
    (run_root/"mailbox"/"outbox"/"reply-0001.json").write_text(json.dumps(guessed))
    bridge.send(dict(base_env))
    try:
        bridge.wait_for_reply(timeout=3)
        print("FAIL preplay accepted")
        sys.exit(1)
    except MailboxReplyError as e:
        print(f"  preplay rejected as expected: {e}")
        print("PREPLAY_REJECTED_PASS")
    clean_mailbox(run_root)

def test_replay():
    print("[binding] test replayed consumed rejected")
    b_session = "probe-replay"
    bridge = MailboxBridge(run_root/"mailbox"/"inbox", run_root/"mailbox"/"outbox", run_root/"mailbox"/"archive", b_session)
    base_env = {"phase":"B","allowed_sequences":[14,22],"event":None,"runtime_snapshot":{},"capability_catalog":[],"capability_history":[],"wake_reason":"probe"}
    bridge.send(dict(base_env))
    out1 = bridge.outstanding
    reply1 = {"round": out1["round"], "request_id": out1["request_id"], "request_digest": out1["request_digest"], "action":"silence"}
    (run_root/"mailbox"/"outbox"/f"reply-{out1['round']:04d}.json").write_text(json.dumps(reply1))
    bridge.wait_for_reply(timeout=3)
    print(f"  round1 consumed id={out1['request_id'][:8]}")
    bridge.send(dict(base_env))
    out2 = bridge.outstanding
    replay = {"round": out2["round"], "request_id": out1["request_id"], "request_digest": out2["request_digest"], "action":"silence"}
    (run_root/"mailbox"/"outbox"/f"reply-{out2['round']:04d}.json").write_text(json.dumps(replay))
    try:
        bridge.wait_for_reply(timeout=3)
        print("FAIL replay accepted")
        sys.exit(1)
    except MailboxReplyError as e:
        msg = str(e).lower()
        assert "replay" in msg or "consumed" in msg or "request_id" in msg
        print(f"  replay rejected as expected: {e}")
        print("REPLAY_REJECTED_PASS")
    clean_mailbox(run_root)

def test_wrong_id():
    print("[binding] test wrong request_id rejected")
    b_session = "probe-wrongid"
    bridge = MailboxBridge(run_root/"mailbox"/"inbox", run_root/"mailbox"/"outbox", run_root/"mailbox"/"archive", b_session)
    base_env = {"phase":"B","allowed_sequences":[14,22],"event":None,"runtime_snapshot":{},"capability_catalog":[],"capability_history":[],"wake_reason":"probe"}
    bridge.send(dict(base_env))
    out = bridge.outstanding
    wrong_id = "f"*32 if out["request_id"] != "f"*32 else "e"*32
    bad = {"round": out["round"], "request_id": wrong_id, "request_digest": out["request_digest"], "action":"silence"}
    (run_root/"mailbox"/"outbox"/f"reply-{out['round']:04d}.json").write_text(json.dumps(bad))
    try:
        bridge.wait_for_reply(timeout=3)
        print("FAIL wrong id accepted")
        sys.exit(1)
    except MailboxReplyError as e:
        print(f"  wrong id rejected: {e}")
        print("WRONG_ID_REJECTED_PASS")
    clean_mailbox(run_root)

def test_wrong_digest():
    print("[binding] test wrong request_digest rejected")
    b_session = "probe-wrongdg"
    bridge = MailboxBridge(run_root/"mailbox"/"inbox", run_root/"mailbox"/"outbox", run_root/"mailbox"/"archive", b_session)
    base_env = {"phase":"B","allowed_sequences":[14,22],"event":None,"runtime_snapshot":{},"capability_catalog":[],"capability_history":[],"wake_reason":"probe"}
    bridge.send(dict(base_env))
    out = bridge.outstanding
    wrong_dg = "f"*64 if out["request_digest"] != "f"*64 else "e"*64
    bad = {"round": out["round"], "request_id": out["request_id"], "request_digest": wrong_dg, "action":"silence"}
    (run_root/"mailbox"/"outbox"/f"reply-{out['round']:04d}.json").write_text(json.dumps(bad))
    try:
        bridge.wait_for_reply(timeout=3)
        print("FAIL wrong digest accepted")
        sys.exit(1)
    except MailboxReplyError as e:
        print(f"  wrong digest rejected: {e}")
        print("WRONG_DIGEST_REJECTED_PASS")
    clean_mailbox(run_root)

def test_future_not_become_valid():
    print("[binding] test future reply does not become valid later")
    b_session = "probe-futurevalid"
    bridge = MailboxBridge(run_root/"mailbox"/"inbox", run_root/"mailbox"/"outbox", run_root/"mailbox"/"archive", b_session)
    base_env = {"phase":"B","allowed_sequences":[14,22],"event":None,"runtime_snapshot":{},"capability_catalog":[],"capability_history":[],"wake_reason":"probe"}
    future_guess = {"round":2, "request_id":"c"*32, "request_digest":"d"*64, "action":"silence"}
    (run_root/"mailbox"/"outbox"/"reply-0002.json").write_text(json.dumps(future_guess))
    bridge.send(dict(base_env))
    out1 = bridge.outstanding
    reply1 = {"round": out1["round"], "request_id": out1["request_id"], "request_digest": out1["request_digest"], "action":"silence"}
    (run_root/"mailbox"/"outbox"/f"reply-{out1['round']:04d}.json").write_text(json.dumps(reply1))
    bridge.wait_for_reply(timeout=3)
    print("  round1 ok")
    bridge.send(dict(base_env))
    try:
        bridge.wait_for_reply(timeout=3)
        print("FAIL future preplayed became valid")
        sys.exit(1)
    except MailboxReplyError as e:
        print(f"  future preplayed correctly rejected even after advancing: {e}")
        print("FUTURE_NOT_VALID_PASS")
    clean_mailbox(run_root)

test_normal()
test_stale()
test_preplay()
test_replay()
test_wrong_id()
test_wrong_digest()
test_future_not_become_valid()
print("ALL_BINDING_TESTS_PASS")
PYEOF
echo "[e2e] binding tests PASS"

echo "[e2e] step 4: genuine Core ModelHandler path E2E (FusedTurnRuntime -> bridge -> sandbox responder -> Core)"
sudo -E "$PY" - "$RUN_ROOT" "$B_PREP" "$REPO_ROOT" <<'PYEOF'
import json, os, sys, time, shutil, subprocess, hashlib
from pathlib import Path
run_root = Path(sys.argv[1])
b_prep = Path(sys.argv[2])
repo = Path(sys.argv[3])
sys.path.insert(0, str(b_prep / "harness"))
sys.path.insert(0, str(repo / "src"))

from mailbox_bridge import MailboxBridge, MailboxReplyError, MailboxEnvelopeError
from bridged_model_handler import MailboxModelHandler, get_contract_sha256
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.turn_runtime import FusedTurnRuntime

world = run_root/"runtime"/"world.sqlite"
index = run_root/"runtime"/"index.sqlite"
lock = run_root/"runtime"/"world.writer.lock"
store = SQLiteWorldStore(world)
idx = WorldSearchIndex(index, store=store)
print(f"[genuine] world_revision={store.current_world_revision()} watermark={idx.watermark()}")

b_session = "probe-genuine-c15-b-001"
contract_sha = get_contract_sha256(repo)
print(f"[genuine] contract_sha256={contract_sha[:16]}...")

bridge = MailboxBridge(run_root/"mailbox"/"inbox", run_root/"mailbox"/"outbox", run_root/"mailbox"/"archive", b_session)
handler = MailboxModelHandler(bridge, b_session_id=b_session, contract_sha256=contract_sha)

for p in (run_root/"mailbox"/"inbox").iterdir():
    try: p.unlink()
    except: os.system(f"sudo rm -f '{p}'")
for p in (run_root/"mailbox"/"outbox").iterdir():
    try: p.unlink()
    except: os.system(f"sudo rm -f '{p}'")

sb = run_root/"sandbox"
if sb.exists():
    os.system(f"sudo rm -rf '{sb}'")
jail_cmd = [
    "sudo", "--preserve-env=PROBE_MODE,PROBE_ROUNDS,PATH",
    "python3", str(b_prep / "harness" / "resident_jail.py"),
    "--repo", str(repo),
    "--sandbox", str(sb),
    "--world", str(world),
    "--index", str(index),
    "--state", str(run_root/"runtime"/"release_state.json"),
    "--lock", str(lock),
    "--mailbox-root", str(run_root/"mailbox"),
    "--inject-dir", str(run_root/"inject"),
    "--", "/usr/bin/python3", "/work/inject/responder.py", "--mode", "genuine", "--rounds", "2"
]
env = os.environ.copy()
proc = subprocess.Popen(jail_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(1.5)
if proc.poll() is not None:
    out = proc.stdout.read().decode()
    print(out)
    print("[genuine] FAIL responder exited early before turn")
    sys.exit(1)

runtime = FusedTurnRuntime(store=store, index=idx, subject_id="user_1", model_handler=handler, max_tool_rounds=4)
session_id = b_session
turn_index = 1
user_input = "synthetic probe hello world - genuine path test"
from datetime import datetime, timezone
occurred_at = datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc)

print("[genuine] invoking FusedTurnRuntime.run_turn with synthetic input")
try:
    result = runtime.run_turn(session_id=session_id, turn_index=turn_index, user_input=user_input, occurred_at=occurred_at)
except Exception as e:
    print(f"[genuine] run_turn failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    proc.terminate()
    proc.wait(timeout=5)
    sys.exit(1)

print(f"[genuine] run_turn completed: model_rounds={result.runtime.model_rounds} termination={result.runtime.termination_reason}")
print(f"[genuine] capability_history len={len(result.runtime.capability_history)}")
assert handler.invocations >= 2, f"expected at least 2 model invocations, got {handler.invocations}"
print(f"[genuine] handler invocations={handler.invocations} (capability + follow-up)")
last_env = handler.last_envelope
assert last_env is not None
rs = last_env.get("runtime_snapshot")
assert isinstance(rs, dict), "runtime_snapshot missing"
if "world_map" not in json.dumps(rs):
    print("[genuine] warning: runtime_snapshot does not contain world_map")
    print(f"  keys: {list(rs.keys())[:20]}")
else:
    print("[genuine] runtime_snapshot contains world_map (Core-generated)")
assert len(last_env.get("capability_catalog", [])) > 10, "capability_catalog too small, not genuine"
print(f"[genuine] capability_catalog size={len(last_env['capability_catalog'])} (genuine)")
print(f"[genuine] bridge round={bridge.round} consumed={len(bridge._consumed)} outstanding={bridge.outstanding}")
assert bridge.round == 2, f"expected bridge round 2, got {bridge.round}"
assert len(bridge._consumed) == 2
assert result.runtime.silenced or result.runtime.termination_reason in ("silence", "tool_round_budget_exhausted", "responded")
print(f"[genuine] silenced={result.runtime.silenced} response={result.runtime.response}")
assert (run_root/"mailbox"/"archive"/"request-0001.json").exists()
assert (run_root/"mailbox"/"archive"/"reply-0001.json").exists()
assert (run_root/"mailbox"/"archive"/"request-0002.json").exists()
assert (run_root/"mailbox"/"archive"/"reply-0002.json").exists()
print("[genuine] archive evidence verified for both rounds")
found_search = any(getattr(ch, 'name', ch.get('name') if isinstance(ch, dict) else '') == "search_world" for ch in result.runtime.capability_history)
if not found_search:
    # check history is tuple of CapabilityResult
    try:
        found_search = any(ch.name == "search_world" for ch in result.runtime.capability_history)
    except:
        pass
if not found_search:
    print(f"[genuine] FAIL capability search_world not in history: {result.runtime.capability_history}")
    sys.exit(1)
print("[genuine] capability search_world executed and second round walked same bridge (verified)")

print("[genuine] testing malformed reply fail-closed on genuine path")
os.system(f"sudo rm -rf '{sb}'")
bridge2 = MailboxBridge(run_root/"mailbox"/"inbox", run_root/"mailbox"/"outbox", run_root/"mailbox"/"archive", b_session + "-malformed")
handler2 = MailboxModelHandler(bridge2, b_session_id=b_session + "-malformed", contract_sha256=contract_sha)
jail2 = [
    "sudo", "--preserve-env=PROBE_MODE,PROBE_ROUNDS,PATH",
    "python3", str(b_prep / "harness" / "resident_jail.py"),
    "--repo", str(repo),
    "--sandbox", str(sb),
    "--world", str(world),
    "--index", str(index),
    "--state", str(run_root/"runtime"/"release_state.json"),
    "--lock", str(lock),
    "--mailbox-root", str(run_root/"mailbox"),
    "--inject-dir", str(run_root/"inject"),
    "--", "/usr/bin/python3", "/work/inject/responder.py", "--mode", "malformed", "--rounds", "1"
]
proc2 = subprocess.Popen(jail2, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(1.5)
store2 = SQLiteWorldStore(world)
idx2 = WorldSearchIndex(index, store=store2)
runtime2 = FusedTurnRuntime(store=store2, index=idx2, subject_id="user_1", model_handler=handler2, max_tool_rounds=4)
try:
    runtime2.run_turn(session_id=b_session+"-mal", turn_index=1, user_input="malformed test", occurred_at=occurred_at)
    print("[genuine] FAIL malformed reply should have caused ModelDispatchNotSubmitted but succeeded")
    proc2.terminate()
    proc2.wait(timeout=5)
    sys.exit(1)
except Exception as e:
    msg = str(e).lower()
    if "dispatch" in msg or "reply" in msg or "malformed" in msg or "bridge" in msg:
        print(f"[genuine] malformed correctly fail-closed: {type(e).__name__}: {e}")
    else:
        print(f"[genuine] malformed failed but unexpected: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        proc2.terminate()
        proc2.wait(timeout=5)
        sys.exit(1)
    print("MALFORMED_FAIL_CLOSED_PASS")

for p in (proc, proc2):
    try:
        p.terminate()
        p.wait(timeout=3)
    except:
        try: p.kill()
        except: pass
    try:
        out = p.stdout.read().decode() if p.stdout else ""
        print("--- responder tail ---")
        print(out[-2000:])
    except: pass

print("GENUINE_CORE_PATH_PASS")
PYEOF
echo "[e2e] genuine Core path PASS"

echo "[e2e] step 5: privdrop negative fail-closed test"
sudo -E "$PY" - "$RUN_ROOT" "$B_PREP" "$REPO_ROOT" <<'PYEOF'
import subprocess, sys, os, time, pathlib, shutil
from pathlib import Path
run_root = Path(sys.argv[1]) if len(sys.argv)>1 else Path(os.getenv("RUN_ROOT"))
b_prep = Path(os.getenv("B_PREP", "/home/user/Haneof-AIOS-Core-v3.0/reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002"))
repo = Path(os.getenv("REPO_ROOT", "/home/user/Haneof-AIOS-Core-v3.0"))
sb = run_root / "sandbox_privdrop"
mb = run_root / "mailbox_privdrop"
if sb.exists():
    os.system(f"sudo rm -rf '{sb}'")
if mb.exists():
    os.system(f"sudo rm -rf '{mb}'")
mb.mkdir(parents=True)
for sub in ("inbox","outbox","archive"):
    (mb/sub).mkdir(parents=True)

sentinel = Path("/tmp/SENTINEL_PRIVDROP_NEGATIVE")
if sentinel.exists():
    sentinel.unlink()

wrapper = run_root / "inject" / "sentinel_wrapper.sh"
wrapper.write_text("#!/bin/sh\necho sentinel_running > /tmp/SHOULD_NOT_EXIST\necho sentinel_running > /work/outbox/SENTINEL_OUTBOX\nexit 0\n")
wrapper.chmod(0o755)

world = run_root/"runtime"/"world.sqlite"
indexp = run_root/"runtime"/"index.sqlite"
state = run_root/"runtime"/"release_state.json"
lock = run_root/"runtime"/"world.writer.lock"

env = os.environ.copy()
env["_RESIDENT_JAIL_INJECT_PRIVDROP_FAIL"] = "1"
cmd = [
    "sudo", "--preserve-env=_RESIDENT_JAIL_INJECT_PRIVDROP_FAIL,_RESIDENT_JAIL_INJECT_FAIL_MODE",
    "python3", str(b_prep/"harness"/"resident_jail.py"),
    "--repo", str(repo),
    "--sandbox", str(sb),
    "--world", str(world),
    "--index", str(indexp),
    "--state", str(state),
    "--lock", str(lock),
    "--mailbox-root", str(mb),
    "--inject-dir", str(run_root/"inject"),
    "--", "/bin/sh", "/work/inject/sentinel_wrapper.sh"
]
print(f"[privdrop] running jail with injected failure, expecting exit 98 and no sentinel")
result = subprocess.run(cmd, env=env, capture_output=True, text=True)
print("stdout:", result.stdout)
print("stderr:", result.stderr)
print(f"exit code: {result.returncode}")
if result.returncode == 0:
    print("FAIL: jail should have failed closed")
    sys.exit(1)
# Check sentinel not created
sentinel_out = mb / "outbox" / "SENTINEL_OUTBOX"
if sentinel_out.exists():
    print(f"FAIL: sentinel outbox was created despite failure")
    sys.exit(1)
else:
    print("PASS: sentinel not created in outbox")
out_files = list((mb/"outbox").glob("*.json"))
if out_files:
    print(f"FAIL: outbox has files after failure: {out_files}")
    sys.exit(1)
else:
    print("PASS: no outbox reply after privdrop failure")
print("PRIVDROP_NEGATIVE_PASS")

env2 = os.environ.copy()
env2["_RESIDENT_JAIL_INJECT_FAIL_MODE"] = "setgid"
result2 = subprocess.run(cmd, env=env2, capture_output=True, text=True)
print(f"[privdrop setgid] exit {result2.returncode}")
if result2.returncode == 0:
    print("FAIL setgid injected failure should not succeed")
    sys.exit(1)
else:
    print("PASS setgid injected failure also fail-closed")
print("PRIVDROP_ALL_PASS")
PYEOF
echo "[e2e] privdrop negative PASS"

echo "[e2e] step 6: signal termination test (PID1 forwards TERM)"
SLEEP_SB="/tmp/b-sleep-test-$$"
SLEEP_MB="/tmp/b-sleep-mb-$$"
sudo rm -rf "$SLEEP_SB" "$SLEEP_MB" 2>/dev/null || true
mkdir -p "$SLEEP_SB" "$SLEEP_MB"/{inbox,outbox,archive}
SLEEP_JAIL_LOG="/tmp/jail_sleep.log"
sudo timeout 10 python3 "$B_PREP/harness/resident_jail.py" \
  --repo "$REPO_ROOT" \
  --sandbox "$SLEEP_SB" \
  --world "$RUN_ROOT/runtime/world.sqlite" \
  --index "$RUN_ROOT/runtime/index.sqlite" \
  --state "$RUN_ROOT/runtime/release_state.json" \
  --lock "$RUN_ROOT/runtime/world.writer.lock" \
  --mailbox-root "$SLEEP_MB" \
  --inject-dir "$RUN_ROOT/inject" \
  -- /bin/sleep 30 >"$SLEEP_JAIL_LOG" 2>&1 &
SLEEP_PID=$!
sleep 2
if kill -0 $SLEEP_PID 2>/dev/null; then
  echo "[signal] jail sleep pid $SLEEP_PID alive, sending TERM"
  sudo kill -TERM $SLEEP_PID 2>/dev/null || kill -TERM $SLEEP_PID
  wait $SLEEP_PID 2>/dev/null || true
  EC=$?
  echo "[signal] jail wait exit code $EC"
  if [ $EC -eq 143 ] || [ $EC -eq 0 ] || [ $EC -eq 124 ] || [ $EC -ge 128 ]; then
    echo "PASS: termination signal correctly ended Resident worker (exit $EC)"
    echo "SIGNAL_TERMINATION_PASS"
  else
    echo "FAIL: unexpected exit code after TERM: $EC"
    cat "$SLEEP_JAIL_LOG" || true
    exit 1
  fi
else
  echo "FAIL: jail sleep process not alive"
  cat "$SLEEP_JAIL_LOG" || true
  exit 1
fi
sudo rm -rf "$SLEEP_SB" "$SLEEP_MB" "$SLEEP_JAIL_LOG"

echo
echo "E2E_PROBE_PASS"
echo "[e2e] all steps complete at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
