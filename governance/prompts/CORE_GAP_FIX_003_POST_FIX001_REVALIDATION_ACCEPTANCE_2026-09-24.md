# CORE-GAP-FIX-003 POST-FIX001 REVALIDATION — FRESH INDEPENDENT ACCEPTANCE

Repository: Haneof/Haneof-AIOS-Core-v3.0

Role: Independent Core Runtime / User-Turn Recovery Acceptance Reviewer.

Candidate:
- PR #157
- title: CORE-GAP-FIX-003: recover user-turn IN_DOUBT safely
- post-FIX001 exact head: `7c0c51a7e9cda41a5aa61357ebba96955948a4a7`

Historical chain:
- original failed head: `81d626820cfa31e4f3f1aba0e892eb48cb11e46c`
- original independent FAIL: PR #162
- corrective pre-FIX001 head: `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`
- serialization review: PR #174 = REBASE_REVALIDATION_REQUIRED
- FIX-001 accepted head: `a56f113ace3c5e01af3acb724468bc2e0fbd4e98`
- FIX-001 merge: `d97a1bfa527caadb4ab22d232fd627c0483e02d8`
- FIX-001-integrated baseline absorbed by #157: `9cfcd2d7e5293e0596eb1de5c203f61213973494`

This review is only for the new post-FIX001 exact head. Do not reuse the old acceptance authority.

## Start

Fetch live main and read:
- governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md
- AIOS_v3.0_CURRENT_CHECKPOINT.md
- governance/AIOS_CORE_S2_POST_FIX002_PARALLELISM_RULING_2026-09-24.md
- governance/CORE_GAP_FIX_001_INTEGRATION_RECEIPT_2026-09-24.md
- governance/prompts/CORE_GAP_FIX_003_CORRECTIVE_001_2026-09-24.md
- governance/prompts/CORE_GAP_FIX_003_REBASE_AFTER_FIX001_2026-09-24.md
- reviews/CORE_GAP_FIX_003_INDEPENDENT_ACCEPTANCE_2026-09-24.md
- reviews/CORE_GAP_FIX_003_CORRECTIVE_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md
- PR #157 current body/diff.

Confirm task state is GATE / REVIEW_READY for the post-FIX001 exact head.

Pin PR #157:
- OPEN
- UNMERGED
- non-draft
- exact head unchanged at `7c0c51a7e9cda41a5aa61357ebba96955948a4a7`.

If head changes, re-pin and do not inherit this exact-head evidence.

## Serialization / merge construction

Verify the new head is a merge/rebase result that contains the FIX-001-integrated main lineage.

The PR body records a double-parent merge:
- parent 1 = `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`
- parent 2 = `9cfcd2d7e5293e0596eb1de5c203f61213973494`.

Independently inspect the overlap, especially `src/aios_core/runtime/turn_runtime.py`.

Verify BOTH semantic families remain present:

FIX-001:
- `_KnowledgeCutoffStoreView`
- active temporal read cut
- historical Wake / Periodic Review cut
- cutoff-aware C14 lineage
- historical search / inspect / cognition read semantics

FIX-003:
- `model_attempt_pre_admission_v1`
- only explicit pre-admission + zero attempts is mechanically safe
- legacy / old `model_attempt_v1 + zero attempts` remains IN_DOUBT
- attempt ledger dominates once an attempt exists
- one-shot explicit retry authorization
- repeated claim→attempt crash recovery
- A09 / input identity / conflicting-input fail closed

No conflict resolution may silently revert either family.

## Re-run semantic review

Freshly verify the corrected CG-003 semantics on the merged head:

1. claim→initial-attempt crash is recoverable only in the explicit pre-admission phase;
2. repeated crashes before admission remain recoverable;
3. provider eventually executes at most once;
4. deterministic round-0 attempt row remains unique;
5. assistant output remains unique;
6. legacy/no-protocol zero-attempt remains IN_DOUBT;
7. old `model_attempt_v1 + zero attempts` remains IN_DOUBT;
8. ambiguous post-dispatch remains IN_DOUBT;
9. `response_returned` remains non-retryable;
10. definitely-not-submitted is recoverable only through explicit authorization;
11. completion recovery remains idempotent;
12. conflicting input remains fail-closed;
13. FIX-002 background attempt ledger remains the sole provider-attempt truth store.

