"""CORE-BACKGROUND-RESPONSE-RECOVERY-001 fault matrix.

Each test kills the process (or the model call) exactly at one durable provider or
application boundary, then proves the smallest Core recovery mechanism:

* an exact provider reply that was durably preserved externally resumes the *same*
  attempt/round through the ordinary CognitiveRuntime application path;
* the provider handler is never called again for that attempt/round;
* capability side effects, assistant output and metering stay exactly-once;
* missing, mismatched or unverifiable exact bytes stay fail-closed (in_doubt /
  blocked), never a retry and never a semantic reconstruction;
* the normal provider path and the existing not_submitted retry semantics are
  unchanged.

No Resident, no sealed fixture and no historical evidence is touched.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import ObjectType, SourceClass, WakeSource
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    BackgroundModelAttemptBlocked,
    BackgroundModelExecutionInDoubt,
    BackgroundModelResponsePending,
    ModelCallProvenance,
    ModelDirective,
    ModelDispatchNotSubmitted,
    ModelUsage,
    TurnAlreadyCompleted,
    TurnExecutionInDoubt,
)
from aios_core.runtime.background_attempt import (
    BackgroundModelResponseConflict,
    encode_model_directive,
)
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import WakeSignalRequest


NOW = datetime(2026, 9, 26, 6, 0, tzinfo=timezone.utc)
PROVIDER = "relay-provider"
MODEL = "relay-model"


class _SimulatedCrash(BaseException):
    """Process death, not a capability error (escapes registry's except Exception)."""


def _world(tmp_path, name="world.db"):
    db = tmp_path / name
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index, db


def _reopen(db):
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def _wake_ref(signal) -> ObjectRef:
    return ObjectRef(object_id=signal.wake_id, revision=signal.revision)


def _emit_wake(runtime, *, key, source=WakeSource.SAFETY, observed_at=NOW):
    return runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=source,
            rule_id=f"cbrr.{key}",
            observed_at=observed_at,
            dedupe_key=f"cbrr:{key}",
        )
    )


def _directive(
    request_id: str,
    *,
    silence: bool = True,
    response: str | None = None,
    capability_calls=(),
    provider: str = PROVIDER,
    model: str = MODEL,
) -> ModelDirective:
    provenance = ModelCallProvenance(
        provider=provider,
        model=model,
        request_id=request_id,
    )
    return ModelDirective(
        response=response,
        silence=silence,
        capability_calls=tuple(capability_calls),
        usage=ModelUsage(
            input_tokens=4,
            output_tokens=1,
            total_tokens=5,
            provider=provider,
            model=model,
            request_id=request_id,
        ),
        provenance=provenance,
    )


def _payload_and_fingerprint(runtime, directive: ModelDirective) -> tuple[str, str]:
    return (
        encode_model_directive(directive),
        runtime.background_model_attempts._response_fingerprint(directive),
    )


def _stage(
    runtime,
    *,
    work_kind: str,
    work_id: str,
    model_round_index: int,
    directive: ModelDirective,
    staged_at: datetime = NOW + timedelta(minutes=2),
    evidence: str = "operator relay journal",
):
    payload, fingerprint = _payload_and_fingerprint(runtime, directive)
    return runtime.stage_exact_background_response(
        work_kind=work_kind,
        work_id=work_id,
        model_round_index=model_round_index,
        provider=directive.provenance.provider,
        model=directive.provenance.model,
        provider_request_id=directive.provenance.request_id,
        response_fingerprint=fingerprint,
        directive_payload=payload,
        staged_at=staged_at,
        evidence=evidence,
    )


def _wake_attempt(runtime, wake_id: str, round_index: int):
    return runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="wake",
        work_id=wake_id,
        model_round_index=round_index,
    )


def _must_not_call(*_args, **_kwargs):
    pytest.fail("the provider must never be re-dispatched for a recovered round")


def _seed_observation(store: SQLiteWorldStore) -> dict[str, object]:
    observation = Observation(
        object_id="obs_cbrr_anchor",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=2)),
        learned_at=NOW - timedelta(hours=2),
        recorded_at=NOW - timedelta(hours=2),
        created_by="test:core-background-response-recovery-001",
        source_kind="conversation",
        modality="text",
        value="A durable anchor fact for the attention-watch capability.",
        metadata={"dimension": "dim:cbrr"},
    )
    store.commit(
        [observation],
        OperationRequest(
            operation_name="test.cbrr.seed_observation",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed capability evidence",
            idempotency_key="cbrr:seed-observation",
            source_class=SourceClass.USER,
        ),
    )
    return {"object_id": "obs_cbrr_anchor", "revision": 1}


def _watch_call(anchor_ref: dict[str, object]) -> CapabilityCall:
    return CapabilityCall(
        name="create_attention_watch",
        arguments={
            "title": "cbrr watch",
            "dimensions": ["dim:cbrr"],
            "reason_refs": [anchor_ref],
            "source_kind": "conversation",
            "modality": "text",
            "priority": 40,
            "cooldown_seconds": 60,
        },
        call_id="call-watch",
    )


