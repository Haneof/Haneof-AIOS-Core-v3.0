#!/usr/bin/env python3
"""C15-RCC-RES-A-RERUN-003 independent acceptance probes (IA-003).

Reviewer-owned, read-only adversarial probe harness for the A-003 evidence candidate.

Rules honoured by this harness
------------------------------

* Every artefact under test is read from the *exact Git object* of PR #235 head
  ``5b6367406c13ea9450b7b2598a5813a64129cbd7`` through ``git cat-file blob``.
  No working-tree copy, no author restatement, and no runtime path such as
  ``/home/user/a003_run`` is trusted as an input.
* Nothing is written into the repository or any evidence path.  SQLite handles are
  opened read-only (``mode=ro``) against temporary scratch copies created only inside
  ``tempfile.mkdtemp``; those copies are discarded in the same probe.
* Frozen Core modules are imported from this repository checkout; probe P00 first
  identity-checks ``src/aios_core`` and ``tests`` at live main against the frozen RC
  trees, so "the frozen code did it" is not an assumption.
* Expected outcomes are frozen in this file before the first execution.  Each probe
  prints the raw measured values, so a mismatch is diagnosable without moving the
  goalposts.

Probe map
---------

  P00 exact candidate identity, evidence-only scope, frozen tree identity
  P01 SHA256SUMS verified from exact Git blob bytes (120/120)
  P02 release receipt chain recomputed from the sealed fixture (order, digests, bytes)
  P03 cursor-14 absence + frozen Phase-A sealed boundary actually refuses a reveal
  P04 canonical USER ingest idempotency (7 turns, one observation each, no duplicate)
  P05 future / fixture leakage scan of all 25 model requests and all evidence bytes
  P06 request/decision pairing, contiguity and causal coupling of the 25 rounds
  P07 metering / attempt / binding / receipt consistency (25/25/25/25, 15+10)
  P08 cursor-1 double recovery correctness (attempt identity, in_doubt first, retry 2)
  P09 World/index revision coherence + backup logical identity
  P10 bridge transport-only provenance: both bridge directions pinned to frozen
      Core digests (outbound request fingerprint, relay id, directive re-encode,
      payload digest, HMAC authenticity proof)
  P11 runtime environment versus the authoritative RC environment manifest
      (is SQLite a frozen execution identity?)
  P12 cognition temporal cut: no future/dangling refs, legal review windows, no
      DRAFT/queued promotion

Negative controls (P13) run against scratch copies only, to prove the frozen
recovery machinery is fail-closed rather than accepting operator prose.
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

HEAD = "5b6367406c13ea9450b7b2598a5813a64129cbd7"
BASE = "7549322681ada61ab6d3c6eee5082acc00a658d6"
EVIDENCE_TREE = "6402fff8b0c8c834e7b3f6b5d7c7427d0f846933"
ROOT = "reviews/internal_habitation/c15-rcc/v1/resident/a003"
FROZEN_SOFTWARE = "27a21db5b656d441248b9240020910b66a223830"
FROZEN_CORE_TREE = "a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6"
FROZEN_TESTS_TREE = "92fcbcc5876833735fb3cb7c73a98c4a8a4a3541"
RUN_ID_PREFIX = "a003run-01c3a44b"
SESSION_ID = "resident-a003-0f5ffeff-3d67-4e06-be86-aa83bbea6ad0"
SUBJECT = "user_1"
CLAIM = "clm_d5f6cb68fdb74636f46360e7"
TASK = "task_835d0a7919485a65096f04ba"
TURN1_ATTEMPT = "bgattempt_e70cedf7b64cf6f18d78253ac8382df0"

HERE = Path(__file__).resolve()
REPO = next(
    parent
    for parent in HERE.parents
    if (parent / "src" / "aios_core").is_dir() and (parent / ".git").exists()
)
RESULTS: list[dict] = []


def record(pid: str, name: str, ok: bool, detail: str) -> None:
    RESULTS.append({"probe": pid, "name": name, "ok": bool(ok), "detail": detail})


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
    tmp = tempfile.mkdtemp(prefix="ia003_")
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
        if p.startswith(("src/", "tests/", ".github/", "docs/", "governance/",
                         "release/", "tools/", "pyproject.toml"))
        or "/fixture/" in p
        or "/evaluator/" in p
        or "/c15-rcc/v1/release/" in p
    ]
    core_main = git("rev-parse", "origin/main:src/aios_core").strip()
    tests_main = git("rev-parse", "origin/main:tests").strip()
    core_frozen = git("rev-parse", f"{FROZEN_SOFTWARE}:src/aios_core").strip()
    tests_frozen = git("rev-parse", f"{FROZEN_SOFTWARE}:tests").strip()
    ancestor = subprocess.run(
        ["git", "-C", str(REPO), "merge-base", "--is-ancestor", FROZEN_SOFTWARE,
         "origin/main"], capture_output=True
    ).returncode == 0
    drift = git("rev-list", "--count", f"{HEAD}..origin/main").strip()
    pr = json.loads(
        subprocess.run(
            ["gh", "pr", "view", "235", "--json", "state,isDraft,headRefOid,mergedAt"],
            capture_output=True, text=True, check=True, cwd=str(REPO),
        ).stdout
    )
    ok = (
        tree == EVIDENCE_TREE
        and parent == BASE
        and len(paths) == 122
        and not outside
        and not nonadd
        and not forbidden
        and core_main == FROZEN_CORE_TREE == core_frozen
        and tests_main == FROZEN_TESTS_TREE == tests_frozen
        and ancestor
        and drift == "0"
        and pr["state"] == "OPEN"
        and pr["isDraft"] is True
        and pr["mergedAt"] is None
        and pr["headRefOid"] == HEAD
    )
    record(
        "P00",
        "exact candidate identity + evidence-only scope + frozen tree identity "
        "+ live PR #235 state",
        ok,
        f"tree={tree} parent={parent} files={len(paths)} outside={len(outside)} "
        f"nonadd={len(nonadd)} forbidden={len(forbidden)} core={core_main} "
        f"tests={tests_main} frozen_ancestor={ancestor} head..main={drift} pr={pr}",
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
    unhashed = sorted(set(evidence_files()) - listed)
    dups = len(entries) - len(listed)
    ok = len(entries) == 120 and not bad and dups == 0 and unhashed == [
        "A003_RESIDENT_RUN_REPORT.md",
        "SHA256SUMS",
    ]
    record(
        "P01",
        "SHA256SUMS verified from exact Git blob bytes",
        ok,
        f"entries={len(entries)} mismatch={len(bad)} dupes={dups} unhashed={unhashed}",
    )


# --------------------------------------------------------------------------- P02
def p02() -> None:
    events, fx_hex = fixture_events()
    state = jblob("release/a003_release_state.json")
    problems = []
    if state["active_phase"] != "A":
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
            ("projection-bytes", jblob(f"events/cursor-{seq:03d}.json") == proj),
            ("keyset", set(jblob(f"events/cursor-{seq:03d}.json")) == set(VISIBLE)),
            ("fixture-sha", r["fixture_sha256"] == "sha256:" + fx_hex),
        ):
            if not cond:
                problems.append(f"{label}@{seq}")
    acks = []
    for seq in range(1, 14):
        a = jblob(f"trace/ops/cursor-{seq:03d}-ack.json")
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
    state = jblob("release/a003_release_state.json")
    files = evidence_files()
    later_files = [f for f in files if re.search(r"cursor-(01[4-9]|[2-9][0-9])", f)]
    blob_all = b"".join(blob(f"{ROOT}/{f}") for f in files)
    ev14 = events[13]
    probes14 = {
        "event_id": ev14["event_id"].encode() in blob_all,
        "payload": ev14["resident_visible_payload"].encode() in blob_all,
        "timestamp": ev14["occurred_at"].encode() in blob_all,
        "digest": sha_text(ev14["resident_visible_payload"]).encode() in blob_all,
    }
    # execute the frozen release operator's own sealed-boundary guard (read-only:
    # the guard raises before any atomic write) against a scratch copy of the state
    reveal_error = None
    try:
        spec = importlib.util.spec_from_file_location(
            "ia003_bindings",
            REPO / "reviews/internal_habitation/c15-rcc/v1/release/bindings.py",
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["ia003_bindings"] = mod
        spec.loader.exec_module(mod)
        op = mod.load_release_operator()
        fixture, manifest, evs = op._load_bundle()
        tmp = tempfile.mkdtemp(prefix="ia003_state_")
        sp = Path(tmp) / "state.json"
        sp.write_text(json.dumps(state), encoding="utf-8")
        loaded = op._load_state(sp, manifest, evs)
        try:
            op.cmd_reveal(type("A", (), {"phase": "A", "state": str(sp)})())
            reveal_error = "REVEAL-ALLOWED-UNEXPECTED"
        except Exception as exc:  # noqa: BLE001
            reveal_error = f"{type(exc).__name__}: {exc}"
        state_after = json.loads(sp.read_text(encoding="utf-8"))
        untouched = state_after == state
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception as exc:  # noqa: BLE001
        reveal_error = f"harness {type(exc).__name__}: {exc}"
        untouched = False
    ok = (
        not later_files
        and not any(probes14.values())
        and state["next_sequence"] == 14
        and state["pending_reveal"] is None
        and reveal_error.startswith("ReleaseError: Phase A sealed boundary")
        and untouched
    )
    record(
        "P03",
        "cursor 14 never revealed; frozen Phase-A sealed boundary refuses it",
        ok,
        f"later_cursor_files={later_files} cursor14_markers={probes14} "
        f"reveal_guard={reveal_error!r} scratch_state_untouched={untouched}",
    )


def _utc_z(value: str) -> str:
    """Normalize a fixture local timestamp to the durable ``...Z`` second shape."""
    from datetime import datetime, timezone

    dt = datetime.fromisoformat(value).astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- P04
def p04() -> None:
    events, _ = fixture_events()
    state = jblob("release/a003_release_state.json")
    recv = {r["sequence"]: r for r in state["receipts"]}
    conn, tmp = ro_db(blob(f"{ROOT}/world/resident_a003_world.db"), "world.db")
    problems = []
    turn_out = {}
    for seq in (1, 3, 5, 6, 8, 10, 12):
        raw = blob(f"{ROOT}/trace/ops/cursor-{seq:03d}-turn.out").decode()
        for line in raw.splitlines():
            if line.startswith("{"):
                turn_out[seq] = json.loads(line)
    for i, seq in enumerate((1, 3, 5, 6, 8, 10, 12), start=1):
        r = recv[seq]
        o = turn_out.get(seq)
        if o is None:
            problems.append(f"missing-turn-output:{seq}")
            continue
        if o["user_observation_id"] != r["ingest_object_id"]:
            problems.append(f"canonical-id-not-reused:{seq}")
        if r.get("turn_index") != i:
            problems.append(f"turn-index:{seq}")
        rows = conn.execute(
            "select revision, payload_json from object_revisions where object_id=?",
            (r["ingest_object_id"],),
        ).fetchall()
        if len(rows) != 1 or rows[0]["revision"] != 1:
            problems.append(f"revision-count:{seq}={len(rows)}")
            continue
        p = json.loads(rows[0]["payload_json"])
        md = p.get("metadata", {})
        checks = {
            "text": p["value"] == events[seq - 1]["resident_visible_payload"],
            "session": md.get("session_id") == SESSION_ID,
            "turn": md.get("turn_index") == i,
            "occurred": p["occurred"]["start"] == _utc_z(events[seq - 1]["occurred_at"]),
            "source_class": p.get("source_kind") == "user_ai_interaction",
        }
        problems += [f"{k}:{seq}" for k, v in checks.items() if not v]
        dup = conn.execute(
            "select count(*) from object_revisions where object_type='observation'"
            " and payload_json like ?",
            (f"%{events[seq - 1]['resident_visible_payload']}%",),
        ).fetchone()[0]
        if dup != 1:
            problems.append(f"semantic-duplicate:{seq}={dup}")
    counts = {
        "user_obs": conn.execute(
            "select count(*) from object_revisions where object_id like 'obs_conv_user_%'"
        ).fetchone()[0],
        "ai_obs": conn.execute(
            "select count(*) from object_revisions where object_id like 'obs_conv_ai_%'"
        ).fetchone()[0],
        "turns": conn.execute(
            "select count(*) from runtime_turn_executions"
        ).fetchone()[0],
        "turn_idx": [
            r[0] for r in conn.execute(
                "select turn_index from runtime_turn_executions order by turn_index"
            )
        ],
    }
    ing = jblob("trace/ops/cursor-001-ingest.json")
    ingest_ok = ing["idempotent_replay"] is False and ing.get("reused_existing", False) is False
    shutil.rmtree(tmp, ignore_errors=True)
    ok = (
        not problems
        and counts["user_obs"] == 7
        and counts["ai_obs"] == 7
        and counts["turns"] == 7
        and counts["turn_idx"] == [1, 2, 3, 4, 5, 6, 7]
        and ingest_ok
    )
    record(
        "P04",
        "canonical USER ingest reused idempotently in run_turn; no duplicate USER "
        "observation; turns 1..7 stable session",
        ok,
        f"counts={counts} first_ingest_replay_flags_ok={ingest_ok} problems={problems[:8]}",
    )


# --------------------------------------------------------------------------- P05
def _sh(text: str, n: int = 16) -> set:
    t = re.sub(r"\s+", "", text)
    return {t[i : i + n] for i in range(max(0, len(t) - n + 1))}


def p05() -> None:
    events, _ = fixture_events()
    state = jblob("release/a003_release_state.json")
    curw = {r["sequence"]: r["ingest_world_revision"] for r in state["receipts"]}
    conn, tmp = ro_db(blob(f"{ROOT}/world/resident_a003_world.db"), "world.db")
    awr = {
        r["attempt_id"]: int(r["admission_world_revision"])
        for r in conn.execute(
            "select attempt_id, admission_world_revision from background_model_attempts"
        )
    }
    shutil.rmtree(tmp, ignore_errors=True)
    hits = []
    for n in range(3, 28):
        raw = blob(f"{ROOT}/trace/model/dec-{n:05d}-request.json").decode("utf-8")
        req = json.loads(raw)
        rel = {s for s, w in curw.items() if w <= awr[req["model_attempt_id"]]}
        released = set()
        for s in rel:
            released |= _sh(events[s - 1]["resident_visible_payload"])
        rsh = _sh(raw)
        for k in range(1, 31):
            if k in rel:
                continue
            uniq = (_sh(events[k - 1]["resident_visible_payload"]) & rsh) - released
            if uniq:
                hits.append({"dec": n, "future_cursor": k, "shingles": sorted(uniq)[:2]})
    # whole-evidence scan: ids/timestamps/digests of every never-released cursor
    files = evidence_files()
    blob_all = b"".join(blob(f"{ROOT}/{f}") for f in files)
    unreleased = [k for k in range(1, 31) if k not in curw]
    markers = {}
    for k in unreleased:
        ev = events[k - 1]
        markers[k] = {
            "id": ev["event_id"].encode() in blob_all,
            "payload": ev["resident_visible_payload"].encode() in blob_all,
            "time": ev["occurred_at"].encode() in blob_all,
            "digest": sha_text(ev["resident_visible_payload"]).encode() in blob_all,
        }
    leaked = {k: v for k, v in markers.items() if any(v.values())}
    # A-002 / historical / evaluator contamination markers
    contamination = {
        name: bool(re.compile(pat, re.I).search(blob_all.decode("utf-8", "replace")))
        for name, pat in {
            "A002_session": r"c15-rcc-res-a-rerun-002|2079f64af49c",
            "A002_digests": r"626c6bb32c7fdae9|ecfabf4eb8261f30|eada20a0bf59d1cf",
            "prior_rc_software": r"773876f92d5f8e53|fe77f8a0706acfaf",
            "C15_PR117_ids": r"resident-a-final-rerun|clm_d95e2508b26a0292|clm_776c4bbfaab7540a|clm_52276ec49967d10c|commexp_|opexp_",
            "historical_pr_refs": r"\b#11[0-9]\b|\b#10[0-9]\b|\b#9[0-9]\b|\b#20[0-9]\b",
            "evaluator_wording": r"EVALUATOR_ONLY|ground-truth leaves|unsupported-self|Do not evaluate by string match|hidden prose handoff",
            "b_c_phase_material": r"active_phase\"?\s*:\s*\"[BC]\"|c15rcc-0(1[4-9]|2[0-9]|30)",
            "prior_evidence_paths": r"resident/a00[0-2]\\b|/home/user/a00[0-2]|C15-RCC-RES-B\\b",
            "other_subjects": r"subject_id[\"']?\s*[:=]\s*[\"'](?!user_1)",
        }.items()
    }
    text_all = blob_all.decode("utf-8", "replace")
    # A-RERUN-002 may only be mentioned as an explicit non-reuse / historical-scope
    # declaration (the task itself requires that declaration to exist).
    rerun002_lines = [ln.strip() for ln in text_all.splitlines() if "RERUN-002" in ln]
    rerun002_unqualified = [
        ln
        for ln in rerun002_lines
        if not re.search(r"NOT REUSED|HISTORICAL_FOR_PRIOR_RC_ONLY|prior RC", ln, re.I)
    ]
    ok = (
        not hits
        and not leaked
        and not any(contamination.values())
        and not rerun002_unqualified
    )
    record(
        "P05",
        "0 future-event matches in 25 requests; no unreleased marker or historical "
        "contamination anywhere in exact evidence",
        ok,
        f"request_hits={len(hits)} {hits[:3]} leaked_unreleased={list(leaked)[:5]} "
        f"contamination={ {k: v for k, v in contamination.items()} } "
        f"rerun002_mentions={len(rerun002_lines)} unqualified={len(rerun002_unqualified)} "
        f"self_dir_excluded=True",
    )


# --------------------------------------------------------------------------- P06
def p06() -> None:
    files = evidence_files()
    reqs = sorted(f.split("/")[-1] for f in files if f.endswith("-request.json"))
    decs = sorted(f.split("/")[-1] for f in files if f.endswith("-decision.json"))
    nums = [int(re.search(r"dec-(\d{5})", f).group(1)) for f in reqs]
    problems = []
    if nums != list(range(3, 28)):
        problems.append(f"contiguity:{nums[0]}..{nums[-1]}:{len(nums)}")
    if [f"dec-{n:05d}-decision.json" for n in nums] != decs:
        problems.append("pairing")
    conn, tmp = ro_db(blob(f"{ROOT}/world/resident_a003_world.db"), "world.db")
    att = {r["provider_request_id"]: dict(r) for r in conn.execute(
        "select * from background_model_attempts")}
    shutil.rmtree(tmp, ignore_errors=True)
    for n in nums:
        rid = f"{RUN_ID_PREFIX}-dec{n:05d}"
        a = att.get(rid)
        if a is None:
            problems.append(f"no-durable-attempt:{n}")
            continue
        req = jblob(f"trace/model/dec-{n:05d}-request.json")
        d = jblob(f"trace/model/dec-{n:05d}-decision.json")
        if req["model_attempt_id"] != a["attempt_id"]:
            problems.append(f"attempt-mismatch:{n}")
        if int(req["round_index"]) != int(a["model_round_index"]):
            problems.append(f"round-mismatch:{n}")
        if d["provenance"]["request_id"] != rid:
            problems.append(f"provenance-request-id:{n}")
        if d["kind"] == "capability_calls":
            calls = {c["call_id"] for c in d.get("capability_calls", [])}
            nxt = att.get(f"{RUN_ID_PREFIX}-dec{n+1:05d}")
            if nxt is None or nxt["work_id"] != a["work_id"]:
                problems.append(f"unanswered-round:{n}")
                continue
            nreq = jblob(f"trace/model/dec-{n+1:05d}-request.json")
            hist = {h["call_id"] for h in nreq["capability_history"]}
            if not calls <= hist:
                problems.append(f"calls-not-fed-forward:{n}")
        else:
            # terminal directive: must be the last round of that work
            later = [
                x for x in att.values()
                if x["work_id"] == a["work_id"]
                and int(x["model_round_index"]) > int(a["model_round_index"])
            ]
            if later:
                problems.append(f"terminal-not-last:{n}")
    ok = not problems
    record(
        "P06",
        "25 request/decision pairs contiguous, durable-attempt bound, causally chained",
        ok,
        f"requests={len(reqs)} decisions={len(decs)} problems={problems[:8]}",
    )


# --------------------------------------------------------------------------- P07
def p07() -> None:
    conn, tmp = ro_db(blob(f"{ROOT}/world/resident_a003_world.db"), "world.db")
    tables = (
        "metering_records",
        "background_model_attempts",
        "background_model_request_bindings",
        "background_model_response_receipts",
        "background_model_responses",
        "cold_archive",
    )
    counts = {t: conn.execute(f"select count(*) from {t}").fetchone()[0] for t in tables}
    kinds = dict(
        conn.execute("select execution_class, count(*) from metering_records group by 1")
    )
    j = conn.execute(
        "select count(*) from metering_records m join background_model_attempts a"
        " on m.background_attempt_id = a.attempt_id"
        " where a.meter_record_id = m.record_id"
    ).fetchone()[0]
    rj = conn.execute(
        "select count(*) from background_model_response_receipts r join"
        " background_model_attempts a using(attempt_id) where"
        " a.provider_request_id = r.provider_request_id"
        " and a.response_fingerprint = r.response_fingerprint"
        " and a.meter_record_id is not null"
    ).fetchone()[0]
    dup_req = conn.execute(
        "select count(*) from (select provider_request_id from"
        " background_model_attempts group by 1 having count(*) > 1)"
    ).fetchone()[0]
    fabricated = conn.execute(
        "select count(*) from metering_records where usage_complete = 1"
        " or total_tokens is not null"
    ).fetchone()[0]
    orphan_receipt = conn.execute(
        "select count(*) from background_model_response_receipts r where not exists"
        " (select 1 from background_model_attempts a where a.attempt_id = r.attempt_id)"
    ).fetchone()[0]
    unmetered = conn.execute(
        "select count(*) from background_model_attempts where state <> 'metered'"
    ).fetchone()[0]
    sessions = conn.execute(
        "select count(distinct subject_id) from object_revisions"
    ).fetchone()[0]
    # no two attempts may claim the same world commit twice for the same work
    dup_meter_work = conn.execute(
        "select count(*) from (select background_attempt_id from metering_records"
        " group by 1 having count(*) > 1)"
    ).fetchone()[0]
    shutil.rmtree(tmp, ignore_errors=True)
    ok = (
        counts
        == {
            "metering_records": 25,
            "background_model_attempts": 25,
            "background_model_request_bindings": 25,
            "background_model_response_receipts": 25,
            "background_model_responses": 0,
            "cold_archive": 0,
        }
        and kinds.get("user_interaction") == 15
        and kinds.get("periodic_review") == 10
        and j == 25
        and rj == 25
        and dup_req == 0
        and fabricated == 0
        and orphan_receipt == 0
        and unmetered == 0
        and dup_meter_work == 0
        and sessions == 1
    )
    record(
        "P07",
        "25/25/25/25 metering-attempt-binding-receipt, 15+10 classes, no fabricated "
        "usage, no orphan receipt, all attempts metered",
        ok,
        f"counts={counts} classes={kinds} meter_join={j} receipt_join={rj} "
        f"dup_request_ids={dup_req} fabricated_usage={fabricated} "
        f"orphan_receipts={orphan_receipt} unmetered={unmetered} dup_meter={dup_meter_work}",
    )


# --------------------------------------------------------------------------- P08
def _json_docs(text: str) -> list[dict]:
    return [json.loads(x) for x in re.findall(r"\{.*?^\}", text, re.S | re.M)]


def p08() -> None:
    from aios_core.storage.idempotency import canonical_json_dumps

    conn, tmp = ro_db(blob(f"{ROOT}/world/resident_a003_world.db"), "world.db")
    attempts = [dict(r) for r in conn.execute("select * from background_model_attempts")]
    bad_identity = [
        a["attempt_id"]
        for a in attempts
        if "bgattempt_"
        + hashlib.sha256(
            canonical_json_dumps(
                [a["subject_id"], a["work_kind"], a["work_id"],
                 int(a["model_round_index"])]
            ).encode("utf-8")
        ).hexdigest()[:32]
        != a["attempt_id"]
    ]
    turn = dict(
        conn.execute(
            "select state, retry_authorized, retry_count, reconciliation_evidence,"
            " attempt_protocol from runtime_turn_executions where turn_index = 1"
        ).fetchone()
    )
    a0 = dict(
        conn.execute(
            "select * from background_model_attempts where attempt_id = ?",
            (TURN1_ATTEMPT,),
        ).fetchone()
    )
    receipt_count_for_a0 = conn.execute(
        "select count(*) from background_model_response_receipts where attempt_id = ?",
        (TURN1_ATTEMPT,),
    ).fetchone()[0]
    binding_count_for_a0 = conn.execute(
        "select count(*) from background_model_request_bindings where attempt_id = ?",
        (TURN1_ATTEMPT,),
    ).fetchone()[0]
    meter_rows = conn.execute(
        "select m.record_id, m.world_revision from metering_records m join"
        " background_model_attempts a on a.attempt_id = m.background_attempt_id"
        " where a.attempt_id = ?",
        (TURN1_ATTEMPT,),
    ).fetchall()
    turn1_rounds = conn.execute(
        "select count(*) from background_model_attempts where work_kind='user_turn'"
        " and work_id like 'turnexec_ca982e53%'"
    ).fetchone()[0]
    shutil.rmtree(tmp, ignore_errors=True)
    ins1 = jblob("trace/ops/cursor-001-inspect.json")
    ins2 = jblob("trace/ops/cursor-001-inspect2.json")
    ar1 = _json_docs(blob(f"{ROOT}/trace/ops/cursor-001-authorize-retry.json").decode())
    ar2 = _json_docs(blob(f"{ROOT}/trace/ops/cursor-001-authorize-retry2.json").decode())
    turn_out = [
        json.loads(line)
        for line in blob(f"{ROOT}/trace/ops/cursor-001-turn.out").decode().splitlines()
        if line.startswith("{")
    ][0]
    ok = (
        not bad_identity
        and len(attempts) == 25
        and turn["state"] == "completed"
        and turn["retry_count"] == 2
        and turn["retry_authorized"] == 0
        and turn["attempt_protocol"] == "model_attempt_v1"
        and bool(turn["reconciliation_evidence"])
        and a0["state"] == "metered"
        and a0["admission_world_revision"] == 1
        and a0["failure_kind"] is None
        and a0["failure_detail"] is None
        and bool(a0["reconciliation_evidence"])
        and bool(
            re.search(
                r"not_submitted|no directive bytes|never reached the provider",
                a0["reconciliation_evidence"],
                re.I,
            )
        )
        and ins1["model_attempts"][0]["state"] == "in_doubt"
        and ins1["model_attempts"][0]["provider"] is None
        and ins1["model_attempts"][0]["provider_request_id"] is None
        and ins1["retry_count"] == 0
        and ins2["retry_count"] == 1
        and ins2["reconciliation_evidence"]
        and ar1[0]["attempts"][0]["state"] == "not_submitted"
        and ar1[0]["attempts"][0]["recovery_disposition"] == "safe_to_retry"
        and ar2[0]["attempts"][0]["state"] == "not_submitted"
        and ar1[1]["retry_authorized"] is True
        and ar2[1]["retry_count"] == 1
        and receipt_count_for_a0 == 1
        and binding_count_for_a0 == 1
        and len(meter_rows) == 1
        and turn1_rounds == 5
        and turn_out["model_rounds"] == 5
        and turn_out["status"] == "turn_completed"
    )
    record(
        "P08",
        "cursor-1 double pre-submission recovery: Core-derived attempt ids, honest "
        "in_doubt before reconcile, single durable attempt/receipt/meter row, retry 2",
        ok,
        f"bad_identity={len(bad_identity)} turn1={turn['state']}/rc={turn['retry_count']}"
        f"/auth={turn['retry_authorized']} inspect1={ins1['model_attempts'][0]['state']}"
        f" inspect2_rc={ins2['retry_count']} receipts_a0={receipt_count_for_a0} "
        f"bindings_a0={binding_count_for_a0} meters_a0={len(meter_rows)} "
        f"turn1_rounds={turn1_rounds} out_rounds={turn_out['model_rounds']}",
    )


# --------------------------------------------------------------------------- P09
def p09() -> None:
    w, t1 = ro_db(blob(f"{ROOT}/world/resident_a003_world.db"), "world.db")
    i, t2 = ro_db(blob(f"{ROOT}/world/resident_a003_world.db.search.sqlite"), "index.db")
    b, t3 = ro_db(blob(f"{ROOT}/backup/resident_a003_world_backup.db"), "backup.db")
    wc = w.execute("select count(*), min(world_revision), max(world_revision) from world_commits").fetchone()
    rev = int(w.execute("select value from world_meta where key='world_revision'").fetchone()[0])
    wq = w.execute("PRAGMA quick_check").fetchone()[0]
    schema = w.execute("PRAGMA user_version").fetchone()[0]
    iwq = i.execute("PRAGMA quick_check").fetchone()[0]
    wm = int(i.execute(
        "select value from search_meta where key='search_watermark_world_revision'"
    ).fetchone()[0])
    wdocs = {(r[0], r[1]) for r in w.execute(
        "select object_id, revision from object_revisions")}
    idocs = {(r[0], r[1]) for r in i.execute("select object_id, revision from search_doc")}
    chain_gap = w.execute(
        "select count(*) from (select world_revision - lag(world_revision) over"
        " (order by world_revision) d from world_commits) where d is not null and d<>1"
    ).fetchone()[0]
    ops = w.execute("select count(*) from operations").fetchone()[0]
    idem = w.execute("select count(*) from idempotency_records").fetchone()[0]
    orphan_ops = w.execute(
        "select count(*) from operations o where not exists (select 1 from world_commits"
        " c where c.operation_id = o.operation_id)"
    ).fetchone()[0]
    maxobj = w.execute("select max(world_revision) from object_revisions").fetchone()[0]
    claim = [r[0] for r in w.execute(
        "select revision from object_revisions where object_id=? order by revision", (CLAIM,))]
    task = [r[0] for r in w.execute(
        "select revision from object_revisions where object_id=? order by revision", (TASK,))]
    wakes = w.execute(
        "select count(distinct object_id) from object_revisions where object_type='wake'"
    ).fetchone()[0]
    bq = b.execute("PRAGMA quick_check").fetchone()[0]
    brev = int(b.execute("select value from world_meta where key='world_revision'").fetchone()[0])
    logical = {}
    for name, q in (
        ("world_commits", "select * from world_commits"),
        ("object_revisions",
         "select object_id, revision, world_revision, payload_json from object_revisions"),
        ("operations", "select * from operations"),
        ("idempotency", "select * from idempotency_records"),
        ("metering", "select * from metering_records"),
        ("attempts", "select * from background_model_attempts"),
        ("bindings", "select * from background_model_request_bindings"),
        ("receipts", "select * from background_model_response_receipts"),
        ("authority", "select * from background_model_authenticity_authority"),
        ("turn_exec", "select * from runtime_turn_executions"),
    ):
        d1 = hashlib.sha256(repr(sorted(tuple(r) for r in w.execute(q))).encode()).hexdigest()
        d2 = hashlib.sha256(repr(sorted(tuple(r) for r in b.execute(q))).encode()).hexdigest()
        logical[name] = d1 == d2
    identical_bytes = blob(f"{ROOT}/world/resident_a003_world.db") == blob(
        f"{ROOT}/backup/resident_a003_world_backup.db"
    )
    for t in (t1, t2, t3):
        shutil.rmtree(t, ignore_errors=True)
    ok = (
        wc[0] == 42 and wc[1] == 1 and wc[2] == 42
        and rev == 42
        and maxobj == 42
        and schema == 1
        and wq == "ok" and iwq == "ok" and bq == "ok"
        and wm == 42
        and wdocs == idocs and len(wdocs) == 76
        and chain_gap == 0
        and ops == idem == 42
        and orphan_ops == 0
        and claim == [1, 2, 3, 4, 5, 6]
        and task == [1, 2, 3, 4]
        and wakes == 4
        and brev == 42
        and all(logical.values())
    )
    record(
        "P09",
        "World 42 / index watermark 42 / lag 0 / 76-doc parity / chain and backup "
        "logical identity (byte identity not required)",
        ok,
        f"commits={tuple(wc)} rev={rev} maxobj={maxobj} schema={schema} wcq={wq} "
        f"icq={iwq} watermark={wm} doc_delta={len(wdocs ^ idocs)} docs={len(wdocs)} "
        f"chain_gap={chain_gap} ops={ops} idem={idem} orphan_ops={orphan_ops} "
        f"claim={claim} task={task} wakes={wakes} backup_rev={brev} bquick={bq} "
        f"logical={ {k: v for k, v in logical.items()} } bytes_identical={identical_bytes}",
    )


# --------------------------------------------------------------------------- P10
def p10() -> None:
    """Bridge provenance: pin BOTH bridge directions to frozen Core computations."""
    from aios_core.runtime.background_attempt import (
        BackgroundModelAttemptStore as S,
        encode_model_directive,
    )
    from aios_core.runtime.cognitive_runtime import (
        CapabilityCall,
        ModelCallProvenance,
        ModelDirective,
    )
    from aios_core.storage.idempotency import canonical_json_dumps

    conn, tmp = ro_db(blob(f"{ROOT}/world/resident_a003_world.db"), "world.db")
    bind = {r["attempt_id"]: dict(r) for r in conn.execute(
        "select * from background_model_request_bindings")}
    rec = {r["attempt_id"]: dict(r) for r in conn.execute(
        "select * from background_model_response_receipts")}
    att = {r["attempt_id"]: dict(r) for r in conn.execute(
        "select * from background_model_attempts")}
    secret = bytes.fromhex(conn.execute(
        "select secret_hex from background_model_authenticity_authority"
        " where authority_id='trusted-return-v1'").fetchone()[0])
    shutil.rmtree(tmp, ignore_errors=True)

    counters = dict(req_fp=0, relay=0, payload=0, respfp=0, hmac_ok=0)
    problems = []
    for n in range(3, 28):
        raw = blob(f"{ROOT}/trace/model/dec-{n:05d}-request.json")
        req = json.loads(raw.decode("utf-8"))
        a = att[req["model_attempt_id"]]
        b = bind[a["attempt_id"]]
        payload = {
            "attempt_id": req["model_attempt_id"],
            "capability_catalog": [dict(x) for x in req["capability_catalog"]],
            "capability_history": [
                {
                    "call_id": h["call_id"],
                    "data": h["data"],
                    "error_code": h["error_code"],
                    "error_message": h["error_message"],
                    "name": h["name"],
                    "ok": bool(h["ok"]),
                }
                for h in req["capability_history"]
            ],
            "cockpit": dict(req["cockpit"]),
            "remaining_tool_rounds": int(req["remaining_tool_rounds"]),
            "round_index": int(req["round_index"]),
            "subject_id": SUBJECT,
            "user_input": req["user_input"],
            "wake_reason": req["wake_reason"],
            "work_id": a["work_id"],
            "work_kind": a["work_kind"],
        }
        fp = hashlib.sha256(canonical_json_dumps(payload).encode("utf-8")).hexdigest()
        if fp == b["outbound_request_fingerprint"]:
            counters["req_fp"] += 1
        else:
            problems.append(f"request-fingerprint:{n}")
        relay = "relay_" + hashlib.sha256(
            canonical_json_dumps(
                {
                    "attempt_id": a["attempt_id"],
                    "model_round_index": int(a["model_round_index"]),
                    "outbound_request_fingerprint": fp,
                    "subject_id": SUBJECT,
                    "work_id": a["work_id"],
                    "work_kind": a["work_kind"],
                }
            ).encode("utf-8")
        ).hexdigest()
        if req["outbound_relay_id"] == b["relay_id"] == relay:
            counters["relay"] += 1
        else:
            problems.append(f"relay-id:{n}")
        d = json.loads(blob(f"{ROOT}/trace/model/dec-{n:05d}-decision.json").decode("utf-8"))
        directive = ModelDirective(
            capability_calls=tuple(
                CapabilityCall(name=c["name"], arguments=dict(c["arguments"]),
                               call_id=c.get("call_id"))
                for c in d.get("capability_calls", [])
            ),
            response=d.get("response"),
            silence=bool(d.get("silence", False)),
            usage=None,
            provenance=ModelCallProvenance(
                provider=d["provenance"]["provider"],
                model=d["provenance"]["model"],
                request_id=d["provenance"]["request_id"],
            ),
        )
        r = rec[a["attempt_id"]]
        if hashlib.sha256(encode_model_directive(directive).encode("utf-8")).hexdigest() == r["payload_sha256"]:
            counters["payload"] += 1
        else:
            problems.append(f"payload-sha:{n}")
        rfp = S._response_fingerprint(directive)
        if rfp == r["response_fingerprint"] == a["response_fingerprint"]:
            counters["respfp"] += 1
        else:
            problems.append(f"response-fingerprint:{n}")
        msg = S._receipt_message(
            attempt_id=a["attempt_id"], subject_id=a["subject_id"],
            work_kind=a["work_kind"], work_id=a["work_id"],
            model_round_index=int(a["model_round_index"]),
            outbound_request_fingerprint=r["outbound_request_fingerprint"],
            relay_id=r["relay_id"], provider=r["provider"], model=r["model"],
            provider_request_id=r["provider_request_id"],
            response_fingerprint=r["response_fingerprint"],
            payload_sha256=r["payload_sha256"],
        )
        if "bgresponse_v1_" + hmac.new(secret, msg, hashlib.sha256).hexdigest() == r["authenticity_proof"]:
            counters["hmac_ok"] += 1
        else:
            problems.append(f"hmac-proof:{n}")
    ok = all(v == 25 for v in counters.values()) and not problems
    record(
        "P10",
        "bridge pinned transport-only: 25/25 outbound request fingerprints, relay ids,"
        " directive re-encode digests, response fingerprints and HMAC receipts",
        ok,
        f"counters={counters} problems={problems[:6]}",
    )


# --------------------------------------------------------------------------- P11
def p11() -> None:
    env = blob("reviews/CORE_RC_REFREEZE_002/environment_manifest.txt").decode()
    wf = blob(".github/workflows/core-rc-refreeze-002-formal-gate.yml").decode()
    pyproject = blob("pyproject.toml").decode()
    packet = blob("release/rc/CORE_RC_REFREEZE_002_OPERATOR_PACKET.md").decode()
    manifest = jblob("manifest/run_manifest.json")
    src_manifest = blob("reviews/CORE_RC_REFREEZE_002/source_manifest.json").decode()
    pin_scan = "\n".join([env, packet, wf, pyproject, src_manifest])
    sqlite_pinned = bool(
        re.search(r"sqlite[^\n]{0,80}3\.\d+\.\d+", pin_scan, re.I)
        or re.search(r"3\.\d+\.\d+[^\n]{0,40}sqlite", pin_scan, re.I)
    )
    py_pin = 'python-version: "3.12.14"' in wf or "python-version: 3.12.14" in wf
    range_based = "requires-python=\">=3.12\"" in pyproject.replace(" ", "")
    declared = manifest.get("runtime_environment", {})
    identity = manifest.get("execution_software", {})
    frozen_ok = (
        identity.get("frozen_commit") == FROZEN_SOFTWARE
        and identity.get("frozen_core_tree") == FROZEN_CORE_TREE
        and identity.get("frozen_tests_tree") == FROZEN_TESTS_TREE
    )
    # behavioural environment markers observable inside the evidence itself
    traced_pydantic = b"errors.pydantic.dev/2.13/v/enum" in blob(
        f"{ROOT}/trace/model/dec-00004-request.json"
    )
    ok = (
        not sqlite_pinned
        and py_pin
        and range_based
        and "Pydantic 2.13.5" in env
        and "3.12.14" in str(declared.get("python", ""))
        and str(declared.get("pydantic", "")) == "2.13.5"
        and frozen_ok
        and traced_pydantic
    )
    record(
        "P11",
        "RC contract pins CPython/pydantic/pytest only; SQLite is NOT a frozen "
        "execution identity, so 3.53.4 is a compatible runtime detail, not drift",
        ok,
        f"sqlite_pinned_in_rc={sqlite_pinned} workflow_python_pin={py_pin} "
        f"pyproject_range_based={range_based} run_env={declared} "
        f"frozen_identity_ok={frozen_ok} pydantic_2_13_marker_in_traces={traced_pydantic} "
        f"declared_sqlite={declared.get('sqlite_version') or declared.get('sqlite')}",
    )


# --------------------------------------------------------------------------- P12
def p12() -> None:
    events, _ = fixture_events()
    state = jblob("release/a003_release_state.json")
    curw = {r["sequence"]: r["ingest_world_revision"] for r in state["receipts"]}
    conn, tmp = ro_db(blob(f"{ROOT}/world/resident_a003_world.db"), "world.db")
    revs = [dict(r) for r in conn.execute(
        "select object_id, revision, object_type, world_revision, learned_at,"
        " payload_json from object_revisions order by world_revision")]
    final_rev = conn.execute("select max(world_revision) from world_commits").fetchone()[0]
    shutil.rmtree(tmp, ignore_errors=True)
    born = {(r["object_id"], r["revision"]): int(r["world_revision"]) for r in revs}
    problems = []
    for r in revs:
        p = json.loads(r["payload_json"])
        wr = int(r["world_revision"])
        refs = []
        for key in ("source_refs", "reason_refs", "support_evidence_set_refs",
                    "counter_evidence_set_refs", "evidence_refs", "member_refs",
                    "task_ref"):
            v = p.get(key) or []
            refs.extend(v if isinstance(v, list) else [v])
        md = p.get("metadata") or {}
        for key in ("revision_evidence_set_ref", "target_ref"):
            if isinstance(md.get(key), dict):
                refs.append(md[key])
        for ref in refs:
            if not isinstance(ref, dict) or not ref.get("object_id"):
                continue
            key = (ref["object_id"], int(ref.get("revision") or 0))
            if key not in born:
                problems.append(f"dangling:{r['object_id']}#{r['revision']}->{key}")
            elif born[key] > wr:
                problems.append(f"future-ref:{r['object_id']}#{r['revision']}->{key}")
        # knowledge window of evidence sets must precede the cognition commit
        kw = (p.get("knowledge_window") or {})
        if kw:
            if int(kw.get("world_revision", 0)) >= wr:
                problems.append(f"knowledge-window-not-prior:{r['object_id']}")
    # review anchors: only released reality inside the window
    anchors_seen = []
    for n in (8, 9, 17, 18, 20, 21, 26, 27):
        req = jblob(f"trace/model/dec-{n:05d}-request.json")
        for h in req["capability_history"]:
            if h["name"] != "read_periodic_review_anchors" or not h["ok"]:
                continue
            for a in h["data"] or []:
                oid = a["object_ref"]["object_id"]
                revn = int(a["object_ref"].get("revision") or 1)
                key = (oid, revn)
                anchors_seen.append(key)
                if key not in born:
                    problems.append(f"anchor-dangling:{oid}@{revn}")
                elif born[key] > req["cockpit"]["world_map"]["world_revision"]:
                    problems.append(f"anchor-future:{oid}@{revn}")
    states = [json.loads(r["payload_json"])["task_state"] for r in revs
              if r["object_id"] == TASK]
    task_terminal = [s for s in states if s in {"completed", "failed", "cancelled"}]
    c6 = [r for r in revs if r["object_id"] == CLAIM and r["revision"] == 6][0]
    discipline_after_cursor10 = int(c6["world_revision"]) > curw[10]
    # production-deletion cognition must appear only after cursor 6, evidence
    # discipline only after cursor 10, and nothing may mention cursor 14+ material
    texts = {
        r["revision"]: json.loads(r["payload_json"]).get("content", "")
        for r in revs if r["object_id"] == CLAIM
    }
    deletion_rev = [k for k, v in texts.items() if "删除" in v and "回滚" in v]
    deletion_ok = (not deletion_rev) or min(deletion_rev) >= 5
    if deletion_rev and min(deletion_rev) < 5:
        problems.append(f"deletion-boundary-too-early:{min(deletion_rev)}")
    evidence_discipline_rev = [k for k, v in texts.items() if "证据纪律" in v]
    if evidence_discipline_rev and min(evidence_discipline_rev) < 6:
        problems.append(f"discipline-too-early:{min(evidence_discipline_rev)}")
    queued_only = "READY_FOR_UPLOAD" in blob(
        f"{ROOT}/trace/model/dec-00022-decision.json").decode()
    published_confirmed = "PUBLISHED" in blob(
        f"{ROOT}/trace/model/dec-00025-decision.json").decode()
    ok = (
        not problems
        and states == ["draft", "ready", "running", "waiting_user"]
        and not task_terminal
        and discipline_after_cursor10
        and deletion_ok
        and len(anchors_seen) >= 4
        and queued_only
        and published_confirmed
        and int(final_rev) == 42
    )
    record(
        "P12",
        "cognition temporal cut: refs never future/dangling, anchors within released "
        "window, boundary cognition appears only after its cursor, no promotion",
        ok,
        f"problems={problems[:6]} task_states={states} anchors={len(anchors_seen)} "
        f"claim6_after_cursor10={discipline_after_cursor10} deletion_rev={deletion_rev}"
        f" discipline_rev={evidence_discipline_rev} queued_only={queued_only} "
        f"published_confirmed={published_confirmed}",
    )


# --------------------------------------------------------------------------- P13
def p13() -> None:
    """Synthetic negative controls (scratch copies / in-memory only).

    These do not test the candidate; they test whether the frozen machinery the
    candidate depends on is actually fail-closed, i.e. whether the two shortcuts a
    faking author would have needed are mechanically refused:

      A) declaring a *receipted* attempt "not submitted";
      B) authorizing a retry while attempts prove provider execution;
      C) editing a decision file after the fact without breaking its durable digest.
    """
    from datetime import datetime, timezone

    from aios_core.contracts.time import canonical_utc_iso
    from aios_core.runtime.background_attempt import (
        BackgroundModelAttemptStore,
        BackgroundModelResponseConflict,
        encode_model_directive,
    )
    from aios_core.runtime.cognitive_runtime import (
        CapabilityCall,
        ModelCallProvenance,
        ModelDirective,
    )
    from aios_core.runtime.turn_execution import (
        TurnExecutionInDoubt,
        TurnExecutionStore,
    )
    from aios_core.storage.idempotency import canonical_json_dumps
    from aios_core.storage.sqlite_store import SQLiteWorldStore

    tmp = tempfile.mkdtemp(prefix="ia003_neg_")
    world = Path(tmp) / "world.db"
    world.write_bytes(blob(f"{ROOT}/world/resident_a003_world.db"))
    out = {}

    # ---- control A: an attempt with an authenticated receipt cannot be reconciled
    store = SQLiteWorldStore(db_path=str(world))
    ledger = BackgroundModelAttemptStore(store)
    try:
        ledger.reconcile_not_submitted(
            TURN1_ATTEMPT,
            reconciled_at=datetime.now(timezone.utc),
            evidence="synthetic reviewer control: attempt already receipted",
        )
        out["A"] = "REFUSED-EXPECTED-NO: reconciliation was allowed"
    except BackgroundModelResponseConflict as exc:
        out["A"] = f"BLOCKED-AS-EXPECTED: {exc.detail}"
    except Exception as exc:  # noqa: BLE001
        out["A"] = f"unexpected {type(exc).__name__}: {exc}"

    # ---- control B: retry cannot be authorized over provider-proven attempts
    events, _ = fixture_events()
    cur1 = events[0]
    occurred = canonical_utc_iso(
        datetime.fromisoformat(cur1["occurred_at"]), "occurred_at"
    )
    from aios_core.ingest.conversation import _stable_suffix

    assistant_id = f"obs_conv_ai_{_stable_suffix(SUBJECT, SESSION_ID, 1, 'assistant')}"
    conn = sqlite3.connect(world)
    conn.execute("delete from object_revisions where object_id = ?", (assistant_id,))
    conn.execute("update runtime_turn_executions set state='started' where turn_index=1")
    conn.execute(
        "update background_model_attempts set state='in_doubt' where work_kind='user_turn'"
        " and work_id = (select work_id from background_model_attempts where attempt_id=?)",
        (TURN1_ATTEMPT,),
    )
    conn.commit()
    conn.close()
    try:
        TurnExecutionStore(world).authorize_retry(
            subject_id=SUBJECT,
            session_id=SESSION_ID,
            turn_index=1,
            user_input=cur1["resident_visible_payload"],
            occurred_at=occurred,
            assistant_id=assistant_id or "unknown",
            evidence="synthetic reviewer control",
        )
        out["B"] = "REFUSED-EXPECTED-NO: retry was authorized over in-doubt attempts"
    except TurnExecutionInDoubt as exc:
        out["B"] = f"BLOCKED-AS-EXPECTED: {exc.state}"
    except Exception as exc:  # noqa: BLE001
        out["B"] = f"unexpected {type(exc).__name__}: {exc}"

    # ---- control C: tampered decision bytes break the durable payload digest
    d = jblob("trace/model/dec-00022-decision.json")
    tampered = json.loads(json.dumps(d))
    tampered["response"] = tampered["response"] + " (reviewer tamper marker)"
    directive = ModelDirective(
        capability_calls=tuple(
            CapabilityCall(name=c["name"], arguments=dict(c["arguments"]),
                           call_id=c.get("call_id"))
            for c in tampered.get("capability_calls", [])
        ),
        response=tampered.get("response"),
        silence=False,
        usage=None,
        provenance=ModelCallProvenance(
            provider=tampered["provenance"]["provider"],
            model=tampered["provenance"]["model"],
            request_id=tampered["provenance"]["request_id"],
        ),
    )
    conn = sqlite3.connect(f"file:{world}?mode=ro", uri=True)
    durable = conn.execute(
        "select payload_sha256 from background_model_response_receipts"
        " where provider_request_id = ?",
        (f"{RUN_ID_PREFIX}-dec00022",),
    ).fetchone()[0]
    conn.close()
    tamper_sha = hashlib.sha256(
        encode_model_directive(directive).encode("utf-8")
    ).hexdigest()
    out["C"] = (
        "DETECTED-AS-EXPECTED: tampered payload digest differs from durable receipt"
        if tamper_sha != durable
        else "REFUSED-EXPECTED-NO: tamper undetectable"
    )
    shutil.rmtree(tmp, ignore_errors=True)
    ok = all(v.startswith("BLOCKED-AS-EXPECTED") or v.startswith("DETECTED-AS-EXPECTED")
             for v in out.values()) and len(out) == 3
    record(
        "P13",
        "negative controls prove the frozen recovery/authenticity machinery is "
        "fail-closed (forgery paths refused)",
        ok,
        f"controls={ {k: v for k, v in out.items()} }",
    )


PROBES = [p00, p01, p02, p03, p04, p05, p06, p07, p08, p09, p10, p11, p12, p13]


def main() -> int:
    sys.path.insert(0, str(REPO / "src"))
    for probe in PROBES:
        try:
            probe()
        except Exception as exc:  # noqa: BLE001
            record(probe.__name__, "harness error", False, f"{type(exc).__name__}: {exc}")
    passed = sum(1 for r in RESULTS if r["ok"])
    for r in RESULTS:
        print(("PASS " if r["ok"] else "FAIL ") + r["probe"] + " | " + r["name"])
        print("      " + r["detail"])
    print(f"\nTOTAL {passed}/{len(RESULTS)} PROBES PASS")
    print(json.dumps({"candidate": HEAD, "tree": EVIDENCE_TREE,
                      "passed": passed, "total": len(RESULTS)}, indent=1))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
