"""Real-scale context budget guardrail.

Why this file exists. The controller budget used to be 3400 — a number with no owner,
no model behind it, and no constitution behind it. It never triggered because the
estimator counted CJK text at ``len(json)/4`` (0.25 token/char) while Chinese actually
costs ~0.636 token/char, a ~2.55x under-count. Two SQLite worlds therefore show
``truncated: true`` zero times, which is not "we never overflowed" but "the estimator
cannot see the cost". That is a false negative, and the moment the estimator is fixed
the same input jumps from ~2000 to ~5400 estimated tokens and starts dropping
``recent_turns`` / ``conversation_summaries`` / ``memory_cards`` — silently, because
``truncated`` is filtered out of the prompt by ``_COCKPIT_SCALAR_SKIP``.

These tests pin the two halves of that failure: real-scale Chinese context must survive
assembly intact, and when it genuinely cannot fit, the loss must be observable.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from aios_core.context.budget_policy import (
    DEFAULT_CONTEXT_BUDGET_POLICY,
    resolve_context_budget_policy,
)
from aios_core.context.controller import ContextController, estimate_tokens
from aios_core.recommendation.proactive import MemoryCard, RecommendationBundle

# ---------------------------------------------------------------------------
# Fixtures: a world snapshot shaped like a real one, in Chinese.
# ---------------------------------------------------------------------------

_BASE_ZH = (
    "用户谈到城西那套老房子下个月就要拆迁，父亲留下的那台蝴蝶牌缝纫机至今不知道该搬到哪里去。"
    "他说母亲当年在灯下踩着踏板做衣服的声音，是他记忆里最稳定的一段背景音，"
    "机器一响，整个屋子就像还有人在。"
    "助手回应说，这类物件承载的不是使用价值，而是一段连续的时间感，"
    "可以先把它的来历、经手的人、曾经存放的位置逐条记下来，再决定是否需要专门的空间安置。"
)


def _zh(target: int) -> str:
    """Build a natural-ish Chinese passage of at least ``target`` characters."""

    out = ""
    while len(out) < target:
        out += _BASE_ZH
    return out[:target]


def _recent_turn(count: int) -> dict[str, Any]:
    """One dialogue turn; user+assistant text together land in the 300~600 字 band."""

    index = count + 1
    user_len = 200 + 35 * count
    assistant_len = 110 + 18 * count
    return {
        "turn_index": index,
        "user": {"text": _zh(user_len) + f"（第{index}轮用户）"},
        "assistant": {"text": _zh(assistant_len) + f"（第{index}轮助手）"},
    }


def _summary(index: int) -> dict[str, Any]:
    return {
        "turn_start": 1 + index * 2,
        "turn_end": 2 + index * 2,
        "kind": "round_summary",
        "content": _zh(260 + 40 * index) + f"（摘要窗口{index}）",
    }


def _card(index: int) -> MemoryCard:
    return MemoryCard(
        object_id=f"obj_memory_{index}",
        revision=1,
        object_type="observation",
        dimension="dim_relationship",
        excerpt=_zh(180 + 30 * index) + f"（记忆卡{index}）",
        retrieval_score=90 - index,
        match_reason="current_topic_index_overlap",
    )


def _capability(name: str, description: str) -> dict[str, Any]:
    return {"name": name, "description": description}


def _snapshot() -> dict[str, Any]:
    """A realistic snapshot: 6 recent turns, 3 summaries, 5 memory cards."""

    recent_turns = [_recent_turn(i) for i in range(6)]
    conversation_summaries = [_summary(i) for i in range(3)]
    cards = tuple(_card(i) for i in range(5))

    return {
        "recent_turns": recent_turns,
        "conversation_summaries": conversation_summaries,
        "recommendation": RecommendationBundle(
            current_topic="老房子拆迁与遗物安置",
            topic_gate_open=True,
            world_revision=7,
            index_watermark=42,
            cards=cards,
            reason="current_topic_index_overlap",
        ),
        "ai_identity": {
            "symbiotic_posture": "old_friend",
            "relationship": [
                {
                    "domain": "relationship",
                    "dimension": "dim_relationship",
                    "object_id": "clm_rel_1",
                    "revision": 1,
                    "statement": "用户把助手当作可以长期托付记忆的老朋友",
                    "confidence": 0.9,
                }
            ],
            "ethical_invariants": ["说话要朴素", "不替用户做遗忘的决定"],
        },
        "world_map": {
            "schema": "aios.world-map.l0.v1",
            "directory_only": True,
            "dimension_count": 12,
            "dimensions": [
                {
                    "dimension": f"dim_{name}",
                    "current_object_count": 30 + i,
                    "object_types": ["observation", "claim"],
                }
                for i, name in enumerate(
                    ["relationship", "event", "preference", "habitat", "work"]
                )
            ],
        },
        "task_context": {
            "current_user_observation_ref": {"object_id": "obs_1", "revision": 1},
            "conversation_continuity": {
                "session_id": "sess_real_scale",
                "recent_turn_count": len(recent_turns),
                "round_summary_count": len(conversation_summaries),
                "summary_index_capability": "list_conversation_summaries",
                "summary_drill_down_capability": "drill_down_conversation",
            },
        },
        "capability_catalog": [
            _capability("read_world_state", "读取当前世界状态的目录与统计"),
            _capability("list_conversation_summaries", "列出同会话的轮次摘要索引"),
            _capability("drill_down_conversation", "按窗口下钻原始对话内容"),
            _capability("search_memory", "按主题检索长期记忆条目"),
            _capability("write_observation", "写入一条新的观察事实"),
            _capability("revise_claim", "对已有判断提出修正"),
            _capability("plan_tool_call", "规划一次外部工具调用"),
            _capability("summarize_round", "为当前轮次生成摘要"),
        ],
        "user_input": "那台缝纫机到底该怎么处理，我拿不定主意。",
        "current_topic": "老房子拆迁与遗物安置",
    }


def _assemble(**overrides: Any):
    snapshot = _snapshot()
    snapshot.update(overrides)
    controller = ContextController()
    bundle = controller.assemble(
        user_input=snapshot["user_input"],
        current_topic=snapshot["current_topic"],
        recommendation=snapshot["recommendation"],
        recent_turns=snapshot["recent_turns"],
        conversation_summaries=snapshot["conversation_summaries"],
        ai_identity=snapshot["ai_identity"],
        world_map=snapshot["world_map"],
        task_context=snapshot["task_context"],
        capability_catalog=snapshot["capability_catalog"],
        token_budget=snapshot.get("token_budget"),
    )
    return controller, snapshot, bundle


def _dropped_counts(bundle, snapshot) -> dict[str, int]:
    """Entries actually dropped per section, derived from what survived (zeros omitted)."""

    supplied: dict[str, Sequence[Mapping[str, Any]]] = {
        "recent_turns": snapshot["recent_turns"],
        "conversation_summaries": snapshot["conversation_summaries"],
        "memory_cards": snapshot["recommendation"].cards,
    }
    kept = {
        "recent_turns": bundle.recent_turns,
        "conversation_summaries": bundle.conversation_summaries,
        "memory_cards": bundle.memory_cards,
    }
    counts = {key: len(value) - len(kept[key]) for key, value in supplied.items()}
    return {key: count for key, count in counts.items() if count}


# ---------------------------------------------------------------------------
# 1. Real Chinese scale must not drop anything.
# ---------------------------------------------------------------------------


def test_real_scale_chinese_context_drops_nothing() -> None:
    """The core acceptance test: a real-sized Chinese world must fit intact."""

    controller, snapshot, bundle = _assemble()

    assert controller.default_token_budget == DEFAULT_CONTEXT_BUDGET_POLICY.context_token_budget
    # A budget that cannot hold ~5.4k tokens of real prompt is the 3400-class bug.
    assert controller.default_token_budget >= 8000

    assert len(bundle.recent_turns) == len(snapshot["recent_turns"]) == 6
    assert len(bundle.conversation_summaries) == 3
    assert len(bundle.memory_cards) == len(snapshot["recommendation"].cards) == 5

    assert bundle.truncated is False
    assert bundle.dropped_sections == {}
    assert bundle.estimated_tokens <= bundle.token_budget


def test_real_scale_turns_are_individually_sized() -> None:
    """Guard the fixture itself: turns really are 300~600 字, as production is."""

    for turn in _snapshot()["recent_turns"]:
        size = len(turn["user"]["text"]) + len(turn["assistant"]["text"])
        assert 300 <= size <= 600, f"fixture turn drifted to {size} chars"


# ---------------------------------------------------------------------------
# 2. Overflow must be observable, not silent.
# ---------------------------------------------------------------------------


def test_overflow_is_reported_per_section() -> None:
    """With a tiny budget, truncation must be visible and counted, not silent."""

    _, snapshot, bundle = _assemble(token_budget=400)

    assert bundle.truncated is True

    expected = _dropped_counts(bundle, snapshot)
    assert bundle.dropped_sections, "dropped_sections is empty: silent amnesia"
    assert bundle.dropped_sections == expected
    assert sum(bundle.dropped_sections.values()) > 0


def test_no_overflow_reports_no_drops() -> None:
    """A bundle that fits must report zero drops; the counter must not over-report."""

    _, snapshot, bundle = _assemble()

    assert bundle.dropped_sections == _dropped_counts(bundle, snapshot)
    assert bundle.dropped_sections == {}


# ---------------------------------------------------------------------------
# 3. The estimator must not under-count Chinese.
# ---------------------------------------------------------------------------


def _conservative_token_lower_bound(text: str) -> int:
    """Conservative floor for real token count: 0.6 token/char for CJK, 0.25 else.

    This is a deliberately conservative lower bound, not a tokenizer. It exists so the
    test fails loudly the moment the estimator falls back to something that treats a
    Chinese character as a quarter of a token.
    """

    cjk = 0
    for char in text:
        code = ord(char)
        if (
            0x3400 <= code <= 0x4DBF  # CJK Ext A
            or 0x4E00 <= code <= 0x9FFF  # CJK unified
            or 0xF900 <= code <= 0xFAFF  # compatibility ideographs
            or 0x3000 <= code <= 0x303F  # CJK punctuation
            or 0xFF00 <= code <= 0xFFEF  # fullwidth forms
        ):
            cjk += 1
    other = len(text) - cjk
    return int(cjk * 0.6 + other * 0.25)


def test_estimator_does_not_undercount_chinese() -> None:
    """estimate_tokens must clear the conservative floor for Chinese text."""

    sample = _zh(600)
    floor = _conservative_token_lower_bound(sample)
    assert estimate_tokens(sample) >= floor, (
        f"estimate_tokens under-counts Chinese: {estimate_tokens(sample)} < {floor} "
        "for 600 chars. A quarter-token-per-char estimator is the 2.55x blind spot."
    )


def test_estimator_does_not_undercount_assembled_sections() -> None:
    """The same floor applied to the shapes the controller actually measures."""

    for turn in _snapshot()["recent_turns"]:
        text = turn["user"]["text"] + turn["assistant"]["text"]
        floor = _conservative_token_lower_bound(text)
        assert estimate_tokens(turn) >= floor, (
            f"a real dialogue turn is estimated at {estimate_tokens(turn)} tokens, "
            f"below the conservative floor of {floor}"
        )


# ---------------------------------------------------------------------------
# Contract: the estimator must stay importable from controller (legacy import path).
# ---------------------------------------------------------------------------


def test_estimate_tokens_still_reexported_from_controller() -> None:
    """Old imports must survive the move to aios_core.context.tokenization."""

    from aios_core.context import estimate_tokens as package_estimate_tokens
    from aios_core.context.controller import estimate_tokens as controller_estimate_tokens

    assert controller_estimate_tokens is estimate_tokens
    assert package_estimate_tokens is estimate_tokens
    assert estimate_tokens("中文测试") >= 1


def test_policy_env_override_and_invalid_fallback(monkeypatch) -> None:
    """Explicit/env overrides apply; junk is ignored, never shrinks a budget."""

    monkeypatch.setenv("AIOS_BUDGET_CONTEXT_TOKEN_BUDGET", "48000")
    monkeypatch.setenv("AIOS_BUDGET_MODEL_OUTPUT_TOKENS", "not-a-number")
    monkeypatch.setenv("AIOS_BUDGET_ACTIVE_WINDOW_TOKEN_BUDGET", "-5")

    policy = resolve_context_budget_policy()
    assert policy.context_token_budget == 48000
    assert policy.model_output_tokens == DEFAULT_CONTEXT_BUDGET_POLICY.model_output_tokens
    assert policy.active_window_token_budget == (
        DEFAULT_CONTEXT_BUDGET_POLICY.active_window_token_budget
    )
    assert resolve_context_budget_policy(context_token_budget=9000).context_token_budget == 9000
