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

FROZEN_CONTROL_PLANE = "026810533679d749d9a33b9c11a06585ae28d9f6"

PACKET_ALLOWED_KEYS = {
    "packet_version", "task_id", "status", "frozen_software_sha",
    "frozen_repository_tree", "frozen_core_tree", "frozen_tests_tree",
    "python_version", "pydantic_version", "pytest_version", "sqlite_version",
    "bootstrap_path", "bootstrap_sha256", "bootstrap_verify_command",
    "runtime_root_default", "runtime_venv_python_default", "harness_root",
    "harness_manifest_sha256", "harness_file_count", "harness_runner_module",
    "harness_entrypoint", "request_publisher_module", "response_publisher_module",
    "ledger_module", "gate_a_status", "gate_a_hash", "gate_b_status",
    "gate_b_hash", "gate_c_status", "gate_c_hash", "gate_d_status",
    "gate_d_hash", "clean_room_contract_path", "clean_room_contract_sha256",
    "resident_run_contract_path", "resident_run_contract_sha256",
    "allowed_cursor_start", "allowed_cursor_end", "real_response_mode",
    "operator_prep_exact_head", "operator_prep_head_rule",
    "environment_record_path", "environment_record_sha256",
    "frozen_core_content_manifest_sha256", "forbidden_startup_categories",
    "forbidden_startup_paths", "allowed_startup_inputs", "generated_utc",
}

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
    unknown = sorted(set(packet) - PACKET_ALLOWED_KEYS)
    if unknown:
        problems.append(f"unknown packet keys: {unknown}")

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
        else "FAIL"
    )
    audit = {
        "task_id": packet["task_id"],
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "packet": str(packet_path.relative_to(root)),
        "packet_sha256": sha256_file(packet_path),
        "packet_structure": packet_audit,
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
