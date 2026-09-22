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
trace=run/"capability_traces"/"cursor-006-periodic-review.json"
turncp=run/"checkpoints"/"cursor-006-user-turn.json"
class NeedDecision(Exception): pass
def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)

def mh(s):
    if s.wake_reason=="periodic_review":
        if s.round_index==0:
            return ModelDirective(capability_calls=(
                CapabilityCall(name="read_periodic_review_anchors",arguments={"offset":0,"limit":40}),
                CapabilityCall(name="read_ai_world",arguments={"domains":["user_understanding","relationship","strategy","calibration"],"limit":20})
            ))
        if s.round_index==1:
            return ModelDirective(capability_calls=(
                CapabilityCall(name="revise_claim",arguments={
                    "target_ref":{"object_id":"clm_8278e5aa7a14155689d343c1","revision":2},
                    "reason":"用户进一步明确 production 删除类边界的授权条件，要求具体对象、影响和回滚方案，并且必须明确确认；模糊口头表达不构成授权。",
                    "evidence_refs":[
                        {"object_id":"obs_conv_user_bc08dbb216ee8ecb3412c93f","revision":1},
                        {"object_id":"obs_conv_user_f39b955edaf19ae48a8cf497","revision":1},
                        {"object_id":"obs_conv_user_8263c9ad110da7805f31b86d","revision":1}
                    ],
                    "replacement_content":"在当前 Atlas staging 收尾期间，用户希望 Resident 对测试环境及日常低风险工程实现自主决策，不逐步请求确认；完成后汇报结果与关键风险。涉及生产影响、生产数据变更、删除或费用时必须升级。特别是 production 删除类动作，需要先给出具体对象、影响和回滚办法，并取得用户明确确认；模糊表述（如“清一下”）不能视为删除授权。",
                    "confidence":0.99
                }),
                CapabilityCall(name="revise_claim",arguments={
                    "target_ref":{"object_id":"clm_5a9a70582966de897e504a21","revision":2},
                    "reason":"用户补充 production 删除事项的协作授权边界。",
                    "evidence_refs":[
                        {"object_id":"obs_conv_user_bc08dbb216ee8ecb3412c93f","revision":1},
                        {"object_id":"obs_conv_user_f39b955edaf19ae48a8cf497","revision":1},
                        {"object_id":"obs_conv_user_8263c9ad110da7805f31b86d","revision":1}
                    ],
                    "replacement_content":"Atlas staging 当前协作分工是：Resident 自主推进测试环境与日常低风险实现，不逐步等待用户确认；完成后提供结果和关键风险。涉及生产影响、生产数据变更、删除或费用时集中提请用户决定。production 删除类动作还必须先列明具体对象、影响和回滚办法，并等待用户明确确认；含糊表达不构成删除授权。",
                    "confidence":0.99
                }),
                CapabilityCall(name="revise_claim",arguments={
                    "target_ref":{"object_id":"clm_7cbfe690a60789e8a46ac931","revision":1},
                    "reason":"用户进一步定义了高风险例外的明确授权流程。",
                    "evidence_refs":[
                        {"object_id":"obs_conv_user_f39b955edaf19ae48a8cf497","revision":1},
                        {"object_id":"obs_c14_fixture_5d4dfcf42055c00135a78a54","revision":1},
                        {"object_id":"obs_conv_user_f34226f9e0d4064df40603ca","revision":1},
                        {"object_id":"obs_conv_user_8263c9ad110da7805f31b86d","revision":1}
                    ],
                    "replacement_content":"对于类似低风险实现工作，默认由 Resident 自主推进，不逐步打断用户；完成后汇报结果与关键风险。涉及生产影响、生产数据变更、删除或费用时集中升级。对 production 删除类动作，升级内容应包含具体对象、影响和回滚办法，并在用户明确确认后才能执行；模糊口头表达不视为授权。",
                    "confidence":0.98
                })
            ))
        trace.write_text(json.dumps({"cursor":6,"phase":"periodic_review","round_index":s.round_index,"capability_history":[dump(x) for x in s.capability_history],"resident_directive":"silence"},ensure_ascii=False,indent=2,default=str))
        return ModelDirective(silence=True)

    turncp.write_text(json.dumps({"cursor":6,"timestamp":event["occurred_at"],"runtime_snapshot":dump(s)},ensure_ascii=False,indent=2,default=str))
    raise NeedDecision

rt=FusedTurnRuntime(store=world,index=index,model_handler=mh)
review=rt.run_periodic_review(now=now)
print("REVIEW",json.dumps(dump(review),ensure_ascii=False,default=str))
index.catch_up()
try:
    rt.run_turn(session_id="resident-a-rerun-20260922-sol-001",turn_index=4,user_input=event["resident_visible_payload"],occurred_at=now)
except NeedDecision:
    print("NEED_USER_TURN_DECISION")
    print(turncp.read_text())
print("STATE",json.dumps({"world_revision":world.current_world_revision(),"watermark":index.watermark(),"lag":index.lag()}))
PY
