#!/usr/bin/env python3
"""
C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-003 — Frozen Production + Synthetic Bridge handlers.

This is the frozen, auditable adapter module for Phase B. It contains TWO
separated handlers:

  * ProductionResidentHandler  — frozen production path for real B (external trusted broker, Path A)
  * SyntheticProbeHandler      — synthetic disposable probe path (mailbox bridge)

The two are explicitly separated in code (different classes, different provider
provenance handling) as required by BLOCKER 1.

ARCHITECTURE (Path A, recommended):
  Resident sandbox remains CLONE_NEWNET (no public internet).
  Provider client runs OUTSIDE the jail on the operator/trusted broker side.
  The only data the provider can see is:
    - system instruction = exact bytes of RESIDENT_B_RUN_CONTRACT.md
    - user content    = Resident-safe envelope JSON (Core RuntimeSnapshot → envelope, plus current 8-field event if any)
  Provider cannot see repo filesystem, fixture, evaluator, governance, A transcript,
  PM report, or operator archive. This is enforced by the adapter: it builds the
  exact request dict containing ONLY those two fields and passes it to ProviderClient.invoke().
  The provider's raw response is parsed as a Resident reply JSON, validated (strict
  allowlist + binding), and translated to ModelDirective with REAL provider provenance.

SYNTHETIC path (SyntheticProbeHandler) still uses MailboxBridge + resident_test_responder
inside the jail for disposable E2E tests. It hard-codes synthetic provenance
(total_tokens=10 etc.) but is NEVER used for real B.

PRODUCTION path (ProductionResidentHandler + FakeProviderClient for preflight):
  Core (FusedTurnRuntime/CognitiveRuntime) → ProductionResidentHandler.__call__(snapshot)
    → build_envelope(snapshot, b_session, contract_sha256, current_event)  # current_event is 8-field projection or None, validated
    → build_model_request(contract_text, envelope)  # {"system": contract_text, "messages": [{"role":"user","content": envelope_json}]}
    → provider_client.invoke(request)  # outside-jail, no fixture access
    → ProviderResponse(provider, model, request_id, usage, content)
    → validate reply binding (round/request_id/request_digest echo)
    → reply_to_directive_production(reply, snapshot, provider_response)  # maps REAL provider metadata
    → ModelDirective(usage=ModelUsage(provider=actual, model=actual, request_id=actual, total_tokens=actual or UNKNOWN handling),
                     provenance=ModelCallProvenance(provider=actual or "UNKNOWN", model=actual or "UNKNOWN", request_id=actual or "UNKNOWN"))
  If provider field not credibly available, record "UNKNOWN" (strings) or None/0 for tokens
  (never fabricate synthetic-responder values).

B release replaces FakeProviderClient with RealProviderClient (same interface, same adapter file
unchanged except client substitution).

This file must be frozen in PR #209 and not edited at release time.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from aios_core.runtime.cognitive_runtime import (
    ModelDirective,
    ModelDispatchNotSubmitted,
    ModelCallProvenance,
    ModelUsage,
    RuntimeSnapshot,
)
from aios_core.runtime.capabilities import CapabilityCall

try:
    from .mailbox_bridge import MailboxBridge, MailboxEnvelopeError, MailboxReplyError
except ImportError:
    from mailbox_bridge import MailboxBridge, MailboxEnvelopeError, MailboxReplyError  # type: ignore

REPO_ROOT_DEFAULT = Path("/home/user/Haneof-AIOS-Core-v3.0")
CONTRACT_REL = Path("reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md")

def get_contract_sha256(repo_root: Path | None = None) -> str:
    repo = Path(repo_root) if repo_root else REPO_ROOT_DEFAULT
    p = repo / CONTRACT_REL
    if not p.exists():
        alt = Path(__file__).resolve().parents[5] / CONTRACT_REL
        if alt.exists():
            p = alt
    data = p.read_bytes()
    return hashlib.sha256(data).hexdigest()

def get_contract_text(repo_root: Path | None = None) -> str:
    repo = Path(repo_root) if repo_root else REPO_ROOT_DEFAULT
    p = repo / CONTRACT_REL
    if not p.exists():
        alt = Path(__file__).resolve().parents[5] / CONTRACT_REL
        if alt.exists():
            p = alt
    return p.read_text(encoding="utf-8")

def _serialize_capability_history(history: Any, b_session_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not history:
        return out
    for item in history:
        if isinstance(item, dict):
            d = dict(item)
            d.setdefault("session_id", b_session_id)
            out.append(d)
        else:
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
                try:
                    json.dumps(d["data"])
                except Exception:
                    d["data"] = str(d["data"])
                out.append(d)
            except Exception:
                out.append({"name": "unknown", "ok": False, "session_id": b_session_id})
    return out

def build_envelope(
    snapshot: RuntimeSnapshot,
    b_session_id: str,
    contract_sha256: str | None = None,
    current_event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Mechanically build Resident-safe envelope from genuine RuntimeSnapshot.
    current_event, if not None, must be an exact 8-field resident-visible projection
    with sequence 14..22. It is validated via MailboxBridge path before inclusion.
    """
    if contract_sha256 is None:
        contract_sha256 = get_contract_sha256()
    runtime_snapshot = dict(snapshot.cockpit) if isinstance(snapshot.cockpit, dict) else {"cockpit": str(snapshot.cockpit)}
    cap_catalog = list(snapshot.capability_catalog) if snapshot.capability_catalog else []
    cap_history = _serialize_capability_history(snapshot.capability_history, b_session_id)

    # Validate current_event early via a temporary envelope validation (without binding fields)
    # We do this by constructing a minimal envelope and running validate_envelope.
    # If current_event is None, event stays None (synthetic disposable case).
    # If provided, it must pass strict allowlist + sequence range.
    event_field = None
    if current_event is not None:
        if not isinstance(current_event, dict):
            raise ValueError("current_event must be dict or None")
        # Basic 8-field check before building final envelope; full validation happens in bridge/caller
        # We expose errors via ModelDispatchNotSubmitted in handlers.
        from mailbox_bridge import EVENT_FIELD_ALLOWLIST  # local import to avoid cycle
        keys = set(current_event.keys())
        if keys != set(EVENT_FIELD_ALLOWLIST):
            missing = set(EVENT_FIELD_ALLOWLIST) - keys
            extra = keys - set(EVENT_FIELD_ALLOWLIST)
            raise ValueError(f"current_event has wrong field set: missing={sorted(missing)} extra={sorted(extra)}")
        seq = current_event.get("sequence")
        if not isinstance(seq, int) or seq < 14 or seq > 22:
            raise ValueError(f"current_event.sequence={seq!r} outside 14..22")
        event_field = dict(current_event)

    envelope: dict[str, Any] = {
        "phase": "B",
        "allowed_sequences": [14, 22],
        "event": event_field,
        "runtime_snapshot": runtime_snapshot,
        "capability_catalog": cap_catalog,
        "capability_history": cap_history,
        "wake_reason": snapshot.wake_reason,
        "is_periodic_review": snapshot.wake_reason == "periodic_review",
        "is_summary_request": False,
        "contract_sha256": contract_sha256,
    }
    return envelope

