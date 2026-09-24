from __future__ import annotations

import hashlib
import multiprocessing
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aios_core.contracts import (
    ObjectType,
    Observation,
    OperationRequest,
    TemporalExtent,
    new_object_id,
)
from aios_core.headless.cli import main as headless_cli_main
from aios_core.headless.core import HeadlessConfig, HeadlessCore
from aios_core.headless.recovery import (
    RecoveryError,
    backup_world,
    rebuild_index,
    recovery_status,
    restore_world,
)
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError


UTC = timezone.utc
T0 = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


class CountingHandler:
    def __init__(self, response: str = "recovery-ok") -> None:
        self.calls = 0
        self.response = response

    def __call__(self, _snapshot):
        self.calls += 1
        return ModelDirective(response=self.response)


def make_obs(object_id: str, revision: int, text: str, learned_at: datetime = T0):
    return Observation(
        object_id=object_id,
        subject_id="user_1",
        revision=revision,
        occurred=TemporalExtent.point(T0 - timedelta(minutes=5)),
        learned_at=learned_at,
        recorded_at=learned_at,
        created_by="recovery-test",
        source_kind="chat",
        modality="text",
        value=text,
    )


def op(world_revision: int, key: str) -> OperationRequest:
    return OperationRequest(
        operation_name="recovery.test.commit",
        expected_world_revision=world_revision,
        reason="recovery fault injection",
        idempotency_key=key,
    )


