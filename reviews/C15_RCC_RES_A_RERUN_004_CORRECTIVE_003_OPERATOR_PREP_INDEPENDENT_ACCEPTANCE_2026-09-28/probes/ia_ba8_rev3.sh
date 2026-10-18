#!/usr/bin/env bash
# BA8 rev3 — second probe-bug correction. rev1 (process substitution) and rev2
# (pipe inside command substitution) both captured an empty commit id although an
# interactive pipe prints it; the pipe read is unreliable in this sandbox. rev3
# decompresses the pax header block to a regular file first. Expected: == PY_COMMIT_SHA.
BOOT=/tmp/ia/clone/reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP/bootstrap/bootstrap_runtime.sh
pin=$(grep '^PY_COMMIT_SHA=' "$BOOT" | cut -d'"' -f2)
gzip -dc /tmp/ia/rt/src/cpython-3.12.14.tar.gz 2>/dev/null | head -c 4096 > /tmp/ia/cpython_header.tar
tcid=$(git get-tar-commit-id < /tmp/ia/cpython_header.tar)
[ "$tcid" = "$pin" ] && s=PASS || s=RED
echo "BA8rev3 | expected=$pin | observed=$tcid | $s"
