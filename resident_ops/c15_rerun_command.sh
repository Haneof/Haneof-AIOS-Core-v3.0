#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python - <<'PY'
import json,dataclasses
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore,WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime,ModelDirective
run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text()); now=datetime.fromisoformat(event["occurred_at"])
world=SQLiteWorldStore(run/"private_world.sqlite"); index=WorldSearchIndex(run/"world_index.sqlite",store=world); index.catch_up()
wakecp=run/"checkpoints"/"cursor-006-post-turn-wake.json"; trace=run/"capability_traces"/"cursor-006-user-turn.json"
class NeedDecision(Exception): pass
def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)
def mh(s):
    if s.wake_reason=="user_interaction":
        trace.write_text(json.dumps({"cursor":6,"runtime_snapshot":dump(s),"resident_response":"明白。production 旧索引删除不会凭模糊表述执行。需要删除时，我会先列出具体对象、影响和回滚办法，等你明确确认后再执行。"},ensure_ascii=False,indent=2,default=str))
        return ModelDirective(response="明白。production 旧索引删除不会凭模糊表述执行。需要删除时，我会先列出具体对象、影响和回滚办法，等你明确确认后再执行。")
    wakecp.write_text(json.dumps({"cursor":6,"timestamp":event["occurred_at"],"runtime_snapshot":dump(s)},ensure_ascii=False,indent=2,default=str))
    raise NeedDecision
rt=FusedTurnRuntime(store=world,index=index,model_handler=mh)
res=rt.run_turn(session_id="resident-a-rerun-20260922-sol-001",turn_index=4,user_input=event["resident_visible_payload"],occurred_at=now)
(run/"checkpoints"/"cursor-006-user-turn-result.json").write_text(json.dumps(dump(res),ensure_ascii=False,indent=2,default=str))
print("TURN",json.dumps(dump(res),ensure_ascii=False,default=str))
index.catch_up()
try:
    while True:
        w=rt.dispatch_next_pending_wake(now=now)
        if w is None:
            print("NO_MORE_DUE_WAKE"); break
        print("WAKE",json.dumps(dump(w),ensure_ascii=False,default=str))
except NeedDecision:
    print("NEED_DUE_WAKE_DECISION"); print(wakecp.read_text())
print("STATE",json.dumps({"world_revision":world.current_world_revision(),"watermark":index.watermark(),"lag":index.lag()}))
PY
