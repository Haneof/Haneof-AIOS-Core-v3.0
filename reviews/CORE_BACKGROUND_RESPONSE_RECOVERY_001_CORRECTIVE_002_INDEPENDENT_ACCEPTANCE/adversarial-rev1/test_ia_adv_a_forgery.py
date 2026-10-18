"""IA-ADV-A: proof forgeability through the public staging/recovery surface.

The external caller holds: relay id, payload bytes, fingerprints, payload
hashes, evidence strings, and any receipts copied out of the public receipt
reader.  None of these, without a genuine trusted-return receipt bound to the
exact bytes, may produce a staged/recovered trusted exact response.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import timedelta

from ia_helpers import (
    NOW,
    assert_rejected_without_mutation,
    capture_return,
    crash_wake,
    directive,
    fingerprint,
    forged_tasks,
    payload_sha,
    seed_watch_anchor,
    stage,
    watch_call,
    world,
)

from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.turn_runtime import FusedTurnRuntime


def _forged_proof() -> str:
    return "bgresponse_v1_" + hmac.new(b"not-the-store-key", b"ia", hashlib.sha256).hexdigest()


def test_adv_a1_forged_hmac_proof_rejected_without_mutation(tmp_path):
    store, index, _db = world(tmp_path)
    anchor = seed_watch_anchor(store)
    index.catch_up()
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="a1")
    binding = runtime.background_model_attempts.outbound_request_binding(attempt.attempt_id)
    forged = directive(
        binding.relay_id,
        capability_calls=(watch_call(anchor, title="FORGED a1"),),
    )
    assert_rejected_without_mutation(
        runtime,
        attempt,
        lambda: stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            d=forged,
            authenticity_proof=_forged_proof(),
        ),
    )
    assert forged_tasks(store, title="FORGED a1") == []


def test_adv_a2_corrective001_complete_bundle_plus_forged_proof_rejected(tmp_path):
    """The complete historical attacker bundle + any caller-made proof string."""

    store, index, _db = world(tmp_path)
    anchor = seed_watch_anchor(store)
    index.catch_up()
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="a2")
    binding = runtime.background_model_attempts.outbound_request_binding(attempt.attempt_id)
    forged = directive(
        binding.relay_id,  # relay echo
        capability_calls=(watch_call(anchor, title="FORGED a2"),),
    )
    payload = encode_model_directive(forged)
    # The caller recomputes every caller-computable artifact self-consistently.
    assert payload_sha(payload) == hashlib.sha256(payload.encode()).hexdigest()
    assert fingerprint(runtime, forged) == fingerprint(runtime, forged)
    assert_rejected_without_mutation(
        runtime,
        attempt,
        lambda: stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            d=forged,
            authenticity_proof=_forged_proof(),
        ),
    )
    assert forged_tasks(store, title="FORGED a2") == []


def test_adv_a3_real_receipt_proof_with_substituted_payload_rejected(tmp_path):
    """A genuine proof copied out of the receipt reader cannot bless new bytes."""

    store, index, _db = world(tmp_path)
    anchor = seed_watch_anchor(store)
    index.catch_up()
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="a3")
    genuine = directive("provider-request-a3", response="genuine bytes")
    receipt = capture_return(runtime, attempt.attempt_id, genuine)
    substituted = directive(
        "provider-request-a3",
        capability_calls=(watch_call(anchor, title="SUBSTITUTED a3"),),
    )
    assert_rejected_without_mutation(
        runtime,
        attempt,
        lambda: stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            d=substituted,
            authenticity_proof=receipt.authenticity_proof,
        ),
    )
    assert forged_tasks(store, title="SUBSTITUTED a3") == []


def test_adv_a4_byte_identical_payload_wrong_claimed_fingerprint_rejected(tmp_path):
    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="a4")
    genuine = directive("provider-request-a4", response="exact bytes")
    receipt = capture_return(runtime, attempt.attempt_id, genuine)
    payload = encode_model_directive(genuine)

    def call():
        return runtime.stage_exact_background_response(
            work_kind="wake",
            work_id=signal.wake_id,
            model_round_index=0,
            provider=genuine.provenance.provider,
            model=genuine.provenance.model,
            provider_request_id=genuine.provenance.request_id,
            response_fingerprint="0" * 64,  # mismatched claimed fingerprint
            directive_payload=payload,  # byte-identical genuine payload
            staged_at=NOW + timedelta(minutes=2),
            evidence="claimed fingerprint mismatch",
            authenticity_proof=receipt.authenticity_proof,
        )

    assert_rejected_without_mutation(runtime, attempt, call)


def test_adv_a5_semantically_equal_byte_different_payload_rejected(tmp_path):
    """Re-encoded (non-canonical) JSON with the same semantics must not stage."""

    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="a5")
    genuine = directive("provider-request-a5", response="canonical")
    receipt = capture_return(runtime, attempt.attempt_id, genuine)
    canonical = encode_model_directive(genuine)
    decoded = json.loads(canonical)
    reserialized = json.dumps(decoded, indent=2, sort_keys=False)  # same semantics
    assert reserialized != canonical

    def call():
        return runtime.stage_exact_background_response(
            work_kind="wake",
            work_id=signal.wake_id,
            model_round_index=0,
            provider=genuine.provenance.provider,
            model=genuine.provenance.model,
            provider_request_id=genuine.provenance.request_id,
            response_fingerprint=fingerprint(runtime, genuine),
            directive_payload=reserialized,
            staged_at=NOW + timedelta(minutes=2),
            evidence="byte-different semantic twin",
            authenticity_proof=receipt.authenticity_proof,
        )

    assert_rejected_without_mutation(runtime, attempt, call)


def test_adv_a6_nested_usage_substitution_rejected(tmp_path):
    """One altered nested usage token, fingerprint recomputed, must not stage."""

    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="a6")
    genuine = directive("provider-request-a6", response="usage bind")
    receipt = capture_return(runtime, attempt.attempt_id, genuine)
    payload = encode_model_directive(genuine)
    tampered = json.loads(payload)
    tampered["usage"]["total_tokens"] = 999999  # nested substitution
    tampered_payload = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
    from aios_core.runtime.background_attempt import decode_model_directive

    tampered_directive = decode_model_directive(tampered_payload)

    def call():
        return runtime.stage_exact_background_response(
            work_kind="wake",
            work_id=signal.wake_id,
            model_round_index=0,
            provider=genuine.provenance.provider,
            model=genuine.provenance.model,
            provider_request_id=genuine.provenance.request_id,
            response_fingerprint=fingerprint(runtime, tampered_directive),
            directive_payload=tampered_payload,
            staged_at=NOW + timedelta(minutes=2),
            evidence="nested substitution with recomputed fingerprint",
            authenticity_proof=receipt.authenticity_proof,
        )

    assert_rejected_without_mutation(runtime, attempt, call)


def test_adv_a7_silence_semantics_substitution_rejected(tmp_path):
    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="a7")
    genuine = directive("provider-request-a7", response="I will answer")
    receipt = capture_return(runtime, attempt.attempt_id, genuine)
    silenced = directive("provider-request-a7", silence=True)

    def call():
        return stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            d=silenced,
            authenticity_proof=receipt.authenticity_proof,
        )

    assert_rejected_without_mutation(runtime, attempt, call)


def test_adv_a8_no_proof_relay_echo_only_rejected(tmp_path):
    """Historical Corrective-001 shape: complete self-consistent bundle, no proof."""

    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="a8")
    binding = runtime.background_model_attempts.outbound_request_binding(attempt.attempt_id)
    forged = directive(binding.relay_id, response="forged via relay echo")
    exc = assert_rejected_without_mutation(
        runtime,
        attempt,
        lambda: stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            d=forged,
            authenticity_proof=None,
        ),
    )
    assert exc is not None
