"""Replay on a source-only immutable export, never on the mixed worktree.

Usage: python3.12 verify_public.py EXPORT OUTPUT [--collect-only]
Dependencies: pytest 8.x, pydantic 2.x. Export only src/**/*.py,
tests/**/*.py and pyproject.toml from the recorded commit (no fixture data).
This Python audit guard is defense in depth, NOT an OS isolation certificate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

EXCLUDED = (
    "tests/habitation/test_fixture_separation.py::test_resident_fixture_contains_only_deliverable_life_events",
    "tests/habitation/test_fixture_separation.py::test_oracle_fixture_is_physically_separate_from_resident_stream",
    "tests/habitation/test_fixture_separation.py::test_manifest_requires_fresh_world_and_evaluator_only_oracle",
    "tests/habitation/test_fixture_separation.py::test_catalog_scenarios_have_separate_resident_and_oracle_files",
    "tests/habitation/test_fixture_separation.py::test_catalog_focuses_on_behavior_not_expected_response_strings",
    "tests/habitation/test_fixture_separation.py::test_resident_subject_ids_are_opaque_and_non_semantic",
    "tests/habitation/test_fixture_separation.py::test_every_catalog_fixture_bundle_has_matching_resident_and_oracle_identity",
    "tests/habitation/test_sol_manual_resident_replay.py::test_sol_manual_resident_replay_exposes_learned_custom_policies",
    "tests/habitation/test_provider_evaluator.py::test_evaluator_cli_writes_report_for_matching_completed_run",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--collect-only", action="store_true")
    options = parser.parse_args()
    source, output = options.source.resolve(), options.output.resolve()
    collect = options.collect_only
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("This receipt requires Python 3.12")
    if (source / ".git").exists() or (source / "tests/habitation/fixtures").exists():
        raise RuntimeError("Require a source-only export without repository fixture data")
    manifest = json.loads(Path(__file__).with_name("source-files.json").read_text())
    actual = {str(p.relative_to(source)) for p in source.rglob("*.py")}
    actual.add("pyproject.toml")
    if actual != set(manifest) or any(
        hashlib.sha256((source / name).read_bytes()).hexdigest() != digest
        for name, digest in manifest.items()
    ):
        raise RuntimeError("Export differs from the recorded immutable source")
    output.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="synthetic-", dir=output)).resolve()
    # Do not pass provider credentials, git auth, or real-resource configuration.
    os.environ.clear()
    os.environ.update(HOME=str(scratch), TMPDIR=str(scratch),
                      PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1")
    tempfile.tempdir = str(scratch)
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source / "src"), str(source)]
    os.chdir(source)
    readable = [source, output, Path(sys.base_prefix).resolve()]
    readable += [Path(p).resolve() for p in sys.path if "site-packages" in p]
    # Standard-library ZoneInfo reads OS timezone tables, not benchmark data.
    from zoneinfo import TZPATH
    readable += [Path(p).resolve() for p in TZPATH]

    def guard(event, args):
        if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo",
                     "socket.bind", "subprocess.Popen", "os.system", "os.posix_spawn",
                     "os.fork", "os.exec"}:
            raise RuntimeError(f"Non-synthetic operation denied: {event}")
        if event in {"open", "sqlite3.connect"} and isinstance(args[0], (str, bytes, os.PathLike)):
            raw = os.fsdecode(args[0])
            if event == "sqlite3.connect" and raw == ":memory:":
                return
            path = Path(raw).resolve()
            if path in {Path("/dev/null"), Path("/dev/urandom")}:
                return
            if not any(path.is_relative_to(root) for root in readable):
                raise RuntimeError("File access outside synthetic export/runtime denied")
            if path.is_relative_to(source / "tests/habitation/fixtures"):
                raise RuntimeError("Repository fixture access denied")

    sys.addaudithook(guard)
    import pytest

    class Receipt:
        nodes: list[str] = []
        reports: list[dict] = []

        def pytest_collection_finish(self, session):
            self.nodes = [item.nodeid for item in session.items]

        def pytest_runtest_logreport(self, report):
            self.reports.append(dict(nodeid=report.nodeid, when=report.when,
                                     outcome=report.outcome))

    receipt = Receipt()
    args = ["tests", "-q", "-p", "no:cacheprovider"]
    if collect:
        args += ["--collect-only"]
    else:
        args += [f"--deselect={node}" for node in EXCLUDED]
        args += [f"--junitxml={output / 'public.xml'}"]
    status = int(pytest.main(args, plugins=[receipt]))
    record = dict(exit_code=status, collected=receipt.nodes, reports=receipt.reports,
                  excluded=[] if collect else list(EXCLUDED))
    (output / ("collection.json" if collect else "execution.json")).write_text(
        json.dumps(record, indent=2) + "\n")
    if status or not receipt.nodes or len(set(receipt.nodes)) != len(receipt.nodes):
        return 1
    if not collect:
        inventory = json.loads((output / "collection.json").read_text())["collected"]
        if not set(EXCLUDED).issubset(inventory):
            return 1
        if set(receipt.nodes) != set(inventory) - set(EXCLUDED):
            return 1
        calls = [r["nodeid"] for r in receipt.reports if r["when"] == "call"]
        if sorted(calls) != sorted(receipt.nodes):
            return 1
        if any(r["outcome"] != "passed" for r in receipt.reports):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