def _watch_tasks(store: SQLiteWorldStore) -> list[dict]:
    return [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.TASK,
            subject_id="user_1",
        )
        if payload.get("title") == "cbrr watch"
    ]


def _seed_review_fact(store: SQLiteWorldStore) -> None:
    fact = Observation(
        object_id="obs_cbrr_review_fact",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=1)),
        learned_at=NOW - timedelta(hours=1),
        recorded_at=NOW - timedelta(hours=1),
        created_by="test:core-background-response-recovery-001",
        source_kind="conversation",
        modality="text",
        value="A durable fact eligible for periodic review.",
        metadata={"dimension": "dim:cbrr"},
    )
    store.commit(
        [fact],
        OperationRequest(
            operation_name="test.cbrr.seed_review_fact",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed periodic review fact",
            idempotency_key="cbrr:seed-review-fact",
            source_class=SourceClass.USER,
        ),
    )


def _running_periodic_review_id(store: SQLiteWorldStore) -> str:
    running = [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.WAKE,
            subject_id="user_1",
        )
        if payload.get("wake_state") == "running"
        and payload.get("wake_source") == WakeSource.PERIODIC_REVIEW.value
    ]
    assert len(running) == 1
    return str(running[0]["object_id"])


def _crash_wake_into_in_doubt(tmp_path, *, key: str):
    """Return (db, signal, attempt_id, calls) after one ambiguous provider death."""

    store, index, db = _world(tmp_path)
    calls: list[int] = []

    def ambiguous(snapshot):
        calls.append(snapshot.round_index)
        raise TimeoutError("provider may already have accepted the request")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=ambiguous)
    signal = _emit_wake(runtime, key=key)
    with pytest.raises(TimeoutError, match="may already have accepted"):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)
    attempt = _wake_attempt(runtime, signal.wake_id, 0)
    assert attempt is not None
    assert attempt.state == "in_doubt"
    return store, index, db, runtime, signal, attempt.attempt_id, calls


# ---------------------------------------------------------------------------
# Case 1: crash after dispatch, exact response absent -> in_doubt, no retry
# ---------------------------------------------------------------------------


def test_case_01_crash_after_dispatch_without_exact_response_stays_in_doubt(tmp_path):
    store, index, db, runtime, signal, attempt_id, calls = _crash_wake_into_in_doubt(
        tmp_path, key="case-01"
    )
    assert calls == [0]
    assert runtime.background_model_attempts.staged_response(attempt_id) is None

    reopened_store, reopened_index = _reopen(db)
    restarted = FusedTurnRuntime(
        store=reopened_store,
        index=reopened_index,
        model_handler=_must_not_call,
    )
    with pytest.raises(BackgroundModelExecutionInDoubt) as blocked:
        restarted.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=5))
    assert blocked.value.attempt.attempt_id == attempt_id
    assert blocked.value.attempt.state == "in_doubt"
    assert calls == [0]
    assert (
        reopened_store.list_payloads(
            object_type=ObjectType.WAKE, subject_id="user_1"
        )[0]["wake_state"]
        == "running"
    )


# ---------------------------------------------------------------------------
# Case 2: exact response durably reconciled -> recovery provider call count = 0
# ---------------------------------------------------------------------------


def test_case_02_exact_response_recovery_never_redispatches_the_provider(tmp_path):
    store, index, db, runtime, signal, attempt_id, calls = _crash_wake_into_in_doubt(
        tmp_path, key="case-02"
    )
    staging = _stage(
        runtime,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
        directive=_directive("req-case-02"),
    )
    reconciled = runtime.background_model_attempts.get(attempt_id)
    assert reconciled.state == "response_returned"
    assert reconciled.provider == PROVIDER
    assert reconciled.model == MODEL
    assert reconciled.provider_request_id == "req-case-02"
    assert staging.response_fingerprint == reconciled.response_fingerprint

    restarted = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=_must_not_call,
    )
    result = restarted.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=3))

    assert result.wake.state == "completed"
    assert result.runtime.termination_reason == "silence"
    assert result.runtime.recovered_response_attempts == (attempt_id,)
    assert calls == [0]

    durable = restarted.background_model_attempts.get(attempt_id)
    assert durable.state == "metered"
    meter_rows = restarted.metering.list_model_calls(
        subject_id="user_1", wake_id=signal.wake_id
    )
    assert len(meter_rows) == 1
    assert meter_rows[0].background_attempt_id == attempt_id
    assert durable.meter_record_id == meter_rows[0].record_id


# ---------------------------------------------------------------------------
# Case 3: wrong fingerprint -> reject
# ---------------------------------------------------------------------------


