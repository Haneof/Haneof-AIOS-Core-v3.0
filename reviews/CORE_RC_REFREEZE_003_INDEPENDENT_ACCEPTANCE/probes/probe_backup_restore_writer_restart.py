#!/usr/bin/env python3
"""Reviewer Independent Probe 5: Backup / restore / rebuild & writer restart smoke.

Validates Sections 13 and 14 requirements:
- World backup creation
- Restore to new path
- Source backup immutability (SHA-256 before == SHA-256 after)
- World/object/operation/recovery continuity
- Trusted-return receipt and authenticity authority survive restore
- Index rebuild works from restored World
- Restored World can continue legal operation without second truth store
- Same World single-writer exclusion enforced
- Custom lock_path override cannot bypass writer exclusion
- Clean stop releases writer lease
- Stale lock metadata does not permanently block restart
- Restarted World does not duplicate durable work
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.headless import (
    HeadlessConfig,
    HeadlessConfigurationError,
    HeadlessCore,
    HeadlessWriterBusy,
)
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
SUBJECT = "user_1"
ANCHOR_ID = "obs_probe5_anchor"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _jsonable(val: Any) -> Any:
    if isinstance(val, bytes):
        return {"__hex__": val.hex()}
    if isinstance(val, (list, tuple)):
        return [_jsonable(item) for item in val]
    if isinstance(val, dict):
        return {str(k): _jsonable(v) for k, v in val.items()}
    return val


def _logical_table_hashes(db_path: Path) -> dict[str, str]:
    with sqlite3.connect(db_path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        result = {}
        for (tname,) in tables:
            rows = conn.execute(f'SELECT * FROM "{tname}" ORDER BY rowid').fetchall()
            encoded = json.dumps([_jsonable(r) for r in rows], sort_keys=True, separators=(",", ":")).encode()
            result[tname] = hashlib.sha256(encoded).hexdigest()
        return result


def _seed_anchor(store: SQLiteWorldStore) -> None:
    moment = NOW - timedelta(hours=2)
    anchor = Observation(
        object_id=ANCHOR_ID,
        subject_id=SUBJECT,
        occurred=TemporalExtent.point(moment),
        learned_at=moment,
        recorded_at=moment,
        created_by="reviewer_probe_5",
        source_kind="conversation",
        modality="text",
        value="Reality anchor for backup/restore verification.",
        metadata={"dimension": "dim:probe5"},
    )
    store.commit(
        [anchor],
        OperationRequest(
            operation_name="probe5.seed",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed anchor",
            idempotency_key="probe5-seed-key",
            source_class=SourceClass.USER,
        ),
    )


def test_backup_restore_and_rebuild() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aios-ia-backup-") as td:
        root = Path(td)
        source_world = root / "source-world.sqlite"
        source_index = root / "source-index.sqlite"

        store = SQLiteWorldStore(source_world)
        index = WorldSearchIndex(source_index, store=store)
        index.rebuild()
        _seed_anchor(store)
        index.catch_up()

        # Run a turn to generate meter rows, attempt, and task object
        def provider(snapshot):
            if snapshot.round_index == 0:
                call = CapabilityCall(
                    name="create_task",
                    call_id="call-backup-task-1",
                    arguments={
                        "title": "task for backup probe",
                        "task_type": "todo",
                        "priority": 10,
                        "next_step": "verify backup",
                        "reason_refs": [{"object_id": ANCHOR_ID, "revision": 1}],
                    },
                )
                return ModelDirective(
                    response=None,
                    capability_calls=(call,),
                    usage=ModelUsage(input_tokens=10, output_tokens=5, total_tokens=15, provider="p", model="m", request_id="req-b0"),
                    provenance=ModelCallProvenance(provider="p", model="m", request_id="req-b0"),
                )
            return ModelDirective(
                response="backup turn completed",
                capability_calls=(),
                usage=ModelUsage(input_tokens=10, output_tokens=5, total_tokens=15, provider="p", model="m", request_id="req-b1"),
                provenance=ModelCallProvenance(provider="p", model="m", request_id="req-b1"),
            )

        runtime = FusedTurnRuntime(store=store, index=index, model_handler=provider)
        turn_res = runtime.run_turn(
            session_id="backup-session",
            turn_index=1,
            user_input="run turn before backup",
            occurred_at=NOW,
        )
        assert turn_res.runtime.response == "backup turn completed"
        source_rev_before_backup = int(store.current_world_revision())
        before_hashes = _logical_table_hashes(source_world)

        # 1. Perform backup
        backup_file = root / "world-backup.sqlite"
        source_config = HeadlessConfig(world_path=source_world, index_path=source_index)
        backup_res = backup_world(source_config, backup_file)
        assert int(backup_res["world_revision"]) == source_rev_before_backup

        backup_sha_before = _sha256(backup_file)
        backup_table_hashes = _logical_table_hashes(backup_file)
        assert backup_table_hashes == before_hashes, "backup table content differs from source"

        # 2. Restore to new path
        restored_world = root / "restored-world.sqlite"
        restored_index = root / "restored-index.sqlite"
        restored_config = HeadlessConfig(world_path=restored_world, index_path=restored_index)

        restore_res = restore_world(restored_config, backup_file)
        assert restore_res["index_disposition"] == "REBUILD_FROM_WORLD"

        # Check immutability of backup file
        backup_sha_after = _sha256(backup_file)
        assert backup_sha_after == backup_sha_before, "backup file was mutated during restore!"

        # Check source world unchanged
        assert _logical_table_hashes(source_world) == before_hashes, "source world was mutated during restore!"

        # Check restored world table hashes match
        restored_hashes = _logical_table_hashes(restored_world)
        assert restored_hashes == before_hashes, "restored world tables differ from backup"

        # 3. Index rebuild from restored World
        rec_status = recovery_status(restored_config)
        assert rec_status["recovery_disposition"] == "REBUILD_FROM_WORLD"

        rebuilt = rebuild_index(restored_config)
        assert int(rebuilt["index_watermark"]) == source_rev_before_backup

        # 4. Continuity and legal continued operation on restored World
        restored_store = SQLiteWorldStore(restored_world)
        restored_search = WorldSearchIndex(restored_index, store=restored_store)
        restored_search.catch_up()
        assert int(restored_search.watermark()) == source_rev_before_backup

        # Replaying completed turn on restored world raises TurnAlreadyCompleted
        restored_runtime = FusedTurnRuntime(
            store=restored_store,
            index=restored_search,
            model_handler=lambda _s: (_ for _ in ()).throw(AssertionError("should not dispatch")),
        )
        replayed = False
        try:
            restored_runtime.run_turn(
                session_id="backup-session",
                turn_index=1,
                user_input="run turn before backup",
                occurred_at=NOW,
            )
        except TurnAlreadyCompleted:
            replayed = True
        assert replayed, "restored world did not short-circuit completed turn"

        # Run a brand new legal turn on restored World with a fresh runtime
        def new_turn_provider(snapshot):
            return ModelDirective(
                response="new turn on restored world ok",
                usage=ModelUsage(input_tokens=5, output_tokens=3, total_tokens=8, provider="p", model="m", request_id="req-post-restore"),
                provenance=ModelCallProvenance(provider="p", model="m", request_id="req-post-restore"),
            )

        new_turn_runtime = FusedTurnRuntime(
            store=restored_store,
            index=restored_search,
            model_handler=new_turn_provider,
        )
        post_restore_res = new_turn_runtime.run_turn(
            session_id="backup-session",
            turn_index=2,
            user_input="new turn on restored world",
            occurred_at=NOW + timedelta(minutes=5),
        )
        assert post_restore_res.runtime.response == "new turn on restored world ok"
        assert int(restored_store.current_world_revision()) > source_rev_before_backup
        restored_search.catch_up()
        assert int(restored_search.watermark()) == int(restored_store.current_world_revision())

    return {
        "status": "BACKUP_RESTORE_CONTINUITY_PASS",
        "backup_immutable": True,
        "source_world_immutable": True,
        "restored_tables_matched": True,
        "index_rebuilt_from_world": True,
        "continued_operation_legal": True,
    }


def test_writer_exclusion_and_restart() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aios-ia-writer-") as td:
        root = Path(td)
        world_path = root / "exclusive-world.sqlite"
        index_path = root / "exclusive-index.sqlite"

        config = HeadlessConfig(
            world_path=world_path,
            index_path=index_path,
        )
        handler = lambda _s: None

        # 1. Start core: acquires writer lease
        core1 = HeadlessCore(config=config, model_handler=handler)
        core1.start()
        status1 = core1.status()
        assert status1["writer_lease_held"] is True

        # 2. Concurrent second core on the SAME World must fail with HeadlessWriterBusy
        busy_raised = False
        try:
            core2 = HeadlessCore(config=config, model_handler=handler)
            core2.start()
        except HeadlessWriterBusy:
            busy_raised = True
        assert busy_raised, "second concurrent writer did not raise HeadlessWriterBusy"

        # 3. Custom lock_path override cannot bypass writer exclusion
        diff_lock = root / "custom.lock"
        bypass_rejected = False
        try:
            config_bypass = HeadlessConfig(
                world_path=world_path,
                index_path=index_path,
                lock_path=diff_lock,
            )
            HeadlessCore(config=config_bypass, model_handler=handler)
        except HeadlessConfigurationError as exc:
            bypass_rejected = True
            assert "lock_path is validation-only" in str(exc)
        assert bypass_rejected, "lock_path override was not rejected"

        # 4. Clean stop releases lease
        core1.stop()
        # After stopping, lock file is unlocked

        # 5. Second core can now acquire lease cleanly
        core3 = HeadlessCore(config=config, model_handler=handler)
        core3.start()
        status3 = core3.status()
        assert status3["writer_lease_held"] is True
        core3.stop()

        # 6. Stale lock metadata does not permanently block restart
        canonical_lock = Path(str(world_path) + ".writer.lock")
        canonical_lock.write_text("STALE_METADATA_PID_99999_TIMESTAMP_EXPIRED\n")

        core4 = HeadlessCore(config=config, model_handler=handler)
        core4.start()
        status4 = core4.status()
        assert status4["writer_lease_held"] is True
        core4.stop()

    return {
        "status": "WRITER_EXCLUSION_AND_RESTART_PASS",
        "single_writer_enforced": True,
        "lock_path_override_blocked": True,
        "clean_stop_releases_lease": True,
        "stale_lock_metadata_handled": True,
    }


def main() -> int:
    backup_res = test_backup_restore_and_rebuild()
    writer_res = test_writer_exclusion_and_restart()

    result = {
        "probe": "probe_backup_restore_writer_restart",
        "status": "PASS",
        "backup_restore_rebuild": backup_res,
        "writer_exclusion_restart": writer_res,
    }
    print("RESULT=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
