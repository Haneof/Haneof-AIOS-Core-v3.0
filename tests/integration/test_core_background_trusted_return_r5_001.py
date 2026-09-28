"""R5-A/B/C/D: exactly-once *durable effects*, not zero callback re-entry.

The normal trusted return callback is the only receipt mint. Crash hooks live after
metering, before/after the real side-effecting capability, and after terminal output.
No recovery test calls the receipt signer or supplies a replacement directive.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import hashlib
import sqlite3

import pytest

from aios_core.contracts.enums import ObjectType, WakeSource
from aios_core.contracts.refs import ObjectRef
from aios_core.runtime import TurnAlreadyCompleted, TurnInputConflict
from aios_core.runtime.background_attempt import BackgroundModelResponseConflict, encode_model_directive
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.wake import WakeSignalRequest
from test_core_background_trusted_return_recovery_001 import (
    NOW, directive, seed_anchor, watch_call, world,
)


class ProcessDeath(BaseException):
    """Escape capability registry's ordinary Exception-to-result conversion."""


def new_runtime(db, handler):
    store, index = world(db)
    return FusedTurnRuntime(store=store, index=index, model_handler=handler)


def execute(runtime, kind, work_id=None, *, now=NOW):
    if kind == "user_turn":
        return runtime.run_turn(session_id="r5-session", turn_index=1,
                                user_input="R5 exact replay", occurred_at=NOW)
    if kind == "wake":
        assert work_id is not None
        return runtime.run_wake(wake_ref=ObjectRef(object_id=work_id, revision=1), now=now)
    assert kind == "periodic_review"
    return runtime.run_periodic_review(now=now)


def start(runtime, kind):
    if kind == "wake":
        signal = runtime.wake_bus.emit(WakeSignalRequest(
            wake_source=WakeSource.SAFETY, rule_id="r5.exact", observed_at=NOW,
            dedupe_key="r5.exact:one"))
        return signal.wake_id
    if kind == "user_turn":
        return runtime.turn_executions.execution_id_for(
            subject_id=runtime.subject_id, session_id="r5-session", turn_index=1)
    assert kind == "periodic_review"
    return None  # Core owns Review Wake admission; discover its attempt afterward.


def scope(runtime, kind, work_id=None):
    if kind == "periodic_review" and work_id is None:
        wakes = [p for p in runtime.store.list_payloads(
            object_type=ObjectType.WAKE, subject_id=runtime.subject_id)
                 if p.get("wake_source") == WakeSource.PERIODIC_REVIEW.value]
        assert len(wakes) == 1
        work_id = str(wakes[0]["object_id"])
    assert work_id is not None
    return work_id


def evidence(runtime, kind, work_id, round_index=0):
    attempt = runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id, work_kind=kind,
        work_id=work_id, model_round_index=round_index)
    assert attempt is not None
    binding = runtime.background_model_attempts.outbound_request_binding(attempt.attempt_id)
    receipt = runtime.background_model_attempts.response_authenticity_receipt(attempt.attempt_id)
    assert binding is not None and receipt is not None
    assert (binding.subject_id, binding.work_kind, binding.work_id,
            binding.model_round_index) == (runtime.subject_id, kind, work_id, round_index)
    assert (receipt.attempt_id, receipt.subject_id, receipt.work_kind,
            receipt.work_id, receipt.model_round_index,
            receipt.outbound_request_fingerprint, receipt.relay_id) == (
                attempt.attempt_id, runtime.subject_id, kind, work_id, round_index,
                binding.outbound_request_fingerprint, binding.relay_id)
    assert (receipt.provider, receipt.model, receipt.provider_request_id,
            receipt.response_fingerprint) == (
                attempt.provider, attempt.model, attempt.provider_request_id,
                attempt.response_fingerprint)
    with sqlite3.connect(runtime.store.db_path) as conn:
        handoff = conn.execute(
            "SELECT directive_payload,payload_sha256,authenticity_proof "
            "FROM background_model_return_handoffs WHERE attempt_id=?",
            (attempt.attempt_id,)).fetchone()
    assert handoff is not None
    assert hashlib.sha256(handoff[0].encode()).hexdigest() == handoff[1] == receipt.payload_sha256
    assert handoff[2] == receipt.authenticity_proof
    meters = [m for m in runtime.metering.list_model_calls(subject_id=runtime.subject_id)
              if m.background_attempt_id == attempt.attempt_id]
    assert len(meters) == 1
    assert attempt.state == "metered" and attempt.meter_record_id == meters[0].record_id
    assert (meters[0].model_round_index, meters[0].provider_request_id) == (
        round_index, receipt.provider_request_id)
    return attempt, binding, receipt, handoff, meters[0]


