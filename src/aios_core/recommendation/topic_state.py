"""Deterministic current-topic state for memory recommendation.

This layer is retrieval infrastructure, not user cognition. It only maintains enough
conversation continuity to decide whether a historical-memory lookup is mechanically
appropriate before the resident model runs.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict


class TopicState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    topic: str | None = None
    gate_open: bool = False
    history_may_help: bool = False
    reason: str
    continued_from_recent_turn: bool = False


_SOCIAL_ONLY = {
    "hi", "hello", "hey", "你好", "您好", "在吗", "早", "早上好", "晚上好",
    "谢谢", "感谢", "ok", "okay", "好的", "好", "嗯", "哈哈", "再见",
}
_CONTINUATION_CUES = (
    "继续", "接着", "刚才", "上面", "前面", "这个", "那个", "那这个", "那怎么办",
    "那怎么", "然后呢", "还有呢", "what about that", "continue", "go on",
)
_HISTORY_CUES = (
    "之前", "上次", "昨天", "前天", "最近", "过去", "以前", "去年", "前年", "历史",
    "还记得", "我们聊过", "继续", "again", "last time", "yesterday", "recently", "before",
)


def _clean(value: str | None) -> str:
    return "" if value is None else " ".join(value.strip().split())


def _recent_user_text(recent_turns: Sequence[Mapping[str, Any]]) -> str | None:
    for item in reversed(recent_turns):
        if str(item.get("role") or "").strip().lower() != "user":
            continue
        text = _clean(str(item.get("text") or ""))
        if text:
            return text
    return None


class TopicStateService:
    def resolve(
        self,
        *,
        user_input: str,
        recent_turns: Sequence[Mapping[str, Any]] = (),
        explicit_topic: str | None = None,
        structured_history_signal: bool = False,
        structured_signal_reason: str | None = None,
    ) -> TopicState:
        current = _clean(user_input)
        if not current:
            return TopicState(reason="blank_input")
        lower = current.lower()
        if lower in _SOCIAL_ONLY:
            return TopicState(reason="social_or_phatic_input")

        previous = _recent_user_text(recent_turns)
        continuation = any(cue in lower for cue in _CONTINUATION_CUES)
        explicit = _clean(explicit_topic)

        if continuation and previous:
            topic = previous
            reason = "continued_recent_user_topic"
            continued = True
        elif explicit and explicit != current:
            topic = explicit
            reason = "explicit_topic_hint"
            continued = False
        else:
            topic = current
            reason = "current_utterance_topic"
            continued = False

        history_cue = any(cue in lower for cue in _HISTORY_CUES)
        # A topic is not itself permission to inject history. Deterministic Core
        # opens proactive recall only on explicit historical/continuation signals
        # (or an explicit topic hint supplied by a trusted caller). The resident
        # model retains search_world for all other cases.
        history_may_help = (
            history_cue
            or continued
            or (bool(explicit) and explicit != current)
            or bool(structured_history_signal)
        )
        if structured_history_signal and structured_signal_reason:
            reason = f"{reason}:{structured_signal_reason.strip()}"
        return TopicState(
            topic=topic,
            gate_open=True,
            history_may_help=history_may_help,
            reason=reason if history_may_help else f"{reason}:history_not_needed",
            continued_from_recent_turn=continued,
        )
