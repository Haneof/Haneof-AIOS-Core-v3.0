"""CORE-BACKGROUND-LATE-TRUSTED-RETURN-001 — frozen ``not_submitted`` probes.

Frozen semantics (WINDOW 13):

    ``not_submitted`` means exactly one thing — Core holds mechanical,
    trustworthy evidence that this attempt never crossed the semantic/provider
    dispatch boundary.

It never means "we do not know, so write not_submitted to unblock a retry".
Absence of a trusted return receipt is **not** proof of non-submission.

RED-first: frozen, hashed and executed against exact current ``main`` before any
production change.
"""
from __future__ import annotations

from datetime import timedelta
import sqlite3

import pytest

from aios_core.runtime import (
    BackgroundModelExecutionInDoubt,
    ModelCallProvenance,
    ModelDirective,
    ModelDispatchNotSubmitted,
    ModelUsage,
    TurnExecutionInDoubt,
)
from aios_core.runtime.background_attempt import BackgroundModelResponseConflict
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from late_trusted_return_fixture import (
    NOW,
    ProcessDeath,
    SyntheticExternalResponder,
    dispatch_then_die,
    meters,
    seed_anchor,
    trusted_directive,
    world,
)
from aios_core.runtime.background_attempt import encode_model_directive

SESSION = "not-submitted-session"
TURN_INDEX = 1
TURN_INPUT = "resolve the not-submitted semantics exactly once"
REQUEST_ID = "not-submitted-provider-request"


def new_runtime(db, *, handler, observer=None):
    store, index = world(db)
    kwargs = {}
    if observer is not None:
        # Registered observers are only relevant to the late-return path; the
        # not_submitted probes below stay runnable on unchanged baseline main.
        kwargs["external_return_observer"] = observer
    return FusedTurnRuntime(store=store, index=index, model_handler=handler, **kwargs)


def admit(store, *, work_id, work_kind="wake", round_index=0, subject_id="user_1"):
    runtime_attempts = store_attempts(store)
    return runtime_attempts.admit(
        subject_id=subject_id,
        work_kind=work_kind,
        work_id=work_id,
        wake_reason="safety",
        model_round_index=round_index,
        world_revision=int(store.current_world_revision()),
        admitted_at=NOW,
    )


def store_attempts(store):
    from aios_core.runtime.background_attempt import BackgroundModelAttemptStore

    return BackgroundModelAttemptStore(store)


def force_in_doubt(runtime, attempt):
    """Frozen step 7-8: restart admission converts dispatching -> in_doubt and raises."""

    with pytest.raises(BackgroundModelExecutionInDoubt) as blocked:
        runtime.background_model_attempts.admit(
            subject_id=attempt.subject_id,
            work_kind=attempt.work_kind,
            work_id=attempt.work_id,
            wake_reason=attempt.wake_reason,
            model_round_index=attempt.model_round_index,
            world_revision=int(runtime.store.current_world_revision()),
            admitted_at=NOW + timedelta(minutes=1),
        )
    assert blocked.value.attempt.state == "in_doubt"
    return blocked.value.attempt


def state_of(db, attempt_id) -> str:
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT state FROM background_model_attempts WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()
    assert row is not None
    return str(row[0])


# ---------------------------------------------------------------------------
# NS-R1 — a pre-dispatch attempt that Core mechanically knows was not submitted
#         may still be reconciled, and may still retry legally.
# ---------------------------------------------------------------------------


