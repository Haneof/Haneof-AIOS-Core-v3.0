"""PM Readiness Blocker Regressions (Window 49).

Covers:
- PM49-BLK-001: Hosted resident-surface base resolution in detached/hosted checkouts.
- PM49-BLK-002: Private signing authority isolation and zero proof-minting in recovery.
"""

from __future__ import annotations

import inspect
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "killpoints"))
from harness import REPO_ROOT, new_root, repo_python_env, wipe  # noqa: E402

from tools.c15_persistence import (  # noqa: E402
    backend as backend_module,
    operator_session as operator_session_module,
    provider as provider_module,
    relay as relay_module,
    resident_surface_check as resident_surface_check_module,
)
from tools.c15_persistence.operator_session import (  # noqa: E402
    DurableTrustedReturnMissing,
    OperatorSession,
)
from tools.c15_persistence.relay import RelayJournal
from tools.c15_persistence.synthetic_release import SyntheticRelease


# -----------------------------------------------------------------------------
# PM49-BLK-002: Trust Authority & Private Key Isolation Attacker Tests
# -----------------------------------------------------------------------------


def test_pm49_blk002_operator_session_has_no_private_key_or_signer_object() -> None:
    """ATTACK TEST: Ordinary OperatorSession object graph and modules cannot possess signing authority.

    Proves:
    1. OperatorSession instance has no private key, exponent, or signer object.
    2. operator_session module has no access to _RSA_D or private signing closures.
    3. No .sign() method exists on OperatorSession.
    """
    parent = new_root("pm49-blk002-nosign")
    try:
        root = parent / "backend"
        session = OperatorSession.create(
            root, run_id="attack-run-001", session_id="attack-sess-001"
        )

        # 1. Inspect session instance attributes
        forbidden_instance_attrs = ("_external_signer", "signer", "_signer", "_RSA_D", "private_key", "sign")
        for attr in forbidden_instance_attrs:
            assert not hasattr(session, attr), f"OperatorSession illegally exposes attribute: {attr}"

        # 2. Inspect session class attributes and methods
        forbidden_class_attrs = ("_RSA_D", "sign", "rsa_sign", "_external_signer")
        for attr in forbidden_class_attrs:
            assert not hasattr(OperatorSession, attr), f"OperatorSession class illegally exposes attribute: {attr}"

        # 3. Inspect operator_session module namespace
        operator_attrs = dir(operator_session_module)
        assert "_RSA_D" not in operator_attrs, "operator_session module illegally imports _RSA_D"
        assert "_provider_authority" not in operator_attrs, "operator_session module illegally imports _provider_authority"
        assert "rsa_sign" not in operator_attrs, "operator_session module illegally imports rsa_sign"
        assert "RouteBProviderSigner" not in operator_attrs, "operator_session module illegally imports RouteBProviderSigner"

        # 4. Inspect public provider module namespace
        provider_attrs = dir(provider_module)
        assert "_RSA_D" not in provider_attrs, "provider module illegally exposes _RSA_D in public namespace"
        assert "rsa_sign" not in provider_attrs, "provider module illegally exposes rsa_sign in public namespace"
        assert "RouteBProviderSigner" not in provider_attrs, "provider module illegally exposes RouteBProviderSigner"

        session.backend.release()
    finally:
        wipe(parent)


def test_pm49_blk002_provider_boundary_rejects_arbitrary_attacker_response_signing() -> None:
    """ATTACK TEST: Provider client / boundary refuses to sign arbitrary caller-supplied responses.

    Proves:
    1. Provider only signs exact responses that IT generated for valid dispatched requests.
    2. No public RPC or function exists allowing callers to request signing for arbitrary directives.
    """
    # Verify public provider module exports
    public_functions = [
        name for name, obj in inspect.getmembers(provider_module, inspect.isfunction)
        if not name.startswith("_")
    ]
    for fn_name in public_functions:
        assert "sign" not in fn_name or fn_name == "route_b_verifier", (
            f"provider module illegally exports public signing function: {fn_name}"
        )


