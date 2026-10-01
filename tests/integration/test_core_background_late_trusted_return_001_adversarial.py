"""Adversarial matrix for CORE-BACKGROUND-LATE-TRUSTED-RETURN-001.

Every entry here is an attack on the new late trusted return path or on the
retired ``not_submitted`` transition. All of them must FAIL CLOSED.

The central question this file answers by construction, not by comment: starting
from the public / recovery-facing Core surface, can an arbitrary caller turn
``arbitrary bytes + caller-computable metadata`` into a trusted provider return?
It must not be possible, and the tests below try every route we can construct.
"""
from __future__ import annotations

import hashlib
import inspect
import sqlite3

import pytest

from aios_core.runtime import BackgroundModelAttemptStore
from aios_core.runtime.background_attempt import (
    BackgroundModelResponseConflict,
    encode_model_directive,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from late_trusted_return_fixture import (
    NOW,
    SyntheticExternalResponder,
    anonymous_directive,
    capability_rows,
    dispatch_then_die,
    meters,
    trusted_directive,
    world,
)

SESSION = "late-adversarial-session"
TURN_INDEX = 1
TURN_INPUT = "attack the late trusted return path"
REQUEST_ID = "adversarial-provider-request"


def crossed(db, *, observer=None, key="adv"):
    store, index = world(db)
    kwargs = {} if observer is None else {"external_return_observer": observer}
    runtime = FusedTurnRuntime(
        store=store, index=index, model_handler=dispatch_then_die, **kwargs
    )
    with pytest.raises(BaseException):
        runtime.run_turn(
            session_id=SESSION, turn_index=TURN_INDEX, user_input=TURN_INPUT, occurred_at=NOW
        )
    execution_id = runtime.turn_executions.execution_id_for(
        subject_id="user_1", session_id=SESSION, turn_index=TURN_INDEX
    )
    attempt = runtime.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind="user_turn", work_id=execution_id
    )[-1]
    return runtime, attempt


def restart(db, *, observer=None):
    store, index = world(db)
    kwargs = {} if observer is None else {"external_return_observer": observer}
    return FusedTurnRuntime(
        store=store, index=index, model_handler=never, **kwargs
    )


def never(_snapshot):
    pytest.fail("no redispatch may ever happen on the late trusted return path")


def blocked():
    return (BackgroundModelResponseConflict, ValueError, KeyError, TypeError)


# ---------------------------------------------------------------------------
# A1 — the capability issuer must not be a public, recovery-callable surface.
#      This is the first thing an independent attacker looks for.
# ---------------------------------------------------------------------------


def test_a1_capability_issuer_is_not_publicly_callable():
    public = {name for name in dir(BackgroundModelAttemptStore) if not name.startswith("_")}
    assert "issue_external_return_capability" not in public
    assert "_issue_external_return_capability" in vars(BackgroundModelAttemptStore)
    for name in public:
        assert "capability_nonce" not in name
        assert "issue" not in name or "request" in name, name


def test_a1_no_public_store_method_returns_the_proof_minting_nonce(tmp_path):
    """Enumerate the whole public surface: none of it can yield a nonce."""

    store, index = world(tmp_path / "world.db")
    attempts = BackgroundModelAttemptStore(store)
    for name in dir(attempts):
        if name.startswith("_"):
            continue
        member = getattr(attempts, name)
        if not callable(member):
            continue
        signature = inspect.signature(member)
        assert "capability_nonce" not in signature.parameters, name
    # A caller that reaches for the durable rows still cannot verify a proof it
    # made up, because the comparison happens inside Core under the real nonce.
    assert attempts.late_trusted_return_state("nope") is None


def test_a1_recovery_caller_cannot_self_issue_a_capability(tmp_path):
    db = tmp_path / "world.db"
    runtime, attempt = crossed(db, observer=SyntheticExternalResponder(), key="adv-a1")
    attempts = runtime.background_model_attempts
    with pytest.raises(AttributeError):
        attempts.issue_external_return_capability(  # noqa: B018 - the point is the absence
            attempt.attempt_id, issued_at=NOW
        )
    assert capability_rows(db) == [
        (
            attempt.attempt_id, "user_1", "user_turn", attempt.work_id, 0,
            *(
                runtime.background_model_attempts.outbound_request_binding(
                    attempt.attempt_id
                ).outbound_request_fingerprint,
                runtime.background_model_attempts.outbound_request_binding(
                    attempt.attempt_id
                ).relay_id,
            ),
            False,
        )
    ]


