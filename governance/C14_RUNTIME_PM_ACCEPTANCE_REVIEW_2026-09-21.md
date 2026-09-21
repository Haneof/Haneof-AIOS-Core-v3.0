# C14-RUNTIME-001 PM Acceptance Review — Side-Effect Escape Blocker

> Status: **BLOCKER FOUND / HARDENING REQUIRED BEFORE C14-LOOP-001**  
> Date: 2026-09-21  
> Reviewed main: `97554b041768d93a6ab9f83d80e87f27972eeaf0`  
> Reviewed task: `C14-RUNTIME-001`  
> Reviewed PR: #61  
> Candidate: `75cc62ca13169c6ba8752e0562224705fe6f9ac2`  
> Core squash merge: `a887ba537e9797d4bf5a7b7fb482fa4a55f47df7`

## 1. What passed

The accepted C14 Runtime implementation correctly:

- routes `COGNITIVE_DERIVATION` through the existing `FusedTurnRuntime -> CognitiveRuntime`;
- uses the existing model handler, tool loop, Wake lifecycle and C13 non-world metering;
- provides an exact pinned Summary cockpit with scheduler/runtime lineage audit;
- shares the C14 provenance resolver rather than creating a second provenance algorithm;
- leaf-grounds `commit_claim`, `commit_ai_world_claim`, `revise_claim`, and `retract_claim`;
- blocks Summary-only / old-AI-Claim recursive support for those Claim paths;
- preserves legitimate real Outcome / operation-case grounding;
- preserves T28 assistant/user separation;
- treats silence as successful zero-semantic-write completion;
- suppresses direct user delivery for COGNITIVE_DERIVATION;
- passes the required candidate and merge-result regression gates.

These parts are accepted and should not be redesigned.

## 2. Blocker discovered during PM side-effect audit

The C14-specific branch in `FusedTurnRuntime._authorize_side_effect()` currently denies:

- `commit_operation_experience`
- `record_communication_experience`
- `propose_cognitive_policy`
- `update_cognitive_policy`
- `rollback_cognitive_policy`

but then falls through to the normal side-effect allowlist.

Therefore a `COGNITIVE_DERIVATION` Resident can still request durable writes through capabilities including:

- `propose_entity`
- `revise_entity`
- `upsert_relation`
- `propose_dimension`
- `transition_dimension`
- `propose_goal`
- `transition_goal`
- `create_task`
- `transition_task`
- `create_attention_watch`
- `propose_action`
- `form_event`
- `transition_event`

These are outside the C14 derivation write contract and create a bypass around the intended "leaf-grounded cognition OR silence" boundary.

## 3. Why this is a real boundary bypass

The C14 grounding validator is invoked only from:

- `commit_claim`
- `commit_ai_world_claim`
- `revise_claim`
- `retract_claim`

The other writable capabilities do not pass through `_validate_c14_cognition_grounding()`.

At least two existing service paths were independently inspected:

### Event

`EventDimensionService.form_event()` requires pinned refs and same-subject refs, but it does not enforce the C14 support-provenance closure rule. A Summary ref can therefore satisfy the ordinary structural input contract without proving a qualifying C14 grounding leaf.

### Dimension

`DimensionRegistryService.propose()/transition()` validates persisted refs and normal dimension contracts, but it does not apply the C14 derivation-specific leaf-grounding closure.

Runtime handlers for Goal/Task/Action/Entity/Relation/AttentionWatch likewise do not invoke the C14 grounding validator before dispatching to their existing services.

This means a model could fail a Summary-only Claim write and still persist a different semantic/execution object from the same background derivation opportunity.

Examples of prohibited escape shapes include:

```text
Summary
 -> COGNITIVE_DERIVATION
 -> form_event(summary-only evidence)
 -> durable Event
```

or:

```text
Summary
 -> COGNITIVE_DERIVATION
 -> propose_goal / create_task / create_attention_watch
 -> persistent execution/attention state
```

This violates C14's scope and risks semantic/execution spam even though the Claim path itself is correctly protected.

## 4. PM ruling for the repair

Create a dedicated one-window task:

`C14-RUNTIME-HARDEN-001`

The preferred minimal repair is:

> During `COGNITIVE_DERIVATION`, side-effect authorization is an explicit allowlist containing only the C14-approved durable cognition operations: `commit_claim`, `commit_ai_world_claim`, `revise_claim`, and `retract_claim`.

All other side-effecting capabilities remain visible only if normal capability-catalog semantics require visibility, but their execution must be denied during this Wake source.

Read capabilities remain available.

This restriction is **only** for `COGNITIVE_DERIVATION`. It must not remove legitimate write capabilities from:

- direct user turns;
- Periodic Review;
- other Wake classes where existing law permits them.

Do not solve this by adding C14 leaf validators independently to every Goal/Task/Event/Entity/Dimension service. C14 is a bounded cognition-derivation Wake, not a universal alternate execution entry point.

If implementation evidence proves one additional write operation is constitutionally necessary for C14, it must be explicitly justified against the ruling before being added to the allowlist. Convenience is not sufficient.

## 5. Required regressions

The hardening task must prove that, during `COGNITIVE_DERIVATION`:

- the four approved Claim create/revise/retract paths remain authorized and leaf-grounded;
- `form_event` is denied before durable Event write;
- Entity/Relation writes are denied;
- Dimension proposal/transition writes are denied;
- Goal/Task/Action proposal/transition writes are denied;
- AttentionWatch creation is denied;
- Experience/Policy writes remain denied;
- read-only search/inspect/compare/ALL_DIMENSIONS remain available;
- denial does not create fake Claim/Outcome/Experience;
- silence remains valid;
- direct user turn and Periodic Review write behavior is not regressed.

## 6. Acceptance decision

`C14-RUNTIME-001` implementation is substantially correct, but **C14 Runtime is not yet PM-accepted for downstream LOOP/Resident testing** because the derivation Wake still has alternate durable-write escape routes.

Therefore:

- keep historical `C14-RUNTIME-001 = DONE` as the merged implementation record;
- insert `C14-RUNTIME-HARDEN-001 = READY`;
- block `C14-LOOP-001` on the hardening task;
- do not start `C14-RES-001` or P16.
