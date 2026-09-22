#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
WORLD="$RUN/private_world.sqlite"; STATE="$RUN/release_state.json"; EVENT="$RUN/current-event.json"
SESSION="resident-a-rerun-20260922-sol-001"
mkdir -p "$RUN"/{release_receipts,cursor_lifecycle,checkpoints,capability_traces}
ING="$RUN/release_receipts/cursor-003-ingest.json"; ACK="$RUN/release_receipts/cursor-003-ack.json"
python reviews/internal_habitation/c15-rcc/v1/release/canonical_conversation_ingest.py   --world-db "$WORLD" --session-id "$SESSION" --turn-index 2 --event-file "$EVENT" | tee "$ING"
REF="$(python -c 'import json,sys;print(json.load(open(sys.argv[1]))["ingest_ref"])' "$ING")"
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py ack   --phase A --state "$STATE" --world-db "$WORLD" --sequence 3 --event-id c15rcc-003 --ingest-ref "$REF"   --conversation-session-id "$SESSION" --conversation-turn-index 2 | tee "$ACK"
cat > "$RUN/cursor_lifecycle/cursor-003.json" <<JSON
{"cursor":3,"event_id":"c15rcc-003","ingest_ref":"$REF","conversation_session_id":"$SESSION","turn_index":2,"acked":true}
JSON
python - <<'PY'
import json,dataclasses
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore,WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime
run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text())
world=SQLiteWorldStore(run/"private_world.sqlite"); index=WorldSearchIndex(run/"world_index.sqlite",store=world); caught=index.catch_up()
now=datetime.fromisoformat(event["occurred_at"]); cp=run/"checkpoints"/"cursor-003-pending-decision.json"
class NeedDecision(Exception): pass
def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)
def save(kind,obj):
    cp.write_text(json.dumps({"cursor":3,"timestamp":event["occurred_at"],"kind":kind,"payload":dump(obj)},ensure_ascii=False,indent=2,default=str)); raise NeedDecision(kind)
def mh(s): save("runtime_snapshot",s)
def dh(x): save("dimension_summary_input",x)
def rh(x): save("round_summary_input",x)
rt=FusedTurnRuntime(store=world,index=index,model_handler=mh,dimension_summary_handler=dh,round_summary_handler=rh)
print("INDEX",json.dumps({"caught":caught,"watermark":index.watermark(),"lag":index.lag(),"world_revision":world.current_world_revision()}))
try:
    print("SUMMARY",dump(rt.run_due_dimension_summaries(now=now)))
    while True:
        w=rt.dispatch_next_pending_wake(now=now)
        if w is None: break
        print("WAKE",dump(w))
    print("REVIEW",dump(rt.run_periodic_review(now=now)))
    rt.run_turn(session_id="resident-a-rerun-20260922-sol-001",turn_index=2,user_input=event["resident_visible_payload"],occurred_at=now)
except NeedDecision as e:
    print("NEED_RESIDENT_DECISION",e)
    print(cp.read_text())
PY
