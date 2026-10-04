"""Phase D authority-lifecycle freeze: verifier consumption and exact replay."""

from __future__ import annotations

import sqlite3

import pytest

from aios_core.runtime.background_attempt import BackgroundModelResponseConflict
from test_core_background_late_trusted_return_corrective_001 import (
    ExternalSigner,
    _attach,
    _directive,
    _dispatch_dead,
    _restart,
)


def test_phase_d_verifier_consumed_exact_replay_only(tmp_path):
    """T7/T9: consumed verifier permits only the already-attached exact return."""

    db = tmp_path / "phase-d-consumed.sqlite"
    signer = ExternalSigner()
    _runtime, attempt = _dispatch_dead(db, signer)
    directive = _directive()
    proof = signer.proof(attempt.attempt_id, directive)
    fresh = _restart(db)

    first = _attach(fresh, attempt, directive, proof)
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            """
            SELECT consumed_at
            FROM background_model_return_verifiers
            WHERE attempt_id=?
            """,
            (attempt.attempt_id,),
        ).fetchone()
        assert row is not None
        assert row[0] is not None

    replay = _attach(fresh, attempt, directive, proof)
    assert replay.directive_payload == first.directive_payload

    conflicting = _directive(response="different response signed by same external key")
    conflicting_proof = signer.proof(attempt.attempt_id, conflicting)
    with pytest.raises(BackgroundModelResponseConflict):
        _attach(fresh, attempt, conflicting, conflicting_proof)

    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT count(*) FROM background_model_response_receipts WHERE attempt_id=?",
            (attempt.attempt_id,),
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT count(*) FROM background_model_return_handoffs WHERE attempt_id=?",
            (attempt.attempt_id,),
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT count(*) FROM background_model_responses WHERE attempt_id=?",
            (attempt.attempt_id,),
        ).fetchone()[0] == 1
