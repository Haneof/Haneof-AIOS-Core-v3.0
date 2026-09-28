"""IA rev2 — §24 real process-loss (SIGKILL) probes, not exception simulation.

rev2 changes harness mechanics only (child template substitution). The rev1 expected
outcome is UNCHANGED:

  IA-KILL-1  a child process reaches the trusted return boundary, durably commits the
             handoff, is SIGKILLed, and a fresh process recovers the exact response from
             the same DB with no provider redispatch and identical durable identities.
  IA-KILL-2  a child process durably applies a real side-effecting capability, is
             SIGKILLed before outer completion, and a fresh process converges to exactly
             one World effect.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import textwrap

import pytest

from ia_harness import (
    ANCHOR, NOW, attempt_rows, handoff_rows, idem_rows, new_runtime, q, receipt_rows,
)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHILD = textwrap.dedent(
    """
    import os, signal, sqlite3, sys
    sys.path.insert(0, os.path.join(sys.argv[1], "src"))
    from datetime import datetime, timezone
    from aios_core.contracts.enums import SourceClass
    from aios_core.contracts.models import Observation
    from aios_core.contracts.operations import OperationRequest
    from aios_core.contracts.time import TemporalExtent
    from aios_core.query.search import WorldSearchIndex
    from aios_core.runtime import (ModelCallProvenance, ModelDirective, ModelUsage)
    from aios_core.runtime.capabilities import CapabilityCall
    from aios_core.runtime.turn_runtime import FusedTurnRuntime
    from aios_core.storage.sqlite_store import SQLiteWorldStore

    REPO, DB, MODE, ANCHOR = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    NOW = datetime(2026, 9, 28, 6, tzinfo=timezone.utc)
    SESSION = "ia-kill-session"

    def directive(r, watch=None):
        rid = "kill-req-" + str(r)
        calls = () if watch is None else (watch,)
        return ModelDirective(
            response=None if watch is not None else "killed exactly once",
            capability_calls=calls,
            usage=ModelUsage(input_tokens=4, output_tokens=2, total_tokens=6,
                             provider="kill-provider", model="kill-model",
                             request_id=rid),
            provenance=ModelCallProvenance(provider="kill-provider",
                                           model="kill-model", request_id=rid))

    def watch(r):
        return CapabilityCall(
            name="create_attention_watch", call_id="kill-watch-" + str(r),
            arguments={"title": "kill watch " + str(r),
                       "dimensions": ["dim:ia"],
                       "reason_refs": [{"object_id": ANCHOR, "revision": 1}],
                       "source_kind": "conversation", "modality": "text",
                       "priority": 40, "cooldown_seconds": 60})

    store = SQLiteWorldStore(DB)
    index = WorldSearchIndex(DB, store=store)
    index.rebuild()
    with sqlite3.connect(DB) as conn:
        n = conn.execute("SELECT count(*) FROM object_revisions").fetchone()[0]
    if n == 0:
        store.commit([Observation(
            object_id=ANCHOR, subject_id="user_1", occurred=TemporalExtent.point(NOW),
            learned_at=NOW, recorded_at=NOW, created_by="ia:kill",
            source_kind="conversation", modality="text", value="kill anchor",
            metadata={"dimension": "dim:ia"})],
            OperationRequest(operation_name="ia.kill.seed",
                             expected_world_revision=int(store.current_world_revision()),
                             reason="seed", idempotency_key="kill-anchor",
                             source_class=SourceClass.USER))
        index.catch_up()

    rt = FusedTurnRuntime(
        store=store, index=index,
        model_handler=lambda s: directive(s.round_index, watch(s.round_index)))

    if MODE == "handoff":
        original = rt.cognitive_runtime.model_response_recorder

        def kill_at_boundary(snapshot, returned):
            if snapshot.round_index == 0:
                sys.stdout.flush()
                os.kill(os.getpid(), signal.SIGKILL)
            original(snapshot, returned)

        rt.cognitive_runtime.model_response_recorder = kill_at_boundary
    else:
        real = rt.registry.invoke

        def boundary(c):
            if c.call_id == "kill-watch-0":
                res = real(c)
                assert res.ok, "pre-kill capability failure"
                sys.stdout.flush()
                os.kill(os.getpid(), signal.SIGKILL)
            return real(c)

        rt.registry.invoke = boundary

    rt.run_turn(session_id=SESSION, turn_index=1, user_input="kill",
                occurred_at=NOW)
    print("CHILD-COMPLETED-WITHOUT-KILL", flush=True)
    """
)


def _spawn(db, mode, anchor=ANCHOR):
    return subprocess.run(
        [sys.executable, "-c", CHILD, REPO, str(db), mode, anchor],
        capture_output=True, text=True, timeout=240,
    )


def _ran_to_completion(proc):
    return proc.returncode == 0 and "CHILD-COMPLETED-WITHOUT-KILL" in proc.stdout


def test_ia_kill1_sigkill_after_trusted_handoff_boundary(tmp_path):
    db = tmp_path / "w.db"
    proc = _spawn(db, "handoff")
    assert not _ran_to_completion(proc), "child was supposed to be SIGKILLed"
    assert proc.returncode == -signal.SIGKILL, (
        f"child exit {proc.returncode}, expected {-signal.SIGKILL}\n"
        f"stderr: {proc.stderr[-1500:]}")

    handoffs, receipts = handoff_rows(db), receipt_rows(db)
    assert len(handoffs) == 1 and len(receipts) == 1
    assert handoffs[0]["attempt_id"] == receipts[0]["attempt_id"]
    aid = handoffs[0]["attempt_id"]
    before = [r for r in attempt_rows(db) if r["attempt_id"] == aid][0]
    assert before["model_round_index"] == 0

    served = []

    def forbidden(snapshot):
        # Round 0 is durably handed off and must never reach the provider again.
        # A later NEW round is legitimate; record and fail on replay of round 0.
        served.append(snapshot.round_index)
        if snapshot.round_index == 0:
            raise AssertionError("KILL-1 REDISPATCH of recovered round 0")
        from aios_core.runtime import (ModelCallProvenance, ModelDirective, ModelUsage)
        rid = f"kill-req-{snapshot.round_index}"
        return ModelDirective(
            response="killed exactly once", capability_calls=(),
            usage=ModelUsage(input_tokens=4, output_tokens=2, total_tokens=6,
                             provider="kill-provider", model="kill-model", request_id=rid),
            provenance=ModelCallProvenance(provider="kill-provider", model="kill-model",
                                           request_id=rid))

    fresh = new_runtime(db, forbidden)
    fresh.run_turn(session_id="ia-kill-session", turn_index=1,
                   user_input="kill", occurred_at=NOW)
    replayed = [r for r in served if r <= before["model_round_index"]]
    assert replayed == [], f"KILL-1 REDISPATCH of the recovered round: {served}"

    after = [r for r in attempt_rows(db) if r["attempt_id"] == aid][0]
    assert after["model_round_index"] == before["model_round_index"]
    for col in ("provider", "model", "provider_request_id", "response_fingerprint"):
        if before[col] is not None:
            assert after[col] == before[col], f"attempt {col} changed on recovery"
    assert handoff_rows(db)[0]["directive_payload"] == handoffs[0]["directive_payload"]
    assert receipt_rows(db)[0]["authenticity_proof"] == receipts[0]["authenticity_proof"]
    meters = [m for m in fresh.metering.list_model_calls(subject_id="user_1")]
    # Exactly one durable meter per (attempt, round); the killed attempt must not be
    # metered twice, and any additional meter must belong to a genuinely new round.
    assert len({m.record_id for m in meters}) == len(meters), "DUPLICATE METER RECORD"
    for_mine = [m for m in meters if m.background_attempt_id == aid]
    assert len(for_mine) == 1, f"killed attempt metered {len(for_mine)} times"
    assert len({(m.background_attempt_id, m.model_round_index) for m in meters}) == len(meters)
    status = fresh.inspect_turn_execution(
        session_id="ia-kill-session", turn_index=1, user_input="kill", occurred_at=NOW)
    assert status.state == "completed"


def test_ia_kill2_sigkill_after_real_capability_side_effect(tmp_path):
    db = tmp_path / "w.db"
    proc = _spawn(db, "effect")
    assert not _ran_to_completion(proc), "child was supposed to be SIGKILLed"
    assert proc.returncode == -signal.SIGKILL, (
        f"child exit {proc.returncode}\nstderr: {proc.stderr[-1500:]}")

    tasks_before = q(db, "SELECT object_id, revision FROM object_revisions "
                         "WHERE object_type='task'")
    assert len(tasks_before) == 1, f"expected one real durable task, got {tasks_before}"
    idem_before = {r["idempotency_key"]: (r["operation_id"], r["world_revision"])
                   for r in idem_rows(db)}
    assert any(k.startswith("task-create:") for k in idem_before), \
        "no real task-create operation was made durable before the kill"

    served = []

    def cont(snapshot):
        from aios_core.runtime import ModelCallProvenance, ModelDirective, ModelUsage
        served.append(snapshot.round_index)
        rid = f"kill-req-{snapshot.round_index}"
        return ModelDirective(
            response="killed exactly once", capability_calls=(),
            usage=ModelUsage(input_tokens=4, output_tokens=2, total_tokens=6,
                             provider="kill-provider", model="kill-model",
                             request_id=rid),
            provenance=ModelCallProvenance(provider="kill-provider", model="kill-model",
                                           request_id=rid))

    fresh = new_runtime(db, cont)
    result = fresh.run_turn(session_id="ia-kill-session", turn_index=1,
                            user_input="kill", occurred_at=NOW)
    assert served == [1], f"recovered round was redispatched: {served}"

    tasks_after = q(db, "SELECT object_id, revision FROM object_revisions "
                        "WHERE object_type='task'")
    assert len(tasks_after) == 1, f"DUPLICATE CAPABILITY EFFECT: {tasks_after}"
    assert tasks_after[0] == tasks_before[0], "task identity/revision changed"

    idem_after = {r["idempotency_key"]: (r["operation_id"], r["world_revision"])
                  for r in idem_rows(db)}
    for key, identity in idem_before.items():
        assert idem_after.get(key) == identity, (
            f"DURABLE IDENTITY CHANGED for {key}: {identity} -> {idem_after.get(key)}")

    hist = {h.call_id: h for h in result.runtime.capability_history}
    assert "kill-watch-0" in hist, "recovered round did not replay the capability"
    assert hist["kill-watch-0"].ok, (
        f"R5-C REPLAY FAILED: {hist['kill-watch-0'].error_code} / "
        f"{hist['kill-watch-0'].error_message}")
    status = fresh.inspect_turn_execution(
        session_id="ia-kill-session", turn_index=1, user_input="kill", occurred_at=NOW)
    assert status.state == "completed"
