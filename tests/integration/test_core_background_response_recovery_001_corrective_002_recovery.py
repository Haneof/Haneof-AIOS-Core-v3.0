"""Positive and tamper coverage for CORRECTIVE-002 trusted-return receipts.

The frozen red-first exploit probes live in the adjacent ``*_authenticity.py`` file.
This file exercises the new trusted boundary itself: receipt durability before the
ordinary response recorder, restart recovery, exact replay, and proof revalidation.
"""

from __future__ import annotations

import multiprocessing
import os
import signal as posix_signal
from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import ObjectType, WakeSource
from aios_core.contracts.refs import ObjectRef
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import ModelCallProvenance, ModelDirective, ModelUsage
from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptStore,
    BackgroundModelResponseConflict,
    encode_model_directive,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import WakeSignalRequest


NOW = datetime(2026, 9, 27, 10, 0, tzinfo=timezone.utc)
PROVIDER = "trusted-relay"
MODEL = "trusted-model"


class _ProcessDeathAfterReceipt(BaseException):
    """Simulate death after receipt commit but before response provenance."""


def _world(tmp_path, name: str = "world.db"):
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


def _directive(
    request_id: str,
    *,
    response: str = "trusted exact response",
    provider: str = PROVIDER,
    model: str = MODEL,
) -> ModelDirective:
    return ModelDirective(
        response=response,
        usage=ModelUsage(
            input_tokens=6,
            output_tokens=4,
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


def _emit(runtime: FusedTurnRuntime, key: str):
    return runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id=f"cbrr-auth-green.{key}",
            observed_at=NOW,
            dedupe_key=f"cbrr-auth-green:{key}",
        )
    )


def _wake_ref(signal) -> ObjectRef:
    return ObjectRef(object_id=signal.wake_id, revision=signal.revision)


def _crash_after_trusted_receipt(tmp_path, *, key: str):
    store, index, db = _world(tmp_path)
    exact = _directive(f"provider-request-{key}")
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: exact,
    )
    signal = _emit(runtime, key)

    def die_before_response_recording(snapshot, directive):
        assert directive is exact
        assert snapshot.model_attempt_id is not None
        receipt = runtime.background_model_attempts.response_authenticity_receipt(
            snapshot.model_attempt_id
        )
        assert receipt is not None
        raise _ProcessDeathAfterReceipt()

    runtime.cognitive_runtime.model_response_recorder = die_before_response_recording
    with pytest.raises(_ProcessDeathAfterReceipt):
        runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)

    attempt = runtime.background_model_attempts.inspect(
        subject_id=runtime.subject_id,
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
    )
    assert attempt is not None
    assert attempt.state == "dispatching"
    assert attempt.provider is None
    assert attempt.model is None
    assert attempt.provider_request_id is None
    assert attempt.response_fingerprint is None
    assert runtime.background_model_attempts.staged_response(attempt.attempt_id) is None
    assert runtime.metering.list_model_calls(
        subject_id=runtime.subject_id, wake_id=signal.wake_id
    ) == ()
    receipt = runtime.background_model_attempts.response_authenticity_receipt(
        attempt.attempt_id
    )
    assert receipt is not None
    return store, index, db, runtime, signal, attempt, exact, receipt


def _stage(runtime, signal, exact, receipt):
    payload = encode_model_directive(exact)
    return runtime.stage_exact_background_response(
        work_kind="wake",
        work_id=signal.wake_id,
        model_round_index=0,
        provider=exact.provenance.provider,
        model=exact.provenance.model,
        provider_request_id=exact.provenance.request_id,
        response_fingerprint=runtime.background_model_attempts._response_fingerprint(
            exact
        ),
        directive_payload=payload,
        staged_at=NOW + timedelta(minutes=1),
        evidence="trusted relay journal persisted receipt and exact bytes",
        authenticity_proof=receipt.authenticity_proof,
    )


