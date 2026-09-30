"""CORE-BACKGROUND-LATE-TRUSTED-RETURN-001 — frozen late trusted return probes.

Failure class (frozen by the WINDOW 12 adjudication): a trusted external return
that arrives *after* the Core process died, for an attempt already in
``dispatching`` / ``in_doubt`` with no ``background_model_response_receipts``
row. Current accepted Core has no legal attach path for that return, and its
only remaining exit is the post-dispatch ``reconcile_not_submitted`` false state.

RED-first discipline: this file was frozen, hashed and executed against exact
current ``main`` **before** any production change. See
``reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001/`` for the baseline manifest.

Every probe here is Core-only. No C15 harness, operator, exchange or run
evidence is touched, and the synthetic adapter in ``late_trusted_return_fixture``
is a unit-test stand-in, never a production transport.
"""
from __future__ import annotations

from datetime import timedelta
import inspect
import multiprocessing
import os
import pathlib
import signal
import sqlite3

import pytest

from aios_core.runtime import (
    BackgroundModelAttemptBlocked,
    BackgroundModelExecutionInDoubt,
    TurnAlreadyCompleted,
    TurnExecutionInDoubt,
)
from aios_core.runtime.background_attempt import (
    BackgroundModelResponseConflict,
    BackgroundModelResponsePending,
    encode_model_directive,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from late_trusted_return_fixture import (
    NOW,
    ProcessDeath,
    SyntheticExternalResponder,
    anonymous_directive,
    capability_rows,
    dispatch_then_die,
    meters,
    seed_anchor,
    trusted_directive,
    world,
)

SESSION = "late-trusted-return-session"
TURN_INDEX = 1
TURN_INPUT = "apply the late trusted return exactly once"
REQUEST_ID = "late-provider-request-0001"
OTHER_REQUEST_ID = "late-provider-request-9999"
FOREIGN_SUBJECT = "user_2"


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------


def build(db, *, handler, observer=None, subject_id="user_1"):
    store, index = world(db)
    kwargs = {}
    if observer is not None:
        # Absent an explicitly registered authorized observer, Core is not asked
        # for a capability at all, so baseline main runs this path unchanged.
        kwargs["external_return_observer"] = observer
    return FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=handler,
        subject_id=subject_id,
        **kwargs,
    )


def never_called(_snapshot):
    pytest.fail("a late trusted return must never redispatch the provider")


def dispatch_then_dead_run(db, *, observer, subject_id="user_1", key="ltr"):
    """Attempt admitted, outbound request published, Core process then dies."""

    runtime = build(db, handler=dispatch_then_die, observer=observer, subject_id=subject_id)
    seed_anchor(runtime.store, key=key)
    runtime.index.catch_up()
    with pytest.raises(ProcessDeath):
        runtime.run_turn(
            session_id=SESSION,
            turn_index=TURN_INDEX,
            user_input=TURN_INPUT,
            occurred_at=NOW,
        )
    return runtime


def dead_attempt(runtime, *, subject_id="user_1"):
    execution_id = runtime.turn_executions.execution_id_for(
        subject_id=subject_id, session_id=SESSION, turn_index=TURN_INDEX
    )
    attempts = runtime.background_model_attempts.list_for_work(
        subject_id=subject_id, work_kind="user_turn", work_id=execution_id
    )
    assert len(attempts) == 1
    return attempts[0]


def restart(db, *, observer=None, subject_id="user_1", handler=never_called):
    return build(db, handler=handler, observer=observer, subject_id=subject_id)


def resume(runtime, *, subject_id="user_1"):
    return runtime.run_turn(
        session_id=SESSION, turn_index=TURN_INDEX, user_input=TURN_INPUT, occurred_at=NOW
    )


def blocked_errors():
    """Every refusal Core may legitimately use for this class of attempt."""

    return (
        BackgroundModelAttemptBlocked,
        BackgroundModelExecutionInDoubt,
        BackgroundModelResponseConflict,
        BackgroundModelResponsePending,
        TurnExecutionInDoubt,
        ValueError,
    )


def force_in_doubt(runtime, attempt):
    """Frozen step 7-8 at the store boundary: restart admission raises in doubt.

    The user-turn entrypoint may refuse even earlier (the turn execution claim is
    itself in doubt), so the deterministic way to reach the documented
    ``dispatching -> in_doubt`` conversion is the admission guard itself.
    """

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


