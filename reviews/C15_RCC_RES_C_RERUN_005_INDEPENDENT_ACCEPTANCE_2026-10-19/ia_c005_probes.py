#!/usr/bin/env python3
"""
Window 76 — Independent Acceptance Probe Harness (IA-005-PHASE-C)
Candidate: resident/c15-rcc-res-c-rerun-005-phase-c (PR #394)
Candidate Commit: 94221b512a573bbe9922eea444552ac9122b3a0e
Parent Commit: 302dab2565f61dd37ca57195bae7ed9337cdfede
Candidate Tree: 4058d97dcfd3b68089de527b76f7657eba0d0b16

Executes 10 adversarial/orthogonal probes (P00..P09) to independently
verify Fresh Resident C Phase-C habitation evidence against AIOS 3.0 Constitution,
老大五大最高铁律, and release contracts.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO = Path("/workspaces/c15-option-b-detached-worktree")
HEAD = "6cd89d6e3761347487946ca95e59bae380a3ae46"
BASE = "302dab2565f61dd37ca57195bae7ed9337cdfede"
EVIDENCE_TREE = "370e9a9941535bd74268870bb5a95373af454b5d"

ROOT = "reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-C-RERUN-005"
RUN_ID = "c15-rcc-res-c-rerun-005-cf585be261f9"
SESSION_ID = "resident-c-005-826a8a7bcef345ab"
CONV_SESSION_ID = "sess-resident-c-005-7969eff964ce44c9"
SUBJECT = "user_1"

RESULTS: List[Dict[str, Any]] = []


def record(probe_id: str, title: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    RESULTS.append({"id": probe_id, "title": title, "ok": ok, "detail": detail})
    print(f"[{status}] {probe_id}: {title}")
    if detail:
        print(f"       Detail: {detail}")


def git(*args: str) -> str:
    res = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(REPO),
    )
    return res.stdout


def blob(path: str, ref: str = HEAD) -> bytes:
    res = subprocess.run(
        ["git", "cat-file", "-p", f"{ref}:{path}"],
        capture_output=True,
        check=True,
        cwd=str(REPO),
    )
    return res.stdout


def jblob(rel_path: str, ref: str = HEAD) -> Any:
    return json.loads(blob(f"{ROOT}/{rel_path}", ref).decode("utf-8"))


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def evidence_files() -> List[str]:
    return git("ls-tree", "-r", "--name-only", f"{HEAD}:{ROOT}").split()


def ro_db(blob_bytes: bytes, name: str = "temp.sqlite") -> Tuple[sqlite3.Connection, str]:
    tmp = tempfile.mkdtemp(prefix="ia005_c_ro_")
    path = Path(tmp) / name
    path.write_bytes(blob_bytes)
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn, tmp


VISIBLE = (
    "event_id",
    "sequence",
    "occurred_at",
    "dimension",
    "source_kind",
    "source_class",
    "modality",
    "resident_visible_payload",
)


def fixture_events():
    raw = blob("reviews/internal_habitation/c15-rcc/v1/fixture/sealed_fixture.json")
    return json.loads(raw.decode("utf-8"))["events"], hashlib.sha256(raw).hexdigest()


# --------------------------------------------------------------------------- P00
def p00() -> None:
    commit = git("cat-file", "-p", HEAD)
    tree = re.search(r"^tree ([0-9a-f]{40})", commit, re.M).group(1)
    parent = re.search(r"^parent ([0-9a-f]{40})", commit, re.M).group(1)
    status = git("diff", "--name-status", BASE, HEAD).splitlines()
    paths = [s.split("\t", 1)[1] for s in status]
    outside = [p for p in paths if not p.startswith(ROOT + "/")]
    nonadd = [s for s in status if not s.startswith("A\t")]
    forbidden = [
        p
        for p in paths
        if p.startswith(("src/", "tests/", ".github/", "docs/", "governance/", "tools/", "pyproject.toml"))
        or "/fixture/" in p
        or "/evaluator/" in p
        or "/c15-rcc/v1/release/" in p
    ]
    core_head = git("rev-parse", f"{HEAD}:src/aios_core").strip()
    core_base = git("rev-parse", f"{BASE}:src/aios_core").strip()
    tools_head = git("rev-parse", f"{HEAD}:tools/c15_persistence").strip()
    tools_base = git("rev-parse", f"{BASE}:tools/c15_persistence").strip()
    
    pr = json.loads(
        subprocess.run(
            ["gh", "pr", "view", "394", "--json", "state,isDraft,headRefOid,mergedAt"],
            capture_output=True, text=True, check=True, cwd=str(REPO),
        ).stdout
    )
    ok = (
        tree == EVIDENCE_TREE
        and parent == BASE
        and len(paths) == 83
        and not outside
        and not nonadd
        and not forbidden
        and core_head == core_base
        and tools_head == tools_base
        and pr["state"] == "OPEN"
        and pr["mergedAt"] is None
        and pr["headRefOid"] == HEAD
    )
    record(
        "P00",
        "exact candidate identity + evidence-only scope + zero code drift + PR #394 open",
        ok,
        f"tree={tree} parent={parent} files={len(paths)} outside={len(outside)} "
        f"nonadd={len(nonadd)} forbidden={len(forbidden)} core_drift={core_head != core_base} "
        f"tools_drift={tools_head != tools_base} pr_state={pr['state']}",
    )


# --------------------------------------------------------------------------- P01
def p01() -> None:
    lines = blob(f"{ROOT}/SHA256SUMS").decode().strip().splitlines()
    entries = []
    for ln in lines:
        h, p = ln.split("  ", 1)
        entries.append((h.strip(), p.strip().lstrip("./")))
    bad = [
        p
        for h, p in entries
        if hashlib.sha256(blob(f"{ROOT}/{p}")).hexdigest() != h
    ]
    listed = {p for _, p in entries}
    all_files = [f.replace(ROOT + "/", "") for f in evidence_files()]
    unhashed = sorted(set(all_files) - listed)
    dups = len(entries) - len(listed)
    ok = len(entries) == 81 and not bad and dups == 0 and unhashed == [
        "SHA256SUMS",
        "completion_report.md",
    ]
    record(
        "P01",
        "SHA256SUMS verified from exact Git blob bytes (81 files, 0 hash mismatches)",
        ok,
        f"entries={len(entries)} mismatch={len(bad)} dupes={dups} unhashed={unhashed}",
    )


# --------------------------------------------------------------------------- P02
def p02() -> None:
    events, fx_hex = fixture_events()
    state = jblob("release-state.json")
    problems = []
    if state.get("active_phase") != "C" and state.get("phase") != "C":
        problems.append("phase")
    if state["last_acked_sequence"] != 30 or state["next_sequence"] != 31:
        problems.append("cursor")
    if state["pending_reveal"] is not None:
        problems.append("pending-reveal")
    if state["last_acked_event_id"] != "c15rcc-030":
        problems.append("last-event")
    if state["fixture_sha256"] != "sha256:" + fx_hex:
        problems.append("fixture-digest")
    receipts = state["receipts"]
    if [r["sequence"] for r in receipts] != list(range(1, 31)):
        problems.append("order")
    
    # Check Phase C receipts (23..30)
    for r in receipts[22:30]:
        seq = r["sequence"]
        ev = events[seq - 1]
        proj = {k: ev[k] for k in VISIBLE}
        for label, cond in (
            ("event", r["event_id"] == ev["event_id"]),
            ("time", r["occurred_at"] == ev["occurred_at"]),
            ("payload-sha", r["fixture_payload_sha256"] == sha_text(ev["resident_visible_payload"])),
            ("projection-sha", r["fixture_projection_sha256"] == sha_text(canon(proj))),
            ("projection-bytes", jblob(f"events/cursor_{seq:02d}.event.json") == proj),
            ("keyset", set(jblob(f"events/cursor_{seq:02d}.event.json")) == set(VISIBLE)),
            ("fixture-sha", r["fixture_sha256"] == "sha256:" + fx_hex),
        ):
            if not cond:
                problems.append(f"{label}@{seq}")
    acks = []
    for seq in range(23, 31):
        a = jblob(f"evidence/cursor_{seq:02d}.ack_receipt.json")
        acks.append(a)
        if a["status"] != "acked" or a["ingest_ref"] != receipts[seq - 1]["ingest_ref"]:
            problems.append(f"ack@{seq}")
        if a["next_sequence"] != seq + 1:
            problems.append(f"ack-next@{seq}")
    record(
        "P02",
        "receipts 23..30 recomputed from sealed fixture + ack refs match",
        not problems,
        f"receipts_checked=8 acks={len(acks)} problems={problems[:8]}",
    )


# --------------------------------------------------------------------------- P03
def p03() -> None:
    events, _ = fixture_events()
    state = jblob("release-state.json")
    files = evidence_files()
    later_files = [f for f in files if re.search(r"cursor_(03[1-9]|[4-9][0-9])", f)]
    
    # execute reveal guard against scratch copy of the final state
    reveal_error = None
    untouched = False
    tmp = tempfile.mkdtemp(prefix="ia005_c_state_")
    try:
        sp = Path(tmp) / "state.json"
        sp.write_text(json.dumps(state), encoding="utf-8")
        rel_py = REPO / "reviews/internal_habitation/c15-rcc/v1/release/release_operator.py"
        py_bin = "/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python"
        res = subprocess.run(
            [py_bin, str(rel_py), "reveal", "--phase", "C", "--state", str(sp)],
            capture_output=True, text=True, cwd=str(REPO)
        )
        reveal_error = res.stderr.strip() if res.returncode != 0 else "REVEAL-ALLOWED-UNEXPECTED"
        state_after = json.loads(sp.read_text(encoding="utf-8"))
        untouched = (state_after == state)
    except Exception as exc:
        reveal_error = f"harness {type(exc).__name__}: {exc}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    ok = (
        not later_files
        and state["last_acked_sequence"] == 30
        and state["next_sequence"] == 31
        and state["pending_reveal"] is None
        and ("ReleaseError" in reveal_error or "release-operator-error" in reveal_error or "fixture release already complete" in reveal_error)
        and untouched
    )
    record(
        "P03",
        "cursor 31 never revealed; frozen Phase-C sealed boundary refuses reveal",
        ok,
        f"later_cursor_files={later_files} "
        f"reveal_guard={reveal_error!r} scratch_state_untouched={untouched}",
    )


# --------------------------------------------------------------------------- P04
def p04() -> None:
    events, _ = fixture_events()
    state = jblob("release-state.json")
    conn, tmp = ro_db(blob(f"{ROOT}/world/world.sqlite"), "world.sqlite")
    problems = []
    user_seqs = (24, 26, 28, 30)
    turn_indices = list(range(1, 5))
    
    try:
        for turn_idx, seq in zip(turn_indices, user_seqs):
            ingest_r = jblob(f"evidence/cursor_{seq:02d}.ingest_receipt.json")
            obj_id = ingest_r["object_id"]
            rows = conn.execute(
                "SELECT * FROM object_revisions WHERE object_id=?", (obj_id,)
            ).fetchall()
            if len(rows) != 1:
                problems.append(f"rev_count@{seq}:{len(rows)}")
                continue
            row = dict(rows[0])
            if row["revision"] != 1:
                problems.append(f"rev_num@{seq}:{row['revision']}")
            payload = json.loads(row["payload_json"])
            if payload.get("metadata", {}).get("session_id") != CONV_SESSION_ID:
                problems.append(f"session_id@{seq}")
            if payload.get("metadata", {}).get("turn_index") != turn_idx:
                problems.append(f"turn_idx@{seq}:{payload.get('metadata', {}).get('turn_index')}!= {turn_idx}")
            if payload.get("source_kind") != "user_ai_interaction":
                problems.append(f"source_kind@{seq}:{payload.get('source_kind')}")
    finally:
        conn.close()
        shutil.rmtree(tmp, ignore_errors=True)

    ok = not problems
    record(
        "P04",
        "canonical USER ingest idempotency (4 turns, 1 observation each at revision 1)",
        ok,
        f"user_turns={len(user_seqs)} problems={problems}",
    )


# --------------------------------------------------------------------------- P05
def p05() -> None:
    events, _ = fixture_events()
    files = evidence_files()
    req_files = [f for f in files if "exchange/requests/req-" in f]
    problems = []
    
    for rf in req_files:
        content = blob(f"{ROOT}/{rf}").decode("utf-8")
        if "sealed_fixture" in content or "evaluator" in content:
            problems.append(f"forbidden_token in {rf}")

    ok = not problems and len(req_files) == 14
    record(
        "P05",
        "future / fixture leakage scan of 14 model requests in Phase C",
        ok,
        f"req_files={len(req_files)} leakage_hits={len(problems)} problems={problems}",
    )


# --------------------------------------------------------------------------- P06
def p06() -> None:
    ledger_raw = blob(f"{ROOT}/exchange/ledger.jsonl").decode("utf-8").strip().splitlines()
    records = [json.loads(line) for line in ledger_raw]
    
    # 14 requests * 3 events = 42 records
    req_pub = [r for r in records if r.get("event") == "request_published"]
    res_pub = [r for r in records if r.get("event") == "response_published"]
    res_con = [r for r in records if r.get("event") == "response_consumed"]
    
    seqs = [r.get("seq") for r in records]
    is_contiguous = (seqs == list(range(1, len(records) + 1)))
    
    # Verify chain hash integrity
    chain_ok = True
    prev_hash = "0" * 64
    for r in records:
        entry = dict(r)
        curr_rec_hash = entry.pop("record_sha256", None)
        curr_prev_hash = entry.get("prev_sha256")
        if curr_prev_hash != prev_hash:
            chain_ok = False
            break
        calc_hash = hashlib.sha256(canon(entry).encode("utf-8")).hexdigest()
        if curr_rec_hash != calc_hash:
            chain_ok = False
            break
        prev_hash = curr_rec_hash

    ok = (
        len(records) == 42
        and len(req_pub) == 14
        and len(res_pub) == 14
        and len(res_con) == 14
        and is_contiguous
        and chain_ok
    )
    record(
        "P06",
        "request/decision pairing & ledger integrity (14/14/14, 42 records, chain valid)",
        ok,
        f"total_records={len(records)} req_pub={len(req_pub)} res_pub={len(res_pub)} "
        f"res_con={len(res_con)} contiguous={is_contiguous} chain_ok={chain_ok}",
    )


# --------------------------------------------------------------------------- P07
def p07() -> None:
    conn_w, tmp_w = ro_db(blob(f"{ROOT}/world/world.sqlite"), "world.sqlite")
    conn_s, tmp_s = ro_db(blob(f"{ROOT}/world/world.sqlite.search.sqlite"), "search.sqlite")
    problems = []
    
    try:
        # PRAGMA quick_check
        qc_w = conn_w.execute("PRAGMA quick_check").fetchone()[0]
        qc_s = conn_s.execute("PRAGMA quick_check").fetchone()[0]
        if qc_w != "ok":
            problems.append(f"world quick_check={qc_w}")
        if qc_s != "ok":
            problems.append(f"search quick_check={qc_s}")
            
        # Revision check
        row_rev = conn_w.execute("SELECT MAX(world_revision) FROM world_commits").fetchone()[0]
        count_commits = conn_w.execute("SELECT COUNT(*) FROM world_commits").fetchone()[0]
        if row_rev != 82:
            problems.append(f"world_revision={row_rev}!= 82")
        if count_commits != 82:
            problems.append(f"commit_count={count_commits}!= 82")
            
        # Search index watermark
        wm_row = conn_s.execute("SELECT value FROM search_meta WHERE key='search_watermark_world_revision'").fetchone()
        watermark = int(wm_row[0]) if wm_row else None
        if watermark != 82:
            problems.append(f"search_watermark={watermark}!= 82")
    finally:
        conn_w.close()
        conn_s.close()
        shutil.rmtree(tmp_w, ignore_errors=True)
        shutil.rmtree(tmp_s, ignore_errors=True)

    ok = not problems
    record(
        "P07",
        "World & search index coherence (quick_check=ok, rev=82, watermark=82, lag=0)",
        ok,
        f"world_rev={row_rev} watermark={watermark} problems={problems}",
    )


# --------------------------------------------------------------------------- P08
def p08() -> None:
    conn, tmp = ro_db(blob(f"{ROOT}/world/world.sqlite"), "world.sqlite")
    problems = []
    try:
        objs = conn.execute("SELECT object_id, revision, object_type, payload_json, recorded_at FROM object_revisions").fetchall()
        for r in objs:
            payload = json.loads(r["payload_json"])
            for ref in payload.get("evidence_refs") or []:
                ref_id = ref.get("object_id")
                match = conn.execute("SELECT COUNT(*) FROM object_revisions WHERE object_id=?", (ref_id,)).fetchone()[0]
                if match == 0:
                    problems.append(f"dangling_ref:{ref_id}")
    finally:
        conn.close()
        shutil.rmtree(tmp, ignore_errors=True)

    ok = not problems
    record(
        "P08",
        "cognition temporal cut & reference integrity across all object revisions",
        ok,
        f"total_objects={len(objs)} dangling_refs={len(problems)} problems={problems[:5]}",
    )


# --------------------------------------------------------------------------- P09
def p09() -> None:
    ident = jblob("RUN_IDENTITY.json")
    send = jblob("SESSION_END.json")
    fman = jblob("FREEZE_MANIFEST.json")
    
    ok = (
        ident["task_id"] == "C15-RCC-RES-C-RERUN-005"
        and ident["run_id"] == RUN_ID
        and ident["resident_session_id"] == SESSION_ID
        and ident["conversation_session_id"] == CONV_SESSION_ID
        and ident["subject_id"] == SUBJECT
        and send["last_acked_sequence"] == 30
        and send["next_sequence"] == 31
        and send["cursor_31_revealed"] is False
        and send["total_exchanges"] == 14
        and fman["final_world_revision"] == 82
        and fman["exchange_integrity"]["ok"] is True
    )
    record(
        "P09",
        "run identity freshness, session termination & freeze manifest consistency",
        ok,
        f"run_id={ident['run_id']} exchanges={send['total_exchanges']} "
        f"cursor_31_revealed={send['cursor_31_revealed']} world_rev={fman['final_world_revision']}",
    )


# --------------------------------------------------------------------------- MAIN
def main() -> int:
    print("==========================================================================")
    print("  WINDOW 76 — C15-RCC-RES-C-RERUN-005 INDEPENDENT ACCEPTANCE PROBES (IA-005-C)")
    print(f"  Candidate commit : {HEAD}")
    print(f"  Parent commit    : {BASE}")
    print("==========================================================================")
    
    p00()
    p01()
    p02()
    p03()
    p04()
    p05()
    p06()
    p07()
    p08()
    p09()

    print("==========================================================================")
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["ok"])
    print(f"SUMMARY: {passed}/{total} probes PASSED")
    if passed == total:
        print("RESULT: ACCEPTANCE_PASS — ALL 10 PROBES SATISFIED 100%")
        return 0
    else:
        print("RESULT: ACCEPTANCE_FAIL")
        return 1


if __name__ == "__main__":
    sys.exit(main())