def test_ns_r1_pre_dispatch_admitted_attempt_may_be_reconciled_and_retried(tmp_path):
    db = tmp_path / "world.db"
    SQLiteWorldStore(db)
    from aios_core.runtime.background_attempt import BackgroundModelAttemptStore

    store = SQLiteWorldStore(db)
    attempts = BackgroundModelAttemptStore(store)
    attempt = attempts.admit(
        subject_id="user_1",
        work_kind="wake",
        work_id="pre-dispatch-wake",
        wake_reason="safety",
        model_round_index=0,
        world_revision=int(store.current_world_revision()),
        admitted_at=NOW,
    )
    assert attempt.state == "admitted"
    # No dispatch boundary was crossed, so no request binding exists at all.
    assert attempts.outbound_request_binding(attempt.attempt_id) is None

    reconciled = attempts.reconcile_not_submitted(
        attempt.attempt_id,
        reconciled_at=NOW,
        evidence="admission failed before any outbound request was published",
    )
    assert reconciled.state == "not_submitted"
    assert reconciled.recovery_disposition == "safe_to_retry"

    # A not_submitted attempt legally re-admits and dispatches once.
    readmitted = attempts.admit(
        subject_id="user_1",
        work_kind="wake",
        work_id="pre-dispatch-wake",
        wake_reason="safety",
        model_round_index=0,
        world_revision=int(store.current_world_revision()),
        admitted_at=NOW + timedelta(minutes=1),
    )
    assert readmitted.state == "admitted"
    dispatched = attempts.mark_dispatching(
        readmitted.attempt_id,
        dispatched_at=NOW + timedelta(minutes=1),
        outbound_request_fingerprint="pre-dispatch-outbound-request",
    )
    assert dispatched.state == "dispatching"
    # ... and after that crossing the same reconciliation is permanently refused.
    with pytest.raises(BackgroundModelResponseConflict):
        attempts.reconcile_not_submitted(
            readmitted.attempt_id,
            reconciled_at=NOW + timedelta(minutes=2),
            evidence="the request really was published this time",
        )
    assert state_of(db, readmitted.attempt_id) == "dispatching"


def test_ns_r1_in_process_definitely_not_submitted_dispatch_failure_still_retries(tmp_path):
    """The accepted in-process typed contract keeps its meaning and its retry."""

    db = tmp_path / "world.db"
    from aios_core.contracts.enums import WakeSource
    from aios_core.contracts.refs import ObjectRef
    from aios_core.wake import WakeSignalRequest

    def not_submitted(_snapshot):
        raise ModelDispatchNotSubmitted("socket failed before the request write")

    runtime = new_runtime(db, handler=not_submitted)
    signal = runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id="ns-r1.typed",
            observed_at=NOW,
            dedupe_key="ns-r1.typed:one",
        )
    )
    with pytest.raises(ModelDispatchNotSubmitted):
        runtime.run_wake(wake_ref=ObjectRef(object_id=signal.wake_id, revision=1), now=NOW)
    attempt = runtime.background_model_attempts.inspect(
        subject_id="user_1", work_kind="wake", work_id=signal.wake_id, model_round_index=0
    )
    assert attempt is not None
    assert attempt.state == "not_submitted"
    assert attempt.recovery_disposition == "safe_to_retry"


# ---------------------------------------------------------------------------
# NS-R2 — once the dispatch boundary is crossed, reconcile_not_submitted must be
#         mechanically refused.
# ---------------------------------------------------------------------------


def _crossed_then_dead(db, *, observer=None, key):
    runtime = new_runtime(db, handler=dispatch_then_die, observer=observer)
    seed_anchor(runtime.store, key=key)
    runtime.index.catch_up()
    with pytest.raises(ProcessDeath):
        runtime.run_turn(
            session_id=SESSION, turn_index=TURN_INDEX, user_input=TURN_INPUT, occurred_at=NOW
        )
    execution_id = runtime.turn_executions.execution_id_for(
        subject_id="user_1", session_id=SESSION, turn_index=TURN_INDEX
    )
    attempt = runtime.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind="user_turn", work_id=execution_id
    )[-1]
    return runtime, attempt


@pytest.mark.parametrize("state_before", ["dispatching", "in_doubt"])
def test_ns_r2_post_dispatch_reconcile_not_submitted_is_mechanically_refused(
    tmp_path, state_before
):
    db = tmp_path / f"world-{state_before}.db"
    runtime, attempt = _crossed_then_dead(db, key=f"ns-r2-{state_before}")
    attempts = runtime.background_model_attempts

    if state_before == "in_doubt":
        force_in_doubt(runtime, attempt)
    assert attempts.get(attempt.attempt_id).state == state_before

    with pytest.raises(BackgroundModelResponseConflict) as refused:
        attempts.reconcile_not_submitted(
            attempt.attempt_id,
            reconciled_at=NOW + timedelta(minutes=5),
            evidence=(
                "the operator believes the provider never received the request"
            ),
        )
    assert "dispatch" in str(refused.value).lower()
    assert attempts.get(attempt.attempt_id).state == state_before
    assert state_of(db, attempt.attempt_id) == state_before
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT reconciliation_evidence FROM background_model_attempts "
            "WHERE attempt_id=?",
            (attempt.attempt_id,),
        ).fetchone()
    assert row[0] is None, "no false reconciliation evidence may ever be persisted"
    assert meters(runtime) == []


