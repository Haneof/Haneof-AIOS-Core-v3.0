"""T2' 记忆抽取轮回归测试。

锁定 durable claim=0 的修复：主对话轮结束后，用独立的确定性抽取 pass
（``durable_fact_extractor``）落地 durable facts，不再依赖主模型「顺便」调用
``commit_ai_world_claim``。

覆盖：
1. extractor 被调用并收到本轮的 user_input + assistant_text。
2. 抽取到的 fact 被程序化落地（第二轮 continuity anchor 可见）。
3. extractor 返回空时不落地。
4. extractor 抛异常不阻断主对话轮，且错误被记录。
5. 未注入 extractor 时向后兼容。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot
from aios_core.runtime.grok_provider import (
    GrokProviderConfig,
    GrokStreamingProvider,
    TurnCompletion,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


class _PromptCapture:
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.provider = GrokStreamingProvider(
            GrokProviderConfig(api_key="test-key", base_url="http://127.0.0.1:1/v1")
        )
        self.provider.stream_chat = self._stream_chat  # type: ignore[method-assign]
        self.provider.stream_chat_with_tools = self._stream_chat_with_tools  # type: ignore[method-assign]

    def _stream_chat(self, messages, *, model=None, **kwargs):
        self.prompts.append(messages[0]["content"])
        return "ok", None, None

    def _stream_chat_with_tools(self, messages, *, model=None, tools=None, **kwargs):
        # Same stub as _stream_chat: capture the prompt, carry no usage/provenance
        # so the turn's metering replay is not exercised by this prompt test.
        self.prompts.append(messages[0]["content"])
        return TurnCompletion(text="ok", usage=None, provenance=None, tool_calls=())  # type: ignore[arg-type]

    @property
    def last(self) -> str:
        assert self.prompts, "no prompt captured"
        return self.prompts[-1]


def _reply_handler(_snapshot: RuntimeSnapshot) -> ModelDirective:
    return ModelDirective(response="好的，我记住了。")


def _make_runtime(tmp_path: Path, *, extractor=None) -> FusedTurnRuntime:
    store = SQLiteWorldStore(str(tmp_path / "world.sqlite"))
    index = WorldSearchIndex(str(tmp_path / "index.sqlite"), store=store)
    index.rebuild()
    return FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=_reply_handler,
        subject_id="user_1",
        recent_turn_limit=3,
        durable_fact_extractor=extractor,
    )


def test_extractor_receives_turn_and_persists_fact(tmp_path: Path) -> None:
    seen: dict = {}

    def extractor(user_input: str, assistant_text: str):
        seen["user_input"] = user_input
        seen["assistant_text"] = assistant_text
        return [
            {
                "domain": "user_understanding",
                "statement": "用户叫老王，做 23cm 柔性屏手环",
                "confidence": 0.95,
                "tags": ["core_context"],
            }
        ]

    runtime = _make_runtime(tmp_path, extractor=extractor)
    result = runtime.run_turn(
        session_id="s1",
        turn_index=1,
        user_input="我叫老王，做 23cm 柔性屏手环。",
        occurred_at=datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc),
    )

    assert seen["user_input"] == "我叫老王，做 23cm 柔性屏手环。"
    assert seen["assistant_text"] == "好的，我记住了。"
    assert result.extracted_durable_facts == (
        {
            "domain": "user_understanding",
            "statement": "用户叫老王，做 23cm 柔性屏手环",
            "confidence": 0.95,
            "tags": ["core_context"],
        },
    )
    assert result.durable_fact_extraction_error is None


def test_extracted_fact_appears_in_next_turn_anchor(tmp_path: Path) -> None:
    """第二轮 continuity anchor 必须能看到抽取轮落地的 fact。"""
    capture = _PromptCapture()

    def extractor(user_input: str, assistant_text: str):
        return [
            {
                "domain": "user_understanding",
                "statement": "用户叫老王",
                "confidence": 0.9,
                "tags": ["core_context"],
            }
        ]

    store = SQLiteWorldStore(str(tmp_path / "world.sqlite"))
    index = WorldSearchIndex(str(tmp_path / "index.sqlite"), store=store)
    index.rebuild()

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=capture.provider.as_model_handler(),
        subject_id="user_1",
        recent_turn_limit=3,
        durable_fact_extractor=extractor,
    )

    base = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
    runtime.run_turn(
        session_id="s_anchor",
        turn_index=1,
        user_input="我叫老王。",
        occurred_at=base,
    )
    runtime.run_turn(
        session_id="s_anchor",
        turn_index=2,
        user_input="今天天气怎么样？",
        occurred_at=base,
    )

    prompt = capture.last
    assert "CONTINUITY ANCHOR" in prompt
    assert "老王" in prompt


def test_empty_extraction_persists_nothing(tmp_path: Path) -> None:
    def extractor(user_input: str, assistant_text: str):
        return []

    runtime = _make_runtime(tmp_path, extractor=extractor)
    result = runtime.run_turn(
        session_id="s1",
        turn_index=1,
        user_input="今天天气怎么样？",
        occurred_at=datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc),
    )
    assert result.extracted_durable_facts == ()
    assert result.durable_fact_extraction_error is None


def test_extractor_error_does_not_break_turn(tmp_path: Path) -> None:
    def extractor(user_input: str, assistant_text: str):
        raise RuntimeError("upstream extraction failed")

    runtime = _make_runtime(tmp_path, extractor=extractor)
    result = runtime.run_turn(
        session_id="s1",
        turn_index=1,
        user_input="我叫老王。",
        occurred_at=datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc),
    )
    # 主对话轮照常返回，错误被记录而不是向上抛。
    assert result.runtime.response == "好的，我记住了。"
    assert result.extracted_durable_facts == ()
    assert result.durable_fact_extraction_error == "RuntimeError: upstream extraction failed"


def test_no_extractor_is_backward_compatible(tmp_path: Path) -> None:
    runtime = _make_runtime(tmp_path, extractor=None)
    result = runtime.run_turn(
        session_id="s1",
        turn_index=1,
        user_input="我叫老王。",
        occurred_at=datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc),
    )
    assert result.extracted_durable_facts == ()
    assert result.durable_fact_extraction_error is None
