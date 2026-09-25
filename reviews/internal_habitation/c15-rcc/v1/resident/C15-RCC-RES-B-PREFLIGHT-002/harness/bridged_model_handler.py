#!/usr/bin/env python3
"""
C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-007 — Frozen Production Transport (ExternalBrokerClient) + Binding Receipt

Blockers closed:
1. REAL_PROVIDER_CLIENT_IS_SEMANTIC_STUB -> ExternalBrokerClient is pure transport (HTTP POST), no semantic decision logic
2. PIN -> exact module:factory:sha256:version
3. CURRENT EVENT binding receipt -> independent receipt vs current-event.json
4. Scheme-A -> _poisoned + durable evidence
5. Wire protocol -> capability string, validated against snapshot.capability_catalog
6-8 handled in manifest/procedure/probe
"""
from __future__ import annotations
import hashlib, importlib, json, os, time, secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from aios_core.runtime.cognitive_runtime import ModelDirective, ModelDispatchNotSubmitted, ModelCallProvenance, ModelUsage, RuntimeSnapshot
from aios_core.runtime.capabilities import CapabilityCall

try:
    from .mailbox_bridge import MailboxBridge, MailboxEnvelopeError, MailboxReplyError
except ImportError:
    from mailbox_bridge import MailboxBridge, MailboxEnvelopeError, MailboxReplyError  # type: ignore

# CORRECTIVE-009 / BLK-08: repository root is resolved MECHANICALLY from this file.
# There is deliberately NO hardcoded absolute path and NO parents[N] guess.
CONTRACT_REL = Path("reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md")
WIRE_PROTOCOL_REL = Path("reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/harness/resident_wire_protocol.json")
CORE_PKG_REL = Path("src") / "aios_core"


def resolve_repo_root() -> Path:
    """Resolve the unique accepted repository root that physically contains this harness.

    Walks upward from ``__file__`` and accepts the single ancestor that simultaneously
    contains ``src/aios_core`` (frozen Core tree) and the canonical B run contract.
    No absolute fallback: if the ancestor cannot be determined uniquely we fail closed,
    so the provider request can never be built from an unrelated checkout.
    """
    start = Path(__file__).resolve()
    matches: list[Path] = []
    for cand in (start.parent, *start.parent.parents):
        if (cand / CORE_PKG_REL).is_dir() and (cand / CONTRACT_REL).is_file():
            matches.append(cand)
    if len(matches) == 1:
        return matches[0].resolve()
    if not matches:
        raise ValueError(
            f"BLK-08: cannot resolve repo root from {start}: no ancestor contains both "
            f"{CORE_PKG_REL} and {CONTRACT_REL} (refusing to fall back to any absolute path)"
        )
    raise ValueError(
        f"BLK-08: ambiguous repo root resolution from {start}: {[str(m) for m in matches]}"
    )


def _bound_repo_file(repo_root: Path | None, rel: Path) -> Path:
    """Resolve ``rel`` inside ``repo_root`` and prove it cannot escape the accepted tree.

    Enforces: regular file, resolved path stays inside the resolved repo root (symlink
    escape rejected), and the resolved repo root is the mechanically resolved one when
    no explicit root is supplied.
    """
    repo = (Path(repo_root) if repo_root else resolve_repo_root()).resolve()
    if not repo.is_dir():
        raise ValueError(f"BLK-08: resolved repo root {repo} is not a directory")
    raw = repo / rel
    resolved = raw.resolve()
    if not resolved.is_relative_to(repo):
        raise ValueError(f"BLK-08: {rel} resolves outside accepted repo root {repo} (symlink escape)")
    if not resolved.is_file():
        raise ValueError(f"BLK-08: required file missing inside accepted repo root: {rel}")
    return resolved
WIRE_PROTOCOL_SHA256 = "a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a"  # 1.0.1 mechanical
WIRE_PROTOCOL_VERSION = "1.0.1"

# Pinned adapter identity (exact)
PINNED_ADAPTER = {
    "module": "bridged_model_handler",
    "factory": "ExternalBrokerClient",
    "version": "1.0.0-frozen",
    "protocol_version": "c15-rcc-b-wire-v1",
    # sha256 will be computed at import time and verified on load; stored here for reference
    # exact file sha is recomputed in get_adapter_sha256()
}

def _file_sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def get_adapter_sha256() -> str:
    # Compute SHA256 of this file (the frozen implementation)
    p = Path(__file__).resolve()
    if p.exists():
        return _file_sha256(p)
    # fallback
    alt = Path(__file__).parent / "bridged_model_handler.py"
    if alt.exists():
        return _file_sha256(alt)
    return "unknown"

def get_contract_sha256(repo_root: Path | None = None) -> str:
    p = _bound_repo_file(repo_root, CONTRACT_REL)
    return hashlib.sha256(p.read_bytes()).hexdigest()

def get_contract_text(repo_root: Path | None = None) -> str:
    p = _bound_repo_file(repo_root, CONTRACT_REL)
    return p.read_text(encoding="utf-8")

def get_wire_protocol_sha256(repo_root: Path | None = None) -> str:
    p = _bound_repo_file(repo_root, WIRE_PROTOCOL_REL)
    actual = hashlib.sha256(p.read_bytes()).hexdigest()
    if actual != WIRE_PROTOCOL_SHA256:
        raise ValueError(f"wire protocol hash mismatch: expected {WIRE_PROTOCOL_SHA256}, got {actual}")
    return WIRE_PROTOCOL_SHA256

def get_wire_protocol_text(repo_root: Path | None = None) -> str:
    p = _bound_repo_file(repo_root, WIRE_PROTOCOL_REL)
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
                d = {"name": getattr(item, "name", "unknown"), "ok": bool(getattr(item, "ok", True)), "data": getattr(item, "data", None), "error_code": getattr(item, "error_code", None), "error_message": getattr(item, "error_message", None), "call_id": getattr(item, "call_id", None), "session_id": b_session_id}
                try: json.dumps(d["data"])
                except: d["data"] = str(d["data"])
                out.append(d)
            except: out.append({"name": "unknown", "ok": False, "session_id": b_session_id})
    return out

def _validate_current_event_fields(current_event: dict[str, Any]) -> None:
    from mailbox_bridge import EVENT_FIELD_ALLOWLIST
    keys = set(current_event.keys())
    if keys != set(EVENT_FIELD_ALLOWLIST):
        missing = set(EVENT_FIELD_ALLOWLIST) - keys
        extra = keys - set(EVENT_FIELD_ALLOWLIST)
        raise ValueError(f"current_event has wrong field set: missing={sorted(missing)} extra={sorted(extra)}")
    seq = current_event.get("sequence")
    if not isinstance(seq, int) or seq < 14 or seq > 22:
        raise ValueError(f"current_event.sequence={seq!r} outside 14..22")
    sk = current_event.get("source_kind")
    # Allow any non-empty source_kind (fixture has conversation/monitoring etc), not just mechanical
    if not isinstance(sk, str) or not sk.strip():
        raise ValueError(f"current_event.source_kind must be non-empty string, got {sk!r}")
    for f in ("source_class", "modality", "dimension", "event_id", "occurred_at"):
        v = current_event.get(f)
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"current_event.{f} must be non-empty string")
    payload = current_event.get("resident_visible_payload")
    # Payload may be string (fixture) or dict (synthetic); must be non-empty
    if isinstance(payload, dict):
        if not payload:
            raise ValueError("resident_visible_payload dict must be non-empty")
    elif isinstance(payload, str):
        if not payload.strip():
            raise ValueError("resident_visible_payload string must be non-empty")
    else:
        raise ValueError(f"resident_visible_payload must be string or object, got {type(payload).__name__}")

def _canonical_projection_bytes(event: dict[str, Any]) -> bytes:
    # Canonical 8-field projection bytes (sorted keys, no whitespace)
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def _current_event_payload_digest(current_event: dict[str, Any]) -> str:
    payload = current_event.get("resident_visible_payload", {})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

def _canonical_projection_sha256(event: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_projection_bytes(event)).hexdigest()

# --- Binding receipt ---

