"""Durable non-world admission for background model execution.

A background Wake/Periodic Review model round gets a stable attempt identity before
provider dispatch. The table records execution uncertainty only; token/usage truth
remains in ModelMeteringLedger.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aios_core.contracts.time import as_utc, canonical_utc_iso
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore

from .capabilities import CapabilityCall
from .cognitive_runtime import ModelCallProvenance, ModelDirective, ModelUsage
from .late_return import (
    LateReturnSigningContext,
    LateReturnVerifier,
    LateReturnVerifierError,
    late_return_message,
    verify_late_return_proof,
)


BackgroundAttemptWorkKind = Literal["wake", "periodic_review", "user_turn"]
BackgroundAttemptState = Literal[
    "admitted",
    "dispatching",
    "not_submitted",
    "in_doubt",
    "response_returned",
    "metered",
]

_DIRECTIVE_FIELDS = frozenset(
    {"capability_calls", "response", "silence", "usage", "provenance"}
)
_CAPABILITY_CALL_FIELDS = frozenset({"name", "arguments", "call_id"})
_USAGE_FIELDS = frozenset(
    {
        "total_tokens",
        "input_tokens",
        "output_tokens",
        "provider",
        "model",
        "request_id",
    }
)
_PROVENANCE_FIELDS = frozenset({"provider", "model", "request_id"})

# Legacy (pre-Corrective-001) keyed authenticator.  Its key lived in the same
# runtime database, which is exactly why `C2-4` requires it to be verified before
# anything derived from it is trusted, and purged atomically afterwards.
_LEGACY_AUTHORITY_ID = "trusted-return-v1"
_LEGACY_RECEIPT_PROOF_PREFIX = "bgresponse_v1_"


class LegacyTrustMigrationError(RuntimeError):
    """Legacy trust state could not be authenticated; nothing was converted."""


def encode_model_directive(directive: ModelDirective) -> str:
    """Deterministic, lossless JSON encoding of one exact provider directive.

    This is the Core-owned exact-response representation. It carries no defaults:
    the encoder and the strict decoder are a matched pair, so a staged payload can
    be re-verified against the durable response fingerprint without interpretation.
    """

    if not isinstance(directive, ModelDirective):
        raise TypeError("directive must be ModelDirective")
    payload = {
        "capability_calls": [
            {
                "arguments": dict(call.arguments),
                "call_id": call.call_id,
                "name": call.name,
            }
            for call in directive.capability_calls
        ],
        "response": directive.response,
        "silence": bool(directive.silence),
        "usage": (
            None
            if directive.usage is None
            else {
                "input_tokens": directive.usage.input_tokens,
                "model": directive.usage.model,
                "output_tokens": directive.usage.output_tokens,
                "provider": directive.usage.provider,
                "request_id": directive.usage.request_id,
                "total_tokens": directive.usage.total_tokens,
            }
        ),
        "provenance": (
            None
            if directive.provenance is None
            else {
                "model": directive.provenance.model,
                "provider": directive.provenance.provider,
                "request_id": directive.provenance.request_id,
            }
        ),
    }
    return canonical_json_dumps(payload)


def _strict_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate object keys before any last-key-wins normalization.

    ``json.loads`` calls this hook for every object, including nested usage,
    provenance, capability-call and capability-argument objects. Raising here
    happens before a dict is returned, so semantic construction never sees a
    silently overwritten field.
    """

    parsed: dict[str, object] = {}
    for key, value in pairs:
        if key in parsed:
            raise ValueError(
                "exact provider response payload contains a duplicate JSON key: "
                f"{key}"
            )
        parsed[key] = value
    return parsed


def decode_model_directive(payload: str) -> ModelDirective:
    """Strictly decode an exact provider directive; no defaults, no fallback."""

    if not isinstance(payload, str) or not payload.strip():
        raise ValueError("exact provider response payload must be non-blank text")
    try:
        raw = json.loads(payload, object_pairs_hook=_strict_json_object)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "exact provider response payload is not valid JSON"
        ) from exc
    if not isinstance(raw, dict) or set(raw) != _DIRECTIVE_FIELDS:
        raise ValueError("exact provider response payload has unexpected fields")

    raw_calls = raw["capability_calls"]
    if not isinstance(raw_calls, list):
        raise ValueError("exact provider response capability_calls must be a list")
    capability_calls: list[CapabilityCall] = []
    for item in raw_calls:
        if not isinstance(item, dict) or set(item) != _CAPABILITY_CALL_FIELDS:
            raise ValueError(
                "exact provider response capability call has unexpected fields"
            )
        name = item["name"]
        arguments = item["arguments"]
        call_id = item["call_id"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("exact provider response capability name must be non-blank")
        if not isinstance(arguments, dict):
            raise ValueError("exact provider response capability arguments must be an object")
        if call_id is not None and (
            not isinstance(call_id, str) or not call_id.strip()
        ):
            raise ValueError(
                "exact provider response capability call_id must be non-blank text"
            )
        capability_calls.append(
            CapabilityCall(name=name, arguments=dict(arguments), call_id=call_id)
        )

    response = raw["response"]
    if response is not None and not isinstance(response, str):
        raise ValueError("exact provider response response must be text or null")
    silence = raw["silence"]
    if not isinstance(silence, bool):
        raise ValueError("exact provider response silence must be a boolean")

    raw_usage = raw["usage"]
    usage: ModelUsage | None = None
    if raw_usage is not None:
        if not isinstance(raw_usage, dict) or set(raw_usage) != _USAGE_FIELDS:
            raise ValueError("exact provider response usage has unexpected fields")
        total_tokens = raw_usage["total_tokens"]
        if isinstance(total_tokens, bool) or not isinstance(total_tokens, int):
            raise ValueError("exact provider response usage total_tokens must be an integer")
        for field_name in ("input_tokens", "output_tokens"):
            value = raw_usage[field_name]
            if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
                raise ValueError(
                    f"exact provider response usage {field_name} must be an integer or null"
                )
        for field_name in ("provider", "model", "request_id"):
            value = raw_usage[field_name]
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(
                    f"exact provider response usage {field_name} must be non-blank text or null"
                )
        usage = ModelUsage(
            total_tokens=total_tokens,
            input_tokens=raw_usage["input_tokens"],
            output_tokens=raw_usage["output_tokens"],
            provider=raw_usage["provider"],
            model=raw_usage["model"],
            request_id=raw_usage["request_id"],
        )

    raw_provenance = raw["provenance"]
    provenance: ModelCallProvenance | None = None
    if raw_provenance is not None:
        if not isinstance(raw_provenance, dict) or set(raw_provenance) != _PROVENANCE_FIELDS:
            raise ValueError("exact provider response provenance has unexpected fields")
        for field_name in ("provider", "model", "request_id"):
            value = raw_provenance[field_name]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"exact provider response provenance {field_name} must be non-blank text"
                )
        provenance = ModelCallProvenance(
            provider=raw_provenance["provider"],
            model=raw_provenance["model"],
            request_id=raw_provenance["request_id"],
        )

    return ModelDirective(
        capability_calls=tuple(capability_calls),
        response=response,
        silence=silence,
        usage=usage,
        provenance=provenance,
    )


class BackgroundModelAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    work_kind: BackgroundAttemptWorkKind
    work_id: str = Field(min_length=1)
    wake_reason: str = Field(min_length=1)
    model_round_index: int = Field(ge=0)
    admission_world_revision: int = Field(ge=0)
    state: BackgroundAttemptState
    admitted_at: datetime
    updated_at: datetime
    provider: str | None = None
    model: str | None = None
    provider_request_id: str | None = None
    response_fingerprint: str | None = None
    meter_record_id: str | None = None
    failure_kind: str | None = None
    failure_detail: str | None = None
    reconciliation_evidence: str | None = None

    @property
    def recovery_disposition(self) -> str:
        if self.state in {"admitted", "not_submitted"}:
            return "safe_to_retry"
        if self.state in {"dispatching", "in_doubt"}:
            return "in_doubt"
        return self.state


class BackgroundModelAttemptBlocked(RuntimeError):
    def __init__(self, attempt: BackgroundModelAttempt):
        self.attempt = attempt
        super().__init__(
            "background model attempt blocked: "
            f"{attempt.attempt_id} is {attempt.state}; "
            "inspect/reconcile the durable attempt instead of reinvoking the provider"
        )


class BackgroundModelResponseConflict(BackgroundModelAttemptBlocked):
    """An exact provider response cannot be reconciled with the durable attempt."""

    def __init__(self, attempt: BackgroundModelAttempt, detail: str):
        self.attempt = attempt
        self.detail = detail
        RuntimeError.__init__(
            self,
            "exact provider response rejected: "
            f"{detail}; attempt {attempt.attempt_id} is {attempt.state}",
        )


class BackgroundModelRequestBinding(BaseModel):
    """Durable originating-request binding for one background model attempt.

    Established before provider dispatch. Recovery verifies a response against
    this row; it is not a token the recovery caller is allowed to fill in.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    work_kind: BackgroundAttemptWorkKind
    work_id: str = Field(min_length=1)
    model_round_index: int = Field(ge=0)
    outbound_request_fingerprint: str = Field(min_length=1)
    relay_id: str = Field(min_length=1)
    bound_at: datetime


class BackgroundModelResponseReceipt(BaseModel):
    """Trusted return-path receipt for exact provider response bytes.

    The HMAC key never leaves the runtime store.  This public receipt may be copied
    into an external response journal: replay is harmless because the authenticator
    binds it to one exact attempt, request binding, provider identity, and payload.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    work_kind: BackgroundAttemptWorkKind
    work_id: str = Field(min_length=1)
    model_round_index: int = Field(ge=0)
    outbound_request_fingerprint: str = Field(min_length=1)
    relay_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    provider_request_id: str = Field(min_length=1)
    response_fingerprint: str = Field(min_length=1)
    payload_sha256: str = Field(min_length=1)
    authenticity_proof: str = Field(min_length=1)
    captured_at: datetime


