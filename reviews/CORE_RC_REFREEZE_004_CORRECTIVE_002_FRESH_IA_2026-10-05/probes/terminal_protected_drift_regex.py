#!/usr/bin/env python3
"""Test candidate #336's initial and terminal protected-drift EREs verbatim."""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile

CANDIDATE = "5a5d384f16798bfff46ffe03f87310b0eafb2321"
WORKFLOW = ".github/workflows/core-rc-refreeze-004-formal-gate.yml"


def candidate_workflow() -> str:
    return subprocess.check_output(["git", "show", f"{CANDIDATE}:{WORKFLOW}"], text=True)


def extract_pattern(line: str) -> str:
    m = re.search(r"grep -Eq '([^']+)'", line)
    if not m:
        raise ValueError(f"no grep ERE found: {line}")
    return m.group(1)


def grep_matches(pattern: str, lines: list[str]) -> bool:
    result = subprocess.run(
        ["grep", "-E", pattern],
        input=("\n".join(lines) + "\n").encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.returncode == 0


def main() -> int:
    source = candidate_workflow()
    lines = source.splitlines()
    initial_index = next(
        i for i, line in enumerate(lines) if '"$live_main"' in line and "grep -Eq" in line
    )
    terminal_index = next(
        i
        for i, line in enumerate(lines)
        if '"$terminal_main"' in line
        and "grep -Eq" in line
        and "TERMINAL_UNADJUDICATED" not in line
    )
    initial = extract_pattern(lines[initial_index])
    terminal = extract_pattern(lines[terminal_index])

    # Build a disposable diff containing only protected paths introduced after
    # the initial main snapshot. This validates the exact path list produced by
    # git diff --name-only, without touching any repository ref.
    with tempfile.TemporaryDirectory(prefix="ia28-drift-regex-") as tmp_s:
        repo = Path(tmp_s)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "IA Probe"], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.email", "ia-probe@example.invalid"],
            check=True,
        )
        (repo / "pyproject.toml").write_text("[project]\nname='frozen'\n", encoding="utf-8")
        (repo / "setup.cfg").write_text("[metadata]\nname = frozen\n", encoding="utf-8")
        (repo / ".github/workflows").mkdir(parents=True)
        (repo / ".github/workflows/core.yml").write_text("name: frozen\n", encoding="utf-8")
        (repo / "src/aios_core").mkdir(parents=True)
        (repo / "src/aios_core/frozen.py").write_text("VALUE = 1\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "frozen"], check=True)
        frozen = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()

        (repo / ".github/workflows/core.yml").write_text("name: changed\n", encoding="utf-8")
        (repo / ".github/workflows/late-added.yml").write_text("name: late\n", encoding="utf-8")
        (repo / "pyproject.toml").write_text("[project]\nname='late'\n", encoding="utf-8")
        (repo / "setup.cfg").write_text("[metadata]\nname = late\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "late protected drift"], check=True)
        diff_paths = subprocess.check_output(
            ["git", "-C", str(repo), "diff", "--name-only", frozen, "HEAD"], text=True
        ).splitlines()

    print(f"candidate_sha={CANDIDATE}")
    print(f"grep_version={subprocess.check_output(['grep', '--version'], text=True).splitlines()[0]}")
    print(f"initial_guard_source_line={initial_index + 1}")
    print(f"initial_guard_ere={initial!r}")
    print(f"terminal_guard_source_line={terminal_index + 1}")
    print(f"terminal_guard_ere={terminal!r}")
    print("disposable_git_diff_paths:")
    for path in diff_paths:
        print(path)
    initial_detected = grep_matches(initial, diff_paths)
    terminal_detected = grep_matches(terminal, diff_paths)
    print(f"initial_guard_matches_diff={str(initial_detected).upper()}")
    print(f"terminal_guard_matches_diff={str(terminal_detected).upper()}")
    for path in [
        ".github/workflows/late-added.yml",
        "pyproject.toml",
        "setup.cfg",
        "src/aios_core/late.py",
        "tests/late.py",
    ]:
        print(
            f"path_probe={path} initial={'MATCH' if grep_matches(initial, [path]) else 'MISS'} "
            f"terminal={'MATCH' if grep_matches(terminal, [path]) else 'MISS'}"
        )
    reproduced = initial_detected and not terminal_detected
    print(
        "RESULT=TERMINAL_PROTECTED_DRIFT_FALSE_NEGATIVE_REPRODUCED"
        if reproduced
        else "RESULT=FALSE_NEGATIVE_NOT_REPRODUCED"
    )
    return 0 if reproduced else 1


if __name__ == "__main__":
    raise SystemExit(main())
