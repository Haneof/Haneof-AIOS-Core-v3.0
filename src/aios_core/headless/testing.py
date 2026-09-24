"""Deterministic mechanical model adapter for headless smoke tests only.

It is never selected by default and encodes no cognition policy.
"""

from __future__ import annotations

import hashlib

from aios_core.runtime.cognitive_runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
    RuntimeSnapshot,
)


def deterministic_model_handler(snapshot: RuntimeSnapshot) -> ModelDirective:
    raw = (
        f"{snapshot.wake_reason}|{snapshot.round_index}|{snapshot.user_input}"
    ).encode("utf-8")
    request_id = "headless-smoke-" + hashlib.sha256(raw).hexdigest()[:20]
    return ModelDirective(
        response="HEADLESS_MECHANICAL_OK",
        usage=ModelUsage(
            total_tokens=2,
            input_tokens=1,
            output_tokens=1,
            provider="headless-test",
            model="deterministic-v1",
            request_id=request_id,
        ),
        provenance=ModelCallProvenance(
            provider="headless-test",
            model="deterministic-v1",
            request_id=request_id,
        ),
    )