def test_ns_r2_false_state_cannot_be_written_even_with_a_verbose_justification(tmp_path):
    db = tmp_path / "world.db"
    runtime, attempt = _crossed_then_dead(db, key="ns-r2-justified")
    attempts = runtime.background_model_attempts
    for evidence in (
        "probably not submitted",
        "the request may not have been delivered",
        "we timed out, so assume nothing happened",
        "operator says the provider never saw it",
        "recovery needs to continue",
        "x" * 4000,
    ):
        with pytest.raises(BackgroundModelResponseConflict):
            attempts.reconcile_not_submitted(
                attempt.attempt_id,
                reconciled_at=NOW + timedelta(minutes=5),
                evidence=evidence,
            )
        assert attempts.get(attempt.attempt_id).state == "dispatching"


# ---------------------------------------------------------------------------
# NS-R3 / NS-R4 — "in_doubt + no receipt" is not proof of non-submission, and
#                the uncertain state must fail closed.
# ---------------------------------------------------------------------------


def test_ns_r3_missing_receipt_alone_never_justifies_not_submitted(tmp_path):
    db = tmp_path / "world.db"
    runtime, attempt = _crossed_then_dead(db, key="ns-r3")
    attempts = runtime.background_model_attempts
    assert attempts.response_authenticity_receipt(attempt.attempt_id) is None
    assert attempts.staged_response(attempt.attempt_id) is None
    with pytest.raises(BackgroundModelResponseConflict):
        attempts.reconcile_not_submitted(
            attempt.attempt_id,
            reconciled_at=NOW,
            evidence="there is no trusted return receipt, therefore it was not submitted",
        )
    assert attempts.get(attempt.attempt_id).state == "dispatching"


def test_ns_r4_uncertain_dispatch_fails_closed_instead_of_recovering(tmp_path):
    db = tmp_path / "world.db"
    runtime, attempt = _crossed_then_dead(db, key="ns-r4")
    fresh = new_runtime(db, handler=lambda _s: pytest.fail("no redispatch"))
    for _ in range(3):
        with pytest.raises(TurnExecutionInDoubt):
            fresh.run_turn(
                session_id=SESSION, turn_index=TURN_INDEX, user_input=TURN_INPUT, occurred_at=NOW
            )
        force_in_doubt(fresh, attempt)
        assert fresh.background_model_attempts.get(attempt.attempt_id).state == "in_doubt"
    assert meters(fresh) == []
    assert fresh.background_model_attempts.staged_response(attempt.attempt_id) is None


# ---------------------------------------------------------------------------
# NS-R5 — a caller-forged non-submission assertion fails closed.
# ---------------------------------------------------------------------------


def test_ns_r5_caller_forged_non_submission_assertion_fails_closed(tmp_path):
    db = tmp_path / "world.db"
    runtime, attempt = _crossed_then_dead(db, key="ns-r5")
    attempts = runtime.background_model_attempts
    for bad_evidence in (None, "", "   ", 42, [], {}):
        with pytest.raises((ValueError, BackgroundModelResponseConflict)):
            attempts.reconcile_not_submitted(
                attempt.attempt_id,
                reconciled_at=NOW,
                evidence=bad_evidence,
            )
        assert attempts.get(attempt.attempt_id).state == "dispatching"
    # Even a receipt-looking identifier is not a non-dispatch proof.
    with pytest.raises(BackgroundModelResponseConflict):
        attempts.reconcile_not_submitted(
            attempt.attempt_id,
            reconciled_at=NOW,
            evidence="bglate_v1_" + "0" * 64,
        )
    assert attempts.get(attempt.attempt_id).state == "dispatching"


def test_ns_r5_runtime_level_turn_reconciliation_is_refused_after_dispatch(tmp_path):
    db = tmp_path / "world.db"
    runtime, attempt = _crossed_then_dead(db, key="ns-r5-runtime")
    with pytest.raises(BackgroundModelResponseConflict):
        runtime.reconcile_turn_model_not_submitted(
            session_id=SESSION,
            turn_index=TURN_INDEX,
            user_input=TURN_INPUT,
            occurred_at=NOW,
            model_round_index=0,
            reconciled_at=NOW + timedelta(minutes=5),
            evidence="the public runtime surface must refuse the same transition",
        )
    assert runtime.background_model_attempts.get(attempt.attempt_id).state == "dispatching"


# ---------------------------------------------------------------------------
# NS-R6 — with a legitimate late return proof, the attempt must take the
#         late-return attach path and never the not_submitted path.
# ---------------------------------------------------------------------------


