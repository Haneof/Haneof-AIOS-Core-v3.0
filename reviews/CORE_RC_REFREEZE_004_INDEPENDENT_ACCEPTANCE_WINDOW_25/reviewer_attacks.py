"""Window 25 reviewer-owned attacks, frozen before first candidate execution.

Enumeration and expected results are deliberately declared in REVIEW_CASES.  These
tests exercise the accepted frozen software, not the RC evidence checkout.
"""

from __future__ import annotations

import inspect
import shutil
import sqlite3
import threading
from datetime import timedelta

import pytest

from aios_core.headless.core import HeadlessConfig
from aios_core.headless.recovery import backup_world, rebuild_index, restore_world
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import BackgroundModelResponseConflict
from aios_core.runtime import background_attempt, live_return
from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from test_core_background_late_trusted_return_corrective_002 import (
    NOW,
    ExternalSigner,
    dispatch_and_crash,
    fresh_recovery_runtime,
    make_directive,
    make_verifier,
    move_to_in_doubt,
    trust_rows,
)


REVIEW_CASES = {
    "W25-OWN-01": "local/reflection/tombstone paths create zero trusted rows",
    "W25-OWN-02": "forged-first loses; genuine proof wins; exact replay is idempotent",
    "W25-OWN-03": "changed bytes and proof transplant fail closed",
    "W25-OWN-04": "verifier-less recovery remains in_doubt with zero trusted rows",
    "W25-OWN-05": "competing genuine proofs have exactly one winner",
    "W25-OWN-06": "partial receipt/handoff survives backup/restore and index rebuild",
    "W25-OWN-07": "consumed verifier plus missing receipt or handoff fails closed",
    "W25-OWN-08": "restored/cloned World neither redispatches nor duplicates meter/effect",
}

FORBIDDEN_LOCAL_MINTS = {
    "record_live_provider_return",
    "_capture_trusted_response_return",
    "consume_live_provider_return_window",
    "_ISSUE_SENTINEL",
    "_OPEN_WINDOWS",
    "_HANDLER_RETURNS",
    "background_model_authenticity_authority",
}


def _context(tmp_path, name: str, *, verifier: bool = True):
    db = tmp_path / f"{name}.sqlite"
    signer = ExternalSigner() if verifier else None
    _, attempt = dispatch_and_crash(
        db,
        session_id=name,
        verifier=make_verifier() if verifier else None,
        signer=signer,
    )
    runtime = fresh_recovery_runtime(db)
    move_to_in_doubt(runtime, attempt)
    return db, signer, attempt, runtime


def _attach(runtime, attempt_id, directive, proof, seconds: int = 5):
    return runtime.background_model_attempts.attach_late_trusted_return(
        attempt_id,
        attached_at=NOW + timedelta(seconds=seconds),
        directive_payload=encode_model_directive(directive),
        late_return_proof=proof,
        evidence="Window 25 reviewer-owned external proof",
    )


def _row_count(db, table: str) -> int:
    with sqlite3.connect(db) as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def test_w25_own_01_local_reflection_and_tombstone_are_inert(tmp_path):
    db, _, attempt, runtime = _context(tmp_path, "w25-own-01")
    holders = (
        vars(background_attempt),
        vars(live_return),
        vars(type(runtime.background_model_attempts)),
        vars(runtime.background_model_attempts),
        vars(runtime),
    )
    for holder in holders:
        assert FORBIDDEN_LOCAL_MINTS.isdisjoint(holder)
        for value in holder.values():
            fn = getattr(value, "__func__", value)
            if inspect.isfunction(fn):
                assert FORBIDDEN_LOCAL_MINTS.isdisjoint(fn.__globals__)

    forged = make_directive(response="W25_LOCAL_FORGERY")
    with live_return.open_live_provider_return_window(
        attempt_id=attempt.attempt_id
    ) as marker:
        live_return.register_handler_return(marker, forged)
        snap = live_return.live_return_authority_snapshot()
        assert snap["decommissioned"] is True
        assert snap["trust_conferred"] is False
        assert snap["durable_trusted_return_authority"] == (
            "external_verifier_plus_genuine_proof_only"
        )
    assert not hasattr(runtime.background_model_attempts, "record_live_provider_return")
    assert trust_rows(db) == (0, 0, 0)
    assert runtime.background_model_attempts.get(attempt.attempt_id).state == "in_doubt"


def test_w25_own_02_03_forged_first_replay_conflict_and_transplant(tmp_path):
    db, signer, attempt, runtime = _context(tmp_path, "w25-own-02")
    assert signer is not None
    winner = make_directive(response="W25_GENUINE_WINNER")
    forged = "bglate_rsa_v1:ca2-external-key:" + "00" * 256
    with pytest.raises(BackgroundModelResponseConflict):
        _attach(runtime, attempt.attempt_id, winner, forged)
    assert trust_rows(db) == (0, 0, 0)

    proof = signer.sign(attempt.attempt_id, winner)
    first = _attach(runtime, attempt.attempt_id, winner, proof, 10)
    replay = _attach(runtime, attempt.attempt_id, winner, proof, 11)
    assert first.directive_payload == replay.directive_payload
    assert trust_rows(db) == (1, 1, 1)

    changed = make_directive(response="W25_CHANGED_CANONICAL_BYTES")
    with pytest.raises(BackgroundModelResponseConflict):
        _attach(runtime, attempt.attempt_id, changed, signer.sign(attempt.attempt_id, changed), 12)
    assert trust_rows(db) == (1, 1, 1)

    other_db, other_signer, other_attempt, other_runtime = _context(
        tmp_path, "w25-own-03-transplant"
    )
    assert other_signer is not None
    with pytest.raises(BackgroundModelResponseConflict):
        _attach(other_runtime, other_attempt.attempt_id, winner, proof, 13)
    assert trust_rows(other_db) == (0, 0, 0)


