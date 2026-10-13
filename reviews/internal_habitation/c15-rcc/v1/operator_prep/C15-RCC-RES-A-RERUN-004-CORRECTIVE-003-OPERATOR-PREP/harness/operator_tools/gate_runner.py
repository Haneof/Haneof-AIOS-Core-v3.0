"""Run binding gates A/B/C/D under the qualified interpreter.

Operator tooling. It refuses to run any gate unless the executing interpreter
is the qualified one (CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2), so the
whole gate set is always produced by one identical environment.

Usage:
    <venv>/bin/python operator_tools/gate_runner.py \
        --repo-root <repo> --harness-root <operator_prep>/harness \
        --evidence-dir <operator_prep>/evidence \
        [--only A,B,C,D] [--tests <dir>]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import platform
import sqlite3
import ssl
import subprocess
import sys
import time
from typing import Any

EXPECTED_PYTHON = "3.12.14"
EXPECTED_PYDANTIC = "2.13.5"
EXPECTED_PYTEST = "8.4.2"

GATE_TEST_FILES = {
    "A": "test_gate_a_durable_exchange.py",
    "B": "test_gate_b_frozen_core_contract.py",
    "C": "test_gate_c_two_round_integration.py",
    "D": "test_gate_d_no_semantic_script.py",
}


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment_snapshot() -> dict[str, Any]:
    import pydantic
    import pytest

    return {
        "python_version": platform.python_version(),
        "python_version_info": list(sys.version_info[:3]),
        "pydantic_version": pydantic.VERSION,
        "pytest_version": pytest.__version__,
        "sqlite_version": sqlite3.sqlite_version,
        "openssl_version": ssl.OPENSSL_VERSION,
        "executable": sys.executable,
    }


def assert_qualified_environment() -> dict[str, Any]:
    snapshot = environment_snapshot()
    problems = []
    if snapshot["python_version"] != EXPECTED_PYTHON:
        problems.append(f"python {snapshot['python_version']} != {EXPECTED_PYTHON}")
    if snapshot["pydantic_version"] != EXPECTED_PYDANTIC:
        problems.append(f"pydantic {snapshot['pydantic_version']} != {EXPECTED_PYDANTIC}")
    if snapshot["pytest_version"] != EXPECTED_PYTEST:
        problems.append(f"pytest {snapshot['pytest_version']} != {EXPECTED_PYTEST}")
    if snapshot["sqlite_version"] != "3.45.1":
        problems.append("SQLite exact runtime pin mismatch")
    if snapshot["openssl_version"].split()[1] != "3.0.13":
        problems.append("OpenSSL exact runtime pin mismatch")
    if problems:
        print("BLOCKED: gate runner is not running in the qualified environment:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        raise SystemExit(2)
    return snapshot


def run_pytest(
    test_file: pathlib.Path,
    *,
    env: dict[str, str],
    extra_args: list[str],
) -> subprocess.CompletedProcess:
    command = [
        sys.executable,
        "-m",
        "pytest",
        str(test_file),
        "-p",
        "no:cacheprovider",
        "-o",
        "addopts=",
        *extra_args,
    ]
    return subprocess.run(command, capture_output=True, text=True, env=env, timeout=1800)


class GateEnumerationError(RuntimeError):
    """Collection output is malformed or cannot prove the exact gate inventory."""


def parse_collection_output(stdout: str, stderr: str, returncode: int) -> list[str]:
    """Parse exact pytest node IDs and fail closed on ambiguous collection.

    The collected summary is parsed independently from the node-ID lines. A
    successful subprocess status alone is not sufficient evidence that a gate
    has a complete, non-empty enumeration.
    """
    import re

    if returncode != 0:
        raise GateEnumerationError(f"pytest --collect-only returned {returncode}")

    summary_text = "\n".join((stdout, stderr))
    summaries = re.findall(
        r"(?m)^\s*(\d+) tests? collected(?: in [^\n]+)?\s*$",
        summary_text,
    )
    if len(summaries) != 1:
        raise GateEnumerationError(
            f"expected exactly one pytest collected-total summary; found {len(summaries)}"
        )
    reported_total = int(summaries[0])

    test_ids = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if "::" in line and not line.startswith(("=", "<")):
            test_ids.append(line)
    if not test_ids:
        raise GateEnumerationError("pytest collection contains no parseable test node IDs")
    if len(set(test_ids)) != len(test_ids):
        raise GateEnumerationError("pytest collection contains duplicate test node IDs")
    if reported_total <= 0:
        raise GateEnumerationError("pytest reports a non-positive collected test total")
    if len(test_ids) != reported_total:
        raise GateEnumerationError(
            f"parsed {len(test_ids)} test IDs but pytest reports {reported_total} collected"
        )
    return test_ids


def count_outcomes(stdout: str) -> dict[str, int]:
    import re

    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for key in counts:
        matches = re.findall(rf"(\d+) {key}", stdout)
        if matches:
            counts[key] = int(matches[-1])
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--harness-root", required=True)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--only", default="A,B,C,D")
    args = parser.parse_args()

    snapshot = assert_qualified_environment()

    repo_root = pathlib.Path(args.repo_root).resolve()
    harness_root = pathlib.Path(args.harness_root).resolve()
    evidence_dir = pathlib.Path(args.evidence_dir).resolve()
    tests_dir = harness_root / "tests"
    gates_dir = evidence_dir / "gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    per_test_evidence = gates_dir / "test_evidence"
    per_test_evidence.mkdir(parents=True, exist_ok=True)

    wanted = [item.strip().upper() for item in args.only.split(",") if item.strip()]

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(harness_root), str(tests_dir), str(repo_root / "src")]
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["AIOS_REPO_ROOT"] = str(repo_root)
    env["AIOS_GATE_EVIDENCE_DIR"] = str(per_test_evidence)
    env["AIOS_FROZEN_CORE_SOURCE"] = str(repo_root / "src" / "aios_core" / "runtime" / "turn_runtime.py")

    preflight = {
        "environment": snapshot,
        "repo_root": str(repo_root),
        "harness_root": str(harness_root),
        "expected": {
            "python": EXPECTED_PYTHON,
            "pydantic": EXPECTED_PYDANTIC,
            "pytest": EXPECTED_PYTEST,
        },
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (gates_dir / "preflight.json").write_text(
        json.dumps(preflight, indent=2) + "\n", encoding="utf-8"
    )

    results: dict[str, Any] = {}
    for gate in wanted:
        if gate not in GATE_TEST_FILES:
            raise SystemExit(f"unknown gate {gate!r}; expected one of {sorted(GATE_TEST_FILES)}")
        test_file = tests_dir / GATE_TEST_FILES[gate]
        collection = run_pytest(test_file, env=env, extra_args=["--collect-only", "-q"])
        enumeration = collection.stdout + collection.stderr
        enumeration_path = gates_dir / f"gate_{gate.lower()}_tests.txt"
        enumeration_path.write_text(enumeration, encoding="utf-8")
        enumeration_sha256 = sha256_file(enumeration_path)
        try:
            test_ids = parse_collection_output(
                collection.stdout,
                collection.stderr,
                collection.returncode,
            )
            collection_error = None
        except GateEnumerationError as exc:
            test_ids = []
            collection_error = str(exc)

        if collection_error is not None:
            # Fail closed before executing any gate whose inventory is ambiguous.
            raw_path = gates_dir / f"gate_{gate.lower()}_raw.txt"
            raw_path.write_text(enumeration, encoding="utf-8")
            result = {
                "gate": gate,
                "task_id": "C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP",
                "status": "BLOCKED",
                "returncode": collection.returncode,
                "collection_returncode": collection.returncode,
                "collection_error": collection_error,
                "reported_collected_count": None,
                "execution_total": 0,
                "test_file": str(test_file.relative_to(harness_root)),
                "test_count": 0,
                "test_ids": [],
                "outcomes": {"passed": 0, "failed": 0, "error": 0, "skipped": 0},
                "duration_s": 0.0,
                "raw_output": raw_path.name,
                "raw_output_sha256": sha256_file(raw_path),
                "enumeration_sha256": enumeration_sha256,
                "environment": snapshot,
                "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            result_path = gates_dir / f"gate_{gate.lower()}_result.json"
            result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            result["result_file"] = result_path.name
            result["result_sha256"] = sha256_file(result_path)
            results[gate] = result
            print(f"gate {gate}: BLOCKED (collection: {collection_error}) -> {result_path.name}")
            continue

        started = time.time()
        completed = run_pytest(test_file, env=env, extra_args=["-v", "--tb=short", "-rA"])
        duration = time.time() - started
        raw = completed.stdout + completed.stderr
        raw_path = gates_dir / f"gate_{gate.lower()}_raw.txt"
        raw_path.write_text(raw, encoding="utf-8")

        outcomes = count_outcomes(completed.stdout)
        execution_total = sum(outcomes.values())
        status = (
            "PASS"
            if completed.returncode == 0
            and outcomes["failed"] == 0
            and outcomes["error"] == 0
            and execution_total == len(test_ids)
            else "FAIL"
        )
        result = {
            "gate": gate,
            "task_id": "C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP",
            "status": status,
            "returncode": completed.returncode,
            "collection_returncode": collection.returncode,
            "reported_collected_count": len(test_ids),
            "execution_total": execution_total,
            "test_file": str(test_file.relative_to(harness_root)),
            "test_count": len(test_ids),
            "test_ids": test_ids,
            "outcomes": outcomes,
            "duration_s": round(duration, 3),
            "raw_output": raw_path.name,
            "raw_output_sha256": sha256_file(raw_path),
            "enumeration_sha256": enumeration_sha256,
            "environment": snapshot,
            "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        result_path = gates_dir / f"gate_{gate.lower()}_result.json"
        result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        result["result_file"] = result_path.name
        result["result_sha256"] = sha256_file(result_path)
        results[gate] = result
        print(f"gate {gate}: {status} ({outcomes}, total={execution_total}/{len(test_ids)}) -> {result_path.name}")

    summary = {
        "task_id": "C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP",
        "status": "PASS" if all(item["status"] == "PASS" for item in results.values()) else "FAIL",
        "gates": {gate: {"status": item["status"], "result_file": item["result_file"], "result_sha256": item["result_sha256"]} for gate, item in results.items()},
        "environment": snapshot,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    summary_path = gates_dir / "gate_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
