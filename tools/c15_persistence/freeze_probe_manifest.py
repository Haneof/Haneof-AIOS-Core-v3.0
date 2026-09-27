"""Freeze the K1-K5 probe enumeration and hash it before first execution.

Run this **before** executing the probes, then commit both artefacts::

    python tools/c15_persistence/freeze_probe_manifest.py

The manifest records, for every probe: the frozen kill barrier, the resumed-run
expectations, and the convergence invariant each probe must satisfy.  The
accompanying ``PROBE_MANIFEST.sha256`` pins the bytes; ``test_killpoints.py``
refuses to run against a modified manifest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[2] / "tests" / "c15_persistence" / "killpoints"

INVARIANT = (
    "recovery converges to the same durable cursor without second reveal, duplicate "
    "ingest, duplicate semantic application, duplicate output/capability, duplicate "
    "ACK, or skipped cursor; a terminal/in_doubt outcome is not convergence"
)

PROBES: list[dict] = [
    {
        "id": "K1",
        "kill_point": "K1_AFTER_REVEAL",
        "barrier": "release state pending_reveal is durable; ingest has not started",
        "expected": {
            "reveals": {"relation": "eq_baseline"},
            "ingests": {"relation": "eq_baseline"},
            "dispatch_ledger": {"relation": "eq_baseline"},
            "capability_side_effects": {"relation": "eq_baseline"},
            "metering_rows": {"relation": "eq_baseline"},
            "assistant_outputs": {"relation": "eq_baseline"},
            "acks": {"relation": "eq_baseline"},
        },
        "invariant": INVARIANT,
    },
    {
        "id": "K2",
        "kill_point": "K2_AFTER_INGEST",
        "barrier": "event is durably ingested into World; provider dispatch has not started",
        "expected": {
            "reveals": {"relation": "eq_baseline"},
            "ingests": {"relation": "eq_baseline"},
            "dispatch_ledger": {"relation": "eq_baseline"},
            "capability_side_effects": {"relation": "eq_baseline"},
            "metering_rows": {"relation": "eq_baseline"},
            "assistant_outputs": {"relation": "eq_baseline"},
            "acks": {"relation": "eq_baseline"},
        },
        "invariant": INVARIANT,
    },
    {
        "id": "K3",
        "kill_point": "K3_AFTER_REQUEST_DISPATCH",
        "barrier": "exact provider request is durably staged/exposed/dispatched; no reply yet",
        "expected": {
            "reveals": {"relation": "eq_baseline"},
            "ingests": {"relation": "eq_baseline"},
            "dispatch_ledger": {"relation": "eq_baseline"},
            "capability_side_effects": {"relation": "eq_baseline"},
            "metering_rows": {"relation": "eq_baseline"},
            "assistant_outputs": {"relation": "eq_baseline"},
            "acks": {"relation": "eq_baseline"},
        },
        "invariant": INVARIANT,
    },
    {
        "id": "K4",
        "kill_point": "K4_AFTER_REPLY_AUTHENTICATED",
        "barrier": (
            "Core trusted-return receipt is durable for the exact reply; downstream "
            "application (remaining capability work, final round, assistant output) "
            "is not complete"
        ),
        "expected": {
            "reveals": {"relation": "eq_baseline"},
            "ingests": {"relation": "eq_baseline"},
            "dispatch_ledger": {"relation": "eq_baseline"},
            "capability_side_effects": {"relation": "eq_baseline"},
            "metering_rows": {"relation": "eq_baseline"},
            "assistant_outputs": {"relation": "eq_baseline"},
            "acks": {"relation": "eq_baseline"},
        },
        "invariant": INVARIANT,
    },
    {
        "id": "K5",
        "kill_point": "K5_AFTER_APPLIED_BEFORE_ACK",
        "barrier": "model/capability work is durably applied in Core; cursor ACK not yet issued",
        "expected": {
            "reveals": {"relation": "eq_baseline"},
            "ingests": {"relation": "eq_baseline"},
            "dispatch_ledger": {"relation": "eq_baseline"},
            "capability_side_effects": {"relation": "eq_baseline"},
            "metering_rows": {"relation": "eq_baseline"},
            "assistant_outputs": {"relation": "eq_baseline"},
            "acks": {"relation": "eq_baseline"},
        },
        "invariant": INVARIANT,
    },
]


def main() -> int:
    import subprocess
    import sys

    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", str(HERE / "test_killpoints.py")],
        cwd=str(HERE.parents[2]),
        capture_output=True,
        text=True,
    )
    manifest = {
        "manifest_version": "c15-killpoint-probe-manifest-v1",
        "invariant": INVARIANT,
        "probes": PROBES,
        "collection": {
            "command": "pytest --collect-only -q tests/c15_persistence/killpoints/test_killpoints.py",
            "returncode": collected.returncode,
            "stdout": collected.stdout.strip(),
        },
    }
    raw = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    (HERE / "PROBE_MANIFEST.json").write_text(raw, encoding="utf-8")
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    (HERE / "PROBE_MANIFEST.sha256").write_text(
        f"{digest}  PROBE_MANIFEST.json\n", encoding="utf-8"
    )
    print(f"frozen {len(PROBES)} probes; manifest sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
