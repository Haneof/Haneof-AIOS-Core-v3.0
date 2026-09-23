"""WAL-safe joint snapshot at an exclusively owned, clean driver boundary.

SQLite writer reservations on BOTH files remain held during backup and checks.
This is stronger than two unrelated successful backups. Non-DB state is protected
by the coordinator's lifetime flock and hash checks. A hostile operator/same-UID
writer remains outside this trust model; no isolation claim is made here.

Publication confirmation is now persistent and auditable (v3):
- After successful rename and parent fsync, a receipt file
  `publication_receipt.json` containing manifest SHA and publication ID is
  atomically created and fsynced.
- Restore requires pinned manifest hash AND valid receipt.
- If parent fsync or receipt creation fails, package may remain visible but
  WITHOUT receipt; ordinary restore is BLOCKED and source driver is marked
  FAILED/UNCERTAIN. Operator must independently verify before explicit
  confirmation via confirm_uncertain_package (requires attestation).

Commit point definition (gap 1):
- The persistent receipt is the formal commit point of publication.
  Fault windows:
  1) After package publish (rename) before receipt: rename succeeded,
     parent fsync before receipt may fail. No receipt -> package UNCERTAIN,
     ordinary restore BLOCKED, driver FAILED with preserved_package.
  2) Receipt write/replace and its dir fsync: atomic_json writes temp file,
     fsyncs it, renames, fsyncs destination dir. Then create_receipt also
     fsyncs destination.parent. Failure in any of these -> no receipt or
     partial receipt (atomic_json ensures no partial), so BLOCKED, driver
     FAILED. If receipt file was already durable but parent fsync after
     receipt fails, receipt exists but durability of parent entry uncertain.
     We treat this as failure and mark FAILED, but receipt exists so
     ordinary restore will succeed per commit point definition (receipt is
     commit). Operator must verify parent durability.
  3) After receipt success, before final FROZEN checkpoint write/fsync:
     receipt exists, so package is CONFIRMED and restorable via ordinary
     restore, even if source checkpoint (FROZEN) fails. Source driver is
     marked FAILED/UNCERTAIN with preserved_package, but package remains
     restorable. This coordination ensures no "uncertain product but
     ordinary restore considers confirmed": uncertain = no receipt = blocked;
     confirmed = receipt exists = restorable, even if source checkpoint fails.

- No deletion of receipt or swallowing exception to fake consistency.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from contextlib import ExitStack, closing
from pathlib import Path
from uuid import uuid4

from .audit import digest, readonly
from .driver import DriverBlocked, atomic_json
from .publication import FrozenPackage, create_receipt


def backup(source: Path, destination: Path):
    # Read via SQLite, not file copy: include all committed WAL pages.
    with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as src, closing(
        sqlite3.connect(destination)
    ) as dst:
        src.backup(dst)
    with destination.open("rb") as stream:
        os.fsync(stream.fileno())


def freeze(driver, destination: Path):
    if driver.lock.closed or driver.state["stage"] != "READY" or driver.trace.failure:
        raise DriverBlocked("freeze requires an owned, successful event boundary")
    if destination.exists():
        raise DriverBlocked("freeze destination already exists")
    driver.verify_boundary()
    stage = None
    publication_id = uuid4().hex
    receipt_created = False
    try:
        driver.transition("FREEZING")
        driver.runtime.index.rebuild()  # Canonical rebuild, not direct SQL reasoning.
        world = Path(driver.runtime.store.db_path).resolve()
        index = Path(driver.runtime.index.db_path).resolve()
        with ExitStack() as locks:
            # Acquire deterministic-order writer locks, then measure a joint cut.
            for path in sorted({world, index}):
                conn = locks.enter_context(closing(sqlite3.connect(path, timeout=0)))
                conn.execute("BEGIN IMMEDIATE")
            revision = int(driver.runtime.store.current_world_revision())
            if driver.runtime.index.watermark() != revision:
                raise DriverBlocked("joint World/index cut is inconsistent")
            driver.checkpoint()
            state_hash = digest(driver.state_path)
            release_hash = digest(driver.port.state)
            release = driver.port.read_state()
            if release["pending_reveal"] is not None or release["last_acked_sequence"] != driver.state["completed_sequence"]:
                raise DriverBlocked("release does not match completed runtime boundary")
            driver.trace.append("freeze_cut", {"world_revision": revision, "index_watermark": revision,
                "completed_sequence": driver.state["completed_sequence"], "release_sha256": release_hash})
            stage = Path(tempfile.mkdtemp(prefix=".c15-freeze-", dir=destination.parent))
            os.chmod(stage, 0o700)
            backup(world, stage / "private_world.sqlite")
            backup(index, stage / "world_index.sqlite")
            shutil.copyfile(driver.port.state, stage / "release_state.json")
            # READY describes a completed runtime boundary, NOT authorization to
            # restore. A persistent receipt after successful publication is mandatory.
            atomic_json(stage / "restart_state.json", {**driver.state, "stage": "READY"})
            shutil.copyfile(driver.trace.path, stage / "trace.jsonl")
            with closing(readonly(stage / "private_world.sqlite")) as w, closing(readonly(stage / "world_index.sqlite")) as i:
                wr = int(w.execute("SELECT value FROM world_meta WHERE key='world_revision'").fetchone()[0])
                iw = int(i.execute("SELECT value FROM search_meta WHERE key='search_watermark_world_revision'").fetchone()[0])
                if wr != iw or wr != revision:
                    raise DriverBlocked("snapshot pair watermark mismatch")
                for conn in (w, i):
                    if conn.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                        raise DriverBlocked("snapshot integrity failure")
                # Metadata-only durable receipt binding; real fixture validation is in ACK.
                for receipt in release["receipts"]:
                    row = w.execute("SELECT world_revision FROM object_revisions WHERE object_id=? AND revision=?",
                        (receipt["ingest_object_id"], receipt["ingest_revision"])).fetchone()
                    if row != (receipt["ingest_world_revision"],):
                        raise DriverBlocked("snapshot receipt lost its durable commit")
            if (digest(driver.state_path) != state_hash or digest(driver.port.state) != release_hash
                    or int(driver.runtime.store.current_world_revision()) != revision
                    or driver.runtime.index.watermark() != revision):
                raise DriverBlocked("source changed while freezing")
            if digest(stage / "release_state.json") != release_hash:
                raise DriverBlocked("release copy changed")
            for path in stage.iterdir():
                if path.name.endswith(("-wal", "-shm", "-journal")):
                    raise DriverBlocked("snapshot still has SQLite sidecars")
                os.chmod(path, 0o600)
                with path.open("rb") as stream:
                    os.fsync(stream.fileno())
            manifest = {"format": "c15-synthetic-freeze-v3", "world_revision": revision,
                        "publication": {"id": publication_id, "status": "VALIDATED"},
                        "index_watermark": revision, "completed_sequence": driver.state["completed_sequence"],
                        "files": {p.name: digest(p) for p in stage.iterdir()}}
            atomic_json(stage / "manifest.json", manifest)
            # Under the exclusively owned run parent, never overwrite an existing package.
            if destination.exists():
                raise DriverBlocked("freeze destination appeared")
            driver.transition("PUBLISHING")
            # Window 1: after rename, before receipt - durability not confirmed
            os.rename(stage, destination)
            stage = None
            fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            # Window 2: receipt write/replace and its dir fsync - commit point
            manifest_sha = digest(destination / "manifest.json")
            receipt_path = create_receipt(
                destination,
                manifest_sha256=manifest_sha,
                publication_id=publication_id,
                driver_state_sha256=state_hash,
                release_sha256=release_hash,
            )
            receipt_created = True
        # Window 3: after receipt success, before final FROZEN checkpoint
        # Receipt is commit point, so even if this fails, package remains restorable
        driver.transition("FROZEN")
        return FrozenPackage(
            manifest=manifest,
            receipt_path=receipt_path,
            manifest_sha256=manifest_sha,
            publication_id=publication_id,
            confirmation=None,
        )
    except BaseException as exc:
        # Determine if receipt file actually exists (commit point) even if flag not set
        # e.g., if create_receipt's parent fsync fails after file creation
        actual_receipt_exists = False
        try:
            actual_receipt_exists = (destination / "publication_receipt.json").exists()
        except Exception:
            pass
        is_confirmed = receipt_created or actual_receipt_exists
        driver.state.update(stage="FAILED", publication_status="UNCERTAIN" if not is_confirmed else "CONFIRMED_BUT_SOURCE_FAILED",
                            publication_id=publication_id,
                            preserved_package=str(stage if stage is not None else destination),
                            receipt_created=is_confirmed)
        try:
            driver.checkpoint()
        except BaseException as checkpoint_error:
            exc.add_note(f"failure checkpoint also failed: {type(checkpoint_error).__name__}")
        # Preserve both partial staging and visible-but-unconfirmed/confirmed publication.
        # Safety does NOT depend on persisting FAILED or deleting a marker.
        # No receipt deletion to fake consistency.
        if stage is not None and stage.exists():
            # Keep stage for inspection; do not auto-delete to hide evidence
            pass
        raise
