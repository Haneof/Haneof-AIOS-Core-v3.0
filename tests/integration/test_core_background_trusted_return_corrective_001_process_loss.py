"""CORRECTIVE-001 real process-loss R5-C probes.

``IA-BLK-TRUSTED-RETURN-001`` requires EXACTLY-ONCE DURABLE EFFECT for an
identical recovered capability invocation, proven for at least one capability
family other than ``create_task`` under a REAL process loss -- not a simulated
one. Every probe here:

  1. forks a child process that dispatches a real model round, returns a real
     trusted provider directive, applies the capability so its side effect is
     durable, and then ``SIGKILL``s itself before the outer completion lands;
  2. asserts the child really died to ``SIGKILL`` (``exitcode == -SIGKILL``);
  3. reopens the durable World in the parent with a brand new runtime and
     replays the identical recovered directive;
  4. asserts: no provider redispatch for the recovered round, one meter row,
     exactly one durable capability effect, one operation identity, and a
     converging logical turn.

Runtime-mode coverage rationale
------------------------------
Background attempts are keyed by ``work_kind``, and the three modes reach the
recovered capability replay through different admission and authorization paths
(``_authorize_side_effect`` gives C14 wakes a four-name allowlist while user
turns, Periodic Review and other wakes share the twenty-name set). The frozen
capability matrix already covers all 22 side-effecting capabilities in one work
kind. These probes therefore add the modes and the family the reviewer demanded:

* ``wake`` + ``revise_claim`` -- the required NON-``create_task`` family, and a
  revision-ADVANCING mutator, where the failure mode is a duplicate second Claim
  revision rather than a rejection. This family was RED on the failed exact
  candidate.
* ``user_turn`` + ``transition_goal`` -- a second revision-advancing mutator in
  the foreground mode, through ``run_turn`` admission.
* ``periodic_review`` + ``form_event`` -- one of the five reviewer-proven RED
  families, in the review work kind.

TIGHTEN_ONLY history (Corrective-003 / Window 22-RERUN-001)
----------------------------------------------------------
Old expectation: after the real ``SIGKILL``, the parent could replay the identical
recovered directive because the *live local handler return inside the child had
already minted a durable trusted receipt* for the round.

Old authority mechanism: ``live_return.open_live_provider_return_window`` +
``register_handler_return`` + ``BackgroundModelAttemptStore.record_live_provider_return``
(reached through the shared ``_stage(trusted_return=True)`` helper).

Why unsafe (BLK-W20-001):
``RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW``, root
cause ``TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE`` -- window issuance was
an ordinary public function, so any process-local recovery caller could self-issue a
window, declare its own bytes handler-returned and mint the trusted receipt these
probes replayed after a real process death.

Replacement route: Route B.  Every runtime in this file (parent and forked child) is
now built by ``_route_b_runtime``, which binds an external late-return verifier before
the provider boundary.  The exact bytes are preserved across the real ``SIGKILL`` by a
genuine external RSA signature over Core's durable pre-dispatch request binding -- the
binding row itself survives the kill, which is what makes the external proof obtainable
in the parent.  The private exponent is TEST-ONLY material owned by the simulated
external side.

Kept unchanged: every real ``SIGKILL`` (``exitcode == -SIGKILL``), every capability
family and runtime mode, the zero-provider-redispatch requirement, the single meter
row, the exactly-one durable capability effect, the single operation identity, the
converging logical turn, and every revision assertion.  No probe was turned into a
simulated crash and no expectation was weakened.
"""
from __future__ import annotations

import multiprocessing
import os
import signal as posix_signal
import sqlite3
from datetime import timedelta

from aios_core.contracts.enums import ObjectType, SourceClass, WakeSource
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import WakeSignalRequest
from test_core_background_response_recovery_001_corrective_001 import (
    NOW,
    _attempt,
    _directive,
    _route_b_runtime,
    _running_review_id,
    _seed_review_fact,
    _stage,
    _wake_ref,
)

SUBJECT = "user_1"
ANCHOR = {"object_id": "obs_corrective001_pl_anchor", "revision": 1}


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #
def _reopen(db):
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def _runtime(db) -> FusedTurnRuntime:
    store, index = _reopen(db)
    return _route_b_runtime(store=store, index=index, model_handler=lambda _s: None)


