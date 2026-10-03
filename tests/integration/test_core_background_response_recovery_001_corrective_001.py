"""CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-001 blocker probes.

Red-first coverage for the two Independent Acceptance blockers. On the historical
failed exact candidate these probes must fail closed only after the corrective;
before that fix they reproduce the accepted transplant and last-key-wins bugs.

IA-BLK-001: an exact self-consistent response from one originating request must
not be staged onto another dispatching/in_doubt attempt, even when provider and
model match and the caller copies A's request identity together with A's bytes.

IA-BLK-002: duplicate JSON object keys must be rejected before semantic
construction. Last-key-wins must not discard a conflicting field.

Rejection must happen before semantic application and before attempt provenance
is rewritten.
"""

from __future__ import annotations

import multiprocessing
import os
import signal as posix_signal
from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import ObjectType, SourceClass, WakeSource
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import BackgroundModelExecutionInDoubt, ModelDirective
from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.live_return import (
    open_live_provider_return_window,
    register_handler_return,
)
from aios_core.runtime.cognitive_runtime import ModelCallProvenance, ModelUsage
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import WakeSignalRequest


NOW = datetime(2026, 9, 26, 8, 0, tzinfo=timezone.utc)
PROVIDER = "relay-provider"
MODEL = "relay-model"


def _world(tmp_path, name="world.db"):
    db = tmp_path / name
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index, db


def _wake_ref(signal) -> ObjectRef:
    return ObjectRef(object_id=signal.wake_id, revision=signal.revision)


def _directive(
    request_id: str,
    *,
    silence: bool = True,
    response: str | None = None,
    capability_calls=(),
) -> ModelDirective:
    provenance = ModelCallProvenance(
        provider=PROVIDER, model=MODEL, request_id=request_id
    )
    return ModelDirective(
        response=response,
        silence=silence,
        capability_calls=tuple(capability_calls),
        usage=ModelUsage(
            input_tokens=4,
            output_tokens=1,
            total_tokens=5,
            provider=PROVIDER,
            model=MODEL,
            request_id=request_id,
        ),
        provenance=provenance,
    )


def _fingerprint(runtime, directive: ModelDirective) -> str:
    return runtime.background_model_attempts._response_fingerprint(directive)


def _bind_handler(runtime, handler) -> None:
    runtime.model_handler = handler
    runtime.cognitive_runtime.model_handler = handler


def _crash_wake(runtime, *, key: str):
    calls: list[int] = []

    def ambiguous(snapshot):
        calls.append(snapshot.round_index)
        raise TimeoutError("provider may already have accepted the request")

    _bind_handler(runtime, ambiguous)
    signal = runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id=f"cbrr-fix.{key}",
            observed_at=NOW,
            dedupe_key=f"cbrr-fix:{key}",
        )
    )
    with pytest.raises(TimeoutError, match="may already have accepted"):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)
    return signal, calls


def _attempt(runtime, *, work_kind: str, work_id: str, round_index: int = 0):
    return runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id,
        work_kind=work_kind,
        work_id=work_id,
        model_round_index=round_index,
    )


def capture_live_provider_return(attempts, attempt_id, *, captured_at, directive):
    """Exercise the real live provider-return authority.

    Corrective-002 history note (Window 19).  This file previously simulated the
    trusted relay return by calling
    ``BackgroundModelAttemptStore._capture_trusted_response_return`` directly.
    Window 17 `BLK-W17-001` proved that helper was a recovery-reachable minting
    oracle (any caller with bytes plus an attempt id could mint a durable trusted
    receipt and handoff), so it was removed.  The helper below opens the same
    ephemeral window the production model-call frame opens, registers the exact
    handler-returned object, and then uses the production writer.  The recovery
    assertions that follow are unchanged and strictly stronger: the receipt can
    now only exist because a live provider return actually happened, or because a
    genuine external RSA proof was verified.
    """

    with open_live_provider_return_window(attempt_id=attempt_id) as window:
        register_handler_return(window, directive)
        return attempts.record_live_provider_return(
            attempt_id,
            captured_at=captured_at,
            directive=directive,
            live_window=window,
        )