def test_case_03_wrong_fingerprint_is_rejected_and_stays_fail_closed(tmp_path):
    store, index, db, runtime, signal, attempt_id, calls = _crash_wake_into_in_doubt(
        tmp_path, key="case-03"
    )
    payload, _fingerprint = _payload_and_fingerprint(runtime, _directive("req-case-03"))
    with pytest.raises(ValueError, match="fingerprint"):
        runtime.stage_exact_background_response(
            work_kind="wake",
            work_id=signal.wake_id,
            model_round_index=0,
            provider=PROVIDER,
            model=MODEL,
            provider_request_id="req-case-03",
            response_fingerprint="0" * 64,
            directive_payload=payload,
            staged_at=NOW + timedelta(minutes=2),
            evidence="wrong fingerprint must never be staged",
        )
    assert runtime.background_model_attempts.staged_response(attempt_id) is None
    assert runtime.background_model_attempts.get(attempt_id).state == "in_doubt"

    with pytest.raises(BackgroundModelExecutionInDoubt):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=4))
    assert calls == [0]


# ---------------------------------------------------------------------------
# Case 4: wrong provider / model / request_id -> reject
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,value",
    (
        ("provider", "other-provider"),
        ("model", "other-model"),
        ("provider_request_id", "other-request-id"),
    ),
)
def test_case_04_supplied_identity_must_match_the_exact_directive(tmp_path, field, value):
    store, index, db, runtime, signal, attempt_id, _calls = _crash_wake_into_in_doubt(
        tmp_path, key=f"case-04-{field}"
    )
    directive = _directive("req-case-04")
    payload, fingerprint = _payload_and_fingerprint(runtime, directive)
    supplied = {
        "provider": PROVIDER,
        "model": MODEL,
        "provider_request_id": "req-case-04",
    }
    supplied[field] = value
    with pytest.raises(ValueError, match="identity"):
        runtime.stage_exact_background_response(
            work_kind="wake",
            work_id=signal.wake_id,
            model_round_index=0,
            provider=supplied["provider"],
            model=supplied["model"],
            provider_request_id=supplied["provider_request_id"],
            response_fingerprint=fingerprint,
            directive_payload=payload,
            staged_at=NOW + timedelta(minutes=2),
            evidence="mismatched provider identity must never be staged",
        )
    assert runtime.background_model_attempts.staged_response(attempt_id) is None
    assert runtime.background_model_attempts.get(attempt_id).state == "in_doubt"


def test_case_04b_exact_response_requires_a_full_provider_identity(tmp_path):
    store, index, db, runtime, signal, attempt_id, _calls = _crash_wake_into_in_doubt(
        tmp_path, key="case-04b"
    )
    anonymous = ModelDirective(silence=True)
    payload, fingerprint = _payload_and_fingerprint(runtime, anonymous)
    with pytest.raises(ValueError, match="provider/model/request_id"):
        runtime.stage_exact_background_response(
            work_kind="wake",
            work_id=signal.wake_id,
            model_round_index=0,
            provider=PROVIDER,
            model=MODEL,
            provider_request_id="req-case-04b",
            response_fingerprint=fingerprint,
            directive_payload=payload,
            staged_at=NOW + timedelta(minutes=2),
            evidence="anonymous replies must never be staged",
        )
    assert runtime.background_model_attempts.staged_response(attempt_id) is None


def test_case_04c_staged_bytes_must_match_durable_attempt_provenance(
    tmp_path, monkeypatch
):
    store, index, db = _world(tmp_path)
    exact = _directive("req-case-04c")
    other = _directive("req-case-other")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: exact,
    )
    signal = _emit_wake(runtime, key="case-04c")

    def fail_meter(**_kwargs):
        raise RuntimeError("simulated crash before meter commit")

    monkeypatch.setattr(runtime.metering, "record_model_call", fail_meter)
    with pytest.raises(RuntimeError, match="before meter commit"):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)
    attempt = _wake_attempt(runtime, signal.wake_id, 0)
    assert attempt.state == "response_returned"
    assert attempt.provider_request_id == "req-case-04c"
    durable_fingerprint = attempt.response_fingerprint

    monkeypatch.undo()
    other_payload, other_fingerprint = _payload_and_fingerprint(runtime, other)
    with pytest.raises(BackgroundModelResponseConflict):
        runtime.stage_exact_background_response(
            work_kind="wake",
            work_id=signal.wake_id,
            model_round_index=0,
            provider=other.provenance.provider,
            model=other.provenance.model,
            provider_request_id=other.provenance.request_id,
            response_fingerprint=other_fingerprint,
            directive_payload=other_payload,
            staged_at=NOW + timedelta(minutes=2),
            evidence="different bytes must never overwrite durable provenance",
        )
    assert runtime.background_model_attempts.staged_response(attempt.attempt_id) is None

    # The same exact bytes that the runtime already fingerprinted are re-verifiable.
    exact_payload, exact_fingerprint = _payload_and_fingerprint(runtime, exact)
    assert exact_fingerprint == durable_fingerprint
    runtime.stage_exact_background_response(
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
        provider=PROVIDER,
        model=MODEL,
        provider_request_id="req-case-04c",
        response_fingerprint=exact_fingerprint,
        directive_payload=exact_payload,
        staged_at=NOW + timedelta(minutes=2),
        evidence="relay journal req-case-04c",
    )
    restarted = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=_must_not_call,
    )
    result = restarted.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=4))
    assert result.wake.state == "completed"
    assert result.runtime.recovered_response_attempts == (attempt.attempt_id,)
    assert (
        len(
            restarted.metering.list_model_calls(
                subject_id="user_1", wake_id=signal.wake_id
            )
        )
        == 1
    )


