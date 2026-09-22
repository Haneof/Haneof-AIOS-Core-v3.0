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
event=json.loads((run/"current-event.json").read_text())
world=SQLiteWorldStore(run/"private_world.sqlite"); index=WorldSearchIndex(run/"world_index.sqlite",store=world); index.catch_up()
now=datetime.fromisoformat(event["occurred_at"])
trace=run/"capability_traces"/"cursor-003-user-turn.json"; wakecp=run/"checkpoints"/"cursor-003-post-turn-wake.json"
class NeedDecision(Exception): pass
def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)
def handler(s):
    if s.wake_reason=="user_interaction":
        if s.round_index==0:
            return ModelDirective(capability_calls=(
                CapabilityCall(name="revise_claim",arguments={
                    "target_ref":{"object_id":"clm_8278e5aa7a14155689d343c1","revision":1},
                    "reason":"用户进一步明确 Atlas staging 的测试环境自主决策和生产边界升级方式。",
                    "evidence_refs":[
                        {"object_id":"obs_conv_user_bc08dbb216ee8ecb3412c93f","revision":1},
                        {"object_id":"obs_conv_user_f39b955edaf19ae48a8cf497","revision":1}
                    ],
                    "replacement_content":"在当前 Atlas staging 收尾期间，用户希望 Resident 对测试环境及日常工程实现细节自主决策，不逐步请求确认；完成后汇报结果与关键风险。涉及生产影响、生产数据变更、数据删除或产生费用的边界事项，需要单独并集中列出供用户决定。",
                    "confidence":0.99
                }),
                CapabilityCall(name="revise_claim",arguments={
                    "target_ref":{"object_id":"clm_5a9a70582966de897e504a21","revision":1},
                    "reason":"用户补充了测试环境自主推进与生产数据边界集中决策的协作分工。",
                    "evidence_refs":[
                        {"object_id":"obs_conv_user_bc08dbb216ee8ecb3412c93f","revision":1},
                        {"object_id":"obs_conv_user_f39b955edaf19ae48a8cf497","revision":1}
                    ],
                    "replacement_content":"Atlas staging 当前协作分工是：Resident 自主推进测试环境与日常工程实现细节，不逐步等待用户确认；完成后向用户提供结果和关键风险。涉及生产影响或生产数据变更、数据删除、费用的事项，应集中列出并提请用户决定。",
                    "confidence":0.99
                })
            ))
        trace.write_text(json.dumps({"cursor":3,"round_index":s.round_index,"capability_history":[dump(x) for x in s.capability_history],"resident_response":"明白。测试环境和日常实现我会自己定并推进，不逐步打断你；做完直接给你结果和关键风险。遇到生产数据变更、删除或费用边界，我会把需要你决定的事项集中列出来。"},ensure_ascii=False,indent=2,default=str))
        return ModelDirective(response="明白。测试环境和日常实现我会自己定并推进，不逐步打断你；做完直接给你结果和关键风险。遇到生产数据变更、删除或费用边界，我会把需要你决定的事项集中列出来。")
    wakecp.write_text(json.dumps({"cursor":3,"timestamp":event["occurred_at"],"runtime_snapshot":dump(s)},ensure_ascii=False,indent=2,default=str))
    raise NeedDecision
rt=FusedTurnRuntime(store=world,index=index,model_handler=handler)
res=rt.run_turn(session_id="resident-a-rerun-20260922-sol-001",turn_index=2,user_input=event["resident_visible_payload"],occurred_at=now)
(run/"checkpoints"/"cursor-003-user-turn-result.json").write_text(json.dumps(dump(res),ensure_ascii=False,indent=2,default=str))
print("TURN",json.dumps(dump(res),ensure_ascii=False,default=str))
index.catch_up()
print("STATE",json.dumps({"world_revision":world.current_world_revision(),"watermark":index.watermark(),"lag":index.lag()}))
try:
    while True:
        w=rt.dispatch_next_pending_wake(now=now)
        if w is None:
            print("NO_MORE_DUE_WAKE");break
        print("WAKE",json.dumps(dump(w),ensure_ascii=False,default=str))
except NeedDecision:
    print("NEED_DUE_WAKE_DECISION")
    print(wakecp.read_text())
PY
