"""Mechanical recovery surfaces for the single-World headless Core.

The canonical SQLite World remains the only truth store.  Backups are immutable
snapshots, and the search index is always treated as a rebuildable projection.
No function in this module invokes a model provider.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore

from .core import HeadlessConfig, _WriterLease


class RecoveryError(RuntimeError):
    """A recovery operation cannot proceed safely."""


def _readonly_uri(path: Path) -> str:
    return path.resolve().as_uri() + "?mode=ro"


def _unlink_sqlite_family(path: Path) -> None:
    for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        try:
            candidate.unlink()
        except FileNotFoundError:
            pass


def _fsync_path(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())
    try:
        directory_fd = os.open(str(path.parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _read_only_world_probe(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise RecoveryError(f"World snapshot does not exist: {path}")
    try:
        with sqlite3.connect(_readonly_uri(path), uri=True) as conn:
            conn.execute("PRAGMA query_only = ON")
            version_row = conn.execute("PRAGMA user_version").fetchone()
            schema_version = 0 if version_row is None else int(version_row[0])
            checks = tuple(str(row[0]) for row in conn.execute("PRAGMA quick_check").fetchall())
            if checks != ("ok",):
                raise RecoveryError(
                    "FATAL_INCOMPATIBLE: SQLite quick_check failed: " + ", ".join(checks)
                )
            meta_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='world_meta'"
            ).fetchone()
            if meta_exists is None:
                raise RecoveryError("FATAL_INCOMPATIBLE: snapshot is not an AIOS World")
            revision_row = conn.execute(
                "SELECT value FROM world_meta WHERE key='world_revision'"
            ).fetchone()
            if revision_row is None:
                raise RecoveryError(
                    "FATAL_INCOMPATIBLE: World is missing world_revision metadata"
                )
            world_revision = int(revision_row[0])
            table_names = {
                str(row[0])
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
    except RecoveryError:
        raise
    except (sqlite3.DatabaseError, OSError, TypeError, ValueError) as exc:
        raise RecoveryError(f"FATAL_INCOMPATIBLE: cannot inspect World snapshot: {exc}") from exc

    if schema_version > SQLiteWorldStore.CURRENT_SCHEMA_VERSION:
        raise RecoveryError(
            "FATAL_INCOMPATIBLE: World schema version "
            f"{schema_version} exceeds supported "
            f"{SQLiteWorldStore.CURRENT_SCHEMA_VERSION}"
        )
    return {
        "schema_version": schema_version,
        "world_revision": world_revision,
        "quick_check": checks,
        "tables": table_names,
    }


def _read_only_index_probe(path: Path, *, world_revision: int) -> dict[str, Any]:
    if not path.exists():
        return {
            "index_status": "missing",
            "index_watermark": None,
            "index_lag": world_revision,
            "recovery_disposition": "REBUILD_FROM_WORLD",
        }
    try:
        with sqlite3.connect(_readonly_uri(path), uri=True) as conn:
            conn.execute("PRAGMA query_only = ON")
            checks = tuple(str(row[0]) for row in conn.execute("PRAGMA quick_check").fetchall())
            if checks != ("ok",):
                return {
                    "index_status": "corrupt",
                    "index_watermark": None,
                    "index_lag": None,
                    "recovery_disposition": "REBUILD_FROM_WORLD",
                }
            meta_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='search_meta'"
            ).fetchone()
            if meta_exists is None:
                return {
                    "index_status": "uninitialized",
                    "index_watermark": None,
                    "index_lag": world_revision,
                    "recovery_disposition": "REBUILD_FROM_WORLD",
                }
            row = conn.execute(
                "SELECT value FROM search_meta WHERE key='search_watermark_world_revision'"
            ).fetchone()
            watermark = 0 if row is None else int(row[0])
    except (sqlite3.DatabaseError, OSError, TypeError, ValueError):
        return {
            "index_status": "unopenable",
            "index_watermark": None,
            "index_lag": None,
            "recovery_disposition": "REBUILD_FROM_WORLD",
        }

    if watermark > world_revision:
        return {
            "index_status": "invalid_future_watermark",
            "index_watermark": watermark,
            "index_lag": None,
            "recovery_disposition": "REBUILD_FROM_WORLD",
        }
    lag = world_revision - watermark
    return {
        "index_status": "ready" if lag == 0 else "stale",
        "index_watermark": watermark,
        "index_lag": lag,
        "recovery_disposition": "AUTO_RECOVERABLE",
    }


def recovery_status(config: HeadlessConfig) -> dict[str, Any]:
    """Inspect storage recovery state without invoking a provider or mutating index truth."""

    lease = _WriterLease(config.lock_path)
    lease.acquire()
    try:
        world = _read_only_world_probe(config.world_path)
        index = _read_only_index_probe(
            config.index_path,
            world_revision=int(world["world_revision"]),
        )
        return {
            "status": "recovery_status",
            "world_path": str(config.world_path),
            "index_path": str(config.index_path),
            "world_revision": int(world["world_revision"]),
            "schema_version": int(world["schema_version"]),
            "supported_schema_version": SQLiteWorldStore.CURRENT_SCHEMA_VERSION,
            "world_quick_check": list(world["quick_check"]),
            **index,
        }
    finally:
        lease.release()


def backup_world(config: HeadlessConfig, destination: str | Path) -> dict[str, Any]:
    """Create one coherent SQLite online-backup snapshot of the canonical World."""

    target = Path(destination).expanduser().resolve()
    if target == config.world_path:
        raise RecoveryError("backup destination must differ from the live World")
    if target.exists():
        raise RecoveryError(f"backup destination already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(str(target) + ".tmp")

    lease = _WriterLease(config.lock_path)
    lease.acquire()
    try:
        store = SQLiteWorldStore(config.world_path)
        if store.quick_check() != ("ok",):
            raise RecoveryError("FATAL_INCOMPATIBLE: live World failed SQLite quick_check")
        source_revision = int(store.current_world_revision())
        source_schema = int(store.schema_version())

        _unlink_sqlite_family(staged)
        try:
            with sqlite3.connect(
                _readonly_uri(config.world_path),
                uri=True,
                timeout=SQLiteWorldStore.SQLITE_BUSY_TIMEOUT_MS / 1000.0,
            ) as source, sqlite3.connect(str(staged)) as destination_conn:
                source.execute("PRAGMA query_only = ON")
                source.backup(destination_conn)
                destination_conn.commit()

            probe = _read_only_world_probe(staged)
            if int(probe["world_revision"]) != source_revision:
                raise RecoveryError("backup World revision does not match source snapshot")
            if int(probe["schema_version"]) != source_schema:
                raise RecoveryError("backup schema version does not match source snapshot")
            _fsync_path(staged)
            os.replace(staged, target)
            _fsync_path(target)
        except Exception:
            _unlink_sqlite_family(staged)
            raise

        return {
            "status": "backup_completed",
            "recovery_disposition": "AUTO_RECOVERABLE",
            "source_world": str(config.world_path),
            "backup_path": str(target),
            "world_revision": source_revision,
            "schema_version": source_schema,
        }
    finally:
        lease.release()


def restore_world(config: HeadlessConfig, source_backup: str | Path) -> dict[str, Any]:
    """Restore an immutable backup into a new World path via a staged SQLite backup."""

    source = Path(source_backup).expanduser().resolve()
    target = config.world_path
    if source == target:
        raise RecoveryError("restore source must differ from destination World")
    probe = _read_only_world_probe(source)
    for candidate in (target, Path(str(target) + "-wal"), Path(str(target) + "-shm")):
        if candidate.exists():
            raise RecoveryError(
                "restore destination must be a new path; existing World state is never overwritten"
            )
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(str(target) + ".restore.tmp")

    lease = _WriterLease(config.lock_path)
    lease.acquire()
    try:
        _unlink_sqlite_family(staged)
        try:
            with sqlite3.connect(_readonly_uri(source), uri=True) as source_conn, sqlite3.connect(
                str(staged)
            ) as destination_conn:
                source_conn.execute("PRAGMA query_only = ON")
                source_conn.backup(destination_conn)
                destination_conn.commit()

            # Any supported legacy upgrade happens only on the staged copy.  The
            # backup itself remains immutable.
            staged_store = SQLiteWorldStore(staged)
            if staged_store.quick_check() != ("ok",):
                raise RecoveryError("restored staged World failed SQLite quick_check")
            restored_revision = int(staged_store.current_world_revision())
            if restored_revision != int(probe["world_revision"]):
                raise RecoveryError("restored World revision differs from backup")
            with sqlite3.connect(str(staged)) as checkpoint:
                checkpoint.execute("PRAGMA wal_checkpoint(FULL)")
                checkpoint.commit()
            # The staged database is checkpointed; sidecars are mechanical residue.
            for sidecar in (Path(str(staged) + "-wal"), Path(str(staged) + "-shm")):
                try:
                    sidecar.unlink()
                except FileNotFoundError:
                    pass
            _fsync_path(staged)
            os.replace(staged, target)
            _fsync_path(target)
        except Exception:
            _unlink_sqlite_family(staged)
            raise

        restored = _read_only_world_probe(target)
        return {
            "status": "restore_completed",
            "recovery_disposition": "AUTO_RECOVERABLE",
            "backup_path": str(source),
            "world_path": str(target),
            "world_revision": int(restored["world_revision"]),
            "schema_version": int(restored["schema_version"]),
            "index_disposition": "REBUILD_FROM_WORLD",
        }
    finally:
        lease.release()


def rebuild_index(config: HeadlessConfig) -> dict[str, Any]:
    """Rebuild the search projection off to the side, then atomically publish it."""

    target = config.index_path
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(str(target) + ".rebuild.tmp")

    lease = _WriterLease(config.lock_path)
    lease.acquire()
    try:
        store = SQLiteWorldStore(config.world_path)
        if store.quick_check() != ("ok",):
            raise RecoveryError("FATAL_INCOMPATIBLE: live World failed SQLite quick_check")
        world_revision = int(store.current_world_revision())

        _unlink_sqlite_family(staged)
        try:
            index = WorldSearchIndex(staged, store=store)
            applied = int(index.rebuild())
            watermark = int(index.watermark())
            if watermark != world_revision:
                raise RecoveryError(
                    f"rebuilt index watermark {watermark} does not match World {world_revision}"
                )
            with sqlite3.connect(str(staged)) as conn:
                checks = tuple(str(row[0]) for row in conn.execute("PRAGMA quick_check"))
            if checks != ("ok",):
                raise RecoveryError("rebuilt index failed SQLite quick_check")
            _fsync_path(staged)
            # Canonical index sidecars are cache-only and never authoritative.
            for sidecar in (Path(str(target) + "-wal"), Path(str(target) + "-shm")):
                try:
                    sidecar.unlink()
                except FileNotFoundError:
                    pass
            os.replace(staged, target)
            _fsync_path(target)
        except Exception:
            _unlink_sqlite_family(staged)
            raise

        return {
            "status": "index_rebuilt",
            "recovery_disposition": "REBUILD_FROM_WORLD",
            "world_revision": world_revision,
            "index_watermark": watermark,
            "indexed_rows": applied,
            "index_path": str(target),
        }
    finally:
        lease.release()