# ---------------------------------------------------------------------------
# Case 5: crash after response reconciliation, before application
# ---------------------------------------------------------------------------


def test_case_05_reconciled_response_survives_process_death_before_application(tmp_path):
    store, index, db, runtime, signal, attempt_id, calls = _crash_wake_into_in_doubt(
        tmp_path, key="case-05"
    )
    _stage(
        runtime,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
        directive=_directive("req-case-05"),
    )

    reopened_store, reopened_index = _reopen(db)
    restarted = FusedTurnRuntime(
        store=reopened_store,
        index=reopened_index,
        model_handler=_must_not_call,
    )
    inspection = restarted.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert inspection.state == "response_returned"

    result = restarted.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=6))
    assert result.wake.state == "completed"
    assert result.runtime.recovered_response_attempts == (attempt_id,)
    assert calls == [0]
    assert (
        len(
            restarted.metering.list_model_calls(
                subject_id="user_1", wake_id=signal.wake_id
            )
        )
        == 1
    )


def test_case_05b_response_recorded_before_meter_resumes_from_exact_bytes(
    tmp_path, monkeypatch
):
    store, index, db = _world(tmp_path)
    exact = _directive("req-case-05b")
    runtime = FusedTurnRuntime(
        store=store, index=index, model_handler=lambda _snapshot: exact
    )
    signal = _emit_wake(runtime, key="case-05b")

    def fail_meter(**_kwargs):
        raise RuntimeError("simulated crash before meter commit")

    monkeypatch.setattr(runtime.metering, "record_model_call", fail_meter)
    with pytest.raises(RuntimeError, match="before meter commit"):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)
    attempt = _wake_attempt(runtime, signal.wake_id, 0)
    assert attempt.state == "response_returned"

    monkeypatch.undo()
    _stage(
        runtime,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
        directive=exact,
    )
    reopened_store, reopened_index = _reopen(db)
    restarted = FusedTurnRuntime(
        store=reopened_store,
        index=reopened_index,
        model_handler=_must_not_call,
    )
    result = restarted.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=7))
    assert result.wake.state == "completed"
    assert result.runtime.recovered_response_attempts == (attempt.attempt_id,)
    durable = restarted.background_model_attempts.get(attempt.attempt_id)
    assert durable.state == "metered"
    assert (
        len(
            restarted.metering.list_model_calls(
                subject_id="user_1", wake_id=signal.wake_id
            )
        )
        == 1
    )


# ---------------------------------------------------------------------------
# Case 6: crash during capability application
# ---------------------------------------------------------------------------


def test_case_06_crash_during_capability_application_replays_exactly_once(tmp_path):
    store, index, db = _world(tmp_path)
    anchor = _seed_observation(store)
    index.catch_up()
    capability_directive = _directive(
        "req-case-06-r0",
        silence=False,
        capability_calls=(_watch_call(anchor),),
    )

    def scripted(snapshot):
        if snapshot.round_index == 0:
            return capability_directive
        raise AssertionError("the first process must die during capability application")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=scripted)
    signal = _emit_wake(runtime, key="case-06")

    real_spec = runtime.registry.get_spec("create_attention_watch")
    real_handler = runtime._create_attention_watch
    runtime.registry.unregister("create_attention_watch")

    def crash_after_commit(**kwargs):
        real_handler(**kwargs)
        raise _SimulatedCrash("simulated process death during capability application")

    runtime.registry.register(real_spec, crash_after_commit)

    with pytest.raises(_SimulatedCrash):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)

    attempt = _wake_attempt(runtime, signal.wake_id, 0)
    assert attempt is not None
    assert attempt.state == "metered"
    assert len(_watch_tasks(store)) == 1
    assert len(runtime.metering.list_model_calls(subject_id="user_1", wake_id=signal.wake_id)) == 1

    reopened_store, reopened_index = _reopen(db)
    calls: list[tuple[int, str | None]] = []

    def provider(snapshot):
        calls.append((snapshot.round_index, snapshot.model_attempt_id))
        return _directive("req-case-06-r1")

    restarted = FusedTurnRuntime(
        store=reopened_store,
        index=reopened_index,
        model_handler=provider,
    )
    _stage(
        restarted,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
        directive=capability_directive,
    )
    result = restarted.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=8))

    assert result.wake.state == "completed"
    assert result.runtime.termination_reason == "silence"
    assert result.runtime.recovered_response_attempts == (attempt.attempt_id,)
    # The recovered round never reached the provider; only the fresh next round did.
    assert len(calls) == 1
    assert calls[0][0] == 1
    assert calls[0][1] != attempt.attempt_id

    tasks = _watch_tasks(reopened_store)
    assert len(tasks) == 1
    assert int(tasks[0]["revision"]) == 1
    meter_rows = restarted.metering.list_model_calls(
        subject_id="user_1", wake_id=signal.wake_id
    )
    assert [row.model_round_index for row in meter_rows] == [0, 1]
    assert restarted.background_model_attempts.get(attempt.attempt_id).state == "metered"