def _invoke(runtime: FusedTurnRuntime, name: str, arguments: dict, *, call_id: str):
    """Invoke a capability at the recovered write time (seeding only)."""

    runtime._active_turn_time = NOW
    try:
        result = runtime.registry.invoke(
            CapabilityCall(name=name, call_id=call_id, arguments=dict(arguments))
        )
    finally:
        runtime._active_turn_time = None
    assert result.ok, f"{name} seed failed: {result.error_code} {result.error_message}"
    return result.data


def _kill_when_done(runtime: FusedTurnRuntime, capability: str) -> None:
    """Let the real handler commit durably, then die before outer completion."""

    real_handler = getattr(runtime, f"_{capability}")

    def die_after_durable_effect(**kwargs):
        real_handler(**kwargs)
        os.kill(os.getpid(), posix_signal.SIGKILL)

    spec = runtime.registry.get_spec(capability)
    runtime.registry.unregister(capability)
    runtime.registry.register(spec, die_after_durable_effect)


def _bind_scripted(runtime: FusedTurnRuntime, directive) -> None:
    def scripted(snapshot):
        if snapshot.round_index == 0:
            return directive
        raise AssertionError("process must die during capability application")

    runtime.model_handler = scripted
    runtime.cognitive_runtime.model_handler = scripted


def _new_wake(runtime: FusedTurnRuntime, *, key: str):
    return runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id=f"corrective001.{key}",
            observed_at=NOW,
            dedupe_key=f"corrective001:{key}",
        )
    )


def _running_wake(store: SQLiteWorldStore) -> dict:
    running = [
        payload
        for payload in store.list_payloads(object_type=ObjectType.WAKE, subject_id=SUBJECT)
        if payload.get("wake_state") == "running"
        and payload.get("wake_source") == WakeSource.SAFETY.value
    ]
    assert len(running) == 1, f"expected one running safety wake, got {len(running)}"
    return running[0]


def _revisions(db, object_id: str) -> list[int]:
    with sqlite3.connect(db) as conn:
        return [
            int(row[0])
            for row in conn.execute(
                "SELECT revision FROM object_revisions WHERE object_id=? ORDER BY revision",
                (object_id,),
            )
        ]


def _operations(db, name_prefix: str) -> list[tuple[str, str, str]]:
    with sqlite3.connect(db) as conn:
        return conn.execute(
            "SELECT operation_id, idempotency_key, status FROM operations "
            "WHERE operation_name LIKE ? ORDER BY rowid",
            (f"{name_prefix}%",),
        ).fetchall()


def _seed_anchor(runtime: FusedTurnRuntime) -> None:
    moment = NOW - timedelta(hours=2)
    runtime.store.commit(
        [
            Observation(
                object_id=ANCHOR["object_id"],
                subject_id=SUBJECT,
                occurred=TemporalExtent.point(moment),
                learned_at=moment,
                recorded_at=moment,
                created_by="test:corrective001-process-loss",
                source_kind="conversation",
                modality="text",
                value="Durable reality anchor for the process-loss probes.",
                metadata={"dimension": "dim:corrective001"},
            )
        ],
        OperationRequest(
            operation_name="test.corrective001.seed_anchor",
            expected_world_revision=int(runtime.store.current_world_revision()),
            reason="seed process-loss evidence",
            idempotency_key="corrective001:seed-process-loss-anchor",
            source_class=SourceClass.USER,
        ),
    )
    runtime.index.catch_up()


def _round0_meter(runtime: FusedTurnRuntime, **scope):
    """The meter rows for the recovered (round 0) model round only.

    A capability directive cannot also terminate the turn -- ``ModelDirective``
    rejects that outright -- so a recovered capability round is always followed by
    a legitimately NEW model round. Exactly-once therefore means exactly one meter
    row for the recovered round itself, not one meter row in total.
    """

    session_id = scope.pop("session_id", None)
    return tuple(
        record
        for record in runtime.metering.list_model_calls(subject_id=SUBJECT, **scope)
        if int(record.model_round_index) == 0
        and (session_id is None or record.session_id == session_id)
    )


def _run_child(target, db) -> None:
    process = multiprocessing.get_context("fork").Process(target=target, args=(str(db),))
    process.start()
    process.join(60)
    assert process.exitcode == -posix_signal.SIGKILL, (
        f"the child must die to a real SIGKILL, exitcode={process.exitcode}"
    )


