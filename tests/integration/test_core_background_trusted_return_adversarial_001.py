"""Adversarial verification of the callback-owned durable handoff.

SQL mutations simulate damaged/untrusted storage, never authorize a provider return.
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
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from test_core_background_trusted_return_recovery_001 import (
    NOW, crash_at_return, directive, world,
)


def restart(db):
    store, index = world(db)
    return FusedTurnRuntime(
        store=store, index=index,
        model_handler=lambda _snapshot: pytest.fail("no redispatch on untrusted handoff"),
    )


def resume(runtime):
    return runtime.run_turn(session_id="trusted-session", turn_index=1,
                            user_input="complete exactly once", occurred_at=NOW)


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
    with sqlite3.connect(db) as conn:
        if mutation in {"forged_directive", "altered_payload"}:
            payload = encode_model_directive(directive(1)).replace("finished once", "forged output")
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
            valid = encode_model_directive(directive(1))
            if mutation == "duplicate_top_key":
                payload = valid[:-1] + ',"response":"forged output"}'
            else:
                payload = valid.replace('"provider":"trusted-provider"', '"provider":"trusted-provider","provider":"forged"', 1)
            conn.execute("UPDATE background_model_return_handoffs SET directive_payload=?, payload_sha256=? WHERE attempt_id=?",
                         (payload, hashlib.sha256(payload.encode()).hexdigest(), target))
        elif mutation == "missing_handoff":
            conn.execute("DELETE FROM background_model_return_handoffs WHERE attempt_id=?", (target,))
        elif mutation == "corrupt_handoff_digest":
            conn.execute("UPDATE background_model_return_handoffs SET payload_sha256=? WHERE attempt_id=?", ("0" * 64, target))
        elif mutation == "corrupt_handoff_proof":
            conn.execute("UPDATE background_model_return_handoffs SET authenticity_proof=? WHERE attempt_id=?", ("0" * 64, target))
        elif mutation == "copied_handoff_from_round":
            conn.execute("UPDATE background_model_return_handoffs SET directive_payload=(SELECT directive_payload FROM background_model_return_handoffs WHERE attempt_id=?), payload_sha256=(SELECT payload_sha256 FROM background_model_return_handoffs WHERE attempt_id=?), authenticity_proof=(SELECT authenticity_proof FROM background_model_return_handoffs WHERE attempt_id=?) WHERE attempt_id=?",
                         (attempts[0].attempt_id,) * 3 + (target,))
        elif mutation == "unknown_attempt_handoff":
            conn.execute("UPDATE background_model_return_handoffs SET attempt_id=? WHERE attempt_id=?", ("unknown-attempt", target))
        elif mutation == "missing_receipt":
            conn.execute("DELETE FROM background_model_response_receipts WHERE attempt_id=?", (target,))
        elif mutation == "invalid_receipt":
            conn.execute("UPDATE background_model_response_receipts SET authenticity_proof=? WHERE attempt_id=?", ("0" * 64, target))
        conn.commit()
    fresh = restart(db)
    before_meters = fresh.metering.list_model_calls(subject_id="user_1")
    with pytest.raises((BackgroundModelResponseConflict, ValueError, TurnExecutionInDoubt)):
        resume(fresh)
    assert fresh.background_model_attempts.get(target).state == "dispatching"
    assert fresh.metering.list_model_calls(subject_id="user_1") == before_meters
    assert fresh.background_model_attempts.staged_response(target) is None


def test_same_bytes_repeated_return_is_idempotent_but_conflicting_return_rejected(tmp_path):
    db, runtime, attempts, receipt, _ = crash_at_return(tmp_path, 1)
    target = attempts[-1].attempt_id
    original = directive(1)
    again = runtime.background_model_attempts._capture_trusted_response_return(
        target, captured_at=NOW + timedelta(seconds=1), directive=original)
    assert again == receipt
    with pytest.raises(BackgroundModelResponseConflict):
        runtime.background_model_attempts._capture_trusted_response_return(
            target, captured_at=NOW + timedelta(seconds=2),
            directive=replace(directive(1), response="conflicting output"))
    assert restart(db).background_model_attempts.response_authenticity_receipt(target) == receipt
    assert resume(restart(db)).runtime.response == "finished once"
    with pytest.raises(TurnAlreadyCompleted):
        resume(restart(db))


def test_return_before_dispatch_boundary_does_not_mint_evidence(tmp_path):
    db = tmp_path / "world.db"
    store, index = world(db)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _: None)
    attempt = runtime.background_model_attempts.admit(
        subject_id="user_1", work_kind="user_turn", work_id="before-dispatch",
        wake_reason="user_interaction", model_round_index=0,
        world_revision=int(store.current_world_revision()), admitted_at=NOW)
    with pytest.raises(BackgroundModelResponseConflict, match="before the provider boundary"):
        runtime.background_model_attempts._capture_trusted_response_return(
            attempt.attempt_id, captured_at=NOW, directive=directive(0))
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM background_model_return_handoffs WHERE attempt_id=?",
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


def _child_kill_after_round_one(db_path):
    import os
    import signal
    from test_core_background_trusted_return_recovery_001 import seed_anchor, watch_call
    store, index = world(db_path)
    seed_anchor(store)
    index.catch_up()
    def provider(snapshot):
        return directive(snapshot.round_index,
                         call=watch_call(0) if snapshot.round_index == 0 else None)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=provider)
    original = runtime.cognitive_runtime.model_response_recorder
    def recorder(snapshot, returned):
        if snapshot.round_index == 1:
            os.kill(os.getpid(), signal.SIGKILL)
        original(snapshot, returned)
    runtime.cognitive_runtime.model_response_recorder = recorder
    resume(runtime)


def test_real_sigkill_after_later_round_trusted_handoff(tmp_path):
    import multiprocessing
    import signal
    db = tmp_path / "world.db"
    world(db)
    child = multiprocessing.get_context("fork").Process(
        target=_child_kill_after_round_one, args=(str(db),))
    child.start()
    child.join(30)
    assert child.exitcode == -signal.SIGKILL
    fresh = restart(db)
    result = resume(fresh)
    assert result.runtime.response == "finished once"
    assert len(fresh.metering.list_model_calls(subject_id="user_1")) == 2
    with pytest.raises(TurnAlreadyCompleted):
        resume(restart(db))
