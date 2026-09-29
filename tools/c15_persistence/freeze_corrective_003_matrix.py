"""Freeze the Corrective-003 binding-blocker probe matrix.

The probe files carry stable ``PROBE: <id>`` / ``EXPECT: ...`` markers in each
probe docstring.  This script enumerates them and hashes the exact probe sources
so the matrix can be frozen *before* any implementation adjustment:

* ``CORRECTIVE_003_PROBE_MATRIX.json`` -- enumeration + source SHA-256 + the
  frozen file hashes;
* ``CORRECTIVE_003_PROBE_MATRIX.sha256`` -- sidecar hash over that JSON.

Usage::

    python -m tools.c15_persistence.freeze_corrective_003_matrix \
        --out reviews/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003/frozen

Re-running after a probe edit is refused unless ``--force`` is passed, because a
changed probe source invalidates the previous freeze.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import platform
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PROBE_FILES = (
    "tests/c15_persistence/test_corrective_003_binding_blockers.py",
    "tests/c15_persistence/test_corrective_003_regressions.py",
    "tests/c15_persistence/killpoints/test_killpoints.py",
    "tests/c15_persistence/test_corrective_002_remote_durability.py",
    "tests/c15_persistence/test_operator_wiring.py",
    "tests/c15_persistence/test_environment_reattach.py",
    "tests/c15_persistence/test_journal.py",
    "tests/c15_persistence/test_resident_surface.py",
)
HARNESS_SOURCES = (
    "tools/c15_persistence/operator_session.py",
    "tools/c15_persistence/probe_cli.py",
    "tests/c15_persistence/killpoints/harness.py",
)

PROBE_RE = re.compile(r"PROBE:\s*([A-Za-z0-9._-]+)")
EXPECT_RE = re.compile(r"EXPECT:\s*(.*)")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _probes_in(path: Path) -> list[dict[str, object]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    found: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        doc = ast.get_docstring(node, clean=True) or ""
        match = PROBE_RE.search(doc)
        if match is None:
            continue
        expect = EXPECT_RE.search(doc)
        found.append(
            {
                "probe_id": match.group(1).rstrip("."),
                "test_function": node.name,
                "node_id": f"{path.as_posix()}::{node.name}",
                "expect": expect.group(1).strip() if expect else "",
            }
        )
    return sorted(found, key=lambda item: str(item["probe_id"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--reason",
        default="",
        help="documented reason for a re-freeze after a probe correction",
    )
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "CORRECTIVE_003_PROBE_MATRIX.json"
    sidecar_path = out_dir / "CORRECTIVE_003_PROBE_MATRIX.sha256"

    sources = {}
    probes: list[dict[str, object]] = []
    for relative in PROBE_FILES:
        path = REPO_ROOT / relative
        if not path.is_file():
            raise SystemExit(f"probe file missing: {relative}")
        sources[relative] = _sha256(path)
        probes.extend(_probes_in(path))
    for relative in HARNESS_SOURCES:
        path = REPO_ROOT / relative
        sources[relative] = _sha256(path)

    ids = [str(item["probe_id"]) for item in probes]
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        raise SystemExit(f"duplicate probe ids: {duplicates}")

    history: list[dict[str, str]] = []
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        history = list(previous.get("freeze_history") or [])
        if previous.get("frozen_at_utc"):
            history.append(
                {
                    "frozen_at_utc": str(previous["frozen_at_utc"]),
                    "head": str(previous.get("head", "")),
                    "reason": "initial freeze",
                }
            )
    if history and not args.reason:
        raise SystemExit("re-freeze requires --reason")

    manifest = {
        "manifest_version": "c15-corrective-003-probe-matrix-v2",
        "freeze_history": history,
        "freeze_reason": args.reason, 
        "frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repository": "Haneof/Haneof-AIOS-Core-v3.0",
        "head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
        ).stdout.strip(),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "sqlite": sqlite3.sqlite_version,
        },
        "probe_count": len(probes),
        "probe_ids": ids,
        "probes": probes,
        "sources": sources,
    }
    if manifest_path.exists() and not args.force:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("sources") != sources:
            raise SystemExit(
                "probe sources changed since the matrix was frozen; "
                "a new freeze requires an explicit --force and a documented reason"
            )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    sidecar_path.write_text(_sha256(manifest_path) + "  CORRECTIVE_003_PROBE_MATRIX.json\n", encoding="utf-8")
    print(f"probe_count={len(probes)}")
    print(f"manifest_sha256={_sha256(manifest_path)}")
    for probe_id in ids:
        print(f"  - {probe_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
