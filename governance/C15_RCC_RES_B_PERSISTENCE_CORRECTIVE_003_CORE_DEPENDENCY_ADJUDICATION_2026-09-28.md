# C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003 — Core Dependency Adjudication

Date: 2026-09-28

## Decision

```text
C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003
= FROZEN_WIP / BLOCKED_ON_CORE_TRUSTED_RETURN_RECOVERY

CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001
= READY
```

This adjudication is not a persistence acceptance verdict and does not authorize Resident B or RELEASE-003.

## Fresh facts

- pre-adjudication live governance main: `809a2536c27621ba73a1f951d93caacbab972d0f`
- authoritative narrowed persistence scope: merged PR #255
- persistence PR #254: CLOSED / DRAFT / UNMERGED / FROZEN
- first Core scope-violating WIP: `f7848952b6519fc40f50806f4a4d8d350ac0f38a`
- PR #254 head when closed: `a2d815c9f5154d87a56b152ed7cf5d1eb1baaaae`
- PM STOP comment on #254: `5863009559`

The PR was closed only to stop continued active-PR workflow flooding after the PM STOP. Its branch, commits, comments and CI history remain preserved.

## Why Corrective-003 cannot legally close blocker C002-002 alone

The frozen RERUN-002 state-loss contract requires exactly-once convergence for a kill after provider request staging and before Resident reply, and for later reply/application boundaries. The original real incident had already crossed one production provider dispatch before environment loss.

Accepted Core deliberately enforces provider-return authenticity:

- `FusedTurnRuntime.stage_exact_background_response(...)` can stage externally durable exact bytes only against an existing durable attempt and a valid trusted-return authenticity proof.
- `BackgroundModelAttemptStore._capture_trusted_response_return(...)` is private and explicitly documented as wired only to the normal trusted provider-return callback.
- recovery callers are intentionally denied access to the HMAC authority/signing capability.
- metadata-only `reconcile_response(...)` is deliberately disabled because caller-computable identity/fingerprint cannot authenticate provider-return bytes.

Later-round process/environment loss can occur after provider submission/return but before Core's normal trusted-return callback has durably committed the receipt. At that point:

- provider redispatch is not allowed;
- exact external reply bytes may exist;
- Core attempt may be dispatching/in-doubt;
- no trusted authenticity receipt exists;
- current accepted Core has no legal continuation that both converges and preserves the authenticity invariant.

That is a Core recovery surface gap.

## Why PR #254's Core experiment is not accepted

WIP `f7848952...` added a public `stage_trusted_returned_background_response(...)` method in `src/aios_core/runtime/turn_runtime.py` and used externally supplied directive payload to invoke the private trusted-return receipt minting path.

That changes the previously accepted trust boundary and risks turning a recovery caller into a signing oracle. It cannot be introduced as an incidental change inside a C15 persistence harness PR.

Later #254 WIP heads continued to modify Core after the PM STOP. None are accepted candidates.

## Required next task

`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001` must establish a trusted durable provider-return handoff/recovery mechanism without giving a recovery caller generic authority to mint authenticity.

Binding prompt:

`governance/prompts/CORE_BACKGROUND_TRUSTED_RETURN_RECOVERY_001_2026-09-28.md`

After that Core task receives fresh Independent Acceptance and PM integration, a new Core RC freeze and fresh Resident-A lineage are mandatory before Corrective-003 may resume.

## Downstream status

BLOCKED:

- persistence Corrective-003 resume
- RELEASE-003
- RERUN-003
- ACCEPT-003
- Resident C
- evaluator
- closure

## Mandatory downstream sequence

Because this task changes accepted Core runtime/recovery semantics, the prior RC/A lineage cannot be silently reused.

Required order:

1. `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001`
2. `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-INDEPENDENT-ACCEPTANCE`
3. PM integration of the accepted Core exact candidate
4. `CORE-RC-REFREEZE-003`
5. `CORE-RC-REFREEZE-003-INDEPENDENT-ACCEPTANCE`
6. fresh `C15-RCC-RES-A-RERUN-004`
7. `C15-RCC-RES-A-RERUN-004-INDEPENDENT-ACCEPTANCE`
8. governance re-release / resume of frozen `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003`
9. fresh persistence Independent Acceptance
10. only then may `C15-RCC-RES-B-RELEASE-003` become eligible

A-003 remains immutable historical evidence for the pre-fix Core/RC; it is never rewritten or hash-swapped into the new lineage.