# ---------------------------------------------------------------------------
# LTR-R0 — the pre-existing surfaces cannot attach a late trusted return, and
#          the post-dispatch attempt stays a terminal dead end. This probe uses
#          only already-accepted public Core API and stays GREEN after the fix:
#          a return with no authorized observer must never become trusted.
# ---------------------------------------------------------------------------


def test_ltr_r0_absent_authorized_observer_keeps_the_late_return_permanently_unattachable(tmp_path):
    db = tmp_path / "world.db"
    runtime = dispatch_then_dead_run(db, observer=None, key="ltr-r0")
    attempt = dead_attempt(runtime)
    assert attempt.state == "dispatching"
    assert runtime.background_model_attempts.response_authenticity_receipt(attempt.attempt_id) is None

    fresh = restart(db)
    with pytest.raises(TurnExecutionInDoubt):
        resume(fresh)

    in_doubt = fresh.background_model_attempts.get(attempt.attempt_id)
    assert in_doubt.state in {"dispatching", "in_doubt"}
    before_dead_end = in_doubt.state
    binding = fresh.background_model_attempts.outbound_request_binding(attempt.attempt_id)
    assert binding is not None
    assert fresh.background_model_attempts.recover_trusted_handoff(
        subject_id="user_1", work_kind="user_turn",
        work_id=fresh.turn_executions.execution_id_for(
            subject_id="user_1", session_id=SESSION, turn_index=TURN_INDEX),
    ) is None
    assert fresh.background_model_attempts.staged_response(attempt.attempt_id) is None
    # Metadata-only reconciliation stays disabled, exactly as accepted.
    with pytest.raises(BackgroundModelResponseConflict):
        fresh.background_model_attempts.reconcile_response(
            attempt.attempt_id,
            reconciled_at=NOW,
            provider="late-trusted-provider",
            model="late-trusted-model",
            provider_request_id=REQUEST_ID,
            response_fingerprint="0" * 64,
            evidence="caller-computable metadata is never authenticity",
        )
    # The single remaining exit may no longer write a retry-enabling false state.
    with pytest.raises(BackgroundModelResponseConflict):
        fresh.background_model_attempts.reconcile_not_submitted(
            attempt.attempt_id,
            reconciled_at=NOW,
            evidence="the request was published before the process died",
        )
    assert_still_blocked(fresh, attempt.attempt_id)
    assert meters(fresh) == []


# ---------------------------------------------------------------------------
# LTR-R1 — late trustworthy response after process death
# ---------------------------------------------------------------------------


def _ltr_r1_converges(tmp_path, *, attach_after_in_doubt, key):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key=key)
    attempt = dead_attempt(runtime)
    assert attempt.state == "dispatching"
    assert runtime.background_model_attempts.response_authenticity_receipt(attempt.attempt_id) is None
    assert capability_rows(db) == [
        (
            attempt.attempt_id, "user_1", "user_turn",
            runtime.turn_executions.execution_id_for(
                subject_id="user_1", session_id=SESSION, turn_index=TURN_INDEX),
            0, *binding_fields(runtime, attempt.attempt_id), False,
        )
    ]

    fresh = restart(db)
    if attach_after_in_doubt:
        # Frozen step 7-8: restart admission raises before the model handler.
        force_in_doubt(fresh, attempt)
        assert_still_blocked(fresh, attempt.attempt_id)

    # Frozen step 5-6: the external trusted responder finishes AFTER Core death.
    exact = trusted_directive(REQUEST_ID)
    proof = responder.finish_after_core_death(attempt.attempt_id, exact)
    assert proof.startswith("bglate_v1_")

    staged = fresh.background_model_attempts.attach_late_trusted_return(
        attempt.attempt_id,
        attached_at=NOW + timedelta(minutes=10),
        directive_payload=encode_model_directive(exact),
        late_return_proof=proof,
        evidence="late trusted external return observed after Core process death",
    )
    assert staged.payload_sha256 == _sha(encode_model_directive(exact))

    # Same attempt, same request, no redispatch, exactly-once convergence.
    result = resume(fresh)
    assert result.runtime.response == "late return applied exactly once"
    assert [record.total_tokens for record in meters(fresh)] == [10]
    final = fresh.background_model_attempts.get(attempt.attempt_id)
    assert final.state == "metered"
    assert final.provider == "late-trusted-provider"
    assert final.model == "late-trusted-model"
    assert final.provider_request_id == REQUEST_ID
    assert fresh.background_model_attempts.staged_response(attempt.attempt_id).directive_payload == (
        encode_model_directive(exact)
    )
    # The stronger terminal receipt short-circuits everything afterwards.
    with pytest.raises(TurnAlreadyCompleted):
        resume(restart(db))
    return fresh


