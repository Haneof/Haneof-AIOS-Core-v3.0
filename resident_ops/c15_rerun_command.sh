#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
WORLD="$RUN/private_world.sqlite"
STATE="$RUN/release_state.json"
EVENT="$RUN/current-event.json"
SESSION="resident-a-rerun-20260922-sol-001"
if [ -e "$RUN" ]; then
  echo "BLOCKER: run directory already exists"; exit 21
fi
mkdir -p "$RUN"/{release_receipts,cursor_lifecycle,checkpoints,summary_requests,capability_traces,final}
cat > "$RUN/run_manifest.json" <<JSON
{
  "task_id": "C15-RCC-RES-A-RERUN-001",
  "starting_main": "1b0d478add02ca133965db84bff60d322749e02b",
  "resident_branch": "resident/c15-rcc-res-a-rerun-20260922-sol",
  "resident_session_id": "$SESSION",
  "phase": "A",
  "fresh_world": true,
  "old_world_copied": false
}
JSON
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py init --phase A --state "$STATE"
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py reveal --phase A --state "$STATE" > "$EVENT"
echo "=== CURRENT_EVENT_BEGIN ==="
cat "$EVENT"
echo "=== CURRENT_EVENT_END ==="
echo "WORLD_EXISTS=$(test -e "$WORLD" && echo yes || echo no)"
echo "SESSION=$SESSION"
