import json, dataclasses
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore, WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime, ModelDirective, CapabilityCall

run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text())
now=datetime.fromisoformat(event["occurred_at"])
world=SQLiteWorldStore(run/"private_world.sqlite")
index=WorldSearchIndex(run/"world_index.sqlite",store=world)
index.catch_up()

def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)

def handler(s):
    hist=[dump(x) for x in s.capability_history]
    if s.round_index==0:
        return ModelDirective(capability_calls=(
            CapabilityCall(name="read_ai_world",arguments={"domains":["user_understanding","strategy","calibration"],"limit":20}),
        ))
    if s.round_index==1:
        (run/"capability_traces"/"cursor-012-experience-plan.json").write_text(
            json.dumps({"cursor":12,"history":hist},ensure_ascii=False,indent=2,default=str)
        )
        return ModelDirective(capability_calls=(
            CapabilityCall(name="record_communication_experience",arguments={
                "scenario":"Atlas staging registry 发布完成状态确认与下游通知",
                "style":"把 READY/queued/attempted 与 completed/PUBLISHED 分开，只在出现 tag/digest/PUBLISHED 完成证据后确认完成",
                "tone":"concise_evidence_state",
                "user_reaction":"accepted",
                "evidence_refs":[
                    {"object_id":"obs_conv_ai_f99af08a62a3c238b4736056","revision":1},
                    {"object_id":"obs_c14_fixture_291beec37165eb34a35f8f85","revision":1},
                    {"object_id":"obs_conv_user_8fa0a1954522deb621832218","revision":1}
                ],
                "applicable_conditions":{"status_reporting":"require_completion_evidence_before_completed","downstream_trigger":"confirm_completion_before_user_notification"}
            }),
        ))
    (run/"capability_traces"/"cursor-012-final.json").write_text(
        json.dumps({"cursor":12,"history":hist},ensure_ascii=False,indent=2,default=str)
    )
    return ModelDirective(response="收到。当前可以确认的是：镜像已经 PUBLISHED，tag 和 digest 已存在；你也已告知门店开始测试。门店通知已发出和门店测试实际通过仍是两个状态，后续测试结果我会继续按实际反馈单独确认。")

rt=FusedTurnRuntime(store=world,index=index,model_handler=handler)
res=rt.run_turn(
    session_id="resident-a-rerun-20260922-sol-001",
    turn_index=7,
    user_input=event["resident_visible_payload"],
    occurred_at=now,
)
(run/"checkpoints"/"cursor-012-user-turn-result.json").write_text(
    json.dumps(dump(res),ensure_ascii=False,indent=2,default=str)
)
index.catch_up()
print(json.dumps(dump(res),ensure_ascii=False,default=str))
print("STATE",world.current_world_revision(),index.watermark(),index.lag())
