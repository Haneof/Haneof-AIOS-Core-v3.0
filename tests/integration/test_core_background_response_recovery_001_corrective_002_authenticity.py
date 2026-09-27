"""CORRECTIVE-002 red-first exact-response authenticity blocker probes.

These probes are intentionally frozen before the corrective implementation.  They
exercise the failed corrective-001 exact candidate at PR #219 head a1c6e74d.  The
candidate's relay id, directive payload, provider metadata, payload SHA/fingerprint,
and caller-written evidence are all caller-visible or caller-computable.  Together
they are the candidate's complete claimed recovery proof bundle; none authenticates
bytes produced by the trusted provider/relay return path.

The invariant under test is implementation-shape neutral: externally staged bytes
must be rejected before staging, attempt provenance mutation, metering, capability
execution, assistant output, or any other World revision unless trusted durable
authenticity evidence binds those exact bytes to that exact request/attempt.

For proof-replay probes, ``evidence`` carries a serialized copy of attempt A's
complete pre-fix proof bundle.  It is deliberately *not* treated as authority.  A
correct implementation may expose a different receipt API; calling the old staging
surface without that required proof must fail closed.  The pre-fix candidate instead
accepts these calls, which is the RED being frozen here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

import pytest

from aios_core.contracts.enums import ObjectType, SourceClass, WakeSource
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import ModelCallProvenance, ModelDirective, ModelUsage
from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import WakeSignalRequest


NOW = datetime(2026, 9, 27, 8, 0, tzinfo=timezone.utc)
PROVIDER = "relay-provider"
MODEL = "relay-model"


class _SimulatedProcessDeath(BaseException):
    """A process death that escapes CognitiveRuntime's ``except Exception`` path."""


@dataclass(frozen=True)
class _PreFixProofBundle:
    """Every authenticity-like artifact corrective-001 can preserve or validate."""

    attempt_id: str
    subject_id: str
    work_kind: str
    work_id: str
    model_round_index: int
    relay_id: str
    outbound_request_fingerprint: str
    provider: str
    model: str
    request_id: str
    directive_payload: str
    response_fingerprint: str
    payload_sha256: str

    def as_evidence(self) -> str:
        return "copied corrective-001 proof bundle: " + json.dumps(
            self.__dict__, sort_keys=True, separators=(",", ":")
        )


def _world(tmp_path, name: str = "world.db"):
    db = tmp_path / name
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index, db


def _wake_ref(signal) -> ObjectRef:
    return ObjectRef(object_id=signal.wake_id, revision=signal.revision)


def _bind_handler(runtime: FusedTurnRuntime, handler: Callable) -> None:
    runtime.model_handler = handler
    runtime.cognitive_runtime.model_handler = handler


def _directive(
    request_id: str,
    *,
    response: str | None = None,
    silence: bool = False,
    capability_calls=(),
    provider: str = PROVIDER,
    model: str = MODEL,
) -> ModelDirective:
    return ModelDirective(
        response=response,
        silence=silence,
        capability_calls=tuple(capability_calls),
        usage=ModelUsage(
            input_tokens=7,
            output_tokens=3,
            total_tokens=10,
            provider=provider,
            model=model,
            request_id=request_id,
        ),
        provenance=ModelCallProvenance(
            provider=provider,
            model=model,
            request_id=request_id,
        ),
    )


def _emit_wake(runtime: FusedTurnRuntime, *, key: str):
    return runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id=f"cbrr-auth.{key}",
            observed_at=NOW,
            dedupe_key=f"cbrr-auth:{runtime.subject_id}:{key}",
        )
    )


def _crash_wake(runtime: FusedTurnRuntime, *, key: str):
    calls: list[int] = []

    def no_response(snapshot):
        calls.append(snapshot.round_index)
        raise TimeoutError("provider returned no response before the process died")

    _bind_handler(runtime, no_response)
    signal = _emit_wake(runtime, key=key)
    with pytest.raises(TimeoutError, match="returned no response"):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)
    attempt = runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert attempt is not None
    assert attempt.state == "in_doubt"
    assert calls == [0]
    return signal, attempt


