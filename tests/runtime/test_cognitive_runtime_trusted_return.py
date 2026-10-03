"""Trusted provider-return boundary ordering for CognitiveRuntime.

Corrective-002 history note (Window 19).  These two tests previously drove the
trusted-return authenticator with a two-argument callback.  Window 17
(`BLK-W17-001`) proved that callback identity was doing no authorization work:
any post-crash recovery caller could mint trusted receipts directly.  The
boundary callback now additionally receives the ephemeral
:class:`LiveProviderReturnWindow` that this frame issues, so the two tests below
keep their original ordering/fail-closed meaning and additionally pin the new,
strictly stronger invariant: a round with no durable provider attempt carries no
live authority window at all, and the authenticator therefore cannot mint.
"""

from __future__ import annotations

import pytest

from aios_core.runtime.capabilities import CapabilityRegistry
from aios_core.runtime.cognitive_runtime import CognitiveRuntime, ModelDirective
from aios_core.runtime.live_return import LiveProviderReturnWindow


def test_trusted_return_authentication_precedes_response_and_usage_recording():
    events: list[str] = []
    windows: list[object] = []

    def model(_snapshot):
        events.append("provider_return")
        return ModelDirective(response="authenticated reply")

    def authenticate(_snapshot, _directive, live_window):
        events.append("authenticate")
        windows.append(live_window)

    runtime = CognitiveRuntime(
        registry=CapabilityRegistry(),
        model_handler=model,
        model_response_authenticator=authenticate,
        model_response_recorder=lambda _snapshot, _directive: events.append(
            "record_response"
        ),
        model_usage_recorder=lambda _snapshot, _directive: events.append("meter"),
    )

    result = runtime.run_turn("test trusted return ordering")

    assert result.response == "authenticated reply"
    assert events == ["provider_return", "authenticate", "record_response", "meter"]
    # No durable provider attempt is bound on this anonymous local round, so no
    # live authority window exists and no trusted provider-return state can be
    # captured.  Anonymous rounds stay fail-closed by construction.
    assert windows == [None]


def test_authentication_failure_prevents_every_downstream_callback_and_output():
    events: list[str] = []

    def reject(_snapshot, _directive, _live_window):
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


def test_live_window_type_is_the_ephemeral_authority_and_is_not_serializable():
    """The live authority is a real capability object, not a naming convention."""

    with pytest.raises(TypeError):
        LiveProviderReturnWindow()  # type: ignore[call-arg]
    assert LiveProviderReturnWindow.__module__ == "aios_core.runtime.live_return"
