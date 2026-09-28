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
from aios_core.runtime.background_attempt import encode_model_directive
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
        object_id="rc003_trusted_return_anchor",
        subject_id="user_1",
        occurred=TemporalExtent.point(moment),
        learned_at=moment,
        recorded_at=moment,
        created_by="rc-refreeze-003-backup-probe",
        source_kind="conversation",
        modality="text",
        value="A durable, disposable anchor for trusted-return backup verification.",
        metadata={"dimension": "dim:rc003_backup_probe"},
    )
    store.commit(
        [anchor],
        OperationRequest(
            operation_name="rc003.backup_probe.seed",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed a disposable World before trusted-return backup probe",
            idempotency_key="rc003-backup-probe-seed",
            source_class=SourceClass.USER,
        ),
    )


def _watch_call() -> CapabilityCall:
    return CapabilityCall(
        name="create_attention_watch",
        call_id="rc003-backup-probe-watch",
        arguments={
            "title": "rc003 backup probe watch",
            "dimensions": ["dim:rc003_backup_probe"],
            "reason_refs": [{"object_id": "rc003_trusted_return_anchor", "revision": 1}],
            "source_kind": "conversation",
            "modality": "text",
            "priority": 40,
            "cooldown_seconds": 60,
        },
    )


def _directive(round_index: int) -> ModelDirective:
    request_id = f"rc003-backup-probe-request-{round_index}"
    common = {
        "usage": ModelUsage(
            input_tokens=5,
            output_tokens=3,
            total_tokens=8,
            provider="rc003-disposable-provider",
            model="deterministic-backup-probe",
            request_id=request_id,
        ),
        "provenance": ModelCallProvenance(
            provider="rc003-disposable-provider",
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
            "background_model_response_receipts",
            "background_model_authenticity_authority",
            "metering_records",
        }
        missing = sorted(required - names)
        if missing:
            raise AssertionError(f"expected durable recovery tables missing: {missing}")
        counts = {
            table: int(conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])
            for table in sorted(required)
        }
        return {"tables": sorted(required), "row_counts": counts}


