"""Gate D — no semantic script in the real-run package.

Mechanically scans the frozen run package (``aios_exchange``) and proves:

* no ``resident_agent.py``-style semantic router module;
* no keyword -> capability rules, no event-id/cursor rules;
* no prewritten Resident reply, claim, policy or goal;
* no hard-coded capability decision;
* no callback interface in the runner (real mode is strictly external);
* the single supported response mode is
  ``EXTERNAL_CURRENT_RESIDENT_SESSION``;
* the package never imports test-only code.
"""

from __future__ import annotations

import inspect
import json
import pathlib

import pytest

from aios_exchange import REAL_RESPONSE_MODE, runner

from operator_tools.no_semantic_scan import render_report, scan_run_package
from synthetic.gate_env import PACKAGE_ROOT, core_source_path, evidence_dir


@pytest.fixture(scope="module")
def scan_report() -> dict:
    report = scan_run_package(PACKAGE_ROOT, core_source=core_source_path())
    evidence = evidence_dir("gate_d")
    (evidence / "no_semantic_scan_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (evidence / "no_semantic_scan_report.txt").write_text(render_report(report), encoding="utf-8")
    return report


def test_gate_d_scan_passes(scan_report: dict) -> None:
    assert scan_report["pass"] is True, render_report(scan_report)
    assert scan_report["file_count"] >= 8


def test_gate_d_individual_checks(scan_report: dict) -> None:
    checks = scan_report["checks"]
    assert checks["no_semantic_module_names"] is True
    assert checks["no_capability_name_literals"] is True
    assert checks["no_content_literals"] is True
    assert checks["no_ast_policy_violations"] is True
    assert checks["runner_has_no_callback_interface"] is True
    assert checks["response_mode_declared"] is True
    assert scan_report["findings"] == [], scan_report["findings"]
    assert scan_report["capability_names_checked"], "frozen capability vocabulary was not derived"


def test_gate_d_response_mode_is_external_session() -> None:
    assert REAL_RESPONSE_MODE == "EXTERNAL_CURRENT_RESIDENT_SESSION"
    assert runner.REAL_RESPONSE_MODE == REAL_RESPONSE_MODE
    config = runner.ExternalSessionConfig(exchange_root=pathlib.Path("/tmp/synthetic-exchange-mode-check"))
    handler = runner.ExternalSessionModelHandler(config)
    for forbidden in ("callback", "cb", "provider", "responder", "model_handler", "decide"):
        assert not hasattr(handler, forbidden), forbidden
    public_instance = {name for name in vars(handler) if not name.startswith("_")}
    assert public_instance == {"config", "bridge", "handoffs"}, sorted(public_instance)
    public_class = {
        name
        for name, member in vars(runner.ExternalSessionModelHandler).items()
        if not name.startswith("_") and callable(member)
    }
    assert public_class == {"handoff_records"}, sorted(public_class)
    # the only parameter interface is the frozen Core ModelHandler call itself
    signature = inspect.signature(runner.ExternalSessionModelHandler.__call__)
    assert [name for name in signature.parameters if name != "self"] == ["snapshot"]


def test_gate_d_package_does_not_import_tests(scan_report: dict) -> None:
    for module, imports in scan_report["imports"].items():
        for imported in imports:
            assert not imported.startswith("tests"), f"{module} imports {imported}"
            assert not imported.startswith("synthetic"), f"{module} imports {imported}"
            assert not imported.startswith("operator_tools"), f"{module} imports {imported}"
            assert "resident_agent" not in imported


def test_gate_d_test_only_responder_is_outside_package() -> None:
    package_files = {path.name for path in PACKAGE_ROOT.rglob("*.py")}
    assert "deterministic_resident.py" not in package_files
    assert "synthetic" not in package_files
    responder_path = PACKAGE_ROOT.parent / "tests" / "synthetic" / "deterministic_resident.py"
    assert responder_path.exists()
    assert PACKAGE_ROOT.resolve() not in responder_path.resolve().parents
