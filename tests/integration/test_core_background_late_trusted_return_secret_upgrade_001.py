"""CA2 RED-first: legacy signing material must be physically absent after upgrade."""

from __future__ import annotations

import sqlite3

from aios_core.runtime.background_attempt import BackgroundModelAttemptStore
from aios_core.storage.sqlite_store import SQLiteWorldStore


def _raw_runtime_bytes(db):
    pieces = [db.read_bytes()]
    wal = db.with_name(db.name + "-wal")
    shm = db.with_name(db.name + "-shm")
    if wal.exists():
        pieces.append(wal.read_bytes())
    if shm.exists():
        pieces.append(shm.read_bytes())
    return b"".join(pieces)


def test_ca2_upgrade_physically_purges_legacy_nonce_and_hmac_secret(tmp_path):
    db = tmp_path / "legacy-secret-upgrade.sqlite"
    store = SQLiteWorldStore(db)
    BackgroundModelAttemptStore(store)

    nonce = "W16_LEGACY_CAPABILITY_NONCE_4f6ac14a9fb74638"
    secret = "W16_LEGACY_HMAC_SECRET_c17f3e2ab92d4a14"

    with store._connection() as conn:
        conn.execute(
            """
            CREATE TABLE background_model_return_capabilities (
                attempt_id TEXT PRIMARY KEY,
                capability_nonce TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO background_model_return_capabilities(
                attempt_id, capability_nonce
            ) VALUES ('legacy-attempt', ?)
            """,
            (nonce,),
        )
        conn.execute(
            """
            CREATE TABLE background_model_authenticity_authority (
                authority_id TEXT PRIMARY KEY,
                secret_hex TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO background_model_authenticity_authority(
                authority_id, secret_hex
            ) VALUES ('trusted-return-v1', ?)
            """,
            (secret,),
        )
        conn.commit()

    before = _raw_runtime_bytes(db)
    assert nonce.encode() in before
    assert secret.encode() in before

    reopened = SQLiteWorldStore(db)
    BackgroundModelAttemptStore(reopened)

    with sqlite3.connect(db) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        dump = "\n".join(conn.iterdump()).encode()

    assert "background_model_return_capabilities" not in tables
    assert "background_model_authenticity_authority" not in tables
    assert nonce.encode() not in dump
    assert secret.encode() not in dump

    after = _raw_runtime_bytes(db)
    assert nonce.encode() not in after
    assert secret.encode() not in after

    backup = tmp_path / "legacy-secret-backup.sqlite"
    with sqlite3.connect(db) as src, sqlite3.connect(backup) as dst:
        src.backup(dst)
    backup_bytes = backup.read_bytes()
    assert nonce.encode() not in backup_bytes
    assert secret.encode() not in backup_bytes
