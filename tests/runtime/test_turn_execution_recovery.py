from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelDispatchNotSubmitted,
    ModelUsage,
    TurnAlreadyCompleted,
    TurnExecutionInDoubt,
    TurnInputConflict,
)
from aios_core.runtime.background_attempt import BackgroundModelAttemptStore
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 24, 7, 0, tzinfo=timezone.utc)
TURN = {
    "session_id": "cg003-session",
    "turn_index": 1,
    "user_input": "SYNTHETIC CG003 request",
    "occurred_at": NOW,
}


def world(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.sqlite")
    index = WorldSearchIndex(tmp_path / "index.sqlite", store=store)
    return store, index


def successful_directive(request_id="cg003-ok"):
    return ModelDirective(
        response="SYNTHETIC recovered response",
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


def test_cg003_pre_model_failure_is_durably_proven_not_dispatched(tmp_path, monkeypatch):
    store, index = world(tmp_path)
    model_calls = []

    def model(_snapshot):
        model_calls.append("called")
        return successful_directive("must-not-run")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)

    def fail_before_model(*, now):
        raise RuntimeError("SYNTHETIC pre-model preparation failure")

    monkeypatch.setattr(runtime.attention_watches, "expire_due", fail_before_model)
    with pytest.raises(RuntimeError, match="pre-model preparation failure"):
        runtime.run_turn(**TURN)

    inspected = runtime.inspect_turn_execution(**TURN)
    assert inspected.recovery_disposition == "safe_to_retry"
    assert [attempt.state for attempt in inspected.model_attempts] == ["admitted"]
    assert model_calls == []

    with pytest.raises(TurnExecutionInDoubt):
        runtime.run_turn(**TURN)

    authorized = runtime.authorize_turn_retry(
        **TURN,
        evidence="durable attempt remained admitted before provider dispatch",
    )
    assert authorized.recovery_disposition == "retry_authorized"


def test_cg003_known_not_submitted_requires_explicit_retry_authorization(tmp_path):
    store, index = world(tmp_path)
    calls = []

    def not_submitted(_snapshot):
        calls.append("not-submitted")
        raise ModelDispatchNotSubmitted("adapter confirms request never left process")

    first = FusedTurnRuntime(store=store, index=index, model_handler=not_submitted)
    with pytest.raises(ModelDispatchNotSubmitted):
        first.run_turn(**TURN)

    inspected = first.inspect_turn_execution(**TURN)
    assert inspected.recovery_disposition == "safe_to_retry"
    assert [attempt.state for attempt in inspected.model_attempts] == ["not_submitted"]

    restarted = FusedTurnRuntime(
        store=SQLiteWorldStore(store.db_path),
        index=WorldSearchIndex(index.db_path, store=SQLiteWorldStore(store.db_path)),
        model_handler=lambda _snapshot: successful_directive("cg003-retry"),
    )
    with pytest.raises(TurnExecutionInDoubt):
        restarted.run_turn(**TURN)

    authorized = restarted.authorize_turn_retry(
        **TURN,
        evidence="durable adapter boundary proves no provider submission",
    )
    assert authorized.recovery_disposition == "retry_authorized"

    result = restarted.run_turn(**TURN)
    assert result.runtime.response == "SYNTHETIC recovered response"
    assert calls == ["not-submitted"]


def test_cg003_ambiguous_provider_interruption_stays_in_doubt_across_restart(tmp_path):
    store, index = world(tmp_path)
    calls = []

    def ambiguous(_snapshot):
        calls.append("called")
        raise TimeoutError("submission may have crossed provider boundary")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=ambiguous)
    with pytest.raises(TimeoutError):
        runtime.run_turn(**TURN)

    inspected = runtime.inspect_turn_execution(**TURN)
    assert inspected.recovery_disposition == "in_doubt"
    assert [attempt.state for attempt in inspected.model_attempts] == ["in_doubt"]

    reopened_store = SQLiteWorldStore(store.db_path)
    reopened_index = WorldSearchIndex(index.db_path, store=reopened_store)
    restarted = FusedTurnRuntime(
        store=reopened_store, index=reopened_index, model_handler=ambiguous
    )
    with pytest.raises(TurnExecutionInDoubt):
        restarted.authorize_turn_retry(
            **TURN,
            evidence="operator cannot prove non-execution",
        )
    with pytest.raises(TurnExecutionInDoubt):
        restarted.run_turn(**TURN)
    assert calls == ["called"]


