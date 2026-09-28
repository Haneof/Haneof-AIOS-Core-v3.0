"""R5 replay conflicts cannot silently overwrite trusted bytes or World truth."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import sqlite3

import pytest

from aios_core.contracts.enums import ObjectType
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.models import Task
from aios_core.contracts.operations import OperationRequest
from aios_core.runtime import TurnInputConflict
from aios_core.runtime.background_attempt import (
    BackgroundModelResponseConflict, decode_model_directive, encode_model_directive,
)
from aios_core.storage.sqlite_store import StoreError
from aios_core.wake.attention import AttentionWatchRequest
from test_core_background_trusted_return_recovery_001 import (
    NOW, directive, seed_anchor, watch_call,
)
from test_core_background_trusted_return_r5_001 import (
    ProcessDeath, evidence, execute, new_runtime, scope, start, task_operation, task_rows,
)


def metered_task_crash(tmp_path):
    db = tmp_path / "world.db"
    initial = new_runtime(db, lambda _: directive(0, call=watch_call(0)))
    seed_anchor(initial.store)
    initial.index.catch_up()
    work_id = start(initial, "wake")
    original = initial.registry.invoke
    def crash_after_commit(call):
        result = original(call)
        assert result.ok
        raise ProcessDeath()
    initial.registry.invoke = crash_after_commit
    with pytest.raises(ProcessDeath):
        execute(initial, "wake", work_id)
    before = evidence(initial, "wake", work_id)
    task = task_rows(initial.store)[0]
    op = task_operation(db, task["object_id"])
    revision = int(initial.store.current_world_revision())
    return db, work_id, before, task, op, revision


@pytest.mark.parametrize("mutation", [
    "capability_args_same_call_id", "capability_call_id", "response_payload",
    "provider", "model", "request_id", "originating_request", "response_fingerprint",
])
def test_r5_c_forged_or_changed_handoff_fails_before_capability_replay(tmp_path, mutation):
    db, work_id, before, task, op, revision = metered_task_crash(tmp_path)
    with sqlite3.connect(db) as conn:
        payload = conn.execute(
            "SELECT directive_payload FROM background_model_return_handoffs WHERE attempt_id=?",
            (before[0].attempt_id,)).fetchone()[0]
        if mutation == "originating_request":
            conn.execute(
                "UPDATE background_model_request_bindings SET outbound_request_fingerprint=? WHERE attempt_id=?",
                ("0" * 64, before[0].attempt_id))
        elif mutation == "response_fingerprint":
            conn.execute(
                "UPDATE background_model_response_receipts SET response_fingerprint=? WHERE attempt_id=?",
                ("0" * 64, before[0].attempt_id))
        else:
            returned = decode_model_directive(payload)
            if mutation == "capability_args_same_call_id":
                altered = replace(returned.capability_calls[0], arguments={
                    **returned.capability_calls[0].arguments, "priority": 99,
                })
                returned = replace(returned, capability_calls=(altered,))
            elif mutation == "capability_call_id":
                altered = replace(returned.capability_calls[0], call_id="altered-id")
                returned = replace(returned, capability_calls=(altered,))
            elif mutation == "response_payload":
                returned = replace(returned, capability_calls=(), response="forged final output")
            else:
                provenance = replace(returned.provenance, **{mutation: "wrong-identity"})
                usage = replace(returned.usage, **{mutation: "wrong-identity"})
                returned = replace(returned, provenance=provenance, usage=usage)
            altered_payload = encode_model_directive(returned)
            conn.execute(
                "UPDATE background_model_return_handoffs SET directive_payload=?,payload_sha256=? WHERE attempt_id=?",
                (altered_payload, hashlib.sha256(altered_payload.encode()).hexdigest(), before[0].attempt_id))
        conn.commit()
    fresh = new_runtime(db, lambda _: pytest.fail("forged replay must not reach provider"))
    with pytest.raises(BackgroundModelResponseConflict):
        execute(fresh, "wake", work_id)
    assert int(fresh.store.current_world_revision()) == revision
    assert task_rows(fresh.store) == [task]
    assert task_operation(db, task["object_id"]) == op
    assert fresh.background_model_attempts.staged_response(before[0].attempt_id) is None
    assert fresh.metering.list_model_calls(subject_id="user_1") == (
        before[4],
    )


def test_r5_c_changed_world_payload_same_idempotency_identity_fails_closed(tmp_path):
    db, work_id, before, task, op, revision = metered_task_crash(tmp_path)
    fresh = new_runtime(db, lambda _: pytest.fail("no provider"))
    args = watch_call(0).arguments
    original = AttentionWatchRequest(
        title=args["title"], dimensions=tuple(args["dimensions"]),
        reason_refs=(ObjectRef(object_id="trusted_return_anchor", revision=1),),
        source_kind=args["source_kind"], modality=args["modality"],
        priority=args["priority"], cooldown_seconds=args["cooldown_seconds"],
    )
    assert fresh.attention_watches.create(original, created_at=NOW).task_id == task["object_id"]
    assert int(fresh.store.current_world_revision()) == revision
    with pytest.raises(StoreError, match="idempotency key was already used for a different request"):
        fresh.attention_watches.create(original.model_copy(update={"priority": 41}), created_at=NOW)
    assert int(fresh.store.current_world_revision()) == revision
    assert task_rows(fresh.store) == [task]
    assert task_operation(db, task["object_id"]) == op


def test_r5_c_altered_idempotency_key_cannot_duplicate_existing_task(tmp_path):
    db, work_id, before, task, op, revision = metered_task_crash(tmp_path)
    fresh = new_runtime(db, lambda _: pytest.fail("no provider"))
    with pytest.raises(StoreError):
        fresh.store.commit(
            [Task.model_validate(fresh.store.get_payload(task["object_id"]))],
            OperationRequest(
                operation_name="execution.task.create",
                arguments={"task_id": task["object_id"], "title": task["title"],
                           "initial_state": task["task_state"]},
                expected_world_revision=revision,
                reason="create evidence-grounded task",
                idempotency_key=f"altered-task-create:{task['object_id']}:1",
            ),
        )
    assert task_rows(fresh.store) == [task]
    assert task_operation(db, task["object_id"]) == op
    assert int(fresh.store.current_world_revision()) == revision


def test_r5_d_conflicting_terminal_delivery_and_stale_turn_input_fail_closed(tmp_path, monkeypatch):
    db = tmp_path / "world.db"
    runtime = new_runtime(db, lambda _: directive(0))
    work_id = start(runtime, "wake")
    monkeypatch.setattr(runtime.wake_bus, "complete",
        lambda *_, **__: (_ for _ in ()).throw(ProcessDeath()))
    with pytest.raises(ProcessDeath):
        execute(runtime, "wake", work_id)
    before = evidence(runtime, "wake", work_id)
    delivery = runtime.ingestor.assistant_delivery_payload(work_id)
    assert delivery is not None and delivery["revision"] == 1
    metadata = delivery["metadata"]["delivery_runtime"]
    wake_ref = ObjectRef.model_validate(delivery["metadata"]["origin_wake_ref"])
    revision = int(runtime.store.current_world_revision())
    fresh = new_runtime(db, lambda _: pytest.fail("terminal output must bypass provider"))
    with pytest.raises(StoreError):
        fresh.ingestor.commit_assistant_delivery(
            assistant_text="forged later delivery", occurred_at=NOW,
            origin_wake_ref=wake_ref,
            termination_reason=metadata["termination_reason"],
            model_rounds=metadata["model_rounds"],
            capability_names=tuple(metadata["capability_names"]),
            step0=metadata["step0"],
        )
    assert fresh.ingestor.assistant_delivery_payload(work_id) == delivery
    assert int(fresh.store.current_world_revision()) == revision
    assert execute(fresh, "wake", work_id).wake.state == "completed"
    assert fresh.ingestor.assistant_delivery_payload(work_id) == delivery

    db2 = tmp_path / "turn.db"
    turn = new_runtime(db2, lambda _: directive(0))
    monkeypatch.setattr(turn.turn_executions, "complete",
        lambda **_: (_ for _ in ()).throw(ProcessDeath()))
    with pytest.raises(ProcessDeath):
        execute(turn, "user_turn")
    status = turn.inspect_turn_execution(session_id="r5-session", turn_index=1,
        user_input="R5 exact replay", occurred_at=NOW)
    assert status.assistant_ref is not None
    turn_rev = int(turn.store.current_world_revision())
    fresh_turn = new_runtime(db2, lambda _: pytest.fail("terminal turn must bypass provider"))
    with pytest.raises(TurnInputConflict):
        fresh_turn.run_turn(session_id="r5-session", turn_index=1,
            user_input="stale conflicting request", occurred_at=NOW)
    assert fresh_turn.store.get_payload(status.assistant_ref.object_id)["revision"] == 1
    assert int(fresh_turn.store.current_world_revision()) == turn_rev


@pytest.mark.parametrize("kind", ["wake", "periodic_review"])
def test_r5_a_terminal_ack_operation_identity_is_stable(tmp_path, kind, monkeypatch):
    db = tmp_path / "world.db"
    initial = new_runtime(db, lambda _: directive(0))
    if kind == "periodic_review":
        seed_anchor(initial.store)
        initial.index.catch_up()
    work_id = start(initial, kind)
    if kind == "wake":
        monkeypatch.setattr(initial.wake_bus, "complete",
            lambda *_, **__: (_ for _ in ()).throw(ProcessDeath()))
    else:
        monkeypatch.setattr(initial.periodic_review, "complete_review",
            lambda *_, **__: (_ for _ in ()).throw(ProcessDeath()))
    with pytest.raises(ProcessDeath):
        execute(initial, kind, work_id)
    work_id = scope(initial, kind, work_id)
    before = evidence(initial, kind, work_id)
    rev_before = int(initial.store.current_world_revision())
    fresh = new_runtime(db, lambda _: pytest.fail("no provider redispatch"))
    result = execute(fresh, kind, work_id)
    assert result.wake.state == "completed" and result.wake.wake_id == work_id
    ack_key = (f"wake-finish:{work_id}:{result.wake.revision}:completed" if kind == "wake"
               else f"review-complete:{work_id}:{result.wake.revision}")
    with sqlite3.connect(db) as conn:
        ack = conn.execute("SELECT operation_id,idempotency_key FROM operations "
                           "WHERE idempotency_key=?", (ack_key,)).fetchall()
        delivery = conn.execute("SELECT operation_id,idempotency_key FROM operations "
            "WHERE idempotency_key=?", (f"wake-assistant-delivery:user_1:{work_id}",)).fetchall()
    assert len(ack) == 1 and ack[0][1] == ack_key
    if kind == "wake":
        assert len(delivery) == 1
        assert result.delivery_observation_ref is not None
    else:
        assert delivery == []  # Review creates no assistant-to-user delivery.
    assert_same = evidence(fresh, kind, work_id)
    assert assert_same[1:] == before[1:]
    assert assert_same[0].attempt_id == before[0].attempt_id
    final_rev = int(fresh.store.current_world_revision())
    assert final_rev > rev_before
    repeated = execute(new_runtime(db, lambda _: pytest.fail("no provider")), kind, work_id)
    assert repeated is None or repeated.wake.revision == result.wake.revision
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT operation_id,idempotency_key FROM operations "
            "WHERE idempotency_key=?", (ack_key,)).fetchall() == ack
        assert conn.execute("SELECT operation_id,idempotency_key FROM operations "
            "WHERE idempotency_key=?", (f"wake-assistant-delivery:user_1:{work_id}",)).fetchall() == delivery
    assert int(fresh.store.current_world_revision()) == final_rev
