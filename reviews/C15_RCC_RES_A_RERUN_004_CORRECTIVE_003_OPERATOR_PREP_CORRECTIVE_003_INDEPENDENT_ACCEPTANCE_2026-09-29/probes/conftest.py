"""Reviewer probe conftest: helpers only. No candidate imports at collection."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time

import pytest

HERE = pathlib.Path(__file__).resolve().parent
WORKER = HERE / "probe_worker.py"


def run_worker(mode: str, *, cwd: pathlib.Path | None = None, timeout: float = 90.0, **opts):
    """Run the probe worker in a fresh OS process and return (payload, proc)."""
    argv = [sys.executable, str(WORKER), mode]
    for key, value in opts.items():
        flag = "--" + key.replace("_", "-")
        if value is True:
            argv.append(flag)
        elif value is False or value is None:
            continue
        else:
            argv.extend([flag, str(value)])
    env = dict(os.environ)
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd or HERE),
        env=env,
    )
    payload = None
    for line in reversed(proc.stdout.strip().splitlines()):
        try:
            payload = json.loads(line)
            break
        except Exception:
            continue
    return payload, proc


def spawn_workers(specs, cwd: pathlib.Path | None = None):
    """Start workers that wait on a shared gate; return (procs, gate_dir)."""
    gate_dir = pathlib.Path(specs[0]["gate"])
    procs = []
    for spec in specs:
        argv = [sys.executable, str(WORKER), spec["mode"]]
        for key, value in spec.items():
            if key == "mode":
                continue
            flag = "--" + key.replace("_", "-")
            if value is True:
                argv.append(flag)
            elif value is False or value is None:
                continue
            else:
                argv.extend([flag, str(value)])
        procs.append(
            subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(cwd or HERE),
            )
        )
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        ready = list(gate_dir.glob("ready-*"))
        if len(ready) >= len(specs):
            break
        time.sleep(0.005)
    (gate_dir / "go").write_text("go")
    return procs


def collect(procs, timeout: float = 90.0):
    results = []
    for proc in procs:
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            results.append({"ok": False, "timeout": True, "stderr": err})
            continue
        payload = None
        for line in reversed((out or "").strip().splitlines()):
            try:
                payload = json.loads(line)
                break
            except Exception:
                continue
        if payload is None:
            payload = {"ok": False, "no_json": True, "stdout": out, "stderr": err}
        payload["returncode"] = proc.returncode
        results.append(payload)
    return results


def assert_linear(root: pathlib.Path, *, expect_events=None):
    """Assert the durable exchange state is linear, chained and unique."""
    from aios_exchange.bridge import ExchangeBridge
    from aios_exchange.canonical import canonical_json_bytes
    import hashlib

    bridge = ExchangeBridge(root)
    rows = bridge.ledger.read_records()
    assert bridge.ledger.verify_chain()["ok"], "ledger chain invalid"
    assert [r["seq"] for r in rows] == list(range(1, len(rows) + 1)), "seq not monotonic"
    previous = "0" * 64
    for row in rows:
        assert row["prev_sha256"] == previous, f"broken chain at seq {row['seq']}"
        body = {k: v for k, v in row.items() if k != "record_sha256"}
        assert hashlib.sha256(canonical_json_bytes(body)).hexdigest() == row["record_sha256"]
        previous = row["record_sha256"]
    counts: dict[tuple, int] = {}
    for row in rows:
        counts[(row["request_id"], row["event"])] = counts.get((row["request_id"], row["event"]), 0) + 1
    assert all(v == 1 for v in counts.values()), f"duplicate semantic event: {counts}"
    for row in rows:
        if row["event"] == "request_published":
            raw = bridge.requests.path_for(row["request_id"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row["request_sha256"], "request digest drift"
            payload = json.loads(raw)
            assert payload["request_id"] == row["request_id"]
        if row["event"] in ("response_published", "response_consumed"):
            raw = bridge.responses.path_for(row["request_id"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row["response_sha256"], "response digest drift"
    if expect_events is not None:
        observed = sorted((r["request_id"], r["event"]) for r in rows)
        assert observed == sorted(expect_events), f"event set drift: {observed}"
    return rows


@pytest.fixture()
def exchange(tmp_path):
    return tmp_path / "exchange"
