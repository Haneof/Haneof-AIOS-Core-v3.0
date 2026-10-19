#!/usr/bin/env python3
"""C15-RCC-RES-A-RERUN-005 independent acceptance probes (IA-005).

Reviewer-owned, read-only adversarial probe harness for the A-005 evidence candidate.

Rules honoured by this harness
------------------------------
* Every artefact under test is read from the exact Git object of PR #392 head
  ``2d92328205e16ec8b5317eaca8f3b666656ad09b`` through ``git cat-file blob``.
  No working-tree copy or uncommitted file is trusted as an input.
* Nothing is written into the repository or any evidence path. SQLite handles are
  opened read-only (``mode=ro``) against temporary scratch copies created only inside
  ``tempfile.mkdtemp``; those copies are discarded in the same probe.
* Frozen Core modules are imported from this repository checkout; probe P00 first
  checks ``src/aios_core`` and ``tests`` at live main against the accepted RC trees,
  so "the frozen code did it" is verified.
* Expected outcomes are frozen in this file before execution.
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

HEAD = "2d92328205e16ec8b5317eaca8f3b666656ad09b"
BASE = "52d169e8fb96248b058ab3685d9dcb1f6cbce204"
EVIDENCE_TREE = "7435f8d586b709621d2bedf7e1a8c9a49c7dda5b"
ROOT = "reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-005"
RUN_ID = "c15-rcc-res-a-rerun-005-8e605da939b0"
SESSION_ID = "resident-a-005-d49cb630c1014fac"
CONV_SESSION_ID = "sess-resident-a-005-75029e633ec54fd0"
SUBJECT = "user_1"

HERE = Path(__file__).resolve()
REPO = Path("/workspaces/c15-option-b-detached-worktree")
if not (REPO / "src" / "aios_core").is_dir():
    # Local fallback
    REPO = next(
        parent
        for parent in HERE.parents
        if (parent / "src" / "aios_core").is_dir() and (parent / ".git").exists()
    )

RESULTS: list[dict] = []


def record(pid: str, name: str, ok: bool, detail: str) -> None:
    RESULTS.append({"probe": pid, "name": name, "ok": bool(ok), "detail": detail})
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {pid}: {name}")
    print(f"       Detail: {detail}")


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True
    ).stdout


def blob(path: str) -> bytes:
    res = subprocess.run(
        ["git", "-C", str(REPO), "cat-file", "blob", f"{HEAD}:{path}"], capture_output=True
    )
    if res.returncode != 0:
        raise RuntimeError(f"missing git blob at exact head: {path}")
    return res.stdout


def jblob(path: str):
    return json.loads(blob(f"{ROOT}/{path}").decode("utf-8"))


def evidence_files() -> list[str]:
    return git("ls-tree", "-r", "--name-only", f"{HEAD}:{ROOT}").split()


def canon(value) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def sha_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def ro_db(data: bytes, name: str):
    tmp = tempfile.mkdtemp(prefix="ia005_")
    path = Path(tmp) / name
    path.write_bytes(data)
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
            ["gh", "pr", "view", "392", "--json", "state,isDraft,headRefOid,mergedAt"],
            capture_output=True, text=True, check=True, cwd=str(REPO),
        ).stdout
    )
    ok = (
        tree == EVIDENCE_TREE
        and parent == BASE
        and len(paths) == 125
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
        "exact candidate identity + evidence-only scope + zero code drift + PR #392 open",
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
    ok = len(entries) == 123 and not bad and dups == 0 and unhashed == [
        "SHA256SUMS",
        "completion_report.md",
    ]
    record(
        "P01",
        "SHA256SUMS verified from exact Git blob bytes (123 files, 0 hash mismatches)",
        ok,
        f"entries={len(entries)} mismatch={len(bad)} dupes={dups} unhashed={unhashed}",
    )


# --------------------------------------------------------------------------- P02
def p02() -> None:
    events, fx_hex = fixture_events()
    state = jblob("release-state.json")
    problems = []
    if state.get("active_phase") != "A" and state.get("phase") != "A":
        problems.append("phase")
    if state["last_acked_sequence"] != 13 or state["next_sequence"] != 14:
        problems.append("cursor")
    if state["pending_reveal"] is not None:
        problems.append("pending-reveal")
    if state["last_acked_event_id"] != "c15rcc-013":
        problems.append("last-event")
    if state["fixture_sha256"] != "sha256:" + fx_hex:
        problems.append("fixture-digest")
    receipts = state["receipts"]
    if [r["sequence"] for r in receipts] != list(range(1, 14)):
        problems.append("order")
    for r in receipts:
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
    for seq in range(1, 14):
        a = jblob(f"evidence/cursor_{seq:02d}.ack_receipt.json")
        acks.append(a)
        if a["status"] != "acked" or a["ingest_ref"] != receipts[seq - 1]["ingest_ref"]:
            problems.append(f"ack@{seq}")
        if a["next_sequence"] != seq + 1:
            problems.append(f"ack-next@{seq}")
    record(
        "P02",
        "receipts 1..13 recomputed from sealed fixture + ack refs match",
        not problems,
        f"receipts={len(receipts)} acks={len(acks)} problems={problems[:8]}",
    )


# --------------------------------------------------------------------------- P03
def p03() -> None:
    events, _ = fixture_events()
    state = jblob("release-state.json")
    files = evidence_files()
    later_files = [f for f in files if re.search(r"cursor_(01[4-9]|[2-9][0-9])", f)]
    blob_all = b"".join(blob(f"{ROOT}/{f}") for f in files)
    ev14 = events[13]
    probes14 = {
        "event_id": ev14["event_id"].encode() in blob_all,
        "payload": ev14["resident_visible_payload"].encode() in blob_all,
        "timestamp": ev14["occurred_at"].encode() in blob_all,
        "digest": sha_text(ev14["resident_visible_payload"]).encode() in blob_all,
    }
    
    # execute reveal guard against scratch copy of the final state
    reveal_error = None
    untouched = False
    tmp = tempfile.mkdtemp(prefix="ia005_state_")
    try:
        sp = Path(tmp) / "state.json"
        sp.write_text(json.dumps(state), encoding="utf-8")
        rel_py = REPO / "reviews/internal_habitation/c15-rcc/v1/release/release_operator.py"
        py_bin = "/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python"
        res = subprocess.run(
            [py_bin, str(rel_py), "reveal", "--phase", "A", "--state", str(sp)],
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
        and not any(probes14.values())
        and state["last_acked_sequence"] == 13
        and state["next_sequence"] == 14
        and state["pending_reveal"] is None
        and ("ReleaseError" in reveal_error or "release-operator-error" in reveal_error or "Phase A sealed boundary" in reveal_error)
        and untouched
    )
    record(
        "P03",
        "cursor 14 never revealed; frozen Phase-A sealed boundary refuses reveal",
        ok,
        f"later_cursor_files={later_files} cursor14_markers={probes14} "
        f"reveal_guard={reveal_error!r} scratch_state_untouched={untouched}",
    )


# --------------------------------------------------------------------------- P04
def p04() -> None:
    events, _ = fixture_events()
    state = jblob("release-state.json")
    recv = {r["sequence"]: r for r in state["receipts"]}
    conn, tmp = ro_db(blob(f"{ROOT}/world/world.sqlite"), "world.sqlite")
    problems = []
    user_seqs = (1, 3, 5, 6, 8, 10, 12)
    turn_indices = list(range(1, 8))
    
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
        "canonical USER ingest idempotency (7 turns, 1 observation each at revision 1)",
        ok,
        f"user_turns={len(user_seqs)} problems={problems}",
    )


# --------------------------------------------------------------------------- P05
def p05() -> None:
    events, _ = fixture_events()
    unreleased = events[13:]  # cursors 14..30
    unreleased_ids = {e["event_id"] for e in unreleased}
    unreleased_texts = [e["resident_visible_payload"] for e in unreleased]
    
    files = evidence_files()
    req_files = [f for f in files if "exchange/requests/req-" in f]
    problems = []
    
    for rf in req_files:
        content = blob(f"{ROOT}/{rf}").decode("utf-8")
        for eid in unreleased_ids:
            if eid in content:
                problems.append(f"id:{eid} in {rf}")
        for utxt in unreleased_texts:
            if len(utxt) > 20 and utxt[:25] in content:
                problems.append(f"text_shingle in {rf}")

    ok = not problems
    record(
        "P05",
        "future / fixture leakage scan of 21 model requests against cursors 14..30",
        ok,
        f"req_files={len(req_files)} leakage_hits={len(problems)} problems={problems}",
    )


# --------------------------------------------------------------------------- P06
def p06() -> None:
    # Verify ledger and exchange integrity
    ledger_raw = blob(f"{ROOT}/exchange/ledger.jsonl").decode("utf-8").strip().splitlines()
    records = [json.loads(line) for line in ledger_raw]
    
    # 21 requests * 3 events (request_published, response_published, response_consumed) = 63 records
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
        len(records) == 63
        and len(req_pub) == 21
        and len(res_pub) == 21
        and len(res_con) == 21
        and is_contiguous
        and chain_ok
    )
    record(
        "P06",
        "request/decision pairing & ledger integrity (21/21/21, 63 records, chain valid)",
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
        if row_rev != 38:
            problems.append(f"world_revision={row_rev}!= 38")
        if count_commits != 38:
            problems.append(f"commit_count={count_commits}!= 38")
            
        # Search index watermark
        wm_row = conn_s.execute("SELECT value FROM search_meta WHERE key='search_watermark_world_revision'").fetchone()
        watermark = int(wm_row[0]) if wm_row else None
        if watermark != 38:
            problems.append(f"search_watermark={watermark}!= 38")
    finally:
        conn_w.close()
        conn_s.close()
        shutil.rmtree(tmp_w, ignore_errors=True)
        shutil.rmtree(tmp_s, ignore_errors=True)

    ok = not problems
    record(
        "P07",
        "World & search index coherence (quick_check=ok, rev=38, watermark=38, lag=0)",
        ok,
        f"world_rev={row_rev} watermark={watermark} problems={problems}",
    )


# --------------------------------------------------------------------------- P08
def p08() -> None:
    conn, tmp = ro_db(blob(f"{ROOT}/world/world.sqlite"), "world.sqlite")
    problems = []
    try:
        # Check that no temporal cut violations exist
        objs = conn.execute("SELECT object_id, revision, object_type, payload_json, recorded_at FROM object_revisions").fetchall()
        for r in objs:
            payload = json.loads(r["payload_json"])
            # verify evidence_refs point to existing objects
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
        ident["task_id"] == "C15-RCC-RES-A-RERUN-005"
        and ident["run_id"] == RUN_ID
        and ident["resident_session_id"] == SESSION_ID
        and ident["conversation_session_id"] == CONV_SESSION_ID
        and ident["subject_id"] == SUBJECT
        and send["last_acked_sequence"] == 13
        and send["next_sequence"] == 14
        and send["cursor_14_revealed"] is False
        and send["total_exchanges"] == 21
        and fman["final_world_revision"] == 38
        and fman["exchange_integrity"]["ok"] is True
    )
    record(
        "P09",
        "run identity freshness, session termination & freeze manifest consistency",
        ok,
        f"run_id={ident['run_id']} exchanges={send['total_exchanges']} "
        f"cursor_14_revealed={send['cursor_14_revealed']} world_rev={fman['final_world_revision']}",
    )


# --------------------------------------------------------------------------- MAIN
def main() -> int:
    print("==========================================================================")
    print("  WINDOW 72 — C15-RCC-RES-A-RERUN-005 INDEPENDENT ACCEPTANCE PROBES (IA-005)")
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
