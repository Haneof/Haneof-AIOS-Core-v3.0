"""Gate-test bootstrap.

Test-only configuration. It never imports Resident semantics and never injects
a semantic responder into the run package; the synthetic responder lives in
``tests/synthetic`` and is only reachable from tests.
"""

from __future__ import annotations

import os
import pathlib
import sys

HARNESS_ROOT = pathlib.Path(__file__).resolve().parents[1]
TESTS_ROOT = pathlib.Path(__file__).resolve().parent

for candidate in (str(HARNESS_ROOT), str(TESTS_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

repo_src = os.environ.get("AIOS_REPO_SRC")
if repo_src and repo_src not in sys.path:
    sys.path.insert(0, repo_src)
