#!/usr/bin/env python3
"""Mechanical writer for a single Segment 003 Resident decision fragment.

Usage:
  python3 write_decision.py <part-NN> response <text>
  python3 write_decision.py <part-NN> silence
  python3 write_decision.py <part-NN> summary <text>
  python3 write_decision.py <part-NN> calls <path-to-calls-json>

The decision key is always taken from the worktree's current pending envelope
(`latest_pending_envelope.json`, written by extract_pending.py). No semantic
interpretation happens here; the text/calls come from the Resident model.

It also refuses to write a fragment whose key already exists in another
fragment, which keeps the runner's mechanical merge step valid.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECISIONS = HERE.parent / "decisions"


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    part = sys.argv[1]
    kind = sys.argv[2]

    envelope = json.loads((HERE / "latest_pending_envelope.json").read_text(encoding="utf-8"))
    key = envelope["decision_key"]

    if kind in {"response", "summary"}:
        if len(sys.argv) < 4:
            raise SystemExit("text argument required")
        payload = {"kind": kind, kind: sys.argv[3]}
    elif kind == "silence":
        payload = {"kind": "silence"}
    elif kind == "calls":
        calls = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        payload = {"kind": "capability_calls", "calls": calls}
    else:
        raise SystemExit(f"unknown kind {kind}")

    for path in sorted(DECISIONS.glob("part-*.json")):
        existing = json.loads(path.read_text(encoding="utf-8"))
        if key in existing:
            raise SystemExit(f"decision key already present in {path.name}: {key}")
        if key in json.loads(path.read_text(encoding="utf-8")):
            raise SystemExit(f"duplicate {path.name}")

    target = DECISIONS / (part if part.endswith(".json") else f"{part}.json")
    if target.exists():
        raise SystemExit(f"{target.name} already exists")
    target.write_text(json.dumps({key: payload}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {target.name} kind={kind} key={key[:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
