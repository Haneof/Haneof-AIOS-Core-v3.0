"""IA-ADV-H: historical blocker regression (IA-BLK-001 transplant, IA-BLK-002
recursive duplicate JSON semantic keys)."""

from __future__ import annotations

import json

import pytest

from ia_helpers import (
    assert_rejected_without_mutation,
    capture_return,
    crash_wake,
    directive,
    emit_wake,
    stage,
    wake_ref,
    world,
)

from aios_core.runtime.background_attempt import (
    decode_model_directive,
    encode_model_directive,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from datetime import timedelta
from ia_helpers import NOW


def test_adv_h1_cross_work_transplant_rejected_pre_and_post_dispatch(tmp_path):
    """IA-BLK-001 shape: work A's exact response must never land on work B."""

    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal_a, attempt_a = crash_wake(runtime, key="h1-a")
    response_a = directive("provider-request-h1-a", response="WORK A EXACT RESPONSE")
    receipt_a = capture_return(runtime, attempt_a.attempt_id, response_a)

    # Work B: an unrelated dispatching/in_doubt work item.
    signal_b = emit_wake(runtime, key="h1-b")

    def no_response_b(_s):
        raise TimeoutError("work B provider never returned")

    from ia_helpers import bind_handler

    bind_handler(runtime, no_response_b)
    with pytest.raises(TimeoutError):
        runtime.run_wake(wake_ref=wake_ref(signal_b), now=NOW)
    attempt_b = runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id,
        work_kind="wake",
        work_id=signal_b.wake_id,
        model_round_index=0,
    )
    assert attempt_b is not None and attempt_b.state == "in_doubt"

    exc = assert_rejected_without_mutation(
        runtime,
        attempt_b,
        lambda: stage(
            runtime,
            work_kind="wake",
            work_id=signal_b.wake_id,
            round_index=0,
            d=response_a,
            authenticity_proof=receipt_a.authenticity_proof,
        ),
    )
    assert exc is not None

    # Work B's own durable provenance must not have inherited work A identity.
    attempt_b_after = runtime.background_model_attempts.get(attempt_b.attempt_id)
    assert attempt_b_after.provider is None
    assert attempt_b_after.response_fingerprint is None


def test_adv_h2_nested_duplicate_json_semantic_keys_fail_closed(tmp_path):
    """IA-BLK-002 shape: duplicate semantic keys must be rejected recursively."""

    base = encode_model_directive(
        directive("provider-request-h2", response="dup keys")
    )
    parsed = json.loads(base)

    variants = {}

    top = dict(parsed)
    top["response"] = "first"
    raw_top = json.dumps(top)[:-1] + ', "response": "second"}'
    variants["top-level"] = raw_top

    usage = dict(parsed)
    usage["usage"] = dict(parsed["usage"])
    usage["usage"]["total_tokens"] = 1
    raw_usage = json.dumps(usage)
    raw_usage = raw_usage.replace(
        '"total_tokens": 1', '"total_tokens": 1, "total_tokens": 9999', 1
    )
    variants["nested-usage"] = raw_usage

    prov = dict(parsed)
    prov["provenance"] = dict(parsed["provenance"])
    raw_prov = json.dumps(prov)
    raw_prov = raw_prov.replace(
        '"request_id": "provider-request-h2"',
        '"request_id": "provider-request-h2", "request_id": "evil-request"',
        1,
    )
    variants["nested-provenance"] = raw_prov

    call_obj = {
        "name": "act",
        "arguments": {"a": 1},
        "call_id": "c1",
    }
    calls = dict(parsed)
    calls["capability_calls"] = [call_obj]
    raw_call = json.dumps(calls)
    raw_call = raw_call.replace('"name": "act"', '"name": "act", "name": "evil"', 1)
    variants["capability-call"] = raw_call

    args_obj = {"a": 1}
    call_args = dict(parsed)
    call_args["capability_calls"] = [
        {"name": "act", "arguments": args_obj, "call_id": "c1"}
    ]
    raw_args = json.dumps(call_args)
    raw_args = raw_args.replace('"a": 1', '"a": 1, "a": 2', 1)
    variants["capability-arguments"] = raw_args

    nested_value = dict(parsed)
    nested_value["capability_calls"] = [
        {"name": "act", "arguments": {"v": {"k": 1}}, "call_id": "c1"}
    ]
    raw_nested = json.dumps(nested_value)
    raw_nested = raw_nested.replace('"k": 1', '"k": 1, "k": 2', 1)
    variants["nested-argument-value"] = raw_nested

    assert len(variants) == 6
    for label, raw in variants.items():
        try:
            decode_model_directive(raw)
        except ValueError:
            continue
        raise AssertionError(f"duplicate JSON keys accepted at: {label}")

    # And the staging surface must reject such payloads before any mutation.
    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="h2")
    exc = assert_rejected_without_mutation(
        runtime,
        attempt,
        lambda: runtime.stage_exact_background_response(
            work_kind="wake",
            work_id=signal.wake_id,
            model_round_index=0,
            provider="ia-trusted-provider",
            model="ia-trusted-model",
            provider_request_id="provider-request-h2",
            response_fingerprint="0" * 64,
            directive_payload=variants["top-level"],
            staged_at=NOW + timedelta(minutes=2),
            evidence="duplicate keys at staging",
            authenticity_proof="bgresponse_v1_" + "4" * 64,
        ),
    )
    assert exc is not None
