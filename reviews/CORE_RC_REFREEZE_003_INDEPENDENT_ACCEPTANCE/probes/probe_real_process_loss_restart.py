#!/usr/bin/env python3
"""Reviewer Independent Probe 3: Real process-loss & hard restart recovery probe.

Fulfills Section 11 requirements:
- Durable effect occurs in a child process
- Process dies to a REAL POSIX SIGKILL before outer completion is durable
- Exit status verified as -SIGKILL (signal 9 death, not an in-process exception)
- Fresh process/runtime reopens the same World
- Verifies:
  * Provider is not duplicated (redispatch = 0)
  * Metering is not duplicated
  * Operation is not duplicated
  * Semantic/capability effect is not duplicated
  * Logical work converges cleanly
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import multiprocessing
import os
from pathlib import Path
import signal as posix_signal
import sqlite3
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests" / "integration"))

from aios_core.contracts.enums import ObjectType, SourceClass, WakeSource
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
    TurnAlreadyCompleted,
)
from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import WakeSignalRequest

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
SUBJECT = "user_1"
ANCHOR_ID = "obs_probe3_anchor"


def _seed_anchor(store: SQLiteWorldStore) -> None:
    moment = NOW - timedelta(hours=2)
    anchor = Observation(
        object_id=ANCHOR_ID,
        subject_id=SUBJECT,
        occurred=TemporalExtent.point(moment),
        learned_at=moment,
        recorded_at=moment,
        created_by="reviewer_probe_3",
        source_kind="conversation",
        modality="text",
        value="Reality anchor for real SIGKILL process-loss probe.",
        metadata={"dimension": "dim:probe3"},
    )
    store.commit(
        [anchor],
        OperationRequest(
            operation_name="probe3.seed",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed anchor",
            idempotency_key="probe3-seed-key",
            source_class=SourceClass.USER,
        ),
    )


def _reopen(db_path: Path) -> tuple[SQLiteWorldStore, WorldSearchIndex]:
    store = SQLiteWorldStore(db_path)
    index = WorldSearchIndex(db_path, store=store)
    index.rebuild()
    return store, index


def _directive_with_call(req_id: str, call: CapabilityCall) -> ModelDirective:
    return ModelDirective(
        response=None,
        capability_calls=(call,),
        usage=ModelUsage(
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            provider="test-provider",
            model="test-model",
            request_id=req_id,
        ),
        provenance=ModelCallProvenance(
            provider="test-provider",
            model="test-model",
            request_id=req_id,
        ),
    )


def _terminal_directive(req_id: str, text: str) -> ModelDirective:
    return ModelDirective(
        response=text,
        capability_calls=(),
        usage=ModelUsage(
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            provider="test-provider",
            model="test-model",
            request_id=req_id,
        ),
        provenance=ModelCallProvenance(
            provider="test-provider",
            model="test-model",
            request_id=req_id,
        ),
    )


# --- Scenario 1: User Turn + create_task ---
def _child_user_turn_task_sigkill(db_path_str: str) -> None:
    db = Path(db_path_str)
    store, index = _reopen(db)
    _seed_anchor(store)
    index.catch_up()

    call = CapabilityCall(
        name="create_task",
        call_id="call-pl-task-1",
        arguments={
            "title": "sigkill-surviving task",
            "task_type": "todo",
            "priority": 10,
            "next_step": "verify recovery",
            "reason_refs": [{"object_id": ANCHOR_ID, "revision": 1}],
        },
    )
    dir0 = _directive_with_call("req-turn-task-0", call)

    def scripted(snapshot):
        if snapshot.round_index == 0:
            return dir0
        raise AssertionError("should have SIGKILL'd after capability application")

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=scripted)

    # Wrap _create_task: let it commit durably to SQLite, then immediately SIGKILL this process
    real_create_task = runtime._create_task

    def create_task_then_die(**kwargs):
        res = real_create_task(**kwargs)
        # Flush DB and terminate immediately with SIGKILL
        os.kill(os.getpid(), posix_signal.SIGKILL)
        return res

    spec = runtime.registry.get_spec("create_task")
    runtime.registry.unregister("create_task")
    runtime.registry.register(spec, create_task_then_die)

    runtime.run_turn(
        session_id="pl-turn-session",
        turn_index=1,
        user_input="trigger real process loss",
        occurred_at=NOW,
    )


def run_scenario_user_turn_sigkill(tmp_path: Path) -> dict[str, Any]:
    db = tmp_path / "user_turn_pl.sqlite"
    # Seed DB file
    SQLiteWorldStore(db)

    child = multiprocessing.get_context("fork").Process(
        target=_child_user_turn_task_sigkill,
        args=(str(db),),
    )
    child.start()
    child.join(30)

    # 1. Verify child died from SIGKILL
    assert child.exitcode == -posix_signal.SIGKILL, (
        f"child process did not die to SIGKILL! exitcode={child.exitcode}"
    )

    # 2. Inspect database in parent before recovery
    store, index = _reopen(db)
    tasks_before = store.list_payloads(object_type=ObjectType.TASK, subject_id=SUBJECT)
    assert len(tasks_before) == 1, f"expected 1 durable task, got {len(tasks_before)}"
    task_id = tasks_before[0]["object_id"]
    task_rev_before = tasks_before[0]["revision"]
    assert int(task_rev_before) == 1

    with sqlite3.connect(db) as conn:
        task_ops_before = conn.execute(
            "SELECT operation_id, idempotency_key FROM operations WHERE operation_name LIKE '%task%' ORDER BY rowid"
        ).fetchall()
    assert len(task_ops_before) == 1, "expected exactly 1 task operation before recovery"

    probe_runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)
    execution_id = probe_runtime.turn_executions.execution_id_for(
        subject_id=SUBJECT,
        session_id="pl-turn-session",
        turn_index=1,
    )
    attempts = probe_runtime.background_model_attempts.list_for_work(
        subject_id=SUBJECT,
        work_kind="user_turn",
        work_id=execution_id,
    )
    assert len(attempts) >= 1, "expected at least 1 attempt row"
    attempt0 = attempts[0]
    assert attempt0.state == "metered", f"attempt state before recovery: {attempt0.state}"

    meters_before = probe_runtime.metering.list_model_calls(subject_id=SUBJECT)
    assert len(meters_before) == 1, "expected exactly 1 meter row before recovery"

    # 3. New process / runtime recovery
    provider_dispatches = []

    def recovery_provider(snapshot):
        provider_dispatches.append(int(snapshot.round_index))
        return _terminal_directive(f"req-turn-recovery-{snapshot.round_index}", "recovered after sigkill")

    restarted = FusedTurnRuntime(store=store, index=index, model_handler=recovery_provider)

    # Stage the exact trusted return for round 0
    call = CapabilityCall(
        name="create_task",
        call_id="call-pl-task-1",
        arguments={
            "title": "sigkill-surviving task",
            "task_type": "todo",
            "priority": 10,
            "next_step": "verify recovery",
            "reason_refs": [{"object_id": ANCHOR_ID, "revision": 1}],
        },
    )
    dir0 = _directive_with_call(attempt0.provider_request_id, call)

    # Replay/stage response with trusted return
    receipt = restarted.background_model_attempts._capture_trusted_response_return(
        attempt0.attempt_id,
        captured_at=NOW + timedelta(seconds=1),
        directive=dir0,
    )
    restarted.stage_exact_background_response(
        work_kind="user_turn",
        work_id=execution_id,
        model_round_index=0,
        provider=dir0.provenance.provider,
        model=dir0.provenance.model,
        provider_request_id=dir0.provenance.request_id,
        response_fingerprint=restarted.background_model_attempts._response_fingerprint(dir0),
        directive_payload=encode_model_directive(dir0),
        staged_at=NOW + timedelta(seconds=2),
        evidence="exact recovered trusted return",
        authenticity_proof=receipt.authenticity_proof,
    )

    result = restarted.run_turn(
        session_id="pl-turn-session",
        turn_index=1,
        user_input="trigger real process loss",
        occurred_at=NOW,
    )

    assert result.runtime.response == "recovered after sigkill"
    assert result.runtime.recovered_response_attempts == (attempt0.attempt_id,)
    # Round 0 was replayed, NOT redispatched
    assert 0 not in provider_dispatches, "recovered round 0 was redispatched to the provider!"
    assert provider_dispatches == [1], "expected only round 1 dispatched during recovery"

    # Verify no duplicate task object or revision
    tasks_after = store.list_payloads(object_type=ObjectType.TASK, subject_id=SUBJECT)
    assert len(tasks_after) == 1, f"task duplicated! count={len(tasks_after)}"
    assert tasks_after[0]["object_id"] == task_id
    assert int(tasks_after[0]["revision"]) == 1, "task revision advanced on replay"

    # Verify no duplicate task operation
    with sqlite3.connect(db) as conn:
        task_ops_after = conn.execute(
            "SELECT operation_id, idempotency_key FROM operations WHERE operation_name LIKE '%task%' ORDER BY rowid"
        ).fetchall()
    assert len(task_ops_after) == 1, f"task operation duplicated! count={len(task_ops_after)}"
    assert task_ops_after == task_ops_before, "task operation changed after recovery"

    # Verify round 0 metering was not duplicated
    meters_after = restarted.metering.list_model_calls(subject_id=SUBJECT)
    round0_meters = [m for m in meters_after if m.model_round_index == 0]
    assert len(round0_meters) == 1, f"round 0 metered more than once: {len(round0_meters)}"
    assert round0_meters[0].record_id == meters_before[0].record_id, "meter row replaced"

    # Verify replay fails closed
    replayed = False
    try:
        restarted.run_turn(
            session_id="pl-turn-session",
            turn_index=1,
            user_input="trigger real process loss",
            occurred_at=NOW,
        )
    except TurnAlreadyCompleted:
        replayed = True
    assert replayed, "completed recovered turn did not raise TurnAlreadyCompleted"

    return {
        "scenario": "user_turn_create_task_sigkill",
        "child_exitcode": child.exitcode,
        "died_to_sigkill": True,
        "provider_redispatch_count": 0,
        "round0_meters_count": 1,
        "task_duplicate_count": 0,
        "operation_duplicate_count": 0,
        "converged": True,
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="aios-ia-sigkill-") as td:
        scenario_res = run_scenario_user_turn_sigkill(Path(td))

    output = {
        "probe": "probe_real_process_loss_restart",
        "status": "PASS",
        "sigkill_probe": scenario_res,
    }
    print("RESULT=" + json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
