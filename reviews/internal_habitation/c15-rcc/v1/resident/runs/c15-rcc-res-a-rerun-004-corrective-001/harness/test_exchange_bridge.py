"""Mandatory synthetic plumbing tests for run-local Resident Exchange Bridge.

Tests purely mechanical plumbing:
- request_id roundtrip
- request SHA-256 binding
- response SHA-256 binding
- atomic publication
- partial read prevention
- ledger monotonic sequence
- ledger hash-chain tamper evidence
- fail-closed crash / torn-write behaviors
- strict dispatch boundary: no not_submitted after request_published

Contains NO C15 fixture content and NO semantic expected answers.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from exchange_bridge import (
    ExchangeBlockedError,
    ExchangeBridge,
    ExchangeLedger,
    LedgerIntegrityError,
    RequestIdMismatchError,
    UnpublishedRequestError,
)


@pytest.fixture
def bridge_env(tmp_path: Path):
    requests_dir = tmp_path / "decision_requests"
    responses_dir = tmp_path / "decision_responses"
    ledger_path = tmp_path / "exchange_ledger.jsonl"
    ledger = ExchangeLedger(ledger_path)
    bridge = ExchangeBridge(
        requests_dir=requests_dir,
        responses_dir=responses_dir,
        ledger=ledger,
    )
    return tmp_path, bridge, ledger


# 1. request_id 正确 roundtrip
def test_01_request_id_roundtrip(bridge_env):
    tmp_path, bridge, ledger = bridge_env
    req_id = "syn-req-001"
    req_data = {"request_id": req_id, "kind": "synthetic_turn", "payload": "ping"}

    req_path, req_sha, req_rec = bridge.publish_request(req_id, req_data)
    assert req_path.exists()
    assert req_rec.request_id == req_id

    resp_data = {"request_id": req_id, "status": "ok", "echo": "pong"}
    resp_path, resp_sha, resp_rec = bridge.publish_response(req_id, req_sha, resp_data)
    assert resp_path.exists()
    assert resp_rec.request_id == req_id

    consumed, cons_rec = bridge.consume_response(req_id, req_sha)
    assert consumed["request_id"] == req_id
    assert consumed["echo"] == "pong"
    assert cons_rec.event == "response_consumed"


# 2. request SHA 绑定
def test_02_request_sha_binding(bridge_env):
    tmp_path, bridge, ledger = bridge_env
    req_id = "syn-req-002"
    req_data = {"synthetic": "sha-bind-check"}
    _, req_sha, _ = bridge.publish_request(req_id, req_data)

    records = ledger.find_records_for_request(req_id)
    assert records[0].request_sha256 == req_sha

    # Publish with wrong request sha must be blocked
    resp_data = {"request_id": req_id, "reply": "dummy"}
    with pytest.raises(ExchangeBlockedError, match="Request SHA-256 mismatch"):
        bridge.publish_response(req_id, "0" * 64, resp_data)


# 3. response SHA 绑定
def test_03_response_sha_binding(bridge_env):
    tmp_path, bridge, ledger = bridge_env
    req_id = "syn-req-003"
    _, req_sha, _ = bridge.publish_request(req_id, {"msg": "hello"})

    resp_data = {"request_id": req_id, "reply": "world"}
    resp_path, resp_sha, resp_rec = bridge.publish_response(req_id, req_sha, resp_data)

    records = ledger.find_records_for_request(req_id)
    resp_pub_rec = next(r for r in records if r.event == "response_published")
    assert resp_pub_rec.response_sha256 == resp_sha

    consumed, _ = bridge.consume_response(req_id, req_sha)
    assert consumed["reply"] == "world"


# 4. atomic response publish
def test_04_atomic_response_publish(bridge_env):
    tmp_path, bridge, ledger = bridge_env
    req_id = "syn-req-004"
    _, req_sha, _ = bridge.publish_request(req_id, {"data": 42})

    resp_data = {"request_id": req_id, "data": 84}
    resp_path, _, _ = bridge.publish_response(req_id, req_sha, resp_data)

    # Response file exists and no temp files remain
    assert resp_path.exists()
    temp_files = list(bridge.responses_dir.glob("*.tmp.*"))
    assert len(temp_files) == 0


# 5. reader 看不到 partial response
def test_05_reader_cannot_observe_partial_response(bridge_env):
    tmp_path, bridge, ledger = bridge_env
    req_id = "syn-req-005"
    _, req_sha, _ = bridge.publish_request(req_id, {"check": "partial"})

    # Simulate incomplete temp write
    partial_temp = bridge.responses_dir / f"{req_id}.json.tmp.simulated"
    with open(partial_temp, "w") as f:
        f.write('{"request_id": "syn-req-005", "incomplete": ')

    # Official file does not exist, ledger has no response_published
    assert not bridge.response_file(req_id).exists()
    with pytest.raises(ExchangeBlockedError, match="no response_published"):
        bridge.consume_response(req_id, req_sha)


# 6. ledger sequence 单调
def test_06_ledger_sequence_monotonic(bridge_env):
    tmp_path, bridge, ledger = bridge_env
    for i in range(1, 4):
        req_id = f"syn-req-mono-{i}"
        _, req_sha, _ = bridge.publish_request(req_id, {"idx": i})
        bridge.publish_response(req_id, req_sha, {"request_id": req_id, "idx": i})
        bridge.consume_response(req_id, req_sha)

    records = ledger.verify()
    assert len(records) == 9  # 3 * 3 events
    for expected_seq, rec in enumerate(records, start=1):
        assert rec.sequence == expected_seq


# 7. ledger hash-chain / tamper evidence
def test_07_ledger_hash_chain_tamper_evidence(bridge_env):
    tmp_path, bridge, ledger = bridge_env
    req_id = "syn-req-tamper"
    _, req_sha, _ = bridge.publish_request(req_id, {"msg": "clean"})
    bridge.publish_response(req_id, req_sha, {"request_id": req_id, "clean": True})

    records_before = ledger.verify()
    assert len(records_before) == 2

    # Tamper with the ledger file content
    with open(ledger.ledger_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    data = json.loads(lines[0])
    data["event"] = "tampered_event"
    lines[0] = json.dumps(data) + "\n"
    with open(ledger.ledger_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    with pytest.raises(LedgerIntegrityError):
        ledger.verify()


# 8. crash before request publication -> 可合法判未提交
def test_08_crash_before_request_publication_allows_not_submitted(bridge_env):
    tmp_path, bridge, ledger = bridge_env
    req_id = "syn-req-crash-pre"
    # Crash happened before request_published reached the exchange ledger
    assert bridge.can_reconcile_not_submitted(req_id) is True


# 9. crash after request publication / before response -> 不允许判 not_submitted
def test_09_crash_after_request_publication_forbids_not_submitted(bridge_env):
    tmp_path, bridge, ledger = bridge_env
    req_id = "syn-req-crash-post-pub"
    bridge.publish_request(req_id, {"dispatched": True})

    # Binding blocker IA-A004-01: once published, can NEVER be reconciled as not_submitted!
    assert bridge.can_reconcile_not_submitted(req_id) is False


# 10. crash during response temp write -> fail closed
def test_10_crash_during_response_temp_write_fails_closed(bridge_env):
    tmp_path, bridge, ledger = bridge_env
    req_id = "syn-req-crash-temp-write"
    _, req_sha, _ = bridge.publish_request(req_id, {"msg": "pending"})

    # Crash during temp write
    torn_temp = bridge.responses_dir / f"{req_id}.json.tmp.torn"
    torn_temp.write_bytes(b'{"incomplete"')

    assert bridge.can_recover_published_response(req_id, req_sha) is False
    with pytest.raises(ExchangeBlockedError, match="no response_published"):
        bridge.consume_response(req_id, req_sha)


# 11. crash after response atomic publish / before consume -> response 可被 durable recovery
def test_11_crash_after_response_atomic_publish_before_consume_recoverable(bridge_env):
    tmp_path, bridge, ledger = bridge_env
    req_id = "syn-req-recoverable"
    _, req_sha, _ = bridge.publish_request(req_id, {"task": "compute"})
    bridge.publish_response(req_id, req_sha, {"request_id": req_id, "ans": 100})

    # Crash occurred after response_published, before consume
    assert bridge.can_recover_published_response(req_id, req_sha) is True
    # Can safely consume
    consumed, rec = bridge.consume_response(req_id, req_sha)
    assert consumed["ans"] == 100
    assert rec.event == "response_consumed"


# 12. crash after response_published ledger / before consume -> chronology 可证明
def test_12_crash_after_response_published_ledger_chronology_provable(bridge_env):
    tmp_path, bridge, ledger = bridge_env
    req_id = "syn-req-chrono"
    _, req_sha, req_rec = bridge.publish_request(req_id, {"step": 1})
    _, resp_sha, resp_rec = bridge.publish_response(req_id, req_sha, {"request_id": req_id, "step": 1})

    # Ledger chronologically proves request_published precedes response_published
    assert req_rec.sequence < resp_rec.sequence
    assert resp_rec.request_sha256 == req_rec.request_sha256
    assert resp_rec.prev_record_hash == req_rec.record_hash

    # And when consumed later:
    _, cons_rec = bridge.consume_response(req_id, req_sha)
    assert resp_rec.sequence < cons_rec.sequence
    assert cons_rec.prev_record_hash == resp_rec.record_hash


# 13. response request_id mismatch -> fail closed
def test_13_response_request_id_mismatch_fails_closed(bridge_env):
    tmp_path, bridge, ledger = bridge_env
    req_id = "syn-req-mismatch"
    _, req_sha, _ = bridge.publish_request(req_id, {"test": "echo"})

    # Attempting to publish response with wrong request_id
    bad_resp = {"request_id": "wrong-id", "test": "echo"}
    with pytest.raises(RequestIdMismatchError):
        bridge.publish_response(req_id, req_sha, bad_resp)


# 14. digest mismatch -> fail closed
def test_14_digest_mismatch_fails_closed(bridge_env):
    tmp_path, bridge, ledger = bridge_env
    req_id = "syn-req-digest-mismatch"
    _, req_sha, _ = bridge.publish_request(req_id, {"auth": "check"})
    resp_path, _, _ = bridge.publish_response(req_id, req_sha, {"request_id": req_id, "valid": True})

    # Tamper response file directly on disk after publication
    with open(resp_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"request_id": req_id, "valid": False}))

    with pytest.raises(ExchangeBlockedError, match="response file SHA .* != ledger response SHA"):
        bridge.consume_response(req_id, req_sha)
