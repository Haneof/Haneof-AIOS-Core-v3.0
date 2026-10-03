"""Background model attempt store unit invariants (Route B).

TIGHTEN_ONLY history (Corrective-003 / Window 22-RERUN-001).

Old expectation
    ``_trusted_attempt`` produced a durable trusted receipt by calling
    ``capture_live_provider_return`` -> the ephemeral live provider-return window ->
    ``BackgroundModelAttemptStore.record_live_provider_return``, and one pre-submission
    retry test called the same helper incidentally before ``record_response``.

Old authority mechanism
    ``live_return.open_live_provider_return_window`` / ``register_handler_return`` +
    ``record_live_provider_return``.

Why that mechanism is unsafe (BLK-W20-001)
    ``RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW`` /
    root cause ``TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE``: window
    issuance was an ordinary public function, so any process-local recovery caller
    could self-issue a window, declare its own bytes handler-returned and mint a
    durable trusted receipt + handoff.

Replacement route
    Route B.  A trusted receipt in these unit tests is now produced only by a genuine
    external RSA signature over Core's durable pre-dispatch request binding, verified
    with public material only and attached through
    ``BackgroundModelAttemptStore.attach_late_trusted_return``.  The verifier is bound
    through the ordinary public ``mark_dispatching(late_return_verifier=...)`` path and
    the public signing scope is read back with ``late_return_signing_context``.  The
    RSA private exponent below is TEST-ONLY external authority material; Core never
    sees it.  It is duplicated here rather than imported from ``tests/integration`` so
    that this directory stays runnable on its own.

Deleted / kept / equal-or-stronger
    Deleted: the incidental live-mint call in the pre-submission retry test (it
    asserted nothing) -- replaced by an explicit assertion that the live completion
    minted NO receipt, handoff or staged response.
    Kept unchanged: every cross-identity receipt-replay refusal (cross work+attempt,
    cross work kind, cross subject, cross round), the "proof is invalid" match, the
    metadata-only reconciliation refusal, and all pre-submission retry identity /
    non-world-revision invariants.
    Strengthened: the cross-identity target is now itself genuinely externally proven,
    so the refusal is proved against a *valid* receipt of a different identity rather
    than against a locally self-minted one.
"""

from datetime import datetime, timedelta, timezone

import pytest

from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptStore,
    BackgroundModelExecutionInDoubt,
    BackgroundModelResponseConflict,
    encode_model_directive,
)
from aios_core.runtime.cognitive_runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
)
import hashlib

from aios_core.runtime.late_return import (
    LATE_RETURN_PROOF_PREFIX,
    LateReturnVerifier,
    late_return_message,
)
from aios_core.runtime.metering import ModelMeteringLedger
from aios_core.storage.sqlite_store import SQLiteWorldStore


NOW = datetime(2026, 9, 24, 6, 0, tzinfo=timezone.utc)

# TEST-ONLY external authority material.  The private exponent belongs to the
# simulated external signer, never to Core: Core persists and verifies with the
# public half only.  Identical to the integration Route B harness so the whole
# repository exercises one external key identity.
_RSA_N = int(
    "f0d13bbf304da61eac4461bc8cd74d124b711b43092ca325c842452027ad9772"
    "49d5246a0b9ca215a62bac1461f1f618526cc2755cf1b4e988dd9e6db0996b0e"
    "970e8ed70b9a19507f3dff5f57738e72ac9d88861d0a628dcec6f75a75676fa6"
    "55eea0ba0d57a9f8d6c3cead1bdb28600322155de8b52a901e9774c70fff26c8"
    "42a0c3588fccf402553e93d7313a3537336e8387bb86b2094ed02669bdb239a3"
    "ac1545e9fe4d32ba20bbd0384457516e4cf66d730bbffc346ba6cdf45e2f2b40"
    "039488880794dec8d87f020a683d4e2e904ed4cf5ff71126f1b5afce184aab46"
    "fa00e8abb7561bda80d9eb07b3e3f4ae77ef41e904d0d6046f635abc072d81bb",
    16,
)
_RSA_D = int(
    "10df98401d3253a1729098088e15c7e0b0488c9075e41aca5aedc9ca26fd92ce"
    "ff3d5fffce307b6ae8e9c674e727fd065740279ff1933e09defd284ca74318ad3"
    "d085819d94642dfd10a970a272681a4a753a26d433ba70c28a0e853fe45f11cc"
    "688a1da6774ed03f28865c2db60cfc36a74c8ea7b93b617c30cf9b1b8fd37ca"
    "4d95137f1deb459720bca1c3a56d52a70b178cdc1fc645a49ced075fc2f2d87b"
    "da9150cdea71d1e2c360d95211cc97c703ec38db443c3b31b5d7e197ae6785c4"
    "afff79efc98b684d7cebf129189d89ee51f2115df40217be44465a2c79393bb2"
    "f126f920c9fab3283196c859d08f24eae952be5ba02f92e8683bb8249352df81",
    16,
)
_RSA_E = 65537
_SHA256_DER = bytes.fromhex("3031300d060960864801650304020105000420")
_ROUTE_B_KEY_ID = "route-b-unit-external-key"


