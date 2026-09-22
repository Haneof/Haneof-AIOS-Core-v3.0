#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
WORLD="$RUN/private_world.sqlite"
STATE="$RUN/release_state.json"
EVENT="$RUN/current-event.json"
SESSION="resident-a-rerun-20260922-sol-001"
mkdir -p "$RUN"/{release_receipts,cursor_lifecycle,checkpoints,summary_requests,capability_traces,final}
RECEIPT="$RUN/release_receipts/cursor-001-ingest.json"
ACK="$RUN/release_receipts/cursor-001-ack.json"
python reviews/internal_habitation/c15-rcc/v1/release/canonical_conversation_ingest.py \
  --world-db "$WORLD" --session-id "$SESSION" --turn-index 1 --event-file "$EVENT" | tee "$RECEIPT"
REF="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["ingest_ref"])' "$RECEIPT")"
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py ack \
  --phase A --state "$STATE" --world-db "$WORLD" \
  --sequence 1 --event-id c15rcc-001 --ingest-ref "$REF" \
  --conversation-session-id "$SESSION" --conversation-turn-index 1 | tee "$ACK"
cat > "$RUN/cursor_lifecycle/cursor-001.json" <<JSON
{
  "cursor": 1,
  "event_id": "c15rcc-001",
  "ingest_ref": "$REF",
  "conversation_session_id": "$SESSION",
  "turn_index": 1,
  "ingest_retry_reason": "initial receipt directory was not materialized by git; canonical ingest retried idempotently",
  "acked": true
}
JSON
echo "=== RECEIPT ==="; cat "$RECEIPT"
echo "=== ACK ==="; cat "$ACK"
echo "=== STATE ==="; cat "$STATE"
echo "=== PACKAGE_SURFACE ==="
python - <<'PY'
import aios_core, pkgutil
for m in sorted(x.name for x in pkgutil.iter_modules(aios_core.__path__)):
    if any(k in m.lower() for k in ("runtime","world","search","summary","wake","review","cogn","turn","index")):
        print(m)
PY
