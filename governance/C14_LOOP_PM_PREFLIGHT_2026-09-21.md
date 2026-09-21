# C14-RUNTIME-HARDEN-001 PM Acceptance + C14-LOOP Preflight

> Date: 2026-09-21  
> Reviewed main: `c12b9418bf68f3885713819432ac77bb585172ff`  
> Reviewed PR: #63  
> Candidate: `3accaeebe8ee1b3d420d2dfa3528ecb5e7388d86`  
> Core squash merge: `09002ddf8fd1fd4af08f54ac5b190d4c39c9e25b`

## 1. PM acceptance

`C14-RUNTIME-HARDEN-001 = PASS`.

Independent verification confirmed:

- `COGNITIVE_DERIVATION` side effects are now explicit default-deny;
- only `commit_claim`, `commit_ai_world_claim`, `revise_claim`, and `retract_claim` are authorized;
- all four still pass the existing C14 leaf-grounding validator;
- all present non-approved durable write capabilities are denied before handler invocation;
- a synthetic future WRITE capability is also denied;
- `CapabilitySpec` automatically marks WRITE/ACTION capabilities as side-effecting, so this default-deny is structurally future-safe;
- CognitiveRuntime invokes the side-effect authorizer before registry handler execution;
- non-side-effecting reads remain available;
- user interaction and Periodic Review keep their existing authorization behavior;
- candidate and squash-merged Core/test blobs are identical;
- required candidate Gates are GREEN.

No new blocker remains in C14-RUNTIME-HARDEN-001.

## 2. LOOP preflight finding A — C14 bundling must preserve the derivation execution contract

Current `FusedTurnRuntime.run_wake()` explicitly includes `WakeSource.COGNITIVE_DERIVATION` in `bundle_excluded_sources`.

Therefore C14 derivation Wakes currently do **not** participate in the normal AttentionBundle path. This is safe but does not yet satisfy the C14-LOOP requirement to coalesce large sibling derivation bursts.

A naive fix that merely removes `COGNITIVE_DERIVATION` from `bundle_excluded_sources` is unsafe.

The normal AttentionRouter emits:

`WakeSource.ATTENTION_BUNDLE`

and current runtime behavior selects several C14 protections by checking the active/running wake source directly:

- derivation-specific cockpit/instruction;
- `_active_wake_source` used by leaf-grounding enforcement;
- derivation-specific side-effect authorization;
- derivation-specific delivery suppression.

If C14 members are mechanically bundled but runtime sees only `ATTENTION_BUNDLE`, the bundle can silently lose the C14 execution contract.

### LOOP acceptance rule

C14-LOOP must make C14 coalescing **contract-preserving**.

At minimum:

- 10+ sibling C14 derivation opportunities within the mechanical window can be coalesced;
- a C14 derivation bundle must retain C14 cognition-only write restrictions;
- it must retain derivation-specific evidence/cockpit semantics for every member Summary;
- it must remain no-user-delivery background work;
- member Summary refs and member Wake refs must remain pinned/auditable;
- no member is silently discarded;
- no child can be re-run independently after durable merge unless recovery semantics require it;
- C14 derivation Wakes must not be mixed into an ordinary background bundle that grants a broader side-effect contract.

Preferred safe interpretation:

> bundle only members that share the same effective execution contract, or otherwise apply the strictest contract deterministically.

For C14, homogeneous COGNITIVE_DERIVATION bundling is the simplest acceptable design.

Do not use semantic similarity to choose bundle membership.

## 3. LOOP preflight finding B — model/tool budget exhaustion is not semantic completion

Current ordinary `run_wake()` calls `wake_bus.complete()` after `CognitiveRuntime.run_turn()` without first distinguishing successful terminal reasons from budget exhaustion.

`CognitiveRuntime` can terminate with non-semantic-completion reasons including:

- `model_round_budget_exhausted`
- `tool_round_budget_exhausted`
- `capability_call_budget_exhausted`

For Periodic Review, a similar condition is already treated as resumable rather than complete.

For C14 derivation, marking a budget-exhausted run COMPLETED can lose unresolved cognitive work and incorrectly turn:

> "the model ran out of execution budget"

into:

> "the cognition opportunity was fully processed."

### LOOP acceptance rule

For C14 derivation / C14-aware bundles:

- only true semantic terminal states such as `responded` or `silence` may close the derivation opportunity;
- runtime/tool/capability budget exhaustion must leave durable resumable work;
- restart must be able to continue/retry without duplicating already committed semantic writes;
- pre-model budget DEFER remains pending;
- HARD_DENY must have a durable disposition and must not be recorded as cognition/silence;
- a partial run must not be counted as a successful cognition conversion.

The exact state transition may reuse existing Wake lifecycle semantics, but it must be dispatchable/recoverable after restart.

## 4. Existing LOOP requirement — provenance reconciliation scale

The previous PM finding remains mandatory:

Current `CognitiveDerivationScheduler.reconcile()` can rebuild the full support-Dependency view once per Summary lineage derivation.

C14-LOOP must remove avoidable Summary x Dependency full-graph repetition using a bounded mechanical approach, such as:

- one support graph build per reconcile pass;
- safe per-pass cache;
- or an incremental equivalent.

This must not introduce:

- a second provenance truth;
- a semantic importance index;
- another scheduler database.

## 5. Existing LOOP requirement — self excitation and Periodic Review coexistence

C14-LOOP must still prove:

- AI cognition write -> AI Summary cannot immediately self-trigger another derivation loop;
- pure AI_COGNITION_ONLY remains blocked;
- mixed lineage follows the ruling without promoting AI-authored material to user fact;
- Wake completion itself is never treated as user preference/success evidence;
- Periodic Review remains a long-horizon independent/backstop mechanism rather than being replaced by continuous derivation.

## 6. Existing LOOP requirement — new Runtime restoration

Before real Resident habitation, deterministic integration must prove:

- a legitimate durable cognition is committed;
- the original FusedTurnRuntime is destroyed;
- a new FusedTurnRuntime is constructed over the durable WorldStore/Index;
- a new session/runtime can recover the cognition through normal AIOS context/search capabilities;
- no previous in-memory model/session context is required.

Semantic behavioral use remains for `C14-RES-001`; LOOP only proves the engineering retrieval path.

## 7. Gate impact

C14-LOOP cannot PASS solely on existing Wake/Attention tests.

It needs targeted regressions for:

1. homogeneous C14 sibling burst coalescing;
2. no C14 contract laundering through `ATTENTION_BUNDLE`;
3. no mixing of C14 into broader-write background bundles;
4. model/tool/capability budget exhaustion remains resumable;
5. restart resumes unresolved C14 work;
6. already committed semantic writes are not duplicated after retry;
7. hard-deny/defer disposition;
8. Periodic Review coexistence;
9. bounded provenance reconciliation;
10. new-runtime cognition retrieval.

