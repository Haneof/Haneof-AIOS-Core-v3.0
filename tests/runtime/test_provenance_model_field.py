"""PM-PROVENANCE-MODEL-FIELD-001: provenance must name the serving model.

The request parameter is not evidence of which model answered. A live run
whose provenance echoes the request cannot be bound to any real model, which
is exactly how the Phase-C World ended up with provider/model NULL on all 47
attempts. These tests drive the real provider against a local SSE server and
assert the provenance records the ``model`` field the server returns — and
records an explicit ``UNKNOWN`` when the server returns none.
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


def _provider(port: int) -> GrokStreamingProvider:
    return GrokStreamingProvider(
        GrokProviderConfig(
            base_url=f"http://127.0.0.1:{port}",
            api_key="test-key",
            timeout_seconds=5.0,
        )
    )


def _run_stream_chat(lines: list[dict[str, Any]], model: str):
    server = _start_server(lines)
    port = server.server_address[1]
    _Recorder.payload = None
    try:
        provider = _provider(port)
        text, usage, provenance = provider.stream_chat(
            [{"role": "user", "content": "你好"}],
            model=model,
        )
        return text, usage, provenance, _Recorder.payload
    finally:
        server.shutdown()
        server.server_close()


def _run_stream_chat_with_tools(lines: list[dict[str, Any]], model: str):
    server = _start_server(lines)
    port = server.server_address[1]
    _Recorder.payload = None
    try:
        provider = _provider(port)
        completion = provider.stream_chat_with_tools(
            [{"role": "user", "content": "你好"}],
            model=model,
        )
        return completion, _Recorder.payload
    finally:
        server.shutdown()
        server.server_close()


def test_stream_chat_records_server_returned_model() -> None:
    """The server says grok-4.5 served it; provenance must say grok-4.5."""

    lines = [
        {
            "id": "chatcmpl-served-1",
            "model": "grok-4.5",
            "choices": [{"delta": {"content": "你好"}}],
        },
        {"choices": [{"finish_reason": "stop", "delta": {}}]},
    ]

    _, usage, provenance, payload = _run_stream_chat(lines, model="grok-4.7")

    assert payload is not None
    assert payload["model"] == "grok-4.7"  # the request really asked for 4.7
    assert provenance.model == "grok-4.5"  # the server says 4.5 served it
    # Usage and provenance must name the same serving model.
    assert usage.model == "grok-4.5"
    assert provenance.provider == "grok"
    assert provenance.request_id == "chatcmpl-served-1"


def test_stream_chat_model_unknown_when_server_omits_model() -> None:
    """No model field anywhere in the stream: say UNKNOWN, never echo."""

    lines = [
        {
            "id": "chatcmpl-no-model",
            "choices": [{"delta": {"content": "你好"}}],
        },
        {"choices": [{"finish_reason": "stop", "delta": {}}]},
    ]

    _, usage, provenance, payload = _run_stream_chat(lines, model="grok-4.7")

    assert payload is not None
    assert payload["model"] == "grok-4.7"
    assert provenance.model == "UNKNOWN"
    assert usage.model == "UNKNOWN"
    assert provenance.request_id == "chatcmpl-no-model"


def test_stream_chat_late_model_field_still_counts() -> None:
    """A model field that first appears on a later chunk still binds."""

    lines = [
        {"choices": [{"delta": {"content": "你"}}]},
        {
            "id": "chatcmpl-late",
            "model": "grok-4.5",
            "choices": [{"delta": {"content": "好"}}],
        },
        {"choices": [{"finish_reason": "stop", "delta": {}}]},
    ]

    _, _, provenance, _ = _run_stream_chat(lines, model="grok-4.7")

    assert provenance.model == "grok-4.5"
    assert provenance.request_id == "chatcmpl-late"


def test_stream_chat_blank_model_field_is_ignored() -> None:
    """A blank model string is not a model name; it must not be recorded."""

    lines = [
        {
            "id": "chatcmpl-blank",
            "model": "   ",
            "choices": [{"delta": {"content": "你好"}}],
        },
        {"choices": [{"finish_reason": "stop", "delta": {}}]},
    ]

    _, _, provenance, _ = _run_stream_chat(lines, model="grok-4.7")

    assert provenance.model == "UNKNOWN"


def test_stream_chat_with_tools_records_server_returned_model() -> None:
    """The tools path has its own provenance build; it must bind the same way."""

    lines = [
        {
            "id": "chatcmpl-tools-1",
            "model": "grok-4.5",
            "choices": [{"delta": {"content": "记住了。"}}],
        },
        {"choices": [{"finish_reason": "stop", "delta": {}}]},
    ]

    completion, payload = _run_stream_chat_with_tools(lines, model="grok-4.7")

    assert payload is not None
    assert payload["model"] == "grok-4.7"
    assert completion.provenance.model == "grok-4.5"
    assert completion.provenance.request_id == "chatcmpl-tools-1"


def test_stream_chat_with_tools_model_unknown_when_server_omits_model() -> None:
    lines = [
        {
            "id": "chatcmpl-tools-no-model",
            "choices": [{"delta": {"content": "记住了。"}}],
        },
        {"choices": [{"finish_reason": "stop", "delta": {}}]},
    ]

    completion, _ = _run_stream_chat_with_tools(lines, model="grok-4.7")

    assert completion.provenance.model == "UNKNOWN"
    assert completion.provenance.request_id == "chatcmpl-tools-no-model"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