def test_receipt_is_durable_before_response_recording_and_recovers_after_restart(
    tmp_path,
):
    _store, _index, db, _runtime, signal, attempt, exact, receipt = (
        _crash_after_trusted_receipt(tmp_path, key="crash-restart")
    )

    reopened_store, reopened_index = _reopen(db)
    provider_calls: list[int] = []

    def must_not_redispatch(snapshot):
        provider_calls.append(snapshot.round_index)
        pytest.fail("authenticated recovery must not redispatch the provider")

    restarted = FusedTurnRuntime(
        store=reopened_store,
        index=reopened_index,
        model_handler=must_not_redispatch,
    )
    reopened_receipt = restarted.background_model_attempts.response_authenticity_receipt(
        attempt.attempt_id
    )
    assert reopened_receipt == receipt
    staged = _stage(restarted, signal, exact, reopened_receipt)
    assert staged.authenticity_proof == receipt.authenticity_proof

    result = restarted.run_wake(
        wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=2)
    )

    assert result.runtime.response == "trusted exact response"
    assert result.runtime.recovered_response_attempts == (attempt.attempt_id,)
    assert result.wake.state == "completed"
    assert provider_calls == []
    meter_rows = restarted.metering.list_model_calls(
        subject_id=restarted.subject_id, wake_id=signal.wake_id
    )
    assert len(meter_rows) == 1
    assert meter_rows[0].background_attempt_id == attempt.attempt_id


def _child_sigkill_after_receipt(db_path: str) -> None:
    store = SQLiteWorldStore(db_path)
    index = WorldSearchIndex(db_path, store=store)
    index.rebuild()
    exact = _directive("provider-request-sigkill")
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=lambda _snapshot: exact,
    )
    signal = _emit(runtime, "actual-sigkill")

    def kill_before_response_recording(_snapshot, _directive):
        os.kill(os.getpid(), posix_signal.SIGKILL)

    runtime.cognitive_runtime.model_response_recorder = kill_before_response_recording
    runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)


def test_actual_sigkill_after_receipt_commit_recovers_without_provider_redispatch(
    tmp_path,
):
    db = tmp_path / "sigkill-world.db"
    # Initialize before fork so the child only exercises the intended return window.
    SQLiteWorldStore(db)
    context = multiprocessing.get_context("fork")
    process = context.Process(
        target=_child_sigkill_after_receipt,
        args=(str(db),),
    )
    process.start()
    process.join(30)
    assert process.exitcode == -posix_signal.SIGKILL

    store, index = _reopen(db)
    running = [
        payload
        for payload in store.list_payloads(
            object_type=ObjectType.WAKE,
            subject_id="user_1",
        )
        if payload.get("wake_state") == "running"
    ]
    assert len(running) == 1
    wake_id = str(running[0]["object_id"])
    attempt_id = BackgroundModelAttemptStore.attempt_id_for(
        subject_id="user_1",
        work_kind="wake",
        work_id=wake_id,
        model_round_index=0,
    )

    provider_calls: list[int] = []

    def must_not_redispatch(snapshot):
        provider_calls.append(snapshot.round_index)
        pytest.fail("authenticated SIGKILL recovery must not redispatch")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=must_not_redispatch,
    )
    attempt = runtime.background_model_attempts.get(attempt_id)
    receipt = runtime.background_model_attempts.response_authenticity_receipt(attempt_id)
    assert attempt is not None
    assert attempt.state == "dispatching"
    assert receipt is not None
    exact = _directive("provider-request-sigkill")
    signal_ref = ObjectRef(
        object_id=wake_id,
        revision=int(running[0]["revision"]),
    )
    payload = encode_model_directive(exact)
    runtime.stage_exact_background_response(
        work_kind="wake",
        work_id=wake_id,
        model_round_index=0,
        provider=PROVIDER,
        model=MODEL,
        provider_request_id="provider-request-sigkill",
        response_fingerprint=runtime.background_model_attempts._response_fingerprint(exact),
        directive_payload=payload,
        staged_at=NOW + timedelta(minutes=1),
        evidence="receipt survived actual SIGKILL",
        authenticity_proof=receipt.authenticity_proof,
    )
    result = runtime.run_wake(
        wake_ref=signal_ref,
        now=NOW + timedelta(minutes=2),
    )

    assert result.runtime.response == "trusted exact response"
    assert result.runtime.recovered_response_attempts == (attempt_id,)
    assert provider_calls == []
    assert len(
        runtime.metering.list_model_calls(
            subject_id="user_1",
            wake_id=wake_id,
        )
    ) == 1


