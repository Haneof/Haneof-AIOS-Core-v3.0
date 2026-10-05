#!/usr/bin/env python3
"""Corrective-002 whole-run identity static regression probe.

Read-only regression guard for the RC004 whole-run identity mechanics.

This probe is deliberately *only* a regression guard. It cannot prove the
inter-job TOCTOU closure: the binding proof is the real hosted GitHub Actions
A -> B control recorded in REAL_GITHUB_TOCTOU_CONTROL.md.

What it does prove mechanically:
  * both write-capable jobs carry the identical extracted identity core;
  * the publisher verifies fresh canonical identity BEFORE the POST and again
    AFTER it, and invalidates the published pin on post-publish drift;
  * the seal job depends on BOTH the gate and the publisher, re-verifies
    identity before and after a bounded settle hold, seals, then re-verifies
    after the seal write and invalidates on drift;
  * the final job in the workflow is the identity seal job (so the workflow can
    only be overall SUCCESS through the seal job);
  * no write-capable job checks out the repository or executes candidate code;
  * the reader job stays read-only and the 201-only publication contract is
    preserved.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

BEGIN = "# >>> RC004_WHOLE_RUN_IDENTITY_CORE_BEGIN"
END = "# <<< RC004_WHOLE_RUN_IDENTITY_CORE_END"


def cut(text: str, start: str, end: str | None) -> str:
    a = text.index(start)
    b = len(text) if end is None else text.index(end)
    return text[a:b]


def core_blocks(text: str) -> list[str]:
    blocks = []
    for part in text.split(BEGIN)[1:]:
        blocks.append(part[: part.index(END)])
    return blocks


def main() -> int:
    workflow = Path(sys.argv[1]).read_text(encoding="utf-8")
    checks: dict[str, bool] = {}

    gate = cut(workflow, "  rc004-freeze-gate:", "  rc004-mandatory-pin-publisher:")
    write_side = cut(workflow, "  rc004-mandatory-pin-publisher:", None)
    publisher = cut(workflow, "  rc004-mandatory-pin-publisher:", "  rc004-whole-run-identity-seal:")
    seal = cut(workflow, "  rc004-whole-run-identity-seal:", None)
    concurrency = cut(workflow, "concurrency:", "env:")

    checks["concurrency_group_is_branch_scoped"] = (
        "group: core-rc-refreeze-004-${{ github.ref }}" in concurrency
    )
    checks["concurrency_cancels_in_progress"] = "cancel-in-progress: true" in concurrency
    checks["reader_job_read_only"] = (
        "      contents: read\n      pull-requests: read" in gate
        and "contents: write" not in gate
    )
    checks["reader_job_no_persisted_credential"] = "persist-credentials: false" in gate
    checks["terminal_remote_equality_before_artifact"] = gate.index(
        "TERMINAL_REMOTE_HEAD_MISMATCH"
    ) < gate.index("actions/upload-artifact")

    blocks = core_blocks(workflow)
    checks["identity_core_present_in_both_write_jobs"] = len(blocks) == 2
    checks["identity_core_identical_in_both_write_jobs"] = len(blocks) == 2 and blocks[0] == blocks[1]

    checks["publisher_fresh_check_before_post"] = publisher.index(
        "rc004_whole_run_identity_require pre_publish"
    ) < publisher.index("-X POST")
    checks["publisher_fresh_check_after_post"] = "rc004_whole_run_identity_require post_publish" in publisher
    pub_flow = publisher.split(END)[-1]
    checks["publisher_invalidates_on_post_publish_drift"] = (
        'rc004_whole_run_identity_require post_publish' in pub_flow
        and 'rc004_invalidate_pin "$pin_id"' in pub_flow
        and pub_flow.index('rc004_whole_run_identity_require post_publish')
        < pub_flow.index('rc004_invalidate_pin "$pin_id"')
    )
    checks["publisher_post_contract_201_only"] = (
        'if [ "$code" != "201" ]; then' in publisher and "exit 1" in publisher
    )
    checks["publisher_pin_is_provisional_only"] = (
        "PROVISIONAL_PENDING_IDENTITY_SEAL" in pub_flow
        and "rc004_seal_pin" not in pub_flow
    )

    checks["seal_job_depends_on_gate_and_publisher"] = (
        "needs: [rc004-freeze-gate, rc004-mandatory-pin-publisher]" in seal
    )
    checks["seal_job_requires_both_success"] = (
        "needs.rc004-freeze-gate.result == 'success' && needs.rc004-mandatory-pin-publisher.result == 'success'"
        in seal
    )
    checks["seal_job_validates_publisher_result"] = (
        "rc004_read_pin_body" in seal
        and "SEAL_PUBLISHER_PIN_SHA_MISMATCH" in seal
        and "SEAL_PUBLISHER_PIN_RUN_MISMATCH" in seal
    )
    checks["seal_holds_between_identity_checks"] = (
        seal.index("rc004_whole_run_identity_require seal_pre_hold")
        < seal.index("sleep 30")
        < seal.index("rc004_whole_run_identity_require seal_post_hold")
    )
    seal_flow = seal.split(END)[-1]
    checks["seal_write_is_sandwiched_by_identity_checks"] = (
        seal_flow.index("rc004_whole_run_identity_require seal_post_hold")
        < seal_flow.index('rc004_seal_pin "$PIN_COMMENT_ID"')
        < seal_flow.index("rc004_whole_run_identity_require seal_post_write")
    )
    checks["seal_invalidates_on_post_seal_drift"] = (
        "SEALED_PIN_INVALIDATED_AFTER_BRANCH_DRIFT" in seal_flow
        and seal_flow.index('rc004_invalidate_pin "$PIN_COMMENT_ID"')
        > seal_flow.index('rc004_seal_pin "$PIN_COMMENT_ID"')
    )
    checks["seal_pin_authority_is_conditional"] = (
        "NON_AUTHORITATIVE_UNTIL_IDENTITY_SEALED_AND_OVERALL_RUN_SUCCESS" in blocks[-1]
        and "ANY_CANONICAL_BRANCH_DRIFT_MAKES_A_STALE_RUN_NON_AUTHORITATIVE" in blocks[-1]
    )

    jobs = re.findall(r"^  ([a-z0-9-]+):$", workflow, re.M)
    checks["identity_seal_is_final_job"] = jobs[-1] == "rc004-whole-run-identity-seal"

    checks["write_side_has_no_checkout"] = "actions/checkout" not in write_side
    checks["write_side_has_no_candidate_code"] = (
        "reviews/" not in write_side and "python " not in write_side
    )
    checks["write_side_write_permission_is_contents_only"] = (
        "permissions:\n      contents: write" in write_side
        and "pull-requests: write" not in write_side
        and "actions: write" not in write_side
    )
    checks["write_side_has_no_mutating_api_calls"] = not re.search(
        r"-X\s+(PUT|DELETE)", write_side
    ) and not re.search(r"/git/refs|/releases|/pulls|/merges|/dispatches|/contents/", write_side)
    checks["no_credential_persisted_anywhere"] = "persist-credentials: false" in gate and (
        "persist-credentials: true" not in workflow
    )

    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "identity_core.sh"
        script.write_text("set -euo pipefail\n" + blocks[0], encoding="utf-8")
        syntax = subprocess.run(
            ["bash", "-n", str(script)], capture_output=True, text=True
        )
        checks["identity_core_shell_syntax"] = syntax.returncode == 0

    print("checks:")
    for name, ok in checks.items():
        print(f"  {name}={str(bool(ok)).lower()}")
    failures = [name for name, ok in checks.items() if not ok]
    if failures:
        print("WHOLE_RUN_IDENTITY_STATIC=FAIL")
        for name in failures:
            print(f"failing_check={name}")
        return 1
    print(f"WHOLE_RUN_IDENTITY_STATIC=PASS checks={len(checks)}")
    print("NOTE=static guard only; binding proof is the hosted A->B control")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
