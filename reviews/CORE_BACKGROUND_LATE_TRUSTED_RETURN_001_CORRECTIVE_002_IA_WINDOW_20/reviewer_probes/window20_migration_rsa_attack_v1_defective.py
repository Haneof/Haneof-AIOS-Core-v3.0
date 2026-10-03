#!/usr/bin/env python3
"""WINDOW 20 Fresh Independent Acceptance — reviewer probes, batch 2.

Task: CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE
Reviewed exact candidate: fec30bd1495017bf13f08b0ef5b1e241dfb0e247 (PR #310)

Batch 2 covers the Corrective-002 migration (`BLK-W17-002`) and RSA /
`not_submitted` / exactly-once (`BLK-W17-003`, `C5`, `C6`) claims with
reviewer-owned material only.  All RSA signing below is performed by the
reviewer's own PKCS#1 v1.5 implementation over the reviewer's own private key;
no candidate signing/proof helper is used to produce any attacking proof (the
public serializer `canonical_json_dumps` is reused only to rebuild the historical
message layout that the legacy `bgresponse_v1` HMAC was defined over).

Frozen before first execution (see PROBE_FREEZE_MANIFEST_BATCH2.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import sqlite3
from pathlib import Path
import sys
import tempfile

from pydantic import ValidationError

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    BackgroundModelExecutionInDoubt,
    BackgroundModelResponseConflict,
    LateReturnEncodingError,
    LateReturnVerifier,
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
)
from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptStore,
    LegacyTrustMigrationError,
    decode_model_directive,
    encode_model_directive,
)
from aios_core.runtime.late_return import (
    LATE_RETURN_PROOF_PREFIX,
    canonical_late_return_proof,
    canonical_key_id,
    decode_late_return_proof,
    late_return_message,
    verify_late_return_proof,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
TURN_INPUT = "window20 batch-2 review input"
LEGACY_SECRET = bytes.fromhex("a1b2c3d4" * 8)

# Reviewer-owned external RSA-2048 private key (generated in the reviewer sandbox
# with `openssl genrsa 2048`; private half never entered the candidate tree).
RSA_N = int("d5adea8a26837ebc4db1815f1553b860045602d65656764198d262907674b454fd3dc2095d7f0bdc02a281a9e2fd1d33b52f4bf568900afd62d6ffe962e7f1bc69eae4596fdd9e76ee14b5b92084af432e1102a36981e34a5acdc6808683238b66ea89fac4712f84520ef0e20c163a8d0a395e978bc15bb0d1ab454d09ecfba333e5ef65f693a9c44f910a475ad08bb8855ebe8dc75c168023b58359da08eedf0d7fad8dbaf2daaa5cf6d8c7bfbcfbe2e20cd962eb5c05ebe00c4d34db9684b3c9f0bf94c4ece3562c19731eebf66576c93982d9046174138e137dd0dcb3be0b18e4f7b65acc7757e52727c3c5339876b741e1ae20a557ecc00ee363c5b42087", 16)
RSA_D = int("494c4465297af7f17e3142b0ac2f30d2f709ce255a2e849851e4f15c9ed5bfba5bb860a437c749f9298a373260a3f4ed74dc8990e0527102a4721e0d20197269f0675bf776112eb79b49cd6078d02b12bf6da45b0be93b5f9930774445601cc44804725a6c226b6b577eba90c016abf50fa9c851f1e5dd1f157d4be376612d9c18a949e8374b24157654fb34ef6dc3f4ad68dd1a27a2fec961bbbdd545393c9b2755c0da3e652df6482c4b659fcab39d7c1508ee3be630fa22dec0e097df3b5364d99e6fd8c443d7376ffcf3ba788046dc71ca6daa5b74a889cbbc00bd4cde6651052ae3870d5047de3f614deb5b4d7b3ebfaa5121e7dd7c9dd9d9c466d907e1", 16)
RSA_E = 65537
_SHA256_DER = bytes.fromhex("3031300d060960864801650304020105000420")


class SimulatedCrash(BaseException):
    pass


@dataclass(frozen=True)
class ProbeResult:
    probe_id: str
    expected: str
    actual: str
    passed: bool


def reviewer_sign(message: bytes, key_id: str) -> str:
    """Reviewer-owned PKCS#1 v1.5 SHA-256 signature -> canonical proof encoding."""
    digest_info = _SHA256_DER + hashlib.sha256(message).digest()
    width = (RSA_N.bit_length() + 7) // 8
    encoded = b"\x00\x01" + b"\xff" * (width - len(digest_info) - 3) + b"\x00" + digest_info
    signature = pow(int.from_bytes(encoded, "big"), RSA_D, RSA_N).to_bytes(width, "big")
    return f"{LATE_RETURN_PROOF_PREFIX}{key_id}:{signature.hex()}"


def make_verifier(key_id: str = "w20-ext-key") -> LateReturnVerifier:
    return LateReturnVerifier(
        key_id=key_id,
        algorithm="rsa-pkcs1v15-sha256",
        modulus_hex=f"{RSA_N:x}",
        public_exponent=RSA_E,
    )


def make_directive(
    *,
    response: str,
    provider: str = "provider-W20B",
    model: str = "model-W20B",
    request_id: str = "req-W20B-1",
) -> ModelDirective:
    return ModelDirective(
        response=response,
        capability_calls=(),
        usage=ModelUsage(
            input_tokens=3,
            output_tokens=5,
            total_tokens=8,
            provider=provider,
            model=model,
            request_id=request_id,
        ),
        provenance=ModelCallProvenance(provider=provider, model=model, request_id=request_id),
    )


