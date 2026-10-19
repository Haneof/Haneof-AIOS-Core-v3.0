"""Unit test suite for MultiModelEdgeScheduler (Window 83).

Validates:
1. Iron Rule 3: WakePriority.P0_CRITICAL_SAFETY bypasses cloud network and
   executes directly on Edge SLM within 50ms.
2. Offline graceful degradation: network offline seamlessly routes to Edge SLM.
3. Timeout circuit breaker: cloud delay > threshold falls back to Edge SLM without turn loss.
4. Exception fallback: cloud errors fall back to Edge SLM.
5. Resident memory gate: attempts to load > 2048 MB on-device models are blocked.
"""

from __future__ import annotations

import time
import pytest

from aios_core.contracts.enums import WakePriority
from aios_core.runtime.edge_model_scheduler import (
    ModelDescriptor,
    ModelTier,
    MultiModelEdgeScheduler,
    ResidentMemoryExceededError,
)


def test_p0_critical_safety_short_circuit_bypass():
    scheduler = MultiModelEdgeScheduler()

    # Dispatch P0 safety event (e.g. cardiac arrest / severe fall)
    res = scheduler.dispatch(
        "检测到心率突降与摔倒冲击！",
        priority=WakePriority.P0_CRITICAL_SAFETY,
    )

    assert res.selected_tier == ModelTier.EDGE_SLM
    assert res.emergency_bypassed is True
    assert res.budget_exceeded is False
    assert res.latency_ms <= 50.0  # Must be sub-50ms
    assert "P0紧急研判" in res.output_text


def test_offline_network_graceful_degradation():
    scheduler = MultiModelEdgeScheduler(is_network_online=False)

    res = scheduler.dispatch(
        "查一下今天的工作日程",
        priority=WakePriority.P2_ROUTINE,
    )

    assert res.selected_tier == ModelTier.EDGE_SLM
    assert res.fallback_triggered is True
    assert res.metadata["reason"] == "OFFLINE_NETWORK_DEGRADATION"
    assert "端侧离线响应" in res.output_text


def test_cloud_timeout_circuit_breaker_falls_back_to_edge_slm():
    def slow_cloud(prompt: str, context: dict) -> str:
        time.sleep(0.06)  # 60ms delay
        return "slow cloud"

    # Set cloud timeout budget to 30ms so slow_cloud triggers circuit breaker
    scheduler = MultiModelEdgeScheduler(
        cloud_llm_executor=slow_cloud,
        cloud_timeout_ms=30.0,
        is_network_online=True,
    )

    res = scheduler.dispatch(
        "做一次长周期深度人生推演",
        priority=WakePriority.P2_ROUTINE,
    )

    assert res.selected_tier == ModelTier.EDGE_SLM
    assert res.fallback_triggered is True
    assert res.budget_exceeded is True
    assert res.metadata["reason"] == "CLOUD_TIMEOUT_CIRCUIT_BREAKER"


def test_cloud_exception_gracefully_falls_back_to_edge_slm():
    def failing_cloud(prompt: str, context: dict) -> str:
        raise ConnectionResetError("503 Service Unavailable")

    scheduler = MultiModelEdgeScheduler(
        cloud_llm_executor=failing_cloud,
        is_network_online=True,
    )

    res = scheduler.dispatch(
        "深度复盘老王合伙历史",
        priority=WakePriority.P2_ROUTINE,
    )

    assert res.selected_tier == ModelTier.EDGE_SLM
    assert res.fallback_triggered is True
    assert res.metadata["reason"] == "CLOUD_EXCEPTION_FALLBACK"


def test_resident_memory_budget_gate_enforces_2gb_limit():
    scheduler = MultiModelEdgeScheduler()
    # Baseline resident model takes 480MB
    assert scheduler.total_resident_memory_mb == 480.0

    # Try registering another 1.2GB resident model (total 1680MB <= 2048MB -> allowed)
    scheduler.register_model(
        ModelDescriptor(
            model_id="speech-whisper-tiny-edge",
            tier=ModelTier.EDGE_SLM,
            param_size_billion=0.039,
            memory_footprint_mb=1200.0,
            max_context_tokens=1024,
            is_resident=True,
        )
    )
    assert scheduler.total_resident_memory_mb == 1680.0

    # Try registering another 500MB resident model (total 2180MB > 2048MB -> rejected)
    with pytest.raises(ResidentMemoryExceededError) as exc_info:
        scheduler.register_model(
            ModelDescriptor(
                model_id="oversized-vision-model",
                tier=ModelTier.EDGE_SLM,
                param_size_billion=0.8,
                memory_footprint_mb=500.0,
                max_context_tokens=1024,
                is_resident=True,
            )
        )
    assert "Resident memory budget exceeded" in str(exc_info.value)
