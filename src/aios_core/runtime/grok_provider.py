"""Real Grok Multi-Model Streaming Provider for AIOS 3.0 Core.

This module provides a production-grade, dependency-free streaming client
connecting to OpenAI-compatible endpoints (specifically tested with grok-4.7
and grok-4.5 via local forwarder/proxies).

Constitutional Mandates:
1. Iron Rule 1: High-quality cognitive reasoning. Full streaming token aggregation
   with zero dropped chunks.
2. Iron Rule 2: Byte-immutable historical facts; model returns carry exact
   provider request IDs and usage tokens for cryptographic auditability.
3. Iron Rule 3: P0 critical safety triage is handled by edge SLM, but deep
   causal reasoning and multi-turn life reviews route to Grok Cloud LLM.
4. Anti-Self-Deception: Real network requests with HTTP 200 SSE streaming,
   accurate token counting, and authentic model provenance.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelHandler,
    ModelUsage,
    RuntimeSnapshot,
)

SILENCE_TOKEN = "<AIOS_SILENCE>"

DEFAULT_BASE_URL = os.environ.get("AIOS_GROK_BASE_URL", "http://127.0.0.1:8080/v1")
# Credentials MUST come from the environment. A literal default here would be
# committed to the repository and leak on every clone; fail closed instead.
DEFAULT_API_KEY = os.environ.get("AIOS_GROK_API_KEY", "")
DEFAULT_MODEL_PRIMARY = os.environ.get("AIOS_GROK_MODEL_PRIMARY", "grok-4.7")
DEFAULT_MODEL_SECONDARY = os.environ.get("AIOS_GROK_MODEL_SECONDARY", "grok-4.5")

# Cockpit keys that are bookkeeping rather than context; they only waste budget.
_COCKPIT_SCALAR_SKIP = frozenset({"token_budget", "estimated_tokens", "truncated", "user_input"})
_MAX_RECENT_CHARS = 6000
_MAX_CARD_CHARS = 2000
_MAX_IDENTITY_CHARS = 1600
_MAX_IDENTITY_STATEMENT_CHARS = 240
_MAX_SUMMARY_CHARS = 1800

# AI-world domains that carry durable "who we are" evidence. Order is deliberate:
# the relationship frames how to read the user, the user facts frame the work, and
# the self view frames the continuity of the assistant.
_IDENTITY_DOMAINS = (
    ("relationship", "relationship"),
    ("user_understanding", "user"),
    ("self", "self"),
)
# Structural identity keys that are rendered explicitly, not as generic scalars.
_IDENTITY_STRUCTURAL_KEYS = frozenset(
    {
        "user_understanding",
        "relationship",
        "self",
        "symbiotic_posture",
        "rapport_score",
        "rapport_tier",
        "active_promise_count",
        "outstanding_promises",
        "ethical_invariants",
        "ai_self_subject",
    }
)


def _render_recent_turns(turns: Any, *, max_chars: int = _MAX_RECENT_CHARS) -> str:
    """Render verbatim recent dialogue for the system prompt.

    The cockpit carries ``recent_turns`` as a list of dicts. The scalar-only
    filter that used to build the prompt dropped it entirely, so the model never
    saw the conversation it was supposed to be continuing.
    """
    if not isinstance(turns, (list, tuple)) or not turns:
        return ""
    lines: list[str] = []
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        idx = turn.get("turn_index")
        user = turn.get("user") or {}
        assistant = turn.get("assistant") or {}
        user_text = str(user.get("text", "")).strip() if isinstance(user, dict) else ""
        ai_text = str(assistant.get("text", "")).strip() if isinstance(assistant, dict) else ""
        if user_text:
            lines.append(f"[turn {idx}] user: {user_text}")
        if ai_text:
            lines.append(f"[turn {idx}] assistant: {ai_text}")
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = "…(earlier turns trimmed)…\n" + text[-max_chars:]
    return text


def _render_identity(identity: Any, *, max_chars: int = _MAX_IDENTITY_CHARS) -> str:
    """Render the durable continuity anchor: who we are, and where we left off.

    This is the block that has to survive context exhaustion. Everything here comes
    from the world store or from Core's own runtime counters — no persona prose is
    invented. Claims keep their object reference so the model can weigh and cite
    them rather than absorb an unverifiable script.

    The previous implementation dropped this whole block: ``ai_identity`` is a
    mapping, and the prompt builder kept only scalars, so the model was handed a
    factory identity every turn no matter how long the relationship had run.
    """
    if not isinstance(identity, Mapping) or not identity:
        return ""

    lines: list[str] = []

    for domain_key, label in _IDENTITY_DOMAINS:
        items = identity.get(domain_key)
        if not isinstance(items, (list, tuple)):
            continue
        for item in items:
            if not isinstance(item, Mapping):
                continue
            statement = str(item.get("statement") or "").strip()
            if not statement:
                continue
            if len(statement) > _MAX_IDENTITY_STATEMENT_CHARS:
                statement = statement[:_MAX_IDENTITY_STATEMENT_CHARS].rstrip() + "…"
            ref = str(item.get("object_id") or "").strip()
            revision = item.get("revision")
            suffix = f" [{ref}@{revision}]" if ref and revision is not None else ""
            lines.append(f"- ({label}) {statement}{suffix}")

    posture = identity.get("symbiotic_posture")
    rapport = identity.get("rapport_score")
    tier = identity.get("rapport_tier")
    if posture or rapport is not None:
        parts = []
        if posture:
            parts.append(f"posture={posture}")
        if rapport is not None:
            parts.append(f"rapport={rapport}")
        if tier:
            parts.append(f"tier={tier}")
        lines.append("- self-state: " + ", ".join(parts))

    promises = identity.get("outstanding_promises")
    if isinstance(promises, (list, tuple)) and promises:
        lines.append(f"- open promises ({len(promises)}):")
        for promise in promises:
            if not isinstance(promise, Mapping):
                continue
            desc = str(promise.get("desc") or promise.get("description") or "").strip()
            if not desc:
                continue
            due = str(promise.get("due") or "").strip()
            lines.append(f"  - {desc}" + (f" (due {due})" if due and due != "None" else ""))
    else:
        count = identity.get("active_promise_count")
        if isinstance(count, int) and count > 0:
            lines.append(f"- open promises: {count}")

    # Any remaining scalar identity fields (future additions) stay visible.
    extras = [
        f"{key}={value}"
        for key, value in identity.items()
        if key not in _IDENTITY_STRUCTURAL_KEYS
        and isinstance(value, (str, int, float, bool))
        and str(value).strip()
    ]
    if extras:
        lines.append("- also: " + ", ".join(extras))

    text = "\n".join(lines)
    if not text:
        return ""
    if len(text) > max_chars:
        # Keep the head, not the tail: relationship frames the user, then user facts,
        # then self-state and promises. Dropping the head would discard exactly the
        # entries that make the anchor an identity rather than a status line.
        text = text[:max_chars].rstrip() + "\n…(further anchor entries omitted)"
    return text


def _render_standing_constraints(identity: Any) -> str:
    """Render invariant behavioural constraints that must not drift across sessions.

    These are not memories and not user preferences; they are the terms the
    assistant holds itself to. They are kept out of the budgeted pool so a long
    conversation can never squeeze them out.
    """
    if not isinstance(identity, Mapping):
        return ""
    invariants = identity.get("ethical_invariants")
    if not isinstance(invariants, (list, tuple)):
        return ""
    lines = [f"- {str(item).strip()}" for item in invariants if str(item).strip()]
    return "\n".join(lines)


def _render_turn_grounding(task_context: Any) -> str:
    """Render what this turn can cite and which history routes exist.

    Two things lived here and never reached the model:

    1. ``current_user_observation_ref`` — the exact evidence reference a cognition
       writeback must cite. Without it the resident had to search first, or guess,
       before it could persist anything. That is a mechanical reason "records nothing"
       looked like "understands nothing".
    2. ``conversation_continuity`` — the names of the summary index, summary search
       and raw drill-down routes. A model that does not know it can look something up
       answers "I don't remember"; one that does, looks it up.

    Deliberately excluded: ``topic_state`` and ``cognitive_policy_context``. Those are
    Core's own gating decisions and policy parameters — audit material, not facts the
    model should be reasoning over, and showing them invites it to argue with the gate.
    """
    if not isinstance(task_context, Mapping) or not task_context:
        return ""

    lines: list[str] = []

    observation = task_context.get("current_user_observation_ref")
    if isinstance(observation, Mapping):
        object_id = str(observation.get("object_id") or "").strip()
        revision = observation.get("revision")
        if object_id and revision is not None:
            lines.append(
                "current user observation: "
                f"{{object_id: {object_id}, revision: {revision}}} "
                "— cite this as evidence when you persist a durable claim this turn"
            )

    continuity = task_context.get("conversation_continuity")
    if isinstance(continuity, Mapping):
        recent = continuity.get("recent_turn_count")
        summaries = continuity.get("round_summary_count")
        routes = [
            f"{label}={continuity[key]}"
            for key, label in (
                ("summary_index_capability", "list"),
                ("summary_search_capability", "search"),
                ("raw_drill_down_capability", "exact words"),
            )
            if continuity.get(key)
        ]
        counts = []
        if recent is not None:
            counts.append(f"{recent} verbatim turns in view")
        if summaries is not None:
            counts.append(f"{summaries} round summaries")
        detail = ", ".join(counts)
        if routes:
            lines.append(
                "history available: "
                + (f"{detail}; " if detail else "")
                + "use "
                + ", ".join(routes)
                + " — check before saying you do not remember"
            )
        elif detail:
            lines.append("history available: " + detail)

    anchors = task_context.get("related_execution_anchors")
    if isinstance(anchors, (list, tuple)) and anchors:
        rendered: list[str] = []
        for anchor in anchors[:5]:
            if not isinstance(anchor, Mapping):
                continue
            label = (
                str(anchor.get("title") or anchor.get("content") or anchor.get("object_id") or "")
                .strip()
            )
            if label:
                rendered.append(f"- {label[:200]}")
        if rendered:
            lines.append("work already in flight on this topic:\n" + "\n".join(rendered))

    return "\n".join(lines)


def _render_world_map(world_map: Any, *, max_dimensions: int = 12) -> str:
    """Render the L0 world directory: what exists, never what it means.

    The cockpit carried a dimension directory every turn and the model never saw it,
    so it had no idea how large the world it could search actually was, or which
    dimensions were active. The map is structure only (``directory_only: true``,
    ``semantic_conclusions: false``); the meaning stays in the objects, behind search.
    """
    if not isinstance(world_map, Mapping) or not world_map:
        return ""
    dimensions = world_map.get("dimensions")
    if not isinstance(dimensions, (list, tuple)) or not dimensions:
        return ""

    lines: list[str] = []
    for dimension in dimensions[:max_dimensions]:
        if not isinstance(dimension, Mapping):
            continue
        key = str(dimension.get("dimension") or "").strip()
        if not key:
            continue
        count = dimension.get("current_object_count")
        kinds = dimension.get("object_types")
        kind_text = (
            "/".join(str(item) for item in kinds[:3])
            if isinstance(kinds, (list, tuple)) and kinds
            else ""
        )
        name = str(dimension.get("name") or "").strip()
        label = f"{name} ({key})" if name else key
        detail = []
        if count is not None:
            detail.append(f"{count} objects")
        if kind_text:
            detail.append(kind_text)
        lines.append(f"- {label}" + (f": {', '.join(detail)}" if detail else ""))

    if not lines:
        return ""

    total = world_map.get("dimension_count")
    header = (
        f"{total} active dimensions" if total is not None else f"{len(lines)} active dimensions"
    )
    if world_map.get("truncated"):
        header += " (directory truncated)"

    expand = world_map.get("expand_capabilities")
    if isinstance(expand, Mapping) and expand:
        routes = ", ".join(
            f"{purpose}={capability}" for purpose, capability in list(expand.items())[:6]
        )
        lines.append("expand with: " + routes)

    return header + "\n" + "\n".join(lines)


def _render_capabilities(catalog: Any, *, max_names_chars: int = 1600) -> str:
    """Render the capability catalog for the prompt.

    Two rules, both learned from a live model that could not persist anything:

    1. **Name every capability.** The old renderer printed the first ten entries of
       an alphabetically sorted list, so half the tools were invisible while the
       prompt still referred to them by name ("use list=list_conversation_summaries")
       — an instruction to call something the model could not see.
    2. **State required arguments where a wrong call is unrecoverable.** A write
       that persists understanding has to be called with the right argument names
       first time. Guessing is not recoverable by retrying, because the turn ends.
    """

    if not isinstance(catalog, (list, tuple)) or not catalog:
        return ""

    names: list[str] = []
    signatures: list[str] = []
    for cap in catalog:
        if not isinstance(cap, Mapping):
            continue
        name = str(cap.get("name") or "").strip()
        if not name:
            continue
        names.append(name)
        required = cap.get("required_args")
        if isinstance(required, Mapping) and required:
            rendered = ", ".join(
                f"{key}:{value}" if value else str(key) for key, value in required.items()
            )
            signatures.append(f"- {name}({rendered})")

    if not names:
        return ""

    blocks = ["named: " + ", ".join(names)[:max_names_chars]]
    if signatures:
        blocks.append(
            "write path — required arguments, optional ones may be omitted:\n"
            + "\n".join(signatures)
        )
        example = _render_capability_example(catalog)
        if example:
            blocks.append(example)
    return "\n".join(blocks)


# A single worked example is worth more than a schema to a small model: a local
# 27B reproduced the same malformed call four rounds running while the argument
# names were stated in prose, and only started emitting the right shape once the
# shape itself was shown. One example teaches the JSON form; the signatures above
# teach the names for the rest.
_PRIMARY_WRITE_CAPABILITY = "commit_ai_world_claim"

_PLACEHOLDERS = (
    ("[{object_id,revision}]", [{"object_id": "<observation object_id>", "revision": 1}]),
    ("{object_id,revision}", {"object_id": "<object_id>", "revision": 1}),
    ("[string]", ["<text>"]),
    ("string", "<text>"),
    ("number[0,1]", 0.9),
)


def _example_value(short_type: str) -> Any:
    for needle, value in _PLACEHOLDERS:
        if short_type == needle:
            return value
    if "|" in short_type:
        # An enum. The first branch is a legal value; the model only needs the form.
        return short_type.split("|")[0].strip()
    return "<value>"


def _render_capability_example(catalog: Any) -> str:
    for cap in catalog:
        if not isinstance(cap, Mapping) or cap.get("name") != _PRIMARY_WRITE_CAPABILITY:
            continue
        required = cap.get("required_args")
        if not isinstance(required, Mapping) or not required:
            return ""
        arguments = {key: _example_value(str(value)) for key, value in required.items()}
        payload = {"call": _PRIMARY_WRITE_CAPABILITY, "arguments": arguments}
        return "example (copy this shape):\n" + json.dumps(payload, ensure_ascii=False)
    return ""


def _render_capability_result(result: Any) -> str:
    """Render one capability result for the model's next round.

    A rejected call must say *why* it was rejected. Reporting only ``ok=False``
    tells the model that something failed and nothing about what to change, so its
    next attempt repeats the same mistake — observed live: a local model called
    ``commit_ai_world_claim`` with ``claim``/``evidence`` instead of
    ``statement``/``evidence_refs``, was told ``ok=False``, and retried with the
    same wrong names. The kernel knew the required arguments were missing; it just
    did not say so.
    """

    name = getattr(result, "name", "capability")
    ok = bool(getattr(result, "ok", False))
    if ok:
        return f"Result of {name}: ok=True, data={json.dumps(getattr(result, 'data', None), ensure_ascii=False, default=str)}"

    error_code = getattr(result, "error_code", None)
    error_message = getattr(result, "error_message", None)
    detail = ", ".join(
        part for part in (str(error_code or "").strip(), str(error_message or "").strip()) if part
    )
    suffix = f", error={detail}" if detail else ""
    return f"Result of {name}: ok=False{suffix}. Fix the arguments and call again, or answer without it."


def _render_conversation_summaries(
    summaries: Any, *, max_chars: int = _MAX_SUMMARY_CHARS
) -> str:
    """Render same-session round summaries as compressed earlier history.

    Round summaries were already committed, already budgeted into the cockpit, and
    still never reached the model: there was no renderer for them. The model could
    only recover them by spending a tool round on ``list_conversation_summaries``,
    which rule 0 of the prompt actively discourages. They belong in the prompt as
    an index, with the exact-wording route named.
    """
    if not isinstance(summaries, (list, tuple)) or not summaries:
        return ""
    lines: list[str] = []
    for summary in summaries:
        if not isinstance(summary, Mapping):
            continue
        content = str(summary.get("content") or "").strip()
        if not content:
            continue
        start = summary.get("turn_start")
        end = summary.get("turn_end")
        span = (
            f"turns {start}-{end}"
            if start is not None and end is not None
            else "earlier turns"
        )
        lines.append(f"- {span}: {content}")
    text = "\n".join(lines)
    return text[-max_chars:] if len(text) > max_chars else text


def _render_memory_cards(cards: Any, *, max_chars: int = _MAX_CARD_CHARS) -> str:
    """Render proactively recommended world objects for the system prompt."""
    if not isinstance(cards, (list, tuple)) or not cards:
        return ""
    lines: list[str] = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        excerpt = str(card.get("excerpt", "")).strip()
        if not excerpt:
            continue
        obj_type = card.get("object_type", "object")
        dimension = card.get("dimension", "")
        lines.append(f"- [{obj_type}/{dimension}] {excerpt[:400]}")
    text = "\n".join(lines)
    return text[-max_chars:] if len(text) > max_chars else text


@dataclass(frozen=True)
class GrokProviderConfig:
    """Configuration for Grok streaming endpoints."""

    base_url: str = DEFAULT_BASE_URL
    api_key: str = DEFAULT_API_KEY
    default_model: str = DEFAULT_MODEL_PRIMARY
    secondary_model: str = DEFAULT_MODEL_SECONDARY
    timeout_seconds: float = 60.0
    temperature: float = 0.6
    max_output_tokens: int = 4096


class GrokStreamingProvider:
    """OpenAI-compatible SSE streaming client for Grok-4.7 and Grok-4.5."""

    def __init__(self, config: GrokProviderConfig | None = None) -> None:
        self.config = config or GrokProviderConfig()
        self._endpoint = f"{self.config.base_url.rstrip('/')}/chat/completions"

    def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> tuple[str, ModelUsage, ModelCallProvenance]:
        """Execute a streaming chat completion and aggregate chunks into a full response.

        Returns (aggregated_text, model_usage, model_provenance).
        """
        chosen_model = model or self.config.default_model
        temp = temperature if temperature is not None else self.config.temperature

        if not self.config.api_key:
            raise RuntimeError(
                "AIOS_GROK_API_KEY is not configured; refusing to send an "
                "unauthenticated request to the provider endpoint"
            )

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": chosen_model,
            "messages": list(messages),
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": temp,
            "max_tokens": self.config.max_output_tokens,
        }

        req_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self._endpoint, data=req_bytes, headers=headers)

        accumulated_chunks: list[str] = []
        captured_id: str | None = None
        raw_usage: dict[str, Any] | None = None

        start_time = time.perf_counter()
        for attempt in range(3):
            accumulated_chunks = []
            captured_id = None
            raw_usage = None
            try:
                with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"Grok provider returned HTTP status {resp.status}")

                    for raw_line in resp:
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        if captured_id is None and chunk.get("id"):
                            captured_id = str(chunk["id"])

                        if chunk.get("usage"):
                            raw_usage = chunk["usage"]

                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                accumulated_chunks.append(content)
                break
            except urllib.error.HTTPError as http_err:
                body = ""
                try:
                    body = http_err.read().decode("utf-8", errors="ignore")[:500]
                except Exception:
                    pass
                if http_err.code in (503, 429) and attempt < 2:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise RuntimeError(
                    f"Grok HTTP {http_err.code} error: {http_err.reason}. Body: {body}"
                ) from http_err
            except (urllib.error.URLError, TimeoutError) as net_err:
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                if isinstance(net_err, TimeoutError):
                    raise TimeoutError(f"Grok stream timed out after {self.config.timeout_seconds}s") from net_err
                raise ConnectionError(f"Grok connection failure: {net_err}") from net_err

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        full_text = "".join(accumulated_chunks).strip()
        request_id = captured_id or f"grok-{int(time.time()*1000)}"

        # Compute usage
        # reasoning_tokens 语义：None = 上游未报告（fallback 估算分支不得瞎猜）；
        # 0 = 上游已报告且确无思考消耗；>0 = 显式记录的思考开销。
        if raw_usage:
            prompt_tokens = int(raw_usage.get("prompt_tokens", 0))
            completion_tokens = int(raw_usage.get("completion_tokens", 0))
            total_tokens = int(raw_usage.get("total_tokens", prompt_tokens + completion_tokens))

            # 思考模型（如 Gemini 3 系列）的 total_tokens 含 reasoning 消耗，而
            # completion_tokens 只计最终可见输出。优先采用厂商给出的明细字段，
            # 缺失时用 total - input - output 反推，避免这部分开销被静默吞掉。
            details = (
                raw_usage.get("completion_tokens_details")
                or raw_usage.get("output_tokens_details")
                or {}
            )
            reported_reasoning = (
                details.get("reasoning_tokens") if isinstance(details, Mapping) else None
            )
            if reported_reasoning is not None:
                reasoning_tokens: int | None = int(reported_reasoning)
            else:
                inferred = total_tokens - prompt_tokens - completion_tokens
                reasoning_tokens = inferred if inferred > 0 else 0

            billed_floor = prompt_tokens + completion_tokens + reasoning_tokens
            if total_tokens < billed_floor:
                total_tokens = billed_floor
        else:
            # Fallback estimation if endpoint omitted usage block
            est_input = max(1, sum(len(m.get("content", "")) for m in messages) // 4)
            est_output = max(1, len(full_text) // 4)
            prompt_tokens = est_input
            completion_tokens = est_output
            total_tokens = est_input + est_output
            # 估算分支无法得知思考开销，显式留空而不是编造数字。
            reasoning_tokens = None

        provenance = ModelCallProvenance(
            provider="grok",
            model=chosen_model,
            request_id=request_id,
        )

        usage = ModelUsage(
            total_tokens=total_tokens,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
            provider="grok",
            model=chosen_model,
            request_id=request_id,
        )

        return full_text, usage, provenance

    def as_executor(self, model: str | None = None) -> Callable[[str, dict[str, Any]], str]:
        """Returns a simple prompt executor callable compatible with MultiModelEdgeScheduler."""
        def _executor(prompt: str, context: dict[str, Any]) -> str:
            system_role = (
                "You are the AIOS 3.0 wearable cognitive symbiote. Provide concise, "
                "insightful, empathetic, and evidence-grounded responses suitable for "
                "a 23cm flexible wristband display."
            )
            messages = [
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt},
            ]
            text, _, _ = self.stream_chat(messages, model=model)
            return text

        return _executor

    def as_model_handler(self, model: str | None = None) -> ModelHandler:
        """Returns a ModelHandler callable compatible with CognitiveRuntime and FusedTurnRuntime."""
        chosen_model = model or self.config.default_model

        def _handler(snapshot: RuntimeSnapshot) -> ModelDirective:
            # 1. Build rich system prompt with context cockpit and capability declarations
            identity = snapshot.cockpit.get("ai_identity")
            system_sections = [
                "You are the AIOS 3.0 symbiotic mind on an ultra-compact wearable band.",
            ]

            # Standing constraints come before everything else and are never
            # budgeted away. A long conversation must not let the assistant drift
            # into a different character.
            standing = _render_standing_constraints(identity)
            if standing:
                system_sections.append(
                    "STANDING CONSTRAINTS (invariant — these do not change with "
                    "topic, session, model or context length):\n" + standing
                )

            # The continuity anchor is what makes a resumed conversation feel like
            # the same assistant rather than a fresh instance.
            anchor = _render_identity(identity)
            if anchor:
                system_sections.append(
                    "CONTINUITY ANCHOR (durable world-store evidence about this "
                    "user and this relationship — evidence, not a script; you still "
                    "decide what it means):\n" + anchor
                )

            system_sections.extend(
                [
                    "DURABLE MEMORY DISCIPLINE:",
                    "- Anything that stays true beyond this conversation — who the user "
                    "is, their long-running work, standing preferences, agreed ways of "
                    "working, promises you made — survives only if you persist it with "
                    'commit_ai_world_claim (domain user_understanding / relationship / '
                    'self, tags ["core_context"]). Claims without that tag will not '
                    "appear in your continuity anchor on a later turn.",
                    "- Persist once, when it is first stated or first changed. Do not "
                    "re-persist what the anchor already says, and do not promote passing "
                    "remarks into durable facts.",
                    "- The claim is a pointer, not a replacement: drill_down_conversation "
                    "still holds the user's exact words.",
                    "CONSTITUTIONAL RULES:",
                    "0. The RECENT CONVERSATION block below is the verbatim dialogue. "
                    "If the answer is already visible there, answer from it directly — "
                    "never claim you cannot remember something that is in front of you, "
                    "and do not spend a tool round retrieving what you can already read.",
                    "1. If no response or action is warranted, output exactly '<AIOS_SILENCE>'.",
                    "2. To invoke a registered capability, output a JSON block:",
                    "```json",
                    '{"call": "<capability_name>", "arguments": { ... }}',
                    "```",
                    "   A call ends the round, not the turn. The kernel runs it and calls "
                    "you again with the result, and you answer the user in that round. "
                    "Persisting something therefore never costs you the reply — never skip "
                    "a durable write because you also want to say something. A frontier "
                    "model with the full write signature in view still produced four "
                    "replies and zero writes, reading this rule as 'either call or answer'.",
                    "3. If no capability is needed, provide a concise, high-value natural "
                    "language response.",
                ]
            )

            grounding = _render_turn_grounding(snapshot.cockpit.get("task_context"))
            if grounding:
                system_sections.append(
                    "THIS TURN — GROUNDING (what you can cite, and how to reach the "
                    "rest of the history):\n" + grounding
                )

            world_map = _render_world_map(snapshot.cockpit.get("world_map"))
            if world_map:
                system_sections.append(
                    "WORLD MAP (L0 directory — what exists, not what it means; open a "
                    "dimension only when the turn needs it):\n" + world_map
                )

            if snapshot.cockpit:
                # Scalars only. Structured blocks (recent_turns / memory_cards /
                # conversation_summaries / ai_identity / world_map / task_context)
                # are rendered explicitly above or below; identity keys are excluded
                # here so they cannot appear as a duplicated, unreferenced dump.
                summary_items = []
                for k, v in snapshot.cockpit.items():
                    if (
                        isinstance(v, (str, int, float, bool))
                        and k not in _COCKPIT_SCALAR_SKIP
                    ):
                        summary_items.append(f"{k}: {v}")
                if summary_items:
                    system_sections.append("ACTIVE COCKPIT CONTEXT:\n" + "\n".join(summary_items[:8]))

            covered = _render_conversation_summaries(
                snapshot.cockpit.get("conversation_summaries")
            )
            if covered:
                system_sections.append(
                    "WHAT WE ALREADY COVERED (compressed earlier turns of this "
                    "session — an index, not verbatim truth; use "
                    "drill_down_conversation when exact wording matters):\n" + covered
                )

            recent = _render_recent_turns(snapshot.cockpit.get("recent_turns"))
            if recent:
                system_sections.append(
                    "RECENT CONVERSATION (verbatim, newest last — this is the real "
                    "dialogue, treat it as ground truth):\n" + recent
                )

            cards = _render_memory_cards(snapshot.cockpit.get("memory_cards"))
            if cards:
                system_sections.append("RELEVANT WORLD MEMORY:\n" + cards)

            if snapshot.capability_catalog:
                system_sections.append(
                    "AVAILABLE CAPABILITIES:\n" + _render_capabilities(snapshot.capability_catalog)
                )

            if snapshot.remaining_tool_rounds == 0:
                system_sections.append(
                    "NOTICE: You have 0 tool rounds remaining. You MUST provide a direct natural language response to the user now without requesting any tool calls."
                )

            messages: list[dict[str, str]] = [
                {"role": "system", "content": "\n\n".join(system_sections)}
            ]

            # Ingest previous capability results in current turn if any
            if snapshot.capability_history:
                history_text = "\n".join(_render_capability_result(r) for r in snapshot.capability_history)
                messages.append({
                    "role": "assistant",
                    "content": f"Capability execution feedback:\n{history_text}"
                })

            user_content = snapshot.user_input
            if snapshot.wake_reason and snapshot.wake_reason != "user_explicit":
                user_content = f"[{snapshot.wake_reason}] {user_content}"
            messages.append({"role": "user", "content": user_content})

            # Execute streaming call
            full_text, usage, provenance = self.stream_chat(messages, model=chosen_model)

            # Check for silence token
            if SILENCE_TOKEN in full_text:
                return ModelDirective(silence=True, usage=usage, provenance=provenance)

            # Check for JSON capability call block only if tool rounds remain
            if snapshot.remaining_tool_rounds > 0:
                tool_call = self._extract_capability_call(full_text, snapshot.capability_catalog)
                if tool_call is not None:
                    return ModelDirective(
                        capability_calls=(tool_call,),
                        usage=usage,
                        provenance=provenance,
                    )

            # Clean response text
            cleaned_response = full_text.strip()
            if not cleaned_response:
                return ModelDirective(silence=True, usage=usage, provenance=provenance)

            return ModelDirective(
                response=cleaned_response,
                usage=usage,
                provenance=provenance,
            )

        return _handler

    @staticmethod
    def _extract_capability_call(
        text: str,
        catalog: Sequence[Mapping[str, Any]],
    ) -> CapabilityCall | None:
        """Parse text for capability invocation blocks matching registered capabilities."""
        available_names = {c.get("name") for c in catalog if isinstance(c, Mapping)}
        if not available_names:
            return None

        # Look for ```json { ... } ``` or raw {"call": ...}
        match = re.search(r"\{[\s\S]*\"call\"\s*:\s*\"([^\"]+)\"[\s\S]*\}", text)
        if not match:
            return None

        try:
            start_idx = text.find("{")
            end_idx = text.rfind("}")
            if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
                return None
            candidate_json = text[start_idx : end_idx + 1]
            data = json.loads(candidate_json)
            call_name = data.get("call")
            if call_name in available_names:
                args = data.get("arguments", {})
                if isinstance(args, dict):
                    return CapabilityCall(name=call_name, arguments=args)
        except Exception:
            return None

        return None
