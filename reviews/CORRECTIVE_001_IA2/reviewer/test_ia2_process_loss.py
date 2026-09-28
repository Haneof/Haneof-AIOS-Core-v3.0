"""INDEPENDENT ACCEPTANCE reviewer probes -- IA2 part 3: REAL process loss.

Each probe forks a child that:
  1. dispatches a REAL model round through the real runtime entry point;
  2. lets the real capability handler commit its durable side effect;
  3. ``os.kill(os.getpid(), SIGKILL)`` -- a real hard process death, before the
     outer completion (metering / turn completion) becomes durable.

The parent then asserts the child really died to SIGKILL, reopens the SAME World
in a brand new runtime, replays the identical authenticated recovered directive,
and asserts exactly-once semantics.

Reviewer-chosen families, deliberately different from the author's three:
  * wake            + upsert_relation     (non-create_task, revision-advancing)
  * user_turn       + revise_entity       (revision-advancing mutation)
  * periodic_review + propose_dimension   (a reviewer-proven historical RED family)
"""
from __future__ import annotations

import multiprocessing
import os
import signal as posix_signal
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import ObjectType, SourceClass, WakeSource
from aios_core.contracts.models import Observation
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import (
    ModelCallProvenance, ModelDirective, ModelUsage,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake import WakeSignalRequest

PT = datetime(2026, 9, 28, 15, tzinfo=timezone.utc)
PROVIDER = "ia2-pl-provider"
MODEL = "ia2-pl-model"
SUBJECT = "user_1"
ANCHOR_ID = "obs_ia2_pl_anchor"
ANCHOR = {"object_id": ANCHOR_ID, "revision": 1}


# --------------------------------------------------------------------------
def _reopen(db):
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def _runtime(db):
    store, index = _reopen(db)
    return FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)


def _directive(request_id, capability_calls):
    return ModelDirective(
        response=None, silence=False, capability_calls=tuple(capability_calls),
        usage=ModelUsage(input_tokens=4, output_tokens=2, total_tokens=6,
                         provider=PROVIDER, model=MODEL, request_id=request_id),
        provenance=ModelCallProvenance(provider=PROVIDER, model=MODEL,
                                       request_id=request_id))


def _seed_anchor(runtime):
    moment = PT - timedelta(hours=2)
    runtime.store.commit(
        [Observation(
            object_id=ANCHOR_ID, subject_id=SUBJECT,
            occurred=TemporalExtent.point(moment), learned_at=moment,
            recorded_at=moment, created_by="ia2:pl-seed",
            source_kind="conversation", modality="text",
            value="reviewer process-loss anchor",
            metadata={"dimension": "dim:ia2pl"})],
        OperationRequest(
            operation_name="ia2.pl_seed_anchor",
            expected_world_revision=int(runtime.store.current_world_revision()),
            reason="seed capability evidence",
            idempotency_key="ia2-pl-seed-anchor", source_class=SourceClass.USER))
    runtime.index.catch_up()


def _seed_review_fact(store):
    moment = PT - timedelta(hours=1)
    store.commit(
        [Observation(
            object_id="obs_ia2_pl_review_fact", subject_id=SUBJECT,
            occurred=TemporalExtent.point(moment), learned_at=moment,
            recorded_at=moment, created_by="ia2:pl-review-seed",
            source_kind="conversation", modality="text",
            value="reviewer periodic review anchor fact",
            metadata={"dimension": "dim:ia2pl"})],
        OperationRequest(
            operation_name="ia2.pl_seed_review_fact",
            expected_world_revision=int(store.current_world_revision()),
            reason="seed periodic review fact",
            idempotency_key="ia2-pl-seed-review-fact",
            source_class=SourceClass.USER))


