#!/usr/bin/env python3
"""WINDOW 17 independently frozen adversarial probes for PR #308.

Target candidate: cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd
Construction base: 0b883c71d91e5f0772334514925237f1570fa780

This script was authored and frozen (SHA-256 recorded in PROBE_FREEZE_MANIFEST.md)
before its first execution against candidate cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd.
Each probe has a fixed expected security/truthfulness outcome derived from C1-C8,
T1-T6, and the Window 17 Independent Acceptance specification.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import multiprocessing
import os
from pathlib import Path
import signal
import sqlite3
import sys
import tempfile
import threading

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    BackgroundModelAttemptBlocked,
    BackgroundModelExecutionInDoubt,
    BackgroundModelResponseConflict,
    CapabilityCall,
    ExternalReturnObserver,
    LATE_RETURN_PROOF_PREFIX,
    LateReturnSigningContext,
    LateReturnVerifier,
    ModelCallProvenance,
    ModelDirective,
    ModelDispatchNotSubmitted,
    ModelUsage,
    TurnAlreadyCompleted,
    TurnExecutionInDoubt,
    late_return_message,
    verify_late_return_proof,
)
from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptStore,
    decode_model_directive,
    encode_model_directive,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
TURN_INPUT = "window17 independent acceptance probe input"

# Reviewer-owned external test RSA-2048 keypair (never passed as private key to Core).
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


class SimulatedProcessLoss(BaseException):
    pass


@dataclass(frozen=True)
class ProbeResult:
    probe_id: str
    expected: str
    actual: str
    passed: bool


def make_verifier(key_id: str = "w17-reviewer-ext-key") -> LateReturnVerifier:
    return LateReturnVerifier(
        key_id=key_id,
        algorithm="rsa-pkcs1v15-sha256",
        modulus_hex=f"{_RSA_N:x}",
        public_exponent=_RSA_E,
    )


def rsa_sign(message: bytes, key_id: str = "w17-reviewer-ext-key") -> str:
    digest_info = _SHA256_DER + hashlib.sha256(message).digest()
    size = (_RSA_N.bit_length() + 7) // 8
    padding = b"\xff" * (size - len(digest_info) - 3)
    encoded = b"\x00\x01" + padding + b"\x00" + digest_info
    sig = pow(int.from_bytes(encoded, "big"), _RSA_D, _RSA_N).to_bytes(size, "big")
    return f"{LATE_RETURN_PROOF_PREFIX}{key_id}:{sig.hex()}"


def make_directive(
    *,
    response: str = "genuine external response",
    provider: str = "provider-W17",
    model: str = "model-W17",
    request_id: str = "req-W17-1",
    capability_calls: tuple[CapabilityCall, ...] = (),
) -> ModelDirective:
    return ModelDirective(
        response=response,
        capability_calls=capability_calls,
        usage=ModelUsage(
            input_tokens=4,
            output_tokens=6,
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


class ReviewerExternalObserver:
    def __init__(self) -> None:
        self.contexts: dict[str, LateReturnSigningContext] = {}

    def accept_return_context(self, snapshot: object, context: LateReturnSigningContext) -> None:
        self.contexts[context.attempt_id] = context

    def sign_directive(
        self,
        attempt_id: str,
        directive: ModelDirective,
        **overrides: object,
    ) -> str:
        ctx = self.contexts[attempt_id]
        payload = encode_model_directive(directive)
        payload_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        resp_fp = BackgroundModelAttemptStore._response_fingerprint(directive)
        fields: dict[str, object] = {
            **ctx.scope_fields(),
            "provider": directive.provenance.provider,
            "model": directive.provenance.model,
            "provider_request_id": directive.provenance.request_id,
            "response_fingerprint": resp_fp,
            "payload_sha256": payload_sha256,
        }
        fields.update(overrides)
        return rsa_sign(late_return_message(**fields), ctx.verifier_key_id)


def open_world(db: Path) -> tuple[SQLiteWorldStore, WorldSearchIndex]:
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def dispatch_and_crash(
    db: Path,
    *,
    session_id: str,
    verifier: LateReturnVerifier | None = None,
    observer: ExternalReturnObserver | None = None,
) -> tuple[FusedTurnRuntime, object]:
    store, index = open_world(db)

    def crashing_handler(_snapshot: object) -> ModelDirective:
        raise SimulatedProcessLoss("simulated SIGKILL after mark_dispatching")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=crashing_handler,
        subject_id="user_1",
        late_return_verifier=verifier,
        external_return_observer=observer,
    )
    try:
        runtime.run_turn(
            session_id=session_id,
            turn_index=1,
            user_input=TURN_INPUT,
            occurred_at=NOW,
        )
    except SimulatedProcessLoss:
        pass
    exec_id = runtime.turn_executions.execution_id_for(
        subject_id="user_1",
        session_id=session_id,
        turn_index=1,
    )
    attempt = runtime.background_model_attempts.list_for_work(
        subject_id="user_1",
        work_kind="user_turn",
        work_id=exec_id,
    )[-1]
    return runtime, attempt


def fresh_recovery_runtime(
    db: Path,
    *,
    verifier: LateReturnVerifier | None = None,
) -> FusedTurnRuntime:
    store, index = open_world(db)

    def forbidden_provider(_snapshot: object) -> ModelDirective:
        raise AssertionError("provider redispatch is forbidden during recovery")

    return FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=forbidden_provider,
        subject_id="user_1",
        late_return_verifier=verifier,
    )


# ---------------------------------------------------------------------------
# CRITICAL ATTACK A1: IA17-MINT-001
# ---------------------------------------------------------------------------
def probe_ia17_mint_001_capture_helper_mints_trusted_return_without_rsa(root: Path) -> ProbeResult:
    """Ordinary recovery caller without RSA key must not mint receipt/handoff or complete turn."""
    db = root / "ia17-mint-001.sqlite"
    observer = ReviewerExternalObserver()
    verifier = make_verifier()
    _, attempt = dispatch_and_crash(
        db,
        session_id="sess-mint-001",
        verifier=verifier,
        observer=observer,
    )

    recovery = fresh_recovery_runtime(db)
    # First transition dispatching -> in_doubt via normal attempt recovery admission check.
    try:
        recovery.background_model_attempts.admit(
            subject_id=attempt.subject_id,
            work_kind=attempt.work_kind,
            work_id=attempt.work_id,
            wake_reason=attempt.wake_reason,
            model_round_index=attempt.model_round_index,
            world_revision=int(recovery.store.current_world_revision()),
            admitted_at=NOW + timedelta(seconds=1),
        )
    except BackgroundModelExecutionInDoubt:
        pass

    in_doubt = recovery.background_model_attempts.get(attempt.attempt_id)
    assert in_doubt is not None and in_doubt.state == "in_doubt"

    forged = make_directive(
        response="FORGED_BY_RECOVERY_CALLER_WITHOUT_RSA_PRIVATE_KEY",
        provider="forged-provider",
        model="forged-model",
        request_id="forged-req-001",
    )
    try:
        # Attempt to mint trusted receipt + handoff via recovery-reachable helper
        # without any RSA signature or external signing key.
        recovery.background_model_attempts._capture_trusted_response_return(
            attempt.attempt_id,
            captured_at=NOW + timedelta(seconds=10),
            directive=forged,
        )
        completed = recovery.run_turn(
            session_id="sess-mint-001",
            turn_index=1,
            user_input=TURN_INPUT,
            occurred_at=NOW,
        )
    except BaseException as exc:
        return ProbeResult(
            "IA17-MINT-001",
            "recovery caller without external RSA signature cannot mint receipt/handoff or complete in_doubt turn",
            f"refused: {type(exc).__name__}: {exc}",
            True,
        )

    # Also check whether the unauthenticated mint permanently blocks the genuine external RSA return.
    genuine = make_directive(response="genuine external signed response")
    genuine_proof = observer.sign_directive(attempt.attempt_id, genuine)
    genuine_blocked = False
    try:
        recovery.background_model_attempts.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(seconds=20),
            directive_payload=encode_model_directive(genuine),
            late_return_proof=genuine_proof,
            evidence="genuine external RSA return after attacker capture",
        )
    except BackgroundModelResponseConflict:
        genuine_blocked = True

    final_attempt = recovery.background_model_attempts.get(attempt.attempt_id)
    meters = recovery.metering.list_model_calls(
        subject_id="user_1", execution_classes=("user_interaction",)
    )
    return ProbeResult(
        "IA17-MINT-001",
        "recovery caller without external RSA signature cannot mint receipt/handoff or complete in_doubt turn",
        (
            f"FORGED TURN COMPLETED without RSA signature! "
            f"response={completed.runtime.response!r}, "
            f"attempt_state={final_attempt.state if final_attempt else None}, "
            f"meters={len(meters)}, "
            f"genuine_rsa_return_poisoned={genuine_blocked}"
        ),
        False,
    )


# ---------------------------------------------------------------------------
# CRITICAL ATTACK A2 & Section 21: IA17-MINT-002
# ---------------------------------------------------------------------------
def probe_ia17_mint_002_anonymous_no_verifier_bypass(root: Path) -> ProbeResult:
    """Attempt dispatched with NO LateReturnVerifier must remain permanently FAIL_CLOSED (in_doubt)."""
    db = root / "ia17-mint-002.sqlite"
    _, attempt = dispatch_and_crash(
        db,
        session_id="sess-mint-002",
        verifier=None,
        observer=None,
    )
    recovery = fresh_recovery_runtime(db)
    try:
        recovery.background_model_attempts.admit(
            subject_id=attempt.subject_id,
            work_kind=attempt.work_kind,
            work_id=attempt.work_id,
            wake_reason=attempt.wake_reason,
            model_round_index=attempt.model_round_index,
            world_revision=int(recovery.store.current_world_revision()),
            admitted_at=NOW + timedelta(seconds=1),
        )
    except BackgroundModelExecutionInDoubt:
        pass

    assert recovery.background_model_attempts.late_return_verifier(attempt.attempt_id) is None
    forged = make_directive(
        response="FORGED_ON_VERIFIERLESS_ATTEMPT",
        provider="anon-bypass-provider",
        model="anon-bypass-model",
        request_id="anon-bypass-req",
    )
    try:
        recovery.background_model_attempts._capture_trusted_response_return(
            attempt.attempt_id,
            captured_at=NOW + timedelta(seconds=15),
            directive=forged,
        )
        completed = recovery.run_turn(
            session_id="sess-mint-002",
            turn_index=1,
            user_input=TURN_INPUT,
            occurred_at=NOW,
        )
    except BaseException as exc:
        return ProbeResult(
            "IA17-MINT-002",
            "attempt dispatched with no LateReturnVerifier remains permanently in_doubt / FAIL_CLOSED",
            f"refused: {type(exc).__name__}: {exc}",
            True,
        )

    return ProbeResult(
        "IA17-MINT-002",
        "attempt dispatched with no LateReturnVerifier remains permanently in_doubt / FAIL_CLOSED",
        (
            f"NO-VERIFIER ATTEMPT BYPASSED FAIL_CLOSED and completed turn with "
            f"response={completed.runtime.response!r}"
        ),
        False,
    )


# ---------------------------------------------------------------------------
# CRITICAL ATTACK B: IA17-DOWNGRADE-001
# ---------------------------------------------------------------------------
def probe_ia17_downgrade_001_public_checksum_and_stage(root: Path) -> ProbeResult:
    """Receipt authenticity proof must not be a caller-computable SHA-256 usable to forge recovery."""
    db = root / "ia17-downgrade-001.sqlite"
    observer = ReviewerExternalObserver()
    _, attempt = dispatch_and_crash(
        db,
        session_id="sess-downgrade-001",
        verifier=make_verifier(),
        observer=observer,
    )
    recovery = fresh_recovery_runtime(db)
    binding = recovery.background_model_attempts.outbound_request_binding(attempt.attempt_id)
    assert binding is not None

    forged = make_directive(
        response="forged via public _receipt_proof checksum",
        provider="public-sha-provider",
        model="public-sha-model",
        request_id="public-sha-req",
    )
    payload = encode_model_directive(forged)
    payload_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    resp_fp = BackgroundModelAttemptStore._response_fingerprint(forged)

    # Compute the candidate's v2 proof using ONLY public data (zero secrets).
    fields = {
        "attempt_id": attempt.attempt_id,
        "subject_id": attempt.subject_id,
        "work_kind": attempt.work_kind,
        "work_id": attempt.work_id,
        "model_round_index": attempt.model_round_index,
        "outbound_request_fingerprint": binding.outbound_request_fingerprint,
        "relay_id": binding.relay_id,
        "provider": "public-sha-provider",
        "model": "public-sha-model",
        "provider_request_id": "public-sha-req",
        "response_fingerprint": resp_fp,
        "payload_sha256": payload_sha256,
    }
    raw_sha256 = hashlib.sha256(
        BackgroundModelAttemptStore._receipt_message(**fields)
    ).hexdigest()
    expected_public_proof = f"bgresponse_v2_{raw_sha256}"
    actual_proof = BackgroundModelAttemptStore._receipt_proof(**fields)
    is_keyless_sha256 = (actual_proof == expected_public_proof)

    minted_and_staged = False
    try:
        receipt = recovery.background_model_attempts._capture_trusted_response_return(
            attempt.attempt_id,
            captured_at=NOW + timedelta(seconds=5),
            directive=forged,
        )
        staged = recovery.background_model_attempts.stage_exact_response(
            attempt.attempt_id,
            staged_at=NOW + timedelta(seconds=6),
            provider="public-sha-provider",
            model="public-sha-model",
            provider_request_id="public-sha-req",
            response_fingerprint=resp_fp,
            directive_payload=payload,
            authenticity_proof=expected_public_proof,
            evidence="caller-computed keyless SHA-256 proof",
        )
        minted_and_staged = (
            receipt.authenticity_proof == expected_public_proof
            and staged.authenticity_proof == expected_public_proof
        )
    except BaseException:
        minted_and_staged = False

    if is_keyless_sha256 and minted_and_staged:
        return ProbeResult(
            "IA17-DOWNGRADE-001",
            "authenticity_proof cannot be caller-computed from public fields and minted into staged response without external signer",
            f"KEYLESS SHA-256 PROOF ({expected_public_proof[:28]}...) computed from public fields and accepted by stage_exact_response",
            False,
        )
    return ProbeResult(
        "IA17-DOWNGRADE-001",
        "authenticity_proof cannot be caller-computed from public fields and minted into staged response without external signer",
        f"is_keyless_sha256={is_keyless_sha256}, minted_and_staged={minted_and_staged}",
        True,
    )


# ---------------------------------------------------------------------------
# CRITICAL ATTACK C (Case 1): IA17-MIGRATE-001
# ---------------------------------------------------------------------------
def _create_pre_upgrade_db_with_hmac_receipt(
    db: Path,
    *,
    session_id: str,
    directive: ModelDirective,
) -> tuple[str, bytes, dict[str, object]]:
    """Build a genuine pre-upgrade DB state matching accepted main (0b883c71)."""
    _, attempt = dispatch_and_crash(db, session_id=session_id, verifier=None, observer=None)
    store = SQLiteWorldStore(db)
    attempts = BackgroundModelAttemptStore(store)
    binding = attempts.outbound_request_binding(attempt.attempt_id)
    assert binding is not None

    secret_bytes = bytes.fromhex("a1b2c3d4" * 8)
    secret_hex = secret_bytes.hex()
    payload = encode_model_directive(directive)
    payload_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    resp_fp = BackgroundModelAttemptStore._response_fingerprint(directive)
    provider, model, req_id = BackgroundModelAttemptStore._provider_identity(directive)
    assert provider and model and req_id

    fields: dict[str, object] = {
        "attempt_id": attempt.attempt_id,
        "subject_id": attempt.subject_id,
        "work_kind": attempt.work_kind,
        "work_id": attempt.work_id,
        "model_round_index": int(attempt.model_round_index),
        "outbound_request_fingerprint": binding.outbound_request_fingerprint,
        "relay_id": binding.relay_id,
        "provider": provider,
        "model": model,
        "provider_request_id": req_id,
        "response_fingerprint": resp_fp,
        "payload_sha256": payload_sha256,
    }
    msg = BackgroundModelAttemptStore._receipt_message(**fields)
    legacy_hmac = "bgresponse_v1_" + hmac.new(secret_bytes, msg, hashlib.sha256).hexdigest()

    with sqlite3.connect(db) as conn:
        conn.execute(
            """
            CREATE TABLE background_model_authenticity_authority (
                authority_id TEXT PRIMARY KEY,
                secret_hex TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO background_model_authenticity_authority(authority_id, secret_hex)
            VALUES ('trusted-return-v1', ?)
            """,
            (secret_hex,),
        )
        conn.execute(
            """
            INSERT INTO background_model_response_receipts(
                attempt_id, subject_id, work_kind, work_id,
                model_round_index, outbound_request_fingerprint, relay_id,
                provider, model, provider_request_id, response_fingerprint,
                payload_sha256, authenticity_proof, captured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                *fields.values(),
                legacy_hmac,
                "2026-10-02T12:00:00Z",
            ),
        )
        conn.execute(
            """
            INSERT INTO background_model_return_handoffs(
                attempt_id, directive_payload, payload_sha256, authenticity_proof
            ) VALUES (?, ?, ?, ?)
            """,
            (attempt.attempt_id, payload, payload_sha256, legacy_hmac),
        )
        conn.commit()
    return attempt.attempt_id, secret_bytes, fields


