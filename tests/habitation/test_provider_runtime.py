from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from aios_core.runtime.capabilities import CapabilityResult
from aios_core.runtime.cognitive_runtime import RuntimeSnapshot

from .current_core import CurrentCoreHabitationTarget
from .harness import HabitationRunner, HabitationScenario, LifeEvent
from .io import run_artifact_json
from .provider_runtime import (
    ProviderConfig,
    ProviderProtocolError,
    ProviderRoundSummaryHandler,
    ProviderResidentHandler,
    ProviderClient,
    capability_input_json_schema,
    provider_tools,
)


NOW = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)


CATALOG = (
    {
        "name": "search_world",
        "description": "Search the durable AIOS world.",
        "kind": "read",
        "input_schema": {
            "query": "string",
            "limit": "integer?",
        },
        "hard_boundary": False,
        "side_effecting": False,
    },
)


def _snapshot(
    round_index: int,
    history: tuple[CapabilityResult, ...] = (),
) -> RuntimeSnapshot:
    return RuntimeSnapshot(
        user_input="What did I say about Seattle?",
        wake_reason="user_interaction",
        cockpit={"memory": [], "task_context": {}},
        capability_catalog=CATALOG,
        capability_history=history,
        round_index=round_index,
        remaining_tool_rounds=max(0, 4 - round_index),
    )


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, payload, timeout):
        self.calls.append(
            {
                "url": url,
                "headers": dict(headers),
                "payload": json.loads(json.dumps(payload)),
                "timeout": timeout,
            }
        )
        if not self.responses:
            raise AssertionError("unexpected provider request")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_capability_shorthand_translates_to_closed_json_schema() -> None:
    schema = capability_input_json_schema(
        {
            "query": "string",
            "limit": "integer?",
            "confidence": "number[0,1]",
            "when": "ISO-8601 datetime?",
            "refs": "array[{object_id:string,revision:integer}]",
            "domain": "user_understanding|relationship|self",
            "cost": "object[number]?",
            "dimension": "string starting dim:",
        }
    )

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "query",
        "confidence",
        "refs",
        "domain",
        "dimension",
    }
    assert schema["properties"]["confidence"] == {
        "type": "number",
        "minimum": 0.0,
        "maximum": 1.0,
    }
    assert schema["properties"]["when"]["format"] == "date-time"
    assert schema["properties"]["refs"]["items"]["required"] == [
        "object_id",
        "revision",
    ]
    assert schema["properties"]["domain"]["enum"] == [
        "user_understanding",
        "relationship",
        "self",
    ]
    assert schema["properties"]["cost"]["additionalProperties"] == {
        "type": "number"
    }
    assert schema["properties"]["dimension"]["pattern"] == "^dim:"

    with pytest.raises(ValueError, match="unsupported capability schema"):
        capability_input_json_schema({"bad": "magic<unknown>"})


def test_provider_tool_shapes_keep_same_aios_contract() -> None:
    openai = provider_tools(CATALOG, provider="openai")[0]
    anthropic = provider_tools(CATALOG, provider="anthropic")[0]
    gemini = provider_tools(CATALOG, provider="gemini")[0]

    assert openai["name"] == anthropic["name"] == gemini["name"] == "search_world"
    assert openai["parameters"] == anthropic["input_schema"] == gemini["parameters"]
    assert openai["type"] == "function"
    assert gemini["type"] == "function"


