"""IA-ADV-G: anonymous/local handler boundary.

Local handlers keep ordinary synchronous execution but must never obtain
externally staged exact-response recovery authority, and no fallback path may
bypass proof verification.
"""

from __future__ import annotations

import pytest

from ia_helpers import (
    NOW,
    assert_rejected_without_mutation,
    bind_handler,
    crash_wake,
    directive,
    identityless_directive,
    emit_wake,
    fingerprint,
    stage,
    wake_ref,
    world,
)

from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from datetime import timedelta


def test_adv_g1_identityless_local_handler_runs_ordinarily_without_receipt(tmp_path):
    store, index, _db = world(tmp_path)
    local = identityless_directive("local anonymous answer")

    def handler(_snapshot):
        return local

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=handler)
    signal = emit_wake(runtime, key="g1")
    result = runtime.run_wake(wake_ref=wake_ref(signal), now=NOW)
    assert result is not None

    attempt = runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert attempt is not None and attempt.state == "response_returned"
    assert attempt.provider is None and attempt.provider_request_id is None
    receipt = runtime.background_model_attempts.response_authenticity_receipt(
        attempt.attempt_id
    )
    assert receipt is None, (
        "an identity-less local handler minted trusted exact-response authority"
    )
    assert runtime.background_model_attempts.staged_response(attempt.attempt_id) is None


def test_adv_g2_identityless_response_cannot_enter_external_exact_recovery(tmp_path):
    store, index, _db = world(tmp_path)
    local = identityless_directive("local anonymous answer")

    def handler(_snapshot):
        return local

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=handler)
    signal = emit_wake(runtime, key="g2")
    runtime.run_wake(wake_ref=wake_ref(signal), now=NOW)
    attempt = runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert attempt is not None

    # External staging of the identity-less bytes must fail closed.
    def call():
        return runtime.stage_exact_background_response(
            work_kind="wake",
            work_id=signal.wake_id,
            model_round_index=0,
            provider="None",
            model="None",
            provider_request_id="None",
            response_fingerprint=fingerprint(runtime, local),
            directive_payload=encode_model_directive(local),
            staged_at=NOW + timedelta(minutes=2),
            evidence="identity-less bytes with None-string identity",
            authenticity_proof="bgresponse_v1_" + "2" * 64,
        )

    exc = assert_rejected_without_mutation(runtime, attempt, call)
    assert exc is not None


def test_adv_g3_empty_identity_strings_cannot_stage(tmp_path):
    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="g3")

    def call():
        return runtime.stage_exact_background_response(
            work_kind="wake",
            work_id=signal.wake_id,
            model_round_index=0,
            provider="   ",
            model="   ",
            provider_request_id="   ",
            response_fingerprint="0" * 64,
            directive_payload='{"capability_calls": [], "response": "x", '
            '"silence": true, "usage": null, "provenance": null}',
            staged_at=NOW + timedelta(minutes=2),
            evidence="empty identity",
            authenticity_proof=None,
        )

    exc = assert_rejected_without_mutation(runtime, attempt, call)
    assert exc is not None


def test_adv_g4_local_handler_with_fabricated_identity_still_requires_trusted_return(tmp_path):
    """Even identity-carrying bytes cannot stage without a genuine receipt."""

    store, index, _db = world(tmp_path)
    fabricated = directive("fabricated-request-id", response="fabricated provider bytes")

    def handler(_snapshot):
        return fabricated

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=handler)
    signal = emit_wake(runtime, key="g4")
    # Ordinary in-process run: the return boundary IS the trust root and records
    # provenance; this is the documented in-process trust assumption.  What must
    # fail is the external journal path without that return:
    runtime2 = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)

    def call():
        return stage(
            runtime2,
            work_kind="wake",
            work_id="unrelated-work-g4",
            round_index=0,
            d=fabricated,
            authenticity_proof="bgresponse_v1_" + "3" * 64,
        )

    with pytest.raises(Exception):
        call()