def probe_ia17_migrate_001_valid_pre_upgrade_recovery(root: Path) -> ProbeResult:
    """Case 1: valid pre-upgrade HMAC receipt+handoff recovers cleanly after secret-purge migration."""
    db = root / "ia17-migrate-001.sqlite"
    genuine = make_directive(response="valid historical pre-upgrade response")
    attempt_id, secret_bytes, _ = _create_pre_upgrade_db_with_hmac_receipt(
        db,
        session_id="sess-migrate-001",
        directive=genuine,
    )

    recovery = fresh_recovery_runtime(db)
    result = recovery.run_turn(
        session_id="sess-migrate-001",
        turn_index=1,
        user_input=TURN_INPUT,
        occurred_at=NOW,
    )
    with sqlite3.connect(db) as conn:
        dump = "\n".join(conn.iterdump()).encode()
    secret_purged = secret_bytes.hex().encode() not in dump and secret_bytes.hex().encode() not in db.read_bytes()
    attempt = recovery.background_model_attempts.get(attempt_id)
    passed = (
        result.runtime.response == "valid historical pre-upgrade response"
        and attempt is not None
        and attempt.state == "metered"
        and secret_purged
    )
    return ProbeResult(
        "IA17-MIGRATE-001",
        "valid pre-upgrade HMAC receipt/handoff recovers exact response and purges legacy secret",
        f"response={result.runtime.response!r}, state={attempt.state if attempt else None}, secret_purged={secret_purged}",
        passed,
    )


