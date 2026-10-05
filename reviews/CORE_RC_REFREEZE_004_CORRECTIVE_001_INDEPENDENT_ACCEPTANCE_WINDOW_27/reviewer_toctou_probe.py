#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
workflow=Path(sys.argv[1]).read_text(encoding="utf-8")
t=workflow.index("      - name: Terminal immutability and protected-drift gate")
u=workflow.index("      - name: Upload complete RC004 evidence bundle")
p=workflow.index("  rc004-mandatory-pin-publisher:")
publisher=workflow[p:]
checks={"terminal_before_upload":t<u,"upload_before_publisher":u<p,"publisher_needs_gate":"needs: rc004-freeze-gate" in publisher,"publisher_condition_only_gate_success":"needs.rc004-freeze-gate.result == 'success'" in publisher,"publisher_has_no_remote_head_recheck":"git ls-remote" not in publisher and "TERMINAL_REMOTE_HEAD_MISMATCH" not in publisher}
print("STATIC",json.dumps(checks,sort_keys=True))
def out(*a,cwd=None): return subprocess.check_output(a,cwd=cwd,text=True).strip()
with tempfile.TemporaryDirectory() as td:
    root=Path(td); work=root/"work"; remote=root/"remote.git"
    subprocess.check_call(["git","init","-q",str(work)])
    subprocess.check_call(["git","-C",str(work),"config","user.email","reviewer@example.invalid"])
    subprocess.check_call(["git","-C",str(work),"config","user.name","W27 Reviewer"])
    (work/"f").write_text("A\n"); subprocess.check_call(["git","-C",str(work),"add","f"]); subprocess.check_call(["git","-C",str(work),"commit","-q","-m","A"]); a=out("git","-C",str(work),"rev-parse","HEAD")
    (work/"f").write_text("B\n"); subprocess.check_call(["git","-C",str(work),"commit","-q","-am","B"]); b=out("git","-C",str(work),"rev-parse","HEAD")
    subprocess.check_call(["git","init","-q","--bare",str(remote)])
    subprocess.check_call(["git","-C",str(work),"remote","add","origin",str(remote)])
    subprocess.check_call(["git","-C",str(work),"push","-q","origin",f"{a}:refs/heads/canonical"])
    before=out("git","ls-remote",str(remote),"refs/heads/canonical").split()[0]; terminal_pass=(before==a)
    subprocess.check_call(["git","-C",str(work),"push","-q","--force","origin",f"{b}:refs/heads/canonical"])
    after=out("git","ls-remote",str(remote),"refs/heads/canonical").split()[0]; drift=(after!=a)
    publisher_success=True
    fg=terminal_pass and drift and publisher_success and checks["publisher_has_no_remote_head_recheck"]
    print("REPRO",json.dumps({"event_sha":a,"terminal_remote_head":before,"post_terminal_remote_head":after,"terminal_check_passed":terminal_pass,"branch_drift_after_terminal":drift,"job_a_result":"success","publisher_http":"201","publisher_success_without_recheck":publisher_success,"old_run_can_remain_success":fg},sort_keys=True))
    print("TOCTOU_FALSE_GREEN_REPRODUCED" if fg else "TOCTOU_FALSE_GREEN_NOT_REPRODUCED")
