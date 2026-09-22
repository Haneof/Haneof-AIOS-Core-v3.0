#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py ack \
  --phase A --state "$RUN/release_state.json" --world-db "$RUN/private_world.sqlite" \
  --sequence 10 --event-id c15rcc-010 --ingest-ref obs_conv_user_0b72a06629de42e21a3fec57@1 \
  --conversation-session-id resident-a-rerun-20260922-sol-001 --conversation-turn-index 6
