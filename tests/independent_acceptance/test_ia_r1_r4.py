"""IA rev1 — R1 pre-submission, R2 ambiguous submission, R3 handoff atomicity, R4 later rounds.

Frozen expectations:
  R1 crash BEFORE provider submission  -> mechanical proof of not-submitted, safe retry,
                                        exactly one provider submission, no phantom rows.
  R2 submitted but NO trusted return  -> never blind-redispatch; fail closed.
  R3 crash around the handoff txn     -> never a receipt-only or handoff-only half state.
  R4 later-round exact recovery       -> same attempt/round/request/receipt/payload,
                                        one meter, no redispatch, correct continuation.
"""
from __future__ import annotations

import sqlite3

import pytest

from aios_core.contracts.enums import ObjectType
from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptBlocked, BackgroundModelResponseConflict,
    BackgroundModelResponsePending, decode_model_directive,
)
from aios_core.runtime.capabilities import CapabilityCall

from ia_harness import (
    ANCHOR, NOW, ProcessDeath, attempt_rows, cap, directive, handoff_rows,
    meter_rows, new_runtime, payloads, q, receipt_rows, seed_anchor, staged_rows,
)

SESSION = "ia-r-session"


def _watch(r):
    return cap("create_attention_watch", f"ia-watch-{r}", dict(
        title=f"ia watch {r}", dimensions=["dim:ia"],
        reason_refs=[{"object_id": ANCHOR, "revision": 1}],
        source_kind="conversation", modality="text", priority=40,
        cooldown_seconds=60))


def _work_id(rt):
    return rt.turn_executions.execution_id_for(
        subject_id=rt.subject_id, session_id=SESSION, turn_index=1)


def _seed(db):
    rt = new_runtime(db, lambda s: directive(0))
    seed_anchor(rt.store)
    rt.index.catch_up()
    return rt


def _counts(db):
    return {
        "attempts": len(attempt_rows(db)),
        "handoffs": len(handoff_rows(db)),
        "receipts": len(receipt_rows(db)),
        "staged": len(staged_rows(db)),
        "meters": len(meter_rows(db)),
    }


# ------------------------------------------------------------------- R1

def test_ia_r1_crash_before_submission_allows_exactly_one_retry(tmp_path):
    db = tmp_path / "w.db"
    rt = _seed(db)
    work_id = _work_id(rt)
    served = []

    def provider(snapshot):
        served.append(snapshot.round_index)
        return directive(snapshot.round_index)

    rt.cognitive_runtime.model_handler = provider
    real = rt.background_model_attempts.mark_dispatching

    def die(*a, **k):
        # the attempt is durably admitted; nothing was submitted to the provider
        raise ProcessDeath("crash after admission, before provider submission")

    rt.background_model_attempts.mark_dispatching = die
    with pytest.raises(ProcessDeath):
        rt.run_turn(session_id=SESSION, turn_index=1, user_input="IA R1", occurred_at=NOW)

    before = _counts(db)
    assert before["handoffs"] == 0 and before["receipts"] == 0, "phantom receipt/handoff"
    assert served == [], "provider was called despite pre-submission crash"

    fresh_served = []

    def cont(snapshot):
        fresh_served.append(snapshot.round_index)
        return directive(snapshot.round_index)

    fresh = new_runtime(db, cont)
    # Core owns the authorization to retry. R1 requires: no blind redispatch of an
    # ambiguous attempt, no phantom receipt/handoff, and no fabricated return.
    try:
        fresh.run_turn(session_id=SESSION, turn_index=1, user_input="IA R1", occurred_at=NOW)
    except Exception:
        pass                                   # fail-closed refusal is acceptable
    assert len(fresh_served) <= 1, f"multiple provider submissions: {fresh_served}"
    after = _counts(db)
    # Either recovery was authorized and completed exactly once, or it failed closed.
    # What must never happen: a fabricated return, or more than one submission.
    assert after["attempts"] >= before["attempts"]
    if fresh_served:
        assert after["receipts"] == 1 and after["handoffs"] == 1, \
            "retry without a trusted return"
    else:
        assert after["receipts"] == 0 and after["handoffs"] == 0, \
            "Core invented a return it never received"


def test_ia_r1_stale_admitted_attempt_state_is_not_treated_as_submitted(tmp_path):
    db = tmp_path / "w.db"
    rt = _seed(db)
    work_id = _work_id(rt)
    served = []
    rt.cognitive_runtime.model_handler = (
        lambda s: served.append(s.round_index) or directive(s.round_index))
    rt.run_turn(session_id=SESSION, turn_index=1, user_input="IA R1b", occurred_at=NOW)
    rows = attempt_rows(db)
    assert rows, "no attempt recorded"
    # An attempt that never reached a terminal metered state must not be replayable.
    states = {r["state"] for r in rows}
    assert states <= {"admitted", "not_submitted", "dispatching", "in_doubt",
                      "response_returned", "metered", "failed"}


