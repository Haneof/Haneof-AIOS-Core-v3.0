"""Synthetic JUnit receipts for the additive PR126 integration gate only."""
from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from pathlib import Path

from tools.ci.pr126_synthetic_gate import (
    REAL_A_CASE, Case, Report, evaluate, exact_receipt, read_junit,
    verify_default_synthetic_boundary,
)


def _core_cases() -> list[Case]:
    return [Case("tests.integration.test_v3_audit_bugfixes", f"test_audit_{i}", "passed")
            for i in range(42)] + [
        Case("tests.unit.test_synthetic_existing", f"test_existing_{i}", "passed")
        for i in range(367)
    ]


def _full_cases() -> list[Case]:
    return [*_core_cases(), *[
        Case("test_driver", f"test_synthetic_preflight_{i}", "passed")
        for i in range(107)
    ], Case("test_round4_fixes", "test_isolation_probe_execution_result", "passed"), *[
        Case("tests.preflight.test_round5_fixes", f"test_synthetic_round5_{i}", "passed")
        for i in range(17)
    ]]


def _report(cases: list[Case]) -> Report:
    return Report(tuple(cases), sum(c.outcome == "failure" for c in cases),
                  sum(c.outcome == "error" for c in cases),
                  sum(c.outcome == "skipped" for c in cases))


def _probe_index(cases: list[Case]) -> int:
    return next(i for i, case in enumerate(cases)
                if case.name == "test_isolation_probe_execution_result")


def test_core_gate_requires_all_42_cases_and_never_claims_real_isolation():
    receipt = evaluate(_report(_core_cases()), mode="core", pytest_exit=0)
    assert receipt.passed and receipt.core_count == 409
    assert receipt.synthetic_isolation == "NOT_RUN"
    assert receipt.resident_isolation.startswith("BLOCKED")
    missing = _core_cases()[1:] + [Case("tests.unit.test_synthetic_existing", "extra", "passed")]
    assert "actually executed 41" in " ".join(evaluate(_report(missing), mode="core", pytest_exit=0).errors)


@pytest.mark.parametrize("outcome", ["failure", "error", "skipped"])
def test_core_gate_cannot_count_failed_or_skipped_case_as_pass(outcome):
    cases = _core_cases()
    cases[0] = Case(cases[0].classname, cases[0].name, outcome, "synthetic error")
    receipt = evaluate(_report(cases), mode="core", pytest_exit=1 if outcome != "skipped" else 0)
    assert not receipt.passed
    assert any("test_audit_0" in error for error in receipt.errors)
    if outcome == "skipped":
        assert any("NOT_TESTED/BLOCKED" in error for error in receipt.errors)


def test_core_gate_preserves_nonzero_pytest_exit_even_with_all_green_xml():
    receipt = evaluate(_report(_core_cases()), mode="core", pytest_exit=2)
    assert not receipt.passed
    assert any("pytest returned 2" in error for error in receipt.errors)


def test_full_gate_treats_environmental_isolation_skip_as_blocked_with_reason():
    cases = _full_cases()
    probe = _probe_index(cases)
    cases[probe] = Case(cases[probe].classname, cases[probe].name, "skipped",
                        "B: probe INCONCLUSIVE (unshare not permitted)")
    receipt = evaluate(_report(cases), mode="full", pytest_exit=0)
    assert not receipt.passed
    assert receipt.synthetic_isolation == "NOT_TESTED/BLOCKED"
    assert any("unshare not permitted" in error for error in receipt.errors)
    assert receipt.resident_isolation.startswith("BLOCKED")


def test_full_gate_pass_is_synthetic_only_and_does_not_release_resident():
    receipt = evaluate(_report(_full_cases()), mode="full", pytest_exit=0)
    assert receipt.passed and receipt.core_count == 409 and receipt.preflight_count == 125
    assert receipt.round5_count == 17
    assert receipt.synthetic_isolation == "SYNTHETIC_CANARY_PASS_ONLY"
    assert receipt.real_a_import == "NOT_TESTED/BLOCKED"
    assert receipt.resident_isolation == "BLOCKED / REAL RESOURCES NOT_TESTED"