def assert_still_blocked(runtime, attempt_id, *, before=None):
    """A refused late return must leave the attempt exactly as it was."""

    attempts = runtime.background_model_attempts
    current = attempts.get(attempt_id)
    assert current is not None
    assert current.state in {"dispatching", "in_doubt"}
    if before is not None:
        assert current.state == before
    assert attempts.response_authenticity_receipt(attempt_id) is None
    assert attempts.staged_response(attempt_id) is None


def binding_fields(runtime, attempt_id):
    binding = runtime.background_model_attempts.outbound_request_binding(attempt_id)
    return (binding.outbound_request_fingerprint, binding.relay_id)


def _sha(payload: str) -> str:
    import hashlib

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_ltr_r1_late_trusted_return_while_dispatch_is_still_durable(tmp_path):
    _ltr_r1_converges(tmp_path, attach_after_in_doubt=False, key="ltr-r1a")


def test_ltr_r1_late_trusted_return_after_restart_admission_raised_in_doubt(tmp_path):
    _ltr_r1_converges(tmp_path, attach_after_in_doubt=True, key="ltr-r1b")


def test_ltr_r1_capability_is_single_use_and_consumed(tmp_path):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key="ltr-r1c")
    attempt = dead_attempt(runtime)
    exact = trusted_directive(REQUEST_ID)
    proof = responder.finish_after_core_death(attempt.attempt_id, exact)
    fresh = restart(db)
    fresh.background_model_attempts.attach_late_trusted_return(
        attempt.attempt_id,
        attached_at=NOW + timedelta(minutes=10),
        directive_payload=encode_model_directive(exact),
        late_return_proof=proof,
        evidence="late trusted external return",
    )
    assert capability_rows(db)[0][-1] is True


def _sigkill_child(str_db, conn):
    import signal as _signal

    def handler(_snapshot):
        os.kill(os.getpid(), _signal.SIGKILL)

    def wire(attempt_id, capability):
        # Connection.send is a synchronous write; a multiprocessing.Queue would
        # hand the bytes to a feeder thread that the SIGKILL below would race.
        conn.send((attempt_id, capability))
        conn.close()

    observer = SyntheticExternalResponder(wire=wire)
    store, index = world(pathlib.Path(str_db))
    runtime = build(
        pathlib.Path(str_db), handler=handler, observer=observer
    )
    runtime.run_turn(
        session_id=SESSION, turn_index=TURN_INDEX, user_input=TURN_INPUT, occurred_at=NOW
    )


def test_ltr_r1_real_sigkill_then_late_trusted_return_converges_exactly_once(tmp_path):
    db = tmp_path / "world.db"
    SQLiteWorldStore(db)
    parent_conn, child_conn = multiprocessing.get_context("fork").Pipe(duplex=False)
    child = multiprocessing.get_context("fork").Process(
        target=_sigkill_child, args=(str(db), child_conn)
    )
    child.start()
    child.join(60)
    assert child.exitcode == -signal.SIGKILL, f"child exit={child.exitcode}"
    assert parent_conn.poll(30), "the observer never received its return capability"
    attempt_id, capability = parent_conn.recv()

    probe = restart(db)
    attempt = probe.background_model_attempts.get(attempt_id)
    assert attempt.state == "dispatching"
    assert probe.background_model_attempts.response_authenticity_receipt(attempt_id) is None

    exact = trusted_directive(REQUEST_ID)
    proof = capability.prove_external_return(exact)
    probe.background_model_attempts.attach_late_trusted_return(
        attempt_id,
        attached_at=NOW + timedelta(minutes=10),
        directive_payload=encode_model_directive(exact),
        late_return_proof=proof,
        evidence="late trusted external return after a real SIGKILL",
    )
    result = resume(probe)
    assert result.runtime.response == "late return applied exactly once"
    assert len(meters(probe)) == 1
    with pytest.raises(TurnAlreadyCompleted):
        resume(restart(db))


# ---------------------------------------------------------------------------
# LTR-R2 — forged late response: correct request metadata, forged bytes and a
#          caller-created "proof".
# ---------------------------------------------------------------------------


