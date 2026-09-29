#!/usr/bin/env python3
"""Independent reviewer probes rev2 (rev1 defect: generic English n-grams from later payloads, e.g. 'authorization', matched frozen-Core capability schema text; rev2 excludes n-grams that occur in frozen Core src/aios_core or accepted harness source; nothing else changed) for C15-RCC-RES-A-RERUN-004-CORRECTIVE-003 IA.
Usage: ia_probes_rev1.py <repo> <candidate_sha> <out_json>
Pure-stdlib (static) probes. Restart probe is separate (ia_restart_probe_rev1.py)."""
import hashlib, json, os, re, subprocess, sys, sqlite3, tempfile, pathlib
REPO, CAND, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
E = "reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003"
PARENT = "f7bcec4e558ebb4c6a11b7b45afe361cc659ef66"
def git(*a, raw=False):
    b = subprocess.check_output(["git", "-C", REPO, *a]); return b if raw else b.decode()
def blob(p): return git("show", f"{CAND}:{E}/{p}", raw=True)
def js(p): return json.loads(blob(p))
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(o): return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
R = {}
def rec(pid, ok, **d): R[pid] = {"result": "PASS" if ok else "FAIL", **d}
FILES = sorted(l[len(E)+1:] for l in git("ls-tree", "-r", "--name-only", CAND, E).splitlines())
FIX = json.loads(git("show", "origin/main:reviews/internal_habitation/c15-rcc/v1/fixture/sealed_fixture.json"))["events"]
PA = sorted([e for e in FIX if e["phase"] == "A"], key=lambda e: e["sequence"])
ALL = sorted(FIX, key=lambda e: e["sequence"])

# P01 scope
ns = git("diff", "--name-status", f"{CAND}^", CAND).splitlines()
parents = git("rev-list", "--parents", "-n1", CAND).split()[1:]
bad = [l for l in ns if not (l.startswith("A\t") and l.split("\t")[1].startswith(E + "/"))]
rec("P01_scope", parents == [PARENT] and git("rev-parse", f"{CAND}^{{tree}}").strip() == "a64b60ad1e64bcb930003f030246baafdae3eb8a"
    and len(ns) == 212 and not bad and git("rev-list", "--count", f"{PARENT}..{CAND}").strip() == "1",
    parents=parents, changed=len(ns), out_of_scope=bad)

# P02 checksums
sums = {}
for l in blob("SHA256SUMS").decode().splitlines():
    h, p = l.split(maxsplit=1); sums[p.lstrip("*").removeprefix("./")] = h
others = [f for f in FILES if f != "SHA256SUMS"]
mism = [p for p, h in sums.items() if p not in FILES or sha(blob(p)) != h]
uncovered = [f for f in others if f not in sums]
exp = {"SHA256SUMS": "1eee5df0650ed03b50bfe0ef558d93076d13ecb32772b036c91b9d8cd8c84bef",
       "run/exchange/ledger.jsonl": "3b2b9e902133c31cc583491aae55834ee9cb71a9bea9ca50a36fd7e8b81da021",
       "run/world/c15-res-a-c003.world.sqlite": "0d6970ed99367a456e4baa29092bde8f15bc7544496095cc87ad9f029e2603b2",
       "run/world/c15-res-a-c003.world.search.sqlite": "79c877a4bf75091fa90ae81076a6bdb2e265cf6376b657c3f195e9e91f9844e5",
       "run/release-state.json": "6b90fc7a09bce7d575dbcb783dcbe838cab81c2e358515adbb5dca9731f57c37",
       "run/FREEZE_MANIFEST.json": "bc66ad55e0dc8dbdb483e644f850c4c4753ae6ba45ba400cbda3b28071f89298"}
got = {p: sha(blob(p)) for p in exp}
rec("P02_checksums", len(FILES) == 212 and len(sums) == 211 and not mism and not uncovered and got == exp,
    files=len(FILES), entries=len(sums), mismatches=mism, uncovered=uncovered, expected_vs_got={p: [exp[p], got[p]] for p in exp})

