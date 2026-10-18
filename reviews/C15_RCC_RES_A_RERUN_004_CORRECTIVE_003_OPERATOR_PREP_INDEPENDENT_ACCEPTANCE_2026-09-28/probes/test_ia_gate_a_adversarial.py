"""IA Gate A adversarial probes (reviewer-authored, frozen before execution).

Every test asserts the SAFE (fail-closed) behaviour required by the IA prompt.
A failing test == a candidate defect (RED). Predictions are recorded separately
in EXPECTED_OUTCOMES.json before first execution.
"""

from __future__ import annotations

import json
import os
import pathlib
import signal
import subprocess
import sys
import threading

import pytest

from ia_common import (
    HARNESS_ROOT,
    IAResponder,
    envelope,
    handler_for,
    rewrite_ledger_lines,
    serialize_runtime_snapshot,
    snapshot,
    snapshot_round1,
)
from aios_exchange.bridge import (
    CLASSIFICATION_COMPLETE,
    CLASSIFICATION_DISPATCHED_AWAITING_RESPONSE,
    CLASSIFICATION_NOT_SUBMITTED,
    ExchangeBridge,
)
from aios_exchange.canonical import canonical_json_bytes, sha256_hex
from aios_exchange.requests import RequestPublishError
from aios_exchange.responses import ResponsePublishError


def _publish(root: pathlib.Path, snap):
    bridge = ExchangeBridge(root)
    pub = bridge.publish_request(kind="model_directive", body=serialize_runtime_snapshot(snap))
    return bridge, pub["request_id"]


# 1 request ID mismatch ------------------------------------------------------
def test_ia_a01_request_id_mismatch(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    with pytest.raises(RequestPublishError):
        bridge.publish_request(kind="model_directive", body={"x": 1}, request_id="req-9999-model_directive-deadbeef")
    other = rid[:-8] + "00000000"
    with pytest.raises(ResponsePublishError):
        bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "t", env_request_id=other))


# 2 request SHA mismatch ------------------------------------------------------
def test_ia_a02_request_sha_mismatch(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    with pytest.raises(ResponsePublishError):
        bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "t", request_sha="0" * 64))


# 3 response SHA mismatch (file changed after publication) ------------------
def test_ia_a03_response_sha_mismatch(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "A"))
    bridge.responses.path_for(rid).write_bytes(envelope(bridge, rid, "B"))
    with pytest.raises(Exception):
        bridge.consume_response(rid)
    with pytest.raises(Exception):
        handler_for(tmp_path)(snapshot(0))


# 4 partial request -----------------------------------------------------------
def test_ia_a04_partial_request(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    p = bridge.requests.path_for(rid)
    p.write_bytes(p.read_bytes()[:40])
    with pytest.raises(Exception):
        bridge.request_payload(rid)
    assert bridge.integrity()["ok"] is False


# 5 partial response ----------------------------------------------------------
def test_ia_a05_partial_response(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "A"))
    p = bridge.responses.path_for(rid)
    p.write_bytes(p.read_bytes()[:30])
    with pytest.raises(Exception):
        bridge.consume_response(rid)