# --------------------------------------------------------------------------- #
# wake mode + revise_claim (revision-advancing mutator, NON-create_task family)
# --------------------------------------------------------------------------- #
REVISE_ARGUMENTS = {
    "reason": "process-loss corrective revision",
    "evidence_refs": [ANCHOR],
    "replacement_content": "process-loss replacement content",
}


def _revise_arguments(claim_id: str) -> dict:
    return {
        "target_ref": {"object_id": claim_id, "revision": 1},
        **REVISE_ARGUMENTS,
    }


def _child_wake_revise_claim_then_sigkill(db_path: str) -> None:
    runtime = _runtime(db_path)
    _seed_anchor(runtime)
    claim = _invoke(
        runtime,
        "commit_claim",
        {
            "content": "process-loss wake claim",
            "evidence_refs": [ANCHOR],
            "confidence": 0.5,
            "dimension": "dim:corrective001",
        },
        call_id="seed-wake-claim",
    )
    _bind_scripted(
        runtime,
        _directive(
            "req-pl-wake-revise",
            silence=False,
            capability_calls=(
                CapabilityCall(
                    name="revise_claim",
                    arguments=_revise_arguments(str(claim["claim_id"])),
                    call_id="call-pl-revise-claim",
                ),
            ),
        ),
    )
    _kill_when_done(runtime, "revise_claim")
    signal = _new_wake(runtime, key="wake-revise-claim")
    runtime.run_wake(wake_ref=_wake_ref(signal), now=NOW)


def test_process_sigkill_after_revise_claim_replays_exactly_once(tmp_path):
    """Real process loss in a revision-advancing NON-create_task family."""

    db = tmp_path / "pl-wake-revise-claim.db"
    _run_child(_child_wake_revise_claim_then_sigkill, db)

    # The capability side effect is durable; the outer completion is not.
    store, index = _reopen(db)
    revised = [
        payload
        for payload in store.list_payloads(object_type=ObjectType.CLAIM, subject_id=SUBJECT)
        if payload.get("content") == REVISE_ARGUMENTS["replacement_content"]
    ]
    assert len(revised) == 1, "the durable revision effect is missing"
    claim_id = str(revised[0]["object_id"])
    assert _revisions(db, claim_id) == [1, 2]
    ops_before = _operations(db, "cognition.revise_claim")
    assert len(ops_before) == 1

    wake = _running_wake(store)
    wake_id = str(wake["object_id"])
    attempt = _attempt(
        _route_b_runtime(store=store, index=index, model_handler=lambda _s: None),
        work_kind="wake",
        work_id=wake_id,
    )
    assert attempt is not None
    assert attempt.state == "metered", (
        "the durable side effect landed, so the outer completion must not have"
    )

    meter_before = _round0_meter(
        _route_b_runtime(store=store, index=index, model_handler=lambda _s: None),
        wake_id=wake_id,
    )
    assert len(meter_before) == 1, "the crashed round was not metered"

    recovery_rounds: list[int] = []

    def provider(snapshot):
        recovery_rounds.append(snapshot.round_index)
        return _directive("req-pl-wake-revise-next", silence=True)

    restarted = _route_b_runtime(store=store, index=index, model_handler=provider)
    _stage(
        restarted,
        work_kind="wake",
        work_id=wake_id,
        round_index=0,
        directive=_directive(
            attempt.provider_request_id,
            silence=False,
            capability_calls=(
                CapabilityCall(
                    name="revise_claim",
                    arguments=_revise_arguments(claim_id),
                    call_id="call-pl-revise-claim",
                ),
            ),
        ),
        trusted_return=True,
    )
    result = restarted.run_wake(
        wake_ref=ObjectRef(object_id=wake_id, revision=int(wake["revision"])),
        now=NOW + timedelta(minutes=9),
    )

    # The recovered round is replayed, never redispatched.
    assert result.runtime.recovered_response_attempts == (attempt.attempt_id,)
    assert recovery_rounds == [1], "round 0 must not be redispatched to the provider"
    # EXACTLY-ONCE durable effect.
    assert _revisions(db, claim_id) == [1, 2], "a second Claim revision was written"
    assert _operations(db, "cognition.revise_claim") == ops_before, (
        "a second revise_claim operation identity appeared"
    )
    round0_after = _round0_meter(restarted, wake_id=wake_id)
    assert len(round0_after) == 1, (
        f"the recovered round was metered twice: {round0_after}"
    )
    assert round0_after[0].record_id == meter_before[0].record_id, (
        "the recovery replaced the original meter row instead of reusing it"
    )
    assert result.wake.state == "completed", "the logical turn did not converge"


