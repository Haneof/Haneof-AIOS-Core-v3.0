#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python - <<'PY'
import json, shutil
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore, WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime, ModelDirective, CapabilityCall
run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text())
world=SQLiteWorldStore(run/"private_world.sqlite")
index=WorldSearchIndex(run/"world_index.sqlite",store=world); index.catch_up()
now=datetime.fromisoformat(event["occurred_at"])
old=run/"checkpoints"/"pending_runtime_snapshot.json"
if old.exists(): shutil.copyfile(old,run/"checkpoints"/"cursor-001-review-r0.json")
out=run/"checkpoints"/"pending_runtime_snapshot.json"
class NeedDecision(Exception): pass
def dump(o):
    return o.model_dump(mode="json") if hasattr(o,"model_dump") else str(o)
def handler(snapshot):
    if snapshot.round_index==0 and not snapshot.capability_history:
        return ModelDirective(capability_calls=(CapabilityCall(name="read_periodic_review_anchors",arguments={"offset":0,"limit":20}),))
    out.write_text(json.dumps({"kind":"runtime_snapshot","cursor":1,"phase":"periodic_review","round":snapshot.round_index,"timestamp":event["occurred_at"],"snapshot":dump(snapshot)},ensure_ascii=False,indent=2))
    raise NeedDecision
rt=FusedTurnRuntime(store=world,index=index,model_handler=handler)
try:
    res=rt.run_periodic_review(now=now)
    print("REVIEW_RESULT",dump(res))
except NeedDecision:
    print("NEED_RESIDENT_DECISION")
    print(out.read_text())
print("WORLD_REVISION",world.current_world_revision())
print("INDEX",index.watermark(),index.lag())
PY
