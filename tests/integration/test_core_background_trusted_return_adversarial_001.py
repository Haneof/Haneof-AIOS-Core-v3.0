"""Adversarial verification of the durable trusted return handoff (Route B).

SQL mutations simulate damaged/untrusted storage; they never authorize a provider
return.

TIGHTEN_ONLY history (Corrective-003 / Window 22-RERUN-001).

Old expectation
    ``crash_at_return`` produced a receipt/handoff purely from the *live local
    handler return*, and this file re-captured bytes through
    ``capture_live_provider_return`` ->
    ``BackgroundModelAttemptStore.record_live_provider_return`` driven by
    ``open_live_provider_return_window`` / ``register_handler_return``.  Damaged
    durable state was then expected to leave the attempt in ``dispatching`` with
    no staged response.

Old authority mechanism
    The ephemeral live provider-return window (process-local registry + ContextVar
    + issuance sentinel + handler-return identity map).

Why that mechanism is unsafe (BLK-W20-001)
    ``RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW``
    / ``TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE``: window issuance
    was an ordinary public function, so any process-local recovery caller could
    self-issue a window, declare its own bytes handler-returned, mint the very
    receipt/handoff rows this file mutates, complete and meter an attempt that must
    have stayed ``in_doubt``, and poison a later genuine RSA trusted return.

Replacement route
    Route B.  The live local return mints nothing.  Every receipt / handoff /
    staged exact response row this file mutates is now produced only by a genuine
    external RSA signature over the durable request binding, attached through
    ``BackgroundModelAttemptStore.attach_late_trusted_return``.  The external
    private key is TEST-ONLY material owned by the simulated external side.

Deleted / kept / equal-or-stronger
    Deleted: the assertion that a damaged handoff leaves the attempt in
    ``dispatching`` with no staged row.  That asserted the *pre-external-proof*
    shape, which no longer exists because the genuine proof is what creates the
    durable trusted state in the first place.
    Added (strictly stronger): for all 21 mutations the test now asserts the real
    security property -- Core either fails closed or reproduces *exactly* the
    genuinely externally-proven bytes and identity, never a mutated byte or a
    mutated identity, and never meters twice.  It also asserts that no local mint
    API exists at all any more, and that the decommissioned live-window names
    confer nothing.
    Kept (unchanged): the 21-case mutation matrix byte-for-byte, zero provider
    redispatch, real multi-process SIGKILL, exactly-once replay, conflicting
    return rejection, and "output before outer ACK" behaviour.

Exactly-once / provenance / crash / truthfulness
    Preserved and strengthened: exactly-once is now asserted both on the refusal
    branch (zero new meters) and on the recovery branch (exactly one new meter and
    durable provenance still equal to the externally-proven values).
"""
from __future__ import annotations

from datetime import timedelta
from dataclasses import replace
import hashlib
import sqlite3

import pytest

from aios_core.runtime import TurnExecutionInDoubt, TurnAlreadyCompleted
from aios_core.runtime.background_attempt import (
    BackgroundModelResponseConflict, encode_model_directive,
)
from aios_core.runtime import live_return as live_return_module
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from test_core_background_trusted_return_recovery_001 import (
    NOW, RouteBExternalSigner, crash_at_return, crash_at_return_with_signer,
    crash_before_local_completion, directive, route_b_verifier, trust_row_counts,
    world,
)


def restart(db):
    store, index = world(db)
    return FusedTurnRuntime(
        store=store, index=index,
        model_handler=lambda _snapshot: pytest.fail("no redispatch on untrusted handoff"),
    )


def attach_genuine_external_return(attempts_store, signer, attempt_id, returned, *, seconds):
    """Produce durable trusted return the only way Route B allows.

    Corrective-003 history note.  This file previously re-captured bytes through
    ``record_live_provider_return`` behind a self-issued ephemeral window.
    ``BLK-W20-001`` established that this is a recovery-reachable minting oracle,
    so the writer no longer exists.  The genuine external signature below is the
    replacement authority: it is produced by the external side over Core's durable
    request binding and verified with public verifier material only.
    """

    attempts_store.attach_late_trusted_return(
        attempt_id,
        attached_at=NOW + timedelta(seconds=seconds),
        directive_payload=encode_model_directive(returned),
        late_return_proof=signer.proof(attempt_id, returned),
        evidence="genuine external Route B return",
    )
    return attempts_store.response_authenticity_receipt(attempt_id)


