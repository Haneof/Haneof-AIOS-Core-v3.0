"""The live handler is the seam between the kernel and any real endpoint.

These tests cover the part that must never be wrong: which endpoint a process is
allowed to talk to, and with what credential. They do not call the network — the
provider's own behaviour is covered elsewhere.
"""

from __future__ import annotations

import pytest

from aios_core.headless.core import HeadlessConfigurationError, load_model_handler
from aios_core.runtime import live_handler
from aios_core.runtime.live_handler import (
    LiveHandlerConfigurationError,
    build_handler,
    build_provider,
    reset_handler_cache,
)

_ENV_KEYS = (
    "AIOS_LIVE_BASE_URL",
    "AIOS_LIVE_MODEL",
    "AIOS_LIVE_API_KEY",
    "AIOS_LIVE_TIMEOUT_SECONDS",
    "AIOS_LIVE_MAX_OUTPUT_TOKENS",
    "AIOS_LIVE_TEMPERATURE",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    reset_handler_cache()


def test_loopback_endpoint_runs_without_a_key() -> None:
    """llama-server and Ollama do not authenticate; a missing key must not block them."""

    built = build_handler(base_url="http://127.0.0.1:8081/v1", model="local-model")
    assert callable(built)


def test_localhost_and_ipv6_loopback_are_also_keyless() -> None:
    for base in ("http://localhost:11434/v1", "http://[::1]:8081/v1"):
        assert callable(build_handler(base_url=base, model="local-model"))


def test_remote_endpoint_without_a_key_is_refused() -> None:
    """The failure mode we refuse is sending an unauthenticated request to a remote host."""

    with pytest.raises(LiveHandlerConfigurationError, match="AIOS_LIVE_API_KEY"):
        build_handler(base_url="https://api.example.com/v1", model="gpt-x")


def test_remote_endpoint_with_a_key_is_allowed() -> None:
    assert callable(
        build_handler(base_url="https://api.example.com/v1", model="gpt-x", api_key="sk-test")
    )


def test_environment_configures_endpoint_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIOS_LIVE_BASE_URL", "http://127.0.0.1:9999/v1")
    monkeypatch.setenv("AIOS_LIVE_MODEL", "qwen-test")
    monkeypatch.setenv("AIOS_LIVE_TIMEOUT_SECONDS", "42")
    monkeypatch.setenv("AIOS_LIVE_MAX_OUTPUT_TOKENS", "128")

    config = build_provider().config
    assert config.base_url == "http://127.0.0.1:9999/v1"
    assert config.default_model == "qwen-test"
    assert config.timeout_seconds == 42.0
    assert config.max_output_tokens == 128


def test_bad_numeric_environment_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIOS_LIVE_BASE_URL", "http://127.0.0.1:8081/v1")
    monkeypatch.setenv("AIOS_LIVE_TIMEOUT_SECONDS", "not-a-number")

    with pytest.raises(LiveHandlerConfigurationError, match="AIOS_LIVE_TIMEOUT_SECONDS"):
        build_handler()


def test_headless_can_load_the_handler_by_reference() -> None:
    """The CLI contract is module:attribute; this is the attribute it will load."""

    loaded = load_model_handler("aios_core.runtime.live_handler:handler")
    assert callable(loaded)


def test_handler_import_does_not_require_a_configured_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Import and load must stay side-effect free, so config can arrive later."""

    monkeypatch.setenv("AIOS_LIVE_BASE_URL", "https://api.example.com/v1")
    reset_handler_cache()
    assert callable(live_handler.handler)  # no request, no exception


def test_handler_cache_can_be_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIOS_LIVE_BASE_URL", "http://127.0.0.1:8081/v1")
    monkeypatch.setenv("AIOS_LIVE_MODEL", "first")
    live_handler.reset_handler_cache()

    # Build through the module-level entry point without invoking a turn.
    first = build_provider()
    monkeypatch.setenv("AIOS_LIVE_MODEL", "second")
    second = build_provider()

    assert first.config.default_model == "first"
    assert second.config.default_model == "second"


def test_missing_attribute_is_reported_by_the_loader() -> None:
    with pytest.raises(HeadlessConfigurationError, match="not found"):
        load_model_handler("aios_core.runtime.live_handler:does_not_exist")
