"""Later-round exact provider return must survive process loss (Route B).

TIGHTEN_ONLY history (Corrective-003 / Window 22-RERUN-001).

Old expectation
    ``crash_at_return`` ran a live turn with NO external authority and asserted
    that, after the crash, ``response_authenticity_receipt(...)`` was already not
    None -- i.e. that the *live local handler return had itself minted* a durable
    trusted receipt + exact handoff, which a fresh process then replayed with zero
    provider calls and no external proof.

Old authority mechanism
    ``BackgroundModelAttemptStore.record_live_provider_return`` driven by
    ``live_return.open_live_provider_return_window`` +
    ``register_handler_return``.

Why that mechanism is unsafe (BLK-W20-001)
    ``RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW``
    / ``TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE``: window issuance
    was an ordinary public function, so any process-local recovery caller could
    issue its own window, declare its own bytes handler-returned, mint the receipt
    + handoff this file used to assert on, complete and meter an attempt that must
    have stayed ``in_doubt``, and poison a later genuine RSA trusted return.

Replacement route
    Route B.  The live local return now mints nothing durable -- asserted
    explicitly below (no receipt, no handoff, no staged response after the crash).
    Durable trusted return is produced only by a verifier bound before the provider
    boundary plus a genuine external RSA proof attached through
    ``BackgroundModelAttemptStore.attach_late_trusted_return``.  The external
    private key is TEST-ONLY material owned by the "external side"; Core persists
    only the public verifier.

Deleted / kept / equal-or-stronger
    Deleted: the assertion that a receipt exists purely because a local handler
    returned bytes.
    Added (strictly stronger): the live frame is now mechanically asserted to
    create ZERO trusted-return rows, and the recovered bytes must be re-proved
    from a genuine external signature over the durable request binding.
    Kept (unchanged): zero provider redispatch on recovery, exactly-once
    completion, one meter per round, capability effects not duplicated, turn
    execution completed, ``TurnAlreadyCompleted`` on rerun, and every tamper /
    cross-identity case in
    ``test_core_background_trusted_return_adversarial_001.py`` which consumes this
    harness.
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
from aios_core.runtime.background_attempt import (
    BackgroundModelResponseConflict, encode_model_directive,
)
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.late_return import LateReturnVerifier, late_return_message
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
# TEST-ONLY external authority material.  The RSA private exponent below belongs
# to the simulated external signer, never to Core: Core persists only the public
# verifier row.  Reused from the frozen Corrective-001 Route B probe module so the
# whole repository exercises one external key identity.
from test_core_background_late_trusted_return_corrective_001 import (
    _RSA_D, _RSA_E, _RSA_N, _SHA256_DER,
)


def route_b_verifier(key_id="route-b-recovery-external-key"):
    """Public half of the external authority, bound durably before dispatch."""

    return LateReturnVerifier(
        key_id=key_id,
        algorithm="rsa-pkcs1v15-sha256",
        modulus_hex=f"{_RSA_N:x}",
        public_exponent=_RSA_E,
    )


class RouteBExternalSigner:
    """Simulated external side: receives public scope, keeps all private authority."""

    def __init__(self):
        self.contexts = {}

    def accept_return_context(self, snapshot, context):
        assert snapshot.model_attempt_id == context.attempt_id
        self.contexts[context.attempt_id] = context

    def proof(self, attempt_id, returned, **overrides):
        from aios_core.runtime.late_return import LATE_RETURN_PROOF_PREFIX

        context = self.contexts[attempt_id]
        payload = encode_model_directive(returned)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        fields = {
            **context.scope_fields(),
            "provider": returned.provenance.provider,
            "model": returned.provenance.model,
            "provider_request_id": returned.provenance.request_id,
            "response_fingerprint": digest,
            "payload_sha256": digest,
        }
        fields.update(overrides)
        message = late_return_message(**fields)
        digest_info = _SHA256_DER + hashlib.sha256(message).digest()
        size = (_RSA_N.bit_length() + 7) // 8
        padding = b"\xff" * (size - len(digest_info) - 3)
        encoded = b"\x00\x01" + padding + b"\x00" + digest_info
        signature = pow(
            int.from_bytes(encoded, "big"), _RSA_D, _RSA_N
        ).to_bytes(size, "big")
        return f"{LATE_RETURN_PROOF_PREFIX}{context.verifier_key_id}:{signature.hex()}"


def trust_row_counts(db, attempt_id):
    """(receipts, handoffs, staged responses) for one attempt."""

    with sqlite3.connect(db) as conn:
        return tuple(
            conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE attempt_id=?", (attempt_id,)
            ).fetchone()[0]
            for table in (
                "background_model_response_receipts",
                "background_model_return_handoffs",
                "background_model_responses",
            )
        )

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


def crash_before_local_completion(tmp_path, last_round):
    """Crash after the durable dispatch boundary, BEFORE any local completion.

    Route B: this leaves ZERO local trusted-return state for the crashed round.
    The attempt is durably ``dispatching`` and can only ever return through a
    genuine external proof.  Returned so that adversarial tests can attack the
    pre-proof window directly.
    """

    db = tmp_path / "world.db"
    store, index = world(db)
    seed_anchor(store)
    index.catch_up()
    calls = []
    signer = RouteBExternalSigner()

    def provider(snapshot):
        calls.append(snapshot.round_index)
        return directive(snapshot.round_index, call=watch_call(snapshot.round_index) if snapshot.round_index < last_round else None)

    runtime = FusedTurnRuntime(
        store=store, index=index, model_handler=provider,
        late_return_verifier=route_b_verifier(),
        external_return_observer=signer,
    )
    original = runtime.cognitive_runtime.model_response_recorder

    def stop_after_dispatch(snapshot, returned):
        if snapshot.round_index == last_round:
            raise ProcessDeath("crash before response provenance / semantic application")
        original(snapshot, returned)

    runtime.cognitive_runtime.model_response_recorder = stop_after_dispatch
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
    target = attempts[-1].attempt_id

    # Route B invariant: the live local handler return minted NOTHING durable.
    assert runtime.background_model_attempts.staged_response(target) is None
    assert runtime.background_model_attempts.response_authenticity_receipt(target) is None
    assert trust_row_counts(db, target) == (0, 0, 0)
    # Earlier rounds completed live without any trusted-return row either.
    for earlier in attempts[:-1]:
        assert trust_row_counts(db, earlier.attempt_id) == (0, 0, 0)
        assert runtime.background_model_attempts.response_authenticity_receipt(
            earlier.attempt_id
        ) is None

    return db, runtime, attempts, signer, execution_id


def crash_at_return_with_signer(tmp_path, last_round):
    """Crash after the durable dispatch boundary, then prove the return externally.

    The receipt and exact handoff the rest of this file (and the adversarial file
    that consumes this harness) rely on are produced only by a genuine external RSA
    signature over the durable request binding, attached through the frozen
    external verifier path -- never by the live local handler return.
    """

    db, runtime, attempts, signer, execution_id = crash_before_local_completion(
        tmp_path, last_round
    )
    target = attempts[-1].attempt_id

    # The only route to durable trusted return: a genuine external proof.
    returned = directive(last_round)
    runtime.background_model_attempts.attach_late_trusted_return(
        target,
        attached_at=NOW + timedelta(seconds=1),
        directive_payload=encode_model_directive(returned),
        late_return_proof=signer.proof(target, returned),
        evidence="genuine external Route B return observed after process loss",
    )
    receipt = runtime.background_model_attempts.response_authenticity_receipt(target)
    assert receipt is not None
    assert trust_row_counts(db, target) == (1, 1, 1)
    return db, runtime, attempts, receipt, execution_id, signer


def crash_at_return(tmp_path, last_round):
    db, runtime, attempts, receipt, execution_id, _signer = crash_at_return_with_signer(
        tmp_path, last_round
    )
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
    meters = fresh.metering.list_model_calls(subject_id="user_1")
    assert len(meters) == last_round + 1
    assert [m.background_attempt_id for m in sorted(meters, key=lambda m: m.model_round_index)] == [a.attempt_id for a in attempts]
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
    assert len(fresh.metering.list_model_calls(subject_id="user_1")) == last_round + 1


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
    assert len(runtime.metering.list_model_calls(subject_id="user_1")) == 1