def _invoke(runtime, name, arguments, *, call_id):
    runtime._active_turn_time = PT
    try:
        result = runtime.registry.invoke(
            CapabilityCall(name=name, call_id=call_id, arguments=dict(arguments)))
    finally:
        runtime._active_turn_time = None
    assert result.ok, f"seed {name} failed: {result.error_code} {result.error_message}"
    return result.data


def _bind_scripted(runtime, directive):
    def scripted(snapshot):
        if snapshot.round_index == 0:
            return directive
        raise AssertionError("process must die during capability application")

    runtime.model_handler = scripted
    runtime.cognitive_runtime.model_handler = scripted


def _kill_when_done(runtime, capability):
    """Let the real handler commit durably, then die before outer completion."""
    real_handler = getattr(runtime, f"_{capability}")

    def die_after_durable_effect(**kwargs):
        real_handler(**kwargs)
        os.kill(os.getpid(), posix_signal.SIGKILL)

    spec = runtime.registry.get_spec(capability)
    runtime.registry.unregister(capability)
    runtime.registry.register(spec, die_after_durable_effect)


def _new_wake(runtime, key):
    return runtime.wake_bus.emit(WakeSignalRequest(
        wake_source=WakeSource.SAFETY, rule_id=f"ia2pl.{key}",
        observed_at=PT, dedupe_key=f"ia2pl:{key}"))


def _wake_ref(signal):
    return ObjectRef(object_id=signal.wake_id, revision=signal.revision)


TURN = dict(session_id="session-ia2-pl", turn_index=1,
            user_input="reviewer process-loss user turn", occurred_at=PT)


# --------------------------------------------------------------------------
# durable observation helpers
# --------------------------------------------------------------------------
def _conn(db):
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    return c


def _revisions(db, object_type):
    with _conn(db) as c:
        return sorted((str(r[0]), int(r[1])) for r in c.execute(
            "SELECT object_id, revision FROM object_revisions WHERE object_type=?",
            (object_type.value,)))


def _ops(db):
    with _conn(db) as c:
        return sorted(tuple(r) for r in c.execute(
            "SELECT operation_id, operation_name, idempotency_key FROM operations"))


def _assert_no_duplicate_operation(db, ops_before, *, label):
    """Recovery may legitimately add its OWN outer-completion operations
    (assistant output, wake completion, review completion).  What it must never
    do is add a SECOND operation for the recovered capability.
    """
    after = _ops(db)
    before_keys = {row[2] for row in ops_before}
    added = [row for row in after if row not in set(ops_before)]
    reused = [row for row in added if row[2] in before_keys]
    assert not reused, (
        f"{label}: recovery reused an existing idempotency key for a second "
        f"operation: {reused}")
    missing = [row for row in ops_before if row not in set(after)]
    assert not missing, f"{label}: recovery lost or mutated operation rows: {missing}"
    return added