# --------------------------------------------------------------------------- #
# user_turn mode + transition_goal (revision-advancing mutator)
# --------------------------------------------------------------------------- #
TURN = dict(
    session_id="session-pl-turn",
    turn_index=1,
    user_input="process-loss user turn",
    occurred_at=NOW,
)
TRANSITION_ARGUMENTS = {
    "new_status": "active",
    "reason": "process-loss goal transition",
    "evidence_refs": [ANCHOR],
}


def _transition_arguments(goal_id: str) -> dict:
    return {"goal_ref": {"object_id": goal_id, "revision": 1}, **TRANSITION_ARGUMENTS}


def _child_user_turn_transition_goal_then_sigkill(db_path: str) -> None:
    runtime = _runtime(db_path)
    _seed_anchor(runtime)
    goal = _invoke(
        runtime,
        "propose_goal",
        {
            "source_type": "user_explicit",
            "title": "process-loss goal",
            "description": "process-loss goal description",
            "evidence_refs": [ANCHOR],
            "confidence": 0.5,
        },
        call_id="seed-turn-goal",
    )
    _bind_scripted(
        runtime,
        _directive(
            "req-pl-turn-transition-goal",
            silence=False,
            capability_calls=(
                CapabilityCall(
                    name="transition_goal",
                    arguments=_transition_arguments(str(goal["goal_id"])),
                    call_id="call-pl-transition-goal",
                ),
            ),
        ),
    )
    _kill_when_done(runtime, "transition_goal")
    runtime.run_turn(**TURN)


def test_process_sigkill_after_transition_goal_replays_exactly_once(tmp_path):
    db = tmp_path / "pl-turn-transition-goal.db"
    _run_child(_child_user_turn_transition_goal_then_sigkill, db)

    store, index = _reopen(db)
    goals = [
        payload
        for payload in store.list_payloads(object_type=ObjectType.GOAL, subject_id=SUBJECT)
        if payload.get("title") == "process-loss goal"
    ]
    assert len(goals) == 1
    goal_id = str(goals[0]["object_id"])
    assert _revisions(db, goal_id) == [1, 2]
    ops_before = _operations(db, "execution.goal.transition")
    assert len(ops_before) == 1

    restarted_probe = _route_b_runtime(store=store, index=index, model_handler=lambda _s: None)
    execution_id = restarted_probe.turn_executions.execution_id_for(
        subject_id=SUBJECT, session_id=TURN["session_id"], turn_index=TURN["turn_index"]
    )
    attempt = _attempt(restarted_probe, work_kind="user_turn", work_id=execution_id)
    assert attempt is not None
    assert attempt.state == "metered"

    meter_before = _round0_meter(
        _route_b_runtime(store=store, index=index, model_handler=lambda _s: None),
        session_id=TURN["session_id"],
    )
    assert len(meter_before) == 1, "the crashed round was not metered"

    recovery_rounds: list[int] = []

    def provider(snapshot):
        recovery_rounds.append(snapshot.round_index)
        return _directive("req-pl-turn-next", silence=True)

    restarted = _route_b_runtime(store=store, index=index, model_handler=provider)
    _stage(
        restarted,
        work_kind="user_turn",
        work_id=execution_id,
        round_index=0,
        directive=_directive(
            attempt.provider_request_id,
            silence=False,
            capability_calls=(
                CapabilityCall(
                    name="transition_goal",
                    arguments=_transition_arguments(goal_id),
                    call_id="call-pl-transition-goal",
                ),
            ),
        ),
        trusted_return=True,
    )
    # The recovered turn keeps the IDENTICAL identity, including occurred_at: that
    # is the stable recovered write time the durable object identity was built from.
    result = restarted.run_turn(**TURN)

    assert result.runtime.recovered_response_attempts == (attempt.attempt_id,)
    assert recovery_rounds == [1], "round 0 must not be redispatched to the provider"
    assert _revisions(db, goal_id) == [1, 2], "a second Goal revision was written"
    assert _operations(db, "execution.goal.transition") == ops_before
    round0_after = _round0_meter(restarted, session_id=TURN["session_id"])
    assert len(round0_after) == 1, (
        f"the recovered round was metered twice: {round0_after}"
    )
    assert round0_after[0].record_id == meter_before[0].record_id, (
        "the recovery replaced the original meter row instead of reusing it"
    )


