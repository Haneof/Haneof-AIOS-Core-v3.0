#!/usr/bin/env python3
"""WINDOW 14 supplementary frozen probes: stale capability across retry + schema upgrade.

Frozen (SHA256SUMS_SUPPLEMENTARY) before first execution.  Fixed expectations,
recorded before any candidate run:

S1 (task 21) — stale capability across a *legal typed* not_submitted retry.
   The branch-aware contract is decided by whether the retry's durable binding
   rotates (new outbound fingerprint/relay) or is identical:
   * binding rotated  -> the capability must rotate/re-scope with it: the
     retried dispatch's own real return MUST remain attachable under the
     capability handed out at the retried dispatch, and the pre-retry
     capability MUST NOT authenticate the new binding's return.  A stale row
     that makes the retried return permanently unattachable is FAIL.
   * binding identical -> the request identity is unchanged; the one-shot
     capability for (attempt, round, request) remains the authority.  It must
     still yield at most one canonical response (first writer wins, conflicting
     bytes fail closed after consumption).  Old-proof-accepted is PASS here.
   In BOTH branches: a second, different response must never attach.

S2 (task 23) — schema upgrade/restart.  Opening a pre-candidate Core DB with the
   candidate runtime must preserve historical attempts and their states
   (in_doubt stays in_doubt), leave World revision unchanged, and mint NO
   capability row for historical attempts that never had a dispatch-time trust
   handoff.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelDispatchNotSubmitted,
    ModelUsage,
)
from aios_core.runtime.background_attempt import (
    BackgroundModelResponseConflict,
    encode_model_directive,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


class Responder:
    def __init__(self):
        self.capabilities = {}

    def accept_return_capability(self, snapshot, capability):
        self.capabilities[capability.attempt_id] = capability


def directive(request_id: str) -> ModelDirective:
    return ModelDirective(
        response=f"return for {request_id}",
        capability_calls=(),
        usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2,
                         provider="p", model="m", request_id=request_id),
        provenance=ModelCallProvenance(provider="p", model="m", request_id=request_id),
    )


def s1_stale_capability_across_retry(root: Path) -> tuple[str, str, bool]:
    db = root / "stale.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    responder = Responder()
    state = {"phase": "first"}

    def handler(_snapshot):
        if state["phase"] == "first":
            raise ModelDispatchNotSubmitted("adapter says: never wrote the request")
        return directive("second-request")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=handler,
                               external_return_observer=responder)
    try:
        runtime.run_turn(session_id="s1", turn_index=1, user_input="go",
                         occurred_at=NOW, current_topic=None)
    except ModelDispatchNotSubmitted:
        pass
    attempts = runtime.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind="user_turn",
        work_id=runtime.turn_executions.execution_id_for(
            subject_id="user_1", session_id="s1", turn_index=1))
    first = attempts[0]
    assert first.state == "not_submitted", first.state
    first_cap = responder.capabilities[first.attempt_id]
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT outbound_request_fingerprint, relay_id, capability_nonce, consumed_at "
            "FROM background_model_return_capabilities WHERE attempt_id=?",
            (first.attempt_id,)).fetchone()
    assert row is not None, "capability row missing after first dispatch"
    old_fp, old_relay, old_nonce, old_consumed = row
    assert old_consumed is None

    # Accepted CG003 legal retry of the same logical attempt.
    state["phase"] = "second"
    runtime.authorize_turn_retry(
        session_id="s1", turn_index=1, user_input="go", occurred_at=NOW,
        evidence="typed adapter boundary proves the first request never left",
    )
    result = runtime.run_turn(session_id="s1", turn_index=1, user_input="go",
                              occurred_at=NOW, current_topic=None)
    binding = runtime.background_model_attempts.outbound_request_binding(first.attempt_id)
    new_cap = responder.capabilities[first.attempt_id]
    with sqlite3.connect(db) as conn:
        row2 = conn.execute(
            "SELECT outbound_request_fingerprint, relay_id, capability_nonce, consumed_at "
            "FROM background_model_return_capabilities WHERE attempt_id=?",
            (first.attempt_id,)).fetchone()

    rotated = (binding.outbound_request_fingerprint, binding.relay_id) != (old_fp, old_relay)
    problems: list[str] = []
    second_return = directive("second-request")

    # 1. The retried dispatch's own real return must be attachable under the
    #    capability handed out at the retried dispatch, in BOTH branches.
    try:
        runtime.background_model_attempts.attach_late_trusted_return(
            first.attempt_id,
            attached_at=NOW + timedelta(minutes=2),
            directive_payload=encode_model_directive(second_return),
            late_return_proof=new_cap.prove_external_return(second_return),
            evidence="current dispatch capability signs its own return",
        )
    except Exception as exc:
        problems.append(
            f"THE RETRIED DISPATCH'S OWN RETURN CANNOT BE ATTACHED: {type(exc).__name__}: {exc}"
        )

    # 2. First-writer-wins: a second, different response must never attach,
    #    regardless of which capability signs it.
    conflicting = directive("conflicting")
    for label, cap in (("pre-retry", first_cap), ("retried", new_cap)):
        try:
            runtime.background_model_attempts.attach_late_trusted_return(
                first.attempt_id,
                attached_at=NOW + timedelta(minutes=3),
                directive_payload=encode_model_directive(conflicting),
                late_return_proof=cap.prove_external_return(conflicting),
                evidence=f"conflicting response under {label} capability",
            )
            problems.append(f"CONFLICTING RESPONSE ATTACHED UNDER {label} CAPABILITY")
        except (BackgroundModelResponseConflict, ValueError):
            pass

    # 3. Branch-specific stale-capability rule.
    stale_signed_new = False
    if rotated:
        try:
            runtime.background_model_attempts.attach_late_trusted_return(
                first.attempt_id,
                attached_at=NOW + timedelta(minutes=1),
                directive_payload=encode_model_directive(second_return),
                late_return_proof=first_cap.prove_external_return(second_return),
                evidence="pre-retry capability signs rotated binding return",
            )
            stale_signed_new = True
            problems.append("PRE-RETRY CAPABILITY AUTHENTICATED THE ROTATED BINDING RETURN")
        except (BackgroundModelResponseConflict, ValueError):
            pass
    detail = (
        f"binding_rotated={rotated} old_binding=({old_fp[:12]}…,{old_relay[:12]}…) "
        f"new_binding=({binding.outbound_request_fingerprint[:12]}…,{binding.relay_id[:12]}…) "
        f"nonce_reused={row2[2] == old_nonce} consumed_after={row2[3]} "
        f"stale_signed_new={stale_signed_new} "
        f"result_response={result.runtime.response!r} problems={problems}"
    )
    return ("S1-STALE-CAPABILITY-001", detail, not problems)


def s2_schema_upgrade(root: Path) -> tuple[str, str, bool]:
    pre = root / "pre.db"
    baseline_src = "/tmp/w14_baseline_wt/src"
    script = f'''
import sys
sys.path.insert(0, r"{baseline_src}")
from datetime import datetime, timezone
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.runtime.background_attempt import BackgroundModelAttemptStore
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.contracts.enums import SourceClass
NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
store = SQLiteWorldStore(r"{pre}")
anchor = Observation(object_id="hist_anchor", subject_id="user_1",
    occurred=TemporalExtent.point(NOW), learned_at=NOW, recorded_at=NOW,
    created_by="t", source_kind="conversation", modality="text", value="v",
    metadata={{"dimension": "dim:x"}})
store.commit([anchor], OperationRequest(operation_name="seed", expected_world_revision=0,
    reason="seed", idempotency_key="seed-hist", source_class=SourceClass.USER))
attempts = BackgroundModelAttemptStore(store)
a = attempts.admit(subject_id="user_1", work_kind="wake", work_id="hist-wake",
    wake_reason="safety", model_round_index=0, world_revision=0, admitted_at=NOW)
attempts.mark_dispatching(a.attempt_id, dispatched_at=NOW,
    outbound_request_fingerprint="historical-outbound")
try:
    attempts.admit(subject_id="user_1", work_kind="wake", work_id="hist-wake",
        wake_reason="safety", model_round_index=0, world_revision=0,
        admitted_at=NOW)
except Exception:
    pass
print("BASELINE_STATE", attempts.get(a.attempt_id).state)
print("BASELINE_REV", int(store.current_world_revision()))
print("BASELINE_ATTEMPT", a.attempt_id)
'''
    out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    if out.returncode != 0:
        return ("S2-SCHEMA-001", f"baseline phase failed: {out.stderr[-800:]}", False)
    lines = dict(
        line.split(maxsplit=1) for line in out.stdout.splitlines() if line.startswith("BASELINE_")
    )
    baseline_state = lines["BASELINE_STATE"]
    baseline_rev = int(lines["BASELINE_REV"])
    baseline_attempt = lines["BASELINE_ATTEMPT"]

    # Candidate runtime opens the same file and runs every migration.
    store = SQLiteWorldStore(pre)
    from aios_core.runtime.background_attempt import BackgroundModelAttemptStore
    BackgroundModelAttemptStore(store)
    index = WorldSearchIndex(pre, store=store)
    index.rebuild()
    runtime = FusedTurnRuntime(
        store=store, index=index,
        model_handler=lambda _s: (_ for _ in ()).throw(AssertionError("no dispatch on historical work")))
    hist = runtime.background_model_attempts.inspect(
        subject_id="user_1", work_kind="wake", work_id="hist-wake", model_round_index=0)
    with sqlite3.connect(pre) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        cap_rows = 0
        if "background_model_return_capabilities" in tables:
            cap_rows = conn.execute(
                "SELECT COUNT(*) FROM background_model_return_capabilities").fetchone()[0]
        state_now = conn.execute(
            "SELECT state FROM background_model_attempts WHERE attempt_id=?",
            (baseline_attempt,)).fetchone()[0]
    rev_now = int(store.current_world_revision())
    problems = []
    if "background_model_return_capabilities" not in tables:
        problems.append("capability table missing after upgrade")
    if cap_rows != 0:
        problems.append(f"capability minted for historical attempts: {cap_rows} rows")
    if state_now != baseline_state or state_now != "in_doubt":
        problems.append(f"historical state changed: {baseline_state} -> {state_now}")
    if rev_now != baseline_rev:
        problems.append(f"world revision changed: {baseline_rev} -> {rev_now}")
    if hist is None or hist.attempt_id != baseline_attempt:
        problems.append("historical attempt identity not preserved")
    detail = (
        f"baseline_state={baseline_state} state_now={state_now} "
        f"rev={baseline_rev}->{rev_now} cap_rows={cap_rows} "
        f"attempt_preserved={hist is not None and hist.attempt_id == baseline_attempt} "
        f"problems={problems}"
    )
    return ("S2-SCHEMA-001", detail, not problems)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="w14-supp-") as directory:
        results = [s1_stale_capability_across_retry(Path(directory)),
                   s2_schema_upgrade(Path(directory))]
    failures = 0
    for probe_id, detail, passed in results:
        print(("PASS" if passed else "FAIL") + f" | {probe_id}")
        print("  actual: " + detail)
        failures += 0 if passed else 1
    print(f"SUMMARY | probes={len(results)} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
