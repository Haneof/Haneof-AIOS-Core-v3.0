#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
WORLD="$RUN/private_world.sqlite"; STATE="$RUN/release_state.json"; EVENT="$RUN/current-event.json"
mkdir -p "$RUN"/{release_receipts,cursor_lifecycle,checkpoints,capability_traces}
ING="$RUN/release_receipts/cursor-007-ingest.json"; ACK="$RUN/release_receipts/cursor-007-ack.json"
python reviews/internal_habitation/c15-rcc/v1/release/mechanical_ingest_adapter.py --world-db "$WORLD" --event-file "$EVENT" | tee "$ING"
REF="$(python -c 'import json,sys;print(json.load(open(sys.argv[1]))["ingest_ref"])' "$ING")"
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py ack   --phase A --state "$STATE" --world-db "$WORLD" --sequence 7 --event-id c15rcc-007 --ingest-ref "$REF" | tee "$ACK"
cat > "$RUN/cursor_lifecycle/cursor-007.json" <<JSON
{"cursor":7,"event_id":"c15rcc-007","ingest_ref":"$REF","acked":true}
JSON
python - <<'PY'
import json,dataclasses
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore,WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime

run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text()); now=datetime.fromisoformat(event["occurred_at"])
world=SQLiteWorldStore(run/"private_world.sqlite"); index=WorldSearchIndex(run/"world_index.sqlite",store=world); index.catch_up()
cp=run/"checkpoints"/"cursor-007-pending-decision.json"
class NeedDecision(Exception): pass
def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)
summaries={
"dim:user_ai_interaction":"11月3日用户进一步明确 production 删除授权边界：若要删除旧索引，必须先说明具体对象、影响和回滚办法，并在用户明确确认后执行；模糊表述不能视为删除授权。Assistant 对该边界作了确认性回复。",
"dim:ai_user_understanding":"11月3日对用户授权偏好的理解更新：低风险工作可自主推进；production 删除类动作需要具体对象、影响、回滚方案以及用户明确确认，模糊表达不构成授权。",
"dim:ai_relationship":"11月3日 Atlas staging 协作边界进一步明确：低风险实现由 Resident 自主推进；production 删除类动作必须先给出对象、影响与回滚办法，并等待用户明确确认。",
"dim:ai_strategy":"11月3日低风险协作策略的高风险例外被细化：production 删除类动作应先列明具体对象、影响和回滚办法，并在用户明确确认后执行；模糊口头表达不视为授权。"
}
def dh(inp):
    dim=getattr(inp,"dimension",None)
    if dim in summaries: return summaries[dim]
    cp.write_text(json.dumps({"cursor":7,"kind":"dimension_summary_input","payload":dump(inp)},ensure_ascii=False,indent=2,default=str)); raise NeedDecision("dimension_summary_input")
def mh(s):
    cp.write_text(json.dumps({"cursor":7,"kind":"runtime_snapshot","payload":dump(s)},ensure_ascii=False,indent=2,default=str)); raise NeedDecision("runtime_snapshot")
rt=FusedTurnRuntime(store=world,index=index,model_handler=mh,dimension_summary_handler=dh)
print("START",json.dumps({"world_revision":world.current_world_revision(),"watermark":index.watermark(),"lag":index.lag()}))
try:
    sr=rt.run_due_dimension_summaries(now=now); print("SUMMARY",json.dumps(dump(sr),ensure_ascii=False,default=str))
    index.catch_up()
    while True:
        w=rt.dispatch_next_pending_wake(now=now)
        if w is None: break
        print("WAKE",json.dumps(dump(w),ensure_ascii=False,default=str))
    rv=rt.run_periodic_review(now=now); print("REVIEW",json.dumps(dump(rv),ensure_ascii=False,default=str))
    print("NO_SEMANTIC_WORK")
except NeedDecision as e:
    print("NEED_RESIDENT_DECISION",str(e)); print(cp.read_text())
print("STATE",json.dumps({"world_revision":world.current_world_revision(),"watermark":index.watermark(),"lag":index.lag()}))
PY