def route_b_verifier() -> LateReturnVerifier:
    """Public half of the external authority, bound durably before dispatch."""

    return LateReturnVerifier(
        key_id=_ROUTE_B_KEY_ID,
        algorithm="rsa-pkcs1v15-sha256",
        modulus_hex=f"{_RSA_N:x}",
        public_exponent=_RSA_E,
    )


def external_proof(context, directive: ModelDirective) -> str:
    """Sign Core's durable public request scope plus the exact returned bytes."""

    payload = encode_model_directive(directive)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    message = late_return_message(
        **context.scope_fields(),
        provider=directive.provenance.provider,
        model=directive.provenance.model,
        provider_request_id=directive.provenance.request_id,
        response_fingerprint=digest,
        payload_sha256=digest,
    )
    digest_info = _SHA256_DER + hashlib.sha256(message).digest()
    size = (_RSA_N.bit_length() + 7) // 8
    encoded = (
        b"\x00\x01"
        + b"\xff" * (size - len(digest_info) - 3)
        + b"\x00"
        + digest_info
    )
    signature = pow(int.from_bytes(encoded, "big"), _RSA_D, _RSA_N).to_bytes(size, "big")
    return f"{LATE_RETURN_PROOF_PREFIX}{context.verifier_key_id}:{signature.hex()}"


def attach_external_trusted_return(
    attempts: BackgroundModelAttemptStore,
    attempt_id: str,
    *,
    attached_at: datetime,
    directive: ModelDirective,
):
    """Produce a durable trusted receipt the only way Route B allows.

    Corrective-003 history note.  These tests used to call
    ``BackgroundModelAttemptStore._capture_trusted_response_return`` (removed by
    Window 17 ``BLK-W17-001``) and then the ephemeral live provider-return window
    plus ``record_live_provider_return`` (removed by Window 20 ``BLK-W20-001``).
    Both were recovery-reachable minting oracles.  The route below requires a
    verifier bound before dispatch and a genuine external signature over Core's
    durable request binding; no local caller can manufacture either.
    """

    context = attempts.late_return_signing_context(attempt_id)
    assert context is not None, "no external verifier was bound before dispatch"
    attempts.attach_late_trusted_return(
        attempt_id,
        attached_at=attached_at,
        directive_payload=encode_model_directive(directive),
        late_return_proof=external_proof(context, directive),
        evidence="genuine external Route B return",
    )
    return attempts.response_authenticity_receipt(attempt_id)