# ---------------------------------------------------------------------------
# Case 7: crash after capability result, before the next model round
# ---------------------------------------------------------------------------


def test_case_07_crash_after_capability_before_next_round_resumes_only_that_round(tmp_path):
    store, index, db = _world(tmp_path)
    anchor = _seed_observation(store)
    index.catch_up()
    capability_directive = _directive(
        "req-case-07-r0",
        silence=False,
        capability_calls=(_watch_call(anchor),),
    )

    def scripted(snapshot):
        if snapshot.round_index == 0:
            return capability_directive
        raise TimeoutError("round 1 died after provider dispatch")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=scripted)
    signal = _emit_wake(runtime, key="case-07")
    with pytest.raises(TimeoutError, match="round 1 died"):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)

    round_0 = _wake_attempt(runtime, signal.wake_id, 0)
    round_1 = _wake_attempt(runtime, signal.wake_id, 1)
    assert round_0.state == "metered"
    assert round_1 is not None and round_1.state == "in_doubt"
    assert len(_watch_tasks(store)) == 1

    reopened_store, reopened_index = _reopen(db)
    restarted = FusedTurnRuntime(
        store=reopened_store,
        index=reopened_index,
        model_handler=_must_not_call,
    )
    _stage(
        restarted,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=1,
        directive=_directive("req-case-07-r1"),
    )
    result = restarted.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=9))

    assert result.wake.state == "completed"
    assert result.runtime.recovered_response_attempts == (round_1.attempt_id,)
    # Round 0 was already applied before the crash and must not be replayed.
    assert len(_watch_tasks(reopened_store)) == 1
    rounds = [
        row.model_round_index
        for row in restarted.metering.list_model_calls(
            subject_id="user_1", wake_id=signal.wake_id
        )
    ]
    assert rounds == [0, 1]
    assert restarted.background_model_attempts.get(round_1.attempt_id).state == "metered"


# ---------------------------------------------------------------------------
# Case 8: crash after terminal response / silence, before the completion marker
# ---------------------------------------------------------------------------


def test_case_08_crash_after_terminal_silence_before_completion_marker(
    tmp_path, monkeypatch
):
    store, index, db = _world(tmp_path)
    exact = _directive("req-case-08")
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: exact)
    signal = _emit_wake(runtime, key="case-08")

    monkeypatch.setattr(
        runtime.wake_bus,
        "complete",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            _SimulatedCrash("simulated process death before Wake completion marker")
        ),
    )
    with pytest.raises(_SimulatedCrash):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)

    attempt = _wake_attempt(runtime, signal.wake_id, 0)
    assert attempt is not None
    assert attempt.state == "metered"
    assert runtime.wake_bus.current_wake(signal.wake_id).wake_state.value == "running"
    assert len(runtime.metering.list_model_calls(subject_id="user_1", wake_id=signal.wake_id)) == 1

    monkeypatch.undo()
    reopened_store, reopened_index = _reopen(db)
    restarted = FusedTurnRuntime(
        store=reopened_store,
        index=reopened_index,
        model_handler=_must_not_call,
    )
    _stage(
        restarted,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
        directive=exact,
    )
    result = restarted.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=10))

    assert result.wake.state == "completed"
    assert result.runtime.termination_reason == "silence"
    assert result.runtime.recovered_response_attempts == (attempt.attempt_id,)
    meter_rows = restarted.metering.list_model_calls(
        subject_id="user_1", wake_id=signal.wake_id
    )
    assert len(meter_rows) == 1
    assert meter_rows[0].background_attempt_id == attempt.attempt_id


# ---------------------------------------------------------------------------
# Case 9: repeated recovery -> no duplicate capability / output / metering
# ---------------------------------------------------------------------------


def test_case_09_repeated_recovery_never_duplicates_state(tmp_path):
    store, index, db, runtime, signal, attempt_id, calls = _crash_wake_into_in_doubt(
        tmp_path, key="case-09"
    )
    exact = _directive("req-case-09")
    _stage(
        runtime,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
        directive=exact,
    )
    restarted = FusedTurnRuntime(store=store, index=index, model_handler=_must_not_call)
    first = restarted.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=11))
    assert first.wake.state == "completed"

    # Re-staging identical exact bytes is idempotent; different bytes conflict.
    again = _stage(
        restarted,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
        directive=exact,
    )
    assert again.attempt_id == attempt_id
    other = _directive("req-case-09-other")
    other_payload, other_fingerprint = _payload_and_fingerprint(restarted, other)
    with pytest.raises(BackgroundModelResponseConflict):
        restarted.background_model_attempts.stage_exact_response(
            attempt_id,
            staged_at=NOW + timedelta(minutes=12),
            provider=PROVIDER,
            model=MODEL,
            provider_request_id="req-case-09-other",
            response_fingerprint=other_fingerprint,
            directive_payload=other_payload,
            evidence="conflicting replay must be refused",
        )

    with pytest.raises(ValueError, match="NEW/QUEUED/RUNNING"):
        restarted.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=13))

    assert calls == [0]
    assert restarted.background_model_attempts.get(attempt_id).state == "metered"
    assert (
        len(
            restarted.metering.list_model_calls(
                subject_id="user_1", wake_id=signal.wake_id
            )
        )
        == 1
    )