def create_current_event_binding_receipt(
    projection: dict[str, Any],
    b_session_id: str,
    release_state_path: Path | str,
    fixture_sha256: str = "sha256:7ccb309d207cb6ee240fbc008ee4f535e25571f04ba7ca1b7c95bf9afb5ebf46",
    operator_request_id: str | None = None,
) -> dict[str, Any]:
    """
    Operator side: create immutable binding receipt from exact reveal projection bytes.
    Must be called immediately after release_operator reveal, capturing exact stdout bytes.
    """
    _validate_current_event_fields(projection)
    canonical_sha = _canonical_projection_sha256(projection)
    rs_path = Path(release_state_path)
    # Fail-closed: release_state must exist and be readable
    if not rs_path.exists():
        raise ValueError(f"release_state missing at {rs_path} (must exist)")
    try:
        rs_text = rs_path.read_bytes()
    except Exception as e:
        raise ValueError(f"release_state unreadable at {rs_path}: {e}")
    try:
        rs = json.loads(rs_text.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"release_state malformed JSON at {rs_path}: {e}")
    try:
        rs_sha = hashlib.sha256(rs_text).hexdigest()
        rs_next = rs.get("next_sequence")
        rs_pending = rs.get("pending_reveal")
    except Exception as e:
        raise ValueError(f"release_state parse failed: {e}")
    if rs_next is None:
        raise ValueError("release_state missing next_sequence")
    if rs_pending is None:
        raise ValueError(f"release_state pending_reveal missing (must have pending reveal for seq {projection.get('sequence')})")
    if rs_pending.get("sequence") != projection.get("sequence"):
        raise ValueError(f"pending_reveal.sequence {rs_pending.get('sequence')!r} != projection sequence {projection.get('sequence')!r} (mismatch)")
    if rs_pending.get("event_id") != projection.get("event_id"):
        raise ValueError(f"pending_reveal.event_id {rs_pending.get('event_id')!r} != projection event_id {projection.get('event_id')!r} (mismatch)")
    if rs_next != projection.get("sequence"):
        raise ValueError(f"release_state next_sequence {rs_next!r} != projection sequence {projection.get('sequence')!r} (mismatch)")
    # CORRECTIVE-008: fixture triple-binding — pending fixture must exist and equal canonical, receipt must carry that exact
    canon_fixture = "sha256:7ccb309d207cb6ee240fbc008ee4f535e25571f04ba7ca1b7c95bf9afb5ebf46"
    pending_fixture = rs_pending.get("fixture_sha256")
    if not pending_fixture:
        raise ValueError(f"release_state pending_reveal.fixture_sha256 missing (must be {canon_fixture!r})")
    if pending_fixture != canon_fixture:
        raise ValueError(f"release_state pending_reveal.fixture_sha256 {pending_fixture!r} != canonical {canon_fixture!r} (live fixture mismatch)")
    # Also ensure the passed fixture_sha256 (if not default) matches canonical/pending, otherwise STOP
    if fixture_sha256 != canon_fixture:
        raise ValueError(f"fixture_sha256 {fixture_sha256!r} != canonical {canon_fixture!r} (must be canonical)")
    if fixture_sha256 != pending_fixture:
        raise ValueError(f"fixture_sha256 {fixture_sha256!r} != pending_reveal.fixture_sha256 {pending_fixture!r} (mismatch)")
    receipt = {
        "phase": "B",
        "b_session_id": b_session_id,
        "sequence": projection.get("sequence"),
        "event_id": projection.get("event_id"),
        "occurred_at": projection.get("occurred_at"),
        "source_kind": projection.get("source_kind"),
        "source_class": projection.get("source_class"),
        "modality": projection.get("modality"),
        "dimension": projection.get("dimension"),
        "canonical_projection_sha256": canonical_sha,
        "resident_visible_payload_sha256": _current_event_payload_digest(projection),
        "release_state_path": str(rs_path),
        "release_state_sha256": rs_sha,
        "release_state_next_sequence": rs_next,
        "release_state_pending_reveal": rs_pending,
        "fixture_sha256": fixture_sha256,
        "reveal_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "operator_request_id": operator_request_id or secrets.token_hex(8),
        "binding_version": "c15-rcc-b-binding-v1",
    }
    return receipt

def write_binding_receipt(receipt: dict[str, Any], dest_path: Path | str) -> None:
    dest = Path(dest_path)
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f"binding receipt dest mkdir failed: {e}")
    tmp = dest.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        raise ValueError(f"binding receipt write failed: {e}")
    try:
        tmp.chmod(0o400)
    except Exception as e:
        raise ValueError(f"binding receipt chmod tmp failed: {e}")
    try:
        tmp.replace(dest)
    except Exception as e:
        raise ValueError(f"binding receipt replace failed: {e}")
    try:
        dest.chmod(0o400)
    except Exception as e:
        raise ValueError(f"binding receipt chmod dest failed: {e}")
    # Verify file exists and is 0400
    if not dest.exists():
        raise ValueError("binding receipt not written")
    try:
        mode = dest.stat().st_mode & 0o777
        if mode != 0o400:
            # enforce 0400; if not, fail-closed
            raise ValueError(f"binding receipt permissions {oct(mode)} != 0o400")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"binding receipt permission check failed: {e}")

