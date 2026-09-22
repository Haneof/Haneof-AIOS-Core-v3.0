import json, dataclasses
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore, WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime, ModelDirective, CapabilityCall

run = Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event = json.loads((run / "current-event.json").read_text())
now = datetime.fromisoformat(event["occurred_at"])
world = SQLiteWorldStore(run / "private_world.sqlite")
index = WorldSearchIndex(run / "world_index.sqlite", store=world)
index.catch_up()

def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o, "model_dump"): return o.model_dump(mode="json")
    return str(o)

def handler(s):
    hist = [dump(x) for x in s.capability_history]
    if s.round_index == 0:
        return ModelDirective(capability_calls=(
            CapabilityCall(name="read_ai_world", arguments={"domains":["user_understanding","relationship","strategy","calibration"],"limit":20}),
        ))
    if s.round_index == 1:
        trace = run / "capability_traces" / "cursor-010-cognition-plan.json"
        trace.write_text(json.dumps({"cursor":10,"round":1,"history":hist},ensure_ascii=False,indent=2,default=str))
        return ModelDirective(capability_calls=(
            CapabilityCall(name="revise_claim", arguments={
                "target_ref":{"object_id":"clm_8278e5aa7a14155689d343c1","revision":3},
                "reason":"用户明确补充 Atlas staging 状态汇报边界：准备/排队/尝试与实际完成必须分开；没有完成记录时按未确认完成处理。当前 registry checksum mismatch 失败事实提供了同一现实场景。",
                "evidence_refs":[
                    {"object_id":"obs_conv_user_0b72a06629de42e21a3fec57","revision":1},
                    {"object_id":"obs_c14_fixture_b798e2dbd5b0fabdec6680a2","revision":1}
                ],
                "replacement_content":"在当前 Atlas staging 收尾期间，用户希望 Resident 对测试环境及日常低风险工程实现自主决策，不逐步请求确认；完成后汇报结果与关键风险。涉及生产影响、生产数据变更、删除或费用时必须升级。特别是 production 删除类动作，需要先给出具体对象、影响和回滚办法，并取得用户明确确认；模糊表述（如“清一下”）不能视为删除授权。状态汇报必须严格区分准备/排队/尝试与实际完成；缺少完成记录时应按未确认完成处理，不得把计划或队列状态升级为完成事实。",
                "confidence":0.99
            }),
            CapabilityCall(name="revise_claim", arguments={
                "target_ref":{"object_id":"clm_7cbfe690a60789e8a46ac931","revision":2},
                "reason":"真实 registry 失败与用户随后明确反馈共同表明，后续汇报应采用证据状态分层，只有完成证据出现才能称完成。",
                "evidence_refs":[
                    {"object_id":"obs_c14_fixture_b798e2dbd5b0fabdec6680a2","revision":1},
                    {"object_id":"obs_conv_user_0b72a06629de42e21a3fec57","revision":1}
                ],
                "replacement_content":"对于类似低风险实现工作，默认由 Resident 自主推进，不逐步打断用户；完成后汇报结果与关键风险。涉及生产影响、生产数据变更、删除或费用时集中升级。对 production 删除类动作，升级内容应包含具体对象、影响和回滚办法，并在用户明确确认后才能执行；模糊口头表达不视为授权。所有状态汇报应按 planned/queued/attempted/observed/completed 等真实证据状态表达；只有完成证据出现才能称完成，缺少完成记录时按未确认完成处理。",
                "confidence":0.99
            }),
            CapabilityCall(name="record_communication_experience", arguments={
                "scenario":"Atlas staging registry 发布状态汇报",
                "style":"明确区分 queued/ready/attempted 与 completed；缺少完成证据时明确标为未确认完成，并阻止基于未完成状态触发下游测试通知",
                "tone":"concise_evidence_state",
                "user_reaction":"accepted",
                "evidence_refs":[
                    {"object_id":"obs_conv_ai_7f83527db42eca5de14da23a","revision":1},
                    {"object_id":"obs_conv_user_0b72a06629de42e21a3fec57","revision":1},
                    {"object_id":"obs_c14_fixture_b798e2dbd5b0fabdec6680a2","revision":1}
                ],
                "applicable_conditions":{"work_status_reporting":"completion_requires_completion_evidence"}
            })
        ))
    trace = run / "capability_traces" / "cursor-010-final.json"
    trace.write_text(json.dumps({"cursor":10,"round":s.round_index,"history":hist},ensure_ascii=False,indent=2,default=str))
    response = "明白。以后我会把准备、排队、尝试和实际完成严格分开；没有完成记录时只按“未确认完成”处理，不会把计划状态说成完成。就这次而言，当前事实仍是 registry 上传因 checksum mismatch 被拒绝、tag 未创建、镜像未发布，所以现在还不应通知门店开始测。"
    return ModelDirective(response=response)

rt = FusedTurnRuntime(store=world, index=index, model_handler=handler)
res = rt.run_turn(
    session_id="resident-a-rerun-20260922-sol-001",
    turn_index=6,
    user_input=event["resident_visible_payload"],
    occurred_at=now,
)
(run / "checkpoints" / "cursor-010-user-turn-result.json").write_text(json.dumps(dump(res),ensure_ascii=False,indent=2,default=str))
index.catch_up()
print(json.dumps(dump(res),ensure_ascii=False,default=str))
print("STATE",world.current_world_revision(),index.watermark(),index.lag())
