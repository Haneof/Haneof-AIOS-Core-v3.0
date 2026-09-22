#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python - <<'PY'
import json
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore, WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime

run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text())
world=SQLiteWorldStore(run/"private_world.sqlite")
index=WorldSearchIndex(run/"world_index.sqlite", store=world)
indexed=index.catch_up()
now=datetime.fromisoformat(event["occurred_at"])
cp=run/"checkpoints"/"pending_runtime_snapshot.json"
cp.parent.mkdir(parents=True,exist_ok=True)
class NeedDecision(Exception): pass

def dump_obj(obj):
    if hasattr(obj,"model_dump"): return obj.model_dump(mode="json")
    if hasattr(obj,"__dict__"): return obj.__dict__
    return str(obj)

def model_handler(snapshot):
    cp.write_text(json.dumps({"kind":"runtime_snapshot","cursor":1,"timestamp":event["occurred_at"],"snapshot":dump_obj(snapshot)},ensure_ascii=False,indent=2))
    raise NeedDecision("resident decision required")

def dim_handler(inp):
    cp.write_text(json.dumps({"kind":"dimension_summary_input","cursor":1,"timestamp":event["occurred_at"],"input":dump_obj(inp)},ensure_ascii=False,indent=2))
    raise NeedDecision("resident summary required")

def round_handler(inp):
    cp.write_text(json.dumps({"kind":"round_summary_input","cursor":1,"timestamp":event["occurred_at"],"input":dump_obj(inp)},ensure_ascii=False,indent=2))
    raise NeedDecision("resident round summary required")

rt=FusedTurnRuntime(store=world,index=index,model_handler=model_handler,dimension_summary_handler=dim_handler,round_summary_handler=round_handler)
print("INDEX",json.dumps({"caught_up_rows":indexed,"watermark":index.watermark(),"lag":index.lag(),"world_revision":world.current_world_revision()}))
try:
    s=rt.run_due_dimension_summaries(now=now)
    print("DUE_SUMMARY_RESULT",dump_obj(s))
    while True:
        w=rt.dispatch_next_pending_wake(now=now)
        if w is None: break
        print("WAKE_RESULT",dump_obj(w))
    rv=rt.run_periodic_review(now=now)
    print("REVIEW_RESULT",dump_obj(rv))
    res=rt.run_turn(
        session_id="resident-a-rerun-20260922-sol-001",
        turn_index=1,
        user_input=event["resident_visible_payload"],
        occurred_at=now
    )
    print("TURN_RESULT",dump_obj(res))
except NeedDecision as e:
    print("NEED_RESIDENT_DECISION",str(e))
    print(cp.read_text())
PY
