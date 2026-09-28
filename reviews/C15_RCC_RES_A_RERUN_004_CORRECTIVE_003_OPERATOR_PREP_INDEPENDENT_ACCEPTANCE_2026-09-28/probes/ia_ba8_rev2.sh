#!/usr/bin/env bash
# BA8 rev2 — probe-bug correction. rev1 used `git get-tar-commit-id < <(gzip -dc ...)`
# inside ia_bootstrap_rc_attacks.sh and captured an empty string (reviewer probe defect;
# rev1 source + output preserved). rev2 uses a plain pipe. Expected: equal to PY_COMMIT_SHA pin.
BOOT=/tmp/ia/clone/reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP/bootstrap/bootstrap_runtime.sh
pin=$(grep '^PY_COMMIT_SHA=' "$BOOT" | cut -d'"' -f2)
tcid=$(gzip -dc /tmp/ia/rt/src/cpython-3.12.14.tar.gz | git get-tar-commit-id)
[ "$tcid" = "$pin" ] && s=PASS || s=RED
echo "BA8rev2 | expected=$pin | observed=$tcid | $s"
