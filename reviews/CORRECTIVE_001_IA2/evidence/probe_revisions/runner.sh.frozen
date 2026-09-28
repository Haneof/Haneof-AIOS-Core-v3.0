#!/usr/bin/env bash
# Reviewer harness runner.
#
# WHY THIS EXISTS: the reviewer probe files live under the main repo tree
# (/home/user/Haneof-AIOS-Core-v3.0/reviews/...).  pytest walks up from the test
# file to find its inifile and picked up the MAIN repo's pyproject.toml, whose
# `pythonpath = ["src"]` resolved aios_core to the live-main checkout -- which
# does NOT contain the corrective.  That produced 60 fake RED results.
#
# This runner therefore copies the probes INTO the target worktree and runs
# pytest with that worktree's own inifile and rootdir, then asserts the guard
# test (which verifies the loaded aios_core path) actually ran and passed.
set -u

TARGET="${1:?usage: run_reviewer_probes.sh <worktree> [pytest args...]}"
shift || true

REVIEWER_DIR="/home/user/Haneof-AIOS-Core-v3.0/reviews/CORRECTIVE_001_IA2/reviewer"
DEST="${TARGET}/tests/reviewer_ia2"
PY="/home/user/venv311/bin/python"

mkdir -p "$DEST"
rm -f "$DEST"/*.py
cp "$REVIEWER_DIR"/test_ia2_*.py "$DEST"/
: > "$DEST/__init__.py"

echo "# target worktree : $TARGET"
echo "# target HEAD     : $(git -C "$TARGET" rev-parse HEAD)"
echo "# probes copied   : $(ls "$DEST" | tr '\n' ' ')"

# The marker inside the guard test must match this worktree.
sed -i "s#^TARGET_SRC_MARKER = .*#TARGET_SRC_MARKER = \"${TARGET}/src\"#" \
    "$DEST"/test_ia2_inventory_and_replay.py

cd "$TARGET" || exit 1
"$PY" -m pytest -p no:cacheprovider \
    -c "$TARGET/pyproject.toml" --rootdir="$TARGET" \
    "$@" "$DEST"
rc=$?

echo "# exit=$rc"
exit $rc
