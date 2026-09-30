from datetime import datetime, timedelta, timezone

import pytest

from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptStore,
    BackgroundModelResponseConflict,
    encode_model_directive,
)
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
    # CORE-BACKGROUND-LATE-TRUSTED-RETURN-001: `not_submitted` is only reachable
    # from a pre-dispatch Core-owned state. The attempt is reconciled here, while
    # it is still `admitted` and provably no outbound request was published.
    assert admitted.state == "admitted"
    assert attempts.outbound_request_binding(admitted.attempt_id) is None
    reconciled = attempts.reconcile_not_submitted(
        admitted.attempt_id,
        reconciled_at=NOW,
        evidence="admission stopped before any outbound request was published",
    )
    assert reconciled.state == "not_submitted"

    # The post-dispatch shape that this task retires: once the provider boundary
    # is crossed the same call must be mechanically refused, and the attempt must
    # stay fail-closed in in_doubt rather than becoming retryable.
    crossed = attempts.admit(
        subject_id="user_1",
        work_kind="wake",
        work_id="wake_attempt_crossed",
        wake_reason="watch_match",
        model_round_index=0,
        world_revision=before,
        admitted_at=NOW,
    )
    attempts.mark_dispatching(
        crossed.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint="unit-outbound-request-crossed",
    )
    in_doubt = attempts.mark_failure(
        crossed.attempt_id,
        failed_at=NOW,
        definitely_not_submitted=False,
        error=TimeoutError("possible submission"),
    )
    assert in_doubt.state == "in_doubt"
    assert in_doubt.recovery_disposition == "in_doubt"
    with pytest.raises(BackgroundModelResponseConflict):
        attempts.reconcile_not_submitted(
            crossed.attempt_id,
            reconciled_at=NOW,
            evidence="provider gateway confirms no request was accepted",
        )
    assert attempts.get(crossed.attempt_id).state == "in_doubt"
    assert attempts.get(crossed.attempt_id).reconciliation_evidence is None

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
    attempts.mark_dispatching(
        retry.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint="unit-outbound-request-retry",
    )

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
    receipt = attempts._capture_trusted_response_return(
        retry.attempt_id,
        captured_at=NOW,
        directive=directive,
    )
    assert receipt.attempt_id == retry.attempt_id
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


def _trusted_attempt(
    attempts: BackgroundModelAttemptStore,
    *,
    subject_id: str,
    work_kind: str,
    work_id: str,
    round_index: int,
    request_id: str,
):
    attempt = attempts.admit(
        subject_id=subject_id,
        work_kind=work_kind,
        work_id=work_id,
        wake_reason="trusted-return-unit",
        model_round_index=round_index,
        world_revision=0,
        admitted_at=NOW,
    )
    attempts.mark_dispatching(
        attempt.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint=(
            f"outbound:{subject_id}:{work_kind}:{work_id}:{round_index}"
        ),
    )
    directive = ModelDirective(
        response=f"response for {request_id}",
        usage=ModelUsage(
            input_tokens=2,
            output_tokens=2,
            total_tokens=4,
            provider="provider",
            model="model",
            request_id=request_id,
        ),
        provenance=ModelCallProvenance(
            provider="provider",
            model="model",
            request_id=request_id,
        ),
    )
    receipt = attempts._capture_trusted_response_return(
        attempt.attempt_id,
        captured_at=NOW + timedelta(seconds=1),
        directive=directive,
    )
    return attempt, directive, receipt


@pytest.mark.parametrize(
    "target_identity",
    (
        pytest.param(
            ("subject-a", "wake", "work-b", 0), id="cross-work-and-attempt"
        ),
        pytest.param(
            ("subject-a", "periodic_review", "work-a", 0), id="cross-work-kind"
        ),
        pytest.param(("subject-b", "wake", "work-a", 0), id="cross-subject"),
        pytest.param(("subject-a", "wake", "work-a", 1), id="cross-round"),
    ),
)
def test_trusted_receipt_proof_cannot_replay_across_bound_identity(
    tmp_path, target_identity
):
    store = SQLiteWorldStore(tmp_path / "world.db")
    attempts = BackgroundModelAttemptStore(store)
    _source, _source_directive, source_receipt = _trusted_attempt(
        attempts,
        subject_id="subject-a",
        work_kind="wake",
        work_id="work-a",
        round_index=0,
        request_id="source-request",
    )
    target, target_directive, _target_receipt = _trusted_attempt(
        attempts,
        subject_id=target_identity[0],
        work_kind=target_identity[1],
        work_id=target_identity[2],
        round_index=target_identity[3],
        request_id="target-request",
    )
    payload = encode_model_directive(target_directive)

    with pytest.raises(BackgroundModelResponseConflict, match="proof is invalid"):
        attempts.stage_exact_response(
            target.attempt_id,
            staged_at=NOW + timedelta(seconds=2),
            provider="provider",
            model="model",
            provider_request_id="target-request",
            response_fingerprint=attempts._response_fingerprint(target_directive),
            directive_payload=payload,
            authenticity_proof=source_receipt.authenticity_proof,
            evidence="attempted cross-identity receipt replay",
        )

    unchanged = attempts.get(target.attempt_id)
    assert unchanged is not None
    assert unchanged.state == "dispatching"
    assert unchanged.provider is None
    assert unchanged.model is None
    assert unchanged.provider_request_id is None
    assert unchanged.response_fingerprint is None
    assert attempts.staged_response(target.attempt_id) is None


def test_metadata_only_reconciliation_cannot_bypass_authenticity(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    attempts = BackgroundModelAttemptStore(store)
    attempt = attempts.admit(
        subject_id="subject-a",
        work_kind="wake",
        work_id="metadata-only",
        wake_reason="trusted-return-unit",
        model_round_index=0,
        world_revision=0,
        admitted_at=NOW,
    )
    attempts.mark_dispatching(
        attempt.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint="metadata-only-outbound",
    )

    with pytest.raises(BackgroundModelResponseConflict, match="metadata-only"):
        attempts.reconcile_response(
            attempt.attempt_id,
            reconciled_at=NOW + timedelta(seconds=1),
            provider="provider",
            model="model",
            provider_request_id="caller-request",
            response_fingerprint="caller-computable-fingerprint",
            evidence="caller-controlled evidence",
        )

    unchanged = attempts.get(attempt.attempt_id)
    assert unchanged is not None
    assert unchanged.state == "dispatching"
    assert unchanged.provider is None
    assert unchanged.response_fingerprint is None
