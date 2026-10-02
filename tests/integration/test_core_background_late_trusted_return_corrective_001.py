"""CA1-CA5 verifier-only late trusted return probes.

Frozen before verifier-only production code.  The RSA private exponent below is
TEST-ONLY external authority material; Core receives only the public verifier.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import inspect
import sqlite3

import pytest

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
    TurnAlreadyCompleted,
)
from aios_core.runtime.background_attempt import (
    BackgroundModelResponseConflict,
    encode_model_directive,
)
from aios_core.runtime.late_return import (
    LATE_RETURN_PROOF_PREFIX,
    ExternalReturnObserver,
    LateReturnSigningContext,
    LateReturnVerifier,
    late_return_message,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
TURN_INPUT = "synthetic verifier-only late return"
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


class ProcessDeath(BaseException):
    pass


def _verifier():
    return LateReturnVerifier(
        key_id="w16-test-external-key",
        algorithm="rsa-pkcs1v15-sha256",
        modulus_hex=f"{_RSA_N:x}",
        public_exponent=_RSA_E,
    )


def _directive(request_id="provider-request-1", response="late return exactly once"):
    return ModelDirective(
        response=response,
        usage=ModelUsage(
            total_tokens=10,
            input_tokens=7,
            output_tokens=3,
            provider="synthetic-provider",
            model="synthetic-model",
            request_id=request_id,
        ),
        provenance=ModelCallProvenance(
            provider="synthetic-provider",
            model="synthetic-model",
            request_id=request_id,
        ),
    )


def _rsa_sign(message: bytes, key_id: str) -> str:
    digest_info = _SHA256_DER + hashlib.sha256(message).digest()
    size = (_RSA_N.bit_length() + 7) // 8
    padding = b"\xff" * (size - len(digest_info) - 3)
    encoded = b"\x00\x01" + padding + b"\x00" + digest_info
    signature = pow(int.from_bytes(encoded, "big"), _RSA_D, _RSA_N).to_bytes(size, "big")
    return f"{LATE_RETURN_PROOF_PREFIX}{key_id}:{signature.hex()}"


class ExternalSigner:
    def __init__(self):
        self.contexts: dict[str, LateReturnSigningContext] = {}

    def accept_return_context(self, snapshot, context):
        assert snapshot.model_attempt_id == context.attempt_id
        self.contexts[context.attempt_id] = context

    def proof(self, attempt_id, directive, **overrides):
        context = self.contexts[attempt_id]
        payload = encode_model_directive(directive)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        fields = {
            **context.scope_fields(),
            "provider": directive.provenance.provider,
            "model": directive.provenance.model,
            "provider_request_id": directive.provenance.request_id,
            "response_fingerprint": digest,
            "payload_sha256": digest,
        }
        fields.update(overrides)
        return _rsa_sign(late_return_message(**fields), context.verifier_key_id)


def _world(db):
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def _build(db, handler, signer=None, verifier=None, subject_id="user_1"):
    store, index = _world(db)
    kwargs = {}
    if signer is not None:
        kwargs["external_return_observer"] = signer
    if verifier is not None:
        kwargs["late_return_verifier"] = verifier
    return FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=handler,
        subject_id=subject_id,
        **kwargs,
    )


def _dispatch_dead(db, signer, session="w16-ca-session"):
    runtime = _build(
        db,
        lambda _snapshot: (_ for _ in ()).throw(ProcessDeath("SIGKILL-shaped loss")),
        signer=signer,
        verifier=_verifier(),
    )
    with pytest.raises(ProcessDeath):
        runtime.run_turn(
            session_id=session,
            turn_index=1,
            user_input=TURN_INPUT,
            occurred_at=NOW,
        )
    execution_id = runtime.turn_executions.execution_id_for(
        subject_id="user_1", session_id=session, turn_index=1
    )
    attempt = runtime.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind="user_turn", work_id=execution_id
    )[-1]
    return runtime, attempt


def _restart(db):
    return _build(
        db,
        lambda _snapshot: pytest.fail("provider redispatch is forbidden"),
    )


def _attach(runtime, attempt, directive, proof, payload=None):
    exact = payload if payload is not None else encode_model_directive(directive)
    return runtime.background_model_attempts.attach_late_trusted_return(
        attempt.attempt_id,
        attached_at=NOW,
        directive_payload=exact,
        late_return_proof=proof,
        evidence="genuine external return after process death",
    )


def test_ca1_recovery_object_graph_has_verifier_but_no_signer_or_mint_authority(tmp_path):
    db = tmp_path / "ca1.sqlite"
    signer = ExternalSigner()
    runtime, attempt = _dispatch_dead(db, signer)
    context = signer.contexts[attempt.attempt_id]
    assert isinstance(context, LateReturnSigningContext)

    fresh = _restart(db)
    attempts = fresh.background_model_attempts
    assert not hasattr(attempts, "_issue_external_return_capability")
    forbidden_names = {"sign", "mint", "prove_external_return", "late_return_proof"}
    for owner in (fresh, attempts, fresh.store):
        for name in dir(owner):
            assert name not in forbidden_names

    verifier = attempts.late_return_verifier(attempt.attempt_id)
    assert verifier is not None
    dumped = verifier.model_dump()
    assert all(
        token not in key.lower()
        for key in dumped
        for token in ("secret", "private", "nonce", "preimage")
    )


def test_ca2_db_wal_dump_backup_contain_verifier_only_and_cannot_forge(tmp_path):
    db = tmp_path / "ca2.sqlite"
    signer = ExternalSigner()
    _runtime, attempt = _dispatch_dead(db, signer)
    private_hex = f"{_RSA_D:x}"

    with sqlite3.connect(db) as conn:
        dump = "\n".join(conn.iterdump())
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        columns = []
        for table in tables:
            columns.extend(
                str(row[1]).lower()
                for row in conn.execute(f"PRAGMA table_info({table})")
            )
    assert private_hex not in dump
    assert all(
        token not in column
        for column in columns
        for token in ("secret", "private_key", "capability_nonce", "preimage")
    )

    backup = tmp_path / "ca2-backup.sqlite"
    with sqlite3.connect(db) as src, sqlite3.connect(backup) as dst:
        src.backup(dst)
    assert private_hex not in backup.read_bytes().hex()

    fresh = _restart(db)
    with pytest.raises(BackgroundModelResponseConflict):
        _attach(
            fresh,
            attempt,
            _directive(),
            f"{LATE_RETURN_PROOF_PREFIX}w16-test-external-key:" + "00" * 256,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("attempt_id", "wrong-attempt"),
        ("subject_id", "user_2"),
        ("work_kind", "wake"),
        ("work_id", "wrong-work"),
        ("model_round_index", 9),
        ("outbound_request_fingerprint", "0" * 64),
        ("relay_id", "wrong-relay"),
        ("provider", "wrong-provider"),
        ("model", "wrong-model"),
        ("provider_request_id", "wrong-request"),
    ],
)
def test_ca5_scope_transplant_fields_fail_closed(tmp_path, field, value):
    db = tmp_path / f"ca5-{field}.sqlite"
    signer = ExternalSigner()
    _runtime, attempt = _dispatch_dead(db, signer)
    directive = _directive()
    proof = signer.proof(attempt.attempt_id, directive, **{field: value})
    fresh = _restart(db)
    with pytest.raises(BackgroundModelResponseConflict):
        _attach(fresh, attempt, directive, proof)
    assert fresh.background_model_attempts.staged_response(attempt.attempt_id) is None


def test_ca5_cross_attempt_transplant_and_payload_attacks_fail_closed(tmp_path):
    db = tmp_path / "ca5-transplant.sqlite"
    signer = ExternalSigner()
    _first, attempt_a = _dispatch_dead(db, signer, session="ca5-a")
    _second, attempt_b = _dispatch_dead(db, signer, session="ca5-b")
    directive = _directive()
    proof_a = signer.proof(attempt_a.attempt_id, directive)
    fresh = _restart(db)

    with pytest.raises(BackgroundModelResponseConflict):
        _attach(fresh, attempt_b, directive, proof_a)

    mutated = _directive(response="mutated response")
    with pytest.raises(BackgroundModelResponseConflict):
        _attach(fresh, attempt_a, mutated, proof_a)

    with pytest.raises((ValueError, BackgroundModelResponseConflict)):
        _attach(fresh, attempt_a, directive, "")
    with pytest.raises((ValueError, BackgroundModelResponseConflict)):
        _attach(
            fresh,
            attempt_a,
            directive,
            proof_a,
            payload=encode_model_directive(directive)[:-1] + ',"response":"duplicate"}',
        )
    with pytest.raises(BackgroundModelResponseConflict):
        _attach(
            fresh,
            attempt_a,
            directive,
            proof_a[:-1] + ("0" if proof_a[-1] != "0" else "1"),
        )


def test_ca4_a_and_ca5_identical_replay_converge_exactly_once(tmp_path):
    db = tmp_path / "ca4-ca5-once.sqlite"
    signer = ExternalSigner()
    _runtime, attempt = _dispatch_dead(db, signer)
    directive = _directive()
    proof = signer.proof(attempt.attempt_id, directive)
    fresh = _restart(db)

    first = _attach(fresh, attempt, directive, proof)
    replay = _attach(fresh, attempt, directive, proof)
    assert replay.directive_payload == first.directive_payload

    result = fresh.run_turn(
        session_id="w16-ca-session",
        turn_index=1,
        user_input=TURN_INPUT,
        occurred_at=NOW,
    )
    assert result.runtime.response == "late return exactly once"
    meters = fresh.metering.list_model_calls(
        subject_id="user_1", execution_classes=("user_interaction",)
    )
    assert len(meters) == 1

    with pytest.raises(TurnAlreadyCompleted):
        fresh.run_turn(
            session_id="w16-ca-session",
            turn_index=1,
            user_input=TURN_INPUT,
            occurred_at=NOW,
        )

    with pytest.raises(BackgroundModelResponseConflict):
        _attach(
            fresh,
            attempt,
            _directive(response="conflicting replay"),
            proof,
        )


def test_ca1_module_exports_verify_only_no_sign_function():
    import aios_core.runtime.late_return as module

    public_callables = {
        name for name, value in vars(module).items()
        if not name.startswith("_") and callable(value)
    }
    assert "late_return_message" in public_callables
    assert "verify_late_return_proof" in public_callables
    assert not any(
        name.startswith(("sign_", "mint_", "prove_"))
        for name in public_callables
    )
    assert inspect.isclass(ExternalReturnObserver)
