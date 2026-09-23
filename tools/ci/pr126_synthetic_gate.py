"""Fail-closed receipts for PR126's public, synthetic integration tests.

This does not certify real Resident isolation or authorize a new Core freeze.
The probe test may report that the CI host cannot run its *synthetic* canary;
that is NOT_TESTED/BLOCKED, never a passing isolation result.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

POSITIVE_MODULE = "test_v3_audit_bugfixes"
PREFLIGHT_MODULES = frozenset({
    "test_c15_operator_preflight", "test_driver", "test_round3_fixes",
    "test_round4_fixes", "test_round5_fixes",
})
ISOLATION_CASE = "test_isolation_probe_execution_result"
ISOLATION_NODEID = "tests/preflight/test_round4_fixes.py::" + ISOLATION_CASE
REAL_A_CASE = "test_real_a_copy_mechanical_import_not_tested_or_verified"
INTEGRATED_BASE_SHA = "76112ca0bb70bd4cdde2a62dee8deb7a7810a370"
# Coverage floors reflect the previously collected public sources, not target
# numbers to pad: Core 420 (including 42 A01-A10), preflight 125 (including
# the one environmental probe and 17 round5), habitation 92. Additions count
# as executed; a removed case needs explicit review instead of a green gate.
MINIMUM_CORE_CASES = 420
MINIMUM_PREFLIGHT_CASES = 125
MINIMUM_ROUND5_CASES = 17
MINIMUM_HABITATION_CASES = 92


@dataclass(frozen=True)
class Case:
    classname: str
    name: str
    outcome: str  # passed / failure / error / skipped
    detail: str = ""

    @property
    def identity(self) -> str:
        return f"{self.classname}::{self.name}"

    @property
    def module(self) -> str:
        return self.classname.rsplit(".", 1)[-1]


@dataclass(frozen=True)
class Report:
    cases: tuple[Case, ...]
    failures: int
    errors: int
    skipped: int


@dataclass(frozen=True)
class Decision:
    errors: tuple[str, ...]
    core_count: int
    preflight_count: int
    round5_count: int
    synthetic_isolation: str
    real_a_import: str = "NOT_TESTED/BLOCKED"
    resident_isolation: str = "BLOCKED / REAL RESOURCES NOT_TESTED"

    @property
    def passed(self) -> bool:
        return not self.errors


def read_junit(path: Path) -> Report:
    root = ET.parse(path).getroot()
    suites = list(root.iter("testsuite"))
    if len(suites) != 1:
        raise ValueError(f"expected exactly one pytest testsuite, got {len(suites)}")
    suite = suites[0]
    cases = []
    for node in suite.iter("testcase"):
        outcomes = [name for name in ("failure", "error", "skipped") if node.find(name) is not None]
        if len(outcomes) > 1:
            raise ValueError("one testcase has multiple mutually exclusive outcomes")
        outcome = outcomes[0] if outcomes else "passed"
        detail_node = node.find(outcome) if outcomes else None
        detail = "" if detail_node is None else str(
            detail_node.get("message") or detail_node.text or ""
        ).strip()
        cases.append(Case(str(node.get("classname") or ""), str(node.get("name") or ""), outcome, detail))
    declared = {key: int(suite.attrib[key]) for key in ("tests", "failures", "errors", "skipped")}
    actual = {
        "tests": len(cases),
        "failures": sum(case.outcome == "failure" for case in cases),
        "errors": sum(case.outcome == "error" for case in cases),
        "skipped": sum(case.outcome == "skipped" for case in cases),
    }
    if actual != declared or not cases:
        raise ValueError(f"JUnit counts are incomplete or inconsistent: declared={declared}, actual={actual}")
    return Report(tuple(cases), actual["failures"], actual["errors"], actual["skipped"])


def read_collection(path: Path) -> tuple[str, ...]:
    """Read pytest -o addopts='' -q --collect-only, not grouped quiet totals."""
    nodeids = tuple(line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                    if line.startswith("tests/") and ".py::" in line)
    if not nodeids or len(nodeids) != len(set(nodeids)):
        raise ValueError("public test collection is empty, duplicated, or not in pytest nodeid format")
    return nodeids


def junit_nodeid(case: Case) -> str:
    """Restore a pytest nodeid from its JUnit classname/name (incl. classes)."""
    parts = case.classname.split(".")
    module_index = next((i for i, part in enumerate(parts) if part.startswith("test_")), None)
    if module_index is None or not case.name:
        raise ValueError(f"testcase has no pytest nodeid: {case.identity}")
    path = "/".join(parts[:module_index + 1]) + ".py"
    suffix = "::".join(parts[module_index + 1:] + [case.name])
    return f"{path}::{suffix}"


def compare_software_collection(report: Report, nodeids: tuple[str, ...]) -> tuple[str, ...]:
    """Exact identity inventory: the *only* missing public case is the probe."""
    executed = tuple(junit_nodeid(case) for case in report.cases)
    expected = set(nodeids) - {ISOLATION_NODEID}
    missing = sorted(expected - set(executed))
    extra = sorted(set(executed) - expected)
    errors = []
    if len(executed) != len(set(executed)):
        errors.append("software JUnit contains duplicate executed nodeids")
    if len(nodeids) != len(executed) + 1 or missing or extra:
        errors.append(f"software must execute exactly default collection minus original probe: "
                      f"collected={len(nodeids)} executed={len(executed)} "
                      f"missing={missing[:3]} extra={extra[:3]}")
    return tuple(errors)


def collection_counts(nodeids: tuple[str, ...]) -> dict[str, int]:
    return {
        "core": sum(node.startswith(("tests/unit/", "tests/runtime/", "tests/integration/"))
                    for node in nodeids),
        "preflight": sum(node.startswith("tests/preflight/") for node in nodeids),
        "habitation": sum(node.startswith("tests/habitation/") for node in nodeids),
        "round5": sum(node.startswith("tests/preflight/test_round5_fixes.py::") for node in nodeids),
        "a01_a10": sum(node.startswith("tests/integration/test_v3_audit_bugfixes.py::")
                        for node in nodeids),
    }


def evaluate_collection(nodeids: tuple[str, ...], *, pytest_exit: int) -> tuple[str, ...]:
    errors = []
    if pytest_exit != 0:
        errors.append(f"public pytest collection returned {pytest_exit}")
    probes = [nodeid for nodeid in nodeids if nodeid == ISOLATION_NODEID]
    if len(probes) != 1:
        errors.append(f"default collection must include exactly one original isolation probe; got {len(probes)}")
    real_a = [nodeid for nodeid in nodeids
              if re.search(r"::test_real_a(?:_|$)", nodeid)]
    if real_a:
        errors.append(f"default public collection contains real-A tests: {real_a[:3]}")
    counts = collection_counts(nodeids)
    for name, floor in (("core", MINIMUM_CORE_CASES), ("preflight", MINIMUM_PREFLIGHT_CASES),
                        ("round5", MINIMUM_ROUND5_CASES), ("habitation", MINIMUM_HABITATION_CASES)):
        if counts[name] < floor:
            errors.append(f"public {name} collection shrank: {counts[name]} < {floor}")
    if counts["a01_a10"] != 42:
        errors.append(f"expected 42 A01-A10 collected cases, got {counts['a01_a10']}")
    for index in range(1, 11):
        if not any(node.startswith("tests/integration/test_v3_audit_bugfixes.py::")
                   and re.search(rf"(?:^|_)a{index:02d}_", node.rsplit("::", 1)[-1])
                   for node in nodeids):
            errors.append(f"A{index:02d} is absent from default collection")
    if len(nodeids) != counts["core"] + counts["preflight"] + counts["habitation"]:
        errors.append("public collection included testcases outside Core/preflight/habitation")
    return tuple(errors)


def verify_positive_source(repo: Path) -> None:
    path = "tests/integration/test_v3_audit_bugfixes.py"
    manifest = json.loads((repo / "reviews/AIOS_CONSTITUTION_FIXES_2026-09-24/manifest.json").read_text())
    expected = manifest["sha256"][path]
    actual = hashlib.sha256((repo / path).read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("A01-A10 positive test source differs from the reviewed handoff manifest")


def verify_default_synthetic_boundary(repo: Path) -> None:
    """Before pytest, reject the known real-A auto-probe and host-path scans.

    This is a test-entry guard, not a real-A attestation. Authorized real-A
    validation remains an independent invocation of the existing fixed-hash
    production entry point, never part of the public synthetic suite.
    """
    unsafe_paths = {"/tmp/real_a", "/tmp/accepted_a", "private_a"}
    for path in sorted((repo / "tests/preflight").glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_real_a_"):
                raise ValueError("real-A auto-probe must not be a default pytest test")
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in unsafe_paths:
                raise ValueError("default preflight test contains a real-A host-path lookup")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "validate_staged_core":
                raise ValueError("default preflight test must not invoke real-A verification")


def evaluate(report: Report, *, mode: str, pytest_exit: int) -> Decision:
    """Three independent lanes; keep 'full' strict for older callers.

    Only the exact original probe is excluded from the software lane; it must
    run on its own and cannot turn an unsupported namespace into a PASS.
    """
    if mode not in {"core", "software", "isolation", "full"}:
        raise ValueError("mode must be core, software, isolation, or full")
    errors = []
    if pytest_exit != 0:
        errors.append(f"pytest returned {pytest_exit}; a nonzero test run cannot pass")
    for case in report.cases:
        if case.outcome in {"failure", "error"}:
            errors.append(f"{case.identity}: {case.outcome}: {case.detail[:300]}")
        elif case.outcome == "skipped":
            errors.append(f"{case.identity}: NOT_TESTED/BLOCKED (skipped: {case.detail[:300]})")
    core = [case for case in report.cases if case.module == POSITIVE_MODULE]
    core_scope = [case for case in report.cases if case.classname.startswith(
        ("tests.unit.", "tests.runtime.", "tests.integration."))]
    preflight = [case for case in report.cases if case.module in PREFLIGHT_MODULES]
    round5 = [case for case in preflight if case.module == "test_round5_fixes"]
    habitation = [case for case in report.cases if case.classname.startswith("tests.habitation.")]
    probes = [case for case in preflight if case.name == ISOLATION_CASE
              and case.module == "test_round4_fixes"]
    if any(re.search(r"^test_real_a(?:_|$)", case.name) for case in report.cases):
        errors.append("real-A auto-probe appeared in the default synthetic test list")

    synthetic_isolation = "NOT_RUN" if mode in {"core", "software"} else "NOT_TESTED/BLOCKED"
    if mode == "isolation":
        if len(report.cases) != 1 or len(probes) != 1:
            errors.append("the original round4 isolation probe must be the only executed case")
        elif probes[0].outcome == "passed":
            synthetic_isolation = "SYNTHETIC_CANARY_PASS_ONLY"
        elif probes[0].outcome in {"failure", "error"}:
            synthetic_isolation = "FAIL/BLOCKED"
        # An unsupported (skipped) probe is NOT_TESTED/BLOCKED, never a pass.
    else:
        if len(core) != 42:
            errors.append(f"expected all 42 A01-A10 cases, actually executed {len(core)}")
        for index in range(1, 11):
            bug_id = f"A{index:02d}"
            if not any(re.search(rf"(?:^|_)a{index:02d}_", case.name) for case in core):
                errors.append(f"{bug_id} has no executed positive regression")
        if len(core_scope) < MINIMUM_CORE_CASES:
            errors.append(f"Core regression coverage shrank: {len(core_scope)} < {MINIMUM_CORE_CASES}")
        if mode == "core":
            if len(report.cases) != len(core_scope):
                errors.append("the Core-only run included unexpected test modules")
        else:
            minimum_preflight = MINIMUM_PREFLIGHT_CASES - (mode == "software")
            if len(preflight) < minimum_preflight:
                errors.append(f"synthetic preflight coverage shrank: {len(preflight)} < {minimum_preflight}")
            if len(round5) < MINIMUM_ROUND5_CASES:
                errors.append(f"reviewed PR125 round5 coverage shrank: {len(round5)} < {MINIMUM_ROUND5_CASES}")
            if len(habitation) < MINIMUM_HABITATION_CASES:
                errors.append(f"habitation public coverage shrank: {len(habitation)} < {MINIMUM_HABITATION_CASES}")
            if len(report.cases) != len(core_scope) + len(preflight) + len(habitation):
                errors.append("public suite included testcases outside Core/preflight/habitation")
            if mode == "software" and probes:
                errors.append("software lane ran the isolation probe; run it only in the environment lane")
            if mode == "full":
                if len(probes) != 1:
                    errors.append("the round4 synthetic isolation probe was not executed exactly once")
                elif probes[0].outcome == "passed":
                    synthetic_isolation = "SYNTHETIC_CANARY_PASS_ONLY"
                elif probes[0].outcome in {"failure", "error"}:
                    synthetic_isolation = "FAIL/BLOCKED"
    return Decision(tuple(errors), len(core_scope), len(preflight), len(round5), synthetic_isolation)


def verify_checkout(repo: Path) -> str:
    """Reject GitHub's moving base merge-ref; attest to this one PR125 base."""
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    intended = os.environ.get("PR_HEAD_SHA")
    if intended and head != intended:
        raise ValueError(f"checkout {head} is not the pinned PR head {intended}")
    if subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                       INTEGRATED_BASE_SHA, head], check=False, capture_output=True).returncode != 0:
        raise ValueError(f"checkout does not include the specified PR125 base {INTEGRATED_BASE_SHA}")
    return head


