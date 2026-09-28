"""Gate C — integrated two-round frozen Core run (mandatory).

Disposable synthetic World, synthetic subject, synthetic session, test-only
deterministic external session. No C15 fixture content of any kind.

Round 0: the frozen Core publishes a decision request (empty capability
history). The synthetic external session answers with one legal read-capability
call. The frozen Core executes it through its real capability registry.

Round 1: the frozen Core publishes the next decision request with a non-empty
capability history. The synthetic session answers terminally.

The test proves mechanically:

* ``round 0 capability execution -> round 1 non-empty capability history``;
* every published capability-history entry carries exactly the six legal
  ``CapabilityResult`` fields and none of the forbidden ones;
* request publication, response publication and consumption are durable,
  ordered, hash-chained and unique per decision;
* no exception (in particular no ``AttributeError``) occurs anywhere in the
  runner, the serializer or the frozen Core path.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from aios_exchange import runner
from aios_exchange.bridge import (
    CLASSIFICATION_COMPLETE,
    ExchangeBridge,
)
from aios_exchange.schema import CAPABILITY_RESULT_EXPECTED_FIELDS, CAPABILITY_RESULT_FORBIDDEN_FIELDS

from synthetic.deterministic_resident import (
    SYNTHETIC_PROBE_CAPABILITY,
    SYNTHETIC_TERMINAL_RESPONSE,
    BackgroundResponder,
)
from synthetic.gate_env import evidence_dir

SYNTHETIC_USER_INPUT = "SYNTHETIC operator-prep two-round liveness probe"
SYNTHETIC_SUBJECT = "synthetic_subject_operator_prep"
SYNTHETIC_SESSION = "synthetic-session-operator-prep"
OCCURRED_AT = "2026-09-27T12:00:00Z"


def test_gate_c_two_round_integration(tmp_path: pathlib.Path) -> None:
    world_path = tmp_path / "synthetic_world.sqlite"
    index_path = tmp_path / "synthetic_world.search.sqlite"
    exchange_root = tmp_path / "exchange"

    responder = BackgroundResponder(str(exchange_root)).start()
    try:
        result = runner.run_user_turn(
            world_path=world_path,
            index_path=index_path,
            exchange_root=exchange_root,
            subject_id=SYNTHETIC_SUBJECT,
            session_id=SYNTHETIC_SESSION,
            turn_index=1,
            user_input=SYNTHETIC_USER_INPUT,
            occurred_at=OCCURRED_AT,
            response_timeout_s=120,
            poll_interval_s=0.02,
        )
    finally:
        responder.stop()

    assert responder.errors == [], responder.errors

    # ---- Round 0 -> Round 1 proof ----------------------------------------
    runtime_result = result["turn_result"]["runtime"]
    assert runtime_result["response"] == SYNTHETIC_TERMINAL_RESPONSE
    assert runtime_result["model_rounds"] == 2, runtime_result
    assert runtime_result["termination_reason"] == "responded"
    history = runtime_result["capability_history"]
    assert len(history) >= 1, "round 0 produced no capability result"
    assert history[0]["name"] == SYNTHETIC_PROBE_CAPABILITY
    assert history[0]["ok"] is True
    assert history[0]["call_id"] == "synthetic-call-0001"

    # ---- handoffs: exactly two published decisions ------------------------
    handoffs = result["handoffs"]
    assert [handoff["path"] for handoff in handoffs] == [
        "published_new_request",
        "published_new_request",
    ]
    assert [handoff["response_mode"] for handoff in handoffs] == [
        "EXTERNAL_CURRENT_RESIDENT_SESSION",
        "EXTERNAL_CURRENT_RESIDENT_SESSION",
    ]
    assert len(responder.served) == 2, responder.served

    bridge = ExchangeBridge(exchange_root)
    request_ids = bridge.ledger.request_ids()
    assert len(request_ids) == 2, request_ids

    round0_payload = bridge.request_payload(request_ids[0])
    round1_payload = bridge.request_payload(request_ids[1])
    assert round0_payload["body"]["capability_history"] == []
    assert round0_payload["body"]["round_index"] == 0
    assert round1_payload["body"]["round_index"] == 1
    round1_history = round1_payload["body"]["capability_history"]
    assert len(round1_history) == 1, "round 1 request did not carry the round 0 result"

    # ---- exact frozen field surface in the published request --------------
    for entry in round1_history:
        assert set(entry) == set(CAPABILITY_RESULT_EXPECTED_FIELDS), sorted(entry)
        for forbidden in CAPABILITY_RESULT_FORBIDDEN_FIELDS:
            assert forbidden not in entry, forbidden
    assert round1_payload["body"]["capability_history_contract"]["allowed_fields"] == list(
        CAPABILITY_RESULT_EXPECTED_FIELDS
    )

    # ---- durable chronology ---------------------------------------------
    records = bridge.ledger.read_records()
    assert [record["event"] for record in records] == [
        "request_published",
        "response_published",
        "response_consumed",
        "request_published",
        "response_published",
        "response_consumed",
    ]
    assert [record["seq"] for record in records] == list(range(1, 7))
    assert bridge.ledger.verify_chain()["ok"] is True
    integrity = bridge.integrity()
    assert integrity["ok"] is True, integrity["problems"]
    for request_id in request_ids:
        assert bridge.recovery_state(request_id)["classification"] == CLASSIFICATION_COMPLETE

    # ---- world/index effects --------------------------------------------
    assert result["status_after"]["world_revision"] > 0
    assert result["status_after"]["index_watermark"] == result["status_after"]["world_revision"]
    assert result["status_after"]["writer_lease_held"] is True
    assert world_path.exists() and world_path.stat().st_size > 0

    # ---- raw evidence ----------------------------------------------------
    evidence = evidence_dir("gate_c")
    (evidence / "round_requests.json").write_text(
        json.dumps({"round0": round0_payload, "round1": round1_payload}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (evidence / "turn_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    (evidence / "exchange_ledger.jsonl").write_text(
        (exchange_root / "ledger.jsonl").read_text(encoding="utf-8"), encoding="utf-8"
    )


def test_gate_c_second_turn_reuses_durable_exchange(tmp_path: pathlib.Path) -> None:
    """A second, independent turn on the same World must re-open the exchange."""

    world_path = tmp_path / "synthetic_world.sqlite"
    exchange_root = tmp_path / "exchange"
    responder = BackgroundResponder(str(exchange_root)).start()
    try:
        first = runner.run_user_turn(
            world_path=world_path,
            exchange_root=exchange_root,
            subject_id=SYNTHETIC_SUBJECT,
            session_id=SYNTHETIC_SESSION,
            turn_index=1,
            user_input=SYNTHETIC_USER_INPUT,
            occurred_at=OCCURRED_AT,
            response_timeout_s=120,
            poll_interval_s=0.02,
        )
        second = runner.run_user_turn(
            world_path=world_path,
            exchange_root=exchange_root,
            subject_id=SYNTHETIC_SUBJECT,
            session_id=SYNTHETIC_SESSION,
            turn_index=2,
            user_input=SYNTHETIC_USER_INPUT + " (turn 2)",
            occurred_at="2026-09-27T12:05:00Z",
            response_timeout_s=120,
            poll_interval_s=0.02,
        )
    finally:
        responder.stop()

    assert responder.errors == [], responder.errors
    assert first["turn_result"]["runtime"]["response"] == SYNTHETIC_TERMINAL_RESPONSE
    assert second["turn_result"]["runtime"]["response"] == SYNTHETIC_TERMINAL_RESPONSE
    bridge = ExchangeBridge(exchange_root)
    assert len(bridge.ledger.request_ids()) == 4
    assert bridge.integrity()["ok"] is True, bridge.integrity()["problems"]
    assert bridge.ledger.verify_chain()["ok"] is True
