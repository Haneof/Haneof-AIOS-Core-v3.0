"""A budget trim must reach the model as a trim, not as amnesia.

``ModelContextBundle.dropped_sections`` records how many entries per section the
controller could not fit. ``truncated`` never reaches the prompt, so if the counts
never reach it either the model experiences a context cut as forgetting: it says "I
don't remember" about entries that are still in the world store, and neither the user
nor the audit trail can tell a retrieval failure from a budget trim.
"""

from __future__ import annotations

from aios_core.context.controller import ContextController
from aios_core.recommendation.proactive import MemoryCard, RecommendationBundle
from aios_core.runtime.cognitive_runtime import RuntimeSnapshot
from aios_core.runtime.grok_provider import (
    GrokProviderConfig,
    GrokStreamingProvider,
    TurnCompletion,
)

CATALOG = (
    {"name": "drill_down_conversation", "description": "read exact raw dialogue"},
    {"name": "list_conversation_summaries", "description": "list round summaries"},
    {"name": "search_world", "description": "search world objects"},
)


def _prompt(cockpit: dict, catalog: tuple = CATALOG) -> str:
    captured: list[str] = []

    def fake_stream_chat(messages, *, model=None, **kwargs):
        captured.append(messages[0]["content"])
        return "ok", [], None

    def fake_stream_chat_with_tools(messages, *, model=None, tools=None, **kwargs):
        captured.append(messages[0]["content"])
        return TurnCompletion(text="ok", usage=None, provenance=None, tool_calls=())  # type: ignore[arg-type]

    provider = GrokStreamingProvider(
        GrokProviderConfig(api_key="test-key", base_url="http://127.0.0.1:1/v1")
    )
    provider.stream_chat = fake_stream_chat  # type: ignore[method-assign]
    provider.stream_chat_with_tools = fake_stream_chat_with_tools  # type: ignore[method-assign]

    snapshot = RuntimeSnapshot(
        user_input="我们上次说到哪了？",
        wake_reason="user_explicit",
        cockpit=cockpit,
        capability_catalog=catalog,
        capability_history=(),
        round_index=0,
        remaining_tool_rounds=2,
    )
    try:
        provider.as_model_handler()(snapshot)
    except Exception:
        # Only the outbound prompt matters; the stub's usage payload is irrelevant.
        pass
    return captured[0]


def test_dropped_sections_are_rendered_as_a_budget_cut_with_a_recall_route() -> None:
    prompt = _prompt(
        {
            "dropped_sections": {"recent_turns": 4, "conversation_summaries": 2},
            "recent_turns": [
                {"turn_index": 9, "user": {"text": "良率掉到62了"}, "assistant": {"text": "先看失效分布"}}
            ],
        }
    )

    assert "CONTEXT TRIMMED THIS TURN" in prompt
    # 1. It was a budget cut, not forgetting and not fabrication.
    assert "budget cut, not missing memory" in prompt
    assert "not forgotten" in prompt
    # 2. Which kind of content, and how many entries.
    assert "recent_turns): 4" in prompt
    assert "conversation_summaries): 2" in prompt
    # 3. A registered capability that pulls it back — and only registered ones.
    assert "drill_down_conversation" in prompt
    assert "list_conversation_summaries" in prompt
    assert "search_conversation_summaries" not in prompt  # not in this catalog
    # No raw JSON dump: the model is told what happened, not handed a data structure.
    assert '{"recent_turns"' not in prompt
    # It must not tell the model it has no such memory.
    assert "do not remember" in prompt


def test_no_drops_renders_no_section() -> None:
    """An empty trim notice wastes tokens and destabilises the cacheable prefix."""

    prompt = _prompt({"dropped_sections": {}, "recent_turns": []})

    assert "CONTEXT TRIMMED" not in prompt


def test_trim_notice_stays_out_of_the_cacheable_prefix() -> None:
    """The static prefix ends with the capability catalogue; the notice is dynamic."""

    prompt = _prompt(
        {
            "dropped_sections": {"memory_cards": 3},
            "ai_identity": {"symbiotic_posture": "old_friend"},
            "recent_turns": [
                {"turn_index": 1, "user": {"text": "早上好"}, "assistant": {"text": "早"}}
            ],
        }
    )

    assert prompt.index("AVAILABLE CAPABILITIES") < prompt.index("CONTEXT TRIMMED")
    assert prompt.index("CONTINUITY ANCHOR") < prompt.index("CONTEXT TRIMMED")


def test_controller_produced_drops_reach_the_model() -> None:
    """End to end: a real over-budget assembly tells the model what it lost."""

    controller = ContextController()
    bundle = controller.assemble(
        user_input="继续",
        current_topic=None,
        recommendation=RecommendationBundle(
            world_revision=1,
            index_watermark=0,
            cards=(
                MemoryCard(
                    object_id="obs_1",
                    revision=1,
                    excerpt="供应链卡在东莞那家供应商",
                    object_type="observation",
                    dimension="dim_work",
                    retrieval_score=9,
                ),
            ),
            reason="test",
        ),
        recent_turns=[
            {"turn_index": i, "user": {"text": "第 %d 轮的一段话" % i}, "assistant": {"text": "嗯"}}
            for i in range(6)
        ],
        token_budget=200,
    )

    assert bundle.dropped_sections, "precondition: this assembly must actually trim"

    prompt = _prompt(bundle.as_cockpit())

    assert "CONTEXT TRIMMED THIS TURN" in prompt
    for key, count in bundle.dropped_sections.items():
        assert f"{key}): {count}" in prompt, f"{key} was dropped but the model is not told"
