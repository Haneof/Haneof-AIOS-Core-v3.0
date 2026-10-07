#!/usr/bin/env bash
set -uo pipefail

FROZEN_SHA="$1"
ACCEPTED_RELEASE_BASELINE="$2"
OUT_FILE="$3"

GUARD_SCRIPT="reviews/CORE_RC_REFREEZE_004_CORRECTIVE_003/probes/terminal_protected_drift_guard.sh"

echo "=== A. OLD MODEL RED ===" | tee -a "$OUT_FILE"
set +e
bash "$GUARD_SCRIPT" "$FROZEN_SHA" "$ACCEPTED_RELEASE_BASELINE" /tmp/old_red_out2.txt > /tmp/old_red_out.txt 2> /tmp/old_red_err.txt
exit_code=$?
set -e

cat /tmp/old_red_out2.txt /tmp/old_red_out.txt /tmp/old_red_err.txt | tee -a "$OUT_FILE"
echo "Exit code: $exit_code" | tee -a "$OUT_FILE"

if [ "$exit_code" -eq 0 ]; then
  echo "FAIL: Old model unexpectedly returned 0 (GREEN)." | tee -a "$OUT_FILE"
  exit 1
fi

if ! grep -qi "workflow" /tmp/old_red_out.txt /tmp/old_red_err.txt /tmp/old_red_out2.txt; then
  echo "FAIL: Old model did not explicitly complain about workflow drift." | tee -a "$OUT_FILE"
  exit 1
fi
echo "PASS: Old model correctly returned RED due to workflow drift." | tee -a "$OUT_FILE"

echo "=== B. NEW PRODUCT BASELINE GREEN ===" | tee -a "$OUT_FILE"
CHANGED_FILES=$(git diff --name-only "$FROZEN_SHA" "$ACCEPTED_RELEASE_BASELINE")
DRIFT_FOUND=0

check_drift() {
  local pattern="$1"
  if echo "$CHANGED_FILES" | grep -E "$pattern" > /dev/null; then
    echo "FAIL: Drift found in $pattern" | tee -a "$OUT_FILE"
    echo "$CHANGED_FILES" | grep -E "$pattern" | tee -a "$OUT_FILE"
    DRIFT_FOUND=1
  fi
}

check_drift "^src/aios_core/"
check_drift "^tests/"
check_drift "^pyproject\.toml$"

for pkg_file in setup.py setup.cfg MANIFEST.in poetry.lock uv.lock tox.ini; do
  if [ -f "$pkg_file" ]; then
    check_drift "^$pkg_file$"
  else
    echo "PACKAGE FILE $pkg_file: NOT_PRESENT" | tee -a "$OUT_FILE"
  fi
done

for pkg_pattern in "^requirements.*\.txt$" "^Pipfile.*" "^conda.*\.yml$" "^conda.*\.yaml$" "^environment.*\.yml$" "^environment.*\.yaml$"; do
  if git ls-files | grep -E "$pkg_pattern" > /dev/null; then
    check_drift "$pkg_pattern"
  else
    echo "PACKAGE PATTERN $pkg_pattern: NOT_PRESENT" | tee -a "$OUT_FILE"
  fi
done

if [ "$DRIFT_FOUND" -ne 0 ]; then
  echo "FAIL: Product/Package drift found between FROZEN_SHA and ACCEPTED_RELEASE_BASELINE." | tee -a "$OUT_FILE"
  exit 1
fi
echo "PASS: New product baseline GREEN (Zero drift in protected product/package surfaces)." | tee -a "$OUT_FILE"

echo "=== C. TERMINAL WORKFLOW DRIFT RED ===" | tee -a "$OUT_FILE"
TEMP_DIR=$(mktemp -d)
git worktree add --detach "$TEMP_DIR" "$ACCEPTED_RELEASE_BASELINE" > /dev/null 2>&1
pushd "$TEMP_DIR" > /dev/null
echo "# Temp mutation" >> .github/workflows/core-rc-refreeze-004-formal-gate.yml
git config user.name "Test"
git config user.email "test@example.com"
git commit -am "temp workflow mutation" > /dev/null
TEMP_MUTATED_COMMIT=$(git rev-parse HEAD)
popd > /dev/null

set +e
bash "$GUARD_SCRIPT" "$ACCEPTED_RELEASE_BASELINE" "$TEMP_MUTATED_COMMIT" /tmp/term_red_out2.txt > /tmp/term_red_out.txt 2> /tmp/term_red_err.txt
exit_code=$?
set -e

cat /tmp/term_red_out2.txt /tmp/term_red_out.txt /tmp/term_red_err.txt | tee -a "$OUT_FILE"
echo "Exit code: $exit_code" | tee -a "$OUT_FILE"

if [ "$exit_code" -eq 0 ]; then
  echo "FAIL: Terminal workflow drift unexpectedly returned 0 (GREEN)." | tee -a "$OUT_FILE"
  git worktree remove --force "$TEMP_DIR" > /dev/null 2>&1
  exit 1
fi
echo "PASS: Terminal workflow drift correctly returned RED." | tee -a "$OUT_FILE"

git worktree remove --force "$TEMP_DIR" > /dev/null 2>&1

echo "ALL PROBES PASSED." | tee -a "$OUT_FILE"
exit 0