def main() -> int:
    target = _assert_target_import()
    report: dict[str, Any] = {
        "target_root": str(target),
        "aios_core_import": str(Path(aios_core.__file__).resolve()),
        "real_provider_used": False,
        "resident_fixture_used": False,
    }

    with tempfile.TemporaryDirectory(prefix="aios-rc-refreeze-003-backup-") as raw:
        root = Path(raw)
        source_world = root / "source-world.sqlite"
        source_index = root / "source-index.sqlite"
        store, index = _world_and_index(source_world, source_index)
        _seed_anchor(store)
        index.catch_up()

        dispatched_rounds: list[int] = []

        def provider(snapshot: Any) -> ModelDirective:
            dispatched_rounds.append(int(snapshot.round_index))
            return _directive(int(snapshot.round_index))

        runtime = FusedTurnRuntime(store=store, index=index, model_handler=provider)
        original_recorder = runtime.cognitive_runtime.model_response_recorder

        def die_after_return_receipt(snapshot: Any, returned: ModelDirective) -> None:
            if int(snapshot.round_index) == 1:
                if snapshot.model_attempt_id is None:
                    raise AssertionError("returned later round has no durable attempt identity")
                receipt = runtime.background_model_attempts.response_authenticity_receipt(
                    snapshot.model_attempt_id
                )
                if receipt is None:
                    raise AssertionError("trusted provider-return receipt was not durable")
                raise SimulatedProcessDeath()
            original_recorder(snapshot, returned)

        runtime.cognitive_runtime.model_response_recorder = die_after_return_receipt
        try:
            runtime.run_turn(
                session_id="rc003-backup-session",
                turn_index=1,
                user_input="recover exact trusted return from a backup",
                occurred_at=NOW,
            )
        except SimulatedProcessDeath:
            pass
        else:
            raise AssertionError("fault injection did not stop after the trusted return")

        execution_id = runtime.turn_executions.execution_id_for(
            subject_id="user_1",
            session_id="rc003-backup-session",
            turn_index=1,
        )
        attempts = runtime.background_model_attempts.list_for_work(
            subject_id="user_1",
            work_kind="user_turn",
            work_id=execution_id,
        )
        if [attempt.model_round_index for attempt in attempts] != [0, 1]:
            raise AssertionError("expected two exact model-round attempts before backup")
        if [attempt.state for attempt in attempts] != ["metered", "dispatching"]:
            raise AssertionError(f"unexpected pre-backup attempt states: {[a.state for a in attempts]}")
        if dispatched_rounds != [0, 1]:
            raise AssertionError(f"unexpected provider dispatch history: {dispatched_rounds}")
        final_attempt = attempts[-1]
        receipt_before = runtime.background_model_attempts.response_authenticity_receipt(
            final_attempt.attempt_id
        )
        if receipt_before is None:
            raise AssertionError("final trusted-return authenticity receipt is absent")
        if runtime.background_model_attempts.staged_response(final_attempt.attempt_id) is not None:
            raise AssertionError("later exact response was already staged before backup")
        if len(runtime.metering.list_model_calls(subject_id="user_1")) != 1:
            raise AssertionError("pre-backup durable meter count must be exactly one")
        existing_tasks = [
            payload
            for payload in store.list_payloads(object_type=ObjectType.TASK, subject_id="user_1")
            if payload.get("title") == "rc003 backup probe watch"
        ]
        if len(existing_tasks) != 1 or int(existing_tasks[0]["revision"]) != 1:
            raise AssertionError("first-round side effect was not present exactly once")

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
        restored_runtime = FusedTurnRuntime(
            store=restored_store,
            index=restored_search,
            model_handler=lambda _snapshot: (_ for _ in ()).throw(
                AssertionError("recovery redispatched the model/provider")
            ),
        )
        receipt_after = restored_runtime.background_model_attempts.response_authenticity_receipt(
            final_attempt.attempt_id
        )
        if receipt_after != receipt_before:
            raise AssertionError("trusted-return receipt did not survive supported backup/restore")

        final_directive = _directive(1)
        staged = restored_runtime.stage_exact_background_response(
            work_kind="user_turn",
            work_id=execution_id,
            model_round_index=1,
            provider=final_directive.provenance.provider,
            model=final_directive.provenance.model,
            provider_request_id=final_directive.provenance.request_id,
            response_fingerprint=restored_runtime.background_model_attempts._response_fingerprint(
                final_directive
            ),
            directive_payload=encode_model_directive(final_directive),
            staged_at=NOW + timedelta(minutes=1),
            evidence="exact trusted-return receipt restored from supported World backup",
            authenticity_proof=receipt_after.authenticity_proof,
        )
        if staged.authenticity_proof != receipt_before.authenticity_proof:
            raise AssertionError("restored authority did not validate the exact receipt")

        result = restored_runtime.run_turn(
            session_id="rc003-backup-session",
            turn_index=1,
            user_input="recover exact trusted return from a backup",
            occurred_at=NOW,
        )
        if result.runtime.response != "trusted return survived backup and restore":
            raise AssertionError("restored exact provider bytes did not converge")
        if result.runtime.recovered_response_attempts != (final_attempt.attempt_id,):
            raise AssertionError("recovered attempt identity changed across restore")
        if int(restored_store.current_world_revision()) <= source_revision:
            raise AssertionError("recovered turn did not advance the same restored World")
        restored_search.catch_up()
        if int(restored_search.watermark()) != int(restored_store.current_world_revision()):
            raise AssertionError("restored index did not catch up to recovered World revision")

        meter_rows = restored_runtime.metering.list_model_calls(subject_id="user_1")
        if len(meter_rows) != 2:
            raise AssertionError(f"expected exactly two meter rows after recovery, got {len(meter_rows)}")
        if [
            row.background_attempt_id
            for row in sorted(meter_rows, key=lambda item: item.model_round_index)
        ] != [attempt.attempt_id for attempt in attempts]:
            raise AssertionError("meter rows do not preserve the exact two attempt identities")
        final_tasks = [
            payload
            for payload in restored_store.list_payloads(object_type=ObjectType.TASK, subject_id="user_1")
            if payload.get("title") == "rc003 backup probe watch"
        ]
        if len(final_tasks) != 1 or int(final_tasks[0]["revision"]) != 1:
            raise AssertionError("restored recovery duplicated the original capability side effect")
        try:
            restored_runtime.run_turn(
                session_id="rc003-backup-session",
                turn_index=1,
                user_input="recover exact trusted return from a backup",
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
            raise AssertionError("restore/rebuild/recovery mutated the source backup bytes")
        if _logical_table_hashes(source_world) != before_hashes:
            raise AssertionError("supported restore path mutated the source World")

        report.update(
            {
                "status": "BACKUP_RESTORE_TRUSTED_RETURN_PASS",
                "source_world_revision_before_backup": source_revision,
                "restored_world_revision_before_recovery": source_revision,
                "restored_world_revision_after_recovery": int(restored_store.current_world_revision()),
                "source_backup_sha256_before": backup_sha_before,
                "source_backup_sha256_after": backup_sha_after,
                "source_backup_immutable": backup_sha_before == backup_sha_after,
                "source_logical_world_immutable": True,
                "world_object_operation_continuity": True,
                "trusted_return_receipt_continuity": receipt_after == receipt_before,
                "trusted_return_authority_validated_after_restore": True,
                "index_rebuild_watermark": int(rebuilt["index_watermark"]),
                "post_recovery_index_watermark": int(restored_search.watermark()),
                "provider_redispatch_count_after_restore": 0,
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