def _stage(
    runtime,
    *,
    work_kind,
    work_id,
    round_index,
    directive,
    payload=None,
    trusted_return=False,
):
    raw = encode_model_directive(directive) if payload is None else payload
    authenticity_proof = None
    if trusted_return:
        attempt = _attempt(
            runtime,
            work_kind=work_kind,
            work_id=work_id,
            round_index=round_index,
        )
        assert attempt is not None
        # Test-only simulation of the trusted provider/relay return boundary,
        # now through the real ephemeral live-return authority.  The historical
        # expectation here was that a private capture helper could be invoked
        # freely; Window 17 `BLK-W17-001` showed that was a recovery-reachable
        # minting oracle, so this probe now drives (and is constrained by) the
        # same authority the production provider-return boundary uses.
        receipt = capture_live_provider_return(
            runtime.background_model_attempts,
            attempt.attempt_id,
            captured_at=NOW + timedelta(minutes=1),
            directive=directive,
        )
        authenticity_proof = receipt.authenticity_proof
    return runtime.stage_exact_background_response(
        work_kind=work_kind,
        work_id=work_id,
        model_round_index=round_index,
        provider=directive.provenance.provider,
        model=directive.provenance.model,
        provider_request_id=directive.provenance.request_id,
        response_fingerprint=_fingerprint(runtime, directive),
        directive_payload=raw,
        staged_at=NOW + timedelta(minutes=2),
        evidence="copied exact response from another originating request",
        authenticity_proof=authenticity_proof,
    )


def _assert_untouched(runtime, attempt_id: str, *, revision_before: int):
    attempt = runtime.background_model_attempts.get(attempt_id)
    assert attempt is not None
    assert attempt.state == "in_doubt"
    assert attempt.provider is None
    assert attempt.model is None
    assert attempt.provider_request_id is None
    assert attempt.response_fingerprint is None
    assert runtime.background_model_attempts.staged_response(attempt_id) is None
    assert int(runtime.store.current_world_revision()) == revision_before
    assert (
        len(runtime.metering.list_model_calls(subject_id=runtime.subject_id)) == 0
    )


def _seed_review_fact(store: SQLiteWorldStore, *, subject_id: str = "user_1") -> None:
    fact = Observation(
        object_id=f"obs_cbrr_fix_review_{subject_id}",
        subject_id=subject_id,
        occurred=TemporalExtent.point(NOW - timedelta(hours=1)),
        learned_at=NOW - timedelta(hours=1),
        recorded_at=NOW - timedelta(hours=1),
        created_by="test:core-background-response-recovery-corrective-001",
        source_kind="conversation",
        modality="text",
        value="A durable fact eligible for periodic review.",
        metadata={"dimension": "dim:cbrr-fix"},
    )
    store.commit(
        [fact],
        OperationRequest(
            operation_name="test.cbrr-fix.seed_review_fact",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed periodic review fact",
            idempotency_key=f"cbrr-fix:seed-review-fact:{subject_id}",
            source_class=SourceClass.USER,
        ),
    )


def _running_review_id(store: SQLiteWorldStore, *, subject_id: str) -> str:
    running = [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.WAKE, subject_id=subject_id
        )
        if payload.get("wake_state") == "running"
        and payload.get("wake_source") == WakeSource.PERIODIC_REVIEW.value
    ]
    assert len(running) == 1
    return str(running[0]["object_id"])


def test_blk001_cross_work_transplant_rejected_before_provenance_rewrite(tmp_path):
    store, index, _db = _world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    _crash_wake(runtime, key="work-a")
    signal_b, calls_b = _crash_wake(runtime, key="work-b")
    attempt_b = _attempt(runtime, work_kind="wake", work_id=signal_b.wake_id)
    revision = int(store.current_world_revision())
    foreign = _directive("req-work-a", silence=False, response="reply that belongs to work A")

    with pytest.raises(Exception, match="originating request"):
        _stage(
            runtime,
            work_kind="wake",
            work_id=signal_b.wake_id,
            round_index=0,
            directive=foreign,
        )

    _assert_untouched(runtime, attempt_b.attempt_id, revision_before=revision)
    with pytest.raises(BackgroundModelExecutionInDoubt):
        runtime.run_wake(wake_ref=_wake_ref(signal_b), now=NOW + timedelta(minutes=3))
    assert calls_b == [0]


