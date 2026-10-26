"""ActiveRollingWindow: Strict 6-turn streaming rolling context window for AIOS 3.0.

Fulfills 争议六 & 问题一:
- Enforces an ergonomic 5~6 turn bounded front-end active window (<= 1500 tokens).
- When a turn slides out of the active window, it automatically queues for background
  streaming extraction without stalling user-facing dialogue (< 1s first-token latency).
- Each turn is bidirectional-linked to durable Observation records in SQLiteWorldStore.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import TYPE_CHECKING, Any, Sequence

from aios_core.context.budget_policy import resolve_context_budget_policy
from aios_core.contracts.models import ObjectRef
from aios_core.contracts.time import as_utc

if TYPE_CHECKING:
    from aios_core.storage.sqlite_store import SQLiteWorldStore


def _estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


@dataclass(frozen=True, slots=True)
class ActiveTurn:
    turn_index: int
    user_text: str
    user_observation_ref: ObjectRef
    occurred_at: datetime
    assistant_text: str | None = None
    assistant_observation_ref: ObjectRef | None = None
    estimated_tokens: int = 0

    def as_context_turn(self) -> dict[str, Any]:
        return {
            "turn_index": self.turn_index,
            "user_text": self.user_text,
            "user_ref": self.user_observation_ref.model_dump(mode="python"),
            "assistant_text": self.assistant_text,
            "assistant_ref": (
                self.assistant_observation_ref.model_dump(mode="python")
                if self.assistant_observation_ref
                else None
            ),
            "occurred_at": self.occurred_at.isoformat(),
            "estimated_tokens": self.estimated_tokens,
        }


class ActiveRollingWindow:
    """Bounded active dialogue window with automatic slide-out buffering for background extraction.

    Durable Persistence (DEF-003 Remediation):
    When an optional `store` (SQLiteWorldStore) is attached, overflow turns that slide out of
    the front-end active window are immediately persisted into `active_window_overflow_staging`.
    This guarantees that even under wearable power cuts, battery drain, or hard restarts,
    slid-out conversation turns waiting for background extraction are never lost in volatile memory.
    """

    def __init__(
        self,
        *,
        max_active_turns: int | None = None,
        max_token_budget: int | None = None,
        session_id: str = "default_session",
        store: SQLiteWorldStore | None = None,
    ) -> None:
        # Omitted -> policy (which also honours AIOS_BUDGET_* overrides); an
        # explicit argument still wins.
        policy = resolve_context_budget_policy(
            active_window_max_turns=max_active_turns,
            active_window_token_budget=max_token_budget,
        )
        max_active_turns = policy.active_window_max_turns
        max_token_budget = policy.active_window_token_budget

        if max_active_turns < 1:
            raise ValueError("max_active_turns must be at least 1")
        if max_token_budget < 256:
            raise ValueError("max_token_budget must be at least 256")

        self.max_active_turns = max_active_turns
        self.max_token_budget = max_token_budget
        self.session_id = session_id
        self.store = store
        self._active_turns: list[ActiveTurn] = []
        self._pending_extract_turns: list[ActiveTurn] = []

        if self.store is not None:
            self._ensure_staging_table()
            self._load_persisted_pending()

    def _ensure_staging_table(self) -> None:
        if self.store is None:
            return
        with self.store._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS active_window_overflow_staging (
                    session_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    user_text TEXT NOT NULL,
                    user_ref_id TEXT NOT NULL,
                    user_ref_rev INTEGER NOT NULL,
                    assistant_text TEXT,
                    assistant_ref_id TEXT,
                    assistant_ref_rev INTEGER,
                    occurred_at TEXT NOT NULL,
                    estimated_tokens INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    staged_at TEXT NOT NULL,
                    PRIMARY KEY (session_id, turn_index)
                )
                """
            )
            conn.commit()

    def _load_persisted_pending(self) -> None:
        if self.store is None:
            return
        with self.store._connection() as conn:
            cur = conn.execute(
                """
                SELECT session_id, turn_index, user_text, user_ref_id, user_ref_rev,
                       assistant_text, assistant_ref_id, assistant_ref_rev,
                       occurred_at, estimated_tokens
                FROM active_window_overflow_staging
                WHERE session_id = ? AND status = 'pending'
                ORDER BY turn_index ASC
                """,
                (self.session_id,),
            )
            for row in cur.fetchall():
                user_ref = ObjectRef(object_id=row["user_ref_id"], revision=row["user_ref_rev"])
                assistant_ref = (
                    ObjectRef(object_id=row["assistant_ref_id"], revision=row["assistant_ref_rev"])
                    if row["assistant_ref_id"]
                    else None
                )
                dt = datetime.fromisoformat(row["occurred_at"])
                turn = ActiveTurn(
                    turn_index=row["turn_index"],
                    user_text=row["user_text"],
                    user_observation_ref=user_ref,
                    occurred_at=dt,
                    assistant_text=row["assistant_text"],
                    assistant_observation_ref=assistant_ref,
                    estimated_tokens=row["estimated_tokens"],
                )
                self._pending_extract_turns.append(turn)

    def _persist_evicted_turn(self, turn: ActiveTurn) -> None:
        if self.store is None:
            return
        with self.store._connection() as conn:
            conn.execute(
                """
                INSERT INTO active_window_overflow_staging (
                    session_id, turn_index, user_text, user_ref_id, user_ref_rev,
                    assistant_text, assistant_ref_id, assistant_ref_rev,
                    occurred_at, estimated_tokens, status, staged_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                ON CONFLICT(session_id, turn_index) DO UPDATE SET
                    user_text = excluded.user_text,
                    assistant_text = excluded.assistant_text,
                    status = 'pending',
                    staged_at = excluded.staged_at
                """,
                (
                    self.session_id,
                    turn.turn_index,
                    turn.user_text,
                    turn.user_observation_ref.object_id,
                    turn.user_observation_ref.revision or 1,
                    turn.assistant_text,
                    turn.assistant_observation_ref.object_id if turn.assistant_observation_ref else None,
                    turn.assistant_observation_ref.revision if turn.assistant_observation_ref else None,
                    turn.occurred_at.isoformat(),
                    turn.estimated_tokens,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    @property
    def active_turns(self) -> list[ActiveTurn]:
        return list(self._active_turns)

    @property
    def pending_extract_turns(self) -> list[ActiveTurn]:
        return list(self._pending_extract_turns)

    def total_active_tokens(self) -> int:
        return sum(t.estimated_tokens for t in self._active_turns)

    def record_turn(
        self,
        *,
        turn_index: int,
        user_text: str,
        user_observation_ref: ObjectRef,
        occurred_at: datetime,
        assistant_text: str | None = None,
        assistant_observation_ref: ObjectRef | None = None,
    ) -> tuple[ActiveTurn, list[ActiveTurn]]:
        """Record a completed or in-progress turn and slide out overflow turns if budget exceeded."""
        dt = as_utc(occurred_at, "occurred_at")

        if user_observation_ref.revision is None or user_observation_ref.revision < 1:
            raise ValueError("user_observation_ref requires pinned revision")
        if assistant_observation_ref is not None:
            if assistant_observation_ref.revision is None or assistant_observation_ref.revision < 1:
                raise ValueError("assistant_observation_ref requires pinned revision")

        est_tokens = _estimate_tokens(user_text) + _estimate_tokens(assistant_text or "")

        turn = ActiveTurn(
            turn_index=turn_index,
            user_text=user_text.strip(),
            user_observation_ref=user_observation_ref,
            occurred_at=dt,
            assistant_text=assistant_text.strip() if assistant_text else None,
            assistant_observation_ref=assistant_observation_ref,
            estimated_tokens=est_tokens,
        )

        self._active_turns.append(turn)

        # Enforce bounds: max turns limit and token budget limit
        slid_out: list[ActiveTurn] = []

        while len(self._active_turns) > self.max_active_turns:
            evicted = self._active_turns.pop(0)
            slid_out.append(evicted)
            self._pending_extract_turns.append(evicted)
            self._persist_evicted_turn(evicted)

        while self.total_active_tokens() > self.max_token_budget and len(self._active_turns) > 1:
            evicted = self._active_turns.pop(0)
            slid_out.append(evicted)
            self._pending_extract_turns.append(evicted)
            self._persist_evicted_turn(evicted)

        return turn, slid_out

    def ack_extracted(self, turn_indices: Sequence[int]) -> int:
        """Acknowledge turns that have been extracted and condensed into summaries by background workers."""
        ack_set = set(turn_indices)
        original_count = len(self._pending_extract_turns)
        self._pending_extract_turns = [
            t for t in self._pending_extract_turns if t.turn_index not in ack_set
        ]
        if self.store is not None:
            with self.store._connection() as conn:
                for idx in ack_set:
                    conn.execute(
                        "UPDATE active_window_overflow_staging SET status = 'extracted' WHERE session_id = ? AND turn_index = ?",
                        (self.session_id, idx),
                    )
                conn.commit()
        return original_count - len(self._pending_extract_turns)

    def get_context_slice(self) -> list[dict[str, Any]]:
        """Produce the context slice representation ready for ModelContextBundle."""
        return [t.as_context_turn() for t in self._active_turns]
