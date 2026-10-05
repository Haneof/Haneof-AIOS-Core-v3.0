#!/usr/bin/env python3
"""Build the Corrective-002 RC004 formal workflow from the frozen failed candidate.

Input:  .github/workflows/core-rc-refreeze-004-formal-gate.yml at
        failed candidate 2380121639865b1bd29176cf944f5a20afe4112d
Output: corrected workflow (Corrective-002 whole-run identity mechanics)

The corrective delta is deliberately explicit and minimal:
  1. canonical branch literal  -> release/core-rc-refreeze-004-corrective-002-window28
  2. concurrency.cancel-in-progress false -> true (server-side stale-run cancellation)
  3. runtime evidence path / artifact name -> CORRECTIVE_002
  4. candidate scope regex accepts reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/**
  5. write-capable jobs replaced by provisional-publish + fresh-identity + seal jobs
  6. one additive read-only regression step for the new identity mechanics

Nothing else changes; no step order, no gate semantics, no classifier semantics.
"""

from __future__ import annotations

import sys
from pathlib import Path

OLD_BRANCH = "release/core-rc-refreeze-004-corrective-001-window26"
NEW_BRANCH = "release/core-rc-refreeze-004-corrective-002-window28"
OLD_TASK = "CORE-RC-REFREEZE-004-CORRECTIVE-001"
NEW_TASK = "CORE-RC-REFREEZE-004-CORRECTIVE-002"
PUBLISHER_MARKER = "  rc004-mandatory-pin-publisher:"
NEW_PROBE_STEP = """      - name: Corrective-002 whole-run identity mechanics regressions
        shell: bash
        run: |
          set -euo pipefail
          WF="$GITHUB_WORKSPACE/.github/workflows/core-rc-refreeze-004-formal-gate.yml"
          "$RC004_VENV/bin/python" "$GITHUB_WORKSPACE/reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/probes/whole_run_identity_static_probe.py" "$WF" 2>&1 | tee "$RC004_OUT/whole-run-identity-static.txt"
          grep -q 'WHOLE_RUN_IDENTITY_STATIC=PASS' "$RC004_OUT/whole-run-identity-static.txt"
          "$RC004_VENV/bin/python" "$GITHUB_WORKSPACE/reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/probes/publisher_identity_fault_matrix.py" "$WF" 2>&1 | tee "$RC004_OUT/publisher-identity-fault-matrix.txt"
          grep -q 'PUBLISHER_IDENTITY_FAULT_MATRIX=PASS' "$RC004_OUT/publisher-identity-fault-matrix.txt"

"""
ANCHOR_AFTER = "          done\n\n      - name: Fresh complete Core regression\n"

REPLACEMENTS = [
    (f'      - "{OLD_BRANCH}"', f'      - "{NEW_BRANCH}"'),
    ("  cancel-in-progress: false", "  cancel-in-progress: true"),
    (
        f'  CANONICAL_CORRECTIVE_BRANCH: "{OLD_BRANCH}"',
        f'  CANONICAL_CORRECTIVE_BRANCH: "{NEW_BRANCH}"',
    ),
    (
        '  FORMAL_PYTEST: "8.4.2"',
        '  FORMAL_PYTEST: "8.4.2"\n  RC004_TASK_NAME: "CORE-RC-REFREEZE-004-CORRECTIVE-002"',
    ),
    (
        'OUT="$GITHUB_WORKSPACE/reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/ci-output"',
        'OUT="$GITHUB_WORKSPACE/reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/ci-output"',
    ),
    (
        'OUT="${RC004_OUT:-$GITHUB_WORKSPACE/reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/ci-output}"',
        'OUT="${RC004_OUT:-$GITHUB_WORKSPACE/reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/ci-output}"',
    ),
    (
        "          name: core-rc-refreeze-004-corrective-001-evidence",
        "          name: core-rc-refreeze-004-corrective-002-evidence",
    ),
    (
        "          path: reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/ci-output/**",
        "          path: reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/ci-output/**",
    ),
    (
        "|(reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/.*))$'",
        "|(reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/.*)|(reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/.*))$'",
    ),
]


def build(old_text: str, new_tail: str) -> str:
    text = old_text
    for old, new in REPLACEMENTS:
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"REPLACEMENT_MATCH_COUNT_{count}_FOR: {old!r}")
        text = text.replace(old, new)
    if text.count(PUBLISHER_MARKER) != 1:
        raise SystemExit("PUBLISHER_MARKER_NOT_UNIQUE")
    head = text[: text.index(PUBLISHER_MARKER)]
    if NEW_PROBE_STEP in head:
        raise SystemExit("PROBE_STEP_ALREADY_PRESENT")
    anchor_count = head.count(ANCHOR_AFTER)
    if anchor_count != 1:
        raise SystemExit(f"ANCHOR_COUNT_{anchor_count}")
    index = head.index(ANCHOR_AFTER) + len("          done\n\n")
    head = head[:index] + NEW_PROBE_STEP + head[index:]
    if "publisher_identity_fault_matrix" not in head:
        raise SystemExit("PROBE_STEP_INSERT_FAILED")
    # the 001 task literal may only survive in append-only carry-forward strings
    tail = new_tail.rstrip("\n") + "\n"
    if OLD_TASK in tail:
        raise SystemExit("OLD_TASK_LITERAL_IN_NEW_TAIL")
    if OLD_BRANCH in head + tail:
        raise SystemExit("OLD_BRANCH_LITERAL_SURVIVES")
    return head + tail


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit("usage: build_workflow.py <old_workflow> <new_tail> <out>")
    old = Path(sys.argv[1]).read_text(encoding="utf-8")
    tail = Path(sys.argv[2]).read_text(encoding="utf-8")
    out = build(old, tail)
    Path(sys.argv[3]).write_text(out, encoding="utf-8")
    print(f"BUILT bytes={len(out)} lines={out.count(chr(10))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