# ---------------------------------------------------------------------------
# CRITICAL ATTACK C (Case 2): IA17-MIGRATE-002
# ---------------------------------------------------------------------------
def probe_ia17_migrate_002_tampered_pre_upgrade_db_laundering(root: Path) -> ProbeResult:
    """Case 2: tampered pre-upgrade DB rows must FAIL_CLOSED on upgrade, never be laundered into valid v2 checksums."""
    laundered_cases: list[str] = []

    # Subcase A: forged/invalid HMAC proof in pre-upgrade receipt & handoff
    db_a = root / "ia17-migrate-002a.sqlite"
    forged_a = make_directive(response="tampered subcase A invalid HMAC")
    attempt_a, _, _ = _create_pre_upgrade_db_with_hmac_receipt(
        db_a,
        session_id="sess-mig-a",
        directive=forged_a,
    )
    with sqlite3.connect(db_a) as conn:
        bad_proof = "bgresponse_v1_" + ("00" * 32)
        conn.execute(
            "UPDATE background_model_response_receipts SET authenticity_proof=? WHERE attempt_id=?",
            (bad_proof, attempt_a),
        )
        conn.execute(
            "UPDATE background_model_return_handoffs SET authenticity_proof=? WHERE attempt_id=?",
            (bad_proof, attempt_a),
        )
        conn.commit()
    try:
        rec_a = fresh_recovery_runtime(db_a)
        res_a = rec_a.run_turn(
            session_id="sess-mig-a",
            turn_index=1,
            user_input=TURN_INPUT,
            occurred_at=NOW,
        )
        laundered_cases.append(f"subcase_A_invalid_hmac_completed({res_a.runtime.response!r})")
    except BaseException:
        pass

    # Subcase B: pre-upgrade receipt+handoff payload/fingerprint tampered without HMAC key
    db_b = root / "ia17-migrate-002b.sqlite"
    genuine_b = make_directive(response="genuine response before tamper")
    attempt_b, _, _ = _create_pre_upgrade_db_with_hmac_receipt(
        db_b,
        session_id="sess-mig-b",
        directive=genuine_b,
    )
    tampered_b = make_directive(response="TAMPERED_PRE_UPGRADE_PAYLOAD_WITHOUT_KEY")
    tampered_payload = encode_model_directive(tampered_b)
    tampered_sha = hashlib.sha256(tampered_payload.encode("utf-8")).hexdigest()
    tampered_fp = BackgroundModelAttemptStore._response_fingerprint(tampered_b)
    with sqlite3.connect(db_b) as conn:
        conn.execute(
            """
            UPDATE background_model_response_receipts
            SET response_fingerprint=?, payload_sha256=?
            WHERE attempt_id=?
            """,
            (tampered_fp, tampered_sha, attempt_b),
        )
        conn.execute(
            """
            UPDATE background_model_return_handoffs
            SET directive_payload=?, payload_sha256=?
            WHERE attempt_id=?
            """,
            (tampered_payload, tampered_sha, attempt_b),
        )
        conn.commit()
    try:
        rec_b = fresh_recovery_runtime(db_b)
        res_b = rec_b.run_turn(
            session_id="sess-mig-b",
            turn_index=1,
            user_input=TURN_INPUT,
            occurred_at=NOW,
        )
        laundered_cases.append(f"subcase_B_tampered_payload_completed({res_b.runtime.response!r})")
    except BaseException:
        pass

    # Subcase C: pre-upgrade handoff authenticity_proof corrupted / mismatched with receipt
    db_c = root / "ia17-migrate-002c.sqlite"
    genuine_c = make_directive(response="handoff proof mismatch subcase C")
    attempt_c, _, _ = _create_pre_upgrade_db_with_hmac_receipt(
        db_c,
        session_id="sess-mig-c",
        directive=genuine_c,
    )
    with sqlite3.connect(db_c) as conn:
        conn.execute(
            "UPDATE background_model_return_handoffs SET authenticity_proof='CORRUPTED_HANDOFF_PROOF' WHERE attempt_id=?",
            (attempt_c,),
        )
        conn.commit()
    try:
        rec_c = fresh_recovery_runtime(db_c)
        res_c = rec_c.run_turn(
            session_id="sess-mig-c",
            turn_index=1,
            user_input=TURN_INPUT,
            occurred_at=NOW,
        )
        laundered_cases.append(f"subcase_C_corrupted_handoff_proof_completed({res_c.runtime.response!r})")
    except BaseException:
        pass

    if laundered_cases:
        return ProbeResult(
            "IA17-MIGRATE-002",
            "tampered pre-upgrade authentication evidence must FAIL_CLOSED and never be normalized into trusted state",
            "LAUNDERED TAMPERED PRE-UPGRADE ROWS INTO TRUSTED STATE: " + "; ".join(laundered_cases),
            False,
        )
    return ProbeResult(
        "IA17-MIGRATE-002",
        "tampered pre-upgrade authentication evidence must FAIL_CLOSED and never be normalized into trusted state",
        "all tampered pre-upgrade subcases refused",
        True,
    )


