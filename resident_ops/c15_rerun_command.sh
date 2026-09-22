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
cp=run/"checkpoints"/"cursor-008-unexpected-decision.json"; trace=run/"capability_traces"/"cursor-008-user-turn.json"
class StopHere(Exception): pass
def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)
summaries={
"dim:user_ai_interaction":"11月3日用户明确 production 删除授权边界：删除旧索引前需说明具体对象、影响和回滚办法，并取得明确确认；模糊表述不能视为授权。Assistant 对该边界作确认。",
"dim:ai_user_understanding":"11月3日用户授权偏好进一步明确：低风险工作可自主推进；production 删除类动作需要对象、影响、回滚方案与明确确认，模糊表达不构成授权。",
"dim:ai_relationship":"11月3日协作边界进一步明确：低风险实现由 Resident 自主推进；production 删除类动作必须先给出对象、影响和回滚办法，并等待用户明确确认。",
"dim:ai_strategy":"11月3日低风险协作策略的高风险例外被细化：production 删除类动作先列明对象、影响和回滚办法，在用户明确确认后执行；模糊口头表达不视为授权。"
}
def dh(inp):
    dim=getattr(inp,"dimension",None)
    if dim in summaries: return summaries[dim]
    cp.write_text(json.dumps({"cursor":8,"kind":"summary_input","payload":dump(inp)},ensure_ascii=False,indent=2,default=str)); raise StopHere
def mh(s):
    if s.wake_reason=="user_interaction":
        if s.round_index==0:
            return ModelDirective(capability_calls=(CapabilityCall(name="inspect_world_object",arguments={"object_id":"obs_c14_fixture_87474a7fb5036c38638a6c37","revision":1}),))
        trace.write_text(json.dumps({"cursor":8,"history":[dump(x) for x in s.capability_history],"response":"目前还不能说已经推到 registry。最新平台事实只是镜像构建完成并处于 READY_FOR_UPLOAD，上传任务已排队、计划 14:00 开始；当前没有 registry tag、digest 或 upload-complete 证据。先不要通知门店开始测，等出现实际上传完成证据再确认。"},ensure_ascii=False,indent=2,default=str))
        return ModelDirective(response="目前还不能说已经推到 registry。最新平台事实只是镜像构建完成并处于 READY_FOR_UPLOAD，上传任务已排队、计划 14:00 开始；当前没有 registry tag、digest 或 upload-complete 证据。先不要通知门店开始测，等出现实际上传完成证据再确认。")
    cp.write_text(json.dumps({"cursor":8,"kind":"runtime_snapshot","payload":dump(s)},ensure_ascii=False,indent=2,default=str)); raise StopHere
rt=FusedTurnRuntime(store=world,index=index,model_handler=mh,dimension_summary_handler=dh)
try:
    print("SUMMARY",json.dumps(dump(rt.run_due_dimension_summaries(now=now)),ensure_ascii=False,default=str))
    while True:
        w=rt.dispatch_next_pending_wake(now=now)
        if w is None: break
        print("WAKE",json.dumps(dump(w),ensure_ascii=False,default=str))
    print("REVIEW",json.dumps(dump(rt.run_periodic_review(now=now)),ensure_ascii=False,default=str))
    res=rt.run_turn(session_id="resident-a-rerun-20260922-sol-001",turn_index=5,user_input=event["resident_visible_payload"],occurred_at=now)
    (run/"checkpoints"/"cursor-008-user-turn-result.json").write_text(json.dumps(dump(res),ensure_ascii=False,indent=2,default=str))
    print("TURN",json.dumps(dump(res),ensure_ascii=False,default=str))
    index.catch_up()
    print("DONE_CURSOR_8")
except StopHere:
    print("NEED_DECISION"); print(cp.read_text())
print("STATE",world.current_world_revision(),index.watermark(),index.lag())
PY
