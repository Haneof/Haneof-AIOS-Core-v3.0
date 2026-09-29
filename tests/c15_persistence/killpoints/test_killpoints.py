"""Frozen K1-K5 kill/restart convergence probes.

See ``PROBE_MANIFEST.json`` for the frozen enumeration and
``PROBE_MANIFEST.sha256`` for its hash.  The manifest is committed **before**
these probes are executed for the first time; re-running the same revision after
changing the probe code or expected outcomes is forbidden.

Each probe kills the operator with SIGKILL at one frozen barrier inside a
disposable synthetic run, resumes in a fresh process, and asserts the frozen
convergence invariant against a freshly measured uninterrupted baseline.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import assert_convergence, measure_baseline, run_kill_point  # noqa: E402

HERE = Path(__file__).resolve().parent
MANIFEST_PATH = HERE / "PROBE_MANIFEST.json"
MANIFEST_SHA_PATH = HERE / "PROBE_MANIFEST.sha256"


def _load_manifest() -> dict:
    import hashlib

    raw = MANIFEST_PATH.read_bytes()
    expected = MANIFEST_SHA_PATH.read_text().strip().split()[0]
    actual = hashlib.sha256(raw).hexdigest()
    assert actual == expected, (
        "frozen probe manifest was modified after freezing; "
        f"expected {expected}, got {actual}"
    )
    return json.loads(raw.decode("utf-8"))


MANIFEST = _load_manifest()

BASELINE = None


def pytest_configure(config):  # pragma: no cover - pytest hook
    global BASELINE
    marker = Path(os.environ.get("C15_BASELINE_CACHE", "")) if os.environ.get("C15_BASELINE_CACHE") else None
    if marker is not None and marker.is_file():
        BASELINE = json.loads(marker.read_text())


def baseline() -> dict:
    global BASELINE
    if BASELINE is None:
        BASELINE = measure_baseline()
    return BASELINE


@pytest.mark.parametrize("entry", MANIFEST["probes"], ids=[p["id"] for p in MANIFEST["probes"]])
def test_kill_point_converges(entry: dict) -> None:
    outcome = run_kill_point(entry["kill_point"])
    assert outcome["kill_at"] is None, "resumed run must not kill again"
    counters = assert_convergence(entry["id"], outcome, baseline())
    # Frozen per-probe expectations recorded in the manifest.
    for key, expectation in entry["expected"].items():
        assert key in counters, f"{entry['id']}: missing counter {key}"
        if expectation["relation"] == "eq_baseline":
            assert counters[key] == baseline()[key], (
                f"{entry['id']}: {key}={counters[key]} != baseline {baseline()[key]}"
            )
        elif expectation["relation"] == "lte_baseline":
            assert counters[key] <= baseline()[key], (
                f"{entry['id']}: {key}={counters[key]} exceeds baseline {baseline()[key]}"
            )
        else:  # pragma: no cover - guard against manifest tampering
            raise AssertionError(f"unknown relation {expectation['relation']}")
