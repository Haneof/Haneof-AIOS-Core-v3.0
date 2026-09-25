#!/usr/bin/env python3
"""
C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-001 — Transport-only mailbox bridge
(envelope-hardened).

Responsibility (transport only, ZERO semantic judgment):

  1. Validate the envelope shape (strict allowlist) before writing to inbox.
     - 'event', if present, must contain EXACTLY the eight resident-visible
       fields per release_contract §4. Extra fields are rejected.
     - Top-level may contain only an explicit allowlist of Resident-safe keys.
     - Capability history entries are filtered to reference only the current
       B session ID (passed to send()).
     - Paths, fixture metadata, governance/evaluator/A-transcript/archive
       content, or any key not in the allowlist causes fail-closed rejection.
  2. Write the validated envelope into inbox_dir as root:nogroup 0644.
  3. Block until a matching reply appears in outbox_dir.
  4. Validate reply structure; return to Core; archive raw bytes in archive_dir.
  5. Provide a strict negative test: malformed/extra-field envelopes raise
     MailboxEnvelopeError before any write.

No semantic answers, keywords, or defaults.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any


# Exact 8-field allowlist for release_contract §4
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

# Top-level envelope allowlist.
# IMPORTANT: we deliberately do NOT include anything from:
#   - governance / task board / checkpoint / PM prose
#   - fixture metadata beyond the 8-field projection in 'event'
#   - A session transcripts / mailbox / decisions / archive
#   - other Resident contracts
#   - file paths that could reveal host layout
TOP_LEVEL_ALLOWLIST = frozenset({
    "round",
    "event",
    "runtime_snapshot",
    "capability_catalog",
    "capability_history",
    "wake_reason",
    "is_periodic_review",
    "is_summary_request",
    "contract_sha256",    # sha256 of the resident-safe contract, integrity only
    "phase",              # "B"
    "allowed_sequences",  # [14, 22] — declares the legal range but does not leak future payloads
})

# Fields that MUST NOT appear anywhere in the envelope. If the RuntimeSnapshot
# from Core happens to contain such a path/string, the envelope must be
# rejected (fail closed) rather than leaking the information.
FORBIDDEN_SUBSTRINGS = (
    "fixture",           # sealed fixture path references
    "evaluator",         # evaluator notes
    "governance",        # governance/task-board/checkpoint
    "sealed_fixture",
    "RESIDENT_A_RERUN",  # A-002 evidence path
    "C15_RCC_RES_A",
    "__pycache__",
    # Paths to sealed repository content
    "/repo/.git",
    "AIOS_SINGLE_WINDOW_TASK_BOARD",
    "AIOS_v3.0_CURRENT_CHECKPOINT",
    "PROJECT_MASTER_MAP",
)


class MailboxEnvelopeError(ValueError):
    """Outbound envelope failed strict validation (fail closed)."""


class MailboxReplyError(ValueError):
    """Inbound reply failed structural validation."""


def _walk(obj: Any, path: str = "") -> list[tuple[str, Any]]:
    """Yield (path, value) pairs for every leaf/dict in obj, used to scan for forbidden substrings."""
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


def validate_envelope(envelope: dict[str, Any], b_session_id: str) -> None:
    """Strict allowlist validation. Raises MailboxEnvelopeError on any violation."""
    if not isinstance(envelope, dict):
        raise MailboxEnvelopeError("envelope must be a JSON object")

    # Top-level keys must all be in the allowlist
    extra_top = set(envelope.keys()) - TOP_LEVEL_ALLOWLIST
    if extra_top:
        raise MailboxEnvelopeError(f"envelope has disallowed top-level keys: {sorted(extra_top)}")

    # 'round' is assigned by the bridge on send; if present it must be positive int.
    r = envelope.get("round")
    if r is not None and (not isinstance(r, int) or r < 1):
        raise MailboxEnvelopeError("envelope.round must be a positive integer when present")

    # event must be either None (due-work rounds) or an object with EXACTLY the 8 fields
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
            # 'sequence' must be within allowed phase-B range
            seq = ev.get("sequence")
            if not isinstance(seq, int) or seq < 14 or seq > 22:
                raise MailboxEnvelopeError(
                    f"envelope.event.sequence={seq!r} outside Phase B range 14..22"
                )

    # phase must be B
    if envelope.get("phase") not in (None, "B"):
        raise MailboxEnvelopeError(f"envelope.phase={envelope.get('phase')!r} invalid (expected B)")

    # allowed_sequences must be [14,22] if present
    if "allowed_sequences" in envelope:
        if envelope["allowed_sequences"] != [14, 22]:
            raise MailboxEnvelopeError(
                f"envelope.allowed_sequences must be [14,22], got {envelope['allowed_sequences']!r}"
            )

    # capability_history must be a list; entries must reference only b_session_id
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
            # Scrub any 'transcript' / 'mailbox_archive' keys
            for bad in ("transcript", "mailbox_archive", "full_history", "prior_session"):
                if bad in entry:
                    raise MailboxEnvelopeError(
                        f"capability_history[{i}] contains forbidden key {bad!r}"
                    )

    # runtime_snapshot must not carry A session info; check session_id field at top level of runtime_snapshot
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

    # Whole-envelope forbidden-substring scan
    _scan_forbidden(envelope)


def validate_reply(reply: dict[str, Any]) -> None:
    if not isinstance(reply, dict):
        raise MailboxReplyError("reply must be a JSON object")
    if "action" not in reply:
        raise MailboxReplyError("reply missing required 'action' field")
    action = reply["action"]
    valid_actions = {"invoke_capability", "end_turn", "silence", "summary_response", "round_repair_request"}
    if action not in valid_actions:
        raise MailboxReplyError(f"reply.action={action!r} not in allowed set {sorted(valid_actions)}")
    if action == "invoke_capability":
        if not isinstance(reply.get("capability"), str) or not reply["capability"]:
            raise MailboxReplyError("invoke_capability reply requires non-empty 'capability' string")
        if "arguments" in reply and not isinstance(reply["arguments"], dict):
            raise MailboxReplyError("reply.arguments must be an object if present")


class MailboxBridge:
    def __init__(self, inbox_dir: Path, outbox_dir: Path, archive_dir: Path, b_session_id: str):
        self.inbox_dir = inbox_dir
        self.outbox_dir = outbox_dir
        self.archive_dir = archive_dir
        self.b_session_id = b_session_id
        self._round = 0
        for d in (inbox_dir, outbox_dir, archive_dir):
            d.mkdir(parents=True, exist_ok=True)
        # Stale files: if running in a fresh run root this should already be empty
        # but clean just in case.
        for d in (inbox_dir, outbox_dir):
            for p in d.iterdir():
                if p.is_file():
                    p.unlink()

    @property
    def round(self) -> int:
        return self._round

    def send(self, envelope: dict[str, Any]) -> Path:
        """Validate and write one Resident-visible envelope. Returns path written.
        Fails closed on any envelope violation (no file is written)."""
        validate_envelope(envelope, self.b_session_id)
        self._round += 1
        envelope["round"] = self._round
        name = f"round-{self._round:04d}.json"
        path = self.inbox_dir / name
        tmp = path.with_suffix(".tmp")
        data = json.dumps(envelope, ensure_ascii=False, sort_keys=True).encode("utf-8")
        tmp.write_bytes(data)
        os.chmod(tmp, 0o644)
        try:
            if os.geteuid() == 0:
                # nogroup is the target; we set group ownership so nobody can read
                import grp
                try:
                    ngid = grp.getgrnam("nogroup").gr_gid
                except KeyError:
                    ngid = grp.getgrnam("nobody").gr_gid
                os.chown(tmp, 0, ngid)
        except (OSError, KeyError):
            pass
        os.replace(tmp, path)
        # Archive on operator side
        (self.archive_dir / f"request-{self._round:04d}.json").write_bytes(data)
        return path

    def wait_for_reply(self, timeout: float = 600.0, poll: float = 0.1) -> dict[str, Any]:
        expected = self.outbox_dir / f"reply-{self._round:04d}.json"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if expected.exists():
                try:
                    raw = expected.read_bytes()
                    data = json.loads(raw.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    raise MailboxReplyError(f"malformed reply JSON at round {self._round}: {e}")
                validate_reply(data)
                (self.archive_dir / f"reply-{self._round:04d}.json").write_bytes(raw)
                # Atomic remove
                try:
                    expected.unlink()
                except FileNotFoundError:
                    pass
                return data
            time.sleep(poll)
        raise TimeoutError(f"mailbox reply round {self._round} timed out after {timeout}s")


# Negative self-tests (run as script)
def _self_tests() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for sub in ("inbox", "outbox", "archive"):
            (root / sub).mkdir()
        b = MailboxBridge(root / "inbox", root / "outbox", root / "archive", "b-session-XYZ")

        # 1. Good minimal envelope should succeed
        ok = {"round": 1, "phase": "B", "allowed_sequences": [14, 22],
              "event": {"event_id":"c15rcc-014","sequence":14,"occurred_at":"2026-11-05T09:00-08:00",
                        "dimension":"conversation","source_kind":"conversation","source_class":"user",
                        "modality":"text","resident_visible_payload":{"text":"hi"}},
              "runtime_snapshot":{},"capability_catalog":[],"capability_history":[]}
        b.send(ok)
        assert (root / "inbox" / "round-0001.json").exists()
        print("self-test 1 PASS: minimal good envelope accepted")

        # 2. Extra top-level key rejected
        bad = {**ok, "transcript": "leak"}
        try:
            b.send(bad); raise SystemExit("FAIL: extra top-level key accepted")
        except MailboxEnvelopeError:
            print("self-test 2 PASS: extra top-level key rejected")

        # 3. Extra event field rejected
        bad = {**ok, "event": {**ok["event"], "fixture_hint": "leak"}}
        try:
            b.send(bad); raise SystemExit("FAIL: extra event field accepted")
        except MailboxEnvelopeError:
            print("self-test 3 PASS: extra event field rejected")

        # 4. A-session capability_history rejected
        bad = {**ok, "capability_history":[{"session_id":"a-session-old","op":"x"}]}
        try:
            b.send(bad); raise SystemExit("FAIL: A-session in cap history accepted")
        except MailboxEnvelopeError:
            print("self-test 4 PASS: A session in capability_history rejected")

        # 5. Forbidden substring in payload rejected
        bad = {**ok, "event":{**ok["event"], "resident_visible_payload":{"text":"look at governance"}}}
        try:
            b.send(bad); raise SystemExit("FAIL: forbidden substring accepted")
        except MailboxEnvelopeError:
            print("self-test 5 PASS: forbidden substring rejected")

        # 6. Wrong phase rejected
        bad = {**ok, "phase": "A"}
        try:
            b.send(bad); raise SystemExit("FAIL: phase=A accepted in B bridge")
        except MailboxEnvelopeError:
            print("self-test 6 PASS: wrong phase rejected")

        # 7. Malformed reply rejected
        try:
            validate_reply({"foo":"bar"}); raise SystemExit("FAIL: reply missing action accepted")
        except MailboxReplyError:
            print("self-test 7 PASS: malformed reply rejected")
    print("ALL SELF-TESTS PASS")
    return 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "self-test":
        raise SystemExit(_self_tests())
