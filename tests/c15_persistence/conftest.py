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

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

for candidate in (REPO_ROOT, REPO_ROOT / "src"):
    entry = str(candidate)
    if candidate.is_dir() and entry not in sys.path:
        sys.path.insert(0, entry)