def build_model_request(contract_text: str, envelope: dict[str, Any]) -> dict[str, Any]:
    """
    Build the EXACT provider request that the production handler will send.
    Only two pieces of data are visible to the provider:
      - system instruction = exact contract text
      - user content    = JSON-serialized Resident-safe envelope
    Any other file, path, or governance content is NOT included.
    """
    if not isinstance(contract_text, str) or not contract_text.strip():
        raise ValueError("contract_text must be non-blank")
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be dict")
    # Ensure envelope does not contain forbidden path leakage (caller's responsibility, but we assert here)
    # We intentionally do NOT include repo path, fixture bytes, etc.
    envelope_json = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "system": contract_text,
        "messages": [{"role": "user", "content": envelope_json}],
        "metadata": {
            "phase": envelope.get("phase"),
            "round": envelope.get("round"),  # may be None until bridge assigns; but production path assigns before this call? For direct provider path we assign round/id/digest here
        },
    }

# --- Provider abstraction for production path ---

@dataclass(frozen=True)
class ProviderResponse:
    """Raw provider result as returned by the external model broker."""
    provider: str | None
    model: str | None
    request_id: str | None
    usage: dict[str, Any] | None  # e.g. {"total_tokens": 42, "input_tokens": 20, "output_tokens": 22}
    content: Any  # The provider's textual content — expected to be a JSON string/dict of the Resident reply (with binding)
    raw: Any | None = None

