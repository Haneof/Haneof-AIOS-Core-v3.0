"""SiliconFlow (硅基流动) OpenAI-compatible model handler for AIOS Core.

This adapter reuses ``GrokStreamingProvider``, which is already a dependency-free
OpenAI-compatible SSE streaming client. We only rebind base_url / api_key / model
through environment variables, so no new HTTP code is introduced.

Environment:
    AIOS_SILICONFLOW_BASE_URL  (default https://api.siliconflow.cn/v1)
    AIOS_SILICONFLOW_API_KEY   (required; fail closed if missing)
    AIOS_SILICONFLOW_MODEL     (default Qwen/Qwen2.5-7B-Instruct)
"""

from __future__ import annotations

import os

from aios_core.runtime.grok_provider import (
    GrokProviderConfig,
    GrokStreamingProvider,
)

DEFAULT_BASE_URL = os.environ.get(
    "AIOS_SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"
)
DEFAULT_API_KEY = os.environ.get("AIOS_SILICONFLOW_API_KEY", "")
DEFAULT_MODEL = os.environ.get(
    "AIOS_SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct"
)


def _build_provider() -> GrokStreamingProvider:
    if not DEFAULT_API_KEY:
        raise RuntimeError(
            "AIOS_SILICONFLOW_API_KEY is not configured; refusing to send an "
            "unauthenticated request to the SiliconFlow endpoint"
        )
    config = GrokProviderConfig(
        base_url=DEFAULT_BASE_URL,
        api_key=DEFAULT_API_KEY,
        default_model=DEFAULT_MODEL,
        secondary_model=DEFAULT_MODEL,
    )
    return GrokStreamingProvider(config)


# Module-level handler object, importable as
# ``aios_core.runtime.siliconflow_handler:handler`` by headless ``--model-handler``.
handler = _build_provider().as_model_handler()
