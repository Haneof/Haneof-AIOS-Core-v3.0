"""Prompt-coverage guardrail: no cockpit field may be assembled and then dropped.

Why this file exists. The same defect has shipped twice:

1. ``9ce11baf`` found that ``recent_turns`` / ``memory_cards`` /
   ``conversation_summaries`` were lists, and the prompt builder kept only scalars,
   so all three were silently dropped. It fixed two of them.
2. ``26c9c481`` found ``ai_identity`` and ``conversation_summaries`` still missing.
3. This turn found ``world_map`` and ``task_context`` still missing.

Each time, the field that got fixed was the one somebody happened to look at. The
missing thing was never a patch; it was a guardrail. So instead of asserting a
particular rendering format, every field below is filled with a unique sentinel and
the test asserts the sentinel reached the outbound messages. A field that stops being
rendered fails here even if nobody thought to look at it.

``test_every_cockpit_field_is_accounted_for`` closes the other half of the hole: a new
field added to ``ModelContextBundle`` without a sentinel or a bookkeeping exemption
fails immediately, at the moment it is introduced rather than three turns later.
"""

from __future__ import annotations

import pytest

from aios_core.context.controller import ModelContextBundle
from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot
from aios_core.runtime.grok_provider import GrokProviderConfig, GrokStreamingProvider

# Fields that carry no meaning for the model and must stay out of the prompt: they are
# budget arithmetic for the controller, not context. Anything else in the cockpit is
# either rendered or is a bug.
BOOKKEEPING_FIELDS = frozenset({"token_budget", "estimated_tokens", "truncated"})

# One unique sentinel per field that must reach the model. The value is injected into
# the field's natural position so the renderer sees a realistic shape.
SENTINELS: dict[str, str] = {
    "user_input": "SENTINEL_user_input_9a1",
    "current_topic": "SENTINEL_current_topic_9a2",
    "ai_identity": "SENTINEL_ai_identity_9a3",
    "world_map": "SENTINEL_world_map_9a4",
    "recent_turns": "SENTINEL_recent_turns_9a5",
    "conversation_summaries": "SENTINEL_conversation_summaries_9a6",
    "memory_cards": "SENTINEL_memory_cards_9a7",
    "task_context": "SENTINEL_task_context_9a8",
    "capability_catalog": "SENTINEL_capability_catalog_9a9",
}


def _cockpit() -> dict:
    return {
        "user_input": SENTINELS["user_input"],
        "current_topic": SENTINELS["current_topic"],
        "ai_identity": {
            "relationship": [
                {
                    "domain": "relationship",
                    "dimension": "dim_rel",
                    "object_id": "clm_rel",
                    "revision": 1,
                    "statement": SENTINELS["ai_identity"],
                    "confidence": 0.9,
                }
            ],
            "symbiotic_posture": "old_friend",
            "ethical_invariants": ["keep it plain"],
        },
        "world_map": {
            "schema": "aios.world-map.l0.v1",
            "directory_only": True,
            "dimension_count": 1,
            "dimensions": [
                {
                    "dimension": SENTINELS["world_map"],
                    "current_object_count": 3,
                    "object_types": ["observation"],
                }
            ],
        },
        "recent_turns": [
            {
                "turn_index": 1,
                "user": {"text": SENTINELS["recent_turns"]},
                "assistant": {"text": "ack"},
            }
        ],
        "conversation_summaries": [
            {
                "turn_start": 1,
                "turn_end": 2,
                "content": SENTINELS["conversation_summaries"],
            }
        ],
        "memory_cards": [
            {
                "excerpt": SENTINELS["memory_cards"],
                "object_type": "observation",
                "dimension": "dim_rel",
            }
        ],
        "task_context": {
            "current_user_observation_ref": {
                "object_id": SENTINELS["task_context"],
                "revision": 1,
            },
            "conversation_continuity": {
                "session_id": "s1",
                "recent_turn_count": 1,
                "round_summary_count": 1,
                "summary_index_capability": "list_conversation_summaries",
                "summary_drill_down_capability": "drill_down_conversation",
            },
        },
        "capability_catalog": [
            {"name": SENTINELS["capability_catalog"], "description": "a capability"}
        ],
        "token_budget": 3400,
        "estimated_tokens": 120,
        "truncated": False,
    }


def _outbound_text(cockpit: dict) -> str:
    """Capture every message the provider would send, system and user alike."""

    captured: list[str] = []

    def fake_stream_chat(messages, *, model=None, **kwargs):
        captured.extend(message["content"] for message in messages)
        return "ok", [], None

    provider = GrokStreamingProvider(
        GrokProviderConfig(api_key="test-key", base_url="http://127.0.0.1:1/v1")
    )
    provider.stream_chat = fake_stream_chat  # type: ignore[method-assign]

    snapshot = RuntimeSnapshot(
        user_input=cockpit["user_input"],
        wake_reason="user_explicit",
        cockpit=cockpit,
        # capability_catalog travels on the snapshot as well as inside the cockpit.
        # The prompt builder reads the snapshot copy, so the guardrail mirrors what
        # TurnRuntime actually does rather than inventing a single-source contract.
        capability_catalog=tuple(cockpit["capability_catalog"]),
        capability_history=(),
        round_index=0,
        remaining_tool_rounds=2,
    )

    handler = provider.as_model_handler()
    try:
        handler(snapshot)
    except Exception:
        # Only the outbound payload matters; the stub's usage object is irrelevant.
        pass

    return "\n".join(captured)


@pytest.mark.parametrize("field", sorted(SENTINELS))
def test_cockpit_field_reaches_the_model(field: str) -> None:
    text = _outbound_text(_cockpit())
    sentinel = SENTINELS[field]
    assert sentinel in text, (
        f"cockpit field {field!r} was assembled but never reached the model. "
        "Either render it in the prompt builder, or declare it bookkeeping in "
        "BOOKKEEPING_FIELDS with a reason."
    )


def test_every_cockpit_field_is_accounted_for() -> None:
    """A new cockpit field must be rendered or explicitly exempted, not forgotten."""

    declared = set(SENTINELS) | set(BOOKKEEPING_FIELDS)
    actual = set(ModelContextBundle.model_fields)
    assert actual == declared, (
        "ModelContextBundle and the prompt-coverage guardrail disagree. "
        f"Unaccounted fields: {sorted(actual - declared)}; "
        f"stale entries: {sorted(declared - actual)}."
    )


def test_bookkeeping_fields_do_not_reach_the_prompt() -> None:
    """Budget arithmetic is not context; leaking it wastes the budget it describes."""

    text = _outbound_text(_cockpit())
    assert "estimated_tokens" not in text
    assert "token_budget" not in text


def test_absent_grounding_renders_nothing() -> None:
    """An empty task_context must not produce an empty, misleading section."""

    cockpit = _cockpit()
    cockpit["task_context"] = {}
    text = _outbound_text(cockpit)
    assert "THIS TURN — GROUNDING" not in text
