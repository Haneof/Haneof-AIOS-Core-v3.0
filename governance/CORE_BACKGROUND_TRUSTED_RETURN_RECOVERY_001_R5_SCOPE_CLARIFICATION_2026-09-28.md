# CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001 — R5 Scope Clarification

Date: 2026-09-28

Pre-ruling live main: `092e895019632016224b526f01d5014b6bd19162`

Engineering PR: #258

Observed engineering WIP at adjudication:

`0de7b2f4ec5d59b36aea13a2d18677d8772bb977`

Engineering STOP comment:

`5863435728`

## Decision

The engineer correctly preserved a RED observation and stopped rather than weakening the contract. The observation is real:

- after a background attempt is already durably metered but before outer Wake completion;
- fresh Core can recover the trusted exact response;
- `CognitiveRuntime.model_usage_recorder` is entered again for that already-metered attempt;
- the durable metering ledger remains one row.

However, **callback/function re-entry by itself is not a frozen-contract duplicate semantic application**.

The binding R5 requirement is clarified as **exactly-once durable effect**, not zero internal function re-entry.

This ruling preserves the engineering STOP as historical evidence. It does not relabel the observation false and does not delete any RED or workflow history.

## Why this clarification is required

The original RERUN-002 state-loss contract requires:

- recovery after model/capability work before ACK;
- same durable cursor convergence;
- no duplicate reveal;
- no duplicate ingest;
- no duplicate semantic application;
- no skipped/duplicate ACK.

The original persistence corrective likewise requires no duplicate reply application/ACK and exactly-once recovery.

Core metering is intentionally recorded **before capability execution**. Therefore a `metered` attempt is not a durable proof that downstream capability/semantic application is complete.

If Core treated `metered` as "application complete; only ACK may remain", a crash in the legal window:

`metered -> before capability execution`

could silently skip required downstream work.

A new generic post-application checkpoint would be a separate product architecture change and is not required merely to close the trusted-return handoff gap.

## Binding R5 semantics

For an authenticated exact response that is already durably metered before outer completion, recovery MAY re-enter the exact deterministic/idempotent downstream application path when no stronger durable application/completion receipt exists.

The following are mandatory:

1. no provider redispatch;
2. no second provider request identity;
3. no duplicate durable metering record;
4. no duplicate capability side effect;
5. no duplicate semantic/World write;
6. no duplicate assistant output or delivery;
7. no duplicate turn/Wake/review completion receipt or ACK;
8. exact attempt / round / request / response identity remains unchanged;
9. any replayed capability/application uses the same durable identity/write-time/idempotency boundary;
10. conflicting replay remains fail-closed.

**Entering an idempotent recorder or application function is not, by itself, a duplicate application if it produces no second durable effect.**

## Stronger durable completion receipts still short-circuit

Where a stronger terminal receipt already exists, runtime replay must not occur.

Examples already represented in Core include:

- durable user-turn assistant output / completed execution;
- durable Wake assistant delivery before Wake terminal completion.

Those paths must mechanically finish completion/ACK without model/provider redispatch or downstream semantic replay.

## Required engineering closure on PR #258

PR #258 remains **DRAFT / NOT REVIEW_READY** until engineering adds explicit R5 regression evidence under this clarified binding.

At minimum prove:

### R5-A — metered final response, no terminal delivery/completion yet

Crash after exact response is metered but before outer completion.

Fresh recovery may mechanically replay the authenticated directive, but must prove:

- provider calls unchanged;
- one meter row only;
- no duplicate World/semantic write;
- no duplicate assistant delivery/output;
- exactly one terminal completion/ACK.

### R5-B — metered capability directive, capability application incomplete

Crash after metering but before capability side effect.

Fresh recovery must execute the required capability exactly once and complete.

### R5-C — capability side effect already durable, outer ACK incomplete

Crash after capability side effect is durable but before outer ACK.

Fresh recovery may traverse the idempotent capability/application path, but the durable capability side effect and World revision/object identity must not duplicate.

### R5-D — stronger terminal delivery/output already durable

Fresh recovery must use the existing completion-recovery shortcut and must not re-enter the model/provider path.

The tests must assert durable identities/counters, not merely callback invocation counts.

## Disposition

```text
CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001
= IN_PROGRESS / R5_SCOPE_CLARIFIED / NOT_REVIEW_READY

PR #258
= DRAFT / CONTINUE_ENGINEERING

NEW POST-APPLICATION CHECKPOINT ARCHITECTURE
= NOT REQUIRED BY THIS TASK
```

No Independent Acceptance is authorized until a new exact PR #258 candidate closes R1-R5 under this ruling and formal gates are green.

All downstream tasks remain BLOCKED.
