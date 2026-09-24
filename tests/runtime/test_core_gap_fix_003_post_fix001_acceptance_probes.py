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
from aios_core.runtime.turn_execution import TURN_PRE_ATTEMPT_PROTOCOL
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 24, 10, 30, tzinfo=timezone.utc)
TURN = {
    "session_id": "post-fix001-acceptance-probe",
    "turn_index": 1,
    "user_input": "SYNTHETIC post-FIX001 acceptance probe",
    "occurred_at": NOW,
}


def _world(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.sqlite")
    index = WorldSearchIndex(tmp_path / "index.sqlite", store=store)
    return store, index


def _directive(request_id):
    return ModelDirective(
        response="SYNTHETIC acceptance probe response",
        usage=ModelUsage(
            input_tokens=4,
            output_tokens=3,
            total_tokens=7,
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


def _reopen(store, index, model_handler):
    reopened_store = SQLiteWorldStore(store.db_path)
    return FusedTurnRuntime(
        store=reopened_store,
        index=WorldSearchIndex(index.db_path, store=reopened_store),
        model_handler=model_handler,
    )


def test_post_fix001_crash_x3_provider_attempt_output_stay_single(tmp_path, monkeypatch):
    store, index = _world(tmp_path)
    provider_calls = []

    def model(_snapshot):
        provider_calls.append("called")
        return _directive("post-fix001-crash-x3")

    def crash_before_attempt(**_kwargs):
        raise RuntimeError("SYNTHETIC crash before initial attempt admission")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)
    monkeypatch.setattr(runtime.background_model_attempts, "admit", crash_before_attempt)
    with pytest.raises(RuntimeError, match="before initial attempt admission"):
        runtime.run_turn(**TURN)

    # Two more crash/restart cycles. Each needs fresh explicit authorization,
    # and each consumed authorization must not survive the failed retry claim.
    for expected_retry_count in (1, 2):
        runtime = _reopen(store, index, model)
        inspected = runtime.inspect_turn_execution(**TURN)
        assert inspected.recovery_disposition == "safe_to_retry"
        assert inspected.model_attempts == ()
        runtime.authorize_turn_retry(
            **TURN,
            evidence=f"pre-admission proof for crash cycle {expected_retry_count}",
        )
        monkeypatch.setattr(runtime.background_model_attempts, "admit", crash_before_attempt)
        with pytest.raises(RuntimeError, match="before initial attempt admission"):
            runtime.run_turn(**TURN)
        after = runtime.inspect_turn_execution(**TURN)
        assert after.retry_count == expected_retry_count
        assert after.model_attempts == ()
        assert provider_calls == []

    runtime = _reopen(store, index, model)
    final_pre = runtime.inspect_turn_execution(**TURN)
    assert final_pre.recovery_disposition == "safe_to_retry"
    assert final_pre.retry_count == 2
    runtime.authorize_turn_retry(
        **TURN,
        evidence="third crash still proves provider dispatch was impossible",
    )
    result = runtime.run_turn(**TURN)
    assert result.runtime.response == "SYNTHETIC acceptance probe response"
    assert provider_calls == ["called"]

    final = runtime.inspect_turn_execution(**TURN)
    assert final.recovery_disposition == "completed"
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
            SELECT COUNT(*) FROM background_model_attempts
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


def test_post_fix001_forged_pre_admission_marker_cannot_override_real_in_doubt_attempt(tmp_path):
    store, index = _world(tmp_path)
    provider_calls = []

    def ambiguous(_snapshot):
        provider_calls.append("called")
        raise TimeoutError("provider submission may have crossed boundary")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=ambiguous)
    with pytest.raises(TimeoutError):
        runtime.run_turn(**TURN)

    before = runtime.inspect_turn_execution(**TURN)
    assert [attempt.state for attempt in before.model_attempts] == ["in_doubt"]

    # Forge a stale turn marker after a real provider-attempt row exists.
    with sqlite3.connect(store.db_path) as conn:
        conn.execute(
            """
            UPDATE runtime_turn_executions
            SET attempt_protocol=?
            WHERE subject_id=? AND session_id=? AND turn_index=?
            """,
            (
                TURN_PRE_ATTEMPT_PROTOCOL,
                runtime.subject_id,
                TURN["session_id"],
                TURN["turn_index"],
            ),
        )

    reopened = _reopen(store, index, ambiguous)
    inspected = reopened.inspect_turn_execution(**TURN)
    assert inspected.recovery_disposition == "in_doubt"
    assert len(inspected.model_attempts) == 1
    assert inspected.model_attempts[0].state == "in_doubt"
    with pytest.raises(TurnExecutionInDoubt):
        reopened.authorize_turn_retry(
            **TURN,
            evidence="forged pre-admission marker must not dominate attempt ledger",
        )
    with pytest.raises(TurnExecutionInDoubt):
        reopened.run_turn(**TURN)
    assert provider_calls == ["called"]