def test_blk001_copied_token_with_copied_response_still_rejected(tmp_path):
    """Copying A's request identity together with A's bytes must not admit B."""

    store, index, _db = _world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    _crash_wake(runtime, key="token-a")
    signal_b, _calls = _crash_wake(runtime, key="token-b")
    attempt_b = _attempt(runtime, work_kind="wake", work_id=signal_b.wake_id)
    foreign = _directive("req-token-a", silence=False, response="A exact bytes")
    payload = encode_model_directive(foreign)
    revision = int(store.current_world_revision())

    with pytest.raises(Exception, match="originating request"):
        runtime.background_model_attempts.stage_exact_response(
            attempt_b.attempt_id,
            staged_at=NOW + timedelta(minutes=2),
            provider=PROVIDER,
            model=MODEL,
            provider_request_id=foreign.provenance.request_id,
            response_fingerprint=_fingerprint(runtime, foreign),
            directive_payload=payload,
            evidence="caller copied A's token and A's response onto B's attempt_id",
        )

    _assert_untouched(runtime, attempt_b.attempt_id, revision_before=revision)


def test_blk001_wake_to_periodic_review_transplant_rejected(tmp_path):
    store, index, _db = _world(tmp_path)
    _seed_review_fact(store)
    index.catch_up()
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    _crash_wake(runtime, key="wake-source")

    def ambiguous(_snapshot):
        raise TimeoutError("review provider may already have accepted the request")

    _bind_handler(runtime, ambiguous)
    with pytest.raises(TimeoutError, match="review provider"):
        runtime.run_periodic_review(now=NOW)
    review_id = _running_review_id(store, subject_id="user_1")
    attempt = _attempt(runtime, work_kind="periodic_review", work_id=review_id)
    revision = int(store.current_world_revision())

    with pytest.raises(Exception, match="originating request"):
        _stage(
            runtime,
            work_kind="periodic_review",
            work_id=review_id,
            round_index=0,
            directive=_directive("req-wake-source", silence=False, response="wake reply"),
        )

    _assert_untouched(runtime, attempt.attempt_id, revision_before=revision)


def test_blk001_periodic_review_to_user_turn_transplant_rejected(tmp_path):
    store, index, _db = _world(tmp_path)
    _seed_review_fact(store)
    index.catch_up()
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)

    def ambiguous(_snapshot):
        raise TimeoutError("provider may already have accepted the request")

    _bind_handler(runtime, ambiguous)
    with pytest.raises(TimeoutError, match="may already have accepted"):
        runtime.run_periodic_review(now=NOW)
    review = _directive("req-review-source", silence=False, response="review reply")

    turn = dict(
        session_id="cbrr-fix-session",
        turn_index=1,
        user_input="SYNTHETIC corrective user turn",
        occurred_at=NOW,
    )
    with pytest.raises(TimeoutError, match="may already have accepted"):
        runtime.run_turn(**turn)
    inspection = runtime.inspect_turn_execution(**turn)
    attempt = inspection.model_attempts[0]
    assert attempt.state == "in_doubt"
    revision = int(store.current_world_revision())

    with pytest.raises(Exception, match="originating request"):
        _stage(
            runtime,
            work_kind="user_turn",
            work_id=inspection.execution_id,
            round_index=0,
            directive=review,
        )

    _assert_untouched(runtime, attempt.attempt_id, revision_before=revision)
    outputs = [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.OBSERVATION, subject_id="user_1"
        )
        if (payload.get("metadata") or {}).get("role") == "assistant"
    ]
    assert outputs == []


def test_blk001_cross_subject_transplant_rejected(tmp_path):
    store, index, _db = _world(tmp_path)
    runtime_a = FusedTurnRuntime(
        store=store, index=index, subject_id="subject_a", model_handler=lambda _s: None
    )
    runtime_b = FusedTurnRuntime(
        store=store, index=index, subject_id="subject_b", model_handler=lambda _s: None
    )
    _crash_wake(runtime_a, key="subject-a")
    signal_b, _calls = _crash_wake(runtime_b, key="subject-b")
    attempt_b = _attempt(runtime_b, work_kind="wake", work_id=signal_b.wake_id)
    revision = int(store.current_world_revision())

    with pytest.raises(Exception, match="originating request"):
        _stage(
            runtime_b,
            work_kind="wake",
            work_id=signal_b.wake_id,
            round_index=0,
            directive=_directive(
                "req-subject-a", silence=False, response="subject A reply"
            ),
        )

    _assert_untouched(runtime_b, attempt_b.attempt_id, revision_before=revision)


