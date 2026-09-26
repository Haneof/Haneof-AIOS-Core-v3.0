# C15-RCC B Persistence Corrective — Core Recovery Adjudication

Date: 2026-09-26
Repository: `Haneof/Haneof-AIOS-Core-v3.0`
Reviewed live main: `f0f2eb8a7030b9b56cbec43c09574e056b2f7c61`

## Verdict

`C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 = FROZEN_WIP / BLOCKED_ON_CORE_RESPONSE_RECOVERY`

New unique READY task:

`CORE-BACKGROUND-RESPONSE-RECOVERY-001`

This ruling does not accept or reject the partial persistence-corrective implementation. It freezes that work because the current frozen Core lacks the exact recovery continuation required to close the task without lying about provider execution or reimplementing cognition in operator scripts.

## Mechanism finding

Fresh source inspection on live main confirmed the following existing behavior:

1. Background model attempts persist durable states including:
   - `admitted`
   - `dispatching`
   - `not_submitted`
   - `in_doubt`
   - `response_returned`
   - `metered`

2. `BackgroundModelAttemptStore.reconcile_response(...)` can mechanically reconcile a durable provider response into `response_returned` when exact external evidence is available.

3. However normal `FusedTurnRuntime` / `CognitiveRuntime` re-entry cannot continue from that state:
   - model-attempt admission runs before the model handler;
   - an existing `dispatching` attempt becomes `in_doubt`;
   - `response_returned` raises `BackgroundModelResponsePending`;
   - the headless CLI exposes this only as `reconciliation_required`;
   - no current headless/runtime continuation consumes a reconciled exact `ModelDirective` and resumes downstream capability/response/silence application without a second provider dispatch.

4. `TurnExecutionStore.authorize_retry(...)` intentionally refuses retry when provider execution is not proven absent. That fail-closed behavior is correct and MUST NOT be weakened.

Therefore an operator-only journal cannot by itself prove the required crash point:

`reply durably staged -> process death -> same response applied exactly once -> no second provider call`

without either:
- falsely rewriting provider execution as not-submitted; or
- duplicating CognitiveRuntime semantic application in an external script.

Both are forbidden.

## Scope decision

The persistence corrective remains conceptually correct and its partial work may be preserved, but it must not continue past this blocker until Core exposes a narrow crash-safe response-resume mechanism.

The current persistence-corrective window must preserve its WIP, red evidence, 158/158 regression result and synthetic journal tests on a dedicated branch/commit, then stop. It must not self-expand into Core changes.

## CORE-BACKGROUND-RESPONSE-RECOVERY-001 contract

Role: Core Runtime Recovery Engineer.

Goal: add the smallest Core mechanism that allows a previously returned, externally durably preserved and cryptographically/provenance-bound model response to resume the same background model round exactly once after crash, without invoking the provider again.

Required properties:

1. **No provider re-dispatch**
   - recovery from a proven `response_returned` state must not call the model handler/provider;
   - request/response identity must stay bound to the original attempt/round.

2. **Exact directive verification**
   - recovery input must be the exact persisted provider reply / parsed `ModelDirective`;
   - Core must verify it against durable attempt provenance and response fingerprint before application;
   - mismatched provider/model/request_id/fingerprint/directive must fail closed.

3. **No semantic reconstruction**
   - Core/operator must not infer or regenerate a lost response;
   - no fixture, keyword logic or default semantic directive;
   - if exact reply bytes/directive are unavailable, remain `in_doubt` / blocked.

4. **Exactly-once downstream application**
   - response/silence/capability calls selected by that exact directive must be applied through the normal CognitiveRuntime path, not a duplicate operator semantic engine;
   - crash during or after capability application must converge without duplicate side effects;
   - metering must remain exactly once or idempotently converge.

5. **State machine preservation**
   - existing `not_submitted` safe retry behavior remains unchanged;
   - existing `in_doubt` fail-closed behavior remains unchanged unless explicit reconciliation evidence proves the exact returned response;
   - ordinary non-recovery model path semantics must remain byte/behavior compatible.

6. **Recovery API**
   - expose a narrow programmatic/headless recovery surface sufficient for operator orchestration;
   - it must be explicit, auditable and impossible to trigger with only self-asserted provider metadata.

7. **Fault-injection matrix**
   Fresh tests must include:
   - crash after dispatch before response is known -> remains in_doubt;
   - exact response reconciled -> no provider second call;
   - crash after reconciled response before semantic application;
   - crash during capability application;
   - crash after response/silence application before completion marker;
   - restart repeats -> exactly-once durable result;
   - wrong fingerprint/request/provider/model -> hard red;
   - missing exact response bytes -> hard red.

8. **No architecture expansion**
   - no second cognition store;
   - no second World;
   - no operator-owned semantic decision engine;
   - no relaxation of current provider-attempt safety.

## Required downstream sequence after Core fix

Because this task changes `src/aios_core/**`, the existing RC freeze no longer covers the software used by future Resident evidence.

Mandatory sequence:

1. `CORE-BACKGROUND-RESPONSE-RECOVERY-001`
2. `CORE-BACKGROUND-RESPONSE-RECOVERY-001-INDEPENDENT-ACCEPTANCE`
3. `CORE-RC-REFREEZE-002`
4. fresh `C15-RCC-RES-A-RERUN-003`
5. `C15-RCC-RES-A-RERUN-003-INDEPENDENT-ACCEPTANCE`
6. resume `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001` from its frozen WIP against the new frozen Core / new canonical A lineage
7. persistence corrective independent acceptance
8. `C15-RCC-RES-B-RELEASE-003`
9. fresh `C15-RCC-RES-B-RERUN-003`
10. B acceptance -> C -> evaluator -> close

Historical PR #205 remains canonical evidence for the old frozen Core only. It is not modified or reinterpreted as evidence for the future re-frozen Core.

## Non-actions

This adjudication:
- does not modify Core;
- does not run Resident A/B/C;
- does not reveal any real fixture cursor;
- does not accept the WIP persistence candidate;
- does not enter Independent Acceptance;
- does not mint a new B run/session identity.
