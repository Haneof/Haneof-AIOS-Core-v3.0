"""Operator-only end-to-end concurrency proof. Disposable synthetic state ONLY.

Two independent request publishers race on one exchange; distinct external
response publishers and consumers complete both requests. The same exchange
then drives one ordinary due synthetic SAFETY Wake through the frozen Core and
an external TEST-ONLY response. This is never a Resident or a fixture run.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import hashlib
import json
import pathlib
import threading
import time
from collections import Counter

from aios_core.contracts.enums import WakeSource
from aios_core.headless import HeadlessConfig, HeadlessCore
from aios_core.runtime.cognitive_runtime import RuntimeSnapshot
from aios_core.wake.service import WakeSignalRequest
from aios_exchange.bridge import ExchangeBridge
from aios_exchange.canonical import canonical_json_bytes
from aios_exchange.runner import ExternalSessionConfig, ExternalSessionModelHandler, run_due_work
from aios_exchange.schema import parse_model_directive, serialize_runtime_snapshot


def response_for(bridge: ExchangeBridge, rid: str, marker: str) -> dict:
    return {"response_version": 1, "request_id": rid,
            "request_sha256": bridge.request_sha256(rid),
            "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
            "directive": {"response": "SYNTHETIC EXTERNAL " + marker}}


def execute(state: pathlib.Path, output: pathlib.Path) -> dict:
    assert not state.exists(), "synthetic state root must start absent"
    state.mkdir(parents=True)
    output.mkdir(parents=True, exist_ok=True)
    exchange = state / "exchange"
    one, two = ExchangeBridge(exchange), ExchangeBridge(exchange)
    barrier = threading.Barrier(2)

    def publish(bridge: ExchangeBridge, tag: str) -> dict:
        original = bridge.requests.next_sequence

        def scheduled_prefix() -> int:
            seq = original()
            try:
                barrier.wait(timeout=1.5)
            except threading.BrokenBarrierError:
                pass  # shared-lock implementations proceed after bounded wait
            return seq

        bridge.requests.next_sequence = scheduled_prefix
        snapshot = RuntimeSnapshot(user_input=f"synthetic integration {tag}",
            wake_reason="synthetic", cockpit={}, capability_catalog=(),
            capability_history=(), round_index=0, remaining_tool_rounds=1)
        return bridge.publish_request(kind="model_directive", body=serialize_runtime_snapshot(snapshot))

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(publish, one, "one"), pool.submit(publish, two, "two")
        published = [a.result(timeout=20), b.result(timeout=20)]
    assert len({receipt["request_id"] for receipt in published}) == 2
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = (pool.submit(bridge.responses.publish_object,
            request_id=receipt["request_id"],
            response=response_for(bridge, receipt["request_id"], marker))
            for bridge, receipt, marker in ((one, published[0], "one"), (two, published[1], "two")))
        responses = [a.result(timeout=20), b.result(timeout=20)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(one.consume_response, published[0]["request_id"]), pool.submit(two.consume_response, published[1]["request_id"])
        consumed = [a.result(timeout=20), b.result(timeout=20)]
    assert all(parse_model_directive(json.loads(raw)).response.startswith("SYNTHETIC EXTERNAL") for raw in consumed)

    now = dt.datetime(2026, 9, 29, 12, tzinfo=dt.timezone.utc)
    world, index = state / "synthetic-world.sqlite", state / "synthetic-index.sqlite"

    def forbidden_model_call(snapshot):
        raise AssertionError("synthetic setup must not call any model")

    with HeadlessCore(config=HeadlessConfig(world_path=world, index_path=index,
            subject_id="synthetic-concurrency-integration"), model_handler=forbidden_model_call) as core:
        core.runtime.wake_bus.emit(WakeSignalRequest(wake_source=WakeSource.SAFETY,
            rule_id="synthetic-concurrency-due", observed_at=now, priority=100,
            dedupe_key="synthetic-concurrency-due"))

    stop = threading.Event()
    errors: list[str] = []
    responder_replies: list[str] = []

    def external_test_responder() -> None:
        try:
            bridge = ExchangeBridge(exchange)
            while not stop.wait(0.01):
                for rid in bridge.recovery_state()["open_dispatched"]:
                    if rid in {receipt["request_id"] for receipt in published}:
                        raise AssertionError("earlier synthetic request was dispatched twice")
                    bridge.responses.publish_object(request_id=rid,
                        response=response_for(bridge, rid, "due-work"))
                    responder_replies.append(rid)
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    worker = threading.Thread(target=external_test_responder, daemon=True)
    worker.start()
    try:
        due = run_due_work(world_path=world, index_path=index,
            subject_id="synthetic-concurrency-integration", exchange_root=exchange,
            now=now, max_wakes=1, include_periodic_review=False,
            response_timeout_s=10, poll_interval_s=0.01)
    finally:
        stop.set()
        worker.join(timeout=15)
    assert not worker.is_alive() and not errors, errors
    assert len(responder_replies) >= 1
    assert due["due_work_result"]["wakes"][0]["wake"]["state"] == "completed"
    assert len(due["handoffs"]) == 1

    # Separately race TWO normal runner model handlers with the SAME snapshot.
    # Their recovery/classification decision must be atomic with dispatch, but
    # must release the lock before awaiting this test-only external response.
    runner_exchange = state / "concurrent-handler-recovery"
    handlers = [ExternalSessionModelHandler(ExternalSessionConfig(runner_exchange,
        response_timeout_s=8, poll_interval_s=0.005)) for _ in range(2)]
    shared_snapshot = RuntimeSnapshot(user_input="synthetic shared runner boundary",
        wake_reason="synthetic", cockpit={}, capability_catalog=(),
        capability_history=(), round_index=0, remaining_tool_rounds=1)
    runner_stop = threading.Event()
    runner_errors = []

    def external_runner_responder() -> None:
        try:
            bridge = ExchangeBridge(runner_exchange)
            while not runner_stop.wait(0.005):
                for rid in bridge.recovery_state()["open_dispatched"]:
                    bridge.responses.publish_object(request_id=rid,
                        response=response_for(bridge, rid, "shared-runner"))
        except Exception as exc:
            runner_errors.append(f"{type(exc).__name__}: {exc}")

    runner_thread = threading.Thread(target=external_runner_responder, daemon=True)
    runner_thread.start()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = (pool.submit(handler, shared_snapshot) for handler in handlers)
            directives = [a.result(timeout=15), b.result(timeout=15)]
    finally:
        runner_stop.set()
        runner_thread.join(timeout=15)
    assert not runner_thread.is_alive() and not runner_errors, runner_errors
    assert all(d.response == "SYNTHETIC EXTERNAL shared-runner" for d in directives)
    runner_bridge = ExchangeBridge(runner_exchange)
    runner_rows = runner_bridge.ledger.read_records()
    assert [r["event"] for r in runner_rows] == [
        "request_published", "response_published", "response_consumed"]
    assert runner_bridge.integrity()["ok"] and runner_bridge.ledger.verify_chain()["ok"]
    (output / "concurrent_handler_ledger.jsonl").write_bytes(runner_bridge.ledger.path.read_bytes())

    bridge = ExchangeBridge(exchange)
    integrity = bridge.ledger.verify_chain()
    assert integrity["ok"] and bridge.integrity()["ok"]
    rows = bridge.ledger.read_records()
    assert [r["seq"] for r in rows] == list(range(1, len(rows)+1))
    assert len(rows) == 9
    assert Counter(r["event"] for r in rows) == {"request_published":3,
        "response_published":3, "response_consumed":3}
    assert max(Counter((r["request_id"], r["event"]) for r in rows).values()) == 1
    request_rows = [r for r in rows if r["event"] == "request_published"]
    for ordinal, row in enumerate(request_rows, 1):
        raw = bridge.requests.path_for(row["request_id"]).read_bytes()
        payload = json.loads(raw)
        assert payload["sequence"] == ordinal
        assert bridge.requests.request_id_for(payload["kind"], payload["body"], ordinal) == row["request_id"]
        assert hashlib.sha256(raw).hexdigest() == row["request_sha256"]
    for row in rows:
        if row["event"] == "response_published":
            assert hashlib.sha256(bridge.responses.path_for(row["request_id"]).read_bytes()).hexdigest() == row["response_sha256"]

    (output / "exchange_ledger.jsonl").write_bytes(bridge.ledger.path.read_bytes())
    (output / "due_work_result.json").write_text(json.dumps(due, indent=2, default=str) + "\n")
    (output / "concurrent_request_receipts.json").write_text(json.dumps(published, indent=2) + "\n")
    summary = {"status":"PASS", "synthetic_only":True,
        "publisher_objects":2, "concurrent_publication_successes":len(published),
        "response_publications":len(responses), "consumptions":len(consumed),
        "due_work_handoffs":len(due["handoffs"]), "synthetic_due_work_completed":True,
        "concurrent_runner_dispatches":sum(r["event"] == "request_published" for r in runner_rows),
        "concurrent_runner_handoffs":sum(len(handler.handoffs) for handler in handlers),
        "concurrent_runner_chain_ok":runner_bridge.ledger.verify_chain()["ok"],
        "ledger_chain_ok":integrity["ok"], "exchange_integrity_ok":bridge.integrity()["ok"],
        "ledger_record_count":len(rows), "request_ids":[r["request_id"] for r in request_rows],
        "request_payload_sequences":[json.loads(bridge.requests.path_for(r["request_id"]).read_bytes())["sequence"] for r in request_rows],
        "ledger_head_sha256":integrity["head_sha256"],
        "core_import":str(pathlib.Path(__import__('aios_core').__file__).resolve()),
        "raw_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file()}}
    (output / "integration_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-root", type=pathlib.Path, required=True)
    ap.add_argument("--evidence-dir", type=pathlib.Path, required=True)
    args = ap.parse_args()
    print(json.dumps(execute(args.state_root, args.evidence_dir), indent=2, sort_keys=True))
