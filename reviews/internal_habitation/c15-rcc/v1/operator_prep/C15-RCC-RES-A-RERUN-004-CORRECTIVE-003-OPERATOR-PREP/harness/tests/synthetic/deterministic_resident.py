"""TEST-ONLY deterministic external session.

This module stands in for the external Resident session **during gate tests
only**. It reads a durably published request and publishes an exact response
through the same mechanical publisher a real session must use.

Its decision rule is purely *structural* (it looks only at the round index and
whether capability history is empty). It contains:

* no keyword matching;
* no user-text inspection;
* no event id, cursor number or fixture identifier;
* no claim, policy, goal or reply derived from any real content;
* no import from the run package other than the mechanical transport API.

The run package (``aios_exchange``) never imports this module; it is not
reachable in real-run mode.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Mapping

from aios_exchange.bridge import ExchangeBridge
from aios_exchange.canonical import canonical_json_bytes

SYNTHETIC_SESSION_LABEL = "SYNTHETIC_OPERATOR_PREP_EXTERNAL_SESSION"
SYNTHETIC_PROBE_CAPABILITY = "search_world"
SYNTHETIC_TERMINAL_RESPONSE = "SYNTHETIC_OPERATOR_PREP_TERMINAL_RESPONSE"


def directive_for_request(request_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Structural, content-blind directive for one published request."""

    body = request_payload.get("body") or {}
    history = body.get("capability_history") or []
    if not history:
        return {
            "capability_calls": [
                {
                    "name": SYNTHETIC_PROBE_CAPABILITY,
                    "arguments": {"query": "synthetic-operator-prep-probe", "limit": 3},
                    "call_id": "synthetic-call-0001",
                }
            ],
            "response": None,
            "silence": False,
        }
    return {
        "capability_calls": [],
        "response": SYNTHETIC_TERMINAL_RESPONSE,
        "silence": False,
    }


def envelope_for(request_payload: Mapping[str, Any], request_sha256: str) -> dict[str, Any]:
    request_id = request_payload["request_id"]
    return {
        "response_version": 1,
        "request_id": request_id,
        "request_sha256": request_sha256,
        "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
        "directive": directive_for_request(request_payload),
    }


def respond_to(exchange_root: str, request_id: str) -> dict[str, Any]:
    """Publish the deterministic response for one published request."""

    bridge = ExchangeBridge(exchange_root)
    payload = bridge.request_payload(request_id)
    envelope = envelope_for(payload, bridge.request_sha256(request_id))
    data = canonical_json_bytes(envelope) + b"\n"
    return bridge.responses.publish_bytes(request_id=request_id, response_bytes=data)


class BackgroundResponder:
    """Async external session: answers every open dispatched request once."""

    def __init__(self, exchange_root: str, poll_interval_s: float = 0.02) -> None:
        self.exchange_root = str(exchange_root)
        self.poll_interval_s = poll_interval_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="synthetic-responder", daemon=True)
        self.served: list[str] = []
        self.errors: list[str] = []

    def start(self) -> "BackgroundResponder":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=30)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                bridge = ExchangeBridge(self.exchange_root)
                state = bridge.recovery_state()
                for request_id in state.get("open_dispatched") or []:
                    respond_to(self.exchange_root, request_id)
                    self.served.append(request_id)
            except Exception as exc:  # recorded, never repaired silently
                self.errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(self.poll_interval_s)
