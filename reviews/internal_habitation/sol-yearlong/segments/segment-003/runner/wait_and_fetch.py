#!/usr/bin/env python3
"""Mechanical helper: wait for the newest session-side runner workflow run for
this branch to finish, then pull the current pending checkpoint.

No semantics: it polls GitHub for run completion and delegates to
fetch_pending.py / extract_pending.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = "Haneof/Haneof-AIOS-Core-v3.0"
BRANCH = "arena/01a0bfa4-haneof-aios-core-v3-0"
WORKFLOW = "sol-seg003-resident-step-arena.yml"
HERE = Path(__file__).resolve().parent


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def newest_run() -> dict:
    out = gh(
        "run",
        "list",
        "--repo",
        REPO,
        "--branch",
        BRANCH,
        "--workflow",
        WORKFLOW,
        "--limit",
        "1",
        "--json",
        "databaseId,status,conclusion,headSha,displayTitle",
    )
    runs = json.loads(out)
    if not runs:
        raise SystemExit("no workflow run found")
    return runs[0]


def main() -> int:
    deadline = time.time() + float(sys.argv[1]) if len(sys.argv) > 1 else time.time() + 300
    while True:
        run = newest_run()
        print(f"run={run['databaseId']} status={run['status']} conclusion={run['conclusion']} sha={run['headSha'][:9]}")
        if run["status"] == "completed":
            break
        if time.time() > deadline:
            print("wait timed out; continuing with whatever is published")
            break
        time.sleep(12)

    subprocess.run([sys.executable, str(HERE / "fetch_pending.py")], check=False)
    return subprocess.run([sys.executable, str(HERE / "extract_pending.py")], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
