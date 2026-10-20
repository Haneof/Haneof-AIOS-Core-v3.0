"""Multi-model edge scheduler for AIOS 3.0 wearable symbiosis.

Constitutional Mandates:
1. Iron Rule 3: WakePriority.P0_CRITICAL_SAFETY events (severe fall, sudden cardiac arrest,
   SOS alert) bypass cloud roundtrips and full world model boards. Routed DIRECTLY
   to on-device Edge SLM with a penetration latency <= 50ms.
2. Graceful Offline Degradation: When offline or cloud latency > budget, seamless
   fallback to on-device Edge SLM ensures zero crash, zero turn drop.
3. Resident Memory Budget: On-device resident model weights + KV cache strictly
   gated <= 2.0GB (2048 MB) DRAM quota.
4. Tiered Dispatch: Cloud LLM handles complex deep causal reasoning and periodic reviews,
   while Edge SLM handles low-latency immediate responses and safety triage.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, Mapping, Sequence

from aios_core.contracts.enums import WakePriority


class ModelTier(StrEnum):
    EDGE_SLM = "EDGE_SLM"       # 0.5B ~ 1.5B on-device resident model (<50ms)
    CLOUD_LLM = "CLOUD_LLM"     # 7B ~ 70B cloud large reasoning model (1~3s)


@dataclass(frozen=True, slots=True)
class ModelDescriptor:
    model_id: str
    tier: ModelTier
    param_size_billion: float
    memory_footprint_mb: float
    max_context_tokens: int
    is_resident: bool = False
    is_available: bool = True


@dataclass(frozen=True, slots=True)
class ModelDispatchResult:
    selected_tier: ModelTier
    model_id: str
    output_text: str
    latency_ms: float
    fallback_triggered: bool
    budget_exceeded: bool
    emergency_bypassed: bool
    metadata: dict[str, Any] = field(default_factory=dict)


class ResidentMemoryExceededError(RuntimeError):
    """Raised when on-device model resident footprint exceeds 2.0GB limit."""


class MultiModelEdgeScheduler:
    """Orchestrates on-device Edge SLM and Cloud LLM dispatching for wearable bands."""

    MAX_RESIDENT_MEMORY_MB: float = 2048.0  # 2.0 GB strict memory quota
    P0_EMERGENCY_BUDGET_MS: float = 50.0    # Iron Rule 3: <= 50ms emergency bypass

    def __init__(
        self,
        *,
        edge_slm_executor: Callable[[str, dict[str, Any]], str] | None = None,
        cloud_llm_executor: Callable[[str, dict[str, Any]], str] | None = None,
        is_network_online: bool = True,
        cloud_timeout_ms: float = 2500.0,
    ) -> None:
        self._models: dict[str, ModelDescriptor] = {}
        self._edge_slm_executor = edge_slm_executor or self._default_edge_slm_stub
        self._cloud_llm_executor = cloud_llm_executor or self._default_cloud_llm_stub
        self._is_network_online = is_network_online
        self._cloud_timeout_ms = cloud_timeout_ms
        self._active_cloud_model_id: str | None = None
        self._active_edge_model_id: str | None = None

        # Register default baseline models
        self.register_model(
            ModelDescriptor(
                model_id="qwen2.5-0.5b-wearable-q4",
                tier=ModelTier.EDGE_SLM,
                param_size_billion=0.5,
                memory_footprint_mb=480.0,
                max_context_tokens=2048,
                is_resident=True,
            )
        )
        self.register_model(
            ModelDescriptor(
                model_id="deepseek-v3-cloud-reasoner",
                tier=ModelTier.CLOUD_LLM,
                param_size_billion=671.0,
                memory_footprint_mb=0.0,  # 0 on-device memory
                max_context_tokens=16384,
                is_resident=False,
            )
        )

    @property
    def is_network_online(self) -> bool:
        return self._is_network_online

    @is_network_online.setter
    def is_network_online(self, value: bool) -> None:
        self._is_network_online = value

    @property
    def total_resident_memory_mb(self) -> float:
        return sum(
            m.memory_footprint_mb
            for m in self._models.values()
            if m.tier == ModelTier.EDGE_SLM and m.is_resident
        )

    def register_model(self, descriptor: ModelDescriptor) -> None:
        """Register a model descriptor, enforcing the 2.0GB resident memory gate."""
        if descriptor.tier == ModelTier.EDGE_SLM and descriptor.is_resident:
            current_mem = self.total_resident_memory_mb
            new_mem = current_mem + descriptor.memory_footprint_mb
            if new_mem > self.MAX_RESIDENT_MEMORY_MB:
                raise ResidentMemoryExceededError(
                    f"Resident memory budget exceeded: {new_mem:.1f}MB > {self.MAX_RESIDENT_MEMORY_MB:.1f}MB"
                )
        self._models[descriptor.model_id] = descriptor

    def dispatch(
        self,
        prompt: str,
        *,
        priority: WakePriority = WakePriority.P2_ROUTINE,
        context_kwargs: dict[str, Any] | None = None,
        force_tier: ModelTier | None = None,
    ) -> ModelDispatchResult:
        """Dispatch inference according to priority, connectivity, and latency constraints."""
        kwargs = context_kwargs or {}
        start_t = time.perf_counter()

        # 1. Iron Rule 3: P0 Critical Safety Emergency Short-Circuit Bypass
        if priority == WakePriority.P0_CRITICAL_SAFETY:
            output = self._edge_slm_executor(prompt, {**kwargs, "emergency_mode": True})
            latency_ms = (time.perf_counter() - start_t) * 1000.0
            return ModelDispatchResult(
                selected_tier=ModelTier.EDGE_SLM,
                model_id=self._get_active_model_id(ModelTier.EDGE_SLM),
                output_text=output,
                latency_ms=latency_ms,
                fallback_triggered=False,
                budget_exceeded=latency_ms > self.P0_EMERGENCY_BUDGET_MS,
                emergency_bypassed=True,
                metadata={"priority": priority.value, "short_circuit": True},
            )

        # 2. Forced tier override
        if force_tier == ModelTier.EDGE_SLM:
            output = self._edge_slm_executor(prompt, kwargs)
            latency_ms = (time.perf_counter() - start_t) * 1000.0
            return ModelDispatchResult(
                selected_tier=ModelTier.EDGE_SLM,
                model_id=self._get_active_model_id(ModelTier.EDGE_SLM),
                output_text=output,
                latency_ms=latency_ms,
                fallback_triggered=False,
                budget_exceeded=False,
                emergency_bypassed=False,
            )

        # 3. Offline degradation: network is offline -> auto fallback to Edge SLM
        if not self._is_network_online:
            output = self._edge_slm_executor(prompt, {**kwargs, "offline_fallback": True})
            latency_ms = (time.perf_counter() - start_t) * 1000.0
            return ModelDispatchResult(
                selected_tier=ModelTier.EDGE_SLM,
                model_id=self._get_active_model_id(ModelTier.EDGE_SLM),
                output_text=output,
                latency_ms=latency_ms,
                fallback_triggered=True,
                budget_exceeded=False,
                emergency_bypassed=False,
                metadata={"reason": "OFFLINE_NETWORK_DEGRADATION"},
            )

        # 4. Standard Online Routing: Attempt Cloud LLM with timeout circuit breaker
        try:
            cloud_start = time.perf_counter()
            output = self._cloud_llm_executor(prompt, kwargs)
            cloud_latency_ms = (time.perf_counter() - cloud_start) * 1000.0

            if cloud_latency_ms > self._cloud_timeout_ms:
                # Cloud exceeded timeout budget -> trigger edge SLM fallback
                edge_output = self._edge_slm_executor(prompt, {**kwargs, "timeout_fallback": True})
                total_latency_ms = (time.perf_counter() - start_t) * 1000.0
                return ModelDispatchResult(
                    selected_tier=ModelTier.EDGE_SLM,
                    model_id=self._get_active_model_id(ModelTier.EDGE_SLM),
                    output_text=edge_output,
                    latency_ms=total_latency_ms,
                    fallback_triggered=True,
                    budget_exceeded=True,
                    emergency_bypassed=False,
                    metadata={"reason": "CLOUD_TIMEOUT_CIRCUIT_BREAKER", "cloud_latency_ms": cloud_latency_ms},
                )

            total_latency_ms = (time.perf_counter() - start_t) * 1000.0
            return ModelDispatchResult(
                selected_tier=ModelTier.CLOUD_LLM,
                model_id=self._get_active_model_id(ModelTier.CLOUD_LLM),
                output_text=output,
                latency_ms=total_latency_ms,
                fallback_triggered=False,
                budget_exceeded=False,
                emergency_bypassed=False,
            )

        except Exception as exc:
            # Cloud invocation failed (network jitter / API error) -> seamless edge SLM fallback
            edge_output = self._edge_slm_executor(prompt, {**kwargs, "error_fallback": True, "error": str(exc)})
            total_latency_ms = (time.perf_counter() - start_t) * 1000.0
            return ModelDispatchResult(
                selected_tier=ModelTier.EDGE_SLM,
                model_id=self._get_active_model_id(ModelTier.EDGE_SLM),
                output_text=edge_output,
                latency_ms=total_latency_ms,
                fallback_triggered=True,
                budget_exceeded=False,
                emergency_bypassed=False,
                metadata={"reason": "CLOUD_EXCEPTION_FALLBACK", "error": str(exc)},
            )

    def set_active_model(self, model_id: str) -> None:
        """Explicitly switch the active model for its tier."""
        if model_id not in self._models:
            raise KeyError(f"Model '{model_id}' is not registered.")
        model = self._models[model_id]
        if model.tier == ModelTier.CLOUD_LLM:
            self._active_cloud_model_id = model_id
        else:
            self._active_edge_model_id = model_id

    def _get_active_model_id(self, tier: ModelTier) -> str:
        if tier == ModelTier.CLOUD_LLM and self._active_cloud_model_id:
            return self._active_cloud_model_id
        if tier == ModelTier.EDGE_SLM and self._active_edge_model_id:
            return self._active_edge_model_id
        for model in self._models.values():
            if model.tier == tier and model.is_available:
                return model.model_id
        return "fallback-stub"

    @staticmethod
    def _default_edge_slm_stub(prompt: str, context: dict[str, Any]) -> str:
        if context.get("emergency_mode"):
            return "【P0紧急研判】检测到严重异常！生命体征/跌倒警报已触发，正在呼叫紧急救援并保持微震交互。"
        if context.get("offline_fallback"):
            return "【端侧离线响应】已在本地离线处理您的请求。"
        return "【端侧轻量响应】" + prompt[:50]

    @staticmethod
    def _default_cloud_llm_stub(prompt: str, context: dict[str, Any]) -> str:
        return "【云端深度心智】根据长周期认知图谱与多维因果证据分析：" + prompt[:100]


def create_production_edge_scheduler(
    *,
    grok_provider: Any = None,
    edge_slm_executor: Callable[[str, dict[str, Any]], str] | None = None,
    is_network_online: bool = True,
    cloud_timeout_ms: float = 30000.0,
) -> MultiModelEdgeScheduler:
    """Creates a production-ready edge scheduler pre-configured with Grok Cloud LLM and Edge SLM."""
    if grok_provider is not None:
        cloud_executor = grok_provider.as_executor(model="grok-4.7")
    else:
        cloud_executor = None

    scheduler = MultiModelEdgeScheduler(
        edge_slm_executor=edge_slm_executor,
        cloud_llm_executor=cloud_executor,
        is_network_online=is_network_online,
        cloud_timeout_ms=cloud_timeout_ms,
    )

    # Register grok-4.7 as primary cloud model and grok-4.5 as secondary cloud model
    scheduler.register_model(
        ModelDescriptor(
            model_id="grok-4.7",
            tier=ModelTier.CLOUD_LLM,
            param_size_billion=100.0,
            memory_footprint_mb=0.0,
            max_context_tokens=131072,
            is_resident=False,
            is_available=True,
        )
    )
    scheduler.register_model(
        ModelDescriptor(
            model_id="grok-4.5",
            tier=ModelTier.CLOUD_LLM,
            param_size_billion=50.0,
            memory_footprint_mb=0.0,
            max_context_tokens=65536,
            is_resident=False,
            is_available=True,
        )
    )
    scheduler.set_active_model("grok-4.7")

    return scheduler
