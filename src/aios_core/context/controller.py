"""Deterministic model-context assembly for AIOS v3.0.

The controller packages information selected by other mechanisms. It does not infer
user meaning, force a reasoning order, or manufacture memory when recommendation is
empty.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from aios_core.context.budget_policy import resolve_context_budget_policy
from aios_core.recommendation.proactive import MemoryCard, RecommendationBundle

_LOGGER = logging.getLogger(__name__)

try:
    # Owned by aios_core.context.tokenization; imported here so the historical
    # ``from aios_core.context.controller import estimate_tokens`` keeps working.
    from aios_core.context.tokenization import estimate_tokens
except ImportError:  # pragma: no cover - tokenization module not landed yet
    _LOGGER.warning(
        "aios_core.context.tokenization is unavailable; falling back to the legacy "
        "len(json)/4 estimator, which under-counts CJK text by ~2.5x."
    )

    import json

    def estimate_tokens(value: Any) -> int:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        return max(1, (len(text) + 3) // 4)


class ModelContextBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_input: str = Field(min_length=1)
    current_topic: str | None = None
    ai_identity: Mapping[str, Any] = Field(default_factory=dict)
    world_map: Mapping[str, Any] = Field(default_factory=dict)
    recent_turns: tuple[Mapping[str, Any], ...] = ()
    conversation_summaries: tuple[Mapping[str, Any], ...] = ()
    memory_cards: tuple[MemoryCard, ...] = ()
    task_context: Mapping[str, Any] = Field(default_factory=dict)
    capability_catalog: tuple[Mapping[str, Any], ...] = ()
    token_budget: int = Field(ge=128)
    estimated_tokens: int = Field(ge=0)
    truncated: bool = False
    # How many entries were dropped per section, e.g. {"recent_turns": 4}. Without it
    # truncation is invisible: `truncated` never reaches the prompt, so the model
    # experiences silent amnesia it cannot explain.
    dropped_sections: Mapping[str, int] = Field(default_factory=dict)

    def as_cockpit(self) -> dict[str, Any]:
        return self.model_dump(mode="python")


class ContextController:
    """Assemble a bounded context without replacing AI judgment."""

    def __init__(self, *, default_token_budget: int | None = None) -> None:
        policy = resolve_context_budget_policy(context_token_budget=default_token_budget)
        budget = policy.context_token_budget
        if budget < policy.context_min_token_budget:
            raise ValueError(
                "default_token_budget must be >= "
                f"{policy.context_min_token_budget}"
            )
        self.default_token_budget = budget

    def assemble(
        self,
        *,
        user_input: str,
        current_topic: str | None,
        recommendation: RecommendationBundle,
        recent_turns: Sequence[Mapping[str, Any]] = (),
        conversation_summaries: Sequence[Mapping[str, Any]] = (),
        ai_identity: Mapping[str, Any] | None = None,
        world_map: Mapping[str, Any] | None = None,
        task_context: Mapping[str, Any] | None = None,
        capability_catalog: Sequence[Mapping[str, Any]] = (),
        token_budget: int | None = None,
    ) -> ModelContextBundle:
        if not user_input.strip():
            raise ValueError("user_input must be non-blank")

        policy = resolve_context_budget_policy()
        budget = self.default_token_budget if token_budget is None else int(token_budget)
        if budget < policy.context_min_token_budget:
            raise ValueError(f"token_budget must be >= {policy.context_min_token_budget}")

        identity = dict(ai_identity or {})
        map_context = dict(world_map or {})
        tasks = dict(task_context or {})
        capabilities = tuple(dict(item) for item in capability_catalog)

        fixed = {
            "user_input": user_input,
            "current_topic": current_topic,
            "ai_identity": identity,
            "world_map": map_context,
            "task_context": tasks,
            "capability_catalog": capabilities,
        }
        used = estimate_tokens(fixed)
        truncated = used > budget

        dropped: dict[str, int] = {}

        selected_turns: list[Mapping[str, Any]] = []
        # Preserve the most recent dialogue first, then restore chronological order.
        for turn in reversed(list(recent_turns)):
            cost = estimate_tokens(turn)
            if used + cost > budget:
                truncated = True
                dropped["recent_turns"] = dropped.get("recent_turns", 0) + 1
                continue
            selected_turns.append(dict(turn))
            used += cost
        selected_turns.reverse()

        selected_summaries: list[Mapping[str, Any]] = []
        # Same-session summaries are continuity indexes. Keep recent raw dialogue
        # higher priority, then admit the newest summary windows that still fit.
        for summary in reversed(list(conversation_summaries)):
            cost = estimate_tokens(summary)
            if used + cost > budget:
                truncated = True
                dropped["conversation_summaries"] = (
                    dropped.get("conversation_summaries", 0) + 1
                )
                continue
            selected_summaries.append(dict(summary))
            used += cost
        selected_summaries.reverse()

        selected_cards: list[MemoryCard] = []
        for card in recommendation.cards:
            cost = estimate_tokens(card.model_dump(mode="python"))
            if used + cost > budget:
                truncated = True
                dropped["memory_cards"] = dropped.get("memory_cards", 0) + 1
                continue
            selected_cards.append(card)
            used += cost

        return ModelContextBundle(
            user_input=user_input,
            current_topic=(current_topic or "").strip() or None,
            ai_identity=identity,
            world_map=map_context,
            recent_turns=tuple(selected_turns),
            conversation_summaries=tuple(selected_summaries),
            memory_cards=tuple(selected_cards),
            task_context=tasks,
            capability_catalog=capabilities,
            token_budget=budget,
            estimated_tokens=used,
            truncated=truncated,
            dropped_sections=dict(dropped),
        )