# 6 torn temp write + torn ledger tail ----------------------------------------
def test_ia_a06_torn_temp_write_not_consumed(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    tmp = bridge.responses.responses_dir / f".{rid}.json.tmp-1-1"
    tmp.write_bytes(envelope(bridge, rid, "A")[:25])
    assert bridge.recovery_state(rid)["classification"] == CLASSIFICATION_DISPATCHED_AWAITING_RESPONSE
    with pytest.raises(Exception):
        handler_for(tmp_path, timeout_s=0.3)(snapshot(0))
    assert not any(r["event"] == "response_consumed" for r in bridge.ledger.read_records())


def test_ia_a06b_torn_ledger_tail_fails_closed(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    with open(bridge.ledger.path, "ab") as h:
        h.write(b'{"seq":2,"event":"response_pub')
    with pytest.raises(Exception):
        handler_for(tmp_path, timeout_s=0.3)(snapshot(0))


# 7 orphan request file ---------------------------------------------------------
def test_ia_a07_orphan_request_file(tmp_path):
    bridge = ExchangeBridge(tmp_path)
    orphan = bridge.requests.requests_dir / "req-0001-model_directive-abcdef01.json"
    orphan.write_bytes(b'{"orphan":true}\n')
    assert any("orphan request" in p for p in bridge.integrity()["problems"])
    with pytest.raises(ResponsePublishError):
        bridge.responses.publish_bytes(
            request_id=orphan.stem,
            response_bytes=envelope(bridge, orphan.stem, "A", request_sha=sha256_hex(orphan.read_bytes())),
        )


# 8 orphan response file --------------------------------------------------------
def test_ia_a08_orphan_response_file_not_consumed(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    bridge.responses.path_for(rid).write_bytes(envelope(bridge, rid, "ORPHAN"))
    assert bridge.integrity()["ok"] is False
    with pytest.raises(Exception):
        handler_for(tmp_path, timeout_s=0.3)(snapshot(0))
    assert not any(r["event"] == "response_consumed" for r in bridge.ledger.read_records())


# 9 duplicate request publication -------------------------------------------------
def test_ia_a09_duplicate_request_id_refused(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    with pytest.raises(RequestPublishError):
        bridge.publish_request(kind="model_directive", body=serialize_runtime_snapshot(snapshot(0)), request_id=rid)


def test_ia_a09b_duplicate_request_record_is_ambiguous_fail_closed(tmp_path):
    """A second request_published record for the same id (valid chain) is an
    ambiguous exchange; the runner must refuse rather than pick one."""
    bridge, rid = _publish(tmp_path, snapshot(0))
    bridge.ledger.append("request_published", request_id=rid, request_sha256="1" * 64)
    try:
        bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "DUP"))
    except Exception:
        pass
    with pytest.raises(Exception):
        handler_for(tmp_path, timeout_s=0.3)(snapshot(0))


# 10 duplicate response publication -----------------------------------------------
def test_ia_a10_duplicate_response_publication(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    data = envelope(bridge, rid, "A")
    bridge.responses.publish_bytes(request_id=rid, response_bytes=data)
    again = bridge.responses.publish_bytes(request_id=rid, response_bytes=data)
    assert again["idempotent_replay"] is True
    assert [r["event"] for r in bridge.ledger.read_records()].count("response_published") == 1


# 11 overwrite response ------------------------------------------------------------
def test_ia_a11_overwrite_response_refused(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "A"))
    with pytest.raises(ResponsePublishError):
        bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "B"))


# 12 response consumed before publish ---------------------------------------------
def test_ia_a12_consume_before_publish(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    with pytest.raises(Exception):
        bridge.consume_response(rid)
    bridge.ledger.append("response_consumed", request_id=rid, request_sha256=bridge.request_sha256(rid))
    assert bridge.integrity()["ok"] is False
    bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "A"))
    with pytest.raises(Exception):
        bridge.consume_response(rid)


# 13 ledger interior mutation -------------------------------------------------------
def test_ia_a13_ledger_interior_mutation_runner_fails_closed(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "ORIGINAL"))
    forged = envelope(bridge, rid, "FORGED")
    bridge.responses.path_for(rid).write_bytes(forged)

    def mutate(lines):
        rec = json.loads(lines[1])
        rec["response_sha256"] = sha256_hex(forged)  # record_sha256 NOT recomputed
        lines[1] = canonical_json_bytes(rec) + b"\n"
        return lines

    rewrite_ledger_lines(bridge.ledger.path, mutate)
    assert bridge.ledger.verify_chain()["ok"] is False
    outcome = None
    try:
        directive = handler_for(tmp_path, timeout_s=0.3)(snapshot(0))
        outcome = directive.response
    except Exception as exc:
        outcome = f"RAISED {type(exc).__name__}"
    assert outcome.startswith("RAISED"), f"runner accepted a broken hash chain and returned {outcome!r}"


def test_ia_a13b_consume_on_broken_chain_fails_closed(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "A"))

    def mutate(lines):
        rec = json.loads(lines[0])
        rec["wall_clock"] = "2000-01-01T00:00:00.000000Z"
        lines[0] = canonical_json_bytes(rec) + b"\n"
        return lines

    rewrite_ledger_lines(bridge.ledger.path, mutate)
    assert bridge.ledger.verify_chain()["ok"] is False
    with pytest.raises(Exception):
        bridge.consume_response(rid)


# 14 ledger interior deletion --------------------------------------------------------
def test_ia_a14_ledger_interior_deletion_runner_fails_closed(tmp_path):
    root = tmp_path
    with IAResponder(root):
        handler_for(root, timeout_s=5)(snapshot(0))
        handler_for(root, timeout_s=5)(snapshot(0))
    bridge = ExchangeBridge(root)
    events = [r["event"] for r in bridge.ledger.read_records()]
    assert events == ["request_published", "response_published", "response_consumed"] * 2
    rewrite_ledger_lines(bridge.ledger.path, lambda lines: lines[:2] + lines[3:])  # delete consume #1
    assert bridge.ledger.verify_chain()["ok"] is False
    outcome = None
    try:
        directive = handler_for(root, timeout_s=0.3)(snapshot(0))
        outcome = directive.response
    except Exception as exc:
        outcome = f"RAISED {type(exc).__name__}"
    assert outcome.startswith("RAISED"), f"runner re-served a response after interior deletion: {outcome!r}"


