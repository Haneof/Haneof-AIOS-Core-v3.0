"""Fail-closed receipts for PR126's public, synthetic integration tests.

This does not certify real Resident isolation or authorize a new Core freeze.
The probe test may report that the CI host cannot run its *synthetic* canary;
that is NOT_TESTED/BLOCKED, never a passing isolation result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

POSITIVE_MODULE = "test_v3_audit_bugfixes"
PREFLIGHT_MODULES = frozenset({
    "test_c15_operator_preflight", "test_driver", "test_round3_fixes", "test_round4_fixes",
})
ISOLATION_CASE = "test_isolation_probe_execution_result"
MINIMUM_CORE_CASES = 409  # 367 pre-existing + 42 positive A01-A10 regressions
MINIMUM_PREFLIGHT_CASES = 108  # PR125's reviewed synthetic test tree


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
    synthetic_isolation: str
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


def verify_positive_source(repo: Path) -> None:
    path = "tests/integration/test_v3_audit_bugfixes.py"
    manifest = json.loads((repo / "reviews/AIOS_CONSTITUTION_FIXES_2026-09-24/manifest.json").read_text())
    expected = manifest["sha256"][path]
    actual = hashlib.sha256((repo / path).read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("A01-A10 positive test source differs from the reviewed handoff manifest")


def evaluate(report: Report, *, mode: str, pytest_exit: int) -> Decision:
    if mode not in {"core", "full"}:
        raise ValueError("mode must be core or full")
    errors = []
    if pytest_exit != 0:
        errors.append(f"pytest returned {pytest_exit}; a nonzero test run cannot pass")
    for case in report.cases:
        if case.outcome in {"failure", "error"}:
            errors.append(f"{case.identity}: {case.outcome}: {case.detail[:300]}")
        elif case.outcome == "skipped":
            errors.append(f"{case.identity}: NOT_TESTED/BLOCKED (skipped: {case.detail[:300]})")
    core = [case for case in report.cases if case.module in {"test_v3_audit_bugfixes"}]
    core_scope = [case for case in report.cases if case.classname.startswith(
        ("tests.unit.", "tests.runtime.", "tests.integration."))]
    if len(core) != 42:
        errors.append(f"expected all 42 A01-A10 cases, actually executed {len(core)}")
    if len(core_scope) < MINIMUM_CORE_CASES:
        errors.append(f"Core regression coverage shrank: {len(core_scope)} < {MINIMUM_CORE_CASES}")
    if mode == "core" and len(report.cases) != len(core_scope):
        errors.append("the Core-only run included unexpected test modules")

    preflight = [case for case in report.cases if case.module in PREFLIGHT_MODULES]
    synthetic_isolation = "NOT_RUN" if mode == "core" else "NOT_TESTED/BLOCKED"
    if mode == "full":
        if len(preflight) < MINIMUM_PREFLIGHT_CASES:
            errors.append(f"synthetic preflight coverage shrank: {len(preflight)} < {MINIMUM_PREFLIGHT_CASES}")
        probes = [case for case in preflight if case.name == ISOLATION_CASE
                  and case.module == "test_round4_fixes"]
        if len(probes) != 1:
            errors.append("the round4 synthetic isolation probe was not executed exactly once")
        elif probes[0].outcome == "passed":
            synthetic_isolation = "SYNTHETIC_CANARY_PASS_ONLY"
        # A skip/failure leaves the synthetic proof NOT_TESTED/BLOCKED even when
        # every other mechanical test passes. Real Resident isolation is *always*
        # out of scope; its status is never inferred from this test.
    return Decision(tuple(errors), len(core_scope), len(preflight), synthetic_isolation)


def exact_receipt(report: Report, decision: Decision, *, mode: str) -> dict[str, object]:
    """Publish exact numbers as an Actions annotation even if logs are unavailable."""
    return {
        "mode": mode,
        "python": sys.version.split()[0],
        "pr_head": os.environ.get("PR_HEAD_SHA", "local"),
        "checkout": os.environ.get("GITHUB_SHA", "local"),
        "tests": len(report.cases),
        "passed": len(report.cases) - report.failures - report.errors - report.skipped,
        "failures": report.failures,
        "errors": report.errors,
        "skipped": report.skipped,
        "a01_a10": sum(case.module == POSITIVE_MODULE for case in report.cases),
        "core": decision.core_count,
        "preflight": decision.preflight_count,
        "synthetic_isolation": decision.synthetic_isolation,
        "resident_isolation": decision.resident_isolation,
    }


def _escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("core", "full"), required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--pytest-exit", type=int, required=True)
    args = parser.parse_args()
    errors = []
    decision = None
    try:
        if sys.version_info < (3, 12):
            raise ValueError("Python >=3.12 is required")
        verify_positive_source(Path.cwd())
        report = read_junit(args.junit)
        decision = evaluate(report, mode=args.mode, pytest_exit=args.pytest_exit)
        errors.extend(decision.errors)
        receipt = exact_receipt(report, decision, mode=args.mode)
        print(f"{args.mode.upper()} SYNTHETIC RECEIPT: " + json.dumps(receipt, sort_keys=True))
        print("::notice title=PR126 synthetic receipt::" + _escape(json.dumps(receipt, sort_keys=True)))
        for case in report.cases:
            if case.outcome == "skipped":
                print(f"SKIP REASON {case.identity}: {case.detail}")
    except (OSError, ValueError, ET.ParseError, KeyError, TypeError) as exc:
        errors.append(f"unable to certify public synthetic test receipt: {exc}")
    for error in errors:
        print("::error title=PR126 synthetic gate::" + _escape(error[:650]))
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(f"\n### PR126 {args.mode} synthetic-only gate\n")
            summary.write(f"- Python: {sys.version.split()[0]}\n")
            summary.write(f"- Checkout: {os.environ.get('GITHUB_SHA', 'local')}\n")
            summary.write(f"- Status: {'BLOCKED' if errors else 'MECHANICAL_PASS_ONLY'}\n")
            if decision:
                summary.write(f"- A01-A10/Core cases: 42/{decision.core_count}\n")
                summary.write(f"- Preflight cases: {decision.preflight_count}\n")
                summary.write(f"- Synthetic isolation: {decision.synthetic_isolation}\n")
                summary.write(f"- Real Resident isolation: {decision.resident_isolation}\n")
            for error in errors:
                summary.write(f"- {error}\n")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