def test_blk001_cross_round_transplant_rejected(tmp_path):
    store, index, _db = _world(tmp_path)
    round_0 = _directive(
        "req-round-0",
        silence=False,
        capability_calls=(
            CapabilityCall(
                name="search_world",
                arguments={"query": "cbrr-fix-round", "limit": 1},
                call_id="call-round-0",
            ),
        ),
    )

    def scripted(snapshot):
        if snapshot.round_index == 0:
            return round_0
        raise TimeoutError("round 1 died after provider dispatch")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=scripted)
    signal = runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id="cbrr-fix.round",
            observed_at=NOW,
            dedupe_key="cbrr-fix:round",
        )
    )
    with pytest.raises(TimeoutError, match="round 1 died"):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)
    round_1 = _attempt(runtime, work_kind="wake", work_id=signal.wake_id, round_index=1)
    assert round_1.state == "in_doubt"
    revision = int(store.current_world_revision())
    meters_before = len(
        runtime.metering.list_model_calls(subject_id="user_1", wake_id=signal.wake_id)
    )

    with pytest.raises(Exception, match="originating request"):
        _stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            round_index=1,
            directive=round_0,
        )

    attempt = runtime.background_model_attempts.get(round_1.attempt_id)
    assert attempt.state == "in_doubt"
    assert attempt.provider_request_id is None
    assert runtime.background_model_attempts.staged_response(round_1.attempt_id) is None
    assert int(store.current_world_revision()) == revision
    assert (
        len(runtime.metering.list_model_calls(subject_id="user_1", wake_id=signal.wake_id))
        == meters_before
    )


def test_blk001_identical_provider_model_transplant_rejected(tmp_path):
    store, index, _db = _world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    _crash_wake(runtime, key="same-meta-a")
    signal_b, _calls = _crash_wake(runtime, key="same-meta-b")
    attempt_b = _attempt(runtime, work_kind="wake", work_id=signal_b.wake_id)
    foreign = _directive("req-same-meta-a")
    assert foreign.provenance.provider == PROVIDER
    assert foreign.provenance.model == MODEL
    revision = int(store.current_world_revision())

    with pytest.raises(Exception, match="originating request"):
        _stage(
            runtime,
            work_kind="wake",
            work_id=signal_b.wake_id,
            round_index=0,
            directive=foreign,
        )

    _assert_untouched(runtime, attempt_b.attempt_id, revision_before=revision)


def _usage(request_id: str = "req-dup") -> str:
    return (
        '{"input_tokens":4,"model":"relay-model","output_tokens":1,'
        f'"provider":"relay-provider","request_id":"{request_id}","total_tokens":5}}'
    )


def _provenance(request_id: str = "req-dup", provider: str = PROVIDER) -> str:
    return (
        f'{{"model":"{MODEL}","provider":"{provider}","request_id":"{request_id}"}}'
    )


def _silence_shell(*, usage: str, provenance: str, extra: str = "") -> str:
    return (
        '{"capability_calls":[],'
        f'"provenance":{provenance},'
        '"response":null,"silence":true,'
        f'"usage":{usage}{extra}}}'
    )


