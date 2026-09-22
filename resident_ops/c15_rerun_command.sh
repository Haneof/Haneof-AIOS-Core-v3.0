#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py reveal --phase A --state "$RUN/release_state.json" > "$RUN/current-event.json"
cat "$RUN/current-event.json"
