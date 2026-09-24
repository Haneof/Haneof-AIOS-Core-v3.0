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
- If both need to modify the same file, the second window stops and reports to the PM; the PM serialises the two tasks rather than letting two windows write the same file.
- Neither window may modify: `governance/**`, `reviews/**`, `tools/c15_preflight/**`, `tests/preflight/**`, historical evidence, fixtures, or any private World.
- Governance status writeback for a fix is performed by the PM at integration, not by the engineering author.

### Standing acceptance rule for these two tasks

Engineering author declares `REVIEW_READY` only. A different independent acceptance window must, at minimum:

1. re-derive the before-fix reproduction at the candidate's own reproduction commit;
2. verify the fix closes it at the exact candidate head;
3. verify scope, Core impact and that no historical evidence/fixture is touched;
4. state an explicit `ACCEPTANCE_PASS` / `ACCEPTANCE_FAIL` verdict with blocker count.

PM integration additionally re-verifies pins and CI from the API and re-runs the decisive evidence locally before merging, as recorded for `CORE-OPERATOR-001`.
