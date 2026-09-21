#!/usr/bin/env python3
"""Mechanical reader: pull the current Segment 003 pending checkpoint from the
mechanic runner's check-run annotations and print it verbatim.

This script performs no semantic interpretation. It only retrieves and decodes
what the runner already printed for the Resident (current pending
RuntimeSnapshot / Summary request plus runner state).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = "Haneof/Haneof-AIOS-Core-v3.0"
BRANCH = "arena/01a0bfa4-haneof-aios-core-v3-0"


def gh_json(*args: str):
    out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out.strip()


def unescape(text: str) -> str:
    return text.replace("%0D", "\r").replace("%0A", "\n").replace("%25", "%")


def main() -> int:
    sha = gh_json("api", f"repos/{REPO}/commits/{BRANCH}", "--jq", ".sha")
    runs = gh_json(
        "api",
        f"repos/{REPO}/commits/{sha}/check-runs?per_page=50",
        "--jq",
        '.check_runs[] | select(.name=="resident-step") | .id',
    )
    check_run = runs if isinstance(runs, int) else (runs if runs else None)
    if check_run is None:
        print("no resident-step check run for", sha, file=sys.stderr)
        return 1

    annotations = gh_json(
        "api", f"repos/{REPO}/check-runs/{check_run}/annotations?per_page=100"
    )
    import base64
    import re
    import zlib

    grouped: dict[str, list[tuple[int, str]]] = {}
    for item in annotations:
        title = (item.get("title") or "").strip()
        match = re.match(r"^(?P<base>seg003-.+?)-(?P<index>\d+)of(?P<total>\d+)$", title)
        if match:
            grouped.setdefault(match.group("base"), []).append(
                (int(match.group("index")), unescape(item.get("message") or ""))
            )
        elif title.startswith("seg003-"):
            grouped.setdefault(title, []).append((1, unescape(item.get("message") or "")))

    out_dir = Path(__file__).resolve().parent
    print(f"check_run={check_run} sha={sha}")
    for base, pieces in sorted(grouped.items()):
        joined = "".join(piece for _, piece in sorted(pieces))
        if base.endswith("-z"):
            try:
                text = zlib.decompress(base64.b64decode(joined)).decode("utf-8")
            except Exception as exc:  # noqa: BLE001
                print(f"{base}: decode failed ({exc}); storing raw")
                text = joined
        else:
            text = joined
        target = out_dir / f"latest_{base}.txt"
        target.write_text(text, encoding="utf-8")
        first = text.strip().splitlines()[0][:120] if text.strip() else "(empty)"
        print(f"{base}: {len(text)} chars -> {target.name} | {first}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