def resume(runtime):
    return runtime.run_turn(session_id="trusted-session", turn_index=1,
                            user_input="complete exactly once", occurred_at=NOW)


def _genuine_other_round_handoff(tmp_path):
    """A genuinely signed handoff that legitimately belongs to ANOTHER round.

    Route B replacement for the old "copy round 0's handoff onto round 1"
    mutation.  Under Route B a live-completed round carries no handoff at all, so
    the NULL copy no longer expressed the intended attack.  This builds a second,
    independent world, produces a real externally-proven handoff for its round 2,
    and returns those exact durable values -- a *valid* handoff with a *valid*
    proof, bound to a different attempt, work, round and byte payload.  That is a
    strictly stronger transplant attack than the old one.
    """

    other_dir = tmp_path / "other_world"
    other_dir.mkdir()
    db, _runtime, attempts, _receipt, _execution_id, _signer = crash_at_return_with_signer(
        other_dir, 2
    )
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT directive_payload, payload_sha256, authenticity_proof "
            "FROM background_model_return_handoffs WHERE attempt_id=?",
            (attempts[-1].attempt_id,),
        ).fetchone()
    assert row is not None
    assert attempts[-1].model_round_index == 2
    return row


@pytest.mark.parametrize("mutation", [
    "forged_directive", "forged_fingerprint", "wrong_provider", "wrong_model",
    "wrong_request_id", "wrong_originating_request", "wrong_response_digest",
    "altered_payload", "duplicate_top_key", "duplicate_nested_key",
    "missing_handoff", "corrupt_handoff_digest", "corrupt_handoff_proof",
    "copied_handoff_from_round", "cross_work", "cross_work_kind", "cross_subject",
    "cross_round", "unknown_attempt_handoff", "missing_receipt", "invalid_receipt",
])
def test_untrusted_handoff_never_adopts_wrong_bytes_or_identity(tmp_path, mutation):
    db, _before, attempts, receipt, execution_id = crash_at_return(tmp_path, 1)
    target = attempts[-1].attempt_id
    genuine_payload = encode_model_directive(directive(1))
    genuine_digest = hashlib.sha256(genuine_payload.encode("utf-8")).hexdigest()
    with sqlite3.connect(db) as conn:
        if mutation in {"forged_directive", "altered_payload"}:
            payload = genuine_payload.replace("finished once", "forged output")
            conn.execute("UPDATE background_model_return_handoffs SET directive_payload=?, payload_sha256=? WHERE attempt_id=?",
                         (payload, hashlib.sha256(payload.encode()).hexdigest(), target))
        elif mutation == "forged_fingerprint":
            conn.execute("UPDATE background_model_response_receipts SET response_fingerprint=? WHERE attempt_id=?",
                         ("0" * 64, target))
        elif mutation in {"wrong_provider", "wrong_model", "wrong_request_id", "wrong_response_digest",
                          "cross_work", "cross_work_kind", "cross_subject", "cross_round"}:
            col, value = {
                "wrong_provider": ("provider", "fake-provider"),
                "wrong_model": ("model", "fake-model"),
                "wrong_request_id": ("provider_request_id", "fake-request"),
                "wrong_response_digest": ("payload_sha256", "0" * 64),
                "cross_work": ("work_id", "other-work"),
                "cross_work_kind": ("work_kind", "wake"),
                "cross_subject": ("subject_id", "other-subject"),
                "cross_round": ("model_round_index", 0),
            }[mutation]
            conn.execute(f"UPDATE background_model_response_receipts SET {col}=? WHERE attempt_id=?", (value, target))
        elif mutation == "wrong_originating_request":
            conn.execute("UPDATE background_model_request_bindings SET outbound_request_fingerprint=? WHERE attempt_id=?",
                         ("0" * 64, target))
        elif mutation in {"duplicate_top_key", "duplicate_nested_key"}:
            if mutation == "duplicate_top_key":
                payload = genuine_payload[:-1] + ',"response":"forged output"}'
            else:
                payload = genuine_payload.replace('"provider":"trusted-provider"', '"provider":"trusted-provider","provider":"forged"', 1)
            conn.execute("UPDATE background_model_return_handoffs SET directive_payload=?, payload_sha256=? WHERE attempt_id=?",
                         (payload, hashlib.sha256(payload.encode()).hexdigest(), target))
        elif mutation == "missing_handoff":
            conn.execute("DELETE FROM background_model_return_handoffs WHERE attempt_id=?", (target,))
        elif mutation == "corrupt_handoff_digest":
            conn.execute("UPDATE background_model_return_handoffs SET payload_sha256=? WHERE attempt_id=?", ("0" * 64, target))
        elif mutation == "corrupt_handoff_proof":
            conn.execute("UPDATE background_model_return_handoffs SET authenticity_proof=? WHERE attempt_id=?", ("0" * 64, target))
        elif mutation == "copied_handoff_from_round":
            # Route B TIGHTEN_ONLY: a live-completed earlier round no longer owns a
            # handoff, so "copied from another round" is now a genuine cross-round
            # transplant of a valid externally-signed handoff (see helper above).
            payload, digest, proof = _genuine_other_round_handoff(tmp_path)
            assert payload != genuine_payload
            conn.execute("UPDATE background_model_return_handoffs SET directive_payload=?, payload_sha256=?, authenticity_proof=? WHERE attempt_id=?",
                         (payload, digest, proof, target))
        elif mutation == "unknown_attempt_handoff":
            conn.execute("UPDATE background_model_return_handoffs SET attempt_id=? WHERE attempt_id=?", ("unknown-attempt", target))
        elif mutation == "missing_receipt":
            conn.execute("DELETE FROM background_model_response_receipts WHERE attempt_id=?", (target,))
        elif mutation == "invalid_receipt":
            conn.execute("UPDATE background_model_response_receipts SET authenticity_proof=? WHERE attempt_id=?", ("0" * 64, target))
        conn.commit()
    fresh = restart(db)
    before_meters = fresh.metering.list_model_calls(subject_id="user_1")

    refused = None
    recovered = None
    try:
        recovered = resume(fresh).runtime.response
    except (BackgroundModelResponseConflict, ValueError, TurnExecutionInDoubt) as exc:
        refused = type(exc).__name__

    # Route B security property: damaged or untrusted durable state can never make
    # Core adopt bytes or an identity other than the genuinely externally-proven
    # ones.  Either recovery fails closed, or it reproduces exactly the signed
    # return -- and in that case the durable provenance is still the proven one.
    assert refused is not None or recovered == "finished once", (
        f"mutation={mutation} refused={refused} recovered={recovered!r}"
    )
    after_state = fresh.background_model_attempts.get(target).state
    meters = fresh.metering.list_model_calls(subject_id="user_1")
    if refused is not None:
        # Fail closed: nothing metered, nothing adopted, state did not advance.
        assert meters == before_meters
        assert after_state == "response_returned"
        assert fresh.inspect_turn_execution(
            session_id="trusted-session", turn_index=1,
            user_input="complete exactly once", occurred_at=NOW,
        ).state != "completed"
    else:
        # Genuine bytes reproduced: exactly one new meter, exactly-once preserved.
        assert len(meters) == len(before_meters) + 1
        assert after_state == "metered"
        attempt_row = fresh.background_model_attempts.get(target)
        assert (attempt_row.provider, attempt_row.model,
                attempt_row.provider_request_id, attempt_row.response_fingerprint) == (
            receipt.provider, receipt.model, receipt.provider_request_id,
            receipt.response_fingerprint,
        )
        staged = fresh.background_model_attempts.staged_response(target)
        assert staged is not None
        assert staged.directive_payload == genuine_payload
        assert staged.payload_sha256 == genuine_digest
        with pytest.raises(TurnAlreadyCompleted):
            resume(restart(db))

    # No mutation may ever leak forged bytes or a forged identity into durable
    # state that Core would later treat as the exact provider reply.
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT directive_payload FROM background_model_responses WHERE attempt_id=?",
            (target,),
        ).fetchall()
    assert all("forged output" not in row[0] for row in rows)
    assert all('"provider":"forged"' not in row[0] for row in rows)
    if rows:
        assert rows[0][0] == genuine_payload


