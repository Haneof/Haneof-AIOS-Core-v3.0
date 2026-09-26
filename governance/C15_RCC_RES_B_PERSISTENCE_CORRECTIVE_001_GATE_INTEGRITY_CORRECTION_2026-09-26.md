# C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 — Gate Integrity Correction

Date: 2026-09-26
Repository: `Haneof/Haneof-AIOS-Core-v3.0`
Reviewed live main: `59e3f48b9fe2a75ea9377ed3d75a97939880b695`

## Status

`governance/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_001_PM_SCOPE_AMENDMENT_2026-09-26.md`

is preserved as historical governance but is **SUPERSEDED FOR ACTIVE EXECUTION** by this correction.

## Why this correction is required

The binding state-loss adjudication froze the persistence corrective acceptance contract before engineering began.

It explicitly required five kill/restart probes, including:

- after reply durably staged but before application;
- after model/capability work but before ACK;

and required:

> each recovery must converge to the same durable cursor without second reveal, duplicate ingest, duplicate semantic application, or skipped ACK.

The engineering WIP then produced a genuine red result at the reply-staged -> application boundary: the current frozen Core remains fail-closed/in-doubt and cannot continue the exact returned directive through normal runtime/headless execution without provider redispatch or a duplicate semantic engine.

PR #214 subsequently changed the acceptance criterion so that this red result could count as a passing terminal/in-doubt state.

That is an ex-post-facto Gate relaxation. It is not permitted.

A safety-only terminal stop can be a correct failure behavior, but it is not equivalent to the previously frozen requirement for crash-safe recovery convergence. Red evidence must remain red until the mechanism is fixed; the acceptance threshold may not be moved after observing the failure.

## Mechanism finding

Fresh source inspection confirms:

- `BackgroundModelAttemptStore.reconcile_response(...)` can durably reconcile exact provider provenance into `response_returned`;
- normal `FusedTurnRuntime` model-attempt admission still blocks on `response_returned`;
- headless reports `BackgroundModelResponsePending` as `reconciliation_required`;
- no current Core surface consumes the exact reconciled `ModelDirective` through normal CognitiveRuntime downstream semantics without another provider call;
- operator code cannot legally solve this by relabeling the attempt `not_submitted`, blindly redispatching, or reimplementing semantic application.

## Active verdict

`C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 = FROZEN_WIP / BLOCKED_ON_CORE_RESPONSE_RECOVERY`

New unique READY:

`CORE-BACKGROUND-RESPONSE-RECOVERY-001`

The existing persistence WIP and all red/green evidence must be preserved. It is not discarded and must later resume from that exact WIP after the Core recovery gap is accepted and the software is re-frozen.

## Required downstream sequence

Because the new task modifies Core, future Resident evidence must not silently reuse the previous RC freeze.

Required order:

1. `CORE-BACKGROUND-RESPONSE-RECOVERY-001`
2. `CORE-BACKGROUND-RESPONSE-RECOVERY-001-INDEPENDENT-ACCEPTANCE`
3. `CORE-RC-REFREEZE-002`
4. `C15-RCC-RES-A-RERUN-003`
5. `C15-RCC-RES-A-RERUN-003-INDEPENDENT-ACCEPTANCE`
6. resume frozen `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001`
7. persistence corrective Independent Acceptance
8. `C15-RCC-RES-B-RELEASE-003`
9. fresh `C15-RCC-RES-B-RERUN-003`
10. B acceptance -> C -> evaluator -> close

Historical PR #205 remains valid evidence for the prior frozen Core only and is never mutated.

## Preservation rule for current WIP

The engineering window that owns the current persistence WIP must only:
- commit/push its current implementation, ENGINEERING_STATUS and red evidence to a dedicated branch;
- report exact branch/head;
- stop.

It must not continue engineering after this correction until the Core/refreeze/fresh-A dependencies are satisfied.
