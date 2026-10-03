"""Real process-loss proof for verifier-only late trusted return.

Process A receives only the public verifier and public dispatch context. The
external side keeps the synthetic test private RSA exponent and signs only after
Process A is confirmed dead by SIGKILL. Process B reopens the same SQLite world,
adopts the exact response, and must not redispatch the provider.
"""

from __future__ import annotations

import hashlib
import multiprocessing
import os
import signal
import sqlite3

import pytest

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import TurnAlreadyCompleted
from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.late_return import LateReturnSigningContext, late_return_message
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from test_core_background_late_trusted_return_corrective_001 import (
    NOW,
    _directive,
    _rsa_sign,
    _verifier,
)


SESSION = "w16-real-sigkill-session"
INPUT = "resume one verifier-only late return after real SIGKILL"


class _PipeObserver:
    def __init__(self, conn):
        self.conn = conn

    def accept_return_context(self, snapshot, context):
        assert snapshot.model_attempt_id == context.attempt_id
        self.conn.send(context.model_dump(mode="json"))
        self.conn.close()


def _child(db_path: str, conn) -> None:
    store = SQLiteWorldStore(db_path)
    index = WorldSearchIndex(db_path, store=store)
    index.rebuild()

    def kill_at_provider_boundary(_snapshot):
        os.kill(os.getpid(), signal.SIGKILL)
        raise AssertionError("SIGKILL must not return")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=kill_at_provider_boundary,
        late_return_verifier=_verifier(),
        external_return_observer=_PipeObserver(conn),
    )
    runtime.run_turn(
        session_id=SESSION,
        turn_index=1,
        user_input=INPUT,
        occurred_at=NOW,
        current_topic=None,
    )


def test_real_sigkill_external_signer_recovers_exactly_once_without_redispatch(tmp_path):
    db = tmp_path / "real-sigkill-verifier-only.sqlite"
    SQLiteWorldStore(db)

    mp = multiprocessing.get_context("fork")
    parent_conn, child_conn = mp.Pipe(duplex=False)
    child = mp.Process(target=_child, args=(str(db), child_conn))
    child.start()
    child.join(60)

    assert child.exitcode == -signal.SIGKILL
    assert parent_conn.poll(30)
    context = LateReturnSigningContext(**parent_conn.recv())

    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    provider_calls: list[int] = []

    def no_redispatch(snapshot):
        provider_calls.append(snapshot.round_index)
        pytest.fail("provider redispatch is forbidden after exact late return")

    fresh = FusedTurnRuntime(store=store, index=index, model_handler=no_redispatch)
    attempt = fresh.background_model_attempts.get(context.attempt_id)
    assert attempt is not None
    assert attempt.state == "dispatching"

    exact = _directive(
        request_id="w16-real-sigkill-provider-request",
        response="verifier-only SIGKILL response",
    )
    payload = encode_model_directive(exact)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    proof = _rsa_sign(
        late_return_message(
            **context.scope_fields(),
            provider=exact.provenance.provider,
            model=exact.provenance.model,
            provider_request_id=exact.provenance.request_id,
            response_fingerprint=digest,
            payload_sha256=digest,
        ),
        context.verifier_key_id,
    )

    staged = fresh.background_model_attempts.attach_late_trusted_return(
        context.attempt_id,
        attached_at=NOW,
        directive_payload=payload,
        late_return_proof=proof,
        evidence="external signer survived real Core SIGKILL",
    )
    assert staged.directive_payload == payload

    result = fresh.run_turn(
        session_id=SESSION,
        turn_index=1,
        user_input=INPUT,
        occurred_at=NOW,
        current_topic=None,
    )
    assert result.runtime.response == "verifier-only SIGKILL response"
    assert provider_calls == []

    inspection = fresh.inspect_turn_execution(
        session_id=SESSION,
        turn_index=1,
        user_input=INPUT,
        occurred_at=NOW,
    )
    assert inspection.state == "completed"
    assert inspection.assistant_ref is not None
    assert len(inspection.model_attempts) == 1
    assert inspection.model_attempts[0].state == "metered"

    meters = fresh.metering.list_model_calls(
        subject_id="user_1", execution_classes=("user_interaction",)
    )
    assert len(meters) == 1

    with sqlite3.connect(db) as conn:
        consumed = conn.execute(
            """
            SELECT consumed_at FROM background_model_return_verifiers
            WHERE attempt_id=?
            """,
            (context.attempt_id,),
        ).fetchone()
        assert consumed is not None and consumed[0] is not None
        assert conn.execute(
            "SELECT count(*) FROM background_model_response_receipts WHERE attempt_id=?",
            (context.attempt_id,),
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT count(*) FROM background_model_return_handoffs WHERE attempt_id=?",
            (context.attempt_id,),
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT count(*) FROM background_model_responses WHERE attempt_id=?",
            (context.attempt_id,),
        ).fetchone()[0] == 1

    with pytest.raises(TurnAlreadyCompleted):
        fresh.run_turn(
            session_id=SESSION,
            turn_index=1,
            user_input=INPUT,
            occurred_at=NOW,
            current_topic=None,
        )
    assert provider_calls == []
    assert len(
        fresh.metering.list_model_calls(
            subject_id="user_1", execution_classes=("user_interaction",)
        )
    ) == 1
