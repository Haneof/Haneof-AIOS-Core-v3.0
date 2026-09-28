"""IA-ADV-B: cross-identity proof/receipt replay must fail before any mutation."""

from __future__ import annotations

import pytest

from ia_helpers import (
    assert_rejected_without_mutation,
    capture_return,
    crash_wake,
    crash_user_turn,
    directive,
    emit_wake,
    stage,
    wake_ref,
    world,
)

from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.contracts.enums import WakeSource
from aios_core.wake import WakeSignalRequest
from datetime import timedelta


def _second_wake(runtime, key: str):
    return runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id=f"ia-adv.{key}",
            observed_at=NOW_LOCAL(),
            dedupe_key=f"ia-adv:{runtime.subject_id}:{key}",
        )
    )


def NOW_LOCAL():
    from ia_helpers import NOW

    return NOW


def test_adv_b1_proof_replay_across_attempts_same_work_different_round(tmp_path):
    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt0 = crash_wake(runtime, key="b1")
    genuine = directive("provider-request-b1-round0", response="round0 bytes")
    receipt0 = capture_return(runtime, attempt0.attempt_id, genuine)

    # A second round of the same work is a distinct durable attempt.
    attempt1 = runtime.background_model_attempts.admit(
        subject_id=runtime.subject_id,
        work_kind="wake",
        work_id=signal.wake_id,
        wake_reason="ia-adv.b1-round1",
        model_round_index=1,
        world_revision=int(store.current_world_revision()),
        admitted_at=NOW_LOCAL() + timedelta(minutes=1),
    )
    runtime.background_model_attempts.mark_dispatching(
        attempt1.attempt_id,
        dispatched_at=NOW_LOCAL() + timedelta(minutes=2),
        outbound_request_fingerprint="round1-outbound-fp",
    )
    round1_directive = directive("provider-request-b1-round1", response="round1 bytes")
    exc = assert_rejected_without_mutation(
        runtime,
        attempt1,
        lambda: stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=1,
            d=round1_directive,
            authenticity_proof=receipt0.authenticity_proof,
        ),
    )
    assert exc is not None


def test_adv_b2_proof_replay_across_work_id(tmp_path):
    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    _signal_a, attempt_a = crash_wake(runtime, key="b2-a")
    genuine_a = directive("provider-request-b2-a", response="work A bytes")
    receipt_a = capture_return(runtime, attempt_a.attempt_id, genuine_a)

    signal_b = _second_wake(runtime, "b2-b")

    def no_response_b(_s):
        raise TimeoutError("work B provider never returned")

    from ia_helpers import bind_handler

    bind_handler(runtime, no_response_b)
    with pytest.raises(TimeoutError):
        runtime.run_wake(wake_ref=wake_ref(signal_b), now=NOW_LOCAL())
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
            d=genuine_a,
            authenticity_proof=receipt_a.authenticity_proof,
        ),
    )
    assert exc is not None


def test_adv_b3_proof_replay_across_work_kind(tmp_path):
    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    _signal, attempt_wake = crash_wake(runtime, key="b3")
    genuine = directive("provider-request-b3", response="wake bytes")
    receipt = capture_return(runtime, attempt_wake.attempt_id, genuine)

    turn, execution_id, attempt_turn = crash_user_turn(runtime, key="b3-turn")
    exc = assert_rejected_without_mutation(
        runtime,
        attempt_turn,
        lambda: stage(
            runtime,
            work_kind="user_turn",
            work_id=execution_id,
            round_index=0,
            d=genuine,
            authenticity_proof=receipt.authenticity_proof,
        ),
    )
    assert exc is not None


def test_adv_b4_proof_replay_across_subject(tmp_path):
    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    _signal, attempt_a = crash_wake(runtime, key="b4")
    genuine = directive("provider-request-b4", response="subject A bytes")
    receipt_a = capture_return(runtime, attempt_a.attempt_id, genuine)

    runtime_b = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _s: None,
        subject_id="user_2",
    )
    signal_b = emit_wake(runtime_b, key="b4-b")

    def no_response_b(_s):
        raise TimeoutError("subject B provider never returned")

    from ia_helpers import bind_handler

    bind_handler(runtime_b, no_response_b)
    with pytest.raises(TimeoutError):
        runtime_b.run_wake(wake_ref=wake_ref(signal_b), now=NOW_LOCAL())
    attempt_b = runtime_b.background_model_attempts.inspect(
        subject_id=runtime_b.subject_id,
        work_kind="wake",
        work_id=signal_b.wake_id,
        model_round_index=0,
    )
    assert attempt_b is not None

    exc = assert_rejected_without_mutation(
        runtime_b,
        attempt_b,
        lambda: stage(
            runtime_b,
            work_kind="wake",
            work_id=signal_b.wake_id,
            round_index=0,
            d=genuine,
            authenticity_proof=receipt_a.authenticity_proof,
        ),
    )
    assert exc is not None


def test_adv_b5_cross_work_full_journal_transplant_rejected(tmp_path):
    """Historical IA-BLK-001 shape: work A's complete response journal onto work B."""

    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    _signal_a, attempt_a = crash_wake(runtime, key="b5-a")
    genuine_a = directive("provider-request-b5-a", response="transplanted bytes")
    receipt_a = capture_return(runtime, attempt_a.attempt_id, genuine_a)

    signal_b = _second_wake(runtime, "b5-b")

    def no_response_b(_s):
        raise TimeoutError("work B provider never returned")

    from ia_helpers import bind_handler

    bind_handler(runtime, no_response_b)
    with pytest.raises(TimeoutError):
        runtime.run_wake(wake_ref=wake_ref(signal_b), now=NOW_LOCAL())
    attempt_b = runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id,
        work_kind="wake",
        work_id=signal_b.wake_id,
        model_round_index=0,
    )

    def call():
        return runtime.stage_exact_background_response(
            work_kind="wake",
            work_id=signal_b.wake_id,
            model_round_index=0,
            provider=genuine_a.provenance.provider,
            model=genuine_a.provenance.model,
            provider_request_id=genuine_a.provenance.request_id,
            response_fingerprint=runtime.background_model_attempts._response_fingerprint(
                genuine_a
            ),
            directive_payload=encode_model_directive(genuine_a),
            staged_at=NOW_LOCAL() + timedelta(minutes=2),
            evidence="copied work A journal onto work B",
            authenticity_proof=receipt_a.authenticity_proof,
        )

    exc = assert_rejected_without_mutation(runtime, attempt_b, call)
    assert exc is not None


def test_adv_b6_proof_replay_across_provider_model_request_id(tmp_path):
    """Same payload bytes but different claimed provider identity must not stage."""

    store, index, _db = world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = crash_wake(runtime, key="b6")
    genuine = directive("provider-request-b6", response="identity bound")
    receipt = capture_return(runtime, attempt.attempt_id, genuine)

    imposter = directive(
        "provider-request-b6",
        response="identity bound",
        provider="imposter-provider",
        model="imposter-model",
    )
    exc = assert_rejected_without_mutation(
        runtime,
        attempt,
        lambda: stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            d=imposter,
            authenticity_proof=receipt.authenticity_proof,
        ),
    )
    assert exc is not None
