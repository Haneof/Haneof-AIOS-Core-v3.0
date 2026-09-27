"""IA-ADV-C: same-attempt stale replay, duplicate returns, retry races."""

from __future__ import annotations

import pytest

from ia_helpers import (
    IAProcessDeath,
    NOW,
    assert_rejected_without_mutation,
    capture_return,
    crash_wake,
    directive,
    effect_snapshot,
    stage,
    world,
)

from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptBlocked,
    BackgroundModelResponseConflict,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from datetime import timedelta


def test_adv_c1_second_trusted_return_with_different_payload_conflicts_and_keeps_first(tmp_path):
    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="c1")
    first = directive("provider-request-c1", response="first payload")
    second = directive("provider-request-c1", response="second payload")
    capture_return(runtime, attempt.attempt_id, first)

    before = effect_snapshot(runtime, attempt)
    with pytest.raises(BackgroundModelResponseConflict):
        capture_return(runtime, attempt.attempt_id, second)
    after = effect_snapshot(runtime, attempt)
    assert after == before, "a conflicting second provider return mutated durable state"

    receipt = runtime.background_model_attempts.response_authenticity_receipt(
        attempt.attempt_id
    )
    from ia_helpers import fingerprint, payload_sha
    from aios_core.runtime.background_attempt import encode_model_directive

    assert receipt.payload_sha256 == payload_sha(encode_model_directive(first))
    assert receipt.response_fingerprint == fingerprint(runtime, first)


def test_adv_c2_duplicate_stage_with_second_payload_and_first_proof_rejected(tmp_path):
    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="c2")
    first = directive("provider-request-c2", response="staged first")
    second = directive("provider-request-c2", response="staged second")
    receipt = capture_return(runtime, attempt.attempt_id, first)
    stage(
        runtime,
        work_kind="wake",
        work_id=signal.wake_id,
        round_index=0,
        d=first,
        authenticity_proof=receipt.authenticity_proof,
    )
    before = effect_snapshot(runtime, attempt)
    with pytest.raises((BackgroundModelResponseConflict, ValueError)):
        stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            d=second,
            authenticity_proof=receipt.authenticity_proof,
        )
    after = effect_snapshot(runtime, attempt)
    assert after == before, "duplicate staging with different bytes mutated durable state"
    staged = runtime.background_model_attempts.staged_response(attempt.attempt_id)
    assert staged is not None
    from aios_core.runtime.background_attempt import encode_model_directive

    assert staged.directive_payload == encode_model_directive(first)


def test_adv_c3_not_submitted_reconciliation_blocked_after_trusted_receipt(tmp_path):
    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="c3")
    genuine = directive("provider-request-c3", response="authenticated")
    capture_return(runtime, attempt.attempt_id, genuine)

    exc = assert_rejected_without_mutation(
        runtime,
        attempt,
        lambda: runtime.background_model_attempts.reconcile_not_submitted(
            attempt.attempt_id,
            reconciled_at=NOW + timedelta(minutes=3),
            evidence="attacker claims never submitted",
        ),
    )
    assert exc is not None

    exc = assert_rejected_without_mutation(
        runtime,
        attempt,
        lambda: runtime.background_model_attempts.mark_failure(
            attempt.attempt_id,
            failed_at=NOW + timedelta(minutes=4),
            definitely_not_submitted=True,
            error=RuntimeError("attacker claims never submitted"),
        ),
    )
    assert exc is not None


def test_adv_c4_staging_after_not_submitted_retry_authorization_rejected(tmp_path):
    """A not_submitted attempt without receipt cannot be externally recovered."""

    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="c4")
    reconciled = runtime.background_model_attempts.reconcile_not_submitted(
        attempt.attempt_id,
        reconciled_at=NOW + timedelta(minutes=1),
        evidence="provider definitely never saw the request",
    )
    assert reconciled.state == "not_submitted"
    forged = directive("provider-request-c4", response="forged after retry auth")
    exc = assert_rejected_without_mutation(
        runtime,
        reconciled,
        lambda: stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            d=forged,
            authenticity_proof="bgresponse_v1_" + "0" * 64,
        ),
    )
    assert exc is not None


def test_adv_c5_repeated_identical_provider_return_is_idempotent(tmp_path):
    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="c5")
    genuine = directive("provider-request-c5", response="idempotent bytes")
    receipt1 = capture_return(runtime, attempt.attempt_id, genuine)
    receipt2 = capture_return(runtime, attempt.attempt_id, genuine)
    assert receipt1 == receipt2, "identical repeated provider return changed the receipt"


def test_adv_c6_restaging_identical_after_completion_changes_nothing(tmp_path):
    from ia_helpers import bind_handler, emit_wake, wake_ref

    store, index, _db = world(tmp_path)
    exact = directive("provider-request-c6", response="completed bytes")

    def handler(_snapshot):
        return exact

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=handler)
    signal = emit_wake(runtime, key="c6")
    attempt = runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert attempt is not None

    def die_before_recording(snapshot, d):
        # The trusted authenticator already minted the receipt (production
        # ordering); death here leaves provenance/metering/effects untouched.
        assert runtime.background_model_attempts.response_authenticity_receipt(
            snapshot.model_attempt_id
        ) is not None
        raise IAProcessDeath("ia crash after receipt, before provenance")

    runtime.cognitive_runtime.model_response_recorder = die_before_recording
    with pytest.raises(IAProcessDeath, match="ia crash after receipt"):
        runtime.run_wake(wake_ref=wake_ref(signal), now=NOW)

    attempt = runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    receipt = runtime.background_model_attempts.response_authenticity_receipt(
        attempt.attempt_id
    )
    assert receipt is not None
    stage(
        runtime,
        work_kind="wake",
        work_id=signal.wake_id,
        round_index=0,
        d=exact,
        authenticity_proof=receipt.authenticity_proof,
    )
    before = effect_snapshot(runtime, attempt)
    stage(
        runtime,
        work_kind="wake",
        work_id=signal.wake_id,
        round_index=0,
        d=exact,
        authenticity_proof=receipt.authenticity_proof,
    )
    after = effect_snapshot(runtime, attempt)
    assert after == before, "identical re-staging mutated durable state"