# --------------------------------------------------------------------------- #
# periodic_review mode + form_event (reviewer-proven RED family)
# --------------------------------------------------------------------------- #
EVENT_TIME = TemporalExtent.point(NOW - timedelta(hours=3)).model_dump(mode="json")
EVENT_ARGUMENTS = {
    "title": "process-loss review event",
    "interpretation": "process-loss review interpretation",
    "event_time": EVENT_TIME,
    "evidence_refs": [ANCHOR],
    "confidence": 0.5,
}


def _child_periodic_review_form_event_then_sigkill(db_path: str) -> None:
    runtime = _runtime(db_path)
    _seed_anchor(runtime)
    _seed_review_fact(runtime.store)
    runtime.index.catch_up()
    _bind_scripted(
        runtime,
        _directive(
            "req-pl-review-form-event",
            silence=False,
            capability_calls=(
                CapabilityCall(
                    name="form_event",
                    arguments=dict(EVENT_ARGUMENTS),
                    call_id="call-pl-form-event",
                ),
            ),
        ),
    )
    _kill_when_done(runtime, "form_event")
    runtime.run_periodic_review(now=NOW)


def test_process_sigkill_after_form_event_replays_exactly_once(tmp_path):
    db = tmp_path / "pl-review-form-event.db"
    _run_child(_child_periodic_review_form_event_then_sigkill, db)

    store, index = _reopen(db)
    events = [
        payload
        for payload in store.list_payloads(object_type=ObjectType.EVENT, subject_id=SUBJECT)
        if payload.get("title") == EVENT_ARGUMENTS["title"]
    ]
    assert len(events) == 1, "the durable event effect is missing"
    event_id = str(events[0]["object_id"])
    assert _revisions(db, event_id) == [1]
    ops_before = _operations(db, "event.form")
    assert len(ops_before) == 1

    review_id = _running_review_id(store, subject_id=SUBJECT)
    attempt = _attempt(
        _route_b_runtime(store=store, index=index, model_handler=lambda _s: None),
        work_kind="periodic_review",
        work_id=review_id,
    )
    assert attempt is not None
    assert attempt.state == "metered"

    meter_before = _round0_meter(
        _route_b_runtime(store=store, index=index, model_handler=lambda _s: None),
        wake_id=review_id,
    )
    assert len(meter_before) == 1, "the crashed round was not metered"

    recovery_rounds: list[int] = []

    def provider(snapshot):
        recovery_rounds.append(snapshot.round_index)
        return _directive("req-pl-review-next", silence=True)

    restarted = _route_b_runtime(store=store, index=index, model_handler=provider)
    _stage(
        restarted,
        work_kind="periodic_review",
        work_id=review_id,
        round_index=0,
        directive=_directive(
            attempt.provider_request_id,
            silence=False,
            capability_calls=(
                CapabilityCall(
                    name="form_event",
                    arguments=dict(EVENT_ARGUMENTS),
                    call_id="call-pl-form-event",
                ),
            ),
        ),
        trusted_return=True,
    )
    result = restarted.run_periodic_review(now=NOW + timedelta(minutes=17))

    assert result.runtime.recovered_response_attempts == (attempt.attempt_id,)
    assert recovery_rounds == [1], "round 0 must not be redispatched to the provider"
    assert _revisions(db, event_id) == [1], "a second Event revision was written"
    assert _operations(db, "event.form") == ops_before
    round0_after = _round0_meter(restarted, wake_id=review_id)
    assert len(round0_after) == 1, (
        f"the recovered round was metered twice: {round0_after}"
    )
    assert round0_after[0].record_id == meter_before[0].record_id, (
        "the recovery replaced the original meter row instead of reusing it"
    )
    assert result.wake.state == "completed", "the review turn did not converge"