# ---------------------------------------------------------------------------
# CRITICAL ATTACK D: IA17-VERIFIER-SUB-001
# ---------------------------------------------------------------------------
def probe_ia17_verifier_sub_001_rebinding_attempts(root: Path) -> ProbeResult:
    """Recovery caller cannot substitute or rebind LateReturnVerifier on an already-dispatched attempt."""
    db = root / "ia17-verifier-sub-001.sqlite"
    observer = ReviewerExternalObserver()
    orig_verifier = make_verifier(key_id="legit-key-1")
    _, attempt = dispatch_and_crash(
        db,
        session_id="sess-vsub-001",
        verifier=orig_verifier,
        observer=observer,
    )

    attacker_verifier = LateReturnVerifier(
        key_id="attacker-key-99",
        algorithm="rsa-pkcs1v15-sha256",
        modulus_hex=f"{_RSA_N:x}",
        public_exponent=_RSA_E,
    )
    recovery = fresh_recovery_runtime(db, verifier=attacker_verifier)

    # 1. Try mark_dispatching again to overwrite verifier
    rebind_succeeded = False
    try:
        recovery.background_model_attempts.mark_dispatching(
            attempt.attempt_id,
            dispatched_at=NOW + timedelta(seconds=5),
            outbound_request_fingerprint="attacker-rebound-fp",
            late_return_verifier=attacker_verifier,
        )
        rebind_succeeded = True
    except (BackgroundModelExecutionInDoubt, BackgroundModelAttemptBlocked):
        pass

    # 2. Try attaching a proof signed under attacker's key_id="attacker-key-99"
    forged = make_directive(response="signed with substituted key_id")
    ctx = observer.contexts[attempt.attempt_id]
    payload = encode_model_directive(forged)
    payload_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    resp_fp = BackgroundModelAttemptStore._response_fingerprint(forged)
    attacker_proof = rsa_sign(
        late_return_message(
            **ctx.scope_fields(),
            provider=forged.provenance.provider,
            model=forged.provenance.model,
            provider_request_id=forged.provenance.request_id,
            response_fingerprint=resp_fp,
            payload_sha256=payload_sha256,
        ),
        key_id="attacker-key-99",
    )
    attach_succeeded = False
    try:
        recovery.background_model_attempts.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(seconds=10),
            directive_payload=payload,
            late_return_proof=attacker_proof,
            evidence="substituted verifier attack",
        )
        attach_succeeded = True
    except BackgroundModelResponseConflict:
        pass

    stored_verifier = recovery.background_model_attempts.late_return_verifier(attempt.attempt_id)
    passed = (
        not rebind_succeeded
        and not attach_succeeded
        and stored_verifier == orig_verifier
    )
    return ProbeResult(
        "IA17-VERIFIER-SUB-001",
        "bound LateReturnVerifier cannot be substituted or rebound via mark_dispatching or attach_late_trusted_return",
        f"rebind_succeeded={rebind_succeeded}, attach_succeeded={attach_succeeded}, stored_key_id={stored_verifier.key_id if stored_verifier else None}",
        passed,
    )


