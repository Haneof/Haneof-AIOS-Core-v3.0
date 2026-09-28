"""Test-only crash worker for the durable-exchange gate.

It performs a mechanical exchange step and then kills its own process with
SIGKILL, so the parent test can verify crash recovery from real process death
rather than from a simulated exception.

Usage:
    python _crash_worker.py --exchange DIR --point before|after_request|after_response
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parents[2]
if str(HARNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(HARNESS_ROOT))

from aios_exchange.bridge import ExchangeBridge  # noqa: E402
from aios_exchange.canonical import canonical_json_bytes  # noqa: E402

# The recovery gate must publish the exact snapshot it later resumes. The old
# unrelated dictionary implicitly exercised the now-forbidden S1 -> S2 reuse.
from aios_core.runtime.cognitive_runtime import RuntimeSnapshot
from aios_exchange.runner import serialize_runtime_snapshot

SYNTHETIC_BODY = serialize_runtime_snapshot(RuntimeSnapshot(
    user_input="synthetic recovery probe", wake_reason="synthetic", cockpit={},
    capability_catalog=(), capability_history=(), round_index=0,
    remaining_tool_rounds=0,
))


def suicide() -> None:
    os.kill(os.getpid(), signal.SIGKILL)


def response_envelope(bridge: ExchangeBridge, request_id: str) -> dict:
    return {
        "response_version": 1,
        "request_id": request_id,
        "request_sha256": bridge.request_sha256(request_id),
        "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
        "directive": {
            "capability_calls": [],
            "response": "SYNTHETIC_OPERATOR_PREP_CRASH_WORKER_RESPONSE",
            "silence": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exchange", required=True)
    parser.add_argument("--point", required=True, choices=["before", "after_request", "after_response"])
    parser.add_argument("--out", required=True, help="file receiving the request id (best effort)")
    args = parser.parse_args()

    bridge = ExchangeBridge(args.exchange)

    if args.point == "before":
        suicide()

    published = bridge.publish_request(kind="model_directive", body=SYNTHETIC_BODY)
    Path(args.out).write_text(published["request_id"], encoding="utf-8")
    if args.point == "after_request":
        suicide()

    envelope = response_envelope(bridge, published["request_id"])
    bridge.responses.publish_bytes(
        request_id=published["request_id"],
        response_bytes=canonical_json_bytes(envelope) + b"\n",
    )
    if args.point == "after_response":
        suicide()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
