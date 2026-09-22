#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py ack   --phase A   --state "$RUN/release_state.json"   --world-db "$RUN/private_world.sqlite"   --sequence 12   --event-id c15rcc-012   --ingest-ref obs_conv_user_8fa0a1954522deb621832218@1   --conversation-session-id resident-a-rerun-20260922-sol-001   --conversation-turn-index 7
