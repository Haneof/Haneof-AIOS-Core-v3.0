import json
from pathlib import Path
run=Path("reviews/internal_habitation/c15-rcc/v1/runs/resident-a-rerun-20260922")
rows=[]
def find_term(o):
    out=[]
    if isinstance(o,dict):
        if "termination_reason" in o: out.append((o.get("termination_reason"),o.get("silenced"),o.get("response")))
        for v in o.values(): out += find_term(v)
    elif isinstance(o,list):
        for v in o: out += find_term(v)
    return out
for p in sorted((run/"checkpoints").glob("*.json")):
    try:
        j=json.loads(p.read_text())
    except Exception:
        continue
    terms=find_term(j)
    if terms: rows.append({"file":p.name,"terms":terms})
print(json.dumps(rows,ensure_ascii=False,indent=2))
