"""Deterministic model-context assembly for AIOS v3.0.

The controller packages information selected by other mechanisms. It does not infer
user meaning, force a reasoning order, or manufacture memory when recommendation is
empty.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from aios_core.recommendation.proactive import MemoryCard, RecommendationBundle


def estimate_tokens(value: Any) -> int:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return max(1, (len(text) + 3) // 4)


class ModelContextBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_input: str = Field(min_length=1)
    current_topic: str | None = None
    ai_identity: Mapping[str, Any] = Field(default_factory=dict)
    recent_turns: tuple[Mapping[str, Any], ...] = ()
    memory_cards: tuple[MemoryCard, ...] = ()
    task_context: Mapping[str, Any] = Field(default_factory=dict)
    capability_catalog: tuple[Mapping[str, Any], ...] = ()
    token_budget: int = Field(ge=128)
    estimated_tokens: int = Field(ge=0)
    truncated: bool = False

    def as_cockpit(self) -> dict[str, Any]:
        return self.model_dump(mode="python")


class ContextController:
    """Assemble a bounded context without replacing AI judgment."""

    def __init__(self, *, default_token_budget: int = 3400) -> None:
        if default_token_budget < 128:
            raise ValueError("default_token_budget must be >= 128")
        self.default_token_budget = default_token_budget

    def assemble(
        self,
        *,
        user_input: str,
        current_topic: str | None,
        recommendation: RecommendationBundle,
        recent_turns: Sequence[Mapping[str, Any]] = (),
        ai_identity: Mapping[str, Any] | None = None,
        task_context: Mapping[str, Any] | None = None,
        capability_catalog: Sequence[Mapping[str, Any]] = (),
        token_budget: int | None = None,
    ) -> ModelContextBundle:
        if not user_input.strip():
            raise ValueError("user_input must be non-blank")

        budget = self.default_token_budget if token_budget is None else int(token_budget)
        if budget < 128:
            raise ValueError("token_budget must be >= 128")

        identity = dict(ai_identity or {})
        tasks = dict(task_context or {})
        capabilities = tuple(dict(item) for item in capability_catalog)

        fixed = {
            "user_input": user_input,
            "current_topic": current_topic,
            "ai_identity": identity,
            "task_context": tasks,
            "capability_catalog": capabilities,
        }
        used = estimate_tokens(fixed)
        truncated = used > budget

        selected_turns: list[Mapping[str, Any]] = []
        # Preserve the most recent dialogue first, then restore chronological order.
        for turn in reversed(list(recent_turns)):
            cost = estimate_tokens(turn)
            if used + cost > budget:
                truncated = True
                continue
            selected_turns.append(dict(turn))
            used += cost
        selected_turns.reverse()

        selected_cards: list[MemoryCard] = []
        for card in recommendation.cards:
            cost = estimate_tokens(card.model_dump(mode="python"))
            if used + cost > budget:
                truncated = True
                continue
            selected_cards.append(card)
            used += cost

        return ModelContextBundle(
            user_input=user_input,
            current_topic=(current_topic or "").strip() or None,
            ai_identity=identity,
            recent_turns=tuple(selected_turns),
            memory_cards=tuple(selected_cards),
            task_context=tasks,
            capability_catalog=capabilities,
            token_budget=budget,
            estimated_tokens=used,
            truncated=truncated,
        )
