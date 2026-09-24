# CORE-GAP-FIX-00N — Independent Acceptance Review

Repository: Haneof/Haneof-AIOS-Core-v3.0

Role: Independent Core Acceptance Reviewer for exactly one of `CORE-GAP-FIX-001` / `-002` / `-003` (the PM names it and the exact candidate PR/head when launching this window).

You are not the fix author, not the audit author, not the PM, not a Resident, and not a semantic evaluator. If you authored or co-authored the candidate, stop.

## Before reviewing

1. Fetch live main; record its SHA.
2. Read `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`, `AIOS_v3.0_CURRENT_CHECKPOINT.md`, `governance/AIOS_CORE_GAP_DISPATCH_2026-09-24.md`, `governance/AIOS_CORE_COMPLETION_PLAN_2026-09-24.md`, `reviews/CORE_GAP_AUDIT_001_2026-09-24.md` (the relevant CG item), and the task prompt `governance/prompts/CORE_GAP_FIX_00N_2026-09-24.md`.
3. Confirm the task is at GATE / REVIEW_READY with one exact candidate head. Review that head only; if it moves during review, restart against the new head.

## Required checks

1. **Reproduction first.** Run the candidate's new regressions against the construction-base Core (candidate tests + base `src/`) and confirm they FAIL for the audited reason; then confirm they PASS on the candidate. A test that passes before the fix is not a reproduction.
2. **Scope.** Diff is limited to what the task prompt allows. No World/Summary/Index/operator/fixture/Resident redesign, no historical evidence rewrite, no second runtime or database, no UI.
3. **Semantics** (per task prompt):
   - FIX-001: one explicit active read cut applied to every model-visible read path (search, exact inspect/drill-down, AI-world/current cognition); T2 facts invisible to resumed T1 C14 derivation and Periodic Review; current-time turns unchanged; missing/corrupt learned_at fails closed.
   - FIX-002: durable model-attempt identity/disposition; not-submitted may retry; submitted-without-response becomes IN_DOUBT and is never blindly re-invoked; returned/metered responses are not re-requested; Wake and Periodic Review both covered; no fabricated completion, budget or meter.
   - FIX-003: user-turn IN_DOUBT recovery consistent with the accepted FIX-002 state model; no turn_id swapping, table clearing or silent duplicate delivery.
4. **Regression.** Targeted tests + all directly affected suites + the full regression gate required by current governance, on the exact head (or a merge ref whose tree you verify equals the head's tree). Report failures and skips separately.
5. **Experiment impact.** The candidate states whether Core semantics changed and that historical Resident evidence is not patched; fresh A/B/C only after RC freeze.
6. **Adversarial probe.** Try at least one input the author's tests do not cover (e.g. revision at the cut boundary, crash between meter write and completion, restart twice).

## Deliverable

A review-only PR adding `reviews/CORE_GAP_FIX_00N_INDEPENDENT_ACCEPTANCE_<date>.md` with: live main SHA, exact candidate head, commands and raw results, reproduction evidence, findings (blocker / non-blocking), and a final verdict of exactly `ACCEPTANCE_PASS` or `ACCEPTANCE_FAIL`.

Do not modify the candidate, Core, tests, fixtures or evidence. Do not merge anything. Do not update the task board (PM integrates). Do not start another task.