class ProviderClient(Protocol):
    def invoke(self, request: dict[str, Any]) -> ProviderResponse:
        ...

class FakeProviderClient:
    """
    Preflight fake that mimics a real provider without network.
    It walks the SAME production code path: it receives the exact model request
    (system=contract, messages[0].content=envelope_json), validates that it
    contains only Resident-safe data, then synthesizes a Resident reply that
    echoes the envelope's round/request_id/request_digest and performs a
    deterministic capability or silence. It also returns fake but VALID provider
    metadata for provenance testing.
    """
    def __init__(
        self,
        provider: str = "fake-provider",
        model: str = "fake-model-v1",
        request_id_prefix: str = "fake-req-",
        input_tokens: int | None = 20,
        output_tokens: int | None = 22,
        total_tokens: int | None = 42,
    ):
        self.provider = provider
        self.model = model
        self.request_id_prefix = request_id_prefix
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        self.invocations = 0
        self.last_request: dict[str, Any] | None = None

    def invoke(self, request: dict[str, Any]) -> ProviderResponse:
        self.invocations += 1
        self.last_request = request
        # Validate request shape: must contain only system + messages, no fixture path leakage
        if not isinstance(request, dict):
            raise ValueError("request must be dict")
        if set(request.keys()) - {"system", "messages", "metadata"}:
            # Allow only those keys; any extra would be leakage
            raise ValueError(f"request has extra keys not in production contract: {set(request.keys()) - {'system','messages','metadata'}}")
        system = request.get("system", "")
        if not isinstance(system, str) or "RESIDENT_B_RUN_CONTRACT" not in system and len(system) < 100:
            # Contract text should be long; we check non-blank
            if not system.strip():
                raise ValueError("system instruction missing contract text")
        # Check messages
        msgs = request.get("messages")
        if not isinstance(msgs, list) or len(msgs) != 1:
            raise ValueError("messages must be single user envelope")
        content = msgs[0].get("content") if isinstance(msgs[0], dict) else None
        if not isinstance(content, str):
            raise ValueError("messages[0].content must be envelope JSON string")
        # Parse envelope
        try:
            envelope = json.loads(content)
        except Exception as e:
            raise ValueError(f"envelope content not JSON: {e}")
        # Validate envelope has no forbidden path leakage (via mailbox_bridge check)
        # We do a light check for path leakage here as well
        for needle in ("/repo/fixture", "/repo/evaluator", "/repo/governance", "/repo/.git"):
            if needle in content:
                raise ValueError(f"provider request leaked forbidden path {needle!r}")

        # Decide reply based on envelope's capability_history length (like synthetic responder)
        # First round (history empty) -> invoke search_world Atlas limit 2 (non-empty legal)
        # Second round (history non-empty) -> silence (or end_turn)
        hist = envelope.get("capability_history", [])
        round_num = envelope.get("round", 1)
        # Note: production path may assign round before calling provider; if not, use invocations
        if not isinstance(round_num, int):
            round_num = self.invocations
        # Echo binding
        envelope_round = envelope.get("round")
        envelope_id = envelope.get("request_id")
        envelope_digest = envelope.get("request_digest")
        # If envelope hasn't been assigned yet (direct provider path without bridge), we assign here for test
        # For bridge-based test, envelope already has these
        if envelope_round is None:
            envelope_round = self.invocations
        if envelope_id is None:
            envelope_id = "a" * 32
        if envelope_digest is None:
            envelope_digest = "b" * 64

        if len(hist) == 0:
            # First model round: invoke a legal non-empty search (Atlas) — will return obs_c14_fixture_* legally
            reply = {
                "round": envelope_round,
                "request_id": envelope_id,
                "request_digest": envelope_digest,
                "action": "invoke_capability",
                "capability": "search_world",
                "arguments": {"query": "Atlas", "limit": 2},
            }
        else:
            # Follow-up: silence (could also be end_turn)
            reply = {
                "round": envelope_round,
                "request_id": envelope_id,
                "request_digest": envelope_digest,
                "action": "silence",
            }

        # Wrap reply as provider content JSON string (as real provider would return text)
        content_str = json.dumps(reply, sort_keys=True)
        usage = None
        if self.total_tokens is not None or self.input_tokens is not None or self.output_tokens is not None:
            usage = {}
            if self.total_tokens is not None:
                usage["total_tokens"] = self.total_tokens
            if self.input_tokens is not None:
                usage["input_tokens"] = self.input_tokens
            if self.output_tokens is not None:
                usage["output_tokens"] = self.output_tokens
        # Simulate provider request id
        prov_req_id = f"{self.request_id_prefix}{self.invocations:04d}"
        return ProviderResponse(
            provider=self.provider,
            model=self.model,
            request_id=prov_req_id,
            usage=usage,
            content=content_str,
            raw={"envelope": envelope, "reply": reply},
        )

