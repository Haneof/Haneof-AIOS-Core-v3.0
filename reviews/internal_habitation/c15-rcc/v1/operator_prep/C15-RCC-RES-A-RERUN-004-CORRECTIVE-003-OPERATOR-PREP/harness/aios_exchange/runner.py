"""Runtime plumbing for the Resident launch boundary.

The runner owns the mechanical side of a turn:

* it drives the frozen Core runtime;
* whenever Core needs a model decision it publishes a durable request through
  the exchange bridge;
* it blocks until some **external** session durably publishes the exact
  response bytes, then parses them into a real ``ModelDirective`` and consumes
  the exchange record.

There is deliberately **no** semantic callback, provider adapter, keyword
router, fixture rule, prewritten answer, default directive or fallback reply in
this module. The only source of a directive is published response bytes.

Recovery follows the frozen corrective rule: once a ``request_published``
record exists, the runner never re-decides; it resumes the existing request or
consumes the already durable response.
"""

from __future__ import annotations

import datetime as _dt
import json
import pathlib
from dataclasses import dataclass
from typing import Any, Mapping

from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot

from . import REAL_RESPONSE_MODE
from .bridge import (
    DISPATCH_BOUNDARY_EVENT,
    DISPATCH_BOUNDARY_RULE,
    ExchangeBridge,
    ExchangeContractError,
)
from .canonical import canonical_json_bytes
from .schema import parse_model_directive, serialize_runtime_snapshot

__all__ = [
    "REAL_RESPONSE_MODE",
    "DISPATCH_BOUNDARY_EVENT",
    "DISPATCH_BOUNDARY_RULE",
    "ExternalSessionConfig",
    "ExternalSessionModelHandler",
    "open_bridge",
    "run_user_turn",
]


@dataclass(frozen=True)
class ExternalSessionConfig:
    """Mechanical configuration of the model boundary."""

    exchange_root: pathlib.Path
    kind: str = "model_directive"
    response_timeout_s: float = 1800.0
    poll_interval_s: float = 0.05

    def __post_init__(self) -> None:
        if not str(self.kind).strip():
            raise ValueError("kind must be non-blank")
        if float(self.response_timeout_s) <= 0:
            raise ValueError("response_timeout_s must be positive")


class ExternalSessionModelHandler:
    """Model boundary usable as a Core ``ModelHandler``.

    ``Callable[[RuntimeSnapshot], ModelDirective]`` where the directive is
    parsed from durably published external response bytes.
    """

    def __init__(self, config: ExternalSessionConfig) -> None:
        self.config = config
        self.bridge = ExchangeBridge(config.exchange_root)
        self.handoffs: list[dict[str, Any]] = []

    # -- model boundary --------------------------------------------------
    def __call__(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        body = serialize_runtime_snapshot(snapshot)
        state = self.bridge.recovery_state()

        durable_unconsumed = list(state.get("durable_unconsumed") or [])
        if durable_unconsumed:
            request_id = durable_unconsumed[0]
            return self._resolve(request_id, body_digest=None, path="recovered_durable_response")

        outstanding = list(state.get("open_dispatched") or [])
        if outstanding:
            request_id = outstanding[0]
            return self._resolve(request_id, body_digest=None, path="resumed_dispatched_request")

        published = self.bridge.publish_request(kind=self.config.kind, body=body)
        return self._resolve(
            published["request_id"],
            body_digest=published["request_sha256"],
            path="published_new_request",
        )

    def _resolve(
        self,
        request_id: str,
        *,
        body_digest: str | None,
        path: str,
    ) -> ModelDirective:
        raw = self.bridge.await_response_bytes(
            request_id,
            timeout_s=self.config.response_timeout_s,
            poll_interval_s=self.config.poll_interval_s,
        )
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise ExchangeContractError(f"published response is not valid JSON: {exc}") from exc
        directive = parse_model_directive(decoded)
        self.bridge.consume_response(request_id)
        self.handoffs.append(
            {
                "request_id": request_id,
                "path": path,
                "request_sha256": durable_request_digest(request_id, self.bridge),
                "response_sha256": self.bridge.response_file_digest(request_id),
                "declared_request_sha256": body_digest,
                "response_mode": REAL_RESPONSE_MODE,
            }
        )
        return directive

    # -- audit -----------------------------------------------------------
    def handoff_records(self) -> list[dict[str, Any]]:
        return list(self.handoffs)


def durable_request_digest(request_id: str, bridge: ExchangeBridge) -> str | None:
    """Digest of the durable request for a request id (mechanical helper)."""

    try:
        return bridge.request_sha256(request_id)
    except Exception:
        return None


def open_bridge(exchange_root: str | pathlib.Path) -> ExchangeBridge:
    return ExchangeBridge(exchange_root)


def run_user_turn(
    *,
    world_path: str | pathlib.Path,
    exchange_root: str | pathlib.Path,
    subject_id: str,
    session_id: str,
    turn_index: int,
    user_input: str,
    occurred_at: str,
    index_path: str | pathlib.Path | None = None,
    response_timeout_s: float = 1800.0,
    poll_interval_s: float = 0.05,
    token_budget: int | None = None,
) -> dict[str, Any]:
    """Run one frozen-Core user turn whose model decisions come from the exchange.

    ``world_path``/``subject_id``/``session_id``/``user_input``/``occurred_at``
    are always supplied by the caller. Nothing here is defaulted or inferred
    from repository state.
    """

    from aios_core.headless.core import HeadlessConfig, HeadlessCore

    moment = _dt.datetime.fromisoformat(
        occurred_at[:-1] + "+00:00" if occurred_at.endswith("Z") else occurred_at
    )
    if moment.tzinfo is None:
        raise ValueError("occurred_at must be timezone-aware")

    config = ExternalSessionConfig(
        exchange_root=pathlib.Path(exchange_root),
        response_timeout_s=response_timeout_s,
        poll_interval_s=poll_interval_s,
    )
    handler = ExternalSessionModelHandler(config)
    headless_config = HeadlessConfig(
        world_path=pathlib.Path(world_path),
        index_path=pathlib.Path(index_path) if index_path is not None else None,
        subject_id=subject_id,
    )
    core = HeadlessCore(config=headless_config, model_handler=handler)
    core.start()
    try:
        status_before = core.status()
        result = core.submit_user_turn(
            session_id=session_id,
            turn_index=turn_index,
            user_input=user_input,
            occurred_at=moment,
            token_budget=token_budget,
        )
        status_after = core.status()
    finally:
        core.stop()

    return {
        "world_path": str(world_path),
        "subject_id": subject_id,
        "session_id": session_id,
        "turn_index": int(turn_index),
        "status_before": status_before,
        "status_after": status_after,
        "turn_result": json.loads(canonical_json_bytes(result).decode("utf-8")),
        "handoffs": handler.handoff_records(),
        "exchange": {
            "recovery_state": handler.bridge.recovery_state(),
            "integrity": handler.bridge.integrity(),
        },
        "response_mode": REAL_RESPONSE_MODE,
    }