# P03 ledger chronology
L = [json.loads(x) for x in blob("run/exchange/ledger.jsonl").decode().splitlines() if x.strip()]
errs = []; prev = "0" * 64; per = {}
for i, r in enumerate(L, 1):
    if r["seq"] != i: errs.append(f"seq {i}")
    if r["prev_sha256"] != prev: errs.append(f"prev {i}")
    body = {k: v for k, v in r.items() if k != "record_sha256"}
    if sha(canon(body)) != r["record_sha256"]: errs.append(f"hash {i}")
    prev = r["record_sha256"]; per.setdefault(r["request_id"], []).append(r)
order = ["request_published", "response_published", "response_consumed"]
for rid, rs in per.items():
    if [x["event"] for x in rs] != order: errs.append(f"order {rid}")
    q = blob(f"run/exchange/requests/{rid}.json"); s = blob(f"run/exchange/responses/{rid}.json")
    if any(x["request_sha256"] != sha(q) for x in rs): errs.append(f"reqsha {rid}")
    if any(x["response_sha256"] != sha(s) for x in rs[1:]): errs.append(f"respsha {rid}")
reqfiles = sorted(f.split("/")[-1][:-5] for f in FILES if f.startswith("run/exchange/requests/"))
respfiles = sorted(f.split("/")[-1][:-5] for f in FILES if f.startswith("run/exchange/responses/"))
rec("P03_exchange_chronology", not errs and len(L) == 63 and len(per) == 21 and reqfiles == respfiles == sorted(per)
    and prev == "7f8afff395442a1d926144bfccb51429faf807490660fd95a9df65616ebba691",
    records=len(L), requests=len(per), head=prev, errors=errs)

# P04 cursor / ingest / ACK chain vs sealed fixture
errs = []
for k in range(1, 14):
    ev = js(f"run/events/cursor_{k:02d}.event.json")
    fx = PA[k - 1]
    flat = json.dumps(ev, ensure_ascii=False)
    if fx["event_id"] not in flat or fx["resident_visible_payload"] not in flat or fx["occurred_at"] not in flat:
        errs.append(f"cursor{k} event != fixture seq {k}")
    for f in (f"run/evidence/cursor_{k:02d}.ingest_receipt.json", f"run/evidence/cursor_{k:02d}.ack_receipt.json"):
        if f.split("/", 1)[1] and f[len(''):] and f.replace('', '') not in [ 'run/'+x[4:] if False else x for x in FILES]: errs.append(f"missing {f}")
rs = js("run/release-state.json")
flat = json.dumps(rs, ensure_ascii=False)
later_ids = [e["event_id"] for e in ALL if e["sequence"] >= 14]
leak14 = [i for i in later_ids if i in flat]
rec("P04_cursor_chain", not errs and not leak14, errors=errs, release_state_keys=list(rs) if isinstance(rs, dict) else None,
    later_ids_in_release_state=leak14, note="receipt ACK-ref binding details recorded in raw dump")
R["P04_cursor_chain"]["release_state"] = rs

# P05 future leak by cursor: map every request/response to its cursor via publish receipts / filenames & ledger order
def grams(t, n=10): return {t[i:i+n] for i in range(0, max(0, len(t) - n + 1))}
known = set()
for e in ALL: pass
fut_by_k = {}
TEMPLATE = ""
for root in (os.environ["FROZEN_SRC"], os.environ["HARNESS_SRC"]):
    for dp, _, fs in os.walk(root):
        for fn in fs:
            if fn.endswith(".py") or fn.endswith(".json") or fn.endswith(".md"):
                TEMPLATE += open(os.path.join(dp, fn), encoding="utf-8", errors="replace").read()
for k in range(1, 14):
    past = TEMPLATE + "".join(e["resident_visible_payload"] for e in ALL if e["sequence"] <= k)
    pastg = grams(past)
    fut = {}
    for e in ALL:
        if e["sequence"] > k:
            g = {x for x in grams(e["resident_visible_payload"]) if x not in pastg and not re.fullmatch(r"[\s\W\d]*", x)}
            fut[e["event_id"]] = g
    fut_by_k[k] = fut
# assign each request to cursor by the receipt files naming
req_cursor = {}
for f in FILES:
    m = re.match(r"run/evidence/cursor_(\d\d)\..*publish_receipt\.json$", f)
    if m:
        t = blob(f).decode()
        for rid in per:
            if rid in t: req_cursor.setdefault(rid, int(m.group(1)))
if "run/evidence/responses/cursor_01.resp_01.json" in FILES:
    pass
