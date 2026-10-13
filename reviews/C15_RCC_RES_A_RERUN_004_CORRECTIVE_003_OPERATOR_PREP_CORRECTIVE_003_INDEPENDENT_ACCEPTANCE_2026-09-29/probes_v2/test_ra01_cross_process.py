"""RA-01: IA288-01 cross-process linearization of exchange mutations.

Every race below uses *separate OS processes* started behind a shared gate file,
with candidate source untouched. Failure is a genuine cross-process defect.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

from conftest import assert_linear, collect, run_worker, spawn_workers


def _specs(tmp_path, root, entries, gate_name="gate"):
    gate = tmp_path / gate_name
    specs = []
    for index, entry in enumerate(entries):
        spec = {"mode": entry.pop("mode"), "root": root, "gate": gate, "token": f"p{index}"}
        spec.update(entry)
        specs.append(spec)
    return specs


def test_ra01_four_process_distinct_publishers(tmp_path, exchange):
    specs = _specs(
        tmp_path,
        exchange,
        [{"mode": "publish", "marker": f"proc-distinct-{i}"} for i in range(4)],
    )
    results = collect(spawn_workers(specs), timeout=90)
    assert all(r.get("ok") for r in results), results
    successes = [r["receipt"] for r in results if r.get("ok")]
    rows = assert_linear(exchange)
    published = [r for r in rows if r["event"] == "request_published"]
    assert len(published) == 4, f"expected 4 durable dispatches, saw {len(published)}"
    assert len({r["request_id"] for r in published}) == 4, "duplicate request identity"
    sequences = [r["seq"] for r in published]
    assert sequences == sorted(sequences), f"ordinal order broken: {sequences}"
    for ordinal, row in enumerate(published, 1):
        payload = json.loads((exchange / "requests" / f"{row['request_id']}.json").read_bytes())
        assert payload["sequence"] == ordinal, "payload sequence does not match ledger ordinal"
        receipt = next(r for r in successes if r["request_id"] == row["request_id"])
        assert receipt["sequence"] == row["seq"], "receipt sequence != ledger seq"


def test_ra01_two_process_explicit_identity_single_dispatch(tmp_path, exchange):
    """v2 (corrects v1 probe ambiguity): the caller-declared request identity is
    the duplicate-suppression contract. Two processes publish the SAME explicit
    request_id concurrently: exactly one durable dispatch, no identity fork."""
    from aios_exchange.bridge import ExchangeBridge

    probe = ExchangeBridge(exchange)
    request_id = probe.requests.request_id_for(
        "model_directive", {"reviewer_marker": "same-explicit-request"}, 1
    )
    specs = _specs(
        tmp_path,
        exchange,
        [
            {
                "mode": "publish-explicit",
                "marker": "same-explicit-request",
                "request_id": request_id,
            }
            for _ in range(2)
        ],
    )
    results = collect(spawn_workers(specs), timeout=90)
    assert all(r.get("ok") for r in results), results
    rows = assert_linear(exchange)
    published = [r for r in rows if r["event"] == "request_published"]
    assert len(published) == 1, f"duplicate semantic dispatch: {len(published)} request_published"
    assert published[0]["request_id"] == request_id
    ids = {r["receipt"]["request_id"] for r in results}
    assert ids == {request_id}, f"deterministic identity forked: {ids}"
    replays = sorted(r["receipt"].get("idempotent_replay") for r in results)
    assert replays in ([False, True], [False]), f"replay pattern {replays}"
    first = next(r for r in results if r["receipt"].get("idempotent_replay") is False)
    second = next(r for r in results if r["receipt"].get("idempotent_replay") is True)
    assert second["receipt"]["request_sha256"] == first["receipt"]["request_sha256"]


def test_ra01_two_process_implicit_same_body_semantics(tmp_path, exchange):
    """v2 informational probe (records boundary semantics, not a blocker test).

    Without a caller-declared identity the publisher's identity rule is
    (ledger sequence, body digest); each implicit submission is therefore a new
    decision request. The binding invariants are: unique sequences, a valid
    chain, no duplicated event for one identity, and exactly-once dispatch at
    the *approved runner* boundary (covered by the handler race probe).
    """
    specs = _specs(
        tmp_path,
        exchange,
        [{"mode": "publish", "marker": "implicit-same-body"} for _ in range(2)],
    )
    results = collect(spawn_workers(specs), timeout=90)
    assert all(r.get("ok") for r in results), results
    rows = assert_linear(exchange)
    published = [r for r in rows if r["event"] == "request_published"]
    assert len(published) == 2, published
    assert len({r["request_id"] for r in published}) == 2, "identity collision"
    assert [r["seq"] for r in published] == [1, 2], "allocation fork"
    bodies = {
        (exchange / "requests" / f"{r['request_id']}.json").read_bytes() for r in published
    }
    assert len(bodies) == 2, "implicit submissions collided onto one artifact"
    recorded = {r["request_id"]: r["request_sha256"] for r in published}
    for request_id, digest in recorded.items():
        raw = (exchange / "requests" / f"{request_id}.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest


def test_ra01_two_process_response_publish_race(tmp_path, exchange):
    seed, _ = run_worker("publish", root=exchange, marker="race-seed")
    assert seed["ok"], seed
    request_id = seed["receipt"]["request_id"]
    specs = _specs(
        tmp_path,
        exchange,
        [
            {"mode": "publish-response", "request_id": request_id, "marker": "resp-A"},
            {"mode": "publish-response", "request_id": request_id, "marker": "resp-B"},
        ],
    )
    results = collect(spawn_workers(specs), timeout=90)
    rows = assert_linear(exchange)
    published = [r for r in rows if r["event"] == "response_published"]
    assert len(published) == 1, f"more than one durable response_published: {len(published)}"
    successes = [r for r in results if r.get("ok")]
    closed = [r for r in results if not r.get("ok")]
    assert len(successes) >= 1, results
    assert len(successes) + len(closed) == 2
    assert len(successes) == 1, f"both publishers of different bytes succeeded: {successes}"
    raw = (exchange / "responses" / f"{request_id}.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == published[0]["response_sha256"]


def test_ra01_two_process_consume_race(tmp_path, exchange):
    seed, _ = run_worker("publish", root=exchange, marker="consume-seed")
    request_id = seed["receipt"]["request_id"]
    response, _ = run_worker(
        "publish-response", root=exchange, request_id=request_id, marker="consume-resp"
    )
    assert response["ok"], response
    specs = _specs(
        tmp_path,
        exchange,
        [{"mode": "consume", "request_id": request_id} for _ in range(2)],
    )
    results = collect(spawn_workers(specs), timeout=90)
    assert all(r.get("ok") for r in results), results
    rows = assert_linear(exchange)
    consumed = [r for r in rows if r["event"] == "response_consumed"]
    assert len(consumed) == 1, f"duplicate response_consumed: {len(consumed)}"


def test_ra01_publish_and_consume_race_across_processes(tmp_path, exchange):
    first, _ = run_worker("publish", root=exchange, marker="race-first")
    request_id = first["receipt"]["request_id"]
    response, _ = run_worker(
        "publish-response", root=exchange, request_id=request_id, marker="race-first-resp"
    )
    assert response["ok"], response
    specs = _specs(
        tmp_path,
        exchange,
        [
            {"mode": "consume", "request_id": request_id},
            {"mode": "publish", "marker": "race-second"},
        ],
    )
    results = collect(spawn_workers(specs), timeout=90)
    assert all(r.get("ok") for r in results), results
    rows = assert_linear(exchange)
    assert len([r for r in rows if r["event"] == "response_consumed"]) == 1
    assert len([r for r in rows if r["event"] == "request_published"]) == 2


def test_ra01_handler_race_two_processes_same_snapshot(tmp_path, exchange):
    """Two independent handler processes on the same snapshot: one dispatch."""
    import threading
    import time

    specs = _specs(
        tmp_path,
        exchange,
        [
            {"mode": "handler", "marker": "shared-snapshot", "timeout": 40},
            {"mode": "handler", "marker": "shared-snapshot", "timeout": 40},
        ],
    )
    procs = spawn_workers(specs)

    # external test-only responder: publishes exactly one response per dispatch
    from aios_exchange.bridge import ExchangeBridge

    bridge = ExchangeBridge(exchange)
    stop = threading.Event()
    published: list[str] = []

    def responder():
        while not stop.is_set():
            state = bridge.recovery_state()
            for rid in state["open_dispatched"]:
                if rid not in published:
                    bridge.responses.publish_object(
                        request_id=rid,
                        response={
                            "response_version": 1,
                            "request_id": rid,
                            "request_sha256": bridge.request_sha256(rid),
                            "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
                            "directive": {
                                "capability_calls": [],
                                "response": "reviewer-runner-race-response",
                                "silence": False,
                            },
                        },
                    )
                    published.append(rid)
            time.sleep(0.01)

    worker = threading.Thread(target=responder, daemon=True)
    worker.start()
    try:
        results = collect(procs, timeout=90)
    finally:
        stop.set()
        worker.join(timeout=10)

    assert all(r.get("ok") for r in results), results
    responses = [r["response"] for r in results]
    assert len(set(responses)) == 1, f"handlers returned different directives: {responses}"
    rows = assert_linear(exchange)
    assert len([r for r in rows if r["event"] == "request_published"]) == 1, "duplicate dispatch"
    assert len([r for r in rows if r["event"] == "response_published"]) == 1
    assert len([r for r in rows if r["event"] == "response_consumed"]) == 1, "duplicate consume"
    paths = {h["path"] for r in results for h in r["handoffs"]}
    assert paths <= {"published_new_request", "resumed_dispatched_request"}, paths
