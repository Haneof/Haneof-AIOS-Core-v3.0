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
from aios_core.runtime.turn_execution import TURN_MODEL_ATTEMPT_PROTOCOL
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



def test_cg003_claim_to_attempt_crash_is_repeatably_recoverable(tmp_path, monkeypatch):
    store, index = world(tmp_path)
    provider_calls = []

    def model(_snapshot):
        provider_calls.append("called")
        return successful_directive("cg003-claim-attempt-recovery")

    first = FusedTurnRuntime(store=store, index=index, model_handler=model)

    def crash_before_initial_attempt(**_kwargs):
        raise RuntimeError("SYNTHETIC crash before initial attempt admission")

    monkeypatch.setattr(
        first.background_model_attempts,
        "admit",
        crash_before_initial_attempt,
    )
    with pytest.raises(RuntimeError, match="before initial attempt admission"):
        first.run_turn(**TURN)

    inspected = first.inspect_turn_execution(**TURN)
    assert inspected.recovery_disposition == "safe_to_retry"
    assert inspected.model_attempts == ()
    assert provider_calls == []

    reopened_store = SQLiteWorldStore(store.db_path)
    second = FusedTurnRuntime(
        store=reopened_store,
        index=WorldSearchIndex(index.db_path, store=reopened_store),
        model_handler=model,
    )
    authorized = second.authorize_turn_retry(
        **TURN,
        evidence="explicit pre-attempt protocol proves dispatch was impossible",
    )
    assert authorized.recovery_disposition == "retry_authorized"

    monkeypatch.setattr(
        second.background_model_attempts,
        "admit",
        crash_before_initial_attempt,
    )
    with pytest.raises(RuntimeError, match="before initial attempt admission"):
        second.run_turn(**TURN)

    reopened_store = SQLiteWorldStore(store.db_path)
    third = FusedTurnRuntime(
        store=reopened_store,
        index=WorldSearchIndex(index.db_path, store=reopened_store),
        model_handler=model,
    )
    inspected_again = third.inspect_turn_execution(**TURN)
    assert inspected_again.recovery_disposition == "safe_to_retry"
    assert inspected_again.model_attempts == ()
    assert inspected_again.retry_count == 1

    # The first authorization was consumed by the crashed retry claim. A second
    # ordinary run cannot reuse it; explicit authorization is one-shot.
    with pytest.raises(TurnExecutionInDoubt):
        third.run_turn(**TURN)

    third.authorize_turn_retry(
        **TURN,
        evidence="second pre-attempt crash still proves dispatch was impossible",
    )
    result = third.run_turn(**TURN)
    assert result.runtime.response == "SYNTHETIC recovered response"
    assert provider_calls == ["called"]

    final = third.inspect_turn_execution(**TURN)
    assert final.recovery_disposition == "completed"
    assert len(final.model_attempts) == 1
    expected_attempt_id = BackgroundModelAttemptStore.attempt_id_for(
        subject_id=third.subject_id,
        work_kind="user_turn",
        work_id=final.execution_id,
        model_round_index=0,
    )
    assert final.model_attempts[0].attempt_id == expected_attempt_id

    _, _, assistant_id = third.ingestor._turn_identity(
        TURN["session_id"], TURN["turn_index"]
    )
    with sqlite3.connect(store.db_path) as conn:
        assistant_rows = conn.execute(
            "SELECT COUNT(*) FROM object_revisions WHERE object_id=?",
            (assistant_id,),
        ).fetchone()[0]
        attempt_rows = conn.execute(
            """
            SELECT COUNT(*) FROM background_model_attempts
            WHERE subject_id=? AND work_kind='user_turn' AND work_id=?
              AND model_round_index=0
            """,
            (third.subject_id, final.execution_id),
        ).fetchone()[0]
    assert assistant_rows == 1
    assert attempt_rows == 1


def test_cg003_legacy_and_old_v1_zero_attempt_rows_remain_in_doubt(tmp_path):
    store, index = world(tmp_path)
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: successful_directive("must-not-run"),
    )
    occurred_iso = "2026-09-24T07:00:00Z"

    def insert_started(*, session_id, turn_index, protocol):
        digest = runtime.turn_executions._input_hash(
            user_input=TURN["user_input"],
            occurred_at=occurred_iso,
        )
        with sqlite3.connect(store.db_path) as conn:
            conn.execute(
                """
                INSERT INTO runtime_turn_executions(
                    subject_id, session_id, turn_index, input_hash, state,
                    attempt_protocol, retry_authorized, retry_count
                ) VALUES (?, ?, ?, ?, 'started', ?, 0, 0)
                """,
                (
                    runtime.subject_id,
                    session_id,
                    turn_index,
                    digest,
                    protocol,
                ),
            )

    insert_started(session_id="legacy-zero", turn_index=1, protocol=None)
    legacy_turn = {**TURN, "session_id": "legacy-zero"}
    legacy = runtime.inspect_turn_execution(**legacy_turn)
    assert legacy.recovery_disposition == "in_doubt"
    assert legacy.model_attempts == ()
    with pytest.raises(TurnExecutionInDoubt):
        runtime.authorize_turn_retry(
            **legacy_turn,
            evidence="legacy zero-attempt rows are not safe proof",
        )

    insert_started(
        session_id="old-v1-zero",
        turn_index=1,
        protocol=TURN_MODEL_ATTEMPT_PROTOCOL,
    )
    old_v1_turn = {**TURN, "session_id": "old-v1-zero"}
    old_v1 = runtime.inspect_turn_execution(**old_v1_turn)
    assert old_v1.recovery_disposition == "in_doubt"
    assert old_v1.model_attempts == ()
    with pytest.raises(TurnExecutionInDoubt):
        runtime.authorize_turn_retry(
            **old_v1_turn,
            evidence="old v1 zero-attempt rows remain fail-closed",
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
    recovered_again = restarted.recover_turn_completion(
        **TURN,
        evidence="repeated reconciliation is idempotent",
    )
    assert recovered_again.recovery_disposition == "completed"
    assert recovered_again.assistant_ref == inspected.assistant_ref

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
