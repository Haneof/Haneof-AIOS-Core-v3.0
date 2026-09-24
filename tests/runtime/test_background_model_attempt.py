from datetime import datetime, timezone

from aios_core.runtime.background_attempt import BackgroundModelAttemptStore
from aios_core.runtime.cognitive_runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
)
from aios_core.runtime.metering import ModelMeteringLedger
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 24, 6, 0, tzinfo=timezone.utc)


def test_background_attempt_reconciliation_keeps_same_identity_and_non_world_revision(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    attempts = BackgroundModelAttemptStore(store)
    ledger = ModelMeteringLedger(store)
    before = int(store.current_world_revision())

    admitted = attempts.admit(
        subject_id="user_1",
        work_kind="wake",
        work_id="wake_attempt_unit",
        wake_reason="watch_match",
        model_round_index=0,
        world_revision=before,
        admitted_at=NOW,
    )
    attempts.mark_dispatching(admitted.attempt_id, dispatched_at=NOW)
    in_doubt = attempts.mark_failure(
        admitted.attempt_id,
        failed_at=NOW,
        definitely_not_submitted=False,
        error=TimeoutError("possible submission"),
    )
    assert in_doubt.state == "in_doubt"
    assert in_doubt.recovery_disposition == "in_doubt"

    reconciled = attempts.reconcile_not_submitted(
        admitted.attempt_id,
        reconciled_at=NOW,
        evidence="provider gateway confirms no request was accepted",
    )
    assert reconciled.state == "not_submitted"
    retry = attempts.admit(
        subject_id="user_1",
        work_kind="wake",
        work_id="wake_attempt_unit",
        wake_reason="watch_match",
        model_round_index=0,
        world_revision=before,
        admitted_at=NOW,
    )
    assert retry.attempt_id == admitted.attempt_id
    attempts.mark_dispatching(retry.attempt_id, dispatched_at=NOW)

    directive = ModelDirective(
        silence=True,
        usage=ModelUsage(
            input_tokens=3,
            output_tokens=1,
            total_tokens=4,
            provider="provider",
            model="model",
            request_id="request-unit",
        ),
        provenance=ModelCallProvenance(
            provider="provider",
            model="model",
            request_id="request-unit",
        ),
    )
    returned = attempts.record_response(
        retry.attempt_id,
        returned_at=NOW,
        directive=directive,
    )
    assert returned.state == "response_returned"
    assert returned.provider_request_id == "request-unit"

    meter = ledger.record_model_call(
        subject_id="user_1",
        world_revision=before,
        recorded_at=NOW,
        execution_class="background",
        wake_id="wake_attempt_unit",
        wake_reason="watch_match",
        model_round_index=0,
        usage=directive.usage,
        provenance=directive.provenance,
        background_attempt_id=retry.attempt_id,
    )
    closed = attempts.get(retry.attempt_id)
    assert closed is not None
    assert closed.state == "metered"
    assert closed.meter_record_id == meter.record_id
    assert meter.background_attempt_id == retry.attempt_id
    assert int(store.current_world_revision()) == before

    reopened = SQLiteWorldStore(tmp_path / "world.db")
    restarted_attempts = BackgroundModelAttemptStore(reopened)
    durable = restarted_attempts.inspect(
        subject_id="user_1",
        work_kind="wake",
        work_id="wake_attempt_unit",
        model_round_index=0,
    )
    assert durable is not None
    assert durable.attempt_id == retry.attempt_id
    assert durable.state == "metered"
    assert durable.provider_request_id == "request-unit"
