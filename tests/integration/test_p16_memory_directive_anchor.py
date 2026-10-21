"""P16 第 3 层：「让你记住的那句话」必须能被解析回原句（hermetic）。

背景（本文件锁定的真实缺口）：
上下文耗尽后，用户问「我刚才让你记住的那句话里，我在哪个城市」。
这句话与 anchor 原文**没有任何实词重叠**（追问句实词是「城市/产品」，
anchor 实词是「杭州/手环」），所以：

- 词法检索永远找不回 anchor（旧实测：候选 score=1，并列最后）；
- 主题门 `history_may_help` 为 False（三张 ~20 词的表都不含这类表达）；
- 结果是 memory_cards=0，模型只能承认「不记得」。

修复思路不是扩词表，而是**换检索对象**：这句话指的不是内容，而是
「一次记忆动作」。所以按记忆动作（记住/记下/记一下）去查「谁下过这条指令」，
把那条用户原话作为有界候选交给模型判断。

本文件把以下契约固化：
1. 指代「让你记住的那句话」→ 能召回原句，且排在首位；
2. 记忆指令本身（「请记住这句话：X」）不得开启召回（否则每轮都灌历史）；
3. 当前这句话不得成为自己的候选（自引用）；
4. 世界里没有记忆指令时，不得凭空造出「记忆锚点」；
5. 普通问句仍然 0 卡片（宪法 2.2：无主题时推荐必须为空）；
6. 卡片数受推荐上限约束（宪法十四-3/4/8，不许每轮全量加载）。

全部 hermetic：进程内假 ModelHandler，无网络、无 API key。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aios_core.ingest.conversation import ConversationIngestor
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore

_NOW = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)

# anchor 里的独特标记：任何 filler 轮次都严禁出现，否则「耗尽后召回」是假阳性。
_ANCHOR_MARKER = "23cm 柔性屏手环"
_ANCHOR_TEXT = "我在杭州做一款 23cm 柔性屏手环，主打运动健康监测，续航 14 天。"
_DIRECTIVE_TEXT = f"请记住这句话：{_ANCHOR_TEXT}"
_RECALL_QUESTION = "我刚才让你记住的那句话里，我在哪个城市、做什么产品？"

_FILLERS = (
    "给我讲讲海底火山是怎么形成的。",
    "四季交替的成因是什么？",
    "水为什么会沸腾？",
    "天空为什么呈现蓝色？",
)

_MAX_RECOMMENDED_CARDS = 5


def _runtime(tmp_path, *, model, recent_turn_limit: int = 8) -> tuple[FusedTurnRuntime, SQLiteWorldStore, WorldSearchIndex]:
    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=model,
        subject_id="user_1",
        recent_turn_limit=recent_turn_limit,
    )
    return runtime, store, index


def _seed_prior_session(store: SQLiteWorldStore, index: WorldSearchIndex) -> None:
    """在 s1 里留下一句显式记忆指令，外加若干无关闲聊。"""

    ingest = ConversationIngestor(store)
    ingest.commit_turn(
        session_id="s1",
        turn_index=1,
        user_text=_DIRECTIVE_TEXT,
        assistant_text="好，我记住了。",
        occurred_at=_NOW,
    )
    for offset, filler in enumerate(_FILLERS, start=2):
        ingest.commit_turn(
            session_id="s1",
            turn_index=offset,
            user_text=filler,
            assistant_text="（回答）",
            occurred_at=_NOW,
        )
    index.rebuild()


def test_reference_to_memory_directive_resolves_to_the_original_sentence(tmp_path) -> None:
    """核心用例：跨会话（换 AI 接上）后仍能凭「让你记住」找回原句。"""

    seen: dict[str, object] = {}

    def model(snapshot):
        topic = snapshot.cockpit["task_context"]["topic_state"]
        cards = snapshot.cockpit["memory_cards"]
        seen["topic"] = topic
        seen["cards"] = cards
        return ModelDirective(response="你在杭州做 23cm 柔性屏手环。")

    runtime, store, index = _runtime(tmp_path, model=model)
    _seed_prior_session(store, index)

    result = runtime.run_turn(
        session_id="s2",
        turn_index=1,
        user_input=_RECALL_QUESTION,
        occurred_at=_NOW,
    )

    topic = seen["topic"]
    assert topic["memory_directive_reference"] is True
    assert topic["antecedent_recall_needed"] is True
    assert topic["history_may_help"] is True
    assert "memory_directive" in topic["reason"]

    cards = seen["cards"]
    assert cards, "记忆指代没有召回任何候选"
    assert cards[0]["match_reason"] == "explicit_memory_directive_anchor"
    assert _ANCHOR_MARKER in cards[0]["excerpt"]
    assert result.recommendation.reason.startswith("memory_directive_reference_resolved")
    # 宪法十四-3/4/8：单轮卡片数受推荐上限约束。
    assert len(cards) <= _MAX_RECOMMENDED_CARDS


def test_current_utterance_is_never_its_own_antecedent(tmp_path) -> None:
    """当前这句本身就含「记住」，但它不可能是自己的前指对象。"""

    seen: dict[str, object] = {}

    def model(snapshot):
        seen["cards"] = snapshot.cockpit["memory_cards"]
        return ModelDirective(response="你在杭州。")

    runtime, store, index = _runtime(tmp_path, model=model)
    _seed_prior_session(store, index)
    runtime.run_turn(
        session_id="s2",
        turn_index=1,
        user_input=_RECALL_QUESTION,
        occurred_at=_NOW,
    )

    excerpts = [card["excerpt"] for card in seen["cards"]]
    assert excerpts, "前置条件：本用例要求确实召回了候选"
    assert not any(_RECALL_QUESTION in excerpt for excerpt in excerpts)


def test_memory_directive_itself_does_not_open_recall(tmp_path) -> None:
    """下指令的那一轮不得开启召回 —— 否则每轮都会灌历史。"""

    seen: dict[str, object] = {}

    def model(snapshot):
        seen["topic"] = snapshot.cockpit["task_context"]["topic_state"]
        seen["cards"] = snapshot.cockpit["memory_cards"]
        return ModelDirective(response="好，我记住了。")

    runtime, store, index = _runtime(tmp_path, model=model)
    ingest = ConversationIngestor(store)
    ingest.commit_turn(
        session_id="s1",
        turn_index=1,
        user_text=_DIRECTIVE_TEXT,
        assistant_text="好，我记住了。",
        occurred_at=_NOW,
    )
    index.rebuild()

    runtime.run_turn(
        session_id="s1",
        turn_index=2,
        user_input=_DIRECTIVE_TEXT,
        occurred_at=_NOW,
    )

    assert seen["topic"]["memory_directive_reference"] is False
    assert seen["topic"]["history_may_help"] is False
    assert len(seen["cards"]) == 0


def test_plain_question_still_recommends_nothing(tmp_path) -> None:
    """宪法 2.2：没有历史指向性时推荐必须为空（0 条是正确结果）。"""

    seen: dict[str, object] = {}

    def model(snapshot):
        seen["cards"] = snapshot.cockpit["memory_cards"]
        return ModelDirective(response="因为瑞利散射。")

    runtime, store, index = _runtime(tmp_path, model=model)
    _seed_prior_session(store, index)
    runtime.run_turn(
        session_id="s2",
        turn_index=1,
        user_input="天空为什么呈现蓝色？",
        occurred_at=_NOW,
    )

    assert len(seen["cards"]) == 0


def test_no_fabricated_anchor_when_world_has_no_directive(tmp_path) -> None:
    """世界里没有记忆指令时，不得凭空产出「记忆锚点」。"""

    seen: dict[str, object] = {}

    def model(snapshot):
        seen["cards"] = snapshot.cockpit["memory_cards"]
        return ModelDirective(response="我不确定你指的是哪句话。")

    runtime, store, index = _runtime(tmp_path, model=model)
    ingest = ConversationIngestor(store)
    ingest.commit_turn(
        session_id="s1",
        turn_index=1,
        user_text="下周三我要去西雅图出差，早上 8 点的航班。",
        assistant_text="记下了。",
        occurred_at=_NOW,
    )
    index.rebuild()

    result = runtime.run_turn(
        session_id="s2",
        turn_index=1,
        user_input=_RECALL_QUESTION,
        occurred_at=_NOW,
    )

    assert not any(
        card["match_reason"] == "explicit_memory_directive_anchor"
        for card in seen["cards"]
    )
    # 门可以开（存在指代），但绝不能假装找到了记忆锚点。
    assert result.recommendation.reason != "memory_directive_reference_resolved"


@pytest.mark.parametrize(
    "utterance",
    [
        "我记住了",
        "记住安全第一",
        "请记住这句话：明天交材料。",
        "继续学习 Python",
    ],
)
def test_self_contained_utterances_do_not_claim_a_memory_reference(utterance: str) -> None:
    """组合判据：只有「记忆动作 + 前指」同时出现才算指代。"""

    from aios_core.recommendation.topic_state import TopicStateService

    state = TopicStateService().resolve(user_input=utterance, recent_turns=())
    assert state.memory_directive_reference is False
