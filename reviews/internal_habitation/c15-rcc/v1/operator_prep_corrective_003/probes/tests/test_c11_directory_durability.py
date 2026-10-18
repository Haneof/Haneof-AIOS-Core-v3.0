"""Frozen C11 / IA288-02: real directory-fsync/open syscall faults.

File fsyncs continue to use the real syscall; only the required containing
*directory* syscall is failed. A visible os.replace is never a dispatch receipt.
All roots are disposable and contain only synthetic data.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
import pathlib
import stat
import sys

import pytest


def _linux_directory() -> None:
    assert sys.platform.startswith("linux"), "qualified Linux directory durability is required"


def _fail_directory_fsync(monkeypatch, directory: pathlib.Path, *, after_exists: pathlib.Path | None = None):
    _linux_directory()
    real = os.fsync
    counts = {"directory_faults": 0, "file_fsyncs": 0}
    target = directory.resolve()

    def fsync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            observed = pathlib.Path(os.readlink(f"/proc/self/fd/{fd}")).resolve()
            if observed == target and (after_exists is None or after_exists.exists()):
                counts["directory_faults"] += 1
                raise OSError(errno.EIO, "synthetic required directory fsync failure")
        else:
            counts["file_fsyncs"] += 1
        return real(fd)

    monkeypatch.setattr(os, "fsync", fsync)
    return counts


def _observe_directory_fsync(monkeypatch, directory: pathlib.Path):
    real = os.fsync
    counts = {"directory_successes": 0, "file_fsyncs": 0}
    target = directory.resolve()

    def fsync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            if pathlib.Path(os.readlink(f"/proc/self/fd/{fd}")).resolve() == target:
                counts["directory_successes"] += 1
        else:
            counts["file_fsyncs"] += 1
        return real(fd)

    monkeypatch.setattr(os, "fsync", fsync)
    return counts


def _fail_directory_open(monkeypatch, directory: pathlib.Path, *, after_exists: pathlib.Path | None = None):
    _linux_directory()
    real = os.open
    counts = {"directory_open_faults": 0}
    target = directory.resolve()

    def open_spy(path, flags, *args, **kwargs):
        if (flags & os.O_DIRECTORY and pathlib.Path(path).resolve() == target
                and (after_exists is None or after_exists.exists())):
            counts["directory_open_faults"] += 1
            raise OSError(errno.EIO, "synthetic required directory open failure")
        return real(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", open_spy)
    return counts


def _request(bridge, marker="synthetic"):
    return bridge.publish_request(kind="model_directive", body={"synthetic_durability": marker})


def _response(request):
    return {"response_version": 1, "request_id": request["request_id"],
            "request_sha256": request["request_sha256"],
            "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
            "directive": {"response": "synthetic directory durability"}}


def test_c11_request_artifact_fsync_failure_is_not_dispatch(tmp_path, monkeypatch):
    from aios_exchange.bridge import ExchangeBridge

    bridge = ExchangeBridge(tmp_path / "exchange")
    with monkeypatch.context() as fault:
        calls = _fail_directory_fsync(fault, bridge.requests.requests_dir)
        with pytest.raises((OSError, RuntimeError)):
            _request(bridge)
    print("C11 request directory fsync fault:", calls)
    assert calls["directory_faults"] >= 1 and calls["file_fsyncs"] >= 1
    assert bridge.ledger.read_records() == []
    assert bridge.recovery_state()["not_submitted_allowed"] is True


def test_c11_response_artifact_fsync_failure_is_not_published(tmp_path, monkeypatch):
    from aios_exchange.bridge import ExchangeBridge

    bridge = ExchangeBridge(tmp_path / "exchange")
    request = _request(bridge)
    with monkeypatch.context() as fault:
        calls = _fail_directory_fsync(fault, bridge.responses.responses_dir)
        with pytest.raises((OSError, RuntimeError)):
            bridge.responses.publish_object(request_id=request["request_id"], response=_response(request))
    print("C11 response directory fsync fault:", calls)
    assert calls["directory_faults"] >= 1 and calls["file_fsyncs"] >= 1
    assert [r["event"] for r in bridge.ledger.read_records()] == ["request_published"]
    assert bridge.published_response_record(request["request_id"]) is None


def test_c11_first_ledger_entry_fsync_failure_and_retry(tmp_path, monkeypatch):
    from aios_exchange.ledger import ExchangeLedger, LedgerError

    ledger = ExchangeLedger(tmp_path / "exchange" / "ledger.jsonl")
    assert not ledger.path.exists()
    kwargs = {"request_id": "synthetic-ledger", "request_sha256": "a" * 64}
    with monkeypatch.context() as fault:
        calls = _fail_directory_fsync(fault, ledger.path.parent, after_exists=ledger.path)
        with pytest.raises((OSError, RuntimeError)):
            ledger.append("request_published", **kwargs)
    print("C11 ledger creation directory fsync fault:", calls)
    assert calls["directory_faults"] >= 1 and calls["file_fsyncs"] >= 1
    assert ledger.read_records() == [], "failure cannot leave a claimed semantic dispatch"
    receipt = ledger.append("request_published", **kwargs)
    assert receipt["seq"] == 1
    assert [r["request_id"] for r in ledger.read_records()] == ["synthetic-ledger"]
    with pytest.raises(LedgerError):
        ledger.append("request_published", **kwargs)  # direct duplicate is still rejected
    assert ledger.verify_chain()["ok"]


def test_c11_request_directory_open_failure_is_not_dispatch(tmp_path, monkeypatch):
    from aios_exchange.bridge import ExchangeBridge

    bridge = ExchangeBridge(tmp_path / "exchange")
    with monkeypatch.context() as fault:
        calls = _fail_directory_open(fault, bridge.requests.requests_dir)
        with pytest.raises((OSError, RuntimeError)):
            _request(bridge)
    assert calls["directory_open_faults"] >= 1
    assert bridge.ledger.read_records() == []
    assert bridge.recovery_state()["not_submitted_allowed"] is True


def test_c11_response_directory_open_failure_is_not_published(tmp_path, monkeypatch):
    from aios_exchange.bridge import ExchangeBridge

    bridge = ExchangeBridge(tmp_path / "exchange")
    request = _request(bridge)
    with monkeypatch.context() as fault:
        calls = _fail_directory_open(fault, bridge.responses.responses_dir)
        with pytest.raises((OSError, RuntimeError)):
            bridge.responses.publish_object(request_id=request["request_id"], response=_response(request))
    assert calls["directory_open_faults"] >= 1
    assert [r["event"] for r in bridge.ledger.read_records()] == ["request_published"]


def test_c11_ledger_creation_directory_open_failure_is_not_dispatch(tmp_path, monkeypatch):
    from aios_exchange.ledger import ExchangeLedger

    ledger = ExchangeLedger(tmp_path / "exchange" / "ledger.jsonl")
    with monkeypatch.context() as fault:
        calls = _fail_directory_open(fault, ledger.path.parent, after_exists=ledger.path)
        with pytest.raises((OSError, RuntimeError)):
            ledger.append("request_published", request_id="synthetic-ledger", request_sha256="a" * 64)
    assert calls["directory_open_faults"] >= 1
    assert ledger.read_records() == []


def test_c11_retry_after_unproven_request_artifact_sync(tmp_path, monkeypatch):
    from aios_exchange.bridge import ExchangeBridge

    bridge = ExchangeBridge(tmp_path / "exchange")
    marker = "synthetic-retry"
    rid = bridge.requests.request_id_for("model_directive", {"synthetic_durability": marker}, 1)
    with monkeypatch.context() as fault:
        calls = _fail_directory_fsync(fault, bridge.requests.requests_dir)
        with pytest.raises((OSError, RuntimeError)):
            _request(bridge, marker)
    assert calls["directory_faults"] >= 1 and calls["file_fsyncs"] >= 1
    assert bridge.requests.path_for(rid).is_file(), "replace was visible but not proven durable"
    assert bridge.recovery_state()["not_submitted_allowed"] is True
    assert bridge.ledger.read_records() == []
    fresh = ExchangeBridge(bridge.root)
    with monkeypatch.context() as probe:
        syncs = _observe_directory_fsync(probe, fresh.requests.requests_dir)
        receipt = _request(fresh, marker)
    print("C11 request retry fsyncs:", syncs, "receipt:", receipt)
    assert syncs["directory_successes"] >= 1 and syncs["file_fsyncs"] >= 1
    assert receipt["request_id"] == rid and receipt["idempotent_replay"] is False
    row, = fresh.ledger.read_records()
    assert row["event"] == "request_published" and row["request_id"] == rid
    assert hashlib.sha256(fresh.requests.path_for(rid).read_bytes()).hexdigest() == row["request_sha256"]
    assert fresh.recovery_state()["open_dispatched"] == [rid]


def test_c11_retry_after_unproven_response_artifact_sync(tmp_path, monkeypatch):
    from aios_exchange.bridge import ExchangeBridge

    bridge = ExchangeBridge(tmp_path / "exchange")
    request = _request(bridge)
    rid = request["request_id"]
    response = _response(request)
    with monkeypatch.context() as fault:
        calls = _fail_directory_fsync(fault, bridge.responses.responses_dir)
        with pytest.raises((OSError, RuntimeError)):
            bridge.responses.publish_object(request_id=rid, response=response)
    assert calls["directory_faults"] >= 1 and calls["file_fsyncs"] >= 1
    assert bridge.responses.path_for(rid).is_file(), "replace was visible but not proven durable"
    assert bridge.ledger.latest_event(rid, "response_published") is None
    fresh = ExchangeBridge(bridge.root)
    # A second still-failing attempt must not silently adopt the visible bytes.
    with monkeypatch.context() as fault:
        again = _fail_directory_fsync(fault, fresh.responses.responses_dir)
        with pytest.raises((OSError, RuntimeError)):
            fresh.responses.publish_object(request_id=rid, response=response)
    assert again["directory_faults"] >= 1
    assert fresh.ledger.latest_event(rid, "response_published") is None
    with monkeypatch.context() as probe:
        syncs = _observe_directory_fsync(probe, fresh.responses.responses_dir)
        receipt = fresh.responses.publish_object(request_id=rid, response=response)
    print("C11 response retry fsyncs:", syncs, "receipt:", receipt)
    assert syncs["directory_successes"] >= 1
    assert receipt["idempotent_replay"] is False
    assert [r["event"] for r in fresh.ledger.read_records()] == ["request_published", "response_published"]
    assert fresh.responses.publish_object(request_id=rid, response=response)["idempotent_replay"] is True
    assert [r["event"] for r in fresh.ledger.read_records()] == ["request_published", "response_published"]
    fresh.consume_response(rid)
    assert [r["event"] for r in fresh.ledger.read_records()] == ["request_published", "response_published", "response_consumed"]


def test_c11_mutated_unproven_request_file_is_not_adopted(tmp_path, monkeypatch):
    from aios_exchange.bridge import ExchangeBridge

    bridge = ExchangeBridge(tmp_path / "exchange")
    marker = "synthetic-mutation"
    rid = bridge.requests.request_id_for("model_directive", {"synthetic_durability": marker}, 1)
    with monkeypatch.context() as fault:
        calls = _fail_directory_fsync(fault, bridge.requests.requests_dir)
        with pytest.raises((OSError, RuntimeError)):
            _request(bridge, marker)
    assert calls["directory_faults"] >= 1
    path = bridge.requests.path_for(rid)
    path.write_bytes(path.read_bytes() + b" ")  # visible bytes modified before retry
    with pytest.raises((OSError, RuntimeError)):
        _request(ExchangeBridge(bridge.root), marker)
    assert bridge.ledger.read_records() == []
    assert bridge.recovery_state()["not_submitted_allowed"] is True


def test_c11_retry_after_unproven_first_ledger_creation(tmp_path, monkeypatch):
    from aios_exchange.bridge import ExchangeBridge

    bridge = ExchangeBridge(tmp_path / "exchange")
    marker = "synthetic-ledger-retry"
    rid = bridge.requests.request_id_for("model_directive", {"synthetic_durability": marker}, 1)
    with monkeypatch.context() as fault:
        calls = _fail_directory_fsync(fault, bridge.ledger.path.parent, after_exists=bridge.ledger.path)
        with pytest.raises((OSError, RuntimeError)):
            _request(bridge, marker)
    assert calls["directory_faults"] >= 1 and calls["file_fsyncs"] >= 1
    assert bridge.ledger.read_records() == []  # no claimed dispatch while init unproven
    fresh = ExchangeBridge(bridge.root)
    receipt = fresh.publish_request(kind="model_directive", body={"synthetic_durability": marker}, request_id=rid)
    assert receipt["request_id"] == rid and receipt["idempotent_replay"] is False
    assert len(fresh.ledger.read_records()) == 1
    assert fresh.ledger.verify_chain()["ok"]
