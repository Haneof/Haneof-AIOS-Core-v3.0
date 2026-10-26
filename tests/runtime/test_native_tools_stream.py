"""T06: reading native tool calls off a stream.

The text protocol forced the model to choose between answering the user and
persisting what it learned, because the response was either a JSON block or prose,
never both. Real endpoints answered and never wrote. The ``tools`` protocol is the
interface they were actually trained on, and it does not impose that choice — one
response can carry a reply *and* a write.

Reading it correctly is the whole job here: a tool's name arrives once, its
arguments arrive in fragments across later deltas, and two calls can interleave in
one stream. Getting any of that wrong looks exactly like the failure we are fixing
— a write that never landed, for reasons nobody can see.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from aios_core.runtime.grok_provider import (
    GrokProviderConfig,
    GrokStreamingProvider,
)

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "commit_ai_world_claim",
            "description": "Persist a durable fact about the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "statement": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                },
                "required": ["statement", "confidence"],
            },
        },
    }
]


class _Recorder:
    payload: dict[str, Any] | None = None


def _start_server(lines: list[dict[str, Any]]) -> HTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", 0) or 0)
            _Recorder.payload = json.loads(self.rfile.read(length) or b"{}")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for line in lines:
                self.wfile.write(b"data: " + json.dumps(line).encode() + b"\n\n")
            self.wfile.write(b"data: [DONE]\n\n")

        def log_message(self, *args: Any) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _run(lines: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None):
    server = _start_server(lines)
    port = server.server_address[1]
    _Recorder.payload = None
    try:
        provider = GrokStreamingProvider(
            GrokProviderConfig(
                base_url=f"http://127.0.0.1:{port}",
                api_key="test-key",
                timeout_seconds=5.0,
            )
        )
        completion = provider.stream_chat_with_tools(
            [{"role": "user", "content": "我叫老王"}],
            tools=tools,
        )
        return completion, _Recorder.payload
    finally:
        server.shutdown()
        server.server_close()


def _tool_delta(index: int, name: str | None = None, arguments: str | None = None,
                call_id: str | None = None) -> dict[str, Any]:
    function: dict[str, Any] = {}
    if name is not None:
        function["name"] = name
    if arguments is not None:
        function["arguments"] = arguments
    fragment: dict[str, Any] = {"index": index, "function": function}
    if call_id is not None:
        fragment["id"] = call_id
        fragment["type"] = "function"
    return {"choices": [{"delta": {"tool_calls": [fragment]}}]}


def test_arguments_arrive_in_fragments_and_reassemble() -> None:
    """One argument object spread over three deltas must survive as one JSON object."""

    lines = [
        _tool_delta(0, name="commit_ai_world_claim", arguments="", call_id="call_1"),
        _tool_delta(0, arguments='{"statement": "老王在东莞做23cm柔性屏手环"'),
        _tool_delta(0, arguments=', "confidence": 0.9}'),
        {"choices": [{"finish_reason": "tool_calls", "delta": {}}]},
    ]

    completion, _ = _run(lines, tools=_TOOLS)

    assert len(completion.tool_calls) == 1
    call = completion.tool_calls[0]
    assert call.name == "commit_ai_world_claim"
    assert call.arguments == {
        "statement": "老王在东莞做23cm柔性屏手环",
        "confidence": 0.9,
    }
    assert call.arguments_parse_error is None
    assert call.call_id == "call_1"
    assert completion.finish_reason == "tool_calls"


def test_reply_and_write_coexist_in_one_response() -> None:
    """The point of the whole change: answering does not have to cost the write."""

    lines = [
        {"choices": [{"delta": {"content": "记住了，老王。"}}]},
        _tool_delta(0, name="commit_ai_world_claim", arguments="", call_id="call_1"),
        _tool_delta(0, arguments='{"statement": "用户叫老王", "confidence": 0.95}'),
        {"choices": [{"finish_reason": "tool_calls", "delta": {}}]},
    ]

    completion, _ = _run(lines, tools=_TOOLS)

    assert completion.text == "记住了，老王。"
    assert len(completion.tool_calls) == 1
    assert completion.tool_calls[0].arguments["statement"] == "用户叫老王"


def test_two_interleaved_calls_stay_separate() -> None:
    """Index-keyed accumulation is what keeps a second call from eating the first."""

    lines = [
        _tool_delta(0, name="commit_ai_world_claim", arguments="", call_id="call_a"),
        _tool_delta(1, name="search_world", arguments="", call_id="call_b"),
        _tool_delta(0, arguments='{"statement": "在东莞"'),
        _tool_delta(1, arguments='{"query": "23cm手环"'),
        _tool_delta(0, arguments=', "confidence": 0.9}'),
        _tool_delta(1, arguments="}"),
        {"choices": [{"finish_reason": "tool_calls", "delta": {}}]},
    ]

    completion, _ = _run(lines, tools=_TOOLS)

    assert [call.name for call in completion.tool_calls] == [
        "commit_ai_world_claim",
        "search_world",
    ]
    assert completion.tool_calls[0].arguments == {"statement": "在东莞", "confidence": 0.9}
    assert completion.tool_calls[1].arguments == {"query": "23cm手环"}


def test_malformed_arguments_are_reported_not_dropped() -> None:
    """A dropped call is invisible: the write simply never happens and nothing red shows.

    Carrying the raw text and the parse error means the turn can hand the failure
    back to the model for correction, the same way a rejected argument does.
    """

    lines = [
        _tool_delta(0, name="commit_ai_world_claim", arguments='{"statement": "unclosed', call_id="c"),
        {"choices": [{"finish_reason": "tool_calls", "delta": {}}]},
    ]

    completion, _ = _run(lines, tools=_TOOLS)

    assert len(completion.tool_calls) == 1
    call = completion.tool_calls[0]
    assert call.arguments_parse_error is not None
    assert "not valid JSON" in call.arguments_parse_error
    assert call.arguments_raw == '{"statement": "unclosed'
    # Still named, so the turn knows what the model was attempting.
    assert call.name == "commit_ai_world_claim"


def test_tools_are_only_advertised_when_given() -> None:
    lines = [{"choices": [{"delta": {"content": "好的"}}]}, {"choices": [{"finish_reason": "stop", "delta": {}}]}]

    _, with_tools = _run(lines, tools=_TOOLS)
    assert "tools" in with_tools
    assert with_tools["tools"][0]["function"]["name"] == "commit_ai_world_claim"

    _, without_tools = _run(lines)
    assert "tools" not in without_tools


def test_no_tool_call_yields_an_empty_tuple_and_the_text() -> None:
    lines = [
        {"choices": [{"delta": {"content": "今天东莞多云。"}}]},
        {"choices": [{"finish_reason": "stop", "delta": {}}]},
    ]

    completion, _ = _run(lines, tools=_TOOLS)

    assert completion.text == "今天东莞多云。"
    assert completion.tool_calls == ()
    assert completion.finish_reason == "stop"


def test_usage_and_provenance_are_recorded() -> None:
    lines = [
        {"choices": [{"delta": {"content": "明白"}}]},
        {"choices": [{"finish_reason": "stop", "delta": {}}]},
        {
            "id": "req-abc",
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 8,
                "total_tokens": 128,
                "prompt_tokens_details": {"cached_tokens": 100},
            },
        },
    ]

    completion, _ = _run(lines, tools=_TOOLS)

    assert completion.usage.input_tokens == 120
    assert completion.usage.output_tokens == 8
    assert completion.usage.total_tokens == 128
    # Prefix-cache savings stay invisible in the ledger unless they are parsed.
    assert completion.usage.cached_input_tokens == 100
    assert completion.provenance.request_id == "req-abc"
    assert completion.provenance.model  # recorded rather than empty


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
