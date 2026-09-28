"""IA-ADV-E: store-private HMAC authority lifecycle must stay single, durable,
and fail-closed when missing or invalid."""

from __future__ import annotations

import shutil

from ia_helpers import (
    NOW,
    assert_rejected_without_mutation,
    authority_secret,
    capture_return,
    crash_wake,
    directive,
    reopen,
    sql_exec,
    sql_rows,
    stage,
    world,
)

from aios_core.runtime.background_attempt import BackgroundModelAttemptStore
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


def test_adv_e1_fresh_db_has_exactly_one_authority_and_restart_preserves_it(tmp_path):
    store, index, db = world(tmp_path, "e1.db")
    secret1 = authority_secret(db)
    assert secret1 is not None and len(bytes.fromhex(secret1)) == 32
    rows = sql_rows(db, "SELECT * FROM background_model_authenticity_authority")
    assert len(rows) == 1 and rows[0]["authority_id"] == "trusted-return-v1"

    reopen(db)  # restart
    secret2 = authority_secret(db)
    assert secret2 == secret1, "restart regenerated the durable authority"
    rows = sql_rows(db, "SELECT * FROM background_model_authenticity_authority")
    assert len(rows) == 1


def test_adv_e2_two_runtime_instances_share_one_durable_authority(tmp_path):
    store_a, index_a, db = world(tmp_path, "e2.db")
    runtime_a = FusedTurnRuntime(store=store_a, index=index_a, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime_a, key="e2")
    genuine = directive("provider-request-e2", response="shared authority bytes")
    receipt = capture_return(runtime_a, attempt.attempt_id, genuine)

    store_b, index_b = reopen(db)
    runtime_b = FusedTurnRuntime(store=store_b, index=index_b, model_handler=lambda _s: None)
    # Instance B must be able to verify a receipt minted by instance A.
    stage(
        runtime_b,
        work_kind="wake",
        work_id=signal.wake_id,
        round_index=0,
        d=genuine,
        authenticity_proof=receipt.authenticity_proof,
    )


def test_adv_e3_authority_row_deleted_fails_closed(tmp_path):
    store, index, db = world(tmp_path, "e3.db")
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="e3")
    genuine = directive("provider-request-e3", response="bytes")
    receipt = capture_return(runtime, attempt.attempt_id, genuine)

    sql_exec(
        db,
        "DELETE FROM background_model_authenticity_authority WHERE authority_id='trusted-return-v1'",
    )
    exc = assert_rejected_without_mutation(
        runtime,
        attempt,
        lambda: stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            d=genuine,
            authenticity_proof=receipt.authenticity_proof,
        ),
    )
    assert exc is not None

    # Even after re-initialization (fresh random key injected), old receipts must
    # not verify under the new authority: fail closed, never accept stale proofs.
    reopen(db)
    store2, index2 = reopen(db)
    runtime2 = FusedTurnRuntime(store=store2, index=index2, model_handler=lambda _s: None)
    exc = assert_rejected_without_mutation(
        runtime2,
        attempt,
        lambda: stage(
            runtime2,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            d=genuine,
            authenticity_proof=receipt.authenticity_proof,
        ),
    )
    assert exc is not None


def test_adv_e4_invalid_authority_secret_fails_closed(tmp_path):
    for bad_value in ("zz-not-hex", "00" * 31, "00" * 33, ""):
        store, index, db = world(tmp_path, f"e4-{len(bad_value)}x{abs(hash(bad_value)) % 7}.db")
        runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
        signal, attempt = crash_wake(runtime, key=f"e4-{bad_value[:2]}-{len(bad_value)}")
        genuine = directive("provider-request-e4", response="bytes")
        receipt = capture_return(runtime, attempt.attempt_id, genuine)
        sql_exec(
            db,
            "UPDATE background_model_authenticity_authority SET secret_hex=? "
            "WHERE authority_id='trusted-return-v1'",
            (bad_value,),
        )
        exc = assert_rejected_without_mutation(
            runtime,
            attempt,
            lambda: stage(
                runtime,
                work_kind="wake",
                work_id=signal.wake_id,
                round_index=0,
                d=genuine,
                authenticity_proof=receipt.authenticity_proof,
            ),
        )
        assert exc is not None


def test_adv_e5_backup_restore_preserves_receipt_verification(tmp_path):
    store, index, db = world(tmp_path, "e5.db")
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="e5")
    genuine = directive("provider-request-e5", response="backed up bytes")
    receipt = capture_return(runtime, attempt.attempt_id, genuine)

    backup = tmp_path / "e5-backup.db"
    shutil.copyfile(db, backup)

    # Restore into a brand-new world path and verify the original receipt.
    restored = tmp_path / "e5-restored.db"
    shutil.copyfile(backup, restored)
    store2, index2 = reopen(restored)
    runtime2 = FusedTurnRuntime(store=store2, index=index2, model_handler=lambda _s: None)
    stage(
        runtime2,
        work_kind="wake",
        work_id=signal.wake_id,
        round_index=0,
        d=genuine,
        authenticity_proof=receipt.authenticity_proof,
    )


def test_adv_e6_concurrent_initialization_produces_single_key(tmp_path):
    db = tmp_path / "e6.db"
    store1 = SQLiteWorldStore(db)
    store2 = SQLiteWorldStore(db)  # second instance during initialization
    BackgroundModelAttemptStore(store1)
    BackgroundModelAttemptStore(store2)
    rows = sql_rows(db, "SELECT * FROM background_model_authenticity_authority")
    assert len(rows) == 1, f"authority key raced into multiple rows: {rows!r}"
