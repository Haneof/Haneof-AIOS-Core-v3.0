"""Durable at-most-once admission and supported user-turn recovery.

A row is claimed before turn side effects. Ordinary retries remain fail-closed.
CG-003 adds an explicit inspection/reconciliation surface that can authorize a
retry only after the shared model-attempt ledger durably proves that every model
attempt for the turn was not submitted. Durable assistant output can instead
reconcile the execution to completed without reinvoking the model.
"""
from __future__ import annotations

from contextlib import closing, contextmanager
from dataclasses import dataclass
import hashlib
from pathlib import Path
import sqlite3
from typing import Iterator, Literal

from aios_core.contracts.refs import ObjectRef
from aios_core.storage.idempotency import canonical_json_dumps


TURN_MODEL_ATTEMPT_PROTOCOL = "model_attempt_v1"
TurnRecoveryDisposition = Literal[
    "not_started",
    "completed",
    "safe_to_retry",
    "retry_authorized",
    "in_doubt",
]


class TurnExecutionRefused(RuntimeError):
    def __init__(self, *, state: str, assistant_ref: ObjectRef | None = None):
        self.state = state
        self.assistant_ref = assistant_ref
        super().__init__(f"turn execution refused: {state}; inspect existing receipts, do not rerun")


class TurnAlreadyCompleted(TurnExecutionRefused):
    """Output already exists; this exception is not a fabricated FusedTurnResult."""


class TurnExecutionInDoubt(TurnExecutionRefused):
    """A previous execution may have crossed a non-repeatable boundary."""


class TurnInputConflict(TurnExecutionRefused):
    """A claimed turn identity was reused with different user input/time."""


@dataclass(frozen=True)
class TurnExecutionStatus:
    execution_id: str
    state: str
    recovery_disposition: TurnRecoveryDisposition
    assistant_ref: ObjectRef | None
    attempt_ids: tuple[str, ...] = ()
    attempt_states: tuple[str, ...] = ()
    retry_authorized: bool = False
    retry_count: int = 0
    reconciliation_evidence: str | None = None


