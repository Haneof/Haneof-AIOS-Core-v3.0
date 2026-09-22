#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python reviews/internal_habitation/c15-rcc/v1/release/mechanical_ingest_adapter.py \
  --world-db "$RUN/private_world.sqlite" \
  --event-file "$RUN/current-event.json"