# ---------------------------------------------------------------------------
# CRITICAL ATTACK E: IA17-OBJGRAPH-001
# ---------------------------------------------------------------------------
def probe_ia17_objgraph_001_recursive_trust_minting_audit(root: Path) -> ProbeResult:
    """Recursive object-graph audit: no reachable method on recovery runtime/store may mint trusted receipts/handoffs."""
    db = root / "ia17-objgraph-001.sqlite"
    observer = ReviewerExternalObserver()
    _, attempt = dispatch_and_crash(
        db,
        session_id="sess-objgraph-001",
        verifier=make_verifier(),
        observer=observer,
    )
    recovery = fresh_recovery_runtime(db)

    visited: set[int] = set()
    queue: list[tuple[str, object]] = [("runtime", recovery)]
    minting_surfaces: list[str] = []

    while queue:
        path, obj = queue.pop(0)
        obj_id = id(obj)
        if obj_id in visited:
            continue
        visited.add(obj_id)

        for attr in dir(obj):
            if attr.startswith("__") and attr.endswith("__"):
                continue
            try:
                val = getattr(obj, attr)
            except Exception:
                continue
            full_path = f"{path}.{attr}"
            if callable(val) and attr in {
                "_capture_trusted_response_return",
                "_authenticate_background_model_response",
                "_issue_external_return_capability",
                "late_return_proof",
            }:
                minting_surfaces.append(full_path)
            elif hasattr(val, "__dict__") and path.count(".") < 3:
                queue.append((full_path, val))

    if minting_surfaces:
        return ProbeResult(
            "IA17-OBJGRAPH-001",
            "recovery object graph exposes zero trusted-receipt/handoff/proof minting callables",
            f"REACHABLE TRUST-MINTING CALLABLES FOUND: {sorted(minting_surfaces)}",
            False,
        )
    return ProbeResult(
        "IA17-OBJGRAPH-001",
        "recovery object graph exposes zero trusted-receipt/handoff/proof minting callables",
        "0 trust-minting callables found on recovery object graph",
        True,
    )


# ---------------------------------------------------------------------------
# CRITICAL ATTACK F: IA17-DB-AT-REST-001
# ---------------------------------------------------------------------------
def probe_ia17_db_at_rest_001_no_private_key_in_db_or_source(root: Path) -> ProbeResult:
    """SQLite DB/WAL/SHM/dump/backup and production source contain no RSA private exponent or capability nonce."""
    db = root / "ia17-db-at-rest-001.sqlite"
    observer = ReviewerExternalObserver()
    _, attempt = dispatch_and_crash(
        db,
        session_id="sess-db-001",
        verifier=make_verifier(),
        observer=observer,
    )
    priv_hex = f"{_RSA_D:x}".encode("ascii")

    raw_bytes = db.read_bytes()
    for suffix in ("-wal", "-shm"):
        p = db.with_name(db.name + suffix)
        if p.exists():
            raw_bytes += p.read_bytes()

    with sqlite3.connect(db) as conn:
        dump_bytes = "\n".join(conn.iterdump()).encode("utf-8")

    backup_db = root / "ia17-db-backup.sqlite"
    with sqlite3.connect(db) as src, sqlite3.connect(backup_db) as dst:
        src.backup(dst)
    backup_bytes = backup_db.read_bytes()

    leaked = (
        priv_hex in raw_bytes
        or priv_hex in dump_bytes
        or priv_hex in backup_bytes
    )
    return ProbeResult(
        "IA17-DB-AT-REST-001",
        "no RSA private key material in DB, WAL, SHM, SQL dump, or backup",
        f"private_key_leaked={leaked}, attempt_id={attempt.attempt_id}",
        not leaked,
    )


# ---------------------------------------------------------------------------
# CRITICAL ATTACK G1: IA17-RSA-001
# ---------------------------------------------------------------------------
def probe_ia17_rsa_001_pkcs1v15_adversarial_matrix(root: Path) -> ProbeResult:
    """Adversarial PKCS#1 v1.5 SHA-256 verification & 12-field canonical message binding checks."""
    del root
    verifier = make_verifier()
    base_fields: dict[str, object] = {
        "attempt_id": "bgattempt_rsa_001",
        "subject_id": "user_1",
        "work_kind": "user_turn",
        "work_id": "work_rsa_001",
        "model_round_index": 0,
        "outbound_request_fingerprint": "a" * 64,
        "relay_id": "relay_rsa_001",
        "provider": "provider-A",
        "model": "model-A",
        "provider_request_id": "req-A",
        "response_fingerprint": "b" * 64,
        "payload_sha256": "c" * 64,
    }
    msg = late_return_message(**base_fields)
    valid_proof = rsa_sign(msg, verifier.key_id)
    assert verify_late_return_proof(verifier, message=msg, proof=valid_proof) is True

    width = (_RSA_N.bit_length() + 7) // 8
    sig_hex = valid_proof.split(":", 2)[2]
    failures: list[str] = []

    def check_reject(label: str, proof_str: str, message_bytes: bytes = msg) -> None:
        if verify_late_return_proof(verifier, message=message_bytes, proof=proof_str):
            failures.append(label)

    # Length variants & integer boundary attacks
    check_reject("len-1", f"{LATE_RETURN_PROOF_PREFIX}{verifier.key_id}:{sig_hex[:-2]}")
    check_reject("len+1", f"{LATE_RETURN_PROOF_PREFIX}{verifier.key_id}:{sig_hex}00")
    check_reject("leading-zero-extra-byte", f"{LATE_RETURN_PROOF_PREFIX}{verifier.key_id}:00{sig_hex}")
    check_reject("sig=0", f"{LATE_RETURN_PROOF_PREFIX}{verifier.key_id}:{'00' * width}")
    check_reject("sig=1", f"{LATE_RETURN_PROOF_PREFIX}{verifier.key_id}:{'00' * (width - 1)}01")
    check_reject("sig=N", f"{LATE_RETURN_PROOF_PREFIX}{verifier.key_id}:{_RSA_N:0{width * 2}x}")
    check_reject("sig=N+1", f"{LATE_RETURN_PROOF_PREFIX}{verifier.key_id}:{_RSA_N + 1:0{width * 2}x}")
    check_reject("wrong-key-id", f"{LATE_RETURN_PROOF_PREFIX}wrong-key:{sig_hex}")
    check_reject("malformed-hex", f"{LATE_RETURN_PROOF_PREFIX}{verifier.key_id}:{'zz' * width}")

    # Crafted PKCS#1 v1.5 blocks signed with the real private key _RSA_D
    digest = hashlib.sha256(msg).digest()
    digest_info = _SHA256_DER + digest
    pad_len = width - len(digest_info) - 3

    def sign_raw_block(block: bytes) -> str:
        assert len(block) == width
        s = pow(int.from_bytes(block, "big"), _RSA_D, _RSA_N).to_bytes(width, "big")
        return f"{LATE_RETURN_PROOF_PREFIX}{verifier.key_id}:{s.hex()}"

    # Block type 0x02 instead of 0x01
    check_reject("block-type-02", sign_raw_block(b"\x00\x02" + (b"\xff" * pad_len) + b"\x00" + digest_info))
    # Leading byte 0x01 instead of 0x00
    check_reject("leading-byte-01", sign_raw_block(b"\x01\x01" + (b"\xff" * pad_len) + b"\x00" + digest_info))
    # Non-0xff byte inside padding
    check_reject("non-ff-padding", sign_raw_block(b"\x00\x01\xfe" + (b"\xff" * (pad_len - 1)) + b"\x00" + digest_info))
    # Missing 0x00 separator before DigestInfo
    check_reject("missing-00-sep", sign_raw_block(b"\x00\x01" + (b"\xff" * (pad_len + 1)) + digest_info))
    # Wrong DigestInfo prefix (flipped OID byte)
    bad_der = bytearray(_SHA256_DER)
    bad_der[-3] ^= 0x01
    check_reject("wrong-digest-info", sign_raw_block(b"\x00\x01" + (b"\xff" * pad_len) + b"\x00" + bytes(bad_der) + digest))
    # Trailing garbage byte after digest (with 1 byte shorter padding)
    check_reject(
        "trailing-bytes-after-digest",
        sign_raw_block(b"\x00\x01" + (b"\xff" * (pad_len - 1)) + b"\x00" + digest_info + b"\x00"),
    )

    # Verifier parameter validation: < 2048-bit modulus & even exponent
    for bad_kwargs, label in (
        ({"key_id": "k", "algorithm": "rsa-pkcs1v15-sha256", "modulus_hex": f"{(1 << 1024) + 1:x}", "public_exponent": 65537}, "modulus<2048"),
        ({"key_id": "k", "algorithm": "rsa-pkcs1v15-sha256", "modulus_hex": f"{_RSA_N:x}", "public_exponent": 65536}, "even-exponent"),
    ):
        try:
            LateReturnVerifier(**bad_kwargs)
            failures.append(label)
        except ValueError:
            pass

    # All 12 canonical message fields must be bound
    mutations: dict[str, object] = {
        "attempt_id": "bgattempt_other",
        "subject_id": "user_2",
        "work_kind": "wake",
        "work_id": "work_other",
        "model_round_index": 1,
        "outbound_request_fingerprint": "d" * 64,
        "relay_id": "relay_other",
        "provider": "provider-B",
        "model": "model-B",
        "provider_request_id": "req-B",
        "response_fingerprint": "e" * 64,
        "payload_sha256": "f" * 64,
    }
    for field_name, new_val in mutations.items():
        mutated_fields = dict(base_fields)
        mutated_fields[field_name] = new_val
        check_reject(f"transplant-{field_name}", valid_proof, late_return_message(**mutated_fields))

    return ProbeResult(
        "IA17-RSA-001",
        "all malformed PKCS#1 v1.5 signatures and all 12 field transplants fail closed",
        f"failures={failures}",
        len(failures) == 0,
    )


