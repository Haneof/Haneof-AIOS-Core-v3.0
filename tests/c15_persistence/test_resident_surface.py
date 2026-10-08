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
from tools.c15_persistence.resident_surface_check import resolve_surface_base  # noqa: E402

# Corrective-003 evidence re-anchor: the committed artifact lives under this
# corrective's own evidence root instead of the frozen Corrective-001 WIP path.
EVIDENCE_DIR = REPO_ROOT / "reviews" / "C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003" / "evidence"


def test_resident_visible_surface_is_unchanged_by_the_durability_layer(tmp_path: Path) -> None:
    # The checked-in evidence file is produced by an explicit, logged invocation
    # of the checker so that the suite never rewrites reviewed evidence; this
    # test writes to a scratch path and asserts on that.
    out = tmp_path / "resident-surface-no-change.json"
    work_root = new_root("resident-surface")
    env = dict(repo_python_env())
    
    # Auto-resolve canonical base SHA if C15_SURFACE_BASE is not explicitly set
    base_sha = resolve_surface_base(os.environ.get("C15_SURFACE_BASE"))
    env["C15_SURFACE_BASE"] = base_sha

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.c15_persistence.resident_surface_check",
            "--out",
            str(out),
            "--base",
            base_sha,
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
        "resident surface check failed:\n"
        f"stdout: {completed.stdout}\nstderr: {completed.stderr}"
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

    # The committed evidence artifact must be present and must itself report the
    # same verdict. The evidence manifest hashes it, so any drift is caught.
    committed = EVIDENCE_DIR / "resident-surface-no-change.json"
    assert committed.is_file(), f"missing committed evidence: {committed}"
    assert json.loads(committed.read_text())["result"] == "RESIDENT_SURFACE_UNCHANGED"


def test_unresolved_symbolic_base_fails_cleanly(tmp_path: Path) -> None:
    """Regression test for PM49-BLK-001 (UNRESOLVED_SYMBOLIC_MAIN_RED).

    Asserts that an unresolvable base ref fails immediately with non-zero exit code
    and explicit error message, preventing vacuous PASS.
    """
    out = tmp_path / "resident-surface-unresolved.json"
    work_root = new_root("resident-surface-unresolved")
    env = dict(repo_python_env())
    env["C15_SURFACE_BASE"] = "nonexistent_symbolic_ref_for_regression_test_404"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.c15_persistence.resident_surface_check",
            "--out",
            str(out),
            "--base",
            "nonexistent_symbolic_ref_for_regression_test_404",
            "--work-root",
            str(work_root / "runs"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert completed.returncode != 0, f"expected failure for invalid base ref, got stdout={completed.stdout}"
    assert "does not resolve to a valid commit" in completed.stderr or "ValueError" in completed.stderr


def test_exact_base_sha_succeeds_non_vacuously(tmp_path: Path) -> None:
    """Regression test for PM49-BLK-001 (EXACT_BASE_SHA_GREEN).

    Asserts that mechanically derived base SHA resolves properly in any checkout
    and executes non-vacuous resident surface check.
    """
    resolved_sha = resolve_surface_base(None)
    assert len(resolved_sha) == 40, f"expected 40-char commit SHA, got {resolved_sha}"

    out = tmp_path / "resident-surface-exact-sha.json"
    work_root = new_root("resident-surface-exact-sha")
    env = dict(repo_python_env())
    env["C15_SURFACE_BASE"] = resolved_sha

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.c15_persistence.resident_surface_check",
            "--out",
            str(out),
            "--base",
            resolved_sha,
            "--work-root",
            str(work_root / "runs"),
        ],
        capture_output=True,
        text=True,
        timeout=900,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert completed.returncode == 0, f"stderr: {completed.stderr}\nstdout: {completed.stdout}"
    evidence = json.loads(out.read_text())
    assert evidence["result"] == "RESIDENT_SURFACE_UNCHANGED"
    assert evidence["pinned_tree_diff_vs_base"]["resolved_base_sha"] == resolved_sha