def test_same_bytes_repeated_return_is_idempotent_but_conflicting_return_rejected(tmp_path):
    db, runtime, attempts, receipt, _execution_id, signer = crash_at_return_with_signer(
        tmp_path, 1
    )
    target = attempts[-1].attempt_id
    store = runtime.background_model_attempts
    original = directive(1)

    # An exact replay of the same genuine external return is effect-free: the
    # verifier is already consumed, so only the identical signed bytes are accepted
    # and the receipt is unchanged (first-writer-wins / exactly-once).
    again = attach_genuine_external_return(
        store, signer, target, original, seconds=2
    )
    assert again == receipt
    assert trust_row_counts(db, target) == (1, 1, 1)

    # A genuinely signed but *different* return for the same attempt is refused:
    # one durable winner only.
    conflicting = replace(directive(1), response="conflicting output")
    with pytest.raises(BackgroundModelResponseConflict):
        store.attach_late_trusted_return(
            target,
            attached_at=NOW + timedelta(seconds=3),
            directive_payload=encode_model_directive(conflicting),
            late_return_proof=signer.proof(target, conflicting),
            evidence="conflicting genuine external return",
        )
    assert trust_row_counts(db, target) == (1, 1, 1)
    assert restart(db).background_model_attempts.response_authenticity_receipt(target) == receipt
    assert resume(restart(db)).runtime.response == "finished once"
    with pytest.raises(TurnAlreadyCompleted):
        resume(restart(db))