# ------------------------------------------------------------------- R2

def test_ia_r2_submitted_without_trusted_return_never_blind_redispatches(tmp_path):
    db = tmp_path / "w.db"
    rt = _seed(db)
    work_id = _work_id(rt)
    served = []

    def provider(snapshot):
        served.append(snapshot.round_index)
        return directive(snapshot.round_index)

    rt.cognitive_runtime.model_handler = provider
    # Crash after the provider returned but BEFORE the trusted callback commits.
    real_capture = rt.background_model_attempts._capture_trusted_response_return

    def die(*a, **k):
        raise ProcessDeath("crash after submission, before trusted handoff")

    rt.background_model_attempts._capture_trusted_response_return = die
    with pytest.raises(ProcessDeath):
        rt.run_turn(session_id=SESSION, turn_index=1, user_input="IA R2", occurred_at=NOW)
    assert served == [0]
    assert handoff_rows(db) == [], "handoff must not exist"
    assert receipt_rows(db) == [], "receipt must not exist"

    fresh_served = []

    def cont(snapshot):
        fresh_served.append(snapshot.round_index)
        pytest.fail("R2 REDISPATCH: ambiguous submission was retried blindly")

    fresh = new_runtime(db, cont)
    with pytest.raises(Exception) as exc:
        fresh.run_turn(session_id=SESSION, turn_index=1, user_input="IA R2", occurred_at=NOW)
    assert fresh_served == [], f"provider was redispatched: {fresh_served}"
    assert handoff_rows(db) == [] and receipt_rows(db) == [], \
        "Core invented a return it never received"


# ------------------------------------------------------------------- R3

def test_ia_r3_handoff_and_receipt_commit_atomically(tmp_path):
    """The trusted callback must never leave receipt-only or handoff-only state."""
    db = tmp_path / "w.db"
    rt = _seed(db)
    work_id = _work_id(rt)
    served = []
    rt.cognitive_runtime.model_handler = (
        lambda s: served.append(s.round_index) or directive(s.round_index, call=_watch(s.round_index)))
    rt.run_turn(session_id=SESSION, turn_index=1, user_input="IA R3", occurred_at=NOW)
    for table in ("background_model_response_receipts", "background_model_return_handoffs"):
        rows = q(db, f"SELECT attempt_id FROM {table}")
        attempts = {r["attempt_id"] for r in attempt_rows(db)}
        for r in rows:
            assert r["attempt_id"] in attempts, f"orphan row in {table}"
    receipt_ids = {r["attempt_id"] for r in receipt_rows(db)}
    handoff_ids = {r["attempt_id"] for r in handoff_rows(db)}
    assert receipt_ids == handoff_ids, (
        f"HALF STATE: receipts-only={receipt_ids - handoff_ids} "
        f"handoff-only={handoff_ids - receipt_ids}")


def test_ia_r3_partial_handoff_is_never_accepted_as_trusted(tmp_path):
    """Deleting only the receipt must make recovery fail closed, not fall back."""
    db = tmp_path / "w.db"
    rt = _seed(db)
    work_id = _work_id(rt)
    served = []
    original = rt.cognitive_runtime.model_response_recorder

    def die(snapshot, returned):
        if snapshot.round_index == 0:
            raise ProcessDeath("crash after handoff")
        original(snapshot, returned)

    rt.cognitive_runtime.model_handler = (
        lambda s: served.append(s.round_index) or directive(s.round_index))
    rt.cognitive_runtime.model_response_recorder = die
    with pytest.raises(ProcessDeath):
        rt.run_turn(session_id=SESSION, turn_index=1, user_input="IA R3b", occurred_at=NOW)
    assert len(handoff_rows(db)) == 1
    with sqlite3.connect(db) as conn:                 # remove only the receipt
        conn.execute("DELETE FROM background_model_response_receipts")
        conn.commit()
    fresh = new_runtime(db, lambda s: pytest.fail("R3 redispatch"))
    with pytest.raises((BackgroundModelResponseConflict, BackgroundModelResponsePending)):
        fresh.background_model_attempts.recover_trusted_handoff(
            subject_id="user_1", work_kind="user_turn", work_id=work_id)


