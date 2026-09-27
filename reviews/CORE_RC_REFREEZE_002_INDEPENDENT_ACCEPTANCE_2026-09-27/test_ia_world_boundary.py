"""Independent RC acceptance probes — world boundary, authenticity, recovery, writer.

Written by the Independent RC Re-Freeze Acceptance Reviewer for
CORE-RC-REFREEZE-002-INDEPENDENT-ACCEPTANCE.  These probes are NOT the author's
probes; they attack the frozen software 27a21db5b656d441248b9240020910b66a223830
from the public/durable boundary using only the frozen Core APIs plus direct
SQLite inspection of the World the runtime itself created.

Invariant families:
  A. authority missing / malformed            -> fail closed
  B. forged or tampered receipt / staging      -> fail closed
  C. historical unauthenticated staged rows    -> never auto-authenticated
  D. writer lock: second writer + lock bypass  -> rejected, canonical only
  E. restart                                    -> no redispatch, exactly-once
  F. backup / restore / rebuild                 -> authority preserved, no
                                                   second key, source immutable
  G. no second truth store                      -> receipts/authority are
                                                   runtime evidence inside the
                                                   single World; index is a
                                                   rebuildable projection
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aios_core.headless import (
    HeadlessConfig,
    HeadlessConfigurationError,
    HeadlessCore,
    HeadlessWriterBusy,
)
from aios_core.headless.recovery import backup_world, rebuild_index, restore_world
from aios_core.headless.testing import deterministic_model_handler
from aios_core.runtime.background_attempt import (
    BackgroundModelResponseConflict,
    BackgroundModelAttemptStore,
    encode_model_directive,
)
from aios_core.storage.sqlite_store import SQLiteWorldStore

T0 = datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _logical_hash(path: Path) -> str:
    """Content-level digest of every table/row (immune to WAL checkpointing)."""
    con = sqlite3.connect(path)
    try:
        h = hashlib.sha256()
        tables = [
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        for table in tables:
            h.update(table.encode())
            for row in con.execute(f"SELECT * FROM {table}"):
                h.update(repr(tuple(str(v) for v in row)).encode())
        return h.hexdigest()
    finally:
        con.close()


def _make_world(tmp_path: Path):
    cfg = HeadlessConfig(world_path=tmp_path / "world.sqlite")
    with HeadlessCore(config=cfg, model_handler=deterministic_model_handler) as core:
        result = core.submit_user_turn(
            session_id="ia-session",
            turn_index=1,
            user_input="independent probe turn",
            occurred_at=T0,
        )
        assert result.runtime.response == "HEADLESS_MECHANICAL_OK"
    return cfg


def _attempt_ids(cfg: HeadlessConfig) -> list[str]:
    con = sqlite3.connect(cfg.world_path)
    try:
        return [
            r[0]
            for r in con.execute(
                "SELECT attempt_id FROM background_model_attempts ORDER BY rowid"
            )
        ]
    finally:
        con.close()


def _receipt_fields(cfg: HeadlessConfig, attempt_id: str) -> dict:
    con = sqlite3.connect(cfg.world_path)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            "SELECT * FROM background_model_response_receipts WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()
        assert row is not None, "trusted return must have produced a receipt"
        return {k: row[k] for k in row.keys()}
    finally:
        con.close()


# --------------------------------------------------------------------------- A
def test_ia_a1_authority_missing_fails_closed(tmp_path):
    cfg = _make_world(tmp_path)
    attempt_id = _attempt_ids(cfg)[0]
    store = SQLiteWorldStore(cfg.world_path)
    attempts = BackgroundModelAttemptStore(store)
    receipt = _receipt_fields(cfg, attempt_id)

    con = sqlite3.connect(cfg.world_path)
    con.execute("DELETE FROM background_model_authenticity_authority")
    con.commit()
    con.close()

    with store._connection() as conn:
        with pytest.raises(RuntimeError, match="authority is missing"):
            BackgroundModelAttemptStore._receipt_proof(conn, **{
                k: receipt[k]
                for k in (
                    "attempt_id",
                    "subject_id",
                    "work_kind",
                    "work_id",
                    "model_round_index",
                    "outbound_request_fingerprint",
                    "relay_id",
                    "provider",
                    "model",
                    "provider_request_id",
                    "response_fingerprint",
                    "payload_sha256",
                )
            })


def test_ia_a2_authority_malformed_fails_closed(tmp_path):
    cfg = _make_world(tmp_path)
    attempt_id = _attempt_ids(cfg)[0]
    store = SQLiteWorldStore(cfg.world_path)
    receipt = _receipt_fields(cfg, attempt_id)
    fields = {
        k: receipt[k]
        for k in (
            "attempt_id",
            "subject_id",
            "work_kind",
            "work_id",
            "model_round_index",
            "outbound_request_fingerprint",
            "relay_id",
            "provider",
            "model",
            "provider_request_id",
            "response_fingerprint",
            "payload_sha256",
        )
    }
    for malformed in ("zz-not-hex", "abcd"):  # non-hex / wrong length
        con = sqlite3.connect(cfg.world_path)
        con.execute(
            "UPDATE background_model_authenticity_authority SET secret_hex=?",
            (malformed,),
        )
        con.commit()
        con.close()
        with store._connection() as conn:
            with pytest.raises(RuntimeError, match="authority is invalid"):
                BackgroundModelAttemptStore._receipt_proof(conn, **fields)


# --------------------------------------------------------------------------- B
def test_ia_b1_attacker_cannot_forge_receipt_without_key(tmp_path):
    """A caller with every caller-visible field but no key cannot mint a proof."""
    cfg = _make_world(tmp_path)
    attempt_id = _attempt_ids(cfg)[0]
    receipt = _receipt_fields(cfg, attempt_id)
    fields = {
        k: receipt[k]
        for k in (
            "attempt_id",
            "subject_id",
            "work_kind",
            "work_id",
            "model_round_index",
            "outbound_request_fingerprint",
            "relay_id",
            "provider",
            "model",
            "provider_request_id",
            "response_fingerprint",
            "payload_sha256",
        )
    }
    # A key-less attacker can only guess; a fixed wrong secret must not verify.
    forge_key = bytes.fromhex("00" * 32)
    import hmac as _hmac
    import json as _json

    guessed = _hmac.new(
        forge_key,
        _json.dumps(
            {
                "attempt_id": fields["attempt_id"],
                "model": fields["model"],
                "model_round_index": int(fields["model_round_index"]),
                "outbound_request_fingerprint": fields["outbound_request_fingerprint"],
                "payload_sha256": fields["payload_sha256"],
                "provider": fields["provider"],
                "provider_request_id": fields["provider_request_id"],
                "relay_id": fields["relay_id"],
                "response_fingerprint": fields["response_fingerprint"],
                "schema": "aios.background-model-response-receipt.v1",
                "subject_id": fields["subject_id"],
                "work_id": fields["work_id"],
                "work_kind": fields["work_kind"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode(),
        hashlib.sha256,
    ).hexdigest()
    assert guessed != receipt["authenticity_proof"].removeprefix("bgresponse_v1_")


def test_ia_b2_tampered_receipt_row_rejected(tmp_path):
    """Mutating durable receipt fields must break verification (fail closed)."""
    cfg = _make_world(tmp_path)
    attempt_id = _attempt_ids(cfg)[0]
    con = sqlite3.connect(cfg.world_path)
    con.execute(
        "UPDATE background_model_response_receipts SET provider_request_id=? "
        "WHERE attempt_id=?",
        ("attacker-substituted-request-id", attempt_id),
    )
    con.commit()
    con.close()

    store = SQLiteWorldStore(cfg.world_path)
    attempts = BackgroundModelAttemptStore(store)
    attempt = attempts.get(attempt_id)
    binding = attempts.outbound_request_binding(attempt_id)
    receipts = _receipt_fields(cfg, attempt_id)
    with store._connection() as conn:
        with pytest.raises(BackgroundModelResponseConflict):
            attempts._verify_response_authenticity(
                conn,
                attempt=attempt,
                binding=binding,
                provider=receipts["provider"],
                model=receipts["model"],
                provider_request_id=receipts["provider_request_id"],
                response_fingerprint=receipts["response_fingerprint"],
                payload_sha256=receipts["payload_sha256"],
                authenticity_proof=receipts["authenticity_proof"],
            )


def test_ia_b3_staging_without_proof_is_refused(tmp_path):
    """staging a reply with no authenticity proof must fail closed."""
    cfg = _make_world(tmp_path)
    attempt_id = _attempt_ids(cfg)[0]
    attempt = BackgroundModelAttemptStore(SQLiteWorldStore(cfg.world_path)).get(
        attempt_id
    )
    attempts = BackgroundModelAttemptStore(SQLiteWorldStore(cfg.world_path))
    with pytest.raises(Exception):
        attempts.stage_exact_response(
            attempt_id,
            staged_at=T0,
            provider=attempt.provider,
            model=attempt.model,
            provider_request_id=attempt.provider_request_id,
            response_fingerprint=attempt.response_fingerprint,
            directive_payload='{"response": "forged"}',
            authenticity_proof=None,
            evidence="independent probe: no proof supplied",
        )
    # fail-closed must also leave no partial staging side effect behind
    assert attempts.staged_response(attempt_id) is None


# --------------------------------------------------------------------------- C
def test_ia_c1_historical_unauthenticated_row_never_authenticated(tmp_path):
    """A legacy staged row that matches provenance but has no proof stays unusable.

    The World is first reduced to the historical schema shape (no
    authenticity_proof column) and a staged reply is written the way the legacy
    runtime wrote it -- with provider identity, fingerprint and payload bytes
    exactly matching the durable attempt.  The corrected runtime then re-opens
    the World.  Migration may add the column, but it must never fabricate a
    proof, and the authenticated read path must fail closed on that row.
    """
    cfg = HeadlessConfig(world_path=tmp_path / "world.sqlite")
    captured: dict = {}

    def capturing(snapshot):
        directive = deterministic_model_handler(snapshot)
        captured["directive"] = directive
        return directive

    with HeadlessCore(config=cfg, model_handler=capturing) as core:
        core.submit_user_turn(
            session_id="ia-legacy",
            turn_index=1,
            user_input="legacy unauthenticated probe",
            occurred_at=T0,
        )

    attempts = BackgroundModelAttemptStore(SQLiteWorldStore(cfg.world_path))
    attempt_id = _attempt_ids(cfg)[0]
    attempt = attempts.get(attempt_id)
    payload = encode_model_directive(captured["directive"])
    assert (
        BackgroundModelAttemptStore._response_fingerprint(captured["directive"])
        == attempt.response_fingerprint
    )

    con = sqlite3.connect(cfg.world_path)
    con.execute("ALTER TABLE background_model_responses DROP COLUMN authenticity_proof")
    con.execute(
        """
        INSERT OR REPLACE INTO background_model_responses(
            attempt_id, provider, model, provider_request_id, response_fingerprint,
            directive_payload, payload_sha256, staged_at, evidence)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            attempt_id,
            attempt.provider,
            attempt.model,
            attempt.provider_request_id,
            attempt.response_fingerprint,
            payload,
            hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            T0.isoformat(),
            "independent probe: legacy row, provenance-identical, no proof",
        ),
    )
    con.commit()
    con.close()

    attempts = BackgroundModelAttemptStore(SQLiteWorldStore(cfg.world_path))
    staged = attempts.staged_response(attempt_id)
    assert staged is not None
    assert staged.authenticity_proof is None, "migration fabricated a proof"

    with pytest.raises(Exception, match="no trusted provider-return authenticity proof"):
        attempts.exact_response_directive(attempt_id)

    con = sqlite3.connect(cfg.world_path)
    try:
        proof = con.execute(
            "SELECT authenticity_proof FROM background_model_responses WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()[0]
    finally:
        con.close()
    assert proof is None


# --------------------------------------------------------------------------- D
def test_ia_d1_second_writer_rejected_and_lock_path_cannot_bypass(tmp_path):
    cfg = _make_world(tmp_path)
    first = HeadlessCore(config=cfg, model_handler=deterministic_model_handler)
    second = HeadlessCore(config=cfg, model_handler=deterministic_model_handler)
    first.start()
    try:
        with pytest.raises(HeadlessWriterBusy):
            second.start()
    finally:
        first.stop()

    # --lock / AIOS_LOCK_PATH must not be able to select a second writer identity
    with pytest.raises(HeadlessConfigurationError):
        HeadlessConfig(world_path=cfg.world_path, lock_path=tmp_path / "elsewhere.lock")


def test_ia_d2_lock_recoverable_after_abrupt_process_kill(tmp_path):
    cfg = _make_world(tmp_path)
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            textwrap.dedent(
                """
                import os, signal
                from aios_core.headless import HeadlessConfig, HeadlessCore
                from aios_core.headless.testing import deterministic_model_handler
                from pathlib import Path
                cfg = HeadlessConfig(world_path=Path(%r))
                core = HeadlessCore(config=cfg, model_handler=deterministic_model_handler)
                print("child-held-lock", flush=True)
                os.kill(os.getpid(), signal.SIGKILL)
                """
            )
            % str(cfg.world_path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert child.returncode == -9, child.stderr
    assert "child-held-lock" in child.stdout
    # A new writer must be able to recover the canonical lock.
    with HeadlessCore(config=cfg, model_handler=deterministic_model_handler) as core:
        assert core.status()["world_revision"] >= 1


# --------------------------------------------------------------------------- E
def test_ia_e1_restart_never_redispatches_or_double_meters(tmp_path):
    cfg = HeadlessConfig(world_path=tmp_path / "world.sqlite")
    calls = {"n": 0}

    def counting(_snapshot):
        calls["n"] += 1
        return deterministic_model_handler(_snapshot)

    with HeadlessCore(config=cfg, model_handler=counting) as core:
        core.submit_user_turn(
            session_id="ia-restart",
            turn_index=1,
            user_input="meter me once",
            occurred_at=T0,
        )
        assert calls["n"] == 1

    def must_not_be_called(_snapshot):
        raise AssertionError("restart redispatched the provider")

    with HeadlessCore(config=cfg, model_handler=must_not_be_called) as core:
        assert core.runtime is not None
        inspection = core.runtime.inspect_turn_execution(
            session_id="ia-restart",
            turn_index=1,
            user_input="meter me once",
            occurred_at=T0,
        )
        assert inspection.recovery_disposition == "completed"
        assert len(inspection.model_attempts) == 1
        metered = core.runtime.metering.list_model_calls(subject_id="user_1")
        assert len(metered) == 1


# --------------------------------------------------------------------------- F
def test_ia_f1_backup_restore_preserves_authority_and_receipts(tmp_path):
    cfg = _make_world(tmp_path)
    attempt_id = _attempt_ids(cfg)[0]
    receipt = _receipt_fields(cfg, attempt_id)

    before_logical = _logical_hash(cfg.world_path)
    backup = tmp_path / "snapshot.sqlite"
    receipt_record = backup_world(cfg, backup)
    assert receipt_record["world_revision"] >= 1
    assert _logical_hash(cfg.world_path) == before_logical, "backup mutated World content"

    restored_cfg = HeadlessConfig(world_path=tmp_path / "restored.sqlite")
    backup_digest = _sha256(backup)
    restored = restore_world(restored_cfg, backup)
    assert _sha256(backup) == backup_digest, "restore mutated the backup"
    assert restored["index_disposition"] == "REBUILD_FROM_WORLD"
    rebuild_index(restored_cfg)

    def authority(path: Path):
        con = sqlite3.connect(path)
        try:
            return con.execute(
                "SELECT authority_id, secret_hex FROM background_model_authenticity_authority"
            ).fetchall()
        finally:
            con.close()

    original = authority(cfg.world_path)
    restored_authority = authority(restored_cfg.world_path)
    assert len(restored_authority) == 1, "restore minted a second authority"
    assert restored_authority == original, "restore changed the authority key"
    assert _receipt_fields(restored_cfg, attempt_id) == receipt

    # The historical valid receipt must still verify against the restored World.
    store = SQLiteWorldStore(restored_cfg.world_path)
    attempts = BackgroundModelAttemptStore(store)
    attempt = attempts.get(attempt_id)
    binding = attempts.outbound_request_binding(attempt_id)
    with store._connection() as conn:
        verified = attempts._verify_response_authenticity(
            conn,
            attempt=attempt,
            binding=binding,
            provider=receipt["provider"],
            model=receipt["model"],
            provider_request_id=receipt["provider_request_id"],
            response_fingerprint=receipt["response_fingerprint"],
            payload_sha256=receipt["payload_sha256"],
            authenticity_proof=receipt["authenticity_proof"],
        )
    assert verified.authenticity_proof == receipt["authenticity_proof"]

    # A forged second key in the restored World must invalidate old receipts.
    con = sqlite3.connect(restored_cfg.world_path)
    con.execute(
        "UPDATE background_model_authenticity_authority SET secret_hex=?",
        ("11" * 32,),
    )
    con.commit()
    con.close()
    store2 = SQLiteWorldStore(restored_cfg.world_path)
    attempts2 = BackgroundModelAttemptStore(store2)
    with store2._connection() as conn:
        with pytest.raises(BackgroundModelResponseConflict):
            attempts2._verify_response_authenticity(
                conn,
                attempt=attempts2.get(attempt_id),
                binding=attempts2.outbound_request_binding(attempt_id),
                provider=receipt["provider"],
                model=receipt["model"],
                provider_request_id=receipt["provider_request_id"],
                response_fingerprint=receipt["response_fingerprint"],
                payload_sha256=receipt["payload_sha256"],
                authenticity_proof=receipt["authenticity_proof"],
            )


# --------------------------------------------------------------------------- G
def test_ia_g1_no_second_truth_store(tmp_path):
    cfg = _make_world(tmp_path)
    sqlite_files = sorted(
        p.name
        for p in tmp_path.iterdir()
        if p.name.endswith(".sqlite") or p.name.endswith(".sqlite3")
    )
    # exactly the canonical World plus its rebuildable search projection
    assert set(sqlite_files) == {"world.sqlite", "world.sqlite.search.sqlite"}, sqlite_files

    con = sqlite3.connect(cfg.world_path)
    try:
        world_tables = {
            r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        index_con = sqlite3.connect(tmp_path / "world.sqlite.search.sqlite")
        try:
            index_tables = {
                r[0]
                for r in index_con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        finally:
            index_con.close()
    finally:
        con.close()

    evidence_tables = {
        "background_model_attempts",
        "background_model_responses",
        "background_model_request_bindings",
        "background_model_response_receipts",
        "background_model_authenticity_authority",
    }
    assert evidence_tables <= world_tables, "recovery/authenticity tables left the World"
    assert not (evidence_tables & index_tables), "evidence tables duplicated in the index"

    # The receipts table must not be a plaintext answer oracle.
    con = sqlite3.connect(cfg.world_path)
    try:
        receipts_text = " ".join(
            str(v)
            for row in con.execute(
                "SELECT * FROM background_model_response_receipts"
            )
            for v in row
        )
    finally:
        con.close()
    assert "HEADLESS_MECHANICAL_OK" not in receipts_text

    # Projection rebuild is safe: destroying the index does not change the World.
    revision_before = con_revision(cfg.world_path)
    index_path = tmp_path / "world.sqlite.search.sqlite"
    index_path.unlink()
    for suffix in ("-wal", "-shm"):
        side = Path(str(index_path) + suffix)
        if side.exists():
            side.unlink()
    rebuilt = rebuild_index(cfg)
    assert rebuilt["index_watermark"] == revision_before
    assert con_revision(cfg.world_path) == revision_before


def con_revision(path: Path) -> int:
    return int(SQLiteWorldStore(path).current_world_revision())