@pytest.mark.parametrize(
    "label,payload_factory,normalized_request_id",
    (
        (
            "top-level-response",
            lambda: (
                '{"capability_calls":[],'
                f'"provenance":{_provenance()},'
                '"response":"must not be applied","response":null,'
                '"silence":true,'
                f'"usage":{_usage()}}}'
            ),
            "req-dup",
        ),
        (
            "top-level-silence",
            lambda: (
                '{"capability_calls":[],'
                f'"provenance":{_provenance()},'
                '"response":null,"silence":false,"silence":true,'
                f'"usage":{_usage()}}}'
            ),
            "req-dup",
        ),
        (
            "top-level-capability-calls",
            lambda: (
                '{"capability_calls":[{"arguments":{},"call_id":"c1",'
                '"name":"create_attention_watch"}],"capability_calls":[],'
                f'"provenance":{_provenance()},'
                '"response":null,"silence":true,'
                f'"usage":{_usage()}}}'
            ),
            "req-dup",
        ),
        (
            "nested-usage-request-id",
            lambda: _silence_shell(
                usage=(
                    '{"input_tokens":4,"model":"relay-model","output_tokens":1,'
                    '"provider":"relay-provider","request_id":"req-hidden",'
                    '"request_id":"req-dup","total_tokens":5}'
                ),
                provenance=_provenance(),
            ),
            "req-dup",
        ),
        (
            "nested-provenance-provider",
            lambda: _silence_shell(
                usage=_usage(),
                provenance=(
                    '{"model":"relay-model","provider":"other-provider",'
                    '"provider":"relay-provider","request_id":"req-dup"}'
                ),
            ),
            "req-dup",
        ),
        (
            "capability-call-name",
            lambda: (
                '{"capability_calls":[{"arguments":{"x":1},"call_id":"c1",'
                '"name":"not-the-name","name":"create_attention_watch"}],'
                f'"provenance":{_provenance()},'
                '"response":null,"silence":false,'
                f'"usage":{_usage()}}}'
            ),
            "req-dup",
        ),
        (
            "nested-capability-arguments",
            lambda: (
                '{"capability_calls":[{"arguments":{"title":"kept-first",'
                '"title":"kept-last"},"call_id":"c1",'
                '"name":"create_attention_watch"}],'
                f'"provenance":{_provenance()},'
                '"response":null,"silence":false,'
                f'"usage":{_usage()}}}'
            ),
            "req-dup",
        ),
    ),
)
def test_blk002_duplicate_json_keys_rejected_before_semantic_construction(
    tmp_path, label, payload_factory, normalized_request_id
):
    store, index, _db = _world(tmp_path, name=f"{label}.db")
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, _calls = _crash_wake(runtime, key=label)
    attempt = _attempt(runtime, work_kind="wake", work_id=signal.wake_id)
    revision = int(store.current_world_revision())
    payload = payload_factory()
    # Fingerprint of the directive last-key-wins would have constructed. The old
    # decoder accepts this payload; the corrective must reject it first.
    normalized = _directive(
        normalized_request_id,
        silence=label not in {"capability-call-name", "nested-capability-arguments"},
        capability_calls=(
            ()
            if label not in {"capability-call-name", "nested-capability-arguments"}
            else (
                CapabilityCall(
                    name="create_attention_watch",
                    arguments=(
                        {"x": 1}
                        if label == "capability-call-name"
                        else {"title": "kept-last"}
                    ),
                    call_id="c1",
                ),
            )
        ),
    )
    with pytest.raises(ValueError, match="duplicate"):
        runtime.stage_exact_background_response(
            work_kind="wake",
            work_id=signal.wake_id,
            model_round_index=0,
            provider=PROVIDER,
            model=MODEL,
            provider_request_id=normalized_request_id,
            response_fingerprint=_fingerprint(runtime, normalized),
            directive_payload=payload,
            staged_at=NOW + timedelta(minutes=2),
            evidence=f"duplicate-key payload {label} must never be staged",
        )

    _assert_untouched(runtime, attempt.attempt_id, revision_before=revision)
    with pytest.raises(BackgroundModelExecutionInDoubt):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=4))
    tasks = [
        payload
        for payload in store.list_payloads(object_type=ObjectType.TASK, subject_id="user_1")
        if payload.get("title") in {"kept-last", "kept-first"}
    ]
    assert tasks == []


def test_blk001_binding_is_durable_before_provider_handler_runs(tmp_path):
    store, index, _db = _world(tmp_path)
    seen: dict[str, str | None] = {}

    def observe(snapshot):
        seen["attempt_id"] = snapshot.model_attempt_id
        seen["relay_id"] = snapshot.outbound_relay_id
        raise TimeoutError("provider may already have accepted the request")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=observe)
    signal = runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id="cbrr-fix.before-handler",
            observed_at=NOW,
            dedupe_key="cbrr-fix:before-handler",
        )
    )
    with pytest.raises(TimeoutError, match="may already have accepted"):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)
    attempt = _attempt(runtime, work_kind="wake", work_id=signal.wake_id)
    binding = runtime.background_model_attempts.outbound_request_binding(
        attempt.attempt_id
    )
    assert binding is not None
    assert seen["attempt_id"] == attempt.attempt_id
    assert seen["relay_id"] == binding.relay_id
    assert attempt.state == "in_doubt"