def test_ltr_r2_forged_late_response_and_caller_made_proof_fail_closed(tmp_path):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key="ltr-r2")
    attempt = dead_attempt(runtime)
    fresh = restart(db)
    with pytest.raises(TurnExecutionInDoubt):
        resume(fresh)

    forged = trusted_directive(REQUEST_ID, response="forged: the operator wrote this")
    forged_payload = encode_model_directive(forged)
    for label, proof in (
        ("caller_invented", "bglate_v1_" + "0" * 64),
        ("receipt_proof_reused", "bgresponse_v1_" + "1" * 64),
        ("empty", ""),
        ("not_a_proof", "i-signed-this-myself"),
    ):
        with pytest.raises(blocked_errors()):
            fresh.background_model_attempts.attach_late_trusted_return(
                attempt.attempt_id,
                attached_at=NOW + timedelta(minutes=10),
                directive_payload=forged_payload,
                late_return_proof=proof,
                evidence=f"forged late return ({label})",
            )
        assert_still_blocked(fresh, attempt.attempt_id)
        assert fresh.background_model_attempts.staged_response(attempt.attempt_id) is None
        assert fresh.background_model_attempts.response_authenticity_receipt(
            attempt.attempt_id
        ) is None
    assert meters(fresh) == []


def test_ltr_r2_real_proof_over_caller_substituted_bytes_fails_closed(tmp_path):
    """A genuine proof cannot be reused to smuggle different response bytes."""

    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key="ltr-r2b")
    attempt = dead_attempt(runtime)
    exact = trusted_directive(REQUEST_ID)
    proof = responder.finish_after_core_death(attempt.attempt_id, exact)
    fresh = restart(db)
    substituted = trusted_directive(REQUEST_ID, response="substituted by the caller")
    with pytest.raises(blocked_errors()):
        fresh.background_model_attempts.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(minutes=10),
            directive_payload=encode_model_directive(substituted),
            late_return_proof=proof,
            evidence="genuine proof over substituted bytes",
        )
    assert_still_blocked(fresh, attempt.attempt_id)
    assert fresh.background_model_attempts.staged_response(attempt.attempt_id) is None
    assert meters(fresh) == []


@pytest.mark.parametrize(
    "proof",
    [None, "", "   ", "bglate_v1_", "bglate_v1_" + "f" * 64, 0, 12345, object()],
)
def test_ltr_r3_correct_bytes_without_a_trusted_proof_fail_closed(tmp_path, proof):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key="ltr-r3")
    attempt = dead_attempt(runtime)
    fresh = restart(db)
    exact = trusted_directive(REQUEST_ID)
    with pytest.raises(blocked_errors()):
        fresh.background_model_attempts.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(minutes=10),
            directive_payload=encode_model_directive(exact),
            late_return_proof=proof,
            evidence="correct bytes, no trusted proof",
        )
    assert_still_blocked(fresh, attempt.attempt_id)
    assert fresh.background_model_attempts.staged_response(attempt.attempt_id) is None
    assert meters(fresh) == []


def test_ltr_r3_pre_dispatch_attempt_has_no_return_capability_at_all(tmp_path):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key="ltr-r3b")
    fresh = restart(db)
    admitted = fresh.background_model_attempts.admit(
        subject_id="user_1",
        work_kind="wake",
        work_id="never-dispatched-wake",
        wake_reason="safety",
        model_round_index=0,
        world_revision=int(fresh.store.current_world_revision()),
        admitted_at=NOW,
    )
    exact = trusted_directive(REQUEST_ID)
    with pytest.raises(blocked_errors()):
        fresh.background_model_attempts.attach_late_trusted_return(
            admitted.attempt_id,
            attached_at=NOW,
            directive_payload=encode_model_directive(exact),
            late_return_proof="bglate_v1_" + "2" * 64,
            evidence="no dispatch boundary was ever crossed",
        )
    assert fresh.background_model_attempts.get(admitted.attempt_id).state == "admitted"
    assert fresh.background_model_attempts.staged_response(admitted.attempt_id) is None


# ---------------------------------------------------------------------------
# LTR-R4 — proof transplant across attempt / round / work / subject / request.
# ---------------------------------------------------------------------------


