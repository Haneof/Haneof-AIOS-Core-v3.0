"""RA-04: software-visible crash boundaries around durability primitives.

Each crash worker exits hard (os._exit(9)) at one precise boundary. A fresh
process then retries/reads. Invariants: no duplicate dispatch, no corrupt
ledger, no lost binding, legal convergence.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

from conftest import assert_linear, run_worker

CRASH_POINTS = [
    "after_temp_fsync_before_replace",
    "after_replace_before_dir_fsync",
    "after_artifact_before_ledger_append",
    "after_ledger_file_fsync_before_dir_fsync",
    "after_ledger_append_before_receipt",
]


def _rows(root: pathlib.Path):
    from aios_exchange.ledger import ExchangeLedger

    path = root / "ledger.jsonl"
    return ExchangeLedger(path).read_records() if path.exists() else []


def _visible(root: pathlib.Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def test_ra04_crash_then_retry_converges(tmp_path, exchange):
    for point in CRASH_POINTS:
        root = tmp_path / f"crash-{point}"
        payload, proc = run_worker(
            "crash-publish", root=root, marker=f"ra04-{point}", point=point, timeout=60
        )
        assert proc.returncode == 9, f"{point}: worker did not crash (rc={proc.returncode})"
        after_crash = _visible(root)
        rows = _rows(root)
        assert len([r for r in rows if r["event"] == "request_published"]) <= 1, point

        retry, retry_proc = run_worker("publish", root=root, marker="ignored-retry-body")
        assert retry is not None, retry_proc.stderr
        # A fresh publisher legitimately obtains the next ordinal; the invariant
        # is that the durable chain stays valid and every event is unique.
        rows = assert_linear(root)
        published = [r for r in rows if r["event"] == "request_published"]
        assert len(published) <= 2, f"{point}: suspicious duplicate dispatch {len(published)}"
        for row in published:
            raw = (root / "requests" / f"{row['request_id']}.json").read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row["request_sha256"], point
        events = [(r["request_id"], r["event"]) for r in rows]
        assert len(events) == len(set(events)), f"{point}: duplicate events {events}"
        assert after_crash is not None


def test_ra04_crash_points_leave_no_orphan_dispatch(tmp_path, exchange):
    """Crash points that happen before the ledger append must leave no dispatch."""
    for point in (
        "after_temp_fsync_before_replace",
        "after_replace_before_dir_fsync",
        "after_artifact_before_ledger_append",
        "after_ledger_file_fsync_before_dir_fsync",
    ):
        root = tmp_path / f"orphan-{point}"
        _, proc = run_worker("crash-publish", root=root, marker=point, point=point, timeout=60)
        assert proc.returncode == 9, point
        rows = _rows(root)
        assert [r for r in rows if r["event"] == "request_published"] == [], (
            f"{point}: a dispatch was recorded despite crashing before the append"
        )


def test_ra04_handler_crash_after_dispatch_resumes_without_second_dispatch(tmp_path, exchange):
    """The runner must resume a durable dispatch instead of re-deciding."""
    import threading
    import time

    payload, proc = run_worker(
        "crash-handler",
        root=exchange,
        marker="ra04-handler-snapshot",
        point="after_ledger_append_before_receipt",
        timeout=60,
    )
    assert proc.returncode == 9, f"handler worker did not crash (rc={proc.returncode})"
    rows = _rows(exchange)
    published = [r for r in rows if r["event"] == "request_published"]
    assert len(published) == 1, f"expected exactly one durable dispatch, saw {len(published)}"

    # resume: the same snapshot must resume, not re-dispatch
    from conftest import collect, spawn_workers

    gate = tmp_path / "resume-gate"
    specs = [
        {"mode": "handler", "root": exchange, "gate": gate, "token": "resume", "marker": "ra04-handler-snapshot", "timeout": 40}
    ]
    procs = spawn_workers(specs)

    from aios_exchange.bridge import ExchangeBridge

    bridge = ExchangeBridge(exchange)
    stop = threading.Event()

    def responder():
        while not stop.is_set():
            state = bridge.recovery_state()
            for rid in state["open_dispatched"]:
                bridge.responses.publish_object(
                    request_id=rid,
                    response={
                        "response_version": 1,
                        "request_id": rid,
                        "request_sha256": bridge.request_sha256(rid),
                        "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
                        "directive": {
                            "capability_calls": [],
                            "response": "ra04-resume-response",
                            "silence": False,
                        },
                    },
                )
            time.sleep(0.01)

    worker = threading.Thread(target=responder, daemon=True)
    worker.start()
    try:
        results = collect(procs, timeout=90)
    finally:
        stop.set()
        worker.join(timeout=10)

    assert all(r.get("ok") for r in results), results
    rows = assert_linear(exchange)
    assert len([r for r in rows if r["event"] == "request_published"]) == 1, "re-dispatch on resume"
    assert results[0]["handoffs"][0]["path"] == "resumed_dispatched_request", results[0]["handoffs"]
