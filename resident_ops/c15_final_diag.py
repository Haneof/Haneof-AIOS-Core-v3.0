import sqlite3, json, hashlib, os
from pathlib import Path
from aios_core.world_graph import SQLiteWorldStore, WorldSearchIndex
run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
world=SQLiteWorldStore(run/"private_world.sqlite")
index=WorldSearchIndex(run/"world_index.sqlite",store=world); index.catch_up()
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest()
db=sqlite3.connect(run/"private_world.sqlite"); db.row_factory=sqlite3.Row
tables=[r[0] for r in db.execute("select name from sqlite_master where type='table' order by name")]
schema={t:[{"name":r["name"],"type":r["type"]} for r in db.execute("pragma table_info('"+t.replace("'","''")+"')")] for t in tables}
release=json.loads((run/"release_state.json").read_text())
print(json.dumps({
 "world_revision":world.current_world_revision(),
 "index_watermark":index.watermark(),
 "index_lag":index.lag(),
 "hashes":{"world":sha(run/"private_world.sqlite"),"index":sha(run/"world_index.sqlite"),"release_state":sha(run/"release_state.json")},
 "release":{"last_acked_sequence":release.get("last_acked_sequence"),"next_sequence":release.get("next_sequence"),"pending_reveal":release.get("pending_reveal"),"receipts":len(release.get("receipts",[]))},
 "tables":schema
},ensure_ascii=False,indent=2))
