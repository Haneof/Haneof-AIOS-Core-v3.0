"""IA-ADV-D: durable database tamper must be re-verified and rejected on recovery.

Attacker model for this file: full read/write access to the runtime SQLite file
EXCEPT knowledge of the store-private HMAC authority secret (the root key row is
the trust root; tampering DATA rows must still fail closed before downstream
effects even after restart).
"""

from __future__ import annotations

import pytest

from ia_helpers import (
    IAProcessDeath,
    NOW,
    authority_secret,
    bind_handler,
    capture_return,
    crash_wake,
    directive,
    effect_snapshot,
    emit_wake,
    reopen,
    sql_exec,
    sql_rows,
    stage,
    wake_ref,
    world,
)

from aios_core.runtime.turn_runtime import FusedTurnRuntime
from datetime import timedelta


def _completed_setup(tmp_path, key: str, *, db_name: str):
    """Crash -> trusted receipt -> stage -> return artifacts for tamper/restart."""

    store, index, db = world(tmp_path, db_name)
    exact = directive(f"provider-request-{key}", response="durable exact bytes")
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: exact)
    signal = emit_wake(runtime, key=key)

    def die_after_receipt(snapshot, d):
        raise IAProcessDeath("ia death after receipt before provenance")

    runtime.cognitive_runtime.model_response_recorder = die_after_receipt
    with pytest.raises(IAProcessDeath, match="ia death"):
        runtime.run_wake(wake_ref=wake_ref(signal), now=NOW)
    attempt = runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    receipt = runtime.background_model_attempts.response_authenticity_receipt(
        attempt.attempt_id
    )
    assert receipt is not None
    stage(
        runtime,
        work_kind="wake",
        work_id=signal.wake_id,
        round_index=0,
        d=exact,
        authenticity_proof=receipt.authenticity_proof,
    )
    assert attempt is not None
    return db, signal, attempt, exact, receipt


def _recovery_must_fail_closed(db, key: str):
    """Restart + run_wake recovery must reject and apply zero effects."""

    from aios_core.contracts.enums import ObjectType
    from aios_core.contracts.refs import ObjectRef

    store, index = reopen(db)
    state_before = {
        "world_revision": int(store.current_world_revision()),
        "tasks": tuple(store.list_payloads(object_type=ObjectType.TASK, subject_id="user_1")),
        "assistant": tuple(
            p
            for p in store.list_payloads(object_type=ObjectType.OBSERVATION, subject_id="user_1")
            if (p.get("metadata") or {}).get("role") == "assistant"
        ),
        "meters": tuple(store.list_payloads(object_type=ObjectType.WAKE, subject_id="user_1")),
    }
    meters_before = len(sql_rows(db, "SELECT 1 FROM metering_records"))

    def must_not_redispatch(_s):
        raise AssertionError("provider must never be redispatched during recovery")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=must_not_redispatch)
    running = [
        payload
        for payload in store.list_payloads(object_type=ObjectType.WAKE, subject_id="user_1")
        if payload.get("wake_state") == "running"
    ]
    assert running, "probe requires a still-running wake"
    try:
        runtime.run_wake(
            wake_ref=ObjectRef(
                object_id=str(running[0]["object_id"]),
                revision=int(running[0]["revision"]),
            ),
            now=NOW + timedelta(minutes=5),
        )
    except AssertionError:
        raise
    except Exception:
        pass
    else:
        raise AssertionError("tampered durable state was ACCEPTED by recovery")

    state_after = {
        "world_revision": int(store.current_world_revision()),
        "tasks": tuple(store.list_payloads(object_type=ObjectType.TASK, subject_id="user_1")),
        "assistant": tuple(
            p
            for p in store.list_payloads(object_type=ObjectType.OBSERVATION, subject_id="user_1")
            if (p.get("metadata") or {}).get("role") == "assistant"
        ),
        "meters": tuple(store.list_payloads(object_type=ObjectType.WAKE, subject_id="user_1")),
    }
    assert state_after == state_before, "tampered recovery mutated World state"
    assert len(sql_rows(db, "SELECT 1 FROM metering_records")) == meters_before, (
        "tampered recovery mutated metering"
    )


