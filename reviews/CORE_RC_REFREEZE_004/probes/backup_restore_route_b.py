#!/usr/bin/env python3
"""Backup/restore/rebuild proof for trusted-return recovery state.

Runs only against the exact frozen software worktree supplied in
AIOS_RC_TARGET_ROOT. The disposable World contains a real trusted-return receipt,
exact handoff bytes, a dispatched-but-not-yet-recorded later turn, durable meter
state, World operations, and idempotency rows before it is backed up.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from typing import Any

import aios_core
from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.headless.core import HeadlessConfig
from aios_core.headless.recovery import backup_world, rebuild_index, recovery_status, restore_world
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
    TurnAlreadyCompleted,
)
from aios_core.runtime.background_attempt import (
    BackgroundModelResponseConflict,
    encode_model_directive,
)
from aios_core.runtime.late_return import (
    LATE_RETURN_PROOF_PREFIX,
    LateReturnSigningContext,
    LateReturnVerifier,
    late_return_message,
)
from aios_core.runtime.live_return import (
    LOCAL_LIVE_RETURN_AUTHORITY_DECOMMISSIONED,
    live_return_authority_snapshot,
)
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)


class SimulatedProcessDeath(BaseException):
    """Crash boundary after trusted receipt commit and before response recording."""


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _logical_table_hashes(db_path: Path) -> dict[str, str]:
    """Hash table definitions and all logical rows without emitting payloads/secrets."""
    with sqlite3.connect(db_path) as conn:
        definitions = conn.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        result: dict[str, str] = {}
        for name, create_sql in definitions:
            escaped = str(name).replace('"', '""')
            try:
                rows = conn.execute(f'SELECT rowid, * FROM "{escaped}" ORDER BY rowid').fetchall()
            except sqlite3.OperationalError:
                rows = conn.execute(f'SELECT * FROM "{escaped}"').fetchall()
                rows = sorted(rows, key=lambda row: json.dumps(_jsonable(row), sort_keys=True))
            payload = {
                "create_sql": create_sql,
                "rows": [_jsonable(row) for row in rows],
            }
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            result[str(name)] = hashlib.sha256(encoded).hexdigest()
        sequence = conn.execute(
            "SELECT name, seq FROM sqlite_sequence ORDER BY name"
        ).fetchall() if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
        ).fetchone() else []
        if sequence:
            result["sqlite_sequence"] = hashlib.sha256(
                json.dumps(sequence, separators=(",", ":")).encode()
            ).hexdigest()
        return result


def _world_and_index(world_path: Path, index_path: Path) -> tuple[SQLiteWorldStore, WorldSearchIndex]:
    store = SQLiteWorldStore(world_path)
    index = WorldSearchIndex(index_path, store=store)
    index.rebuild()
    return store, index


def _seed_anchor(store: SQLiteWorldStore) -> None:
    moment = NOW - timedelta(hours=2)
    anchor = Observation(
        object_id="rc004_trusted_return_anchor",
        subject_id="user_1",
        occurred=TemporalExtent.point(moment),
        learned_at=moment,
        recorded_at=moment,
        created_by="rc-refreeze-003-backup-probe",
        source_kind="conversation",
        modality="text",
        value="A durable, disposable anchor for trusted-return backup verification.",
        metadata={"dimension": "dim:rc004_backup_probe"},
    )
    store.commit(
        [anchor],
        OperationRequest(
            operation_name="rc004.backup_probe.seed",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed a disposable World before trusted-return backup probe",
            idempotency_key="rc004-backup-probe-seed",
            source_class=SourceClass.USER,
        ),
    )


def _watch_call() -> CapabilityCall:
    return CapabilityCall(
        name="create_attention_watch",
        call_id="rc004-backup-probe-watch",
        arguments={
            "title": "rc004 backup probe watch",
            "dimensions": ["dim:rc004_backup_probe"],
            "reason_refs": [{"object_id": "rc004_trusted_return_anchor", "revision": 1}],
            "source_kind": "conversation",
            "modality": "text",
            "priority": 40,
            "cooldown_seconds": 60,
        },
    )


def _directive(round_index: int) -> ModelDirective:
    request_id = f"rc004-backup-probe-request-{round_index}"
    common = {
        "usage": ModelUsage(
            input_tokens=5,
            output_tokens=3,
            total_tokens=8,
            provider="rc004-disposable-provider",
            model="deterministic-backup-probe",
            request_id=request_id,
        ),
        "provenance": ModelCallProvenance(
            provider="rc004-disposable-provider",
            model="deterministic-backup-probe",
            request_id=request_id,
        ),
    }
    if round_index == 0:
        return ModelDirective(
            response=None,
            capability_calls=(_watch_call(),),
            **common,
        )
    return ModelDirective(response="trusted return survived backup and restore", **common)


_RSA_N = int(
    "f0d13bbf304da61eac4461bc8cd74d124b711b43092ca325c842452027ad9772"
    "49d5246a0b9ca215a62bac1461f1f618526cc2755cf1b4e988dd9e6db0996b0e"
    "970e8ed70b9a19507f3dff5f57738e72ac9d88861d0a628dcec6f75a75676fa6"
    "55eea0ba0d57a9f8d6c3cead1bdb28600322155de8b52a901e9774c70fff26c8"
    "42a0c3588fccf402553e93d7313a3537336e8387bb86b2094ed02669bdb239a3"
    "ac1545e9fe4d32ba20bbd0384457516e4cf66d730bbffc346ba6cdf45e2f2b40"
    "039488880794dec8d87f020a683d4e2e904ed4cf5ff71126f1b5afce184aab46"
    "fa00e8abb7561bda80d9eb07b3e3f4ae77ef41e904d0d6046f635abc072d81bb",
    16,
)
_RSA_D = int(
    "10df98401d3253a1729098088e15c7e0b0488c9075e41aca5aedc9ca26fd92ce"
    "ff3d5fffce307b6ae8e9c674e727fd065740279ff1933e09defd284ca74318ad3"
    "d085819d94642dfd10a970a272681a4a753a26d433ba70c28a0e853fe45f11cc"
    "688a1da6774ed03f28865c2db60cfc36a74c8ea7b93b617c30cf9b1b8fd37ca"
    "4d95137f1deb459720bca1c3a56d52a70b178cdc1fc645a49ced075fc2f2d87b"
    "da9150cdea71d1e2c360d95211cc97c703ec38db443c3b31b5d7e197ae6785c4"
    "afff79efc98b684d7cebf129189d89ee51f2115df40217be44465a2c79393bb2"
    "f126f920c9fab3283196c859d08f24eae952be5ba02f92e8683bb8249352df81",
    16,
)
_RSA_E = 65537
_SHA256_DER = bytes.fromhex("3031300d060960864801650304020105000420")


def _verifier() -> LateReturnVerifier:
    return LateReturnVerifier(
        key_id="rc004-external-backup-key",
        algorithm="rsa-pkcs1v15-sha256",
        modulus_hex=f"{_RSA_N:x}",
        public_exponent=_RSA_E,
    )


def _rsa_sign(message: bytes, key_id: str) -> str:
    digest_info = _SHA256_DER + hashlib.sha256(message).digest()
    size = (_RSA_N.bit_length() + 7) // 8
    padding = b"\xff" * (size - len(digest_info) - 3)
    encoded = b"\x00\x01" + padding + b"\x00" + digest_info
    signature = pow(int.from_bytes(encoded, "big"), _RSA_D, _RSA_N).to_bytes(size, "big")
    return f"{LATE_RETURN_PROOF_PREFIX}{key_id}:{signature.hex()}"


class ExternalSigner:
    """Test-only external authority. Core receives only public verifier material."""

    def __init__(self) -> None:
        self.contexts: dict[str, LateReturnSigningContext] = {}

    def accept_return_context(self, snapshot: Any, context: LateReturnSigningContext) -> None:
        if snapshot.model_attempt_id != context.attempt_id:
            raise AssertionError("external signing context attempt identity mismatch")
        self.contexts[context.attempt_id] = context

    def proof(self, owner_attempt_id: str, directive: ModelDirective) -> str:
        context = self.contexts[owner_attempt_id]
        payload = encode_model_directive(directive)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        fields = {
            **context.scope_fields(),
            "provider": directive.provenance.provider,
            "model": directive.provenance.model,
            "provider_request_id": directive.provenance.request_id,
            "response_fingerprint": digest,
            "payload_sha256": digest,
        }
        return _rsa_sign(late_return_message(**fields), context.verifier_key_id)


def _snapshot_details(db_path: Path) -> dict[str, Any]:
    with sqlite3.connect(db_path) as conn:
        names = {
            str(row[0])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        required = {
            "world_commits",
            "object_revisions",
            "operations",
            "idempotency_records",
            "background_model_attempts",
            "background_model_request_bindings",
            "background_model_return_handoffs",
            "background_model_return_verifiers",
            "background_model_response_receipts",
            "background_model_responses",
            "metering_records",
        }
        missing = sorted(required - names)
        if missing:
            raise AssertionError(f"expected durable recovery tables missing: {missing}")
        retired_local_authority = {
            "background_model_authenticity_authority",
            "background_model_return_capabilities",
        }
        unexpectedly_present = sorted(retired_local_authority & names)
        if unexpectedly_present:
            raise AssertionError(
                "retired local trusted-return authority tables unexpectedly present: "
                f"{unexpectedly_present}"
            )
        counts = {
            table: int(conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])
            for table in sorted(required)
        }
        return {
            "tables": sorted(required),
            "row_counts": counts,
            "retired_local_authority_absent": True,
        }


def main() -> int:
    target = _assert_target_import()
    report: dict[str, Any] = {
        "target_root": str(target),
        "aios_core_import": str(Path(aios_core.__file__).resolve()),
        "real_provider_used": False,
        "resident_fixture_used": False,
        "external_private_key_held_by_core": False,
    }

    with tempfile.TemporaryDirectory(prefix="aios-rc-refreeze-004-backup-") as raw:
        root = Path(raw)
        source_world = root / "source-world.sqlite"
        source_index = root / "source-index.sqlite"
        store, index = _world_and_index(source_world, source_index)
        _seed_anchor(store)
        index.catch_up()

        signer = ExternalSigner()
        dispatched_rounds: list[int] = []

        def provider(snapshot: Any) -> ModelDirective:
            round_index = int(snapshot.round_index)
            dispatched_rounds.append(round_index)
            if round_index == 0:
                return _directive(0)
            raise SimulatedProcessDeath("provider process lost after durable dispatch")

        runtime = FusedTurnRuntime(
            store=store,
            index=index,
            model_handler=provider,
            late_return_verifier=_verifier(),
            external_return_observer=signer,
        )
        try:
            runtime.run_turn(
                session_id="rc004-backup-session",
                turn_index=1,
                user_input="recover exact genuine trusted return from a backup",
                occurred_at=NOW,
            )
        except SimulatedProcessDeath:
            pass
        else:
            raise AssertionError("fault injection did not stop at the provider boundary")

        execution_id = runtime.turn_executions.execution_id_for(
            subject_id="user_1",
            session_id="rc004-backup-session",
            turn_index=1,
        )
        attempts = runtime.background_model_attempts.list_for_work(
            subject_id="user_1",
            work_kind="user_turn",
            work_id=execution_id,
        )
        if [attempt.model_round_index for attempt in attempts] != [0, 1]:
            raise AssertionError("expected two exact model-round attempts before backup")
        if attempts[0].state != "metered" or attempts[1].state not in {"dispatching", "in_doubt"}:
            raise AssertionError(f"unexpected pre-return attempt states: {[a.state for a in attempts]}")
        if dispatched_rounds != [0, 1]:
            raise AssertionError(f"unexpected provider dispatch history: {dispatched_rounds}")
        final_attempt = attempts[-1]
        if final_attempt.attempt_id not in signer.contexts:
            raise AssertionError("external signer did not receive the durable signing context")

        final_directive = _directive(1)
        payload = encode_model_directive(final_directive)
        genuine_proof = signer.proof(final_attempt.attempt_id, final_directive)

        attempt_store_class = type(runtime.background_model_attempts)
        original_stage_exact = attempt_store_class.stage_exact_response

        def die_after_receipt_handoff_commit(self: Any, *args: Any, **kwargs: Any) -> Any:
            raise SimulatedProcessDeath("crash after receipt/handoff commit before staging")

        attempt_store_class.stage_exact_response = die_after_receipt_handoff_commit
        try:
            runtime.background_model_attempts.attach_late_trusted_return(
                final_attempt.attempt_id,
                attached_at=NOW + timedelta(seconds=10),
                directive_payload=payload,
                late_return_proof=genuine_proof,
                evidence="genuine external return before backup",
            )
        except SimulatedProcessDeath:
            pass
        else:
            raise AssertionError("partial-commit fault injection did not fire")
        finally:
            attempt_store_class.stage_exact_response = original_stage_exact

        receipt_before = runtime.background_model_attempts.response_authenticity_receipt(
            final_attempt.attempt_id
        )
        if receipt_before is None:
            raise AssertionError("genuine external trusted-return receipt was not durable")
        if runtime.background_model_attempts.staged_response(final_attempt.attempt_id) is not None:
            raise AssertionError("response was staged despite partial-commit crash")
        with sqlite3.connect(source_world) as conn:
            handoff = conn.execute(
                "SELECT directive_payload, payload_sha256, authenticity_proof "
                "FROM background_model_return_handoffs WHERE attempt_id=?",
                (final_attempt.attempt_id,),
            ).fetchone()
            verifier = conn.execute(
                "SELECT consumed_at FROM background_model_return_verifiers WHERE attempt_id=?",
                (final_attempt.attempt_id,),
            ).fetchone()
        if handoff is None or verifier is None or verifier[0] is None:
            raise AssertionError("receipt/handoff/verifier-consumption partial commit is incomplete")
        if len(runtime.metering.list_model_calls(subject_id="user_1")) != 1:
            raise AssertionError("pre-backup durable meter count must be exactly one")

        existing_tasks = [
            item
            for item in store.list_payloads(object_type=ObjectType.TASK, subject_id="user_1")
            if item.get("title") == "rc004 backup probe watch"
        ]
        if len(existing_tasks) != 1 or int(existing_tasks[0]["revision"]) != 1:
            raise AssertionError("first-round capability effect was not present exactly once")

        before_hashes = _logical_table_hashes(source_world)
        source_details = _snapshot_details(source_world)
        source_revision = int(store.current_world_revision())
        backup = root / "source-backup.sqlite"
        source_config = HeadlessConfig(world_path=source_world, index_path=source_index)
        backup_result = backup_world(source_config, backup)
        backup_sha_before = _sha256(backup)
        backup_hashes = _logical_table_hashes(backup)
        if backup_hashes != before_hashes:
            raise AssertionError("backup logical World tables differ from source")
        if int(backup_result["world_revision"]) != source_revision:
            raise AssertionError("backup revision differs from source World")

        private_hex = f"{_RSA_D:x}"
        with sqlite3.connect(backup) as conn:
            backup_dump = "\n".join(conn.iterdump())
        if private_hex in backup_dump or private_hex in backup.read_bytes().hex():
            raise AssertionError("external RSA private authority leaked into the World backup")

        restored_world = root / "restored-world.sqlite"
        restored_index = root / "restored-index.sqlite"
        restored_config = HeadlessConfig(world_path=restored_world, index_path=restored_index)
        restore_result = restore_world(restored_config, backup)
        if restore_result["index_disposition"] != "REBUILD_FROM_WORLD":
            raise AssertionError("restored index disposition is not rebuild-from-World")
        recovery_before_rebuild = recovery_status(restored_config)
        if recovery_before_rebuild["recovery_disposition"] != "REBUILD_FROM_WORLD":
            raise AssertionError("missing restored index did not take safe rebuild path")
        rebuilt = rebuild_index(restored_config)
        if int(rebuilt["index_watermark"]) != source_revision:
            raise AssertionError("rebuilt index watermark does not match restored World")

        restored_hashes = _logical_table_hashes(restored_world)
        if restored_hashes != before_hashes:
            raise AssertionError("restored logical table contents differ from pre-backup source")
        restored_details = _snapshot_details(restored_world)
        if restored_details != source_details:
            raise AssertionError("restored World/object/operation row counts differ from source")

        restored_store = SQLiteWorldStore(restored_world)
        restored_search = WorldSearchIndex(restored_index, store=restored_store)
        restored_search.catch_up()
        provider_calls_after_restore: list[int] = []

        def forbidden_provider(snapshot: Any) -> ModelDirective:
            provider_calls_after_restore.append(int(snapshot.round_index))
            raise AssertionError("recovery redispatched the model/provider")

        restored_runtime = FusedTurnRuntime(
            store=restored_store,
            index=restored_search,
            model_handler=forbidden_provider,
        )
        receipt_after = restored_runtime.background_model_attempts.response_authenticity_receipt(
            final_attempt.attempt_id
        )
        if receipt_after != receipt_before:
            raise AssertionError("trusted-return receipt did not survive supported backup/restore")
        if hasattr(restored_runtime.background_model_attempts, "record_live_provider_return"):
            raise AssertionError("restore resurrected local live-return mint authority")
        snapshot = live_return_authority_snapshot()
        if (
            not LOCAL_LIVE_RETURN_AUTHORITY_DECOMMISSIONED
            or snapshot.get("trust_conferred") is not False
            or snapshot.get("durable_trusted_return_authority")
            != "external_verifier_plus_genuine_proof_only"
        ):
            raise AssertionError(f"restore expanded local trusted-return authority: {snapshot!r}")

        forged = f"{LATE_RETURN_PROOF_PREFIX}{_verifier().key_id}:" + "00" * 256
        try:
            restored_runtime.background_model_attempts.attach_late_trusted_return(
                final_attempt.attempt_id,
                attached_at=NOW + timedelta(seconds=20),
                directive_payload=payload,
                late_return_proof=forged,
                evidence="forged proof must fail closed after restore",
            )
        except BackgroundModelResponseConflict:
            forged_refused = True
        else:
            raise AssertionError("restore accepted a forged local trusted-return proof")

        conflicting_directive = ModelDirective(
            response="conflicting genuine bytes must lose",
            usage=final_directive.usage,
            provenance=final_directive.provenance,
        )
        conflicting_payload = encode_model_directive(conflicting_directive)
        conflicting_proof = signer.proof(final_attempt.attempt_id, conflicting_directive)
        try:
            restored_runtime.background_model_attempts.attach_late_trusted_return(
                final_attempt.attempt_id,
                attached_at=NOW + timedelta(seconds=30),
                directive_payload=conflicting_payload,
                late_return_proof=conflicting_proof,
                evidence="conflicting genuine proof must lose first-writer-wins",
            )
        except BackgroundModelResponseConflict:
            conflict_refused = True
        else:
            raise AssertionError("consumed verifier accepted conflicting genuine return bytes")

        staged = restored_runtime.background_model_attempts.attach_late_trusted_return(
            final_attempt.attempt_id,
            attached_at=NOW + timedelta(seconds=40),
            directive_payload=payload,
            late_return_proof=genuine_proof,
            evidence="winning exact genuine proof retry after restore",
        )
        if staged.authenticity_proof != receipt_before.authenticity_proof:
            raise AssertionError("winning exact proof retry did not preserve canonical receipt")

        result = restored_runtime.run_turn(
            session_id="rc004-backup-session",
            turn_index=1,
            user_input="recover exact genuine trusted return from a backup",
            occurred_at=NOW,
        )
        if result.runtime.response != "trusted return survived backup and restore":
            raise AssertionError("restored exact provider bytes did not converge")
        if result.runtime.recovered_response_attempts != (final_attempt.attempt_id,):
            raise AssertionError("recovered attempt identity changed across restore")
        if provider_calls_after_restore:
            raise AssertionError(f"provider redispatched after restore: {provider_calls_after_restore}")
        if int(restored_store.current_world_revision()) <= source_revision:
            raise AssertionError("recovered turn did not advance the restored World")

        restored_search.catch_up()
        if int(restored_search.watermark()) != int(restored_store.current_world_revision()):
            raise AssertionError("restored index did not catch up to recovered World revision")
        meter_rows = restored_runtime.metering.list_model_calls(subject_id="user_1")
        if len(meter_rows) != 2:
            raise AssertionError(f"expected exactly two meter rows after recovery, got {len(meter_rows)}")
        final_tasks = [
            item
            for item in restored_store.list_payloads(object_type=ObjectType.TASK, subject_id="user_1")
            if item.get("title") == "rc004 backup probe watch"
        ]
        if len(final_tasks) != 1 or int(final_tasks[0]["revision"]) != 1:
            raise AssertionError("restored recovery duplicated the original capability effect")

        try:
            restored_runtime.run_turn(
                session_id="rc004-backup-session",
                turn_index=1,
                user_input="recover exact genuine trusted return from a backup",
                occurred_at=NOW,
            )
        except TurnAlreadyCompleted:
            pass
        else:
            raise AssertionError("completed recovered turn did not fail closed on replay")
        if len(restored_runtime.metering.list_model_calls(subject_id="user_1")) != 2:
            raise AssertionError("completed-turn replay duplicated metering")

        backup_sha_after = _sha256(backup)
        if backup_sha_after != backup_sha_before:
            raise AssertionError("restore/rebuild/recovery mutated source backup bytes")
        if _logical_table_hashes(source_world) != before_hashes:
            raise AssertionError("supported restore path mutated source World")

        report.update(
            {
                "status": "BACKUP_RESTORE_ROUTE_B_PASS",
                "source_world_revision_before_backup": source_revision,
                "restored_world_revision_before_recovery": source_revision,
                "restored_world_revision_after_recovery": int(restored_store.current_world_revision()),
                "source_backup_sha256_before": backup_sha_before,
                "source_backup_sha256_after": backup_sha_after,
                "source_backup_immutable": backup_sha_before == backup_sha_after,
                "source_logical_world_immutable": True,
                "world_object_operation_continuity": True,
                "trusted_return_receipt_continuity": receipt_after == receipt_before,
                "trusted_return_handoff_continuity": True,
                "restore_did_not_expand_trust_authority": True,
                "forged_local_proof_refused": forged_refused,
                "conflicting_genuine_proof_refused": conflict_refused,
                "winning_exact_proof_retry_recovered": True,
                "index_rebuild_watermark": int(rebuilt["index_watermark"]),
                "post_recovery_index_watermark": int(restored_search.watermark()),
                "provider_redispatch_count_after_restore": len(provider_calls_after_restore),
                "meter_rows_after_recovery": len(meter_rows),
                "capability_side_effect_count_after_recovery": len(final_tasks),
                "table_hashes_before_backup": before_hashes,
                "source_table_row_counts": source_details["row_counts"],
                "restore_disposition": restore_result["recovery_disposition"],
                "index_rebuild_disposition": rebuilt["recovery_disposition"],
            }
        )

    print("RESULT=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
