#!/usr/bin/env python3
"""Mechanical reproduction of the RC004 C15 classifier false-green path."""
from __future__ import annotations
import re

def candidate_classifier(text: str, pytest_exit: int) -> tuple[list[str], list[str]]:
    failed=[m.group(1) for m in re.finditer(r"^FAILED\s+([^\s:]+(?::[^\s]+)?)", text, re.M)]
    bad=[item for item in failed if not item.startswith("tests/c15_persistence/")]
    print(f"pytest_exit={pytest_exit}")
    print(f"failed_count={len(failed)}")
    print("non_downstream_failures=" + ",".join(bad))
    if bad:
        raise SystemExit("ACCEPTED_CORE_REGRESSION_EXPOSED_BY_C15")
    print("CORE_FREEZE_NOT_BLOCKED_BY_DOWNSTREAM_OPERATOR_DEBT")
    print("C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT")
    return failed,bad

def main() -> int:
    text="ERROR: usage error: unrecognized arguments: --junitxml=/unwritable/out.xml\n  inifile: pyproject.toml\n  rootdir: /frozen\n"
    failed,bad=candidate_classifier(text,pytest_exit=4)
    assert failed==[] and bad==[]
    print("REPRO_RESULT=CANDIDATE_CLASSIFIER_EXITED_ZERO_AFTER_PYTEST_EXIT_4")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
