"""Live provider-return boundary: Route B confers no local authenticity.

TIGHTEN_ONLY history (Corrective-003 / Window 22-RERUN-001).

Old expectation
    Two tests drove a three-argument ``model_response_authenticator`` callback and
    asserted (a) that it ran after the provider return and before response/usage
    recording, and (b) that it received the ephemeral
    :class:`LiveProviderReturnWindow` issued by the live frame (``windows ==
    [None]`` for an anonymous round).  A third test asserted the window type was a
    real capability object rather than a naming convention.

Old authority mechanism
    ``aios_core.runtime.live_return.open_live_provider_return_window`` +
    ``register_handler_return`` + ``LiveProviderReturnWindow._issue`` +
    ``_ISSUE_SENTINEL`` / ``_OPEN_WINDOWS`` / ``_HANDLER_RETURNS`` /
    ``_ACTIVE_WINDOW``, consumed by
    ``BackgroundModelAttemptStore.record_live_provider_return``.

Why that mechanism is unsafe (BLK-W20-001)
    ``RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW``
    / root cause ``TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE``.  The
    issuance helpers were ordinary public module functions, so any process-local
    recovery caller could issue its own window, declare its own bytes
    "handler-returned", mint a durable trusted receipt + exact handoff, complete
    and meter an attempt that must have stayed ``in_doubt``, and poison a later
    genuine RSA trusted return.  Frozen reviewer probes ``IA20-MINT-003``,
    ``IA20-MINT-004``, ``IA20-OBJGRAPH-002`` and ``IA20-WINDOW-001`` all failed on
    the frozen candidate ``fec30bd1495017bf13f08b0ef5b1e241dfb0e247``.

Replacement route
    Route B.  The local self-trusting live provider-return authority is removed
    entirely.  A live local handler return authenticates nothing and mints nothing
    durable.  Durable trusted provider/late return is produced only by a durable
    external verifier bound before the provider boundary plus a genuine external
    cryptographic proof (``BackgroundModelAttemptStore.attach_late_trusted_return``),
    which is exercised by
    ``tests/integration/test_core_background_late_trusted_return_corrective_001.py``
    and by the frozen Window 17 / Window 20 reviewer probes.

What was deleted / what is equal-or-stronger
    Deleted: the assertion that a live-return *authenticator* callback exists and
    is ordered before recording, and the assertion that it receives a live
    authority window.  Both asserted the presence of the adjudicated-unsafe
    authority, so keeping them would have required keeping the oracle.
    Added (strictly stronger): mechanical assertions that no live-return
    authenticity hook can be installed at all, that the provider handler and every
    remaining callback receive no authority object, that the decommissioned
    window type cannot be constructed / copied / pickled and carries no issuance
    machinery, and that the tombstone module exposes no registry, no sentinel and
    no handler-return map for reflection to reach.
    Kept (unchanged): the downstream fail-closed ordering property -- a callback
    that raises still prevents metering and still prevents any response from
    escaping -- now pinned on ``model_response_recorder``.

Exactly-once / provenance / crash / truthfulness
    Not weakened here: those properties live in the store and are covered by the
    Route B integration tests and the frozen reviewer probes (Suite B
    ``IA20-EXACTONCE-001`` and W17 ``IA17-RACE-CRASH-001`` /
    ``IA17-SIGKILL-001`` remain green).
"""

from __future__ import annotations

import copy
import pickle

import pytest

from aios_core.runtime import live_return as live_return_module
from aios_core.runtime.capabilities import CapabilityRegistry
from aios_core.runtime.cognitive_runtime import CognitiveRuntime, ModelDirective
from aios_core.runtime.live_return import LiveProviderReturnWindow


def test_no_live_return_authenticity_hook_can_be_installed_at_all():
    """Route B: there is no live-return authenticity callback to order or satisfy.

    Stronger than the old ordering assertion: instead of pinning *when* a local
    authenticity hook runs, this pins that such a hook cannot exist, so no local
    caller can be handed -- or hand itself -- provider-return authenticity.
    """

    events: list[str] = []
    authority_like: list[object] = []

    def model(_snapshot):
        events.append("provider_return")
        return ModelDirective(response="live reply that authenticates nothing")

    def record(_snapshot, directive):
        # The recorder receives exactly two arguments and no authority object.
        authority_like.append(directive)
        events.append("record_response")

    runtime = CognitiveRuntime(
        registry=CapabilityRegistry(),
        model_handler=model,
        model_response_recorder=record,
        model_usage_recorder=lambda _snapshot, _directive: events.append("meter"),
    )

    # The historical hook is gone: installing it is a hard TypeError rather than a
    # silently ignored argument.
    with pytest.raises(TypeError):
        CognitiveRuntime(  # type: ignore[call-arg]
            registry=CapabilityRegistry(),
            model_handler=model,
            model_response_authenticator=lambda *args: None,
        )
    assert not hasattr(runtime, "model_response_authenticator")
    assert not hasattr(CognitiveRuntime, "_live_provider_return_window")
    assert not hasattr(live_return_module, "_live_provider_return_window")

    result = runtime.run_turn("test route b live return")

    assert result.response == "live reply that authenticates nothing"
    # Recording still precedes metering; nothing runs "before" it as an
    # authenticity gate, because no such gate exists any more.
    assert events == ["provider_return", "record_response", "meter"]
    # No callback ever receives a live authority object.
    assert not any(
        isinstance(value, LiveProviderReturnWindow) for value in authority_like
    )


