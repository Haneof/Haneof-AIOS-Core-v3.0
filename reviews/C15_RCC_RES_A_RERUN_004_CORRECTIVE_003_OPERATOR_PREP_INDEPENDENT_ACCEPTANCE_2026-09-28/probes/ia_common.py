"""IA reviewer probe helpers (synthetic / disposable data only).

Independent reviewer code. Imports the *candidate* harness package
(``aios_exchange``) and the frozen Core from the candidate checkout given by
``IA_CANDIDATE_ROOT`` (default ``/tmp/ia/clone``). Contains no C15 fixture
content, no event payload, no cursor, no evaluator semantics.
"""

from __future__ import annotations

import os
import pathlib
import sys
import threading
import time

CANDIDATE_ROOT = pathlib.Path(os.environ.get("IA_CANDIDATE_ROOT", "/tmp/ia/clone"))
PREP_ROOT = (
    CANDIDATE_ROOT
    / "reviews/internal_habitation/c15-rcc/v1/operator_prep"
    / "C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP"
)
HARNESS_ROOT = PREP_ROOT / "harness"
CORE_SRC = CANDIDATE_ROOT / "src"

# NOTE: deliberately NOT adding harness/tests to sys.path, so the candidate's
# test-only synthetic responder is unreachable from these probes.
for entry in (str(HARNESS_ROOT), str(CORE_SRC)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from aios_core.runtime.capabilities import CapabilityResult  # noqa: E402
from aios_core.runtime.cognitive_runtime import RuntimeSnapshot  # noqa: E402

from aios_exchange.bridge import ExchangeBridge  # noqa: E402
from aios_exchange.canonical import canonical_json_bytes, sha256_hex  # noqa: E402
from aios_exchange.runner import ExternalSessionConfig, ExternalSessionModelHandler  # noqa: E402
from aios_exchange.schema import serialize_runtime_snapshot  # noqa: E402

IA_LABEL = "IA_REVIEWER_SYNTHETIC"


def snapshot(round_index: int, history: tuple = ()) -> RuntimeSnapshot:
    return RuntimeSnapshot(
        user_input="IA synthetic probe input",
        wake_reason="ia_synthetic",
        cockpit={"ia": True},
        capability_catalog=({"name": "ia_probe_capability", "kind": "read"},),
        capability_history=tuple(history),
        round_index=round_index,
        remaining_tool_rounds=max(0, 4 - round_index),
    )


def snapshot_round1() -> RuntimeSnapshot:
    return snapshot(
        1,
        (
            CapabilityResult(
                name="ia_probe_capability", ok=True, data={"ia": 1}, call_id="ia-call-1"
            ),
        ),
    )


def envelope(bridge: ExchangeBridge, request_id: str, text: str, *, request_sha: str | None = None,
             env_request_id: str | None = None) -> bytes:
    body = {
        "response_version": 1,
        "request_id": env_request_id or request_id,
        "request_sha256": request_sha or bridge.request_sha256(request_id),
        "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
        "directive": {"capability_calls": [], "response": text, "silence": False},
    }
    return canonical_json_bytes(body) + b"\n"


def handler_for(root: pathlib.Path, timeout_s: float = 2.0) -> ExternalSessionModelHandler:
    return ExternalSessionModelHandler(
        ExternalSessionConfig(exchange_root=root, response_timeout_s=timeout_s, poll_interval_s=0.01)
    )


class IAResponder:
    """Reviewer-authored content-blind responder: answers open requests with a
    fixed synthetic terminal text. Used only for disposable exchanges."""

    def __init__(self, root: pathlib.Path, text: str = IA_LABEL + "_TERMINAL") -> None:
        self.root = root
        self.text = text
        self._stop = threading.Event()
        self.errors: list[str] = []
        self.served: list[str] = []
        self._t = threading.Thread(target=self._loop, daemon=True)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._t.join(10)

    def _loop(self):
        while not self._stop.is_set():
            try:
                bridge = ExchangeBridge(self.root)
                for rid in bridge.recovery_state()["open_dispatched"]:
                    bridge.responses.publish_bytes(
                        request_id=rid, response_bytes=envelope(bridge, rid, self.text)
                    )
                    self.served.append(rid)
            except Exception as exc:  # recorded
                self.errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(0.01)


def rewrite_ledger_lines(path: pathlib.Path, mutate) -> None:
    lines = path.read_bytes().splitlines(keepends=True)
    path.write_bytes(b"".join(mutate(lines)))