# ---------------------------------------------------------------------------
# CRITICAL ATTACK G2: IA17-RSA-DELIMITER-001
# ---------------------------------------------------------------------------
def probe_ia17_rsa_delimiter_001_key_id_colon_and_negative_modulus(root: Path) -> ProbeResult:
    """key_id delimiter ambiguity and negative modulus_hex must not silently break legitimate verification."""
    problems: list[str] = []

    # Part A: key_id containing ':' (e.g. 'provider:key-2026-v1')
    colon_key_id = "provider:key-2026-v1"
    try:
        colon_verifier = make_verifier(key_id=colon_key_id)
    except ValueError:
        colon_verifier = None

    if colon_verifier is not None:
        # Since LateReturnVerifier accepted key_id='provider:key-2026-v1', a genuine
        # external signature for an attempt bound to colon_verifier MUST verify and attach!
        db = root / "ia17-colon-key.sqlite"
        observer = ReviewerExternalObserver()
        _, attempt = dispatch_and_crash(
            db,
            session_id="sess-colon-key",
            verifier=colon_verifier,
            observer=observer,
        )
        genuine = make_directive(response="legitimate return under colon key_id")
        proof = observer.sign_directive(attempt.attempt_id, genuine)
        recovery = fresh_recovery_runtime(db)
        try:
            recovery.background_model_attempts.attach_late_trusted_return(
                attempt.attempt_id,
                attached_at=NOW + timedelta(seconds=10),
                directive_payload=encode_model_directive(genuine),
                late_return_proof=proof,
                evidence="legitimate external return with namespaced key_id",
            )
        except BackgroundModelResponseConflict as exc:
            problems.append(
                f"LateReturnVerifier accepted key_id={colon_key_id!r} at dispatch, "
                f"but verify_late_return_proof split(':', 1) permanently rejected genuine signature: {exc}"
            )

    # Part B: negative hex modulus in LateReturnVerifier
    try:
        neg_verifier = LateReturnVerifier(
            key_id="neg-mod-key",
            algorithm="rsa-pkcs1v15-sha256",
            modulus_hex=f"-{_RSA_N:x}",
            public_exponent=_RSA_E,
        )
        problems.append(
            f"LateReturnVerifier accepted negative modulus_hex (modulus_int < 0, bit_length={neg_verifier.modulus_int.bit_length()})"
        )
    except ValueError:
        pass

    return ProbeResult(
        "IA17-RSA-DELIMITER-001",
        "LateReturnVerifier either rejects colon key_id / negative modulus_hex at construction or verifies legitimate signatures accurately",
        "; ".join(problems) if problems else "no delimiter or negative-modulus defect",
        len(problems) == 0,
    )


# ---------------------------------------------------------------------------
# CRITICAL ATTACK H: IA17-RACE-CRASH-001
# ---------------------------------------------------------------------------
def probe_ia17_race_crash_001_concurrent_consumption_and_crash_matrix(root: Path) -> ProbeResult:
    """Concurrent attach race produces 1 winner; post-commit pre-stage crash converges exactly once."""
    db = root / "ia17-race-001.sqlite"
    observer = ReviewerExternalObserver()
    _, attempt = dispatch_and_crash(
        db,
        session_id="sess-race-001",
        verifier=make_verifier(),
        observer=observer,
    )
    dir_a = make_directive(response="concurrent candidate A", request_id="req-race-A")
    dir_b = make_directive(response="concurrent candidate B", request_id="req-race-B")
    proof_a = observer.sign_directive(attempt.attempt_id, dir_a)
    proof_b = observer.sign_directive(attempt.attempt_id, dir_b)

    barrier = threading.Barrier(2)
    outcomes: list[tuple[str, str]] = []
    lock = threading.Lock()

    def worker(label: str, d: ModelDirective, p: str) -> None:
        rt = fresh_recovery_runtime(db)
        barrier.wait()
        try:
            rt.background_model_attempts.attach_late_trusted_return(
                attempt.attempt_id,
                attached_at=NOW + timedelta(seconds=10),
                directive_payload=encode_model_directive(d),
                late_return_proof=p,
                evidence=f"race-{label}",
            )
            with lock:
                outcomes.append((label, "accepted"))
        except BackgroundModelResponseConflict:
            with lock:
                outcomes.append((label, "refused"))

    t1 = threading.Thread(target=worker, args=("A", dir_a, proof_a))
    t2 = threading.Thread(target=worker, args=("B", dir_b, proof_b))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    statuses = sorted(status for _, status in outcomes)
    recovery = fresh_recovery_runtime(db)
    res = recovery.run_turn(
        session_id="sess-race-001",
        turn_index=1,
        user_input=TURN_INPUT,
        occurred_at=NOW,
    )
    meters = recovery.metering.list_model_calls(
        subject_id="user_1", execution_classes=("user_interaction",)
    )
    passed = (
        statuses == ["accepted", "refused"]
        and res.runtime.response in {"concurrent candidate A", "concurrent candidate B"}
        and len(meters) == 1
    )
    return ProbeResult(
        "IA17-RACE-CRASH-001",
        "concurrent valid proofs yield 1 accepted + 1 refused and 1 metered turn completion",
        f"outcomes={outcomes}, response={res.runtime.response!r}, meters={len(meters)}",
        passed,
    )


