#!/usr/bin/env python3
"""
C15-RCC-RES-B-PREFLIGHT-002 — Transport-only mailbox bridge.

Responsibility (transport only, ZERO semantic judgment):

  1. Write the current RuntimeSnapshot + resident-visible event projection
     (8 fields per release_contract §4) + capability catalog/history to
     /work/inbox/round-NNNN.json INSIDE the sandbox (tmpfs).
  2. Block until the Resident writes a reply to /work/outbox/reply-NNNN.json.
  3. Read the reply; validate ONLY that it is a JSON object with an
     expected envelope shape (action + capability args or summary).
  4. Hand the reply to Core on the operator side; record the result in the
     mailbox archive OUTSIDE the sandbox (for evidence, not for Resident
     visibility).

Semantic decisions (what Claim to write, what entity key to use, whether
to revise, whether to remain silent, what Summary text to produce) are
made ENTIRELY by the Resident model.  The bridge MUST NOT:
  - suggest answers, keywords, or capability calls;
  - prefill directives;
  - retry on malformed Resident output without re-presenting the SAME
    snapshot/projection (Resident chooses repairs);
  - inject A-era mailbox contents, A transcripts, or governance prose.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


class MailboxBridge:
    def __init__(self, inbox_dir: Path, outbox_dir: Path, archive_dir: Path):
        self.inbox_dir = inbox_dir
        self.outbox_dir = outbox_dir
        self.archive_dir = archive_dir
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self._round = 0

    def send(self, snapshot: dict[str, Any]) -> Path:
        """Write one Resident-visible envelope into inbox_dir.
        Returns the path written. The Resident model context is
        assembled externally from this envelope; this bridge only
        places the bytes.
        """
        self._round += 1
        name = f"round-{self._round:04d}.json"
        path = self.inbox_dir / name
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(snapshot, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)
        # Archive the request on the operator side
        (self.archive_dir / f"request-{self._round:04d}.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )
        return path

    def wait_for_reply(self, timeout: float = 600.0, poll: float = 0.25) -> dict[str, Any]:
        """Block until a matching reply appears in outbox_dir.
        Returns parsed JSON reply, or raises TimeoutError.
        Performs ONLY structural validation.
        """
        expected = self.outbox_dir / f"reply-{self._round:04d}.json"
        deadline = time.time() + timeout
        while time.time() < deadline:
            if expected.exists():
                try:
                    data = json.loads(expected.read_text(encoding="utf-8"))
                except json.JSONDecodeError as e:
                    raise ValueError(f"malformed reply JSON at round {self._round}: {e}")
                if not isinstance(data, dict):
                    raise ValueError(f"reply at round {self._round} must be a JSON object")
                if "action" not in data:
                    raise ValueError(f"reply at round {self._round} missing 'action' field")
                # Archive on operator side, then remove from outbox to prevent replay
                (self.archive_dir / f"reply-{self._round:04d}.json").write_text(
                    json.dumps(data, ensure_ascii=False, sort_keys=True), encoding="utf-8"
                )
                expected.unlink()
                return data
            time.sleep(poll)
        raise TimeoutError(f"mailbox reply round {self._round} timed out after {timeout}s")

    @property
    def round(self) -> int:
        return self._round


# Resident-visible envelope schema (only what's allowed by release_contract §4):
# {
#   "round": int,
#   "event": {                # 8 fields ONLY
#     "event_id", "sequence", "occurred_at", "dimension",
#     "source_kind", "source_class", "modality", "resident_visible_payload"
#   } | null,                # null for due-work rounds with no new event
#   "runtime_snapshot": { ... },  # produced by Core; no A transcript, no governance prose
#   "capability_catalog": [ ... ],
#   "capability_history": [ ... ],  # only history from THIS B session
#   "wake_reason": str | null,
#   "is_summary_request": bool,
# }
#
# Reply envelope schema (Resident → Core):
# {
#   "action": "invoke_capability" | "end_turn" | "silence" | "summary_response",
#   "capability": "<name>" | null,
#   "arguments": { ... } | null,
#   "summary_text": str | null,
#   "notes": str | null   # optional; operator stores but does not treat as action
# }
#
# NOTE: no keyword default, no semantic fallback. If the reply is structurally
# invalid the operator must NOT guess — it must re-present the snapshot/projection
# (Resident repairs its own output via a fresh model round).
