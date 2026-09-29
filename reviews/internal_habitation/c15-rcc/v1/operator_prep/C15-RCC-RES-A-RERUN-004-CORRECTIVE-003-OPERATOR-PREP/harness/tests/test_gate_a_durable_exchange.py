"""Gate A — durable exchange.

Binding checks (all mechanical, no C15 content, synthetic data only):

A01 request ID roundtrip
A02 request SHA-256 binding
A03 response SHA-256 binding
A04 atomic request publication
A05 atomic response publication
A06 temporary write + file fsync
A07 ``os.replace`` publication
A08 containing-directory fsync
A09 readers never observe a partial response
A10 monotonic ledger sequence
A11 hash-chained ledger / tamper detection
A12 crash before request publication -> not_submitted allowed
A13 crash after request publication -> not_submitted forbidden, durable recovery
A14 torn response write -> nothing observable, fail closed, safe retry
A15 response published before consume -> recovered without re-deciding
A16 request-id mismatch -> fail closed
A17 digest mismatch -> fail closed
A18 missing ledger publication record -> fail closed
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import threading
import time

import pytest

from aios_exchange import atomic
from aios_exchange.bridge import (
    CLASSIFICATION_COMPLETE,
    CLASSIFICATION_DISPATCHED_AWAITING_RESPONSE,
    CLASSIFICATION_NOT_SUBMITTED,
    CLASSIFICATION_RESPONSE_DURABLE_UNCONSUMED,
    ExchangeBridge,
    ExchangeContractError,
)
from aios_exchange.canonical import canonical_json_bytes, sha256_hex
from aios_exchange.responses import ResponsePublishError

CRASH_WORKER = pathlib.Path(__file__).resolve().parent / "_crash_worker.py"


# ---------------------------------------------------------------------------
# helpers (synthetic only)
# ---------------------------------------------------------------------------
def synthetic_body(marker: str) -> dict:
    return {
        "synthetic_probe": marker,
        "synthetic_subject": "synthetic_subject_operator_prep",
        "synthetic_round": 0,
    }


def envelope(request_payload: dict, text: str = "SYNTHETIC_OPERATOR_PREP_RESPONSE") -> dict:
    return {
        "response_version": 1,
        "request_id": request_payload["request_id"],
        "request_sha256": request_payload["request_sha256"],
        "authored_by": "EXTERNAL_CURRENT_RESIDENT_SESSION",
        "directive": {
            "capability_calls": [],
            "response": text,
            "silence": False,
        },
    }


def publish_request_with_digest(bridge: ExchangeBridge, marker: str) -> tuple[str, str, dict]:
    published = bridge.publish_request(kind="model_directive", body=synthetic_body(marker))
    payload = bridge.request_payload(published["request_id"])
    payload["request_sha256"] = published["request_sha256"]
    return published["request_id"], published["request_sha256"], payload


def publish_full_pair(bridge: ExchangeBridge, marker: str, text: str = "SYNTHETIC_OPERATOR_PREP_RESPONSE") -> dict:
    request_id, request_digest, payload = publish_request_with_digest(bridge, marker)
    response = bridge.responses.publish_bytes(
        request_id=request_id,
        response_bytes=canonical_json_bytes(envelope(payload, text)) + b"\n",
    )
    return {
        "request_id": request_id,
        "request_sha256": request_digest,
        "response_sha256": response["response_sha256"],
        "payload": payload,
    }


@pytest.fixture()
def bridge(tmp_path: pathlib.Path) -> ExchangeBridge:
    return ExchangeBridge(tmp_path / "exchange")


# ---------------------------------------------------------------------------
# A01 - A05
# ---------------------------------------------------------------------------
def test_a01_request_id_roundtrip(bridge: ExchangeBridge) -> None:
    published = bridge.publish_request(kind="model_directive", body=synthetic_body("a01"))
    assert published["request_id"].startswith("req-0001-model_directive-")
    payload = bridge.request_payload(published["request_id"])
    assert payload["request_id"] == published["request_id"]
    assert payload["sequence"] == 1
    assert payload["response_mode"] == "EXTERNAL_CURRENT_RESIDENT_SESSION"
    assert payload["body"] == synthetic_body("a01")


def test_a02_request_sha256_binding(bridge: ExchangeBridge) -> None:
    request_id, digest, _payload = publish_request_with_digest(bridge, "a02")
    record = bridge.ledger.latest_event(request_id, "request_published")
    on_disk = pathlib.Path(bridge.requests.path_for(request_id)).read_bytes()
    assert record["request_sha256"] == digest == sha256_hex(on_disk)
    assert bridge.request_sha256(request_id) == digest


def test_a03_response_sha256_binding(bridge: ExchangeBridge) -> None:
    pair = publish_full_pair(bridge, "a03")
    record = bridge.ledger.latest_event(pair["request_id"], "response_published")
    on_disk = pathlib.Path(bridge.responses.path_for(pair["request_id"])).read_bytes()
    assert record["response_sha256"] == pair["response_sha256"] == sha256_hex(on_disk)
    assert record["request_sha256"] == pair["request_sha256"]
    consumed = bridge.consume_response(pair["request_id"])
    assert sha256_hex(consumed) == pair["response_sha256"]


def test_a04_atomic_request_publication(bridge: ExchangeBridge) -> None:
    atomic.reset_counters()
    published = bridge.publish_request(kind="model_directive", body=synthetic_body("a04"))
    assert atomic.COUNTERS["temp_writes"] >= 1
    assert atomic.COUNTERS["file_fsync"] >= 1
    assert atomic.COUNTERS["replace"] == 1
    assert atomic.COUNTERS["dir_fsync"] >= 1
    leftovers = [p.name for p in bridge.requests.requests_dir.glob(".*tmp*")]
    assert leftovers == []
    payload = json.loads(pathlib.Path(published["path"]).read_text())
    assert payload["request_id"] == published["request_id"]


def test_a05_atomic_response_publication(bridge: ExchangeBridge) -> None:
    request_id, _digest, payload = publish_request_with_digest(bridge, "a05")
    atomic.reset_counters()
    result = bridge.responses.publish_bytes(
        request_id=request_id,
        response_bytes=canonical_json_bytes(envelope(payload)) + b"\n",
    )
    assert atomic.COUNTERS["temp_writes"] >= 1
    assert atomic.COUNTERS["replace"] == 1
    assert atomic.COUNTERS["dir_fsync"] >= 1
    assert [p.name for p in bridge.responses.responses_dir.glob(".*tmp*")] == []
    assert sha256_hex(pathlib.Path(result["path"]).read_bytes()) == result["response_sha256"]


# ---------------------------------------------------------------------------
# A06 - A08 (real syscall spies)
# ---------------------------------------------------------------------------
def test_a06_temp_write_and_file_fsync(bridge: ExchangeBridge, monkeypatch: pytest.MonkeyPatch) -> None:
    observed: list[int] = []
    real_fsync = os.fsync

    def spy(fd: int) -> None:
        observed.append(fd)
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", spy)
    bridge.publish_request(kind="model_directive", body=synthetic_body("a06"))
    assert len(observed) >= 2, "expected fsync of the temp file and of the directory"


def test_a07_os_replace_used(bridge: ExchangeBridge, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []
    real_replace = os.replace

    def spy(src, dst):  # type: ignore[no-untyped-def]
        calls.append((str(src), str(dst)))
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy)
    published = bridge.publish_request(kind="model_directive", body=synthetic_body("a07"))
    assert len(calls) == 1
    src, dst = calls[0]
    assert pathlib.Path(src).name.startswith(".")
    assert "tmp" in pathlib.Path(src).name
    assert pathlib.Path(src).parent == pathlib.Path(dst).parent
    assert dst == published["path"]


def test_a08_directory_fsync_supported(bridge: ExchangeBridge) -> None:
    receipt = atomic.atomic_write_json(bridge.root / "requests" / "tmp-probe.json", {"probe": True})
    assert receipt["fsync_directory"] is True
    assert atomic.COUNTERS["dir_fsync"] >= 1


# ---------------------------------------------------------------------------
# A09
# ---------------------------------------------------------------------------
def test_a09_reader_never_observes_partial_response(tmp_path: pathlib.Path) -> None:
    bridge = ExchangeBridge(tmp_path / "exchange")
    request_id, _digest, payload = publish_request_with_digest(bridge, "a09")
    final_payload = envelope(payload, text="T" * 400_000)
    data = canonical_json_bytes(final_payload) + b"\n"
    final_digest = sha256_hex(data)
    response_path = bridge.responses.path_for(request_id)

    observed: list[str] = []
    stop = threading.Event()

    def reader() -> None:
        while not stop.is_set():
            if response_path.exists():
                blob = response_path.read_bytes()
                observed.append(sha256_hex(blob))
                json.loads(blob.decode("utf-8"))  # a partial blob would raise here

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    try:
        bridge.responses.publish_bytes(request_id=request_id, response_bytes=data)
        time.sleep(0.05)
    finally:
        stop.set()
        thread.join(timeout=10)

    assert observed, "reader never observed the published response"
    assert set(observed) == {final_digest}, "a reader observed a torn/partial response"
    assert sha256_hex(response_path.read_bytes()) == final_digest


# ---------------------------------------------------------------------------
# A10 - A11
# ---------------------------------------------------------------------------
def test_a10_monotonic_ledger_sequence(bridge: ExchangeBridge) -> None:
    for index in range(3):
        pair = publish_full_pair(bridge, f"a10-{index}")
        bridge.consume_response(pair["request_id"])
    records = bridge.ledger.read_records()
    assert [record["seq"] for record in records] == list(range(1, 10))
    assert [record["event"] for record in records] == [
        "request_published", "response_published", "response_consumed"
    ] * 3
    assert bridge.ledger.verify_chain()["ok"] is True


def test_a11_hash_chain_tamper_detection(bridge: ExchangeBridge) -> None:
    pair = publish_full_pair(bridge, "a11")
    bridge.consume_response(pair["request_id"])
    ledger_path = bridge.ledger.path
    lines = ledger_path.read_bytes().splitlines(keepends=True)

    # (i) editing any record breaks the chain at that record.
    tampered = json.loads(lines[1].decode("utf-8"))
    tampered["response_sha256"] = "0" * 64
    lines[1] = canonical_json_bytes(tampered) + b"\n"
    ledger_path.write_bytes(b"".join(lines))
    report = ExchangeBridge(bridge.root).ledger.verify_chain()
    assert report["ok"] is False
    assert report["first_bad_seq"] == 2
    assert ExchangeBridge(bridge.root).integrity()["ok"] is False

    # (ii) deleting an interior record breaks the forward link.
    ledger_path.write_bytes(lines[0] + lines[2])
    report = ExchangeBridge(bridge.root).ledger.verify_chain()
    assert report["ok"] is False

    # (iii) truncating the tail cannot be seen by the chain alone (the remaining
    # prefix is still a valid chain); the durable-artifact cross-check catches it
    # because the response file survives its deleted record as an orphan.
    ledger_path.write_bytes(lines[0])
    fresh = ExchangeBridge(bridge.root)
    assert fresh.ledger.verify_chain()["ok"] is True
    integrity = fresh.integrity()
    assert integrity["ok"] is False
    assert any("orphan" in problem or "without a durable response_published" in problem for problem in integrity["problems"]), integrity["problems"]
    assert fresh.recovery_state(pair["request_id"])["classification"] == CLASSIFICATION_DISPATCHED_AWAITING_RESPONSE


# ---------------------------------------------------------------------------
# A12 - A13 (real SIGKILL crash)
# ---------------------------------------------------------------------------
def _run_crash_worker(tmp_path: pathlib.Path, point: str) -> tuple[subprocess.CompletedProcess, pathlib.Path, pathlib.Path]:
    exchange = tmp_path / f"exchange-{point}"
    exchange.mkdir(parents=True, exist_ok=True)
    out = tmp_path / f"request-id-{point}.txt"
    completed = subprocess.run(
        [sys.executable, str(CRASH_WORKER), "--exchange", str(exchange), "--point", point, "--out", str(out)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return completed, exchange, out


def test_a12_crash_before_request_publication(tmp_path: pathlib.Path) -> None:
    completed, exchange, _out = _run_crash_worker(tmp_path, "before")
    assert completed.returncode == -9, completed.stderr
    bridge = ExchangeBridge(exchange)
    assert bridge.ledger.read_records() == []
    state = bridge.recovery_state()
    assert state["not_submitted_allowed"] is True
    assert state["open_dispatched"] == [] and state["durable_unconsumed"] == []
    assert not list((exchange / "requests").glob("req-*.json"))

    # the not-submitted path is legitimate here: a fresh decision may be published
    published = bridge.publish_request(kind="model_directive", body=synthetic_body("a12-retry"))
    assert published["sequence"] == 1


def test_a13_crash_after_request_publication(tmp_path: pathlib.Path) -> None:
    completed, exchange, out = _run_crash_worker(tmp_path, "after_request")
    assert completed.returncode == -9, completed.stderr
    request_id = out.read_text().strip()
    bridge = ExchangeBridge(exchange)
    state = bridge.recovery_state(request_id)
    assert state["classification"] == CLASSIFICATION_DISPATCHED_AWAITING_RESPONSE
    assert state["not_submitted_allowed"] is False
    assert state["requests"][0]["semantic_dispatch_occurred"] is True
    assert state["open_dispatched"] == [request_id]

    # durable recovery: the outstanding request is completed, never re-decided
    payload = bridge.request_payload(request_id)
    payload["request_sha256"] = bridge.request_sha256(request_id)
    bridge.responses.publish_bytes(
        request_id=request_id,
        response_bytes=canonical_json_bytes(envelope(payload, "SYNTHETIC_CRASH_RECOVERY")) + b"\n",
    )
    consumed = bridge.consume_response(request_id)
    assert b"SYNTHETIC_CRASH_RECOVERY" in consumed
    assert bridge.recovery_state(request_id)["classification"] == CLASSIFICATION_COMPLETE
    request_records = [
        record for record in bridge.ledger.read_records() if record["event"] == "request_published"
    ]
    assert len(request_records) == 1, "recovery must not create a second decision request"


# ---------------------------------------------------------------------------
# A14
# ---------------------------------------------------------------------------
def test_a14_torn_response_write_fails_closed(bridge: ExchangeBridge, monkeypatch: pytest.MonkeyPatch) -> None:
    request_id, _digest, payload = publish_request_with_digest(bridge, "a14")
    data = canonical_json_bytes(envelope(payload, "SYNTHETIC_TORN_WRITE")) + b"\n"
    response_path = bridge.responses.path_for(request_id)

    def exploding_replace(src, dst):  # type: ignore[no-untyped-def]
        raise OSError("simulated crash between temp write and rename")

    monkeypatch.setattr(os, "replace", exploding_replace)
    with pytest.raises(OSError):
        bridge.responses.publish_bytes(request_id=request_id, response_bytes=data)
    monkeypatch.undo()

    assert not response_path.exists(), "a torn write must not be observable"
    assert [p.name for p in bridge.responses.responses_dir.glob(".*tmp*")] == []
    with pytest.raises(ExchangeContractError):
        bridge.consume_response(request_id)

    # a partial blob under the published name is never consumed
    response_path.write_bytes(data[: len(data) // 2])
    with pytest.raises(ExchangeContractError):
        bridge.consume_response(request_id)

    # safe retry produces the exact bytes once
    response_path.unlink()
    result = bridge.responses.publish_bytes(request_id=request_id, response_bytes=data)
    assert sha256_hex(response_path.read_bytes()) == result["response_sha256"]
    assert bridge.consume_response(request_id) == data


# ---------------------------------------------------------------------------
# A15
# ---------------------------------------------------------------------------
def test_a15_response_published_before_consume_is_recovered(tmp_path: pathlib.Path) -> None:
    completed, exchange, out = _run_crash_worker(tmp_path, "after_response")
    assert completed.returncode == -9, completed.stderr
    request_id = out.read_text().strip()
    bridge = ExchangeBridge(exchange)
    state = bridge.recovery_state(request_id)
    assert state["classification"] == CLASSIFICATION_RESPONSE_DURABLE_UNCONSUMED
    assert state["durable_unconsumed"] == [request_id]
    assert state["not_submitted_allowed"] is False

    from aios_exchange.runner import ExternalSessionConfig, ExternalSessionModelHandler
    from aios_core.runtime.cognitive_runtime import RuntimeSnapshot

    handler = ExternalSessionModelHandler(
        ExternalSessionConfig(exchange_root=exchange, response_timeout_s=30)
    )
    snapshot = RuntimeSnapshot(
        user_input="synthetic recovery probe",
        wake_reason="synthetic",
        cockpit={},
        capability_catalog=(),
        capability_history=(),
        round_index=0,
        remaining_tool_rounds=0,
    )
    directive = handler(snapshot)
    assert directive.response == "SYNTHETIC_OPERATOR_PREP_CRASH_WORKER_RESPONSE"
    assert handler.handoffs[0]["path"] == "recovered_durable_response"
    request_records = [
        record for record in bridge.ledger.read_records() if record["event"] == "request_published"
    ]
    assert len(request_records) == 1, "recovery must not publish a second request"
    assert bridge.recovery_state(request_id)["classification"] == CLASSIFICATION_COMPLETE


# ---------------------------------------------------------------------------
# A16 - A18
# ---------------------------------------------------------------------------
def test_a16_request_id_mismatch_fails_closed(bridge: ExchangeBridge) -> None:
    request_id, _digest, payload = publish_request_with_digest(bridge, "a16")
    wrong = dict(payload)
    wrong["request_id"] = "req-9999-model_directive-deadbeef"
    with pytest.raises(ResponsePublishError):
        bridge.responses.publish_bytes(
            request_id=request_id,
            response_bytes=canonical_json_bytes(envelope(wrong)) + b"\n",
        )
    assert bridge.published_response_record(request_id) is None
    with pytest.raises(ExchangeContractError):
        bridge.consume_response(request_id)


def test_a17_digest_mismatch_fails_closed(bridge: ExchangeBridge) -> None:
    pair = publish_full_pair(bridge, "a17")
    response_path = bridge.responses.path_for(pair["request_id"])
    original = response_path.read_bytes()
    response_path.write_bytes(original + b" ")
    with pytest.raises(ResponsePublishError):
        bridge.responses.published_bytes(pair["request_id"])
    with pytest.raises(ExchangeContractError):
        bridge.consume_response(pair["request_id"])

    # a request whose digest does not match the ledger is refuse-on-read
    request_path = bridge.requests.path_for(pair["request_id"])
    request_bytes = request_path.read_bytes()
    request_path.write_bytes(request_bytes + b" ")
    with pytest.raises(Exception):
        bridge.request_payload(pair["request_id"])
    request_path.write_bytes(request_bytes)
    response_path.write_bytes(original)
    assert bridge.consume_response(pair["request_id"]) == original


def test_a18_missing_ledger_publication_record_fails_closed(tmp_path: pathlib.Path) -> None:
    bridge = ExchangeBridge(tmp_path / "exchange")
    request_id, _digest, payload = publish_request_with_digest(bridge, "a18")

    # (i) a complete response file with no ledger record at all
    response_path = bridge.responses.path_for(request_id)
    response_path.write_bytes(canonical_json_bytes(envelope(payload, "SYNTHETIC_ORPHAN")) + b"\n")
    assert bridge.published_response_record(request_id) is None
    with pytest.raises(ExchangeContractError):
        bridge.consume_response(request_id)
    with pytest.raises(Exception):
        bridge.responses.published_bytes(request_id)
    assert bridge.integrity()["ok"] is False

    # (ii) publication record removed after the fact
    bridge.responses.publish_bytes(
        request_id=request_id,
        response_bytes=canonical_json_bytes(envelope(payload, "SYNTHETIC_ORPHAN")) + b"\n",
    )
    assert bridge.recovery_state(request_id)["classification"] == CLASSIFICATION_RESPONSE_DURABLE_UNCONSUMED
    ledger_path = bridge.ledger.path
    lines = ledger_path.read_bytes().splitlines(keepends=True)
    ledger_path.write_bytes(lines[0])
    tampered = ExchangeBridge(bridge.root)
    integrity = tampered.integrity()
    assert integrity["ok"] is False
    assert any("response" in problem for problem in integrity["problems"]), integrity["problems"]
    assert tampered.recovery_state(request_id)["classification"] == CLASSIFICATION_DISPATCHED_AWAITING_RESPONSE
    with pytest.raises(ExchangeContractError):
        tampered.consume_response(request_id)


def test_a19_not_submitted_classification_requires_absence_of_dispatch(bridge: ExchangeBridge) -> None:
    """The classification contract itself: dispatch evidence forbids not_submitted."""

    state_before = bridge.recovery_state()
    assert state_before["not_submitted_allowed"] is True
    assert state_before["classification"] == CLASSIFICATION_NOT_SUBMITTED

    published = bridge.publish_request(kind="model_directive", body=synthetic_body("a19"))
    state_after = bridge.recovery_state(published["request_id"])
    assert state_after["not_submitted_allowed"] is False
    assert state_after["classification"] == CLASSIFICATION_DISPATCHED_AWAITING_RESPONSE
    assert state_after["dispatch_boundary_event"] == "request_published"
