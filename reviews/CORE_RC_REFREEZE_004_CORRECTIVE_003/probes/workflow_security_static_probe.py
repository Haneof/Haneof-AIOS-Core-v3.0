#!/usr/bin/env python3
"""Static security and carry-forward contract checks for the formal workflow."""
from __future__ import annotations

from pathlib import Path
import re
import sys


def job_block(text: str, name: str) -> str:
    lines = text.splitlines()
    marker = f"  {name}:"
    start = lines.index(marker)
    end = next((i for i in range(start + 1, len(lines))
                if re.match(r"^  [A-Za-z0-9_-]+:\s*$", lines[i])), len(lines))
    return "\n".join(lines[start:end])


def require(condition: bool, name: str, results: dict[str, bool]) -> None:
    results[name] = bool(condition)


def main() -> int:
    workflow_path = Path(sys.argv[1])
    text = workflow_path.read_text(encoding="utf-8")
    gate = job_block(text, "rc004-freeze-gate")
    control_gate = job_block(text, "rc004-postread-control-gate")
    publisher = job_block(text, "rc004-mandatory-pin-publisher")
    seal = job_block(text, "rc004-whole-run-identity-seal")
    control_seal = job_block(text, "rc004-postread-control-seal")
    results: dict[str, bool] = {}

    require("permissions:\n      contents: read\n      pull-requests: read" in gate and "contents: write" not in gate,
            "job_a_read_only", results)
    require("persist-credentials: false" in gate, "checkout_credentials_disabled", results)
    require("contents: read" in text.split("permissions:", 1)[1].split("concurrency:", 1)[0],
            "workflow_default_read_only", results)
    require("cancel-in-progress: true" in text and "core-rc-refreeze-004-${{ github.ref }}" in text,
            "same_ref_cancellation_enabled", results)

    publisher_permissions = re.search(r"(?ms)^    permissions:\n((?:^      [^\n]*\n)+)", publisher)
    scopes = [] if publisher_permissions is None else [
        line.strip() for line in publisher_permissions.group(1).splitlines() if line.strip()
    ]
    require(scopes == ["contents: write"], "publisher_only_comment_write_permission", results)
    require("actions/checkout" not in publisher and "uses:" not in publisher
            and "reviews/" not in publisher and "python " not in publisher,
            "publisher_no_checkout_or_candidate_script", results)
    require('"$api/commits/$GITHUB_SHA/comments"' in publisher,
            "publisher_only_commit_comment_endpoint", results)
    require("PIN_PUBLISH_TRANSPORT_FAILURE" in publisher and 'if [ "$code" != "201" ]; then' in publisher,
            "publisher_transport_and_http201_fail_closed", results)
    require("-X POST" in publisher and publisher.count("-X POST") == 1,
            "publisher_one_write_request", results)

    require("persist-credentials: false" in gate and "actions/checkout" in gate,
            "formal_job_a_checkout_contract", results)
    require("permissions:\n      contents: read\n      actions: read" in seal
            and "contents: write" not in seal and "actions: write" not in seal,
            "formal_seal_read_only", results)
    require("actions/checkout" not in seal and "actions/checkout" not in control_seal,
            "seals_have_no_checkout", results)
    for token in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA",
                  "CANONICAL_CORRECTIVE_BRANCH", "PIN_COMMENT_ID"):
        require(token in seal, f"formal_seal_binds_{token.lower()}", results)

    require("FINAL_SEAL_BRANCH_QUERY" in seal and "POST_READ_SETTLE_BARRIER_STARTED" in seal,
            "formal_last_ref_read_precedes_postread_barrier", results)
    require("actions/workflows/core-rc-refreeze-004-formal-gate.yml/runs" in seal
            and "POST_READ_SUPERSEDED_BY_NEWER_RUN" in seal,
            "formal_seal_checks_successor_run_lineage", results)
    require(seal.index("FINAL_SEAL_BRANCH_QUERY") < seal.index("POST_READ_SETTLE_BARRIER_STARTED")
            < seal.index("actions/workflows/core-rc-refreeze-004-formal-gate.yml/runs")
            < seal.index("WHOLE_RUN_IDENTITY_SEAL=PASS"),
            "formal_authority_ordering", results)
    require("PROVISIONAL_PENDING_FINAL_IDENTITY_SEAL" in publisher
            and "NOT_A_FORMAL_RELEASE_OR_ACCEPTANCE_PIN" in publisher,
            "pins_never_self_promote_to_authority", results)

    require("permissions:\n      contents: read" in control_gate and "contents: write" not in control_gate,
            "control_gate_read_only", results)
    require("permissions:\n      contents: read\n      actions: read" in control_seal,
            "control_seal_read_only", results)
    require("POSTREAD_CONTROL_LAST_CANONICAL_READ_COMPLETE" in control_seal
            and "sleep 180" in control_seal
            and "OLD_A_MUST_NOT_SEAL_SUCCESS" in control_seal,
            "hosted_control_barrier_after_last_ref_read", results)
    require("SUCCESSOR_B_POSTREAD_CONTROL=PASS" in control_seal
            and "actions/workflows/core-rc-refreeze-004-formal-gate.yml/runs" in control_seal,
            "hosted_control_requires_successor_b", results)

    require("terminal_protected_drift_guard.sh" in gate
            and "terminal_protected_drift_guard.sh" in job_block(text, "rc004-freeze-gate"),
            "formal_uses_shared_terminal_drift_shell", results)
    require("$RC004_LIVE_MAIN" in gate and "terminal_main" in gate,
            "terminal_guard_uses_initial_main_snapshot", results)
    require("terminal_protected_drift_controls.py" in gate,
            "formal_runs_positive_negative_drift_controls", results)
    require("reviews/CORE_RC_REFREEZE_004_CORRECTIVE_003/" in text,
            "evidence_paths_scoped_to_corrective_003", results)
    for marker in (
        "Fresh complete Core regression",
        "Fresh extract and run frozen Window 20 A/B and Window 17 reviewer probes",
        "Corrective-003 trust-root, alternate-mint, replay/conflict, supersession, and partial-commit checks",
        "Real SIGKILL and fresh-process recovery",
        "Clean non-editable wheel install and headless lifecycle",
        "Backup restore rebuild and trusted-return authority preservation",
        "Writer restart historical FIX current-time and no-second-truth-store spot checks",
        "Fresh C15 downstream compatibility debt classification",
        "Fresh open-PR contamination inventory",
    ):
        require(marker in gate, "carry_forward_" + marker.split()[0].lower(), results)
    require("C15_PYTEST_EXIT_NOT_ADMISSIBLE" in gate and "0|1)" in gate
            and "--junit \"$junit\"" in gate,
            "c15_exit_classification_and_junit_carry_forward", results)

    for key, value in results.items():
        print(f"{key}={'PASS' if value else 'FAIL'}")
    if not all(results.values()):
        print("WORKFLOW_SECURITY_STATIC=FAIL")
        return 1
    print("WORKFLOW_SECURITY_STATIC=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