# 15 tail truncation ------------------------------------------------------------------
def test_ia_a15_tail_truncation_partial_line_fails_closed(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "A"))
    raw = bridge.ledger.path.read_bytes()
    bridge.ledger.path.write_bytes(raw[:-15])
    with pytest.raises(Exception):
        handler_for(tmp_path, timeout_s=0.3)(snapshot(0))


def test_ia_a15b_whole_record_tail_truncation_INFO(tmp_path):
    """INFO only: dropping complete trailing records leaves a valid prefix chain.
    Records observed behaviour; no pass/fail requirement (no external anchor)."""
    bridge, rid = _publish(tmp_path, snapshot(0))
    bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "A"))
    bridge.consume_response(rid)
    rewrite_ledger_lines(bridge.ledger.path, lambda lines: lines[:-1])
    state = bridge.recovery_state(rid)
    print("INFO a15b classification after dropping trailing consume record:", state["classification"],
          "chain_ok:", bridge.ledger.verify_chain()["ok"])


# 16 missing request_published ----------------------------------------------------------
def test_ia_a16_missing_request_published(tmp_path):
    bridge = ExchangeBridge(tmp_path)
    rid = "req-0001-model_directive-00000000"
    (bridge.requests.requests_dir / f"{rid}.json").write_bytes(b"{}\n")
    with pytest.raises(ResponsePublishError):
        bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "A", request_sha="a" * 64))
    with pytest.raises(Exception):
        bridge.consume_response(rid)
    assert bridge.recovery_state(rid)["classification"] == CLASSIFICATION_NOT_SUBMITTED


# 17 missing response_published -----------------------------------------------------------
def test_ia_a17_missing_response_published(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    bridge.responses.path_for(rid).write_bytes(envelope(bridge, rid, "A"))
    with pytest.raises(Exception):
        bridge.consume_response(rid)
    with pytest.raises(Exception):
        handler_for(tmp_path, timeout_s=0.3)(snapshot(0))


# 18 crash before request publication (real SIGKILL between file write and ledger append)
CRASH_WORKER = r'''
import os, signal, sys
sys.path.insert(0, sys.argv[2]); sys.path.insert(0, sys.argv[3])
from aios_exchange.bridge import ExchangeBridge
import aios_exchange.ledger as L
orig = L.ExchangeLedger.append
def boom(self, event, **kw):
    if event == "request_published":
        os.kill(os.getpid(), signal.SIGKILL)
    return orig(self, event, **kw)
L.ExchangeLedger.append = boom
sys.path.insert(0, sys.argv[4])
from ia_common import snapshot, serialize_runtime_snapshot
ExchangeBridge(sys.argv[1]).publish_request(kind="model_directive", body=serialize_runtime_snapshot(snapshot(0)))
'''


def test_ia_a18_crash_before_request_publication(tmp_path):
    from ia_common import CORE_SRC
    root = tmp_path / "x"
    proc = subprocess.run(
        [sys.executable, "-c", CRASH_WORKER, str(root), str(HARNESS_ROOT), str(CORE_SRC), str(pathlib.Path(__file__).parent)],
        capture_output=True, text=True,
    )
    assert proc.returncode == -signal.SIGKILL, proc.stderr
    bridge = ExchangeBridge(root)
    assert list(bridge.requests.requests_dir.glob("req-*.json")), "expected orphan request file"
    state = bridge.recovery_state()
    assert state["classification"] == CLASSIFICATION_NOT_SUBMITTED
    assert bridge.integrity()["ok"] is False
    # restart: runner must not return a directive for a request lacking a ledger record
    returned = None
    try:
        with IAResponder(root):
            returned = handler_for(root, timeout_s=2)(snapshot(0))
    except Exception as exc:
        returned = f"RAISED {type(exc).__name__}"
    if not isinstance(returned, str):
        pub = [r for r in bridge.ledger.read_records() if r["event"] == "request_published"]
        assert pub, "directive returned without any request_published record"
    print("INFO a18 restart outcome:", returned if isinstance(returned, str) else "directive-after-new-publication")


# 19 crash after request publication --------------------------------------------------------
def test_ia_a19_crash_after_request_same_snapshot_resumes(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    t = threading.Timer(0.2, lambda: bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "RESUMED")))
    t.start()
    d = handler_for(tmp_path, timeout_s=5)(snapshot(0))
    t.join()
    assert d.response == "RESUMED"
    assert [r["event"] for r in bridge.ledger.read_records()].count("request_published") == 1


