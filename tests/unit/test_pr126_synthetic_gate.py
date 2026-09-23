"""Synthetic JUnit receipts for the additive PR126 integration gate only."""
from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from pathlib import Path

from tools.ci.pr126_synthetic_gate import (
    ISOLATION_NODEID, REAL_A_CASE, Case, Report, compare_software_collection,
    evaluate, evaluate_collection, exact_receipt, junit_nodeid, read_collection,
    read_junit, verify_default_synthetic_boundary,
)


def _core_cases() -> list[Case]:
    return [Case("tests.integration.test_v3_audit_bugfixes",
                 f"test_a{i % 10 + 1:02d}_synthetic_{i}", "passed")
            for i in range(42)] + [
        Case("tests.unit.test_synthetic_existing", f"test_existing_{i}", "passed")
        for i in range(378)
    ]


def _full_cases() -> list[Case]:
    return [*_core_cases(), *[
        Case("tests.preflight.test_driver", f"test_synthetic_preflight_{i}", "passed")
        for i in range(107)
    ], Case("tests.preflight.test_round4_fixes", "test_isolation_probe_execution_result", "passed"), *[
        Case("tests.preflight.test_round5_fixes", f"test_synthetic_round5_{i}", "passed")
        for i in range(17)
    ], *[
        Case("tests.habitation.test_public", f"test_habitation_{i}", "passed")
        for i in range(92)
    ]]


def _software_cases() -> list[Case]:
    cases = _full_cases()
    cases.pop(_probe_index(cases))
    return cases


def _report(cases: list[Case]) -> Report:
    return Report(tuple(cases), sum(c.outcome == "failure" for c in cases),
                  sum(c.outcome == "error" for c in cases),
                  sum(c.outcome == "skipped" for c in cases))


def _probe_index(cases: list[Case]) -> int:
    return next(i for i, case in enumerate(cases)
                if case.name == "test_isolation_probe_execution_result")


def test_core_gate_requires_all_42_cases_and_never_claims_real_isolation():
    receipt = evaluate(_report(_core_cases()), mode="core", pytest_exit=0)
    assert receipt.passed and receipt.core_count == 420
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
    assert any("test_a01_synthetic_0" in error for error in receipt.errors)
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
    assert receipt.passed and receipt.core_count == 420 and receipt.preflight_count == 125
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
    assert receipt["tests"] == 637 and receipt["passed"] == 636
    assert receipt["skipped"] == 1 and receipt["a01_a10"] == 42
    assert receipt["core"] == 420 and receipt["preflight"] == 125 and receipt["round5"] == 17
    assert receipt["software_regressions"] == "NOT_EVALUATED"
    assert all(receipt["a01_a10_by_bug"][f"A{i:02d}"]["passed"] > 0 for i in range(1, 11))
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
    synthetic.write_text('def test_synthetic():\n    pass\n')
    other = tmp_path / "tests/preflight/test_round4_fixes.py"
    other.write_text('def test_real_a_other_auto_probe():\n    pass\n')
    with pytest.raises(ValueError, match="real-A auto-probe"):
        verify_default_synthetic_boundary(tmp_path)


def test_software_lane_passes_without_running_or_counting_the_environment_probe():
    cases = _software_cases()
    decision = evaluate(_report(cases), mode="software", pytest_exit=0)
    assert decision.passed and decision.core_count == 420 and decision.preflight_count == 124
    assert decision.round5_count == 17 and decision.synthetic_isolation == "NOT_RUN"
    receipt = exact_receipt(_report(cases), decision, mode="software")
    assert receipt["tests"] == 636 and receipt["passed"] == 636
    assert receipt["skipped"] == 0 and receipt["software_regressions"] == "PASS"
    assert receipt["real_a_testcases"] == 0
    assert receipt["real_a_import"] == "NOT_TESTED/BLOCKED"
    assert receipt["resident_isolation"].startswith("BLOCKED")

    unexpected = [*cases, _full_cases()[_probe_index(_full_cases())]]
    assert "software lane ran the isolation probe" in " ".join(
        evaluate(_report(unexpected), mode="software", pytest_exit=0).errors)
    missing = cases[:]
    missing.pop(next(i for i, case in enumerate(missing) if case.module == "test_round5_fixes"))
    assert "round5 coverage shrank" in " ".join(
        evaluate(_report(missing), mode="software", pytest_exit=0).errors)
    missing = [case for case in cases if case.module != "test_public"]
    assert "habitation public coverage shrank" in " ".join(
        evaluate(_report(missing), mode="software", pytest_exit=0).errors)
    skipped = cases[:]
    skipped[0] = Case(skipped[0].classname, skipped[0].name, "skipped", "unexpected")
    blocked = evaluate(_report(skipped), mode="software", pytest_exit=0)
    assert not blocked.passed and "NOT_TESTED/BLOCKED" in " ".join(blocked.errors)
    assert exact_receipt(_report(skipped), blocked, mode="software")["software_regressions"] == "BLOCKED"


