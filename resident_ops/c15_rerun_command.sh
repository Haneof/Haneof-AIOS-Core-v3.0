#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python - <<'PY'
import json, dataclasses
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore, WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime, ModelDirective

run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text())
world=SQLiteWorldStore(run/"private_world.sqlite")
index=WorldSearchIndex(run/"world_index.sqlite",store=world); index.catch_up()
now=datetime.fromisoformat(event["occurred_at"])
turn_trace=run/"capability_traces"/"cursor-001-user-turn.json"
wake_cp=run/"checkpoints"/"cursor-001-post-turn-wake.json"
turn_trace.parent.mkdir(parents=True,exist_ok=True); wake_cp.parent.mkdir(parents=True,exist_ok=True)

class NeedDecision(Exception): pass
def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)

def handler(snapshot):
    if snapshot.wake_reason == "user_interaction":
        turn_trace.write_text(json.dumps({
            "cursor":1,
            "phase":"user_turn",
            "runtime_snapshot":dump(snapshot),
            "resident_directive":{
                "response":"明白。我会按这个分工推进：日常工程细节我持续跟进，给你结果和关键风险；涉及生产影响、删除数据或费用的事项，我会单独提出来，不和日常事项混在一起处理。"
            }
        },ensure_ascii=False,indent=2,default=str))
        return ModelDirective(response="明白。我会按这个分工推进：日常工程细节我持续跟进，给你结果和关键风险；涉及生产影响、删除数据或费用的事项，我会单独提出来，不和日常事项混在一起处理。")
    wake_cp.write_text(json.dumps({
        "cursor":1,
        "phase":"post_user_turn_due_wake",
        "timestamp":event["occurred_at"],
        "runtime_snapshot":dump(snapshot)
    },ensure_ascii=False,indent=2,default=str))
    raise NeedDecision("due wake decision required")

rt=FusedTurnRuntime(store=world,index=index,model_handler=handler)
result=rt.run_turn(
    session_id="resident-a-rerun-20260922-sol-001",
    turn_index=1,
    user_input=event["resident_visible_payload"],
    occurred_at=now
)
(run/"checkpoints"/"cursor-001-user-turn-result.json").write_text(json.dumps(dump(result),ensure_ascii=False,indent=2,default=str))
print("TURN_RESULT",json.dumps(dump(result),ensure_ascii=False,default=str))
index.catch_up()
print("AFTER_TURN",json.dumps({"world_revision":world.current_world_revision(),"index_watermark":index.watermark(),"index_lag":index.lag()}))
try:
    while True:
        w=rt.dispatch_next_pending_wake(now=now)
        if w is None:
            print("NO_MORE_DUE_WAKE")
            break
        print("WAKE_RESULT",json.dumps(dump(w),ensure_ascii=False,default=str))
except NeedDecision as e:
    print("NEED_RESIDENT_DECISION",str(e))
    print(wake_cp.read_text())
PY
