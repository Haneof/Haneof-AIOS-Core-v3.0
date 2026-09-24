from datetime import datetime, timezone
import sqlite3

import pytest

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
    TurnExecutionInDoubt,
)
from aios_core.runtime.background_attempt import BackgroundModelAttemptStore
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 24, 10, 0, tzinfo=timezone.utc)
TURN = {
    "session_id": "independent-corrective-probe",
    "turn_index": 1,
    "user_input": "independent corrective recovery probe",
    "occurred_at": NOW,
}


def _directive(request_id: str):
    return ModelDirective(
        response="independent recovered response",
        usage=ModelUsage(
            input_tokens=2,
            output_tokens=2,
            total_tokens=4,
            provider="synthetic",
            model="synthetic-model",
            request_id=request_id,
        ),
        provenance=ModelCallProvenance(
            provider="synthetic",
            model="synthetic-model",
            request_id=request_id,
        ),
    )


def _world(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.sqlite")
    index = WorldSearchIndex(tmp_path / "index.sqlite", store=store)
    return store, index


def _reopen(store, index, model):
    reopened_store = SQLiteWorldStore(store.db_path)
    reopened_index = WorldSearchIndex(index.db_path, store=reopened_store)
    return FusedTurnRuntime(
        store=reopened_store,
        index=reopened_index,
        model_handler=model,
    )


def test_independent_three_consecutive_pre_attempt_crashes_recover_exactly_once(
    tmp_path, monkeypatch
):
    store, index = _world(tmp_path)
    provider_calls = []

    def model(_snapshot):
        provider_calls.append("called")
        return _directive("independent-crash-x3")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)

    def crash_before_admission(**_kwargs):
        raise RuntimeError("INDEPENDENT pre-attempt admission crash")

    # Crash #1 is on the fresh claim. Crashes #2 and #3 occur after a fresh,
    # one-shot explicit authorization has been consumed by claim().
    for crash_index in range(3):
        if crash_index:
            authorized = runtime.authorize_turn_retry(
                **TURN,
                evidence=f"independent authorization before crash {crash_index + 1}",
            )
            assert authorized.recovery_disposition == "retry_authorized"

        monkeypatch.setattr(
            runtime.background_model_attempts,
            "admit",
            crash_before_admission,
        )
        with pytest.raises(RuntimeError, match="pre-attempt admission crash"):
            runtime.run_turn(**TURN)

        runtime = _reopen(store, index, model)
        inspected = runtime.inspect_turn_execution(**TURN)
        assert inspected.recovery_disposition == "safe_to_retry"
        assert inspected.model_attempts == ()
        assert inspected.retry_count == crash_index
        assert provider_calls == []

        # The authorization used for the just-failed retry is consumed atomically;
        # an ordinary run cannot reuse it.
        with pytest.raises(TurnExecutionInDoubt):
            runtime.run_turn(**TURN)

    runtime.authorize_turn_retry(
        **TURN,
        evidence="independent final authorization after crash 3",
    )
    result = runtime.run_turn(**TURN)
    assert result.runtime.response == "independent recovered response"
    assert provider_calls == ["called"]

    final = runtime.inspect_turn_execution(**TURN)
    assert final.recovery_disposition == "completed"
    assert final.retry_count == 3
    assert len(final.model_attempts) == 1

    expected_attempt_id = BackgroundModelAttemptStore.attempt_id_for(
        subject_id=runtime.subject_id,
        work_kind="user_turn",
        work_id=final.execution_id,
        model_round_index=0,
    )
    assert final.model_attempts[0].attempt_id == expected_attempt_id

    _, _, assistant_id = runtime.ingestor._turn_identity(
        TURN["session_id"], TURN["turn_index"]
    )
    with sqlite3.connect(store.db_path) as conn:
        attempt_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM background_model_attempts
            WHERE subject_id=? AND work_kind='user_turn' AND work_id=?
              AND model_round_index=0
            """,
            (runtime.subject_id, final.execution_id),
        ).fetchone()[0]
        assistant_rows = conn.execute(
            "SELECT COUNT(*) FROM object_revisions WHERE object_id=?",
            (assistant_id,),
        ).fetchone()[0]

    assert attempt_rows == 1
    assert assistant_rows == 1


def test_independent_attempt_ledger_in_doubt_dominates_pre_admission_marker(
    tmp_path, monkeypatch
):
    store, index = _world(tmp_path)
    provider_calls = []

    def model(_snapshot):
        provider_calls.append("called")
        return _directive("must-not-run")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)

    # Force a crash after the deterministic round-0 attempt is durable but before
    # turn protocol promotion. This deliberately leaves pre-admission marker +
    # a real attempt row, then we drive that attempt ledger to IN_DOUBT.
    def crash_before_protocol_promotion(**_kwargs):
        raise RuntimeError("INDEPENDENT crash before protocol promotion")

    monkeypatch.setattr(
        runtime.turn_executions,
        "mark_initial_attempt_admitted",
        crash_before_protocol_promotion,
    )
    with pytest.raises(RuntimeError, match="before protocol promotion"):
        runtime.run_turn(**TURN)

    after_admission = runtime.inspect_turn_execution(**TURN)
    assert len(after_admission.model_attempts) == 1
    attempt = after_admission.model_attempts[0]
    assert attempt.state == "admitted"
    assert provider_calls == []

    runtime.background_model_attempts.mark_dispatching(
        attempt.attempt_id,
        dispatched_at=NOW,
    )
    runtime.background_model_attempts.mark_failure(
        attempt.attempt_id,
        failed_at=NOW,
        definitely_not_submitted=False,
        error=TimeoutError("provider submission may have occurred"),
    )

    conflicted = runtime.inspect_turn_execution(**TURN)
    assert conflicted.model_attempts[0].state == "in_doubt"
    assert conflicted.recovery_disposition == "in_doubt"

    with pytest.raises(TurnExecutionInDoubt):
        runtime.authorize_turn_retry(
            **TURN,
            evidence="pre-admission marker must not override attempt truth",
        )