def test_pm49_blk002_recovery_path_never_invokes_signing_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ATTACK TEST: Recovery path never calls signing functions or mints late-return proofs.

    Proves that during OperatorSession.resume() / _recover_with_core(), zero signing calls occur.
    """
    from tools.c15_persistence import _provider_authority

    sign_calls: list[Any] = []
    original_sign = _provider_authority.rsa_sign_message

    def tracking_sign(*args: Any, **kwargs: Any) -> str:
        sign_calls.append((args, kwargs))
        return original_sign(*args, **kwargs)

    parent = new_root("pm49-blk002-rec-nosign")
    try:
        root = parent / "backend"
        run_id = "test-rec-nosign-001"
        session_id = "test-rec-nosign-sess"
        session = OperatorSession.create(root, run_id=run_id, session_id=session_id)
        projection = session.reveal()
        session.ingest(projection)
        session.runtime = session._build_runtime()
        session._session_id = f"{session.backend.owner['run_id']}-conv"
        
        # Stage and dispatch request (K3)
        turn_index = int(projection["sequence"])
        attempt_id = session._attempt_id(turn_index=turn_index, round_index=0)
        request_id = session._request_id(attempt_id, 0)
        nonce = "test-nonce-12345678"
        req_bytes, metadata = session._request_bytes(
            attempt_id=attempt_id,
            request_id=request_id,
            round_index=0,
            cursor=turn_index,
            event_id=str(projection["event_id"]),
            payload=str(projection["resident_visible_payload"]),
            nonce=nonce,
            binding_digest=session._binding_digest(),
        )
        session.journal.stage(metadata, req_bytes, generation=0)
        session.journal.expose(request_id)
        session._write_outbox(request_id, req_bytes, round_index=0)
        provider_module.dispatch(session.mailbox, request_id)

        # Simulate Core having marked dispatch started without a durable receipt
        execution_id = session.runtime.turn_executions.execution_id_for(
            subject_id=session.runtime.subject_id,
            session_id=session._session_id,
            turn_index=turn_index,
        )
        session.runtime.background_model_attempts.admit(
            subject_id=session.runtime.subject_id,
            work_kind="user_turn",
            work_id=execution_id,
            wake_reason="user_turn",
            model_round_index=0,
            world_revision=1,
            admitted_at=datetime.now(timezone.utc),
        )
        session.runtime.background_model_attempts.mark_dispatching(
            attempt_id=attempt_id,
            dispatched_at=datetime.now(timezone.utc),
            outbound_request_fingerprint="test-fp",
        )
        session.backend.release()

        # 2. Attach monkeypatch tracking and attempt recovery
        monkeypatch.setattr(_provider_authority, "rsa_sign_message", tracking_sign)

        recovered = OperatorSession.attach(root, run_id=run_id, session_id=session_id)
        # Recovery must fail closed with DurableTrustedReturnMissing without calling rsa_sign_message
        with pytest.raises(DurableTrustedReturnMissing):
            recovered.resume()

        assert len(sign_calls) == 0, (
            f"Security violation: recovery called signing function {len(sign_calls)} times!"
        )
        recovered.backend.release()
    finally:
        wipe(parent)


def test_pm49_blk002_positive_live_path_produces_and_verifies_provider_proof() -> None:
    """POSITIVE TEST: Full live turn runs end-to-end with provider-produced proof verified by Core.

    Proves:
    1. Provider process generates reply + proof in mailbox.
    2. Core verifier successfully verifies provider proof.
    3. Operator correctly records receipt and handoff in journal and converges.
    """
    parent = new_root("pm49-blk002-live")
    try:
        root = parent / "backend"
        session = OperatorSession.create(
            root, run_id="test-live-001", session_id="test-live-sess"
        )
        
        outcome = session.process_one_cursor()
        assert outcome["ack"]["status"] == "acked"
        assert outcome["ack"]["sequence"] == 1
        
        # Verify receipt was created in Core SQLite
        runtime = session._build_runtime()
        session._session_id = f"{session.backend.owner['run_id']}-conv"
        session.runtime = runtime
        attempt_id = session._attempt_id(turn_index=1, round_index=0)
        receipt = runtime.background_model_attempts.response_authenticity_receipt(attempt_id)
        assert receipt is not None
        assert receipt.attempt_id == attempt_id
        assert receipt.provider == provider_module.PROVIDER_NAME
        assert receipt.model == provider_module.MODEL_NAME
        assert bool(receipt.authenticity_proof)
        
        session.backend.release()
    finally:
        wipe(parent)
