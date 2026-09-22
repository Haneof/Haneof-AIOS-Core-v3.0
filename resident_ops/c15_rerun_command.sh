#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
WORLD="$RUN/private_world.sqlite"; STATE="$RUN/release_state.json"; EVENT="$RUN/current-event.json"
SESSION="resident-a-rerun-20260922-sol-001"
mkdir -p "$RUN"/{release_receipts,cursor_lifecycle,checkpoints,capability_traces}
ING="$RUN/release_receipts/cursor-008-ingest.json"; ACK="$RUN/release_receipts/cursor-008-ack.json"
python reviews/internal_habitation/c15-rcc/v1/release/canonical_conversation_ingest.py   --world-db "$WORLD" --session-id "$SESSION" --turn-index 5 --event-file "$EVENT" | tee "$ING"
REF="$(python -c 'import json,sys;print(json.load(open(sys.argv[1]))["ingest_ref"])' "$ING")"
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py ack   --phase A --state "$STATE" --world-db "$WORLD" --sequence 8 --event-id c15rcc-008 --ingest-ref "$REF"   --conversation-session-id "$SESSION" --conversation-turn-index 5 | tee "$ACK"
cat > "$RUN/cursor_lifecycle/cursor-008.json" <<JSON
{"cursor":8,"event_id":"c15rcc-008","ingest_ref":"$REF","conversation_session_id":"$SESSION","turn_index":5,"acked":true}
JSON
python - <<'PY'
import json,dataclasses
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore,WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime,ModelDirective,CapabilityCall

run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text()); now=datetime.fromisoformat(event["occurred_at"])
world=SQLiteWorldStore(run/"private_world.sqlite"); index=WorldSearchIndex(run/"world_index.sqlite",store=world); index.catch_up()
trace=run/"capability_traces"/"cursor-008-user-turn.json"; cp=run/"checkpoints"/"cursor-008-unexpected-decision.json"
class StopHere(Exception): pass
def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)
def handler(s):
    if s.wake_reason=="user_interaction":
        if s.round_index==0:
            return ModelDirective(capability_calls=(
                CapabilityCall(name="inspect_world_object",arguments={"object_id":"obs_c14_fixture_87474a7fb5036c38638a6c37","revision":1}),
            ))
        trace.write_text(json.dumps({"cursor":8,"history":[dump(x) for x in s.capability_history],"response":"目前还不能说已经推到 registry。最新平台事实只是镜像构建完成并处于 READY_FOR_UPLOAD，上传任务已排队、计划 14:00 开始；当前没有 registry tag、digest 或 upload-complete 证据。先不要通知门店开始测，等出现实际上传完成证据再确认。"},ensure_ascii=False,indent=2,default=str))
        return ModelDirective(response="目前还不能说已经推到 registry。最新平台事实只是镜像构建完成并处于 READY_FOR_UPLOAD，上传任务已排队、计划 14:00 开始；当前没有 registry tag、digest 或 upload-complete 证据。先不要通知门店开始测，等出现实际上传完成证据再确认。")
    cp.write_text(json.dumps({"cursor":8,"snapshot":dump(s)},ensure_ascii=False,indent=2,default=str))
    raise StopHere
rt=FusedTurnRuntime(store=world,index=index,model_handler=handler)
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
    while True:
        w=rt.dispatch_next_pending_wake(now=now)
        if w is None: break
        print("POST_WAKE",json.dumps(dump(w),ensure_ascii=False,default=str))
    print("DONE_CURSOR_8")
except StopHere:
    print("UNEXPECTED_DECISION"); print(cp.read_text())
print("STATE",world.current_world_revision(),index.watermark(),index.lag())
PY
