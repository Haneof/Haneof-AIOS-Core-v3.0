#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
STATE="$RUN/release_state.json"
EVENT="$RUN/current-event.json"
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py reveal --phase A --state "$STATE" > "$EVENT"
echo "=== CURRENT_EVENT_BEGIN ==="
cat "$EVENT"
echo
echo "=== CURRENT_EVENT_END ==="