class TurnExecutionStore:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runtime_turn_executions (
                    subject_id TEXT NOT NULL, session_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL, input_hash TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('started', 'completed')),
                    attempt_protocol TEXT,
                    retry_authorized INTEGER NOT NULL DEFAULT 0,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    reconciliation_evidence TEXT,
                    PRIMARY KEY(subject_id, session_id, turn_index)
                )
            """)
            columns = {
                str(row["name"])
                for row in conn.execute(
                    "PRAGMA table_info(runtime_turn_executions)"
                ).fetchall()
            }
            if "attempt_protocol" not in columns:
                conn.execute(
                    "ALTER TABLE runtime_turn_executions ADD COLUMN attempt_protocol TEXT"
                )
            if "retry_authorized" not in columns:
                conn.execute(
                    "ALTER TABLE runtime_turn_executions "
                    "ADD COLUMN retry_authorized INTEGER NOT NULL DEFAULT 0"
                )
            if "retry_count" not in columns:
                conn.execute(
                    "ALTER TABLE runtime_turn_executions "
                    "ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0"
                )
            if "reconciliation_evidence" not in columns:
                conn.execute(
                    "ALTER TABLE runtime_turn_executions "
                    "ADD COLUMN reconciliation_evidence TEXT"
                )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with closing(sqlite3.connect(self.db_path, timeout=5.0)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout=5000")
            with conn:
                yield conn

    @staticmethod
    def execution_id_for(*, subject_id: str, session_id: str, turn_index: int) -> str:
        raw = canonical_json_dumps(
            [subject_id, session_id, int(turn_index)]
        ).encode("utf-8")
        return f"turnexec_{hashlib.sha256(raw).hexdigest()[:32]}"

    @staticmethod
    def _input_hash(*, user_input: str, occurred_at: str) -> str:
        return hashlib.sha256(
            canonical_json_dumps([user_input, occurred_at]).encode()
        ).hexdigest()

    @staticmethod
    def _assistant_ref(
        conn: sqlite3.Connection, assistant_id: str
    ) -> ObjectRef | None:
        output = conn.execute("""
            SELECT revision FROM object_revisions WHERE object_id=?
            ORDER BY revision DESC LIMIT 1
        """, (assistant_id,)).fetchone()
        if output is None:
            return None
        return ObjectRef(object_id=assistant_id, revision=int(output["revision"]))

    @staticmethod
    def _attempt_rows(
        conn: sqlite3.Connection,
        *,
        subject_id: str,
        execution_id: str,
    ) -> tuple[sqlite3.Row, ...]:
        try:
            rows = conn.execute("""
                SELECT attempt_id, state
                FROM background_model_attempts
                WHERE subject_id=? AND work_kind='user_turn' AND work_id=?
                ORDER BY model_round_index ASC
            """, (subject_id, execution_id)).fetchall()
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc):
                raise
            rows = []
        return tuple(rows)

    @staticmethod
    def _validate_input(
        row: sqlite3.Row,
        *,
        digest: str,
        assistant_ref: ObjectRef | None,
    ) -> None:
        if row["input_hash"] != digest:
            raise TurnInputConflict(
                state="input_conflict",
                assistant_ref=assistant_ref,
            )

    @staticmethod
    def _disposition(
        *,
        row: sqlite3.Row,
        assistant_ref: ObjectRef | None,
        attempt_states: tuple[str, ...],
    ) -> TurnRecoveryDisposition:
        if row["state"] == "completed" or assistant_ref is not None:
            return "completed"
        if bool(row["retry_authorized"]):
            return "retry_authorized"
        if row["attempt_protocol"] != TURN_MODEL_ATTEMPT_PROTOCOL:
            return "in_doubt"
        if attempt_states and all(state == "not_submitted" for state in attempt_states):
            return "safe_to_retry"
        return "in_doubt"

    def inspect(
        self,
        *,
        subject_id: str,
        session_id: str,
        turn_index: int,
        user_input: str,
        occurred_at: str,
        assistant_id: str,
    ) -> TurnExecutionStatus:
        digest = self._input_hash(user_input=user_input, occurred_at=occurred_at)
        execution_id = self.execution_id_for(
            subject_id=subject_id,
            session_id=session_id,
            turn_index=turn_index,
        )
        key = (subject_id, session_id, turn_index)
        with self._connect() as conn:
            row = conn.execute("""
                SELECT input_hash, state, attempt_protocol, retry_authorized,
                       retry_count, reconciliation_evidence
                FROM runtime_turn_executions
                WHERE subject_id=? AND session_id=? AND turn_index=?
            """, key).fetchone()
            ref = self._assistant_ref(conn, assistant_id)
            if row is None:
                if ref is not None:
                    return TurnExecutionStatus(
                        execution_id=execution_id,
                        state="legacy_output_present",
                        recovery_disposition="completed",
                        assistant_ref=ref,
                    )
                return TurnExecutionStatus(
                    execution_id=execution_id,
                    state="not_started",
                    recovery_disposition="not_started",
                    assistant_ref=None,
                )
            self._validate_input(row, digest=digest, assistant_ref=ref)
            attempts = self._attempt_rows(
                conn, subject_id=subject_id, execution_id=execution_id
            )
            attempt_ids = tuple(str(item["attempt_id"]) for item in attempts)
            attempt_states = tuple(str(item["state"]) for item in attempts)
            return TurnExecutionStatus(
                execution_id=execution_id,
                state=str(row["state"]),
                recovery_disposition=self._disposition(
                    row=row,
                    assistant_ref=ref,
                    attempt_states=attempt_states,
                ),
                assistant_ref=ref,
                attempt_ids=attempt_ids,
                attempt_states=attempt_states,
                retry_authorized=bool(row["retry_authorized"]),
                retry_count=int(row["retry_count"]),
                reconciliation_evidence=row["reconciliation_evidence"],
            )

    def claim(self, *, subject_id: str, session_id: str, turn_index: int,
              user_input: str, occurred_at: str, assistant_id: str) -> None:
        digest = self._input_hash(user_input=user_input, occurred_at=occurred_at)
        key = (subject_id, session_id, turn_index)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("""
                SELECT input_hash, state, attempt_protocol, retry_authorized,
                       retry_count, reconciliation_evidence
                FROM runtime_turn_executions
                WHERE subject_id=? AND session_id=? AND turn_index=?
            """, key).fetchone()
            ref = self._assistant_ref(conn, assistant_id)
            if row is not None:
                self._validate_input(row, digest=digest, assistant_ref=ref)
                if row["state"] == "completed":
                    raise TurnAlreadyCompleted(state="completed", assistant_ref=ref)
                if ref is not None:
                    conn.execute("""
                        UPDATE runtime_turn_executions
                        SET state='completed', retry_authorized=0,
                            reconciliation_evidence=COALESCE(
                                reconciliation_evidence,
                                'durable assistant output recovered during admission'
                            )
                        WHERE subject_id=? AND session_id=? AND turn_index=?
                          AND state='started'
                    """, key)
                    raise TurnAlreadyCompleted(
                        state="recovered_completed_output",
                        assistant_ref=ref,
                    )
                if bool(row["retry_authorized"]):
                    changed = conn.execute("""
                        UPDATE runtime_turn_executions
                        SET retry_authorized=0, retry_count=retry_count+1
                        WHERE subject_id=? AND session_id=? AND turn_index=?
                          AND state='started' AND retry_authorized=1
                    """, key).rowcount
                    if changed != 1:
                        raise TurnExecutionInDoubt(
                            state="retry_authorization_race",
                            assistant_ref=None,
                        )
                    return
                raise TurnExecutionInDoubt(
                    state="started_or_interrupted",
                    assistant_ref=ref,
                )
            if ref is not None:
                # Upgrade compatibility: pre-guard durable assistant output also
                # prohibits inference. Do not claim all old maintenance completed.
                raise TurnAlreadyCompleted(
                    state="legacy_output_present",
                    assistant_ref=ref,
                )
            conn.execute("""
                INSERT INTO runtime_turn_executions
                (subject_id, session_id, turn_index, input_hash, state,
                 attempt_protocol, retry_authorized, retry_count)
                VALUES (?, ?, ?, ?, 'started', ?, 0, 0)
            """, (*key, digest, TURN_MODEL_ATTEMPT_PROTOCOL))

    def authorize_retry(
        self,
        *,
        subject_id: str,
        session_id: str,
        turn_index: int,
        user_input: str,
        occurred_at: str,
        assistant_id: str,
        evidence: str,
    ) -> TurnExecutionStatus:
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError("retry authorization evidence must be non-blank")
        digest = self._input_hash(user_input=user_input, occurred_at=occurred_at)
        execution_id = self.execution_id_for(
            subject_id=subject_id,
            session_id=session_id,
            turn_index=turn_index,
        )
        key = (subject_id, session_id, turn_index)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("""
                SELECT input_hash, state, attempt_protocol, retry_authorized,
                       retry_count, reconciliation_evidence
                FROM runtime_turn_executions
                WHERE subject_id=? AND session_id=? AND turn_index=?
            """, key).fetchone()
            ref = self._assistant_ref(conn, assistant_id)
            if row is None:
                raise TurnExecutionInDoubt(
                    state="no_durable_execution_claim",
                    assistant_ref=ref,
                )
            self._validate_input(row, digest=digest, assistant_ref=ref)
            if row["state"] == "completed" or ref is not None:
                raise TurnAlreadyCompleted(
                    state="completed_output_present",
                    assistant_ref=ref,
                )
            attempts = self._attempt_rows(
                conn, subject_id=subject_id, execution_id=execution_id
            )
            attempt_states = tuple(str(item["state"]) for item in attempts)
            if (
                row["attempt_protocol"] != TURN_MODEL_ATTEMPT_PROTOCOL
                or not attempt_states
                or not all(state == "not_submitted" for state in attempt_states)
            ):
                raise TurnExecutionInDoubt(
                    state="provider_execution_not_proven_absent",
                    assistant_ref=None,
                )
            conn.execute("""
                UPDATE runtime_turn_executions
                SET retry_authorized=1, reconciliation_evidence=?
                WHERE subject_id=? AND session_id=? AND turn_index=?
                  AND state='started'
            """, (evidence.strip(), *key))

        return self.inspect(
            subject_id=subject_id,
            session_id=session_id,
            turn_index=turn_index,
            user_input=user_input,
            occurred_at=occurred_at,
            assistant_id=assistant_id,
        )

    def reconcile_completed(
        self,
        *,
        subject_id: str,
        session_id: str,
        turn_index: int,
        user_input: str,
        occurred_at: str,
        assistant_id: str,
        evidence: str,
    ) -> TurnExecutionStatus:
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError("completion reconciliation evidence must be non-blank")
        digest = self._input_hash(user_input=user_input, occurred_at=occurred_at)
        key = (subject_id, session_id, turn_index)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("""
                SELECT input_hash, state, attempt_protocol, retry_authorized,
                       retry_count, reconciliation_evidence
                FROM runtime_turn_executions
                WHERE subject_id=? AND session_id=? AND turn_index=?
            """, key).fetchone()
            ref = self._assistant_ref(conn, assistant_id)
            if row is None:
                if ref is None:
                    raise TurnExecutionInDoubt(
                        state="no_completion_receipt",
                        assistant_ref=None,
                    )
                return TurnExecutionStatus(
                    execution_id=self.execution_id_for(
                        subject_id=subject_id,
                        session_id=session_id,
                        turn_index=turn_index,
                    ),
                    state="legacy_output_present",
                    recovery_disposition="completed",
                    assistant_ref=ref,
                    reconciliation_evidence=evidence.strip(),
                )
            self._validate_input(row, digest=digest, assistant_ref=ref)
            if ref is None:
                raise TurnExecutionInDoubt(
                    state="assistant_output_not_durable",
                    assistant_ref=None,
                )
            conn.execute("""
                UPDATE runtime_turn_executions
                SET state='completed', retry_authorized=0,
                    reconciliation_evidence=?
                WHERE subject_id=? AND session_id=? AND turn_index=?
            """, (evidence.strip(), *key))

        return self.inspect(
            subject_id=subject_id,
            session_id=session_id,
            turn_index=turn_index,
            user_input=user_input,
            occurred_at=occurred_at,
            assistant_id=assistant_id,
        )

    def complete(self, *, subject_id: str, session_id: str, turn_index: int) -> None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            updated = conn.execute("""
                UPDATE runtime_turn_executions
                SET state='completed', retry_authorized=0
                WHERE subject_id=? AND session_id=? AND turn_index=? AND state='started'
            """, (subject_id, session_id, turn_index))
            if updated.rowcount != 1:
                raise RuntimeError("turn completion has no matching execution claim")
