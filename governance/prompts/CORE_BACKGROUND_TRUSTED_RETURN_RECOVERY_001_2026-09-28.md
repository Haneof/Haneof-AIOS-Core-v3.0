# CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001

Date: 2026-09-28  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`

## Role

Core Runtime Recovery Engineer

You are NOT:

- C15 persistence harness engineer
- Resident B
- PM
- Independent Acceptance reviewer
- release operator
- semantic evaluator

## Why this task exists

C15 persistence Corrective-003 binding blocker `IA-BLK-PERSIST-C002-002` exposed a Core recovery gap that cannot be legally repaired inside `tools/c15_persistence/**`.

The exact failing window is:

1. Core has durably admitted a background/user-turn model attempt and crossed the provider-dispatch boundary.
2. The trusted external provider/relay returns exact `ModelDirective` bytes.
3. Those exact returned bytes can survive externally across process/environment loss.
4. The process dies before Core's normal trusted-return callback commits the `BackgroundModelResponseReceipt`.
5. On restart, Core sees a durable dispatching/in-doubt attempt but no trusted-return receipt.
6. Blind provider redispatch is forbidden.
7. Recovery caller must not be allowed to mint or forge provider-return authenticity.

Accepted Core currently has:

- `stage_exact_background_response(...)`, which correctly requires a pre-existing trusted authenticity proof;
- private `BackgroundModelAttemptStore._capture_trusted_response_return(...)`, deliberately wired only to Core's normal trusted-return boundary;
- no accepted recovery API that may invoke that signing authority from arbitrary externally supplied response bytes.

## Historical evidence / prohibited WIP

Persistence PR #254 is CLOSED / FROZEN; its branch and all historical commits remain preserved.

Observed invalid WIP:

`f7848952b6519fc40f50806f4a4d8d350ac0f38a`

It added:

`FusedTurnRuntime.stage_trusted_returned_background_response(...)`

which accepts externally supplied directive payload and calls the private trusted-return receipt minting path.

That WIP is **NOT an accepted design** and MUST NOT be cherry-picked or treated as the solution.

Why:

The previously accepted `CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002` explicitly closed a provenance/authenticity flaw by ensuring recovery callers cannot self-establish trusted provider-return authenticity.

This new task must preserve that invariant.

## Frozen invariants

The repair MUST preserve all of the following:

1. Recovery caller never receives:
   - HMAC authority secret;
   - signing callable;
   - generic "mint receipt for these bytes" capability.

2. Externally supplied directive bytes alone are never sufficient to establish trusted-return authenticity.

3. Caller-computable:
   - response fingerprint;
   - provider/model/request_id strings;
   - relay id;
   - request digest;
   are not an authenticity authority by themselves.

4. Exact response must remain bound to:
   - subject_id;
   - work_kind;
   - work_id;
   - model_round_index;
   - attempt_id;
   - originating outbound request fingerprint;
   - relay/request identity;
   - provider/model/provider_request_id;
   - exact directive payload SHA-256 / response fingerprint.

5. No blind provider redispatch after provider submission may already have occurred.

6. No duplicate semantic application, assistant output, capability application, metering or ACK.

7. Existing exact-response staging must remain fail-closed for:
   - cross-work transplant;
   - cross-subject transplant;
   - cross-round transplant;
   - request/relay mismatch;
   - provider/model/request-id mismatch;
   - payload mismatch;
   - missing/invalid authenticity proof;
   - duplicate semantic-key JSON.

8. Do not create a second World, cognition store, or shadow semantic engine.

## Required design property

The solution must establish a **trusted durable return handoff** at the provider-return boundary.

A crash after the provider has returned exact bytes but before ordinary downstream turn application must leave enough Core-owned durable evidence to recover the exact return without:

- calling the provider again;
- trusting an arbitrary recovery caller;
- granting the recovery caller signing authority.

The trusted event must be established by a boundary already authorized to observe the real provider return, not retrospectively inferred from recovery-supplied bytes.

Permitted designs may include a narrowly scoped trusted-return handoff/receipt mechanism integrated into the trusted provider-return path, provided the authority remains Core-owned and cannot be invoked as a general recovery signing oracle.

Do NOT merely expose `_capture_trusted_response_return()` publicly.

## Required crash matrix

At minimum test:

### R1 — before provider submission
Safe ordinary dispatch is allowed only when Core mechanically knows submission did not occur.

### R2 — provider submitted, no return yet
Recovery must not blindly redispatch. It may reattach/poll a provider/relay using the exact existing request identity if that transport operation is mechanically idempotent.

### R3 — provider exact return observed at trusted boundary, receipt/handoff durable
Crash immediately after the trusted durable return handoff. Restart must stage/recover exact response without redispatch.

### R4 — trusted return durable, exact response staged, before semantic application
Recovery converges exactly once.

### R5 — response applied / metered, before outer cursor ACK
Recovery does not rerun model/capability/semantic work.

## Adversarial authenticity probes

Must attempt to falsify:

- forged directive with same provider/model/request_id;
- forged response fingerprint;
- copied receipt from another attempt;
- copied receipt from another round;
- copied receipt from another work id / work kind / subject;
- correct reply bytes with wrong originating request;
- correct request with wrong reply;
- duplicate JSON keys / ambiguous semantic payload;
- replay of a valid old receipt;
- missing receipt;
- corrupted receipt;
- trusted-handoff record without corresponding durable attempt;
- attempt without originating request binding;
- provider return recorded before provider boundary.

All must fail closed as applicable.

## Relationship to C15 persistence

This Core task does NOT modify:

- PR #254 persistence implementation;
- `tools/c15_persistence/**`;
- Resident B data;
- C15 release state.

Corrective-003 remains frozen while this task is active.

After this Core task is independently accepted and integrated, governance must determine the required Core RC re-freeze / lineage revalidation before persistence Corrective-003 may resume.

## Environment

Formal Core gate:

- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2

Run:

- new focused trusted-return crash recovery suite;
- all existing background-response authenticity/recovery tests;
- full Core regression;
- headless/recovery/scale gates as applicable.

Preserve every red attempt.

## Engineering discipline

- fresh fetch live `main`;
- create a new Core engineering branch/PR;
- do not modify PR #254;
- do not modify historical PR #219 evidence;
- do not weaken prior accepted authenticity checks;
- do not merge;
- stop at `REVIEW_READY`;
- fresh Independent Acceptance is mandatory.

## Completion

Only if implementation + formal gates are green:

```text
CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001 = REVIEW_READY
READY_FOR_INDEPENDENT_ACCEPTANCE
```

Otherwise:

```text
CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001 = BLOCKED
```

and preserve the exact blocker/red evidence.