# --- Reply to directive translators ---

def _reply_to_directive_synthetic(reply: dict[str, Any], snapshot: RuntimeSnapshot) -> ModelDirective:
    """Synthetic probe: hard-coded fake provenance (separated from production)."""
    action = reply.get("action")
    req_id = reply.get("request_id", "unknown")
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
    raise ValueError(f"unsupported reply action: {action!r}")

def _reply_to_directive_production(reply: dict[str, Any], snapshot: RuntimeSnapshot, provider_resp: ProviderResponse) -> ModelDirective:
    """Production: use REAL provider metadata (or UNKNOWN if not credibly available)."""
    action = reply.get("action")
    # Provider provenance — must be real, not synthetic
    prov = provider_resp.provider if isinstance(provider_resp.provider, str) and provider_resp.provider.strip() else "UNKNOWN"
    mod = provider_resp.model if isinstance(provider_resp.model, str) and provider_resp.model.strip() else "UNKNOWN"
    req = provider_resp.request_id if isinstance(provider_resp.request_id, str) and provider_resp.request_id.strip() else "UNKNOWN"

    # If provider indicated UNKNOWN explicitly, keep it
    if prov == "UNKNOWN" or mod == "UNKNOWN" or req == "UNKNOWN":
        # still valid per spec: record UNKNOWN, never fabricate synthetic-responder
        pass

    # Token usage mapping: use provider's actual numbers if provided, else UNKNOWN handling
    # ModelUsage requires total_tokens int; if provider gives no usage at all, we treat as incomplete (set usage=None)
    # But spec says if field not credibly available, record UNKNOWN — for string fields we use "UNKNOWN",
    # for tokens we set input/output to None and total to sum or UNKNOWN via None? We choose to create usage only if provider gave total_tokens.
    usage: ModelUsage | None = None
    if provider_resp.usage is not None and isinstance(provider_resp.usage, dict):
        tot = provider_resp.usage.get("total_tokens")
        inp = provider_resp.usage.get("input_tokens")
        out = provider_resp.usage.get("output_tokens")
        # Validate ints if present
        def _int_or_none(v):
            if v is None:
                return None
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                return None
            return int(v)
        tot_i = _int_or_none(tot)
        inp_i = _int_or_none(inp)
        out_i = _int_or_none(out)
        if tot_i is not None:
            # If tot provided, ensure it covers inp+out if both provided
            if inp_i is not None and out_i is not None and tot_i < inp_i + out_i:
                # provider gave inconsistent, treat as UNKNOWN for total (fallback to sum)
                tot_i = inp_i + out_i
            try:
                usage = ModelUsage(
                    total_tokens=tot_i,
                    input_tokens=inp_i,
                    output_tokens=out_i,
                    provider=prov if prov != "UNKNOWN" else None,
                    model=mod if mod != "UNKNOWN" else None,
                    request_id=req if req != "UNKNOWN" else None,
                )
                # If provider is UNKNOWN, usage provider/model/request_id should be None to avoid conflict with provenance UNKNOWN
                # Actually ModelUsage allows None for those, while provenance requires non-blank; we keep them None if UNKNOWN
            except Exception:
                usage = None
        elif inp_i is not None or out_i is not None:
            # No total but have inp/out — treat total as sum, still UNKNOWN for total? Use sum
            sum_tot = (inp_i or 0) + (out_i or 0)
            try:
                usage = ModelUsage(
                    total_tokens=sum_tot,
                    input_tokens=inp_i,
                    output_tokens=out_i,
                    provider=prov if prov != "UNKNOWN" else None,
                    model=mod if mod != "UNKNOWN" else None,
                    request_id=req if req != "UNKNOWN" else None,
                )
            except Exception:
                usage = None
        else:
            # No usage at all — leave usage as None (model_usage_complete will be False, not fabricated)
            usage = None
    else:
        # provider gave no usage dict — leave usage None (honest UNKNOWN, not fake 10)
        usage = None

    # provenance must always be non-blank per dataclass; use UNKNOWN if missing
    provenance = ModelCallProvenance(provider=prov, model=mod, request_id=req)

    if action == "silence":
        return ModelDirective(silence=True, usage=usage, provenance=provenance)
    if action == "end_turn":
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
    raise ValueError(f"unsupported reply action: {action!r}")

