"""The durability layer must not change anything the Resident can observe.

This is the suite-level entry point for
``tools/c15_persistence/resident_surface_check.py``; the check itself runs in a
fresh interpreter so what is measured is the real production wiring, not an
in-process import of it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "killpoints"))

from harness import REPO_ROOT, new_root, repo_python_env  # noqa: E402

EVIDENCE_DIR = (
    REPO_ROOT / "reviews" / "C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_001" / "resumed" / "evidence"
)


def test_resident_visible_surface_is_unchanged_by_the_durability_layer() -> None:
    out = EVIDENCE_DIR / "resident-surface-no-change.json"
    work_root = new_root("resident-surface")
    env = dict(repo_python_env())
    env["C15_SURFACE_BASE"] = os.environ.get("C15_SURFACE_BASE", "main")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.c15_persistence.resident_surface_check",
            "--out",
            str(out),
            "--base",
            env["C15_SURFACE_BASE"],
            "--work-root",
            str(work_root / "runs"),
        ],
        capture_output=True,
        text=True,
        timeout=900,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert completed.returncode == 0, (
        "resident surface check failed:\\n"
        f"stdout: {completed.stdout}\\nstderr: {completed.stderr}"
    )
    evidence = json.loads(out.read_text())
    assert evidence["result"] == "RESIDENT_SURFACE_UNCHANGED", evidence["comparisons"]

    # Everything the Resident or the model can observe must be byte-identical
    # between the wired production path and the no-persistence control.
    for name, equal in evidence["comparisons"].items():
        assert equal is True, f"resident-visible surface differs: {name}"

    # The pinned trees the run depends on are untouched by this corrective.
    for scope, detail in evidence["pinned_tree_diff_vs_base"].items():
        if isinstance(detail, dict):
            assert detail["clean"] is True, f"{scope} was modified: {detail['diff']}"

    # The audit is only meaningful if the surface was actually exercised.
    assert len(evidence["control"]["calls"]) >= 2, evidence["control"]["calls"]
    assert evidence["control"]["catalog"], "empty capability catalog"