def task_rows(store):
    return [p for p in store.list_payloads(object_type=ObjectType.TASK, subject_id="user_1")
            if p.get("title") == "trusted watch 0"]


def task_operation(db, task_id):
    key = f"task-create:{task_id}:1"
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT o.operation_id,o.idempotency_key,i.world_revision "
            "FROM operations AS o JOIN idempotency_records AS i "
            "ON i.operation_id=o.operation_id WHERE o.idempotency_key=?", (key,)).fetchall()
    assert len(rows) == 1 and rows[0][1] == key
    return rows[0]


def assert_same_evidence(before, after):
    old_attempt, old_binding, old_receipt, old_handoff, old_meter = before
    attempt, binding, receipt, handoff, meter = after
    assert attempt.attempt_id == old_attempt.attempt_id
    assert attempt.model_round_index == old_attempt.model_round_index
    assert binding == old_binding
    assert receipt == old_receipt
    assert handoff == old_handoff
    assert meter == old_meter
    assert attempt.meter_record_id == old_attempt.meter_record_id


@pytest.mark.parametrize("kind", ["user_turn", "wake", "periodic_review"])
def test_r5_a_metered_final_no_terminal_ack_exactly_once(tmp_path, kind, monkeypatch):
    db = tmp_path / "world.db"
    initial = new_runtime(db, lambda _: directive(0))
    if kind == "periodic_review":
        seed_anchor(initial.store)
        initial.index.catch_up()
    work_id = start(initial, kind)
    if kind == "user_turn":
        monkeypatch.setattr(initial.ingestor, "commit_assistant_output",
                            lambda **_: (_ for _ in ()).throw(ProcessDeath()))
    elif kind == "wake":
        monkeypatch.setattr(initial.ingestor, "commit_assistant_delivery",
                            lambda **_: (_ for _ in ()).throw(ProcessDeath()))
    else:
        monkeypatch.setattr(initial.periodic_review, "complete_review",
                            lambda *_, **__: (_ for _ in ()).throw(ProcessDeath()))
    with pytest.raises(ProcessDeath):
        execute(initial, kind, work_id)
    work_id = scope(initial, kind, work_id)
    before = evidence(initial, kind, work_id)
    rev_before = int(initial.store.current_world_revision())
    if kind == "wake":
        assert initial.ingestor.assistant_delivery_payload(work_id) is None
        wake_before = initial.wake_bus.current_wake(work_id)
        assert wake_before.wake_state.value == "running"
    elif kind == "user_turn":
        status = initial.inspect_turn_execution(session_id="r5-session", turn_index=1,
            user_input="R5 exact replay", occurred_at=NOW)
        assert status.assistant_ref is None and status.execution_id == work_id
    else:
        assert initial.store.get_payload(work_id)["wake_state"] == "running"
    assert task_rows(initial.store) == []

    calls = []
    fresh = new_runtime(db, lambda snapshot: calls.append(snapshot.round_index) or
                        pytest.fail("metered final provider was redispatched"))
    result = execute(fresh, kind, work_id, now=NOW + timedelta(minutes=1))
    assert calls == []
    assert_same_evidence(before, evidence(fresh, kind, work_id))
    assert task_rows(fresh.store) == []
    if kind == "user_turn":
        status = fresh.inspect_turn_execution(session_id="r5-session", turn_index=1,
            user_input="R5 exact replay", occurred_at=NOW)
        assert status.execution_id == work_id and status.state == "completed"
        assert status.assistant_ref == ObjectRef(
            object_id=result.conversation_commit.assistant_observation_id, revision=1)
        assert fresh.store.get_payload(status.assistant_ref.object_id)["value"] == "finished once"
        assert len([p for p in fresh.store.list_payloads(
            object_type=ObjectType.OBSERVATION, subject_id="user_1")
            if p.get("object_id") == status.assistant_ref.object_id]) == 1
        with pytest.raises(TurnAlreadyCompleted):
            execute(new_runtime(db, lambda _: pytest.fail("no provider")), kind)
    else:
        assert result.wake.wake_id == work_id and result.wake.state == "completed"
        assert result.wake.revision == int(fresh.store.get_payload(work_id)["revision"])
        if kind == "wake":
            delivery = fresh.ingestor.assistant_delivery_payload(work_id)
            assert delivery is not None and delivery["revision"] == 1
            assert result.delivery_observation_ref == ObjectRef(
                object_id=delivery["object_id"], revision=1)
            assert result.delivery_response == "finished once"
        else:
            assert fresh.ingestor.assistant_delivery_payload(work_id) is None
    rev_after = int(fresh.store.current_world_revision())
    assert rev_after > rev_before
    # A second ACK must never append an additional completion/output revision.
    if kind == "wake":
        again = execute(new_runtime(db, lambda _: pytest.fail("no provider")), kind,
                        work_id, now=NOW + timedelta(minutes=1))
        assert again.wake.revision == result.wake.revision
        assert again.delivery_observation_ref == result.delivery_observation_ref
    elif kind == "periodic_review":
        again = execute(new_runtime(db, lambda _: pytest.fail("no provider")), kind,
                        now=NOW + timedelta(minutes=1))
        assert again is None or again.wake.revision == result.wake.revision
    assert int(fresh.store.current_world_revision()) == rev_after


