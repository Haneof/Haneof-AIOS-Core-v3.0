"""Frozen Core RED: later-round trusted callback must hand off exact bytes durably.

The recovery caller supplies no directive, proof, fingerprint or signing capability.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import sqlite3

import pytest

from aios_core.contracts.enums import ObjectType, SourceClass
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import ModelCallProvenance, ModelDirective, ModelUsage, TurnAlreadyCompleted
from aios_core.runtime.background_attempt import BackgroundModelResponseConflict
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 9, 28, 6, tzinfo=timezone.utc)


class ProcessDeath(BaseException):
    pass


def world(db):
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def directive(round_index, *, call=None):
    request_id = f"trusted-provider-request-{round_index}"
    return ModelDirective(
        response="finished once" if call is None else None,
        capability_calls=() if call is None else (call,),
        usage=ModelUsage(input_tokens=4, output_tokens=2, total_tokens=6,
                         provider="trusted-provider", model="trusted-model", request_id=request_id),
        provenance=ModelCallProvenance(provider="trusted-provider", model="trusted-model", request_id=request_id),
    )


def seed_anchor(store):
    anchor = Observation(
        object_id="trusted_return_anchor", subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=2)),
        learned_at=NOW - timedelta(hours=2), recorded_at=NOW - timedelta(hours=2),
        created_by="test:trusted-return", source_kind="conversation", modality="text",
        value="A durable anchor for trusted return", metadata={"dimension": "dim:trusted"},
    )
    store.commit([anchor], OperationRequest(
        operation_name="test.trusted_return.seed",
        expected_world_revision=int(store.current_world_revision()),
        reason="seed anchor", idempotency_key="trusted-return-anchor", source_class=SourceClass.USER,
    ))


def watch_call(round_index):
    return CapabilityCall(
        name="create_attention_watch", call_id=f"trusted-watch-{round_index}",
        arguments={"title": f"trusted watch {round_index}", "dimensions": ["dim:trusted"],
                   "reason_refs": [{"object_id": "trusted_return_anchor", "revision": 1}],
                   "source_kind": "conversation", "modality": "text", "priority": 40,
                   "cooldown_seconds": 60},
    )


def crash_at_return(tmp_path, last_round):
    db = tmp_path / "world.db"
    store, index = world(db)
    seed_anchor(store)
    index.catch_up()
    calls = []

    def provider(snapshot):
        calls.append(snapshot.round_index)
        return directive(snapshot.round_index, call=watch_call(snapshot.round_index) if snapshot.round_index < last_round else None)

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=provider)
    original = runtime.cognitive_runtime.model_response_recorder

    def stop_after_handoff(snapshot, returned):
        if snapshot.round_index == last_round:
            raise ProcessDeath("crash before response provenance / semantic application")
        original(snapshot, returned)

    runtime.cognitive_runtime.model_response_recorder = stop_after_handoff
    with pytest.raises(ProcessDeath):
        runtime.run_turn(session_id="trusted-session", turn_index=1,
                         user_input="complete exactly once", occurred_at=NOW)
    execution_id = runtime.turn_executions.execution_id_for(
        subject_id="user_1", session_id="trusted-session", turn_index=1)
    attempts = runtime.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind="user_turn", work_id=execution_id)
    assert calls == list(range(last_round + 1))
    assert [a.model_round_index for a in attempts] == list(range(last_round + 1))
    assert [a.state for a in attempts] == ["metered"] * last_round + ["dispatching"]
    assert runtime.background_model_attempts.staged_response(attempts[-1].attempt_id) is None
    receipt = runtime.background_model_attempts.response_authenticity_receipt(attempts[-1].attempt_id)
    assert receipt is not None
    return db, runtime, attempts, receipt, execution_id


@pytest.mark.parametrize("last_round", [1, 2])
def test_later_round_return_survives_process_loss_without_caller_supplied_reply(tmp_path, last_round):
    db, before, attempts, receipt, execution_id = crash_at_return(tmp_path, last_round)
    store, index = world(db)
    provider_calls = []

    def forbidden(snapshot):
        provider_calls.append(snapshot.round_index)
        pytest.fail("provider must not be redispatched")

    fresh = FusedTurnRuntime(store=store, index=index, model_handler=forbidden)
    result = fresh.run_turn(session_id="trusted-session", turn_index=1,
                            user_input="complete exactly once", occurred_at=NOW)
    assert result.runtime.response == "finished once"
    assert result.runtime.recovered_response_attempts == (attempts[-1].attempt_id,)
    assert provider_calls == []
    after = fresh.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind="user_turn", work_id=execution_id)
    assert [a.attempt_id for a in after] == [a.attempt_id for a in attempts]
    assert [a.state for a in after] == ["metered"] * (last_round + 1)
    binding = fresh.background_model_attempts.outbound_request_binding(attempts[-1].attempt_id)
    assert binding is not None
    assert receipt.outbound_request_fingerprint == binding.outbound_request_fingerprint
    assert receipt.relay_id == binding.relay_id
    assert fresh.background_model_attempts.response_authenticity_receipt(attempts[-1].attempt_id) == receipt
    staged = fresh.background_model_attempts.staged_response(attempts[-1].attempt_id)
    assert staged is not None and staged.authenticity_proof == receipt.authenticity_proof
    assert fresh.background_model_attempts.exact_response_directive(attempts[-1].attempt_id).response == "finished once"
    meters = fresh.metering.list_model_calls(subject_id="user_1", session_id="trusted-session")
    assert len(meters) == last_round + 1
    assert [m.background_attempt_id for m in meters] == [a.attempt_id for a in attempts]
    tasks = [p for p in store.list_payloads(object_type=ObjectType.TASK, subject_id="user_1")
             if str(p.get("title", "")).startswith("trusted watch")]
    assert len(tasks) == last_round
    assert all(p["revision"] == 1 for p in tasks)
    status = fresh.inspect_turn_execution(session_id="trusted-session", turn_index=1,
                                          user_input="complete exactly once", occurred_at=NOW)
    assert status.state == "completed" and status.recovery_disposition == "completed"
    with pytest.raises(TurnAlreadyCompleted):
        fresh.run_turn(session_id="trusted-session", turn_index=1,
                       user_input="complete exactly once", occurred_at=NOW)
    assert len(fresh.metering.list_model_calls(subject_id="user_1", session_id="trusted-session")) == last_round + 1


def test_trusted_callback_atomically_hands_off_exact_bytes_before_any_downstream_effect(tmp_path):
    db, runtime, attempts, receipt, _ = crash_at_return(tmp_path, 1)
    # The callback must have committed both the receipt and exact payload, even
    # though the ordinary response recorder and metering never ran for round 1.
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT directive_payload, payload_sha256, authenticity_proof FROM background_model_return_handoffs WHERE attempt_id=?",
            (attempts[-1].attempt_id,),
        ).fetchone()
    assert row is not None
    assert hashlib.sha256(row[0].encode()).hexdigest() == row[1] == receipt.payload_sha256
    assert row[2] == receipt.authenticity_proof
    assert len(runtime.metering.list_model_calls(subject_id="user_1", session_id="trusted-session")) == 1