def test_recorder_failure_prevents_metering_and_any_response_output():
    """Fail-closed ordering is preserved on the surviving durable writer."""

    events: list[str] = []

    def reject(_snapshot, _directive):
        events.append("record_response")
        raise RuntimeError("durable response recording refused")

    runtime = CognitiveRuntime(
        registry=CapabilityRegistry(),
        model_handler=lambda _snapshot: ModelDirective(response="must not escape"),
        model_response_recorder=reject,
        model_usage_recorder=lambda _snapshot, _directive: events.append("meter"),
    )

    with pytest.raises(RuntimeError, match="durable response recording refused"):
        runtime.run_turn("test fail closed")

    assert events == ["record_response"]


def test_handler_failure_is_reported_to_the_failure_recorder_without_minting():
    """A provider exception still routes to the failure recorder, mints nothing."""

    events: list[str] = []

    def exploding_handler(_snapshot):
        raise ValueError("provider blew up")

    runtime = CognitiveRuntime(
        registry=CapabilityRegistry(),
        model_handler=exploding_handler,
        model_failure_recorder=lambda _s, exc, not_submitted: events.append(
            f"failure:{type(exc).__name__}:{not_submitted}"
        ),
        model_response_recorder=lambda _s, _d: events.append("record_response"),
        model_usage_recorder=lambda _s, _d: events.append("meter"),
    )

    with pytest.raises(ValueError, match="provider blew up"):
        runtime.run_turn("test handler failure")

    assert events == ["failure:ValueError:False"]


def test_decommissioned_window_type_is_not_a_capability_object():
    """The retained type is an inert tombstone, not an authority."""

    with pytest.raises(TypeError):
        LiveProviderReturnWindow()  # type: ignore[call-arg]
    assert LiveProviderReturnWindow.__module__ == "aios_core.runtime.live_return"

    marker = live_return_module._inert_marker("bgattempt_probe")
    assert isinstance(marker, LiveProviderReturnWindow)
    # Non-copyable and non-serializable: nothing can be cloned out of a frame.
    for operation in (
        lambda: copy.copy(marker),
        lambda: copy.deepcopy(marker),
        lambda: pickle.dumps(marker),
    ):
        with pytest.raises(TypeError):
            operation()


def test_tombstone_module_exposes_no_issuance_machinery_for_reflection():
    """C3-2: reflection over the module yields no usable mint authority."""

    for removed in (
        "_ISSUE_SENTINEL",
        "_OPEN_WINDOWS",
        "_HANDLER_RETURNS",
        "consume_live_provider_return_window",
    ):
        assert not hasattr(live_return_module, removed), removed
    assert not hasattr(LiveProviderReturnWindow, "_issue")

    # The retained public names are inert: arming them changes nothing observable
    # and confers nothing, and the diagnostics snapshot says so mechanically.
    with live_return_module.open_live_provider_return_window(
        attempt_id="bgattempt_probe"
    ) as window:
        assert isinstance(window, LiveProviderReturnWindow)
        live_return_module.register_handler_return(
            window, ModelDirective(response="self-asserted bytes")
        )
        live_return_module.register_handler_return(window)
        live_return_module.register_handler_return()
        snapshot = live_return_module.live_return_authority_snapshot()
        assert snapshot["decommissioned"] is True
        assert snapshot["trust_conferred"] is False
        assert snapshot["open_windows"] == 0
        assert snapshot["pending_handler_returns"] == 0
        # No AUTHORITY is ever armed, even while the inert marker is on the stack.
        assert snapshot["armed_on_this_stack"] is False
        assert snapshot["inert_marker_on_this_stack"] is True
        assert (
            snapshot["durable_trusted_return_authority"]
            == "external_verifier_plus_genuine_proof_only"
        )
    assert live_return_module.LOCAL_LIVE_RETURN_AUTHORITY_DECOMMISSIONED is True
    after = live_return_module.live_return_authority_snapshot()
    assert after["open_windows"] == 0
    assert after["inert_marker_on_this_stack"] is False
    assert after["armed_on_this_stack"] is False
