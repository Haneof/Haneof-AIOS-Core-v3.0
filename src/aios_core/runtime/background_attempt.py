"""Durable non-world admission for background model execution.

A background Wake/Periodic Review model round gets a stable attempt identity before
provider dispatch. The table records execution uncertainty only; token/usage truth
remains in ModelMeteringLedger.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aios_core.contracts.time import as_utc, canonical_utc_iso
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore

from .capabilities import CapabilityCall
from .cognitive_runtime import ModelCallProvenance, ModelDirective, ModelUsage


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
            # A single store-private authority key authenticates return receipts.
            # It is never returned by an API, attached to RuntimeSnapshot, written
            # to evidence, or accepted from the recovery caller.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS background_model_authenticity_authority (
                    authority_id TEXT PRIMARY KEY,
                    secret_hex TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO background_model_authenticity_authority(
                    authority_id, secret_hex
                ) VALUES ('trusted-return-v1', ?)
                """,
                (secrets.token_hex(32),),
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
            conn.commit()

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

    @staticmethod
    def _authority_key(conn: object) -> bytes:
        row = conn.execute(
            """
            SELECT secret_hex
            FROM background_model_authenticity_authority
            WHERE authority_id='trusted-return-v1'
            """
        ).fetchone()
        if row is None:
            raise RuntimeError("trusted response authenticity authority is missing")
        try:
            key = bytes.fromhex(str(row["secret_hex"]))
        except ValueError as exc:
            raise RuntimeError(
                "trusted response authenticity authority is invalid"
            ) from exc
        if len(key) != 32:
            raise RuntimeError("trusted response authenticity authority is invalid")
        return key

    @classmethod
    def _receipt_proof(cls, conn: object, **fields: object) -> str:
        digest = hmac.new(
            cls._authority_key(conn),
            cls._receipt_message(**fields),
            hashlib.sha256,
        ).hexdigest()
        return f"bgresponse_v1_{digest}"

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
            # A not_submitted retry dispatches a new outbound request. Replace
            # the previous binding only inside this admitted→dispatching
            # transition; an in-doubt attempt's binding is never rewritten here.
            conn.execute(
                """
                INSERT INTO background_model_request_bindings(
                    attempt_id, subject_id, work_kind, work_id,
                    model_round_index, outbound_request_fingerprint,
                    relay_id, bound_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(attempt_id) DO UPDATE SET
                    subject_id=excluded.subject_id,
                    work_kind=excluded.work_kind,
                    work_id=excluded.work_id,
                    model_round_index=excluded.model_round_index,
                    outbound_request_fingerprint=excluded.outbound_request_fingerprint,
                    relay_id=excluded.relay_id,
                    bound_at=excluded.bound_at
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

    def mark_failure(
        self,
        attempt_id: str,
        *,
        failed_at: datetime,
        definitely_not_submitted: bool,
        error: BaseException,
    ) -> BackgroundModelAttempt:
        moment = as_utc(failed_at, "failed_at")
        target = "not_submitted" if definitely_not_submitted else "in_doubt"
        kind = type(error).__name__
        detail = str(error)[:1000]
        with self.store._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if definitely_not_submitted:
                receipt_row = conn.execute(
                    """
                    SELECT 1 FROM background_model_response_receipts
                    WHERE attempt_id=?
                    """,
                    (attempt_id,),
                ).fetchone()
                if receipt_row is not None:
                    attempt_row = conn.execute(
                        "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                        (attempt_id,),
                    ).fetchone()
                    conn.rollback()
                    if attempt_row is None:
                        raise KeyError(
                            f"unknown background model attempt: {attempt_id}"
                        )
                    raise BackgroundModelResponseConflict(
                        self._from_row(attempt_row),
                        "an authenticated provider return cannot be marked not submitted",
                    )
            conn.execute(
                """
                UPDATE background_model_attempts
                SET state=?, updated_at=?, failure_kind=?, failure_detail=?
                WHERE attempt_id=? AND state IN ('admitted', 'dispatching')
                """,
                (
                    target,
                    canonical_utc_iso(moment, "updated_at"),
                    kind,
                    detail,
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
        moment = as_utc(returned_at, "returned_at")
        provider, model, request_id = self._provider_identity(directive)
        has_recoverable_identity = all(
            value is not None for value in (provider, model, request_id)
        )
        fingerprint = self._response_fingerprint(directive)
        payload_sha256 = (
            hashlib.sha256(encode_model_directive(directive).encode("utf-8")).hexdigest()
            if has_recoverable_identity
            else None
        )
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
                receipt_row = conn.execute(
                    """
                    SELECT * FROM background_model_response_receipts
                    WHERE attempt_id=?
                    """,
                    (attempt_id,),
                ).fetchone()
                if receipt_row is None:
                    conn.rollback()
                    raise BackgroundModelResponseConflict(
                        current,
                        "provider response reached Core without a trusted "
                        "return-path receipt",
                    )
                receipt = self._receipt_from_row(receipt_row)
                try:
                    binding = self._require_origin_binding(
                        current,
                        binding,
                        supplied_request_id=request_id,
                        require_relay_echo=False,
                    )
                    self._verify_response_authenticity(
                        conn,
                        attempt=current,
                        binding=binding,
                        provider=provider,
                        model=model,
                        provider_request_id=request_id,
                        response_fingerprint=fingerprint,
                        payload_sha256=payload_sha256,
                        authenticity_proof=receipt.authenticity_proof,
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
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError("reconciliation evidence must be non-blank")
        moment = as_utc(reconciled_at, "reconciled_at")
        with self.store._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            receipt_row = conn.execute(
                """
                SELECT 1 FROM background_model_response_receipts
                WHERE attempt_id=?
                """,
                (attempt_id,),
            ).fetchone()
            if receipt_row is not None:
                attempt_row = conn.execute(
                    "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                    (attempt_id,),
                ).fetchone()
                conn.rollback()
                if attempt_row is None:
                    raise KeyError(f"unknown background model attempt: {attempt_id}")
                raise BackgroundModelResponseConflict(
                    self._from_row(attempt_row),
                    "an authenticated provider return cannot be reconciled as "
                    "not submitted",
                )
            conn.execute(
                """
                UPDATE background_model_attempts
                SET state='not_submitted', updated_at=?,
                    reconciliation_evidence=?, failure_kind=NULL,
                    failure_detail=NULL
                WHERE attempt_id=? AND state IN ('dispatching', 'in_doubt')
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

    def _capture_trusted_response_return(
        self,
        attempt_id: str,
        *,
        captured_at: datetime,
        directive: ModelDirective,
    ) -> BackgroundModelResponseReceipt:
        """Mint a receipt at the internal provider/relay return boundary.

        This method is intentionally private and is invoked only by Core-owned
        trusted-return surfaces: CognitiveRuntime's normal return callback and
        FusedTurnRuntime's exact returned-response recovery API. External staging
        receives neither the HMAC key nor a signing callable and cannot supply or
        override a proof.
        """

        moment = as_utc(captured_at, "captured_at")
        provider, model, request_id = self._provider_identity(directive)
        if provider is None or model is None or request_id is None:
            raise ValueError(
                "trusted provider response must carry full provider/model/request_id identity"
            )
        directive_payload = encode_model_directive(directive)
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
            if attempt.state not in {
                "dispatching",
                "in_doubt",
                "response_returned",
                "metered",
            }:
                conn.rollback()
                raise BackgroundModelResponseConflict(
                    attempt,
                    "trusted return receipt cannot be captured before the provider boundary",
                )
            if attempt.state in {"response_returned", "metered"} and (
                attempt.provider,
                attempt.model,
                attempt.provider_request_id,
                attempt.response_fingerprint,
            ) != (provider, model, request_id, response_fingerprint):
                conn.rollback()
                raise BackgroundModelResponseConflict(
                    attempt,
                    "trusted return bytes conflict with durable attempt provenance",
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
                    supplied_request_id=request_id,
                    require_relay_echo=False,
                )
            except BackgroundModelResponseConflict:
                conn.rollback()
                raise

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
                "provider_request_id": request_id,
                "response_fingerprint": response_fingerprint,
                "payload_sha256": payload_sha256,
            }
            proof = self._receipt_proof(conn, **receipt_fields)
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
                    proof,
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
                raise RuntimeError("trusted response receipt was not durable")
            receipt = self._receipt_from_row(receipt_row)
            expected = (
                *receipt_fields.values(),
                proof,
            )
            actual = (
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
            if actual != expected:
                conn.rollback()
                raise BackgroundModelResponseConflict(
                    attempt,
                    "trusted return bytes conflict with the receipt already captured "
                    "for this attempt",
                )
            conn.commit()
        return receipt

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
        expected_proof = self._receipt_proof(conn, **receipt_fields)
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
                conn.rollback()
                raise BackgroundModelResponseConflict(
                    current,
                    "supplied exact provider identity conflicts with durable "
                    "attempt provenance",
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
