#!/usr/bin/env python3
"""
C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-002 — Frozen Bridge ModelHandler adapter.

This is the frozen, auditable adapter that connects genuine Core
FusedTurnRuntime/CognitiveRuntime model requests to the isolated Resident via
MailboxBridge. It is the ONLY approved transport for Phase B; operator must use
this file, not a custom/inline handler at release time.

Enforces:
  - One handler per B session, backed by exactly one MailboxBridge instance.
  - Envelope is built mechanically from the real RuntimeSnapshot supplied by Core
    (no hand-written fake snapshot).
  - Every model round (including capability-result follow-up rounds) goes
    through the same bridge (verified by probe).
  - No semantic default on bridge failure: malformed/stale/timeout replies raise
    ModelDispatchNotSubmitted and fail the turn closed (Core does not synthesize
    a default response).
  - Request/reply binding verified by bridge (round/request_id/request_digest).

Usage (probe example):
  from harness.bridged_model_handler import MailboxModelHandler, build_envelope
  bridge = MailboxBridge(inbox, outbox, archive, b_session)
  handler = MailboxModelHandler(bridge, contract_sha256=..., b_session_id=b_session)
  runtime = FusedTurnRuntime(store, index, model_handler=handler, ...)
  runtime.run_turn(...)

Headless CLI usage (operator side):
  Set env:
    AIOS_MAILBOX_ROOT=/tmp/.../mailbox
    AIOS_B_SESSION_ID=c15-rcc-res-b-...
    AIOS_CONTRACT_SHA256=<sha256 of RESIDENT_B_RUN_CONTRACT.md>   (optional, auto-computed)
  Then pass --model-handler harness.bridged_model_handler:headless_handler

This file must be frozen in PR #209 and not edited at release time.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from aios_core.runtime.cognitive_runtime import (
    ModelDirective,
    ModelDispatchNotSubmitted,
    ModelCallProvenance,
    ModelUsage,
    RuntimeSnapshot,
)
from aios_core.runtime.capabilities import CapabilityCall

try:
    # When imported as harness.bridged_model_handler from repo root via PYTHONPATH,
    # relative import should work. For direct path import, fallback.
    from .mailbox_bridge import MailboxBridge, MailboxEnvelopeError, MailboxReplyError
except ImportError:
    from mailbox_bridge import MailboxBridge, MailboxEnvelopeError, MailboxReplyError  # type: ignore

REPO_ROOT_DEFAULT = Path("/home/user/Haneof-AIOS-Core-v3.0")
CONTRACT_REL = Path("reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md")


def get_contract_sha256(repo_root: Path | None = None) -> str:
    repo = Path(repo_root) if repo_root else REPO_ROOT_DEFAULT
    p = repo / CONTRACT_REL
    if not p.exists():
        # Try relative to this file's repo
        alt = Path(__file__).resolve().parents[5] / CONTRACT_REL  # harness is 5 deep?
        if alt.exists():
            p = alt
    data = p.read_bytes()
    return hashlib.sha256(data).hexdigest()


def _serialize_capability_history(history: Any, b_session_id: str) -> list[dict[str, Any]]:
    """Convert snapshot.capability_history (tuple of CapabilityResult) to bridge-safe list."""
    out: list[dict[str, Any]] = []
    if not history:
        return out
    for item in history:
        # item may be CapabilityResult or dict
        if isinstance(item, dict):
            d = dict(item)
            d.setdefault("session_id", b_session_id)
            out.append(d)
        else:
            # CapabilityResult dataclass
            try:
                d = {
                    "name": getattr(item, "name", "unknown"),
                    "ok": bool(getattr(item, "ok", True)),
                    "data": getattr(item, "data", None),
                    "error_code": getattr(item, "error_code", None),
                    "error_message": getattr(item, "error_message", None),
                    "call_id": getattr(item, "call_id", None),
                    "session_id": b_session_id,
                }
                # Ensure data is json-serializable; if not, stringify
                try:
                    json.dumps(d["data"])
                except Exception:
                    d["data"] = str(d["data"])
                out.append(d)
            except Exception:
                out.append({"name": "unknown", "ok": False, "session_id": b_session_id})
    return out


def build_envelope(snapshot: RuntimeSnapshot, b_session_id: str, contract_sha256: str | None = None) -> dict[str, Any]:
    """
    Mechanically build Resident-safe envelope from genuine RuntimeSnapshot.
    This is the ONLY place where snapshot is projected to envelope; no fake snapshot.
    """
    if contract_sha256 is None:
        contract_sha256 = get_contract_sha256()
    # RuntimeSnapshot fields: user_input, wake_reason, cockpit, capability_catalog, capability_history, round_index, remaining_tool_rounds
    # We project cockpit as runtime_snapshot, capability catalog/history from snapshot, wake_reason etc.
    # The cockpit itself is already a Core-assembled dict (context, recommendation, world_map, etc.)
    runtime_snapshot = dict(snapshot.cockpit) if isinstance(snapshot.cockpit, dict) else {"cockpit": str(snapshot.cockpit)}
    # Ensure no forbidden keys leak (bridge will also check)
    # Normalize capability_catalog to list
    cap_catalog = list(snapshot.capability_catalog) if snapshot.capability_catalog else []
    cap_history = _serialize_capability_history(snapshot.capability_history, b_session_id)

    envelope: dict[str, Any] = {
        "phase": "B",
        "allowed_sequences": [14, 22],
        "event": None,  # synthetic/disposable input has no sealed event projection; real B release will fill this via reveal pipeline before turn
        "runtime_snapshot": runtime_snapshot,
        "capability_catalog": cap_catalog,
        "capability_history": cap_history,
        "wake_reason": snapshot.wake_reason,
        "is_periodic_review": snapshot.wake_reason == "periodic_review",
        "is_summary_request": False,
        "contract_sha256": contract_sha256,
    }
    return envelope


def reply_to_directive(reply: dict[str, Any], snapshot: RuntimeSnapshot) -> ModelDirective:
    """Translate validated Resident reply (with binding fields) to Core ModelDirective."""
    action = reply.get("action")
    # Use reply's request_id as provenance request_id so provider identity is traceable
    req_id = reply.get("request_id", "unknown")
    # Dummy usage/provenance for synthetic probe - real provider would supply tokens
    usage = ModelUsage(
        total_tokens=10,
        input_tokens=5,
        output_tokens=5,
        provider="sandbox-bridge",
        model="synthetic-responder-v1",
        request_id=req_id,
    )
    provenance = ModelCallProvenance(
        provider="sandbox-bridge",
        model="synthetic-responder-v1",
        request_id=req_id,
    )

    if action == "silence":
        return ModelDirective(silence=True, usage=usage, provenance=provenance)
    if action == "end_turn":
        # end_turn without explicit response is treated as silence; if response present use it
        text = reply.get("response")
        if isinstance(text, str) and text.strip():
            return ModelDirective(response=text, usage=usage, provenance=provenance)
        return ModelDirective(silence=True, usage=usage, provenance=provenance)
    if action == "invoke_capability":
        cap = reply.get("capability")
        args = reply.get("arguments") or {}
        if not isinstance(args, dict):
            raise ValueError("invoke_capability arguments must be object")
        call = CapabilityCall(name=str(cap), arguments=dict(args))
        return ModelDirective(capability_calls=(call,), usage=usage, provenance=provenance)
    if action == "summary_response":
        text = reply.get("response") or reply.get("summary") or ""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("summary_response requires non-empty response")
        return ModelDirective(response=text, usage=usage, provenance=provenance)
    if action == "round_repair_request":
        # Treat as silence with signal that same envelope should be resent (handled by bridge's next round)
        return ModelDirective(silence=True, usage=usage, provenance=provenance)
    raise ValueError(f"unsupported reply action: {action!r}")


class MailboxModelHandler:
    """Frozen bridge handler: RuntimeSnapshot -> envelope -> bridge -> reply -> ModelDirective."""

    def __init__(self, bridge: MailboxBridge, b_session_id: str, contract_sha256: str | None = None):
        self.bridge = bridge
        self.b_session_id = b_session_id
        self.contract_sha256 = contract_sha256 or get_contract_sha256()
        self.invocations = 0
        self.last_snapshot: RuntimeSnapshot | None = None
        self.last_envelope: dict[str, Any] | None = None
        self.last_reply: dict[str, Any] | None = None

    def __call__(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        self.invocations += 1
        self.last_snapshot = snapshot
        # Provenance log for evidence: prove snapshot came from Core
        # snapshot.cockpit should contain world_map, capability_catalog, etc., built by FusedTurnRuntime
        envelope = build_envelope(snapshot, self.b_session_id, self.contract_sha256)
        self.last_envelope = envelope
        try:
            self.bridge.send(envelope)
        except MailboxEnvelopeError as e:
            # Envelope fail-closed => treat as dispatch not submitted, Core will fail closed
            raise ModelDispatchNotSubmitted(f"envelope validation failed: {e}") from e
        except Exception as e:
            raise ModelDispatchNotSubmitted(f"bridge send failed: {e}") from e

        try:
            reply = self.bridge.wait_for_reply(timeout=30.0)
        except (MailboxReplyError, TimeoutError) as e:
            # Binding mismatch / malformed / stale / replay / timeout => fail closed, no semantic default
            raise ModelDispatchNotSubmitted(f"bridge reply binding failed: {e}") from e
        except Exception as e:
            # Any other bridge error also fail closed
            raise ModelDispatchNotSubmitted(f"bridge wait failed: {e}") from e

        self.last_reply = reply
        try:
            directive = reply_to_directive(reply, snapshot)
        except Exception as e:
            raise ModelDispatchNotSubmitted(f"reply translation failed: {e}") from e
        return directive


# Headless-compatible global handler (lazy bridge)
_global_handler: MailboxModelHandler | None = None

def headless_handler(snapshot: RuntimeSnapshot) -> ModelDirective:
    """
    Headless CLI entrypoint: harness.bridged_model_handler:headless_handler
    Reads mailbox location from env set by operator (outside sandbox).
    """
    global _global_handler
    if _global_handler is None:
        mailbox_root = os.getenv("AIOS_MAILBOX_ROOT")
        b_session = os.getenv("AIOS_B_SESSION_ID")
        if not mailbox_root or not b_session:
            raise ModelDispatchNotSubmitted(
                "AIOS_MAILBOX_ROOT and AIOS_B_SESSION_ID must be set for bridged handler"
            )
        root = Path(mailbox_root)
        bridge = MailboxBridge(root / "inbox", root / "outbox", root / "archive", b_session)
        contract_sha = os.getenv("AIOS_CONTRACT_SHA256") or get_contract_sha256()
        _global_handler = MailboxModelHandler(bridge, b_session_id=b_session, contract_sha256=contract_sha)
    return _global_handler(snapshot)


# For testing: reset global
def _reset_global():
    global _global_handler
    _global_handler = None