def test_blk001_same_attempt_correct_binding_recovers_with_zero_provider_calls(tmp_path):
    store, index, db = _world(tmp_path)
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, calls = _crash_wake(runtime, key="positive-same-attempt")
    attempt = _attempt(runtime, work_kind="wake", work_id=signal.wake_id)
    binding = runtime.background_model_attempts.outbound_request_binding(
        attempt.attempt_id
    )
    assert binding is not None
    assert binding.subject_id == runtime.subject_id
    assert binding.work_kind == "wake"
    assert binding.work_id == signal.wake_id
    assert binding.model_round_index == 0
    assert binding.attempt_id == attempt.attempt_id
    assert binding.outbound_request_fingerprint
    assert binding.relay_id == runtime.background_model_attempts.relay_id_for(
        subject_id=binding.subject_id,
        work_kind=binding.work_kind,
        work_id=binding.work_id,
        model_round_index=binding.model_round_index,
        attempt_id=binding.attempt_id,
        outbound_request_fingerprint=binding.outbound_request_fingerprint,
    )
    exact = _directive(
        binding.relay_id, silence=False, response="exact recovered reply"
    )
    _stage(
        runtime,
        work_kind="wake",
        work_id=signal.wake_id,
        round_index=0,
        directive=exact,
        trusted_return=True,
    )
    recovery_calls: list[int] = []

    def must_not_call(snapshot):
        recovery_calls.append(snapshot.round_index)
        pytest.fail("recovered round must not redispatch the provider")

    reopened_store, reopened_index = _reopen(db)
    restarted = FusedTurnRuntime(
        store=reopened_store, index=reopened_index, model_handler=must_not_call
    )
    result = restarted.run_wake(
        wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=5)
    )
    assert result.wake.state == "completed"
    assert result.runtime.response == "exact recovered reply"
    assert result.runtime.recovered_response_attempts == (attempt.attempt_id,)
    assert recovery_calls == []
    assert calls == [0]
    assert (
        len(
            restarted.metering.list_model_calls(
                subject_id="user_1", wake_id=signal.wake_id
            )
        )
        == 1
    )


def _reopen(db):
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def _child_stage_exact_then_sigkill(db_path: str) -> None:
    store = SQLiteWorldStore(db_path)
    index = WorldSearchIndex(db_path, store=store)
    index.rebuild()
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    signal, _calls = _crash_wake(runtime, key="sigkill-staged")
    attempt = _attempt(runtime, work_kind="wake", work_id=signal.wake_id)
    binding = runtime.background_model_attempts.outbound_request_binding(
        attempt.attempt_id
    )
    exact = _directive(binding.relay_id, silence=False, response="durable before kill")
    _stage(
        runtime,
        work_kind="wake",
        work_id=signal.wake_id,
        round_index=0,
        directive=exact,
        trusted_return=True,
    )
    os.kill(os.getpid(), posix_signal.SIGKILL)


def _child_capability_then_sigkill(db_path: str) -> None:
    store = SQLiteWorldStore(db_path)
    index = WorldSearchIndex(db_path, store=store)
    index.rebuild()
    observation = Observation(
        object_id="obs_cbrr_fix_kill_anchor",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=2)),
        learned_at=NOW - timedelta(hours=2),
        recorded_at=NOW - timedelta(hours=2),
        created_by="test:core-background-response-recovery-corrective-001",
        source_kind="conversation",
        modality="text",
        value="Anchor for the killed capability write.",
        metadata={"dimension": "dim:cbrr-fix"},
    )
    store.commit(
        [observation],
        OperationRequest(
            operation_name="test.cbrr-fix.seed_kill_anchor",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed capability evidence",
            idempotency_key="cbrr-fix:seed-kill-anchor",
            source_class=SourceClass.USER,
        ),
    )
    index.catch_up()
    directive = _directive(
        "req-kill-capability",
        silence=False,
        capability_calls=(
            CapabilityCall(
                name="create_attention_watch",
                arguments={
                    "title": "cbrr fix kill watch",
                    "dimensions": ["dim:cbrr-fix"],
                    "reason_refs": [
                        {"object_id": "obs_cbrr_fix_kill_anchor", "revision": 1}
                    ],
                    "source_kind": "conversation",
                    "modality": "text",
                    "priority": 40,
                    "cooldown_seconds": 60,
                },
                call_id="call-kill-watch",
            ),
        ),
    )

    def scripted(snapshot):
        if snapshot.round_index == 0:
            return directive
        raise AssertionError("process must die during capability application")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=scripted)
    signal = runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id="cbrr-fix.kill-capability",
            observed_at=NOW,
            dedupe_key="cbrr-fix:kill-capability",
        )
    )
    real_handler = runtime._create_attention_watch

    def kill_after_commit(**kwargs):
        real_handler(**kwargs)
        os.kill(os.getpid(), posix_signal.SIGKILL)

    spec = runtime.registry.get_spec("create_attention_watch")
    runtime.registry.unregister("create_attention_watch")
    runtime.registry.register(spec, kill_after_commit)
    runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)