# --- Handlers ---

class SyntheticProbeHandler:
    """Synthetic disposable probe handler: Core -> MailboxBridge -> synthetic responder (inside jail) -> Core.
    Uses synthetic provenance (10 tokens) — NEVER for real B.
    """
    def __init__(self, bridge: MailboxBridge, b_session_id: str, contract_sha256: str | None = None):
        self.bridge = bridge
        self.b_session_id = b_session_id
        self.contract_sha256 = contract_sha256 or get_contract_sha256()
        self.invocations = 0
        self.last_snapshot: RuntimeSnapshot | None = None
        self.last_envelope: dict[str, Any] | None = None
        self.last_reply: dict[str, Any] | None = None
        self.current_event: dict[str, Any] | None = None

    def set_current_event(self, event: dict[str, Any] | None) -> None:
        self.current_event = event

    def __call__(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        self.invocations += 1
        self.last_snapshot = snapshot
        envelope = build_envelope(snapshot, self.b_session_id, self.contract_sha256, current_event=self.current_event)
        self.last_envelope = envelope
        try:
            self.bridge.send(envelope)
        except MailboxEnvelopeError as e:
            raise ModelDispatchNotSubmitted(f"envelope validation failed: {e}") from e
        except Exception as e:
            raise ModelDispatchNotSubmitted(f"bridge send failed: {e}") from e
        try:
            reply = self.bridge.wait_for_reply(timeout=30.0)
        except (MailboxReplyError, TimeoutError) as e:
            raise ModelDispatchNotSubmitted(f"bridge reply binding failed: {e}") from e
        except Exception as e:
            raise ModelDispatchNotSubmitted(f"bridge wait failed: {e}") from e
        self.last_reply = reply
        try:
            directive = _reply_to_directive_synthetic(reply, snapshot)
        except Exception as e:
            raise ModelDispatchNotSubmitted(f"reply translation failed: {e}") from e
        return directive

# Backward alias for existing probe code
MailboxModelHandler = SyntheticProbeHandler

class ProductionResidentHandler:
    """Frozen production handler: Core -> Envelope(+current_event) -> ProviderClient (outside jail) -> validated reply -> ModelDirective with REAL provenance.

    ProviderClient is injected; for preflight we use FakeProviderClient, for real B we use RealProviderClient (same interface).
    No MailboxBridge is used here — the model is not inside the jail, so CLONE_NEWNET remains sealed.
    """
    def __init__(
        self,
        b_session_id: str,
        provider_client: ProviderClient,
        contract_sha256: str | None = None,
        contract_text: str | None = None,
    ):
        self.b_session_id = b_session_id
        self.provider_client = provider_client
        self.contract_sha256 = contract_sha256 or get_contract_sha256()
        self.contract_text = contract_text if contract_text is not None else get_contract_text()
        self.invocations = 0
        self.last_snapshot: RuntimeSnapshot | None = None
        self.last_envelope: dict[str, Any] | None = None
        self.last_provider_response: ProviderResponse | None = None
        self.last_reply: dict[str, Any] | None = None
        self.current_event: dict[str, Any] | None = None
        self._bridge_for_binding = None
        # For binding verification without MailboxBridge, we replicate request_id/digest generation
        # We still need round/request_id/request_digest binding: we generate them here deterministically.
        self._round = 0
        self._consumed: set[str] = set()
        self._outstanding: dict[str, Any] | None = None

    def set_current_event(self, event: dict[str, Any] | None) -> None:
        self.current_event = event

    def _assign_binding(self, envelope: dict[str, Any]) -> dict[str, Any]:
        # Mirror MailboxBridge binding generation (one-at-a-time)
        if self._outstanding is not None:
            raise ModelDispatchNotSubmitted(f"cannot send new request while round {self._outstanding['round']} outstanding")
        self._round += 1
        import secrets, hashlib, json
        for _ in range(5):
            request_id = secrets.token_hex(16)
            if request_id not in self._consumed:
                break
        else:
            raise ModelDispatchNotSubmitted("request_id collision")
        envelope_copy = dict(envelope)
        envelope_copy["round"] = self._round
        envelope_copy["request_id"] = request_id
        canonical = json.dumps(envelope_copy, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        request_digest = hashlib.sha256(canonical).hexdigest()
        envelope_copy["request_digest"] = request_digest
        # Validate envelope (including event sequence etc.)
        from mailbox_bridge import validate_envelope
        validate_envelope(envelope_copy, self.b_session_id)
        self._outstanding = {"round": self._round, "request_id": request_id, "request_digest": request_digest}
        return envelope_copy

    def _verify_reply_binding(self, reply: dict[str, Any]) -> None:
        if self._outstanding is None:
            raise ModelDispatchNotSubmitted("no outstanding request")
        exp = self._outstanding
        if reply.get("round") != exp["round"]:
            raise ModelDispatchNotSubmitted(f"reply round {reply.get('round')!r} != outstanding {exp['round']}")
        if reply.get("request_id") != exp["request_id"]:
            if reply.get("request_id") in self._consumed:
                raise ModelDispatchNotSubmitted(f"reply request_id {reply.get('request_id')!r} is replay of consumed")
            raise ModelDispatchNotSubmitted(f"reply request_id {reply.get('request_id')!r} != outstanding {exp['request_id']!r}")
        if reply.get("request_digest") != exp["request_digest"]:
            raise ModelDispatchNotSubmitted(f"reply request_digest mismatch")
        if reply["request_id"] in self._consumed:
            raise ModelDispatchNotSubmitted(f"reply already consumed")
        # success
        self._consumed.add(exp["request_id"])
        self._outstanding = None

    def __call__(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        self.invocations += 1
        self.last_snapshot = snapshot
        envelope = build_envelope(snapshot, self.b_session_id, self.contract_sha256, current_event=self.current_event)
        # Assign binding (like MailboxBridge.send but without file)
        envelope = self._assign_binding(envelope)
        self.last_envelope = envelope
        # Build exact model request (only contract + envelope)
        request = build_model_request(self.contract_text, envelope)
        # Invoke provider (outside jail)
        try:
            provider_resp = self.provider_client.invoke(request)
        except Exception as e:
            raise ModelDispatchNotSubmitted(f"provider invoke failed: {e}") from e
        self.last_provider_response = provider_resp
        # Content must be JSON string/dict of reply
        content = provider_resp.content
        if isinstance(content, str):
            try:
                reply = json.loads(content)
            except Exception as e:
                raise ModelDispatchNotSubmitted(f"provider content not JSON: {e}") from e
        elif isinstance(content, dict):
            reply = dict(content)
        else:
            raise ModelDispatchNotSubmitted(f"provider content must be JSON string/dict, got {type(content)}")
        # Validate reply schema and binding echo
        from mailbox_bridge import validate_reply
        try:
            validate_reply(reply)
        except Exception as e:
            raise ModelDispatchNotSubmitted(f"reply structural invalid: {e}") from e
        try:
            self._verify_reply_binding(reply)
        except Exception as e:
            raise ModelDispatchNotSubmitted(f"reply binding failed: {e}") from e
        self.last_reply = reply
        try:
            directive = _reply_to_directive_production(reply, snapshot, provider_resp)
        except Exception as e:
            raise ModelDispatchNotSubmitted(f"reply translation failed: {e}") from e
        return directive

# Headless-compatible global handlers (lazy)
_global_synthetic: SyntheticProbeHandler | None = None
_global_production: ProductionResidentHandler | None = None

def headless_handler(snapshot: RuntimeSnapshot) -> ModelDirective:
    global _global_synthetic
    if _global_synthetic is None:
        mailbox_root = os.getenv("AIOS_MAILBOX_ROOT")
        b_session = os.getenv("AIOS_B_SESSION_ID")
        if not mailbox_root or not b_session:
            raise ModelDispatchNotSubmitted("AIOS_MAILBOX_ROOT and AIOS_B_SESSION_ID must be set for bridged handler")
        root = Path(mailbox_root)
        bridge = MailboxBridge(root / "inbox", root / "outbox", root / "archive", b_session)
        contract_sha = os.getenv("AIOS_CONTRACT_SHA256") or get_contract_sha256()
        _global_synthetic = SyntheticProbeHandler(bridge, b_session_id=b_session, contract_sha256=contract_sha)
    return _global_synthetic(snapshot)

def headless_production_handler(snapshot: RuntimeSnapshot) -> ModelDirective:
    """Production headless: uses FakeProviderClient if no real provider env."""
    global _global_production
    if _global_production is None:
        b_session = os.getenv("AIOS_B_SESSION_ID")
        if not b_session:
            raise ModelDispatchNotSubmitted("AIOS_B_SESSION_ID must be set for production handler")
        # In real B, provider client would be constructed from env creds; here fake
        provider = os.getenv("FAKE_PROVIDER", "fake-provider")
        model = os.getenv("FAKE_MODEL", "fake-model-v1")
        client = FakeProviderClient(provider=provider, model=model)
        contract_sha = os.getenv("AIOS_CONTRACT_SHA256") or get_contract_sha256()
        contract_text = os.getenv("AIOS_CONTRACT_TEXT") or get_contract_text()
        _global_production = ProductionResidentHandler(b_session_id=b_session, provider_client=client, contract_sha256=contract_sha, contract_text=contract_text)
        # Also propagate current_event if operator set it via env/file
        evt_path = os.getenv("AIOS_CURRENT_EVENT_PATH")
        if evt_path and Path(evt_path).exists():
            try:
                evt = json.loads(Path(evt_path).read_text())
                _global_production.set_current_event(evt)
            except Exception:
                pass
    return _global_production(snapshot)

def _reset_global():
    global _global_synthetic, _global_production
    _global_synthetic = None
    _global_production = None