def validate_current_event_binding(
    current_event: dict[str, Any] | None,
    b_session_id: str,
    release_state_path: Path | str | None = None,
    binding_receipt_path: Path | str | None = None,
) -> None:
    """
    Validate current_event against independent binding receipt and release_state.
    Must be called by ProductionResidentHandler on every __call__.
    """
    # Resolve paths
    rs_path = None
    if release_state_path:
        rs_path = Path(release_state_path)
    else:
        env_rs = os.getenv("AIOS_RELEASE_STATE_PATH")
        if env_rs:
            rs_path = Path(env_rs)
    bind_path = None
    if binding_receipt_path:
        bind_path = Path(binding_receipt_path)
    else:
        env_bind = os.getenv("AIOS_CURRENT_EVENT_BINDING_PATH")
        if env_bind:
            bind_path = Path(env_bind)
        else:
            # default location relative to release_state
            if rs_path:
                bind_path = rs_path.parent.parent / "binding" / "current-event-binding.json"
                # also try RUN_ROOT/binding
                alt = rs_path.parent / "binding" / "current-event-binding.json"
                if alt.exists():
                    bind_path = alt
    # CORRECTIVE-009 / BLK-04: the live release state is MANDATORY for a Phase-B binding.
    # A missing / unreadable / malformed / non-object state file can never downgrade the
    # validation to "receipt only". Fail closed before anything else is inspected.
    if rs_path is None:
        raise ValueError("BLK-04: release_state_path is mandatory for current-event binding (none supplied)")
    if not rs_path.exists():
        raise ValueError(f"BLK-04: release_state missing at {rs_path} (live state must exist)")
    if not rs_path.is_file():
        raise ValueError(f"BLK-04: release_state path is not a regular file: {rs_path}")
    try:
        rs_bytes = rs_path.read_bytes()
    except Exception as e:
        raise ValueError(f"BLK-04: release_state unreadable at {rs_path}: {e}")
    try:
        rs = json.loads(rs_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"BLK-04: release_state malformed JSON at {rs_path}: {e}")
    if not isinstance(rs, dict):
        raise ValueError(f"BLK-04: release_state must be a JSON object at {rs_path}")
    live_rs_sha = hashlib.sha256(rs_bytes).hexdigest()

    if current_event is None:
        # Check if event is required
        try:
            nxt = rs.get("next_sequence")
            # If nxt is not None and pending is None, we may be at a boundary where event is required for next turn
            # For now, if binding receipt exists and expects an event, fail
            if bind_path and bind_path.exists():
                raise ValueError("current-event is None but binding receipt exists (missing event file)")
        except ValueError:
            raise
        except Exception:
            pass
        return
    _validate_current_event_fields(current_event)
    # Must have binding receipt
    if bind_path is None or not bind_path.exists():
        raise ValueError(f"binding receipt missing at {bind_path} (current-event binding must exist)")
    try:
        receipt = json.loads(bind_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"binding receipt malformed JSON: {e}")
    # Validate receipt fields — full schema (CORRECTIVE-007) : 18 required
    required = ("binding_version","phase","b_session_id","sequence","event_id","occurred_at","dimension","source_kind","source_class","modality","canonical_projection_sha256","resident_visible_payload_sha256","fixture_sha256","release_state_path","release_state_sha256","release_state_next_sequence","release_state_pending_reveal","operator_request_id")
    for f in required:
        if f not in receipt:
            raise ValueError(f"binding receipt missing {f}")
    if receipt.get("phase") != "B":
        raise ValueError(f"binding receipt phase {receipt.get('phase')!r} != B")
    if receipt.get("binding_version") != "c15-rcc-b-binding-v1":
        raise ValueError(f"binding receipt binding_version {receipt.get('binding_version')!r} != c15-rcc-b-binding-v1 (wrong version)")
    if receipt.get("b_session_id") != b_session_id:
        raise ValueError(f"binding receipt b_session_id {receipt.get('b_session_id')!r} != {b_session_id!r} (wrong session)")
    # Enforce fixture_sha256 present and exact (must equal canonical C15 fixture SHA) — triple binding (CORRECTIVE-008)
    canon_fixture = "sha256:7ccb309d207cb6ee240fbc008ee4f535e25571f04ba7ca1b7c95bf9afb5ebf46"
    if not receipt.get("fixture_sha256"):
        raise ValueError("binding receipt missing fixture_sha256")
    if receipt.get("fixture_sha256") != canon_fixture:
        raise ValueError(f"binding receipt fixture_sha256 {receipt.get('fixture_sha256')!r} != canonical {canon_fixture!r} (wrong fixture SHA)")
    # Enforce release_state_path identity matches current
    if receipt.get("release_state_path") and rs_path and str(receipt.get("release_state_path")) != str(rs_path):
        raise ValueError(f"binding receipt release_state_path {receipt.get('release_state_path')!r} != current {str(rs_path)!r} (path identity mismatch)")
    if receipt.get("sequence") != current_event.get("sequence"):
        raise ValueError(f"current_event.sequence {current_event.get('sequence')} != receipt sequence {receipt.get('sequence')} (future/stale)")
    if receipt.get("event_id") != current_event.get("event_id"):
        raise ValueError(f"current_event event_id {current_event.get('event_id')!r} != receipt event_id {receipt.get('event_id')!r}")
    # Check occurred_at, dimension, source_kind etc. against receipt if present
    for f in ("occurred_at", "dimension", "source_kind", "source_class", "modality"):
        if f in receipt and receipt[f] != current_event.get(f):
            raise ValueError(f"current_event.{f} {current_event.get(f)!r} != receipt {f} {receipt[f]!r} (modified {f})")
    # Check canonical projection SHA
    # canonical_projection_sha256 already validated as required above
    expected_sha = receipt.get("canonical_projection_sha256")
    actual_sha = _canonical_projection_sha256(current_event)
    if expected_sha != actual_sha:
        raise ValueError(f"current_event canonical projection sha {actual_sha[:12]}... != receipt {expected_sha[:12]}... (modified payload/dimension)")
    # Also check payload digest if receipt has it
    exp_payload_sha = receipt.get("resident_visible_payload_sha256")
    if exp_payload_sha:
        actual_payload_sha = _current_event_payload_digest(current_event)
        if exp_payload_sha != actual_payload_sha:
            raise ValueError(f"current_event payload digest mismatch (modified text)")
    # Enforce release_state receipt fields are present and non-empty (already required) and will be validated against live state below
    # Additional strict: operator_request_id must be non-empty hex-like
    if not isinstance(receipt.get("operator_request_id"), str) or not receipt.get("operator_request_id").strip():
        raise ValueError("binding receipt operator_request_id must be non-empty string")
    # Validate against release_state (BLK-04: unconditional — live state already proven readable)
    if True:
        rs_text = rs_bytes
        current_rs_sha = live_rs_sha
        nxt = rs.get("next_sequence")
        pending = rs.get("pending_reveal")
        if nxt is not None and current_event.get("sequence") != nxt:
            raise ValueError(f"current_event.sequence {current_event.get('sequence')} != release_state next_sequence {nxt} (future/stale)")
        # Enforce release_state SHA equality (reveal -> model -> ACK unchanged)
        receipt_rs_sha = receipt.get("release_state_sha256")
        if receipt_rs_sha and receipt_rs_sha != current_rs_sha:
            raise ValueError(f"release_state SHA mismatch: receipt {receipt_rs_sha[:12]}... != current {current_rs_sha[:12]}... (stale receipt or state mutated)")
        # Enforce receipt's saved next_sequence matches live release_state
        receipt_next = receipt.get("release_state_next_sequence")
        if receipt_next != nxt:
            raise ValueError(f"binding receipt release_state_next_sequence {receipt_next!r} != release_state next_sequence {nxt!r} (next_sequence mismatch)")
        # Enforce receipt's saved pending_reveal matches live release_state
        receipt_pending = receipt.get("release_state_pending_reveal")
        if receipt_pending != pending:
            raise ValueError(f"binding receipt release_state_pending_reveal {receipt_pending!r} != release_state pending_reveal {pending!r} (pending_reveal mismatch)")
        # CORRECTIVE-008: live fixture triple-binding — pending fixture == receipt fixture == canonical
        if pending is not None:
            live_pending_fixture = pending.get("fixture_sha256")
            if not live_pending_fixture:
                raise ValueError(f"live release_state pending_reveal.fixture_sha256 missing (must be {canon_fixture!r})")
            if live_pending_fixture != canon_fixture:
                raise ValueError(f"live release_state pending_reveal.fixture_sha256 {live_pending_fixture!r} != canonical {canon_fixture!r} (live fixture mismatch)")
            if live_pending_fixture != receipt.get("fixture_sha256"):
                raise ValueError(f"live pending fixture {live_pending_fixture!r} != receipt fixture {receipt.get('fixture_sha256')!r} (fixture triple mismatch)")
        else:
            # If pending is None but receipt expects fixture, should have been caught earlier
            pass
        # Enforce pending_reveal matches receipt and current event
        if pending is not None:
            if pending.get("sequence") != receipt.get("sequence"):
                raise ValueError(f"release_state pending_reveal.sequence {pending.get('sequence')!r} != receipt sequence {receipt.get('sequence')!r}")
            if pending.get("event_id") != receipt.get("event_id"):
                raise ValueError(f"release_state pending_reveal.event_id {pending.get('event_id')!r} != receipt event_id {receipt.get('event_id')!r}")
            if pending.get("sequence") != current_event.get("sequence"):
                raise ValueError(f"release_state pending_reveal.sequence {pending.get('sequence')!r} != current_event sequence {current_event.get('sequence')!r} (stale)")
            # Also enforce next_sequence matches pending sequence
            if nxt != pending.get("sequence"):
                raise ValueError(f"release_state next_sequence {nxt!r} != pending_reveal.sequence {pending.get('sequence')!r} (state corrupted)")
        pending = rs.get("pending_reveal")
        if isinstance(pending, dict):
            if pending.get("sequence") is not None and current_event.get("sequence") != pending.get("sequence"):
                raise ValueError(f"current_event sequence {current_event.get('sequence')} != pending_reveal sequence {pending.get('sequence')}")
            if pending.get("event_id") and current_event.get("event_id") != pending.get("event_id"):
                raise ValueError(f"current_event event_id {current_event.get('event_id')!r} != pending_reveal event_id {pending.get('event_id')!r}")
        # The live-state SHA is bound above (live_rs_sha / current_rs_sha); the receipt's
        # release_state_sha256 is compared against it there. No silent re-read here.

# --- Envelope / Request ---

def build_envelope(snapshot: RuntimeSnapshot, b_session_id: str, contract_sha256: str | None = None, current_event: dict[str, Any] | None = None, release_state_path: Path | str | None = None, binding_receipt_path: Path | str | None = None) -> dict[str, Any]:
    if contract_sha256 is None:
        contract_sha256 = get_contract_sha256()
    runtime_snapshot = dict(snapshot.cockpit) if isinstance(snapshot.cockpit, dict) else {"cockpit": str(snapshot.cockpit)}
    cap_catalog = list(snapshot.capability_catalog) if snapshot.capability_catalog else []
    cap_history = _serialize_capability_history(snapshot.capability_history, b_session_id)
    event_field = None
    if current_event is not None:
        if not isinstance(current_event, dict):
            raise ValueError("current_event must be dict or None")
        validate_current_event_binding(current_event, b_session_id, release_state_path=release_state_path, binding_receipt_path=binding_receipt_path)
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

def build_model_request(contract_text: str, envelope: dict[str, Any], wire_protocol_text: str | None = None) -> dict[str, Any]:
    if not isinstance(contract_text, str) or not contract_text.strip():
        raise ValueError("contract_text must be non-blank")
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be dict")
    if wire_protocol_text is None:
        wire_protocol_text = get_wire_protocol_text()
    wire_sha = get_wire_protocol_sha256()
    if hashlib.sha256(wire_protocol_text.encode("utf-8")).hexdigest() != wire_sha:
        if hashlib.sha256(wire_protocol_text.encode()).hexdigest() != wire_sha:
            raise ValueError("wire protocol hash mismatch")
    envelope_json = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "system": contract_text,
        "wire_protocol": wire_protocol_text,
        "wire_protocol_sha256": wire_sha,
        "messages": [{"role": "user", "content": envelope_json}],
        "metadata": {"phase": envelope.get("phase"), "round": envelope.get("round"), "contract_sha256": envelope.get("contract_sha256"), "wire_protocol_sha256": wire_sha},
    }

# --- Provider abstraction ---