def test_openai_responses_tool_loop_and_provenance() -> None:
    transport = FakeTransport(
        [
            {
                "id": "resp_1",
                "output": [
                    {
                        "type": "function_call",
                        "name": "search_world",
                        "call_id": "call_1",
                        "arguments": '{"query":"Seattle","limit":5}',
                    }
                ],
                "usage": {"input_tokens": 20, "output_tokens": 8},
            },
            {
                "id": "resp_2",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": "You mentioned Seattle."}
                        ],
                    }
                ],
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
        ]
    )
    client = ProviderClient(
        ProviderConfig(provider="openai", model="test-model"),
        transport=transport,
        api_key="secret-openai-test-key",
    )
    handler = ProviderResidentHandler(client)

    first = handler(_snapshot(0))
    assert len(first.capability_calls) == 1
    assert first.capability_calls[0].call_id == "call_1"
    assert first.usage is not None
    assert first.usage.total_tokens == 28
    assert first.usage.provider == "openai"
    assert first.usage.model == "test-model"
    assert first.usage.request_id == "resp_1"
    assert first.provenance is not None
    assert first.provenance.provider == "openai"
    assert first.provenance.model == "test-model"
    assert first.provenance.request_id == "resp_1"
    assert first.capability_calls[0].arguments["query"] == "Seattle"

    result = CapabilityResult(
        name="search_world",
        ok=True,
        data=[{"object_id": "obs-1", "excerpt": "Seattle trip"}],
        call_id="call_1",
    )
    second = handler(_snapshot(1, (result,)))
    assert second.response == "You mentioned Seattle."
    assert second.usage is not None
    assert second.usage.total_tokens == 15

    assert transport.calls[0]["payload"]["tools"][0]["name"] == "search_world"
    continuation = transport.calls[1]["payload"]
    assert continuation["previous_response_id"] == "resp_1"
    assert continuation["input"][0]["type"] == "function_call_output"
    assert continuation["input"][0]["call_id"] == "call_1"
    assert "instructions" in continuation

    provenance = handler.provenance_snapshot()
    assert provenance["provider"] == "openai"
    assert provenance["model"] == "test-model"
    assert len(provenance["requests"]) == 2
    assert "secret-openai-test-key" not in json.dumps(provenance)


def test_anthropic_messages_tool_loop_round_trips_tool_result() -> None:
    transport = FakeTransport(
        [
            {
                "id": "msg_1",
                "stop_reason": "tool_use",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "search_world",
                        "input": {"query": "Seattle"},
                    }
                ],
                "usage": {"input_tokens": 15, "output_tokens": 6},
            },
            {
                "id": "msg_2",
                "stop_reason": "end_turn",
                "content": [
                    {"type": "text", "text": "Claude continued from the world."}
                ],
                "usage": {"input_tokens": 9, "output_tokens": 7},
            },
        ]
    )
    client = ProviderClient(
        ProviderConfig(provider="anthropic", model="test-claude"),
        transport=transport,
        api_key="secret-anthropic-test-key",
    )
    handler = ProviderResidentHandler(client)

    first = handler(_snapshot(0))
    assert first.capability_calls[0].call_id == "toolu_1"
    assert first.usage is not None
    assert first.usage.total_tokens == 21
    assert first.usage.provider == "anthropic"
    assert first.usage.model == "test-claude"
    assert first.usage.request_id == "msg_1"
    assert first.provenance is not None
    assert first.provenance.provider == "anthropic"
    assert first.provenance.model == "test-claude"
    assert first.provenance.request_id == "msg_1"

    result = CapabilityResult(
        name="search_world",
        ok=True,
        data={"hits": ["Seattle"]},
        call_id="toolu_1",
    )
    second = handler(_snapshot(1, (result,)))
    assert second.response == "Claude continued from the world."
    assert second.usage is not None
    assert second.usage.total_tokens == 16

    second_request = transport.calls[1]["payload"]
    assert second_request["messages"][-2]["role"] == "assistant"
    tool_result_message = second_request["messages"][-1]
    assert tool_result_message["role"] == "user"
    assert tool_result_message["content"][0]["type"] == "tool_result"
    assert tool_result_message["content"][0]["tool_use_id"] == "toolu_1"
    assert transport.calls[0]["headers"]["anthropic-version"] == "2023-06-01"


