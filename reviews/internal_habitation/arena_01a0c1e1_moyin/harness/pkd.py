"""Compact renderer for pending dimension_summary / round_summary checkpoints.

Evidence-only tooling: it reads the already-materialised RuntimeSnapshot and
prints the same information in fewer tokens. It makes no semantic decision.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PENDING = BASE / "run" / "pending.json"
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 130


def main() -> None:
    meta = json.loads(PENDING.read_text(encoding="utf-8"))
    rec = json.loads(Path(meta["snapshot_path"]).read_text(encoding="utf-8"))
    p = rec["payload"]
    print(f"# {meta['checkpoint_id']} kind={meta['kind']} at={meta['simulated_at']}")
    scalar = {k: v for k, v in p.items() if isinstance(v, (str, int, float, bool, type(None)))}
    for k in sorted(scalar):
        print(f"  {k} = {scalar[k]}")
    for key, val in sorted(p.items()):
        if isinstance(val, (str, int, float, bool, type(None))):
            continue
        if isinstance(val, list):
            print(f"  [{key}] n={len(val)}")
            for item in val[:40]:
                if isinstance(item, dict):
                    oid = item.get("object_id") or (item.get("object_ref") or {}).get("object_id") or ""
                    typ = item.get("object_type") or item.get("dimension") or ""
                    txt = item.get("excerpt") or item.get("content") or item.get("text") or item.get("payload") or ""
                    if isinstance(txt, dict):
                        txt = json.dumps(txt, ensure_ascii=False)
                    print(f"    - {typ} {oid} :: {str(txt)[:LIMIT]}".replace("\n", " "))
                else:
                    print(f"    - {str(item)[:LIMIT]}")
        elif isinstance(val, dict):
            print(f"  {{{key}}} keys={sorted(val.keys())}")
            for k2, v2 in val.items():
                if isinstance(v2, (str, int, float, bool, type(None))):
                    print(f"    {k2} = {str(v2)[:LIMIT]}")
                elif isinstance(v2, list):
                    print(f"    {k2}: n={len(v2)}")
                    for item in v2[:40]:
                        if isinstance(item, dict):
                            oid = item.get("object_id") or (item.get("object_ref") or {}).get("object_id") or ""
                            txt = item.get("excerpt") or item.get("content") or item.get("text") or ""
                            print(f"      - {item.get('object_type','')} {oid} :: {str(txt)[:LIMIT]}".replace("\n", " "))
                        else:
                            print(f"      - {str(item)[:LIMIT]}")
                else:
                    print(f"    {k2} = {json.dumps(v2, ensure_ascii=False)[:LIMIT]}")


main()
