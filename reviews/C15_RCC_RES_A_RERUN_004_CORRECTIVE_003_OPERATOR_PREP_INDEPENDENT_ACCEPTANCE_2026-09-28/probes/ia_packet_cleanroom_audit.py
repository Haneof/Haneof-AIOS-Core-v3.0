"""IA packet / clean-room / contamination / freeze audit (stdlib only).

Different logic from the author's marker-regex audit: every packet value must
belong to a mechanical value class (hex digest, git object id, repo path,
version, enum token, integer, timestamp, or an explicitly enumerated
prohibition category). Anything else is surfaced for manual review.
Prints a JSON report; each check has an explicit expected value declared here
before first execution.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys

CAND = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/ia/clone")
PREP = CAND / "reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP"
HEAD = "10901d467679b70437ae112747eab81f889fd5cb"
PARENT = "abb8b435e5187c7c6c2f4332aea37cd805b4a53c"

HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
TOKEN = re.compile(r"^[A-Za-z0-9_.:\-]+$")
PATHLIKE = re.compile(r"^[A-Za-z0-9_./*<>\-]+$")
TS = re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.]+\+00:00$")


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*a):
    return subprocess.run(["git", "-C", str(CAND), *a], capture_output=True, text=True).stdout.strip()


def classify(v):
    if isinstance(v, bool) or isinstance(v, int):
        return "int"
    if not isinstance(v, str):
        return "non-str"
    for name, rx in (("hex64", HEX64), ("hex40", HEX40), ("version", VERSION), ("ts", TS), ("token", TOKEN), ("path", PATHLIKE)):
        if rx.match(v):
            return name
    return "FREE_TEXT"


checks = {}
pk_path = PREP / "RESIDENT_SAFE_LAUNCH_PACKET.json"
pk = json.loads(pk_path.read_text())

# --- packet status / cursor / mode ---------------------------------------------
checks["status_is_PREP_REVIEW_READY"] = (pk["status"] == "PREP_REVIEW_READY", True)
checks["status_not_READY_FOR_RESIDENT"] = (pk["status"] != "READY_FOR_RESIDENT", True)
checks["cursor_range_1_13"] = ((pk["allowed_cursor_start"], pk["allowed_cursor_end"]) == (1, 13), True)
checks["real_response_mode"] = (pk["real_response_mode"] == "EXTERNAL_CURRENT_RESIDENT_SESSION", True)
checks["task_id"] = (pk["task_id"] == "C15-RCC-RES-A-RERUN-004-CORRECTIVE-003", True)
checks["versions"] = ((pk["python_version"], pk["pydantic_version"], pk["pytest_version"], pk["sqlite_version"]) == ("3.12.14", "2.13.5", "8.4.2", "3.45.1"), True)

# --- packet head rule ----------------------------------------------------------
checks["packet_head_equals_parent"] = (pk["operator_prep_exact_head"] == PARENT, True)
checks["candidate_single_parent_is_packet_head"] = (git("rev-list", "--parents", "-n1", HEAD).split()[1:] == [PARENT], True)
rel_pk = pk_path.relative_to(CAND).as_posix()
checks["packet_absent_in_parent"] = (subprocess.run(["git", "-C", str(CAND), "cat-file", "-e", f"{PARENT}:{rel_pk}"]).returncode != 0, True)
checks["packet_present_in_head"] = (subprocess.run(["git", "-C", str(CAND), "cat-file", "-e", f"{HEAD}:{rel_pk}"]).returncode == 0, True)

# --- hash pins -------------------------------------------------------------------
pins = {
    "bootstrap_sha256": sha(CAND / pk["bootstrap_path"]),
    "clean_room_contract_sha256": sha(CAND / pk["clean_room_contract_path"]),
    "resident_run_contract_sha256": sha(CAND / pk["resident_run_contract_path"]),
    "environment_record_sha256": sha(PREP / pk["environment_record_path"]),
    "harness_manifest_sha256": json.loads((PREP / "evidence/harness_manifest.json").read_text())["manifest_sha256"],
}
for g in "abcd":
    pins[f"gate_{g}_hash"] = sha(PREP / f"evidence/gates/gate_{g}_result.json")
for k, v in pins.items():
    checks[f"pin_{k}"] = (pk[k] == v, True)
checks["rc_software_is_commit"] = (git("cat-file", "-t", pk["frozen_software_sha"]) == "commit", True)
checks["rc_repo_tree"] = (git("rev-parse", pk["frozen_software_sha"] + "^{tree}") == pk["frozen_repository_tree"], True)
checks["rc_core_tree"] = (git("rev-parse", pk["frozen_software_sha"] + ":src/aios_core") == pk["frozen_core_tree"], True)
checks["rc_tests_tree"] = (git("rev-parse", pk["frozen_software_sha"] + ":tests") == pk["frozen_tests_tree"], True)

# --- freeze manifest ---------------------------------------------------------------
fm = json.loads((PREP / "evidence/FREEZE_MANIFEST.json").read_text())
checks["freeze_packet_sha"] = (fm["launch_packet_sha256"] == sha(pk_path), True)
checks["freeze_audit_sha"] = (fm["packet_audit_sha256"] == sha(PREP / "evidence/resident_safe_packet_audit.json"), True)
checks["freeze_harness_manifest"] = (fm["harness_manifest_sha256"] == pins["harness_manifest_sha256"], True)
checks["freeze_head"] = (fm["operator_prep_exact_head"] == PARENT, True)
gs = json.loads((PREP / "evidence/gates/gate_summary.json").read_text())
checks["freeze_gate_summary_matches"] = (fm["gate_summary"] == gs["gates"], True)

# --- SHA256SUMS coverage -------------------------------------------------------------
sums = {}
for line in (PREP / "evidence/SHA256SUMS").read_text().splitlines():
    h, p = line.split("  ", 1)
    sums[p] = h
all_files = sorted(p.relative_to(PREP).as_posix() for p in PREP.rglob("*") if p.is_file())
checks["sha256sums_all_match"] = (all(sha(PREP / p) == h for p, h in sums.items()), True)
checks["sha256sums_uncovered_files"] = (sorted(set(all_files) - set(sums)), ["evidence/SHA256SUMS"])
for must in ("bootstrap/bootstrap_runtime.sh", "RESIDENT_SAFE_LAUNCH_PACKET.json", "evidence/resident_safe_packet_audit.json",
             "evidence/environment_record.json", "evidence/FREEZE_MANIFEST.json", "evidence/harness_manifest.json",
             "harness/aios_exchange/runner.py"):
    checks[f"sha256sums_covers_{must}"] = (must in sums, True)

# --- packet value classes (contamination, value-type logic) ----------------------------
value_classes = {}
free_text = []


def walk(prefix, v):
    if isinstance(v, list):
        for i, x in enumerate(v):
            walk(f"{prefix}[{i}]", x)
    elif isinstance(v, dict):
        for k, x in v.items():
            walk(f"{prefix}.{k}", x)
    else:
        c = classify(v)
        value_classes[prefix] = c
        if c == "FREE_TEXT":
            free_text.append((prefix, v))


walk("packet", pk)
checks["packet_free_text_values"] = (free_text, "MANUAL_REVIEW")

# --- clean-room boundary ------------------------------------------------------------------
cr = (CAND / pk["clean_room_contract_path"]).read_text()
allowed = [x.lower() for x in pk["allowed_startup_inputs"]]
checks["packet_allowed_inputs_include_clean_room_contract"] = (any("clean_room_contract" in x or "corrective_003_clean_room" in x for x in allowed), True)
checks["packet_allowed_inputs_exact"] = (pk["allowed_startup_inputs"], "MANUAL_REVIEW")
forbidden_needed = ["pm_governance_and_task_board", "global_checkpoint", "pm_adjudications_and_review_ready_reports",
                    "prior_resident_run_evidence_and_exchange_ledgers", "independent_acceptance_reports",
                    "git_history_and_pull_request_metadata_concerning_prior_runs", "fixture_payload",
                    "evaluator_expected_semantics", "release_operator_source_and_release_state"]
checks["forbidden_categories_explicit"] = (all(c in pk["forbidden_startup_categories"] for c in forbidden_needed), True)
checks["packet_mentions_board_or_checkpoint_as_allowed"] = (any(("board" in x or "checkpoint" in x or "governance" in x) for x in allowed), False)

# --- contamination scan of Resident-readable startup artifacts (manual-review hits) -------
markers = [r"\bclaim", r"should learn", r"expected (answer|semantic)", r"\bassistant\b", r"\buser said\b", r"summary",
           r"cursor\s*\d", r"previous run", r"prior run", r"last run", r"\breply\b", r"\bsilence\b", r"lesson", r"diagnos"]
hits = {}
for label, p in (("packet", pk_path), ("clean_room_contract", CAND / pk["clean_room_contract_path"]),
                 ("run_contract", CAND / pk["resident_run_contract_path"]), ("bootstrap", CAND / pk["bootstrap_path"])):
    text = p.read_text()
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in markers:
            if re.search(m, line, re.I):
                hits.setdefault(label, []).append(f"{lineno}: {line.strip()[:160]}")
checks["startup_artifact_marker_hits"] = (hits, "MANUAL_REVIEW")

# --- no real Resident execution evidence -------------------------------------------------
suspicious = [p.relative_to(PREP).as_posix() for p in PREP.rglob("*")
              if p.is_file() and re.search(r"(release[-_]?state|current[-_]?event|\.db$|\.sqlite$|world|reveal)", p.name, re.I)]
checks["no_release_state_or_world_files"] = (suspicious, [])
blob = "\n".join((PREP / p).read_text(errors="replace") for p in all_files)
checks["no_release_operator_invocation_in_evidence"] = (bool(re.search(r"release_operator\.py\s+(init|reveal|ack)", blob)), False)
checks["gate_c_user_input_synthetic"] = ("SYNTHETIC operator-prep two-round liveness probe" in (PREP / "evidence/gates/test_evidence/gate_c/round_requests.json").read_text(), True)

# --- post-gate harness edit check (timeline) ------------------------------------------------
gate_times = {g: json.loads((PREP / f"evidence/gates/gate_{g}_result.json").read_text())["generated_utc"] for g in "abcd"}
checks["timeline"] = ({
    "environment_record": json.loads((PREP / "evidence/environment_record.json").read_text())["generated_utc"],
    "rc_identity": json.loads((PREP / "evidence/rc_identity.json").read_text())["generated_utc"],
    "gates": gate_times,
    "freeze": fm["generated_utc"],
    "packet": pk["generated_utc"],
    "commit_parent_author_committer": git("show", "-s", "--format=%aI %cI", PARENT),
    "commit_head_author_committer": git("show", "-s", "--format=%aI %cI", HEAD),
    "harness_changed_in_head_commit": git("diff", "--name-only", PARENT, HEAD, "--", str(PREP.relative_to(CAND) / "harness")),
}, "MANUAL_REVIEW")

report = {}
fails = []
for k, (obs, exp) in checks.items():
    status = "INFO" if exp == "MANUAL_REVIEW" else ("PASS" if obs == exp else "RED")
    report[k] = {"observed": obs, "expected": exp, "status": status}
    if status == "RED":
        fails.append(k)
report["_value_classes"] = value_classes
report["_red"] = fails
print(json.dumps(report, indent=2, default=str))