def _crash_user_turn(runtime: FusedTurnRuntime, *, key: str):
    calls: list[int] = []

    def no_response(snapshot):
        calls.append(snapshot.round_index)
        raise TimeoutError("provider returned no response before the process died")

    _bind_handler(runtime, no_response)
    turn = {
        "session_id": f"cbrr-auth-{key}",
        "turn_index": 1,
        "user_input": f"SYNTHETIC authenticity probe {key}",
        "occurred_at": NOW,
    }
    with pytest.raises(TimeoutError, match="returned no response"):
        runtime.run_turn(**turn)
    inspection = runtime.inspect_turn_execution(**turn)
    assert len(inspection.model_attempts) == 1
    attempt = inspection.model_attempts[0]
    assert attempt.state == "in_doubt"
    assert calls == [0]
    return turn, inspection.execution_id, attempt


def _binding(runtime: FusedTurnRuntime, attempt):
    binding = runtime.background_model_attempts.outbound_request_binding(
        attempt.attempt_id
    )
    assert binding is not None
    assert binding.attempt_id == attempt.attempt_id
    return binding


def _fingerprint(runtime: FusedTurnRuntime, directive: ModelDirective) -> str:
    return runtime.background_model_attempts._response_fingerprint(directive)


def _bundle(
    runtime: FusedTurnRuntime,
    attempt,
    directive: ModelDirective,
) -> _PreFixProofBundle:
    binding = _binding(runtime, attempt)
    payload = encode_model_directive(directive)
    return _PreFixProofBundle(
        attempt_id=attempt.attempt_id,
        subject_id=attempt.subject_id,
        work_kind=attempt.work_kind,
        work_id=attempt.work_id,
        model_round_index=attempt.model_round_index,
        relay_id=binding.relay_id,
        outbound_request_fingerprint=binding.outbound_request_fingerprint,
        provider=directive.provenance.provider,
        model=directive.provenance.model,
        request_id=directive.provenance.request_id,
        directive_payload=payload,
        response_fingerprint=_fingerprint(runtime, directive),
        payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    )


def _stage(
    runtime: FusedTurnRuntime,
    *,
    work_kind: str,
    work_id: str,
    round_index: int,
    directive: ModelDirective,
    evidence: str,
):
    payload = encode_model_directive(directive)
    return runtime.stage_exact_background_response(
        work_kind=work_kind,
        work_id=work_id,
        model_round_index=round_index,
        provider=directive.provenance.provider,
        model=directive.provenance.model,
        provider_request_id=directive.provenance.request_id,
        response_fingerprint=_fingerprint(runtime, directive),
        directive_payload=payload,
        staged_at=NOW + timedelta(minutes=2),
        evidence=evidence,
    )


def _effect_snapshot(runtime: FusedTurnRuntime, attempt) -> dict[str, object]:
    return {
        "attempt": runtime.background_model_attempts.get(attempt.attempt_id),
        "staged": runtime.background_model_attempts.staged_response(attempt.attempt_id),
        "world_revision": int(runtime.store.current_world_revision()),
        "meters": tuple(
            runtime.metering.list_model_calls(subject_id=runtime.subject_id)
        ),
        "tasks": tuple(
            runtime.store.list_payloads(
                object_type=ObjectType.TASK,
                subject_id=runtime.subject_id,
            )
        ),
        "assistant": tuple(
            payload
            for payload in runtime.store.list_payloads(
                object_type=ObjectType.OBSERVATION,
                subject_id=runtime.subject_id,
            )
            if (payload.get("metadata") or {}).get("role") == "assistant"
        ),
    }


def _try_stage_or_confirm_clean_rejection(
    runtime: FusedTurnRuntime,
    attempt,
    stage_call: Callable[[], object],
) -> bool:
    """Return True for a clean rejection and False when vulnerable staging accepts."""

    before = _effect_snapshot(runtime, attempt)
    try:
        stage_call()
    except Exception:
        after = _effect_snapshot(runtime, attempt)
        assert after == before, "authenticity rejection mutated durable state"
        return True
    return False


