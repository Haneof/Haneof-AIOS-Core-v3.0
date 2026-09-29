"""Frozen C10 / IA288-01: independent writers and state-driving races.

Every file below lives in tmp_path. The barriers only schedule legal calls; they
never edit candidate source or durable exchange bytes. Broken barriers time out
so a correctly serialized implementation cannot deadlock in these probes.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import inspect
import json
import pathlib
import subprocess
import sys
import threading


def _parallel(first, second):
    def outcome(call):
        try:
            return {"status": "success", "receipt": call()}
        except Exception as exc:
            return {"status": "closed", "error": f"{type(exc).__name__}: {exc}"}

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(outcome, first), pool.submit(outcome, second)
        return [a.result(timeout=20), b.result(timeout=20)]


def _pause_after_prefix_read(obj, method: str, barrier: threading.Barrier) -> None:
    original = getattr(obj, method)
    used = False

    def paced(*args, **kwargs):
        nonlocal used
        result = original(*args, **kwargs)
        if not used:
            used = True
            try:
                barrier.wait(timeout=1.5)
            except threading.BrokenBarrierError:
                pass  # serialized operation proceeds; never wait forever
        return result

    setattr(obj, method, paced)


def _pause_append_read(ledger, barrier: threading.Barrier) -> None:
    original = ledger.read_records
    used = False

    def paced():
        nonlocal used
        rows = original()  # a genuine, fully validated prefix
        # Publisher lookups are not the append read. Only delay the exact
        # read/validate/allocate/write window when the implementation uses it.
        callers = {frame.function for frame in inspect.stack()[1:6]}
        if not used and ("append" in callers or "_append_locked" in callers):
            used = True
            try:
                barrier.wait(timeout=1.5)
            except threading.BrokenBarrierError:
                pass
        return rows

    ledger.read_records = paced


def _state_is_linear(bridge):
    from aios_exchange.canonical import canonical_json_bytes

    assert bridge.ledger.verify_chain()["ok"], "two successful mutations may not corrupt the ledger"
    rows = bridge.ledger.read_records()
    assert [r["seq"] for r in rows] == list(range(1, len(rows) + 1))
    previous = "0" * 64
    for row in rows:
        assert row["prev_sha256"] == previous
        previous = row["record_sha256"]
        body = {k: v for k, v in row.items() if k != "record_sha256"}
        assert hashlib.sha256(canonical_json_bytes(body)).hexdigest() == previous
    event_counts = Counter((r["request_id"], r["event"]) for r in rows)
    assert all(count == 1 for count in event_counts.values()), "duplicate semantic dispatch/event"
    requests = [r for r in rows if r["event"] == "request_published"]
    for ordinal, row in enumerate(requests, 1):
        raw = bridge.requests.path_for(row["request_id"]).read_bytes()
        payload = json.loads(raw)
        assert hashlib.sha256(raw).hexdigest() == row["request_sha256"]
        assert payload["sequence"] == ordinal, "stale request sequence was published"
        assert payload["request_id"] == row["request_id"]
        assert bridge.requests.request_id_for(payload["kind"], payload["body"], ordinal) == row["request_id"]
    for row in rows:
        if row["event"] == "response_published":
            raw = bridge.responses.path_for(row["request_id"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row["response_sha256"]
    return rows


def _request(bridge, marker, *, request_id=None):
    return bridge.publish_request(kind="model_directive", body={"synthetic_concurrency": marker}, request_id=request_id)


def _response(request):
    return {
        "response_version": 1,
        "request_id": request["request_id"],
        "request_sha256": request["request_sha256"],
        "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
        "directive": {"response": "synthetic concurrency receipt"},
    }


def test_c10_independent_ledgers_same_valid_prefix(tmp_path):
    from aios_exchange.ledger import ExchangeLedger

    path = tmp_path / "exchange" / "ledger.jsonl"
    left, right = ExchangeLedger(path), ExchangeLedger(path)
    barrier = threading.Barrier(2)
    _pause_after_prefix_read(left, "read_records", barrier)
    _pause_after_prefix_read(right, "read_records", barrier)
    outcomes = _parallel(
        lambda: left.append("request_published", request_id="synthetic-ledger-left", request_sha256="a" * 64),
        lambda: right.append("request_published", request_id="synthetic-ledger-right", request_sha256="b" * 64),
    )
    print("C10 ledgers:", outcomes)
    rows = ExchangeLedger(path).read_records()
    assert [r["seq"] for r in rows] == list(range(1, len(rows) + 1))
    assert len(rows) == sum(o["status"] == "success" for o in outcomes)
    assert len(rows) >= 1
    assert ExchangeLedger(path).verify_chain()["ok"]


def test_c10_independent_publishers_distinct_identities(tmp_path):
    from aios_exchange.bridge import ExchangeBridge

    left, right = ExchangeBridge(tmp_path / "exchange"), ExchangeBridge(tmp_path / "exchange")
    barrier = threading.Barrier(2)
    _pause_after_prefix_read(left.requests, "next_sequence", barrier)
    _pause_after_prefix_read(right.requests, "next_sequence", barrier)
    outcomes = _parallel(lambda: _request(left, "left"), lambda: _request(right, "right"))
    print("C10 distinct publishers:", outcomes)
    rows = _state_is_linear(ExchangeBridge(left.root))
    successes = [o["receipt"] for o in outcomes if o["status"] == "success"]
    assert len(successes) >= 1
    assert len([r for r in rows if r["event"] == "request_published"]) == len(successes)
    assert len({o["request_id"] for o in successes}) == len(successes)
    for receipt in successes:
        row = next(r for r in rows if r["request_id"] == receipt["request_id"])
        assert receipt["sequence"] == row["seq"]


def test_c10_duplicate_explicit_request_id_single_dispatch(tmp_path):
    from aios_exchange.bridge import ExchangeBridge

    left, right = ExchangeBridge(tmp_path / "exchange"), ExchangeBridge(tmp_path / "exchange")
    body = {"synthetic_concurrency": "same-request"}
    rid = left.requests.request_id_for("model_directive", body, 1)
    barrier = threading.Barrier(2)
    _pause_after_prefix_read(left.requests, "next_sequence", barrier)
    _pause_after_prefix_read(right.requests, "next_sequence", barrier)
    outcomes = _parallel(
        lambda: _request(left, "same-request", request_id=rid),
        lambda: _request(right, "same-request", request_id=rid),
    )
    print("C10 duplicate request:", outcomes)
    rows = _state_is_linear(ExchangeBridge(left.root))
    assert len([r for r in rows if r["event"] == "request_published"]) == 1
    assert rows[0]["request_id"] == rid
    assert any(o["status"] == "success" for o in outcomes)
    assert len({o["receipt"]["request_id"] for o in outcomes if o["status"] == "success"}) == 1


def test_c10_response_races_new_request(tmp_path):
    from aios_exchange.bridge import ExchangeBridge

    base = ExchangeBridge(tmp_path / "exchange")
    request = _request(base, "first")
    a, b = ExchangeBridge(base.root), ExchangeBridge(base.root)
    barrier = threading.Barrier(2)
    _pause_append_read(a.ledger, barrier)
    _pause_append_read(b.ledger, barrier)
    outcomes = _parallel(
        lambda: a.responses.publish_object(request_id=request["request_id"], response=_response(request)),
        lambda: _request(b, "second"),
    )
    print("C10 response/request:", outcomes)
    rows = _state_is_linear(ExchangeBridge(base.root))
    assert sum(o["status"] == "success" for o in outcomes) >= 1
    assert sum(r["event"] == "response_published" for r in rows) <= 1
    for receipt in (o["receipt"] for o in outcomes if o["status"] == "success"):
        if "response_sha256" in receipt:
            assert any(r["event"] == "response_published" and r["response_sha256"] == receipt["response_sha256"] for r in rows)


def test_c10_consume_races_new_request(tmp_path):
    from aios_exchange.bridge import ExchangeBridge

    base = ExchangeBridge(tmp_path / "exchange")
    request = _request(base, "first")
    base.responses.publish_object(request_id=request["request_id"], response=_response(request))
    a, b = ExchangeBridge(base.root), ExchangeBridge(base.root)
    barrier = threading.Barrier(2)
    _pause_append_read(a.ledger, barrier)
    _pause_append_read(b.ledger, barrier)
    outcomes = _parallel(lambda: a.consume_response(request["request_id"]), lambda: _request(b, "second"))
    print("C10 consume/request:", [{k: (v if k != "receipt" or not isinstance(v, bytes) else "response bytes") for k, v in o.items()} for o in outcomes])
    rows = _state_is_linear(ExchangeBridge(base.root))
    assert sum(o["status"] == "success" for o in outcomes) >= 1
    assert sum(r["event"] == "response_consumed" for r in rows) <= 1


def test_c10_concurrent_duplicate_response_is_idempotent(tmp_path):
    from aios_exchange.bridge import ExchangeBridge

    base = ExchangeBridge(tmp_path / "exchange")
    request = _request(base, "response-duplicate")
    a, b = ExchangeBridge(base.root), ExchangeBridge(base.root)
    barrier = threading.Barrier(2)
    _pause_append_read(a.ledger, barrier)
    _pause_append_read(b.ledger, barrier)
    outcomes = _parallel(
        lambda: a.responses.publish_object(request_id=request["request_id"], response=_response(request)),
        lambda: b.responses.publish_object(request_id=request["request_id"], response=_response(request)),
    )
    print("C10 duplicate response:", outcomes)
    rows = _state_is_linear(ExchangeBridge(base.root))
    assert any(o["status"] == "success" for o in outcomes)
    assert sum(r["event"] == "response_published" for r in rows) == 1


def test_c10_concurrent_duplicate_consume_is_idempotent(tmp_path):
    from aios_exchange.bridge import ExchangeBridge

    base = ExchangeBridge(tmp_path / "exchange")
    request = _request(base, "consume-duplicate")
    base.responses.publish_object(request_id=request["request_id"], response=_response(request))
    a, b = ExchangeBridge(base.root), ExchangeBridge(base.root)
    barrier = threading.Barrier(2)
    _pause_append_read(a.ledger, barrier)
    _pause_append_read(b.ledger, barrier)
    outcomes = _parallel(lambda: a.consume_response(request["request_id"]), lambda: b.consume_response(request["request_id"]))
    print("C10 duplicate consume:", [{k: (v if k != "receipt" or not isinstance(v, bytes) else "response bytes") for k, v in o.items()} for o in outcomes])
    rows = _state_is_linear(ExchangeBridge(base.root))
    assert all(o["status"] == "success" for o in outcomes)
    assert sum(r["event"] == "response_consumed" for r in rows) == 1


def test_c10_independent_subprocess_publishers(tmp_path):
    from aios_exchange.bridge import ExchangeBridge

    root = tmp_path / "exchange"
    coordination = tmp_path / "coordination"
    coordination.mkdir()
    worker = pathlib.Path(__file__).parent / "synthetic" / "process_publisher.py"
    children = [subprocess.Popen([sys.executable, str(worker), str(root), str(coordination), token],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                for token in ("process-left", "process-right")]
    try:
        results = []
        for child in children:
            out, err = child.communicate(timeout=25)
            assert child.returncode == 0, (child.returncode, out, err)
            results.append(json.loads(out.strip()))
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.communicate()
    print("C10 subprocesses:", results)
    rows = _state_is_linear(ExchangeBridge(root))
    assert sum(o["status"] == "success" for o in results) >= 1
    assert len([r for r in rows if r["event"] == "request_published"]) == sum(o["status"] == "success" for o in results)