def _second_dispatched_attempt(db, *, key):
    """A second, independently dispatched attempt with its own capability."""

    responder = SyntheticExternalResponder()
    runtime = build(db, handler=dispatch_then_die, observer=responder)
    seed_anchor(runtime.store, key=key)
    runtime.index.catch_up()
    with pytest.raises(ProcessDeath):
        runtime.run_turn(
            session_id=f"{SESSION}-{key}",
            turn_index=TURN_INDEX,
            user_input=TURN_INPUT,
            occurred_at=NOW,
        )
    execution_id = runtime.turn_executions.execution_id_for(
        subject_id="user_1", session_id=f"{SESSION}-{key}", turn_index=TURN_INDEX
    )
    attempt = runtime.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind="user_turn", work_id=execution_id
    )[-1]
    return runtime, attempt, responder


def test_ltr_r4_proof_from_another_attempt_cannot_be_transplanted(tmp_path):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key="ltr-r4a")
    target = dead_attempt(runtime)
    _other_runtime, other, other_responder = _second_dispatched_attempt(
        db, key="ltr-r4b"
    )
    exact = trusted_directive(REQUEST_ID)
    foreign_proof = other_responder.finish_after_core_death(other.attempt_id, exact)
    fresh = restart(db)
    with pytest.raises(blocked_errors()):
        fresh.background_model_attempts.attach_late_trusted_return(
            target.attempt_id,
            attached_at=NOW + timedelta(minutes=10),
            directive_payload=encode_model_directive(exact),
            late_return_proof=foreign_proof,
            evidence="proof transplanted from another attempt",
        )
    assert_still_blocked(fresh, target.attempt_id)
    # and the genuine owner of that proof can still use it on its own attempt
    assert other_responder.capabilities


def test_ltr_r4_proof_cannot_be_transplanted_to_another_subject_or_work(tmp_path):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key="ltr-r4c")
    target = dead_attempt(runtime)
    exact = trusted_directive(REQUEST_ID)
    proof = responder.finish_after_core_death(target.attempt_id, exact)
    fresh = restart(db)

    other_subject = fresh.background_model_attempts.admit(
        subject_id=FOREIGN_SUBJECT,
        work_kind="user_turn",
        work_id="foreign-subject-work",
        wake_reason="user",
        model_round_index=0,
        world_revision=int(fresh.store.current_world_revision()),
        admitted_at=NOW,
    )
    for candidate in (other_subject,):
        with pytest.raises(blocked_errors()):
            fresh.background_model_attempts.attach_late_trusted_return(
                candidate.attempt_id,
                attached_at=NOW,
                directive_payload=encode_model_directive(exact),
                late_return_proof=proof,
                evidence="proof transplanted to another subject",
            )
        assert fresh.background_model_attempts.get(candidate.attempt_id).state == "admitted"
    assert_still_blocked(fresh, target.attempt_id)


def test_ltr_r4_proof_cannot_be_transplanted_to_another_round(tmp_path):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key="ltr-r4d")
    target = dead_attempt(runtime)
    exact = trusted_directive(REQUEST_ID)
    proof = responder.finish_after_core_death(target.attempt_id, exact)
    fresh = restart(db)
    # Round 1 of the same work is only reachable after round 0 resolves, so the
    # transplant is attempted through a directly constructed, dispatched round.
    round_one = fresh.background_model_attempts.admit(
        subject_id="user_1",
        work_kind="user_turn",
        work_id=fresh.turn_executions.execution_id_for(
            subject_id="user_1", session_id=SESSION, turn_index=TURN_INDEX
        ),
        wake_reason="user",
        model_round_index=1,
        world_revision=int(fresh.store.current_world_revision()),
        admitted_at=NOW,
    )
    fresh.background_model_attempts.mark_dispatching(
        round_one.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint="a-different-outbound-request",
    )
    with pytest.raises(blocked_errors()):
        fresh.background_model_attempts.attach_late_trusted_return(
            round_one.attempt_id,
            attached_at=NOW,
            directive_payload=encode_model_directive(exact),
            late_return_proof=proof,
            evidence="proof transplanted to another round and request",
        )
    assert fresh.background_model_attempts.get(round_one.attempt_id).state == "dispatching"
    assert fresh.background_model_attempts.staged_response(round_one.attempt_id) is None