def test_ia_a19b_crash_after_request_different_snapshot_fails_closed(tmp_path):
    """Outstanding request was published for a round-1 snapshot; after restart the
    frozen Core replays the turn from round 0 (history empty). Resolving the old
    request for the new snapshot silently binds a decision to a context it was
    not made for; the runner must refuse (fail closed)."""
    bridge, rid = _publish(tmp_path, snapshot_round1())
    t = threading.Timer(0.3, lambda: bridge.responses.publish_bytes(
        request_id=rid, response_bytes=envelope(bridge, rid, "DECIDED_FOR_ROUND_1")))
    t.start()
    outcome = None
    try:
        outcome = handler_for(tmp_path, timeout_s=3)(snapshot(0)).response
    except Exception as exc:
        outcome = f"RAISED {type(exc).__name__}"
    t.join()
    assert outcome.startswith("RAISED"), (
        f"round-0 snapshot received the directive decided for the round-1 request: {outcome!r}"
    )


# 20 response durable but not consumed --------------------------------------------------------
def test_ia_a20_durable_unconsumed_same_snapshot_consumed_once(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "DURABLE"))
    d = handler_for(tmp_path)(snapshot(0))
    assert d.response == "DURABLE"
    ev = [r["event"] for r in bridge.ledger.read_records()]
    assert ev == ["request_published", "response_published", "response_consumed"]


def test_ia_a20b_durable_unconsumed_different_snapshot_fails_closed(tmp_path):
    """Crash after the response for a round-1 request became durable; the Core
    replays from round 0. The durable round-1 answer must not be applied to the
    round-0 snapshot."""
    bridge, rid = _publish(tmp_path, snapshot_round1())
    bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "DECIDED_FOR_ROUND_1"))
    outcome = None
    try:
        outcome = handler_for(tmp_path, timeout_s=0.5)(snapshot(0)).response
    except Exception as exc:
        outcome = f"RAISED {type(exc).__name__}"
    assert outcome.startswith("RAISED"), f"durable response for round-1 request applied to round-0 snapshot: {outcome!r}"


# multiple outstanding -----------------------------------------------------------------------
def test_ia_a21_multiple_outstanding_is_ambiguous_fail_closed(tmp_path):
    bridge = ExchangeBridge(tmp_path)
    r1 = bridge.publish_request(kind="model_directive", body=serialize_runtime_snapshot(snapshot(0)))["request_id"]
    r2 = bridge.publish_request(kind="model_directive", body=serialize_runtime_snapshot(snapshot_round1()))["request_id"]
    bridge.responses.publish_bytes(request_id=r1, response_bytes=envelope(bridge, r1, "FIRST"))
    bridge.responses.publish_bytes(request_id=r2, response_bytes=envelope(bridge, r2, "SECOND"))
    outcome = None
    try:
        outcome = handler_for(tmp_path, timeout_s=0.5)(snapshot(0)).response
    except Exception as exc:
        outcome = f"RAISED {type(exc).__name__}"
    assert outcome.startswith("RAISED"), f"two unconsumed responses; runner silently picked {outcome!r}"


# dispatch boundary invariant -----------------------------------------------------------------
def test_ia_inv_dispatch_boundary_null_provider_fields(tmp_path):
    bridge, rid = _publish(tmp_path, snapshot(0))
    st = bridge.recovery_state(rid)
    assert st["classification"] != CLASSIFICATION_NOT_SUBMITTED
    assert st["not_submitted_allowed"] is False
    assert st["semantic_dispatch_occurred"] is True
    # response with null usage/provenance (provider/model null)
    bridge.responses.publish_bytes(request_id=rid, response_bytes=envelope(bridge, rid, "A"))
    bridge.consume_response(rid)
    st = bridge.recovery_state(rid)
    assert st["classification"] == CLASSIFICATION_COMPLETE
    assert st["not_submitted_allowed"] is False
    # no code path in the run package emits a not_submitted verdict from provider fields
    src = "".join(p.read_text() for p in (HARNESS_ROOT / "aios_exchange").glob("*.py"))
    assert "ModelDispatchNotSubmitted" not in src