@pytest.mark.parametrize(
    "mutation",
    ("proof", "payload", "provider", "model", "provider_request_id"),
)
def test_tampered_return_bundle_is_rejected_before_provenance_or_metering(
    tmp_path, mutation
):
    store, _index, _db, runtime, signal, attempt, exact, receipt = (
        _crash_after_trusted_receipt(tmp_path, key=f"tamper-{mutation}")
    )
    revision_before = int(store.current_world_revision())
    candidate = exact
    proof = receipt.authenticity_proof
    if mutation == "proof":
        proof = receipt.authenticity_proof[:-1] + (
            "0" if receipt.authenticity_proof[-1] != "0" else "1"
        )
    elif mutation == "payload":
        candidate = _directive(
            exact.provenance.request_id,
            response="tampered self-consistent response bytes",
        )
    elif mutation == "provider":
        candidate = _directive(
            exact.provenance.request_id,
            provider="other-provider",
        )
    elif mutation == "model":
        candidate = _directive(
            exact.provenance.request_id,
            model="other-model",
        )
    else:
        candidate = _directive("other-provider-request")

    payload = encode_model_directive(candidate)
    fingerprint = runtime.background_model_attempts._response_fingerprint(candidate)
    with pytest.raises(BackgroundModelResponseConflict):
        runtime.stage_exact_background_response(
            work_kind="wake",
            work_id=signal.wake_id,
            model_round_index=0,
            provider=candidate.provenance.provider,
            model=candidate.provenance.model,
            provider_request_id=candidate.provenance.request_id,
            response_fingerprint=fingerprint,
            directive_payload=payload,
            staged_at=NOW + timedelta(minutes=1),
            evidence="tampered trusted-return bundle",
            authenticity_proof=proof,
        )

    after = runtime.background_model_attempts.get(attempt.attempt_id)
    assert after is not None
    assert after.state == "dispatching"
    assert after.provider is None
    assert after.model is None
    assert after.provider_request_id is None
    assert after.response_fingerprint is None
    assert runtime.background_model_attempts.staged_response(attempt.attempt_id) is None
    assert runtime.metering.list_model_calls(
        subject_id=runtime.subject_id, wake_id=signal.wake_id
    ) == ()
    assert int(store.current_world_revision()) == revision_before


@pytest.mark.parametrize("tamper_target", ("staged-proof", "receipt-payload"))
def test_durable_proof_is_reverified_before_recovered_response_application(
    tmp_path, tamper_target
):
    store, _index, _db, runtime, signal, attempt, exact, receipt = (
        _crash_after_trusted_receipt(tmp_path, key=f"apply-{tamper_target}")
    )
    _stage(runtime, signal, exact, receipt)
    revision_before = int(store.current_world_revision())

    with store._connection() as conn:
        if tamper_target == "staged-proof":
            conn.execute(
                """
                UPDATE background_model_responses
                SET authenticity_proof=?
                WHERE attempt_id=?
                """,
                ("bgresponse_v1_" + "0" * 64, attempt.attempt_id),
            )
        else:
            conn.execute(
                """
                UPDATE background_model_response_receipts
                SET payload_sha256=?
                WHERE attempt_id=?
                """,
                ("0" * 64, attempt.attempt_id),
            )
        conn.commit()

    runtime.cognitive_runtime.model_handler = lambda _snapshot: pytest.fail(
        "tampered recovery must not call the provider"
    )
    with pytest.raises(BackgroundModelResponseConflict):
        runtime.run_wake(
            wake_ref=_wake_ref(signal), now=NOW + timedelta(minutes=2)
        )

    assert runtime.metering.list_model_calls(
        subject_id=runtime.subject_id, wake_id=signal.wake_id
    ) == ()
    assert int(store.current_world_revision()) == revision_before
