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

class NeedDecision(Exception):
    pass

def dump(o):
    if dataclasses.is_dataclass(o):
        return dataclasses.asdict(o)
    if hasattr(o,"model_dump"):
        return o.model_dump(mode="json")
    return str(o)

def summary_handler(inp):
    if getattr(inp,"dimension",None)=="dim:ai_communication_experience":
        return "11月2日的 Atlas staging 低风险实现沟通经验：Resident 自主推进低风险实现，不逐步请求确认；完成后汇报结果与关键风险；高风险边界集中提请用户决定。该次用户反馈为 accepted。"
    cp.write_text(json.dumps({"cursor":6,"kind":"dimension_summary_input","payload":dump(inp)},ensure_ascii=False,indent=2,default=str))
    raise NeedDecision("dimension_summary_input")

def model_handler(snapshot):
    cp.write_text(json.dumps({"cursor":6,"kind":"runtime_snapshot","payload":dump(snapshot)},ensure_ascii=False,indent=2,default=str))
    raise NeedDecision("runtime_snapshot")

rt=FusedTurnRuntime(store=world,index=index,model_handler=model_handler,dimension_summary_handler=summary_handler)
try:
    print("SUMMARY_RESULT", dump(rt.run_due_dimension_summaries(now=now)))
    index.catch_up()
    while True:
        wake=rt.dispatch_next_pending_wake(now=now)
        if wake is None:
            break
        print("WAKE_RESULT", dump(wake))
    print("REVIEW_RESULT", dump(rt.run_periodic_review(now=now)))
    rt.run_turn(session_id="resident-a-rerun-20260922-sol-001",turn_index=4,user_input=event["resident_visible_payload"],occurred_at=now)
except NeedDecision as e:
    print("NEED_RESIDENT_DECISION", str(e))
    print(cp.read_text())
print("STATE",json.dumps({"world_revision":world.current_world_revision(),"watermark":index.watermark(),"lag":index.lag()}))
PY
