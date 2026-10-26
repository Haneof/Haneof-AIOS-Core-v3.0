"""Single source of truth for AIOS context and output token budgets.

Why this module exists. ``ContextController(default_token_budget=3400)`` carried a
number that is neither a model limit, nor a constitutional rule, nor a hardware
constraint: it was invented once and only ever left a trace in a governance receipt
(``governance/CORE_SCALE_001_INTEGRATION_RECEIPT_2026-09-24.md``, "2095/2102/2105 <=
3400"). Budgets scattered across modules fight each other, and a budget nobody can
trace is a budget nobody can change safely. Everything that bounds context or output
resolves through this module instead.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from typing import Any

#: Environment overrides are spelled ``AIOS_BUDGET_`` + the field name, uppercased.
ENV_PREFIX = "AIOS_BUDGET_"


@dataclass(frozen=True)
class ContextBudgetPolicy:
    """AIOS 上下文/输出 token 上限的唯一真源。分散散落各处会造成预算互相打架。

    ``context_token_budget = 32000`` 的选择理由（真实 API，差分斜率法实测）：

    * 当前单轮首调 prompt 已经约 5351 tokens（能力目录 ~2900 占 54%、宪法/规则 ~1300
      占 24%、动态世界状态 ~1100 占 21%）；
    * 工具续接轮平均 9320 tokens，峰值 22694 tokens。

    32000 对峰值给出约 6 倍余量，同时仅为 1M 上下文窗口的 3%。本项目已实现 prompt
    prefix 缓存（实测 NVIDIA / MiniMax 上第二次调用 ``cached_tokens`` 为 3712 /
    3786，命中率 98%），静态部分（能力目录、宪法/规则）的边际成本与延迟几乎不计。

    因此"保留预算"这件事仍然有必要——成本、首字延迟、以及 lost-in-the-middle 噪音都
    随上下文增长而恶化——但 3400 是错误量级：一旦 token 估算器修准（中文真实约
    0.636 token/字符，旧的 ``len(json)/4`` 只给 0.25，低估约 2.55 倍），同样这份输入
    的估算值会从约 2000 跳到约 5400，立刻越过 3400，controller 将开始静默丢弃
    ``recent_turns`` / ``conversation_summaries`` / ``memory_cards``。而 ``truncated``
    被 ``runtime/grok_provider.py`` 的 ``_COCKPIT_SCALAR_SKIP`` 排除在 prompt 之外，
    模型看不到自己的记忆被裁掉，表现为不可解释的"突然失忆"。32000 就是为了让修准后
    的真实规模有处可站。
    """

    context_token_budget: int = 32000  # ContextController 装配预算
    context_min_token_budget: int = 128
    active_window_token_budget: int = 1500  # ActiveRollingWindow
    active_window_max_turns: int = 6
    model_output_tokens: int = 4096  # 单次模型输出上限
    resilient_text_output_tokens: int = 2048  # 降级纯文本通道输出上限
    capability_injection_tokens: int = 6000  # grok_provider 能力/世界卡注入软上限
    recent_turn_injection_tokens: int = 2000  # 近期对话注入软上限
    memory_injection_tokens: int = 1800  # 记忆卡注入软上限
    narrative_context_tokens: int = 500  # topic_associator / turn_runtime 叙事预算


DEFAULT_CONTEXT_BUDGET_POLICY = ContextBudgetPolicy()


def _positive_int(raw: Any) -> int | None:
    """Coerce to a positive int, or None when absent / non-numeric / non-positive."""

    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def resolve_context_budget_policy(
    context_token_budget: int | None = None,
    context_min_token_budget: int | None = None,
    active_window_token_budget: int | None = None,
    active_window_max_turns: int | None = None,
    model_output_tokens: int | None = None,
    resilient_text_output_tokens: int | None = None,
    capability_injection_tokens: int | None = None,
    recent_turn_injection_tokens: int | None = None,
    memory_injection_tokens: int | None = None,
    narrative_context_tokens: int | None = None,
) -> ContextBudgetPolicy:
    """Resolve the policy: explicit argument, then environment, then default.

    Environment variables are named ``AIOS_BUDGET_`` + the field name uppercased, e.g.
    ``AIOS_BUDGET_CONTEXT_TOKEN_BUDGET``, ``AIOS_BUDGET_MODEL_OUTPUT_TOKENS``,
    ``AIOS_BUDGET_ACTIVE_WINDOW_TOKEN_BUDGET``. Anything illegal or non-positive is
    ignored and falls back to the next source, so a stray export can never shrink or
    blow up a budget into an unusable value.
    """

    explicit: dict[str, Any] = {
        "context_token_budget": context_token_budget,
        "context_min_token_budget": context_min_token_budget,
        "active_window_token_budget": active_window_token_budget,
        "active_window_max_turns": active_window_max_turns,
        "model_output_tokens": model_output_tokens,
        "resilient_text_output_tokens": resilient_text_output_tokens,
        "capability_injection_tokens": capability_injection_tokens,
        "recent_turn_injection_tokens": recent_turn_injection_tokens,
        "memory_injection_tokens": memory_injection_tokens,
        "narrative_context_tokens": narrative_context_tokens,
    }

    resolved: dict[str, int] = {}
    for field in fields(ContextBudgetPolicy):
        value = _positive_int(explicit.get(field.name))
        if value is None:
            value = _positive_int(os.environ.get(ENV_PREFIX + field.name.upper()))
        if value is None:
            value = getattr(DEFAULT_CONTEXT_BUDGET_POLICY, field.name)
        resolved[field.name] = value

    return ContextBudgetPolicy(**resolved)
