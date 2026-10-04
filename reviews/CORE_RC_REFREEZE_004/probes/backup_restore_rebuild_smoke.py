#!/usr/bin/env python3
"""CORE-RC-REFREEZE-004 §10 backup / restore / index-rebuild / authority proof.

Runs only against the exact frozen software worktree supplied in
AIOS_RC_TARGET_ROOT.  The disposable source World contains a genuinely proven
trusted return (durable external-verifier row, response receipt, exact return
handoff, staged exact response, meter and completed turn) plus two
dispatched-but-unproven attempts (one with a bound external verifier, one with
none).  The probe backs the World up, restores it into a new path, rebuilds the
projection from World truth, and then proves that the restore did not widen
trusted-return authority: forged / transplanted / verifier-less attaches stay
refused, an exact genuine replay stays idempotent, and a genuine proof still
completes its turn exactly once without provider redispatch.
"""
from __future__ import annotations

from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from typing import Any

import aios_core
from aios_core.headless.core import HeadlessConfig
from aios_core.headless.recovery import (
    backup_world,
    rebuild_index,
    recovery_status,
    restore_world,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import BackgroundModelResponseConflict, TurnAlreadyCompleted
from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


def _assert_target_import() -> Path:
    raw_target = os.environ.get("AIOS_RC_TARGET_ROOT")
    if not raw_target:
        raise RuntimeError("AIOS_RC_TARGET_ROOT must identify the exact software worktree")
    target = Path(raw_target).resolve()
    module_path = Path(aios_core.__file__).resolve()
    if target not in module_path.parents:
        raise RuntimeError(
            f"wrong aios_core import: {module_path}; expected below exact target {target}"
        )
    return target


TARGET = _assert_target_import()
sys.path.insert(0, str(TARGET / "tests" / "integration"))
import test_core_background_late_trusted_return_corrective_002 as helpers  # noqa: E402

NOW = helpers.NOW
TURN_INPUT = helpers.TURN_INPUT
TRUST_TABLES = helpers.TRUST_TABLES


class ProcessDeath(BaseException):
    """Crash boundary after the durable dispatch, before any local completion."""


def open_world(db: Path, index_path: Path) -> tuple[SQLiteWorldStore, WorldSearchIndex]:
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(index_path, store=store)
    index.rebuild()
    return store, index


def dispatch_and_crash(
    db: Path,
    index_path: Path,
    *,
    session_id: str,
    verifier: Any,
    signer: Any,
):
    store, index = open_world(db, index_path)

    def crashing_handler(_snapshot: Any):
        raise ProcessDeath("simulated process death after the durable dispatch boundary")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=crashing_handler,
        subject_id="user_1",
        late_return_verifier=verifier,
        external_return_observer=signer,
    )
    try:
        runtime.run_turn(
            session_id=session_id, turn_index=1, user_input=TURN_INPUT, occurred_at=NOW
        )
    except ProcessDeath:
        pass
    execution_id = runtime.turn_executions.execution_id_for(
        subject_id="user_1", session_id=session_id, turn_index=1
    )
    attempt = runtime.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind="user_turn", work_id=execution_id
    )[-1]
    return runtime, attempt


def recovery_runtime(db: Path, index_path: Path) -> FusedTurnRuntime:
    store, index = open_world(db, index_path)
    return FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: (_ for _ in ()).throw(
            AssertionError("provider redispatch is forbidden during recovery")
        ),
        subject_id="user_1",
    )


def complete_turn(db: Path, index_path: Path, *, session_id: str):
    store, index = open_world(db, index_path)
    provider_calls: list[int] = []

    def forbidden_provider(_snapshot: Any):
        provider_calls.append(1)
        raise AssertionError("provider redispatch is forbidden during recovery")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=forbidden_provider,
        subject_id="user_1",
    )
    result = runtime.run_turn(
        session_id=session_id, turn_index=1, user_input=TURN_INPUT, occurred_at=NOW
    )
    return runtime, result, provider_calls