def test_background_attempt_pre_submission_retry_keeps_identity_and_non_world_revision(tmp_path):
    """A genuine pre-submission failure may retry; no dispatch fact is rotated."""

    store = SQLiteWorldStore(tmp_path / "world.db")
    attempts = BackgroundModelAttemptStore(store)
    ledger = ModelMeteringLedger(store)
    before = int(store.current_world_revision())

    admitted = attempts.admit(
        subject_id="user_1",
        work_kind="wake",
        work_id="wake_attempt_unit",
        wake_reason="watch_match",
        model_round_index=0,
        world_revision=before,
        admitted_at=NOW,
    )
    not_submitted = attempts.mark_failure(
        admitted.attempt_id,
        failed_at=NOW,
        definitely_not_submitted=True,
        error=RuntimeError("mechanically pre-submission"),
    )
    assert not_submitted.state == "not_submitted"
    assert attempts.outbound_request_binding(admitted.attempt_id) is None

    retry = attempts.admit(
        subject_id="user_1",
        work_kind="wake",
        work_id="wake_attempt_unit",
        wake_reason="watch_match",
        model_round_index=0,
        world_revision=before,
        admitted_at=NOW,
    )
    assert retry.attempt_id == admitted.attempt_id
    dispatched = attempts.mark_dispatching(
        retry.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint="unit-first-real-outbound-request",
    )
    assert dispatched.state == "dispatching"

    directive = ModelDirective(
        silence=True,
        usage=ModelUsage(
            input_tokens=3,
            output_tokens=1,
            total_tokens=4,
            provider="provider",
            model="model",
            request_id="request-unit",
        ),
        provenance=ModelCallProvenance(
            provider="provider",
            model="model",
            request_id="request-unit",
        ),
    )
    # Route B: the incidental live-mint call that used to sit here is gone.  A live
    # local completion authenticates itself and mints no durable trusted state.
    returned = attempts.record_response(
        retry.attempt_id,
        returned_at=NOW,
        directive=directive,
    )
    assert returned.state == "response_returned"
    assert attempts.response_authenticity_receipt(retry.attempt_id) is None
    assert attempts.staged_response(retry.attempt_id) is None
    with store._connection() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM background_model_return_handoffs WHERE attempt_id=?",
            (retry.attempt_id,),
        ).fetchone()[0] == 0

    meter = ledger.record_model_call(
        subject_id="user_1",
        world_revision=before,
        recorded_at=NOW,
        execution_class="background",
        wake_id="wake_attempt_unit",
        wake_reason="watch_match",
        model_round_index=0,
        usage=directive.usage,
        provenance=directive.provenance,
        background_attempt_id=retry.attempt_id,
    )
    closed = attempts.get(retry.attempt_id)
    assert closed is not None and closed.state == "metered"
    assert closed.meter_record_id == meter.record_id
    assert int(store.current_world_revision()) == before


def test_background_attempt_post_binding_not_submitted_is_refused_and_in_doubt(tmp_path):
    """C4/C5 Route B: caller booleans/evidence cannot erase a durable binding."""

    store = SQLiteWorldStore(tmp_path / "world.db")
    attempts = BackgroundModelAttemptStore(store)
    admitted = attempts.admit(
        subject_id="user_1",
        work_kind="wake",
        work_id="route-b-post-binding",
        wake_reason="watch_match",
        model_round_index=0,
        world_revision=int(store.current_world_revision()),
        admitted_at=NOW,
    )
    attempts.mark_dispatching(
        admitted.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint="route-b-first-request",
    )
    first_binding = attempts.outbound_request_binding(admitted.attempt_id)
    assert first_binding is not None

    with pytest.raises(BackgroundModelResponseConflict):
        attempts.mark_failure(
            admitted.attempt_id,
            failed_at=NOW + timedelta(seconds=1),
            definitely_not_submitted=True,
            error=RuntimeError("caller claims not submitted"),
        )
    durable = attempts.get(admitted.attempt_id)
    assert durable is not None and durable.state == "in_doubt"

    with pytest.raises(BackgroundModelResponseConflict):
        attempts.reconcile_not_submitted(
            admitted.attempt_id,
            reconciled_at=NOW + timedelta(seconds=2),
            evidence="operator says provider did not accept it",
        )
    durable = attempts.get(admitted.attempt_id)
    assert durable is not None and durable.state == "in_doubt"

    with pytest.raises(BackgroundModelExecutionInDoubt):
        attempts.admit(
            subject_id="user_1",
            work_kind="wake",
            work_id="route-b-post-binding",
            wake_reason="watch_match",
            model_round_index=0,
            world_revision=int(store.current_world_revision()),
            admitted_at=NOW + timedelta(seconds=3),
        )

    second_binding = attempts.outbound_request_binding(admitted.attempt_id)
    assert second_binding == first_binding


