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
    antecedent_recall_needed: bool = False


_SOCIAL_ONLY = {
    "hi", "hello", "hey", "你好", "您好", "在吗", "早", "早上好", "晚上好",
    "谢谢", "感谢", "ok", "okay", "好的", "好", "嗯", "哈哈", "再见",
}
_CONTINUATION_CUES = (
    "继续", "接着", "刚才", "上面", "前面", "那怎么办", "那怎么",
    "然后呢", "还有呢", "what about that", "continue", "go on",
)
# Bare demonstratives are useful for same-session continuity, where the recent turn is
# already present in the cockpit, but are too weak to justify opening cross-session
# recall on their own. In particular, a demonstrative embedded in a locally specified
# noun phrase ("这个偏好", "那个方案") is not mechanical evidence of missing history.
_BARE_REFERENCE_CUES = ("这个", "那个", "那这个")
_TRAILING_DISCOURSE_PUNCTUATION = " \t\r\n,.!?;:，。！？；："
_HISTORY_CUES = (
    "之前", "上次", "昨天", "前天", "最近", "过去", "以前", "去年", "前年", "历史",
    "还记得", "我们聊过", "again", "last time", "yesterday", "recently", "before",
)

# Surface deixis/ellipsis only. These cues do not identify an antecedent; they merely
# indicate that the current utterance may depend on context not present in this session.
# The runtime may then expose a bounded candidate set for the resident model to resolve.
_DEICTIC_CUES = (
    "那天", "那次", "那个时候", "那件事", "那趟", "那场", "那个安排", "那个计划", "当时",
    "that day", "that time", "that trip", "that meeting", "that event", "that plan",
    "the other day", "back then",
)


def _clean(value: str | None) -> str:
    return "" if value is None else " ".join(value.strip().split())


def _recent_user_text(recent_turns: Sequence[Mapping[str, Any]]) -> str | None:
    for item in reversed(recent_turns):
        # P14 canonical continuity exposes one turn as
        # {"turn_index": ..., "user": {"text": ...}, "assistant": {...}}.
        # Accept that durable shape first and read only the user side.
        canonical_user = item.get("user")
        if isinstance(canonical_user, Mapping):
            text = _clean(str(canonical_user.get("text") or ""))
            if text:
                return text

        # Keep the direct role/text shape for TopicState's small deterministic API
        # and existing callers/tests. Assistant rows are never antecedent sources.
        if str(item.get("role") or "").strip().lower() != "user":
            continue
        text = _clean(str(item.get("text") or ""))
        if text:
            return text
    return None


def _strip_trailing_discourse_punctuation(value: str) -> str:
    return value.rstrip(_TRAILING_DISCOURSE_PUNCTUATION)


def _has_discourse_continuation_cue(value: str) -> bool:
    """Detect a discourse-level continuation request without substring inference.

    The gate intentionally recognizes only cues that stand at the end of the current
    utterance after punctuation is removed. This keeps deterministic Core from
    treating ordinary self-contained clauses such as "继续学习 Python" as evidence
    that hidden history is required. It still does not resolve any antecedent.
    """

    surface = _strip_trailing_discourse_punctuation(value)
    return any(surface == cue or surface.endswith(cue) for cue in _CONTINUATION_CUES)


def _has_same_session_continuation_cue(value: str) -> bool:
    """Recognize local continuity without turning arbitrary substrings into recall."""

    surface = _strip_trailing_discourse_punctuation(value).lstrip()
    return _has_discourse_continuation_cue(surface) or any(
        surface.startswith(cue) for cue in _BARE_REFERENCE_CUES
    )


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
        # Same-session continuity already has a bounded, canonical recent user turn
        # in the cockpit, but even there an arbitrary substring is not enough to
        # replace the current topic with history. A discourse-level continuation or
        # a leading demonstrative can expose the recent turn without resolving it.
        same_session_continuation_cue = _has_same_session_continuation_cue(lower)
        cross_session_continuation_cue = _has_discourse_continuation_cue(lower)
        deictic_cue = any(cue in lower for cue in _DEICTIC_CUES)
        explicit = _clean(explicit_topic)

        continued = bool(previous and same_session_continuation_cue)
        # A discourse-level continuation/deictic surface cue with no same-session
        # antecedent is not evidence of what the user means. It is only a mechanical
        # reason to expose a small, auditable cross-session candidate set.
        antecedent_recall_needed = bool(
            deictic_cue
            or (cross_session_continuation_cue and previous is None)
        )

        if continued:
            topic = previous
            reason = "continued_recent_user_topic"
        elif explicit and explicit != current:
            topic = explicit
            reason = "explicit_topic_hint"
        else:
            topic = current
            reason = "current_utterance_topic"

        history_cue = any(cue in lower for cue in _HISTORY_CUES)
        # A topic is not itself permission to inject history. Deterministic Core
        # opens proactive recall only on explicit historical/continuation signals
        # (or an explicit topic hint supplied by a trusted caller). The resident
        # model retains search_world for all other cases.
        history_may_help = (
            history_cue
            or continued
            or antecedent_recall_needed
            or (bool(explicit) and explicit != current)
            or bool(structured_history_signal)
        )
        if antecedent_recall_needed:
            reason = f"{reason}:antecedent_candidate_recall"
        if structured_history_signal and structured_signal_reason:
            reason = f"{reason}:{structured_signal_reason.strip()}"
        return TopicState(
            topic=topic,
            gate_open=True,
            history_may_help=history_may_help,
            reason=reason if history_may_help else f"{reason}:history_not_needed",
            continued_from_recent_turn=continued,
            antecedent_recall_needed=antecedent_recall_needed,
        )
