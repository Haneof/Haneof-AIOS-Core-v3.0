"""Test-path bootstrap for the C15 persistence harness probes.

The probes import ``tools.c15_persistence`` from the repository root.  A bare
``pytest`` invocation - which is exactly what the repository's formal CI gates
use (``pytest -q``, ``pytest -o addopts='' ...``) - does *not* put the current
directory on ``sys.path``, so collection aborted with
``ModuleNotFoundError: No module named 'tools'``.  ``python -m pytest`` happens
to insert the current directory, which is why the defect only appears in CI.

Adding the repository root here makes the probes runnable under both
invocations while preserving the binding constraints:

* the harness stays **not installed** (no packaging change, no ``.pth`` file);
* no product code (``src/aios_core/**``) is touched;
* the scope is deliberately local to this directory - no root ``conftest.py``
  and no global pytest configuration change, so no other suite is affected.

The ``src`` directory is added as well so the probes also work when the
surrounding invocation does not apply ``pythonpath`` from ``pyproject.toml``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    entry = str(candidate)
    if candidate.is_dir() and entry not in sys.path:
        sys.path.insert(0, entry)


# --------------------------------------------------------------------------- CI
# GitHub check-run *logs* are not always reachable to a reviewer (they live in an
# object store behind the API), while check-run *annotations* are.  Emitting one
# annotation per failing test makes a red gate actionable without downloading a
# multi-megabyte log: the failure identity and the last lines of the failure are
# visible directly in the checks UI/API.  Strictly read-only - no expectation,
# assertion or probe outcome is affected, and nothing is emitted outside CI.
_MAX_ANNOTATIONS = 10
_MAX_DETAIL = 300


def _failure_lines(stats: dict[str, list[Any]]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for status in ("failed", "error"):
        for report in stats.get(status, []) or []:
            nodeid = str(getattr(report, "nodeid", "?")).strip() or "?"
            if nodeid in seen:
                continue
            seen.add(nodeid)
            detail = str(getattr(report, "longrepr", "") or "").strip().splitlines()
            summary = " | ".join(detail[-2:]) if detail else "no failure detail"
            lines.append(f"{nodeid} :: {summary[:_MAX_DETAIL]}")
    return sorted(lines)


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: Any) -> None:
    """Surface every failing test (whole session, not just this directory)."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    lines = _failure_lines(getattr(terminalreporter, "stats", {}) or {})
    if not lines:
        return
    for line in lines[:_MAX_ANNOTATIONS]:
        print(f"::error title=pytest failure::{line}", flush=True)
    if len(lines) > _MAX_ANNOTATIONS:
        remainder = " ;; ".join(lines[_MAX_ANNOTATIONS:])[:60000]
        print(f"::error title=pytest failures {len(lines)}::{remainder}", flush=True)
    print(f"::error title=pytest failure count::{len(lines)}", flush=True)
