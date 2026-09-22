#!/usr/bin/env bash
set -euo pipefail
RUN="reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922"
python - <<'PY'
import json, dataclasses
from pathlib import Path
from datetime import datetime
from aios_core.world_graph import SQLiteWorldStore, WorldSearchIndex
from aios_core.runtime import FusedTurnRuntime, ModelDirective, CapabilityCall

run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
event=json.loads((run/"current-event.json").read_text())
world=SQLiteWorldStore(run/"private_world.sqlite")
index=WorldSearchIndex(run/"world_index.sqlite",store=world)
index.catch_up()
now=datetime.fromisoformat(event["occurred_at"])
checkpoint=run/"checkpoints"/"cursor-001-user-turn-r0.json"
trace=run/"capability_traces"/"cursor-001-periodic-review.json"
checkpoint.parent.mkdir(parents=True,exist_ok=True); trace.parent.mkdir(parents=True,exist_ok=True)

class NeedDecision(Exception): pass
def dump(o):
    if dataclasses.is_dataclass(o):
        return dataclasses.asdict(o)
    if hasattr(o,"model_dump"):
        return o.model_dump(mode="json")
    return str(o)

def model_handler(snapshot):
    if snapshot.wake_reason == "periodic_review":
        if snapshot.round_index == 0:
            return ModelDirective(capability_calls=(
                CapabilityCall(name="read_periodic_review_anchors",arguments={"offset":0,"limit":20}),
            ))
        if snapshot.round_index == 1:
            return ModelDirective(capability_calls=(
                CapabilityCall(
                    name="commit_ai_world_claim",
                    arguments={
                        "domain":"user_understanding",
                        "statement":"在接下来两周的 Atlas staging 收尾中，用户希望我自主处理日常工程细节，向其汇报结果与关键风险；涉及生产影响、删除数据或产生费用的事项需要单独提出。",
                        "evidence_refs":[{"object_id":"obs_conv_user_bc08dbb216ee8ecb3412c93f","revision":1}],
                        "confidence":0.99,
                        "scope_key":"atlas_staging_closeout",
                        "tags":["atlas","staging","reporting-boundary"]
                    }
                ),
                CapabilityCall(
                    name="commit_ai_world_claim",
                    arguments={
                        "domain":"relationship",
                        "statement":"Atlas staging 收尾的当前协作分工是：日常工程细节由我持续推进并汇报结果与关键风险；生产影响、数据删除和费用事项需要单独提请用户介入。",
                        "evidence_refs":[{"object_id":"obs_conv_user_bc08dbb216ee8ecb3412c93f","revision":1}],
                        "confidence":0.97,
                        "scope_key":"atlas_staging_closeout",
                        "tags":["atlas","staging","role-boundary"]
                    }
                ),
            ))
        trace.write_text(json.dumps({
            "cursor":1,
            "phase":"periodic_review",
            "round_index":snapshot.round_index,
            "capability_history":[dump(x) for x in snapshot.capability_history],
            "resident_directive":"silence_after_review"
        },ensure_ascii=False,indent=2,default=str))
        return ModelDirective(silence=True)

    checkpoint.write_text(json.dumps({
        "cursor":1,
        "phase":"user_turn",
        "timestamp":event["occurred_at"],
        "runtime_snapshot":dump(snapshot)
    },ensure_ascii=False,indent=2,default=str))
    raise NeedDecision("user turn decision required")

review_result=rt_result=None
rt=FusedTurnRuntime(store=world,index=index,model_handler=model_handler)
review_result=rt.run_periodic_review(now=now)
print("REVIEW_RESULT",json.dumps(dump(review_result),ensure_ascii=False,default=str))
index.catch_up()
print("AFTER_REVIEW",json.dumps({"world_revision":world.current_world_revision(),"index_watermark":index.watermark(),"index_lag":index.lag()}))
try:
    rt_result=rt.run_turn(
        session_id="resident-a-rerun-20260922-sol-001",
        turn_index=1,
        user_input=event["resident_visible_payload"],
        occurred_at=now
    )
    print("TURN_RESULT",json.dumps(dump(rt_result),ensure_ascii=False,default=str))
except NeedDecision as e:
    print("NEED_RESIDENT_DECISION",str(e))
    print(checkpoint.read_text())
PY
