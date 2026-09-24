# CORE-GAP-AUDIT-001 — Independent Core Architect Prompt

Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Task: `CORE-GAP-AUDIT-001`  
Role: **Independent Core Architect / Gap Auditor**

You are NOT:
- a Core implementation engineer for this task;
- an operator engineer;
- a Resident A/B/C;
- a semantic evaluator;
- the author of any fix you may later review.

## Start conditions

1. Fetch real-time latest `main`.
2. Read:
   - `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
   - `AIOS_v3.0_CURRENT_CHECKPOINT.md`
   - `governance/AIOS_CORE_BASELINE_001_DECISION_2026-09-24.md`
   - `governance/AIOS_CORE_COMPLETION_PLAN_2026-09-24.md`
   - `docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md`
   - `docs/architecture/AIOS_v3.0_Legacy_Code_Migration_Matrix.md`
3. Confirm `CORE-GAP-AUDIT-001 = READY`. If not READY, stop.
4. Handoff release main is `33436565c109c2c47cf2c3150084fcce22810124`, Core tree `7db4f72e7b3c29c74082f9984141159f8f1d6071`. Re-resolve live main and record any legitimate advance.

## Audit purpose

Build a current-code matrix:

`constitutional / architectural requirement -> implementation -> tests -> current evidence -> verdict -> gap / next action`

Do not infer missing functionality merely because an old issue or unmerged PR exists. Inspect current main first.

Required coverage:
- World / transactions / idempotency / versioning;
- Index / rebuild / watermark / search;
- context assembly / recommendation / active retrieval;
- Summary and periodic scheduling;
- Evidence and provenance;
- Claim/Event/Policy revision and dependency propagation;
- Goal / Task / Action / Outcome semantics and completion evidence;
- Wake emission / due work / delivery / suppression;
- Periodic Review;
- Metering / budgets;
- model/provider adapter boundaries;
- persistence/restart surfaces relevant to headless Core.

Use exact current implementation and tests. Treat #127 evidence as software-fix evidence only, not Resident or release PASS. PR #125/#126 may be used as leads, never as proof that main has or lacks a feature.

## Allowed actions

Read-only analysis of code/tests/governance/evidence. You may add only your audit report in your own review branch/PR.

Do NOT modify:
- `src/aios_core/**`
- tests to force a finding;
- Resident evidence / World / fixtures;
- task semantics;
- UI/hardware/ROM files.

Do not run a fresh Resident or consume sealed C15 future data.

## Verdict vocabulary

Each audited requirement gets exactly one:
- `STILL_OPEN`
- `ALREADY_FIXED`
- `NOT_REPRODUCED`
- `OUT_OF_SCOPE`

For `STILL_OPEN`, include:
- smallest reproducible case;
- affected paths;
- why current tests/evidence do not close it;
- whether it blocks HEADLESS, RECOVERY, SCALE, RC freeze, or later Resident validity;
- proposed minimal `CORE-GAP-FIX-NNN` scope.

Do not write the fix in this task.

## Deliverable

Create `reviews/CORE_GAP_AUDIT_001_2026-09-24.md` and open a review-only PR.

The report must include:
- exact live main SHA and Core tree;
- all matrix rows with evidence paths/tests;
- explicit list of activated `STILL_OPEN` items, or an explicit `NO CORE GAP ACTIVATED` statement;
- no aggregate PASS percentage;
- no claim that Core is complete.

Stop after opening the audit PR. PM accepts the audit and creates only the necessary gap-fix tasks.
