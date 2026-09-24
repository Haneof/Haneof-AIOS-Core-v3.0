# CORE-GAP-AUDIT-001 PM Acceptance and S2 Gap Dispatch — 2026-09-24

Status: ACTIVE
PM acceptance baseline: main@bc4bf735e15c5c0787fdc533fe3f10d0e17fdac3
Accepted audit: PR #132
Audit exact head: 1700a3feab58959bba95eb3420625a8f32aef2fc
Audit report: reviews/CORE_GAP_AUDIT_001_2026-09-24.md

## PM decision

The independent audit is accepted as the authoritative current-Core gap disposition.

Accepted RC blockers:
1. CG-001 RUNTIME_TEMPORAL_READ_CUT -> CORE-GAP-FIX-001
2. CG-002 BACKGROUND_MODEL_EXECUTION_IN_DOUBT -> CORE-GAP-FIX-002
3. CG-003 USER_TURN_IN_DOUBT_RECOVERY -> CORE-GAP-FIX-003

The 14 ALREADY_FIXED findings are not reopened. The 7 NOT_REPRODUCED findings are not converted into engineering tasks. The 6 OUT_OF_SCOPE findings remain in their assigned later phases.

## Scheduling

- CORE-GAP-FIX-001 = READY / NOT_STARTED.
- CORE-GAP-FIX-002 = READY / NOT_STARTED.
- CORE-GAP-FIX-003 = BLOCKED on independent acceptance/integration of CORE-GAP-FIX-002. Reason: both touch model-execution/recovery boundaries and turn_runtime; sequencing avoids duplicate execution-state machinery and conflicting semantics.
- CORE-OPERATOR-001 = DONE (see the dispatch update below).
- CORE-HEADLESS-001 remains BLOCKED until operator acceptance plus all RC-blocking gap fixes are independently accepted and integrated.
- No Resident A/B/C is authorized before CORE-RC-FREEZE-001.

Each fix uses a distinct engineer window. Each candidate requires a different independent acceptance reviewer. Engineering authors may only declare REVIEW_READY, never DONE.

---

## Dispatch update — 2026-09-24, after CORE-OPERATOR-001 integration

New dispatch baseline: live `main` at or after `e72a63874ed2c28798b00cec51f191caf1594a00`. Each window must re-fetch live main and must not pin this SHA as a permanent construction base.

### Closed since this dispatch was written

- `CORE-OPERATOR-001 = DONE`. Independent acceptance PR #135 (`ACCEPTANCE_PASS`, 0 blockers) → PM integration of PR #131 exact head `0e1d69eebc801278f93ccc1941b8f066a4ea09ef` → merge `e72a63874ed2c28798b00cec51f191caf1594a00`. Receipt: `governance/CORE_OPERATOR_001_INTEGRATION_RECEIPT_2026-09-24.md`.
- The operator/preflight surface (`tools/c15_preflight/**`, `tests/preflight/**`, `.github/workflows/c15-operator-preflight.yml`) is now on main and is the single operator bridge. Do not create a second bridge and do not re-port PR #125 assets again.
- PR #130 = SUPERSEDED BY #131; left OPEN, must not be merged.

### Effect on the two READY fixes

- Integration was Core ZERO DIFF, so neither `CORE-GAP-FIX-001` nor `CORE-GAP-FIX-002` needs to re-baseline any Core semantics because of it.
- New surface now present on main that both engineers must respect:
  - `tools/c15_preflight/**` and `tests/preflight/**` are **out of write scope** for both gap fixes. A gap fix must not edit operator tooling to make a Core regression pass.
  - `c15-operator-preflight` now triggers on PRs touching those paths. A Core-only fix will not trigger it; the repository full regression gate still applies.
  - If a Core fix legitimately breaks an operator-surface test, stop and report the conflict to the PM instead of editing the operator surface inside the fix PR.

### Write-scope separation for the two parallel windows

To keep the two active windows conflict-free:

- `CORE-GAP-FIX-001` (CG-001, temporal read cut) owns the model-visible read-cut surface: query/search read paths, exact-object reads and the time-pinned execution cut.
- `CORE-GAP-FIX-002` (CG-002, background model execution IN_DOUBT) owns the background execution/outcome-durability surface.
- **Verified 2026-09-24: both tasks do in fact write `src/aios_core/runtime/turn_runtime.py`.** Parallel work is same-file / different-region, not path-disjoint. The binding conditions (symbol-level ownership, no drive-by refactors, serialised integration, mandatory re-verification of the second candidate on its rebased head) are in `governance/AIOS_CORE_S2_PARALLELISM_RULING_2026-09-24.md`.
- If a window needs to modify a symbol owned by the other task, it stops and reports to the PM; the PM serialises the two tasks rather than letting two windows edit the same region.
- Neither window may modify: `governance/**`, `reviews/**`, `tools/c15_preflight/**`, `tests/preflight/**`, historical evidence, fixtures, or any private World.
- Governance status writeback for a fix is performed by the PM at integration, not by the engineering author.

### Standing acceptance rule for these two tasks

Engineering author declares `REVIEW_READY` only. A different independent acceptance window must, at minimum:

1. re-derive the before-fix reproduction at the candidate's own reproduction commit;
2. verify the fix closes it at the exact candidate head;
3. verify scope, Core impact and that no historical evidence/fixture is touched;
4. state an explicit `ACCEPTANCE_PASS` / `ACCEPTANCE_FAIL` verdict with blocker count.

PM integration additionally re-verifies pins and CI from the API and re-runs the decisive evidence locally before merging, as recorded for `CORE-OPERATOR-001`.


---

## Dispatch update — 2026-09-24, S2 serialization triggered by PR #145

Binding successor ruling: `governance/AIOS_CORE_S2_SERIALIZATION_RULING_2026-09-24.md`.

PR #145 established that CG-001 cannot be fully closed only inside the previously assigned read-path
symbols: resumed C14/Periodic Review builds model-visible cockpit state before the historical T1 cut is
established, so the minimal correct fix must touch `run_wake` / `run_periodic_review`.

Per the original parallelism ruling's stop-and-report clause, development is now serialized:

1. `CORE-GAP-FIX-002` continues first in draft PR #143 and owns the background entrypoints/state machine.
2. `CORE-GAP-FIX-001` is preserved as FROZEN_WIP in draft PR #145 at head
   `97a76e3b90db9ec7bf9873e87a9108d4457afc33`; do not restart, merge, or review it yet.
3. After FIX-002 independent acceptance + PM integration, #145 rebases live main and resumes. At that
   point FIX-001 receives a narrow exception to establish/pass the temporal read cutoff before
   model-visible cockpit/snapshot construction, without changing FIX-002 provider-attempt semantics.
4. `CORE-GAP-FIX-003` remains blocked behind FIX-002 integration.
5. CI-fix candidate PR #144 is separate and may proceed to independent acceptance in parallel.
