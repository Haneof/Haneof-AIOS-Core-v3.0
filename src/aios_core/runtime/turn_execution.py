"""Durable at-most-once admission, NOT general mid-turn crash recovery.

A row is claimed before any turn side effects. A crash/exception leaves an
uncertain claim: a caller must inspect receipts, not blindly run the turn again.
The table is additive runtime state in the same private World SQLite database.
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from contextlib import closing, contextmanager
from typing import Iterator

from aios_core.contracts.refs import ObjectRef
from aios_core.storage.idempotency import canonical_json_dumps


class TurnExecutionRefused(RuntimeError):
    def __init__(self, *, state: str, assistant_ref: ObjectRef | None = None):
        self.state = state
        self.assistant_ref = assistant_ref
        super().__init__(f"turn execution refused: {state}; inspect existing receipts, do not rerun")


class TurnAlreadyCompleted(TurnExecutionRefused):
    """Output already exists; this exception is not a fabricated FusedTurnResult."""


class TurnExecutionInDoubt(TurnExecutionRefused):
    """Another caller may be running, or a previous attempt was interrupted."""


class TurnInputConflict(TurnExecutionRefused):
    """A claimed turn identity was reused with different user input/time."""


class TurnExecutionStore:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runtime_turn_executions (
                    subject_id TEXT NOT NULL, session_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL, input_hash TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('started', 'completed')),
                    PRIMARY KEY(subject_id, session_id, turn_index)
                )
            """)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with closing(sqlite3.connect(self.db_path, timeout=5.0)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout=5000")
            with conn:
                yield conn

    def claim(self, *, subject_id: str, session_id: str, turn_index: int,
              user_input: str, occurred_at: str, assistant_id: str) -> None:
        digest = hashlib.sha256(canonical_json_dumps([user_input, occurred_at]).encode()).hexdigest()
        key = (subject_id, session_id, turn_index)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("""
                SELECT input_hash, state FROM runtime_turn_executions
                WHERE subject_id=? AND session_id=? AND turn_index=?
            """, key).fetchone()
            output = conn.execute("""
                SELECT revision FROM object_revisions WHERE object_id=?
                ORDER BY revision DESC LIMIT 1
            """, (assistant_id,)).fetchone()
            ref = None if output is None else ObjectRef(object_id=assistant_id, revision=output["revision"])
            if row is not None:
                if row["input_hash"] != digest:
                    raise TurnInputConflict(state="input_conflict", assistant_ref=ref)
                if row["state"] == "completed":
                    raise TurnAlreadyCompleted(state="completed", assistant_ref=ref)
                raise TurnExecutionInDoubt(state="started_or_interrupted", assistant_ref=ref)
            if ref is not None:
                # Upgrade compatibility: pre-guard durable assistant output also
                # prohibits inference. Do not claim all old maintenance completed.
                raise TurnAlreadyCompleted(state="legacy_output_present", assistant_ref=ref)
            conn.execute("""
                INSERT INTO runtime_turn_executions
                (subject_id, session_id, turn_index, input_hash, state)
                VALUES (?, ?, ?, ?, 'started')
            """, (*key, digest))

    def complete(self, *, subject_id: str, session_id: str, turn_index: int) -> None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            updated = conn.execute("""
                UPDATE runtime_turn_executions SET state='completed'
                WHERE subject_id=? AND session_id=? AND turn_index=? AND state='started'
            """, (subject_id, session_id, turn_index))
            if updated.rowcount != 1:
                raise RuntimeError("turn completion has no matching execution claim")
