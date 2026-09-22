import sqlite3, json, hashlib
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
def q(sql,args=()): return [dict(r) for r in db.execute(sql,args)]
type_counts=q("select object_type, count(*) as n from object_revisions group by object_type order by object_type")
latest_claims=q("select object_id,max(revision) revision from object_revisions where object_type='claim' group by object_id order by object_id")
claim_rows=[]
for x in latest_claims:
    row=db.execute("select object_id,revision,payload_json from object_revisions where object_id=? and revision=?",(x["object_id"],x["revision"])).fetchone()
    p=json.loads(row["payload_json"])
    claim_rows.append({"ref":f'{row["object_id"]}@{row["revision"]}',"dimension":p.get("dimension"),"status":p.get("status"),"statement":p.get("statement") or p.get("content")})
summaries=q("select count(*) n from object_revisions where object_type='summary'")[0]["n"]
wakes=q("select count(*) n from object_revisions where object_type='wake'")[0]["n"]
reviews=q("select count(*) n from object_revisions where object_type='wake' and payload_json like '%periodic_review%'")[0]["n"]
user_obs=q("select count(*) n from object_revisions where object_type='observation' and payload_json like '%\"role\": \"user\"%'")[0]["n"]
assistant_obs=q("select count(*) n from object_revisions where object_type='observation' and payload_json like '%\"role\": \"assistant\"%'")[0]["n"]
release=json.loads((run/"release_state.json").read_text())
checkpoints=list((run/"checkpoints").glob("*.json"))
caps=list((run/"capability_traces").glob("*.json"))
print(json.dumps({
 "world_revision":world.current_world_revision(),"index_watermark":index.watermark(),"index_lag":index.lag(),
 "hashes":{"world":sha(run/"private_world.sqlite"),"index":sha(run/"world_index.sqlite"),"release_state":sha(run/"release_state.json")},
 "release":{"last_acked_sequence":release.get("last_acked_sequence"),"next_sequence":release.get("next_sequence"),"pending_reveal":release.get("pending_reveal"),"receipts":len(release.get("receipts",[]))},
 "type_counts":type_counts,"latest_claims":claim_rows,"summary_revisions":summaries,"wake_revisions":wakes,"periodic_review_wake_revisions":reviews,
 "user_observation_rows":user_obs,"assistant_observation_rows":assistant_obs,"checkpoint_files":len(checkpoints),"capability_trace_files":len(caps)
},ensure_ascii=False,indent=2))
