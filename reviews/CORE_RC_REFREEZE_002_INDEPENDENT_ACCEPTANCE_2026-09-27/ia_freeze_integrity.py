#!/usr/bin/env python3
"""Independent RC re-freeze integrity probes (freeze-identity family).

Probes F1..F6 attack the freeze packet itself: manifest reproducibility, tree
substitution, stale-RC hash swap, merge-ref equivalence, and open-PR
contamination false negatives.  Read-only against the git object database.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = "/home/user/Haneof-AIOS-Core-v3.0"
FROZEN = "27a21db5b656d441248b9240020910b66a223830"
CAND = "a93972c95356f46d20f5e9e7be82026fe84c0687"
CAND_TREE = "66d89a0344b68520b840690c43aead629e9f7957"
CORE_TREE = "a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6"
TESTS_TREE = "92fcbcc5876833735fb3cb7c73a98c4a8a4a3541"
HISTORICAL_RC = "773876f92d5f8e53422f8f5a68cc651953d93052"
HISTORICAL_CORE = "fe77f8a0706acfaf369041d0882b6d0e6de39f22"
MANIFEST_SHA = "34b3d8adfad376a9cd7170ebec3e6093d40444b03ffd61130ed79602e63e3883"
PLACEHOLDER = "0" * 64

results: list[tuple[bool, str, str]] = []


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


def probe(name: str, ok: bool, detail: str) -> None:
    results.append((ok, name, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")


def recompute_manifest_digest() -> str:
    raw = subprocess.run(
        ["git", "show", f"{CAND}:reviews/CORE_RC_REFREEZE_002/source_manifest.json"],
        cwd=REPO,
        capture_output=True,
        check=True,
    ).stdout
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    # F1 — manifest is byte-reproducible; any tamper changes the digest.
    digest = recompute_manifest_digest()
    tampered = hashlib.sha256(
        subprocess.run(
            ["git", "show", f"{CAND}:reviews/CORE_RC_REFREEZE_002/source_manifest.json"],
            cwd=REPO,
            capture_output=True,
            check=True,
        ).stdout.replace(b"a9618abe", b"a9618abf")
    ).hexdigest()
    probe(
        "F1-manifest-tamper-detection",
        digest == MANIFEST_SHA and tampered != digest,
        f"recomputed={digest[:16]} matches pin={digest == MANIFEST_SHA}; "
        f"single-byte mutation changes digest={tampered != digest}",
    )

    # F2 — wrong Core tree substitution is detectable (and detected).
    frozen_core = git("rev-parse", f"{FROZEN}:src/aios_core")
    hist_core = git("rev-parse", f"{HISTORICAL_RC}:src/aios_core")
    probe(
        "F2-core-tree-substitution",
        frozen_core == CORE_TREE and hist_core == HISTORICAL_CORE and hist_core != frozen_core,
        f"frozen={frozen_core[:12]} historical={hist_core[:12]} (distinct)",
    )

    # F3 — wrong tests tree substitution is detectable.
    frozen_tests = git("rev-parse", f"{FROZEN}:tests")
    hist_tests = git("rev-parse", f"{HISTORICAL_RC}:tests")
    probe(
        "F3-tests-tree-substitution",
        frozen_tests == TESTS_TREE and hist_tests != frozen_tests,
        f"frozen={frozen_tests[:12]} historical={hist_tests[:12]} (distinct)",
    )

    # F4 — stale historical RC identity cannot be passed off as this freeze.
    manifest = json.loads(
        subprocess.run(
            ["git", "show", f"{CAND}:reviews/CORE_RC_REFREEZE_002/source_manifest.json"],
            cwd=REPO,
            capture_output=True,
            check=True,
        ).stdout
    )
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", HISTORICAL_RC, FROZEN], cwd=REPO
    ).returncode == 0
    probe(
        "F4-stale-RC-SHA-substitution",
        manifest["frozen_software_sha"] == FROZEN
        and manifest["historical_rc_freeze_001_software"] == HISTORICAL_RC
        and manifest["historical_rc_freeze_001_core_tree"] == HISTORICAL_CORE
        and ancestry,
        "packet pins historical RC separately from frozen software; "
        f"historical RC is ancestor={ancestry}",
    )

    # F5 — merge-ref equivalence for the reported gate SHA.
    merge_sha = "f9e5cdc6f4ec9b26be1722779fb7f7756389bdc9"
    merge_tree = git("rev-parse", f"{merge_sha}^{{tree}}")
    parents = git("log", "-1", "--format=%P", merge_sha).split()
    merge_core = git("rev-parse", f"{merge_sha}:src/aios_core")
    merge_tests = git("rev-parse", f"{merge_sha}:tests")
    delta = sorted(git("diff", "--name-only", FROZEN, merge_sha).splitlines())
    packet_delta = sorted(
        [
            ".github/workflows/core-rc-refreeze-002-formal-gate.yml",
            "AIOS_v3.0_CURRENT_CHECKPOINT.md",
            "PROJECT_MASTER_MAP.md",
            "governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md",
            "release/rc/CORE_RC_REFREEZE_002_MANIFEST.json",
            "release/rc/CORE_RC_REFREEZE_002_OPERATOR_PACKET.md",
            "reviews/CORE_RC_FREEZE_002_COMPLETION_EVIDENCE_2026-09-27.md",
        ]
        + [
            f"reviews/CORE_RC_REFREEZE_002/{name}"
            for name in (
                "SHA256SUMS",
                "backup_restore_rebuild_smoke.md",
                "crash_recovery_smoke.md",
                "environment_manifest.txt",
                "focused_regressions.md",
                "full_regression.md",
                "headless_smoke.md",
                "known_limitations.md",
                "legacy_fix_spot_checks.md",
                "migration_compatibility.md",
                "no_second_truth_store.md",
                "open_pr_contamination_review.md",
                "rc_impact_adjudication.md",
                "scale.md",
                "source_manifest.json",
                "trusted_return_authenticity_spot_checks.md",
                "writer_restart_smoke.md",
            )
        ]
    )
    non_packet = [
        f for f in delta if f.startswith(("src/", "tests/", "pyproject.toml"))
    ]
    ok = (
        merge_tree == CAND_TREE
        and parents == [FROZEN, CAND]
        and merge_core == CORE_TREE
        and merge_tests == TESTS_TREE
        and delta == packet_delta
        and not non_packet
    )
    probe(
        "F5-merge-ref-identity-mismatch",
        ok,
        f"tree==candidate={merge_tree == CAND_TREE}; parents==[frozen,head]="
        f"{parents == [FROZEN, CAND]}; src/aios_core==a9618abe="
        f"{merge_core == CORE_TREE}; tests==92fcbcc5={merge_tests == TESTS_TREE}; "
        f"delta==declared packet ({len(packet_delta)} files)={delta == packet_delta}; "
        f"src/tests/pyproject delta={non_packet or 'none'}",
    )

    # F6 — open-PR contamination false-negative check (RC closure).
    #
    # Criterion (two parts, both independently verifiable):
    #   (1) exactly the PRs {126,113,111,110} touch src/ relative to their own
    #       merge-base; every other open PR carries zero src/ changes, so it can
    #       never be a competing Core implementation;
    #   (2) each of those four is superseded or integrated, not an active
    #       unmerged Core: #126's changed src blobs are verbatim historical
    #       versions of main's files (stale branch), and #113/#111/#110's
    #       feature symbols plus their test modules already exist in frozen
    #       main in evolved form.
    def git_out(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=REPO, capture_output=True, text=True
        ).stdout

    open_prs = [
        216, 205, 144, 130, 126, 125, 121, 119, 118, 117, 113, 112,
        111, 110, 109, 107, 101, 92, 79, 75, 74, 37,
    ]
    src_touching = []
    for n in open_prs:
        head = git_out("rev-parse", f"refs/remotes/origin/pr{n}").strip()
        if not head:
            continue
        base = git_out("merge-base", FROZEN, head).strip()
        changed = [
            f
            for f in git_out("diff", "--name-only", base, head, "--", "src/").splitlines()
            if f
        ]
        if changed:
            src_touching.append((n, changed))

    stale_ok = True
    for n, changed in src_touching:
        if n != 126:
            continue
        for f in changed:
            blob = git_out("rev-parse", f"refs/remotes/origin/pr{n}:{f}").strip()
            found = False
            for commit in git_out("log", "--format=%H", FROZEN, "--", f).splitlines():
                if git_out("rev-parse", f"{commit}:{f}").strip() == blob:
                    found = True
                    break
            if not found:
                stale_ok = False

    integrated_ok = True
    for sym in ("valid_time", "unknown_items", "counter_evidence"):
        if sym not in git_out("show", f"{FROZEN}:src/aios_core/ai_world/cognition.py"):
            integrated_ok = False
    if "evidence_policy" not in git_out("show", f"{FROZEN}:src/aios_core/revision/service.py"):
        integrated_ok = False
    if "CognitionEvidencePolicy" not in git_out("show", f"{FROZEN}:src/aios_core/policy/evidence.py"):
        integrated_ok = False
    for tf in (
        "tests/integration/test_v3_c15_cognition_fields.py",
        "tests/integration/test_v3_c15_rcc_fields_fix_f02_f03.py",
        "tests/integration/test_v3_c15_cognition_evidence_policy.py",
    ):
        if subprocess.run(["git", "cat-file", "-e", f"{FROZEN}:{tf}"], cwd=REPO).returncode != 0:
            integrated_ok = False

    probe(
        "F6-open-PR-contamination-false-negative",
        sorted(n for n, _ in src_touching) == [110, 111, 113, 126]
        and stale_ok
        and integrated_ok,
        f"src-touching open PRs={sorted(n for n, _ in src_touching)} "
        f"(packet-adjudicated set expected [110, 111, 113, 126]); "
        f"#126 stale-branch blobs are historical main versions={stale_ok}; "
        f"#113/#111/#110 symbols+test modules in frozen main={integrated_ok}",
    )

    failed = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(failed)}/{len(results)} freeze-integrity probes PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
