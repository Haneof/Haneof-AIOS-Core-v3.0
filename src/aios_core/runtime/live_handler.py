"""Live model handler for any OpenAI-compatible endpoint.

The headless process refuses to make a provider constitutional: it accepts
``--model-handler module:attribute`` and loads whatever callable it finds. That
keeps the choice of model out of the kernel, but it also meant every real
deployment had to write its own adapter module first. This module is that
adapter, so a local runtime can be plugged in without writing code::

    AIOS_LIVE_BASE_URL=http://127.0.0.1:8081/v1 \\
    AIOS_LIVE_MODEL=qwen3.8-27b-coder390-q3lynnstyle16g-mtp \\
    aios-core-headless turn \\
        --model-handler aios_core.runtime.live_handler:handler \\
        --world ./world.sqlite --session s1 --turn-index 1 --text "..."

Works unchanged against llama.cpp's ``llama-server``, Ollama (``/v1``), vLLM,
LM Studio and any hosted relay that speaks the OpenAI chat-completions dialect
with SSE streaming.

Configuration is read from the environment on the first turn, never at import
time, so a process can still be configured after the handler is loaded:

    AIOS_LIVE_BASE_URL           default http://127.0.0.1:8080/v1
    AIOS_LIVE_MODEL              default grok-4.7 (the provider's own default)
    AIOS_LIVE_API_KEY            optional for loopback endpoints
    AIOS_LIVE_TIMEOUT_SECONDS    default 300
    AIOS_LIVE_MAX_OUTPUT_TOKENS  default 4096
    AIOS_LIVE_TEMPERATURE        default 0.6

Loopback endpoints (127.0.0.1 / localhost / ::1) are allowed to run without a
key, because llama-server and friends do not authenticate. Remote endpoints are
not: an empty key against a remote host raises instead of sending an
unauthenticated request, which is the same fail-closed rule the provider
already applies.
"""

from __future__ import annotations

import os
import urllib.parse
from typing import Final

from aios_core.runtime.cognitive_runtime import ModelDirective, ModelHandler, RuntimeSnapshot
from aios_core.runtime.grok_provider import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL_PRIMARY,
    GrokProviderConfig,
    GrokStreamingProvider,
)

_LOOPBACK_HOSTS: Final[frozenset[str]] = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})
# Sent to loopback endpoints that do not authenticate. Never used for remote
# hosts: a real provider must receive a real credential or nothing at all.
_LOOPBACK_PLACEHOLDER_KEY: Final[str] = "loopback-no-auth"


class LiveHandlerConfigurationError(RuntimeError):
    """Raised when the environment does not describe a usable endpoint."""


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise LiveHandlerConfigurationError(f"{name} must be a number, got {raw!r}") from exc


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise LiveHandlerConfigurationError(f"{name} must be an integer, got {raw!r}") from exc


def _resolve_api_key(base_url: str, configured: str) -> str:
    """Return a usable credential, or refuse.

    A loopback endpoint is allowed to have no credential. A remote endpoint is
    not: the failure mode we refuse is "silently send an unauthenticated request
    and let the relay decide".
    """

    if configured:
        return configured
    host = (urllib.parse.urlsplit(base_url).hostname or "").lower()
    if host in _LOOPBACK_HOSTS:
        return _LOOPBACK_PLACEHOLDER_KEY
    raise LiveHandlerConfigurationError(
        f"AIOS_LIVE_API_KEY is not configured for remote endpoint {base_url!r}; "
        "refusing to send an unauthenticated request"
    )


def build_provider(
    *,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    timeout_seconds: float | None = None,
    max_output_tokens: int | None = None,
    temperature: float | None = None,
) -> GrokStreamingProvider:
    """Build the provider from explicit arguments, falling back to the environment."""

    resolved_base = (base_url or os.environ.get("AIOS_LIVE_BASE_URL", "").strip()
                     or DEFAULT_BASE_URL)
    resolved_model = (model or os.environ.get("AIOS_LIVE_MODEL", "").strip()
                      or DEFAULT_MODEL_PRIMARY)
    configured_key = api_key if api_key is not None else os.environ.get("AIOS_LIVE_API_KEY", "").strip()

    config = GrokProviderConfig(
        base_url=resolved_base,
        api_key=_resolve_api_key(resolved_base, configured_key),
        default_model=resolved_model,
        timeout_seconds=(
            timeout_seconds
            if timeout_seconds is not None
            else _env_float("AIOS_LIVE_TIMEOUT_SECONDS", 300.0)
        ),
        temperature=(
            temperature
            if temperature is not None
            else _env_float("AIOS_LIVE_TEMPERATURE", 0.6)
        ),
        max_output_tokens=(
            max_output_tokens
            if max_output_tokens is not None
            else _env_int("AIOS_LIVE_MAX_OUTPUT_TOKENS", 4096)
        ),
    )
    return GrokStreamingProvider(config)


def build_handler(
    *,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    timeout_seconds: float | None = None,
    max_output_tokens: int | None = None,
    temperature: float | None = None,
) -> ModelHandler:
    """Build the ``RuntimeSnapshot -> ModelDirective`` callable the kernel expects."""

    provider = build_provider(
        base_url=base_url,
        model=model,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
    )
    return provider.as_model_handler(model=provider.config.default_model)


_cached: ModelHandler | None = None


def handler(snapshot: RuntimeSnapshot) -> ModelDirective:
    """Headless entry point: ``--model-handler aios_core.runtime.live_handler:handler``."""

    global _cached
    if _cached is None:
        _cached = build_handler()
    return _cached(snapshot)


def reset_handler_cache() -> None:
    """Drop the cached handler so the next turn re-reads the environment."""

    global _cached
    _cached = None
