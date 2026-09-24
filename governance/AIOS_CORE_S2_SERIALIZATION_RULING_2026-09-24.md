# S2 Serialization Ruling — FIX-002 before resuming FIX-001

Date: 2026-09-24  
Issued by: Core Delivery PM  
Baseline at decision: `main@5ccb51c0bbcc11380887c60e8bfaa5c87f05c110`  
Status: ACTIVE / binding

## Trigger

`CORE-GAP-FIX-001` PR #145 independently reproduced CG-001 and then stopped under the existing
`AIOS_CORE_S2_PARALLELISM_RULING_2026-09-24.md` because full closure requires establishing the
historical read cut before the first resumed background cockpit/snapshot is built.

That ordering point is inside `run_wake` and `run_periodic_review`, which the existing ruling assigns
to `CORE-GAP-FIX-002`.

This is no longer merely same-file/different-region parallel work. Both tasks now need the same
entrypoint functions and their execution-order semantics. The existing ruling explicitly requires
PM serialization when that occurs.

## Decision

1. `CORE-GAP-FIX-002` proceeds first.
   - Current engineering candidate: draft PR #143.
   - Construction base: `5ccb51c0bbcc11380887c60e8bfaa5c87f05c110`.
   - FIX-002 keeps ownership of `run_wake`, `run_periodic_review`, and the background provider-attempt
     durability/recovery state machine until independent acceptance and PM integration.

2. `CORE-GAP-FIX-001` becomes `FROZEN_WIP / BLOCKED_ON_FIX_002_INTEGRATION`.
   - Preserve draft PR #145 and branch `core-gap-fix-001-temporal-read-cut-20260924-r2`.
   - Preserve reproduction-only SHA `a9a089a65414f9ba3a4b3dd6721edc3f05773834`.
   - Preserve stopped WIP head `97a76e3b90db9ec7bf9873e87a9108d4457afc33`.
   - Do not restart from scratch, close, merge, or independently accept #145 in this state.

3. After FIX-002 is independently accepted and integrated:
   - re-fetch live main;
   - rebase/merge #145 onto that exact main;
   - FIX-001 may then make the minimal entrypoint change necessary solely to establish/pass the active
     temporal read cutoff before any resumed C14/Periodic Review model-visible cockpit or snapshot read;
   - it must not alter FIX-002's model-attempt state machine, retry disposition, attempt identity,
     metering semantics, Wake/Review lifecycle, or recovery policy;
   - rerun the CG-001 targeted reproduction/regressions and the full repository gate on the rebased head;
   - a new independent acceptance verdict is required on that exact post-FIX-002 candidate head.

4. `CORE-GAP-FIX-003` remains BLOCKED until FIX-002 is independently accepted and integrated. The
existing dependency is unchanged.

5. `CORE-CI-FIX-001` is orthogonal. PR #144 is engineering `REVIEW_READY`; it may undergo its own
independent acceptance in parallel. It does not change the FIX-002 -> FIX-001 serialization order.

## Boundary for resumed FIX-001

The post-FIX-002 exception to the old symbol ownership is narrow:

Allowed in `run_wake` / `run_periodic_review`:
- establish or pass the historical active read cutoff before model-visible cockpit/snapshot construction;
- restore/clear that cutoff with correct exception-safe scope if needed.

Not allowed:
- provider-attempt admission/disposition changes;
- retry/reconcile policy changes;
- metering or budget state-machine changes;
- Wake/Review completion semantics changes;
- unrelated refactor/reformat.

If the resumed FIX-001 requires any of those, stop and return to PM.

## Release impact

No Resident execution is authorized. No historical evidence may be patched. RC freeze remains blocked
until all gap fixes, headless/recovery/scale, and CI-fix acceptance/integration requirements are closed.