def test_adv_d1_tamper_receipt_proof_then_restart_rejected(tmp_path):
    db, signal, attempt, exact, receipt = _completed_setup(tmp_path, "d1", db_name="d1.db")
    sql_exec(
        db,
        "UPDATE background_model_response_receipts SET authenticity_proof=? WHERE attempt_id=?",
        ("bgresponse_v1_" + "0" * 64, attempt.attempt_id),
    )
    _recovery_must_fail_closed(db, "d1")


def test_adv_d2_tamper_receipt_payload_sha_then_restart_rejected(tmp_path):
    db, signal, attempt, exact, receipt = _completed_setup(tmp_path, "d2", db_name="d2.db")
    sql_exec(
        db,
        "UPDATE background_model_response_receipts SET payload_sha256=? WHERE attempt_id=?",
        ("f" * 64, attempt.attempt_id),
    )
    _recovery_must_fail_closed(db, "d2")


def test_adv_d3_tamper_receipt_provider_identity_then_restart_rejected(tmp_path):
    for field in ("provider", "model", "provider_request_id"):
        db, signal, attempt, exact, receipt = _completed_setup(
            tmp_path, f"d3-{field}", db_name=f"d3-{field}.db"
        )
        sql_exec(
            db,
            f"UPDATE background_model_response_receipts SET {field}=? WHERE attempt_id=?",
            ("tampered-" + field, attempt.attempt_id),
        )
        _recovery_must_fail_closed(db, f"d3-{field}")


def test_adv_d4_tamper_receipt_binding_rows_then_restart_rejected(tmp_path):
    for field in (
        "subject_id",
        "work_kind",
        "work_id",
        "model_round_index",
        "outbound_request_fingerprint",
        "relay_id",
    ):
        value: object = "tampered-" + field
        if field == "model_round_index":
            value = 7
        if field == "work_kind":
            value = "periodic_review"
        db, signal, attempt, exact, receipt = _completed_setup(
            tmp_path, f"d4-{field}", db_name=f"d4-{field}.db"
        )
        sql_exec(
            db,
            f"UPDATE background_model_response_receipts SET {field}=? WHERE attempt_id=?",
            (value, attempt.attempt_id),
        )
        _recovery_must_fail_closed(db, f"d4-{field}")


def test_adv_d5_tamper_staged_rows_then_restart_rejected(tmp_path):
    for field in (
        "directive_payload",
        "payload_sha256",
        "authenticity_proof",
        "response_fingerprint",
    ):
        value = "tampered-" + field
        if field == "response_fingerprint":
            value = "e" * 64
        if field == "authenticity_proof":
            value = "bgresponse_v1_" + "1" * 64
        db, signal, attempt, exact, receipt = _completed_setup(
            tmp_path, f"d5-{field}", db_name=f"d5-{field}.db"
        )
        sql_exec(
            db,
            f"UPDATE background_model_responses SET {field}=? WHERE attempt_id=?",
            (value, attempt.attempt_id),
        )
        _recovery_must_fail_closed(db, f"d5-{field}")


def test_adv_d6_nullify_staged_proof_then_restart_rejected(tmp_path):
    """Historical/NULL-proof staged rows must stay unusable (fail closed)."""

    db, signal, attempt, exact, receipt = _completed_setup(tmp_path, "d6", db_name="d6.db")
    sql_exec(
        db,
        "UPDATE background_model_responses SET authenticity_proof=NULL WHERE attempt_id=?",
        (attempt.attempt_id,),
    )
    _recovery_must_fail_closed(db, "d6")


def test_adv_d7_tamper_attempt_provenance_then_restart_rejected(tmp_path):
    db, signal, attempt, exact, receipt = _completed_setup(tmp_path, "d7", db_name="d7.db")
    sql_exec(
        db,
        "UPDATE background_model_attempts SET response_fingerprint=? WHERE attempt_id=?",
        ("d" * 64, attempt.attempt_id),
    )
    _recovery_must_fail_closed(db, "d7")


def test_adv_d8_tamper_staged_bytes_alone_without_hash_change_rejected(tmp_path):
    db, signal, attempt, exact, receipt = _completed_setup(tmp_path, "d8", db_name="d8.db")
    sql_exec(
        db,
        "UPDATE background_model_responses SET directive_payload=? WHERE attempt_id=?",
        (
            '{"capability_calls": [], "response": "evil", "silence": true, '
            '"usage": null, "provenance": null}',
            attempt.attempt_id,
        ),
    )
    _recovery_must_fail_closed(db, "d8")
