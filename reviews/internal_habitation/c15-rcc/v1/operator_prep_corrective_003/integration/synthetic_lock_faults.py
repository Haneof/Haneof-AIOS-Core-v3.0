"""Operator-only supplemental lock acquisition faults on synthetic state."""
from __future__ import annotations

import argparse
import errno
import json
import os
import pathlib
from unittest.mock import patch

from aios_exchange.ledger import ExchangeLedger, LedgerError


def check(state: pathlib.Path) -> dict:
    assert not state.exists()
    ledger = ExchangeLedger(state / "exchange" / "ledger.jsonl")
    assert not ledger.path.exists()
    real_open = os.open

    def denied_open(path, flags, *args, **kwargs):
        if str(path) == str(ledger.lock_path):
            raise OSError(errno.EIO, "synthetic lock open failure")
        return real_open(path, flags, *args, **kwargs)

    faults = {}
    with patch("os.open", side_effect=denied_open):
        try:
            ledger.append("request_published", request_id="synthetic", request_sha256="a" * 64)
        except LedgerError as exc:
            faults["open"] = type(exc).__name__
        else:
            raise AssertionError("lock-open failure returned a successful ledger append")
    assert not ledger.path.exists()
    with patch("fcntl.flock", side_effect=OSError(errno.EIO, "synthetic flock failure")):
        try:
            ledger.append("request_published", request_id="synthetic", request_sha256="a" * 64)
        except LedgerError as exc:
            faults["flock"] = type(exc).__name__
        else:
            raise AssertionError("flock failure returned a successful ledger append")
    assert not ledger.path.exists()
    record = ledger.append("request_published", request_id="synthetic", request_sha256="a" * 64)
    assert record["seq"] == 1 and ledger.verify_chain()["ok"]
    return {"status": "PASS", "synthetic_only": True, "faults": faults,
            "no_dispatch_during_lock_failure": True, "recovery_record_count": len(ledger.read_records())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    report = check(args.state_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