@dataclass(frozen=True)
class ProviderResponse:
    provider: str | None
    model: str | None
    request_id: str | None
    usage: dict[str, Any] | None
    content: Any
    raw: Any | None = None

class ProviderClient(Protocol):
    def invoke(self, request: dict[str, Any]) -> ProviderResponse: ...

# --- ExternalBrokerClient (production, pure transport) ---

class ExternalBrokerClient:
    """
    Frozen production provider adapter — pure transport, no Resident semantics.
    Sends exact contract+envelope+wire_protocol to broker via HTTP POST, returns provider response.
    Never decides capability or action; purely transports the envelope.
    """
    PINNED_IDENTITY = {
        "module": "bridged_model_handler",
        "factory": "ExternalBrokerClient",
        "version": "1.0.0-frozen",
        "protocol_version": "c15-rcc-b-wire-v1",
    }
    def __init__(self, api_key: str | None = None, endpoint: str | None = None, timeout: int = 10, model: str | None = None, provider: str | None = None, allow_test_loopback: bool = False):
        self.api_key = api_key or os.getenv("AIOS_REAL_PROVIDER_API_KEY")
        self.endpoint = endpoint or os.getenv("AIOS_REAL_PROVIDER_ENDPOINT")
        self.timeout = int(timeout)
        self.model = model or os.getenv("AIOS_REAL_PROVIDER_MODEL", "real-model-v1")
        self.provider = provider or "real-provider"
        self.version = "1.0.0-frozen"
        self.invocations = 0
        self.last_request: dict[str, Any] | None = None
        # allow_test_loopback is test-only direct constructor, default False, never set by production entrypoint (CORRECTIVE-008)
        self.allow_test_loopback = bool(allow_test_loopback)
        if not self.api_key or not self.endpoint:
            raise ValueError("ExternalBrokerClient requires AIOS_REAL_PROVIDER_API_KEY and AIOS_REAL_PROVIDER_ENDPOINT")
        if self.provider == "fake-provider" or self.model.startswith("fake-"):
            raise ValueError("ExternalBrokerClient cannot use fake provider/model")
        # Endpoint must look like HTTP(S) or fake:// for test (but fake:// is not allowed in prod; only real HTTP)
        if not (self.endpoint.startswith("http://") or self.endpoint.startswith("https://") or self.endpoint.startswith("fake://")):
            raise ValueError(f"endpoint must be http(s)://, got {self.endpoint!r}")
        # Production HTTP plaintext forbidden: only https:// legal for production; http:// loopback only for explicit test-only direct constructor
        if self.endpoint.startswith("http://"):
            is_loopback = self.endpoint.startswith("http://127.0.0.1:") or self.endpoint.startswith("http://localhost:")
            if not is_loopback:
                raise ValueError(f"plaintext http:// not allowed for production endpoint {self.endpoint!r} (must be https:// or test-only http://127.0.0.1:<port> with allow_test_loopback=True)")
            # Loopback is test-only: require explicit allow_test_loopback=True, production entrypoint never sets it, env flags do not affect
            if not self.allow_test_loopback:
                raise ValueError(f"loopback http:// endpoint not allowed without allow_test_loopback=True (must be https://) got {self.endpoint!r} (production entrypoint is HTTPS-only)")

    def invoke(self, request: dict[str, Any]) -> ProviderResponse:
        self.invocations += 1
        self.last_request = request
        if not isinstance(request, dict):
            raise ValueError("request must be dict")
        allowed_keys = {"system", "messages", "metadata", "wire_protocol", "wire_protocol_sha256"}
        extra = set(request.keys()) - allowed_keys
        if extra:
            raise ValueError(f"request has extra keys {extra}")
        system = request.get("system")
        wire = request.get("wire_protocol")
        if not isinstance(system, str) or not system.strip():
            raise ValueError("system missing contract")
        if not isinstance(wire, str) or not wire.strip():
            raise ValueError("wire_protocol missing")
        if request.get("wire_protocol_sha256") != WIRE_PROTOCOL_SHA256:
            raise ValueError(f"wire_protocol_sha256 mismatch: expected {WIRE_PROTOCOL_SHA256}")
        msgs = request.get("messages")
        if not isinstance(msgs, list) or len(msgs) != 1:
            raise ValueError("messages must be single")
        content = msgs[0].get("content") if isinstance(msgs[0], dict) else None
        if not isinstance(content, str):
            raise ValueError("messages[0].content must be envelope JSON")
        try:
            envelope = json.loads(content)
        except Exception as e:
            raise ValueError(f"envelope not JSON: {e}")
        for needle in ("/repo/fixture", "/repo/evaluator", "/repo/governance", "/repo/.git"):
            if needle in content:
                raise ValueError(f"leaked {needle!r}")
        # --- Transport: HTTP POST to broker ---
        # For fake:// endpoints, we simulate transport failure (to test unreachable)
        if self.endpoint.startswith("fake://"):
            raise ConnectionError(f"fake endpoint unreachable: {self.endpoint}")
        # If endpoint is http://127.0.0.1:*/fake we treat as FakeBrokerServer via HTTP
        # Use http.client for minimal deps
        import urllib.request, urllib.error
        body = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Contract-SHA256": hashlib.sha256(system.encode("utf-8")).hexdigest(),
            "X-Wire-Protocol-SHA256": WIRE_PROTOCOL_SHA256,
        }
        # Add timeout handling
        req = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_body = resp.read()
                status = resp.status
                if status < 200 or status >= 300:
                    raise ConnectionError(f"broker HTTP {status}: {resp_body[:200]}")
                try:
                    broker_resp = json.loads(resp_body.decode("utf-8"))
                except Exception as e:
                    raise ValueError(f"broker response not JSON: {e}")
        except urllib.error.HTTPError as e:
            raise ConnectionError(f"broker HTTP error {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise ConnectionError(f"broker unreachable: {e.reason}") from e
        except Exception as e:
            if isinstance(e, (ConnectionError, ValueError)):
                raise
            raise ConnectionError(f"broker transport failed: {e}") from e
        # Broker response must contain provider/model/request_id/usage/content
        if not isinstance(broker_resp, dict):
            raise ValueError("broker response must be object")
        # Extract fields, allow UNKNOWN if missing
        provider = broker_resp.get("provider")
        model = broker_resp.get("model")
        req_id = broker_resp.get("request_id")
        usage = broker_resp.get("usage")
        content_b = broker_resp.get("content")
        if content_b is None:
            # Some brokers use "reply" field
            content_b = broker_resp.get("reply")
        if content_b is None:
            raise ValueError("broker response missing content/reply")
        # Content should be JSON string of reply or dict
        if isinstance(content_b, dict):
            content_str = json.dumps(content_b, sort_keys=True)
        elif isinstance(content_b, str):
            # Verify it's JSON
            try: json.loads(content_b)
            except: raise ValueError(f"broker content not JSON: {content_b[:200]}")
            content_str = content_b
        else:
            raise ValueError(f"broker content must be JSON string/dict, got {type(content_b)}")
        # Usage validation: keep raw, don't rewrite
        # Broker may return usage as dict with total/input/output
        return ProviderResponse(provider=provider, model=model, request_id=req_id, usage=usage if isinstance(usage, dict) else None, content=content_str, raw=broker_resp)

# --- FakeBrokerServer (test-only, must not be used via production entrypoint) ---

class FakeBrokerServer:
    """
    Test-only fake broker that simulates provider responses.
    It decides what reply to return for testing, but production client never decides.
    Production client just transports to this server via HTTP; server's decision is test data, not Resident semantics.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 0, mode: str = "normal"):
        self.host = host
        self.port = port
        self.mode = mode
        self.invocations = 0
        self._server = None
        self._thread = None

    def _handler(self):
        outer = self
        import http.server, json, hashlib
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                outer.invocations += 1
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                try:
                    req = json.loads(body.decode("utf-8"))
                except:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'{"error":"bad request not json"}')
                    return
                # Extract envelope
                try:
                    content = req["messages"][0]["content"]
                    envelope = json.loads(content)
                except:
                    envelope = {}
                hist = envelope.get("capability_history", []) if isinstance(envelope, dict) else []
                rnd = envelope.get("round", outer.invocations)
                rid = envelope.get("request_id", "a"*32)
                dig = envelope.get("request_digest", "b"*64)
                # Mode handling
                if outer.mode == "unreachable":
                    self.send_response(503)
                    self.end_headers()
                    self.wfile.write(b'{"error":"broker unreachable"}')
                    return
                if outer.mode == "timeout":
                    import time
                    time.sleep(5)
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'{"error":"timeout"}')
                    return
                if outer.mode == "malformed":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"provider":"fake-broker","model":"fake-model","request_id":"fake-req-0001","usage":{"total_tokens":42,"input_tokens":20,"output_tokens":22},"content":"not json at all"}')
                    return
                if outer.mode == "schema_invalid":
                    # Return reply with extra field that violates schema
                    reply = {"round": rnd, "request_id": rid, "request_digest": dig, "action": "silence", "capability": "search_world", "extra": "bad"}
                    broker_resp = {"provider": "fake-broker", "model": "fake-model", "request_id": "fake-req-0001", "usage": {"total_tokens":42,"input_tokens":20,"output_tokens":22}, "content": json.dumps(reply)}
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(broker_resp).encode())
                    return
                if outer.mode == "wrong_binding":
                    reply = {"round": 999, "request_id": rid, "request_digest": dig, "action": "silence"}
                    broker_resp = {"provider": "fake-broker", "model": "fake-model", "request_id": "fake-req-0001", "usage": {"total_tokens":42,"input_tokens":20,"output_tokens":22}, "content": json.dumps(reply)}
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(broker_resp).encode())
                    return
                if outer.mode == "missing_metadata":
                    reply = {"round": rnd, "request_id": rid, "request_digest": dig, "action": "silence"}
                    broker_resp = {"content": json.dumps(reply)}  # missing provider/model/request_id/usage
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(broker_resp).encode())
                    return
                if outer.mode == "inconsistent_usage":
                    reply = {"round": rnd, "request_id": rid, "request_digest": dig, "action": "silence"}
                    broker_resp = {"provider": "fake-broker", "model": "fake-model", "request_id": "fake-req-0001", "usage": {"total_tokens":10,"input_tokens":20,"output_tokens":22}, "content": json.dumps(reply)}
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(broker_resp).encode())
                    return
                # Normal: first round search_world Atlas, later silence (this is test broker deciding, not production client)
                if len(hist) == 0:
                    reply = {"round": rnd, "request_id": rid, "request_digest": dig, "action": "invoke_capability", "capability": "search_world", "arguments": {"query": "Atlas", "limit": 2}}
                else:
                    reply = {"round": rnd, "request_id": rid, "request_digest": dig, "action": "silence"}
                broker_resp = {"provider": "fake-broker", "model": "fake-model", "request_id": f"fake-req-{outer.invocations:04d}", "usage": {"total_tokens":42,"input_tokens":20,"output_tokens":22}, "content": json.dumps(reply)}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(broker_resp).encode())
            def log_message(self, format, *args):
                return
        return Handler

    def start(self) -> str:
        import http.server, threading
        Handler = self._handler()
        self._server = http.server.HTTPServer((self.host, self.port), Handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return f"http://{self.host}:{self.port}/v1/chat"

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=1)

# FakeProviderClient kept for backward compat but not allowed via prod entrypoint
class FakeProviderClient:
    """Legacy fake — test only, not via production."""
    def __init__(self, *a, **kw):
        raise RuntimeError("FakeProviderClient not allowed; use FakeBrokerServer + ExternalBrokerClient for tests")

def load_provider_client(adapter: str, **kwargs) -> Any:
    if ":" not in adapter:
        raise ValueError(f"adapter must be 'module:factory', got {adapter!r}")
    module_name, factory_name = adapter.split(":", 1)
    # Pin check: only exact allowed
    allowed = "bridged_model_handler:ExternalBrokerClient"
    if adapter != allowed:
        # Also check file hash
        raise ModelDispatchNotSubmitted(f"unapproved provider adapter {adapter!r}, expected {allowed!r} (ModelDispatchNotSubmitted/STOP)")
    # Verify file hash mandatory (blocker 4)
    try:
        actual_hash = get_adapter_sha256()
        if len(actual_hash) != 64 or not all(c in "0123456789abcdef" for c in actual_hash):
            raise ValueError("adapter hash invalid")
        expected_adapter_hash = os.getenv("AIOS_ADAPTER_SHA256")
        if not expected_adapter_hash:
            raise ModelDispatchNotSubmitted(f"AIOS_ADAPTER_SHA256 missing (required for production, got actual {actual_hash}) (STOP)")
        if expected_adapter_hash != actual_hash:
            raise ModelDispatchNotSubmitted(f"adapter hash mismatch: expected {expected_adapter_hash}, got {actual_hash} (STOP)")
    except ModelDispatchNotSubmitted:
        raise
    except Exception as e:
        raise ModelDispatchNotSubmitted(f"adapter hash verification failed: {e}") from e
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        raise ValueError(f"cannot import provider module {module_name!r}: {e}")
    try:
        factory = getattr(mod, factory_name)
    except AttributeError:
        raise ValueError(f"provider factory {factory_name!r} not found in {module_name!r}")
    # Prevent fake via prod
    if "fake" in factory_name.lower():
        raise ModelDispatchNotSubmitted(f"fake adapter not allowed via production entrypoint: {adapter}")
    try:
        client = factory(**kwargs) if kwargs else factory()
    except Exception as e:
        raise ModelDispatchNotSubmitted(f"provider factory {adapter!r} failed: {e}") from e
    if client.__class__.__name__.lower().find("fake") != -1:
        raise ModelDispatchNotSubmitted(f"fake client not allowed in prod: {client.__class__.__name__}")
    return client

# --- Reply translators ---


def _reply_to_directive_synthetic(reply: dict[str, Any], snapshot: RuntimeSnapshot) -> ModelDirective:
    action = reply.get("action")
    req_id = reply.get("request_id", "unknown")
    usage = ModelUsage(total_tokens=10, input_tokens=5, output_tokens=5, provider="sandbox-bridge", model="synthetic-responder-v1", request_id=req_id)
    provenance = ModelCallProvenance(provider="sandbox-bridge", model="synthetic-responder-v1", request_id=req_id)
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
    action = reply.get("action")
    # Validate capability against catalog (blocker 5)
    if action == "invoke_capability":
        cap_name = reply.get("capability")
        if not isinstance(cap_name, str) or not cap_name.strip():
            raise ValueError("capability must be non-empty string")
        # Build catalog names set
        catalog = snapshot.capability_catalog or []
        catalog_names = set()
        for c in catalog:
            if isinstance(c, dict):
                n = c.get("name") or c.get("capability") or c.get("id")
                if isinstance(n, str):
                    catalog_names.add(n)
            elif isinstance(c, str):
                catalog_names.add(c)
            else:
                try:
                    n = getattr(c, "name", None)
                    if isinstance(n, str):
                        catalog_names.add(n)
                except: pass
        # If catalog is non-empty, enforce
        if cap_name not in catalog_names:
            raise ModelDispatchNotSubmitted(f"capability {cap_name!r} not in snapshot.capability_catalog {sorted(catalog_names)[:5]}... (fail closed)")
    prov = provider_resp.provider if isinstance(provider_resp.provider, str) and provider_resp.provider.strip() else "UNKNOWN"
    mod = provider_resp.model if isinstance(provider_resp.model, str) and provider_resp.model.strip() else "UNKNOWN"
    req = provider_resp.request_id if isinstance(provider_resp.request_id, str) and provider_resp.request_id.strip() else "UNKNOWN"
    usage: ModelUsage | None = None
    raw_usage = provider_resp.usage
    if raw_usage is not None and isinstance(raw_usage, dict):
        def _token_or_missing(key: str) -> tuple[int | None, bool]:
            if key not in raw_usage or raw_usage.get(key) is None:
                return None, True
            value = raw_usage.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                return None, False
            return int(value), True

        tot_i, tot_valid = _token_or_missing("total_tokens")
        inp_i, inp_valid = _token_or_missing("input_tokens")
        out_i, out_valid = _token_or_missing("output_tokens")
        if not (tot_valid and inp_valid and out_valid):
            usage = None
        elif tot_i is None:
            # ModelUsage requires provider-reported total_tokens. Never synthesize a total
            # from partial input/output telemetry; preserve provenance but expose usage=None.
            usage = None
        elif inp_i is not None and out_i is not None and tot_i < inp_i + out_i:
            usage = None
        else:
            try:
                usage = ModelUsage(
                    total_tokens=tot_i,
                    input_tokens=inp_i,
                    output_tokens=out_i,
                    provider=prov if prov!="UNKNOWN" else None,
                    model=mod if mod!="UNKNOWN" else None,
                    request_id=req if req!="UNKNOWN" else None,
                )
            except (TypeError, ValueError):
                usage = None
    else:
        usage = None
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

# --- Synthetic handler (for mailbox E2E, not production) ---

class SyntheticProbeHandler:
    def __init__(self, bridge: MailboxBridge, b_session_id: str, contract_sha256: str | None = None):
        self.bridge = bridge
        self.b_session_id = b_session_id
        self.contract_sha256 = contract_sha256 or get_contract_sha256()
        self.contract_text = get_contract_text()
        self.wire_protocol_text = get_wire_protocol_text()
        self.wire_protocol_sha256 = get_wire_protocol_sha256()
        self.current_event: dict[str, Any] | None = None
        self._round = 0
        self.invocations = 0
    def set_current_event(self, event: dict[str, Any] | None) -> None:
        self.current_event = event
    def __call__(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        self.invocations += 1
        # Build envelope with no binding check (synthetic)
        runtime_snapshot = dict(snapshot.cockpit) if isinstance(snapshot.cockpit, dict) else {"cockpit": str(snapshot.cockpit)}
        cap_catalog = list(snapshot.capability_catalog) if snapshot.capability_catalog else []
        cap_history = _serialize_capability_history(snapshot.capability_history, self.b_session_id)
        envelope = {"phase": "B", "allowed_sequences": [14,22], "event": self.current_event, "runtime_snapshot": runtime_snapshot, "capability_catalog": cap_catalog, "capability_history": cap_history, "wake_reason": snapshot.wake_reason, "is_periodic_review": False, "is_summary_request": False, "contract_sha256": self.contract_sha256}
        # Send via bridge (bridge assigns round/request_id/request_digest)
        from mailbox_bridge import validate_envelope
        validate_envelope(envelope, self.b_session_id)
        # Bridge will assign binding; we capture it after send
        self.bridge.send(envelope)
        # Retrieve assigned binding from bridge's outstanding
        outstanding = self.bridge._outstanding  # type: ignore
        if outstanding is None or "round" not in outstanding:
            # Fallback: use internal round
            self._round += 1
            request_id = outstanding.get("request_id", "unknown") if outstanding else "unknown"
            request_digest = outstanding.get("request_digest", "unknown") if outstanding else "unknown"
            assigned_round = self._round
        else:
            assigned_round = outstanding["round"]
            request_id = outstanding["request_id"]
            request_digest = outstanding["request_digest"]
            self._round = assigned_round
        reply = self.bridge.wait_for_reply(timeout=10)
        from mailbox_bridge import validate_reply
        validate_reply(reply)
        # Verify binding
        if reply.get("round") != assigned_round or reply.get("request_id") != request_id or reply.get("request_digest") != request_digest:
            raise ModelDispatchNotSubmitted("synthetic reply binding mismatch")
        return _reply_to_directive_synthetic(reply, snapshot)

# --- Production handler with poison & evidence ---

class ProductionResidentHandler:
    """
    Frozen production handler: transport via ExternalBrokerClient, binding receipt, poison, catalog check.
    """
    def __init__(self, b_session_id: str, provider_client: Any, contract_sha256: str | None = None, contract_text: str | None = None, release_state_path: Path | str | None = None, wire_protocol_sha256: str | None = None, binding_receipt_path: Path | str | None = None, evidence_dir: Path | str | None = None):
        self.b_session_id = b_session_id
        self.provider_client = provider_client
        self.contract_sha256 = contract_sha256 or get_contract_sha256()
        self.contract_text = contract_text if contract_text is not None else get_contract_text()
        self.release_state_path = Path(release_state_path) if release_state_path else (Path(os.getenv("AIOS_RELEASE_STATE_PATH")) if os.getenv("AIOS_RELEASE_STATE_PATH") else None)
        self.binding_receipt_path = Path(binding_receipt_path) if binding_receipt_path else (Path(os.getenv("AIOS_CURRENT_EVENT_BINDING_PATH")) if os.getenv("AIOS_CURRENT_EVENT_BINDING_PATH") else None)
        # Fallback binding path
        if self.binding_receipt_path is None and self.release_state_path:
            cand = self.release_state_path.parent.parent / "binding" / "current-event-binding.json"
            if cand.exists():
                self.binding_receipt_path = cand
            else:
                alt = self.release_state_path.parent / "binding" / "current-event-binding.json"
                if alt.exists():
                    self.binding_receipt_path = alt
                else:
                    self.binding_receipt_path = cand
        self.wire_protocol_sha256 = wire_protocol_sha256 or get_wire_protocol_sha256()
        self.wire_protocol_text = get_wire_protocol_text()
        self.evidence_dir = Path(evidence_dir) if evidence_dir else (Path(os.getenv("AIOS_EVIDENCE_DIR")) if os.getenv("AIOS_EVIDENCE_DIR") else (self.release_state_path.parent.parent / "evidence" if self.release_state_path else Path("/tmp/evidence")))
        self.invocations = 0
        self.last_snapshot: RuntimeSnapshot | None = None
        self.last_envelope: dict[str, Any] | None = None
        self.last_provider_response: ProviderResponse | None = None
        self.last_reply: dict[str, Any] | None = None
        self.current_event: dict[str, Any] | None = None
        self._round = 0
        self._consumed: set[str] = set()
        self._outstanding: dict[str, Any] | None = None
        self._failure_evidence: list[dict[str, Any]] = []
        self._poisoned = False
        self._poison_reason: str | None = None

    def set_current_event(self, event: dict[str, Any] | None) -> None:
        if self._poisoned:
            raise ModelDispatchNotSubmitted(f"handler poisoned: {self._poison_reason} (must reconstruct)")
        self.current_event = event

    def _load_current_event_from_file(self) -> dict[str, Any] | None:
        path = os.getenv("AIOS_CURRENT_EVENT_PATH")
        if not path:
            return self.current_event
        p = Path(path)
        if not p.exists():
            if self.current_event is not None:
                return None
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            raise ModelDispatchNotSubmitted(f"current-event file malformed JSON: {e}")
        if not isinstance(data, dict):
            raise ModelDispatchNotSubmitted("current-event file must be JSON object")
        return data

    def _assign_binding(self, envelope: dict[str, Any]) -> dict[str, Any]:
        if self._poisoned:
            raise ModelDispatchNotSubmitted(f"handler poisoned: {self._poison_reason}")
        if self._outstanding is not None:
            raise ModelDispatchNotSubmitted(f"cannot send new request while round {self._outstanding['round']} outstanding (Scheme A requires reconstruction)")
        self._round += 1
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
        self._consumed.add(exp["request_id"])
        self._outstanding = None

    def _poison_and_evidence(self, failure_class: str, reason: str, request_id: str | None = None, request_digest: str | None = None, provider_request_id: str | None = None) -> None:
        # CORRECTIVE-009 / BLK-06 ordering: poison, snapshot outstanding, then CLEAR it,
        # all before any evidence is built or written. A durable-write failure can therefore
        # never leave a stale _outstanding behind, and never blocks protocol-state cleanup.
        self._poisoned = True
        self._poison_reason = f"{failure_class}: {reason}"
        outstanding = self._outstanding
        self._outstanding = None
        # Build evidence even without outstanding (pre-binding failures must still be durable)
        evidence: dict[str, Any] = {}
        if outstanding is not None:
            evidence = dict(outstanding)
        else:
            # No outstanding yet (e.g., binding failure before request_id assigned) -> use nullable fields
            evidence = {"round": self._round, "request_id": request_id, "request_digest": request_digest}
        evidence["failure_class"] = failure_class
        evidence["failure_reason"] = reason
        evidence["envelope"] = self.last_envelope
        evidence["provider_request_id"] = provider_request_id
        evidence["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        evidence["failure_phase"] = "model_request"
        evidence["session"] = self.b_session_id
        # Cursor not advanced proof: capture release_state next_sequence / pending_reveal
        if self.release_state_path and self.release_state_path.exists():
            try:
                rs = json.loads(self.release_state_path.read_text())
                evidence["release_next_sequence"] = rs.get("next_sequence")
                evidence["release_pending_reveal"] = rs.get("pending_reveal")
                evidence["release_state_sha256"] = hashlib.sha256(self.release_state_path.read_bytes()).hexdigest()
                evidence["cursor_not_advanced"] = True
            except Exception as e:
                evidence["cursor_not_advanced"] = f"unknown: {e}"
                evidence["release_next_sequence"] = None
                evidence["release_pending_reveal"] = None
        else:
            evidence["release_next_sequence"] = None
            evidence["release_pending_reveal"] = None
            evidence["cursor_not_advanced"] = "no_release_state"
        evidence["b_session_id"] = self.b_session_id
        evidence["current_event"] = self.current_event
        evidence["binding_receipt_path"] = str(self.binding_receipt_path) if self.binding_receipt_path else None
        self._failure_evidence.append(evidence)
        # Durable receipt: must fail-closed on write error (no except: pass)
        try:
            self.evidence_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ModelDispatchNotSubmitted(f"evidence dir creation failed: {e}") from e
        try:
            # CORRECTIVE-009 / BLK-06: collision-safe, never-overwrite receipt name.
            # time_ns() + an 8-hex nonce makes same-session/same-round/same-second retries
            # impossible to collide; O_CREAT|O_EXCL guarantees an existing 0400 receipt can
            # never be silently overwritten or cause a PermissionError.
            nonce = secrets.token_hex(4)
            fname = f"failure-{self.b_session_id}-round-{self._round}-{time.time_ns()}-{nonce}.json"
            fpath = self.evidence_dir / fname
            evidence["receipt_path"] = str(fpath)
            payload_text = json.dumps(evidence, sort_keys=True, indent=2, ensure_ascii=False)
            fd = os.open(str(fpath), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(payload_text)
            except Exception:
                try:
                    os.close(fd)
                except OSError:
                    pass
                raise
            # Latest pointer is derived from the unique receipt, never overwritten in place.
            latest = self.evidence_dir / f"failure-latest-{self._round}.json"
            try:
                if latest.exists() or latest.is_symlink():
                    latest.unlink()
            except FileNotFoundError:
                pass
            latest.write_text(payload_text, encoding="utf-8")
            # Ensure durable: chmod 0400 — fail-closed (CORRECTIVE-007)
            try:
                fpath.chmod(0o400)
            except Exception as e:
                raise ModelDispatchNotSubmitted(f"evidence chmod failed: {e}") from e
            try:
                mode = fpath.stat().st_mode & 0o777
                if mode != 0o400:
                    raise ModelDispatchNotSubmitted(f"evidence permissions {oct(mode)} != 0o400")
            except ModelDispatchNotSubmitted:
                raise
            except Exception as e:
                raise ModelDispatchNotSubmitted(f"evidence permission check failed: {e}") from e
            try:
                latest.chmod(0o400)
            except Exception as e:
                raise ModelDispatchNotSubmitted(f"evidence latest chmod failed: {e}") from e
            try:
                mode2 = latest.stat().st_mode & 0o777
                if mode2 != 0o400:
                    raise ModelDispatchNotSubmitted(f"evidence latest permissions {oct(mode2)} != 0o400")
            except ModelDispatchNotSubmitted:
                raise
            except Exception as e:
                raise ModelDispatchNotSubmitted(f"evidence latest permission check failed: {e}") from e
        except Exception as e:
            # Surfacing write failure explicitly, not silent, and as its OWN failure class so
            # it can never be confused with (or mask) the original failure semantics.
            # _outstanding was already cleared above, so protocol state stays consistent.
            evidence["evidence_persistence_failure"] = f"{type(e).__name__}: {e}"
            self._failure_evidence.append(dict(evidence))
            raise ModelDispatchNotSubmitted(
                f"evidence_persistence_failure: durable failure receipt write failed: {e}"
            ) from e

    def __call__(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        if self._poisoned:
            raise ModelDispatchNotSubmitted(f"handler poisoned: {self._poison_reason} (new instance required)")
        self.invocations += 1
        self.last_snapshot = snapshot
        # Refresh current_event per call
        try:
            refreshed = self._load_current_event_from_file()
        except ModelDispatchNotSubmitted:
            self._poison_and_evidence("binding_failure", "current-event refresh failed", provider_request_id=None)
            raise
        except Exception as e:
            self._poison_and_evidence("binding_failure", f"current-event refresh failed: {e}")
            raise ModelDispatchNotSubmitted(f"current-event refresh failed: {e}") from e
        self.current_event = refreshed
        if self.current_event is None:
            self._poison_and_evidence(
                "binding_failure",
                "no current-event binding: Phase-B model dispatch requires a current legal B event "
                "(no event -> no dispatch, no wake_reason/round_index exemption)",
            )
            raise ModelDispatchNotSubmitted(
                "no current-event binding: Phase-B model dispatch requires a current legal B event "
                "(no event -> no dispatch)"
            )
        try:
            validate_current_event_binding(self.current_event, self.b_session_id, release_state_path=self.release_state_path, binding_receipt_path=self.binding_receipt_path)
        except Exception as e:
            self._poison_and_evidence("binding_failure", str(e))
            raise ModelDispatchNotSubmitted(f"current-event binding failed: {e}") from e
        # Build envelope
        try:
            envelope = build_envelope(snapshot, self.b_session_id, self.contract_sha256, current_event=self.current_event, release_state_path=self.release_state_path, binding_receipt_path=self.binding_receipt_path)
        except Exception as e:
            self._poison_and_evidence("binding_failure", f"envelope build failed: {e}")
            raise ModelDispatchNotSubmitted(f"envelope build failed: {e}") from e
        try:
            envelope = self._assign_binding(envelope)
        except ModelDispatchNotSubmitted:
            # _assign_binding already failed due to outstanding, poison?
            if self._outstanding is not None:
                self._poison_and_evidence("protocol_mismatch", "assign binding failed outstanding")
            raise
        except Exception as e:
            self._poison_and_evidence("protocol_mismatch", f"binding assign failed: {e}")
            raise ModelDispatchNotSubmitted(f"binding assign failed: {e}") from e
        self.last_envelope = envelope
        try:
            request = build_model_request(self.contract_text, envelope, wire_protocol_text=self.wire_protocol_text)
        except Exception as e:
            self._poison_and_evidence("protocol_mismatch", f"build_model_request failed: {e}", request_id=envelope.get("request_id"), request_digest=envelope.get("request_digest"))
            raise ModelDispatchNotSubmitted(f"build_model_request failed: {e}") from e
        try:
            provider_resp = self.provider_client.invoke(request)
        except Exception as e:
            # Distinguish transport failure
            failure_class = "provider_transport_failure"
            if "timeout" in str(e).lower():
                failure_class = "provider_timeout"
            self._poison_and_evidence(failure_class, f"provider invoke failed: {e}", request_id=envelope.get("request_id"), request_digest=envelope.get("request_digest"), provider_request_id=getattr(self.provider_client, "last_request", None) and getattr(self.provider_client, "last_request_id", None))
            raise ModelDispatchNotSubmitted(f"provider invoke failed: {e}") from e
        self.last_provider_response = provider_resp
        content = provider_resp.content
        if isinstance(content, str):
            try: reply = json.loads(content)
            except Exception as e:
                self._poison_and_evidence("non_json", f"provider content not JSON: {e}", request_id=envelope.get("request_id"), request_digest=envelope.get("request_digest"), provider_request_id=provider_resp.request_id)
                raise ModelDispatchNotSubmitted(f"provider content not JSON: {e}") from e
        elif isinstance(content, dict):
            reply = dict(content)
        else:
            self._poison_and_evidence("non_json", f"provider content must be JSON string/dict", request_id=envelope.get("request_id"), request_digest=envelope.get("request_digest"), provider_request_id=provider_resp.request_id)
            raise ModelDispatchNotSubmitted(f"provider content must be JSON string/dict, got {type(content)}")
        from mailbox_bridge import validate_reply
        try:
            validate_reply(reply)
        except Exception as e:
            self._poison_and_evidence("schema_failure", f"reply structural invalid: {e}", request_id=envelope.get("request_id"), request_digest=envelope.get("request_digest"), provider_request_id=provider_resp.request_id)
            raise ModelDispatchNotSubmitted(f"reply structural invalid: {e}") from e
        try:
            self._verify_reply_binding(reply)
        except Exception as e:
            self._poison_and_evidence("binding_failure", f"reply binding failed: {e}", request_id=envelope.get("request_id"), request_digest=envelope.get("request_digest"), provider_request_id=provider_resp.request_id)
            raise ModelDispatchNotSubmitted(f"reply binding failed: {e}") from e
        self.last_reply = reply
        try:
            directive = _reply_to_directive_production(reply, snapshot, provider_resp)
        except ModelDispatchNotSubmitted:
            self._poison_and_evidence("schema_failure", "reply translation failed", request_id=envelope.get("request_id"), request_digest=envelope.get("request_digest"), provider_request_id=provider_resp.request_id)
            raise
        except Exception as e:
            self._poison_and_evidence("schema_failure", f"reply translation failed: {e}", request_id=envelope.get("request_id"), request_digest=envelope.get("request_digest"), provider_request_id=provider_resp.request_id)
            raise ModelDispatchNotSubmitted(f"reply translation failed: {e}") from e
        return directive

# Keep alias for backward compat but poison will handle
ProductionResidentHandler = ProductionResidentHandler

# Headless globals
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
    evt_path = os.getenv("AIOS_CURRENT_EVENT_PATH")
    if evt_path:
        try:
            if Path(evt_path).exists():
                evt = json.loads(Path(evt_path).read_text())
                _global_synthetic.set_current_event(evt)
            else:
                _global_synthetic.set_current_event(None)
        except: pass
    return _global_synthetic(snapshot)

def headless_production_handler(snapshot: RuntimeSnapshot) -> ModelDirective:
    global _global_production
    if _global_production is not None:
        if _global_production._poisoned:
            raise ModelDispatchNotSubmitted(f"handler poisoned: {_global_production._poison_reason} (reconstruction required)")
        evt_path = os.getenv("AIOS_CURRENT_EVENT_PATH")
        if evt_path:
            p = Path(evt_path)
            if p.exists():
                try:
                    evt = json.loads(p.read_text())
                    _global_production.set_current_event(evt)
                except Exception as e:
                    raise ModelDispatchNotSubmitted(f"AIOS_CURRENT_EVENT_PATH malformed: {e}")
            else:
                _global_production.set_current_event(None)
        # Also refresh binding receipt path if changed
        bind_path = os.getenv("AIOS_CURRENT_EVENT_BINDING_PATH")
        if bind_path:
            _global_production.binding_receipt_path = Path(bind_path)
        return _global_production(snapshot)
    b_session = os.getenv("AIOS_B_SESSION_ID")
    if not b_session:
        raise ModelDispatchNotSubmitted("AIOS_B_SESSION_ID must be set for production handler")
    # Mandatory B boundary envs (blocker 5)
    required_envs = ["AIOS_RELEASE_STATE_PATH", "AIOS_CURRENT_EVENT_PATH", "AIOS_CURRENT_EVENT_BINDING_PATH", "AIOS_EVIDENCE_DIR", "AIOS_ADAPTER_SHA256", "AIOS_CONTRACT_SHA256", "AIOS_WIRE_PROTOCOL_SHA256"]
    missing = [k for k in required_envs if not os.getenv(k)]
    if missing:
        raise ModelDispatchNotSubmitted(f"missing mandatory B boundary envs {missing} (ModelDispatchNotSubmitted/STOP)")
    # Verify files exist and readable
    for fkey in ["AIOS_RELEASE_STATE_PATH", "AIOS_CURRENT_EVENT_PATH", "AIOS_CURRENT_EVENT_BINDING_PATH"]:
        fpath = os.getenv(fkey)
        if fpath and not Path(fpath).exists():
            raise ModelDispatchNotSubmitted(f"{fkey} file missing at {fpath} (fail closed)")
        if fpath:
            try:
                Path(fpath).read_text(encoding="utf-8")  # readable check
            except Exception as e:
                raise ModelDispatchNotSubmitted(f"{fkey} unreadable at {fpath}: {e}")
    # Verify receipt session matches B session
    try:
        bind_path = Path(os.getenv("AIOS_CURRENT_EVENT_BINDING_PATH"))
        if bind_path.exists():
            receipt = json.loads(bind_path.read_text(encoding="utf-8"))
            if receipt.get("b_session_id") != b_session:
                raise ModelDispatchNotSubmitted(f"binding receipt session {receipt.get('b_session_id')!r} != AIOS_B_SESSION_ID {b_session!r} (wrong session)")
    except ModelDispatchNotSubmitted:
        raise
    except Exception as e:
        raise ModelDispatchNotSubmitted(f"binding receipt session check failed: {e}") from e
    api_key = os.getenv("AIOS_REAL_PROVIDER_API_KEY")
    endpoint = os.getenv("AIOS_REAL_PROVIDER_ENDPOINT")
    if not api_key or not endpoint:
        raise ModelDispatchNotSubmitted("real provider not configured: AIOS_REAL_PROVIDER_API_KEY and AIOS_REAL_PROVIDER_ENDPOINT must be set (no fake fallback)")
    adapter = os.getenv("AIOS_PROVIDER_ADAPTER", "bridged_model_handler:ExternalBrokerClient")
    # Pin check (exact)
    allowed = "bridged_model_handler:ExternalBrokerClient"
    if adapter != allowed:
        raise ModelDispatchNotSubmitted(f"unapproved provider adapter {adapter!r}, expected {allowed!r} (ModelDispatchNotSubmitted/STOP)")
    # Adapter SHA mandatory (blocker 4): must be set and equal actual file SHA
    expected_hash = os.getenv("AIOS_ADAPTER_SHA256")
    actual_hash = get_adapter_sha256()
    if not expected_hash:
        raise ModelDispatchNotSubmitted(f"AIOS_ADAPTER_SHA256 missing (required, got actual {actual_hash}) (ModelDispatchNotSubmitted/STOP)")
    if expected_hash != actual_hash:
        raise ModelDispatchNotSubmitted(f"adapter hash mismatch: expected {expected_hash}, got {actual_hash} (ModelDispatchNotSubmitted/STOP)")
    # Also check factory via load_provider_client (will do same pin)
    try:
        client = load_provider_client(adapter)
    except ModelDispatchNotSubmitted:
        raise
    except Exception as e:
        raise ModelDispatchNotSubmitted(f"real provider adapter not resolvable: {e}") from e
    if client.__class__.__name__ == "FakeProviderClient" or "fake" in client.__class__.__name__.lower():
        raise ModelDispatchNotSubmitted("FakeProviderClient not allowed in production entrypoint")
    # Contract and wire hash exact checks (CORRECTIVE-007): env must equal frozen expected and actual file
    frozen_contract = "28d3262f56b7ef93a32a842f1d4d66f99748f2b07adcece43e815eb9d5cd18ef"
    frozen_wire = "a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a"
    contract_sha = os.getenv("AIOS_CONTRACT_SHA256")
    if not contract_sha:
        raise ModelDispatchNotSubmitted("AIOS_CONTRACT_SHA256 missing (required)")
    if contract_sha != frozen_contract:
        raise ModelDispatchNotSubmitted(f"contract SHA env mismatch: expected {frozen_contract}, got {contract_sha} (STOP)")
    contract_text = get_contract_text()
    if hashlib.sha256(contract_text.encode("utf-8")).hexdigest() != frozen_contract:
        raise ModelDispatchNotSubmitted(f"contract file SHA mismatch: expected {frozen_contract}")
    if hashlib.sha256(contract_text.encode("utf-8")).hexdigest() != contract_sha:
        raise ModelDispatchNotSubmitted("contract SHA mismatch")
    try:
        wire_sha_env = os.getenv("AIOS_WIRE_PROTOCOL_SHA256")
        if not wire_sha_env:
            raise ModelDispatchNotSubmitted("AIOS_WIRE_PROTOCOL_SHA256 missing (required)")
        if wire_sha_env != frozen_wire:
            raise ModelDispatchNotSubmitted(f"wire protocol SHA env mismatch: expected {frozen_wire}, got {wire_sha_env} (STOP)")
        wire_sha = get_wire_protocol_sha256()
        if wire_sha != frozen_wire:
            raise ModelDispatchNotSubmitted(f"wire protocol hash mismatch: expected {frozen_wire}, got {wire_sha}")
        wire_text = get_wire_protocol_text()
        if hashlib.sha256(wire_text.encode("utf-8")).hexdigest() != frozen_wire:
            raise ModelDispatchNotSubmitted("wire protocol file hash mismatch")
        if wire_sha_env != wire_sha:
            raise ModelDispatchNotSubmitted(f"wire protocol env {wire_sha_env} != actual {wire_sha} (STOP)")
    except ModelDispatchNotSubmitted:
        raise
    except Exception as e:
        raise ModelDispatchNotSubmitted(f"wire protocol not available: {e}") from e
    release_state_path = os.getenv("AIOS_RELEASE_STATE_PATH")
    binding_receipt_path = os.getenv("AIOS_CURRENT_EVENT_BINDING_PATH")
    evidence_dir = os.getenv("AIOS_EVIDENCE_DIR")
    _global_production = ProductionResidentHandler(b_session_id=b_session, provider_client=client, contract_sha256=contract_sha, contract_text=contract_text, release_state_path=release_state_path, wire_protocol_sha256=wire_sha, binding_receipt_path=binding_receipt_path, evidence_dir=evidence_dir)
    evt_path = os.getenv("AIOS_CURRENT_EVENT_PATH")
    if evt_path and Path(evt_path).exists():
        try:
            evt = json.loads(Path(evt_path).read_text())
            _global_production.set_current_event(evt)
        except Exception as e:
            raise ModelDispatchNotSubmitted(f"AIOS_CURRENT_EVENT_PATH malformed: {e}") from e
    return _global_production(snapshot)

def _reset_global():
    global _global_synthetic, _global_production
    _global_synthetic = None
    _global_production = None
