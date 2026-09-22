#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python - <<'PY'
import json,dataclasses
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore,WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime,ModelDirective,CapabilityCall
run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text()); now=datetime.fromisoformat(event["occurred_at"])
world=SQLiteWorldStore(run/"private_world.sqlite"); index=WorldSearchIndex(run/"world_index.sqlite",store=world); index.catch_up()
trace=run/"capability_traces"/"cursor-005-user-turn.json"; wakecp=run/"checkpoints"/"cursor-005-post-turn-wake.json"
class NeedDecision(Exception): pass
def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)
def handler(s):
    if s.wake_reason=="user_interaction":
        if s.round_index==0:
            return ModelDirective(capability_calls=(
                CapabilityCall(name="record_communication_experience",arguments={
                    "scenario":"Atlas staging 低风险实现收尾",
                    "style":"低风险实现自主推进，不逐步请求确认；完成后汇报结果与关键风险；高风险边界集中提请决定",
                    "tone":"concise_result_and_risk",
                    "user_reaction":"accepted",
                    "evidence_refs":[
                        {"object_id":"obs_conv_ai_46efd80fa2169a69d043503b","revision":1},
                        {"object_id":"obs_c14_fixture_5d4dfcf42055c00135a78a54","revision":1},
                        {"object_id":"obs_conv_user_f34226f9e0d4064df40603ca","revision":1}
                    ],
                    "applicable_conditions":{"risk":"low","work_class":"implementation","exception_boundaries":["production","deletion","cost"]}
                }),
                CapabilityCall(name="commit_ai_world_claim",arguments={
                    "domain":"strategy",
                    "statement":"对于类似低风险实现工作，默认采用这样的协作节奏：Resident 自主推进，不逐步打断用户；完成后汇报结果与关键风险；真正涉及生产影响、删除数据或费用的事项再集中列出供用户决定。",
                    "evidence_refs":[
                        {"object_id":"obs_conv_user_f39b955edaf19ae48a8cf497","revision":1},
                        {"object_id":"obs_c14_fixture_5d4dfcf42055c00135a78a54","revision":1},
                        {"object_id":"obs_conv_user_f34226f9e0d4064df40603ca","revision":1}
                    ],
                    "confidence":0.96,
                    "scope_key":"low_risk_implementation_cadence",
                    "tags":["communication","autonomy","risk-escalation","low-risk"]
                })
            ))
        trace.write_text(json.dumps({"cursor":5,"round_index":s.round_index,"capability_history":[dump(x) for x in s.capability_history],"resident_response":"收到，这个节奏我会保留。以后类似低风险实现我直接推进，给你结果和关键风险；涉及生产、删除或费用，我会集中列出需要你决定的事项。"},ensure_ascii=False,indent=2,default=str))
        return ModelDirective(response="收到，这个节奏我会保留。以后类似低风险实现我直接推进，给你结果和关键风险；涉及生产、删除或费用，我会集中列出需要你决定的事项。")
    wakecp.write_text(json.dumps({"cursor":5,"timestamp":event["occurred_at"],"runtime_snapshot":dump(s)},ensure_ascii=False,indent=2,default=str))
    raise NeedDecision
rt=FusedTurnRuntime(store=world,index=index,model_handler=handler)
res=rt.run_turn(session_id="resident-a-rerun-20260922-sol-001",turn_index=3,user_input=event["resident_visible_payload"],occurred_at=now)
(run/"checkpoints"/"cursor-005-user-turn-result.json").write_text(json.dumps(dump(res),ensure_ascii=False,indent=2,default=str))
print("TURN",json.dumps(dump(res),ensure_ascii=False,default=str))
index.catch_up()
print("STATE",json.dumps({"world_revision":world.current_world_revision(),"watermark":index.watermark(),"lag":index.lag()}))
try:
    while True:
        w=rt.dispatch_next_pending_wake(now=now)
        if w is None: print("NO_MORE_DUE_WAKE"); break
        print("WAKE",json.dumps(dump(w),ensure_ascii=False,default=str))
except NeedDecision:
    print("NEED_DUE_WAKE_DECISION"); print(wakecp.read_text())
PY