def open_world(db: Path):
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def dispatch_and_crash(db: Path, *, session_id: str, verifier: LateReturnVerifier | None):
    store, index = open_world(db)

    def crashing_handler(_snapshot):
        raise SimulatedCrash("simulated loss after durable dispatch boundary")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=crashing_handler,
        subject_id="user_1",
        late_return_verifier=verifier,
    )
    try:
        runtime.run_turn(session_id=session_id, turn_index=1, user_input=TURN_INPUT, occurred_at=NOW)
    except SimulatedCrash:
        pass
    exec_id = runtime.turn_executions.execution_id_for(
        subject_id="user_1", session_id=session_id, turn_index=1
    )
    attempt = runtime.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind="user_turn", work_id=exec_id
    )[-1]
    return runtime, attempt


def fresh_recovery_runtime(db: Path, *, verifier: LateReturnVerifier | None = None):
    store, index = open_world(db)

    def forbidden(_snapshot):
        raise AssertionError("provider redispatch is forbidden during recovery")

    return FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=forbidden,
        subject_id="user_1",
        late_return_verifier=verifier,
    )


def drive_to_in_doubt(recovery, attempt):
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
    return recovery.background_model_attempts.get(attempt.attempt_id)


# -- legacy (pre-upgrade `bgresponse_v1`) trust state ------------------------
def legacy_message(fields: dict) -> bytes:
    return canonical_json_dumps(
        {
            "attempt_id": fields["attempt_id"],
            "model": fields["model"],
            "model_round_index": int(fields["model_round_index"]),
            "outbound_request_fingerprint": fields["outbound_request_fingerprint"],
            "payload_sha256": fields["payload_sha256"],
            "provider": fields["provider"],
            "provider_request_id": fields["provider_request_id"],
            "relay_id": fields["relay_id"],
            "response_fingerprint": fields["response_fingerprint"],
            "schema": "aios.background-model-response-receipt.v1",
            "subject_id": fields["subject_id"],
            "work_id": fields["work_id"],
            "work_kind": fields["work_kind"],
        }
    ).encode("utf-8")


def legacy_proof(fields: dict, secret: bytes = LEGACY_SECRET) -> str:
    return "bgresponse_v1_" + hmac.new(secret, legacy_message(fields), hashlib.sha256).hexdigest()


