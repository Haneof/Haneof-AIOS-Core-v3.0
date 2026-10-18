"""Build the Resident-safe launch packet.

Operator tooling. The packet contains mechanical launch facts only; it is
written to the operator-prep root because the Resident is allowed to read it
and nothing else from the control plane.

Usage:
    python operator_tools/build_launch_packet.py \
        --operator-prep-root <root> --repo-root <repo> \
        --environment-record <root>/evidence/environment_record.json \
        --head <operator_prep_exact_head sha>
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
from typing import Any

TASK_ID = "C15-RCC-RES-A-RERUN-004-CORRECTIVE-003"

#: Frozen RC-REFREEZE-003 identities (software / repository / Core / tests).
FROZEN_SOFTWARE_SHA = "f20f2edfa7af00d0286493fd15196ca9503bc315"
FROZEN_REPOSITORY_TREE = "1ac3a675b884167d3a29aa432e7ef3eaff94d404"
FROZEN_CORE_TREE = "9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623"
FROZEN_TESTS_TREE = "7e33b5ef8432370234965d3ccd61248c703c4019"

CLEAN_ROOM_CONTRACT = "reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_CORRECTIVE_003_CLEAN_ROOM_CONTRACT.md"
RUN_CONTRACT = "reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_RUN_CONTRACT.md"

FORBIDDEN_STARTUP_CATEGORIES = [
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
]

FORBIDDEN_STARTUP_PATHS = [
    "governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md",
    "AIOS_v3.0_CURRENT_CHECKPOINT.md",
    "governance/**",
    "reviews/internal_habitation/c15-rcc/v1/fixture/**",
    "reviews/internal_habitation/c15-rcc/v1/evaluator/**",
    "reviews/internal_habitation/c15-rcc/v1/release/**",
    "reviews/internal_habitation/c15-rcc/v1/resident/runs/**",
    "reviews/internal_habitation/c15-rcc/**/BLOCKED_REPORT.md",
]

ALLOWED_STARTUP_INPUTS = [
    "RESIDENT_SAFE_LAUNCH_PACKET.json (this file)",
    RUN_CONTRACT,
    "mechanical environment/harness status emitted by the approved launch tools",
]


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_gate(evidence: pathlib.Path, gate: str) -> dict[str, Any]:
    path = evidence / "gates" / f"gate_{gate.lower()}_result.json"
    if not path.exists():
        return {"status": "MISSING", "hash": None}
    payload = json.loads(path.read_text())
    return {"status": payload["status"], "hash": sha256_file(path), "test_count": payload["test_count"]}


def build(operator_prep_root: pathlib.Path, repo_root: pathlib.Path, evidence: pathlib.Path, head: str) -> dict[str, Any]:
    environment = json.loads((evidence / "environment_record.json").read_text())
    manifest = json.loads((evidence / "harness_manifest.json").read_text())
    bootstrap = operator_prep_root / "bootstrap" / "bootstrap_runtime.sh"
    clean_room = repo_root / CLEAN_ROOM_CONTRACT
    run_contract = repo_root / RUN_CONTRACT

    observed = environment["observed"]
    gates = {gate: load_gate(evidence, gate) for gate in ("A", "B", "C", "D")}

    packet = {
        "packet_version": 1,
        "task_id": TASK_ID,
        "status": "PREP_REVIEW_READY",
        "frozen_software_sha": FROZEN_SOFTWARE_SHA,
        "frozen_repository_tree": FROZEN_REPOSITORY_TREE,
        "frozen_core_tree": FROZEN_CORE_TREE,
        "frozen_tests_tree": FROZEN_TESTS_TREE,
        "python_version": observed["python_version"],
        "pydantic_version": observed["pydantic_version"],
        "pytest_version": observed["pytest_version"],
        "sqlite_version": observed["sqlite_version"],
        "bootstrap_path": "reviews/internal_habitation/c15-rcc/v1/operator_prep/"
        "C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP/bootstrap/bootstrap_runtime.sh",
        "bootstrap_sha256": sha256_file(bootstrap),
        "bootstrap_verify_command": "bash <bootstrap_path> --verify",
        "runtime_root_default": environment["runtime_root"],
        "runtime_venv_python_default": environment["paths"]["venv_python"],
        "harness_root": "reviews/internal_habitation/c15-rcc/v1/operator_prep/"
        "C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP/harness",
        "harness_manifest_sha256": manifest["manifest_sha256"],
        "harness_file_count": manifest["file_count"],
        "harness_runner_module": "aios_exchange.runner",
        "harness_entrypoint": "aios_exchange.runner:run_user_turn",
        "request_publisher_module": "aios_exchange.requests:RequestPublisher",
        "response_publisher_module": "aios_exchange.responses:ResponsePublisher",
        "ledger_module": "aios_exchange.ledger:ExchangeLedger",
        "gate_a_status": gates["A"]["status"],
        "gate_a_hash": gates["A"]["hash"],
        "gate_b_status": gates["B"]["status"],
        "gate_b_hash": gates["B"]["hash"],
        "gate_c_status": gates["C"]["status"],
        "gate_c_hash": gates["C"]["hash"],
        "gate_d_status": gates["D"]["status"],
        "gate_d_hash": gates["D"]["hash"],
        "clean_room_contract_path": CLEAN_ROOM_CONTRACT,
        "clean_room_contract_sha256": sha256_file(clean_room),
        "resident_run_contract_path": RUN_CONTRACT,
        "resident_run_contract_sha256": sha256_file(run_contract),
        "allowed_cursor_start": 1,
        "allowed_cursor_end": 13,
        "real_response_mode": "EXTERNAL_CURRENT_RESIDENT_SESSION",
        "operator_prep_exact_head": head,
        "operator_prep_head_rule": "packet_commit_parent_equals_operator_prep_exact_head",
        "environment_record_path": "evidence/environment_record.json",
        "environment_record_sha256": sha256_file(evidence / "environment_record.json"),
        "frozen_core_content_manifest_sha256": environment.get("frozen_core_content_manifest_sha256"),
        "forbidden_startup_categories": FORBIDDEN_STARTUP_CATEGORIES,
        "forbidden_startup_paths": FORBIDDEN_STARTUP_PATHS,
        "allowed_startup_inputs": ALLOWED_STARTUP_INPUTS,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operator-prep-root", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--environment-record", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    root = pathlib.Path(args.operator_prep_root).resolve()
    repo = pathlib.Path(args.repo_root).resolve()
    evidence = pathlib.Path(args.environment_record).resolve().parent
    packet = build(root, repo, evidence, args.head)
    target = pathlib.Path(args.output) if args.output else root / "RESIDENT_SAFE_LAUNCH_PACKET.json"
    target.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"packet": str(target), "sha256": sha256_file(target), "status": packet["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