hits = []
for rid, k in sorted(req_cursor.items()):
    for side in ("requests", "responses"):
        t = blob(f"run/exchange/{side}/{rid}.json").decode("utf-8")
        t = json.loads(t); t = json.dumps(t, ensure_ascii=False)
        for eid, g in fut_by_k[k].items():
            if eid in t: hits.append([rid, side, k, "event_id", eid])
            h = [x for x in g if x in t]
            if len(h) >= 3: hits.append([rid, side, k, "payload_ngrams", eid, len(h), sorted(h)[:3]])
rec("P05_future_leak", len(req_cursor) == 21 and not hits, mapped=req_cursor, hits=hits)

# P06 forbidden startup / contamination strings in all resident-produced material
PAT = [r"TASK_BOARD", r"CURRENT_CHECKPOINT", r"governance/", r"PM_REVIEW_READY", r"adjudicat", r"PR ?#?29[0-9]", r"#292", r"#294",
       r"RERUN-00[123]\b", r"RERUN-004(?!-CORRECTIVE-003)", r"CORRECTIVE-00[12]\b(?!-)", r"sealed_fixture", r"fixture/", r"evaluator",
       r"release_operator", r"resident/runs/", r"Resident ?[BC]\b", r"INDEPENDENT_ACCEPTANCE", r"expected_semantics", r"c15rcc-0(1[4-9]|[2-9]\d)"]
hits = []
scan = [f for f in FILES if (f.startswith("run/exchange/") or f.startswith("run/evidence/responses/")) and f.endswith(".json")]
for f in scan:
    t = blob(f).decode("utf-8", "replace")
    for p in PAT:
        for m in re.finditer(p, t, flags=re.I):
            hits.append([f, p, t[max(0, m.start()-60):m.end()+60]])
rec("P06_forbidden_material", not hits, scanned=len(scan), hits=hits[:200], total_hits=len(hits))

# P07 responses provenance markers + no deterministic responder
marks = {}
for rid in per:
    r = json.loads(blob(f"run/exchange/responses/{rid}.json"))
    s = json.dumps(r, ensure_ascii=False)
    marks[rid] = {"external": "EXTERNAL_CURRENT_RESIDENT_SESSION" in s, "deterministic": bool(re.search(r"deterministic|synthetic|test_responder", s, re.I))}
rec("P07_response_provenance", all(v["external"] and not v["deterministic"] for v in marks.values()), marks=marks)

# P08 World / index introspection
td = tempfile.mkdtemp()
wp = os.path.join(td, "w.sqlite"); ip = os.path.join(td, "i.sqlite")
open(wp, "wb").write(blob("run/world/c15-res-a-c003.world.sqlite")); open(ip, "wb").write(blob("run/world/c15-res-a-c003.world.search.sqlite"))
def tables(p):
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    out = {t: c.execute(f'select count(*) from "{t}"').fetchone()[0] for (t,) in c.execute("select name from sqlite_master where type='table'")}
    ic = c.execute("pragma integrity_check").fetchone()[0]; c.close(); return out, ic
wt, wic = tables(wp); it, iic = tables(ip)
# future text / id leak into world
c = sqlite3.connect(f"file:{wp}?mode=ro", uri=True)
dump = "\n".join(c.iterdump()); c.close()
fut_ids = [e["event_id"] for e in ALL if e["sequence"] >= 14 and e["event_id"] in dump]
g14 = fut_by_k[13]; wl = {eid: len([x for x in g if x in dump]) for eid, g in g14.items()}
wl = {k: v for k, v in wl.items() if v >= 3}
# USER duplicate ingest: count occurrences of each USER payload as full text
dup = {}
for e in PA[:13]:
    if e["source_class"] == "USER":
        dup[e["event_id"]] = dump.count(e["resident_visible_payload"])
rec("P08_world_coherence", wic == "ok" and iic == "ok" and not fut_ids and not wl,
    world_tables=wt, index_tables=it, future_ids=fut_ids, future_ngram_hits=wl, user_payload_occurrences=dup,
    note="user payload occurrence counts are informational; canonical dedupe verified in raw dump review")
json.dump({"candidate": CAND, "probes": R}, open(OUT, "w"), ensure_ascii=False, indent=1, default=str)
print({k: v["result"] for k, v in R.items()})