def test_forged_local_return_cannot_poison_a_later_genuine_external_return(tmp_path):
    """C3 matrix property 25, expressed against the real store.

    A local caller that fabricates a completion for a still-``dispatching`` attempt
    mints no trusted-return row at all, so its bytes are never recovery-eligible;
    and because the absence of a receipt row is the durable marker that the local
    provenance was never externally proven, the genuine external proof supersedes
    it instead of being blocked by it.
    """

    db, runtime, attempts, signer, _execution_id = crash_before_local_completion(
        tmp_path, 1
    )
    target = attempts[-1].attempt_id
    store = runtime.background_model_attempts
    assert store.get(target).state == "dispatching"
    assert trust_row_counts(db, target) == (0, 0, 0)

    # Attack: fabricate a live completion using only caller-supplied bytes.
    forged = replace(directive(1), response="forged local completion")
    store.record_response(
        target, returned_at=NOW + timedelta(seconds=2), directive=forged
    )
    assert store.get(target).state == "response_returned"
    # ...and it minted NOTHING: no receipt, no handoff, no staged exact response.
    assert trust_row_counts(db, target) == (0, 0, 0)
    assert store.staged_response(target) is None
    assert store.response_authenticity_receipt(target) is None

    # The genuine external proof still wins and corrects the unverified provenance.
    genuine = directive(1)
    store.attach_late_trusted_return(
        target,
        attached_at=NOW + timedelta(seconds=3),
        directive_payload=encode_model_directive(genuine),
        late_return_proof=signer.proof(target, genuine),
        evidence="genuine external return after a forged local completion",
    )
    receipt = store.response_authenticity_receipt(target)
    assert receipt is not None
    staged = store.staged_response(target)
    assert staged is not None
    assert staged.directive_payload == encode_model_directive(genuine)
    after = store.get(target)
    assert (after.provider, after.model, after.provider_request_id,
            after.response_fingerprint) == (
        receipt.provider, receipt.model, receipt.provider_request_id,
        receipt.response_fingerprint,
    )
    assert trust_row_counts(db, target) == (1, 1, 1)

    # End to end: a fresh process recovers the GENUINE bytes, never the forgery.
    result = resume(restart(db))
    assert result.runtime.response == "finished once"
    assert "forged local completion" not in str(result.runtime.response)
    with sqlite3.connect(db) as conn:
        adopted = conn.execute(
            "SELECT directive_payload FROM background_model_responses WHERE attempt_id=?",
            (target,),
        ).fetchall()
    assert len(adopted) == 1
    assert "forged local completion" not in adopted[0][0]
    with pytest.raises(TurnAlreadyCompleted):
        resume(restart(db))
    assert len(restart(db).metering.list_model_calls(subject_id="user_1")) == 2


