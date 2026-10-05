#!/usr/bin/env python3
"""Exercise the exact shell helper called by the formal terminal guard."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile

GUARD = Path(__file__).with_name("terminal_protected_drift_guard.sh")


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def run_case(repo: Path, base: str, name: str, changes: dict[str, str | None], expect_block: bool) -> None:
    git(repo, "reset", "--hard", base)
    git(repo, "clean", "-fdx")
    for rel, content in changes.items():
        path = repo / rel
        if content is None:
            path.unlink(missing_ok=True)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    if changes:
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", f"control {name}")
    terminal = git(repo, "rev-parse", "HEAD")
    output = repo.parent / f"{name}.diff"
    result = subprocess.run(["bash", str(GUARD), base, terminal, str(output)],
                            cwd=repo, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    blocked = result.returncode != 0
    if blocked != expect_block:
        raise AssertionError(
            f"{name}: expected blocked={expect_block}, got rc={result.returncode}\n{result.stdout}"
        )
    print(f"case={name} expected={'FAIL_CLOSED' if expect_block else 'PASS'} "
          f"actual={'FAIL_CLOSED' if blocked else 'PASS'} rc={result.returncode}")
    for line in result.stdout.splitlines():
        if line.startswith("TERMINAL_"):
            print(f"  {line}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="w30-terminal-drift-") as tmp_s:
        root = Path(tmp_s) / "repo"
        root.mkdir()
        git(root.parent, "init", "-q", str(root))
        git(root, "config", "user.name", "Window 30 guard control")
        git(root, "config", "user.email", "w30-guard@example.invalid")
        (root / ".github/workflows").mkdir(parents=True)
        (root / ".github/workflows/core.yml").write_text("name: baseline\n", encoding="utf-8")
        (root / "pyproject.toml").write_text("[project]\nname='baseline'\n", encoding="utf-8")
        (root / "setup.cfg").write_text("[metadata]\nname=baseline\n", encoding="utf-8")
        (root / "MANIFEST.in").write_text("include README.md\n", encoding="utf-8")
        (root / "requirements.txt").write_text("pydantic==2.13.5\n", encoding="utf-8")
        (root / "src/aios_core").mkdir(parents=True)
        (root / "src/aios_core/core.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "tests").mkdir()
        (root / "tests/test_core.py").write_text("def test_base(): pass\n", encoding="utf-8")
        git(root, "add", ".")
        git(root, "commit", "-qm", "initial main snapshot")
        base = git(root, "rev-parse", "HEAD")

        run_case(root, base, "no-drift", {}, False)
        run_case(root, base, "late-workflow-add-and-modify", {
            ".github/workflows/core.yml": "name: changed\n",
            ".github/workflows/late-added.yml": "name: late\n",
        }, True)
        run_case(root, base, "late-pyproject-change", {
            "pyproject.toml": "[project]\nname='late'\n",
        }, True)
        run_case(root, base, "setup-manifest-requirements", {
            "setup.py": "from setuptools import setup\n",
            "setup.cfg": "[metadata]\nname=late\n",
            "MANIFEST.in": "include changed.txt\n",
            "requirements-dev.txt": "pytest==8.4.2\n",
            "requirements/ci.txt": "ruff==0.14.0\n",
        }, True)
        run_case(root, base, "existing-src-and-tests-protection", {
            "src/aios_core/core.py": "VALUE = 2\n",
            "tests/test_new.py": "def test_new(): pass\n",
        }, True)
        run_case(root, base, "protected-deletion", {
            "setup.cfg": None,
        }, True)
        run_case(root, base, "unprotected-review-evidence", {
            "reviews/control-note.md": "non-protected evidence\n",
        }, False)

    print("SHELL_MATCH=FORMAL_WORKFLOW_CALLS_THIS_EXACT_HELPER")
    print("TERMINAL_PROTECTED_DRIFT_CONTROLS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
