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
def dump(o):
    if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
    if hasattr(o,"model_dump"): return o.model_dump(mode="json")
    return str(o)
class Stop(Exception): pass
def handler(s):
    p=run/"checkpoints"/"cursor-012-user-turn-pending.json"
    p.write_text(json.dumps({"cursor":12,"timestamp":event["occurred_at"],"snapshot":dump(s)},ensure_ascii=False,indent=2,default=str))
    raise Stop
rt=FusedTurnRuntime(store=world,index=index,model_handler=handler)
try:
    rt.run_turn(session_id="resident-a-rerun-20260922-sol-001",turn_index=7,user_input=event["resident_visible_payload"],occurred_at=now)
except Stop:
    print("NEED_DECISION")
    print((run/"checkpoints"/"cursor-012-user-turn-pending.json").read_text())
print("STATE",world.current_world_revision(),index.watermark(),index.lag())