def db_state(db: Path) -> dict[str, dict[str, Any]]:
    """Per-table logical row counts and order-independent row hashes (no payloads)."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        state: dict[str, dict[str, Any]] = {}
        for table in tables:
            rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
            digest = hashlib.sha256()
            for row in sorted(repr(tuple(value for value in row)) for row in rows):
                digest.update(row.encode("utf-8"))
            state[table] = {"count": len(rows), "rows_sha256": digest.hexdigest()}
        return state
    finally:
        conn.close()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def meter_count(runtime: FusedTurnRuntime) -> int:
    return len(runtime.metering.list_model_calls(subject_id="user_1"))


def main() -> int:
    report: dict[str, Any] = {
        "status": "BACKUP_RESTORE_REBUILD_FAILED",
        "target_root": str(TARGET),
        "aios_core_import": str(Path(aios_core.__file__).resolve()),
        "real_provider_used": False,
        "resident_fixture_used": False,
    }
    checks: dict[str, Any] = {}

    with tempfile.TemporaryDirectory(prefix="aios-rc004-backup-") as raw:
        root = Path(raw)
        src_world = root / "source-world.sqlite"
        src_index = root / "source-index.sqlite"
        signer = helpers.ExternalSigner()
        verifier = helpers.make_verifier()

        # --- source World: one genuine external trusted return -----------------
        _, attempt1 = dispatch_and_crash(
            src_world, src_index, session_id="rc004-src-1", verifier=verifier, signer=signer
        )
        directive1 = helpers.make_directive(
            response="rc004 genuine backed-up return", request_id="rc004-1"
        )
        src_runtime = recovery_runtime(src_world, src_index)
        src_runtime.background_model_attempts.attach_late_trusted_return(
            attempt1.attempt_id,
            attached_at=NOW + timedelta(seconds=1),
            directive_payload=encode_model_directive(directive1),
            late_return_proof=signer.sign(attempt1.attempt_id, directive1),
            evidence="RC-004 §10 source World genuine external trusted return",
        )
        runtime1, result1, calls1 = complete_turn(src_world, src_index, session_id="rc004-src-1")
        checks["turn1_completed_without_redispatch"] = calls1 == [] and (
            result1.runtime.response == directive1.response
        )
        checks["turn1_recovered_attempt"] = result1.runtime.recovered_response_attempts == (
            attempt1.attempt_id,
        )
        meters_before = meter_count(runtime1)

        # --- two dispatched-but-unproven attempts ------------------------------
        _, attempt2 = dispatch_and_crash(
            src_world, src_index, session_id="rc004-src-2", verifier=verifier, signer=signer
        )
        _, attempt3 = dispatch_and_crash(
            src_world, src_index, session_id="rc004-src-3", verifier=None, signer=None
        )
        checks["attempt2_state_before_backup"] = attempt2.state
        checks["attempt3_state_before_backup"] = attempt3.state

        pre_state = db_state(src_world)
        pre_trust_rows = helpers.trust_rows(src_world)
        pre_revision = int(SQLiteWorldStore(src_world).current_world_revision())
        checks["pre_backup_trust_rows"] = list(pre_trust_rows)

        # --- backup -------------------------------------------------------------
        cfg_src = HeadlessConfig(world_path=src_world, index_path=src_index)
        backup_path = root / "backup" / "rc004-backup.sqlite"
        backup_result = backup_world(cfg_src, backup_path)
        backup_sha_before = sha256_file(backup_path)

        # --- restore into a NEW path -------------------------------------------
        rest_world = root / "restored-world.sqlite"
        rest_index = root / "restored-index.sqlite"
        cfg_rest = HeadlessConfig(world_path=rest_world, index_path=rest_index)
        restore_result = restore_world(cfg_rest, backup_path)
        backup_sha_after = sha256_file(backup_path)

        checks["backup_immutable_after_restore"] = backup_sha_before == backup_sha_after
        checks["source_world_immutable"] = db_state(src_world) == pre_state
        checks["source_backup_sha256"] = backup_sha_before
        checks["restore_revision_matches"] = int(restore_result["world_revision"]) == pre_revision
        checks["restored_state_matches_source"] = db_state(rest_world) == pre_state
        checks["restored_index_is_separate_projection"] = "search_postings" not in db_state(
            rest_world
        )
        checks["restored_trust_rows"] = list(helpers.trust_rows(rest_world))

        # --- index rebuild from World truth ------------------------------------
        status_before = recovery_status(cfg_rest)
        rebuild_result = rebuild_index(cfg_rest)
        status_after = recovery_status(cfg_rest)
        checks["index_disposition_before_rebuild"] = status_before.get("index_disposition")
        checks["index_rebuild_status"] = rebuild_result.get("status")
        checks["index_rebuild_watermark"] = rebuild_result.get("index_watermark")
        checks["index_watermark_equals_world_revision"] = int(
            status_after["index_watermark"]
        ) == pre_revision
        checks["index_lag_after_rebuild"] = status_after.get("index_lag")
        checks["safe_recovery_status"] = status_after.get("recovery_disposition")

        # --- restored runtime: trust continuity + authority not widened --------
        rest_store, rest_index_obj = open_world(rest_world, rest_index)
        rest_runtime = FusedTurnRuntime(
            store=rest_store,
            index=rest_index_obj,
            model_handler=lambda _snapshot: (_ for _ in ()).throw(
                AssertionError("provider redispatch is forbidden on the restored World")
            ),
            subject_id="user_1",
        )
        checks["local_mint_api_absent_after_restore"] = not hasattr(
            rest_store, "record_live_provider_return"
        )
        receipt1 = rest_runtime.background_model_attempts.response_authenticity_receipt(
            attempt1.attempt_id
        )
        checks["receipt_continuity"] = receipt1 is not None
        staged1 = rest_runtime.background_model_attempts.staged_response(attempt1.attempt_id)
        checks["staged_exact_response_continuity"] = (
            staged1 is not None and receipt1 is not None and staged1.authenticity_proof == receipt1.authenticity_proof
        )
        checks["verifier_consumed_continuity"] = (
            rest_runtime.background_model_attempts.late_return_verifier(attempt1.attempt_id)
            is not None
        )

        refused = []
        # forged proof shape over the exact attempt 2 scope
        try:
            rest_runtime.background_model_attempts.attach_late_trusted_return(
                attempt2.attempt_id,
                attached_at=NOW + timedelta(seconds=30),
                directive_payload=encode_model_directive(
                    helpers.make_directive(response="forged", request_id="rc004-forged")
                ),
                late_return_proof="bglate_rsa_v1:ca2-external-key:" + "00" * 256,
                evidence="RC-004 §10 forged proof after restore",
            )
        except BackgroundModelResponseConflict:
            refused.append("forged_proof")
        # transplanted genuine proof from attempt 1
        try:
            rest_runtime.background_model_attempts.attach_late_trusted_return(
                attempt2.attempt_id,
                attached_at=NOW + timedelta(seconds=31),
                directive_payload=encode_model_directive(directive1),
                late_return_proof=signer.sign(attempt1.attempt_id, directive1),
                evidence="RC-004 §10 transplanted proof after restore",
            )
        except BackgroundModelResponseConflict:
            refused.append("transplanted_proof")
        # verifier-less attempt 3 can never be given trusted bytes
        try:
            rest_runtime.background_model_attempts.attach_late_trusted_return(
                attempt3.attempt_id,
                attached_at=NOW + timedelta(seconds=32),
                directive_payload=encode_model_directive(
                    helpers.make_directive(response="no verifier", request_id="rc004-3")
                ),
                late_return_proof="bglate_rsa_v1:ca2-external-key:" + "11" * 256,
                evidence="RC-004 §10 verifier-less attempt after restore",
            )
        except BackgroundModelResponseConflict:
            refused.append("verifier_less")
        checks["post_restore_refusals"] = refused
        checks["post_restore_refusals_complete"] = refused == [
            "forged_proof",
            "transplanted_proof",
            "verifier_less",
        ]
        checks["trust_rows_unchanged_by_refusals"] = list(helpers.trust_rows(rest_world)) == list(
            pre_trust_rows
        )

        # --- genuine proof still works exactly once on the restored World ------
        directive2 = helpers.make_directive(
            response="rc004 restored genuine return", request_id="rc004-2"
        )
        rest_runtime.background_model_attempts.attach_late_trusted_return(
            attempt2.attempt_id,
            attached_at=NOW + timedelta(seconds=40),
            directive_payload=encode_model_directive(directive2),
            late_return_proof=signer.sign(attempt2.attempt_id, directive2),
            evidence="RC-004 §10 genuine proof on the restored World",
        )
        rows_after_genuine = list(helpers.trust_rows(rest_world))
        replay_outcome = rest_runtime.background_model_attempts.attach_late_trusted_return(
            attempt2.attempt_id,
            attached_at=NOW + timedelta(seconds=41),
            directive_payload=encode_model_directive(directive2),
            late_return_proof=signer.sign(attempt2.attempt_id, directive2),
            evidence="RC-004 §10 exact genuine replay",
        )
        checks["genuine_attach_trust_rows"] = rows_after_genuine
        checks["exact_genuine_replay_effect_free"] = (
            list(helpers.trust_rows(rest_world)) == rows_after_genuine
            and replay_outcome is not None
        )
        runtime2, result2, calls2 = complete_turn(rest_world, rest_index, session_id="rc004-src-2")
        checks["turn2_completed_without_redispatch"] = calls2 == [] and (
            result2.runtime.response == directive2.response
        )
        checks["meters_after_two_recoveries"] = meter_count(runtime2)
        attempt3_after = runtime2.background_model_attempts.get(attempt3.attempt_id)
        checks["turn3_state_after_restore"] = attempt3_after.state
        checks["turn3_never_proven"] = (
            attempt3_after.state in {"dispatching", "in_doubt"}
            and runtime2.background_model_attempts.response_authenticity_receipt(
                attempt3.attempt_id
            )
            is None
            and runtime2.background_model_attempts.staged_response(attempt3.attempt_id) is None
        )
        with_replay_error = None
        try:
            runtime2.run_turn(
                session_id="rc004-src-2", turn_index=1, user_input=TURN_INPUT, occurred_at=NOW
            )
        except TurnAlreadyCompleted as exc:
            with_replay_error = type(exc).__name__
        checks["completed_turn_replay_fails_closed"] = with_replay_error == "TurnAlreadyCompleted"
        checks["meters_after_completed_replay"] = meter_count(runtime2)

        report.update(
            {
                "world_revision_before_backup": pre_revision,
                "world_revision_restored": int(restore_result["world_revision"]),
                "backup_result": backup_result.get("status"),
                "restore_result": restore_result.get("status"),
                "pre_backup_table_state": {
                    name: value["count"] for name, value in sorted(pre_state.items())
                },
                "checks": checks,
            }
        )
        all_ok = (
            checks["turn1_completed_without_redispatch"]
            and checks["backup_immutable_after_restore"]
            and checks["source_world_immutable"]
            and checks["restored_state_matches_source"]
            and checks["index_watermark_equals_world_revision"]
            and checks["post_restore_refusals_complete"]
            and checks["receipt_continuity"]
            and checks["staged_exact_response_continuity"]
            and checks["turn2_completed_without_redispatch"]
            and checks["completed_turn_replay_fails_closed"]
            and checks["meters_after_two_recoveries"] == meters_before + 1
            and checks["meters_after_completed_replay"] == meters_before + 1
            and checks["turn3_never_proven"]
        )
        report["status"] = (
            "BACKUP_RESTORE_REBUILD_PASS" if all_ok else "BACKUP_RESTORE_REBUILD_FAILED"
        )
        print("RESULT=" + json.dumps(report, sort_keys=True))
        return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