def test_cg003_reconciled_not_submitted_attempt_can_be_authorized_after_restart(tmp_path):
    store, index = world(tmp_path)

    def ambiguous(_snapshot):
        raise TimeoutError("submission initially unknown")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=ambiguous)
    with pytest.raises(TimeoutError):
        runtime.run_turn(**TURN)

    reopened_store = SQLiteWorldStore(store.db_path)
    reopened_index = WorldSearchIndex(index.db_path, store=reopened_store)
    restarted = FusedTurnRuntime(
        store=reopened_store,
        index=reopened_index,
        model_handler=lambda _snapshot: successful_directive("cg003-reconciled"),
    )
    reconciled = restarted.reconcile_turn_model_not_submitted(
        **TURN,
        model_round_index=0,
        reconciled_at=NOW + timedelta(seconds=1),
        evidence="provider gateway durable log proves request was not accepted",
    )
    assert reconciled.model_attempts[0].state == "not_submitted"
    assert reconciled.recovery_disposition == "safe_to_retry"

    restarted.authorize_turn_retry(
        **TURN,
        evidence="provider gateway durable log proves request was not accepted",
    )
    result = restarted.run_turn(**TURN)
    assert result.runtime.response == "SYNTHETIC recovered response"


def test_cg003_response_provenance_durable_but_later_meter_failure_is_not_retryable(
    tmp_path, monkeypatch
):
    store, index = world(tmp_path)
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: successful_directive("cg003-response"),
    )

    def fail_meter(**_kwargs):
        raise RuntimeError("SYNTHETIC meter write interruption")

    monkeypatch.setattr(runtime.metering, "record_model_call", fail_meter)
    with pytest.raises(RuntimeError, match="meter write interruption"):
        runtime.run_turn(**TURN)

    inspected = runtime.inspect_turn_execution(**TURN)
    assert inspected.recovery_disposition == "in_doubt"
    assert inspected.model_attempts[0].state == "response_returned"
    assert inspected.model_attempts[0].provider_request_id == "cg003-response"
    with pytest.raises(TurnExecutionInDoubt):
        runtime.authorize_turn_retry(**TURN, evidence="response already returned")


def test_cg003_assistant_output_persistence_failure_remains_in_doubt(tmp_path, monkeypatch):
    store, index = world(tmp_path)
    calls = []

    def model(_snapshot):
        calls.append("called")
        return successful_directive("cg003-assistant-write")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)

    def fail_assistant(**_kwargs):
        raise RuntimeError("SYNTHETIC assistant persistence failure")

    monkeypatch.setattr(runtime.ingestor, "commit_assistant_output", fail_assistant)
    with pytest.raises(RuntimeError, match="assistant persistence failure"):
        runtime.run_turn(**TURN)

    inspected = runtime.inspect_turn_execution(**TURN)
    assert inspected.recovery_disposition == "in_doubt"
    with pytest.raises(TurnExecutionInDoubt):
        FusedTurnRuntime(
            store=SQLiteWorldStore(store.db_path),
            index=WorldSearchIndex(index.db_path, store=SQLiteWorldStore(store.db_path)),
            model_handler=model,
        ).run_turn(**TURN)
    assert calls == ["called"]