def _stage_rejected_before_effect(
    runtime: FusedTurnRuntime,
    attempt,
    stage_call: Callable[[], object],
) -> None:
    """Require clean rejection; expose staging acceptance as a precise RED."""

    before = _effect_snapshot(runtime, attempt)
    rejected = _try_stage_or_confirm_clean_rejection(runtime, attempt, stage_call)
    if rejected:
        return
    after = _effect_snapshot(runtime, attempt)
    assert after == before, (
        "FORGED/MISSING AUTHENTICITY PROOF WAS ACCEPTED: staging or attempt "
        f"provenance changed; before={before!r}; after={after!r}"
    )


def _seed_watch_anchor(store: SQLiteWorldStore, *, subject_id: str = "user_1"):
    observation = Observation(
        object_id=f"obs_cbrr_auth_anchor_{subject_id}",
        subject_id=subject_id,
        occurred=TemporalExtent.point(NOW - timedelta(hours=1)),
        learned_at=NOW - timedelta(hours=1),
        recorded_at=NOW - timedelta(hours=1),
        created_by="test:core-background-response-authenticity",
        source_kind="conversation",
        modality="text",
        value="Durable anchor for an authenticity forgery probe.",
        metadata={"dimension": "dim:cbrr-auth"},
    )
    store.commit(
        [observation],
        OperationRequest(
            operation_name="test.cbrr-auth.seed-anchor",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed the capability-forgery probe",
            idempotency_key=f"cbrr-auth:seed-anchor:{subject_id}",
            source_class=SourceClass.USER,
        ),
    )
    return {"object_id": observation.object_id, "revision": 1}


def _watch_call(anchor_ref: dict[str, object], *, title: str) -> CapabilityCall:
    return CapabilityCall(
        name="create_attention_watch",
        arguments={
            "title": title,
            "dimensions": ["dim:cbrr-auth"],
            "reason_refs": [anchor_ref],
            "source_kind": "conversation",
            "modality": "text",
            "priority": 40,
            "cooldown_seconds": 60,
        },
        call_id="forged-watch-call",
    )


def _seed_review_fact(store: SQLiteWorldStore, *, subject_id: str = "user_1") -> None:
    fact = Observation(
        object_id=f"obs_cbrr_auth_review_{subject_id}",
        subject_id=subject_id,
        occurred=TemporalExtent.point(NOW - timedelta(hours=2)),
        learned_at=NOW - timedelta(hours=2),
        recorded_at=NOW - timedelta(hours=2),
        created_by="test:core-background-response-authenticity",
        source_kind="conversation",
        modality="text",
        value="Durable fact eligible for the cross-work-kind review probe.",
        metadata={"dimension": "dim:cbrr-auth"},
    )
    store.commit(
        [fact],
        OperationRequest(
            operation_name="test.cbrr-auth.seed-review",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed periodic review",
            idempotency_key=f"cbrr-auth:seed-review:{subject_id}",
            source_class=SourceClass.USER,
        ),
    )


def _running_review_id(store: SQLiteWorldStore, *, subject_id: str) -> str:
    running = [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.WAKE,
            subject_id=subject_id,
        )
        if payload.get("wake_state") == "running"
        and payload.get("wake_source") == WakeSource.PERIODIC_REVIEW.value
    ]
    assert len(running) == 1
    return str(running[0]["object_id"])