def _crash_with_uncommitted_world_rows(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("BEGIN IMMEDIATE")
    conn.execute(
        """
        INSERT INTO world_commits(
            world_revision, committed_at, operation_id, session_id, reason, source_class
        ) VALUES(1, ?, 'crash-uncommitted-op', NULL, 'fault injection', 'user')
        """,
        (T0.isoformat(),),
    )
    conn.execute(
        """
        INSERT INTO object_revisions(
            object_id, revision, object_type, subject_id, world_revision,
            learned_at, recorded_at, payload_json, revision_kind
        ) VALUES(
            'obs_uncommitted_crash', 1, 'observation', 'user_1', 1,
            ?, ?, '{}', 'content'
        )
        """,
        (T0.isoformat(), T0.isoformat()),
    )
    conn.execute("UPDATE world_meta SET value='1' WHERE key='world_revision'")
    os._exit(0)


def _commit_then_crash(path: str) -> None:
    store = SQLiteWorldStore(path)
    oid = "obs_committed_crash"
    store.commit([make_obs(oid, 1, "committed before process death")], op(0, "wal-commit"))
    os._exit(0)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_r1_wal_process_crash_distinguishes_uncommitted_and_committed(tmp_path):
    uncommitted_path = tmp_path / "uncommitted.sqlite"
    SQLiteWorldStore(uncommitted_path)
    ctx = multiprocessing.get_context("fork")
    process = ctx.Process(
        target=_crash_with_uncommitted_world_rows,
        args=(str(uncommitted_path),),
    )
    process.start()
    process.join(10)
    assert process.exitcode == 0

    reopened = SQLiteWorldStore(uncommitted_path)
    assert reopened.current_world_revision() == 0
    with pytest.raises(StoreError):
        reopened.get_payload("obs_uncommitted_crash", revision=1)
    assert reopened.quick_check() == ("ok",)

    committed_path = tmp_path / "committed.sqlite"
    SQLiteWorldStore(committed_path)
    process = ctx.Process(target=_commit_then_crash, args=(str(committed_path),))
    process.start()
    process.join(10)
    assert process.exitcode == 0

    committed = SQLiteWorldStore(committed_path)
    assert committed.current_world_revision() == 1
    assert committed.get_payload("obs_committed_crash", revision=1)["value"] == (
        "committed before process death"
    )
    assert committed.quick_check() == ("ok",)


def test_r6_stale_index_catches_up_without_mutating_world(tmp_path):
    world_path = tmp_path / "world.sqlite"
    index_path = tmp_path / "index.sqlite"
    store = SQLiteWorldStore(world_path)
    index = WorldSearchIndex(index_path, store=store)

    first = new_object_id(ObjectType.OBSERVATION)
    store.commit([make_obs(first, 1, "alpha")], op(0, "index-1"))
    index.catch_up()
    assert index.watermark() == 1

    second = new_object_id(ObjectType.OBSERVATION)
    store.commit([make_obs(second, 1, "beta")], op(1, "index-2"))
    before = store.current_world_revision()
    assert index.lag() == 1
    index.catch_up()
    assert index.watermark() == before
    assert store.current_world_revision() == before


def test_r6_missing_and_corrupt_index_rebuild_from_world(tmp_path):
    cfg = HeadlessConfig(
        world_path=tmp_path / "world.sqlite",
        index_path=tmp_path / "index.sqlite",
    )
    store = SQLiteWorldStore(cfg.world_path)
    oid = new_object_id(ObjectType.OBSERVATION)
    store.commit([make_obs(oid, 1, "recoverable index truth")], op(0, "rebuild-1"))
    world_revision = store.current_world_revision()

    missing = recovery_status(cfg)
    assert missing["recovery_disposition"] == "REBUILD_FROM_WORLD"
    assert missing["index_status"] == "missing"

    rebuilt = rebuild_index(cfg)
    assert rebuilt["index_watermark"] == world_revision
    assert SQLiteWorldStore(cfg.world_path).current_world_revision() == world_revision

    cfg.index_path.write_bytes(b"not-a-sqlite-index")
    corrupt = recovery_status(cfg)
    assert corrupt["recovery_disposition"] == "REBUILD_FROM_WORLD"
    assert corrupt["index_status"] in {"corrupt", "unopenable"}

    rebuilt_again = rebuild_index(cfg)
    assert rebuilt_again["index_watermark"] == world_revision
    clean = WorldSearchIndex(cfg.index_path, store=SQLiteWorldStore(cfg.world_path))
    page = clean.co_search(["recoverable"], subject="user_1", strict_freshness=True)
    assert page.status == "ok"
    assert {hit.object_id for hit in page.hits} == {oid}
    assert SQLiteWorldStore(cfg.world_path).current_world_revision() == world_revision


def test_r7_backup_restore_preserves_world_execution_attempt_and_metering(tmp_path):
    cfg = HeadlessConfig(world_path=tmp_path / "world.sqlite")
    handler = CountingHandler()
    with HeadlessCore(config=cfg, model_handler=handler) as core:
        result = core.submit_user_turn(
            session_id="recovery-session",
            turn_index=1,
            user_input="persist me",
            occurred_at=T0,
        )
        assert result.runtime.response == "recovery-ok"
        assert core.runtime is not None
        inspection = core.runtime.inspect_turn_execution(
            session_id="recovery-session",
            turn_index=1,
            user_input="persist me",
            occurred_at=T0,
        )
        assert inspection.recovery_disposition == "completed"
        assert len(inspection.model_attempts) == 1
        assert len(core.runtime.metering.list_model_calls(subject_id="user_1")) == 1
        revision = core.status()["world_revision"]

    backup = tmp_path / "backup.sqlite"
    receipt = backup_world(cfg, backup)
    assert receipt["world_revision"] == revision
    backup_hash = _sha256(backup)

    restored_cfg = HeadlessConfig(world_path=tmp_path / "restored.sqlite")
    restored = restore_world(restored_cfg, backup)
    assert restored["world_revision"] == revision
    assert restored["index_disposition"] == "REBUILD_FROM_WORLD"
    assert _sha256(backup) == backup_hash

    rebuilt = rebuild_index(restored_cfg)
    assert rebuilt["index_watermark"] == revision
    restored_handler = CountingHandler("must-not-be-called")
    with HeadlessCore(config=restored_cfg, model_handler=restored_handler) as core:
        assert core.status()["world_revision"] == revision
        assert core.runtime is not None
        inspection = core.runtime.inspect_turn_execution(
            session_id="recovery-session",
            turn_index=1,
            user_input="persist me",
            occurred_at=T0,
        )
        assert inspection.recovery_disposition == "completed"
        assert len(inspection.model_attempts) == 1
        assert len(core.runtime.metering.list_model_calls(subject_id="user_1")) == 1
        assert restored_handler.calls == 0


def test_r7_restore_never_overwrites_existing_world(tmp_path):
    source_cfg = HeadlessConfig(world_path=tmp_path / "source.sqlite")
    SQLiteWorldStore(source_cfg.world_path)
    backup = tmp_path / "backup.sqlite"
    backup_world(source_cfg, backup)

    destination_cfg = HeadlessConfig(world_path=tmp_path / "destination.sqlite")
    destination = SQLiteWorldStore(destination_cfg.world_path)
    oid = new_object_id(ObjectType.OBSERVATION)
    destination.commit([make_obs(oid, 1, "keep")], op(0, "keep-destination"))
    before = _sha256(destination_cfg.world_path)

    with pytest.raises(RecoveryError, match="never overwritten"):
        restore_world(destination_cfg, backup)
    assert _sha256(destination_cfg.world_path) == before


def test_r8_current_schema_is_marked_and_repeat_open_is_idempotent(tmp_path):
    path = tmp_path / "world.sqlite"
    first = SQLiteWorldStore(path)
    assert first.schema_version() == SQLiteWorldStore.CURRENT_SCHEMA_VERSION
    before = first.current_world_revision()

    second = SQLiteWorldStore(path)
    assert second.schema_version() == SQLiteWorldStore.CURRENT_SCHEMA_VERSION
    assert second.current_world_revision() == before


def test_r8_future_schema_fails_non_destructively_before_runtime_migration(tmp_path):
    path = tmp_path / "future.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE sentinel(value TEXT NOT NULL)")
        conn.execute("INSERT INTO sentinel(value) VALUES('unchanged')")
        conn.execute(
            f"PRAGMA user_version = {SQLiteWorldStore.CURRENT_SCHEMA_VERSION + 100}"
        )
        conn.commit()
    before = _sha256(path)

    with pytest.raises(StoreError) as error:
        SQLiteWorldStore(path)
    assert error.value.context["reason"] == "incompatible_future_schema"
    assert _sha256(path) == before

    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT value FROM sentinel").fetchone()[0] == "unchanged"
        assert conn.execute("PRAGMA user_version").fetchone()[0] == (
            SQLiteWorldStore.CURRENT_SCHEMA_VERSION + 100
        )
        assert conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='world_meta'"
        ).fetchone() is None