def _meters(db, round_index=None):
    with _conn(db) as c:
        tables = [r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%meter%'")]
        rows = []
        for t in tables:
            rows.extend(tuple(r) for r in c.execute(f"SELECT * FROM {t}"))
        return tables, rows


# --------------------------------------------------------------------------
# WAKE + upsert_relation
# --------------------------------------------------------------------------
def _child_wake_upsert_relation(db_path):
    runtime = _runtime(db_path)
    _seed_anchor(runtime)
    left = _invoke(runtime, "propose_entity",
                   dict(entity_key="entity:ia2pl-left", entity_kind="concept",
                        evidence_refs=[ANCHOR], canonical_name="PL Left"),
                   call_id="seed-left")
    right = _invoke(runtime, "propose_entity",
                    dict(entity_key="entity:ia2pl-right", entity_kind="concept",
                         evidence_refs=[ANCHOR], canonical_name="PL Right"),
                    call_id="seed-right")
    args = dict(
        left_ref={"object_id": left["entity_id"], "revision": 1},
        relation_type="related_to",
        right_ref={"object_id": right["entity_id"], "revision": 1},
        evidence_refs=[ANCHOR], confidence=0.5, reason="reviewer process loss")
    _bind_scripted(runtime, _directive("req-ia2pl-wake-relation", (
        CapabilityCall(name="upsert_relation", arguments=args,
                       call_id="call-ia2pl-relation"),)))
    _kill_when_done(runtime, "upsert_relation")
    signal = _new_wake(runtime, "relation")
    runtime.run_wake(wake_ref=_wake_ref(signal), now=PT)
    # record the wake id for the parent
    with _conn(db_path) as c:
        pass


def test_process_loss_wake_upsert_relation_replays_exactly_once(tmp_path):
    db = tmp_path / "pl-wake-relation.db"
    ctx = multiprocessing.get_context("fork")
    proc = ctx.Process(target=_child_wake_upsert_relation, args=(str(db),))
    proc.start()
    proc.join(120)
    assert proc.exitcode == -posix_signal.SIGKILL, (
        f"child must die to a real SIGKILL, exitcode={proc.exitcode}")

    relation_before = _revisions(db, ObjectType.RELATION)
    assert relation_before, "the child never made the relation durable"
    ops_before = _ops(db)

    restarted = _runtime(db)
    wake = [p for p in restarted.store.list_payloads(
        object_type=ObjectType.WAKE, subject_id=SUBJECT)][-1]
    wake_ref = ObjectRef(object_id=str(wake["object_id"]),
                         revision=int(wake["revision"]))

    dispatches = []

    def counting(snapshot):
        dispatches.append(snapshot.round_index)
        return ModelDirective(
            response=None, silence=True, capability_calls=(),
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2,
                             provider=PROVIDER, model=MODEL,
                             request_id=f"req-recover-{snapshot.round_index}"),
            provenance=ModelCallProvenance(provider=PROVIDER, model=MODEL,
                                           request_id=f"req-recover-{snapshot.round_index}"))

    restarted.model_handler = counting
    restarted.cognitive_runtime.model_handler = counting
    restarted.run_wake(wake_ref=wake_ref, now=PT)

    assert _revisions(db, ObjectType.RELATION) == relation_before, (
        "recovery produced a SECOND durable relation revision")
    added = _assert_no_duplicate_operation(db, ops_before, label="review/dimension")
    assert not any("propose_dimension" in row[1] or "dimension-proposal" in row[2]
                   for row in added), (
        f"recovery added a SECOND propose_dimension operation: {added}")
    tables, rows = _meters(db)
    assert tables, "no metering table found"


# --------------------------------------------------------------------------
# USER_TURN + revise_entity
# --------------------------------------------------------------------------
def _child_user_turn_revise_entity(db_path):
    runtime = _runtime(db_path)
    _seed_anchor(runtime)
    entity = _invoke(runtime, "propose_entity",
                     dict(entity_key="entity:ia2pl-revise", entity_kind="concept",
                          evidence_refs=[ANCHOR], canonical_name="PL Revise Target"),
                     call_id="seed-revise-target")
    args = dict(entity_ref={"object_id": entity["entity_id"], "revision": 1},
                reason="reviewer process-loss revision",
                evidence_refs=[ANCHOR], canonical_name="Revised By Recovery")
    _bind_scripted(runtime, _directive("req-ia2pl-turn-revise", (
        CapabilityCall(name="revise_entity", arguments=args,
                       call_id="call-ia2pl-revise"),)))
    _kill_when_done(runtime, "revise_entity")
    runtime.run_turn(**TURN)


