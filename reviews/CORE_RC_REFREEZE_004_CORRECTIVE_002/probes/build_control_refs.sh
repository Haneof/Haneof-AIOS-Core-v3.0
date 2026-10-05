#!/usr/bin/env bash
# Corrective-002 control-ref builder (read-only w.r.t. the candidate branch).
#
# Produces disposable control refs used for the RED-first reproduction and for
# the real hosted whole-run identity control:
#
#   red   : failed-candidate mechanics, only the branch literal substituted
#   green : corrected mechanics, only the branch literal substituted
#
# Both control workflows are derived from an existing workflow blob by a single
# literal substitution, so `git diff` between the candidate workflow and a
# control workflow must show exactly the branch-name lines. That diff is part of
# the recorded evidence.
#
# usage:
#   build_control_refs.sh red   <outdir>
#   build_control_refs.sh green <outdir>
set -euo pipefail

MODE="${1:?mode}"
OUT="${2:?outdir}"
REPO="${REPO:-$PWD}"
WF_PATH=".github/workflows/core-rc-refreeze-004-formal-gate.yml"

FAILED_CANDIDATE="2380121639865b1bd29176cf944f5a20afe4112d"
OLD_BRANCH="release/core-rc-refreeze-004-corrective-001-window26"
RED_BRANCH="review/w28-toctou-red-control"
GREEN_BRANCH="review/w28-toctou-green-control"

mkdir -p "$OUT"
export GIT_INDEX_FILE="$OUT/.control-index"

case "$MODE" in
  red)
    base="$FAILED_CANDIDATE"
    branch="$RED_BRANCH"
    marker_path="reviews/CORE_RC_REFREEZE_004/control/DRIFT_MARKER_W28_RED.md"
    source_branch="$OLD_BRANCH"
    ;;
  green)
    base="${GREEN_BASE:?GREEN_BASE required}"
    branch="$GREEN_BRANCH"
    marker_path="reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/control/DRIFT_MARKER_W28_GREEN.md"
    source_branch="${GREEN_SOURCE_BRANCH:?GREEN_SOURCE_BRANCH required}"
    ;;
  *)
    echo "unknown mode $MODE"; exit 2;;
esac

rm -f "$GIT_INDEX_FILE"

# --- control A: workflow with only the canonical-branch literal substituted ---
git cat-file blob "$base:$WF_PATH" | sed "s|$source_branch|$branch|g" > "$OUT/control-workflow.yml"

# the diff versus the source workflow must only touch branch-name lines
git cat-file blob "$base:$WF_PATH" | sed "s|$source_branch|__BRANCH__|g" > "$OUT/a.txt"
sed "s|$branch|__BRANCH__|g" < "$OUT/control-workflow.yml" > "$OUT/b.txt"
if ! diff -q "$OUT/a.txt" "$OUT/b.txt" >/dev/null; then
  echo "CONTROL_WORKFLOW_NOT_PURE_BRANCH_SUBSTITUTION"; exit 1
fi

git read-tree "$base"
wf_blob="$(git hash-object -w --stdin < "$OUT/control-workflow.yml")"
git update-index --add --cacheinfo "100644,$wf_blob,$WF_PATH"
tree_a="$(git write-tree)"
commit_a="$(git commit-tree "$tree_a" -p "$base" -m "review(w28): disposable ${MODE} whole-run identity control (A)")"

# --- control B: one append-only drift marker commit on the same branch ---
printf 'control=%s\nbranch=%s\nparent_a=%s\npurpose=deliberate canonical branch advance during the live control run\n' \
  "$MODE" "$branch" "$commit_a" > "$OUT/marker.md"
git read-tree "$commit_a"
marker_blob="$(git hash-object -w --stdin < "$OUT/marker.md")"
git update-index --add --cacheinfo "100644,$marker_blob,$marker_path"
tree_b="$(git write-tree)"
commit_b="$(git commit-tree "$tree_b" -p "$commit_a" -m "review(w28): deliberate canonical branch advance during live ${MODE} control (B)")"

rm -f "$GIT_INDEX_FILE"
{
  echo "mode=$MODE"
  echo "control_branch=$branch"
  echo "base=$base"
  echo "branch_literal_replaced=$source_branch->$branch"
  echo "control_workflow_blob=$wf_blob"
  echo "A_commit=$commit_a"
  echo "A_tree=$tree_a"
  echo "A_parent=$base"
  echo "B_commit=$commit_b"
  echo "B_tree=$tree_b"
  echo "B_parent=$commit_a"
  echo "marker_path=$marker_path"
} | tee "$OUT/control-identity.txt"

git diff --no-index --stat "$OUT/control-workflow.yml" <(git cat-file blob "$base:$WF_PATH") || true
