"""RA-06: TOCTOU windows, direct-consume mutation, mixed due-work/user-turn.

All state is disposable synthetic state; no C15 fixture, release-state or
Resident is used.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import threading
import time

from conftest import (
    assert_chain_only,
    assert_linear,
    collect,
    run_worker,
    spawn_workers,
)


def _respond_to_open_dispatched(bridge, stop: threading.Event, label: str):
    def responder():
        while not stop.is_set():
            try:
                state = bridge.recovery_state()
            except Exception:
                time.sleep(0.01)
                continue
            for rid in state["open_dispatched"]:
                try:
                    bridge.responses.publish_object(
                        request_id=rid,
                        response={
                            "response_version": 1,
                            "request_id": rid,
                            "request_sha256": bridge.request_sha256(rid),
                            "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
                            "directive": {
                                "capability_calls": [],
                                "response": f"{label}-{rid}",
                                "silence": False,
                            },
                        },
                    )
                except Exception:
                    pass
            time.sleep(0.01)

    return responder


def test_ra06_tamper_between_artifact_write_and_ledger_append(tmp_path, exchange):
    """TOCTOU: swap the request bytes inside the publication window, then check
    that the tampered bytes can never be treated as the dispatched request."""
    import subprocess
    import sys

    worker = pathlib.Path(__file__).parent / "probe_worker.py"
    proc = subprocess.Popen(
        [sys.executable, str(worker), "toctou-publish", "--root", str(exchange),
         "--marker", "ra06-toctou"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    window = exchange / "window-open"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not window.exists():
        time.sleep(0.01)
    assert window.exists(), "publication window never opened"
    target = pathlib.Path(window.read_text())
    assert target.exists()
    target.write_bytes(b'{"reviewer_tamper":true}\n')
    out, err = proc.communicate(timeout=60)
    payload = None
    for line in reversed(out.strip().splitlines()):
        try:
            payload = json.loads(line)
            break
        except Exception:
            continue

    from aios_exchange.bridge import ExchangeBridge

    bridge = ExchangeBridge(exchange)
    rows = bridge.ledger.read_records()
    assert rows, "no durable record at all"
    assert bridge.ledger.verify_chain()["ok"], "chain corrupted by external tampering"

    tampered_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    for row in rows:
        if row["event"] == "request_published":
            # the durable record must describe the bytes the publisher wrote,
            # never the externally tampered bytes
            assert row["request_sha256"] != tampered_digest, "tampered bytes dispatched"

    # v2 (corrected expectation): an external process overwriting a published
    # file cannot be prevented by the writer, but it MUST be detected on every
    # semantic read path and must never enter a semantic result.
    detected = False
    try:
        bridge.request_body(payload["receipt"]["request_id"])
    except Exception:
        detected = True
    assert detected, "tampered request bytes were accepted as the durable request"
    integrity = bridge.integrity()
    assert integrity["ok"] is False, f"tampering not reported by integrity: {integrity}"
    assert any(
        "request file digest mismatch" in problem for problem in integrity["problems"]
    ), integrity["problems"]

    # v2: a retry of the same declared identity must never adopt drifted bytes.
    request_id = payload["receipt"]["request_id"]
    retry, retry_proc = run_worker(
        "publish-explicit", root=exchange, marker="ra06-toctou",
        request_id=request_id, timeout=60,
    )
    assert retry is not None, retry_proc.stderr
    if retry.get("ok"):
        row = bridge.ledger.latest_event(request_id, "request_published")
        raw = (exchange / "requests" / f"{request_id}.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row["request_sha256"], (
            "retry reported success while drifted bytes remained on disk"
        )
        assert ExchangeBridge(exchange).integrity()["ok"] is True
    else:
        assert "do not match the durable ledger" in str(retry.get("error", "")), retry


def test_ra06_direct_consume_after_request_file_mutation(tmp_path, exchange):
    """#290 observation, re-tested: mutate the request file, then consume directly.

    Expected: the durable response binding (request digest held in the ledger)
    is unaffected; the mutated request bytes can never enter the semantic result.
    """
    seed, _ = run_worker("publish", root=exchange, marker="ra06-direct-consume")
    request_id = seed["receipt"]["request_id"]
    published, _ = run_worker(
        "publish-response", root=exchange, request_id=request_id, marker="ra06-published-response"
    )
    assert published["ok"], published
    request_path = exchange / "requests" / f"{request_id}.json"
    request_path.write_bytes(b'{"reviewer_mutation":true}\n')

    from aios_exchange.bridge import ExchangeBridge

    bridge = ExchangeBridge(exchange)
    durable_request_digest = bridge.request_sha256(request_id)
    raw = bridge.consume_response(request_id)
    directive = bridge.directive_for(request_id)
    assert directive.response == "ra06-published-response", "semantic result drifted"
    # v2: compare against the durable request digest (the receipt carries the
    # response digest, not the request digest)
    assert json.loads(raw.decode())["request_sha256"] == durable_request_digest
    assert hashlib.sha256(raw).hexdigest() == published["receipt"]["response_sha256"]
    # the mutated request file must not be usable as a durable request
    mutated_used = False
    try:
        bridge.request_body(request_id)
        mutated_used = True
    except Exception:
        mutated_used = False
    assert not mutated_used, "mutated request bytes were accepted as the durable request"
    # v2: chain invariants only — the request artifact is deliberately drifted,
    # and the response binding (digest in ledger) must be untouched by it.
    rows = assert_chain_only(exchange)
    assert len([r for r in rows if r["event"] == "response_consumed"]) == 1
    response_row = next(r for r in rows if r["event"] == "response_published")
    assert hashlib.sha256((exchange / "responses" / f"{request_id}.json").read_bytes()).hexdigest() == (
        response_row["response_sha256"]
    ), "response bytes drifted from their durable binding"
    problems = bridge.integrity()["problems"]
    assert any("request file digest mismatch" in problem for problem in problems), problems


def test_ra06_two_processes_recover_same_dispatch(tmp_path, exchange):
    """Two independent recovery processes on one durable dispatch: no re-dispatch."""
    seed, _ = run_worker("publish", root=exchange, marker="ra06-recovery-snapshot")
    request_id = seed["receipt"]["request_id"]
    specs = [
        {"mode": "consume", "root": exchange, "gate": tmp_path / "rec-gate", "token": f"r{i}", "request_id": request_id}
        for i in range(2)
    ]
    # publish the response first, then both consumers race
    run_worker("publish-response", root=exchange, request_id=request_id, marker="ra06-recovery-resp")
    results = collect(spawn_workers(specs), timeout=90)
    assert all(r.get("ok") for r in results), results
    rows = assert_linear(exchange)
    assert len([r for r in rows if r["event"] == "request_published"]) == 1
    assert len([r for r in rows if r["event"] == "response_consumed"]) == 1


def test_ra06_due_work_and_user_turn_share_exchange_root(tmp_path, exchange):
    """Simultaneous due work and user turn on one exchange root, answered by one
    external test-only responder: no corruption, no cross-binding, no deadlock."""
    from aios_exchange.bridge import ExchangeBridge

    due_world = tmp_path / "due-world.sqlite"
    due_index = tmp_path / "due-index.sqlite"
    turn_world = tmp_path / "turn-world.sqlite"
    turn_index = tmp_path / "turn-index.sqlite"

    gate = tmp_path / "mixed-gate"
    specs = [
        {
            "mode": "due-work",
            "root": exchange,
            "gate": gate,
            "token": "due",
            "marker": str(due_world),
            "body_file": str(due_index),
            "request_id": "2026-09-29T12:00:00+00:00",
            "timeout": 40,
        },
        {
            "mode": "user-turn",
            "root": exchange,
            "gate": gate,
            "token": "turn",
            "marker": str(turn_world),
            "body_file": str(turn_index),
            "request_id": "2026-09-29T12:00:00+00:00",
            "timeout": 40,
        },
    ]
    procs = spawn_workers(specs)

    bridge = ExchangeBridge(exchange)
    stop = threading.Event()
    worker = threading.Thread(
        target=_respond_to_open_dispatched(bridge, stop, "ra06-mixed"), daemon=True
    )
    worker.start()
    try:
        results = collect(procs, timeout=150)
    finally:
        stop.set()
        worker.join(timeout=10)

    assert all(r.get("ok") for r in results), results
    rows = assert_linear(exchange)
    published = [r for r in rows if r["event"] == "request_published"]
    assert len(published) == len([r for r in rows if r["event"] == "response_published"]), rows
    assert len([r for r in rows if r["event"] == "response_consumed"]) == len(published)
    # every response must be bound to its own request digest (no cross-binding)
    for row in rows:
        if row["event"] == "response_published":
            raw = (exchange / "responses" / f"{row['request_id']}.json").read_bytes()
            envelope = json.loads(raw)
            assert envelope["request_sha256"] == row["request_sha256"], "cross-binding"
            assert envelope["request_id"] == row["request_id"]
    assert results[0]["wake_state"] == "completed", results[0]