def test_metered_attempt_without_exact_bytes_stays_blocked(tmp_path, monkeypatch):
    """The pre-existing ambiguous no-exact-response protection is unchanged."""

    store, index, db = _world(tmp_path)
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: _directive("req-metered-no-bytes"),
    )
    signal = _emit_wake(runtime, key="metered-no-bytes")
    monkeypatch.setattr(
        runtime.wake_bus,
        "complete",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("crash")),
    )
    with pytest.raises(RuntimeError, match="crash"):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)
    attempt = _wake_attempt(runtime, signal.wake_id, 0)
    assert attempt.state == "metered"

    reopened_store, reopened_index = _reopen(db)
    restarted = FusedTurnRuntime(
        store=reopened_store,
        index=reopened_index,
        model_handler=_must_not_call,
    )
    with pytest.raises(BackgroundModelAttemptBlocked) as blocked:
        restarted.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=14))
    assert blocked.value.attempt.attempt_id == attempt.attempt_id
    assert blocked.value.attempt.recovery_disposition == "metered"


def test_no_exact_response_can_be_staged_for_a_call_that_never_reached_provider(
    tmp_path, monkeypatch
):
    """Staging is refused where the attempt proves the provider boundary was not
    crossed, so no operator-supplied reply can turn a safe retry into a lie."""

    # (a) crash before dispatch: durable attempt is still `admitted`.
    store, index, db = _world(tmp_path, name="admitted.db")
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=_must_not_call)
    signal = _emit_wake(runtime, key="never-dispatched")

    def crash_before_dispatch(_attempt_id, *, dispatched_at):
        raise RuntimeError("simulated crash before provider dispatch")

    monkeypatch.setattr(
        runtime.background_model_attempts, "mark_dispatching", crash_before_dispatch
    )
    with pytest.raises(RuntimeError, match="before provider dispatch"):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)
    admitted = _wake_attempt(runtime, signal.wake_id, 0)
    assert admitted.state == "admitted"
    assert admitted.recovery_disposition == "safe_to_retry"

    monkeypatch.undo()
    with pytest.raises(BackgroundModelResponseConflict, match="provider boundary"):
        _stage(
            runtime,
            work_kind="wake",
            work_id=signal.wake_id,
            model_round_index=0,
            directive=_directive("req-never-dispatched"),
        )
    assert runtime.background_model_attempts.staged_response(admitted.attempt_id) is None

    # (b) definitely-not-submitted dispatch failure keeps the same refusal.
    store2, index2, db2 = _world(tmp_path, name="not-submitted.db")

    def not_submitted(_snapshot):
        raise ModelDispatchNotSubmitted("socket failed before request write")

    runtime2 = FusedTurnRuntime(store=store2, index=index2, model_handler=not_submitted)
    signal2 = _emit_wake(runtime2, key="never-submitted")
    with pytest.raises(ModelDispatchNotSubmitted):
        runtime2.run_wake(wake_ref=_wake_ref(signal2), now=NOW)
    refused = _wake_attempt(runtime2, signal2.wake_id, 0)
    assert refused.state == "not_submitted"
    assert refused.recovery_disposition == "safe_to_retry"
    with pytest.raises(BackgroundModelResponseConflict, match="provider boundary"):
        _stage(
            runtime2,
            work_kind="wake",
            work_id=signal2.wake_id,
            model_round_index=0,
            directive=_directive("req-never-submitted"),
        )
    assert runtime2.background_model_attempts.staged_response(refused.attempt_id) is None


@pytest.mark.parametrize(
    "payload",
    (
        "not json at all",
        '{"response": "x", "silence": true}',
        '{"capability_calls": [], "response": null, "silence": true, "usage": null,'
        ' "provenance": null, "unexpected": 1}',
        '{"capability_calls": [], "response": "x", "silence": true, "usage": null,'
        ' "provenance": null}',
        '{"capability_calls": [], "response": null, "silence": false, "usage": null,'
        ' "provenance": null}',
    ),
)
def test_malformed_exact_payloads_are_rejected_without_defaults(tmp_path, payload):
    """Strict decode: no extra fields, no missing fields, no defaults, no fallback."""

    store, index, db, runtime, signal, attempt_id, _calls = _crash_wake_into_in_doubt(
        tmp_path, key="malformed"
    )
    with pytest.raises(ValueError):
        runtime.stage_exact_background_response(
            work_kind="wake",
            work_id=signal.wake_id,
            model_round_index=0,
            provider=PROVIDER,
            model=MODEL,
            provider_request_id="req-malformed",
            response_fingerprint="0" * 64,
            directive_payload=payload,
            staged_at=NOW + timedelta(minutes=2),
            evidence="malformed bytes must never be staged",
        )
    assert runtime.background_model_attempts.staged_response(attempt_id) is None
    assert runtime.background_model_attempts.get(attempt_id).state == "in_doubt"


