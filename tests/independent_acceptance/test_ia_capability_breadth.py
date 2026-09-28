"""IA rev3 — §17 capability-family breadth of the R5-C exactly-once replay contract.

rev2 -> rev3 changes harness mechanics only. The frozen expected outcome is UNCHANGED
from rev1:

  for every actually-reachable side-effecting capability family, a crash AFTER the
  capability's World effect is durable but BEFORE outer completion must converge on
  fresh recovery to exactly one durable effect, and the replayed capability must
  report ok=True.

rev3 identifies each capability's own durable operation by the operations-table delta
across its invocation, instead of guessing object types and payload predicates.

The candidate repairs exactly one family (execution.task.create). The frozen R5
contract is capability-family wide, so this probe sweeps the whole registry.
"""
from __future__ import annotations

import os
import tempfile

import pytest

from aios_core.contracts.time import TemporalExtent
from aios_core.runtime.capabilities import CapabilityCall

from ia_harness import (
    ANCHOR, NOW, ProcessDeath, cap, directive, idem_rows, new_runtime, op_rows,
    q, seed_anchor,
)

SESSION = "ia-cap-session"


def _work_id(rt):
    return rt.turn_executions.execution_id_for(
        subject_id=rt.subject_id, session_id=SESSION, turn_index=1)


def _ops(db):
    return {r["idempotency_key"]: (r["operation_id"], r["operation_name"],
                                   r["expected_world_revision"], r["result_world_revision"])
            for r in op_rows(db)}


def _crash_after_effect(tmp_path, plan, target_call_id):
    """Let the target capability's World effect commit, then die before outer ACK."""
    db = tmp_path / "w.db"
    served = []
    captured = {}

    def provider(snapshot):
        served.append(snapshot.round_index)
        item = plan.get(snapshot.round_index)
        return directive(snapshot.round_index) if item is None else directive(
            snapshot.round_index, call=item)

    initial = new_runtime(db, provider)
    seed_anchor(initial.store)
    initial.index.catch_up()
    work_id = _work_id(initial)
    real_invoke = initial.registry.invoke

    def boundary(c):
        if c.call_id == target_call_id:
            before = _ops(db)
            res = real_invoke(c)          # durable World effect lands here
            assert res.ok, f"PRE-CRASH {c.name} FAILED: {res.error_code} {res.error_message}"
            after = _ops(db)
            captured["new_ops"] = {k: v for k, v in after.items() if k not in before}
            assert captured["new_ops"], (
                f"{c.name} reported success but produced no durable operation")
            raise ProcessDeath(f"crash after {c.name} effect")
        return real_invoke(c)

    initial.registry.invoke = boundary
    with pytest.raises(ProcessDeath):
        initial.run_turn(session_id=SESSION, turn_index=1,
                         user_input="IA capability breadth", occurred_at=NOW)
    return db, initial, work_id, served, captured["new_ops"]


def _recover(db, served):
    fresh_rounds = []

    def continuation(snapshot):
        assert snapshot.round_index == len(served), (
            f"REDISPATCH: recovered round reached provider "
            f"(round={snapshot.round_index}, expected first new round={len(served)})")
        fresh_rounds.append(snapshot.round_index)
        return directive(snapshot.round_index)

    fresh = new_runtime(db, continuation)
    result = fresh.run_turn(session_id=SESSION, turn_index=1,
                            user_input="IA capability breadth", occurred_at=NOW)
    return fresh, result, fresh_rounds


def _hist(result, call_id):
    for item in result.runtime.capability_history:
        if item.call_id == call_id:
            return item
    return None


def _ref():
    return {"object_id": ANCHOR, "revision": 1}