def test_return_before_dispatch_boundary_does_not_mint_evidence(tmp_path):
    db = tmp_path / "world.db"
    store, index = world(db)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _: None)
    attempt = runtime.background_model_attempts.admit(
        subject_id="user_1", work_kind="user_turn", work_id="before-dispatch",
        wake_reason="user_interaction", model_round_index=0,
        world_revision=int(store.current_world_revision()), admitted_at=NOW)
    attempts_store = runtime.background_model_attempts

    # Corrective-003 / Route B: the strictly stronger invariant is that no local
    # mint writer exists at all -- neither the pre-Corrective-002 private helper
    # nor the Corrective-002 public live-window writer.
    for removed in ("_capture_trusted_response_return", "record_live_provider_return"):
        assert not hasattr(attempts_store, removed), removed
        assert not hasattr(type(attempts_store), removed), removed

    # The decommissioned live-window names confer nothing: driving them exactly as
    # the frozen BLK-W20-001 attack did cannot create any trusted-return row.
    with live_return_module.open_live_provider_return_window(
        attempt_id=attempt.attempt_id
    ) as window:
        live_return_module.register_handler_return(window, directive(0))
        with pytest.raises(AttributeError):
            attempts_store.record_live_provider_return(  # type: ignore[attr-defined]
                attempt.attempt_id, captured_at=NOW, directive=directive(0),
                live_window=window,
            )
    assert trust_row_counts(db, attempt.attempt_id) == (0, 0, 0)

    # The genuine external route also refuses before the provider boundary: there
    # is no durable request binding and no bound verifier to prove against.
    signer = RouteBExternalSigner()
    with pytest.raises(BackgroundModelResponseConflict):
        attempts_store.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW,
            directive_payload=encode_model_directive(directive(0)),
            late_return_proof="bglate_rsa_v1:" + route_b_verifier().key_id + ":" + "00" * 256,
            evidence="no provider boundary was ever crossed",
        )
    assert attempts_store.outbound_request_binding(attempt.attempt_id) is None
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM background_model_return_handoffs WHERE attempt_id=?",
                            (attempt.attempt_id,)).fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM background_model_response_receipts WHERE attempt_id=?",
                            (attempt.attempt_id,)).fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM background_model_responses WHERE attempt_id=?",
                            (attempt.attempt_id,)).fetchone()[0] == 0


def test_metered_valid_handoff_replay_does_not_duplicate_completion(tmp_path):
    db, _runtime, attempts, _, _ = crash_at_return(tmp_path, 2)
    first = restart(db)
    resume(first)
    with pytest.raises(TurnAlreadyCompleted):
        resume(restart(db))
    after = restart(db)
    assert len(after.metering.list_model_calls(subject_id="user_1")) == 3
    assert len(after.background_model_attempts.list_for_work(subject_id="user_1", work_kind="user_turn",
        work_id=after.turn_executions.execution_id_for(subject_id="user_1", session_id="trusted-session", turn_index=1))) == 3
    # Route B: only the externally-proven round carries trusted-return rows; the
    # two live-completed rounds carry none, and replaying never adds any.
    assert trust_row_counts(db, attempts[-1].attempt_id) == (1, 1, 1)
    for earlier in attempts[:-1]:
        assert trust_row_counts(db, earlier.attempt_id) == (0, 0, 0)


def test_durable_output_before_outer_ack_only_completes_mechanical_receipt(tmp_path, monkeypatch):
    db = tmp_path / "world.db"
    store, index = world(db)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _: directive(0))
    def die_before_ack(**_kwargs):
        raise RuntimeError("after output before ACK")
    monkeypatch.setattr(runtime.turn_executions, "complete", die_before_ack)
    with pytest.raises(RuntimeError, match="after output before ACK"):
        resume(runtime)
    before_meters = runtime.metering.list_model_calls(subject_id="user_1")
    before_revision = store.current_world_revision()
    fresh = restart(db)
    with pytest.raises(TurnAlreadyCompleted):
        resume(fresh)
    assert fresh.metering.list_model_calls(subject_id="user_1") == before_meters
    assert store.current_world_revision() == before_revision
    assert fresh.inspect_turn_execution(session_id="trusted-session", turn_index=1,
        user_input="complete exactly once", occurred_at=NOW).state == "completed"
    with pytest.raises(TurnAlreadyCompleted):
        resume(restart(db))
    # Route B: a live local completion still mints no trusted-return row at all.
    execution_id = fresh.turn_executions.execution_id_for(
        subject_id="user_1", session_id="trusted-session", turn_index=1)
    live_attempt = fresh.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind="user_turn", work_id=execution_id)[-1]
    assert trust_row_counts(db, live_attempt.attempt_id) == (0, 0, 0)


