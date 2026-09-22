#!/usr/bin/env bash
set -euo pipefail
python reviews/internal_habitation/c15-rcc/v1/release/mechanical_ingest_adapter.py --help
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py ack --help