@pytest.mark.parametrize("kind", ["user_turn", "wake", "periodic_review"])
@pytest.mark.parametrize("already_applied", [False, True], ids=["B-before-capability", "C-after-capability"])
def test_r5_b_c_metered_capability_effect_and_replay(tmp_path, kind, already_applied):
    db = tmp_path / "world.db"
    calls = []
    def initial_provider(snapshot):
        calls.append(snapshot.round_index)
        assert snapshot.round_index == 0
        return directive(0, call=watch_call(0))
    initial = new_runtime(db, initial_provider)
    seed_anchor(initial.store)
    initial.index.catch_up()
    work_id = start(initial, kind)
    real_invoke = initial.registry.invoke
    def crash_boundary(call):
        assert call.call_id == "trusted-watch-0"
        if already_applied:
            result = real_invoke(call)
            assert result.ok and result.call_id == call.call_id
            assert len(task_rows(initial.store)) == 1
        raise ProcessDeath()
    initial.registry.invoke = crash_boundary
    with pytest.raises(ProcessDeath):
        execute(initial, kind, work_id)
    assert calls == [0]
    work_id = scope(initial, kind, work_id)
    before = evidence(initial, kind, work_id)
    assert before[0].state == "metered"
    tasks_before = task_rows(initial.store)
    assert len(tasks_before) == int(already_applied)
    rev_before = int(initial.store.current_world_revision())
    old_op = task_operation(db, tasks_before[0]["object_id"]) if already_applied else None
    if old_op is not None:
        assert old_op[2] == rev_before
        assert tasks_before[0]["revision"] == 1

    fresh_provider_calls = []
    round_one_state = []
    def continuation(snapshot):
        # A *new* next round is allowed; replay of round 0 is never allowed.
        assert snapshot.round_index == 1
        fresh_provider_calls.append(snapshot.round_index)
        tasks = task_rows(fresh.store)
        assert len(tasks) == 1 and tasks[0]["revision"] == 1
        op = task_operation(db, tasks[0]["object_id"])
        assert op[2] == int(fresh.store.current_world_revision()) if kind == "user_turn" else op[2] <= int(fresh.store.current_world_revision())
        if old_op is not None:
            assert op == old_op
            assert tasks == tasks_before
        else:
            assert op[2] == rev_before + 1
        round_one_state.append((tasks[0]["object_id"], op))
        return directive(1)
    fresh = new_runtime(db, continuation)
    result = execute(fresh, kind, work_id, now=NOW + timedelta(minutes=1))
    assert fresh_provider_calls == [1] and len(round_one_state) == 1
    assert_same_evidence(before, evidence(fresh, kind, work_id))
    tasks_after = task_rows(fresh.store)
    assert len(tasks_after) == 1 and tasks_after[0]["revision"] == 1
    assert tasks_after[0]["object_id"] == round_one_state[0][0]
    final_op = task_operation(db, tasks_after[0]["object_id"])
    assert final_op == round_one_state[0][1]
    if already_applied:
        assert final_op == old_op and tasks_after == tasks_before
    assert int(fresh.store.current_world_revision()) > rev_before
    assert result.runtime.capability_history[0].call_id == "trusted-watch-0"
    assert result.runtime.capability_history[0].ok
    assert result.runtime.capability_history[0].data["task_id"] == tasks_after[0]["object_id"]
    assert result.runtime.recovered_response_attempts == (before[0].attempt_id,)
    assert [a.model_round_index for a in fresh.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind=kind, work_id=work_id)] == [0, 1]
    work_attempts = fresh.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind=kind, work_id=work_id)
    work_meters = sorted((m for m in fresh.metering.list_model_calls(subject_id="user_1")
                          if m.background_attempt_id in {a.attempt_id for a in work_attempts}),
                         key=lambda m: m.model_round_index)
    assert [m.background_attempt_id for m in work_meters] == [a.attempt_id for a in work_attempts]
    if kind == "user_turn":
        status = fresh.inspect_turn_execution(session_id="r5-session", turn_index=1,
            user_input="R5 exact replay", occurred_at=NOW)
        assert status.state == "completed" and status.execution_id == work_id
    else:
        assert result.wake.state == "completed" and result.wake.wake_id == work_id



