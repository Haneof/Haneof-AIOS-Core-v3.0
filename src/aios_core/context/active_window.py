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
from typing import Any, Sequence

from aios_core.contracts.models import ObjectRef
from aios_core.contracts.time import as_utc


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
    """Bounded active dialogue window with automatic slide-out buffering for background extraction."""

    def __init__(
        self,
        *,
        max_active_turns: int = 6,
        max_token_budget: int = 1500,
        session_id: str = "default_session",
    ) -> None:
        if max_active_turns < 1:
            raise ValueError("max_active_turns must be at least 1")
        if max_token_budget < 256:
            raise ValueError("max_token_budget must be at least 256")

        self.max_active_turns = max_active_turns
        self.max_token_budget = max_token_budget
        self.session_id = session_id
        self._active_turns: list[ActiveTurn] = []
        self._pending_extract_turns: list[ActiveTurn] = []

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

        while self.total_active_tokens() > self.max_token_budget and len(self._active_turns) > 1:
            evicted = self._active_turns.pop(0)
            slid_out.append(evicted)
            self._pending_extract_turns.append(evicted)

        return turn, slid_out

    def ack_extracted(self, turn_indices: Sequence[int]) -> int:
        """Acknowledge turns that have been extracted and condensed into summaries by background workers."""
        ack_set = set(turn_indices)
        original_count = len(self._pending_extract_turns)
        self._pending_extract_turns = [
            t for t in self._pending_extract_turns if t.turn_index not in ack_set
        ]
        return original_count - len(self._pending_extract_turns)

    def get_context_slice(self) -> list[dict[str, Any]]:
        """Produce the context slice representation ready for ModelContextBundle."""
        return [t.as_context_turn() for t in self._active_turns]
