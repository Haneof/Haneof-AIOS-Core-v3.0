#!/usr/bin/env python3
from __future__ import annotations
import json, posixpath, sys
from pathlib import Path
import xml.etree.ElementTree as ET
p=Path(sys.argv[1]); rc=int(sys.argv[2]); out={"pytest_exit":rc,"exists":p.exists(),"size":p.stat().st_size if p.exists() else 0}
if rc not in (0,1):
    out["classification"]="NON_ADMISSIBLE_PYTEST_EXIT"; print(json.dumps(out,sort_keys=True)); raise SystemExit
if not p.exists() or not p.stat().st_size:
    out["classification"]="JUNIT_MISSING_OR_EMPTY"; print(json.dumps(out,sort_keys=True)); raise SystemExit
try:
    root=ET.parse(p).getroot()
except ET.ParseError as exc:
    out["classification"]="JUNIT_MALFORMED"; out["error"]=str(exc); print(json.dumps(out,sort_keys=True)); raise SystemExit
suites=[]; cases=[]; bad_count=False
for n in root.iter():
    tag=n.tag.split("}")[-1]
    if tag=="testsuite":
        rec=dict(n.attrib); suites.append(rec)
        for k in ("failures","errors"):
            if k in rec:
                try: int(rec[k])
                except ValueError: bad_count=True
    if tag=="testcase":
        kinds=[x.tag.split("}")[-1] for x in list(n) if x.tag.split("}")[-1] in ("failure","error")]
        if kinds:
            f=(n.attrib.get("file") or "").replace("\\","/")
            c=n.attrib.get("classname") or ""
            if f:
                mapped=posixpath.normpath(f); traversal=".." in f.split("/")
            else:
                mapped=c.replace(".","/") if c else ""; traversal=False
            cases.append({"kinds":kinds,"file":f,"classname":c,"mapped":mapped,"traversal":traversal,"downstream":(not traversal and mapped.startswith("tests/c15_persistence/"))})
out.update({"root_tag":root.tag,"suites":suites,"structured_case_count":len(cases),"cases":cases,"bad_count":bad_count})
if bad_count:
    cls="JUNIT_BAD_COUNT"
elif rc==0:
    cls="RC0_CLEAN" if not cases and all(int(s.get("failures","0"))+int(s.get("errors","0"))==0 for s in suites) else "RC0_JUNIT_NOT_CLEAN"
elif not cases:
    cls="RC1_ZERO_STRUCTURED_FAILURE_ERROR"
elif any(len(x["kinds"])!=1 for x in cases):
    cls="AMBIGUOUS_MULTI_KIND_CASE"
elif any(not x["downstream"] for x in cases):
    cls="NON_DOWNSTREAM_STRUCTURED_CASE"
else:
    concrete=[s for s in suites if "failures" in s or "errors" in s]
    count=sum(int(s.get("failures","0"))+int(s.get("errors","0")) for s in concrete)
    cls="DOWNSTREAM_ONLY_DEBT" if not concrete or count==len(cases) else "SUMMARY_CASE_COUNT_MISMATCH"
out["classification"]=cls
print(json.dumps(out,sort_keys=True))