def test_process_loss_user_turn_revise_entity_replays_exactly_once(tmp_path):
    db = tmp_path / "pl-turn-revise.db"
    ctx = multiprocessing.get_context("fork")
    proc = ctx.Process(target=_child_user_turn_revise_entity, args=(str(db),))
    proc.start()
    proc.join(120)
    assert proc.exitcode == -posix_signal.SIGKILL, (
        f"child must die to a real SIGKILL, exitcode={proc.exitcode}")

    entity_before = _revisions(db, ObjectType.ENTITY)
    assert entity_before, "the child never made the entity revision durable"
    ops_before = _ops(db)

    restarted = _runtime(db)
    dispatches = []

    def counting(snapshot):
        dispatches.append(snapshot.round_index)
        return ModelDirective(
            response=None, silence=True, capability_calls=(),
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2,
                             provider=PROVIDER, model=MODEL,
                             request_id=f"req-recover-{snapshot.round_index}"),
            provenance=ModelCallProvenance(provider=PROVIDER, model=MODEL,
                                           request_id=f"req-recover-{snapshot.round_index}"))

    restarted.model_handler = counting
    restarted.cognitive_runtime.model_handler = counting
    restarted.run_turn(**TURN)

    assert _revisions(db, ObjectType.ENTITY) == entity_before, (
        "recovery produced a SECOND durable entity revision")
    added = _assert_no_duplicate_operation(db, ops_before, label="turn/revise")
    assert not any("revise_entity" in row[1] or "entity-revise" in row[2]
                   for row in added), (
        f"recovery added a SECOND revise_entity operation: {added}")


# --------------------------------------------------------------------------
# PERIODIC REVIEW + propose_dimension
# --------------------------------------------------------------------------
def _child_periodic_review_propose_dimension(db_path):
    runtime = _runtime(db_path)
    _seed_anchor(runtime)
    _seed_review_fact(runtime.store)
    runtime.index.catch_up()
    args = dict(dimension_key="dim:ia2pl-processloss", name="PL Axis",
                description="reviewer process-loss axis", data_shape="scalar",
                evidence_refs=[ANCHOR],
                why_existing_dimensions_are_insufficient="none",
                continuity_rationale="c", user_value_rationale="u",
                maintenance_cost_rationale="m", confidence=0.5)
    _bind_scripted(runtime, _directive("req-ia2pl-review-dimension", (
        CapabilityCall(name="propose_dimension", arguments=args,
                       call_id="call-ia2pl-dimension"),)))
    _kill_when_done(runtime, "propose_dimension")
    runtime.run_periodic_review(now=PT)


def test_process_loss_periodic_review_propose_dimension_replays_exactly_once(tmp_path):
    db = tmp_path / "pl-review-dimension.db"
    ctx = multiprocessing.get_context("fork")
    proc = ctx.Process(target=_child_periodic_review_propose_dimension,
                       args=(str(db),))
    proc.start()
    proc.join(120)
    assert proc.exitcode == -posix_signal.SIGKILL, (
        f"child must die to a real SIGKILL, exitcode={proc.exitcode}")

    dim_before = _revisions(db, ObjectType.DIMENSION_DEFINITION)
    assert dim_before, "the child never made the dimension durable"
    ops_before = _ops(db)

    restarted = _runtime(db)
    dispatches = []

    def counting(snapshot):
        dispatches.append(snapshot.round_index)
        return ModelDirective(
            response=None, silence=True, capability_calls=(),
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2,
                             provider=PROVIDER, model=MODEL,
                             request_id=f"req-recover-{snapshot.round_index}"),
            provenance=ModelCallProvenance(provider=PROVIDER, model=MODEL,
                                           request_id=f"req-recover-{snapshot.round_index}"))

    restarted.model_handler = counting
    restarted.cognitive_runtime.model_handler = counting
    restarted.run_periodic_review(now=PT + timedelta(minutes=21))

    assert _revisions(db, ObjectType.DIMENSION_DEFINITION) == dim_before, (
        "recovery produced a SECOND durable dimension revision")
    added = _assert_no_duplicate_operation(db, ops_before, label="review/dimension")
    assert not any("propose_dimension" in row[1] or "dimension-proposal" in row[2]
                   for row in added), (
        f"recovery added a SECOND propose_dimension operation: {added}")