def insert_legacy_state(db: Path, attempts, directives) -> dict[str, dict]:
    """Create the legacy authority table + valid v1 receipt/handoff rows."""
    fields_by_attempt: dict[str, dict] = {}
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            CREATE TABLE background_model_authenticity_authority (
                authority_id TEXT PRIMARY KEY,
                secret_hex TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO background_model_authenticity_authority(authority_id, secret_hex) VALUES (?, ?)",
            ("trusted-return-v1", LEGACY_SECRET.hex()),
        )
        for attempt, directive in zip(attempts, directives):
            binding = conn.execute(
                "SELECT * FROM background_model_request_bindings WHERE attempt_id=?",
                (attempt.attempt_id,),
            ).fetchone()
            assert binding is not None
            payload = encode_model_directive(directive)
            payload_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            provider, model, request_id = BackgroundModelAttemptStore._provider_identity(directive)
            fields = {
                "attempt_id": attempt.attempt_id,
                "subject_id": attempt.subject_id,
                "work_kind": attempt.work_kind,
                "work_id": attempt.work_id,
                "model_round_index": int(attempt.model_round_index),
                "outbound_request_fingerprint": binding["outbound_request_fingerprint"],
                "relay_id": binding["relay_id"],
                "provider": provider,
                "model": model,
                "provider_request_id": request_id,
                "response_fingerprint": BackgroundModelAttemptStore._response_fingerprint(directive),
                "payload_sha256": payload_sha256,
            }
            fields_by_attempt[attempt.attempt_id] = fields
            proof = legacy_proof(fields)
            conn.execute(
                """
                INSERT INTO background_model_response_receipts(
                    attempt_id, subject_id, work_kind, work_id, model_round_index,
                    outbound_request_fingerprint, relay_id, provider, model,
                    provider_request_id, response_fingerprint, payload_sha256,
                    authenticity_proof, captured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*fields.values(), proof, "2026-10-02T12:00:00Z"),
            )
            conn.execute(
                """
                INSERT INTO background_model_return_handoffs(
                    attempt_id, directive_payload, payload_sha256, authenticity_proof
                ) VALUES (?, ?, ?, ?)
                """,
                (attempt.attempt_id, payload, payload_sha256, proof),
            )
        conn.commit()
    return fields_by_attempt


def dump_trust_state(db: Path) -> dict:
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        state = {
            "receipts": {
                r["attempt_id"]: r["authenticity_proof"]
                for r in conn.execute("SELECT * FROM background_model_response_receipts").fetchall()
            },
            "handoffs": {
                r["attempt_id"]: r["authenticity_proof"]
                for r in conn.execute("SELECT * FROM background_model_return_handoffs").fetchall()
            },
            "responses": {
                r["attempt_id"]: r["authenticity_proof"]
                for r in conn.execute("SELECT * FROM background_model_responses").fetchall()
            },
            "attempt_states": {
                r["attempt_id"]: r["state"]
                for r in conn.execute("SELECT * FROM background_model_attempts").fetchall()
            },
            "legacy_secret": None,
            "legacy_table": False,
        }
        tables = {
            t[0]
            for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "background_model_authenticity_authority" in tables:
            state["legacy_table"] = True
            rows = conn.execute(
                "SELECT authority_id, secret_hex FROM background_model_authenticity_authority"
            ).fetchall()
            state["legacy_secret"] = [(r["authority_id"], r["secret_hex"]) for r in rows]
    return state


# ---------------------------------------------------------------------------
# IA20-MIGRATE-003 — multi-row conversion atomicity / fail-closed retry
# ---------------------------------------------------------------------------
def probe_ia20_migrate_003_multi_row_atomicity(root: Path) -> ProbeResult:
    db = root / "ia20-migrate-003.sqlite"
    attempts = []
    directives = []
    for index in range(3):
        _, attempt = dispatch_and_crash(db, session_id=f"sess-m003-{index}", verifier=None)
        attempts.append(attempt)
        directives.append(make_directive(response=f"legacy row {index}", request_id=f"req-m003-{index}"))
    insert_legacy_state(db, attempts, directives)

    # Tamper the LAST row only, after two valid rows: a converter that writes as
    # it goes would leave rows 1..2 already normalized.
    tampered_id = attempts[-1].attempt_id
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE background_model_response_receipts SET authenticity_proof=? WHERE attempt_id=?",
            ("bgresponse_v1_" + "00" * 32, tampered_id),
        )
        conn.commit()

    before = dump_trust_state(db)
    refused_first = None
    try:
        fresh_recovery_runtime(db)
        refused_first = "NO-RAISE"
    except BaseException as exc:  # noqa: BLE001
        refused_first = f"{type(exc).__name__}"
    after_first = dump_trust_state(db)

    refused_retry = None
    try:
        fresh_recovery_runtime(db)
        refused_retry = "NO-RAISE"
    except BaseException as exc:  # noqa: BLE001
        refused_retry = f"{type(exc).__name__}"
    after_retry = dump_trust_state(db)

    unchanged = before == after_first == after_retry
    no_v2 = not any(
        isinstance(p, str) and p.startswith("bgresponse_v2_")
        for group in ("receipts", "handoffs", "responses")
        for p in after_retry[group].values()
    )
    secret_preserved = after_retry["legacy_table"] and after_retry["legacy_secret"] == before["legacy_secret"]
    fail_closed = refused_first.startswith("LegacyTrustMigrationError") and refused_retry.startswith(
        "LegacyTrustMigrationError"
    )
    passed = bool(unchanged and no_v2 and secret_preserved and fail_closed)
    return ProbeResult(
        "IA20-MIGRATE-003",
        "a tampered legacy row (even as the last of several) converts nothing, purges no secret, and every retry fails closed identically",
        (
            f"first={refused_first}, retry={refused_retry}, state_unchanged={unchanged}, "
            f"no_v2_proof_anywhere={no_v2}, secret_preserved={secret_preserved}, "
            f"tampered_attempt={tampered_id}"
        ),
        passed,
    )


# ---------------------------------------------------------------------------
# IA20-MIGRATE-004 — legacy edge/empty-branch matrix
# ---------------------------------------------------------------------------
def probe_ia20_migrate_004_edge_branches(root: Path) -> ProbeResult:
    outcomes: dict[str, str] = {}

    def base_db(name: str) -> tuple[Path, object]:
        db = root / f"ia20-migrate-004-{name}.sqlite"
        _, attempt = dispatch_and_crash(db, session_id=f"sess-m004-{name}", verifier=None)
        return db, attempt

    # (a) authority + no receipts/handoffs + staged response carrying a legacy proof
    db, attempt = base_db("a")
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE background_model_authenticity_authority(authority_id TEXT PRIMARY KEY, secret_hex TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO background_model_authenticity_authority VALUES ('trusted-return-v1', ?)",
            (LEGACY_SECRET.hex(),),
        )
        conn.execute(
            """
            INSERT INTO background_model_responses(
                attempt_id, provider, model, provider_request_id, response_fingerprint,
                directive_payload, payload_sha256, authenticity_proof, staged_at
            ) VALUES (?, 'p', 'm', 'r', ?, ?, ?, ?, '2026-10-02T12:00:00Z')
            """,
            (
                attempt.attempt_id,
                "f" * 64,
                encode_model_directive(make_directive(response="orphan staged")),
                "e" * 64,
                "bgresponse_v1_" + "11" * 32,
            ),
        )
        conn.commit()
    try:
        fresh_recovery_runtime(db)
        outcomes["a"] = "NO-RAISE"
    except BaseException as exc:  # noqa: BLE001
        outcomes["a"] = type(exc).__name__
    state_a = dump_trust_state(db)
    outcomes["a_detail"] = (
        f"secret_preserved={state_a['legacy_secret'] == [('trusted-return-v1', LEGACY_SECRET.hex())]}, "
        f"staged_unchanged={'bgresponse_v1_' + '11' * 32 == state_a['responses'].get(attempt.attempt_id)}"
    )

    # (b) authority + no receipts/handoffs + staged response with a v2 fingerprint
    db, attempt = base_db("b")
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE background_model_authenticity_authority(authority_id TEXT PRIMARY KEY, secret_hex TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO background_model_authenticity_authority VALUES ('trusted-return-v1', ?)",
            (LEGACY_SECRET.hex(),),
        )
        conn.execute(
            """
            INSERT INTO background_model_responses(
                attempt_id, provider, model, provider_request_id, response_fingerprint,
                directive_payload, payload_sha256, authenticity_proof, staged_at
            ) VALUES (?, 'p', 'm', 'r', ?, ?, ?, ?, '2026-10-02T12:00:00Z')
            """,
            (
                attempt.attempt_id,
                "f" * 64,
                encode_model_directive(make_directive(response="v2 staged no receipt")),
                "e" * 64,
                "bgresponse_v2_" + "22" * 32,
            ),
        )
        conn.commit()
    try:
        fresh_recovery_runtime(db)
        outcomes["b"] = "completed"
    except BaseException as exc:  # noqa: BLE001
        outcomes["b"] = type(exc).__name__
    state_b = dump_trust_state(db)
    outcomes["b_detail"] = (
        f"secret_purged={state_b['legacy_secret'] is None and not state_b['legacy_table']}, "
        f"receipts_created={len(state_b['receipts'])}, "
        f"attempt_state={state_b['attempt_states'].get(attempt.attempt_id)}"
    )

    # (c) two authority rows
    db, _ = base_db("c")
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE background_model_authenticity_authority(authority_id TEXT PRIMARY KEY, secret_hex TEXT NOT NULL)"
        )
        conn.executemany(
            "INSERT INTO background_model_authenticity_authority VALUES (?, ?)",
            [("trusted-return-v1", LEGACY_SECRET.hex()), ("trusted-return-v2", "ab" * 32)],
        )
        conn.commit()
    try:
        fresh_recovery_runtime(db)
        outcomes["c"] = "NO-RAISE"
    except BaseException as exc:  # noqa: BLE001
        outcomes["c"] = type(exc).__name__
    outcomes["c_detail"] = f"rows_preserved={len(dump_trust_state(db)['legacy_secret'] or [])}"

    # (d) wrong authority id
    db, _ = base_db("d")
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE background_model_authenticity_authority(authority_id TEXT PRIMARY KEY, secret_hex TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO background_model_authenticity_authority VALUES ('attacker-authority', ?)",
            (LEGACY_SECRET.hex(),),
        )
        conn.commit()
    try:
        fresh_recovery_runtime(db)
        outcomes["d"] = "NO-RAISE"
    except BaseException as exc:  # noqa: BLE001
        outcomes["d"] = type(exc).__name__

    # (e) non-hex secret, (f) wrong-length secret
    for label, secret_hex in (("e", "zz" * 32), ("f", "ab" * 31)):
        db, _ = base_db(label)
        with sqlite3.connect(db) as conn:
            conn.execute(
                "CREATE TABLE background_model_authenticity_authority(authority_id TEXT PRIMARY KEY, secret_hex TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT INTO background_model_authenticity_authority VALUES ('trusted-return-v1', ?)",
                (secret_hex,),
            )
            conn.commit()
        try:
            fresh_recovery_runtime(db)
            outcomes[label] = "NO-RAISE"
        except BaseException as exc:  # noqa: BLE001
            outcomes[label] = type(exc).__name__
        outcomes[f"{label}_detail"] = f"secret_preserved={dump_trust_state(db)['legacy_secret'] is not None}"

    # (g) authority present but receipts already carry v2 fingerprints
    db, attempt = base_db("g")
    fields = insert_legacy_state(db, [attempt], [make_directive(response="already converted")])
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE background_model_response_receipts SET authenticity_proof=? WHERE attempt_id=?",
            ("bgresponse_v2_" + "33" * 32, attempt.attempt_id),
        )
        conn.commit()
    try:
        fresh_recovery_runtime(db)
        outcomes["g"] = "NO-RAISE"
    except BaseException as exc:  # noqa: BLE001
        outcomes["g"] = type(exc).__name__
    outcomes["g_detail"] = f"secret_preserved={dump_trust_state(db)['legacy_secret'] is not None}"

    # (h) orphan receipt without handoff
    db, attempt = base_db("h")
    insert_legacy_state(db, [attempt], [make_directive(response="orphan receipt")])
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM background_model_return_handoffs WHERE attempt_id=?", (attempt.attempt_id,))
        conn.commit()
    try:
        fresh_recovery_runtime(db)
        outcomes["h"] = "NO-RAISE"
    except BaseException as exc:  # noqa: BLE001
        outcomes["h"] = type(exc).__name__
    outcomes["h_detail"] = f"secret_preserved={dump_trust_state(db)['legacy_secret'] is not None}"

    expected = {
        "a": "LegacyTrustMigrationError",
        "b": "completed",
        "c": "LegacyTrustMigrationError",
        "d": "LegacyTrustMigrationError",
        "e": "LegacyTrustMigrationError",
        "f": "LegacyTrustMigrationError",
        "g": "LegacyTrustMigrationError",
        "h": "LegacyTrustMigrationError",
    }
    wrong = {k: v for k, v in outcomes.items() if not k.endswith("_detail") and v != expected[k]}
    details_ok = all(
        outcomes.get(key, "").endswith("True") or "receipts_created=0" in outcomes.get(key, "")
        for key in ("a_detail", "b_detail", "c_detail", "e_detail", "f_detail", "g_detail", "h_detail")
    )
    return ProbeResult(
        "IA20-MIGRATE-004",
        "legacy edge branches fail closed (a,c,d,e,f,g,h) with the secret preserved, and the empty-trust-state branch never launders (b)",
        f"outcomes={outcomes}, unexpected={wrong}, details_ok={details_ok}",
        not wrong and details_ok,
    )


# ---------------------------------------------------------------------------
# IA20-RSA-ENC-001 — frozen proof/key-id encoding grammar
# ---------------------------------------------------------------------------
def probe_ia20_rsa_enc_001_encoding_grammar(root: Path) -> ProbeResult:
    del root
    accepted: list[str] = []
    refused: list[str] = []

    valid_ids = ["0", "a", "Z", "key-2026.v1_x", "9" + "a" * 127, "A.b-c_d"]
    for key_id in valid_ids:
        try:
            verifier = make_verifier(key_id)
            proof = canonical_late_return_proof(key_id=key_id, signature_hex="ab" * 256)
            decoded_id, decoded_sig = decode_late_return_proof(proof)
            ok = decoded_id == key_id and decoded_sig == "ab" * 256
            # genuine signature under the same key id must verify for the exact message
            directive = make_directive(response="encoding probe")
            fields = {
                "attempt_id": "bgattempt_enc",
                "subject_id": "user_1",
                "work_kind": "user_turn",
                "work_id": "work_enc",
                "model_round_index": 0,
                "outbound_request_fingerprint": "a" * 64,
                "relay_id": "relay_enc",
                "provider": "provider-W20B",
                "model": "model-W20B",
                "provider_request_id": "req-W20B-1",
                "response_fingerprint": "b" * 64,
                "payload_sha256": hashlib.sha256(
                    encode_model_directive(directive).encode()
                ).hexdigest(),
            }
            message = late_return_message(**fields)
            genuine = reviewer_sign(message, key_id)
            verified = verify_late_return_proof(verifier, message=message, proof=genuine)
            accepted.append(f"{key_id!r}:roundtrip={ok},genuine_verify={verified}")
        except BaseException as exc:  # noqa: BLE001
            refused.append(f"{key_id!r}:UNEXPECTED_REFUSAL:{type(exc).__name__}")

    invalid_ids = [
        "",
        ":",
        "a:b",
        " a",
        "a ",
        "a\nb",
        "a\tb",
        "a\x00",
        "\x00a",
        "key\u200b1",
        "ke\u0443",
        "a" * 129,
        "-abc",
        ".abc",
        "_abc",
        "two words",
    ]
    wrongly_accepted = []
    for key_id in invalid_ids:
        try:
            make_verifier(key_id)
            wrongly_accepted.append(repr(key_id))
        except BaseException:  # noqa: BLE001
            pass

    # proof-level malformed encodings
    malformed = [
        "bglate_rsa_v1:key:" + "ab" * 256 + ":extra",
        "bglate_rsa_v1:key",
        "bglate_rsa_v1::" + "ab" * 256,
        "bglate_rsa_v1:key:",
        "bglate_rsa_v1:key:" + "AB" * 256,
        "bglate_rsa_v1:key:0x12ab",
        "bglate_rsa_v1:key:12 34",
        "bglate_rsa_v1:key:zz",
    ]
    malformed_accepted = []
    for proof in malformed:
        try:
            decode_late_return_proof(proof)
            malformed_accepted.append(proof[:32])
        except BaseException:  # noqa: BLE001
            pass

    # odd-length signature: representable but must never verify
    odd_len_note = "n/a"
    try:
        odd_proof = canonical_late_return_proof(key_id="key-odd", signature_hex="abc")
        verifier = make_verifier("key-odd")
        directive = make_directive(response="odd")
        fields = {
            "attempt_id": "bgattempt_odd",
            "subject_id": "user_1",
            "work_kind": "user_turn",
            "work_id": "work_odd",
            "model_round_index": 0,
            "outbound_request_fingerprint": "a" * 64,
            "relay_id": "relay_odd",
            "provider": "provider-W20B",
            "model": "model-W20B",
            "provider_request_id": "req-W20B-1",
            "response_fingerprint": "b" * 64,
            "payload_sha256": "c" * 64,
        }
        message = late_return_message(**fields)
        odd_len_note = f"representable=True, verifies={verify_late_return_proof(verifier, message=message, proof=odd_proof)}"
    except BaseException as exc:  # noqa: BLE001
        odd_len_note = f"representable=False:{type(exc).__name__}"

    passed = not refused and not wrongly_accepted and not malformed_accepted
    return ProbeResult(
        "IA20-RSA-ENC-001",
        "every accepted key_id round-trips exactly and verifies genuine signatures; non-canonical ids and ambiguous proofs are refused",
        (
            f"accepted={accepted}, unexpected_refusals={refused}, wrongly_accepted={wrongly_accepted}, "
            f"malformed_accepted={malformed_accepted}, odd_length_signature={odd_len_note}"
        ),
        passed,
    )


# ---------------------------------------------------------------------------
# IA20-RSA-PARAM-001 — durable verifier parameter validation matrix
# ---------------------------------------------------------------------------
def probe_ia20_rsa_param_001_parameter_matrix(root: Path) -> ProbeResult:
    del root
    base_hex = f"{RSA_N:x}"
    even_modulus = format((RSA_N - 1) | 1, "x")  # keep odd? build an even value instead:
    even_modulus = format(RSA_N - 1, "x")
    undersized_hex = format((1 << 2047) - 1, "x")

    modulus_cases = {
        "negative": "-" + base_hex,
        "zero": "0",
        "one": "1",
        "two_even": "2",
        "even_2048": even_modulus,
        "undersized_2047": undersized_hex,
        "leading_zero": "0" + base_hex,
        "plus_prefixed": "+" + base_hex,
        "zero_x_prefixed": "0x" + base_hex,
        "uppercase": base_hex.upper(),
        "whitespace": " " + base_hex,
        "trailing_whitespace": base_hex + " ",
        "non_hex": "zz" * 256,
    }
    exponent_cases = {
        "bool_true": True,
        "bool_false": False,
        "float": 65537.0,
        "none": None,
        "negative": -3,
        "zero": 0,
        "one": 1,
        "two_even": 2,
        "even_four": 4,
        "e_ge_n": RSA_N,
    }
    algorithm_cases = {"uppercase": "RSA-PKCS1V15-SHA256", "sha1": "rsa-pkcs1v15-sha1", "empty": ""}

    failures: list[str] = []
    for label, modulus in modulus_cases.items():
        try:
            LateReturnVerifier(
                key_id="k", algorithm="rsa-pkcs1v15-sha256", modulus_hex=modulus, public_exponent=RSA_E
            )
            failures.append(f"modulus_{label}:ACCEPTED")
        except BaseException:  # noqa: BLE001
            pass
    for label, exponent in exponent_cases.items():
        try:
            LateReturnVerifier(
                key_id="k",
                algorithm="rsa-pkcs1v15-sha256",
                modulus_hex=base_hex,
                public_exponent=exponent,
            )
            failures.append(f"exponent_{label}:ACCEPTED")
        except BaseException:  # noqa: BLE001
            pass
    for label, algorithm in algorithm_cases.items():
        try:
            LateReturnVerifier(
                key_id="k", algorithm=algorithm, modulus_hex=base_hex, public_exponent=RSA_E
            )
            failures.append(f"algorithm_{label}:ACCEPTED")
        except BaseException:  # noqa: BLE001
            pass

    legal: list[str] = []
    for label, exponent in (("e3", 3), ("e65537", 65537)):
        try:
            LateReturnVerifier(
                key_id="k", algorithm="rsa-pkcs1v15-sha256", modulus_hex=base_hex, public_exponent=exponent
            )
            legal.append(label)
        except BaseException as exc:  # noqa: BLE001
            failures.append(f"{label}:REFUSED:{type(exc).__name__}")
    # the canonical 2048-bit odd reviewer modulus must be accepted
    try:
        LateReturnVerifier(
            key_id="k", algorithm="rsa-pkcs1v15-sha256", modulus_hex=base_hex, public_exponent=65537
        )
        legal.append("modulus_2048_valid")
    except BaseException as exc:  # noqa: BLE001
        failures.append(f"modulus_2048_valid:REFUSED:{type(exc).__name__}")

    return ProbeResult(
        "IA20-RSA-PARAM-001",
        "signed/zero/even/undersized/non-normalized moduli and non-canonical exponents/algorithms are refused at construction; legal parameters are accepted",
        f"unexpected={failures}, accepted_legal={legal}",
        not failures,
    )


# ---------------------------------------------------------------------------
# IA20-RSA-TRANSPLANT-001 — genuine signature + 12-field transplant matrix
# ---------------------------------------------------------------------------
def _signing_fields(attempt, binding, directive, verifier_key_id: str) -> dict:
    payload = encode_model_directive(directive)
    provider, model, request_id = BackgroundModelAttemptStore._provider_identity(directive)
    return {
        "attempt_id": attempt.attempt_id,
        "subject_id": attempt.subject_id,
        "work_kind": attempt.work_kind,
        "work_id": attempt.work_id,
        "model_round_index": int(attempt.model_round_index),
        "outbound_request_fingerprint": binding.outbound_request_fingerprint,
        "relay_id": binding.relay_id,
        "provider": provider,
        "model": model,
        "provider_request_id": request_id,
        "response_fingerprint": BackgroundModelAttemptStore._response_fingerprint(directive),
        "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "verifier_key_id": verifier_key_id,
    }


def probe_ia20_rsa_transplant_001_field_binding(root: Path) -> ProbeResult:
    outcome: dict[str, str] = {}

    # positive control: a genuine reviewer-signed return must be accepted once
    db = root / "ia20-transplant-positive.sqlite"
    key_id = "w20-ext-key"
    _, attempt = dispatch_and_crash(db, session_id="sess-transplant-pos", verifier=make_verifier(key_id))
    recovery = fresh_recovery_runtime(db)
    in_doubt = drive_to_in_doubt(recovery, attempt)
    assert in_doubt is not None and in_doubt.state == "in_doubt"
    binding = recovery.background_model_attempts.outbound_request_binding(attempt.attempt_id)
    genuine = make_directive(response="genuine reviewer-signed return")
    fields = _signing_fields(attempt, binding, genuine, key_id)
    message = late_return_message(**{k: v for k, v in fields.items() if k != "verifier_key_id"})
    proof = reviewer_sign(message, key_id)
    try:
        recovery.background_model_attempts.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(seconds=20),
            directive_payload=encode_model_directive(genuine),
            late_return_proof=proof,
            evidence="reviewer genuine external signature",
        )
        result = recovery.run_turn(
            session_id="sess-transplant-pos", turn_index=1, user_input=TURN_INPUT, occurred_at=NOW
        )
        meters = len(
            recovery.metering.list_model_calls(
                subject_id="user_1", execution_classes=("user_interaction",)
            )
        )
        outcome["positive"] = (
            f"completed response={result.runtime.response!r} meters={meters}"
        )
    except BaseException as exc:  # noqa: BLE001
        outcome["positive"] = f"REFUSED:{type(exc).__name__}:{exc}"

    # transplant matrix: keep a valid signature, move each bound field
    transplants = {
        "attempt_id": "bgattempt_other",
        "subject_id": "user_2",
        "work_kind": "wake_reason",
        "work_id": "work_other",
        "model_round_index": 7,
        "outbound_request_fingerprint": "f" * 64,
        "relay_id": "relay_other",
        "provider": "provider-other",
        "model": "model-other",
        "provider_request_id": "req-other",
        "response_fingerprint": "e" * 64,
        "payload_sha256": "d" * 64,
    }
    accepted_transplants: list[str] = []
    for label, mutated in transplants.items():
        db_t = root / f"ia20-transplant-{label}.sqlite"
        _, attempt_t = dispatch_and_crash(
            db_t, session_id=f"sess-transplant-{label}", verifier=make_verifier(key_id)
        )
        recovery_t = fresh_recovery_runtime(db_t)
        drive_to_in_doubt(recovery_t, attempt_t)
        binding_t = recovery_t.background_model_attempts.outbound_request_binding(attempt_t.attempt_id)
        directive_t = make_directive(response=f"transplant {label}")
        fields_t = _signing_fields(attempt_t, binding_t, directive_t, key_id)
        message_t = late_return_message(
            **{k: v for k, v in fields_t.items() if k != "verifier_key_id"}
        )
        # sign the MUTATED field set, then present the ORIGINAL payload:
        mutated_fields = dict(fields_t)
        mutated_fields[label] = mutated
        mutated_message = late_return_message(
            **{k: v for k, v in mutated_fields.items() if k != "verifier_key_id"}
        )
        proof_t = reviewer_sign(mutated_message, key_id)
        try:
            recovery_t.background_model_attempts.attach_late_trusted_return(
                attempt_t.attempt_id,
                attached_at=NOW + timedelta(seconds=20),
                directive_payload=encode_model_directive(directive_t),
                late_return_proof=proof_t,
                evidence=f"transplant {label}",
            )
            accepted_transplants.append(label)
        except BaseException:  # noqa: BLE001
            pass

    passed = (
        outcome.get("positive", "").startswith("completed")
        and "meters=1" in outcome.get("positive", "")
        and not accepted_transplants
    )
    return ProbeResult(
        "IA20-RSA-TRANSPLANT-001",
        "reviewer-signed genuine return completes exactly once; every one of the 12 bound-field transplants is rejected",
        f"positive={outcome.get('positive')}, accepted_transplants={accepted_transplants}",
        passed,
    )


# ---------------------------------------------------------------------------
# IA20-NOTSUB-002 — post-binding not_submitted must be impossible
# ---------------------------------------------------------------------------
def probe_ia20_notsub_002_post_binding_downgrade(root: Path) -> ProbeResult:
    outcome: dict[str, str] = {}
    db = root / "ia20-notsub-002.sqlite"
    _, attempt = dispatch_and_crash(db, session_id="sess-notsub-002", verifier=make_verifier())
    recovery = fresh_recovery_runtime(db)
    state_before = recovery.background_model_attempts.get(attempt.attempt_id).state

    for label, call in (
        (
            "reconcile_not_submitted",
            lambda: recovery.background_model_attempts.reconcile_not_submitted(
                attempt.attempt_id,
                reconciled_at=NOW + timedelta(seconds=5),
                evidence="reviewer caller asserts it probably was not sent",
            ),
        ),
        (
            "mark_failure_timeout",
            lambda: recovery.background_model_attempts.mark_failure(
                attempt.attempt_id,
                failed_at=NOW + timedelta(seconds=6),
                definitely_not_submitted=True,
                error=RuntimeError("socket timeout"),
            ),
        ),
    ):
        try:
            call()
            outcome[label] = "ACCEPTED"
        except BaseException as exc:  # noqa: BLE001
            outcome[label] = f"refused:{type(exc).__name__}"
        outcome[f"{label}_state"] = recovery.background_model_attempts.get(attempt.attempt_id).state

    # a second run_turn must not redispatch (handler raises if invoked)
    dispatched = {"called": False}

    def forbidden(_snapshot):
        dispatched["called"] = True
        raise AssertionError("redispatch attempted")

    store, index = open_world(db)
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=forbidden,
        subject_id="user_1",
        late_return_verifier=make_verifier(),
    )
    try:
        runtime.run_turn(session_id="sess-notsub-002", turn_index=1, user_input=TURN_INPUT, occurred_at=NOW)
        outcome["second_run"] = "completed"
    except BaseException as exc:  # noqa: BLE001
        outcome["second_run"] = f"refused:{type(exc).__name__}"
    outcome["redispatch_called"] = dispatched["called"]
    final_state = runtime.background_model_attempts.get(attempt.attempt_id).state

    passed = (
        outcome["reconcile_not_submitted"].startswith("refused")
        and outcome["mark_failure_timeout"].startswith("refused")
        and outcome["reconcile_not_submitted_state"] != "not_submitted"
        and outcome["mark_failure_timeout_state"] != "not_submitted"
        and dispatched["called"] is False
        and final_state != "not_submitted"
    )
    return ProbeResult(
        "IA20-NOTSUB-002",
        "after the durable dispatch/binding boundary, no caller assertion can write not_submitted and no redispatch occurs",
        f"state_before={state_before}, outcome={outcome}, final_state={final_state}",
        passed,
    )


# ---------------------------------------------------------------------------
# IA20-EXACTONCE-001 — first writer wins, no duplicate meter/output
# ---------------------------------------------------------------------------
def probe_ia20_exactonce_001_duplicate_and_conflict(root: Path) -> ProbeResult:
    db = root / "ia20-exactonce-001.sqlite"
    key_id = "w20-ext-key"
    _, attempt = dispatch_and_crash(db, session_id="sess-exactonce", verifier=make_verifier(key_id))
    recovery = fresh_recovery_runtime(db)
    drive_to_in_doubt(recovery, attempt)
    binding = recovery.background_model_attempts.outbound_request_binding(attempt.attempt_id)

    def signed_payload(directive):
        fields = _signing_fields(attempt, binding, directive, key_id)
        message = late_return_message(**{k: v for k, v in fields.items() if k != "verifier_key_id"})
        return encode_model_directive(directive), reviewer_sign(message, key_id)

    first = make_directive(response="first accepted payload")
    payload_a, proof_a = signed_payload(first)
    outcome: dict[str, str] = {}
    try:
        recovery.background_model_attempts.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(seconds=20),
            directive_payload=payload_a,
            late_return_proof=proof_a,
            evidence="first genuine return",
        )
        outcome["first"] = "accepted"
    except BaseException as exc:  # noqa: BLE001
        outcome["first"] = f"refused:{type(exc).__name__}"

    result = recovery.run_turn(
        session_id="sess-exactonce", turn_index=1, user_input=TURN_INPUT, occurred_at=NOW
    )
    meters_after_first = len(
        recovery.metering.list_model_calls(subject_id="user_1", execution_classes=("user_interaction",))
    )

    second = make_directive(response="conflicting second payload")
    payload_b, proof_b = signed_payload(second)
    for label, (payload, proof) in (
        ("conflicting_second", (payload_b, proof_b)),
        ("exact_replay_first", (payload_a, proof_a)),
    ):
        try:
            recovery.background_model_attempts.attach_late_trusted_return(
                attempt.attempt_id,
                attached_at=NOW + timedelta(seconds=30),
                directive_payload=payload,
                late_return_proof=proof,
                evidence=f"{label} attempt",
            )
            outcome[label] = "ACCEPTED"
        except BaseException as exc:  # noqa: BLE001
            outcome[label] = f"refused:{type(exc).__name__}"

    final_attempt = recovery.background_model_attempts.get(attempt.attempt_id)
    meters_final = len(
        recovery.metering.list_model_calls(subject_id="user_1", execution_classes=("user_interaction",))
    )
    inspection = recovery.inspect_turn_execution(
        session_id="sess-exactonce",
        turn_index=1,
        user_input=TURN_INPUT,
        occurred_at=NOW,
    )
    passed = (
        outcome["first"] == "accepted"
        and result.runtime.response == "first accepted payload"
        and meters_after_first == 1
        and meters_final == 1
        and outcome["conflicting_second"].startswith("refused")
        and outcome["exact_replay_first"].startswith("refused")
        and final_attempt is not None
        and final_attempt.state == "metered"
        and inspection.state == "completed"
        and inspection.assistant_ref is not None
    )
    return ProbeResult(
        "IA20-EXACTONCE-001",
        "first genuine return wins; conflicting and replayed returns are refused with exactly one meter, one output, one completion",
        (
            f"outcome={outcome}, response={result.runtime.response!r}, meters={meters_final}, "
            f"state={final_attempt.state if final_attempt else None}, "
            f"execution_state={inspection.state}, assistant_ref={'set' if inspection.assistant_ref else None}"
        ),
        passed,
    )


PROBES = (
    probe_ia20_migrate_003_multi_row_atomicity,
    probe_ia20_migrate_004_edge_branches,
    probe_ia20_rsa_enc_001_encoding_grammar,
    probe_ia20_rsa_param_001_parameter_matrix,
    probe_ia20_rsa_transplant_001_field_binding,
    probe_ia20_notsub_002_post_binding_downgrade,
    probe_ia20_exactonce_001_duplicate_and_conflict,
)


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory(prefix="w20-ia-batch2-") as tmp:
        root = Path(tmp)
        for probe_fn in PROBES:
            try:
                res = probe_fn(root)
            except BaseException as exc:  # noqa: BLE001
                res = ProbeResult(probe_fn.__name__, "probe executes", f"PROBE_CRASH:{type(exc).__name__}:{exc}", False)
            status = "PASS" if res.passed else "FAIL"
            if not res.passed:
                failures += 1
            print(f"{status} | {res.probe_id}")
            print(f"  expected: {res.expected}")
            print(f"  actual:   {res.actual}")
    print(f"SUMMARY | probes={len(PROBES)} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