def test_tampered_staged_bytes_fail_closed_before_application(tmp_path):
    """A locally altered staged payload can never reach the application path."""

    store, index, db, runtime, signal, attempt_id, calls = _crash_wake_into_in_doubt(
        tmp_path, key="tampered-bytes"
    )
    _stage(
        runtime,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
        directive=_directive("req-tampered"),
    )
    with store._connection() as conn:
        conn.execute(
            """
            UPDATE background_model_responses
            SET directive_payload=?
            WHERE attempt_id=?
            """,
            (
                encode_model_directive(_directive("req-tampered-other")),
                attempt_id,
            ),
        )
        conn.commit()

    reopened_store, reopened_index = _reopen(db)
    restarted = FusedTurnRuntime(
        store=reopened_store,
        index=reopened_index,
        model_handler=_must_not_call,
    )
    with pytest.raises(BackgroundModelResponseConflict, match="payload hash"):
        restarted.run_wake(wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=16))
    assert calls == [0]
    assert restarted.background_model_attempts.get(attempt_id).state == "response_returned"


# ---------------------------------------------------------------------------
# Periodic review recovery (same mechanism, review work kind)
# ---------------------------------------------------------------------------


def test_periodic_review_exact_response_recovery_is_zero_provider_call(tmp_path):
    store, index, db = _world(tmp_path)
    _seed_review_fact(store)
    index.catch_up()
    calls: list[int] = []

    def ambiguous(_snapshot):
        calls.append(0)
        raise TimeoutError("review provider may already have accepted the request")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=ambiguous)
    with pytest.raises(TimeoutError, match="may already have accepted"):
        runtime.run_periodic_review(now=NOW)
    wake_id = _running_periodic_review_id(store)
    attempt = runtime.background_model_attempts.inspect(
        subject_id="user_1",
        work_kind="periodic_review",
        work_id=wake_id,
        model_round_index=0,
    )
    assert attempt is not None
    assert attempt.state == "in_doubt"

    reopened_store, reopened_index = _reopen(db)
    restarted = FusedTurnRuntime(
        store=reopened_store,
        index=reopened_index,
        model_handler=_must_not_call,
    )
    _stage(
        restarted,
        work_kind="periodic_review",
        work_id=wake_id,
        model_round_index=0,
        directive=_directive("req-review-recovery"),
    )
    result = restarted.run_periodic_review(now=NOW + timedelta(minutes=15))

    assert result.wake.state == "completed"
    assert result.runtime.recovered_response_attempts == (attempt.attempt_id,)
    assert calls == [0]
    assert restarted.background_model_attempts.get(attempt.attempt_id).state == "metered"


# ---------------------------------------------------------------------------
# User-turn recovery (same mechanism, user_turn work kind)
# ---------------------------------------------------------------------------


def test_user_turn_exact_response_recovery_is_exactly_once(tmp_path):
    store, index, db = _world(tmp_path)
    calls: list[int] = []

    def ambiguous(snapshot):
        calls.append(snapshot.round_index)
        raise TimeoutError("turn provider may already have accepted the request")

    first = FusedTurnRuntime(store=store, index=index, model_handler=ambiguous)
    turn = dict(
        session_id="cbrr-session",
        turn_index=1,
        user_input="SYNTHETIC cbrr user turn",
        occurred_at=NOW,
    )
    with pytest.raises(TimeoutError, match="may already have accepted"):
        first.run_turn(**turn)

    inspection = first.inspect_turn_execution(**turn)
    assert inspection.state == "started"
    assert inspection.recovery_disposition == "in_doubt"
    assert [attempt.state for attempt in inspection.model_attempts] == ["in_doubt"]
    attempt_id = inspection.model_attempts[0].attempt_id

    # Ordinary retry stays refused: no exact bytes were staged yet.
    with pytest.raises(TurnExecutionInDoubt):
        first.run_turn(**turn)
    assert calls == [0]

    reopened_store, reopened_index = _reopen(db)
    restarted = FusedTurnRuntime(
        store=reopened_store,
        index=reopened_index,
        model_handler=_must_not_call,
    )
    exact = _directive(
        "req-turn-recovery",
        silence=False,
        response="Exact staged reply for the synthetic turn.",
    )
    _stage(
        restarted,
        work_kind="user_turn",
        work_id=inspection.execution_id,
        model_round_index=0,
        directive=exact,
    )
    ready = restarted.inspect_turn_execution(**turn)
    assert ready.recovery_disposition == "exact_response_ready"

    result = restarted.run_turn(**turn)
    assert result.runtime.response == exact.response
    assert result.runtime.recovered_response_attempts == (attempt_id,)
    assert calls == [0]
    assert restarted.inspect_turn_execution(**turn).state == "completed"

    outputs = [
        payload
        for payload in reopened_store.list_payloads(
            object_type=ObjectType.OBSERVATION, subject_id="user_1"
        )
        if (payload.get("metadata") or {}).get("role") == "assistant"
    ]
    assert [payload["value"] for payload in outputs] == [exact.response]
    meter_rows = restarted.metering.list_model_calls(
        subject_id="user_1", execution_classes=("user_interaction",)
    )
    assert len(meter_rows) == 1
    assert meter_rows[0].background_attempt_id == attempt_id

    with pytest.raises(TurnAlreadyCompleted):
        restarted.run_turn(**turn)
    assert calls == [0]
    outputs_after = [
        payload
        for payload in reopened_store.list_payloads(
            object_type=ObjectType.OBSERVATION, subject_id="user_1"
        )
        if (payload.get("metadata") or {}).get("role") == "assistant"
    ]
    assert len(outputs_after) == 1
    assert (
        len(
            restarted.metering.list_model_calls(
                subject_id="user_1", execution_classes=("user_interaction",)
            )
        )
        == 1
    )