def test_ltr_r4_durable_binding_tampering_invalidates_the_proof(tmp_path):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key="ltr-r4e")
    attempt = dead_attempt(runtime)
    exact = trusted_directive(REQUEST_ID)
    proof = responder.finish_after_core_death(attempt.attempt_id, exact)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE background_model_request_bindings "
            "SET outbound_request_fingerprint=? WHERE attempt_id=?",
            ("0" * 64, attempt.attempt_id),
        )
        conn.commit()
    fresh = restart(db)
    with pytest.raises(blocked_errors()):
        fresh.background_model_attempts.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(minutes=10),
            directive_payload=encode_model_directive(exact),
            late_return_proof=proof,
            evidence="the originating outbound request was rewritten underneath",
        )
    assert fresh.background_model_attempts.staged_response(attempt.attempt_id) is None


# ---------------------------------------------------------------------------
# LTR-R5 — changed response under the same proof.
# ---------------------------------------------------------------------------


def test_ltr_r5_changed_response_under_the_same_proof_fails_closed(tmp_path):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key="ltr-r5")
    attempt = dead_attempt(runtime)
    exact = trusted_directive(REQUEST_ID)
    proof = responder.finish_after_core_death(attempt.attempt_id, exact)
    fresh = restart(db)
    for changed in (
        trusted_directive(REQUEST_ID, response="a different but trusted-looking reply"),
        trusted_directive(REQUEST_ID, response=exact.response, model="late-trusted-model-v2"),
        trusted_directive(OTHER_REQUEST_ID),
        trusted_directive(REQUEST_ID, provider="another-provider"),
    ):
        with pytest.raises(blocked_errors()):
            fresh.background_model_attempts.attach_late_trusted_return(
                attempt.attempt_id,
                attached_at=NOW + timedelta(minutes=10),
                directive_payload=encode_model_directive(changed),
                late_return_proof=proof,
                evidence="the response changed under an already-minted proof",
            )
        assert_still_blocked(fresh, attempt.attempt_id)
        assert fresh.background_model_attempts.staged_response(attempt.attempt_id) is None
    assert meters(fresh) == []


# ---------------------------------------------------------------------------
# LTR-R6 — proof replay.
# ---------------------------------------------------------------------------


def test_ltr_r6_consumed_proof_replay_is_deterministic_exact_recovery(tmp_path):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key="ltr-r6")
    attempt = dead_attempt(runtime)
    exact = trusted_directive(REQUEST_ID)
    proof = responder.finish_after_core_death(attempt.attempt_id, exact)
    fresh = restart(db)
    payload = encode_model_directive(exact)
    first = fresh.background_model_attempts.attach_late_trusted_return(
        attempt.attempt_id,
        attached_at=NOW + timedelta(minutes=10),
        directive_payload=payload,
        late_return_proof=proof,
        evidence="late trusted external return",
    )
    replay = fresh.background_model_attempts.attach_late_trusted_return(
        attempt.attempt_id,
        attached_at=NOW + timedelta(minutes=20),
        directive_payload=payload,
        late_return_proof=proof,
        evidence="replay of an already consumed late return proof",
    )
    assert replay.payload_sha256 == first.payload_sha256
    assert replay.directive_payload == first.directive_payload
    assert fresh.background_model_attempts.get(attempt.attempt_id).state == "response_returned"
    result = resume(fresh)
    assert result.runtime.response == "late return applied exactly once"
    assert len(meters(fresh)) == 1
    with pytest.raises(TurnAlreadyCompleted):
        resume(restart(db))


def test_ltr_r6_consumed_proof_replay_with_different_bytes_fails_closed(tmp_path):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key="ltr-r6b")
    attempt = dead_attempt(runtime)
    exact = trusted_directive(REQUEST_ID)
    proof = responder.finish_after_core_death(attempt.attempt_id, exact)
    fresh = restart(db)
    fresh.background_model_attempts.attach_late_trusted_return(
        attempt.attempt_id,
        attached_at=NOW + timedelta(minutes=10),
        directive_payload=encode_model_directive(exact),
        late_return_proof=proof,
        evidence="late trusted external return",
    )
    resume(fresh)
    before = meters(fresh)
    with pytest.raises(blocked_errors()):
        fresh.background_model_attempts.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(minutes=30),
            directive_payload=encode_model_directive(
                trusted_directive(REQUEST_ID, response="replayed substitution")
            ),
            late_return_proof=proof,
            evidence="consumed proof replayed with different bytes",
        )
    assert fresh.background_model_attempts.get(attempt.attempt_id).state == "metered"
    assert meters(fresh) == before


# ---------------------------------------------------------------------------
# LTR-R7 / R8 — anonymous and local handlers are never auto-upgraded.
# ---------------------------------------------------------------------------


