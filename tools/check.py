#!/usr/bin/env python3
"""One command that answers the question this repository could not answer: is it
healthy right now?

Before this existed, the only way to know was to read 48 workflow files and work
out which subset each one runs. The workflows each run a subset, and three of
them come close to the full suite, so a green CI never meant the suite passed.
Measured: `pytest tests` needs well over 25 minutes (it was killed at 50%
progress), which is why nobody ran it by hand and why this entry point reports
its own duration instead of pretending the suite is quick.

Three steps, no new dependencies:

    1. pytest over the requested suites, with skip reasons captured
    2. the governance baseline check (drift + secret scan)
    3. a distribution of *why* tests skipped — a skipped suite is not a green one

Exit status is 0 only when both gate steps pass. Skips do not fail the run, but
they are printed, because "green because everything skipped" is a failure mode
this repository has already lived through.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ElementTree
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE = REPO_ROOT / "governance" / "baseline.json"
GOVERNANCE_CHECK = REPO_ROOT / "tools" / "governance" / "check_baseline.py"

# The suites that have to pass for anything downstream to mean anything.
DEFAULT_SUITES = ("tests",)
FAST_SUITES = ("tests/runtime", "tests/unit", "tests/audit")

# "-rs" prints "SKIPPED [1] path/to/test.py:123: reason text"
_SKIP_RE = re.compile(r"^SKIPPED \[\d+\] (?P<reason>.+)$", re.MULTILINE)


def _run_step(label: str, command: list[str], timeout: float | None) -> dict[str, object]:
    """Run one gate. Never raises for a non-zero exit; that is the result."""

    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout, stderr, returncode = completed.stdout, completed.stderr, completed.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or "")
        stderr = ""
        returncode = 124
        timed_out = True
    elapsed = time.monotonic() - started

    print(f"[{label}] exit={returncode} elapsed={elapsed:.1f}s" + (" TIMEOUT" if timed_out else ""))
    return {
        "label": label,
        "exit_code": returncode,
        "elapsed_seconds": round(elapsed, 2),
        "timed_out": timed_out,
        "stdout": stdout,
        "stderr": stderr,
    }


def _skips(output: str) -> Counter:
    """Collect skip reasons. The message is everything pytest tells us."""

    return Counter(match.group("reason").strip() for match in _SKIP_RE.finditer(output))


def _junit_path() -> Path:
    handle = tempfile.NamedTemporaryFile(suffix=".xml", delete=False)
    handle.close()
    return Path(handle.name)


def _pytest_command(suites: tuple[str, ...], junit_xml: Path) -> list[str]:
    # Two reporting channels, because each one alone is not enough:
    #   - "-rs" for humans reading the log
    #   - "--junitxml" because pytest drops the "N passed in Xs" summary line when
    #     stdout is not a terminal, so there is no summary string to parse here.
    return [
        sys.executable,
        "-m",
        "pytest",
        *suites,
        "-q",
        "-rs",
        "--junitxml",
        str(junit_xml),
        "-p",
        "no:warnings",
        "--no-header",
    ]


def _read_junit(junit_xml: Path) -> dict[str, object]:
    """Turn the JUnit report into the counts a human asked for."""

    if not junit_xml.exists():
        return {"available": False}

    try:
        tree = ElementTree.parse(junit_xml)
    except ElementTree.ParseError:
        # A run killed mid-way leaves a partial document; say so instead of hiding it.
        return {"available": False, "note": "junit report missing or truncated (run did not finish)"}

    root = tree.getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")

    total = sum(int(suite.get("tests", 0)) for suite in suites)
    failed = sum(int(suite.get("failures", 0)) for suite in suites)
    errored = sum(int(suite.get("errors", 0)) for suite in suites)
    skipped = sum(int(suite.get("skipped", 0)) for suite in suites)
    passed = max(total - failed - errored - skipped, 0)

    parts = [f"{passed} passed"]
    if failed:
        parts.append(f"{failed} failed")
    if errored:
        parts.append(f"{errored} error")
    if skipped:
        parts.append(f"{skipped} skipped")
    return {
        "available": True,
        "total": total,
        "passed": passed,
        "failed": failed,
        "errored": errored,
        "skipped": skipped,
        "summary": ", ".join(parts),
    }


def build_report(args: argparse.Namespace) -> dict[str, object]:
    report: dict[str, object] = {"repo_root": str(REPO_ROOT), "steps": []}

    if not args.no_tests:
        junit_xml = _junit_path()
        tests = _run_step(
            "tests", _pytest_command(args.suites, junit_xml), args.timeout
        )
        counts = _read_junit(junit_xml)
        report["steps"].append(tests)
        report["test_counts"] = counts
        report["test_summary"] = counts.get("summary") or "(no counts recovered)"
        report["skip_reasons"] = dict(_skips(tests["stdout"]))
        report["junit_path"] = str(junit_xml)
    else:
        report["test_summary"] = None
        report["skip_reasons"] = {}

    if not args.no_governance:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
            drift_path = handle.name
        governance = _run_step(
            "governance",
            [
                sys.executable,
                str(GOVERNANCE_CHECK),
                "--repo",
                str(REPO_ROOT),
                "--baseline",
                str(BASELINE),
                "--head",
                "HEAD",
                "--json",
                drift_path,
            ],
            args.timeout,
        )
        report["steps"].append(governance)
        report["drift_report_path"] = drift_path

    failed = [step for step in report["steps"] if step["exit_code"] != 0]
    report["ok"] = not failed
    report["total_elapsed_seconds"] = round(
        sum(float(step["elapsed_seconds"]) for step in report["steps"]), 2
    )
    return report


def print_report(report: dict[str, object]) -> None:
    print()
    print("=" * 68)
    if report["test_summary"]:
        print(f"tests      : {report['test_summary']}")
    else:
        print("tests      : skipped")

    skip_reasons = report.get("skip_reasons") or {}
    if skip_reasons:
        print(f"skip reasons: {len(skip_reasons)} distinct")
        for reason, count in sorted(skip_reasons.items(), key=lambda kv: (-kv[1], kv[0])):
            truncated = reason if len(reason) <= 96 else reason[:93] + "..."
            print(f"  {count:>4}x  {truncated}")
    else:
        print("skip reasons: none")

    for step in report["steps"]:
        marker = "PASS" if step["exit_code"] == 0 else "FAIL"
        print(f"{step['label']:<11}: {marker} ({step['elapsed_seconds']}s)")

    print(f"total      : {report['total_elapsed_seconds']}s")
    print("=" * 68)
    print("VERDICT: " + ("PASS" if report["ok"] else "FAIL"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--quick",
        action="store_true",
        help=f"run the fast suites only ({', '.join(FAST_SUITES)}) instead of all of tests/",
    )
    parser.add_argument(
        "--suite",
        action="append",
        dest="chosen_suites",
        metavar="PATH",
        help="run this suite; repeatable. Overrides --quick.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="per-step timeout in seconds. Without it, a step runs as long as it takes.",
    )
    parser.add_argument("--no-tests", action="store_true", help="skip the pytest step")
    parser.add_argument("--no-governance", action="store_true", help="skip the baseline check")
    parser.add_argument("--json", dest="json_path", metavar="PATH", help="write the report here")
    args = parser.parse_args(argv)

    if args.chosen_suites:
        args.suites = tuple(args.chosen_suites)
    elif args.quick:
        args.suites = FAST_SUITES
    else:
        args.suites = DEFAULT_SUITES

    print(f"AIOS health check — suites: {', '.join(args.suites)}")
    report = build_report(args)
    print_report(report)

    if args.json_path:
        Path(args.json_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"report written to {args.json_path}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
