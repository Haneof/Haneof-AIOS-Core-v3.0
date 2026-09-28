"""Shared harness for CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002
independent adversarial acceptance probes.

These helpers exist to ATTACK the exact candidate.  Legitimate trusted returns
are simulated through the internal return-boundary callback exactly as the
production wiring invokes it; every other artifact the "external caller" holds
(payload bytes, fingerprints, hashes, evidence, relay echo, receipts copied out
of the public receipt reader) is treated as untrusted caller input.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Callable

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

NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
PROVIDER = "ia-trusted-provider"
MODEL = "ia-trusted-model"


class IAProcessDeath(BaseException):
    """Simulated process death that escapes except-Exception recovery paths."""


def world(tmp_path, name: str = "world.db"):
    db = tmp_path / name
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index, db


def reopen(db):
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def directive(
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
            input_tokens=5,
            output_tokens=5,
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


def identityless_directive(response: str = "local anonymous response") -> ModelDirective:
    return ModelDirective(response=response)


def bind_handler(runtime: FusedTurnRuntime, handler: Callable) -> None:
    runtime.model_handler = handler
    runtime.cognitive_runtime.model_handler = handler


def emit_wake(runtime: FusedTurnRuntime, *, key: str):
    return runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id=f"ia-adv.{key}",
            observed_at=NOW,
            dedupe_key=f"ia-adv:{runtime.subject_id}:{key}",
        )
    )


def wake_ref(signal) -> ObjectRef:
    return ObjectRef(object_id=signal.wake_id, revision=signal.revision)


def fingerprint(runtime: FusedTurnRuntime, d: ModelDirective) -> str:
    return runtime.background_model_attempts._response_fingerprint(d)


def payload_sha(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def crash_wake(runtime: FusedTurnRuntime, *, key: str):
    """Force a dispatching->in_doubt attempt with NO provider response."""

    def no_response(snapshot):
        raise TimeoutError("ia probe: provider never returned")

    bind_handler(runtime, no_response)
    signal = emit_wake(runtime, key=key)
    try:
        runtime.run_wake(wake_ref=wake_ref(signal), now=NOW)
    except TimeoutError:
        pass
    else:  # pragma: no cover - probe failure
        raise AssertionError("probe setup expected a provider-never-returned failure")
    attempt = runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert attempt is not None and attempt.state == "in_doubt", attempt
    return signal, attempt


def crash_user_turn(runtime: FusedTurnRuntime, *, key: str):
    def no_response(snapshot):
        raise TimeoutError("ia probe: provider never returned")

    bind_handler(runtime, no_response)
    turn = {
        "session_id": f"ia-adv-{key}",
        "turn_index": 1,
        "user_input": f"IA adversarial probe {key}",
        "occurred_at": NOW,
    }
    try:
        runtime.run_turn(**turn)
    except TimeoutError:
        pass
    else:  # pragma: no cover - probe failure
        raise AssertionError("probe setup expected a provider-never-returned failure")
    inspection = runtime.inspect_turn_execution(**turn)
    attempt = inspection.model_attempts[0]
    assert attempt.state == "in_doubt", attempt
    return turn, inspection.execution_id, attempt


def capture_return(
    runtime: FusedTurnRuntime,
    attempt_id: str,
    d: ModelDirective,
    *,
    captured_at: datetime | None = None,
):
    """Simulate the trusted provider/relay return callback (production wiring).

    This is the ONLY accepted stand-in for a real provider return in these
    probes.  Forged-path probes must not use it to create the forged artifacts.
    """

    return runtime.background_model_attempts._capture_trusted_response_return(
        attempt_id,
        captured_at=captured_at or (NOW + timedelta(seconds=1)),
        directive=d,
    )


def stage(
    runtime: FusedTurnRuntime,
    *,
    work_kind: str,
    work_id: str,
    round_index: int,
    d: ModelDirective,
    evidence: str = "ia external response journal replay",
    authenticity_proof: str | None = None,
    staged_at: datetime | None = None,
):
    payload = encode_model_directive(d)
    return runtime.stage_exact_background_response(
        work_kind=work_kind,
        work_id=work_id,
        model_round_index=round_index,
        provider=d.provenance.provider,
        model=d.provenance.model,
        provider_request_id=d.provenance.request_id,
        response_fingerprint=fingerprint(runtime, d),
        directive_payload=payload,
        staged_at=staged_at or (NOW + timedelta(minutes=2)),
        evidence=evidence,
        authenticity_proof=authenticity_proof,
    )


def effect_snapshot(runtime: FusedTurnRuntime, attempt) -> dict:
    return {
        "attempt": runtime.background_model_attempts.get(attempt.attempt_id),
        "staged": runtime.background_model_attempts.staged_response(attempt.attempt_id),
        "receipt": runtime.background_model_attempts.response_authenticity_receipt(
            attempt.attempt_id
        ),
        "world_revision": int(runtime.store.current_world_revision()),
        "meters": tuple(runtime.metering.list_model_calls(subject_id=runtime.subject_id)),
        "tasks": tuple(
            runtime.store.list_payloads(
                object_type=ObjectType.TASK, subject_id=runtime.subject_id
            )
        ),
        "assistant": tuple(
            payload
            for payload in runtime.store.list_payloads(
                object_type=ObjectType.OBSERVATION, subject_id=runtime.subject_id
            )
            if (payload.get("metadata") or {}).get("role") == "assistant"
        ),
    }


def assert_rejected_without_mutation(runtime, attempt, call: Callable[[], object]) -> Exception:
    """The call must raise AND leave every audited surface byte-identical."""

    before = effect_snapshot(runtime, attempt)
    try:
        call()
    except BaseException as exc:  # noqa: BLE001 - probe asserts any rejection
        after = effect_snapshot(runtime, attempt)
        assert after == before, (
            f"rejected call still mutated durable state: before={before!r} after={after!r}"
        )
        return exc
    raise AssertionError("forged/invalid call was ACCEPTED by the exact candidate")


def seed_watch_anchor(store: SQLiteWorldStore, *, subject_id: str = "user_1"):
    observation = Observation(
        object_id=f"obs_ia_adv_anchor_{subject_id}",
        subject_id=subject_id,
        occurred=TemporalExtent.point(NOW - timedelta(hours=1)),
        learned_at=NOW - timedelta(hours=1),
        recorded_at=NOW - timedelta(hours=1),
        created_by="test:ia-adversarial",
        source_kind="conversation",
        modality="text",
        value="IA adversarial anchor for capability forgery probes.",
        metadata={"dimension": "dim:ia-adv"},
    )
    store.commit(
        [observation],
        OperationRequest(
            operation_name="test.ia-adv.seed-anchor",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed capability forgery probe",
            idempotency_key=f"ia-adv:seed-anchor:{subject_id}",
            source_class=SourceClass.USER,
        ),
    )
    return {"object_id": observation.object_id, "revision": 1}


def watch_call(anchor_ref: dict, *, title: str, call_id: str = "ia-forged-call"):
    return CapabilityCall(
        name="create_attention_watch",
        arguments={
            "title": title,
            "dimensions": ["dim:ia-adv"],
            "reason_refs": [anchor_ref],
            "source_kind": "conversation",
            "modality": "text",
            "priority": 40,
            "cooldown_seconds": 60,
        },
        call_id=call_id,
    )


def forged_tasks(store: SQLiteWorldStore, *, title: str):
    return [
        payload
        for payload in store.list_payloads(object_type=ObjectType.TASK, subject_id="user_1")
        if payload.get("title") == title
    ]


def assistant_outputs(store: SQLiteWorldStore, *, value: str):
    return [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.OBSERVATION, subject_id="user_1"
        )
        if (payload.get("metadata") or {}).get("role") == "assistant"
        and payload.get("value") == value
    ]


def raw_conn(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def authority_secret(db_path) -> str | None:
    with raw_conn(db_path) as conn:
        row = conn.execute(
            "SELECT secret_hex FROM background_model_authenticity_authority "
            "WHERE authority_id='trusted-return-v1'"
        ).fetchone()
    return None if row is None else str(row["secret_hex"])


def sql_rows(db_path, sql: str, args: tuple = ()):
    with raw_conn(db_path) as conn:
        return [dict(row) for row in conn.execute(sql, args).fetchall()]


def sql_exec(db_path, sql: str, args: tuple = ()) -> None:
    with raw_conn(db_path) as conn:
        conn.execute(sql, args)
        conn.commit()


def running_wake_id(store: SQLiteWorldStore, *, key: str = "") -> str | None:
    running = [
        payload
        for payload in store.list_payloads(object_type=ObjectType.WAKE, subject_id="user_1")
        if payload.get("wake_state") == "running"
    ]
    if key:
        running = [p for p in running if key in str(p.get("object_id", ""))]
    return None if not running else str(running[-1]["object_id"])


# --- crash/restart child fixtures (top-level for multiprocessing) -------------

class CatchableDeath(Exception):
    """Catchable simulated death used inside child processes before SIGKILL."""


def exact_directive(key: str = "i1") -> ModelDirective:
    return directive(f"provider-request-{key}", response="sigkill recovered exact response")


def capability_directive(key: str = "i3") -> ModelDirective:
    anchor = {"object_id": "obs_ia_adv_anchor_user_1", "revision": 1}
    return directive(
        f"provider-request-{key}",
        silence=False,
        capability_calls=(
            CapabilityCall(
                name="create_attention_watch",
                arguments={
                    "title": "ia sigkill exactly-once watch",
                    "dimensions": ["dim:ia-adv"],
                    "reason_refs": [anchor],
                    "source_kind": "conversation",
                    "modality": "text",
                    "priority": 40,
                    "cooldown_seconds": 60,
                },
                call_id="ia-sigkill-watch-call",
            ),
        ),
    )


def sole_attempt_id(store) -> str:
    rows = sql_rows(store.db_path, "SELECT attempt_id FROM background_model_attempts")
    assert rows, "expected exactly one durable attempt"
    return str(rows[-1]["attempt_id"])


def sole_running_wake(store) -> dict:
    running = [
        payload
        for payload in store.list_payloads(object_type=ObjectType.WAKE, subject_id="user_1")
        if payload.get("wake_state") == "running"
    ]
    assert len(running) == 1, f"expected one running wake: {running!r}"
    return {
        "object_id": str(running[0]["object_id"]),
        "revision": int(running[0]["revision"]),
    }


def child_receipt_then_sigkill(db_path: str) -> None:
    import os
    import signal as posix_signal

    store, index, _db = world_from_path(db_path)
    exact = exact_directive("i1")
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: exact)
    signal = emit_wake(runtime, key="i1")

    def die_at_recorder(snapshot, d):
        os.kill(os.getpid(), posix_signal.SIGKILL)

    runtime.cognitive_runtime.model_response_recorder = die_at_recorder
    runtime.run_wake(wake_ref=wake_ref(signal), now=NOW)


def child_staged_then_sigkill(db_path: str) -> None:
    import os
    import signal as posix_signal

    store, index, _db = world_from_path(db_path)
    exact = exact_directive("i2")
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: exact)
    signal = emit_wake(runtime, key="i2")

    def die_catchably(snapshot, d):
        raise CatchableDeath("ia i2 death after receipt")

    runtime.cognitive_runtime.model_response_recorder = die_catchably
    try:
        runtime.run_wake(wake_ref=wake_ref(signal), now=NOW)
    except CatchableDeath:
        pass
    attempt = runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    receipt = runtime.background_model_attempts.response_authenticity_receipt(
        attempt.attempt_id
    )
    assert receipt is not None
    stage(
        runtime,
        work_kind="wake",
        work_id=signal.wake_id,
        round_index=0,
        d=exact,
        authenticity_proof=receipt.authenticity_proof,
    )
    os.kill(os.getpid(), posix_signal.SIGKILL)


def capability_sigkill_exactly_once_child(db_path: str) -> None:
    import os
    import signal as posix_signal

    from aios_core.contracts.models import Observation
    from aios_core.contracts.operations import OperationRequest
    from aios_core.contracts.time import TemporalExtent

    store, index, _db = world_from_path(db_path)
    observation = Observation(
        object_id="obs_ia_adv_anchor_user_1",
        subject_id="user_1",
        occurred=TemporalExtent.point(NOW - timedelta(hours=1)),
        learned_at=NOW - timedelta(hours=1),
        recorded_at=NOW - timedelta(hours=1),
        created_by="test:ia-adversarial",
        source_kind="conversation",
        modality="text",
        value="IA adversarial anchor for capability forgery probes.",
        metadata={"dimension": "dim:ia-adv"},
    )
    store.commit(
        [observation],
        OperationRequest(
            operation_name="test.ia-adv.seed-anchor",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed capability forgery probe",
            idempotency_key="ia-adv:seed-anchor:user_1",
            source_class=SourceClass.USER,
        ),
    )
    index.catch_up()
    exact = capability_directive("i3")

    def scripted(snapshot):
        if snapshot.round_index == 0:
            return exact
        return ModelDirective(silence=True)

    runtime = FusedTurnRuntime(store=store, index=index, model_handler=scripted)
    signal = emit_wake(runtime, key="i3")
    real_handler = runtime._create_attention_watch

    def kill_after_commit(**kwargs):
        real_handler(**kwargs)
        os.kill(os.getpid(), posix_signal.SIGKILL)

    spec = runtime.registry.get_spec("create_attention_watch")
    runtime.registry.unregister("create_attention_watch")
    runtime.registry.register(spec, kill_after_commit)
    runtime.run_wake(wake_ref=wake_ref(signal), now=NOW)


def world_from_path(db_path: str):
    from pathlib import Path

    return world(Path(db_path).parent, Path(db_path).name)