def test_r8_failed_upgrade_is_not_falsely_marked_current(tmp_path, monkeypatch):
    path = tmp_path / "legacy.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE legacy_sentinel(value TEXT)")
        conn.execute("INSERT INTO legacy_sentinel(value) VALUES('legacy')")
        conn.commit()

    def fail_upgrade(self, _conn):
        raise RuntimeError("synthetic migration interruption")

    monkeypatch.setattr(SQLiteWorldStore, "_ensure_source_class_schema", fail_upgrade)
    with pytest.raises(RuntimeError, match="migration interruption"):
        SQLiteWorldStore(path)

    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
        assert conn.execute("SELECT value FROM legacy_sentinel").fetchone()[0] == "legacy"


def test_r9_interrupted_index_rebuild_leaves_canonical_projection_publish_safe(
    tmp_path, monkeypatch
):
    cfg = HeadlessConfig(
        world_path=tmp_path / "world.sqlite",
        index_path=tmp_path / "index.sqlite",
    )
    store = SQLiteWorldStore(cfg.world_path)
    oid = new_object_id(ObjectType.OBSERVATION)
    store.commit([make_obs(oid, 1, "stable canonical index")], op(0, "r9-index"))
    rebuild_index(cfg)
    canonical_before = _sha256(cfg.index_path)

    original = WorldSearchIndex.rebuild

    def fail_rebuild(self):
        self.catch_up()
        raise RuntimeError("synthetic rebuild interruption")

    monkeypatch.setattr(WorldSearchIndex, "rebuild", fail_rebuild)
    with pytest.raises(RuntimeError, match="rebuild interruption"):
        rebuild_index(cfg)
    assert _sha256(cfg.index_path) == canonical_before
    assert not Path(str(cfg.index_path) + ".rebuild.tmp").exists()

    monkeypatch.setattr(WorldSearchIndex, "rebuild", original)
    done = rebuild_index(cfg)
    assert done["index_watermark"] == store.current_world_revision()


def test_r9_interrupted_restore_does_not_mutate_backup_or_publish_partial_world(
    tmp_path, monkeypatch
):
    source_cfg = HeadlessConfig(world_path=tmp_path / "source.sqlite")
    store = SQLiteWorldStore(source_cfg.world_path)
    oid = new_object_id(ObjectType.OBSERVATION)
    store.commit([make_obs(oid, 1, "restore source")], op(0, "r9-restore"))
    backup = tmp_path / "backup.sqlite"
    backup_world(source_cfg, backup)
    backup_hash = _sha256(backup)

    destination_cfg = HeadlessConfig(world_path=tmp_path / "destination.sqlite")
    import aios_core.headless.recovery as recovery_module

    original_replace = recovery_module.os.replace

    def fail_publish(_source, _target):
        raise OSError("synthetic publish interruption")

    monkeypatch.setattr(recovery_module.os, "replace", fail_publish)
    with pytest.raises(OSError, match="publish interruption"):
        restore_world(destination_cfg, backup)
    assert not destination_cfg.world_path.exists()
    assert _sha256(backup) == backup_hash

    monkeypatch.setattr(recovery_module.os, "replace", original_replace)
    done = restore_world(destination_cfg, backup)
    assert done["world_revision"] == store.current_world_revision()
    assert _sha256(backup) == backup_hash


def test_r10_recovery_cli_does_not_require_model_handler(tmp_path, capfd):
    cfg = HeadlessConfig(world_path=tmp_path / "world.sqlite")
    store = SQLiteWorldStore(cfg.world_path)
    oid = new_object_id(ObjectType.OBSERVATION)
    store.commit([make_obs(oid, 1, "cli recovery")], op(0, "cli-recovery"))

    rc = headless_cli_main(["--world", str(cfg.world_path), "recovery-status"])
    assert rc == 0
    status = capfd.readouterr().out
    assert '"status": "recovery_status"' in status

    backup = tmp_path / "cli-backup.sqlite"
    rc = headless_cli_main(
        ["--world", str(cfg.world_path), "backup", "--to", str(backup)]
    )
    assert rc == 0
    assert backup.exists()

    cfg.index_path.write_bytes(b"broken")
    rc = headless_cli_main(["--world", str(cfg.world_path), "rebuild-index"])
    assert rc == 0
    assert recovery_status(cfg)["index_status"] == "ready"

    restored = tmp_path / "cli-restored.sqlite"
    rc = headless_cli_main(
        [
            "--world",
            str(restored),
            "restore",
            "--from-backup",
            str(backup),
        ]
    )
    assert rc == 0
    assert SQLiteWorldStore(restored).current_world_revision() == store.current_world_revision()
