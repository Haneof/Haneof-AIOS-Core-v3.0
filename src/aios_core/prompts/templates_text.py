"""Text-output task templates: SUMMARIZE, DIGEST and DIALOGUE.

Three of the six task kinds answer in natural language rather than structured
labels, so they share one risk that the structured jobs do not have: *length*.
Everything below is shaped by failures we measured on real hardware, not by
style preference.

Why the length caps are hard numbers in the prompt body
------------------------------------------------------
A reasoning model spends its ``max_tokens`` budget on thinking before it emits
the first visible character. When the budget is too tight the call returns
``finish_reason=length`` with an empty body — the most expensive way to fail,
because nothing downstream can tell "empty summary" apart from "no data".
Measured on single-dimension summarization: 2500 output tokens is the sweet
spot (a couple hundred Chinese characters of prose, comfortably), while 8000
trips the gateway into a 504. Cross-dimension digesting is heavier and settles
at 4000; at 2500 it returned empty, at 8000 it timed out. So each template
declares a *character* ceiling that keeps its runtime budget in the safe band,
and states it in the prompt instead of trusting the model to be brief.

Why SUMMARIZE insists the sources are lower-scale summaries
-----------------------------------------------------------
Summarization used to re-read raw observations at every level. A one-week
``heart_rate`` summary pulled 881 sources / 52,095 characters (~26k tokens) for
what should have been seven day summaries. That is both a cost bug and a
quality bug: the model drowns in raw events and writes a worse summary than it
would from the day conclusions. The rule this enforces is "every level reads
only the finished product of the level below it" — DAY reads raw records, WEEK
and above read lower-scale summaries. The prompt therefore tells the model what
kind of text it is holding, and tells it not to re-derive raw detail from it.
When raw observations leak in anyway (a level below failed, say), the template
asks for consolidation only, never a second pass of extraction — re-extracting
from raw at the wrong layer is how the 26k-token window came back.

Everything else each task needs — dimension profile, time window, tool catalog —
arrives as ``PromptRenderParams``. The shared persona lives in the
constitutional prefix and is never restated here.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .contracts import (
    DimensionProfile,
    PromptRenderParams,
    PromptSpec,
    TaskKind,
    render_sources,
    untrusted_block,
)

# Output markers the caller pattern-matches on. Declared once so a template and
# its consumer cannot drift apart.
EMPTY_MARKER = "<AIOS_EMPTY>"
SILENCE_MARKER = "<AIOS_SILENCE>"


def _granularity_label(granularity: str) -> str:
    """Human-readable Chinese label for one window scale."""

    labels = {
        "day": "今日",
        "week": "本周",
        "month": "本月",
        "quarter": "本季度",
        "half_year": "本半年",
        "year": "本年度",
        # "multi_year" is what the summaries layer actually emits for the
        # open-ended multi-year scale; without it the raw English key leaks
        # into a Chinese prompt.
        "multi_year": "近多年",
        "multi_year_3y": "近三年",
        "multi_year_5y": "近五年",
        "decade": "近十年",
    }
    return labels.get(granularity, granularity)


def _digest_title(granularity: str) -> str:
    """Headline wording for a cross-dimension digest.

    day/week/month get idiomatic Chinese; every other scale uses the generic
    "{scale}总览" form so adding a scale never needs a wording decision.
    """

    titles = {
        "day": "今日总览",
        "week": "本周总览",
        "month": "本月总览",
        "quarter": "季度总览",
        "half_year": "半年总览",
        "year": "年度总览",
        "multi_year_3y": "三年总览",
        "multi_year_5y": "五年总览",
        "decade": "十年总览",
    }
    return titles.get(granularity, f"{granularity}总览")


def _summary_length(granularity: str) -> int:
    """Character ceiling for a single-dimension summary at this scale."""

    # day windows carry a handful of records and must stay glanceable on a
    # 23cm band screen; weekly/monthly need room for a few themes; anything
    # longer needs the most room but is capped all the same.
    lengths = {
        "day": 220,
        "week": 300,
        "month": 300,
        "quarter": 400,
        "half_year": 400,
        "year": 400,
        "multi_year_3y": 400,
        "multi_year_5y": 400,
        "decade": 400,
    }
    return lengths.get(granularity, 400)


def _digest_length(granularity: str) -> int:
    """Character ceiling for a cross-dimension digest at this scale."""

    return 300 if granularity == "day" else 400


def _window_line(params: PromptRenderParams) -> str:
    if params.window_start and params.window_end:
        return f"时间窗口：{params.window_start} ~ {params.window_end}"
    if params.window_start:
        return f"时间窗口：{params.window_start} 起"
    if params.window_end:
        return f"时间窗口：截至 {params.window_end}"
    return "时间窗口：未给出"


def _sources_block(sources: Sequence[Mapping[str, Any]]) -> str:
    rendered = render_sources(sources).strip()
    return rendered if rendered else "（源列表为空）"


def _json_block(value: Any) -> str:
    """Render arbitrary caller-supplied structure for the prompt. Never raises."""

    try:
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except (TypeError, ValueError):
        return str(value)


def _schema_argument_names(schema: Any) -> list[str]:
    """Pull parameter names out of whatever the catalog calls a schema.

    The catalog is caller-shaped, so accept both flat ``{name: type}`` maps and
    JSON-Schema objects. Only *names* come out: that is the whole point, see
    ``DialoguePrompt``'s docstring.
    """

    if isinstance(schema, Mapping):
        properties = schema.get("properties")
        if isinstance(properties, Mapping) and properties:
            return [str(name) for name in properties]
        return [str(name) for name in schema]
    if isinstance(schema, Sequence) and not isinstance(schema, str):
        # A bare list of names is still better than nothing.
        return [str(name) for name in schema]
    return []


def _render_capabilities(catalog: Any) -> str:
    """Render the callable-tool list with parameter names visible.

    Listing a tool's name without its parameters was measured to make the model
    invent argument names, and the call then gets rejected by the dispatcher —
    a failure that costs a full round-trip and reads to the user as silence.
    """

    lines: list[str] = []
    for capability in catalog:
        if not isinstance(capability, Mapping):
            lines.append(f"- {capability}")
            continue
        name = str(capability.get("name") or "").strip()
        if not name:
            continue
        description = str(capability.get("description") or "").strip()
        lines.append(f"- {name}：{description}" if description else f"- {name}")
        arguments = _schema_argument_names(capability.get("input_schema"))
        lines.append(f"  参数：{', '.join(arguments)}" if arguments else "  参数：无")
    return "\n".join(lines)


class SummarizePrompt(PromptSpec):
    """Describe one dimension over one time window. Output: one Chinese paragraph.

    Reads ``params.sources`` (lower-scale material for this dimension), the
    dimension profile, the granularity and the window. See the module docstring
    for why the character ceiling is stated inside the prompt and why anything
    above ``day`` is expected to read summaries rather than raw records.
    """

    task = TaskKind.SUMMARIZE
    # Not just "text": the empty-window branch requires a sentinel, and the
    # caller branches on it. A contract that says only "text" cannot tell a
    # shortened summary apart from a dropped one.
    output_contract = "text|EMPTY_MARKER"

    def body(self, params: PromptRenderParams) -> str:
        granularity = params.granularity or "day"
        label = _granularity_label(granularity)
        length = _summary_length(granularity)
        dimension_block = (
            params.dimension.as_prompt_block()
            if params.dimension is not None
            else "维度：未给出"
        )

        # An empty window still has to produce a prompt: the caller skips these
        # windows upstream, but a template that throws would take the whole
        # batch down with it, and the marker below keeps "nothing happened"
        # distinguishable from "the model said nothing".
        if not params.sources:
            return "\n".join(
                [
                    "【任务】单维度单尺度总结（SUMMARIZE）",
                    "",
                    "【本次契约】",
                    dimension_block,
                    f"时间尺度：{granularity}（{label}）",
                    _window_line(params),
                    "",
                    "【输入源】本次窗口内该维度没有任何源内容。",
                    "",
                    "【输出】不要试图总结、不要寒暄、不要解释原因。",
                    f"只输出一行空标记：{EMPTY_MARKER}",
                ]
            )

        source_note = ""
        if granularity != "day":
            # The whole point of the layering fix; see module docstring.
            source_note = "\n".join(
                [
                    "",
                    "【源的性质 · 必读】",
                    f"本次尺度是 {granularity}（{label}），不是 day。你读到的源应当是下一级"
                    "（day 级或更低尺度）的总结，而不是原始观测记录：",
                    "- 把它们当成别人已经做好的总结来读。不要把它们当成原始记录，",
                    "  不要试图从中还原原始细节，也不要因为源里缺少细节就去补写细节。",
                    "- 如果发现源里混入了大量原始观测（逐条流水、事件明细、重复片段），",
                    "  不要对它们做二次提炼：只做整合与去重，原样继承其中的事实即可。",
                    "  （AIOS 的分层原则是：每一级只读下一级的成品——day 读原始，",
                    "  week 及以上读下级总结。把原始观测再提炼一遍是越级，不是更认真。）",
                ]
            )

        return "\n".join(
            [
                "【任务】单维度单尺度总结（SUMMARIZE）",
                "",
                "【本次契约】",
                dimension_block,
                f"时间尺度：{granularity}（{label}）",
                _window_line(params),
                f"输出：一段中文描述性总结正文，不超过 {length} 字。",
                "",
                "【你要做的事】",
                "提炼这个窗口内这个维度值得记住的事实。",
                "按时间顺序或按主题组织都可以，选择更能讲清楚的一种。",
                "每条尽量回扣源里的关键词（原文用词、人名、数字、地点），让读者能对得上。",
                "它们不必面面俱到：同一件事反复出现写一次，信息量低的略过。",
            ]
            + ([source_note] if source_note else [])
            + [
                "",
                "【不要】",
                "- 不要编造源里没有的内容；不要把客套话、寒暄、表态、无信息的流水当成事实写进去。",
                "- 不要输出标题、小标题、 numbered 列表符号或 Markdown 标记——只输出正文。",
                "- 不要写“以下是总结”“总的来说”这类开场白，不要向用户说话或提问。",
                "- 不要因为没写满字数而凑够长度；没有值得记住的事就写得更短。",
                "",
                "【输入源】",
                _sources_block(params.sources),
            ]
        )


class DigestPrompt(PromptSpec):
    """Merge lower-scale per-dimension summaries into one cross-dimension view.

    This is the level where isolated dimension summaries ("I ran", "meeting
    moved") become a picture of a period of someone's life. It consumes what the
    other tasks produce and nothing else — see the module docstring for the
    measured reason it must not reach for raw records, and for why this template
    is budgeted more generously than SUMMARIZE.
    """

    task = TaskKind.DIGEST
    output_contract = "text"

    def body(self, params: PromptRenderParams) -> str:
        granularity = params.granularity or "day"
        title = _digest_title(granularity)
        length = _digest_length(granularity)

        return "\n".join(
            [
                "【任务】跨维度总览（DIGEST）",
                "",
                "【本次契约】",
                f"产出形态：{title}",
                f"时间尺度：{granularity}",
                _window_line(params),
                f"输出：一段中文跨维度全貌正文，不超过 {length} 字。",
                "",
                "【输入源】",
                _sources_block(params.sources),
                "",
                "【源的性质 · 必读】",
                "源是各个维度已经做好的总结（每条前缀里的括号标出了它来自哪个维度），",
                "不是原始记录。不要再去翻更细的东西，也不要假设原始细节存在。",
                "",
                "【你要做的事】",
                f"把这个窗口跨维度发生过什么，整合成一条能看懂的{title}。",
                "按时间线或按主题来组织都可以：多个维度在同一天指向同一件事时，并到一处写。",
                "保留关键的人名、承诺和数字——这些是全貌里唯一不可替换的部分。",
                "只在源之间建立联系：同一事件的多个侧面、先后发生的因果顺序（先后不是因果）。",
                "",
                "【不要】",
                "- 不要重复罗列各维度的原文，不要把每个维度各写一句拼成清单；要织成一条时间线。",
                "- 不要推测源里没有的原因、动机、趋势或情感，不要写“可能是因为”“说明他最近”。",
                "- 不要编造事件，不要用常识去填补源之间的空白。",
                "- 不要输出标题或 Markdown 标记，只输出正文；不要向用户说话或提问。",
                "- 不要为了凑长度重复同一件事；证据不足就如实写得更短。",
            ]
        )


class DialoguePrompt(PromptSpec):
    """Talk to the user, optionally emitting one tool call. Output: prose + calls.

    This template carries the lightest algorithmic load and the heaviest
    product load of the six: it is what the user experiences. Two things it
    deliberately does *not* do matter more than anything it does.

    It does not clean data and it does not summarize dimensions. Those are now
    the ANNOTATE/GATE and SUMMARIZE/DIGEST tasks' jobs, and this prompt says so
    out loud, because otherwise the model re-derives conclusions from whatever
    fragments happen to be pasted into ``extra`` and quietly invents the world.
    All it may do is *request* that a stage re-run, which is also stated below.

    It renders tool *parameter names*, not just tool names. When a catalog listed
    only names, the model invented argument names and the dispatcher rejected the
    call — costing a round-trip and surfacing to the user as silence, which on a
    23cm band screen reads as a dead device.
    """

    task = TaskKind.DIALOGUE
    # Three shapes the caller must disambiguate: prose, the silence sentinel, and
    # a single tool-call object. Naming them keeps "what this task may return"
    # answerable without reading the template.
    output_contract = "text|SILENCE_MARKER|json[call,arguments]"

    def body(self, params: PromptRenderParams) -> str:
        user_input = str(params.get("user_input") or "").strip()
        recent_turns = params.get("recent_turns") or []
        identity_anchor = params.get("identity_anchor")
        world_map = params.get("world_map")
        catalog = params.get("capability_catalog") or []

        sections: list[str] = [
            "【任务】与用户对话（DIALOGUE）",
            "",
            "【分工 · 必读】",
            "数据清洗、维度总结、事实抽取由专用环节完成，不在这里执行；你只看得见它们的产物，",
            "需要时可以请求重新执行某个环节。",
            "因此：不要根据眼前的对话或片段自行归纳长期结论、自己更新画像、自己给维度做总结——",
            "那是别的环节的职责，你越权做出来的东西不会回到系统里，只会误导这一次回答。",
            "",
            "【用户这一轮说的话】",
            user_input if user_input else "（本轮没有新的用户输入）",
            "",
            "【输出格式 · 三选一】",
            "1) 需要调用工具：只输出一个 JSON 代码块，不要同时输出回复文字：",
            _tool_call_example(),
            "2) 不需要任何动作（用户没提问、只是在陈述，或你已经答过了）：",
            f"只输出一行 {SILENCE_MARKER}",
            "3) 其余情况：直接输出自然语言回复。",
            "",
            "【回复要求】",
            "- 语言跟随用户：用户用简体中文，你就用简体中文；用户切换语言你就跟着切换。",
            "- 简洁。这是一块 23cm 的手环屏，回答能短就短，能用一句话就别用一段。",
            "- 不确定的时候说不确定，可以请求重新执行某个环节来获取证据，不要凭印象作答。",
            "- 不要复述用户的话，不要为没有做的事道歉，不要列清单式长文。",
        ]

        tools = _render_capabilities(catalog)
        if tools:
            sections += [
                "",
                "【可调用的工具】",
                tools,
                "",
                "【调用纪律】",
                "- 只能调用上面列出的工具，参数名必须使用“参数：”里给出的名字；",
                "  自己编一个参数名会被拒绝，等于白跑一趟。",
                "- 一次只发一个调用。需要多个工具时，等上一个结果回来再决定下一个。",
                "- 用户没有明确请求，就不要调用会带来副作用（写入、删除）的工具。",
            ]

        if isinstance(recent_turns, Sequence) and not isinstance(recent_turns, str) and recent_turns:
            sections += [
                "",
                "【近期对话】",
                # Fenced: turns arrive through ``extra`` and may contain relayed
                # third-party text. The current user turn above is *not* fenced —
                # that is the user's own instruction channel, and fencing it would
                # make the model refuse legitimate requests.
                untrusted_block(_recent_turns_block(recent_turns)),
            ]

        if identity_anchor:
            sections += [
                "",
                "【连续性锚点 · 用户画像 / 关系 / 自我认知】",
                "这是先前环节沉淀下来的产物，用来保持跨会话的连续性，不要当场改写或补充它。",
                _json_block(identity_anchor),
            ]

        if world_map:
            sections += [
                "",
                "【维度目录】",
                _json_block(world_map),
            ]

        return "\n".join(sections)


def _recent_turns_block(turns: Sequence[Any]) -> str:
    """Render recent dialogue turns as speaker-attributed lines."""

    lines: list[str] = []
    for turn in turns:
        if isinstance(turn, Mapping):
            role = str(turn.get("role") or turn.get("speaker") or "").strip() or "?"
            text = str(turn.get("text") or turn.get("content") or "")
        else:
            role = "?"
            text = str(turn)
        lines.append(f"{role}: {text}")
    return "\n".join(lines) if lines else "（无）"


def _tool_call_example() -> str:
    return "```json\n" + _CALL_EXAMPLE_JSON + "\n```"


_CALL_EXAMPLE_JSON = '{"call": "工具名", "arguments": {"参数名": "参数值"}}'


__all__ = [
    "SummarizePrompt",
    "DigestPrompt",
    "DialoguePrompt",
    "EMPTY_MARKER",
    "SILENCE_MARKER",
]
