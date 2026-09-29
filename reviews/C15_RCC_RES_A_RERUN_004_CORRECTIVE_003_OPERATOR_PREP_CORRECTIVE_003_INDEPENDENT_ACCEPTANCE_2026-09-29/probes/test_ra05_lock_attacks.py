"""RA-05: lock path/symlink/inode/staleness attacks and locking design.

These probes test the *claimed* authority properties: a dedicated persistent
lock inode, cross-process exclusion, no nested self-deadlock, fail-closed on
lock anomalies, release before awaiting an external response, and recovery from
a stale lock file left by a dead process.
"""

from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import sys
import time

from conftest import assert_linear, collect, run_worker, spawn_workers


def _lock_path(root: pathlib.Path) -> pathlib.Path:
    return root / "ledger.jsonl.lock"


def test_ra05_lock_path_is_stable_and_dedicated(tmp_path, exchange):
    from aios_exchange.ledger import ExchangeLedger

    ledger = ExchangeLedger(exchange / "ledger.jsonl")
    assert ledger.lock_path != ledger.path, "lock must not be the ledger file itself"
    assert ledger.lock_path.name.endswith(".lock")
    run_worker("publish", root=exchange, marker="ra05-lock-created")
    assert _lock_path(exchange).is_file(), "dedicated lock inode was not created"
    # independent objects resolve to the same lock path
    other = ExchangeLedger(exchange / "ledger.jsonl")
    assert str(other.lock_path) == str(ledger.lock_path)


def test_ra05_lock_symlink_fails_closed(tmp_path, exchange):
    exchange.mkdir(parents=True, exist_ok=True)
    decoy = tmp_path / "decoy-target"
    decoy.write_text("decoy")
    os.symlink(str(decoy), str(_lock_path(exchange)))
    payload, proc = run_worker("publish", root=exchange, marker="ra05-symlink")
    assert not payload["ok"], f"symlinked lock path was accepted: {payload}"
    assert "LedgerError" in payload["error"] or "ExchangeContractError" in payload["error"], payload


def test_ra05_lock_path_directory_fails_closed(tmp_path, exchange):
    exchange.mkdir(parents=True, exist_ok=True)
    _lock_path(exchange).mkdir()
    payload, proc = run_worker("publish", root=exchange, marker="ra05-dirlock")
    assert not payload["ok"], f"directory lock path was accepted: {payload}"


def test_ra05_lock_inode_replacement_still_excludes(tmp_path, exchange):
    """Replacing the lock file with a new inode while idle must be detected or
    must not break mutual exclusion for subsequent writers."""
    run_worker("publish", root=exchange, marker="ra05-seed")
    lock = _lock_path(exchange)
    lock.unlink()
    lock.write_text("")  # new inode
    specs = [
        {"mode": "publish", "root": exchange, "gate": tmp_path / "g1", "token": f"i{i}", "marker": f"ra05-after-replace-{i}"}
        for i in range(2)
    ]
    results = collect(spawn_workers(specs), timeout=90)
    assert all(r.get("ok") for r in results), results
    rows = assert_linear(exchange)
    idents = [(r["request_id"], r["event"]) for r in rows]
    assert len(idents) == len(set(idents))


def test_ra05_stale_lock_file_after_process_death(tmp_path, exchange):
    """A SIGKILLed holder leaves the lock file; a new process must proceed."""
    gate = tmp_path / "hold-gate"
    holder = subprocess.Popen(
        [sys.executable, str(pathlib.Path(__file__).parent / "probe_worker.py"), "lock-hold-stop",
         "--root", str(exchange), "--gate", str(gate), "--token", "holder"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and not list(gate.glob("ready-*")):
        time.sleep(0.01)
    (gate / "go").write_text("go")
    time.sleep(1.0)  # holder stops itself while holding the lock
    assert _lock_path(exchange).exists(), "lock file missing after acquisition"
    holder.kill()
    holder.communicate(timeout=30)
    start = time.monotonic()
    payload, proc = run_worker("publish", root=exchange, marker="ra05-after-death", timeout=60)
    elapsed = time.monotonic() - start
    assert payload and payload.get("ok"), (payload, proc.stderr)
    assert elapsed < 45, f"stale lock starved a new writer for {elapsed:.1f}s"
    assert_linear(exchange)


def test_ra05_contention_is_real_cross_process(tmp_path, exchange):
    """While a holder owns the lock, an independent process must observe exclusion."""
    gate = tmp_path / "hold-gate-2"
    holder = subprocess.Popen(
        [sys.executable, str(pathlib.Path(__file__).parent / "probe_worker.py"), "lock-hold-stop",
         "--root", str(exchange), "--gate", str(gate), "--token", "holder"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and not list(gate.glob("ready-*")):
        time.sleep(0.01)
    (gate / "go").write_text("go")
    time.sleep(1.0)
    probe, proc = run_worker("lock-nb", root=exchange, timeout=30)
    assert probe is not None, proc.stderr
    assert probe.get("acquired") is False, f"second process acquired the held lock: {probe}"
    holder.send_signal(signal.SIGCONT)
    out, err = holder.communicate(timeout=30)
    assert holder.returncode == 0, (out, err)


def test_ra05_nested_mutation_does_not_self_deadlock(tmp_path, exchange):
    """Nested transactions in one process (same path, different objects) must not
    deadlock, and must release only at the outermost exit."""
    from aios_exchange.bridge import ExchangeBridge
    from aios_exchange.ledger import ExchangeLedger

    bridge = ExchangeBridge(exchange)
    other = ExchangeLedger(exchange / "ledger.jsonl")
    with bridge.ledger.mutation():
        with bridge.ledger.mutation():
            with other.mutation():
                bridge.ledger._append_locked(
                    "request_published", request_id="ra05-nested", request_sha256="a" * 64
                )
    rows = assert_linear(exchange)
    assert len(rows) == 1


def test_ra05_lock_released_while_awaiting_external_response(tmp_path, exchange):
    """A handler blocked on external bytes must not hold the exchange lock."""
    import threading
    import time as _time

    from conftest import collect as _collect, spawn_workers as _spawn

    gate = tmp_path / "handler-gate"
    specs = [
        {"mode": "handler", "root": exchange, "gate": gate, "token": "waiting", "marker": "ra05-wait-snapshot", "timeout": 40}
    ]
    procs = _spawn(specs)
    _time.sleep(1.5)  # handler has published and is now awaiting the response
    start = _time.monotonic()
    probe, proc = run_worker("lock-nb", root=exchange, timeout=30)
    elapsed = _time.monotonic() - start
    assert probe is not None, proc.stderr
    assert probe.get("acquired") is True, (
        "handler appears to hold the mutation lock while awaiting external bytes: " f"{probe}"
    )
    assert elapsed < 20

    # finish cleanly: publish the response so the handler can exit
    from aios_exchange.bridge import ExchangeBridge

    bridge = ExchangeBridge(exchange)
    deadline = _time.monotonic() + 20
    while _time.monotonic() < deadline:
        state = bridge.recovery_state()
        if state["open_dispatched"]:
            break
        _time.sleep(0.01)
    for rid in state["open_dispatched"]:
        bridge.responses.publish_object(
            request_id=rid,
            response={
                "response_version": 1,
                "request_id": rid,
                "request_sha256": bridge.request_sha256(rid),
                "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
                "directive": {"capability_calls": [], "response": "ra05-release-response", "silence": False},
            },
        )
    results = _collect(procs, timeout=90)
    assert all(r.get("ok") for r in results), results
    assert_linear(exchange)
