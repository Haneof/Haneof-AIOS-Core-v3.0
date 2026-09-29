#!/usr/bin/env python3
"""Final restart probe rev2 (rev1 defect: compared raw SQLite file bytes; opening a SQLite DB under frozen Core rewrites file-header bytes without logical change. rev2 compares logical iterdump of World + index before/after open and after due; raw bytes still recorded): run under frozen-RC venv. Args: <repo> <cand> <harness_dir> <out>"""
import sys, json, os, shutil, subprocess, tempfile, hashlib, datetime, pathlib
REPO, CAND, HD, OUT = sys.argv[1:5]
E = "reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003"
sys.path.insert(0, HD)
import aios_core
from aios_core.headless.core import HeadlessConfig, HeadlessCore
from aios_exchange.bridge import ExchangeBridge
td = pathlib.Path(tempfile.mkdtemp()); subprocess.check_call(f"git -C {REPO} archive {CAND} {E}/run | tar -x -C {td}", shell=True)
run = td / E / "run"
w = run / "world/c15-res-a-c003.world.sqlite"; i = run / "world/c15-res-a-c003.world.search.sqlite"
h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
import sqlite3
def L(p):
    c = sqlite3.connect(str(p)); x = "\n".join(c.iterdump()); c.close(); return hashlib.sha256(x.encode()).hexdigest()
lb = {"world": L(w), "index": L(i)}
before = {"world": h(w), "index": h(i)}
calls = []
def handler(snapshot):
    calls.append(repr(snapshot)[:500]); raise RuntimeError("REVIEWER_PROBE: model invoked during restart")
ev13 = json.loads((run / "events/cursor_13.event.json").read_text())
occ = None
def find(o):
    global occ
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "occurred_at" and occ is None: occ = v
            find(v)
    elif isinstance(o, list): [find(x) for x in o]
find(ev13)
core = HeadlessCore(config=HeadlessConfig(world_path=w, index_path=i, subject_id="user_1"), model_handler=handler)
core.start(); st = core.status(); core.stop()
after_open = {"world": h(w), "index": h(i)}; lo = {"world": L(w), "index": L(i)}
core = HeadlessCore(config=HeadlessConfig(world_path=w, index_path=i, subject_id="user_1"), model_handler=handler)
core.start(); err = None
try:
    dr = core.process_due_work(now=datetime.datetime.fromisoformat(occ), max_wakes=8, include_periodic_review=True)
    dr = repr(dr)[:3000]
except Exception as ex: err = repr(ex); dr = None
st2 = core.status(); core.stop()
la = {"world": L(w), "index": L(i)}
b = ExchangeBridge(run / "exchange"); rs = b.recovery_state(); integ = b.integrity()
out = {"aios_core_file": aios_core.__file__, "python": sys.version, "status_restart": st, "status_after_due": st2,
       "cursor13_occurred_at": occ, "due_result": dr, "due_error": err, "model_calls": calls,
       "hash_before": before, "hash_after_open": after_open, "hash_after_due": {"world": h(w), "index": h(i)},
       "exchange_recovery_state": rs, "logical_before": lb, "logical_after_open": lo, "logical_after_due": la, "exchange_integrity": integ}
ok = (st["world_revision"] == 38 and st["index_watermark"] == 38 and st["index_lag"] == 0 and not calls and err is None
      and lb == lo == la and st2["world_revision"] == 38 and rs["classification"] == "COMPLETE" and integ["ok"] and integ["chain"]["records"] == 63)
out["result"] = "PASS" if ok else "FAIL"
json.dump(out, open(OUT, "w"), indent=1, default=str); print(out["result"], st, st2, err, calls[:1])