# ---------------------------------------------------------------------------
# Case 10: normal path + not_submitted retry regression
# ---------------------------------------------------------------------------


def test_case_10_normal_path_and_not_submitted_retry_regression(tmp_path):
    store, index, db = _world(tmp_path)
    calls: list[str | None] = []

    def provider(snapshot):
        calls.append(snapshot.model_attempt_id)
        return _directive("req-normal-wake")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=provider)
    signal = _emit_wake(runtime, key="case-10-normal")
    result = runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)
    assert result.wake.state == "completed"
    assert result.runtime.recovered_response_attempts == ()
    assert len(calls) == 1
    normal_attempt = _wake_attempt(runtime, signal.wake_id, 0)
    assert normal_attempt.state == "metered"
    assert normal_attempt.attempt_id == calls[0]
    assert runtime.background_model_attempts.staged_response(normal_attempt.attempt_id) is None
    assert len(runtime.metering.list_model_calls(subject_id="user_1", wake_id=signal.wake_id)) == 1

    # not_submitted keeps its safe-retry semantics on the same attempt identity.
    store2, index2, db2 = _world(tmp_path, name="retry.db")
    retry_calls: list[str | None] = []

    def flaky(snapshot):
        retry_calls.append(snapshot.model_attempt_id)
        if len(retry_calls) == 1:
            raise ModelDispatchNotSubmitted("socket failed before request write")
        return _directive("req-retry-after-not-submitted")

    retry_runtime = FusedTurnRuntime(store=store2, index=index2, model_handler=flaky)
    retry_signal = _emit_wake(retry_runtime, key="case-10-retry")
    with pytest.raises(ModelDispatchNotSubmitted):
        retry_runtime.run_wake(wake_ref=_wake_ref(retry_signal), now=NOW)
    not_submitted = _wake_attempt(retry_runtime, retry_signal.wake_id, 0)
    assert not_submitted.state == "not_submitted"
    assert not_submitted.recovery_disposition == "safe_to_retry"

    retried = retry_runtime.run_wake(
        wake_ref=_wake_ref(retry_signal), now=NOW + timedelta(minutes=1)
    )
    assert retried.wake.state == "completed"
    assert retried.runtime.recovered_response_attempts == ()
    assert retry_calls == [not_submitted.attempt_id, not_submitted.attempt_id]
    assert retry_runtime.background_model_attempts.get(not_submitted.attempt_id).state == "metered"
    assert (
        len(
            retry_runtime.metering.list_model_calls(
                subject_id="user_1", wake_id=retry_signal.wake_id
            )
        )
        == 1
    )

    # Normal user turn and normal periodic review are unchanged.
    store3, index3, db3 = _world(tmp_path, name="turn.db")
    turn_calls: list[str | None] = []

    def turn_provider(snapshot):
        turn_calls.append(snapshot.model_attempt_id)
        return _directive(
            "req-normal-turn",
            silence=False,
            response="Normal synthetic reply.",
        )

    turn_runtime = FusedTurnRuntime(store=store3, index=index3, model_handler=turn_provider)
    turn = dict(
        session_id="cbrr-normal-session",
        turn_index=1,
        user_input="SYNTHETIC normal cbrr turn",
        occurred_at=NOW,
    )
    turn_result = turn_runtime.run_turn(**turn)
    assert turn_result.runtime.response == "Normal synthetic reply."
    assert turn_result.runtime.recovered_response_attempts == ()
    assert len(turn_calls) == 1
    assert turn_runtime.inspect_turn_execution(**turn).state == "completed"

    store4, index4, db4 = _world(tmp_path, name="review.db")
    _seed_review_fact(store4)
    index4.catch_up()
    review_calls: list[str | None] = []

    def review_provider(snapshot):
        review_calls.append(snapshot.model_attempt_id)
        return _directive("req-normal-review")

    review_runtime = FusedTurnRuntime(
        store=store4, index=index4, model_handler=review_provider
    )
    review_result = review_runtime.run_periodic_review(now=NOW)
    assert review_result.wake.state == "completed"
    assert len(review_calls) == 1
    assert (
        review_runtime.background_model_attempts.get(review_calls[0]).state == "metered"
    )
    assert not review_runtime.background_model_attempts.staged_response(review_calls[0])