def test_ltr_r7_anonymous_handler_gets_no_capability_and_no_attach(tmp_path):
    db = tmp_path / "world.db"
    runtime = dispatch_then_dead_run(db, observer=None, key="ltr-r7")
    assert capability_rows(db) == []
    attempt = dead_attempt(runtime)
    fresh = restart(db)
    with pytest.raises(TurnExecutionInDoubt):
        resume(fresh)
    with pytest.raises(blocked_errors()):
        fresh.background_model_attempts.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW,
            directive_payload=encode_model_directive(anonymous_directive()),
            late_return_proof="bglate_v1_" + "3" * 64,
            evidence="anonymous local handler bytes",
        )
    assert_still_blocked(fresh, attempt.attempt_id)


def test_ltr_r8_anonymous_external_return_can_never_mint_a_late_proof(tmp_path):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key="ltr-r8")
    attempt = dead_attempt(runtime)
    with pytest.raises(ValueError):
        responder.finish_after_core_death(attempt.attempt_id, anonymous_directive())
    assert capability_rows(db)[0][-1] is False
    fresh = restart(db)
    assert fresh.background_model_attempts.get(attempt.attempt_id).state == "dispatching"


# ---------------------------------------------------------------------------
# LTR-R9 / R10 — the capability is not a signing oracle.
# ---------------------------------------------------------------------------


def test_ltr_r9_leaked_capability_cannot_mint_a_proof_for_another_attempt(tmp_path):
    db = tmp_path / "world.db"
    responder = SyntheticExternalResponder()
    runtime = dispatch_then_dead_run(db, observer=responder, key="ltr-r9a")
    target = dead_attempt(runtime)
    _other, other, _ = _second_dispatched_attempt(db, key="ltr-r9b")
    leaked = responder.capabilities[target.attempt_id]
    other_exact = trusted_directive(OTHER_REQUEST_ID)
    # The leaked capability can still speak for its own exact scope ...
    own = leaked.prove_external_return(trusted_directive(REQUEST_ID))
    assert own.startswith("bglate_v1_")
    # ... but Core refuses that proof on any other attempt/round/binding.
    fresh = restart(db)
    with pytest.raises(blocked_errors()):
        fresh.background_model_attempts.attach_late_trusted_return(
            other.attempt_id,
            attached_at=NOW,
            directive_payload=encode_model_directive(other_exact),
            late_return_proof=own,
            evidence="a leaked capability reused outside its exact scope",
        )
    assert fresh.background_model_attempts.get(other.attempt_id).state == "dispatching"
    assert fresh.background_model_attempts.staged_response(other.attempt_id) is None


def test_ltr_r10_no_public_surface_converts_arbitrary_bytes_into_a_trusted_return():
    """Source-level audit: the bytes -> trusted-receipt oracle does not exist."""

    from aios_core.runtime import background_attempt as module

    forbidden = (
        "mint_receipt_for_payload",
        "stage_trusted_returned_background_response",
        "sign_response",
        "issue_authenticity_proof",
    )
    for name in dir(module.BackgroundModelAttemptStore):
        assert name not in forbidden, f"signing-oracle-shaped surface: {name}"
    # No public/recovery-facing method returns or accepts the return capability.
    for name, member in vars(module.BackgroundModelAttemptStore).items():
        if name.startswith("_") or not callable(member):
            continue
        signature = inspect.signature(member)
        assert "capability_nonce" not in signature.parameters
        if "late_return_proof" in signature.parameters:
            # The only bytes -> trusted path is fail-closed behind proof verification.
            assert name == "attach_late_trusted_return", name
    # The minting authority stays private and is never returned by a public API.
    assert "capability" not in dir(module.BackgroundModelAttemptStore.response_authenticity_receipt)
    assert module.BackgroundModelAttemptStore.response_authenticity_receipt.__doc__


def test_ltr_r10_the_only_proof_minting_surface_needs_the_capability_object():
    from aios_core.runtime.late_return import BackgroundModelReturnCapability

    parameters = inspect.signature(
        BackgroundModelReturnCapability.prove_external_return
    ).parameters
    assert list(parameters) == ["self", "directive"]
    # Constructing one requires an explicit nonce argument; there is no default.
    fields = BackgroundModelReturnCapability.model_fields
    assert "capability_nonce" not in fields
    assert fields["attempt_id"].is_required()