def test_process_sigkill_after_exact_response_staged_recovers_with_zero_provider_calls(
    tmp_path,
):
    db = tmp_path / "sigkill-staged.db"
    ctx = multiprocessing.get_context("fork")
    process = ctx.Process(target=_child_stage_exact_then_sigkill, args=(str(db),))
    process.start()
    process.join(30)
    assert process.exitcode == -posix_signal.SIGKILL

    store, index = _reopen(db)
    recovery_calls: list[int] = []

    def must_not_call(snapshot):
        recovery_calls.append(snapshot.round_index)
        pytest.fail("provider must not be called after SIGKILL recovery")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=must_not_call)
    running = [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.WAKE, subject_id="user_1"
        )
        if payload.get("wake_state") == "running"
    ]
    assert len(running) == 1
    wake_id = str(running[0]["object_id"])
    attempt = _attempt(runtime, work_kind="wake", work_id=wake_id)
    assert attempt.state == "response_returned"
    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=wake_id, revision=int(running[0]["revision"])),
        now=NOW + timedelta(minutes=6),
    )
    assert result.runtime.response == "durable before kill"
    assert result.runtime.recovered_response_attempts == (attempt.attempt_id,)
    assert recovery_calls == []
    assert (
        len(runtime.metering.list_model_calls(subject_id="user_1", wake_id=wake_id))
        == 1
    )


def test_process_sigkill_after_capability_side_effect_replays_exactly_once(tmp_path):
    db = tmp_path / "sigkill-capability.db"
    ctx = multiprocessing.get_context("fork")
    process = ctx.Process(target=_child_capability_then_sigkill, args=(str(db),))
    process.start()
    process.join(30)
    assert process.exitcode == -posix_signal.SIGKILL

    store, index = _reopen(db)
    tasks = [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.TASK, subject_id="user_1"
        )
        if payload.get("title") == "cbrr fix kill watch"
    ]
    assert len(tasks) == 1
    assert int(tasks[0]["revision"]) == 1

    recovery_calls: list[int] = []

    def provider(snapshot):
        recovery_calls.append(snapshot.round_index)
        return _directive("req-after-kill-next", silence=True)

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=provider)
    running = [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.WAKE, subject_id="user_1"
        )
        if payload.get("wake_state") == "running"
    ]
    assert len(running) == 1
    wake_id = str(running[0]["object_id"])
    attempt = _attempt(runtime, work_kind="wake", work_id=wake_id)
    assert attempt.state == "metered"
    exact = _directive(
        attempt.provider_request_id,
        silence=False,
        capability_calls=(
            CapabilityCall(
                name="create_attention_watch",
                arguments={
                    "title": "cbrr fix kill watch",
                    "dimensions": ["dim:cbrr-fix"],
                    "reason_refs": [
                        {"object_id": "obs_cbrr_fix_kill_anchor", "revision": 1}
                    ],
                    "source_kind": "conversation",
                    "modality": "text",
                    "priority": 40,
                    "cooldown_seconds": 60,
                },
                call_id="call-kill-watch",
            ),
        ),
    )
    _stage(
        runtime,
        work_kind="wake",
        work_id=wake_id,
        round_index=0,
        directive=exact,
        trusted_return=True,
    )
    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=wake_id, revision=int(running[0]["revision"])),
        now=NOW + timedelta(minutes=8),
    )
    assert result.runtime.recovered_response_attempts == (attempt.attempt_id,)
    assert recovery_calls == [1]
    tasks_after = [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.TASK, subject_id="user_1"
        )
        if payload.get("title") == "cbrr fix kill watch"
    ]
    assert len(tasks_after) == 1
    assert int(tasks_after[0]["revision"]) == 1