def test_exact_receipt_preserves_skip_and_real_resource_block(monkeypatch):
    monkeypatch.setenv("PR_HEAD_SHA", "synthetic-head-sha")
    cases = _full_cases()
    probe = _probe_index(cases)
    cases[probe] = Case(cases[probe].classname, cases[probe].name, "skipped", "unshare is blocked")
    report = _report(cases)
    decision = evaluate(report, mode="full", pytest_exit=0)
    receipt = exact_receipt(report, decision, mode="full")
    assert receipt["tests"] == 534 and receipt["passed"] == 533
    assert receipt["skipped"] == 1 and receipt["a01_a10"] == 42
    assert receipt["core"] == 409 and receipt["preflight"] == 125 and receipt["round5"] == 17
    assert receipt["synthetic_isolation"] == "NOT_TESTED/BLOCKED"
    assert receipt["real_a_testcases"] == 0
    assert receipt["real_a_import"] == "NOT_TESTED/BLOCKED"
    assert receipt["resident_isolation"].startswith("BLOCKED")
    assert receipt["pr_head"] == "synthetic-head-sha"


def test_full_gate_refuses_missing_probe_and_other_unexpected_skips():
    cases = _full_cases()
    probe = _probe_index(cases)
    cases[probe] = Case("test_round4_fixes", "different_test", "passed")
    assert "not executed exactly once" in " ".join(
        evaluate(_report(cases), mode="full", pytest_exit=0).errors)
    cases[probe] = _full_cases()[probe]
    cases[43] = Case(cases[43].classname, cases[43].name, "skipped", "unrelated skip")
    assert "unrelated skip" in " ".join(
        evaluate(_report(cases), mode="full", pytest_exit=0).errors)


def test_full_gate_excludes_real_a_and_rejects_automatic_reintroduction(tmp_path):
    source_root = Path(__file__).resolve().parents[2]
    verify_default_synthetic_boundary(source_root)  # public test source only
    cases = _full_cases()
    receipt = evaluate(_report(cases), mode="full", pytest_exit=0)
    assert receipt.passed and receipt.preflight_count == 125
    assert receipt.real_a_import == "NOT_TESTED/BLOCKED"
    assert all(case.name != REAL_A_CASE for case in cases)

    cases.append(Case("tests.preflight.test_round5_fixes", REAL_A_CASE, "passed"))
    blocked = evaluate(_report(cases), mode="full", pytest_exit=0)
    assert not blocked.passed
    assert any("auto-probe appeared" in error for error in blocked.errors)

    synthetic = tmp_path / "tests/preflight/test_round5_fixes.py"
    synthetic.parent.mkdir(parents=True)
    synthetic.write_text(f"def {REAL_A_CASE}():\n    pass\n")
    with pytest.raises(ValueError, match="real-A auto-probe"):
        verify_default_synthetic_boundary(tmp_path)
    synthetic.write_text('def test_synthetic():\n    return "/tmp/real_a"\n')
    with pytest.raises(ValueError, match="host-path lookup"):
        verify_default_synthetic_boundary(tmp_path)


def test_junit_reader_refuses_inconsistent_declared_counts(tmp_path):
    xml = tmp_path / "synthetic.xml"
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", tests="1", failures="0", errors="0", skipped="0")
    case = ET.SubElement(suite, "testcase", classname="test_round4_fixes",
                         name="test_isolation_probe_execution_result")
    ET.SubElement(case, "skipped", message="environment unsupported")
    ET.ElementTree(root).write(xml)
    with pytest.raises(ValueError, match="inconsistent"):
        read_junit(xml)
    suite.set("skipped", "1")
    ET.ElementTree(root).write(xml)
    receipt = read_junit(xml)
    assert receipt.skipped == 1
    assert receipt.cases[0].detail == "environment unsupported"
