#!/bin/sh
set -u
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
RESULTS_ROOT="$SCRIPT_DIR/development-test-runs"
mkdir -p "$RESULTS_ROOT"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
RUN_DIR="$RESULTS_ROOT/$RUN_ID"
mkdir "$RUN_DIR"
export PYTHONDONTWRITEBYTECODE=1
python3 -B "$SCRIPT_DIR/run_development_tests.py" \
  --junit "$RUN_DIR/test-results.xml" \
  >"$RUN_DIR/stdout.txt" 2>"$RUN_DIR/stderr.txt"
TEST_EXIT=$?
python3 -B "$SCRIPT_DIR/record_development_run.py" "$TEST_EXIT" "$RUN_DIR"
RECORD_EXIT=$?
if [ "$RECORD_EXIT" -ne 0 ]; then
  exit "$RECORD_EXIT"
fi
exit "$TEST_EXIT"
