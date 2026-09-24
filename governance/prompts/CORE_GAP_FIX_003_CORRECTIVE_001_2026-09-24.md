# CORE-GAP-FIX-003-CORRECTIVE-001

Repository: Haneof/Haneof-AIOS-Core-v3.0

Role: Core Runtime / User-Turn Recovery Engineer.

Continue the existing:
- PR #157
- branch `core-gap-fix-003-user-turn-recovery-20260924-sol`

Do not create a competing PR. Do not restart CORE-GAP-FIX-003 from scratch.

## Trigger

Independent acceptance PR #162 reviewed exact candidate
`81d626820cfa31e4f3f1aba0e892eb48cb11e46c`
and returned ACCEPTANCE_FAIL with exactly one blocker:

`CORE-GAP-FIX-003-ACCEPT-BLOCKER-001`

Meaning:

A process crash after durable `runtime_turn_executions.claim()` commits a new-protocol
`started` row, but before round-0 `user_turn` provider-attempt admission is durable,
leaves:

- state = started
- attempt_protocol = model_attempt_v1
- zero user_turn attempts
- no assistant output

The current recovery surface classifies this as IN_DOUBT and cannot authorize, reconcile,
complete, or otherwise recover the original turn identity.

Historical acceptance report:
`reviews/CORE_GAP_FIX_003_INDEPENDENT_ACCEPTANCE_2026-09-24.md`.

## Required start

1. Fetch current live main.
2. Read:
   - governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md
   - AIOS_v3.0_CURRENT_CHECKPOINT.md
   - governance/AIOS_CORE_S2_POST_FIX002_PARALLELISM_RULING_2026-09-24.md
   - governance/prompts/CORE_GAP_FIX_003_2026-09-24.md
   - reviews/CORE_GAP_FIX_003_INDEPENDENT_ACCEPTANCE_2026-09-24.md
3. Confirm `CORE-GAP-FIX-003-CORRECTIVE-001 = READY`.
4. Reuse the existing PR #157 and preserve all prior reproduction / exact-head evidence.

## Only blocker to fix

Close the crash window between:
1. durable initial user-turn claim; and
2. durable round-0 `user_turn` provider-attempt admission.

The correction must preserve BOTH:
- A09 at-most-once / conflicting-input fail-closed behavior;
- liveness: the original turn identity must have a supported forward recovery when provider dispatch is mechanically proven not to have occurred.

## Acceptable correction classes

Use the smallest correct design.

### Option A — atomic initial admission

Make the initial user-turn claim and round-0 provider-attempt admission one SQLite atomic durable boundary in the same private World DB.

If used:
- either both durable records commit, or neither does;
- deterministic execution/attempt identity must remain stable;
- do not create a second provider-attempt truth store;
- do not bypass the accepted BackgroundModelAttempt semantics.

### Option B — explicit durable pre-attempt proof/state

Introduce an equivalently safe durable state/protocol that means:
- the turn identity is claimed;
- no provider-attempt row has yet been admitted;
- by construction provider dispatch cannot have occurred.

This state may be recoverable only because the runtime invariant mechanically proves provider dispatch is impossible before attempt admission.

If used:
- legacy rows without the new protocol remain IN_DOUBT;
- zero attempts is safe ONLY for the explicit new pre-attempt state, never generically;
- recovery/retry still requires the defined explicit authorization/evidence boundary unless the chosen forward-repair transition itself is the durable mechanical proof;
- after an attempt exists, disposition must come from the attempt ledger states, not the pre-attempt marker;
- repeated crashes in the same claim→attempt window must remain recoverable and must not create duplicate provider attempts.

Do not merely change:
`zero attempts => safe_to_retry`
for all `model_attempt_v1` rows. That would incorrectly bless legacy/corrupt states.

## Required crash-window regressions

Add a real fault-injection regression for the exact blocker.

At minimum cover:

1. initial claim durable -> crash before round-0 attempt admission;
2. restart inspection gives a supported recoverable disposition, not permanent IN_DOUBT;
3. perform the legal recovery/authorization path;
4. crash AGAIN at the same claim→attempt boundary;
5. restart again and prove the turn is still recoverable;
6. eventually continue and prove exactly one provider execution occurs;
7. only one deterministic round-0 attempt identity exists.

Also preserve/verify:

8. legacy started row with no new protocol remains IN_DOUBT;
9. ambiguous post-dispatch state remains IN_DOUBT;
10. response_returned remains non-retryable;
11. durable assistant-output completion recovery remains idempotent;
12. conflicting input still raises TurnInputConflict;
13. one-shot retry authorization cannot be consumed twice.

## FIX-002 compatibility

Do not redesign:
- Wake / Periodic Review `run_wake` / `run_periodic_review`;
- background attempt state meanings;
- attempt identity rules for background work;
- reconciliation;
- metering;
- budget;
- lifecycle;
- completion semantics.

The accepted shared `background_model_attempts` ledger remains the single provider-attempt truth store.

If an atomic solution requires a reusable storage primitive, keep it narrow and prove existing Wake/Review rows and indexes remain unchanged.

## FIX-001 boundary / serialization

PR #145 is currently in corrective work after failed acceptance.

If FIX-001 becomes ACCEPTANCE_PASS and is integrated before this corrective reaches final REVIEW_READY:
- merge/rebase then-live main into #157;
- resolve only necessary conflicts;
- rerun all FIX-003 targeted/affected gates + full P16;
- produce a new exact head;
- receive a fresh independent acceptance on that rebased exact head.

If FIX-001 is still unmerged, current branch may proceed normally.

Do not modify FIX-001 temporal read-cut semantics.

## Preserve all already-passing FIX-003 behavior

Do not weaken:
- A09 admission identity;
- conflicting-input fail-closed;
- ModelDispatchNotSubmitted -> not_submitted;
- ambiguous provider interruption -> IN_DOUBT;
- response_returned before later work;
- completed-output recovery;
- retry authorization evidence requirement;
- one-shot authorization consumption;
- FIX-002 schema migration compatibility.

## Verification before handoff

At minimum rerun:
- dedicated claim→attempt crash regression;
- full `tests/runtime/test_turn_execution_recovery.py`;
- fused-turn-runtime;
- C09 Wake;
- P15 Periodic Review;
- C14 runtime;
- C14 loop;
- p9 / p10 / p11 / p12 / p14 as affected;
- constitutional-cognition-closure;
- c15-cognition-evidence-policy;
- full P16 `pytest -q`.

Record exact run/job IDs.

## Deliverable

Update existing PR #157 body with:
- failed reviewed head `81d626820cfa31e4f3f1aba0e892eb48cb11e46c`;
- blocker ID;
- chosen corrective invariant;
- exact claim→attempt fault-injection evidence, including repeated crash;
- compatibility evidence;
- current live-main / FIX-001 serialization state;
- new exact candidate head;
- targeted/full CI.

Set author state REVIEW_READY only.

Do not self-accept.
Do not merge.
Do not modify task board/checkpoint from the engineering window.
Do not run Resident.