# A. No provider response + known relay id -> forged capability.
def test_auth_a_no_provider_response_known_relay_id_cannot_forge_capability(tmp_path):
    store, index, _db = _world(tmp_path)
    anchor = _seed_watch_anchor(store)
    index.catch_up()
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = _crash_wake(runtime, key="forged-capability")
    binding = _binding(runtime, attempt)
    title = "FORGED capability from no provider response"
    forged = _directive(
        binding.relay_id,
        capability_calls=(_watch_call(anchor, title=title),),
    )

    rejected = _try_stage_or_confirm_clean_rejection(
        runtime,
        attempt,
        lambda: _stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            directive=forged,
            evidence="no provider response existed; caller forged capability bytes",
        ),
    )
    if rejected:
        return

    def terminate_after_forged_capability(snapshot):
        return _directive(
            f"ordinary-next-round-{snapshot.round_index}", silence=True
        )

    _bind_handler(runtime, terminate_after_forged_capability)
    runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=3))
    forged_tasks = [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.TASK, subject_id="user_1"
        )
        if payload.get("title") == title
    ]
    assert forged_tasks == [], (
        "provider returned no response, but caller-forged capability bytes created "
        f"World tasks: {forged_tasks!r}"
    )


# B. No provider response + known relay id -> forged assistant response.
def test_auth_b_no_provider_response_known_relay_id_cannot_forge_assistant_response(
    tmp_path,
):
    store, index, _db = _world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    turn, execution_id, attempt = _crash_user_turn(runtime, key="forged-assistant")
    binding = _binding(runtime, attempt)
    forged_text = "FORGED assistant response never returned by the provider"
    forged = _directive(binding.relay_id, response=forged_text)

    rejected = _try_stage_or_confirm_clean_rejection(
        runtime,
        attempt,
        lambda: _stage(
            runtime,
            work_kind="user_turn",
            work_id=execution_id,
            round_index=0,
            directive=forged,
            evidence="no provider response existed; caller forged assistant bytes",
        ),
    )
    if rejected:
        return

    _bind_handler(
        runtime,
        lambda _snapshot: pytest.fail(
            "a recovered terminal response must not redispatch the provider"
        ),
    )
    runtime.run_turn(**turn)
    forged_outputs = [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.OBSERVATION, subject_id="user_1"
        )
        if (payload.get("metadata") or {}).get("role") == "assistant"
        and payload.get("value") == forged_text
    ]
    assert forged_outputs == [], (
        "caller-forged assistant bytes became durable output: "
        f"{forged_outputs!r}"
    )


# C. No provider response + known relay id -> forged silence.
def test_auth_c_no_provider_response_known_relay_id_cannot_forge_silence(tmp_path):
    store, index, _db = _world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = _crash_wake(runtime, key="forged-silence")
    binding = _binding(runtime, attempt)
    forged = _directive(binding.relay_id, silence=True)

    rejected = _try_stage_or_confirm_clean_rejection(
        runtime,
        attempt,
        lambda: _stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            directive=forged,
            evidence="no provider response existed; caller forged silence",
        ),
    )
    if rejected:
        return

    _bind_handler(
        runtime,
        lambda _snapshot: pytest.fail(
            "a recovered terminal silence must not redispatch the provider"
        ),
    )
    result = runtime.run_wake(
        wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=3)
    )
    assert result.wake.state == "running", (
        "caller-forged silence completed work despite no provider response: "
        f"{result!r}"
    )


# D. Modify a genuinely returned response and recompute the ordinary fingerprint.
def test_auth_d_modified_real_response_with_recomputed_fingerprint_is_rejected(
    tmp_path,
):
    store, index, _db = _world(tmp_path)
    captured: list[ModelDirective] = []

    def provider_returned_real_bytes(snapshot):
        exact = _directive(
            snapshot.outbound_relay_id,
            response="REAL provider response captured at the return boundary",
        )
        captured.append(exact)
        return exact

    runtime = FusedTurnRuntime(
        store=store, index=index, model_handler=provider_returned_real_bytes
    )
    signal = _emit_wake(runtime, key="tampered-real-response")

    def die_after_return_before_core_record(_snapshot, _directive):
        raise _SimulatedProcessDeath()

    runtime.cognitive_runtime.model_response_recorder = die_after_return_before_core_record
    with pytest.raises(_SimulatedProcessDeath):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)
    attempt = runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert attempt is not None and attempt.state == "dispatching"
    assert len(captured) == 1
    authentic_payload = encode_model_directive(captured[0])
    tampered = _directive(
        captured[0].provenance.request_id,
        response="TAMPERED provider response substituted after capture",
    )
    assert encode_model_directive(tampered) != authentic_payload

    _stage_rejected_before_effect(
        runtime,
        attempt,
        lambda: _stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            directive=tampered,
            evidence="real bytes were modified; caller recomputed ordinary fingerprint",
        ),
    )


