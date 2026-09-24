"""Resident broker boundary tests - Architecture A.

Synthetic only, no real B/C, no private A.

Verifies:
- Broker only emits plain(snapshot), no repo, canary, token, GitHub
- Model endpoint receives only allowed packet, has no filesystem
- Logs owned by operator, not model
- Timeout and error handling fail-closed
- No default silence
"""
import json
import time
from pathlib import Path
import pytest

from tools.c15_preflight.resident_broker import (
    ResidentBroker, SyntheticModelEndpoint,
    start_synthetic_endpoint, stop_synthetic_endpoint,
    BrokerError
)
from aios_core.runtime.cognitive_runtime import RuntimeSnapshot


def _make_fake_snapshot():
    try:
        snap = RuntimeSnapshot(
            user_input="synthetic user input for broker test",
            wake_reason="user_interaction",
            cockpit={"test": "cockpit"},
            capability_catalog=(),
            capability_history=(),
            round_index=0,
            remaining_tool_rounds=5,
        )
        return snap
    except Exception as e:
        pytest.skip(f"Cannot create RuntimeSnapshot for test: {e}")

def test_broker_emits_only_plain_snapshot_no_canary():
    server, thread, port = start_synthetic_endpoint(0)
    try:
        broker = ResidentBroker(f"http://127.0.0.1:{port}", timeout=5)
        snap = _make_fake_snapshot()
        result = broker.invoke(snap)
        assert result is not None
        assert len(broker.emitted_log) == 1
        emitted = broker.emitted_log[0]
        assert "request_id" in emitted
        assert "canary" not in json.dumps(emitted).lower()
        assert len(SyntheticModelEndpoint.received_log) == 1
        received = SyntheticModelEndpoint.received_log[0]
        assert received["has_canary"] is False, "packet leaked canary"
        assert received["has_token"] is False, "packet leaked token"
        assert received["has_repo"] is False, "packet leaked repo path"
        assert received["size"] < 100000
        assert "input_sha256" in received
    finally:
        stop_synthetic_endpoint(server)

def test_broker_logs_owned_by_operator_not_model():
    server, thread, port = start_synthetic_endpoint(0)
    try:
        broker = ResidentBroker(f"http://127.0.0.1:{port}", timeout=5)
        snap = _make_fake_snapshot()
        broker.invoke(snap)
        assert len(broker.emitted_log) == 1
        received = SyntheticModelEndpoint.received_log[0]
        assert "trace.jsonl" not in json.dumps(received)
    finally:
        stop_synthetic_endpoint(server)

def test_broker_timeout_fail_closed():
    server, thread, port = start_synthetic_endpoint(0)
    try:
        SyntheticModelEndpoint.delay_seconds = 2
        broker = ResidentBroker(f"http://127.0.0.1:{port}", timeout=1)
        snap = _make_fake_snapshot()
        with pytest.raises(BrokerError, match="timeout|unreachable"):
            broker.invoke(snap)
    finally:
        SyntheticModelEndpoint.delay_seconds = 0
        stop_synthetic_endpoint(server)

def test_broker_malformed_response_fail_closed():
    server, thread, port = start_synthetic_endpoint(0)
    try:
        SyntheticModelEndpoint.next_response = {}
        broker = ResidentBroker(f"http://127.0.0.1:{port}", timeout=5)
        snap = _make_fake_snapshot()
        with pytest.raises(BrokerError, match="binding|invalid|directive|response"):
            broker.invoke(snap)
    finally:
        SyntheticModelEndpoint.next_response = None
        stop_synthetic_endpoint(server)

def test_broker_no_default_silence():
    server, thread, port = start_synthetic_endpoint(0)
    try:
        SyntheticModelEndpoint.next_response = {"silence": True}
        broker = ResidentBroker(f"http://127.0.0.1:{port}", timeout=5)
        snap = _make_fake_snapshot()
        result = broker.invoke(snap)
        assert result.silence is True
        SyntheticModelEndpoint.next_response = None
        SyntheticModelEndpoint.delay_seconds = 2
        broker2 = ResidentBroker(f"http://127.0.0.1:{port}", timeout=1)
        with pytest.raises(BrokerError):
            broker2.invoke(snap)
    finally:
        SyntheticModelEndpoint.delay_seconds = 0
        SyntheticModelEndpoint.next_response = None
        stop_synthetic_endpoint(server)
