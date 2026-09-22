#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
WORLD="$RUN/private_world.sqlite"
EVENT="$RUN/current-event.json"
SESSION="resident-a-rerun-20260922-sol-001"
RECEIPT="$RUN/release_receipts/cursor-001-ingest.json"
python reviews/internal_habitation/c15-rcc/v1/release/canonical_conversation_ingest.py \
  --world-db "$WORLD" \
  --session-id "$SESSION" \
  --turn-index 1 \
  --event-file "$EVENT" | tee "$RECEIPT"
echo "=== RECEIPT ==="
cat "$RECEIPT"
echo "=== PACKAGE_SURFACE ==="
python - <<'PY'
import aios_core, pkgutil
print("aios_core", getattr(aios_core, "__file__", ""))
for m in sorted(x.name for x in pkgutil.iter_modules(aios_core.__path__)):
    if any(k in m.lower() for k in ("runtime","world","search","summary","wake","review","cogn","turn")):
        print(m)
PY