## FIX-001 compatibility

Because this candidate now includes FIX-001, independently verify:
- historical temporal cut still activates before model-visible cockpit construction;
- cutoff-aware C14 direct and bundle lineage still excludes T2-only support;
- current-time control still sees current state;
- FIX-003 user-turn changes do not reset or bypass active temporal cut.

## Exact-head CI

Exact head:
`7c0c51a7e9cda41a5aa61357ebba96955948a4a7`

All 13 required workflows must be SUCCESS:

- p16-convergence-gate — run `35986286182`
- fused-turn-runtime — `35986286308`
- c09-wake-dispatch — `35986286147`
- p15-periodic-review — `35986286137`
- c14-cognitive-derivation-runtime — `35986286215`
- c14-cognitive-derivation-loop — `35986286171`
- p9-revision-gate — `35986286173`
- p10-ai-world-gate — `35986286193`
- p11-dimension-gate — `35986286157`
- p12-execution-gate — `35986286175`
- p14-long-context — `35986286246`
- constitutional-cognition-closure — `35986286165`
- c15-cognition-evidence-policy — `35986286133`

Full P16 primary job:
`107589604043`

Re-read raw logs. PM observed:
- CPython 3.12.14
- pytest 8.4.2
- pydantic 2.13.5
- command `pytest -q`
- 100%
- 662 pass markers
- workflow SUCCESS

Do not rely only on badge.

## Late-main drift

After construction, main advanced from `9cfcd2d7...` to `d4028c033...` only by adding the review-only PR #174 report.

Independently verify no `src/**`, tests, or workflow changes occurred in that drift.

If live main has advanced further, compare the new drift:
- review/governance-only drift does not automatically require a code rebase;
- any semantic `src/**`, test-contract, or workflow change that affects the candidate requires stop/revalidation.

## Independent adversarial probes

Perform at least two of:

A. crash-x3 on the merged head, proving provider=1 / attempt row=1 / output=1;

B. forged/stale pre-admission marker plus a real `in_doubt` attempt, proving the attempt ledger dominates;

C. combine a historical T1 Wake/C14 cutoff scenario with user-turn recovery state present in the same World, proving FIX-003 state does not contaminate temporal read-cut behavior.

Do not modify PR #157.

## Scope

Expected PR diff against FIX-001-integrated baseline is six files:
- reviews/CORE_GAP_FIX_003_COMPLETION_EVIDENCE_2026-09-24.md
- src/aios_core/runtime/__init__.py
- src/aios_core/runtime/background_attempt.py
- src/aios_core/runtime/turn_execution.py
- src/aios_core/runtime/turn_runtime.py
- tests/runtime/test_turn_execution_recovery.py

No task board/checkpoint/Resident/fixture/operator/UI/hardware changes are allowed in the candidate.

## Verdict

ACCEPTANCE_PASS only if:
- CG-003 blocker remains closed on the post-FIX001 head;
- FIX-001 semantics remain intact;
- FIX-002 semantics remain intact;
- A09 remains intact;
- adversarial probes pass;
- 13/13 workflows pass;
- full P16 passes;
- no semantic live-main drift invalidates the candidate;
- blockers = 0.

ACCEPTANCE_FAIL for any implementation blocker.

REBASE_REVALIDATION_REQUIRED only if a new semantic main change lands before review completion and materially invalidates the pinned head.

## Report

Do not overwrite historical reports.

Create a new review-only report:

`reviews/CORE_GAP_FIX_003_POST_FIX001_REVALIDATION_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

Create one review-only PR from current live main.

Final report must include:
- review-time main
- PR #157
- exact head
- merge/rebase construction review
- FIX-001 compatibility
- FIX-002 compatibility
- CG-003 recovery verdict
- adversarial probes
- exact-head workflow evidence
- P16 evidence
- live-main drift verdict
- blocker count
- final verdict.

Do not merge #157.
