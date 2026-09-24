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
- CORE-OPERATOR-001 is already at engineering REVIEW_READY in PR #131 and awaits a different independent reviewer.
- CORE-HEADLESS-001 remains BLOCKED until operator acceptance plus all RC-blocking gap fixes are independently accepted and integrated.
- No Resident A/B/C is authorized before CORE-RC-FREEZE-001.

Each fix uses a distinct engineer window. Each candidate requires a different independent acceptance reviewer. Engineering authors may only declare REVIEW_READY, never DONE.