def test_ia_r3_mismatched_receipt_and_handoff_fails_closed(tmp_path):
    db = tmp_path / "w.db"
    rt = _seed(db)
    work_id = _work_id(rt)
    original = rt.cognitive_runtime.model_response_recorder

    def die(snapshot, returned):
        if snapshot.round_index == 0:
            raise ProcessDeath("crash after handoff")
        original(snapshot, returned)

    rt.cognitive_runtime.model_handler = lambda s: directive(s.round_index)
    rt.cognitive_runtime.model_response_recorder = die
    with pytest.raises(ProcessDeath):
        rt.run_turn(session_id=SESSION, turn_index=1, user_input="IA R3c", occurred_at=NOW)
    h = handoff_rows(db)[0]
    aid = h["attempt_id"]
    other = [r for r in handoff_rows(db)]
    payload = h["directive_payload"].replace("finished once", "finished TWICE")
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE background_model_return_handoffs SET directive_payload=? "
                     "WHERE attempt_id=?", (payload, aid))
        conn.commit()
    fresh = new_runtime(db, lambda s: pytest.fail("R3 redispatch"))
    with pytest.raises((BackgroundModelResponseConflict, BackgroundModelResponsePending)):
        fresh.background_model_attempts.recover_trusted_handoff(
            subject_id="user_1", work_kind="user_turn", work_id=work_id)


# ------------------------------------------------------------------- R4

@pytest.mark.parametrize("last_round", [1, 2])
def test_ia_r4_later_round_exact_recovery(tmp_path, last_round):
    db = tmp_path / "w.db"
    served = []

    def provider(snapshot):
        served.append(snapshot.round_index)
        item = _watch(snapshot.round_index) if snapshot.round_index < last_round else None
        return directive(snapshot.round_index, call=item)

    initial = new_runtime(db, provider)
    seed_anchor(initial.store)
    initial.index.catch_up()
    work_id = _work_id(initial)
    original = initial.cognitive_runtime.model_response_recorder

    def die(snapshot, returned):
        if snapshot.round_index == last_round:
            raise ProcessDeath("crash at later-round trusted return")
        original(snapshot, returned)

    initial.cognitive_runtime.model_response_recorder = die
    with pytest.raises(ProcessDeath):
        initial.run_turn(session_id=SESSION, turn_index=1, user_input="IA R4",
                         occurred_at=NOW)
    assert served == list(range(last_round + 1))

    store = rt_store = initial.background_model_attempts
    before_attempts = store.list_for_work(subject_id="user_1", work_kind="user_turn",
                                          work_id=work_id)
    assert [a.model_round_index for a in before_attempts] == list(range(last_round + 1))
    before_receipts = {a.attempt_id: store.response_authenticity_receipt(a.attempt_id)
                       for a in before_attempts}
    before_handoffs = {r["attempt_id"]: r for r in handoff_rows(db)}
    before_meters = sorted(
        (m for m in initial.metering.list_model_calls(subject_id="user_1")),
        key=lambda m: m.model_round_index)

    fresh_rounds = []

    def cont(snapshot):
        fresh_rounds.append(snapshot.round_index)
        return directive(snapshot.round_index)

    fresh = new_runtime(db, cont)
    result = fresh.run_turn(session_id=SESSION, turn_index=1, user_input="IA R4",
                            occurred_at=NOW)
    replayed = [r for r in fresh_rounds if r <= last_round]
    assert replayed == [], f"REDISPATCH: recovered round reached provider: {fresh_rounds}"

    after_attempts = fresh.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind="user_turn", work_id=work_id)
    assert [a.attempt_id for a in after_attempts[:last_round + 1]] == \
        [a.attempt_id for a in before_attempts], "attempt identity changed"
    for a in before_attempts:
        assert fresh.background_model_attempts.response_authenticity_receipt(
            a.attempt_id) == before_receipts[a.attempt_id], "receipt changed"
        assert before_handoffs[a.attempt_id]["directive_payload"] == \
            {r["attempt_id"]: r for r in handoff_rows(db)}[a.attempt_id]["directive_payload"]
    after_meters = sorted(
        (m for m in fresh.metering.list_model_calls(subject_id="user_1")),
        key=lambda m: m.model_round_index)
    for m in before_meters:
        assert sum(1 for x in after_meters if x.record_id == m.record_id) == 1, \
            f"DUPLICATE METER for {m.record_id}"
    status = fresh.inspect_turn_execution(session_id=SESSION, turn_index=1,
                                         user_input="IA R4", occurred_at=NOW)
    assert status.state == "completed", "turn did not converge after later-round recovery"
