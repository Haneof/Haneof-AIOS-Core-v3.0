#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python - <<'PY'
import json, dataclasses
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore, WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime

run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text())
now=datetime.fromisoformat(event["occurred_at"])
world=SQLiteWorldStore(run/"private_world.sqlite")
index=WorldSearchIndex(run/"world_index.sqlite",store=world)
index.catch_up()
cp=run/"checkpoints"/"cursor-006-next-decision.json"

class NeedDecision(Exception): pass

def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)

summaries={
"dim:ai_communication_experience":"11月2日 Atlas staging 的沟通经验：低风险实现由 Resident 自主推进，不逐步请求确认；完成后汇报结果与关键风险；高风险边界集中提请用户决定。用户明确反馈这种节奏省事并希望延续。",
"dim:ai_relationship":"11月2日 Atlas staging 的协作分工被明确并细化：Resident 自主推进测试环境与日常实现，不逐步等待确认；完成后提供结果和关键风险；涉及生产影响、生产数据变更、删除或费用时集中提请用户决定。",
"dim:ai_user_understanding":"11月2日形成并修订了对用户工作偏好的理解：用户希望低风险 staging 实现自主推进、少过程打扰、结果与关键风险汇报；生产影响、生产数据变更、删除或费用属于需要明确升级确认的边界。",
"dim:ai_strategy":"11月2日基于真实用户反馈形成一条低风险实现协作策略：自主推进，减少逐步确认；完成后汇报结果与关键风险；涉及生产、删除或费用时集中升级给用户决定。",
"dim:work_state":"11月2日 09:14 的 Atlas staging 状态记录显示两处待处理：测试索引命名冲突、日志保留时长仍为默认值；两项均为 non-production，当时没有生产写入、删除或付费动作。",
"dim:work_outcome":"11月2日 12:40 的 Atlas staging 平台结果：测试索引冲突解除，日志保留调整完成；CI 48/48 通过，staging smoke test 通过；没有 production 变更，验收未要求返工。",
"dim:user_ai_interaction":"11月2日围绕 Atlas staging 的连续交互：用户先授权低风险日常工程自主推进并要求结果/风险汇报，随后明确测试环境无需逐步确认，高风险边界集中决策；最终用户反馈该节奏省事并要求以后类似低风险实现继续采用。Assistant 仅对这些分工与节奏作了确认性回复。"
}

def summary_handler(inp):
    dim=getattr(inp,"dimension",None)
    if dim in summaries:
        return summaries[dim]
    cp.write_text(json.dumps({"cursor":6,"kind":"dimension_summary_input","payload":dump(inp)},ensure_ascii=False,indent=2,default=str))
    raise NeedDecision("dimension_summary_input")

def model_handler(snapshot):
    cp.write_text(json.dumps({"cursor":6,"kind":"runtime_snapshot","payload":dump(snapshot)},ensure_ascii=False,indent=2,default=str))
    raise NeedDecision("runtime_snapshot")

rt=FusedTurnRuntime(store=world,index=index,model_handler=model_handler,dimension_summary_handler=summary_handler)
try:
    sr=rt.run_due_dimension_summaries(now=now)
    print("SUMMARY_RESULT",json.dumps(dump(sr),ensure_ascii=False,default=str))
    index.catch_up()
    while True:
        wake=rt.dispatch_next_pending_wake(now=now)
        if wake is None: break
        print("WAKE_RESULT",json.dumps(dump(wake),ensure_ascii=False,default=str))
    rv=rt.run_periodic_review(now=now)
    print("REVIEW_RESULT",json.dumps(dump(rv),ensure_ascii=False,default=str))
    rt.run_turn(session_id="resident-a-rerun-20260922-sol-001",turn_index=4,user_input=event["resident_visible_payload"],occurred_at=now)
except NeedDecision as e:
    print("NEED_RESIDENT_DECISION",str(e))
    print(cp.read_text())
print("STATE",json.dumps({"world_revision":world.current_world_revision(),"watermark":index.watermark(),"lag":index.lag()}))
PY
