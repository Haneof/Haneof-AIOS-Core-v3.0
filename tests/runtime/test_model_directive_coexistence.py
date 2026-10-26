"""T07: ModelDirective may answer and request capabilities in the same turn.

The old invariant — "a directive cannot request capabilities and terminate
simultaneously" — had zero test coverage and forbade the native-tools shape where a
model writes a durable fact and greets the user in one response. These tests pin the
relaxed contract and the two turn-termination rules it unlocks:

* response + only writes  -> execute the writes, then terminate (no extra round)
* response + any read     -> execute the calls, feed the results back, ask again
"""

from __future__ import annotations

import pytest

from aios_core.runtime.capabilities import (
    CapabilityCall,
    CapabilityKind,
    CapabilityRegistry,
    CapabilitySpec,
)
from aios_core.runtime.cognitive_runtime import CognitiveRuntime, ModelDirective


def test_directive_allows_response_with_calls():
    directive = ModelDirective(
        response="你好，我记住了。",
        capability_calls=(CapabilityCall(name="commit_claim", arguments={"content": "老王在东莞"}),),
    )
    assert directive.response == "你好，我记住了。"
    assert len(directive.capability_calls) == 1


def test_directive_rejects_silence_with_response():
    with pytest.raises(ValueError):
        ModelDirective(response="不该同时静默", silence=True)


def test_directive_rejects_silence_with_calls():
    with pytest.raises(ValueError):
        ModelDirective(
            silence=True,
            capability_calls=(CapabilityCall(name="commit_claim", arguments={}),),
        )


def test_directive_rejects_empty():
    with pytest.raises(ValueError):
        ModelDirective()


def test_response_with_only_writes_executes_then_terminates():
    registry = CapabilityRegistry()
    executed = []
    registry.register(
        CapabilitySpec(
            name="commit_claim",
            description="commit a derived claim",
            kind=CapabilityKind.WRITE,
            side_effecting=True,
        ),
        lambda content: executed.append(content) or {"committed": True},
    )

    def model(snapshot):
        # One round: greet AND persist, together.
        return ModelDirective(
            response="你好，我记住了。",
            capability_calls=(
                CapabilityCall(name="commit_claim", arguments={"content": "老王在东莞"}),),
        )

    runtime = CognitiveRuntime(
        registry=registry,
        model_handler=model,
        side_effect_authorizer=lambda spec, call, snapshot: spec.name == "commit_claim",
    )
    result = runtime.run_turn("我叫老王，在东莞")

    # The write landed AND the response was returned — no second model round.
    assert executed == ["老王在东莞"]
    assert result.capability_history[0].ok is True
    assert result.capability_history[0].name == "commit_claim"
    assert result.response == "你好，我记住了。"
    assert result.model_rounds == 1
    assert result.termination_reason == "responded"


def test_response_with_a_read_rounds_again_to_digest_result():
    registry = CapabilityRegistry()
    registry.register(
        CapabilitySpec(
            name="search_world",
            description="return candidate memories",
            kind=CapabilityKind.READ,
        ),
        lambda query: [{"object_id": "obs_1", "excerpt": f"关于 {query} 的旧事"}],
    )

    def model(snapshot):
        if not snapshot.capability_history:
            # Reply text arrives with a read request; it must not short-circuit the
            # read, and it is superseded once the read result comes back.
            return ModelDirective(
                response="我先查一下。",
                capability_calls=(CapabilityCall(name="search_world", arguments={"query": "老王"}),),
            )
        return ModelDirective(response="查到了：obs_1 是关于老王的旧事。")

    result = CognitiveRuntime(registry=registry, model_handler=model).run_turn("老王那事后来怎么样？")

    assert result.capability_history[0].name == "search_world"
    assert result.capability_history[0].ok is True
    assert result.response == "查到了：obs_1 是关于老王的旧事。"
    # One round for the read, one round to synthesize the answer.
    assert result.model_rounds == 2


def test_response_with_writes_is_exempt_from_last_round_fail_closed():
    registry = CapabilityRegistry()
    executed = []
    registry.register(
        CapabilitySpec(
            name="commit_claim",
            description="commit a derived claim",
            kind=CapabilityKind.WRITE,
            side_effecting=True,
        ),
        lambda content: executed.append(content) or {"committed": True},
    )

    def model(snapshot):
        return ModelDirective(
            response="记下了。",
            capability_calls=(CapabilityCall(name="commit_claim", arguments={"content": "名字：老王"}),),
        )

    runtime = CognitiveRuntime(
        registry=registry,
        model_handler=model,
        side_effect_authorizer=lambda spec, call, snapshot: True,
    )
    # max_model_rounds=1 makes this the final allowed round.
    result = runtime.run_turn("我叫老王", max_model_rounds=1)

    # Not a loop: the write lands and the turn still responds.
    assert executed == ["名字：老王"]
    assert result.response == "记下了。"
    assert result.termination_reason == "responded"


def test_bare_calls_on_last_round_still_fail_closed():
    registry = CapabilityRegistry()
    registry.register(
        CapabilitySpec(
            name="search_world",
            description="return candidate memories",
            kind=CapabilityKind.READ,
        ),
        lambda query: [{"object_id": "obs_1"}],
    )

    def model(snapshot):
        return ModelDirective(
            capability_calls=(CapabilityCall(name="search_world", arguments={"query": "老王"}),),
        )

    result = CognitiveRuntime(registry=registry, model_handler=model).run_turn(
        "查一下", max_model_rounds=1
    )

    # Bare tool request with no response: the final round does not execute it and
    # does not start another loop.
    assert result.response is None
    assert result.capability_history == ()
    assert result.termination_reason == "model_round_budget_exhausted"
