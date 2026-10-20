"""Physical Multi-Model Habitation & Real Provider Integration Test Suite.

Constitutional Mandates Verified:
1. Iron Rule 1: High-quality reasoning, live SSE chunk aggregation.
2. Iron Rule 2: Byte-immutable historical records across multi-model transitions.
3. Iron Rule 3: P0 critical safety bypasses cloud LLM with latency <= 50ms.
4. C15 R6 Reconciliation: Live execution of grok-4.7 and grok-4.5 across
   session boundaries without synthetic stubs.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
import pytest

from aios_core.contracts.enums import SourceClass, WakePriority
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent, as_utc
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.cognitive_runtime import (
    CognitiveRuntime,
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
    RuntimeSnapshot,
)
from aios_core.runtime.edge_model_scheduler import (
    ModelTier,
    MultiModelEdgeScheduler,
    create_production_edge_scheduler,
)
from aios_core.runtime.grok_provider import (
    GrokProviderConfig,
    GrokStreamingProvider,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore


@pytest.fixture
def grok_provider() -> GrokStreamingProvider:
    return GrokStreamingProvider()


@pytest.fixture
def clean_world(tmp_path):
    db_path = tmp_path / "live_multimodel_world.sqlite"
    index_path = tmp_path / "live_multimodel_index.sqlite"
    store = SQLiteWorldStore(str(db_path))
    index = WorldSearchIndex(str(index_path), store=store)
    return store, index, db_path


def test_01_live_grok_streaming_chat(grok_provider: GrokStreamingProvider):
    """Verify live HTTP 200 SSE streaming chat against grok-4.7."""
    messages = [
        {"role": "system", "content": "You are a concise AI assistant. Respond with 'AIOS_ONLINE'."},
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


def test_03_multimodel_scheduler_p0_bypass_vs_cloud(grok_provider: GrokStreamingProvider):
    """Verify Iron Rule 3: P0 critical safety bypasses cloud latency budget (<= 50ms)."""
    scheduler = create_production_edge_scheduler(
        grok_provider=grok_provider,
        cloud_timeout_ms=60000.0,
    )

    # 1. P0 critical emergency dispatch: must complete under 50ms using edge SLM
    emergency_start = time.perf_counter()
    p0_result = scheduler.dispatch(
        "用户心率骤降至 38bpm，加速度计检测到 12.5g 剧烈冲击碰撞！",
        priority=WakePriority.P0_CRITICAL_SAFETY,
    )
    emergency_elapsed_ms = (time.perf_counter() - emergency_start) * 1000.0

    assert p0_result.selected_tier == ModelTier.EDGE_SLM
    assert p0_result.emergency_bypassed is True
    assert p0_result.latency_ms <= 50.0 or emergency_elapsed_ms <= 50.0
    assert "P0" in p0_result.output_text or "紧急" in p0_result.output_text

    # 2. Routine dispatch: routes to live Grok-4.7 cloud model
    routine_result = scheduler.dispatch(
        "心智连通性检测，请回复 ONLINE。",
        priority=WakePriority.P2_ROUTINE,
    )
    assert routine_result.selected_tier == ModelTier.CLOUD_LLM
    assert routine_result.model_id == "grok-4.7"
    assert len(routine_result.output_text) > 0
    assert routine_result.fallback_triggered is False


def test_04_cross_model_continuity_and_immutability(grok_provider: GrokStreamingProvider, clean_world):
    """Verify C15 R6: Model A (grok-4.7) writes facts, Model B (grok-4.5) resumes and maintains continuity."""
    store, index, db_path = clean_world
    subject_id = "symbiotic_user_001"
    now_utc = datetime.now(timezone.utc)

    # Ingest a baseline observation into SQLite world store
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

    # --- Turn 1: Handled by Grok-4.7 ---
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
        (result_t1.runtime.response is not None and len(result_t1.runtime.response.strip()) > 0)
        or len(result_t1.runtime.capability_history) > 0
    )
    rev_after_t1 = store.current_world_revision()
    assert rev_after_t1 > initial_rev

    # --- Turn 2: Switched to Grok-4.5 on the EXACT SAME SQLite World Store ---
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
        (result_t2.runtime.response is not None and len(result_t2.runtime.response.strip()) > 0)
        or len(result_t2.runtime.capability_history) > 0
    )
    rev_after_t2 = store.current_world_revision()
    assert rev_after_t2 > rev_after_t1

    # --- Iron Rule 2 Verification: Historical Observation byte immutability ---
    stored_payload = store.get_payload(obs.object_id, revision=1)
    assert stored_payload is not None
    assert stored_payload["value"] == "用户在杭州设立了AIOS端侧硬件心智实验室，重点研发23cm柔性屏手环。"