class BackgroundModelResponseStaging(BaseModel):
    """Exact provider response bytes durably bound to one model attempt/round."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    provider_request_id: str = Field(min_length=1)
    response_fingerprint: str = Field(min_length=1)
    directive_payload: str = Field(min_length=1)
    payload_sha256: str = Field(min_length=1)
    authenticity_proof: str | None = None
    staged_at: datetime
    evidence: str = Field(min_length=1)

    def directive(self) -> ModelDirective:
        return decode_model_directive(self.directive_payload)


class BackgroundModelExecutionInDoubt(BackgroundModelAttemptBlocked):
    """Provider submission may have happened; blind retry is forbidden."""


class BackgroundModelResponsePending(BackgroundModelAttemptBlocked):
    """A provider response is durable, but later Core work did not finish."""


class BackgroundModelAttemptStore:
    """Same-database, non-world attempt admission/provenance state."""

    def __init__(self, store: SQLiteWorldStore) -> None:
        self.store = store
        self._initialize()

    def _initialize(self) -> None:
        create_table = """
            CREATE TABLE background_model_attempts (
                attempt_id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                work_kind TEXT NOT NULL
                    CHECK(work_kind IN ('wake', 'periodic_review', 'user_turn')),
                work_id TEXT NOT NULL,
                wake_reason TEXT NOT NULL,
                model_round_index INTEGER NOT NULL
                    CHECK(model_round_index >= 0),
                admission_world_revision INTEGER NOT NULL
                    CHECK(admission_world_revision >= 0),
                state TEXT NOT NULL
                    CHECK(state IN (
                        'admitted',
                        'dispatching',
                        'not_submitted',
                        'in_doubt',
                        'response_returned',
                        'metered'
                    )),
                admitted_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                provider TEXT,
                model TEXT,
                provider_request_id TEXT,
                response_fingerprint TEXT,
                meter_record_id TEXT,
                failure_kind TEXT,
                failure_detail TEXT,
                reconciliation_evidence TEXT,
                UNIQUE(subject_id, work_kind, work_id, model_round_index)
            )
        """
        with self.store._connection() as conn:
            existing = conn.execute(
                """
                SELECT sql
                FROM sqlite_master
                WHERE type='table' AND name='background_model_attempts'
                """
            ).fetchone()
            if existing is None:
                conn.execute(create_table)
            elif "'user_turn'" not in str(existing["sql"] or ""):
                # FIX-003 extends the accepted FIX-002 attempt ledger rather than
                # creating a second provider-attempt truth store. Rebuild the
                # SQLite CHECK constraint in one transaction while preserving all
                # existing Wake/Periodic Review rows byte-for-byte by column.
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "ALTER TABLE background_model_attempts "
                    "RENAME TO background_model_attempts_fix002"
                )
                conn.execute(create_table)
                conn.execute(
                    """
                    INSERT INTO background_model_attempts(
                        attempt_id, subject_id, work_kind, work_id, wake_reason,
                        model_round_index, admission_world_revision, state,
                        admitted_at, updated_at, provider, model,
                        provider_request_id, response_fingerprint,
                        meter_record_id, failure_kind, failure_detail,
                        reconciliation_evidence
                    )
                    SELECT
                        attempt_id, subject_id, work_kind, work_id, wake_reason,
                        model_round_index, admission_world_revision, state,
                        admitted_at, updated_at, provider, model,
                        provider_request_id, response_fingerprint,
                        meter_record_id, failure_kind, failure_detail,
                        reconciliation_evidence
                    FROM background_model_attempts_fix002
                    """
                )
                conn.execute("DROP TABLE background_model_attempts_fix002")

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_background_attempt_work
                    ON background_model_attempts(
                        subject_id, work_kind, work_id, model_round_index
                    )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_background_attempt_state
                    ON background_model_attempts(subject_id, state, updated_at)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS background_model_responses (
                    attempt_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    provider_request_id TEXT NOT NULL,
                    response_fingerprint TEXT NOT NULL,
                    directive_payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    authenticity_proof TEXT NOT NULL,
                    staged_at TEXT NOT NULL,
                    evidence TEXT NOT NULL
                )
                """
            )
            response_columns = {
                str(row["name"])
                for row in conn.execute(
                    "PRAGMA table_info(background_model_responses)"
                ).fetchall()
            }
            if "authenticity_proof" not in response_columns:
                # Historical staged rows have no authenticity authority and stay
                # unusable until they are re-established through the trusted return
                # path. NULL is deliberately fail-closed in every read path.
                conn.execute(
                    "ALTER TABLE background_model_responses "
                    "ADD COLUMN authenticity_proof TEXT"
                )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_background_response_identity
                    ON background_model_responses(
                        provider, provider_request_id, response_fingerprint
                    )
                """
            )
            # Same runtime database, not a second World or cognition store.
            # Written atomically with the dispatch transition, before the
            # provider handler runs, and never supplied by the recovery caller.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS background_model_request_bindings (
                    attempt_id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    work_kind TEXT NOT NULL,
                    work_id TEXT NOT NULL,
                    model_round_index INTEGER NOT NULL
                        CHECK(model_round_index >= 0),
                    outbound_request_fingerprint TEXT NOT NULL,
                    relay_id TEXT NOT NULL,
                    bound_at TEXT NOT NULL
                )
                """
            )
            # Verifier-only late-return authority.  Every value here is public:
            # the external/provider side retains the private signing key and Core
            # persists only the exact request scope plus RSA public verifier.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS background_model_return_verifiers (
                    attempt_id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    work_kind TEXT NOT NULL,
                    work_id TEXT NOT NULL,
                    model_round_index INTEGER NOT NULL
                        CHECK(model_round_index >= 0),
                    outbound_request_fingerprint TEXT NOT NULL,
                    relay_id TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    algorithm TEXT NOT NULL,
                    modulus_hex TEXT NOT NULL,
                    public_exponent INTEGER NOT NULL,
                    bound_at TEXT NOT NULL,
                    consumed_at TEXT
                )
                """
            )
            verifier_columns = {
                str(row["name"])
                for row in conn.execute(
                    "PRAGMA table_info(background_model_return_verifiers)"
                ).fetchall()
            }
            if "consumed_at" not in verifier_columns:
                conn.execute(
                    "ALTER TABLE background_model_return_verifiers "
                    "ADD COLUMN consumed_at TEXT"
                )
            # This is non-World runtime provenance in the existing database.  Rows
            # can only be minted by the trusted provider-return callback; staging
            # can read and verify them but cannot create or rewrite them.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS background_model_response_receipts (
                    attempt_id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    work_kind TEXT NOT NULL,
                    work_id TEXT NOT NULL,
                    model_round_index INTEGER NOT NULL
                        CHECK(model_round_index >= 0),
                    outbound_request_fingerprint TEXT NOT NULL,
                    relay_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    provider_request_id TEXT NOT NULL,
                    response_fingerprint TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    authenticity_proof TEXT NOT NULL UNIQUE,
                    captured_at TEXT NOT NULL
                )
                """
            )
            # The receipt alone authenticates a digest, not the bytes needed after
            # process loss. Both rows must commit in the SAME transaction at the
            # trusted provider-return callback, before downstream application.
            conn.execute("""
                CREATE TABLE IF NOT EXISTS background_model_return_handoffs (
                    attempt_id TEXT PRIMARY KEY,
                    directive_payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    authenticity_proof TEXT NOT NULL
                )
            """)

            # Secret-separation upgrade. Neither the failed Window-13
            # capability nonce nor the older receipt HMAC key may survive in the
            # runtime DB, WAL, dump or backup. Secure-delete zeroes deleted cell
            # content; a successful TRUNCATE checkpoint below removes historical
            # WAL frames before startup is allowed to continue.
            legacy_capability = conn.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type='table'
                  AND name='background_model_return_capabilities'
                """
            ).fetchone()
            legacy_authority = conn.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type='table'
                  AND name='background_model_authenticity_authority'
                """
            ).fetchone()
            purge_legacy_secrets = (
                legacy_capability is not None or legacy_authority is not None
            )
            if purge_legacy_secrets:
                conn.execute("PRAGMA secure_delete = ON")

            if legacy_capability is not None:
                # The failed candidate was never merged, but a copied/review DB
                # must still be safe to open. No nonce/preimage is converted into
                # the new verifier table: it is destroyed and the attempt remains
                # fail-closed unless a genuine first dispatch pins a public key.
                conn.execute("DELETE FROM background_model_return_capabilities")
                conn.execute("DROP TABLE background_model_return_capabilities")

            if legacy_authority is not None:
                # Corrective-002 (`BLK-W17-002` / `C2-4`): verify-before-convert.
                # The legacy keyed authenticator is authenticated with the legacy
                # HMAC authority and cross-checked against every related durable
                # row BEFORE a single byte of trust state is rewritten.  Any
                # inconsistency fails closed with a full rollback: no partial
                # conversion, no secret purge, no turn completion.
                started_transaction = not conn.in_transaction
                if started_transaction:
                    conn.execute("BEGIN IMMEDIATE")
                try:
                    self._migrate_legacy_authenticity_authority(conn)
                except BaseException:
                    conn.rollback()
                    raise
                if started_transaction:
                    conn.commit()

            conn.commit()
            if purge_legacy_secrets:
                checkpoint = conn.execute(
                    "PRAGMA wal_checkpoint(TRUNCATE)"
                ).fetchone()
                if checkpoint is None or int(checkpoint[0]) != 0:
                    raise RuntimeError(
                        "legacy signing material purge could not truncate SQLite WAL"
                    )

    # -- legacy authenticity-authority migration (`C2-4`) ----------------
    @staticmethod
    def _legacy_receipt_fields(row: object) -> dict[str, object]:
        return {
            "attempt_id": row["attempt_id"],
            "subject_id": row["subject_id"],
            "work_kind": row["work_kind"],
            "work_id": row["work_id"],
            "model_round_index": int(row["model_round_index"]),
            "outbound_request_fingerprint": row["outbound_request_fingerprint"],
            "relay_id": row["relay_id"],
            "provider": row["provider"],
            "model": row["model"],
            "provider_request_id": row["provider_request_id"],
            "response_fingerprint": row["response_fingerprint"],
            "payload_sha256": row["payload_sha256"],
        }

    @staticmethod
    def _legacy_migration_error(detail: str) -> LegacyTrustMigrationError:
        return LegacyTrustMigrationError(
            "legacy authenticity-authority migration refused (fail closed, no "
            f"partial conversion, legacy authority preserved): {detail}"
        )

    def _legacy_authority_rows(self, conn: object) -> list[object]:
        rows = conn.execute(
            "SELECT authority_id, secret_hex FROM background_model_authenticity_authority"
        ).fetchall()
        if len(rows) != 1:
            raise self._legacy_migration_error(
                "legacy authority table does not hold exactly one authority row"
            )
        if str(rows[0]["authority_id"]) != _LEGACY_AUTHORITY_ID:
            raise self._legacy_migration_error(
                "legacy authority row identity is not the recognized trusted-return authority"
            )
        return rows

    def _read_legacy_authority_key(self, rows: list[object]) -> bytes:
        raw = rows[0]["secret_hex"]
        if not isinstance(raw, str):
            raise self._legacy_migration_error(
                "legacy authority secret is not a hexadecimal string"
            )
        try:
            key = bytes.fromhex(raw)
        except ValueError as exc:
            raise self._legacy_migration_error(
                "legacy authority secret is not valid hexadecimal"
            ) from exc
        if len(key) != 32:
            raise self._legacy_migration_error(
                "legacy authority secret is not the expected 256-bit key"
            )
        return key

    def _migrate_legacy_authenticity_authority(self, conn: object) -> None:
        """Authenticate and cross-verify all legacy trust state, then convert it.

        Corrective-002 (`BLK-W17-002` / `C2-4`).  Every legacy ``bgresponse_v1``
        receipt is authenticated with the legacy HMAC authority and then
        cross-checked against its durable attempt, request binding, exact handoff
        and staged response before *any* rewrite happens.  Verification completes
        for the whole database first; only then are the proofs replaced with the
        public integrity fingerprint and the obsolete secret purged, inside the
        caller's single transaction.
        """

        authority_rows = self._legacy_authority_rows(conn)
        receipts = conn.execute(
            "SELECT * FROM background_model_response_receipts ORDER BY attempt_id"
        ).fetchall()
        handoffs = conn.execute(
            "SELECT * FROM background_model_return_handoffs ORDER BY attempt_id"
        ).fetchall()
        responses = conn.execute(
            "SELECT * FROM background_model_responses ORDER BY attempt_id"
        ).fetchall()

        if not receipts and not handoffs:
            # There is no legacy trust state to authenticate or convert, so no
            # record is trusted on the strength of the legacy secret and nothing
            # is rewritten.  The obsolete secret must still be destroyed: leaving
            # it behind would violate secret separation, and destroying it cannot
            # launder anything because no row becomes trusted here.  A staged
            # response that still carries a legacy authenticator would however
            # become permanently unverifiable once the secret is gone, so that
            # state fails closed instead of being silently stranded.
            for response in responses:
                staged_proof = response["authenticity_proof"]
                if isinstance(staged_proof, str) and staged_proof.startswith(
                    _LEGACY_RECEIPT_PROOF_PREFIX
                ):
                    raise self._legacy_migration_error(
                        f"staged response {response['attempt_id']!r} carries an "
                        "unverifiable legacy authenticator with no receipt"
                    )
            conn.execute("DELETE FROM background_model_authenticity_authority")
            conn.execute("DROP TABLE background_model_authenticity_authority")
            return

        legacy_key = self._read_legacy_authority_key(authority_rows)
        bindings = {
            str(row["attempt_id"]): row
            for row in conn.execute(
                "SELECT * FROM background_model_request_bindings"
            ).fetchall()
        }
        attempts = {
            str(row["attempt_id"]): row
            for row in conn.execute("SELECT * FROM background_model_attempts").fetchall()
        }

        receipt_ids = [str(row["attempt_id"]) for row in receipts]
        handoff_ids = [str(row["attempt_id"]) for row in handoffs]
        if len(set(receipt_ids)) != len(receipt_ids):
            raise self._legacy_migration_error("duplicated legacy receipt row")
        if len(set(handoff_ids)) != len(handoff_ids):
            raise self._legacy_migration_error("duplicated legacy handoff row")
        if set(receipt_ids) != set(handoff_ids):
            raise self._legacy_migration_error(
                "legacy receipt and handoff row sets do not correspond one-to-one"
            )

        handoff_by_id = {str(row["attempt_id"]): row for row in handoffs}
        verified: dict[str, tuple[dict[str, object], str, str]] = {}

        for receipt in receipts:
            attempt_id = str(receipt["attempt_id"])
            proof = receipt["authenticity_proof"]
            if not isinstance(proof, str) or not proof.startswith(
                _LEGACY_RECEIPT_PROOF_PREFIX
            ):
                raise self._legacy_migration_error(
                    f"receipt {attempt_id!r} carries no legacy bgresponse_v1 "
                    "authenticator while the legacy authority still exists"
                )
            fields = self._legacy_receipt_fields(receipt)
            expected_proof = _LEGACY_RECEIPT_PROOF_PREFIX + hmac.new(
                legacy_key,
                self._receipt_message(**fields),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(proof, expected_proof):
                raise self._legacy_migration_error(
                    f"receipt {attempt_id!r} is not authenticated by the legacy "
                    "HMAC authority over its own scope fields"
                )
            try:
                datetime.fromisoformat(str(receipt["captured_at"]).replace("Z", "+00:00"))
            except ValueError as exc:
                raise self._legacy_migration_error(
                    f"receipt {attempt_id!r} has a malformed captured_at"
                ) from exc

            attempt_row = attempts.get(attempt_id)
            if attempt_row is None:
                raise self._legacy_migration_error(
                    f"receipt {attempt_id!r} has no durable attempt row"
                )
            if str(attempt_row["state"]) not in {
                "dispatching",
                "in_doubt",
                "response_returned",
                "metered",
            }:
                raise self._legacy_migration_error(
                    f"receipt {attempt_id!r} is bound to an attempt state that "
                    "never crossed the provider boundary"
                )
            for column in ("subject_id", "work_kind", "work_id"):
                if str(attempt_row[column]) != str(receipt[column]):
                    raise self._legacy_migration_error(
                        f"receipt {attempt_id!r} does not match its attempt {column}"
                    )
            if int(attempt_row["model_round_index"]) != int(
                receipt["model_round_index"]
            ):
                raise self._legacy_migration_error(
                    f"receipt {attempt_id!r} does not match its attempt model round"
                )
            if attempt_row["provider"] is not None and (
                str(attempt_row["provider"]),
                str(attempt_row["model"]),
                str(attempt_row["provider_request_id"]),
                str(attempt_row["response_fingerprint"]),
            ) != (
                str(fields["provider"]),
                str(fields["model"]),
                str(fields["provider_request_id"]),
                str(fields["response_fingerprint"]),
            ):
                raise self._legacy_migration_error(
                    f"receipt {attempt_id!r} conflicts with durable attempt "
                    "provider/model/request identity"
                )
            binding_row = bindings.get(attempt_id)
            if binding_row is None:
                raise self._legacy_migration_error(
                    f"receipt {attempt_id!r} has no durable originating request binding"
                )
            binding = self._binding_from_row(binding_row)
            if (
                binding.attempt_id,
                binding.subject_id,
                binding.work_kind,
                binding.work_id,
                binding.model_round_index,
            ) != (
                str(fields["attempt_id"]),
                str(fields["subject_id"]),
                str(fields["work_kind"]),
                str(fields["work_id"]),
                int(fields["model_round_index"]),
            ):
                raise self._legacy_migration_error(
                    f"receipt {attempt_id!r} does not match its durable request "
                    "binding identity (cross-attempt transplant)"
                )
            if (
                binding.outbound_request_fingerprint,
                binding.relay_id,
            ) != (
                str(fields["outbound_request_fingerprint"]),
                str(fields["relay_id"]),
            ):
                raise self._legacy_migration_error(
                    f"receipt {attempt_id!r} does not match its durable outbound "
                    "request fingerprint / relay binding"
                )
            expected_relay = self.relay_id_for(
                subject_id=binding.subject_id,
                work_kind=binding.work_kind,
                work_id=binding.work_id,
                model_round_index=binding.model_round_index,
                attempt_id=binding.attempt_id,
                outbound_request_fingerprint=binding.outbound_request_fingerprint,
            )
            if binding.relay_id != expected_relay:
                raise self._legacy_migration_error(
                    f"receipt {attempt_id!r} relay identity is not the durable "
                    "relay for its outbound request"
                )

            handoff = handoff_by_id[attempt_id]
            if str(handoff["authenticity_proof"]) != proof:
                raise self._legacy_migration_error(
                    f"handoff {attempt_id!r} authenticator does not equal its receipt"
                )
            if str(handoff["payload_sha256"]) != str(fields["payload_sha256"]):
                raise self._legacy_migration_error(
                    f"handoff {attempt_id!r} payload digest does not equal its receipt"
                )
            payload = handoff["directive_payload"]
            if not isinstance(payload, str):
                raise self._legacy_migration_error(
                    f"handoff {attempt_id!r} payload is not a string"
                )
            if hashlib.sha256(payload.encode("utf-8")).hexdigest() != str(
                fields["payload_sha256"]
            ):
                raise self._legacy_migration_error(
                    f"handoff {attempt_id!r} exact payload does not hash to the "
                    "digest bound by its receipt"
                )
            try:
                directive = decode_model_directive(payload)
            except ValueError as exc:
                raise self._legacy_migration_error(
                    f"handoff {attempt_id!r} payload is not a canonical model directive"
                ) from exc
            if self._response_fingerprint(directive) != str(
                fields["response_fingerprint"]
            ):
                raise self._legacy_migration_error(
                    f"handoff {attempt_id!r} payload response fingerprint does not "
                    "match its receipt"
                )
            if self._provider_identity(directive) != (
                str(fields["provider"]),
                str(fields["model"]),
                str(fields["provider_request_id"]),
            ):
                raise self._legacy_migration_error(
                    f"handoff {attempt_id!r} payload provider identity does not "
                    "match its receipt"
                )
            verified[attempt_id] = (fields, proof, payload)

        convertible_responses: list[str] = []
        for response in responses:
            attempt_id = str(response["attempt_id"])
            record = verified.get(attempt_id)
            if record is None:
                staged_proof = response["authenticity_proof"]
                if isinstance(staged_proof, str) and staged_proof.startswith(
                    _LEGACY_RECEIPT_PROOF_PREFIX
                ):
                    raise self._legacy_migration_error(
                        f"staged response {attempt_id!r} carries an unverifiable "
                        "legacy authenticator with no corresponding receipt"
                    )
                continue
            fields, proof, payload = record
            if str(response["authenticity_proof"]) != proof:
                raise self._legacy_migration_error(
                    f"staged response {attempt_id!r} authenticator does not equal "
                    "its receipt"
                )
            for column, expected in (
                ("provider", fields["provider"]),
                ("model", fields["model"]),
                ("provider_request_id", fields["provider_request_id"]),
                ("response_fingerprint", fields["response_fingerprint"]),
                ("payload_sha256", fields["payload_sha256"]),
            ):
                if str(response[column]) != str(expected):
                    raise self._legacy_migration_error(
                        f"staged response {attempt_id!r} {column} does not equal "
                        "its receipt"
                    )
            staged_payload = response["directive_payload"]
            if not isinstance(staged_payload, str) or staged_payload != payload:
                raise self._legacy_migration_error(
                    f"staged response {attempt_id!r} exact bytes do not equal its "
                    "durable handoff"
                )
            convertible_responses.append(attempt_id)

        # Every record is authenticated and consistent: now, and only now, convert.
        for attempt_id in sorted(verified):
            fields, _legacy_proof, _payload = verified[attempt_id]
            converted = self._receipt_proof(**fields)
            for statement, parameters in (
                (
                    "UPDATE background_model_response_receipts "
                    "SET authenticity_proof=? WHERE attempt_id=?",
                    (converted, attempt_id),
                ),
                (
                    "UPDATE background_model_return_handoffs "
                    "SET authenticity_proof=? WHERE attempt_id=?",
                    (converted, attempt_id),
                ),
            ):
                if conn.execute(statement, parameters).rowcount != 1:
                    raise self._legacy_migration_error(
                        f"legacy trust row {attempt_id!r} could not be converted "
                        "exactly once"
                    )
        for attempt_id in sorted(convertible_responses):
            fields, _legacy_proof, _payload = verified[attempt_id]
            converted = self._receipt_proof(**fields)
            if (
                conn.execute(
                    "UPDATE background_model_responses "
                    "SET authenticity_proof=? WHERE attempt_id=?",
                    (converted, attempt_id),
                ).rowcount
                != 1
            ):
                raise self._legacy_migration_error(
                    f"legacy staged response {attempt_id!r} could not be "
                    "converted exactly once"
                )

        conn.execute("DELETE FROM background_model_authenticity_authority")
        conn.execute("DROP TABLE background_model_authenticity_authority")

    @staticmethod
    def attempt_id_for(
        *,
        subject_id: str,
        work_kind: BackgroundAttemptWorkKind,
        work_id: str,
        model_round_index: int,
    ) -> str:
        raw = canonical_json_dumps(
            [subject_id, work_kind, work_id, int(model_round_index)]
        ).encode("utf-8")
        return f"bgattempt_{hashlib.sha256(raw).hexdigest()[:32]}"

    @staticmethod
    def relay_id_for(
        *,
        subject_id: str,
        work_kind: str,
        work_id: str,
        model_round_index: int,
        attempt_id: str,
        outbound_request_fingerprint: str,
    ) -> str:
        """Mechanical relay identity for one exact outbound request.

        Derived only from the durable attempt identity and the outbound request
        fingerprint recorded at dispatch. A recovery caller cannot mint this.
        """

        raw = canonical_json_dumps(
            {
                "attempt_id": attempt_id,
                "model_round_index": int(model_round_index),
                "outbound_request_fingerprint": outbound_request_fingerprint,
                "subject_id": subject_id,
                "work_id": work_id,
                "work_kind": work_kind,
            }
        ).encode("utf-8")
        return f"relay_{hashlib.sha256(raw).hexdigest()}"

    @staticmethod
    def _response_fingerprint(directive: ModelDirective) -> str:
        payload = {
            "capability_calls": [
                {
                    "name": call.name,
                    "arguments": dict(call.arguments),
                    "call_id": call.call_id,
                }
                for call in directive.capability_calls
            ],
            "response": directive.response,
            "silence": directive.silence,
            "usage": (
                None
                if directive.usage is None
                else {
                    "total_tokens": directive.usage.total_tokens,
                    "input_tokens": directive.usage.input_tokens,
                    "output_tokens": directive.usage.output_tokens,
                    "provider": directive.usage.provider,
                    "model": directive.usage.model,
                    "request_id": directive.usage.request_id,
                }
            ),
            "provenance": (
                None
                if directive.provenance is None
                else {
                    "provider": directive.provenance.provider,
                    "model": directive.provenance.model,
                    "request_id": directive.provenance.request_id,
                }
            ),
        }
        raw = canonical_json_dumps(payload).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _provider_identity(
        directive: ModelDirective,
    ) -> tuple[str | None, str | None, str | None]:
        provider = (
            None if directive.provenance is None else directive.provenance.provider
        )
        model = None if directive.provenance is None else directive.provenance.model
        request_id = (
            None if directive.provenance is None else directive.provenance.request_id
        )
        if directive.usage is not None:
            provider = directive.usage.provider or provider
            model = directive.usage.model or model
            request_id = directive.usage.request_id or request_id
        return provider, model, request_id

    @staticmethod
    def _receipt_message(
        *,
        attempt_id: str,
        subject_id: str,
        work_kind: str,
        work_id: str,
        model_round_index: int,
        outbound_request_fingerprint: str,
        relay_id: str,
        provider: str,
        model: str,
        provider_request_id: str,
        response_fingerprint: str,
        payload_sha256: str,
    ) -> bytes:
        return canonical_json_dumps(
            {
                "attempt_id": attempt_id,
                "model": model,
                "model_round_index": int(model_round_index),
                "outbound_request_fingerprint": outbound_request_fingerprint,
                "payload_sha256": payload_sha256,
                "provider": provider,
                "provider_request_id": provider_request_id,
                "relay_id": relay_id,
                "response_fingerprint": response_fingerprint,
                "schema": "aios.background-model-response-receipt.v1",
                "subject_id": subject_id,
                "work_id": work_id,
                "work_kind": work_kind,
            }
        ).encode("utf-8")

    @classmethod
    def _receipt_proof(cls, **fields: object) -> str:
        """Integrity fingerprint for a Core-owned durable receipt row.

        This is deliberately not authentication authority.  Authenticity comes
        from where the row was created: either the live trusted return boundary,
        or a verified external RSA late-return proof.  Recovery can recompute this
        checksum but cannot create a missing receipt row through any API.
        """

        digest = hashlib.sha256(cls._receipt_message(**fields)).hexdigest()
        return f"bgresponse_v2_{digest}"

    @staticmethod
    def _receipt_from_row(row: object) -> BackgroundModelResponseReceipt:
        return BackgroundModelResponseReceipt(
            attempt_id=row["attempt_id"],
            subject_id=row["subject_id"],
            work_kind=row["work_kind"],
            work_id=row["work_id"],
            model_round_index=int(row["model_round_index"]),
            outbound_request_fingerprint=row["outbound_request_fingerprint"],
            relay_id=row["relay_id"],
            provider=row["provider"],
            model=row["model"],
            provider_request_id=row["provider_request_id"],
            response_fingerprint=row["response_fingerprint"],
            payload_sha256=row["payload_sha256"],
            authenticity_proof=row["authenticity_proof"],
            captured_at=datetime.fromisoformat(
                str(row["captured_at"]).replace("Z", "+00:00")
            ),
        )

    @staticmethod
    def _from_row(row: object) -> BackgroundModelAttempt:
        return BackgroundModelAttempt(
            attempt_id=row["attempt_id"],
            subject_id=row["subject_id"],
            work_kind=row["work_kind"],
            work_id=row["work_id"],
            wake_reason=row["wake_reason"],
            model_round_index=int(row["model_round_index"]),
            admission_world_revision=int(row["admission_world_revision"]),
            state=row["state"],
            admitted_at=datetime.fromisoformat(
                str(row["admitted_at"]).replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                str(row["updated_at"]).replace("Z", "+00:00")
            ),
            provider=row["provider"],
            model=row["model"],
            provider_request_id=row["provider_request_id"],
            response_fingerprint=row["response_fingerprint"],
            meter_record_id=row["meter_record_id"],
            failure_kind=row["failure_kind"],
            failure_detail=row["failure_detail"],
            reconciliation_evidence=row["reconciliation_evidence"],
        )

    def get(self, attempt_id: str) -> BackgroundModelAttempt | None:
        with self.store._connection() as conn:
            row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
        return None if row is None else self._from_row(row)

    def inspect(
        self,
        *,
        subject_id: str,
        work_kind: BackgroundAttemptWorkKind,
        work_id: str,
        model_round_index: int,
    ) -> BackgroundModelAttempt | None:
        attempt_id = self.attempt_id_for(
            subject_id=subject_id,
            work_kind=work_kind,
            work_id=work_id,
            model_round_index=model_round_index,
        )
        return self.get(attempt_id)

    def list_for_work(
        self,
        *,
        subject_id: str,
        work_kind: BackgroundAttemptWorkKind,
        work_id: str,
    ) -> tuple[BackgroundModelAttempt, ...]:
        with self.store._connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM background_model_attempts
                WHERE subject_id=? AND work_kind=? AND work_id=?
                ORDER BY model_round_index ASC
                """,
                (subject_id, work_kind, work_id),
            ).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def admit(
        self,
        *,
        subject_id: str,
        work_kind: BackgroundAttemptWorkKind,
        work_id: str,
        wake_reason: str,
        model_round_index: int,
        world_revision: int,
        admitted_at: datetime,
    ) -> BackgroundModelAttempt:
        moment = as_utc(admitted_at, "admitted_at")
        attempt_id = self.attempt_id_for(
            subject_id=subject_id,
            work_kind=work_kind,
            work_id=work_id,
            model_round_index=model_round_index,
        )
        with self.store._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT OR IGNORE INTO background_model_attempts(
                    attempt_id, subject_id, work_kind, work_id, wake_reason,
                    model_round_index, admission_world_revision, state,
                    admitted_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'admitted', ?, ?)
                """,
                (
                    attempt_id,
                    subject_id,
                    work_kind,
                    work_id,
                    wake_reason,
                    int(model_round_index),
                    int(world_revision),
                    canonical_utc_iso(moment, "admitted_at"),
                    canonical_utc_iso(moment, "updated_at"),
                ),
            )
            row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if row is None:
                conn.rollback()
                raise RuntimeError("background model attempt admission was not durable")
            current = self._from_row(row)
            immutable = (
                current.subject_id == subject_id
                and current.work_kind == work_kind
                and current.work_id == work_id
                and current.wake_reason == wake_reason
                and current.model_round_index == int(model_round_index)
            )
            if not immutable:
                conn.rollback()
                raise RuntimeError(
                    "background model attempt identity conflicts with durable work identity"
                )

            if current.state == "not_submitted":
                # C4/C6 Route B: a retry is legal only for a genuinely
                # pre-submission attempt. Historical or corrupted rows that retain
                # any durable dispatch/verifier/receipt artifact are never retried.
                if self._durable_submission_artifacts(conn, attempt_id):
                    conn.rollback()
                    raise BackgroundModelAttemptBlocked(current)
                conn.execute(
                    """
                    UPDATE background_model_attempts
                    SET state='admitted', updated_at=?, failure_kind=NULL,
                        failure_detail=NULL
                    WHERE attempt_id=? AND state='not_submitted'
                    """,
                    (canonical_utc_iso(moment, "updated_at"), attempt_id),
                )
                row = conn.execute(
                    "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                    (attempt_id,),
                ).fetchone()
                conn.commit()
                if row is None:
                    raise RuntimeError("background attempt disappeared during retry admission")
                return self._from_row(row)

            if current.state == "admitted":
                conn.commit()
                return current

            if current.state == "dispatching":
                conn.execute(
                    """
                    UPDATE background_model_attempts
                    SET state='in_doubt', updated_at=?,
                        failure_kind='restart_after_dispatch_boundary',
                        failure_detail=?
                    WHERE attempt_id=? AND state='dispatching'
                    """,
                    (
                        canonical_utc_iso(moment, "updated_at"),
                        "provider dispatch boundary was crossed without a durable response",
                        attempt_id,
                    ),
                )
                row = conn.execute(
                    "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                    (attempt_id,),
                ).fetchone()
                conn.commit()
                if row is None:
                    raise RuntimeError("background attempt disappeared during recovery")
                raise BackgroundModelExecutionInDoubt(self._from_row(row))

            conn.commit()
            if current.state == "in_doubt":
                raise BackgroundModelExecutionInDoubt(current)
            if current.state == "response_returned":
                raise BackgroundModelResponsePending(current)
            raise BackgroundModelAttemptBlocked(current)

    def mark_dispatching(
        self,
        attempt_id: str,
        *,
        dispatched_at: datetime,
        outbound_request_fingerprint: str,
        late_return_verifier: LateReturnVerifier | None = None,
    ) -> BackgroundModelAttempt:
        """Cross the provider boundary and durably bind the outbound request.

        The binding is committed in the same transaction as the dispatching
        transition, before the provider handler is invoked. A later exact-response
        recovery must match this pre-existing binding; it cannot supply a
        substitute token.
        """

        if (
            not isinstance(outbound_request_fingerprint, str)
            or not outbound_request_fingerprint.strip()
        ):
            raise ValueError(
                "outbound request fingerprint must be non-blank before provider dispatch"
            )
        fingerprint = outbound_request_fingerprint.strip()
        moment = as_utc(dispatched_at, "dispatched_at")
        with self.store._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if row is None:
                conn.rollback()
                raise KeyError(f"unknown background model attempt: {attempt_id}")
            current = self._from_row(row)
            if current.state != "admitted":
                conn.rollback()
                if current.state in {"dispatching", "in_doubt"}:
                    raise BackgroundModelExecutionInDoubt(current)
                if current.state == "response_returned":
                    raise BackgroundModelResponsePending(current)
                raise BackgroundModelAttemptBlocked(current)
            # Route B makes binding rotation impossible: an admitted attempt may
            # cross the provider boundary only if this is its first durable
            # dispatch fact. A legacy not_submitted row that still has a binding,
            # verifier/capability, or receipt cannot create a second request.
            if self._durable_submission_artifacts(conn, attempt_id):
                conn.rollback()
                raise BackgroundModelAttemptBlocked(current)
            relay_id = self.relay_id_for(
                subject_id=current.subject_id,
                work_kind=current.work_kind,
                work_id=current.work_id,
                model_round_index=current.model_round_index,
                attempt_id=current.attempt_id,
                outbound_request_fingerprint=fingerprint,
            )
            bound_at = canonical_utc_iso(moment, "bound_at")
            updated_at = canonical_utc_iso(moment, "updated_at")
            changed = conn.execute(
                """
                UPDATE background_model_attempts
                SET state='dispatching', updated_at=?
                WHERE attempt_id=? AND state='admitted'
                """,
                (updated_at, attempt_id),
            ).rowcount
            if changed != 1:
                conn.rollback()
                raise RuntimeError(
                    "background model attempt did not enter dispatching"
                )
            # C6 Route B: this INSERT is the first and only durable provider
            # request identity. A legal pre-submission retry has no prior binding;
            # post-binding attempts never return to admitted and cannot rotate it.
            conn.execute(
                """
                INSERT INTO background_model_request_bindings(
                    attempt_id, subject_id, work_kind, work_id,
                    model_round_index, outbound_request_fingerprint,
                    relay_id, bound_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    current.attempt_id,
                    current.subject_id,
                    current.work_kind,
                    current.work_id,
                    int(current.model_round_index),
                    fingerprint,
                    relay_id,
                    bound_at,
                ),
            )
            if late_return_verifier is not None:
                if not isinstance(late_return_verifier, LateReturnVerifier):
                    conn.rollback()
                    raise TypeError("late_return_verifier must be LateReturnVerifier")
                conn.execute(
                    """
                    INSERT INTO background_model_return_verifiers(
                        attempt_id, subject_id, work_kind, work_id,
                        model_round_index, outbound_request_fingerprint, relay_id,
                        key_id, algorithm, modulus_hex, public_exponent, bound_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        current.attempt_id,
                        current.subject_id,
                        current.work_kind,
                        current.work_id,
                        int(current.model_round_index),
                        fingerprint,
                        relay_id,
                        late_return_verifier.key_id,
                        late_return_verifier.algorithm,
                        late_return_verifier.modulus_hex,
                        int(late_return_verifier.public_exponent),
                        bound_at,
                    ),
                )
            row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            conn.commit()
        if row is None:
            raise KeyError(f"unknown background model attempt: {attempt_id}")
        return self._from_row(row)

    def adopt_legacy_in_doubt(
        self,
        *,
        subject_id: str,
        work_kind: BackgroundAttemptWorkKind,
        work_id: str,
        wake_reason: str,
        model_round_index: int,
        world_revision: int,
        observed_at: datetime,
    ) -> BackgroundModelAttempt:
        """Fail closed for a pre-upgrade RUNNING work item with no attempt row."""

        moment = as_utc(observed_at, "observed_at")
        attempt_id = self.attempt_id_for(
            subject_id=subject_id,
            work_kind=work_kind,
            work_id=work_id,
            model_round_index=model_round_index,
        )
        with self.store._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT OR IGNORE INTO background_model_attempts(
                    attempt_id, subject_id, work_kind, work_id, wake_reason,
                    model_round_index, admission_world_revision, state,
                    admitted_at, updated_at, failure_kind, failure_detail
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'in_doubt', ?, ?,
                          'legacy_running_without_attempt', ?)
                """,
                (
                    attempt_id,
                    subject_id,
                    work_kind,
                    work_id,
                    wake_reason,
                    int(model_round_index),
                    int(world_revision),
                    canonical_utc_iso(moment, "admitted_at"),
                    canonical_utc_iso(moment, "updated_at"),
                    "pre-upgrade RUNNING work has no durable provider-attempt boundary",
                ),
            )
            row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            conn.commit()
        if row is None:
            raise RuntimeError("legacy background attempt adoption was not durable")
        return self._from_row(row)

    @staticmethod
    def _durable_submission_artifacts(
        conn: object,
        attempt_id: str,
    ) -> tuple[str, ...]:
        """Return durable facts that make not_submitted mechanically false.

        The table list includes both the current verifier name and the historical
        failed-candidate capability name. The lookup is schema-aware so upgrades
        remain fail-closed without requiring every table to exist.
        """

        artifacts: list[str] = []
        for table in (
            "background_model_request_bindings",
            "background_model_return_verifiers",
            "background_model_return_capabilities",
            "background_model_response_receipts",
        ):
            exists = conn.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type='table' AND name=?
                """,
                (table,),
            ).fetchone()
            if exists is None:
                continue
            row = conn.execute(
                f"SELECT 1 FROM {table} WHERE attempt_id=? LIMIT 1",
                (attempt_id,),
            ).fetchone()
            if row is not None:
                artifacts.append(table)
        return tuple(artifacts)

    @staticmethod
    def _route_post_binding_failure_to_in_doubt(
        conn: object,
        *,
        attempt_id: str,
        failed_at: datetime,
        kind: str,
        detail: str,
    ) -> object | None:
        """Persist uncertainty, never false non-submission, after dispatch."""

        conn.execute(
            """
            UPDATE background_model_attempts
            SET state='in_doubt', updated_at=?, failure_kind=?, failure_detail=?
            WHERE attempt_id=? AND state='dispatching'
            """,
            (
                canonical_utc_iso(failed_at, "updated_at"),
                kind,
                detail,
                attempt_id,
            ),
        )
        return conn.execute(
            "SELECT * FROM background_model_attempts WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()

    def mark_failure(
        self,
        attempt_id: str,
        *,
        failed_at: datetime,
        definitely_not_submitted: bool,
        error: BaseException,
    ) -> BackgroundModelAttempt:
        """Record failure without allowing caller assertions to rewrite dispatch truth.

        definitely_not_submitted=True is accepted only while the attempt is
        still admitted and has zero durable dispatch/verifier/receipt facts.
        After any dispatch fact exists, uncertainty is durably in_doubt and the
        attempted non-submission claim is refused.
        """

        moment = as_utc(failed_at, "failed_at")
        kind = type(error).__name__
        detail = str(error)[:1000]
        with self.store._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current_row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if current_row is None:
                conn.rollback()
                raise KeyError(f"unknown background model attempt: {attempt_id}")
            current = self._from_row(current_row)

            if definitely_not_submitted:
                artifacts = self._durable_submission_artifacts(conn, attempt_id)
                if current.state != "admitted" or artifacts:
                    row = self._route_post_binding_failure_to_in_doubt(
                        conn,
                        attempt_id=attempt_id,
                        failed_at=moment,
                        kind=kind,
                        detail=detail,
                    )
                    conn.commit()
                    attempt = current if row is None else self._from_row(row)
                    facts = ", ".join(artifacts) if artifacts else current.state
                    raise BackgroundModelResponseConflict(
                        attempt,
                        "not_submitted requires state=admitted with zero durable "
                        "dispatch/verifier/receipt facts; caller booleans and "
                        f"exception types are not proof (durable={facts})",
                    )
                target = "not_submitted"
                allowed_states = ("admitted",)
            else:
                target = "in_doubt"
                allowed_states = ("admitted", "dispatching")

            placeholders = ", ".join("?" for _ in allowed_states)
            conn.execute(
                f"""
                UPDATE background_model_attempts
                SET state=?, updated_at=?, failure_kind=?, failure_detail=?
                WHERE attempt_id=? AND state IN ({placeholders})
                """,
                (
                    target,
                    canonical_utc_iso(moment, "updated_at"),
                    kind,
                    detail,
                    attempt_id,
                    *allowed_states,
                ),
            )
            row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            conn.commit()
        if row is None:
            raise KeyError(f"unknown background model attempt: {attempt_id}")
        attempt = self._from_row(row)
        if attempt.state not in {target, "response_returned", "metered"}:
            raise BackgroundModelAttemptBlocked(attempt)
        return attempt

    def record_response(

        self,
        attempt_id: str,
        *,
        returned_at: datetime,
        directive: ModelDirective,
    ) -> BackgroundModelAttempt:
        """Close one LIVE in-process provider round without minting any trust.

        Route B (Corrective-003, closing ``BLK-W20-001`` /
        ``TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE``): a normal live
        local handler return does **not** create a durable trusted receipt and does
        **not** create an exact return handoff.  Durable trusted provider/late
        return exists only through
        :meth:`attach_late_trusted_return` with a durable bound external verifier
        plus a genuine external cryptographic proof.

        This method therefore writes only the live completion transition
        (``dispatching`` -> ``response_returned``) plus the round's unverified live
        provenance.  Because it creates no receipt, no handoff and no staged exact
        response, the round it closes is permanently **not** recovery-eligible: no
        caller can later adopt arbitrary bytes for it, and no forged local
        completion can be replayed as an exact provider reply.

        Two properties keep this from being a caller-manufacturable trust oracle:

        1. it creates **no** receipt, **no** handoff and **no** staged exact
           response, so the round it closes is permanently not recovery-eligible:
           no caller can later adopt arbitrary bytes for it, and a local
           completion can never be replayed as an exact provider reply;
        2. it is refused when durable trusted-return rows already exist for the
           attempt.  Those rows can only have been created by genuine external
           proof, so a local completion can never race or replace them
           (first-writer-wins for the external authority).

        An attempt that has already been driven to ``in_doubt`` by the admission
        guard is refused structurally: the completion transition below matches
        ``state='dispatching'`` only.  Conversely, a genuine external proof is
        authoritative over the *unverified* provenance this method writes: because
        the absence of a receipt row is itself the durable, unforgeable marker
        that the provenance was never externally proven,
        :meth:`stage_exact_response` lets a verified external return supersede it
        instead of being blocked by it.  A local caller therefore cannot poison a
        later genuine RSA trusted return.
        """

        moment = as_utc(returned_at, "returned_at")
        provider, model, request_id = self._provider_identity(directive)
        has_recoverable_identity = all(
            value is not None for value in (provider, model, request_id)
        )
        fingerprint = self._response_fingerprint(directive)
        with self.store._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current_row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if current_row is None:
                conn.rollback()
                raise KeyError(f"unknown background model attempt: {attempt_id}")
            current = self._from_row(current_row)
            # Route B hard gate: never race or overwrite durable trusted-return
            # state, which only genuine external proof can have created.  This is
            # what preserves first-writer-wins for the external authority.
            trusted_rows = conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM background_model_response_receipts
                     WHERE attempt_id=?) AS receipts,
                    (SELECT COUNT(*) FROM background_model_return_handoffs
                     WHERE attempt_id=?) AS handoffs,
                    (SELECT COUNT(*) FROM background_model_responses
                     WHERE attempt_id=?) AS staged
                """,
                (attempt_id, attempt_id, attempt_id),
            ).fetchone()
            if trusted_rows is not None and any(
                int(trusted_rows[index] or 0) for index in range(3)
            ):
                conn.rollback()
                raise BackgroundModelResponseConflict(
                    current,
                    "durable trusted provider-return state already exists for this "
                    "attempt and can only have been created by genuine external "
                    "proof; a local live completion may not race or replace it",
                )
            if has_recoverable_identity:
                binding_row = conn.execute(
                    """
                    SELECT * FROM background_model_request_bindings
                    WHERE attempt_id=?
                    """,
                    (attempt_id,),
                ).fetchone()
                binding = (
                    None
                    if binding_row is None
                    else self._binding_from_row(binding_row)
                )
                try:
                    binding = self._require_origin_binding(
                        current,
                        binding,
                        supplied_request_id=request_id,
                        require_relay_echo=False,
                    )
                except BackgroundModelResponseConflict:
                    conn.rollback()
                    raise
            conn.execute(
                """
                UPDATE background_model_attempts
                SET state='response_returned', updated_at=?, provider=?, model=?,
                    provider_request_id=?, response_fingerprint=?,
                    failure_kind=NULL, failure_detail=NULL
                WHERE attempt_id=? AND state='dispatching'
                """,
                (
                    canonical_utc_iso(moment, "updated_at"),
                    provider,
                    model,
                    request_id,
                    fingerprint,
                    attempt_id,
                ),
            )
            row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            conn.commit()
        attempt = self._from_row(row)
        if attempt.state in {"response_returned", "metered"}:
            if (
                attempt.response_fingerprint != fingerprint
                or attempt.provider != provider
                or attempt.model != model
                or attempt.provider_request_id != request_id
            ):
                raise RuntimeError(
                    "provider response conflicts with durable background attempt provenance"
                )
            return attempt
        raise BackgroundModelAttemptBlocked(attempt)

    def reconcile_not_submitted(
        self,
        attempt_id: str,
        *,
        reconciled_at: datetime,
        evidence: str,
    ) -> BackgroundModelAttempt:
        """Record only mechanically proven pre-submission non-dispatch.

        Human/operator evidence text is audit metadata, not proof. The transition
        is writable only from admitted with zero durable dispatch/verifier/receipt
        facts. A post-binding call is refused and any still-dispatching attempt is
        durably routed to in_doubt.
        """

        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError("reconciliation evidence must be non-blank")
        moment = as_utc(reconciled_at, "reconciled_at")
        with self.store._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if row is None:
                conn.rollback()
                raise KeyError(f"unknown background model attempt: {attempt_id}")
            current = self._from_row(row)
            artifacts = self._durable_submission_artifacts(conn, attempt_id)

            if current.state == "not_submitted" and not artifacts:
                conn.commit()
                return current

            if current.state != "admitted" or artifacts:
                row = self._route_post_binding_failure_to_in_doubt(
                    conn,
                    attempt_id=attempt_id,
                    failed_at=moment,
                    kind="reconcile_not_submitted_refused",
                    detail="post-binding non-submission reconciliation is forbidden",
                )
                conn.commit()
                attempt = current if row is None else self._from_row(row)
                facts = ", ".join(artifacts) if artifacts else current.state
                raise BackgroundModelResponseConflict(
                    attempt,
                    "not_submitted reconciliation requires state=admitted with "
                    "zero durable dispatch/verifier/receipt facts; supplied "
                    f"evidence cannot override durable truth (durable={facts})",
                )

            conn.execute(
                """
                UPDATE background_model_attempts
                SET state='not_submitted', updated_at=?,
                    reconciliation_evidence=?, failure_kind=NULL,
                    failure_detail=NULL
                WHERE attempt_id=? AND state='admitted'
                """,
                (
                    canonical_utc_iso(moment, "updated_at"),
                    evidence.strip(),
                    attempt_id,
                ),
            )
            row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            conn.commit()
        if row is None:
            raise KeyError(f"unknown background model attempt: {attempt_id}")
        attempt = self._from_row(row)
        if attempt.state != "not_submitted":
            raise BackgroundModelAttemptBlocked(attempt)
        return attempt

    def reconcile_response(

        self,
        attempt_id: str,
        *,
        reconciled_at: datetime,
        provider: str,
        model: str,
        provider_request_id: str,
        response_fingerprint: str,
        evidence: str,
    ) -> BackgroundModelAttempt:
        """Reject the obsolete metadata-only response-reconciliation path.

        Metadata and a caller-computable fingerprint cannot authenticate provider
        bytes.  Keeping this method fail-closed avoids a compatibility-shaped path
        that could mutate attempt provenance before trusted receipt verification;
        callers must use ``stage_exact_response`` with exact bytes and proof.
        """

        del reconciled_at, provider, model, provider_request_id, response_fingerprint
        del evidence
        attempt = self.get(attempt_id)
        if attempt is None:
            raise KeyError(f"unknown background model attempt: {attempt_id}")
        raise BackgroundModelResponseConflict(
            attempt,
            "metadata-only response reconciliation is disabled; exact provider "
            "bytes and a trusted return-path proof are required",
        )

    # -- exact provider response recovery -------------------------------------
    #
    # A process can die after the provider boundary was crossed while the exact
    # reply bytes are already durable outside Core. Recovering that attempt/round
    # requires the exact directive, its response fingerprint and the exact
    # provider/model/request_id. This is the only Core surface allowed to carry an
    # externally preserved reply back into the same attempt; it never re-dispatches
    # the provider and it never fabricates or approximations a response.

    _STAGABLE_STATES = frozenset(
        {"dispatching", "in_doubt", "response_returned", "metered"}
    )

    @staticmethod
    def _staging_from_row(row: object) -> BackgroundModelResponseStaging:
        return BackgroundModelResponseStaging(
            attempt_id=row["attempt_id"],
            provider=row["provider"],
            model=row["model"],
            provider_request_id=row["provider_request_id"],
            response_fingerprint=row["response_fingerprint"],
            directive_payload=row["directive_payload"],
            payload_sha256=row["payload_sha256"],
            authenticity_proof=row["authenticity_proof"],
            staged_at=datetime.fromisoformat(
                str(row["staged_at"]).replace("Z", "+00:00")
            ),
            evidence=row["evidence"],
        )

    @staticmethod
    def _binding_from_row(row: object) -> BackgroundModelRequestBinding:
        return BackgroundModelRequestBinding(
            attempt_id=row["attempt_id"],
            subject_id=row["subject_id"],
            work_kind=row["work_kind"],
            work_id=row["work_id"],
            model_round_index=int(row["model_round_index"]),
            outbound_request_fingerprint=row["outbound_request_fingerprint"],
            relay_id=row["relay_id"],
            bound_at=datetime.fromisoformat(
                str(row["bound_at"]).replace("Z", "+00:00")
            ),
        )

    def outbound_request_binding(
        self,
        attempt_id: str,
    ) -> BackgroundModelRequestBinding | None:
        """Read the pre-dispatch originating-request binding. Never mints one."""

        with self.store._connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM background_model_request_bindings
                WHERE attempt_id=?
                """,
                (attempt_id,),
            ).fetchone()
        return None if row is None else self._binding_from_row(row)

    def _require_origin_binding(
        self,
        attempt: BackgroundModelAttempt,
        binding: BackgroundModelRequestBinding | None,
        *,
        supplied_request_id: str,
        require_relay_echo: bool,
    ) -> BackgroundModelRequestBinding:
        """Verify a response against the binding written before dispatch.

        The supplied request id is compared to the stored relay id. A caller
        who copies another attempt's request id together with that attempt's
        response still fails, because this method never trusts a caller-supplied
        token in place of the pre-existing row.
        """

        if binding is None:
            raise BackgroundModelResponseConflict(
                attempt,
                "durable originating request binding is missing; exact response "
                "adoption cannot prove which outbound request this attempt made",
            )
        if (
            binding.attempt_id != attempt.attempt_id
            or binding.subject_id != attempt.subject_id
            or binding.work_kind != attempt.work_kind
            or binding.work_id != attempt.work_id
            or binding.model_round_index != attempt.model_round_index
        ):
            raise BackgroundModelResponseConflict(
                attempt,
                "durable originating request binding does not match the attempt "
                "subject, work kind, work id, model round, or attempt id",
            )
        expected_relay = self.relay_id_for(
            subject_id=binding.subject_id,
            work_kind=binding.work_kind,
            work_id=binding.work_id,
            model_round_index=binding.model_round_index,
            attempt_id=binding.attempt_id,
            outbound_request_fingerprint=binding.outbound_request_fingerprint,
        )
        if binding.relay_id != expected_relay:
            raise BackgroundModelResponseConflict(
                attempt,
                "durable originating request binding is internally inconsistent "
                "with the recorded outbound request",
            )
        if require_relay_echo and supplied_request_id != binding.relay_id:
            raise BackgroundModelResponseConflict(
                attempt,
                "exact response is not bound to this attempt's durable "
                "originating request",
            )
        return binding

    def late_return_verifier(
        self,
        attempt_id: str,
    ) -> LateReturnVerifier | None:
        """Return only public verifier material for one dispatched attempt."""

        with self.store._connection() as conn:
            row = conn.execute(
                """
                SELECT key_id, algorithm, modulus_hex, public_exponent
                FROM background_model_return_verifiers
                WHERE attempt_id=?
                """,
                (attempt_id,),
            ).fetchone()
        if row is None:
            return None
        try:
            return LateReturnVerifier(
                key_id=row["key_id"],
                algorithm=row["algorithm"],
                modulus_hex=row["modulus_hex"],
                public_exponent=int(row["public_exponent"]),
            )
        except ValueError as exc:
            # Corrective-002 (`C2-5` / `C2-6`): a bound verifier that is not
            # canonical can never verify a genuine external signature, so it is
            # fail-closed rather than silently unusable.
            raise LateReturnVerifierError(
                "durable late-return verifier material is not canonical; the "
                "bound external authority can never be verified for this attempt"
            ) from exc

    def late_return_signing_context(
        self,
        attempt_id: str,
    ) -> LateReturnSigningContext | None:
        """Public request scope for an external signer; never signing authority."""

        with self.store._connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM background_model_return_verifiers
                WHERE attempt_id=?
                """,
                (attempt_id,),
            ).fetchone()
        if row is None:
            return None
        return LateReturnSigningContext(
            attempt_id=row["attempt_id"],
            subject_id=row["subject_id"],
            work_kind=row["work_kind"],
            work_id=row["work_id"],
            model_round_index=int(row["model_round_index"]),
            outbound_request_fingerprint=row["outbound_request_fingerprint"],
            relay_id=row["relay_id"],
            verifier_key_id=row["key_id"],
        )

    def attach_late_trusted_return(
        self,
        attempt_id: str,
        *,
        attached_at: datetime,
        directive_payload: str,
        late_return_proof: str,
        evidence: str,
    ) -> BackgroundModelResponseStaging:
        """Verify an externally signed late return and atomically adopt exact bytes."""

        if not isinstance(directive_payload, str) or not directive_payload.strip():
            raise ValueError("late trusted return payload must be non-blank")
        if not isinstance(late_return_proof, str) or not late_return_proof.strip():
            raise ValueError("late trusted return proof must be non-blank")
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError("late trusted return evidence must be non-blank")
        moment = as_utc(attached_at, "attached_at")

        directive = decode_model_directive(directive_payload)
        provider, model, provider_request_id = self._provider_identity(directive)
        if provider is None or model is None or provider_request_id is None:
            raise ValueError(
                "late trusted return requires full provider/model/request_id identity"
            )
        response_fingerprint = self._response_fingerprint(directive)
        payload_sha256 = hashlib.sha256(
            directive_payload.encode("utf-8")
        ).hexdigest()

        with self.store._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            attempt_row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if attempt_row is None:
                conn.rollback()
                raise KeyError(f"unknown background model attempt: {attempt_id}")
            attempt = self._from_row(attempt_row)
            if attempt.state not in self._STAGABLE_STATES:
                conn.rollback()
                raise BackgroundModelResponseConflict(
                    attempt,
                    "late trusted return cannot attach before durable dispatch",
                )
            binding_row = conn.execute(
                """
                SELECT * FROM background_model_request_bindings
                WHERE attempt_id=?
                """,
                (attempt_id,),
            ).fetchone()
            binding = (
                None if binding_row is None else self._binding_from_row(binding_row)
            )
            try:
                binding = self._require_origin_binding(
                    attempt,
                    binding,
                    supplied_request_id=provider_request_id,
                    require_relay_echo=False,
                )
            except BackgroundModelResponseConflict:
                conn.rollback()
                raise

            verifier_row = conn.execute(
                """
                SELECT * FROM background_model_return_verifiers
                WHERE attempt_id=?
                """,
                (attempt_id,),
            ).fetchone()
            if verifier_row is None:
                conn.rollback()
                raise BackgroundModelResponseConflict(
                    attempt,
                    "no external late-return verifier was bound before dispatch",
                )
            verifier_scope = (
                verifier_row["attempt_id"],
                verifier_row["subject_id"],
                verifier_row["work_kind"],
                verifier_row["work_id"],
                int(verifier_row["model_round_index"]),
                verifier_row["outbound_request_fingerprint"],
                verifier_row["relay_id"],
            )
            expected_scope = (
                attempt.attempt_id,
                attempt.subject_id,
                attempt.work_kind,
                attempt.work_id,
                attempt.model_round_index,
                binding.outbound_request_fingerprint,
                binding.relay_id,
            )
            if verifier_scope != expected_scope:
                conn.rollback()
                raise BackgroundModelResponseConflict(
                    attempt,
                    "late-return verifier scope does not match durable request binding",
                )
            try:
                verifier = LateReturnVerifier(
                    key_id=verifier_row["key_id"],
                    algorithm=verifier_row["algorithm"],
                    modulus_hex=verifier_row["modulus_hex"],
                    public_exponent=int(verifier_row["public_exponent"]),
                )
            except ValueError as exc:
                conn.rollback()
                raise BackgroundModelResponseConflict(
                    attempt,
                    "bound late-return verifier is not a canonical external "
                    "authority; the exact return cannot be verified",
                ) from exc
            message = late_return_message(
                attempt_id=attempt.attempt_id,
                subject_id=attempt.subject_id,
                work_kind=attempt.work_kind,
                work_id=attempt.work_id,
                model_round_index=attempt.model_round_index,
                outbound_request_fingerprint=binding.outbound_request_fingerprint,
                relay_id=binding.relay_id,
                provider=provider,
                model=model,
                provider_request_id=provider_request_id,
                response_fingerprint=response_fingerprint,
                payload_sha256=payload_sha256,
            )
            if not verify_late_return_proof(
                verifier,
                message=message,
                proof=late_return_proof.strip(),
            ):
                conn.rollback()
                raise BackgroundModelResponseConflict(
                    attempt,
                    "late trusted return signature is invalid for this exact "
                    "attempt, request and response",
                )

            already_consumed = verifier_row["consumed_at"] is not None
            if already_consumed:
                # Consumption is a durable one-shot gate, not key destruction:
                # the external signer may physically still hold its private key,
                # but Core will accept only an exact replay of the response that
                # already won first-writer-wins. Missing canonical rows after a
                # consumed verifier fail closed rather than being reconstructed.
                existing_receipt = conn.execute(
                    """
                    SELECT * FROM background_model_response_receipts
                    WHERE attempt_id=?
                    """,
                    (attempt_id,),
                ).fetchone()
                existing_handoff = conn.execute(
                    """
                    SELECT * FROM background_model_return_handoffs
                    WHERE attempt_id=?
                    """,
                    (attempt_id,),
                ).fetchone()
                if existing_receipt is None or existing_handoff is None:
                    conn.rollback()
                    raise BackgroundModelResponseConflict(
                        attempt,
                        "late-return verifier is already consumed but its canonical "
                        "receipt/handoff is missing",
                    )

            receipt_fields = {
                "attempt_id": attempt.attempt_id,
                "subject_id": attempt.subject_id,
                "work_kind": attempt.work_kind,
                "work_id": attempt.work_id,
                "model_round_index": attempt.model_round_index,
                "outbound_request_fingerprint": binding.outbound_request_fingerprint,
                "relay_id": binding.relay_id,
                "provider": provider,
                "model": model,
                "provider_request_id": provider_request_id,
                "response_fingerprint": response_fingerprint,
                "payload_sha256": payload_sha256,
            }
            receipt_proof = self._receipt_proof(**receipt_fields)
            conn.execute(
                """
                INSERT OR IGNORE INTO background_model_response_receipts(
                    attempt_id, subject_id, work_kind, work_id,
                    model_round_index, outbound_request_fingerprint, relay_id,
                    provider, model, provider_request_id, response_fingerprint,
                    payload_sha256, authenticity_proof, captured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    *receipt_fields.values(),
                    receipt_proof,
                    canonical_utc_iso(moment, "captured_at"),
                ),
            )
            receipt_row = conn.execute(
                """
                SELECT * FROM background_model_response_receipts
                WHERE attempt_id=?
                """,
                (attempt_id,),
            ).fetchone()
            if receipt_row is None:
                conn.rollback()
                raise RuntimeError("verified late return receipt was not durable")
            receipt = self._receipt_from_row(receipt_row)
            actual_receipt = (
                receipt.attempt_id,
                receipt.subject_id,
                receipt.work_kind,
                receipt.work_id,
                receipt.model_round_index,
                receipt.outbound_request_fingerprint,
                receipt.relay_id,
                receipt.provider,
                receipt.model,
                receipt.provider_request_id,
                receipt.response_fingerprint,
                receipt.payload_sha256,
                receipt.authenticity_proof,
            )
            expected_receipt = (*receipt_fields.values(), receipt_proof)
            if actual_receipt != expected_receipt:
                conn.rollback()
                raise BackgroundModelResponseConflict(
                    attempt,
                    "verified late return conflicts with existing durable receipt",
                )

            conn.execute(
                """
                INSERT OR IGNORE INTO background_model_return_handoffs(
                    attempt_id, directive_payload, payload_sha256,
                    authenticity_proof
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    directive_payload,
                    payload_sha256,
                    receipt_proof,
                ),
            )
            handoff = conn.execute(
                """
                SELECT * FROM background_model_return_handoffs
                WHERE attempt_id=?
                """,
                (attempt_id,),
            ).fetchone()
            if handoff is None or (
                handoff["directive_payload"],
                handoff["payload_sha256"],
                handoff["authenticity_proof"],
            ) != (
                directive_payload,
                payload_sha256,
                receipt_proof,
            ):
                conn.rollback()
                raise BackgroundModelResponseConflict(
                    attempt,
                    "verified late return conflicts with existing exact handoff",
                )

            if not already_consumed:
                consumed = conn.execute(
                    """
                    UPDATE background_model_return_verifiers
                    SET consumed_at=?
                    WHERE attempt_id=? AND consumed_at IS NULL
                    """,
                    (
                        canonical_utc_iso(moment, "consumed_at"),
                        attempt_id,
                    ),
                ).rowcount
                if consumed != 1:
                    conn.rollback()
                    raise BackgroundModelResponseConflict(
                        attempt,
                        "late-return verifier consumption lost a concurrent race",
                    )
            conn.commit()

        return self.stage_exact_response(
            attempt_id,
            staged_at=moment,
            provider=provider,
            model=model,
            provider_request_id=provider_request_id,
            response_fingerprint=response_fingerprint,
            directive_payload=directive_payload,
            authenticity_proof=receipt_proof,
            evidence=evidence.strip(),
        )

    def response_authenticity_receipt(
        self,
        attempt_id: str,
    ) -> BackgroundModelResponseReceipt | None:
        """Read a public receipt; never exposes or invokes the signing authority."""

        with self.store._connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM background_model_response_receipts
                WHERE attempt_id=?
                """,
                (attempt_id,),
            ).fetchone()
        return None if row is None else self._receipt_from_row(row)

    def _verify_response_authenticity(
        self,
        conn: object,
        *,
        attempt: BackgroundModelAttempt,
        binding: BackgroundModelRequestBinding,
        provider: str,
        model: str,
        provider_request_id: str,
        response_fingerprint: str,
        payload_sha256: str,
        authenticity_proof: str,
    ) -> BackgroundModelResponseReceipt:
        row = conn.execute(
            """
            SELECT * FROM background_model_response_receipts
            WHERE attempt_id=?
            """,
            (attempt.attempt_id,),
        ).fetchone()
        if row is None:
            raise BackgroundModelResponseConflict(
                attempt,
                "trusted provider-return authenticity receipt is missing",
            )
        receipt = self._receipt_from_row(row)
        receipt_fields = {
            "attempt_id": receipt.attempt_id,
            "subject_id": receipt.subject_id,
            "work_kind": receipt.work_kind,
            "work_id": receipt.work_id,
            "model_round_index": receipt.model_round_index,
            "outbound_request_fingerprint": receipt.outbound_request_fingerprint,
            "relay_id": receipt.relay_id,
            "provider": receipt.provider,
            "model": receipt.model,
            "provider_request_id": receipt.provider_request_id,
            "response_fingerprint": receipt.response_fingerprint,
            "payload_sha256": receipt.payload_sha256,
        }
        expected_proof = self._receipt_proof(**receipt_fields)
        if not hmac.compare_digest(receipt.authenticity_proof, expected_proof):
            raise BackgroundModelResponseConflict(
                attempt,
                "trusted provider-return receipt authenticator is invalid",
            )
        if not hmac.compare_digest(authenticity_proof, receipt.authenticity_proof):
            raise BackgroundModelResponseConflict(
                attempt,
                "supplied provider-return authenticity proof is invalid",
            )
        expected_identity = (
            attempt.attempt_id,
            attempt.subject_id,
            attempt.work_kind,
            attempt.work_id,
            attempt.model_round_index,
            binding.outbound_request_fingerprint,
            binding.relay_id,
            provider,
            model,
            provider_request_id,
            response_fingerprint,
            payload_sha256,
        )
        actual_identity = (
            receipt.attempt_id,
            receipt.subject_id,
            receipt.work_kind,
            receipt.work_id,
            receipt.model_round_index,
            receipt.outbound_request_fingerprint,
            receipt.relay_id,
            receipt.provider,
            receipt.model,
            receipt.provider_request_id,
            receipt.response_fingerprint,
            receipt.payload_sha256,
        )
        if actual_identity != expected_identity:
            raise BackgroundModelResponseConflict(
                attempt,
                "trusted provider-return receipt does not bind the exact attempt, "
                "request, provider identity, and response bytes",
            )
        return receipt

    def staged_response(
        self,
        attempt_id: str,
    ) -> BackgroundModelResponseStaging | None:
        with self.store._connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM background_model_responses WHERE attempt_id=?
                """,
                (attempt_id,),
            ).fetchone()
        return None if row is None else self._staging_from_row(row)

    def stage_exact_response(
        self,
        attempt_id: str,
        *,
        staged_at: datetime,
        provider: str,
        model: str,
        provider_request_id: str,
        response_fingerprint: str,
        directive_payload: str,
        authenticity_proof: str | None = None,
        evidence: str,
    ) -> BackgroundModelResponseStaging:
        """Durably bind one exact externally preserved provider reply to an attempt.

        Verification is exact and fail-closed: the payload must strictly decode to
        a ModelDirective, must carry a full provider/model/request_id identity that
        matches both the caller-supplied identity and its own usage/provenance, and
        must reproduce the supplied response fingerprint. Staging is refused for an
        attempt that provably never crossed the provider boundary.
        """

        moment = as_utc(staged_at, "staged_at")
        for field_name, value in (
            ("provider", provider),
            ("model", model),
            ("provider_request_id", provider_request_id),
            ("response_fingerprint", response_fingerprint),
            ("directive_payload", directive_payload),
            ("evidence", evidence),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"exact provider response {field_name} must be non-blank"
                )
        supplied_provider = provider.strip()
        supplied_model = model.strip()
        supplied_request_id = provider_request_id.strip()
        supplied_fingerprint = response_fingerprint.strip()
        supplied_authenticity_proof = (
            authenticity_proof.strip()
            if isinstance(authenticity_proof, str) and authenticity_proof.strip()
            else None
        )

        directive = decode_model_directive(directive_payload)
        fingerprint = self._response_fingerprint(directive)
        if fingerprint != supplied_fingerprint:
            raise ValueError(
                "exact provider response fingerprint does not match the supplied directive"
            )
        directive_provider, directive_model, directive_request_id = (
            self._provider_identity(directive)
        )
        if (
            directive_provider is None
            or directive_model is None
            or directive_request_id is None
        ):
            raise ValueError(
                "exact provider response must carry a full provider/model/request_id identity"
            )
        if (
            directive_provider,
            directive_model,
            directive_request_id,
        ) != (supplied_provider, supplied_model, supplied_request_id):
            raise ValueError(
                "exact provider response identity conflicts with its own directive identity"
            )
        payload_sha256 = hashlib.sha256(
            directive_payload.encode("utf-8")
        ).hexdigest()

        with self.store._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if row is None:
                conn.rollback()
                raise KeyError(f"unknown background model attempt: {attempt_id}")
            current = self._from_row(row)
            if current.state not in self._STAGABLE_STATES:
                conn.rollback()
                raise BackgroundModelResponseConflict(
                    current,
                    "a durable exact provider response cannot be staged for an "
                    "attempt that provably did not cross the provider boundary",
                )
            # Route B (Corrective-003, closing `BLK-W20-001`): a receipt row can
            # now only have been created by a genuine external cryptographic proof
            # verified against the durable bound verifier.  Its absence is
            # therefore a durable, unforgeable marker that any provider provenance
            # already on the attempt row was written by an *unverified* local live
            # completion and carries no authenticity.  A genuine external proof is
            # authoritative over such state and supersedes it, instead of being
            # blocked by it -- which is what makes a forged local completion unable
            # to poison a later genuine RSA trusted return.  When a verified
            # receipt does exist, the strict equality/conflict rule is unchanged,
            # preserving first-writer-wins and exactly-once for verified state.
            verified_receipt_row = conn.execute(
                """
                SELECT authenticity_proof FROM background_model_response_receipts
                WHERE attempt_id=?
                """,
                (attempt_id,),
            ).fetchone()
            # The receipt proof is an HMAC over exactly the supplied fields, so
            # equality means "the verified receipt in durable storage is for these
            # very bytes".  Note that ``attach_late_trusted_return`` commits the
            # receipt before staging (see FINAL_HANDOFF.md, inherited observation
            # 1), so a matching receipt here is normally the one this same genuine
            # proof just created.  Only a *differing* verified receipt means a
            # different return already won first-writer-wins.
            verified_conflicting_receipt = (
                verified_receipt_row is not None
                and str(verified_receipt_row["authenticity_proof"])
                != str(supplied_authenticity_proof).strip()
            )
            supersedes_unverified_local = False
            if current.state in {"response_returned", "metered"} and (
                current.provider,
                current.model,
                current.provider_request_id,
                current.response_fingerprint,
            ) != (
                supplied_provider,
                supplied_model,
                supplied_request_id,
                supplied_fingerprint,
            ):
                if verified_conflicting_receipt:
                    conn.rollback()
                    raise BackgroundModelResponseConflict(
                        current,
                        "supplied exact provider identity conflicts with durable "
                        "attempt provenance",
                    )
                supersedes_unverified_local = True
            binding_row = conn.execute(
                """
                SELECT * FROM background_model_request_bindings
                WHERE attempt_id=?
                """,
                (attempt_id,),
            ).fetchone()
            binding = (
                None if binding_row is None else self._binding_from_row(binding_row)
            )
            try:
                # The pre-dispatch binding proves routing.  The trusted receipt
                # below proves the actual returned provider bytes, so recovery no
                # longer treats a caller-visible relay echo as authenticity.
                binding = self._require_origin_binding(
                    current,
                    binding,
                    supplied_request_id=supplied_request_id,
                    require_relay_echo=(
                        supplied_authenticity_proof is None
                        and current.state in {"dispatching", "in_doubt"}
                    ),
                )
                if supplied_authenticity_proof is None:
                    raise BackgroundModelResponseConflict(
                        current,
                        "trusted provider-return authenticity proof is missing",
                    )
                self._verify_response_authenticity(
                    conn,
                    attempt=current,
                    binding=binding,
                    provider=supplied_provider,
                    model=supplied_model,
                    provider_request_id=supplied_request_id,
                    response_fingerprint=supplied_fingerprint,
                    payload_sha256=payload_sha256,
                    authenticity_proof=supplied_authenticity_proof,
                )
            except BackgroundModelResponseConflict:
                conn.rollback()
                raise

            conn.execute(
                """
                INSERT OR IGNORE INTO background_model_responses(
                    attempt_id, provider, model, provider_request_id,
                    response_fingerprint, directive_payload, payload_sha256,
                    authenticity_proof, staged_at, evidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    supplied_provider,
                    supplied_model,
                    supplied_request_id,
                    supplied_fingerprint,
                    directive_payload,
                    payload_sha256,
                    supplied_authenticity_proof,
                    canonical_utc_iso(moment, "staged_at"),
                    evidence.strip(),
                ),
            )
            staged_row = conn.execute(
                "SELECT * FROM background_model_responses WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if staged_row is None:
                conn.rollback()
                raise RuntimeError("exact provider response staging was not durable")
            staged = self._staging_from_row(staged_row)
            if (
                staged.provider,
                staged.model,
                staged.provider_request_id,
                staged.response_fingerprint,
                staged.directive_payload,
                staged.authenticity_proof,
            ) != (
                supplied_provider,
                supplied_model,
                supplied_request_id,
                supplied_fingerprint,
                directive_payload,
                supplied_authenticity_proof,
            ):
                conn.rollback()
                raise BackgroundModelResponseConflict(
                    current,
                    "durable exact provider response conflicts with the staged replay",
                )

            if current.state in {"dispatching", "in_doubt"}:
                conn.execute(
                    """
                    UPDATE background_model_attempts
                    SET state='response_returned', updated_at=?, provider=?,
                        model=?, provider_request_id=?, response_fingerprint=?,
                        reconciliation_evidence=?, failure_kind=NULL,
                        failure_detail=NULL
                    WHERE attempt_id=? AND state IN ('dispatching', 'in_doubt')
                    """,
                    (
                        canonical_utc_iso(moment, "updated_at"),
                        supplied_provider,
                        supplied_model,
                        supplied_request_id,
                        supplied_fingerprint,
                        evidence.strip(),
                        attempt_id,
                    ),
                )
            elif supersedes_unverified_local:
                # Route B: correct the unverified local provenance to the exact
                # externally-proven identity without demoting a state that has
                # already been durably recorded (and possibly metered).  The
                # verified receipt + handoff + staged response written above are
                # what make this attempt's bytes authoritative from now on.
                conn.execute(
                    """
                    UPDATE background_model_attempts
                    SET provider=?, model=?, provider_request_id=?,
                        response_fingerprint=?, reconciliation_evidence=?,
                        updated_at=?
                    WHERE attempt_id=? AND state IN ('response_returned', 'metered')
                    """,
                    (
                        supplied_provider,
                        supplied_model,
                        supplied_request_id,
                        supplied_fingerprint,
                        evidence.strip(),
                        canonical_utc_iso(moment, "updated_at"),
                        attempt_id,
                    ),
                )
            row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            conn.commit()
        if row is None:
            raise RuntimeError("background attempt disappeared during exact-response staging")
        attempt = self._from_row(row)
        if attempt.state not in {"response_returned", "metered"}:
            raise BackgroundModelAttemptBlocked(attempt)
        return staged

    def recover_trusted_handoff(
        self,
        *,
        subject_id: str,
        work_kind: BackgroundAttemptWorkKind,
        work_id: str,
    ) -> tuple[BackgroundModelAttempt, BackgroundModelResponseStaging] | None:
        """Promote only Core-owned, trusted-callback bytes for the latest round.

        No caller supplies response bytes or receives a signing capability. An
        absent handoff never licenses provider redispatch; ordinary admission
        guards remain responsible for unresolved dispatching attempts.
        """
        attempts = self.list_for_work(
            subject_id=subject_id, work_kind=work_kind, work_id=work_id,
        )
        if not attempts:
            return None
        latest = attempts[-1]
        if any(previous.state != "metered" for previous in attempts[:-1]):
            return None
        with self.store._connection() as conn:
            handoff = conn.execute(
                "SELECT * FROM background_model_return_handoffs WHERE attempt_id=?",
                (latest.attempt_id,),
            ).fetchone()
        if handoff is None:
            return self.pending_exact_response(
                subject_id=subject_id, work_kind=work_kind, work_id=work_id,
            )
        payload = handoff["directive_payload"]
        digest = handoff["payload_sha256"]
        proof = handoff["authenticity_proof"]
        if (
            not isinstance(payload, str)
            or not isinstance(digest, str)
            or hashlib.sha256(payload.encode("utf-8")).hexdigest() != digest
            or not isinstance(proof, str)
        ):
            raise BackgroundModelResponseConflict(
                latest, "trusted return handoff payload or digest is corrupt",
            )
        # The existing strict decoder rejects duplicate semantic JSON keys at
        # every nesting level. stage_exact_response verifies the signed receipt,
        # originating request, complete attempt scope and exact payload digest.
        directive = decode_model_directive(payload)
        provider, model, request_id = self._provider_identity(directive)
        if provider is None or model is None or request_id is None:
            raise BackgroundModelResponseConflict(
                latest, "trusted return handoff has no provider identity",
            )
        existing = self.staged_response(latest.attempt_id)
        if existing is not None:
            # Verify the already-staged bytes first (including the legacy payload
            # hash error) before comparing them with the callback's handoff.
            self.exact_response_directive(latest.attempt_id)
            if (existing.directive_payload, existing.payload_sha256,
                existing.authenticity_proof) != (payload, digest, proof):
                raise BackgroundModelResponseConflict(
                    latest, "staged response conflicts with trusted return handoff",
                )
            return latest, existing
        staged = self.stage_exact_response(
            latest.attempt_id,
            staged_at=latest.admitted_at,
            provider=provider,
            model=model,
            provider_request_id=request_id,
            response_fingerprint=self._response_fingerprint(directive),
            directive_payload=payload,
            authenticity_proof=proof,
            evidence="Core trusted provider-return handoff",
        )
        return latest, staged

    def pending_exact_response(
        self,
        *,
        subject_id: str,
        work_kind: BackgroundAttemptWorkKind,
        work_id: str,
    ) -> tuple[BackgroundModelAttempt, BackgroundModelResponseStaging] | None:
        """Return the attempt/round an exact durable provider reply can resume.

        Only the latest attempt of the work item is eligible, and every earlier
        round must already be durably metered. Any other shape (including an
        unresolved attempt with no exact reply) stays fail-closed and uses the
        existing blocked/in-doubt/response-pending dispositions.
        """

        attempts = self.list_for_work(
            subject_id=subject_id,
            work_kind=work_kind,
            work_id=work_id,
        )
        if not attempts:
            return None
        latest = attempts[-1]
        if latest.state in {"admitted", "not_submitted"}:
            return None
        staged = self.staged_response(latest.attempt_id)
        if staged is None:
            return None
        if any(earlier.state != "metered" for earlier in attempts[:-1]):
            return None
        return latest, staged

    def exact_response_directive(self, attempt_id: str) -> ModelDirective:
        """Re-verify and return the exact directive for one durable attempt."""

        attempt = self.get(attempt_id)
        if attempt is None:
            raise KeyError(f"unknown background model attempt: {attempt_id}")
        staged = self.staged_response(attempt_id)
        if staged is None:
            raise BackgroundModelResponsePending(attempt)
        if attempt.state not in {"response_returned", "metered"}:
            raise BackgroundModelResponseConflict(
                attempt,
                "staged exact provider response is not durably reconciled with "
                "the attempt",
            )
        if (
            attempt.provider,
            attempt.model,
            attempt.provider_request_id,
            attempt.response_fingerprint,
        ) != (
            staged.provider,
            staged.model,
            staged.provider_request_id,
            staged.response_fingerprint,
        ):
            raise BackgroundModelResponseConflict(
                attempt,
                "staged exact provider response does not match durable attempt "
                "provenance",
            )
        if (
            hashlib.sha256(staged.directive_payload.encode("utf-8")).hexdigest()
            != staged.payload_sha256
        ):
            raise BackgroundModelResponseConflict(
                attempt,
                "staged exact provider response bytes do not match their durable "
                "payload hash",
            )
        directive = decode_model_directive(staged.directive_payload)
        if self._response_fingerprint(directive) != attempt.response_fingerprint:
            raise BackgroundModelResponseConflict(
                attempt,
                "staged directive does not reproduce the durable response "
                "fingerprint",
            )
        binding = self.outbound_request_binding(attempt_id)
        binding = self._require_origin_binding(
            attempt,
            binding,
            supplied_request_id=staged.provider_request_id,
            require_relay_echo=False,
        )
        if staged.authenticity_proof is None:
            raise BackgroundModelResponseConflict(
                attempt,
                "staged exact response has no trusted provider-return authenticity proof",
            )
        with self.store._connection() as conn:
            self._verify_response_authenticity(
                conn,
                attempt=attempt,
                binding=binding,
                provider=staged.provider,
                model=staged.model,
                provider_request_id=staged.provider_request_id,
                response_fingerprint=staged.response_fingerprint,
                payload_sha256=staged.payload_sha256,
                authenticity_proof=staged.authenticity_proof,
            )
        return directive
