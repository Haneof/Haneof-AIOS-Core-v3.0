"""Resident-safe packet audit.

Operator tooling. It proves, file by file, that this operator-prep window put
no prior Resident semantics anywhere the Resident can reach:

A. the launch packet itself: strict key allowlist, value-shape limits, and a
   per-value marker scan, with the two *required* forbidden-vocabulary lists
   validated against their exact expected content instead of being content
   scanned (they are mechanical names of forbidden things, not content);
B. this window's own artifacts:
   * the real-run package (``aios_exchange``) is scanned in code-only mode by
     the frozen Gate D scanner (its code carries the transport protocol only);
   * the bootstrap script is marker scanned as raw text;
   * test files, operator tools and the Gate D scanner itself are *excluded*
     from raw marker scanning by design: they necessarily quote the prohibition
     vocabulary (patterns, negative assertions) and are not Resident-readable
     launch inputs. The exclusion is recorded in the report.
C. the clean-room inputs the packet points at: the two contract files must be
   byte-identical to the frozen control-plane commit (git blob identity), so
   this window added nothing to them.

Usage:
    python operator_tools/packet_audit.py \
        --operator-prep-root <root> --repo-root <repo> --packet <path> \
        [--frozen-control-plane <commit>]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
from typing import Any

FROZEN_CONTROL_PLANE = "b7c9e85014806637f7a01c8fd6695bc9f57672ba"

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

PACKET_ALLOWED_KEYS = {
    "openssl_version", "content_manifest_algorithm", "rc_identity_evidence_sha256",
    "tests_content_manifest_sha256", "c1_c3_regression_sha256", "due_work_entrypoint",
    "corrective_003_carry_commit", "corrective_003_probe_freeze_commit",
    "corrective_003_baseline_red_commit", "historical_review_blocked_h2",
    "historical_review_blocked_h1b", "historical_additional_ia_exact",
    "historical_corrective_002_h1_exact", "historical_corrective_002_h2_exact",
    "historical_corrective_002_ia_exact",
    "packet_version", "task_id", "status", "frozen_software_sha",
    "frozen_repository_tree", "frozen_core_tree", "frozen_tests_tree",
    "python_version", "pydantic_version", "pytest_version", "sqlite_version",
    "bootstrap_path", "bootstrap_sha256", "bootstrap_verify_command",
    "atomic_publication_sha256", "ledger_mutation_sha256",
    "wheel_lock_path", "wheel_lock_sha256", "wheel_lock_verification_sha256",
    "clean_bootstrap_evidence_path", "clean_bootstrap_evidence_sha256",
    "runtime_root_default", "runtime_venv_python_default", "harness_root",
    "harness_manifest_sha256", "harness_manifest_file_sha256", "harness_file_count", "harness_runner_module",
    "harness_entrypoint", "request_publisher_module", "response_publisher_module",
    "ledger_module", "gate_a_status", "gate_a_hash", "gate_a_test_count", "gate_b_status",
    "gate_b_hash", "gate_b_test_count", "gate_c_status", "gate_c_hash", "gate_c_test_count", "gate_d_status",
    "gate_d_hash", "gate_d_test_count", "clean_room_contract_path", "clean_room_contract_sha256",
    "resident_run_contract_path", "resident_run_contract_sha256",
    "allowed_cursor_start", "allowed_cursor_end", "real_response_mode",
    "operator_prep_exact_head", "operator_prep_exact_parent", "operator_prep_head_rule",
    "corrective_starting_main_sha", "corrective_parent_rule",
    "historical_failed_candidate_exact", "historical_failed_ia_exact",
    "corrective_probe_freeze_sha256", "targeted_baseline_red_result_sha256",
    "targeted_candidate_green_result_sha256",
    "c10_c11_probe_freeze_sha256", "c10_c11_probe_enumeration_sha256",
    "c10_c11_probe_source_hashes_sha256", "c10_c11_baseline_red_result_sha256",
    "c10_c11_candidate_green_result_sha256", "concurrency_integration_sha256",
    "durability_fault_evidence_sha256",
    "environment_record_path", "environment_record_sha256",
    "frozen_core_content_manifest_sha256", "forbidden_startup_categories",
    "forbidden_startup_paths", "allowed_startup_inputs", "generated_utc",
}
REQUIRED_PACKET_KEYS = PACKET_ALLOWED_KEYS - {"frozen_core_content_manifest_sha256"}

EXPECTED_FORBIDDEN_CATEGORIES = {
    "pm_governance_and_task_board",
    "global_checkpoint",
    "pm_adjudications_and_review_ready_reports",
    "prior_resident_run_evidence_and_exchange_ledgers",
    "independent_acceptance_reports",
    "fixture_payload",
    "evaluator_expected_semantics",
    "release_operator_source_and_release_state",
    "future_events_and_future_release_output",
    "git_history_and_pull_request_metadata_concerning_prior_runs",
    "prior_resident_semantic_summaries_claims_and_replies",
}

#: Keys whose values are the required forbidden-vocabulary lists (validated by
#: exact content, never content scanned).
VOCABULARY_KEYS = {"forbidden_startup_categories", "forbidden_startup_paths"}

#: Semantic-content markers. These describe *prior-run content*, never the
#: mechanical vocabulary of prohibitions.
FORBIDDEN_CONTENT_CHECKS: dict[str, tuple[str, ...]] = {
    "prior_user_payload": (
        r"prior user",
        r"previous user",
        r"user said",
        r"the user (wrote|asked|said|mentioned)",
        r"user message",
    ),
    "prior_assistant_text": (
        r"assistant (said|replied|wrote|responded)",
        r"resident (said|replied|wrote|responded)",
        r"previous assistant",
        r"prior reply",
    ),
    "prior_claims_or_summaries": (
        r"(prior|previous|old|earlier)\s+claims?\b",
        r"(prior|previous|old|earlier)\s+summar",
    ),
    "expected_answer_or_cognition": (
        r"expected (answer|response|reply|output|learning|outcome)",
        r"should (learn|know|conclude)",
        r"ground truth",
        r"correct answer",
    ),
    "evaluator_language": (
        r"evaluator (answer|expectation|semantic|rubric)",
        r"rubric",
        r"grading (of|the) resident",
    ),
    "prior_cursor_semantic_decisions": (
        r"cursor\s*\d+\s*(was|had|revealed|contained|meant)",
        r"at cursor \d+ (the|it|he|she|they)",
        r"event \d+ (was|said|contained)",
    ),
    "run_lineage_semantic_detail": (
        r"\bA-004\b",
        r"\bCorrective-00[12]\b",
        r"#27[3579]\b",
    ),
}

MAX_STRING_LENGTH = 400
EXCLUDED_FROM_RAW_SCAN = {
    "harness/operator_tools/packet_audit.py": "audit tool: embeds the marker patterns",
    "harness/operator_tools/no_semantic_scan.py": "gate D scanner: embeds the prohibited-vocabulary patterns",
    "harness/tests/test_gate_d_no_semantic_script.py": "gate D test: asserts the prohibited-vocabulary behaviour",
}


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


#: A marker that appears inside a prohibition ("Contains NO ... evaluator
#: expectation") names forbidden material instead of carrying it. Such matches
#: are recorded separately for human review and do not fail the audit.
NEGATION_PATTERN = re.compile(r"\b(no|not|never|without|forbid|forbidden|prohibit|prohibited|exclude|excluded)\b", re.I)
NEGATION_WINDOW = 64


def scan_text(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for category, patterns in FORBIDDEN_CONTENT_CHECKS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.I):
                line = text[: match.start()].count("\n") + 1
                window = text[max(0, match.start() - NEGATION_WINDOW) : match.start()]
                negated = bool(NEGATION_PATTERN.search(window))
                findings.append(
                    {
                        "category": category,
                        "pattern": pattern,
                        "line": line,
                        "match": match.group(0),
                        "negated": negated,
                    }
                )
    return findings


def audit_packet(packet: dict[str, Any]) -> dict[str, Any]:
    problems: list[str] = []
    from operator_tools.build_launch_packet import ALLOWED_STARTUP_INPUTS
    inputs = packet.get("allowed_startup_inputs")
    if not isinstance(inputs, list) or not all(isinstance(item, str) for item in inputs) or len(inputs) != 4 or set(inputs) != set(ALLOWED_STARTUP_INPUTS):
        problems.append("allowed_startup_inputs must equal the exact approved four-item set")
    unknown = sorted(set(packet) - PACKET_ALLOWED_KEYS)
    missing_keys = sorted(REQUIRED_PACKET_KEYS - set(packet))
    if unknown:
        problems.append(f"unknown packet keys: {unknown}")
    if missing_keys:
        problems.append(f"required packet keys are missing: {missing_keys}")
    if packet.get("status") != "PREP_REVIEW_READY":
        problems.append("packet status must remain PREP_REVIEW_READY")
    if packet.get("real_response_mode") != "EXTERNAL_CURRENT_RESIDENT_SESSION":
        problems.append("real response mode is not the approved external-session mode")
    if packet.get("operator_prep_head_rule") != "final_freeze_commit_parent_equals_corrected_candidate_exact_head":
        problems.append("corrected exact-head/parent rule is missing or incorrect")
    if packet.get("corrective_parent_rule") != "corrective_003_exact_carry_commit_parent_equals_task_start_live_main":
        problems.append("corrective-003 carry does not pin its live-main parent rule")
    historical = {
        "historical_failed_candidate_exact": "10901d467679b70437ae112747eab81f889fd5cb",
        "historical_failed_ia_exact": "e3394da5d607e34c0286c16a11837ac7ea173a56",
        "historical_corrective_002_h1_exact": "63c972ad7a19671cbdf809177f7a552aa2c2ecc6",
        "historical_corrective_002_h2_exact": "771b200c33dbd6055b1d209935f8e1552f13090f",
        "historical_corrective_002_ia_exact": "39408137edf77976d0c4833fcde551891d5d081a",
    }
    if any(packet.get(key) != value for key, value in historical.items()):
        problems.append("historical immutable failed exact identities are not pinned")
    for key in ("operator_prep_exact_head", "operator_prep_exact_parent", "corrective_starting_main_sha",
                "corrective_003_carry_commit", "corrective_003_probe_freeze_commit", "corrective_003_baseline_red_commit"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(packet.get(key, ""))):
            problems.append(f"{key} is not an exact 40-character commit identity")
    if packet.get("python_version") != "3.12.14" or packet.get("pydantic_version") != "2.13.5" or packet.get("pytest_version") != "8.4.2" or packet.get("sqlite_version") != "3.45.1":
        problems.append("packet does not pin the qualified runtime versions")
    if packet.get("openssl_version") != "OpenSSL 3.0.13 30 Jan 2024":
        problems.append("packet does not pin exact OpenSSL runtime")
    if packet.get("due_work_entrypoint") != "aios_exchange.runner:run_due_work":
        problems.append("approved due-work entrypoint missing")
    if packet.get("content_manifest_algorithm") != "sorted-path-sha256-size-json-v1":
        problems.append("canonical content algorithm mismatch")
    from aios_exchange.content_manifest import FROZEN_CORE_MANIFEST
    if packet.get("frozen_core_content_manifest_sha256") != FROZEN_CORE_MANIFEST:
        problems.append("canonical Core manifest mismatch")
    for gate in "abcd":
        if packet.get(f"gate_{gate}_status") != "PASS":
            problems.append(f"Gate {gate.upper()} is not PASS in launch packet")
        if not isinstance(packet.get(f"gate_{gate}_test_count"), int) or packet.get(f"gate_{gate}_test_count", 0) <= 0:
            problems.append(f"Gate {gate.upper()} has no non-empty test enumeration count")

    for key in VOCABULARY_KEYS:
        values = packet.get(key)
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            problems.append(f"{key} must be a list of strings")

    categories = packet.get("forbidden_startup_categories")
    if isinstance(categories, list) and set(categories) != EXPECTED_FORBIDDEN_CATEGORIES:
        problems.append("forbidden_startup_categories is not the exact required vocabulary")

    value_findings: list[dict[str, Any]] = []
    negated: list[dict[str, Any]] = []
    prose: list[str] = []

    def walk(value: Any, path: str, *, in_vocabulary: bool) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{path}.{key}", in_vocabulary=key in VOCABULARY_KEYS or in_vocabulary)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]", in_vocabulary=in_vocabulary)
        elif isinstance(value, str):
            if len(value) > MAX_STRING_LENGTH:
                problems.append(f"{path}: string longer than {MAX_STRING_LENGTH} characters")
            if "\n" in value:
                problems.append(f"{path}: string contains a newline")
            if len(value.split()) > 12:
                prose.append(path)
            if not in_vocabulary:
                for finding in scan_text(value):
                    if finding["negated"]:
                        negated.append({**finding, "path": path})
                    else:
                        value_findings.append({**finding, "path": path})

    walk(packet, "packet", in_vocabulary=False)
    if prose:
        problems.append(f"prose-shaped packet values: {prose}")

    return {
        "ok": not problems and not value_findings,
        "problems": problems,
        "value_findings": value_findings,
        "negated_matches": negated,
        "checked_keys": sorted(PACKET_ALLOWED_KEYS),
    }


def git_blob_id(repo_root: pathlib.Path, commit: str, path: str) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", f"{commit}:{path}"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def git_hash_object(repo_root: pathlib.Path, path: pathlib.Path) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "hash-object", str(path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operator-prep-root", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--packet", required=True)
    parser.add_argument("--frozen-control-plane", default=FROZEN_CONTROL_PLANE)
    args = parser.parse_args()

    root = pathlib.Path(args.operator_prep_root).resolve()
    repo = pathlib.Path(args.repo_root).resolve()
    packet_path = pathlib.Path(args.packet).resolve()
    packet = json.loads(packet_path.read_text())

    # ---- A. packet ------------------------------------------------------
    packet_audit = audit_packet(packet)
    scanned: list[dict[str, Any]] = [
        {
            "file": str(packet_path.relative_to(root)),
            "sha256": sha256_file(packet_path),
            "mode": "packet-structure+values",
            "result": "PASS" if packet_audit["ok"] else "FAIL",
            "findings": packet_audit["value_findings"],
        }
    ]

    # ---- B. this window's artifacts -------------------------------------
    gate_d_path = root / "evidence" / "gates" / "test_evidence" / "gate_d" / "no_semantic_scan_report.json"
    gate_d = json.loads(gate_d_path.read_text()) if gate_d_path.exists() else None
    scanned.append(
        {
            "file": "harness/aios_exchange/**",
            "sha256": packet.get("harness_manifest_sha256"),
            "mode": "gate D code-only scan (frozen)",
            "result": "PASS" if gate_d and gate_d["pass"] else "FAIL",
            "findings": (gate_d or {}).get("findings", []),
            "scanner": "harness/operator_tools/no_semantic_scan.py",
        }
    )

    bootstrap = root / "bootstrap" / "bootstrap_runtime.sh"
    bootstrap_matches = scan_text(bootstrap.read_text(encoding="utf-8"))
    bootstrap_findings = [item for item in bootstrap_matches if not item["negated"]]
    scanned.append(
        {
            "file": "bootstrap/bootstrap_runtime.sh",
            "sha256": sha256_file(bootstrap),
            "mode": "raw marker scan",
            "result": "PASS" if not bootstrap_findings else "FAIL",
            "findings": bootstrap_findings,
            "negated_matches": [item for item in bootstrap_matches if item["negated"]],
        }
    )
    wheel_lock = root / "bootstrap" / "PYTHON_WHEEL_LOCK.json"
    wheel_lock_matches = scan_text(wheel_lock.read_text(encoding="utf-8"))
    wheel_lock_findings = [item for item in wheel_lock_matches if not item["negated"]]
    scanned.append(
        {
            "file": "bootstrap/PYTHON_WHEEL_LOCK.json",
            "sha256": sha256_file(wheel_lock),
            "mode": "raw marker scan + pre-download trust-root pin",
            "result": "PASS" if not wheel_lock_findings else "FAIL",
            "findings": wheel_lock_findings,
        }
    )
    wheel_lock_tool = root / "bootstrap" / "wheel_lock.py"
    wheel_lock_tool_matches = scan_text(wheel_lock_tool.read_text(encoding="utf-8"))
    wheel_lock_tool_findings = [item for item in wheel_lock_tool_matches if not item["negated"]]
    scanned.append(
        {
            "file": "bootstrap/wheel_lock.py",
            "sha256": sha256_file(wheel_lock_tool),
            "mode": "raw marker scan + artifact-lock verifier",
            "result": "PASS" if not wheel_lock_tool_findings else "FAIL",
            "findings": wheel_lock_tool_findings,
        }
    )

    excluded = [
        {"file": rel, "reason": reason, "resident_readable": False}
        for rel, reason in sorted(EXCLUDED_FROM_RAW_SCAN.items())
    ]

    # ---- C. clean-room inputs ------------------------------------------
    clean_room: list[dict[str, Any]] = []
    for key in ("clean_room_contract_path", "resident_run_contract_path"):
        relative = packet[key]
        path = repo / relative
        frozen_blob = git_blob_id(repo, args.frozen_control_plane, relative)
        observed_blob = git_hash_object(repo, path)
        clean_room.append(
            {
                "file": relative,
                "sha256": sha256_file(path),
                "packet_sha256": packet[f"{'clean_room' if 'CLEAN_ROOM' in relative else 'resident_run'}_contract_sha256"],
                "frozen_control_plane_blob": frozen_blob,
                "observed_blob": observed_blob,
                "result": "PASS" if frozen_blob and frozen_blob == observed_blob else "FAIL",
            }
        )

    pin_checks: list[dict[str, Any]] = []

    def check_pin(label: str, path: pathlib.Path, expected: str) -> None:
        exists = path.is_file()
        observed = sha256_file(path) if exists else None
        pin_checks.append({
            "label": label,
            "path": str(path),
            "expected_sha256": expected,
            "observed_sha256": observed,
            "result": "PASS" if exists and observed == expected else "FAIL",
        })

    check_pin("bootstrap", root / "bootstrap/bootstrap_runtime.sh", packet.get("bootstrap_sha256", ""))
    check_pin("atomic_publication", root / "harness/aios_exchange/atomic.py", packet.get("atomic_publication_sha256", ""))
    check_pin("ledger_mutation", root / "harness/aios_exchange/ledger.py", packet.get("ledger_mutation_sha256", ""))
    check_pin("wheel_lock", root / "bootstrap/PYTHON_WHEEL_LOCK.json", packet.get("wheel_lock_sha256", ""))
    check_pin("wheel_lock_verification", root / "evidence/wheel_lock_verification.json", packet.get("wheel_lock_verification_sha256", ""))
    check_pin("clean_bootstrap_evidence", root / "evidence/clean_bootstrap_manifest.json", packet.get("clean_bootstrap_evidence_sha256", ""))
    check_pin("harness_manifest_file", root / "evidence/harness_manifest.json", packet.get("harness_manifest_file_sha256", ""))
    check_pin("environment_record", root / "evidence/environment_record.json", packet.get("environment_record_sha256", ""))
    check_pin("clean_room_contract", repo / packet.get("clean_room_contract_path", ""), packet.get("clean_room_contract_sha256", ""))
    check_pin("resident_run_contract", repo / packet.get("resident_run_contract_path", ""), packet.get("resident_run_contract_sha256", ""))
    corrective_evidence = repo / "reviews/internal_habitation/c15-rcc/v1/operator_prep_corrective_002"
    check_pin("corrective_probe_freeze", corrective_evidence / "probes_v2/PROBE_FREEZE.v2.json", packet.get("corrective_probe_freeze_sha256", ""))
    check_pin("targeted_baseline_red", corrective_evidence / "BASELINE_RED.v2.json", packet.get("targeted_baseline_red_result_sha256", ""))
    check_pin("targeted_candidate_green", root / "evidence/corrective_candidate_green.json", packet.get("targeted_candidate_green_result_sha256", ""))
    corrective_003 = repo / "reviews/internal_habitation/c15-rcc/v1/operator_prep_corrective_003"
    check_pin("c10_c11_probe_freeze", corrective_003 / "probes/PROBE_FREEZE.json", packet.get("c10_c11_probe_freeze_sha256", ""))
    check_pin("c10_c11_probe_enumeration", corrective_003 / "probes/probe_collection.txt", packet.get("c10_c11_probe_enumeration_sha256", ""))
    check_pin("c10_c11_probe_source_hashes", corrective_003 / "probes/PROBE_SHA256SUMS", packet.get("c10_c11_probe_source_hashes_sha256", ""))
    check_pin("c10_c11_baseline_red", corrective_003 / "raw/baseline/BASELINE_RED.json", packet.get("c10_c11_baseline_red_result_sha256", ""))
    check_pin("c10_c11_candidate_green", root / "evidence/c10_c11_candidate_green.json", packet.get("c10_c11_candidate_green_result_sha256", ""))
    check_pin("concurrency_integration", root / "evidence/concurrency_integration.json", packet.get("concurrency_integration_sha256", ""))
    check_pin("durability_fault_evidence", root / "evidence/durability_fault_evidence.json", packet.get("durability_fault_evidence_sha256", ""))
    try:
        freeze = json.loads((corrective_003 / "probes/PROBE_FREEZE.json").read_text())
        expected_ids = (corrective_003 / "probes/probe_collection.txt").read_text().splitlines()
        source_ok = all(sha256_file(corrective_003 / "probes" / relative) == digest
                        for relative, digest in freeze["source_sha256"].items())
        green = json.loads((root / "evidence/c10_c11_candidate_green.json").read_text())
        baseline = json.loads((corrective_003 / "raw/baseline/BASELINE_RED.json").read_text())
        proof_ok = (source_ok and freeze["enumeration_sha256"] == sha256_file(corrective_003 / "probes/probe_collection.txt")
                    and [row["test_id"] for row in freeze["expected_outcomes"]] == expected_ids
                    and len(expected_ids) == 18
                    and baseline["failed"] == 18 and baseline["passed"] == 0
                    and green["status"] == "GREEN" and green["passed"] == 18 and green["failed"] == 0
                    and green["collected_and_enumerated"] == 18
                    and [row["test_id"] for row in green["cases"]] == expected_ids
                    and all(row["status"] == "PASS" for row in green["cases"]))
        integration = json.loads((root / "evidence/concurrency_integration.json").read_text())
        durability = json.loads((root / "evidence/durability_fault_evidence.json").read_text())
        proof_ok = proof_ok and integration["status"] == "PASS" and integration["ledger_chain_ok"] is True
        proof_ok = proof_ok and durability["status"] == "PASS" and durability["verified_c11_cases"] == 10
    except (OSError, KeyError, ValueError, TypeError) as exc:
        proof_ok = False
    pin_checks.append({"label": "c10_c11_frozen_enumeration_red_green_and_integration",
                       "result": "PASS" if proof_ok else "FAIL"})

    check_pin("c1_c3_regression", root / "evidence/c1_c3_regression.json", packet.get("c1_c3_regression_sha256", ""))
    check_pin("rc_identity", root / "evidence/rc_identity.json", packet.get("rc_identity_evidence_sha256", ""))
    from operator_tools.rc_identity import verify
    rc = verify(repo)
    pin_checks.append({"label": "current_frozen_working_bytes",
        "result": "PASS" if rc["ok"] and rc["observed"]["core_content_manifest_sha256"] == packet["frozen_core_content_manifest_sha256"] and rc["observed"]["tests_content_manifest_sha256"] == packet["tests_content_manifest_sha256"] else "FAIL"})
    current_manifest = json.loads((root / "evidence/harness_manifest.json").read_text())
    for entry in current_manifest["files"]:
        check_pin("harness_content", root / entry["path"], entry["sha256"])
    parent = subprocess.check_output(["git", "-C", str(repo), "rev-parse", packet["operator_prep_exact_head"] + "^"], text=True).strip()
    initial_parent = subprocess.check_output(["git", "-C", str(repo), "rev-parse", packet["corrective_003_carry_commit"] + "^"], text=True).strip()
    probe_parent = subprocess.check_output(["git", "-C", str(repo), "rev-parse", packet["corrective_003_probe_freeze_commit"] + "^"], text=True).strip()
    red_parent = subprocess.check_output(["git", "-C", str(repo), "rev-parse", packet["corrective_003_baseline_red_commit"] + "^"], text=True).strip()
    ancestry_ok = (parent == packet["operator_prep_exact_parent"]
                   and initial_parent == packet["corrective_starting_main_sha"]
                   and probe_parent == packet["corrective_003_carry_commit"]
                   and red_parent == packet["corrective_003_probe_freeze_commit"]
                   and packet["operator_prep_exact_parent"] == packet["corrective_003_baseline_red_commit"])
    pin_checks.append({"label": "candidate_carry_probe_freeze_and_red_parent_identities",
                       "result": "PASS" if ancestry_ok else "FAIL"})
    for gate in "abcd":
        gate_root = root / "evidence/gates"
        result_path = gate_root / f"gate_{gate}_result.json"
        enumeration_path = gate_root / f"gate_{gate}_tests.txt"
        raw_path = gate_root / f"gate_{gate}_raw.txt"
        status_key = f"gate_{gate}_status"
        if not result_path.is_file():
            pin_checks.append({"label": f"gate_{gate}_result", "result": "FAIL", "reason": "missing result"})
            continue
        gate_result = json.loads(result_path.read_text(encoding="utf-8"))
        gate_hash_ok = sha256_file(result_path) == packet.get(f"gate_{gate}_hash")
        ids = gate_result.get("test_ids", [])
        test_count = gate_result.get("test_count")
        outcomes = gate_result.get("outcomes", {})
        execution_total = sum(int(outcomes.get(k, 0)) for k in ("passed", "failed", "error", "skipped"))
        metadata_ok = (
            gate_result.get("status") == packet.get(status_key) == "PASS"
            and isinstance(test_count, int)
            and test_count == len(ids) == packet.get(f"gate_{gate}_test_count")
            and test_count > 0
            and execution_total == test_count
            and gate_result.get("execution_total") == execution_total
            and enumeration_path.is_file()
            and raw_path.is_file()
            and gate_result.get("enumeration_sha256") == sha256_file(enumeration_path)
            and gate_result.get("raw_output_sha256") == sha256_file(raw_path)
        )
        pin_checks.append({
            "label": f"gate_{gate}_enumeration_execution_and_result",
            "result": "PASS" if gate_hash_ok and metadata_ok else "FAIL",
            "test_count": test_count,
            "test_ids_count": len(ids),
            "execution_total": execution_total,
            "gate_result_sha256": sha256_file(result_path),
        })

    category_report = {}
    for category in FORBIDDEN_CONTENT_CHECKS:
        findings = []
        for entry in scanned:
            findings.extend(
                item for item in entry.get("findings", []) if item.get("category") == category
            )
        category_report[category] = {
            "result": "PASS" if not findings else "FAIL",
            "findings": findings,
        }
    category_report["unmodified_clean_room_inputs"] = {
        "result": "PASS" if all(item["result"] == "PASS" for item in clean_room) else "FAIL",
        "findings": [],
    }

    result = (
        "PASS"
        if packet_audit["ok"]
        and all(entry["result"] == "PASS" for entry in scanned)
        and all(item["result"] == "PASS" for item in clean_room)
        and all(item["result"] == "PASS" for item in pin_checks)
        else "FAIL"
    )
    audit = {
        "task_id": packet["task_id"],
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "packet": str(packet_path.relative_to(root)),
        "packet_sha256": sha256_file(packet_path),
        "packet_structure": packet_audit,
        "pin_checks": pin_checks,
        "pin_check_count": len(pin_checks),
        "scanned_files": scanned,
        "scanned_file_count": len(scanned),
        "excluded_from_raw_scan": excluded,
        "clean_room_inputs": clean_room,
        "frozen_control_plane": args.frozen_control_plane,
        "forbidden_category_checks": category_report,
        "result": result,
    }
    target_path = root / "evidence" / "resident_safe_packet_audit.json"
    target_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"audit": str(target_path), "result": result,
                      "scanned": len(scanned), "categories": len(category_report)}, indent=2))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
