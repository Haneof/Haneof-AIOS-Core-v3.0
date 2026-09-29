"""Freeze the Corrective-003 evidence manifest + candidate scope gate.

Everything is computed from the *staged index* (or ``HEAD`` with ``--from-head``)
so it describes exactly the commit that will carry the manifest.  A file cannot
contain the hash of the commit that contains it, so the candidate SHA/tree are
published externally (PR comment + branch tip).

The scope gate is mechanical:

allowed
    ``tools/c15_persistence/**``, ``tests/c15_persistence/**`` and this task's
    persistence review/evidence material under
    ``reviews/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003/**``.
forbidden
    ``src/aios_core/**``, product packaging, Resident A/B/C or evaluator
    evidence, real-run artifacts, fixture/future data, UI/hardware and unrelated
    governance architecture.

Usage::

    PYTHONPATH=src:. python -m tools.c15_persistence.freeze_corrective_003_evidence \
        --base 016a2f7db5ed01b41fc614701079c507d2c2c02e
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = REPO_ROOT / "reviews" / "C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003"
EVIDENCE_DIR = REVIEW_DIR / "evidence"
PROBE_MATRIX = REVIEW_DIR / "frozen" / "CORRECTIVE_003_PROBE_MATRIX.json"

# Historical identities that must stay preserved and must NOT be ancestors of
# this continuation (the frozen WIP is read for scope-compliant files only; no
# WIP commit is cherry-picked and no scope-violating Core diff is inherited).
FROZEN_WIP_HEAD = "a2d815c9f5154d87a56b152ed7cf5d1eb1baaaae"
SCOPE_VIOLATING_WIP = "f7848952b6519fc40f50806f4a4d8d350ac0f38a"
FAILED_EXACT_002 = "7b2556e738d9c9386ec21c13fec39400c87d0916"
HISTORICAL_SIX_BLOCKER_VERDICT = "ACCEPTANCE_FAIL / blocker=6"
PM_FROZEN_CONTRACT_RELEASE_BLOCKERS = 3

ALLOWED_PREFIXES = (
    "tools/c15_persistence/",
    "tests/c15_persistence/",
    "reviews/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003/",
)
FORBIDDEN_EXACT = (
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
)
FORBIDDEN_PREFIXES = (
    "src/aios_core/",
    "reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-",
    "reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-",
    "reviews/internal_habitation/c15-rcc/v1/evaluator/",
    "reviews/internal_habitation/c14-resident/",
    "fixtures/",
    ".github/workflows/",
)


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


def _is_ancestor(sha: str, head: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", sha, head],
            cwd=str(REPO_ROOT),
            capture_output=True,
        ).returncode
        == 0
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _classify(path: str) -> str:
    if path in FORBIDDEN_EXACT or path.startswith(FORBIDDEN_PREFIXES):
        return "FORBIDDEN"
    if path.startswith(ALLOWED_PREFIXES):
        return "ALLOWED"
    return "OUT_OF_DECLARED_SCOPE"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="starting live main sha")
    parser.add_argument("--from-head", action="store_true", help="use HEAD, not the index")
    parser.add_argument("--out", default=str(EVIDENCE_DIR / "EVIDENCE_MANIFEST.json"))
    args = parser.parse_args(argv)

    head = _git("rev-parse", "HEAD")
    diff_target = "HEAD" if args.from_head else "--cached"
    changed = [
        line
        for line in _git("diff", diff_target, "--name-only", args.base).splitlines()
        if line
    ]
    self_path = str(Path(args.out).relative_to(REPO_ROOT))
    if self_path not in changed:
        changed.append(self_path)
    changed = sorted(set(changed))

    core_diff = [
        path for path in changed if path == "src/aios_core" or path.startswith("src/aios_core/")
    ]
    classification = {path: _classify(path) for path in changed}
    scope_violations = [
        path for path, verdict in classification.items() if verdict != "ALLOWED"
    ]

    matrix = json.loads(PROBE_MATRIX.read_text(encoding="utf-8"))
    evidence_files = sorted(
        path
        for path in EVIDENCE_DIR.rglob("*")
        if path.is_file()
        and path.name not in {"EVIDENCE_MANIFEST.json", "EVIDENCE_MANIFEST.json.sha256"}
    )

    manifest = {
        "kind": "C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003-EVIDENCE-MANIFEST",
        "note": (
            "A file cannot contain the hash of the commit that contains it, so the "
            "candidate commit SHA/tree and the PR number are published externally "
            "(PR comment + branch tip). Every proof below is computed from the "
            "staged index (or HEAD when --from-head is used)."
        ),
        "candidate": {
            "staged_against_head": head,
            "resume_base_live_main": args.base,
            "changed_files_vs_base": changed,
            "path_classification": classification,
            "scope_violations": scope_violations,
            "src_aios_core_diff_vs_base": core_diff,
            "src_aios_core_diff_is_zero": not core_diff,
            "product_packaging_touched": any(
                path in FORBIDDEN_EXACT for path in changed
            ),
        },
        "historical_preservation": {
            "pr_251_failed_exact_candidate": FAILED_EXACT_002,
            "pr_251_verdict": HISTORICAL_SIX_BLOCKER_VERDICT,
            "pm_frozen_contract_release_blockers": PM_FROZEN_CONTRACT_RELEASE_BLOCKERS,
            "pr_254_frozen_wip_head": FROZEN_WIP_HEAD,
            "pr_254_frozen_wip_head_is_ancestor_of_candidate": _is_ancestor(
                FROZEN_WIP_HEAD, head
            ),
            "scope_violating_wip": SCOPE_VIOLATING_WIP,
            "scope_violating_wip_is_ancestor_of_candidate": _is_ancestor(
                SCOPE_VIOLATING_WIP, head
            ),
        },
        "environment_identity": {
            "python": sys.version.split()[0],
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "sqlite": sqlite3.sqlite_version,
            "formal_gate_pin": "CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1",
            "disclosed_delta": (
                "This sandbox cannot obtain CPython 3.12.14 (GitHub release-asset and "
                "python.org downloads are blocked; Debian 12 ships CPython 3.11). The "
                "candidate was executed on CPython 3.11.2 / Pydantic 2.13.5 / pytest "
                "8.4.2 / SQLite 3.40.1 and the delta is disclosed rather than hidden."
            ),
        },
        "frozen_probe_matrix": {
            "manifest_path": str(PROBE_MATRIX.relative_to(REPO_ROOT)),
            "manifest_sha256": _sha256(PROBE_MATRIX),
            "probe_count": matrix["probe_count"],
            "probe_ids": matrix["probe_ids"],
            "freeze_history": matrix["freeze_history"],
            "freeze_reason": matrix["freeze_reason"],
            "sources": matrix["sources"],
        },
        "evidence": [
            {
                "path": str(path.relative_to(REPO_ROOT)),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in evidence_files
        ],
    }

    out = Path(args.out)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out.with_suffix(".json.sha256").write_text(
        f"{_sha256(out)}  {out.name}\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "manifest": str(out),
                "sha256": _sha256(out),
                "changed_files": len(changed),
                "scope_violations": scope_violations,
                "src_diff_zero": not core_diff,
                "probe_count": matrix["probe_count"],
            },
            indent=2,
        )
    )
    return 1 if scope_violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