# E. Copy the complete pre-fix proof bundle from attempt A to attempt B.
def test_auth_e_proof_a_cannot_be_replayed_to_attempt_b(tmp_path):
    store, index, _db = _world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal_a, attempt_a = _crash_wake(runtime, key="proof-attempt-a")
    signal_b, attempt_b = _crash_wake(runtime, key="proof-attempt-b")
    binding_a = _binding(runtime, attempt_a)
    binding_b = _binding(runtime, attempt_b)
    response_a = _directive(binding_a.relay_id, response="response/proof from attempt A")
    proof_a = _bundle(runtime, attempt_a, response_a)
    forged_for_b = _directive(
        binding_b.relay_id,
        response="response/proof from attempt A",
    )

    _stage_rejected_before_effect(
        runtime,
        attempt_b,
        lambda: _stage(
            runtime,
            work_kind="wake",
            work_id=signal_b.wake_id,
            round_index=0,
            directive=forged_for_b,
            evidence=proof_a.as_evidence(),
        ),
    )


# F. Copy proof across work kind (wake -> periodic_review).
def test_auth_f_proof_cannot_be_replayed_across_work_kind(tmp_path):
    store, index, _db = _world(tmp_path)
    _seed_review_fact(store)
    index.catch_up()
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    _signal_a, attempt_a = _crash_wake(runtime, key="proof-work-kind-a")
    binding_a = _binding(runtime, attempt_a)
    proof_a = _bundle(
        runtime,
        attempt_a,
        _directive(binding_a.relay_id, response="wake response A"),
    )

    def review_no_response(_snapshot):
        raise TimeoutError("periodic provider returned no response")

    _bind_handler(runtime, review_no_response)
    with pytest.raises(TimeoutError, match="periodic provider"):
        runtime.run_periodic_review(now=NOW)
    review_id = _running_review_id(store, subject_id="user_1")
    attempt_b = runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="periodic_review",
        work_id=review_id,
        model_round_index=0,
    )
    assert attempt_b is not None and attempt_b.state == "in_doubt"
    binding_b = _binding(runtime, attempt_b)
    forged_for_review = _directive(
        binding_b.relay_id,
        response="wake response A relabeled as periodic review",
    )

    _stage_rejected_before_effect(
        runtime,
        attempt_b,
        lambda: _stage(
            runtime,
            work_kind="periodic_review",
            work_id=review_id,
            round_index=0,
            directive=forged_for_review,
            evidence=proof_a.as_evidence(),
        ),
    )


# G. Copy proof across subject.
def test_auth_g_proof_cannot_be_replayed_across_subject(tmp_path):
    store, index, _db = _world(tmp_path)
    runtime_a = FusedTurnRuntime(
        store=store, index=index, subject_id="subject_a", model_handler=lambda _s: None
    )
    runtime_b = FusedTurnRuntime(
        store=store, index=index, subject_id="subject_b", model_handler=lambda _s: None
    )
    _signal_a, attempt_a = _crash_wake(runtime_a, key="proof-subject-a")
    signal_b, attempt_b = _crash_wake(runtime_b, key="proof-subject-b")
    binding_a = _binding(runtime_a, attempt_a)
    binding_b = _binding(runtime_b, attempt_b)
    proof_a = _bundle(
        runtime_a,
        attempt_a,
        _directive(binding_a.relay_id, response="subject A response"),
    )
    forged_for_b = _directive(
        binding_b.relay_id,
        response="subject A response relabeled for subject B",
    )

    _stage_rejected_before_effect(
        runtime_b,
        attempt_b,
        lambda: _stage(
            runtime_b,
            work_kind="wake",
            work_id=signal_b.wake_id,
            round_index=0,
            directive=forged_for_b,
            evidence=proof_a.as_evidence(),
        ),
    )


