#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
WORLD="$RUN/private_world.sqlite"
STATE="$RUN/release_state.json"
EVENT="$RUN/current-event.json"
mkdir -p "$RUN"/{release_receipts,cursor_lifecycle,checkpoints,summary_requests,capability_traces}
INGEST="$RUN/release_receipts/cursor-002-ingest.json"
ACK="$RUN/release_receipts/cursor-002-ack.json"
python reviews/internal_habitation/c15-rcc/v1/release/mechanical_ingest_adapter.py --world-db "$WORLD" --event-file "$EVENT" | tee "$INGEST"
REF="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["ingest_ref"])' "$INGEST")"
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py ack \
  --phase A --state "$STATE" --world-db "$WORLD" \
  --sequence 2 --event-id c15rcc-002 --ingest-ref "$REF" | tee "$ACK"
cat > "$RUN/cursor_lifecycle/cursor-002.json" <<JSON
{"cursor":2,"event_id":"c15rcc-002","ingest_ref":"$REF","acked":true}
JSON
python - <<'PY'
import json, dataclasses
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore, WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime

run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text())
world=SQLiteWorldStore(run/"private_world.sqlite")
index=WorldSearchIndex(run/"world_index.sqlite",store=world)
caught=index.catch_up()
now=datetime.fromisoformat(event["occurred_at"])
cp=run/"checkpoints"/"cursor-002-pending-decision.json"
class NeedDecision(Exception): pass
def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)
def save(kind,obj):
    cp.write_text(json.dumps({"cursor":2,"timestamp":event["occurred_at"],"kind":kind,"payload":dump(obj)},ensure_ascii=False,indent=2,default=str))
    raise NeedDecision(kind)
def model_handler(snapshot): save("runtime_snapshot",snapshot)
def dimension_summary_handler(inp): save("dimension_summary_input",inp)
def round_summary_handler(inp): save("round_summary_input",inp)
rt=FusedTurnRuntime(store=world,index=index,model_handler=model_handler,dimension_summary_handler=dimension_summary_handler,round_summary_handler=round_summary_handler)
print("INDEX_BEFORE",json.dumps({"caught":caught,"watermark":index.watermark(),"lag":index.lag(),"world_revision":world.current_world_revision()}))
try:
    sr=rt.run_due_dimension_summaries(now=now)
    print("SUMMARY_RESULT",json.dumps(dump(sr),ensure_ascii=False,default=str))
    while True:
        w=rt.dispatch_next_pending_wake(now=now)
        if w is None: break
        print("WAKE_RESULT",json.dumps(dump(w),ensure_ascii=False,default=str))
    rv=rt.run_periodic_review(now=now)
    print("REVIEW_RESULT",json.dumps(dump(rv),ensure_ascii=False,default=str))
    print("NO_SEMANTIC_WORK")
except NeedDecision as e:
    print("NEED_RESIDENT_DECISION",str(e))
    print(cp.read_text())
print("FINAL_MECH",json.dumps({"world_revision":world.current_world_revision(),"index_watermark":index.watermark(),"index_lag":index.lag()}))
PY
