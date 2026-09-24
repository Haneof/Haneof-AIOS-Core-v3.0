# CORE-GAP-FIX-003 — REBASE / REVALIDATION AFTER FIX-001 INTEGRATION

Repository: Haneof/Haneof-AIOS-Core-v3.0

Continue the existing:
- PR #157
- branch `core-gap-fix-003-user-turn-recovery-20260924-sol`

Do not create a competing PR.
Do not redesign the accepted FIX-003 corrective mechanism.

## Trigger

CORE-GAP-FIX-001 was independently accepted and integrated first.

Accepted FIX-001 exact head:
`a56f113ace3c5e01af3acb724468bc2e0fbd4e98`

FIX-001 merge:
`d97a1bfa527caadb4ab22d232fd627c0483e02d8`

Therefore the post-FIX002 serialization ruling now requires PR #157 to rebase/merge live main,
rerun gates, and obtain fresh independent acceptance before any PM integration.

The prior #157 corrective exact head:
`ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`

is preserved as historical corrective evidence but is no longer directly merge-authorized.

## Start

1. Fetch current live main.
2. Read:
   - governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md
   - AIOS_v3.0_CURRENT_CHECKPOINT.md
   - governance/AIOS_CORE_S2_POST_FIX002_PARALLELISM_RULING_2026-09-24.md
   - governance/CORE_GAP_FIX_001_INTEGRATION_RECEIPT_2026-09-24.md
   - governance/prompts/CORE_GAP_FIX_003_CORRECTIVE_001_2026-09-24.md
   - reviews/CORE_GAP_FIX_003_INDEPENDENT_ACCEPTANCE_2026-09-24.md
3. Confirm FIX-003 is marked REBASE / REVALIDATION REQUIRED.
4. Continue the existing #157 branch.

## Required action

Merge or rebase then-live main into #157 so the branch contains the integrated FIX-001 temporal read-cut code.

Resolve only real overlaps. Preserve the FIX-003 corrective invariant:
- fresh user-turn pre-attempt marker = `model_attempt_pre_admission_v1`;
- only explicit pre-admission + zero attempts is safely recoverable;
- legacy / old `model_attempt_v1 + zero attempts` remains IN_DOUBT;
- attempt ledger dominates once an attempt exists;
- repeated claim→attempt crashes remain recoverable;
- A09 and conflicting-input fail-closed remain intact.

Do not change FIX-001 temporal semantics unless required solely to resolve a merge conflict.
Do not modify historical Resident evidence, fixtures, operator, UI, or hardware.

## Revalidation

After integration with live main, rerun at minimum:
- `tests/runtime/test_turn_execution_recovery.py`;
- fused-turn-runtime;
- C09 Wake;
- P15 Periodic Review;
- C14 runtime;
- C14 loop;
- P9 / P10 / P11 / P12 / P14;
- constitutional cognition closure;
- C15 cognition evidence policy;
- full P16 `pytest -q`.

Because FIX-001 changes temporal semantics in `turn_runtime.py`, explicitly verify:
- user-turn recovery code did not bypass or reset active temporal read-cut behavior;
- Wake/Periodic Review historical cut remains intact;
- no conflict resolution reverted FIX-001's cutoff-aware C14 lineage;
- no conflict resolution reverted FIX-003's pre-admission recovery protocol.

## Handoff

Update PR #157 body with:
- previous corrective head `ac8d5a43...` preserved as historical;
- live main merged/rebased SHA;
- conflict resolution summary;
- new exact rebased candidate head;
- exact run/job IDs;
- full P16 result.

Then set author state REVIEW_READY and stop.

Do not self-accept.
Do not merge.
Do not modify task board/checkpoint from the engineering window.
Do not run Resident.
