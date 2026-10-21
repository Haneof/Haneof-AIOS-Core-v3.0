"""Physical Multi-Model Habitation & Real Provider Integration Test Suite.

Constitutional Mandates Verified:
1. Iron Rule 1: High-quality reasoning, live SSE chunk aggregation.
2. Iron Rule 2: Byte-immutable historical records across multi-model transitions.
3. Iron Rule 3: P0 critical safety bypasses cloud LLM with latency <= 50ms.
4. C15 R6 Reconciliation: Live execution of grok-4.7 and grok-4.5 across
   session boundaries without synthetic stubs.

CI GATING (added 2026-10-20, PM-AUDIT remediation)
-------------------------------------------------
This module contains two classes of tests that must NOT be conflated:

* **Hermetic tests** (always run): scheduler routing, P0 emergency bypass and
  SSE stream parsing. They use a local loopback stub server or an injected
  executor, so they are deterministic and network-free.
* **Live provider tests** (opt-in): they talk to a real OpenAI-compatible
  endpoint and therefore cannot run on a hosted CI runner. They only execute
  when ``AIOS_LIVE_PROVIDER=1`` is set *and* the endpoint is reachable.

Historically these live tests ran unconditionally, which turned every CI run
red with ``ConnectionRefusedError`` while the author's local machine (with a
127.0.0.1 forwarder) reported "4/4 PASS". That divergence is exactly what the
gating below removes.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from aios_core.contracts.enums import SourceClass, WakePriority
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
    RuntimeSnapshot,
)
from aios_core.runtime.edge_model_scheduler import (
    ModelTier,
    create_production_edge_scheduler,
)
from aios_core.runtime.grok_provider import (
    GrokProviderConfig,
    GrokStreamingProvider,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore

LIVE_ENABLED = os.environ.get("AIOS_LIVE_PROVIDER") == "1"
LIVE_API_KEY = os.environ.get("AIOS_GROK_API_KEY", "")

live_only = pytest.mark.skipif(
    not LIVE_ENABLED,
    reason=(
        "live provider test: set AIOS_LIVE_PROVIDER=1 and provide a reachable "
        "OpenAI-compatible endpoint (AIOS_GROK_BASE_URL) to run"
    ),
)


def live(fn):
    """Mark a test as needing a real endpoint, and skip it unless opted in.

    The ``live`` marker also lets CI exclude these tests explicitly (``-m "not
    live"``) in suites that assert a zero-skip receipt.
    """
    return pytest.mark.live(live_only(fn))


@pytest.fixture
def grok_provider() -> GrokStreamingProvider:
    return GrokStreamingProvider(
        GrokProviderConfig(api_key=LIVE_API_KEY or "live-test-placeholder")
    )


@pytest.fixture
def clean_world(tmp_path):
    db_path = tmp_path / "live_multimodel_world.sqlite"
    index_path = tmp_path / "live_multimodel_index.sqlite"
    store = SQLiteWorldStore(str(db_path))
    index = WorldSearchIndex(str(index_path), store=store)
    return store, index, db_path


class StubCloudProvider:
    """Network-free stand-in for GrokStreamingProvider.

    Only implements ``as_executor`` because that is the single seam the
    scheduler uses. Recording calls lets the test assert *routing*, which is
    the actual invariant under test, without depending on connectivity.
    """

    def __init__(self, reply: str = "ONLINE") -> None:
        self.reply = reply
        self.calls: list[tuple[str | None, str]] = []

    def as_executor(self, model: str | None = None):
        def _executor(prompt: str, context: dict) -> str:
            self.calls.append((model, prompt))
            return self.reply

        return _executor


# ---------------------------------------------------------------------------
# Hermetic: scheduler routing (no network)
# ---------------------------------------------------------------------------


def test_03_p0_emergency_bypass_offline():
    """Iron Rule 3: P0 critical safety short-circuits to the edge SLM under 50ms.

    Runs with a stub cloud executor so the assertion is about the bypass path
    itself, never about whether a network happens to be available.
    """
    stub = StubCloudProvider()
    scheduler = create_production_edge_scheduler(
        grok_provider=stub,
        cloud_timeout_ms=60000.0,
    )

    started = time.perf_counter()
    result = scheduler.dispatch(
        "用户心率骤降至 38bpm，加速度计检测到 12.5g 剧烈冲击碰撞！",
        priority=WakePriority.P0_CRITICAL_SAFETY,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    assert result.selected_tier == ModelTier.EDGE_SLM
    assert result.emergency_bypassed is True
    assert result.fallback_triggered is False
    assert result.latency_ms <= 50.0 or elapsed_ms <= 50.0
    assert "P0" in result.output_text or "紧急" in result.output_text
    assert stub.calls == [], "P0 emergency path must never reach the cloud executor"


def test_03b_routine_dispatch_routes_to_cloud_tier():
    """Routine turns route to the CLOUD_LLM tier with the primary model id.

    This is the assertion the original test_03 was making, but it previously
    relied on a live endpoint: when the endpoint was unreachable the scheduler
    correctly degraded to EDGE_SLM and the test failed for the *wrong* reason.
    Injecting the executor isolates the routing contract.
    """
    stub = StubCloudProvider(reply="心智连通，ONLINE。")
    scheduler = create_production_edge_scheduler(
        grok_provider=stub,
        cloud_timeout_ms=60000.0,
    )

    result = scheduler.dispatch(
        "心智连通性检测，请回复 ONLINE。",
        priority=WakePriority.P2_ROUTINE,
    )

    assert result.selected_tier == ModelTier.CLOUD_LLM
    assert result.model_id == "grok-4.7"
    assert result.fallback_triggered is False
    assert result.output_text == "心智连通，ONLINE。"
    assert len(stub.calls) == 1


def test_03c_offline_degrades_without_dropping_turn():
    """Offline degradation: no network -> edge SLM, turn still answered."""
    stub = StubCloudProvider()
    scheduler = create_production_edge_scheduler(
        grok_provider=stub,
        is_network_online=False,
    )

    result = scheduler.dispatch("随便聊聊。", priority=WakePriority.P2_ROUTINE)

    assert result.selected_tier == ModelTier.EDGE_SLM
    assert result.fallback_triggered is True
    assert result.output_text.strip() != ""
    assert stub.calls == []


# ---------------------------------------------------------------------------
# Hermetic: SSE stream parsing against a loopback stub endpoint
# ---------------------------------------------------------------------------


class _SSEStubHandler(BaseHTTPRequestHandler):
    """Emits an OpenAI-compatible SSE stream, including a usage-only tail chunk."""

    protocol_version = "HTTP/1.0"

    def do_POST(self):  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            payload = {}

        self.server.last_request = payload  # type: ignore[attr-defined]
        self.server.last_auth = self.headers.get("Authorization")  # type: ignore[attr-defined]

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        chunks = [
            {"id": "chatcmpl-stub-001", "choices": [{"delta": {"content": "AIOS"}}]},
            {"id": "chatcmpl-stub-001", "choices": [{"delta": {"content": "_ONLINE"}}]},
            {
                "id": "chatcmpl-stub-001",
                "choices": [],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 4,
                    "total_tokens": 16,
                },
            },
        ]
        for chunk in chunks:
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, *args):  # silence test output
        return


@pytest.fixture
def sse_stub_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _SSEStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_05_sse_stream_parsing_against_loopback_stub(sse_stub_server):
    """Aggregates chunked deltas, parses usage, and honours stream=True.

    Covers the streaming parser deterministically: the endpoint is a local
    loopback stub, so this runs on any CI runner without external network.
    """
    port = sse_stub_server.server_address[1]
    provider = GrokStreamingProvider(
        GrokProviderConfig(
            base_url=f"http://127.0.0.1:{port}/v1",
            api_key="stub-key-for-tests",
            timeout_seconds=10.0,
        )
    )

    text, usage, provenance = provider.stream_chat(
        [{"role": "user", "content": "Ping test."}],
        model="grok-4.7",
    )

    assert text == "AIOS_ONLINE"
    assert provenance.provider == "grok"
    assert provenance.model == "grok-4.7"
    assert provenance.request_id == "chatcmpl-stub-001"
    assert usage.input_tokens == 12
    assert usage.output_tokens == 4
    assert usage.total_tokens == 16
    assert usage.total_tokens >= usage.input_tokens + usage.output_tokens

    request = sse_stub_server.last_request
    assert request["stream"] is True
    assert request["stream_options"] == {"include_usage": True}
    assert request["model"] == "grok-4.7"
    assert sse_stub_server.last_auth == "Bearer stub-key-for-tests"


def test_05b_missing_api_key_fails_closed():
    """A provider with no credential must refuse to send a request."""
    provider = GrokStreamingProvider(
        GrokProviderConfig(api_key="", base_url="http://127.0.0.1:1/v1")
    )
    with pytest.raises(RuntimeError, match="AIOS_GROK_API_KEY"):
        provider.stream_chat([{"role": "user", "content": "hi"}], model="grok-4.7")


class _ReasoningSSEStubHandler(BaseHTTPRequestHandler):
    """Emits a thinking-model usage block: total >> input + visible output.

    Gemini 3 系列的 usage 里 total_tokens 含思考消耗，completion_tokens 只算
    最终可见输出。这里用实测数据（16 / 8 / 312）复现该形态，验证 288 个思考
    token 被显式记录而不是被静默吞掉。
    """

    protocol_version = "HTTP/1.0"

    def do_POST(self):  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        chunks = [
            {"id": "chatcmpl-reasoning-001", "choices": [{"delta": {"content": "OK"}}]},
            {
                "id": "chatcmpl-reasoning-001",
                "choices": [],
                "usage": {
                    "prompt_tokens": 16,
                    "completion_tokens": 8,
                    "total_tokens": 312,
                },
            },
        ]
        for chunk in chunks:
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, *args):  # silence test output
        return


@pytest.fixture
def reasoning_sse_stub_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ReasoningSSEStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_05c_reasoning_tokens_are_recorded_not_swallowed(reasoning_sse_stub_server):
    """思考模型的 reasoning 消耗必须显式落在 ModelUsage 上（hermetic，无网络）。

    旧行为把 output_tokens 记为 8，288 个思考 token 凭空消失，而
    ``total >= input + output`` 恰好成立，因此没有任何告警，成本低估约 20 倍。
    """
    port = reasoning_sse_stub_server.server_address[1]
    provider = GrokStreamingProvider(
        GrokProviderConfig(
            base_url=f"http://127.0.0.1:{port}/v1",
            api_key="stub-key-for-tests",
            timeout_seconds=10.0,
        )
    )

    text, usage, _ = provider.stream_chat(
        [{"role": "user", "content": "Think hard."}],
        model="gemini-3-pro",
    )

    assert text == "OK"
    assert usage.input_tokens == 16
    assert usage.output_tokens == 8
    assert usage.reasoning_tokens == 288
    assert usage.total_tokens == 312
    assert (
        usage.total_tokens
        >= usage.input_tokens + usage.output_tokens + usage.reasoning_tokens
    )


# ---------------------------------------------------------------------------
# Live provider tests (opt-in, requires AIOS_LIVE_PROVIDER=1 + reachable endpoint)
# ---------------------------------------------------------------------------


@live
def test_01_live_grok_streaming_chat(grok_provider: GrokStreamingProvider):
    """Verify live HTTP 200 SSE streaming chat against grok-4.7."""
    messages = [
        {
            "role": "system",
            "content": "You are a concise AI assistant. Respond with 'AIOS_ONLINE'.",
        },
        {"role": "user", "content": "Ping test."},
    ]
    text, usage, provenance = grok_provider.stream_chat(messages, model="grok-4.7")

    assert text is not None and len(text) > 0
    assert "AIOS_ONLINE" in text or "online" in text.lower() or len(text.strip()) > 0
    assert provenance.provider == "grok"
    assert provenance.model == "grok-4.7"
    assert provenance.request_id != ""
    assert usage.total_tokens > 0
    assert usage.input_tokens is not None and usage.input_tokens > 0
    assert usage.output_tokens is not None and usage.output_tokens > 0
    assert usage.total_tokens >= usage.input_tokens + usage.output_tokens


@live
def test_02_live_grok_model_handler_directive(grok_provider: GrokStreamingProvider):
    """Verify as_model_handler returns valid ModelDirective with token usage and provenance."""
    handler = grok_provider.as_model_handler(model="grok-4.7")
    snapshot = RuntimeSnapshot(
        user_input="你好，请用一句话告诉我你的名字和状态。",
        wake_reason="user_explicit",
        cockpit={"current_topic": "system_diagnostics", "battery_level": 92},
        capability_catalog=(),
        capability_history=(),
        round_index=0,
        remaining_tool_rounds=2,
    )

    directive = handler(snapshot)
    assert isinstance(directive, ModelDirective)
    assert directive.response is not None
    assert len(directive.response.strip()) > 0
    assert directive.usage is not None
    assert directive.provenance is not None
    assert directive.provenance.model == "grok-4.7"


@live
def test_04_cross_model_continuity_and_immutability(
    grok_provider: GrokStreamingProvider, clean_world
):
    """Verify C15 R6: Model A (grok-4.7) writes facts, Model B (grok-4.5) resumes and maintains continuity."""
    store, index, db_path = clean_world
    subject_id = "symbiotic_user_001"
    now_utc = datetime.now(timezone.utc)

    obs = Observation(
        object_id="obs_symbiosis_anchor",
        learned_at=now_utc,
        created_by="system",
        subject_id=subject_id,
        source_kind="wearable_sensor",
        modality="text",
        value="用户在杭州设立了AIOS端侧硬件心智实验室，重点研发23cm柔性屏手环。",
    )
    op = OperationRequest(
        operation_name="seed.anchor_obs",
        expected_world_revision=store.current_world_revision(),
        reason="seed anchor observation",
        idempotency_key="seed_anchor_obs_001",
        source_class=SourceClass.USER,
    )
    store.commit([obs], op)
    index.rebuild()
    initial_rev = store.current_world_revision()
    assert initial_rev >= 1

    handler_grok47 = grok_provider.as_model_handler(model="grok-4.7")
    runtime_turn1 = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=handler_grok47,
        subject_id=subject_id,
    )

    result_t1 = runtime_turn1.run_turn(
        session_id="session_multimodel_001",
        turn_index=1,
        user_input="你好！请确认就绪，并记录任务：双模型端侧调度测试。",
        occurred_at=now_utc,
    )

    assert result_t1.runtime.model_rounds >= 1
    assert result_t1.conversation_commit is not None
    assert (
        (
            result_t1.runtime.response is not None
            and len(result_t1.runtime.response.strip()) > 0
        )
        or len(result_t1.runtime.capability_history) > 0
    )
    rev_after_t1 = store.current_world_revision()
    assert rev_after_t1 > initial_rev

    handler_grok45 = grok_provider.as_model_handler(model="grok-4.5")
    runtime_turn2 = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=handler_grok45,
        subject_id=subject_id,
    )

    result_t2 = runtime_turn2.run_turn(
        session_id="session_multimodel_001",
        turn_index=2,
        user_input="刚才记录的任务是什么？",
        occurred_at=now_utc,
    )

    assert result_t2.runtime.model_rounds >= 1
    assert result_t2.conversation_commit is not None
    assert (
        (
            result_t2.runtime.response is not None
            and len(result_t2.runtime.response.strip()) > 0
        )
        or len(result_t2.runtime.capability_history) > 0
    )
    rev_after_t2 = store.current_world_revision()
    assert rev_after_t2 > rev_after_t1

    stored_payload = store.get_payload(obs.object_id, revision=1)
    assert stored_payload is not None
    assert (
        stored_payload["value"]
        == "用户在杭州设立了AIOS端侧硬件心智实验室，重点研发23cm柔性屏手环。"
    )


# ---------------------------------------------------------------------------
# Hermetic: prompt assembly must not drop the conversation
# ---------------------------------------------------------------------------


def test_model_handler_includes_recent_conversation_in_prompt():
    """The system prompt must carry verbatim recent turns.

    Regression guard: the prompt builder used to keep only scalar cockpit values,
    so `recent_turns` (a list) never reached the model. The assistant then told
    users it could not remember something it had just been told, and burned tool
    rounds re-retrieving it.
    """
    provider = GrokStreamingProvider(GrokProviderConfig(api_key="prompt-test-key"))
    captured: dict[str, object] = {}

    def fake_stream_chat(messages, model=None):
        captured["messages"] = messages
        return (
            "OK",
            ModelUsage(
                total_tokens=3,
                input_tokens=2,
                output_tokens=1,
                provider="grok",
                model="test-model",
                request_id="req-test",
            ),
            ModelCallProvenance(provider="grok", model="test-model", request_id="req-test"),
        )

    provider.stream_chat = fake_stream_chat  # type: ignore[method-assign]

    snapshot = RuntimeSnapshot(
        user_input="我刚才让你记住的那句话里，我在哪个城市？",
        wake_reason="user_explicit",
        cockpit={
            "current_topic": "recall",
            "token_budget": 3400,
            "estimated_tokens": 120,
            "truncated": False,
            "recent_turns": [
                {
                    "turn_index": 1,
                    "user": {"text": "请记住：我在杭州做 23cm 柔性屏手环项目。"},
                    "assistant": {"text": "已记录。"},
                }
            ],
            "memory_cards": [
                {
                    "object_type": "observation",
                    "dimension": "dim_work",
                    "excerpt": "杭州 23cm 柔性屏手环项目",
                }
            ],
        },
        capability_catalog=(),
        capability_history=(),
        round_index=0,
        remaining_tool_rounds=2,
    )

    provider.as_model_handler(model="test-model")(snapshot)
    messages = captured["messages"]
    system_prompt = messages[0]["content"]

    assert "RECENT CONVERSATION" in system_prompt
    assert "杭州" in system_prompt, "prior user turn was dropped from the prompt"
    assert "[turn 1] user:" in system_prompt
    assert "RELEVANT WORLD MEMORY" in system_prompt
    assert "token_budget" not in system_prompt, "bookkeeping keys must not consume prompt budget"