def exact_receipt(report: Report, decision: Decision, *, mode: str, checkout: str = "local") -> dict[str, object]:
    """Publish exact numbers and proof boundaries, even if logs are unavailable."""
    by_bug = {}
    for index in range(1, 11):
        matches = [case for case in report.cases if case.module == POSITIVE_MODULE
                   and re.search(rf"(?:^|_)a{index:02d}_", case.name)]
        by_bug[f"A{index:02d}"] = {
            "executed": len(matches),
            "passed": sum(case.outcome == "passed" for case in matches),
            "failures": sum(case.outcome == "failure" for case in matches),
            "errors": sum(case.outcome == "error" for case in matches),
            "skipped": sum(case.outcome == "skipped" for case in matches),
        }
    return {
        "mode": mode,
        "software_regressions": ("PASS" if decision.passed else "BLOCKED")
        if mode in {"core", "software"} else "NOT_EVALUATED",
        "a01_a10_by_bug": by_bug,
        "python": sys.version.split()[0],
        "pr_head": os.environ.get("PR_HEAD_SHA", "local"),
        "checkout": checkout,
        "integrated_base": INTEGRATED_BASE_SHA,
        "tests": len(report.cases),
        "passed": len(report.cases) - report.failures - report.errors - report.skipped,
        "failures": report.failures,
        "errors": report.errors,
        "skipped": report.skipped,
        "a01_a10": sum(case.module == POSITIVE_MODULE for case in report.cases),
        "core": decision.core_count,
        "preflight": decision.preflight_count,
        "round5": decision.round5_count,
        "synthetic_isolation": decision.synthetic_isolation,
        "real_a_testcases": sum(case.name == REAL_A_CASE for case in report.cases),
        "real_a_import": decision.real_a_import,
        "resident_isolation": decision.resident_isolation,
    }


