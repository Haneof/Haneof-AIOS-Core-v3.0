import sqlite3,json
from pathlib import Path
run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
db=sqlite3.connect(run/"private_world.sqlite"); db.row_factory=sqlite3.Row
# latest wake states
latest=[]
for x in db.execute("select object_id,max(revision) revision from object_revisions where object_type='wake' group by object_id"):
    r=db.execute("select object_id,revision,payload_json from object_revisions where object_id=? and revision=?",(x["object_id"],x["revision"])).fetchone()
    p=json.loads(r["payload_json"])
    latest.append({"ref":f'{r["object_id"]}@{r["revision"]}',"state":p.get("state") or p.get("status"),"reason":p.get("reason") or p.get("wake_reason")})
# capability trace calls
calls=[]; term=[]
def walk(o):
    if isinstance(o,dict):
        if "name" in o and "ok" in o and isinstance(o.get("ok"),bool):
            calls.append((o.get("name"),o.get("ok"),o.get("error_code")))
        if "termination_reason" in o: term.append(o.get("termination_reason"))
        for v in o.values(): walk(v)
    elif isinstance(o,list):
        for v in o: walk(v)
for pth in (run/"capability_traces").glob("*.json"):
    try: walk(json.loads(pth.read_text()))
    except Exception: pass
print(json.dumps({
 "wake_latest_count":len(latest),
 "wake_latest_completed":sum(1 for x in latest if x["state"]=="completed"),
 "wake_latest_states":latest,
 "capability_call_records":len(calls),
 "capability_failures":sum(1 for _,ok,_ in calls if not ok),
 "capability_names":{n:sum(1 for n2,_,_ in calls if n2==n) for n in sorted(set(n for n,_,_ in calls))},
 "termination_reasons":{t:term.count(t) for t in sorted(set(term))}
},ensure_ascii=False,indent=2))
