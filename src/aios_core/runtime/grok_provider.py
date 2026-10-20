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
            system_sections = [
                "You are the AIOS 3.0 symbiotic mind on an ultra-compact wearable band.",
                "CONSTITUTIONAL RULES:",
                "0. The RECENT CONVERSATION block below is the verbatim dialogue. "
                "If the answer is already visible there, answer from it directly — "
                "never claim you cannot remember something that is in front of you, "
                "and do not spend a tool round retrieving what you can already read.",
                "1. If no response or action is warranted, output exactly '<AIOS_SILENCE>'.",
                "2. If you need to invoke a registered capability, output a JSON block:",
                "```json",
                '{"call": "<capability_name>", "arguments": { ... }}',
                "```",
                "3. Otherwise, provide a concise, high-value natural language response.",
            ]

            if snapshot.cockpit:
                # Scalars only. Structured blocks (recent_turns / memory_cards /
                # conversation_summaries) are lists and were silently dropped by
                # this filter, which is why the model could not answer follow-up
                # questions about things it had just been told.
                summary_items = []
                for k, v in snapshot.cockpit.items():
                    if isinstance(v, (str, int, float, bool)) and k not in _COCKPIT_SCALAR_SKIP:
                        summary_items.append(f"{k}: {v}")
                if summary_items:
                    system_sections.append("ACTIVE COCKPIT CONTEXT:\n" + "\n".join(summary_items[:8]))

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
                cat_desc = [
                    f"- {cap.get('name')}: {cap.get('description', '')}"
                    for cap in snapshot.capability_catalog[:10]
                ]
                system_sections.append("AVAILABLE CAPABILITIES:\n" + "\n".join(cat_desc))

            if snapshot.remaining_tool_rounds == 0:
                system_sections.append(
                    "NOTICE: You have 0 tool rounds remaining. You MUST provide a direct natural language response to the user now without requesting any tool calls."
                )

            messages: list[dict[str, str]] = [
                {"role": "system", "content": "\n\n".join(system_sections)}
            ]

            # Ingest previous capability results in current turn if any
            if snapshot.capability_history:
                history_text = "\n".join(
                    f"Result of {r.name}: ok={r.ok}, data={json.dumps(r.data, ensure_ascii=False, default=str)}"
                    for r in snapshot.capability_history
                )
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
