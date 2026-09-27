"""IA-ADV-I: real SIGKILL crash/restart authenticity and exactly-once effects."""

from __future__ import annotations

import multiprocessing
import os
import signal as posix_signal
from datetime import timedelta

from aios_core.contracts.enums import ObjectType
from aios_core.contracts.refs import ObjectRef
from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from ia_helpers import (
    NOW,
    capability_directive,
    capability_sigkill_exactly_once_child,
    child_receipt_then_sigkill,
    child_staged_then_sigkill,
    exact_directive,
    payload_sha,
    reopen,
    sole_attempt_id,
    sole_running_wake,
    sql_rows,
    stage,
    world,
)


def test_adv_i1_sigkill_after_receipt_recovers_exactly_once_with_zero_redispatch(tmp_path):
    """Real subprocess death after trusted receipt commit, before provenance."""

    db = tmp_path / "i1.db"
    ctx = multiprocessing.get_context("fork")
    process = ctx.Process(target=child_receipt_then_sigkill, args=(str(db),))
    process.start()
    process.join(30)
    assert process.exitcode == -posix_signal.SIGKILL, process.exitcode

    store, index = reopen(db)
    exact = exact_directive("i1")
    attempt_id = sole_attempt_id(store)
    receipts = sql_rows(
        db,
        "SELECT * FROM background_model_response_receipts WHERE attempt_id=?",
        (attempt_id,),
    )
    assert len(receipts) == 1, f"receipt must be durable across SIGKILL: {receipts!r}"
    provenance_rows = sql_rows(
        db, "SELECT provider, response_fingerprint FROM background_model_attempts"
    )
    assert provenance_rows[0]["provider"] is None, (
        "provenance was mutated before the SIGKILL boundary"
    )
    assert sql_rows(db, "SELECT 1 FROM metering_records") == []

    calls: list[int] = []

    def must_not_redispatch(snapshot):
        calls.append(snapshot.round_index)
        raise AssertionError("provider must not be redispatched after recovery")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=must_not_redispatch)
    signal = sole_running_wake(store)
    receipt = runtime.background_model_attempts.response_authenticity_receipt(attempt_id)
    assert receipt is not None
    stage(
        runtime,
        work_kind="wake",
        work_id=signal["object_id"],
        round_index=0,
        d=exact,
        authenticity_proof=receipt.authenticity_proof,
    )
    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=signal["object_id"], revision=int(signal["revision"])),
        now=NOW + timedelta(minutes=5),
    )
    assert calls == [], "provider was redispatched during exact recovery"
    assert result is not None

    meters = sql_rows(db, "SELECT * FROM metering_records")
    assert len(meters) == 1, f"metering must happen exactly once: {meters!r}"
    assert meters[0]["provider"] == exact.provenance.provider
    assistant = [
        p
        for p in store.list_payloads(object_type=ObjectType.OBSERVATION, subject_id="user_1")
        if (p.get("metadata") or {}).get("role") == "assistant"
    ]
    assert len(assistant) == 1 and assistant[0].get("value") == exact.response
    staged = runtime.background_model_attempts.staged_response(attempt_id)
    assert staged is not None
    assert staged.directive_payload == encode_model_directive(exact)
    assert staged.payload_sha256 == payload_sha(staged.directive_payload)


def test_adv_i2_sigkill_after_staging_then_restart_replays_exactly_once(tmp_path):
    """Death after durable staging, before application: restart must re-verify
    the persisted proof and apply the exact response exactly once."""

    db = tmp_path / "i2.db"
    ctx = multiprocessing.get_context("fork")
    process = ctx.Process(target=child_staged_then_sigkill, args=(str(db),))
    process.start()
    process.join(30)
    assert process.exitcode == -posix_signal.SIGKILL, process.exitcode

    store, index = reopen(db)
    attempt_id = sole_attempt_id(store)
    staged_rows = sql_rows(
        db, "SELECT * FROM background_model_responses WHERE attempt_id=?", (attempt_id,)
    )
    assert len(staged_rows) == 1, f"staging must be durable across SIGKILL: {staged_rows!r}"

    def must_not_redispatch(_s):
        raise AssertionError("provider must not be redispatched after recovery")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=must_not_redispatch)
    signal = sole_running_wake(store)
    result = runtime.run_wake(
        wake_ref=ObjectRef(object_id=signal["object_id"], revision=int(signal["revision"])),
        now=NOW + timedelta(minutes=5),
    )
    assert result is not None
    meters = sql_rows(db, "SELECT * FROM metering_records")
    assert len(meters) == 1, f"metering must happen exactly once: {meters!r}"
    assistant = [
        p
        for p in store.list_payloads(object_type=ObjectType.OBSERVATION, subject_id="user_1")
        if (p.get("metadata") or {}).get("role") == "assistant"
    ]
    assert len(assistant) == 1, f"output must be produced exactly once: {assistant!r}"

    try:
        runtime.run_wake(
            wake_ref=ObjectRef(
                object_id=signal["object_id"], revision=int(signal["revision"])
            ),
            now=NOW + timedelta(minutes=6),
        )
    except Exception:
        pass
    assert len(sql_rows(db, "SELECT * FROM metering_records")) == 1
    assistant_after = [
        p
        for p in store.list_payloads(object_type=ObjectType.OBSERVATION, subject_id="user_1")
        if (p.get("metadata") or {}).get("role") == "assistant"
    ]
    assert len(assistant_after) == 1


def test_adv_i3_sigkill_after_capability_commit_replays_world_effect_exactly_once(tmp_path):
    """SIGKILL right after the first capability commit: replay must not double-write."""

    from aios_core.runtime import ModelDirective

    db = tmp_path / "i3.db"
    ctx = multiprocessing.get_context("fork")
    process = ctx.Process(target=capability_sigkill_exactly_once_child, args=(str(db),))
    process.start()
    process.join(30)
    assert process.exitcode == -posix_signal.SIGKILL, process.exitcode

    store, index = reopen(db)
    attempt_id = sole_attempt_id(store)
    signal = sole_running_wake(store)

    def recovered_then_silence(snapshot):
        if snapshot.round_index == 0:
            raise AssertionError("round 0 must be recovered, not redispatched")
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(
        store=store, index=index, model_handler=recovered_then_silence
    )
    receipt = runtime.background_model_attempts.response_authenticity_receipt(attempt_id)
    assert receipt is not None
    exact = capability_directive("i3")
    stage(
        runtime,
        work_kind="wake",
        work_id=signal["object_id"],
        round_index=0,
        d=exact,
        authenticity_proof=receipt.authenticity_proof,
    )
    runtime.run_wake(
        wake_ref=ObjectRef(object_id=signal["object_id"], revision=int(signal["revision"])),
        now=NOW + timedelta(minutes=5),
    )
    tasks = [
        p
        for p in store.list_payloads(object_type=ObjectType.TASK, subject_id="user_1")
        if p.get("title") == "ia sigkill exactly-once watch"
    ]
    assert len(tasks) == 1, f"World effect must replay exactly once: {tasks!r}"
    assert int(tasks[0]["revision"]) == 1, (
        f"World effect replay created a new mutation: {tasks!r}"
    )
    recovered_meters = [
        row
        for row in sql_rows(db, "SELECT * FROM metering_records")
        if row["background_attempt_id"] == attempt_id
    ]
    assert len(recovered_meters) == 1, (
        f"recovered attempt must be metered exactly once: {recovered_meters!r}"
    )
