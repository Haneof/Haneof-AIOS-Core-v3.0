#!/usr/bin/env bash
set -euo pipefail
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py --help
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py ack --help || true
python reviews/internal_habitation/c15-rcc/v1/release/mechanical_ingest_adapter.py --help
python reviews/internal_habitation/c15-rcc/v1/release/canonical_conversation_ingest.py --help
python - <<'PY'
import importlib.metadata as m
print("ENTRY_POINTS")
for ep in m.entry_points(group="console_scripts"):
    if "aios" in ep.name.lower():
        print(ep.name, ep.value)
PY
