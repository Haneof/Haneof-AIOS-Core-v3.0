#!/usr/bin/env python3
"""
C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-004 — Transport-only mailbox bridge
(envelope-hardened + request/reply binding + schema-aware leakage guard).

Responsibility (transport only, ZERO semantic judgment):

  1. On send(), generate cryptographically-random request_id (nonce) and
     canonical request_digest, inject them plus round, validate strict envelope,
     and write to inbox. Fail closed on any violation (no file write).
  2. Track outstanding request binding (round + request_id + request_digest) and
     a consumed set to prevent replay / stale / future / preplay acceptance.
  3. wait_for_reply() verifies that the reply's round, request_id and
     request_digest exactly match the current outstanding request. Any mismatch
     (stale prior-round, preplayed future-round, replayed consumed, wrong id,
     wrong digest) fails closed with MailboxReplyError.
  4. Provide strict negative self-tests covering all 6 binding cases and strict reply schema.
  5. Leakage guard is SCHEMA-AWARE: forbidden material is identified by
     section/path allowlists, not by arbitrary substring in legal durable World
     values. E.g. obs_c14_fixture_* object ids are legal World ids and are
     explicitly allowed, whereas raw paths like /repo/fixture, /repo/evaluator,
     /repo/governance etc. are forbidden even if they appear inside envelope.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

EVENT_FIELD_ALLOWLIST = frozenset({
    "event_id",
    "sequence",
    "occurred_at",
    "dimension",
    "source_kind",
    "source_class",
    "modality",
    "resident_visible_payload",
})

# Top-level envelope allowlist. Includes bridge-assigned binding fields.
TOP_LEVEL_ALLOWLIST = frozenset({
    "round",
    "request_id",
    "request_digest",
    "event",
    "runtime_snapshot",
    "capability_catalog",
    "capability_history",
    "wake_reason",
    "is_periodic_review",
    "is_summary_request",
    "contract_sha256",
    "phase",
    "allowed_sequences",
})

# FORBIDDEN paths/substrings that indicate sealed material leakage.
# CRITICAL: Do NOT use bare words like "fixture" — the accepted durable World
# legitimately contains object ids such as obs_c14_fixture_xxx which are NOT leaks.
# Only block path-like or sealed-fixture markers that cannot appear in legal World values.
FORBIDDEN_SUBSTRINGS = (
    "sealed_fixture",
    "RESIDENT_A_RERUN",
    "C15_RCC_RES_A",
    "__pycache__",
    "/repo/.git",
    "AIOS_SINGLE_WINDOW_TASK_BOARD",
    "AIOS_v3.0_CURRENT_CHECKPOINT",
    "PROJECT_MASTER_MAP",
    "/repo/fixture",
    "/repo/evaluator",
    "/repo/governance",
    "/repo/prompts",
    "/fixture/",
    "/evaluator/",
    "/governance/",
    "/release/",
    "/resident/C15-RCC-RES-A-RERUN",
    "/c14-resident",
)

# Reply schema per action — strict top-level allowlist
_REPLY_COMMON_FIELDS = frozenset({"round", "request_id", "request_digest", "action"})
_REPLY_ALLOWLISTS = {
    "invoke_capability": _REPLY_COMMON_FIELDS | {"capability", "arguments"},
    "end_turn": _REPLY_COMMON_FIELDS | {"response"},
    "silence": _REPLY_COMMON_FIELDS,
    "summary_response": _REPLY_COMMON_FIELDS | {"response", "summary"},
    # round_repair_request is deprecated per CORRECTIVE-003 Scheme A (fail closed, no repair). Kept for error message only.
    "round_repair_request": _REPLY_COMMON_FIELDS,
}
_VALID_ACTIONS = frozenset(_REPLY_ALLOWLISTS.keys())

class MailboxEnvelopeError(ValueError):
    """Outbound envelope failed strict validation (fail closed)."""

class MailboxReplyError(ValueError):
    """Inbound reply failed structural or binding validation."""

def _walk(obj: Any, path: str = "") -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    if isinstance(obj, dict):
        out.append((path or "<root>", obj))
        for k, v in obj.items():
            out.extend(_walk(v, f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(_walk(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        out.append((path, obj))
    return out

def _scan_forbidden(envelope: dict) -> None:
    for path, value in _walk(envelope):
        if not isinstance(value, str):
            continue
        low = value.lower()
        for needle in FORBIDDEN_SUBSTRINGS:
            if needle.lower() in low:
                raise MailboxEnvelopeError(
                    f"envelope contains forbidden substring {needle!r} at {path!r}; refuse to send"
                )

def _is_hex(s: Any, length: int) -> bool:
    if not isinstance(s, str) or len(s) != length:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False

def validate_envelope(envelope: dict[str, Any], b_session_id: str) -> None:
    if not isinstance(envelope, dict):
        raise MailboxEnvelopeError("envelope must be a JSON object")
    extra_top = set(envelope.keys()) - TOP_LEVEL_ALLOWLIST
    if extra_top:
        raise MailboxEnvelopeError(f"envelope has disallowed top-level keys: {sorted(extra_top)}")
    # round, request_id, request_digest assigned by bridge; if present validate format
    r = envelope.get("round")
    if r is not None and (not isinstance(r, int) or r < 1):
        raise MailboxEnvelopeError("envelope.round must be a positive integer when present")
    rid = envelope.get("request_id")
    if rid is not None:
        if not isinstance(rid, str) or not _is_hex(rid, 32):
            raise MailboxEnvelopeError("envelope.request_id must be 32 hex chars")
    rdg = envelope.get("request_digest")
    if rdg is not None:
        if not isinstance(rdg, str) or not _is_hex(rdg, 64):
            raise MailboxEnvelopeError("envelope.request_digest must be 64 hex chars (sha256)")
    if "event" in envelope:
        ev = envelope["event"]
        if ev is not None:
            if not isinstance(ev, dict):
                raise MailboxEnvelopeError("envelope.event must be an object or null")
            keys = set(ev.keys())
            if keys != EVENT_FIELD_ALLOWLIST:
                missing = EVENT_FIELD_ALLOWLIST - keys
                extra = keys - EVENT_FIELD_ALLOWLIST
                raise MailboxEnvelopeError(
                    f"envelope.event has wrong field set: missing={sorted(missing)} extra={sorted(extra)}"
                )
            seq = ev.get("sequence")
            if not isinstance(seq, int) or seq < 14 or seq > 22:
                raise MailboxEnvelopeError(
                    f"envelope.event.sequence={seq!r} outside Phase B range 14..22"
                )
            # Mechanical validation for source_kind, payload etc. (BLOCKER 4) — allow monitoring for fixture_observation B events
            sk = ev.get("source_kind")
            if sk not in ("conversation", "mechanical", "monitoring"):
                raise MailboxEnvelopeError(f"envelope.event.source_kind={sk!r} must be conversation|mechanical|monitoring")
            for f in ("source_class", "modality", "dimension", "event_id", "occurred_at"):
                v = ev.get(f)
                if not isinstance(v, str) or not v.strip():
                    raise MailboxEnvelopeError(f"envelope.event.{f} must be non-empty string")
            payload = ev.get("resident_visible_payload")
            if isinstance(payload, dict):
                if not payload:
                    raise MailboxEnvelopeError("envelope.event.resident_visible_payload dict must be non-empty")
            elif isinstance(payload, str):
                if not payload.strip():
                    raise MailboxEnvelopeError("envelope.event.resident_visible_payload string must be non-empty")
            else:
                raise MailboxEnvelopeError(f"envelope.event.resident_visible_payload must be string or object, got {type(payload).__name__}")
    if envelope.get("phase") not in (None, "B"):
        raise MailboxEnvelopeError(f"envelope.phase={envelope.get('phase')!r} invalid (expected B)")
    if "allowed_sequences" in envelope:
        if envelope["allowed_sequences"] != [14, 22]:
            raise MailboxEnvelopeError(
                f"envelope.allowed_sequences must be [14,22], got {envelope['allowed_sequences']!r}"
            )
    ch = envelope.get("capability_history")
    if ch is not None:
        if not isinstance(ch, list):
            raise MailboxEnvelopeError("capability_history must be a list")
        for i, entry in enumerate(ch):
            if not isinstance(entry, dict):
                raise MailboxEnvelopeError(f"capability_history[{i}] must be an object")
            sid = entry.get("session_id")
            if sid is not None and sid != b_session_id:
                raise MailboxEnvelopeError(
                    f"capability_history[{i}].session_id={sid!r} refers to a non-B session; refuse to send"
                )
            for bad in ("transcript", "mailbox_archive", "full_history", "prior_session"):
                if bad in entry:
                    raise MailboxEnvelopeError(
                        f"capability_history[{i}] contains forbidden key {bad!r}"
                    )
    rs = envelope.get("runtime_snapshot")
    if rs is not None:
        if not isinstance(rs, dict):
            raise MailboxEnvelopeError("runtime_snapshot must be an object")
        for bad_key in (
            "transcript", "a_transcript", "b_transcript",
            "fixture_data", "sealed_events", "evaluator_notes",
            "operator_archive", "mailbox_archive",
        ):
            if bad_key in rs:
                raise MailboxEnvelopeError(f"runtime_snapshot contains forbidden key {bad_key!r}")
    _scan_forbidden(envelope)

def validate_reply(reply: dict[str, Any]) -> None:
    if not isinstance(reply, dict):
        raise MailboxReplyError("reply must be a JSON object")
    # binding fields must be present and correctly typed (checked also in wait_for_reply)
    for field in ("round", "request_id", "request_digest"):
        if field not in reply:
            raise MailboxReplyError(f"reply missing required binding field '{field}'")
    if not isinstance(reply["round"], int) or reply["round"] < 1:
        raise MailboxReplyError("reply.round must be positive integer")
    if not isinstance(reply["request_id"], str) or not _is_hex(reply["request_id"], 32):
        raise MailboxReplyError("reply.request_id must be 32 hex chars")
    if not isinstance(reply["request_digest"], str) or not _is_hex(reply["request_digest"], 64):
        raise MailboxReplyError("reply.request_digest must be 64 hex chars")
    if "action" not in reply:
        raise MailboxReplyError("reply missing required 'action' field")
    action = reply["action"]
    if action not in _VALID_ACTIONS:
        raise MailboxReplyError(f"reply.action={action!r} not in allowed set {sorted(_VALID_ACTIONS)}")
    # Strict top-level allowlist per action: extra fields fail closed
    allow = _REPLY_ALLOWLISTS[action]
    extra = set(reply.keys()) - allow
    if extra:
        raise MailboxReplyError(f"reply for action {action!r} has extra fields {sorted(extra)} not allowed")
    if action == "invoke_capability":
        if not isinstance(reply.get("capability"), str) or not reply["capability"]:
            raise MailboxReplyError("invoke_capability reply requires non-empty 'capability' string")
        if "arguments" in reply and not isinstance(reply["arguments"], dict):
            raise MailboxReplyError("reply.arguments must be an object if present")
    elif action == "end_turn":
        if "response" in reply and not isinstance(reply["response"], str):
            raise MailboxReplyError("end_turn response must be string if present")
        if "response" in reply and reply["response"] is not None and not reply["response"].strip():
            raise MailboxReplyError("end_turn response must be non-blank if present")
    elif action == "silence":
        # silence must not contain capability/response etc. — already enforced by allowlist
        pass
    elif action == "summary_response":
        # must have at least one of response/summary non-blank, but allowlist already restricts
        has_resp = isinstance(reply.get("response"), str) and reply.get("response").strip()
        has_sum = isinstance(reply.get("summary"), str) and reply.get("summary").strip()
        if not (has_resp or has_sum):
            raise MailboxReplyError("summary_response requires non-blank response or summary")
    elif action == "round_repair_request":
        # Per CORRECTIVE-003 Scheme A, this action is not supported in production; but if received it must be treated as fail-closed by the handler.
        # Here we accept its shape but the handler will reject it.
        pass

def _canonical_digest(envelope_without_digest: dict[str, Any]) -> str:
    """Deterministic sha256 over JSON sort_keys, separators=(',',':')."""
    canonical = json.dumps(envelope_without_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

class MailboxBridge:
    def __init__(self, inbox_dir: Path, outbox_dir: Path, archive_dir: Path, b_session_id: str):
        self.inbox_dir = inbox_dir
        self.outbox_dir = outbox_dir
        self.archive_dir = archive_dir
        self.b_session_id = b_session_id
        self._round = 0
        self._outstanding: dict[str, Any] | None = None
        self._consumed: set[str] = set()
        for d in (inbox_dir, outbox_dir, archive_dir):
            d.mkdir(parents=True, exist_ok=True)
        for d in (inbox_dir, outbox_dir):
            for p in d.iterdir():
                if p.is_file():
                    p.unlink()

    @property
    def round(self) -> int:
        return self._round

    @property
    def outstanding(self) -> dict[str, Any] | None:
        return dict(self._outstanding) if self._outstanding else None

    def send(self, envelope: dict[str, Any]) -> Path:
        """Validate, assign binding (round/request_id/request_digest), write."""
        if not isinstance(envelope, dict):
            raise MailboxEnvelopeError("envelope must be a JSON object")
        # Forbid caller pre-setting bridge-assigned fields
        for forbidden in ("round", "request_id", "request_digest"):
            if forbidden in envelope:
                raise MailboxEnvelopeError(f"envelope must not pre-set '{forbidden}' (bridge-assigned)")
        # Must not have outstanding unconsumed request (enforce one-at-a-time)
        if self._outstanding is not None:
            raise MailboxEnvelopeError(
                f"cannot send new request while round {self._outstanding['round']} outstanding (must wait_for_reply first)"
            )
        # Allocate round and request_id
        self._round += 1
        # Generate unique request_id not in consumed set
        for _ in range(5):
            request_id = secrets.token_hex(16)  # 32 hex chars
            if request_id not in self._consumed:
                break
        else:
            raise MailboxEnvelopeError("request_id collision after retries")
        # Build envelope with round and request_id, compute digest without request_digest
        envelope_copy = dict(envelope)
        envelope_copy["round"] = self._round
        envelope_copy["request_id"] = request_id
        # Compute digest over copy WITHOUT request_digest
        request_digest = _canonical_digest(envelope_copy)
        envelope_copy["request_digest"] = request_digest
        # Strict validation after binding
        validate_envelope(envelope_copy, self.b_session_id)
        # Write atomically
        name = f"round-{self._round:04d}.json"
        path = self.inbox_dir / name
        tmp = path.with_suffix(".tmp")
        data = json.dumps(envelope_copy, ensure_ascii=False, sort_keys=True).encode("utf-8")
        tmp.write_bytes(data)
        os.chmod(tmp, 0o644)
        try:
            if os.geteuid() == 0:
                import grp
                try:
                    ngid = grp.getgrnam("nogroup").gr_gid
                except KeyError:
                    ngid = grp.getgrnam("nobody").gr_gid
                os.chown(tmp, 0, ngid)
        except (OSError, KeyError):
            pass
        os.replace(tmp, path)
        (self.archive_dir / f"request-{self._round:04d}.json").write_bytes(data)
        # Record outstanding
        self._outstanding = {
            "round": self._round,
            "request_id": request_id,
            "request_digest": request_digest,
            "envelope_bytes": data,
            "envelope": envelope_copy,
        }
        return path

    def wait_for_reply(self, timeout: float = 600.0, poll: float = 0.1) -> dict[str, Any]:
        if self._outstanding is None:
            raise MailboxReplyError("no outstanding request to wait for (send() first)")
        expected_round = self._outstanding["round"]
        expected_id = self._outstanding["request_id"]
        expected_digest = self._outstanding["request_digest"]
        expected = self.outbox_dir / f"reply-{expected_round:04d}.json"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if expected.exists():
                try:
                    raw = expected.read_bytes()
                    data = json.loads(raw.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    try:
                        (self.archive_dir / f"rejected-reply-{expected_round:04d}.json").write_bytes(raw if 'raw' in locals() else b"")
                    except Exception:
                        pass
                    try:
                        expected.unlink()
                    except FileNotFoundError:
                        pass
                    raise MailboxReplyError(f"malformed reply JSON at round {expected_round}: {e}")
                # Structural validation first
                try:
                    validate_reply(data)
                except MailboxReplyError as e:
                    try:
                        (self.archive_dir / f"rejected-reply-{expected_round:04d}.json").write_bytes(raw)
                    except Exception:
                        pass
                    try:
                        expected.unlink()
                    except FileNotFoundError:
                        pass
                    raise MailboxReplyError(f"reply structural invalid: {e}")

                # Binding verification: round, request_id, request_digest all must match exactly
                if data.get("round") != expected_round:
                    try:
                        (self.archive_dir / f"rejected-reply-{expected_round:04d}.json").write_bytes(raw)
                    except Exception:
                        pass
                    try:
                        expected.unlink()
                    except FileNotFoundError:
                        pass
                    raise MailboxReplyError(
                        f"reply round {data.get('round')!r} != outstanding {expected_round} (stale/future)"
                    )
                if data.get("request_id") != expected_id:
                    if data.get("request_id") in self._consumed:
                        try:
                            (self.archive_dir / f"rejected-reply-{expected_round:04d}.json").write_bytes(raw)
                        except Exception:
                            pass
                        try:
                            expected.unlink()
                        except FileNotFoundError:
                            pass
                        raise MailboxReplyError(
                            f"reply request_id {data.get('request_id')!r} is replay of consumed id (replay rejected)"
                        )
                    try:
                        (self.archive_dir / f"rejected-reply-{expected_round:04d}.json").write_bytes(raw)
                    except Exception:
                        pass
                    try:
                        expected.unlink()
                    except FileNotFoundError:
                        pass
                    raise MailboxReplyError(
                        f"reply request_id {data.get('request_id')!r} != outstanding {expected_id!r} (wrong id)"
                    )
                if data.get("request_digest") != expected_digest:
                    try:
                        (self.archive_dir / f"rejected-reply-{expected_round:04d}.json").write_bytes(raw)
                    except Exception:
                        pass
                    try:
                        expected.unlink()
                    except FileNotFoundError:
                        pass
                    raise MailboxReplyError(
                        f"reply request_digest {data.get('request_digest')!r} != outstanding {expected_digest!r} (wrong digest)"
                    )
                if data["request_id"] in self._consumed:
                    try:
                        (self.archive_dir / f"rejected-reply-{expected_round:04d}.json").write_bytes(raw)
                    except Exception:
                        pass
                    try:
                        expected.unlink()
                    except FileNotFoundError:
                        pass
                    raise MailboxReplyError(f"reply request_id {data['request_id']!r} already consumed (replay)")

                # Success: archive, consume, clear outstanding, unlink
                (self.archive_dir / f"reply-{expected_round:04d}.json").write_bytes(raw)
                try:
                    expected.unlink()
                except FileNotFoundError:
                    pass
                self._consumed.add(expected_id)
                self._outstanding = None
                return data
            time.sleep(poll)
        raise TimeoutError(f"mailbox reply round {expected_round} timed out after {timeout}s")

# Negative self-tests

def _self_tests() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for sub in ("inbox", "outbox", "archive"):
            (root / sub).mkdir()
        b = MailboxBridge(root / "inbox", root / "outbox", root / "archive", "b-session-XYZ")

        ok = {"phase": "B", "allowed_sequences": [14, 22],
              "event": {"event_id":"c15rcc-014","sequence":14,"occurred_at":"2026-11-05T09:00-08:00",
                        "dimension":"conversation","source_kind":"conversation","source_class":"user",
                        "modality":"text","resident_visible_payload":{"text":"hi"}},
              "runtime_snapshot":{},"capability_catalog":[],"capability_history":[]}
        b.send(ok)
        assert (root / "inbox" / "round-0001.json").exists()
        inbox_data = json.loads((root / "inbox" / "round-0001.json").read_text())
        assert "request_id" in inbox_data and "request_digest" in inbox_data and "round" in inbox_data
        print("self-test 1 PASS: minimal good envelope accepted with binding")

        # 2 extra top-level
        bad = {**ok, "transcript": "leak"}
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            try:
                bb.send(bad); raise SystemExit("FAIL: extra top-level key accepted")
            except MailboxEnvelopeError:
                print("self-test 2 PASS: extra top-level key rejected")

        # 3 extra event field
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            bad2 = {**ok, "event": {**ok["event"], "fixture_hint": "leak"}}
            try:
                bb.send(bad2); raise SystemExit("FAIL: extra event field accepted")
            except MailboxEnvelopeError:
                print("self-test 3 PASS: extra event field rejected")

        # 4 A-session in cap history
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            bad3 = {**ok, "capability_history":[{"session_id":"a-session-old","op":"x"}]}
            try:
                bb.send(bad3); raise SystemExit("FAIL: A-session accepted")
            except MailboxEnvelopeError:
                print("self-test 4 PASS: A session in capability_history rejected")

        # 5 forbidden path substring (sealed_fixture) — bare 'fixture' in durable World ids like obs_c14_fixture_* is ALLOWED, only path leakage blocked
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            bad4 = {**ok, "event":{**ok["event"], "resident_visible_payload":{"text":"leak /repo/fixture/sealed"}}}
            try:
                bb.send(bad4); raise SystemExit("FAIL: forbidden path accepted")
            except MailboxEnvelopeError:
                print("self-test 5 PASS: forbidden path substring rejected (legal obs_c14_fixture_* allowed)")

        # 5b legal durable World fixture id is ALLOWED (obs_c14_fixture_*)
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            # This mimics a capability_history entry containing a legal World object id with fixture substring — must NOT be rejected
            legal = {**ok, "capability_history":[{"session_id":"b-session-XYZ","name":"search_world","ok":True,"data":[{"object_id":"obs_c14_fixture_5d4dfcf42055c00135a78a54","excerpt":"Atlas"}],"call_id":None}]}
            try:
                bb.send(legal)
                print("self-test 5b PASS: legal durable World fixture id allowed (obs_c14_fixture_*)")
            except MailboxEnvelopeError as e:
                raise SystemExit(f"FAIL: legal World fixture id wrongly rejected: {e}")

        # 6 wrong phase
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            bad5 = {**ok, "phase": "A"}
            try:
                bb.send(bad5); raise SystemExit("FAIL: phase=A accepted")
            except MailboxEnvelopeError:
                print("self-test 6 PASS: wrong phase rejected")

        # 7 malformed reply
        try:
            validate_reply({"foo":"bar"}); raise SystemExit("FAIL: reply missing action accepted")
        except MailboxReplyError:
            print("self-test 7 PASS: malformed reply rejected")

        # 7b extra reply field rejected (strict allowlist per action)
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            bb.send(ok)
            out = bb.outstanding
            # silence must not contain capability
            bad_reply = {"round": out["round"], "request_id": out["request_id"], "request_digest": out["request_digest"], "action": "silence", "capability": "search_world"}
            (r2/"outbox"/f"reply-{out['round']:04d}.json").write_text(json.dumps(bad_reply))
            try:
                bb.wait_for_reply(timeout=2)
                raise SystemExit("FAIL: extra field in silence reply accepted")
            except MailboxReplyError as e:
                if "extra" not in str(e).lower():
                    raise SystemExit(f"FAIL: wrong error for extra field: {e}")
                print("self-test 7b PASS: extra reply field rejected (strict schema)")
            # clean for next: need fresh bridge for remaining tests, use new temp
        # 8 binding: correct exact-bound reply accepted
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            bb.send(ok)
            outstanding = bb.outstanding
            assert outstanding is not None
            reply = {"round": outstanding["round"], "request_id": outstanding["request_id"], "request_digest": outstanding["request_digest"], "action": "silence"}
            (r2/"outbox"/f"reply-{outstanding['round']:04d}.json").write_text(json.dumps(reply))
            got = bb.wait_for_reply(timeout=2)
            assert got["action"] == "silence"
            print("self-test 8 PASS: correct exact-bound reply accepted")

        # 9 stale prior-round reply rejected
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            bb.send(ok)
            out1 = bb.outstanding
            reply1 = {"round": out1["round"], "request_id": out1["request_id"], "request_digest": out1["request_digest"], "action": "silence"}
            (r2/"outbox"/f"reply-{out1['round']:04d}.json").write_text(json.dumps(reply1))
            bb.wait_for_reply(timeout=2)
            bb.send(ok)
            out2 = bb.outstanding
            stale = {"round": out1["round"], "request_id": out1["request_id"], "request_digest": out1["request_digest"], "action": "silence"}
            (r2/"outbox"/f"reply-{out2['round']:04d}.json").write_text(json.dumps(stale))
            try:
                bb.wait_for_reply(timeout=2)
                raise SystemExit("FAIL: stale prior-round reply accepted")
            except MailboxReplyError as e:
                assert "round" in str(e) or "stale" in str(e)
                print("self-test 9 PASS: stale prior-round reply rejected")

        # 10 preplayed future-round reply rejected
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            guessed = {"round": 1, "request_id": "a"*32, "request_digest": "b"*64, "action": "silence"}
            (r2/"outbox"/"reply-0001.json").write_text(json.dumps(guessed))
            bb.send(ok)
            try:
                bb.wait_for_reply(timeout=2)
                raise SystemExit("FAIL: preplayed future reply accepted")
            except MailboxReplyError:
                print("self-test 10 PASS: preplayed future-round reply rejected")

        # 11 replayed consumed reply rejected
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            bb.send(ok)
            out = bb.outstanding
            reply = {"round": out["round"], "request_id": out["request_id"], "request_digest": out["request_digest"], "action": "silence"}
            (r2/"outbox"/f"reply-{out['round']:04d}.json").write_text(json.dumps(reply))
            bb.wait_for_reply(timeout=2)
            bb.send(ok)
            out2 = bb.outstanding
            replay = {"round": out2["round"], "request_id": out["request_id"], "request_digest": out2["request_digest"], "action": "silence"}
            (r2/"outbox"/f"reply-{out2['round']:04d}.json").write_text(json.dumps(replay))
            try:
                bb.wait_for_reply(timeout=2)
                raise SystemExit("FAIL: replayed consumed reply accepted")
            except MailboxReplyError as e:
                assert "replay" in str(e) or "consumed" in str(e) or "request_id" in str(e)
                print("self-test 11 PASS: replayed consumed reply rejected")

        # 12 wrong request_id rejected
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            bb.send(ok)
            out = bb.outstanding
            wrong_id = "f"*32 if out["request_id"] != "f"*32 else "e"*32
            bad = {"round": out["round"], "request_id": wrong_id, "request_digest": out["request_digest"], "action": "silence"}
            (r2/"outbox"/f"reply-{out['round']:04d}.json").write_text(json.dumps(bad))
            try:
                bb.wait_for_reply(timeout=2)
                raise SystemExit("FAIL: wrong request_id accepted")
            except MailboxReplyError:
                print("self-test 12 PASS: wrong request_id rejected")

        # 13 wrong digest rejected
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            bb.send(ok)
            out = bb.outstanding
            wrong_dg = "f"*64 if out["request_digest"] != "f"*64 else "e"*64
            bad = {"round": out["round"], "request_id": out["request_id"], "request_digest": wrong_dg, "action": "silence"}
            (r2/"outbox"/f"reply-{out['round']:04d}.json").write_text(json.dumps(bad))
            try:
                bb.wait_for_reply(timeout=2)
                raise SystemExit("FAIL: wrong digest accepted")
            except MailboxReplyError:
                print("self-test 13 PASS: wrong request_digest rejected")

        # 14 cannot send while outstanding
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            bb.send(ok)
            try:
                bb.send(ok)
                raise SystemExit("FAIL: second send while outstanding accepted")
            except MailboxEnvelopeError:
                print("self-test 14 PASS: double send while outstanding rejected")

        # 15 pre-set binding fields rejected
        with tempfile.TemporaryDirectory() as td2:
            r2 = Path(td2)
            for sub in ("inbox","outbox","archive"):
                (r2/sub).mkdir()
            bb = MailboxBridge(r2/"inbox", r2/"outbox", r2/"archive", "b-session-XYZ")
            bad = {**ok, "request_id": "a"*32}
            try:
                bb.send(bad)
                raise SystemExit("FAIL: pre-set request_id accepted")
            except MailboxEnvelopeError:
                print("self-test 15 PASS: pre-set request_id rejected")

    print("ALL SELF-TESTS PASS")
    return 0

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "self-test":
        raise SystemExit(_self_tests())
