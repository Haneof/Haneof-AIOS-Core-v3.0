# CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001

Date: 2026-09-28

Repository: `Haneof/Haneof-AIOS-Core-v3.0`

## Role

Core Runtime Corrective Engineer.

This task exists only to close `IA-BLK-TRUSTED-RETURN-001`.

Do not act as Independent Acceptance reviewer, PM, Resident, release operator, or persistence harness engineer.

## Start gate

Fresh-fetch live main, PR #258, PR #261, task board, checkpoint and this prompt.

Required state:

- `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001 = FAILED EXACT CANDIDATE / CORRECTIVE REQUIRED`
- `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001 = READY`
- failed exact candidate = `1ebf51c4cb905e2a2578a09b64007b50bca0d4ac`
- review evidence PR #261 remains review-only / unmerged.

If governance differs, stop as BLOCKED.

## Historical evidence

Preserve without rewriting:

- original later-round RED `cca64dca...`;
- historical STOP `5863435728`;
- merged R5 clarification;
- frozen R5 RED `d3fa0490...`;
- failed exact candidate `1ebf51c4...`;
- review-only PR #261 / exact review head `b9d692dd...`;
- all author greens and reviewer REDs.

Do not modify PR #261.

## Binding blocker

Fresh Independent Acceptance found that R5-C exact replay convergence is incomplete outside the `execution.task.create` family.

Five reproduced reachable examples:

- `propose_goal`
- `form_event`
- `propose_entity`
- `propose_dimension`
- `propose_cognitive_policy`

Observed failure modes include exact-replay `StoreError` due to changed operation request identity and pre-commit "already exists" rejection.

`commit_claim` is not proof of general correctness; it passes because `CognitionWritebackService.commit_claim()` already has a pre-existing exact-retry guard.

## First requirement: freeze the complete capability replay matrix before implementation

Before changing Core, enumerate the current runtime capability registry and identify every reachable capability that can produce a durable World / semantic / execution side effect in user_turn, Wake or Periodic Review.

For every side-effecting capability classify:

1. durable write service/path;
2. stable logical object / operation identity;
3. idempotency key;
4. behavior after side effect is durable but outer completion is not;
5. whether identical R5-C replay currently:
   - returns exact prior success,
   - rejects,
   - duplicates,
   - or is non-applicable;
6. changed/conflicting replay expected behavior.

Freeze the matrix and reviewer-proven baseline RED against exact `1ebf51c4...` before implementation.

At minimum reproduce the five reviewer-proven failing families.

Do not weaken expected outcomes after execution.

## Required semantics

For an identical recovered capability call whose durable side effect already exists:

- no provider redispatch of the recovered round;
- no second durable meter;
- no second capability side effect;
- no second World/semantic write;
- same object/revision/operation identity where the contract defines one;
- capability replay must return a successful result consistent with the original durable effect;
- the logical turn must continue/converge.

For changed/conflicting replay:

- fail closed;
- never treat a changed request as identical merely because an idempotency key or object id matches.

## Implementation constraints

Use the smallest correct mechanism.

Permitted patterns include:

- a pre-existing-object exact-retry guard when the service contract has a deterministic stable object identity;
- reuse of the original durable operation identity/expected revision when the exact same canonical request can be mechanically proven;
- a narrow reusable helper if several services share exactly the same semantics.

Do not:

- disable or weaken `request_fingerprint`;
- make `SQLiteWorldStore.commit()` accept changed requests under an existing key;
- silently overwrite existing objects;
- generalize "already exists" into success without exact request equivalence;
- create a second truth store;
- introduce a generic post-application state machine;
- change trusted-return receipt/handoff authority;
- grant recovery callers signing/minting authority.

## Trusted-return invariants must remain unchanged

The Core-owned trusted provider-return callback remains the only receipt/handoff minting boundary.

Recovery callers must not be able to supply arbitrary reply bytes and obtain a trusted receipt.

All prior authenticity/transplant/corruption attacks must remain fail-closed.

## R5 scope

Binding R5 remains exactly-once durable effects, not zero callback re-entry.

An authenticated deterministic/idempotent path may be re-entered when there is no stronger completion receipt.

A stronger durable terminal output/delivery receipt must continue to short-circuit runtime replay.

## Tests

Freeze corrective tests before implementation.

Required coverage:

- the complete side-effecting capability replay matrix;
- all reviewer-proven five RED families;
- representative create/revise/transition/register-like mutation families;
- exact identical replay after unrelated later World revisions;
- changed args under same call id/key;
- changed payload/object identity;
- changed evidence/reason where part of request identity;
- corrupted operation/idempotency rows;
- existing-object exact retry;
- existing-object conflicting retry;
- real process-loss R5-C at least one non-task-create family;
- R1-R5 regression;
- trusted-return authenticity/transplant matrix;
- candidate historical tests;
- complete pytest regression.

## Formal environment

- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2
- record actual SQLite version.

## Branch / PR

Create a new corrective engineering branch and new PR from fresh live main.

Do not continue or rewrite PR #258.

PR #258 remains the failed exact historical candidate.

If the platform forces one fixed session branch, document that limitation but still create a distinct Corrective-001 PR if possible.

## Completion gate

Only when the complete side-effecting capability matrix is green, R1-R5 remain green, authenticity remains fail-closed, and full regression is green may the task become:

`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001 = REVIEW_READY`

Then publish an exact handoff and stop at:

`READY_FOR_INDEPENDENT_ACCEPTANCE`

Do not self-accept, merge, enter RC refreeze, Resident A/B, persistence Corrective-003, or release work.