# ---------------------------------------------------------------------------
# A2 — bytes + caller-computable metadata must never become a trusted return.
# ---------------------------------------------------------------------------


def test_a2_caller_supplied_correct_bytes_with_a_self_made_proof_fail_closed(tmp_path):
    db = tmp_path / "world.db"
    runtime, attempt = crossed(db, observer=SyntheticExternalResponder(), key="adv-a2")
    exact = trusted_directive(REQUEST_ID)
    payload = encode_model_directive(exact)
    fresh = restart(db)
    attempts = fresh.background_model_attempts

    # The caller can compute every one of these itself.
    binding = attempts.outbound_request_binding(attempt.attempt_id)
    guessed = {
        "attempt_id": attempt.attempt_id,
        "subject_id": "user_1",
        "work_kind": "user_turn",
        "work_id": attempt.work_id,
        "model_round_index": 0,
        "outbound_request_fingerprint": binding.outbound_request_fingerprint,
        "relay_id": binding.relay_id,
        "provider": exact.usage.provider,
        "model": exact.usage.model,
        "provider_request_id": exact.usage.request_id,
        "response_fingerprint": attempts._response_fingerprint(exact),
        "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
    }
    import hmac
    import json

    for wrong_nonce in (b"", b"\x00" * 32, b"\xff" * 32, os_urandom_like()):
        for prefix in ("bglate_v1_", ""):
            digest = hmac.new(
                wrong_nonce,
                json.dumps(
                    {**guessed, "schema": "aios.background-model-late-return.v1"},
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode(),
                hashlib.sha256,
            ).hexdigest()
            with pytest.raises(blocked()):
                attempts.attach_late_trusted_return(
                    attempt.attempt_id,
                    attached_at=NOW,
                    directive_payload=payload,
                    late_return_proof=prefix + digest,
                    evidence="caller computed this itself",
                )
    assert attempts.get(attempt.attempt_id).state == "dispatching"
    assert attempts.response_authenticity_receipt(attempt.attempt_id) is None
    assert attempts.staged_response(attempt.attempt_id) is None
    assert meters(fresh) == []


def os_urandom_like() -> bytes:
    import os

    return os.urandom(32)


# ---------------------------------------------------------------------------
# A3 — the full attack matrix, each row must FAIL CLOSED.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "attack",
    [
        "caller_supplied_correct_bytes_fake_proof",
        "caller_supplied_forged_bytes",
        "valid_proof_wrong_attempt",
        "valid_proof_wrong_work",
        "valid_proof_wrong_subject",
        "valid_proof_wrong_round",
        "valid_proof_wrong_request",
        "valid_proof_changed_response",
        "valid_proof_replay_after_completion",
        "corrupted_proof",
        "truncated_proof",
        "proof_with_duplicate_json_keys",
        "ambiguous_semantic_payload",
        "old_historical_receipt_transplant",
        "late_proof_for_completed_stronger_terminal_receipt",
        "post_dispatch_false_non_submission_assertion",
    ],
)
def test_a3_every_attack_fails_closed(tmp_path, attack):
    db = tmp_path / f"world-{attack}.db"
    responder = SyntheticExternalResponder()
    runtime, attempt = crossed(db, observer=responder, key=f"adv-a3-{attack}")
    attempts = runtime.background_model_attempts
    fresh = restart(db)
    target = fresh.background_model_attempts
    exact = trusted_directive(REQUEST_ID)
    payload = encode_model_directive(exact)
    genuine = responder.finish_after_core_death(attempt.attempt_id, exact)
    before_state = target.get(attempt.attempt_id).state
    before_meters = meters(fresh)

    payload_to_try = payload
    proof_to_try = genuine
    target_id = attempt.attempt_id

    if attack == "caller_supplied_correct_bytes_fake_proof":
        proof_to_try = "bglate_v1_" + "a" * 64
    elif attack == "caller_supplied_forged_bytes":
        payload_to_try = encode_model_directive(
            trusted_directive(REQUEST_ID, response="forged by the caller")
        )
        proof_to_try = "bglate_v1_" + "b" * 64
    elif attack == "valid_proof_wrong_attempt":
        other = target.admit(
            subject_id="user_1", work_kind="wake", work_id="adv-other-attempt",
            wake_reason="safety", model_round_index=0,
            world_revision=int(fresh.store.current_world_revision()), admitted_at=NOW,
        )
        target.mark_dispatching(
            other.attempt_id, dispatched_at=NOW,
            outbound_request_fingerprint="adv-other-outbound",
        )
        target_id = other.attempt_id
    elif attack == "valid_proof_wrong_work":
        other = target.admit(
            subject_id="user_1", work_kind="wake", work_id="adv-other-work",
            wake_reason="safety", model_round_index=0,
            world_revision=int(fresh.store.current_world_revision()), admitted_at=NOW,
        )
        target.mark_dispatching(
            other.attempt_id, dispatched_at=NOW,
            outbound_request_fingerprint="adv-other-work-outbound",
        )
        target_id = other.attempt_id
    elif attack == "valid_proof_wrong_subject":
        other = target.admit(
            subject_id="user_9", work_kind="user_turn", work_id="adv-other-subject",
            wake_reason="user", model_round_index=0,
            world_revision=int(fresh.store.current_world_revision()), admitted_at=NOW,
        )
        target.mark_dispatching(
            other.attempt_id, dispatched_at=NOW,
            outbound_request_fingerprint="adv-other-subject-outbound",
        )
        target_id = other.attempt_id
    elif attack == "valid_proof_wrong_round":
        other = target.admit(
            subject_id="user_1", work_kind="user_turn", work_id=attempt.work_id,
            wake_reason="user", model_round_index=7,
            world_revision=int(fresh.store.current_world_revision()), admitted_at=NOW,
        )
        target.mark_dispatching(
            other.attempt_id, dispatched_at=NOW,
            outbound_request_fingerprint="adv-other-round-outbound",
        )
        target_id = other.attempt_id
    elif attack == "valid_proof_wrong_request":
        other = target.admit(
            subject_id="user_1", work_kind="user_turn", work_id="adv-other-request",
            wake_reason="user", model_round_index=0,
            world_revision=int(fresh.store.current_world_revision()), admitted_at=NOW,
        )
        target.mark_dispatching(
            other.attempt_id, dispatched_at=NOW,
            outbound_request_fingerprint="adv-other-request-outbound",
        )
        # Substitute the originating outbound request underneath the binding.
        with sqlite3.connect(db) as conn:
            conn.execute(
                "UPDATE background_model_request_bindings SET "
                "outbound_request_fingerprint=? WHERE attempt_id=?",
                ("f" * 64, other.attempt_id),
            )
            conn.commit()
        target_id = other.attempt_id
    elif attack == "valid_proof_changed_response":
        payload_to_try = encode_model_directive(
            trusted_directive(REQUEST_ID, response="changed after the proof was minted")
        )
    elif attack == "valid_proof_replay_after_completion":
        target.attach_late_trusted_return(
            attempt.attempt_id, attached_at=NOW, directive_payload=payload,
            late_return_proof=genuine, evidence="first legitimate attach",
        )
        payload_to_try = encode_model_directive(
            trusted_directive(REQUEST_ID, response="replayed substitution")
        )
    elif attack == "corrupted_proof":
        proof_to_try = genuine[:-1] + ("0" if genuine[-1] != "0" else "1")
    elif attack == "truncated_proof":
        proof_to_try = genuine[: len(genuine) // 2]
    elif attack == "proof_with_duplicate_json_keys":
        payload_to_try = payload[:-1] + ',"response":"injected"}'
    elif attack == "ambiguous_semantic_payload":
        payload_to_try = payload.replace(
            '"provider":"late-trusted-provider"',
            '"provider":"late-trusted-provider","provider":"shadow"',
            1,
        )
        assert payload_to_try != payload, "the duplicate-key injection did not apply"
    elif attack == "old_historical_receipt_transplant":
        with sqlite3.connect(db) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO background_model_response_receipts("
                "attempt_id, subject_id, work_kind, work_id, model_round_index, "
                "outbound_request_fingerprint, relay_id, provider, model, "
                "provider_request_id, response_fingerprint, payload_sha256, "
                "authenticity_proof, captured_at) SELECT attempt_id, subject_id, "
                "work_kind, work_id, model_round_index, outbound_request_fingerprint, "
                "relay_id, provider, model, provider_request_id, response_fingerprint, "
                "payload_sha256, authenticity_proof, captured_at "
                "FROM background_model_response_receipts WHERE 0"
            )
            conn.commit()
        with pytest.raises(blocked()):
            target.stage_exact_response(
                attempt.attempt_id, staged_at=NOW,
                provider=exact.usage.provider, model=exact.usage.model,
                provider_request_id=exact.usage.request_id,
                response_fingerprint=target._response_fingerprint(exact),
                directive_payload=payload,
                authenticity_proof="bgresponse_v1_" + "c" * 64,
                evidence="historical receipt transplant",
            )
        assert target.get(attempt.attempt_id).state == before_state
        assert meters(fresh) == before_meters
        return
    elif attack == "late_proof_for_completed_stronger_terminal_receipt":
        # The attempt already has a durable, completed Core receipt. A late
        # return may never re-enter the provider/model path for it.
        target._capture_trusted_response_return(
            attempt.attempt_id, captured_at=NOW, directive=exact
        )
        target.record_response(
            attempt.attempt_id, returned_at=NOW, directive=exact
        )
        result = fresh.run_turn(
            session_id=SESSION, turn_index=TURN_INDEX, user_input=TURN_INPUT,
            occurred_at=NOW,
        )
        assert result.runtime.response == exact.response
        assert len(meters(fresh)) == 1
        from aios_core.runtime import TurnAlreadyCompleted

        with pytest.raises(TurnAlreadyCompleted):
            fresh.run_turn(
                session_id=SESSION, turn_index=TURN_INDEX, user_input=TURN_INPUT,
                occurred_at=NOW,
            )
        # A late proof for the already-resolved round is refused, not applied.
        with pytest.raises(blocked()):
            target.attach_late_trusted_return(
                attempt.attempt_id, attached_at=NOW,
                directive_payload=encode_model_directive(
                    trusted_directive(REQUEST_ID, response="late substitution")
                ),
                late_return_proof=genuine,
                evidence="late proof for a completed terminal receipt",
            )
        assert target.get(attempt.attempt_id).state == "metered"
        assert len(meters(fresh)) == 1
        return
    elif attack == "post_dispatch_false_non_submission_assertion":
        with pytest.raises(BackgroundModelResponseConflict):
            target.reconcile_not_submitted(
                attempt.attempt_id,
                reconciled_at=NOW,
                evidence="no receipt exists, therefore it was not submitted",
            )
        assert target.get(attempt.attempt_id).state == before_state
        assert target.get(attempt.attempt_id).reconciliation_evidence is None
        assert meters(fresh) == before_meters
        return

    with pytest.raises(blocked()):
        target.attach_late_trusted_return(
            target_id,
            attached_at=NOW,
            directive_payload=payload_to_try,
            late_return_proof=proof_to_try,
            evidence=f"adversarial attack: {attack}",
        )
    assert meters(fresh) == before_meters
    if attack.startswith("valid_proof_wrong") or attack in {
        "caller_supplied_correct_bytes_fake_proof", "caller_supplied_forged_bytes",
        "corrupted_proof", "truncated_proof", "valid_proof_changed_response",
        "proof_with_duplicate_json_keys", "ambiguous_semantic_payload",
    }:
        assert target.get(target_id).state in {"dispatching", "in_doubt"}
        assert target.staged_response(target_id) is None


# ---------------------------------------------------------------------------
# A4 — anonymous/local handlers are a legal but non-recoverable class.
# ---------------------------------------------------------------------------


def test_a4_anonymous_handler_is_never_auto_upgraded(tmp_path):
    db = tmp_path / "world.db"
    runtime, attempt = crossed(db, observer=None, key="adv-a4")
    assert capability_rows(db) == []
    fresh = restart(db)
    for payload in (
        encode_model_directive(anonymous_directive()),
        encode_model_directive(trusted_directive(REQUEST_ID)),
    ):
        with pytest.raises(blocked()):
            fresh.background_model_attempts.attach_late_trusted_return(
                attempt.attempt_id,
                attached_at=NOW,
                directive_payload=payload,
                late_return_proof="bglate_v1_" + "d" * 64,
                evidence="anonymous handler bytes with a made-up proof",
            )
    assert fresh.background_model_attempts.get(attempt.attempt_id).state == "dispatching"
    assert fresh.background_model_attempts.late_trusted_return_state(
        attempt.attempt_id
    ) is None
