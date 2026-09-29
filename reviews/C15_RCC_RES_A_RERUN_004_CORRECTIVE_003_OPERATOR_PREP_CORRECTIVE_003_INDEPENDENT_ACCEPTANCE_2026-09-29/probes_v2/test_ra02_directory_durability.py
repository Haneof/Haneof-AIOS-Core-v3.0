"""RA-02: IA288-02 directory durability injection (files still fsync normally).

Every injection happens in a fresh process; the probe proves the fault was
directory-specific by checking the injector counters (file fsync succeeded) and
that no success receipt / durable dispatch record exists.
"""

from __future__ import annotations

import pathlib

from conftest import run_worker


def _ledger_rows(root: pathlib.Path):
    from aios_exchange.ledger import ExchangeLedger

    path = root / "ledger.jsonl"
    if not path.exists():
        return []
    return ExchangeLedger(path).read_records()


def _assert_no_dispatch(root: pathlib.Path):
    rows = _ledger_rows(root)
    assert [r for r in rows if r["event"] == "request_published"] == [], "dispatch recorded"
    assert [r for r in rows if r["event"] == "response_published"] == []


def test_ra02_request_dir_fsync_failure_is_not_dispatch(tmp_path, exchange):
    payload, proc = run_worker(
        "fault-publish",
        root=exchange,
        fault_kind="dir_fsync",
        fault_path=exchange / "requests",
        marker="ra02-req-fsync",
        side="request",
    )
    assert payload is not None, proc.stderr
    assert payload["first"]["status"] == "closed", payload["first"]
    assert payload["fault"]["counters"]["dir_fsync_failed"] == 1, payload["fault"]
    assert payload["fault"]["counters"]["file_fsync_ok"] >= 1, "file fsync did not run normally"
    _assert_no_dispatch(exchange)


def test_ra02_request_dir_open_failure_is_not_dispatch(tmp_path, exchange):
    payload, proc = run_worker(
        "fault-publish",
        root=exchange,
        fault_kind="dir_open",
        fault_path=exchange / "requests",
        marker="ra02-req-open",
        side="request",
    )
    assert payload is not None, proc.stderr
    assert payload["first"]["status"] == "closed", payload["first"]
    assert payload["fault"]["counters"]["dir_open_failed"] >= 1, payload["fault"]
    _assert_no_dispatch(exchange)


def test_ra02_response_dir_fsync_failure_is_not_published(tmp_path, exchange):
    seed, _ = run_worker("publish", root=exchange, marker="ra02-resp-seed")
    request_id = seed["receipt"]["request_id"]
    payload, proc = run_worker(
        "fault-publish",
        root=exchange,
        fault_kind="dir_fsync",
        fault_path=exchange / "responses",
        marker="ra02-resp-fsync",
        side="response",
        request_id=request_id,
    )
    assert payload is not None, proc.stderr
    assert payload["first"]["status"] == "closed", payload["first"]
    assert payload["fault"]["counters"]["dir_fsync_failed"] == 1, payload["fault"]
    assert payload["fault"]["counters"]["file_fsync_ok"] >= 1
    rows = _ledger_rows(exchange)
    assert [r for r in rows if r["event"] == "response_published"] == []


def test_ra02_response_dir_open_failure_is_not_published(tmp_path, exchange):
    seed, _ = run_worker("publish", root=exchange, marker="ra02-resp-seed2")
    request_id = seed["receipt"]["request_id"]
    payload, proc = run_worker(
        "fault-publish",
        root=exchange,
        fault_kind="dir_open",
        fault_path=exchange / "responses",
        marker="ra02-resp-open",
        side="response",
        request_id=request_id,
    )
    assert payload is not None, proc.stderr
    assert payload["first"]["status"] == "closed", payload["first"]
    assert payload["fault"]["counters"]["dir_open_failed"] >= 1
    rows = _ledger_rows(exchange)
    assert [r for r in rows if r["event"] == "response_published"] == []


def test_ra02_first_ledger_creation_dir_fsync_failure_is_not_durable(tmp_path, exchange):
    payload, proc = run_worker(
        "fault-publish",
        root=exchange,
        fault_kind="dir_fsync",
        fault_path=exchange,
        marker="ra02-ledger-fsync",
        side="request",
    )
    assert payload is not None, proc.stderr
    assert payload["first"]["status"] == "closed", payload["first"]
    assert payload["fault"]["counters"]["dir_fsync_failed"] >= 1, payload["fault"]
    ledger_file = exchange / "ledger.jsonl"
    assert ledger_file.exists(), "expected the visible-but-unproven ledger entry"
    assert _ledger_rows(exchange) == [], "unproven ledger creation claimed a record"
    _assert_no_dispatch(exchange)


def test_ra02_first_ledger_creation_dir_open_failure_is_not_durable(tmp_path, exchange):
    payload, proc = run_worker(
        "fault-publish",
        root=exchange,
        fault_kind="dir_open",
        fault_path=exchange,
        marker="ra02-ledger-open",
        side="request",
    )
    assert payload is not None, proc.stderr
    assert payload["first"]["status"] == "closed", payload["first"]
    assert payload["fault"]["counters"]["dir_open_failed"] >= 1
    _assert_no_dispatch(exchange)


def test_ra02_ledger_append_file_fsync_failure_is_not_durable(tmp_path, exchange):
    """Control: a *file* fsync failure must also fail closed."""
    payload, proc = run_worker(
        "fault-publish",
        root=exchange,
        fault_kind="dir_fsync",
        fault_path=exchange / "nonexistent-dir-control",
        marker="ra02-control",
        side="request",
    )
    assert payload is not None, proc.stderr
    # no fault injected on a real path: publication must succeed (sanity control)
    assert payload["first"]["status"] == "success", payload["first"]
