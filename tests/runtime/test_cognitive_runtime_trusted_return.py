"""Trusted provider-return boundary ordering for CognitiveRuntime."""

from __future__ import annotations

import pytest

from aios_core.runtime.capabilities import CapabilityRegistry
from aios_core.runtime.cognitive_runtime import CognitiveRuntime, ModelDirective


def test_trusted_return_authentication_precedes_response_and_usage_recording():
    events: list[str] = []

    def model(_snapshot):
        events.append("provider_return")
        return ModelDirective(response="authenticated reply")

    runtime = CognitiveRuntime(
        registry=CapabilityRegistry(),
        model_handler=model,
        model_response_authenticator=lambda _snapshot, _directive: events.append(
            "authenticate"
        ),
        model_response_recorder=lambda _snapshot, _directive: events.append(
            "record_response"
        ),
        model_usage_recorder=lambda _snapshot, _directive: events.append("meter"),
    )

    result = runtime.run_turn("test trusted return ordering")

    assert result.response == "authenticated reply"
    assert events == ["provider_return", "authenticate", "record_response", "meter"]


def test_authentication_failure_prevents_every_downstream_callback_and_output():
    events: list[str] = []

    def reject(_snapshot, _directive):
        events.append("authenticate")
        raise RuntimeError("invalid trusted return")

    runtime = CognitiveRuntime(
        registry=CapabilityRegistry(),
        model_handler=lambda _snapshot: ModelDirective(response="must not escape"),
        model_response_authenticator=reject,
        model_response_recorder=lambda _snapshot, _directive: events.append(
            "record_response"
        ),
        model_usage_recorder=lambda _snapshot, _directive: events.append("meter"),
    )

    with pytest.raises(RuntimeError, match="invalid trusted return"):
        runtime.run_turn("test fail closed")

    assert events == ["authenticate"]
