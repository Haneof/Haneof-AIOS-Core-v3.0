"""The shared constitutional prefix every task prompt must carry.

Separating prompts by contract risks one thing: six prompts drifting into six
different personas — a summarizer that chatters, a cleaner that hedges. This
prefix is the antidote. It is prepended to every task body and no task may
override it (``PromptSpec.requires_constitutional_prefix`` defaults to True and
``render`` raises when the prefix is missing).

It states only what is true for *every* job: who this is, what language to use,
that fabrication is forbidden, and that conclusions must point at evidence.
Task-specific rules belong in the task body, never here.
"""

from __future__ import annotations

CONSTITUTIONAL_PREFIX_VERSION = "v1"

CONSTITUTIONAL_PREFIX = """你是 AIOS 3.0 —— 运行在超紧凑可穿戴设备上的共生认知体。

【不变量 · 适用于你执行的每一个任务】
1. 语言：用户用简体中文，你就用简体中文输出，包括总结、判断理由和写入世界的陈述。
   标识符、字段名、JSON 的键保持英文。
2. 不得编造：只陈述输入中实际存在的内容。输入里没有的，就是"没发生"。
   不许为了回答完整而补充不存在的细节，不许把猜测写成事实。
3. "不知道"是合法状态：证据不足时明确说不知道，不要用模糊表述掩盖缺失。
4. 证据优先于印象：任何结论都要能指向输入里的具体条目（记录 id / object_id）。
   引用用 {object_id, revision} 形式的引用，不复制粘贴大段原文替代引用。
5. 你只负责本任务声明的那件事。不做本任务之外的判断，不替其他环节下结论，
   不输出本任务契约之外的额外内容。

【输出纪律】
- 严格按本任务要求的格式输出，不要解释你的推理过程，不要加开场白或结束语。
- 不得在输出里对用户说话、提问、寒暄或给出建议——除非本任务就是对话任务。
"""

CONSTITUTIONAL_PREFIX_LINES: tuple[str, ...] = tuple(
    line for line in CONSTITUTIONAL_PREFIX.strip().splitlines() if line.strip()
)


def constitutional_prefix(version: str | None = None) -> str:
    """Return the prefix. Versioned so a change is a deliberate, traceable act."""

    chosen = version or CONSTITUTIONAL_PREFIX_VERSION
    if chosen != CONSTITUTIONAL_PREFIX_VERSION:
        raise ValueError(
            f"unknown constitutional prefix version: {chosen} "
            f"(known: {CONSTITUTIONAL_PREFIX_VERSION})"
        )
    return CONSTITUTIONAL_PREFIX.strip()


CONSTITUTIONAL_PREFIX_VERSIONS: tuple[str, ...] = (CONSTITUTIONAL_PREFIX_VERSION,)


def is_constitutional_prefix(text: str) -> bool:
    """True when ``text`` is exactly one of the published prefixes.

    Why equality and not "contains the marker". A string that carries the marker
    *plus a paragraph of its own rules* passes a marker test and still ships a
    different persona. The prefix is the one thing a task may not edit, so the
    only acceptable values are the published ones — checked by identity, and
    version-aware so a future v2 is accepted without weakening v1.
    """

    stripped = (text or "").strip()
    return any(
        stripped == constitutional_prefix(version)
        for version in CONSTITUTIONAL_PREFIX_VERSIONS
    )


def assert_prefix_present(prompt: str) -> None:
    """Guardrail helper: a rendered prompt must carry the invariant block."""

    marker = "【不变量 · 适用于你执行的每一个任务】"
    if marker not in prompt:
        raise ValueError(
            "rendered prompt is missing the constitutional prefix; every task "
            "prompt must carry it so separated tasks keep one persona"
        )
