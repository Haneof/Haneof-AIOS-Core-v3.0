#!/usr/bin/env python3
"""Mechanical extractor: split the runner's sanitized output into the pending
envelope JSON plus the runner status lines, and print a compact digest.

No semantic interpretation: it only parses what the runner printed.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    text = (HERE / "latest_seg003-sanitized-txt-z.txt").read_text(encoding="utf-8", errors="replace")
    integrity = (HERE / "latest_seg003-sanitized-txt-z-integrity.txt").read_text(encoding="utf-8").strip()
    import hashlib

    digest, size, chunks = integrity.split(":")
    actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print(f"integrity_ok={actual == digest} bytes={len(text.encode('utf-8'))} chunks={chunks}")

    for line in text.splitlines():
        if line.startswith(("SEG003_", "RESTORE_OK", "segment003_decisions=")):
            print(line[:300])

    if "MANUAL_RESIDENT_PENDING_BEGIN" in text:
        kind = "resident"
        begin, end = "MANUAL_RESIDENT_PENDING_BEGIN", "MANUAL_RESIDENT_PENDING_END"
    elif "MANUAL_SUMMARY_PENDING_BEGIN" in text:
        kind = "summary"
        begin, end = "MANUAL_SUMMARY_PENDING_BEGIN", "MANUAL_SUMMARY_PENDING_END"
    else:
        print("no pending envelope in runner output")
        return 1

    body = text.split(begin, 1)[1].split(end, 1)[0]
    payload = json.loads(body)
    payload["_kind"] = kind
    (HERE / "latest_pending_envelope.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"kind={kind} decision_key={payload.get('decision_key')} clock={payload.get('simulated_clock')} rev={payload.get('world_revision_before')}")

    request = payload.get("snapshot") or payload.get("summary_request") or {}
    if kind == "resident":
        print("wake_reason=", request.get("wake_reason"), "round=", request.get("round_index"), "remaining=", request.get("remaining_tool_rounds"))
        print("user_input=", str(request.get("user_input"))[:400].replace("\n", " "))
    else:
        print("summary_request=", json.dumps(request, ensure_ascii=False)[:600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
