#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python reviews/internal_habitation/c15-rcc/v1/release/canonical_conversation_ingest.py --world-db "$RUN/private_world.sqlite" --session-id resident-a-rerun-20260922-sol-001 --turn-index 7 --event-file "$RUN/current-event.json"
