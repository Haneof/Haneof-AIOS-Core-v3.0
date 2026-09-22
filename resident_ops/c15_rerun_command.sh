#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py ack --phase A --state "$RUN/release_state.json" --world-db "$RUN/private_world.sqlite" --sequence 11 --event-id c15rcc-011 --ingest-ref obs_c14_fixture_291beec37165eb34a35f8f85@1