def test_gemini_interactions_tool_loop_uses_previous_interaction() -> None:
    transport = FakeTransport(
        [
            {
                "id": "interaction_1",
                "steps": [
                    {
                        "type": "function_call",
                        "id": "fc_1",
                        "name": "search_world",
                        "arguments": {"query": "Seattle"},
                    }
                ],
                "usage": {
                    "total_input_tokens": 12,
                    "total_output_tokens": 0,
                    "total_tokens": 12,
                },
            },
            {
                "id": "interaction_2",
                "steps": [],
                "output_text": "Gemini continued from the world.",
                "usage": {
                    "total_input_tokens": 0,
                    "total_output_tokens": 6,
                    "total_tokens": 6,
                },
            },
        ]
    )
    client = ProviderClient(
        ProviderConfig(provider="gemini", model="test-gemini"),
        transport=transport,
        api_key="secret-gemini-test-key",
    )
    handler = ProviderResidentHandler(client)

    first = handler(_snapshot(0))
    assert first.capability_calls[0].call_id == "fc_1"
    assert first.usage is not None
    assert first.usage.total_tokens == 12
    assert first.usage.provider == "gemini"
    assert first.usage.model == "test-gemini"
    assert first.usage.request_id == "interaction_1"
    assert first.provenance is not None
    assert first.provenance.provider == "gemini"
    assert first.provenance.model == "test-gemini"
    assert first.provenance.request_id == "interaction_1"

    result = CapabilityResult(
        name="search_world",
        ok=True,
        data={"hits": ["Seattle"]},
        call_id="fc_1",
    )
    second = handler(_snapshot(1, (result,)))
    assert second.response == "Gemini continued from the world."
    assert second.usage is not None
    assert second.usage.total_tokens == 6

    continuation = transport.calls[1]["payload"]
    assert continuation["previous_interaction_id"] == "interaction_1"
    assert continuation["input"][0]["type"] == "function_result"
    assert continuation["input"][0]["call_id"] == "fc_1"
    assert transport.calls[0]["headers"]["x-goog-api-key"] == "secret-gemini-test-key"





@pytest.mark.parametrize(
    ("provider", "model", "response", "response_id"),
    (
        (
            "openai",
            "no-usage-openai",
            {
                "id": "resp_no_usage",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "done"}],
                    }
                ],
            },
            "resp_no_usage",
        ),
        (
            "anthropic",
            "no-usage-claude",
            {
                "id": "msg_no_usage",
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "done"}],
            },
            "msg_no_usage",
        ),
        (
            "gemini",
            "no-usage-gemini",
            {
                "id": "interaction_no_usage",
                "steps": [],
                "output_text": "done",
            },
            "interaction_no_usage",
        ),
    ),
)
def test_provider_response_keeps_auditable_identity_when_usage_is_unknown(
    provider,
    model,
    response,
    response_id,
) -> None:
    client = ProviderClient(
        ProviderConfig(provider=provider, model=model),
        transport=FakeTransport([response]),
        api_key="secret-test-key",
    )
    directive = ProviderResidentHandler(client)(_snapshot(0))

    assert directive.response == "done"
    assert directive.usage is None
    assert directive.provenance is not None
    assert directive.provenance.provider == provider
    assert directive.provenance.model == model
    assert directive.provenance.request_id == response_id


def test_provider_round_summary_uses_same_secret_safe_provenance() -> None:
    transport = FakeTransport(
        [
            {
                "id": "summary_resp",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "User discussed the Seattle schedule.",
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 5, "output_tokens": 5},
            }
        ]
    )
    client = ProviderClient(
        ProviderConfig(provider="openai", model="summary-model"),
        transport=transport,
        api_key="summary-secret",
    )
    summary = ProviderRoundSummaryHandler(client)

    class Request:
        def as_model_input(self):
            return {
                "instruction": "summarize only raw dialogue",
                "messages": [{"role": "user", "text": "Seattle"}],
            }

    assert summary(Request()) == "User discussed the Seattle schedule."
    provenance = summary.provenance_snapshot()
    assert provenance["requests"][0]["purpose"] == "round_summary"
    assert "summary-secret" not in json.dumps(provenance)


