#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python - <<'PY'
import json, dataclasses
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore, WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime, ModelDirective, CapabilityCall

run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text()); now=datetime.fromisoformat(event["occurred_at"])
world=SQLiteWorldStore(run/"private_world.sqlite"); index=WorldSearchIndex(run/"world_index.sqlite",store=world); index.catch_up()
cp=run/"checkpoints"/"cursor-006-review-r1.json"
class NeedDecision(Exception): pass
def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)
def mh(s):
    if s.wake_reason=="periodic_review" and s.round_index==0 and not s.capability_history:
        return ModelDirective(capability_calls=(
            CapabilityCall(name="read_periodic_review_anchors",arguments={"offset":0,"limit":40}),
            CapabilityCall(name="read_ai_world",arguments={"domains":["user_understanding","relationship","strategy","calibration"],"limit":20})
        ))
    cp.write_text(json.dumps({"cursor":6,"timestamp":event["occurred_at"],"runtime_snapshot":dump(s)},ensure_ascii=False,indent=2,default=str))
    raise NeedDecision
rt=FusedTurnRuntime(store=world,index=index,model_handler=mh)
try:
    rv=rt.run_periodic_review(now=now)
    print("REVIEW_RESULT",json.dumps(dump(rv),ensure_ascii=False,default=str))
except NeedDecision:
    print("NEED_RESIDENT_DECISION")
    print(cp.read_text())
PY