def _trusted_attempt(
    attempts: BackgroundModelAttemptStore,
    *,
    subject_id: str,
    work_kind: str,
    work_id: str,
    round_index: int,
    request_id: str,
):
    attempt = attempts.admit(
        subject_id=subject_id,
        work_kind=work_kind,
        work_id=work_id,
        wake_reason="trusted-return-unit",
        model_round_index=round_index,
        world_revision=0,
        admitted_at=NOW,
    )
    attempts.mark_dispatching(
        attempt.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint=(
            f"outbound:{subject_id}:{work_kind}:{work_id}:{round_index}"
        ),
        late_return_verifier=route_b_verifier(),
    )
    directive = ModelDirective(
        response=f"response for {request_id}",
        usage=ModelUsage(
            input_tokens=2,
            output_tokens=2,
            total_tokens=4,
            provider="provider",
            model="model",
            request_id=request_id,
        ),
        provenance=ModelCallProvenance(
            provider="provider",
            model="model",
            request_id=request_id,
        ),
    )
    receipt = attach_external_trusted_return(
        attempts,
        attempt.attempt_id,
        attached_at=NOW + timedelta(seconds=1),
        directive=directive,
    )
    assert receipt is not None
    return attempt, directive, receipt


@pytest.mark.parametrize(
    "target_identity",
    (
        pytest.param(
            ("subject-a", "wake", "work-b", 0), id="cross-work-and-attempt"
        ),
        pytest.param(
            ("subject-a", "periodic_review", "work-a", 0), id="cross-work-kind"
        ),
        pytest.param(("subject-b", "wake", "work-a", 0), id="cross-subject"),
        pytest.param(("subject-a", "wake", "work-a", 1), id="cross-round"),
    ),
)
def test_trusted_receipt_proof_cannot_replay_across_bound_identity(
    tmp_path, target_identity
):
    store = SQLiteWorldStore(tmp_path / "world.db")
    attempts = BackgroundModelAttemptStore(store)
    _source, _source_directive, source_receipt = _trusted_attempt(
        attempts,
        subject_id="subject-a",
        work_kind="wake",
        work_id="work-a",
        round_index=0,
        request_id="source-request",
    )
    target, target_directive, _target_receipt = _trusted_attempt(
        attempts,
        subject_id=target_identity[0],
        work_kind=target_identity[1],
        work_id=target_identity[2],
        round_index=target_identity[3],
        request_id="target-request",
    )
    payload = encode_model_directive(target_directive)

    with pytest.raises(BackgroundModelResponseConflict, match="proof is invalid"):
        attempts.stage_exact_response(
            target.attempt_id,
            staged_at=NOW + timedelta(seconds=2),
            provider="provider",
            model="model",
            provider_request_id="target-request",
            response_fingerprint=attempts._response_fingerprint(target_directive),
            directive_payload=payload,
            authenticity_proof=source_receipt.authenticity_proof,
            evidence="attempted cross-identity receipt replay",
        )

    unchanged = attempts.get(target.attempt_id)
    assert unchanged is not None
    # Route B: the target is itself genuinely externally proven, so the refused
    # cross-identity replay must leave its verified provenance and staged bytes
    # exactly as the genuine proof wrote them -- never the source attempt's.
    assert unchanged.state == "response_returned"
    assert unchanged.provider == "provider"
    assert unchanged.model == "model"
    assert unchanged.provider_request_id == "target-request"
    assert unchanged.response_fingerprint == attempts._response_fingerprint(
        target_directive
    )
    staged = attempts.staged_response(target.attempt_id)
    assert staged is not None
    assert staged.directive_payload == payload
    assert staged.authenticity_proof == _target_receipt.authenticity_proof
    assert staged.authenticity_proof != source_receipt.authenticity_proof


def test_metadata_only_reconciliation_cannot_bypass_authenticity(tmp_path):
    store = SQLiteWorldStore(tmp_path / "world.db")
    attempts = BackgroundModelAttemptStore(store)
    attempt = attempts.admit(
        subject_id="subject-a",
        work_kind="wake",
        work_id="metadata-only",
        wake_reason="trusted-return-unit",
        model_round_index=0,
        world_revision=0,
        admitted_at=NOW,
    )
    attempts.mark_dispatching(
        attempt.attempt_id,
        dispatched_at=NOW,
        outbound_request_fingerprint="metadata-only-outbound",
    )

    with pytest.raises(BackgroundModelResponseConflict, match="metadata-only"):
        attempts.reconcile_response(
            attempt.attempt_id,
            reconciled_at=NOW + timedelta(seconds=1),
            provider="provider",
            model="model",
            provider_request_id="caller-request",
            response_fingerprint="caller-computable-fingerprint",
            evidence="caller-controlled evidence",
        )

    unchanged = attempts.get(attempt.attempt_id)
    assert unchanged is not None
    assert unchanged.state == "dispatching"
    assert unchanged.provider is None
    assert unchanged.response_fingerprint is None
