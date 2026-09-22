import sqlite3, json
from pathlib import Path
run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
db=sqlite3.connect(run/"private_world.sqlite"); db.row_factory=sqlite3.Row
rows=[]
for r in db.execute("select object_id,revision,world_revision,payload_json from object_revisions where object_type='observation' order by world_revision"):
    p=json.loads(r["payload_json"])
    rows.append({
      "ref":f'{r["object_id"]}@{r["revision"]}',"wr":r["world_revision"],
      "dimension":p.get("metadata",{}).get("dimension") or p.get("dimension"),
      "source_class":p.get("metadata",{}).get("source_class") or p.get("source_class"),
      "source_kind":p.get("source_kind"),"role":p.get("role"),
      "originating_wake":p.get("metadata",{}).get("originating_wake_ref") or p.get("metadata",{}).get("wake_ref"),
      "value":p.get("value") or p.get("text")
    })
print(json.dumps(rows,ensure_ascii=False,indent=2))