def test_ns_r6_legitimate_late_return_proof_uses_attach_not_reconciliation(tmp_path):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime, attempt = _crossed_then_dead(db, observer=responder, key="ns-r6")
    fresh = new_runtime(db, handler=lambda _s: pytest.fail("no redispatch"))
    force_in_doubt(fresh, attempt)

    exact = trusted_directive(REQUEST_ID)
    proof = responder.finish_after_core_death(attempt.attempt_id, exact)
    with pytest.raises(BackgroundModelResponseConflict):
        # The false-state shortcut stays refused even when a genuine proof exists.
        fresh.background_model_attempts.reconcile_not_submitted(
            attempt.attempt_id,
            reconciled_at=NOW + timedelta(minutes=5),
            evidence="a genuine late return exists, but this is still not_submitted",
        )
    fresh.background_model_attempts.attach_late_trusted_return(
        attempt.attempt_id,
        attached_at=NOW + timedelta(minutes=6),
        directive_payload=encode_model_directive(exact),
        late_return_proof=proof,
        evidence="legitimate late trusted return",
    )
    assert fresh.background_model_attempts.get(attempt.attempt_id).state == "response_returned"
    result = fresh.run_turn(
        session_id=SESSION, turn_index=TURN_INDEX, user_input=TURN_INPUT, occurred_at=NOW
    )
    assert result.runtime.response == "late return applied exactly once"
    assert len(meters(fresh)) == 1


# ---------------------------------------------------------------------------
# the accepted invariants that must survive this change
# ---------------------------------------------------------------------------


def test_ns_r7_receipt_absence_guard_still_protects_a_real_authenticated_return(tmp_path):
    """The original receipt-absence guard is kept; it is merely no longer alone."""

    from aios_core.runtime.background_attempt import BackgroundModelAttemptStore

    store = SQLiteWorldStore(tmp_path / "world.db")
    attempts = BackgroundModelAttemptStore(store)
    attempt = attempts.admit(
        subject_id="user_1",
        work_kind="wake",
        work_id="receipt-guarded",
        wake_reason="safety",
        model_round_index=0,
        world_revision=int(store.current_world_revision()),
        admitted_at=NOW,
    )
    attempts.mark_dispatching(
        attempt.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint="receipt-guarded-request",
    )
    exact = trusted_directive(REQUEST_ID)
    receipt = attempts._capture_trusted_response_return(
        attempt.attempt_id, captured_at=NOW, directive=exact
    )
    with pytest.raises(BackgroundModelResponseConflict) as refused:
        attempts.reconcile_not_submitted(
            attempt.attempt_id,
            reconciled_at=NOW,
            evidence="there is a real trusted return receipt",
        )
    assert "not submitted" in str(refused.value).lower()
    assert receipt.payload_sha256 is not None
    assert attempts.get(attempt.attempt_id).state == "dispatching"


def test_ns_r7_metadata_only_reconciliation_stays_disabled(tmp_path):
    from aios_core.runtime.background_attempt import BackgroundModelAttemptStore

    store = SQLiteWorldStore(tmp_path / "world.db")
    attempts = BackgroundModelAttemptStore(store)
    attempt = attempts.admit(
        subject_id="user_1",
        work_kind="user_turn",
        work_id="metadata-only",
        wake_reason="user",
        model_round_index=0,
        world_revision=int(store.current_world_revision()),
        admitted_at=NOW,
    )
    attempts.mark_dispatching(
        attempt.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint="metadata-only-request",
    )
    for state in ("dispatching", "in_doubt"):
        if state == "in_doubt":
            with pytest.raises(BackgroundModelExecutionInDoubt):
                attempts.admit(
                    subject_id="user_1",
                    work_kind="user_turn",
                    work_id="metadata-only",
                    wake_reason="user",
                    model_round_index=0,
                    world_revision=int(store.current_world_revision()),
                    admitted_at=NOW + timedelta(minutes=1),
                )
        with pytest.raises(BackgroundModelResponseConflict):
            attempts.reconcile_response(
                attempt.attempt_id,
                reconciled_at=NOW,
                provider="late-trusted-provider",
                model="late-trusted-model",
                provider_request_id=REQUEST_ID,
                response_fingerprint="0" * 64,
                evidence="metadata is never authenticity",
            )
    assert attempts.get(attempt.attempt_id).state == "in_doubt"
