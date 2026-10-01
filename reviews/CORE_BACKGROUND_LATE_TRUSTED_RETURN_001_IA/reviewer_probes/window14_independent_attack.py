#!/usr/bin/env python3
"""WINDOW 14 independently frozen adversarial probes for PR #305.

This script was written before its first execution against candidate
5ad0524c425592210ff184e00ad52abb2c14e366.  Each probe has a fixed expected
security outcome.  It deliberately uses only ordinary Python object references
available to a recovery process (the public attempt store and public SQLite
store path); it does not monkeypatch Core or mutate source/database rows.

A non-zero exit means at least one mandatory acceptance invariant was violated.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import multiprocessing
import os
from pathlib import Path
import signal
import sqlite3
import sys
import tempfile
import threading
from typing import Callable

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    BackgroundModelAttemptBlocked,
    BackgroundModelExecutionInDoubt,
    ModelCallProvenance,
    ModelDirective,
    ModelDispatchNotSubmitted,
    ModelUsage,
    TurnAlreadyCompleted,
)
from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptStore,
    BackgroundModelResponseConflict,
    decode_model_directive,
    encode_model_directive,
    response_fingerprint,
)
from aios_core.runtime.late_return import late_return_proof
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class ProbeResult:
    probe_id: str
    expected: str
    actual: str
    passed: bool


def directive(
    *,
    response: str = "reviewer-controlled bytes",
    usage_provider: str = "provider-A",
    usage_model: str = "model-A",
    usage_request: str = "request-A",
    provenance_provider: str | None = None,
    provenance_model: str | None = None,
    provenance_request: str | None = None,
) -> ModelDirective:
    """Build a fully identified response, optionally with conflicting identity."""

    return ModelDirective(
        response=response,
        capability_calls=(),
        usage=ModelUsage(
            input_tokens=3,
            output_tokens=2,
            total_tokens=5,
            provider=usage_provider,
            model=usage_model,
            request_id=usage_request,
        ),
        provenance=ModelCallProvenance(
            provider=provenance_provider or usage_provider,
            model=provenance_model or usage_model,
            request_id=provenance_request or usage_request,
        ),
    )


def make_crossed_attempt(db: Path, *, work_id: str) -> tuple[SQLiteWorldStore, BackgroundModelAttemptStore, object]:
    """Create a genuine durable post-dispatch attempt without test-only SQL."""

    store = SQLiteWorldStore(db)
    attempts = BackgroundModelAttemptStore(store)
    attempt = attempts.admit(
        subject_id="user_1",
        work_kind="user_turn",
        work_id=work_id,
        wake_reason="user_interaction",
        model_round_index=0,
        world_revision=int(store.current_world_revision()),
        admitted_at=NOW,
    )
    attempt = attempts.mark_dispatching(
        attempt.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint=f"reviewer-outbound-{work_id}",
    )
    assert attempt.state == "dispatching"
    return store, attempts, attempt


def reopen_as_recovery(db: Path, attempt: object) -> tuple[SQLiteWorldStore, BackgroundModelAttemptStore]:
    """Fresh process equivalent: reopen DB and force restart admission to in_doubt."""

    store = SQLiteWorldStore(db)
    attempts = BackgroundModelAttemptStore(store)
    try:
        attempts.admit(
            subject_id=attempt.subject_id,
            work_kind=attempt.work_kind,
            work_id=attempt.work_id,
            wake_reason=attempt.wake_reason,
            model_round_index=attempt.model_round_index,
            world_revision=int(store.current_world_revision()),
            admitted_at=NOW + timedelta(minutes=1),
        )
    except BackgroundModelExecutionInDoubt:
        pass
    state = attempts.get(attempt.attempt_id)
    assert state is not None and state.state == "in_doubt"
    return store, attempts


def is_safe_refusal(exc: BaseException) -> bool:
    return isinstance(
        exc,
        (
            AttributeError,
            BackgroundModelAttemptBlocked,
            BackgroundModelResponseConflict,
            PermissionError,
            RuntimeError,
            ValueError,
        ),
    )


def probe_oracle_reissue(root: Path) -> ProbeResult:
    """An ordinary fresh recovery object must not reacquire proof authority."""

    db = root / "oracle-reissue.db"
    _, initial, attempt = make_crossed_attempt(db, work_id="oracle-reissue")
    _, recovery = reopen_as_recovery(db, attempt)
    forged = directive(response="attacker bytes accepted after restart")
    try:
        # No observer is registered in this recovery process.  The underscore is
        # intentionally called through the normal public runtime/store object
        # graph because Python naming convention is not an access-control boundary.
        capability = recovery._issue_external_return_capability(
            attempt.attempt_id, issued_at=NOW + timedelta(minutes=2)
        )
        proof = capability.prove_external_return(forged)
        staged = recovery.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(minutes=3),
            directive_payload=encode_model_directive(forged),
            late_return_proof=proof,
            evidence="reviewer normal-object-graph oracle attack",
        )
    except BaseException as exc:  # a refusal is the required result
        if is_safe_refusal(exc):
            return ProbeResult(
                "IA14-ORACLE-001",
                "fresh ordinary recovery cannot reissue/retrieve capability or attach arbitrary bytes",
                f"refused: {type(exc).__name__}: {exc}",
                True,
            )
        raise
    return ProbeResult(
        "IA14-ORACLE-001",
        "fresh ordinary recovery cannot reissue/retrieve capability or attach arbitrary bytes",
        f"CAPABILITY REISSUED and arbitrary bytes staged for {staged.attempt_id}",
        False,
    )


def probe_nonce_path_exfiltration(root: Path) -> ProbeResult:
    """A recovery caller with the public store object must not recover the nonce."""

    db = root / "nonce-path.db"
    _, initial, attempt = make_crossed_attempt(db, work_id="nonce-path")
    # This line simulates normal dispatch-time issuance to the trusted observer.
    initial._issue_external_return_capability(attempt.attempt_id, issued_at=NOW)
    recovery_store, recovery = reopen_as_recovery(db, attempt)
    forged = directive(response="bytes signed from public db_path")
    binding = recovery.outbound_request_binding(attempt.attempt_id)
    assert binding is not None
    try:
        # SQLiteWorldStore.db_path is a public attribute.  This is not reflection,
        # monkeypatching, or a direct SQL mutation; it is a read-only normal file
        # open from an ordinary recovery object.
        with sqlite3.connect(recovery_store.db_path) as conn:
            row = conn.execute(
                "SELECT capability_nonce FROM background_model_return_capabilities WHERE attempt_id=?",
                (attempt.attempt_id,),
            ).fetchone()
        assert row is not None
        nonce = bytes.fromhex(str(row[0]))
        payload = encode_model_directive(forged)
        proof = late_return_proof(
            nonce,
            attempt_id=binding.attempt_id,
            subject_id=binding.subject_id,
            work_kind=binding.work_kind,
            work_id=binding.work_id,
            model_round_index=binding.model_round_index,
            outbound_request_fingerprint=binding.outbound_request_fingerprint,
            relay_id=binding.relay_id,
            provider="provider-A",
            model="model-A",
            provider_request_id="request-A",
            response_fingerprint=response_fingerprint(forged),
            payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        )
        staged = recovery.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(minutes=3),
            directive_payload=payload,
            late_return_proof=proof,
            evidence="reviewer db-path nonce-read attack",
        )
    except BaseException as exc:
        if is_safe_refusal(exc):
            return ProbeResult(
                "IA14-NONCE-001",
                "ordinary recovery object cannot read capability nonce or turn it into trusted bytes",
                f"refused: {type(exc).__name__}: {exc}",
                True,
            )
        raise
    return ProbeResult(
        "IA14-NONCE-001",
        "ordinary recovery object cannot read capability nonce or turn it into trusted bytes",
        f"public db_path exposed nonce and arbitrary bytes staged for {staged.attempt_id}",
        False,
    )


def probe_conflicting_provider_identity(root: Path) -> ProbeResult:
    """Conflicting provenance/usage identities must be refused, never overridden."""

    db = root / "identity-conflict.db"
    _, attempts, attempt = make_crossed_attempt(db, work_id="identity-conflict")
    capability = attempts._issue_external_return_capability(attempt.attempt_id, issued_at=NOW)
    try:
        conflicted = directive(
            response="identity conflict must not be canonicalized",
            usage_provider="usage-provider",
            usage_model="usage-model",
            usage_request="usage-request",
            provenance_provider="provenance-provider",
            provenance_model="provenance-model",
            provenance_request="provenance-request",
        )
    except ValueError as exc:
        # Construction is the earliest valid refusal point.  It is stronger than
        # waiting for proof/attach and is the required outcome for this probe.
        return ProbeResult(
            "IA14-ID-001",
            "conflicting provenance/usage provider, model, request_id are rejected",
            f"refused during directive construction: {type(exc).__name__}: {exc}",
            True,
        )
    try:
        # This branch should be unreachable.  Retain it so that if a future
        # constructor weakens, the attack continues through the late-return path
        # rather than silently becoming a passing test.
        proof = capability.prove_external_return(conflicted)
        staged = attempts.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(minutes=1),
            directive_payload=encode_model_directive(conflicted),
            late_return_proof=proof,
            evidence="reviewer provenance-vs-usage conflict attack",
        )
    except BaseException as exc:
        if is_safe_refusal(exc):
            return ProbeResult(
                "IA14-ID-001",
                "conflicting provenance/usage provider, model, request_id are rejected",
                f"refused: {type(exc).__name__}: {exc}",
                True,
            )
        raise
    return ProbeResult(
        "IA14-ID-001",
        "conflicting provenance/usage provider, model, request_id are rejected",
        f"conflicting directive silently accepted and staged for {staged.attempt_id}",
        False,
    )


def probe_postdispatch_not_submitted(root: Path) -> ProbeResult:
    """Every write site must refuse false not_submitted after durable binding."""

    db = root / "postdispatch-not-submitted.db"
    _, attempts, attempt = make_crossed_attempt(db, work_id="postdispatch-not-submitted")
    try:
        result = attempts.mark_failure(
            attempt.attempt_id,
            failed_at=NOW + timedelta(minutes=1),
            definitely_not_submitted=True,
            error=ModelDispatchNotSubmitted("claimed pre-write after a durable dispatch binding"),
        )
    except BaseException as exc:
        if is_safe_refusal(exc):
            state = attempts.get(attempt.attempt_id)
            return ProbeResult(
                "IA14-NS-001",
                "post-dispatch typed failure cannot write not_submitted",
                f"refused: {type(exc).__name__}; durable state={state.state if state else None}",
                True,
            )
        raise
    return ProbeResult(
        "IA14-NS-001",
        "post-dispatch typed failure cannot write not_submitted",
        f"mark_failure accepted caller boolean and wrote state={result.state}",
        False,
    )


def probe_duplicate_json_rejection() -> ProbeResult:
    """A positive parser-differential check retained as a control probe."""

    payload = (
        '{"capability_calls":[],"response":"x","silence":false,'
        '"usage":{"total_tokens":1,"input_tokens":null,"output_tokens":null,'
        '"provider":"first","provider":"second","model":"m","request_id":"r"},'
        '"provenance":{"provider":"p","model":"m","request_id":"r"}}'
    )
    try:
        decode_model_directive(payload)
    except ValueError as exc:
        return ProbeResult(
            "IA14-JSON-001",
            "duplicate nested JSON keys fail before directive construction",
            f"refused: {type(exc).__name__}: {exc}",
            True,
        )
    return ProbeResult(
        "IA14-JSON-001",
        "duplicate nested JSON keys fail before directive construction",
        "duplicate provider key was accepted",
        False,
    )


def probe_concurrent_conflict(root: Path) -> ProbeResult:
    """Two different proofs racing one capability must yield one canonical return."""

    db = root / "concurrent-conflict.db"
    _, attempts, attempt = make_crossed_attempt(db, work_id="concurrent-conflict")
    capability = attempts._issue_external_return_capability(attempt.attempt_id, issued_at=NOW)
    left = directive(response="race-left", usage_request="race-left")
    right = directive(response="race-right", usage_request="race-right")
    work: list[tuple[str, str]] = []
    lock = threading.Lock()
    barrier = threading.Barrier(2)

    def attach(label: str, item: ModelDirective) -> None:
        local = BackgroundModelAttemptStore(SQLiteWorldStore(db))
        proof = capability.prove_external_return(item)
        barrier.wait(timeout=10)
        try:
            local.attach_late_trusted_return(
                attempt.attempt_id,
                attached_at=NOW + timedelta(minutes=2),
                directive_payload=encode_model_directive(item),
                late_return_proof=proof,
                evidence=f"reviewer concurrent proof {label}",
            )
        except BackgroundModelResponseConflict:
            outcome = "refused"
        else:
            outcome = "accepted"
        with lock:
            work.append((label, outcome))

    threads = [
        threading.Thread(target=attach, args=("left", left), daemon=True),
        threading.Thread(target=attach, args=("right", right), daemon=True),
    ]
    for worker in threads:
        worker.start()
    for worker in threads:
        worker.join(timeout=30)
    if any(worker.is_alive() for worker in threads):
        return ProbeResult(
            "IA14-RACE-001",
            "one canonical response; conflicting proof fails closed without deadlock",
            "thread did not complete",
            False,
        )
    accepted = [label for label, outcome in work if outcome == "accepted"]
    staged = attempts.staged_response(attempt.attempt_id)
    passed = len(accepted) == 1 and len(work) == 2 and staged is not None
    return ProbeResult(
        "IA14-RACE-001",
        "one canonical response; conflicting proof fails closed without deadlock",
        f"outcomes={sorted(work)}; staged={staged.directive_payload if staged else None!r}",
        passed,
    )


def _sigkill_child(db: str, conn: object) -> None:
    """Dispatch through the real turn runtime, hand capability outside, then die."""

    class PipeObserver:
        def accept_return_capability(self, snapshot: object, capability: object) -> None:
            conn.send((capability.attempt_id, capability))
            conn.close()

    def kill_at_provider_boundary(snapshot: object) -> ModelDirective:
        del snapshot
        os.kill(os.getpid(), signal.SIGKILL)
        raise AssertionError("SIGKILL should not return")

    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=kill_at_provider_boundary,
        external_return_observer=PipeObserver(),
    )
    runtime.run_turn(
        session_id="w14-sigkill-session",
        turn_index=1,
        user_input="resume one late trusted response exactly once",
        occurred_at=NOW,
        current_topic=None,
    )


def probe_real_sigkill_recovery(root: Path) -> ProbeResult:
    """Reviewer-owned actual SIGKILL + surviving observer + fresh Core recovery."""

    db = root / "real-sigkill.db"
    SQLiteWorldStore(db)
    context = multiprocessing.get_context("fork")
    parent_conn, child_conn = context.Pipe(duplex=False)
    child = context.Process(target=_sigkill_child, args=(str(db), child_conn))
    child.start()
    child.join(60)
    if child.exitcode != -signal.SIGKILL:
        return ProbeResult(
            "IA14-SIGKILL-001",
            "real process loss can attach exactly one observed return without redispatch",
            f"child exit={child.exitcode}, expected={-signal.SIGKILL}",
            False,
        )
    if not parent_conn.poll(30):
        return ProbeResult(
            "IA14-SIGKILL-001",
            "real process loss can attach exactly one observed return without redispatch",
            "surviving observer did not receive a capability before death",
            False,
        )
    attempt_id, capability = parent_conn.recv()
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    calls: list[int] = []

    def no_redispatch(snapshot: object) -> ModelDirective:
        calls.append(getattr(snapshot, "round_index", -1))
        raise AssertionError("provider was redispatched during late-return recovery")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=no_redispatch)
    attempt = runtime.background_model_attempts.get(attempt_id)
    if attempt is None or attempt.state != "dispatching":
        return ProbeResult(
            "IA14-SIGKILL-001",
            "real process loss can attach exactly one observed return without redispatch",
            f"unexpected post-death attempt state={attempt.state if attempt else None}",
            False,
        )
    exact = directive(response="reviewer SIGKILL response", usage_request="sigkill-request")
    proof = capability.prove_external_return(exact)
    try:
        runtime.background_model_attempts.attach_late_trusted_return(
            attempt_id,
            attached_at=NOW + timedelta(minutes=5),
            directive_payload=encode_model_directive(exact),
            late_return_proof=proof,
            evidence="reviewer surviving observer after SIGKILL",
        )
        result = runtime.run_turn(
            session_id="w14-sigkill-session",
            turn_index=1,
            user_input="resume one late trusted response exactly once",
            occurred_at=NOW,
            current_topic=None,
        )
        inspection = runtime.inspect_turn_execution(
            session_id="w14-sigkill-session",
            turn_index=1,
            user_input="resume one late trusted response exactly once",
            occurred_at=NOW,
        )
        meters = list(runtime.metering.list_model_calls(subject_id="user_1"))
        # A second invocation is the terminal-receipt short circuit. The Core
        # contract may return the completed result or raise TurnAlreadyCompleted;
        # either is safe, provided no model/meter work is repeated.
        try:
            terminal = runtime.run_turn(
                session_id="w14-sigkill-session",
                turn_index=1,
                user_input="resume one late trusted response exactly once",
                occurred_at=NOW,
                current_topic=None,
            )
            terminal_outcome = f"result:{terminal.runtime.response!r}"
            terminal_safe = terminal.runtime.response == "reviewer SIGKILL response"
        except TurnAlreadyCompleted as exc:
            terminal_outcome = f"TurnAlreadyCompleted:{exc}"
            terminal_safe = True
    except BaseException as exc:
        return ProbeResult(
            "IA14-SIGKILL-001",
            "real process loss can attach exactly one observed return without redispatch",
            f"recovery raised {type(exc).__name__}: {exc}",
            False,
        )
    passed = (
        result.runtime.response == "reviewer SIGKILL response"
        and terminal_safe
        and calls == []
        and len(meters) == 1
        and inspection.state == "completed"
        and inspection.assistant_ref is not None
        and len(inspection.model_attempts) == 1
        and inspection.model_attempts[0].state == "metered"
    )
    return ProbeResult(
        "IA14-SIGKILL-001",
        "real process loss can attach exactly one observed return without redispatch",
        (
            f"response={result.runtime.response!r}; terminal={terminal_outcome}; "
            f"provider_calls={calls}; meters={len(meters)}; state={inspection.state}; "
            f"assistant_ref={inspection.assistant_ref}; attempts={[x.state for x in inspection.model_attempts]}"
        ),
        passed,
    )


def run_all(root: Path) -> list[ProbeResult]:
    return [
        probe_oracle_reissue(root),
        probe_nonce_path_exfiltration(root),
        probe_conflicting_provider_identity(root),
        probe_postdispatch_not_submitted(root),
        probe_duplicate_json_rejection(),
        probe_concurrent_conflict(root),
        probe_real_sigkill_recovery(root),
    ]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="window14-independent-") as directory:
        results = run_all(Path(directory))
    for result in results:
        verdict = "PASS" if result.passed else "FAIL"
        print(f"{verdict} | {result.probe_id}")
        print(f"  expected: {result.expected}")
        print(f"  actual:   {result.actual}")
    failures = [result for result in results if not result.passed]
    print(f"SUMMARY | probes={len(results)} failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
