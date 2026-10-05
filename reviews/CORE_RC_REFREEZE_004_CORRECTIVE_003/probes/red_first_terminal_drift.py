#!/usr/bin/env python3
"""RED-first reproduction of #336's terminal protected-drift false negative.

The patterns are extracted from the exact workflow, and GNU grep -E is used
against paths returned by git diff in a disposable repository.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path


def extract_ere(line: str) -> str:
    match = re.search(r"grep -Eq '([^']+)'", line)
    if not match:
        raise AssertionError(f"no ERE on line: {line}")
    return match.group(1)


def grep_matches(pattern: str, paths: list[str]) -> bool:
    result = subprocess.run(["grep", "-E", pattern], input="\n".join(paths) + "\n",
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=False)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr)
    return result.returncode == 0


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def main() -> int:
    workflow = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    initial_line = next(line for line in workflow if '"$live_main"' in line and "grep -Eq" in line)
    terminal_line = next(line for line in workflow if '"$terminal_main"' in line and "grep -Eq" in line)
    initial, terminal = extract_ere(initial_line), extract_ere(terminal_line)
    with tempfile.TemporaryDirectory(prefix="w30-red-drift-") as tmp_s:
        repo = Path(tmp_s)
        git(repo.parent, "init", "-q", str(repo))
        git(repo, "config", "user.name", "Window 30 RED probe")
        git(repo, "config", "user.email", "w30-red@example.invalid")
        (repo / ".github/workflows").mkdir(parents=True)
        (repo / ".github/workflows/core.yml").write_text("name: base\n", encoding="utf-8")
        (repo / "pyproject.toml").write_text("[project]\nname='base'\n", encoding="utf-8")
        (repo / "setup.cfg").write_text("[metadata]\nname=base\n", encoding="utf-8")
        (repo / "src/aios_core").mkdir(parents=True)
        (repo / "src/aios_core/core.py").write_text("VALUE=1\n", encoding="utf-8")
        (repo / "tests").mkdir()
        (repo / "tests/test_core.py").write_text("def test_ok(): pass\n", encoding="utf-8")
        git(repo, "add", "."); git(repo, "commit", "-qm", "initial main snapshot")
        base = git(repo, "rev-parse", "HEAD")
        (repo / ".github/workflows/core.yml").write_text("name: changed\n", encoding="utf-8")
        (repo / ".github/workflows/late-added.yml").write_text("name: late\n", encoding="utf-8")
        (repo / "pyproject.toml").write_text("[project]\nname='late'\n", encoding="utf-8")
        (repo / "setup.cfg").write_text("[metadata]\nname=late\n", encoding="utf-8")
        (repo / "src/aios_core/late.py").write_text("VALUE=2\n", encoding="utf-8")
        (repo / "tests/test_late.py").write_text("def test_late(): pass\n", encoding="utf-8")
        git(repo, "add", "."); git(repo, "commit", "-qm", "late protected drift")
        paths = git(repo, "diff", "--name-only", base, "HEAD").splitlines()
    print(f"source_workflow={sys.argv[1]}")
    print("test_git=disposable_repository; refs outside repository untouched")
    print(f"initial_ere={initial!r}")
    print(f"terminal_ere={terminal!r}")
    print("diff_paths=" + ",".join(paths))
    target_paths = [".github/workflows/late-added.yml", "pyproject.toml", "setup.cfg"]
    print(f"initial_guard_detects_all={str(grep_matches(initial, paths)).upper()}")
    print(f"terminal_guard_detects_all={str(grep_matches(terminal, paths)).upper()}")
    print(f"initial_guard_detects_late_workflow_packaging={str(grep_matches(initial, target_paths)).upper()}")
    print(f"terminal_guard_detects_late_workflow_packaging={str(grep_matches(terminal, target_paths)).upper()}")
    for path in (*target_paths, "src/aios_core/late.py", "tests/test_late.py"):
        print(f"path={path} initial={'MATCH' if grep_matches(initial, [path]) else 'MISS'} "
              f"terminal={'MATCH' if grep_matches(terminal, [path]) else 'MISS'}")
    reproduced = (grep_matches(initial, target_paths) and not grep_matches(terminal, target_paths)
                  and grep_matches(terminal, ["src/aios_core/late.py"])
                  and grep_matches(terminal, ["tests/test_late.py"]))
    print("RED=TERMINAL_PROTECTED_DRIFT_FALSE_NEGATIVE_REPRODUCED" if reproduced
          else "RED=NOT_REPRODUCED")
    return 0 if reproduced else 1


if __name__ == "__main__":
    raise SystemExit(main())