def test_cg003_durable_assistant_output_recovers_completion_without_model_reinvoke(
    tmp_path, monkeypatch
):
    store, index = world(tmp_path)
    calls = []

    def model(_snapshot):
        calls.append("called")
        return successful_directive("cg003-completion")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=model)

    def fail_complete(**_kwargs):
        raise RuntimeError("SYNTHETIC completion marker failure")

    monkeypatch.setattr(runtime.turn_executions, "complete", fail_complete)
    with pytest.raises(RuntimeError, match="completion marker failure"):
        runtime.run_turn(**TURN)

    reopened_store = SQLiteWorldStore(store.db_path)
    reopened_index = WorldSearchIndex(index.db_path, store=reopened_store)
    restarted = FusedTurnRuntime(
        store=reopened_store, index=reopened_index, model_handler=model
    )
    inspected = restarted.inspect_turn_execution(**TURN)
    assert inspected.recovery_disposition == "completed"
    assert inspected.assistant_ref is not None

    recovered = restarted.recover_turn_completion(
        **TURN,
        evidence="durable assistant observation proves user-visible completion",
    )
    assert recovered.recovery_disposition == "completed"
    assert recovered.assistant_ref == inspected.assistant_ref

    with pytest.raises(TurnAlreadyCompleted) as error:
        restarted.run_turn(**TURN)
    assert error.value.assistant_ref == inspected.assistant_ref
    assert calls == ["called"]


def test_cg003_conflicting_input_remains_fail_closed_during_recovery(tmp_path):
    store, index = world(tmp_path)

    def ambiguous(_snapshot):
        raise TimeoutError("submission unknown")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=ambiguous)
    with pytest.raises(TimeoutError):
        runtime.run_turn(**TURN)

    changed = {**TURN, "user_input": "DIFFERENT INPUT"}
    with pytest.raises(TurnInputConflict):
        runtime.inspect_turn_execution(**changed)
    with pytest.raises(TurnInputConflict):
        runtime.authorize_turn_retry(**changed, evidence="must not matter")


def test_cg003_background_attempt_schema_upgrade_preserves_fix002_semantics(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.sqlite")
    with sqlite3.connect(store.db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE background_model_attempts (
                attempt_id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                work_kind TEXT NOT NULL
                    CHECK(work_kind IN ('wake', 'periodic_review')),
                work_id TEXT NOT NULL,
                wake_reason TEXT NOT NULL,
                model_round_index INTEGER NOT NULL CHECK(model_round_index >= 0),
                admission_world_revision INTEGER NOT NULL CHECK(admission_world_revision >= 0),
                state TEXT NOT NULL
                    CHECK(state IN (
                        'admitted','dispatching','not_submitted',
                        'in_doubt','response_returned','metered'
                    )),
                admitted_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                provider TEXT,
                model TEXT,
                provider_request_id TEXT,
                response_fingerprint TEXT,
                meter_record_id TEXT,
                failure_kind TEXT,
                failure_detail TEXT,
                reconciliation_evidence TEXT,
                UNIQUE(subject_id, work_kind, work_id, model_round_index)
            );
            INSERT INTO background_model_attempts(
                attempt_id, subject_id, work_kind, work_id, wake_reason,
                model_round_index, admission_world_revision, state,
                admitted_at, updated_at
            ) VALUES (
                'legacy-wake-attempt', 'user_1', 'wake', 'wake-legacy',
                'watch_match', 0, 0, 'not_submitted',
                '2026-09-24T07:00:00Z', '2026-09-24T07:00:00Z'
            );
            """
        )

    attempts = BackgroundModelAttemptStore(store)
    legacy = attempts.get("legacy-wake-attempt")
    assert legacy is not None
    assert legacy.work_kind == "wake"
    assert legacy.state == "not_submitted"

    user_attempt = attempts.admit(
        subject_id="user_1",
        work_kind="user_turn",
        work_id="turnexec-synthetic",
        wake_reason="user_interaction",
        model_round_index=0,
        world_revision=0,
        admitted_at=NOW,
    )
    assert user_attempt.work_kind == "user_turn"
    assert user_attempt.state == "admitted"