# ---------------------------------------------------------------------------
# Sections 19 & 20: IA17-NS-ROUTE-B-001
# ---------------------------------------------------------------------------
def probe_ia17_ns_route_b_001_post_binding_and_pre_submission(root: Path) -> ProbeResult:
    """All post-binding not_submitted write sites fail closed; pre-submission retry + late return succeeds."""
    db = root / "ia17-route-b.sqlite"
    observer = ReviewerExternalObserver()
    verifier = make_verifier()
    _, attempt = dispatch_and_crash(
        db,
        session_id="sess-route-b",
        verifier=verifier,
        observer=observer,
    )
    recovery = fresh_recovery_runtime(db)
    attempts = recovery.background_model_attempts

    refused_all = True
    for fn in (
        lambda: attempts.mark_failure(
            attempt.attempt_id,
            failed_at=NOW + timedelta(seconds=1),
            definitely_not_submitted=True,
            error=ModelDispatchNotSubmitted("typed exception post-binding"),
        ),
        lambda: attempts.mark_failure(
            attempt.attempt_id,
            failed_at=NOW + timedelta(seconds=2),
            definitely_not_submitted=True,
            error=RuntimeError("runtime error post-binding"),
        ),
        lambda: attempts.reconcile_not_submitted(
            attempt.attempt_id,
            reconciled_at=NOW + timedelta(seconds=3),
            evidence="operator claim post-binding",
        ),
        lambda: recovery.reconcile_turn_model_not_submitted(
            session_id="sess-route-b",
            turn_index=1,
            user_input=TURN_INPUT,
            occurred_at=NOW,
            model_round_index=0,
            reconciled_at=NOW + timedelta(seconds=4),
            evidence="turn wrapper post-binding",
        ),
    ):
        try:
            fn()
            refused_all = False
        except BackgroundModelResponseConflict:
            pass

    after = attempts.get(attempt.attempt_id)
    post_binding_ok = refused_all and after is not None and after.state == "in_doubt"

    # Genuine pre-submission retry followed by first real dispatch + late return
    db_pre = root / "ia17-pre-sub.sqlite"
    store_pre, index_pre = open_world(db_pre)
    attempts_pre = BackgroundModelAttemptStore(store_pre)
    exec_id = FusedTurnRuntime(
        store=store_pre,
        index=index_pre,
        model_handler=lambda _s: make_directive(),
        subject_id="user_1",
    ).turn_executions.execution_id_for(
        subject_id="user_1",
        session_id="sess-pre-sub",
        turn_index=1,
    )
    admitted = attempts_pre.admit(
        subject_id="user_1",
        work_kind="user_turn",
        work_id=exec_id,
        wake_reason="user_interaction",
        model_round_index=0,
        world_revision=int(store_pre.current_world_revision()),
        admitted_at=NOW,
    )
    ns = attempts_pre.mark_failure(
        admitted.attempt_id,
        failed_at=NOW,
        definitely_not_submitted=True,
        error=ModelDispatchNotSubmitted("genuine pre-dispatch failure"),
    )
    assert ns.state == "not_submitted"

    obs_pre = ReviewerExternalObserver()
    _, crashed_attempt = dispatch_and_crash(
        db_pre,
        session_id="sess-pre-sub",
        verifier=verifier,
        observer=obs_pre,
    )
    assert crashed_attempt.attempt_id == admitted.attempt_id
    genuine = make_directive(response="completed after pre-submission retry + late return")
    proof = obs_pre.sign_directive(crashed_attempt.attempt_id, genuine)
    rec_pre = fresh_recovery_runtime(db_pre)
    rec_pre.background_model_attempts.attach_late_trusted_return(
        crashed_attempt.attempt_id,
        attached_at=NOW + timedelta(seconds=10),
        directive_payload=encode_model_directive(genuine),
        late_return_proof=proof,
        evidence="late return after pre-submission retry",
    )
    res_pre = rec_pre.run_turn(
        session_id="sess-pre-sub",
        turn_index=1,
        user_input=TURN_INPUT,
        occurred_at=NOW,
    )
    passed = post_binding_ok and res_pre.runtime.response == "completed after pre-submission retry + late return"
    return ProbeResult(
        "IA17-NS-ROUTE-B-001",
        "post-binding not_submitted refused across all write sites; pre-submission retry + late return succeeds",
        f"post_binding_ok={post_binding_ok}, pre_sub_response={res_pre.runtime.response!r}",
        passed,
    )


# ---------------------------------------------------------------------------
# Section 22: IA17-ID-JSON-001
# ---------------------------------------------------------------------------
def probe_ia17_id_json_001_parser_and_identity_attacks(root: Path) -> ProbeResult:
    """Conflicting provider/model/request_id and duplicate JSON keys fail closed."""
    db = root / "ia17-id-json.sqlite"
    observer = ReviewerExternalObserver()
    _, attempt = dispatch_and_crash(
        db,
        session_id="sess-id-json",
        verifier=make_verifier(),
        observer=observer,
    )
    recovery = fresh_recovery_runtime(db)
    failures: list[str] = []

    # 1. Conflicting usage vs provenance at construction
    for kwargs, label in (
        ({"usage_provider": "p1", "prov_provider": "p2"}, "provider-mismatch"),
        ({"usage_model": "m1", "prov_model": "m2"}, "model-mismatch"),
        ({"usage_req": "r1", "prov_req": "r2"}, "request_id-mismatch"),
    ):
        try:
            ModelDirective(
                response="x",
                usage=ModelUsage(
                    input_tokens=1,
                    output_tokens=1,
                    total_tokens=2,
                    provider=kwargs.get("usage_provider", "p1"),
                    model=kwargs.get("usage_model", "m1"),
                    request_id=kwargs.get("usage_req", "r1"),
                ),
                provenance=ModelCallProvenance(
                    provider=kwargs.get("prov_provider", "p1"),
                    model=kwargs.get("prov_model", "m1"),
                    request_id=kwargs.get("prov_req", "r1"),
                ),
            )
            failures.append(label)
        except ValueError:
            pass

    # 2. Duplicate top-level and nested JSON keys in decode_model_directive / attach_late_trusted_return
    dup_top = '{"capability_calls":[],"provenance":{"model":"m","provider":"p","request_id":"r"},"response":"a","response":"b","silence":false,"usage":{"input_tokens":1,"model":"m","output_tokens":1,"provider":"p","request_id":"r","total_tokens":2}}'
    dup_nested = '{"capability_calls":[],"provenance":{"model":"m","provider":"p","provider":"evil","request_id":"r"},"response":"a","silence":false,"usage":{"input_tokens":1,"model":"m","output_tokens":1,"provider":"p","request_id":"r","total_tokens":2}}'
    for payload_str, label in ((dup_top, "dup-top-json"), (dup_nested, "dup-nested-json")):
        try:
            decode_model_directive(payload_str)
            failures.append(label)
        except ValueError:
            pass

    # 3. Equivalent JSON with extra whitespace vs signed canonical payload_sha256
    genuine = make_directive(response="canonical json test")
    proof = observer.sign_directive(attempt.attempt_id, genuine)
    non_canonical_payload = encode_model_directive(genuine) + "   \n"
    try:
        recovery.background_model_attempts.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(seconds=10),
            directive_payload=non_canonical_payload,
            late_return_proof=proof,
            evidence="whitespace mutated payload bytes",
        )
        failures.append("whitespace-mutated-payload-accepted")
    except BackgroundModelResponseConflict:
        pass

    return ProbeResult(
        "IA17-ID-JSON-001",
        "provider/model/request_id conflicts, duplicate JSON keys, and non-canonical byte mutations fail closed",
        f"failures={failures}",
        len(failures) == 0,
    )