# name -> (capability, argument builder)
FAMILIES = {
    "commit_claim": ("commit_claim", lambda r: dict(
        content=f"IA claim {r}", evidence_refs=[_ref()], confidence=0.8,
        dimension="dim:ia")),
    "commit_ai_world_claim": ("commit_ai_world_claim", lambda r: dict(
        domain="intent", statement=f"IA world claim {r}", evidence_refs=[_ref()],
        confidence=0.7)),
    "propose_entity": ("propose_entity", lambda r: dict(
        entity_key=f"entity:ia{r}", entity_kind="person",
        canonical_name=f"IA Entity {r}", evidence_refs=[_ref()])),
    "propose_goal": ("propose_goal", lambda r: dict(
        source_type="ai_self", title=f"IA goal {r}", description="IA breadth goal",
        evidence_refs=[_ref()], confidence=0.7)),
    "propose_dimension": ("propose_dimension", lambda r: dict(
        dimension_key=f"dim:iax{r}", name=f"IA dim {r}",
        description="IA breadth dimension", data_shape="scalar",
        evidence_refs=[_ref()], why_existing_dimensions_are_insufficient="IA probe",
        continuity_rationale="IA probe", user_value_rationale="IA probe",
        maintenance_cost_rationale="IA probe", confidence=0.6,
        update_method="ia", expected_value="ia")),
    "propose_cognitive_policy": ("propose_cognitive_policy", lambda r: dict(
        policy_id=f"ia.policy.{r}", scope="ia_scope", default_value="a",
        current_value="b", reason="IA probe", evidence_refs=[_ref()],
        evaluation_window="30d")),
    "create_task": ("create_task", lambda r: dict(
        title=f"IA task {r}", task_type="follow_up", reason_refs=[_ref()],
        initial_state="draft")),
    "form_event": ("form_event", lambda r: dict(
        title=f"IA event {r}", interpretation="IA breadth event",
        event_time=TemporalExtent.point(NOW).model_dump(mode="json"),
        evidence_refs=[_ref()], confidence=0.7)),
    "create_attention_watch": ("create_attention_watch", lambda r: dict(
        title=f"IA watch {r}", dimensions=["dim:ia"], reason_refs=[_ref()],
        source_kind="conversation", modality="text", priority=40,
        cooldown_seconds=60)),
}


def test_ia_registry_side_effecting_inventory():
    """Guard: the sweep must track the real registry, not a hard-coded list."""
    rt = new_runtime(os.path.join(tempfile.mkdtemp(), "w.db"), lambda s: None)
    side = sorted(c["name"] for c in rt.registry.catalog() if c["side_effecting"])
    assert len(side) >= 20, f"registry shrank to {len(side)}: {side}"
    for required in ("create_attention_watch", "commit_claim", "propose_entity",
                     "upsert_relation", "propose_goal", "create_task",
                     "transition_task", "commit_operation_experience",
                     "revise_claim", "retract_claim", "form_event",
                     "transition_event", "propose_dimension",
                     "propose_cognitive_policy", "commit_ai_world_claim"):
        assert required in side, f"{required} not side-effecting"


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_ia_capability_family_r5c_exactly_once(tmp_path, family):
    cname, mkargs = FAMILIES[family]
    call_id = f"ia-{family}-0"
    plan = {0: cap(cname, call_id, mkargs(0))}
    db, initial, work_id, served, effect_ops = _crash_after_effect(
        tmp_path, plan, call_id)
    op_names = {v[1] for v in effect_ops.values()}

    ops_before_recovery = _ops(db)
    idem_before = {r["idempotency_key"]: (r["operation_id"], r["world_revision"])
                   for r in idem_rows(db)}

    fresh, result, fresh_rounds = _recover(db, served)
    assert fresh_rounds == [1], f"[{family}] unexpected new provider rounds {fresh_rounds}"

    h = _hist(result, call_id)
    assert h is not None, f"[{family}] recovered round did not replay the capability"
    assert h.ok, (f"[{family}] R5-C REPLAY FAILED: {h.name} "
                  f"{h.error_code} / {h.error_message}")

    ops_after = _ops(db)
    # 1. every durable identity that existed before recovery is byte-identical after
    for key, identity in ops_before_recovery.items():
        assert ops_after.get(key) == identity, (
            f"[{family}] DURABLE IDENTITY CHANGED for {key}: "
            f"{identity} -> {ops_after.get(key)}")
    # 2. the capability's own operation family gained no second row
    for name in op_names:
        rows = [k for k, v in ops_after.items() if v[1] == name]
        assert len(rows) == len({k for k, v in ops_before_recovery.items() if v[1] == name}), (
            f"[{family}] DUPLICATE OPERATION for {name}: {rows}")
    # 3. every pre-existing idempotency record is unchanged
    idem_after = {r["idempotency_key"]: (r["operation_id"], r["world_revision"])
                  for r in idem_rows(db)}
    for key, identity in idem_before.items():
        assert idem_after.get(key) == identity, (
            f"[{family}] IDEMPOTENCY IDENTITY CHANGED for {key}: "
            f"{identity} -> {idem_after.get(key)}")