@pytest.mark.parametrize("outcome,pytest_exit,expected", [
    ("skipped", 0, "NOT_TESTED/BLOCKED"),
    ("failure", 1, "failure"),
    ("error", 1, "error"),
    ("passed", 2, "pytest returned 2"),
])
def test_isolation_lane_fails_closed_on_skip_failure_error_or_nonzero_exit(outcome, pytest_exit, expected):
    probe = _full_cases()[_probe_index(_full_cases())]
    result = Case(probe.classname, probe.name, outcome, "unshare not permitted")
    decision = evaluate(_report([result]), mode="isolation", pytest_exit=pytest_exit)
    assert not decision.passed and expected in " ".join(decision.errors)
    expected_isolation = ({"passed": "SYNTHETIC_CANARY_PASS_ONLY",
                           "skipped": "NOT_TESTED/BLOCKED",
                           "failure": "FAIL/BLOCKED", "error": "FAIL/BLOCKED"}[outcome])
    assert decision.synthetic_isolation == expected_isolation
    assert decision.resident_isolation.startswith("BLOCKED")
    if outcome == "skipped":
        receipt = exact_receipt(_report([result]), decision, mode="isolation")
        assert receipt["tests"] == 1 and receipt["passed"] == 0 and receipt["skipped"] == 1
        assert receipt["real_a_import"] == "NOT_TESTED/BLOCKED"


def test_isolation_lane_cannot_pass_without_original_probe_or_claim_resident():
    probe = _full_cases()[_probe_index(_full_cases())]
    decision = evaluate(_report([probe]), mode="isolation", pytest_exit=0)
    assert decision.passed and decision.synthetic_isolation == "SYNTHETIC_CANARY_PASS_ONLY"
    assert decision.real_a_import == "NOT_TESTED/BLOCKED"
    assert decision.resident_isolation.startswith("BLOCKED")
    fake = Case("tests.preflight.test_round4_fixes", "different_test", "passed")
    assert "only executed case" in " ".join(
        evaluate(_report([fake]), mode="isolation", pytest_exit=0).errors)
    assert "only executed case" in " ".join(
        evaluate(_report([probe, fake]), mode="isolation", pytest_exit=0).errors)


def test_software_collection_matches_every_public_test_except_separate_probe():
    all_collected = tuple(junit_nodeid(case) for case in _full_cases())
    software = _software_cases()
    assert not compare_software_collection(_report(software), all_collected)
    missing = software[:-1]
    assert "missing=" in " ".join(compare_software_collection(_report(missing), all_collected))
    substituted = software[:]
    substituted[0] = Case(substituted[0].classname, "test_a01_uncollected", "passed")
    assert "extra=" in " ".join(compare_software_collection(_report(substituted), all_collected))
    duplicated = software[:]
    duplicated[-1] = duplicated[0]
    assert "duplicate" in " ".join(compare_software_collection(_report(duplicated), all_collected))
    probe_in_software = [*software, _full_cases()[_probe_index(_full_cases())]]
    assert compare_software_collection(_report(probe_in_software), all_collected)


def test_boundary_collection_uses_actual_nodeids_and_never_calls_real_a(tmp_path):
    nodeids = [f"{case.classname.replace('.', '/')}.py::{case.name}" for case in _full_cases()]
    assert ISOLATION_NODEID in nodeids
    text = "\n".join([*nodeids, "637 tests collected in 0.12s"]) + "\n"
    collected = tmp_path / "collected.txt"
    collected.write_text(text)
    assert read_collection(collected) == tuple(nodeids)
    assert not evaluate_collection(read_collection(collected), pytest_exit=0)
    assert "returned 2" in " ".join(evaluate_collection(tuple(nodeids), pytest_exit=2))
    assert "one original isolation probe" in " ".join(
        evaluate_collection(tuple(node for node in nodeids if node != ISOLATION_NODEID), pytest_exit=0))
    assert "real-A tests" in " ".join(evaluate_collection(
        tuple([*nodeids, f"tests/preflight/test_real.py::{REAL_A_CASE}"]), pytest_exit=0))
    collected.write_text(f"{ISOLATION_NODEID}\n{ISOLATION_NODEID}\n")
    with pytest.raises(ValueError, match="duplicated"):
        read_collection(collected)


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