def _child_kill_after_round_one(db_path, conn_pipe):
    import os
    import signal
    from test_core_background_trusted_return_recovery_001 import seed_anchor, watch_call
    store, index = world(db_path)
    seed_anchor(store)
    index.catch_up()

    class PipeSigner:
        """External side in the parent process: child only publishes public scope."""

        def accept_return_context(self, snapshot, context):
            conn_pipe.send(context.model_dump(mode="json"))

    def provider(snapshot):
        return directive(snapshot.round_index,
                         call=watch_call(0) if snapshot.round_index == 0 else None)
    runtime = FusedTurnRuntime(
        store=store, index=index, model_handler=provider,
        late_return_verifier=route_b_verifier(),
        external_return_observer=PipeSigner(),
    )
    original = runtime.cognitive_runtime.model_response_recorder
    def recorder(snapshot, returned):
        if snapshot.round_index == 1:
            conn_pipe.close()
            os.kill(os.getpid(), signal.SIGKILL)
        original(snapshot, returned)
    runtime.cognitive_runtime.model_response_recorder = recorder
    try:
        resume(runtime)
    except BaseException:
        import traceback
        with open(db_path + ".child-trace", "w") as trace:
            traceback.print_exc(file=trace)
        raise


def test_real_sigkill_after_later_round_trusted_handoff(tmp_path):
    """Real SIGKILL + genuine external proof recovers exactly once (Route B)."""

    import multiprocessing
    import signal
    from aios_core.runtime.late_return import LateReturnSigningContext

    db = tmp_path / "world.db"
    # Initialize the World before fork, but leave FTS/index projection creation
    # to the child. Forking an open SQLite FTS connection can yield intermittent
    # disk I/O errors before the tested trusted-return boundary is reached.
    from aios_core.storage.sqlite_store import SQLiteWorldStore
    SQLiteWorldStore(db)
    ctx = multiprocessing.get_context("fork")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    child = ctx.Process(target=_child_kill_after_round_one, args=(str(db), child_conn))
    child.start()
    child.join(30)
    trace = db.with_suffix(".db.child-trace")
    assert child.exitcode == -signal.SIGKILL, (
        f"child exit={child.exitcode} trace={trace.read_text() if trace.exists() else 'none'}"
    )

    contexts = []
    while parent_conn.poll(5):
        contexts.append(LateReturnSigningContext(**parent_conn.recv()))
    assert len(contexts) == 2, contexts
    # The killed round is the second dispatch; its public signing scope survived
    # process death because Core persisted the bound verifier before dispatch.
    signing_context = contexts[-1]

    fresh = restart(db)
    target = signing_context.attempt_id
    # Route B: the fresh process holds NO local mint authority. The only way this
    # attempt can ever return is a genuine external signature.
    assert not hasattr(fresh.background_model_attempts, "record_live_provider_return")
    assert trust_row_counts(db, target) == (0, 0, 0)

    signer = RouteBExternalSigner()
    signer.contexts[target] = signing_context
    genuine = directive(1)
    attach_genuine_external_return(
        fresh.background_model_attempts, signer, target, genuine, seconds=30
    )

    result = resume(restart(db))
    assert result.runtime.response == "finished once"
    assert trust_row_counts(db, target) == (1, 1, 1)
    meters = restart(db).metering.list_model_calls(subject_id="user_1")
    assert len(meters) == 2
    with pytest.raises(TurnAlreadyCompleted):
        resume(restart(db))
    assert len(restart(db).metering.list_model_calls(subject_id="user_1")) == 2
