"""S3-ROUTE-B / CA4-B: post-binding non-submission is structurally dead."""

from datetime import datetime, timezone

import pytest

from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptBlocked,
    BackgroundModelAttemptStore,
    BackgroundModelExecutionInDoubt,
    BackgroundModelResponseConflict,
)
from aios_core.runtime.cognitive_runtime import ModelDispatchNotSubmitted
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)


def _admitted(tmp_path, key):
    store = SQLiteWorldStore(tmp_path / f"{key}.sqlite")
    attempts = BackgroundModelAttemptStore(store)
    attempt = attempts.admit(
        subject_id="user_1",
        work_kind="wake",
        work_id=f"wake-{key}",
        wake_reason="safety",
        model_round_index=0,
        world_revision=int(store.current_world_revision()),
        admitted_at=NOW,
    )
    return attempts, attempt


@pytest.mark.parametrize(
    "error",
    [
        ModelDispatchNotSubmitted("caller boolean/typed exception is not proof"),
        RuntimeError("arbitrary caller exception is not proof"),
    ],
)
def test_s3_route_b_post_binding_mark_failure_refuses_not_submitted(tmp_path, error):
    attempts, attempt = _admitted(tmp_path, "route-b-mark")
    attempts.mark_dispatching(
        attempt.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint="request-v1",
    )
    binding = attempts.outbound_request_binding(attempt.attempt_id)
    assert binding is not None

    with pytest.raises(BackgroundModelResponseConflict):
        attempts.mark_failure(
            attempt.attempt_id,
            failed_at=NOW,
            definitely_not_submitted=True,
            error=error,
        )
    after = attempts.get(attempt.attempt_id)
    assert after is not None
    assert after.state == "in_doubt"
    assert attempts.outbound_request_binding(attempt.attempt_id) == binding

    with pytest.raises(BackgroundModelExecutionInDoubt):
        attempts.admit(
            subject_id=attempt.subject_id,
            work_kind=attempt.work_kind,
            work_id=attempt.work_id,
            wake_reason=attempt.wake_reason,
            model_round_index=attempt.model_round_index,
            world_revision=0,
            admitted_at=NOW,
        )


def test_ca4_b_post_binding_reconcile_refused_no_second_request_identity(tmp_path):
    attempts, attempt = _admitted(tmp_path, "route-b-reconcile")
    attempts.mark_dispatching(
        attempt.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint="request-v1",
    )
    binding = attempts.outbound_request_binding(attempt.attempt_id)
    assert binding is not None

    with pytest.raises(BackgroundModelResponseConflict):
        attempts.reconcile_not_submitted(
            attempt.attempt_id,
            reconciled_at=NOW,
            evidence="operator assertion cannot erase dispatch truth",
        )
    after = attempts.get(attempt.attempt_id)
    assert after is not None
    assert after.state == "in_doubt"

    with pytest.raises((BackgroundModelExecutionInDoubt, BackgroundModelAttemptBlocked)):
        attempts.mark_dispatching(
            attempt.attempt_id,
            dispatched_at=NOW,
            outbound_request_fingerprint="request-v2",
        )
    assert attempts.outbound_request_binding(attempt.attempt_id) == binding


def test_ca4_a_true_pre_submission_retry_remains_legal(tmp_path):
    attempts, attempt = _admitted(tmp_path, "route-a-pre")
    failed = attempts.mark_failure(
        attempt.attempt_id,
        failed_at=NOW,
        definitely_not_submitted=True,
        error=RuntimeError("failed before any dispatch fact was durable"),
    )
    assert failed.state == "not_submitted"
    assert attempts.outbound_request_binding(attempt.attempt_id) is None

    retried = attempts.admit(
        subject_id=attempt.subject_id,
        work_kind=attempt.work_kind,
        work_id=attempt.work_id,
        wake_reason=attempt.wake_reason,
        model_round_index=attempt.model_round_index,
        world_revision=0,
        admitted_at=NOW,
    )
    assert retried.state == "admitted"
    attempts.mark_dispatching(
        retried.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint="first-real-request",
    )
    binding = attempts.outbound_request_binding(retried.attempt_id)
    assert binding is not None
    assert binding.outbound_request_fingerprint == "first-real-request"
