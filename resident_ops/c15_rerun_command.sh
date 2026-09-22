#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python - <<'PY'
import json,dataclasses
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore,WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime
run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text())
now=datetime.fromisoformat(event["occurred_at"])
world=SQLiteWorldStore(run/"private_world.sqlite")
index=WorldSearchIndex(run/"world_index.sqlite",store=world)
index.catch_up()
class StopHere(Exception): pass
def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)
def handler(s):
    p=run/"checkpoints"/"cursor-009-pending-decision.json"
    p.write_text(json.dumps({"cursor":9,"timestamp":event["occurred_at"],"snapshot":dump(s)},ensure_ascii=False,indent=2,default=str))
    raise StopHere
rt=FusedTurnRuntime(store=world,index=index,model_handler=handler)
try:
    while True:
        w=rt.dispatch_next_pending_wake(now=now)
        if w is None: break
        print("WAKE",json.dumps(dump(w),ensure_ascii=False,default=str))
    print("REVIEW",json.dumps(dump(rt.run_periodic_review(now=now)),ensure_ascii=False,default=str))
    index.catch_up()
    print("NO_DECISION_DUE")
except StopHere:
    print("NEED_DECISION")
    print((run/"checkpoints"/"cursor-009-pending-decision.json").read_text())
print("STATE",world.current_world_revision(),index.watermark(),index.lag())
PY