# H. Copy proof from round N to round M.
def test_auth_h_proof_cannot_be_replayed_from_round_n_to_round_m(tmp_path):
    store, index, _db = _world(tmp_path)
    returned_round_0: list[ModelDirective] = []

    def provider(snapshot):
        if snapshot.round_index == 0:
            directive = _directive(
                snapshot.outbound_relay_id,
                capability_calls=(
                    CapabilityCall(
                        name="search_world",
                        arguments={"query": "cbrr-auth-round", "limit": 1},
                        call_id="round-zero-search",
                    ),
                ),
            )
            returned_round_0.append(directive)
            return directive
        raise TimeoutError("round 1 provider returned no response")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=provider)
    signal = _emit_wake(runtime, key="proof-cross-round")
    with pytest.raises(TimeoutError, match="round 1"):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)
    round_0 = runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    round_1 = runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=1,
    )
    assert round_0 is not None and round_0.state == "metered"
    assert round_1 is not None and round_1.state == "in_doubt"
    assert len(returned_round_0) == 1
    proof_round_0 = _bundle(runtime, round_0, returned_round_0[0])
    binding_round_1 = _binding(runtime, round_1)
    forged_round_1 = _directive(
        binding_round_1.relay_id,
        response="round 0 proof replayed as round 1 response",
    )

    _stage_rejected_before_effect(
        runtime,
        round_1,
        lambda: _stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=1,
            directive=forged_round_1,
            evidence=proof_round_0.as_evidence(),
        ),
    )


# I. Copy proof while changing provider/model/request metadata.  Each resulting
# directive is internally self-consistent and has a recomputed ordinary fingerprint.
@pytest.mark.parametrize("tampered_field", ("provider", "model", "request_id"))
def test_auth_i_copied_proof_with_metadata_tamper_is_rejected(
    tmp_path,
    tampered_field,
):
    store, index, _db = _world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    _signal_a, attempt_a = _crash_wake(runtime, key=f"metadata-a-{tampered_field}")
    signal_b, attempt_b = _crash_wake(runtime, key=f"metadata-b-{tampered_field}")
    binding_a = _binding(runtime, attempt_a)
    binding_b = _binding(runtime, attempt_b)
    proof_a = _bundle(
        runtime,
        attempt_a,
        _directive(binding_a.relay_id, response="authentic metadata A"),
    )

    provider = "tampered-provider" if tampered_field == "provider" else PROVIDER
    model = "tampered-model" if tampered_field == "model" else MODEL
    # Moving A's alleged proof to B necessarily tampers request metadata from A's
    # relay id to B's public relay id.  This remains true in the request_id case.
    request_id = binding_b.relay_id
    forged_for_b = _directive(
        request_id,
        provider=provider,
        model=model,
        response=f"proof A with tampered {tampered_field}",
    )

    _stage_rejected_before_effect(
        runtime,
        attempt_b,
        lambda: _stage(
            runtime,
            work_kind="wake",
            work_id=signal_b.wake_id,
            round_index=0,
            directive=forged_for_b,
            evidence=proof_a.as_evidence(),
        ),
    )


# J. Exact bytes and all public metadata, but no trusted authenticity proof.
def test_auth_j_missing_authenticity_proof_fails_closed(tmp_path):
    store, index, _db = _world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, attempt = _crash_wake(runtime, key="missing-proof")
    binding = _binding(runtime, attempt)
    exact_but_unauthenticated = _directive(
        binding.relay_id,
        response="self-consistent bytes without trusted authenticity proof",
    )

    _stage_rejected_before_effect(
        runtime,
        attempt,
        lambda: _stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=0,
            directive=exact_but_unauthenticated,
            evidence="MISSING_AUTHENTICITY_PROOF",
        ),
    )
