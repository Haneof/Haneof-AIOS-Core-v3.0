#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
workflow=Path(sys.argv[1]).read_text(encoding="utf-8")
publisher=workflow[workflow.index("  rc004-mandatory-pin-publisher:"):]
static={
 "needs_gate":"needs: rc004-freeze-gate" in publisher,
 "success_if":"needs.rc004-freeze-gate.result == 'success'" in publisher,
 "contents_write":"contents: write" in publisher,
 "no_checkout":"actions/checkout" not in publisher,
 "no_candidate_reviews_exec":"reviews/" not in publisher,
 "no_python":"python " not in publisher,
 "explicit_non201":'if [ "$code" != "201" ]; then' in publisher and "exit 1" in publisher,
 "commit_comment_endpoint":"/commits/" in publisher and "/comments" in publisher,
 "no_other_write_endpoint":"/git/refs" not in publisher and "/contents/" not in publisher and "/releases" not in publisher and "/dispatches" not in publisher,
 "no_remote_recheck":"git ls-remote" not in publisher,
}
print("STATIC",json.dumps(static,sort_keys=True))
def shell_case(label,code,curl_rc=0):
    script="set -euo pipefail\ncurl() { printf '%s' "+json.dumps(code)+"; return "+str(curl_rc)+"; }\ncode=\"$(curl ignored)\"\nif [ \"$code\" != \"201\" ]; then echo diagnostic; exit 1; fi\nexit 0\n"
    cp=subprocess.run(["bash","-c",script],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print(json.dumps({"label":label,"http_text":code,"curl_rc":curl_rc,"shell_exit":cp.returncode,"stdout":cp.stdout.splitlines()},sort_keys=True))
for code in ["200","201","202","204","301","302","400","401","403","404","409","422","429","500","","abc"]:
    shell_case("http_"+(code or "empty"),code,0)
for rc in [1,6,7,28]:
    shell_case("transport_"+str(rc),"000",rc)
