"""Rate-limited text completion for AIOS summary handlers (NVIDIA-only build).

The Core's multi-scale summary scheduler (day / week / month / quarter / year)
expects a ``summary_handler`` returning plain text. This shares the same paced,
per-key request budget as ``resilient_handler``: pacing first, back off and retry
on 429, and only fall back to a second endpoint if the primary is unusable.

Environment: same as ``resilient_handler``.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from aios_core.context.budget_policy import resolve_context_budget_policy
from aios_core.runtime.resilient_handler import (
    _LIMITER,
    _is_rate_limited,
    _is_transient,
    PRIMARY_API_KEY,
    PRIMARY_BASE_URL,
    PRIMARY_MODEL,
    RETRY_ATTEMPTS,
    SECONDARY_API_KEY,
    SECONDARY_BASE_URL,
    SECONDARY_MODEL,
)

_SUMMARY_TIMEOUT = float(os.environ.get("AIOS_SUMMARY_TIMEOUT", "180"))


class _BlankCompletion(RuntimeError):
    """Provider returned 200 but produced no text (all budget went to reasoning)."""


def _complete(base_url: str, api_key: str, model: str, system: str, prompt: str) -> str:
    if not api_key:
        raise RuntimeError("model API key is not configured")
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        # Single source of truth (also honours AIOS_BUDGET_RESILIENT_TEXT_OUTPUT_TOKENS).
        "max_tokens": resolve_context_budget_policy().resilient_text_output_tokens,
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=_SUMMARY_TIMEOUT) as resp:
        body = json.loads(resp.read().decode("utf-8", errors="replace"))
    content = body["choices"][0]["message"]["content"]
    if isinstance(content, list):  # some providers return structured parts
        content = "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return str(content or "").strip()


def complete_text(system: str, prompt: str) -> str:
    """Text completion under the shared paced budget, with 429 backoff.

    A 200 response with an empty ``content`` is a real outcome for reasoning
    models: the whole output budget can be spent on hidden reasoning and the
    visible answer comes back blank. That is an upstream failure, not a valid
    summary, so it is retried like any other transient fault instead of being
    returned. Callers (the multi-scale summary scheduler) reject blank text, and
    letting one blank reply abort a whole habitation run loses every summary in
    the window -- including the ones the Core already paid for.
    """
    last_exc: BaseException | None = None
    for attempt in range(RETRY_ATTEMPTS + 1):
        _LIMITER.acquire()
        try:
            text = _complete(
                PRIMARY_BASE_URL, PRIMARY_API_KEY, PRIMARY_MODEL, system, prompt
            )
            if not text.strip():
                raise _BlankCompletion(
                    "provider returned 200 with empty content "
                    "(output budget likely consumed by reasoning)"
                )
            _LIMITER.reward()
            return text
        except BaseException as exc:  # noqa: BLE001
            last_exc = exc
            if _is_rate_limited(exc) and attempt < RETRY_ATTEMPTS:
                time.sleep(_LIMITER.penalize(attempt))
                continue
            if isinstance(exc, _BlankCompletion) and attempt < RETRY_ATTEMPTS:
                # Retrying the same prompt usually succeeds; the reasoning length
                # varies per call.
                time.sleep(1.5 * (attempt + 1))
                continue
            if _is_transient(exc) and attempt < RETRY_ATTEMPTS:
                time.sleep(2.0 * (attempt + 1))
                continue
            break
    # Independent endpoint as a last resort (not a rate-limit escape).
    try:
        text = _complete(
            SECONDARY_BASE_URL, SECONDARY_API_KEY, SECONDARY_MODEL, system, prompt
        )
        if text.strip():
            return text
        raise _BlankCompletion("secondary endpoint also returned empty content")
    except BaseException:  # noqa: BLE001
        if last_exc is not None:
            raise last_exc
        raise


_SUMMARY_SYSTEM = (
    "You are the summarizer inside AIOS, a long-lived cognitive world store. "
    "You are given a window of durable world evidence (observations, claims, "
    "prior summaries) for one dimension and one calendar window. "
    "Write a faithful, concise summary in Simplified Chinese (简体中文), even "
    "when the evidence is in another language, because the world owner reads "
    "Chinese. Keep proper nouns, identifiers and numbers exactly as recorded. "
    "Rules: never invent facts that the evidence does not support; never assert "
    "causality you cannot ground in the evidence; state what changed and what "
    "stayed stable; if the evidence is thin or contradictory, say so explicitly "
    "rather than smoothing it over. Return plain text only."
)


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(value)


class ResilientSummaryHandler:
    """``RoundSummaryHandler``: takes a prepared request, returns summary text."""

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id

    def __call__(self, request: Any) -> str:
        model_input = (
            request.as_model_input()
            if hasattr(request, "as_model_input")
            else _safe_json(request)
        )
        if not isinstance(model_input, str):
            model_input = _safe_json(model_input)
        return complete_text(_SUMMARY_SYSTEM, model_input)

    def provenance_snapshot(self) -> dict[str, Any]:
        return {
            "primary": PRIMARY_MODEL,
            "secondary": SECONDARY_MODEL,
            "rate": _LIMITER.snapshot(),
            "at": time.time(),
        }


def build_summary_handler(model_id: str) -> ResilientSummaryHandler:
    return ResilientSummaryHandler(model_id)