def test_current_core_run_artifact_contains_provider_provenance_not_secret(tmp_path) -> None:
    transport = FakeTransport(
        [
            {
                "id": "resp_final",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Recorded."}],
                    }
                ],
                "usage": {"input_tokens": 11, "output_tokens": 2},
            }
        ]
    )
    client = ProviderClient(
        ProviderConfig(provider="openai", model="resident-test"),
        transport=transport,
        api_key="NEVER_SERIALIZE_THIS_KEY",
    )
    handler = ProviderResidentHandler(client)
    target = CurrentCoreHabitationTarget(
        model_id=handler.model_id,
        subject_id="synthetic-provider-user",
        db_path=tmp_path / "provider.sqlite",
        model_handler=handler,
    )
    scenario = HabitationScenario(
        scenario_id="provider-provenance",
        subject_id="synthetic-provider-user",
        events=(
            LifeEvent(
                event_id="chat-1",
                occurred_at=NOW,
                channel="conversation",
                payload="Please remember the Seattle plan.",
                metadata={"session": "s1"},
            ),
        ),
    )

    run = HabitationRunner().run(
        scenario=scenario,
        model_id=handler.model_id,
        target=target,
    )
    artifact = run_artifact_json(scenario=scenario, run=run)

    assert '"provider": "openai"' in artifact
    assert '"model": "resident-test"' in artifact
    assert '"config_fingerprint": "sha256:' in artifact
    assert "NEVER_SERIALIZE_THIS_KEY" not in artifact


def test_provider_protocol_rejects_missing_call_id_on_continuation() -> None:
    transport = FakeTransport(
        [
            {
                "id": "resp_1",
                "output": [
                    {
                        "type": "function_call",
                        "name": "search_world",
                        "call_id": "call_1",
                        "arguments": '{"query":"Seattle"}',
                    }
                ],
            }
        ]
    )
    handler = ProviderResidentHandler(
        ProviderClient(
            ProviderConfig(provider="openai", model="test-model"),
            transport=transport,
            api_key="test-key",
        )
    )
    handler(_snapshot(0))

    with pytest.raises(ProviderProtocolError, match="missing call_id"):
        handler(
            _snapshot(
                1,
                (
                    CapabilityResult(
                        name="search_world",
                        ok=True,
                        data={"hits": []},
                        call_id=None,
                    ),
                ),
            )
        )



def test_gemini_without_total_token_count_does_not_guess_usage() -> None:
    transport = FakeTransport(
        [
            {
                "id": "interaction_no_total",
                "steps": [],
                "output_text": "done",
                "usage_metadata": {
                    "prompt_token_count": 12,
                    "candidates_token_count": 3,
                },
            }
        ]
    )
    client = ProviderClient(
        ProviderConfig(provider="gemini", model="test-gemini"),
        transport=transport,
        api_key="secret-gemini-test-key",
    )
    directive = ProviderResidentHandler(client)(_snapshot(0))
    assert directive.response == "done"
    assert directive.usage is None



def test_gemini_legacy_usage_metadata_remains_readable() -> None:
    transport = FakeTransport(
        [
            {
                "id": "interaction_legacy_usage",
                "steps": [],
                "output_text": "legacy-compatible",
                "usage_metadata": {
                    "prompt_token_count": 8,
                    "candidates_token_count": 2,
                    "total_token_count": 10,
                },
            }
        ]
    )
    client = ProviderClient(
        ProviderConfig(provider="gemini", model="test-gemini"),
        transport=transport,
        api_key="secret-gemini-test-key",
    )
    directive = ProviderResidentHandler(client)(_snapshot(0))
    assert directive.response == "legacy-compatible"
    assert directive.usage is not None
    assert directive.usage.input_tokens == 8
    assert directive.usage.output_tokens == 2
    assert directive.usage.total_tokens == 10