@pytest.mark.parametrize("kind", ["user_turn", "wake"])
def test_r5_d_terminal_receipt_bypasses_all_runtime_replay(tmp_path, kind, monkeypatch):
    db = tmp_path / "world.db"
    initial = new_runtime(db, lambda _: directive(0))
    work_id = start(initial, kind)
    if kind == "user_turn":
        monkeypatch.setattr(initial.turn_executions, "complete",
                            lambda **_: (_ for _ in ()).throw(ProcessDeath()))
    else:
        monkeypatch.setattr(initial.wake_bus, "complete",
                            lambda *_, **__: (_ for _ in ()).throw(ProcessDeath()))
    with pytest.raises(ProcessDeath):
        execute(initial, kind, work_id)
    before = evidence(initial, kind, work_id)
    rev_before = int(initial.store.current_world_revision())
    if kind == "user_turn":
        pre = initial.inspect_turn_execution(session_id="r5-session", turn_index=1,
            user_input="R5 exact replay", occurred_at=NOW)
        assert pre.state == "started" and pre.assistant_ref is not None
        output_id = pre.assistant_ref.object_id
        output = initial.store.get_payload(output_id)
    else:
        assert initial.wake_bus.current_wake(work_id).wake_state.value == "running"
        output = initial.ingestor.assistant_delivery_payload(work_id)
        assert output is not None and output["revision"] == 1
        output_id = str(output["object_id"])

    fresh = new_runtime(db, lambda _: pytest.fail("R5-D provider must not run"))
    def prohibited(*_args, **_kwargs):
        pytest.fail("R5-D must use stronger terminal receipt, not model/capability replay")
    fresh.cognitive_runtime.run_turn = prohibited
    fresh.cognitive_runtime.model_usage_recorder = prohibited
    fresh.registry.invoke = prohibited
    fresh.ingestor.commit_assistant_delivery = prohibited
    if kind == "user_turn":
        with pytest.raises(TurnAlreadyCompleted):
            execute(fresh, kind)
        status = fresh.inspect_turn_execution(session_id="r5-session", turn_index=1,
            user_input="R5 exact replay", occurred_at=NOW)
        assert status.state == "completed" and status.execution_id == work_id
        assert status.assistant_ref == pre.assistant_ref
        assert int(fresh.store.current_world_revision()) == rev_before  # SQL ACK only
    else:
        result = execute(fresh, kind, work_id, now=NOW + timedelta(minutes=1))
        assert result.runtime is None and result.wake.state == "completed"
        assert result.delivery_observation_ref == ObjectRef(object_id=output_id, revision=1)
        assert result.wake.revision == int(fresh.store.get_payload(work_id)["revision"])
        assert int(fresh.store.current_world_revision()) == rev_before + 1  # Wake ACK only
    assert fresh.store.get_payload(output_id) == output
    assert_same_evidence(before, evidence(fresh, kind, work_id))
    final_rev = int(fresh.store.current_world_revision())
    if kind == "user_turn":
        with pytest.raises(TurnAlreadyCompleted):
            execute(fresh, kind)
    else:
        again = execute(fresh, kind, work_id, now=NOW + timedelta(minutes=1))
        assert again.wake.revision == result.wake.revision
    assert int(fresh.store.current_world_revision()) == final_rev
