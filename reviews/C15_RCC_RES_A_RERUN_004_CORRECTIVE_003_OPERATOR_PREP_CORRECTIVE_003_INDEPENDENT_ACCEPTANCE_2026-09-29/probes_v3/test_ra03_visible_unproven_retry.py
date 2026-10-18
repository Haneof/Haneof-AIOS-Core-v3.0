"""RA-03: visible-but-unproven retry after directory durability failure.

The exact attack sequence required by the acceptance prompt: make bytes visible,
force required directory durability to fail, require the failure to be reported,
restore durability, retry, and prove that the retry re-validates and re-proves
durability instead of adopting the visible bytes as an already-durable
dispatch.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

from conftest import assert_linear, run_worker


def _rows(root: pathlib.Path):
    from aios_exchange.ledger import ExchangeLedger

    path = root / "ledger.jsonl"
    return ExchangeLedger(path).read_records() if path.exists() else []


def test_ra03_request_retry_after_unproven_dir_fsync(tmp_path, exchange):
    payload, proc = run_worker(
        "fault-retry",
        root=exchange,
        fault_kind="dir_fsync",
        fault_path=exchange / "requests",
        marker="ra03-retry-request",
        side="request",
    )
    assert payload is not None, proc.stderr
    assert payload["first"]["status"] == "closed", payload["first"]
    assert payload["retry"]["status"] == "success", payload["retry"]
    assert payload["fault"]["counters"]["dir_fsync_failed"] == 1
    rows = assert_linear(exchange)
    published = [r for r in rows if r["event"] == "request_published"]
    assert len(published) == 1, f"retry produced {len(published)} dispatches"
    record = published[0]
    raw = (exchange / "requests" / f"{record['request_id']}.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == record["request_sha256"], "bytes/digest drift"
    assert payload["retry"]["receipt"]["request_id"] == record["request_id"]


def test_ra03_request_retry_rejects_mutated_visible_bytes(tmp_path, exchange):
    payload, proc = run_worker(
        "fault-retry",
        root=exchange,
        fault_kind="dir_fsync",
        fault_path=exchange / "requests",
        marker="ra03-retry-mutated",
        side="request",
        mutate_visible_after_fault=True,
    )
    assert payload is not None, proc.stderr
    assert payload["first"]["status"] == "closed", payload["first"]
    assert payload["mutated"], "probe did not find a visible request file to mutate"
    assert payload["retry"]["status"] == "closed", (
        "mutated visible bytes were accepted as a dispatch: " f"{payload['retry']}"
    )
    rows = _rows(exchange)
    assert [r for r in rows if r["event"] == "request_published"] == [], "mutated bytes dispatched"


def test_ra03_response_retry_after_unproven_dir_fsync(tmp_path, exchange):
    seed, _ = run_worker("publish", root=exchange, marker="ra03-resp-seed")
    request_id = seed["receipt"]["request_id"]
    payload, proc = run_worker(
        "fault-retry",
        root=exchange,
        fault_kind="dir_fsync",
        fault_path=exchange / "responses",
        marker="ra03-response-retry",
        side="response",
        request_id=request_id,
    )
    assert payload is not None, proc.stderr
    assert payload["first"]["status"] == "closed", payload["first"]
    assert payload["retry"]["status"] == "success", payload["retry"]
    rows = assert_linear(exchange)
    published = [r for r in rows if r["event"] == "response_published"]
    assert len(published) == 1, f"retry produced {len(published)} response events"
    raw = (exchange / "responses" / f"{request_id}.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == published[0]["response_sha256"]


def test_ra03_response_retry_with_different_bytes_fails_closed(tmp_path, exchange):
    """After an unproven visible response, a different second submission must not
    silently become the durable response."""
    seed, _ = run_worker("publish", root=exchange, marker="ra03-resp-seed2")
    request_id = seed["receipt"]["request_id"]
    payload, proc = run_worker(
        "fault-retry",
        root=exchange,
        fault_kind="dir_fsync",
        fault_path=exchange / "responses",
        marker="ra03-response-original",
        side="response",
        request_id=request_id,
        second_marker="ra03-response-different",
    )
    assert payload is not None, proc.stderr
    assert payload["first"]["status"] == "closed", payload["first"]
    assert payload["retry"]["status"] == "closed", payload["retry"]
    rows = _rows(exchange)
    assert [r for r in rows if r["event"] == "response_published"] == [], "different bytes published"
    # the visible unproven bytes are still the first submission, undispached
    visible = (exchange / "responses" / f"{request_id}.json").read_bytes()
    assert b"ra03-response-original" in visible


def test_ra03_first_ledger_retry_single_entry(tmp_path, exchange):
    payload, proc = run_worker(
        "fault-retry",
        root=exchange,
        fault_kind="dir_fsync",
        fault_path=exchange,
        marker="ra03-ledger-retry",
        side="request",
    )
    assert payload is not None, proc.stderr
    assert payload["first"]["status"] == "closed", payload["first"]
    assert payload["retry"]["status"] == "success", payload["retry"]
    rows = assert_linear(exchange)
    assert len([r for r in rows if r["event"] == "request_published"]) == 1
    assert rows[0]["seq"] == 1
