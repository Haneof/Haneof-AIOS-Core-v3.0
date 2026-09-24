# CORE-GAP-AUDIT-001 PM Acceptance and Gap-Fix Dispatch — 2026-09-24

Status: PM_ACCEPTED / DISPATCH_READY

## Accepted audit

- Independent audit PR: #132
- Audit exact head: `1700a3feab58959bba95eb3420625a8f32aef2fc`
- Audit baseline: `c8807876ba62a4f4180beba8ff974e2342786340`
- Audited Core tree: `7db4f72e7b3c29c74082f9984141159f8f1d6071`
- Audit merge: `bc4bf735e15c5c0787fdc533fe3f10d0e17fdac3`
- Report: `reviews/CORE_GAP_AUDIT_001_2026-09-24.md`

PM source inspection independently confirmed the three release-level gaps are real on the audited Core:
1. `CG-001 RUNTIME_TEMPORAL_READ_CUT`
2. `CG-002 BACKGROUND_MODEL_EXECUTION_IN_DOUBT`
3. `CG-003 USER_TURN_IN_DOUBT_RECOVERY`

All three block `CORE-RC-FREEZE-001`.

## Dispatch policy

One gap = one engineering task = one engineering window. The author of a fix may not independently accept the same candidate.

The fixes are intentionally serialized even though they are logically distinct because all three may touch `src/aios_core/runtime/turn_runtime.py`, and FIX-003 should reuse any generic model-attempt/recovery mechanism introduced by FIX-002 instead of creating a second truth store.

Order:
1. `CORE-GAP-FIX-001` — READY
2. `CORE-GAP-FIX-002` — BLOCKED on accepted+merged FIX-001
3. `CORE-GAP-FIX-003` — BLOCKED on accepted+merged FIX-002

Each engineer must:
- start from real-time latest main;
- reproduce the exact gap before fixing;
- do the minimum Core change;
- add targeted regression coverage;
- run affected Core suites plus the repository full regression required by the task;
- open a focused candidate PR;
- stop at `REVIEW_READY`.

A different independent reviewer must review each candidate exact head before PM integration.

## Parallel work still active

`CORE-OPERATOR-001` remains a separate S1 prerequisite. PR #131 is `REVIEW_READY` and OPEN/UNMERGED pending independent acceptance. It is not made DONE by this dispatch.

No Resident A/B/C is authorized. Historical Resident evidence remains immutable.

## Downstream

`CORE-HEADLESS-001` stays BLOCKED until:
- CORE-OPERATOR-001 is independently accepted and integrated; and
- CORE-GAP-FIX-001/002/003 are independently accepted and integrated.

Then S2 continues:
`CORE-HEADLESS-001 -> CORE-RECOVERY-001 -> CORE-SCALE-001 -> CORE-RC-FREEZE-001`.

Only after RC freeze may the planned fresh C15 A -> B -> C chain begin.