def _escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("boundary", "core", "software", "isolation", "full"), required=True)
    parser.add_argument("--junit", type=Path)
    parser.add_argument("--collected", type=Path)
    parser.add_argument("--pytest-exit", type=int, required=True)
    args = parser.parse_args()
    errors = []
    decision = None
    report = None
    receipt = None
    checkout = "NOT_VERIFIED"
    try:
        if sys.version_info < (3, 12):
            raise ValueError("Python >=3.12 is required")
        repo = Path.cwd()
        checkout = verify_checkout(repo)
        verify_positive_source(repo)
        verify_default_synthetic_boundary(repo)
        if args.mode == "boundary":
            if args.collected is None or args.junit is not None:
                raise ValueError("boundary mode needs --collected and no --junit")
            nodeids = read_collection(args.collected)
            errors.extend(evaluate_collection(nodeids, pytest_exit=args.pytest_exit))
            real_a = sum(bool(re.search(r"::test_real_a(?:_|$)", nodeid)) for nodeid in nodeids)
            receipt = {
                "mode": "boundary", "pr_head": os.environ.get("PR_HEAD_SHA", "local"),
                "checkout": checkout, "integrated_base": INTEGRATED_BASE_SHA,
                "default_collected": len(nodeids), **collection_counts(nodeids),
                "original_isolation_probe": nodeids.count(ISOLATION_NODEID),
                "real_a_testcases": real_a, "real_a_import": "NOT_TESTED/BLOCKED",
                "resident_isolation": "BLOCKED / REAL RESOURCES NOT_TESTED",
                "status": "BLOCKED" if errors else "DEFAULT_COLLECTION_BOUNDARY_PASS_ONLY",
            }
        else:
            if args.junit is None or (args.mode == "software") != (args.collected is not None):
                raise ValueError("test modes need --junit; software additionally needs --collected")
            report = read_junit(args.junit)
            decision = evaluate(report, mode=args.mode, pytest_exit=args.pytest_exit)
            errors.extend(decision.errors)
            receipt = exact_receipt(report, decision, mode=args.mode, checkout=checkout)
            if args.mode == "software":
                nodeids = read_collection(args.collected)
                errors.extend(evaluate_collection(nodeids, pytest_exit=0))
                errors.extend(compare_software_collection(report, nodeids))
                receipt.update({"default_collected": len(nodeids),
                                "separately_executed_environment_case": ISOLATION_NODEID,
                                "deliberate_deselections": len(nodeids) - len(report.cases),
                                "software_regressions": "BLOCKED" if errors else "PASS"})
            for case in report.cases:
                if case.outcome == "skipped":
                    print(f"SKIP REASON {case.identity}: {case.detail}")
        print(f"{args.mode.upper()} SYNTHETIC RECEIPT: " + json.dumps(receipt, sort_keys=True))
        print("::notice title=PR126 synthetic receipt::" + _escape(json.dumps(receipt, sort_keys=True)))
    except (OSError, ValueError, ET.ParseError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        errors.append(f"unable to certify public synthetic test receipt: {exc}")
    for error in errors:
        print("::error title=PR126 synthetic gate::" + _escape(error[:650]))
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(f"\n### PR126 {args.mode} synthetic-only gate\n")
            summary.write(f"- Python: {sys.version.split()[0]}\n")
            summary.write(f"- Checkout: {checkout}\n")
            status = ("BLOCKED" if errors else "SOFTWARE_PASS_ONLY" if args.mode in {"core", "software"}
                      else "DEFAULT_COLLECTION_BOUNDARY_PASS_ONLY" if args.mode == "boundary"
                      else "SYNTHETIC_CANARY_PASS_ONLY")
            summary.write(f"- Status: {status}\n")
            if receipt:
                summary.write(f"- Actual receipt: {json.dumps(receipt, sort_keys=True)}\n")
            if decision:
                summary.write(f"- Synthetic isolation: {decision.synthetic_isolation}\n")
                summary.write(f"- Real Resident isolation: {decision.resident_isolation}\n")
            for error in errors:
                summary.write(f"- {error}\n")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
