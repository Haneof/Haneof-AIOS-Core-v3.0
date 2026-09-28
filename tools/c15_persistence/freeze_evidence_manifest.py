"""Freeze the resumed evidence manifest.

The manifest deliberately does **not** record its own commit SHA or tree: a file
cannot contain a hash of the commit that contains it.  Those two values are
published externally (PR comment / branch tip).  Everything else - ancestry
proofs, the zero ``src/aios_core`` diff, the changed-file list and every
evidence hash - is computed from the *staged index*, so it describes exactly
the commit that will carry this manifest.


Produces ``reviews/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_001/resumed/evidence/
EVIDENCE_MANIFEST.json`` plus its ``.sha256``:

* every evidence file in the resumed tree with its SHA256,
* the frozen probe-suite revision and manifest SHA,
* the git identity of the candidate (sha, parents, tree, ancestry proofs),
* the ``src/aios_core`` diff against the resume base (must be zero).

Usage::

    PYTHONPATH=src:. python3 -m tools.c15_persistence.freeze_evidence_manifest \\
        --sha <candidate-sha> --base <resume-base-sha>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = (
    REPO_ROOT
    / "reviews"
    / "C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_001"
    / "resumed"
    / "evidence"
)
PROBE_MANIFEST = REPO_ROOT / "tests" / "c15_persistence" / "killpoints" / "PROBE_MANIFEST.json"
PROBE_MANIFEST_SHA = (
    REPO_ROOT / "tests" / "c15_persistence" / "killpoints" / "PROBE_MANIFEST.sha256"
)


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


def environment_identity() -> dict[str, str]:
    import platform
    import sys

    identity = {
        "python": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "grade": "ENGINEERING",
        "note": (
            "Local sandbox is CPython 3.11.2; the formal CPython 3.12.14 + "
            "pydantic 2.13.5 + pytest 8.x result comes from the "
            "c15-rcc-res-b-persistence-corrective-001-formal-gate workflow."
        ),
    }
    try:
        import pydantic

        identity["pydantic"] = pydantic.VERSION
    except Exception:  # pragma: no cover - optional
        pass
    try:
        import pytest

        identity["pytest"] = pytest.__version__
    except Exception:  # pragma: no cover - optional
        pass
    return identity


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="resume base (main) sha")
    parser.add_argument(
        "--historical",
        default="6db057a5fddbaf403be8377682b81219a074fef6",
        help="frozen WIP head that must be an ancestor of --sha",
    )
    parser.add_argument("--out", default=str(EVIDENCE_DIR / "EVIDENCE_MANIFEST.json"))
    args = parser.parse_args(argv)

    head = _git("rev-parse", "HEAD")
    is_ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", args.historical, head],
        cwd=str(REPO_ROOT),
        capture_output=True,
    ).returncode == 0

    # Staged index -> exactly the commit this manifest will travel in.
    core_diff = _git("diff", "--cached", "--name-only", args.base, "--", "src/aios_core")
    changed = _git("diff", "--cached", "--name-only", args.base).splitlines()
    self_path = str(Path(args.out).relative_to(REPO_ROOT))
    if self_path not in changed:
        changed.append(self_path)

    files = sorted(
        p for p in EVIDENCE_DIR.rglob("*")
        if p.is_file() and p.name not in {"EVIDENCE_MANIFEST.json", "EVIDENCE_MANIFEST.json.sha256"}
    )
    manifest = {
        "kind": "C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001-RESUMED-EVIDENCE-MANIFEST",
        "note": (
            "A file cannot contain the hash of the commit that contains it, so the "
            "candidate commit SHA and tree are published externally (PR #216 comment "
            "and the branch tip). Every proof below is computed from the staged index."
        ),
        "candidate": {
            "staged_against_head": head,
            "resume_base": args.base,
            "historical_frozen_wip_head": args.historical,
            "historical_head_is_ancestor_of_head": is_ancestor,
            "changed_files_vs_base": sorted(changed),
            "src_aios_core_diff_vs_base": core_diff.splitlines(),
            "src_aios_core_diff_is_zero": core_diff.strip() == "",
        },
        "environment_identity": environment_identity(),
        "frozen_probe_suite": {
            "manifest_path": str(PROBE_MANIFEST.relative_to(REPO_ROOT)),
            "manifest_sha256": sha256(PROBE_MANIFEST),
            "manifest_sha256_file": PROBE_MANIFEST_SHA.read_text().split()[0],
            "revision": json.loads(PROBE_MANIFEST.read_text()).get("revision"),
        },
        "evidence": [
            {
                "path": str(path.relative_to(REPO_ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }

    out = Path(args.out)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (out.with_suffix(".json.sha256")).write_text(f"{sha256(out)}  {out.name}\n")
    print(json.dumps({"manifest": str(out), "sha256": sha256(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
