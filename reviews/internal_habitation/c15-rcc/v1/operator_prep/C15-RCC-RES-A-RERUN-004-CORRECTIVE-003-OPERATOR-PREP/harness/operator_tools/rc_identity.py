"""Operator tooling: frozen RC identity and Core content verification.

Uses git object ids only; it never prints or inspects commit content. This tool
is deliberately outside the run package so the run package needs no
``subprocess``.

Usage:
    python operator_tools/rc_identity.py --repo-root <repo> [--json <path>]
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import subprocess
import sys
from typing import Any

FROZEN_SOFTWARE_SHA = "f20f2edfa7af00d0286493fd15196ca9503bc315"
FROZEN_REPOSITORY_TREE = "1ac3a675b884167d3a29aa432e7ef3eaff94d404"
FROZEN_CORE_TREE = "9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623"
FROZEN_TESTS_TREE = "7e33b5ef8432370234965d3ccd61248c703c4019"


def _git(repo_root: pathlib.Path, *args: str) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args], capture_output=True, text=True, timeout=120
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def verify(repo_root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(repo_root)
    observed = {
        "software_object_type": _git(repo, "cat-file", "-t", FROZEN_SOFTWARE_SHA),
        "repository_tree": _git(repo, "rev-parse", f"{FROZEN_SOFTWARE_SHA}^{{tree}}"),
        "core_tree": _git(repo, "rev-parse", f"{FROZEN_SOFTWARE_SHA}:src/aios_core"),
        "tests_tree": _git(repo, "rev-parse", f"{FROZEN_SOFTWARE_SHA}:tests"),
        "head": _git(repo, "rev-parse", "HEAD"),
        "head_core_tree": _git(repo, "rev-parse", "HEAD:src/aios_core"),
        "head_tests_tree": _git(repo, "rev-parse", "HEAD:tests"),
        "src_drift": _git(repo, "diff", "--stat", FROZEN_SOFTWARE_SHA, "HEAD", "--", "src"),
        "tests_drift": _git(repo, "diff", "--stat", FROZEN_SOFTWARE_SHA, "HEAD", "--", "tests"),
    }
    checks = {
        "software_object_is_commit": observed["software_object_type"] == "commit",
        "repository_tree_matches": observed["repository_tree"] == FROZEN_REPOSITORY_TREE,
        "core_tree_matches": observed["core_tree"] == FROZEN_CORE_TREE,
        "tests_tree_matches": observed["tests_tree"] == FROZEN_TESTS_TREE,
        "head_core_tree_matches_frozen": observed["head_core_tree"] == FROZEN_CORE_TREE,
        "head_tests_tree_matches_frozen": observed["head_tests_tree"] == FROZEN_TESTS_TREE,
        "no_src_drift_from_frozen_software": observed["src_drift"] == "",
        "no_tests_drift_from_frozen_software": observed["tests_drift"] == "",
    }
    return {
        "ok": all(checks.values()),
        "repo_root": str(repo),
        "checks": checks,
        "observed": observed,
        "expected": {
            "software": FROZEN_SOFTWARE_SHA,
            "repository_tree": FROZEN_REPOSITORY_TREE,
            "core_tree": FROZEN_CORE_TREE,
            "tests_tree": FROZEN_TESTS_TREE,
        },
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--json", default=None)
    args = parser.parse_args()
    report = verify(args.repo_root)
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
