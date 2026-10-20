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
from tools.c15_persistence.resident_surface_check import (  # noqa: E402
    _authorized_tasks,
    resolve_surface_base,
)

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
    evidence = json.loads(out.read_text()) if out.is_file() else {}
    if completed.returncode != 0:
        pinned = evidence.get("pinned_tree_diff_vs_base", {})
        detail = {
            "comparisons_failed": [
                k for k, v in evidence.get("comparisons", {}).items() if v is not True
            ],
            "pinned_scopes": {
                k: {
                    "clean": v.get("clean"),
                    "authorized": v.get("authorized"),
                    "diff": (v.get("diff") or "")[:400],
                }
                for k, v in pinned.items()
                if isinstance(v, dict)
            },
            "authorized_by": evidence.get("pinned_diff_authorized_by"),
            "resolved_base": pinned.get("resolved_base_sha"),
        }
        pytest.fail(
            "resident surface check failed:\n"
            f"{json.dumps(detail, indent=2, ensure_ascii=False)}\n"
            f"stderr: {completed.stderr[-2000:]}"
        )
    assert evidence["result"] == "RESIDENT_SURFACE_UNCHANGED", evidence["comparisons"]

    # Everything the Resident or the model can observe must be byte-identical
    # between the wired production path and the no-persistence control.
    for name, equal in evidence["comparisons"].items():
        assert equal is True, f"resident-visible surface differs: {name}"

    # The pinned trees the run depends on are either untouched, or changed by an
    # increment that declares the governance task authorising the change. An
    # undeclared Core change still fails.
    for scope, detail in evidence["pinned_tree_diff_vs_base"].items():
        if isinstance(detail, dict):
            assert detail["clean"] or detail["authorized"], (
                f"{scope} was modified without an Authorized-Task declaration: {detail['diff']}"
            )

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
    evidence = json.loads(out.read_text()) if out.is_file() else {}
    if completed.returncode != 0:
        pinned = evidence.get("pinned_tree_diff_vs_base", {})
        pytest.fail(
            "exact-base surface check failed:\n"
            + json.dumps(
                {
                    "comparisons_failed": [
                        k for k, v in evidence.get("comparisons", {}).items() if v is not True
                    ],
                    "pinned_scopes": {
                        k: {
                            "clean": v.get("clean"),
                            "authorized": v.get("authorized"),
                            "diff": (v.get("diff") or "")[:400],
                        }
                        for k, v in pinned.items()
                        if isinstance(v, dict)
                    },
                    "authorized_by": evidence.get("pinned_diff_authorized_by"),
                    "resolved_base": pinned.get("resolved_base_sha"),
                },
                indent=2,
                ensure_ascii=False,
            )
            + f"\nstderr: {completed.stderr[-2000:]}"
        )
    assert evidence["result"] == "RESIDENT_SURFACE_UNCHANGED"
    assert evidence["pinned_tree_diff_vs_base"]["resolved_base_sha"] == resolved_sha


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
    )


def test_undeclared_core_change_is_still_rejected(tmp_path: Path) -> None:
    """A Core change without an Authorized-Task trailer must not be authorised.

    This is the negative half of the split invariant: relaxing "Core must never
    change" to "Core may change when declared" is only safe if the undeclared
    case still fails closed.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "core.py").write_text("v1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")

    (repo / "core.py").write_text("v2\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "undeclared core change")

    assert _authorized_tasks("HEAD~1", repo_root=repo) == []

    (repo / "core.py").write_text("v3\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "declared core change\n\nAuthorized-Task: SOME-TASK-001")

    assert _authorized_tasks("HEAD~2", repo_root=repo) == ["SOME-TASK-001"]
