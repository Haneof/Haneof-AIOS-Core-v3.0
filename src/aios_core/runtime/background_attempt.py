"""Durable non-world admission for background model execution.

A background Wake/Periodic Review model round gets a stable attempt identity before
provider dispatch. The table records execution uncertainty only; token/usage truth
remains in ModelMeteringLedger.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aios_core.contracts.time import as_utc, canonical_utc_iso
from aios_core.storage.idempotency import canonical_json_dumps
from aios_core.storage.sqlite_store import SQLiteWorldStore

from .cognitive_runtime import ModelDirective


BackgroundAttemptWorkKind = Literal["wake", "periodic_review", "user_turn"]
BackgroundAttemptState = Literal[
    "admitted",
    "dispatching",
    "not_submitted",
    "in_doubt",
    "response_returned",
    "metered",
]


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
    ) -> BackgroundModelAttempt:
        moment = as_utc(dispatched_at, "dispatched_at")
        with self.store._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            changed = conn.execute(
                """
                UPDATE background_model_attempts
                SET state='dispatching', updated_at=?
                WHERE attempt_id=? AND state='admitted'
                """,
                (canonical_utc_iso(moment, "updated_at"), attempt_id),
            ).rowcount
            row = conn.execute(
                "SELECT * FROM background_model_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            conn.commit()
        if row is None:
            raise KeyError(f"unknown background model attempt: {attempt_id}")
        attempt = self._from_row(row)
        if changed == 1:
            return attempt
        if attempt.state in {"dispatching", "in_doubt"}:
            raise BackgroundModelExecutionInDoubt(attempt)
        if attempt.state == "response_returned":
            raise BackgroundModelResponsePending(attempt)
        raise BackgroundModelAttemptBlocked(attempt)

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
        fingerprint = self._response_fingerprint(directive)
        with self.store._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
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
        if row is None:
            raise KeyError(f"unknown background model attempt: {attempt_id}")
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
        values = {
            "provider": provider,
            "model": model,
            "provider_request_id": provider_request_id,
            "response_fingerprint": response_fingerprint,
            "evidence": evidence,
        }
        if any(not isinstance(value, str) or not value.strip() for value in values.values()):
            raise ValueError("response reconciliation fields must be non-blank")
        moment = as_utc(reconciled_at, "reconciled_at")
        with self.store._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                UPDATE background_model_attempts
                SET state='response_returned', updated_at=?, provider=?, model=?,
                    provider_request_id=?, response_fingerprint=?,
                    reconciliation_evidence=?, failure_kind=NULL,
                    failure_detail=NULL
                WHERE attempt_id=? AND state IN ('dispatching', 'in_doubt')
                """,
                (
                    canonical_utc_iso(moment, "updated_at"),
                    provider.strip(),
                    model.strip(),
                    provider_request_id.strip(),
                    response_fingerprint.strip(),
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
        if attempt.state != "response_returned":
            raise BackgroundModelAttemptBlocked(attempt)
        return attempt
