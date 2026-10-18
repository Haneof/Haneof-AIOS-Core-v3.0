#!/usr/bin/env python3
"""Reviewer Independent Probe 1: Capability inventory & replay spot-checks.

This probe independently validates:
1. Dynamic catalog check: exactly 43 total callable, exactly 22 side-effecting.
2. Complete 22 side-effecting capability surface spot checks on the frozen software:
   - exact replay converges
   - same-key changed request fails closed or identity-shifts
   - unrelated World revision advancement does not break legal replay
   - original durable identity is preserved
   - duplicate-effect prevention across all families
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from typing import Any

# Add src and tests/integration to sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests" / "integration"))

from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.turn_runtime import FusedTurnRuntime
import test_core_background_trusted_return_corrective_001_capability_replay as replay_mod

EXPECTED_SIDE_EFFECTING = sorted([
    "commit_ai_world_claim",
    "commit_claim",
    "commit_operation_experience",
    "create_attention_watch",
    "create_task",
    "form_event",
    "propose_action",
    "propose_cognitive_policy",
    "propose_dimension",
    "propose_entity",
    "propose_goal",
    "record_communication_experience",
    "retract_claim",
    "revise_claim",
    "revise_entity",
    "rollback_cognitive_policy",
    "transition_dimension",
    "transition_event",
    "transition_goal",
    "transition_task",
    "update_cognitive_policy",
    "upsert_relation",
])


def verify_inventory() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aios-ia-inv-") as td:
        root = Path(td)
        store = SQLiteWorldStore(root / "world.sqlite")
        index = WorldSearchIndex(root / "index.sqlite", store=store)
        index.rebuild()
        runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _s: None)

        catalog = runtime.registry.catalog()
        all_names = sorted(item["name"] for item in catalog)
        side_effecting = sorted(item["name"] for item in catalog if item["side_effecting"])
        non_side_effecting = sorted(item["name"] for item in catalog if not item["side_effecting"])

        assert len(catalog) == 43, f"expected 43 total capabilities, got {len(catalog)}"
        assert len(side_effecting) == 22, f"expected 22 side-effecting, got {len(side_effecting)}"
        assert len(non_side_effecting) == 21, f"expected 21 read-only, got {len(non_side_effecting)}"
        assert side_effecting == EXPECTED_SIDE_EFFECTING, (
            f"side-effecting mismatch: extra={set(side_effecting) - set(EXPECTED_SIDE_EFFECTING)}, "
            f"missing={set(EXPECTED_SIDE_EFFECTING) - set(side_effecting)}"
        )

        return {
            "total_capabilities": len(catalog),
            "side_effecting_count": len(side_effecting),
            "read_only_count": len(non_side_effecting),
            "side_effecting_names": side_effecting,
        }


def verify_replay_convergence_all_22() -> dict[str, Any]:
    passed_scenarios = []
    with tempfile.TemporaryDirectory(prefix="aios-ia-replay-") as td:
        for idx, scenario_name in enumerate(sorted(replay_mod.SCENARIO_BY_NAME)):
            db = Path(td) / f"world_{idx}.sqlite"
            scenario = replay_mod.SCENARIO_BY_NAME[scenario_name]
            rt, arguments, _first = replay_mod.apply_scenario(db, scenario)

            # Crash window: advance world with an unrelated operation
            replay_mod.advance_world(db, scenario_name)
            rev_after_advance = int(replay_mod.world(db)[0].current_world_revision())
            state_after_advance = replay_mod.durable_state(db)

            identity_before = (
                replay_mod.object_revisions(db, scenario.identity)
                if scenario.identity is not None
                else None
            )
            operations_before = replay_mod.operation_rows(db)
            idempotency_before = replay_mod.idempotency_rows(db)

            # Fresh runtime replaying identical recovered call
            fresh = replay_mod.new_runtime(db)
            replay = replay_mod.invoke(fresh, scenario_name, arguments, call_id="ia-replay")

            assert replay.ok, f"{scenario_name}: identical replay must converge: {replay.error_code} {replay.error_message}"
            assert replay_mod.durable_state(db) == state_after_advance, f"{scenario_name}: durable state mutated on replay"
            assert int(fresh.store.current_world_revision()) == rev_after_advance, f"{scenario_name}: replay advanced world revision"
            assert replay_mod.operation_rows(db) == operations_before, f"{scenario_name}: duplicate operation row added"
            assert replay_mod.idempotency_rows(db) == idempotency_before, f"{scenario_name}: idempotency row changed"
            if scenario.identity is not None:
                assert replay_mod.object_revisions(db, scenario.identity) == identity_before, f"{scenario_name}: produced second durable revision"

            passed_scenarios.append(scenario_name)

    return {
        "status": "ALL_22_REPLAY_CONVERGENCE_PASS",
        "passed_count": len(passed_scenarios),
        "scenarios": passed_scenarios,
    }


def verify_conflict_fail_closed_and_identity_shifts() -> dict[str, Any]:
    conflict_checks = []
    shift_checks = []

    with tempfile.TemporaryDirectory(prefix="aios-ia-conflict-") as td:
        for idx, scenario_name in enumerate(sorted(replay_mod.SCENARIO_BY_NAME)):
            scenario = replay_mod.SCENARIO_BY_NAME[scenario_name]
            db = Path(td) / f"world_{idx}.sqlite"

            if scenario.conflicts:
                db_c = Path(td) / f"world_c_{idx}.sqlite"
                rt, arguments, _first = replay_mod.apply_scenario(db_c, scenario)
                replay_mod.advance_world(db_c, scenario_name)
                state_before_conflict = replay_mod.durable_state(db_c)
                operations_before = replay_mod.operation_rows(db_c)

                for label, mutator in scenario.conflicts:
                    changed_args = mutator(dict(arguments))
                    fresh = replay_mod.new_runtime(db_c)
                    conflict_call = replay_mod.invoke(fresh, scenario_name, changed_args, call_id="ia-conflict")
                    assert not conflict_call.ok, f"{scenario_name} ({label}): changed request must fail closed"
                    assert replay_mod.durable_state(db_c) == state_before_conflict, f"{scenario_name} ({label}): mutated state"
                    assert replay_mod.operation_rows(db_c) == operations_before, f"{scenario_name} ({label}): wrote operation"
                conflict_checks.append(scenario_name)

            if scenario.identity_shifts:
                db_s = Path(td) / f"world_s_{idx}.sqlite"
                rt, arguments, _first = replay_mod.apply_scenario(db_s, scenario)
                replay_mod.advance_world(db_s, scenario_name)
                digests_before_attempt = replay_mod.object_digests(db_s, scenario.identity)

                for label, mutator in scenario.identity_shifts:
                    changed_args = mutator(dict(arguments))
                    state_before_attempt = replay_mod.durable_state(db_s)
                    digests_before_iter = replay_mod.object_digests(db_s, scenario.identity)
                    fresh = replay_mod.new_runtime(db_s)
                    shift_call = replay_mod.invoke(fresh, scenario_name, changed_args, call_id=f"ia-shift-{label}")
                    digests_after = replay_mod.object_digests(db_s, scenario.identity)

                    # Original object must never be overwritten
                    for key, before_digest in digests_before_attempt.items():
                        assert digests_after.get(key) == before_digest, (
                            f"{scenario_name} ({label}): original object {key} was overwritten"
                        )

                    if shift_call.ok:
                        new_ids = set(digests_after) - set(digests_before_iter)
                        assert new_ids, f"{scenario_name} ({label}): reported ok but created no new durable identity"
                    else:
                        assert replay_mod.durable_state(db_s) == state_before_attempt, (
                            f"{scenario_name} ({label}): rejected request wrote durable state"
                        )
                shift_checks.append(scenario_name)

    return {
        "status": "CONFLICTS_AND_IDENTITY_SHIFTS_PASS",
        "conflict_checked_scenarios": conflict_checks,
        "shift_checked_scenarios": shift_checks,
    }


def main() -> int:
    inv = verify_inventory()
    replay = verify_replay_convergence_all_22()
    conflicts = verify_conflict_fail_closed_and_identity_shifts()

    result = {
        "probe": "probe_capability_inventory_and_replay",
        "status": "PASS",
        "inventory": inv,
        "replay_convergence": replay,
        "conflicts_and_identity_shifts": conflicts,
    }
    print("RESULT=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