def test_w25_own_04_verifierless_fails_closed(tmp_path):
    db, _, attempt, runtime = _context(tmp_path, "w25-own-04", verifier=False)
    forged = make_directive(response="W25_VERIFIERLESS_FORGERY")
    with pytest.raises(BackgroundModelResponseConflict):
        _attach(
            runtime,
            attempt.attempt_id,
            forged,
            "bglate_rsa_v1:ca2-external-key:" + "00" * 256,
        )
    assert runtime.background_model_attempts.late_return_verifier(attempt.attempt_id) is None
    assert runtime.background_model_attempts.get(attempt.attempt_id).state == "in_doubt"
    assert trust_rows(db) == (0, 0, 0)


def test_w25_own_05_competing_genuine_proofs_one_winner(tmp_path):
    db, signer, attempt, runtime = _context(tmp_path, "w25-own-05")
    assert signer is not None
    directives = [
        make_directive(response="W25_RACE_A"),
        make_directive(response="W25_RACE_B"),
    ]
    proofs = [signer.sign(attempt.attempt_id, directive) for directive in directives]
    barrier = threading.Barrier(2)
    results: list[str] = []

    def compete(index: int) -> None:
        barrier.wait()
        try:
            _attach(runtime, attempt.attempt_id, directives[index], proofs[index], 20 + index)
        except BackgroundModelResponseConflict:
            results.append("refused")
        else:
            results.append("accepted")

    threads = [threading.Thread(target=compete, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["accepted", "refused"]
    assert trust_rows(db) == (1, 1, 1)


def test_w25_own_06_07_08_backup_restore_partial_and_missing_rows(tmp_path):
    source = tmp_path / "w25-source.sqlite"
    signer = ExternalSigner()
    _, attempt = dispatch_and_crash(
        source,
        session_id="w25-own-restore",
        verifier=make_verifier(),
        signer=signer,
    )
    runtime = fresh_recovery_runtime(source)
    move_to_in_doubt(runtime, attempt)
    directive = make_directive(response="W25_RESTORED_GENUINE")
    proof = signer.sign(attempt.attempt_id, directive)

    cls = type(runtime.background_model_attempts)
    original_stage = cls.stage_exact_response

    class CrashBeforeStage(BaseException):
        pass

    def crash_before_stage(self, *args, **kwargs):
        raise CrashBeforeStage

    cls.stage_exact_response = crash_before_stage
    try:
        with pytest.raises(CrashBeforeStage):
            _attach(runtime, attempt.attempt_id, directive, proof, 30)
    finally:
        cls.stage_exact_response = original_stage

    assert trust_rows(source) == (1, 1, 0)
    with sqlite3.connect(source) as conn:
        consumed = conn.execute(
            "SELECT consumed_at FROM background_model_return_verifiers WHERE attempt_id=?",
            (attempt.attempt_id,),
        ).fetchone()
    assert consumed is not None and consumed[0] is not None

    source_config = HeadlessConfig(
        world_path=source, index_path=tmp_path / "w25-source-index.sqlite"
    )
    backup = tmp_path / "w25-backup.sqlite"
    backup_world(source_config, backup)
    immutable_before = backup.read_bytes()

    restored = tmp_path / "w25-restored.sqlite"
    restored_index = tmp_path / "w25-restored-index.sqlite"
    restored_config = HeadlessConfig(world_path=restored, index_path=restored_index)
    restore_world(restored_config, backup)
    rebuild_index(restored_config)
    assert backup.read_bytes() == immutable_before

    calls: list[int] = []

    def forbidden_provider(snapshot):
        calls.append(int(snapshot.round_index))
        raise AssertionError("provider redispatch")

    restored_store = SQLiteWorldStore(restored)
    restored_search = WorldSearchIndex(restored_index, store=restored_store)
    restored_runtime = FusedTurnRuntime(
        store=restored_store,
        index=restored_search,
        subject_id="user_1",
        model_handler=forbidden_provider,
    )
    _attach(restored_runtime, attempt.attempt_id, directive, proof, 31)
    result = restored_runtime.run_turn(
        session_id="w25-own-restore",
        turn_index=1,
        user_input="corrective-002 adversarial matrix input",
        occurred_at=NOW,
    )
    assert result.runtime.response == "W25_RESTORED_GENUINE"
    assert calls == []
    assert _row_count(restored, "metering_records") == 1
    assert trust_rows(restored) == (1, 1, 1)

    for table in (
        "background_model_response_receipts",
        "background_model_return_handoffs",
    ):
        damaged = tmp_path / f"w25-damaged-{table}.sqlite"
        shutil.copyfile(backup, damaged)
        with sqlite3.connect(damaged) as conn:
            conn.execute(f"DELETE FROM {table} WHERE attempt_id=?", (attempt.attempt_id,))
            conn.commit()
        damaged_runtime = fresh_recovery_runtime(damaged)
        with pytest.raises(BackgroundModelResponseConflict):
            _attach(damaged_runtime, attempt.attempt_id, directive, proof, 40)
        assert damaged_runtime.background_model_attempts.staged_response(
            attempt.attempt_id
        ) is None


def test_reviewer_enumeration_is_frozen_and_complete():
    assert tuple(REVIEW_CASES) == tuple(f"W25-OWN-{i:02d}" for i in range(1, 9))

