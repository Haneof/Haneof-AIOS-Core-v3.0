import json, dataclasses
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore, WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime, ModelDirective, CapabilityCall

run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text())
now=datetime.fromisoformat(event["occurred_at"])
world=SQLiteWorldStore(run/"private_world.sqlite")
index=WorldSearchIndex(run/"world_index.sqlite",store=world); index.catch_up()
def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)
def handler(s):
    if s.wake_reason!="periodic_review":
        return ModelDirective(silence=True)
    if s.round_index==0:
        return ModelDirective(capability_calls=(CapabilityCall(name="read_periodic_review_anchors",arguments={"offset":0,"limit":20}),))
    (run/"checkpoints"/"cursor-013-review-final.json").write_text(json.dumps({
        "cursor":13,
        "timestamp":event["occurred_at"],
        "decision":"silence",
        "semantic_note":"Retain existing cognition. Final runbook evidence is DRAFT only; no review, execution, Outcome, or user acceptance supports a success/strategy update.",
        "snapshot":dump(s)
    },ensure_ascii=False,indent=2,default=str))
    return ModelDirective(silence=True)
rt=FusedTurnRuntime(store=world,index=index,model_handler=handler)
while True:
    w=rt.dispatch_next_pending_wake(now=now)
    if w is None: break
    print("WAKE",json.dumps(dump(w),ensure_ascii=False,default=str))
print("REVIEW",json.dumps(dump(rt.run_periodic_review(now=now)),ensure_ascii=False,default=str))
index.catch_up()
print("STATE",world.current_world_revision(),index.watermark(),index.lag())