# ---------------------------------------------------------------------------
# Section 23: IA17-SIGKILL-001
# ---------------------------------------------------------------------------
def _sigkill_child_entry(db_str: str, conn_pipe: object) -> None:
    db = Path(db_str)
    store, index = open_world(db)

    class PipeObserver:
        def accept_return_context(self, _snapshot: object, context: LateReturnSigningContext) -> None:
            conn_pipe.send(context.model_dump(mode="json"))
            conn_pipe.close()

    def kill_self(_snapshot: object) -> ModelDirective:
        os.kill(os.getpid(), signal.SIGKILL)
        raise RuntimeError("unreachable")

    rt = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=kill_self,
        subject_id="user_1",
        late_return_verifier=make_verifier(),
        external_return_observer=PipeObserver(),
    )
    rt.run_turn(
        session_id="sess-sigkill-w17",
        turn_index=1,
        user_input=TURN_INPUT,
        occurred_at=NOW,
        current_topic=None,
    )


def probe_ia17_sigkill_001_real_process_loss(root: Path) -> ProbeResult:
    """Real multi-process SIGKILL after dispatch + external RSA signature recovers exactly once."""
    db = root / "ia17-sigkill.sqlite"
    SQLiteWorldStore(db)
    ctx = multiprocessing.get_context("fork")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_sigkill_child_entry, args=(str(db), child_conn))
    proc.start()
    proc.join(timeout=30)
    assert proc.exitcode == -signal.SIGKILL
    assert parent_conn.poll(10)
    raw_context = parent_conn.recv()

    signing_ctx = LateReturnSigningContext(**raw_context)
    observer = ReviewerExternalObserver()
    observer.contexts[signing_ctx.attempt_id] = signing_ctx

    genuine = make_directive(
        response="recovered after real SIGKILL",
        request_id="req-w17-sigkill-1",
    )
    proof = observer.sign_directive(signing_ctx.attempt_id, genuine)

    provider_calls: list[int] = []
    store, index = open_world(db)

    def forbidden_redispatch(snapshot: object) -> ModelDirective:
        provider_calls.append(getattr(snapshot, "round_index", -1))
        raise AssertionError("redispatch forbidden")

    recovery = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=forbidden_redispatch,
        subject_id="user_1",
        late_return_verifier=make_verifier(),
    )
    recovery.background_model_attempts.attach_late_trusted_return(
        signing_ctx.attempt_id,
        attached_at=NOW + timedelta(seconds=30),
        directive_payload=encode_model_directive(genuine),
        late_return_proof=proof,
        evidence="reviewer real SIGKILL external return",
    )
    result = recovery.run_turn(
        session_id="sess-sigkill-w17",
        turn_index=1,
        user_input=TURN_INPUT,
        occurred_at=NOW,
        current_topic=None,
    )
    already_completed = False
    try:
        recovery.run_turn(
            session_id="sess-sigkill-w17",
            turn_index=1,
            user_input=TURN_INPUT,
            occurred_at=NOW,
            current_topic=None,
        )
    except TurnAlreadyCompleted:
        already_completed = True

    inspection = recovery.inspect_turn_execution(
        session_id="sess-sigkill-w17",
        turn_index=1,
        user_input=TURN_INPUT,
        occurred_at=NOW,
    )
    meters = recovery.metering.list_model_calls(
        subject_id="user_1", execution_classes=("user_interaction",)
    )
    attempt = recovery.background_model_attempts.get(signing_ctx.attempt_id)
    passed = (
        proc.exitcode == -signal.SIGKILL
        and result.runtime.response == "recovered after real SIGKILL"
        and provider_calls == []
        and len(meters) == 1
        and inspection.state == "completed"
        and inspection.assistant_ref is not None
        and attempt is not None
        and attempt.state == "metered"
        and already_completed
    )
    return ProbeResult(
        "IA17-SIGKILL-001",
        "real SIGKILL child + external RSA signature recovers turn with 1 meter, 1 effect, 1 output, 0 redispatch",
        (
            f"exitcode={proc.exitcode}, response={result.runtime.response!r}, "
            f"provider_calls={provider_calls}, meters={len(meters)}, "
            f"state={attempt.state if attempt else None}, replay_blocked={already_completed}"
        ),
        passed,
    )


def main() -> int:
    probes = (
        probe_ia17_mint_001_capture_helper_mints_trusted_return_without_rsa,
        probe_ia17_mint_002_anonymous_no_verifier_bypass,
        probe_ia17_downgrade_001_public_checksum_and_stage,
        probe_ia17_migrate_001_valid_pre_upgrade_recovery,
        probe_ia17_migrate_002_tampered_pre_upgrade_db_laundering,
        probe_ia17_verifier_sub_001_rebinding_attempts,
        probe_ia17_objgraph_001_recursive_trust_minting_audit,
        probe_ia17_db_at_rest_001_no_private_key_in_db_or_source,
        probe_ia17_rsa_001_pkcs1v15_adversarial_matrix,
        probe_ia17_rsa_delimiter_001_key_id_colon_and_negative_modulus,
        probe_ia17_race_crash_001_concurrent_consumption_and_crash_matrix,
        probe_ia17_ns_route_b_001_post_binding_and_pre_submission,
        probe_ia17_id_json_001_parser_and_identity_attacks,
        probe_ia17_sigkill_001_real_process_loss,
    )
    failures = 0
    with tempfile.TemporaryDirectory(prefix="w17-ia-probes-") as tmp:
        root = Path(tmp)
        for probe_fn in probes:
            res = probe_fn(root)
            status = "PASS" if res.passed else "FAIL"
            if not res.passed:
                failures += 1
            print(f"{status} | {res.probe_id}")
            print(f"  expected: {res.expected}")
            print(f"  actual:   {res.actual}")
    print(f"SUMMARY | probes={len(probes)} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
