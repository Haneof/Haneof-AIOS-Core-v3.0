# S2 Post-FIX-002 Parallelism Ruling — 2026-09-24

Status: ACTIVE
Baseline at creation: `main@3d980fadf6beefcdd02ff4367ba834a5b013d871`

## Purpose

CORE-GAP-FIX-002 is independently accepted and integrated. Both remaining RC blockers may now proceed,
but FIX-001 and FIX-003 can still touch `turn_runtime.py`. This ruling keeps development parallel while
preventing semantic overlap.

## CORE-GAP-FIX-001 resumed ownership

Existing PR #145 / branch `core-gap-fix-001-temporal-read-cut-20260924-r2`.

Owns:
- temporal/model-visible read-cut behavior;
- query/search AS_KNOWN cutoff helper;
- `_search_world`;
- `_inspect_world_object`;
- `_world_map_context`;
- active read-cut plumbing;
- only the minimal ordering change inside `run_wake` / `run_periodic_review` needed to establish/pass
  the historical cutoff before resumed model-visible cockpit/snapshot construction.

Must not change:
- FIX-002 background attempt identity/disposition state machine;
- provider retry/reconcile semantics;
- metering/budget semantics;
- Wake/Review completion semantics.

## CORE-GAP-FIX-003 ownership

New branch from then-live main after FIX-002 integration.

Owns:
- ordinary user-turn IN_DOUBT inspection/reconciliation;
- user-turn admission/recovery boundaries;
- `turn_execution.py` and ordinary `run_turn` recovery paths as needed;
- reuse/adaptation of accepted FIX-002 primitives only where semantics are genuinely shared.

Must not change:
- FIX-001 temporal read-cut helpers/semantics;
- background `run_wake` / `run_periodic_review` execution flow;
- background attempt disposition semantics;
- historical Resident evidence.

## Integration rule

Development may run in parallel, but integration is serialized.
Whichever candidate is independently accepted and integrated first establishes the new main.
The second candidate must rebase/merge that live main, rerun targeted + full gates, and receive
independent acceptance on the rebased exact head before PM integration.

If either task needs a symbol or semantic area owned by the other, stop and report to PM.
