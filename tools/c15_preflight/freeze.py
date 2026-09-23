"""WAL-safe joint snapshot at an exclusively owned, clean driver boundary.

SQLite writer reservations on BOTH files remain held during backup and checks.
This is stronger than two unrelated successful backups. Non-DB state is protected
by the coordinator's lifetime flock and hash checks. A hostile operator/same-UID
writer remains outside this trust model; no isolation claim is made here.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from contextlib import ExitStack, closing
from pathlib import Path
from uuid import uuid4

from .audit import digest, readonly
from .driver import DriverBlocked, atomic_json
from .publication import FrozenPackage, _confirm


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
            # restore. A separate live publication confirmation is mandatory.
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
            manifest = {"format": "c15-synthetic-freeze-v2", "world_revision": revision,
                        "publication": {"id": publication_id, "status": "VALIDATED_NOT_CONFIRMED"},
                        "index_watermark": revision, "completed_sequence": driver.state["completed_sequence"],
                        "files": {p.name: digest(p) for p in stage.iterdir()}}
            atomic_json(stage / "manifest.json", manifest)
            # Under the exclusively owned run parent, never overwrite an existing package.
            if destination.exists():
                raise DriverBlocked("freeze destination appeared")
            driver.transition("PUBLISHING")
            # From rename through the last successful fsync, durability is not
            # confirmed. An exception leaves the package for inspection, but NO
            # restore capability exists, even if every on-disk byte looks valid.
            os.rename(stage, destination)
            stage = None
            fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        driver.transition("FROZEN")
        # Last action: no I/O follows issuance. A process crash before delivery
        # loses confirmation and requires independent review, not auto-recovery.
        return FrozenPackage(manifest, _confirm(digest(destination / "manifest.json"), publication_id))
    except BaseException as exc:
        driver.state.update(stage="FAILED", publication_status="UNCERTAIN",
                            publication_id=publication_id,
                            preserved_package=str(stage if stage is not None else destination))
        try:
            driver.checkpoint()
        except BaseException as checkpoint_error:
            exc.add_note(f"failure checkpoint also failed: {type(checkpoint_error).__name__}")
        # Preserve both partial staging and visible-but-unconfirmed publication.
        # Safety does NOT depend on persisting FAILED or deleting a marker.
        raise
