#!/usr/bin/env python3
"""Generate a deterministic SHA-256 source/config manifest for RC-REFREEZE-003."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import tomllib
from typing import Any

TARGET_DEFAULT = "f20f2edfa7af00d0286493fd15196ca9503bc315"


def git(*args: str, text: bool = True) -> str | bytes:
    out = subprocess.check_output(["git", *args])
    return out.decode("utf-8") if text else out


def tree_path(revision: str, path: str) -> str:
    return str(git("rev-parse", f"{revision}:{path}")).strip()


def file_paths(revision: str, path: str) -> list[str]:
    raw = git("ls-tree", "-r", "--name-only", revision, "--", path)
    assert isinstance(raw, str)
    return [line for line in raw.splitlines() if line]


def file_entry(revision: str, path: str) -> dict[str, str]:
    blob = str(git("rev-parse", f"{revision}:{path}")).strip()
    content = git("cat-file", "blob", blob, text=False)
    assert isinstance(content, bytes)
    return {
        "path": path,
        "git_blob": blob,
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def commit_record(sha: str) -> dict[str, Any]:
    raw = str(git("show", "-s", "--format=%H%x00%P%x00%s", sha)).strip("\n")
    commit_sha, parents, subject = raw.split("\x00", 2)
    changed = str(git("diff-tree", "--root", "--no-commit-id", "--name-status", "-r", "-m", sha))
    return {
        "sha": commit_sha,
        "parents": parents.split() if parents else [],
        "subject": subject,
        "changed_paths_by_parent": [line for line in changed.splitlines() if line],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=TARGET_DEFAULT)
    parser.add_argument("--live-main", default="origin/main")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    target, live = args.target, args.live_main

    project_bytes = git("show", f"{target}:pyproject.toml", text=False)
    assert isinstance(project_bytes, bytes)
    project = tomllib.loads(project_bytes.decode("utf-8"))
    workflows = file_paths(target, ".github/workflows")
    constitution = file_paths(target, "docs/constitution")
    architecture_baselines = [
        path for path in (
            "docs/architecture/AIOS_v3.0_Development_Master_Plan.md",
            "docs/architecture/AIOS_v3.0_Legacy_Code_Migration_Matrix.md",
            "docs/architecture/AIOS_v3.0_System_Closure_Plan.md",
        ) if str(git("cat-file", "-e", f"{target}:{path}", text=True)) == ""
    ]
    # A deterministic list of all implementation files and release/config inputs.
    source_files = file_paths(target, "src/aios_core")
    test_files = file_paths(target, "tests")
    changed = str(git("diff", "--name-status", target, live)).splitlines()
    changed_paths = [line.split("\t")[-1] for line in changed if line]
    protected = [
        path for path in changed_paths
        if path.startswith(("src/", "tests/", ".github/workflows/")) or path == "pyproject.toml"
    ]
    live_governance_paths = [
        path for path in changed_paths
        if not (path.startswith(("src/", "tests/", ".github/workflows/")) or path == "pyproject.toml")
    ]
    governance_reference_paths = [
        path for path in (
            "PROJECT_MASTER_MAP.md",
            "AIOS_v3.0_CURRENT_CHECKPOINT.md",
            "governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md",
        ) if str(git("cat-file", "-e", f"{target}:{path}", text=True)) == ""
    ]

    target_record = {
        "sha": str(git("rev-parse", target)).strip(),
        "parents": str(git("show", "-s", "--format=%P", target)).split(),
        "tree": str(git("rev-parse", f"{target}^{{tree}}")).strip(),
        "src_aios_core_tree": tree_path(target, "src/aios_core"),
        "tests_tree": tree_path(target, "tests"),
        "workflow_tree": tree_path(target, ".github/workflows"),
    }

    # Resolve every commit that is reachable from fresh live main but not the target.
    later = [line for line in str(git("rev-list", "--reverse", "--topo-order", f"{target}..{live}")).splitlines() if line]
    later_records = [commit_record(sha) for sha in later]

    manifest: dict[str, Any] = {
        "schema": "aios-core-rc-source-manifest-v1",
        "task": "CORE-RC-REFREEZE-003",
        "repository": "Haneof/Haneof-AIOS-Core-v3.0",
        "frozen_software": target_record,
        "fresh_main": {
            "ref": live,
            "sha": str(git("rev-parse", live)).strip(),
            "tree": str(git("rev-parse", f"{live}^{{tree}}")).strip(),
            "commits_after_frozen_software": later_records,
            "aggregate_changed_paths": changed,
            "post_target_governance_evidence_files": [
                file_entry(live, path) for path in live_governance_paths
            ],
            "protected_implementation_drift": protected,
            "protected_implementation_drift_count": len(protected),
            "src_tree_equal": tree_path(target, "src/aios_core") == tree_path(live, "src/aios_core"),
            "tests_tree_equal": tree_path(target, "tests") == tree_path(live, "tests"),
            "workflow_tree_equal": tree_path(target, ".github/workflows") == tree_path(live, ".github/workflows"),
        },
        "source_files": [file_entry(target, path) for path in source_files],
        "test_files": [file_entry(target, path) for path in test_files],
        "release_relevant_workflows": [file_entry(target, path) for path in workflows],
        "release_configs": [file_entry(target, "pyproject.toml")],
        "constitution_baseline_files": [
            file_entry(target, path) for path in constitution + architecture_baselines
        ],
        "governance_reference_files_at_frozen_target": [
            file_entry(target, path) for path in governance_reference_paths
        ],
        "dependency_environment_declaration": {
            "pyproject_blob": str(git("rev-parse", f"{target}:pyproject.toml")).strip(),
            "pyproject_sha256": hashlib.sha256(project_bytes).hexdigest(),
            "requires_python": project["project"].get("requires-python"),
            "dependencies": project["project"].get("dependencies", []),
            "optional_dependencies": project["project"].get("optional-dependencies", {}),
            "lockfiles": [],
            "formal_runtime_pins": {
                "python": "CPython 3.12.14",
                "pydantic": "2.13.5",
                "pytest": "8.4.2",
                "sqlite": "recorded from the exact formal runner; see environment_manifest.txt",
            },
        },
        "candidate_evidence_inputs": [
            {
                "path": path,
                "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            }
            for path in (
                "reviews/CORE_RC_REFREEZE_003/generate_source_manifest.py",
                "reviews/CORE_RC_REFREEZE_003/open_pr_snapshot.json",
                "reviews/CORE_RC_REFREEZE_003/open_pr_contamination_review.md",
                "reviews/CORE_RC_REFREEZE_003/probes/clean_install_headless_smoke.py",
                "reviews/CORE_RC_REFREEZE_003/probes/backup_restore_trusted_return.py",
                "reviews/CORE_RC_REFREEZE_003/probes/trusted_return_registry_inventory.py",
                ".github/workflows/core-rc-refreeze-003-formal-gate.yml",
            )
        ],
    }
    encoded = json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
