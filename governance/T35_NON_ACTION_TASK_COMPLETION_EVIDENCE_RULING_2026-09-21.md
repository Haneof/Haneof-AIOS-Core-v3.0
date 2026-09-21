# T35-RULE-001 — Non-Action Task Completion Evidence Ruling

> Status: NORMATIVE PROJECT RULING FOR T35 IMPLEMENTATION  
> Task: `T35-RULE-001`  
> Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
> Intake main SHA: `f8a2f8e4cf53de579bd0bc69cfd85421d109d65b`  
> Governance claim commit: `f83438729b7ef0a0ba58b0c3302e1deb5f4ca6bd`  
> Date: 2026-09-21  
> Scope: semantic/contract ruling only. This document does not modify runtime, schema, state-machine code, or authorization behavior.

## 1. Decision

The current universal rule "every COMPLETED / FAILED Task must reference an `Outcome` object" is too broad.

The controlling rule is:

> **A Task terminal transition MUST be grounded in pinned, durable evidence that satisfies that Task's explicit completion contract. An `Outcome` object is mandatory when the Task requires an AIOS-initiated external action or other real execution result. A Task that can be resolved entirely from durable world evidence or a durable internal work product MUST NOT be forced to fabricate an Action or Outcome.**

This ruling does not weaken the external-action boundary.

For external execution:

```text
Task
  -> Action proposal
  -> authorization
  -> external execution
  -> Outcome
  -> Task COMPLETED / FAILED
```

remains mandatory.

For a non-Action Task:

```text
Task
  -> real/pinned World evidence or validated internal artifact
  -> evidence-grounded terminal transition
```

is valid without inventing an Action or Outcome.

The model saying "done" is never completion evidence.

## 2. Controlling sources reviewed

This ruling is based on the current fused baseline and current implementation at the intake main.

### 2.1 Fused baseline

`docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md`  
blob: `ac15b6e404b3737037a975137b0f9475ffa9908c`

Relevant principles:

- deterministic infrastructure owns data structure, references, permissions, hard boundaries and auditable state machines;
- AI owns high-level understanding, but that understanding does not itself become factual truth;
- Observation / Evidence / Claim / Summary / Goal / Task / Action / Outcome are all first-class World objects with different semantics;
- model output itself must not automatically become fact;
- external action remains authorization-bound.

### 2.2 Goal / Task constitution

`docs/constitution/AIOS_v3.0_Goal_Task_Constitution.md`  
blob: `28980c40d8c4d09da47b1ede92819cf3ffc4fde7`

The apparent tension is inside the same document:

- the heading says Task completion must have real Outcome;
- the operative condition says **"when a Task involves a real execution result"**, use `Action -> Outcome -> Task Completed/Failed`;
- the prohibition says a **real-world task** must not be declared complete without Outcome;
- the root definition says whether **reality was actually completed** is ultimately spoken by Outcome.

The narrow external-execution reading is therefore more consistent than a universal typed-Outcome requirement.

### 2.3 Current typed contracts

`src/aios_core/contracts/models.py`  
blob: `dd37b83a1ae151974ad74055095e15e7ec533c99`

Current `Outcome` requires a pinned `action_ref`. It is therefore structurally an Action result object, not a generic "anything finished" record.

Forcing an internal verification, analysis, review or information task to create an `Outcome` would also force a fake Action lineage. That is semantically incorrect.

### 2.4 Current execution implementation

`src/aios_core/execution/service.py`  
blob: `3bbb1362af254c9e0a43234943c3069211077584`

Current behavior:

- `TaskTransitionRequest` rejects every COMPLETED / FAILED transition without `outcome_refs`;
- `transition_task()` requires every `outcome_ref` to point to ObjectType.OUTCOME.

This is the implementation gap identified by Issue #35; it is not the final semantic rule.

### 2.5 Resident capability surface

`src/aios_core/runtime/turn_runtime.py`  
blob: `2ac4f304722aa0db08671d9501fa0a90db6b0d7c`

The Resident can transition Tasks and propose Actions. The capability description currently repeats the universal Outcome requirement. There is no generic Resident capability that can honestly create a non-Action Outcome.

### 2.6 P15 precedent

`src/aios_core/review/periodic.py`  
blob: `148643f866eefcbe40a2ee0a33e0c81a43dc745b`

P15 already distinguishes a learned/derived object from its real result evidence:

- OperationExperience must be grounded in real result cases;
- accepted case types include real Observation / Outcome / CommunicationExperience;
- assistant raw Observation is explicitly rejected as real result evidence.

This is the correct direction for T35: derived cognition may depend on real evidence, but it must not replace the evidence.

### 2.7 Current audit and live reproduction

`reviews/AUDIT-001_ISSUE30_CURRENT_MAIN_EVIDENCE_MATRIX_2026-09-21.md`  
blob: `172dc36caec8474d72850170f95bd3417b6455e0`

AUDIT-001 revalidated T35 as `STILL_OPEN`: a verification Task grounded by real user/photo Observations cannot reach COMPLETED because the current implementation demands typed Outcome refs.

Issue #35 documents the same lifecycle mismatch.

## 3. A — Task classification

### 3.1 Do not add new TaskType categories for this ruling

The existing `TaskType` enum describes work shape/scheduling intent:

- immediate
- scheduled
- deadline
- todo
- recurring
- follow_up
- observation
- verification
- maintenance
- app

It does **not** safely answer whether completion requires an external side effect.

For example, a scheduled Task can be either:

- "at 15:00 verify whether a report arrived" — no external action; or
- "at 15:00 send the report" — external action required.

Therefore T35 MUST NOT overload `TaskType` as an authorization/completion category.

### 3.2 Completion mode is an orthogonal completion contract

Each Task needs an explicit, structured completion-evidence mode attached to its completion contract. The implementation may encode this in the existing structured `completion_condition` or in an equivalent explicit contract field, but it MUST NOT infer it from natural-language title/reason text.

The semantic modes are:

1. **WORLD_EVIDENCE**
   - completion can be established entirely from durable World evidence or a durable internal work product;
   - no AIOS external side effect is required.

2. **ACTION_OUTCOME**
   - satisfying the Task requires an AIOS-initiated external side effect or other authorized execution;
   - Action -> Outcome is mandatory.

3. **MIXED**
   - completion criteria contain both internal/world-verification and external-execution requirements;
   - both evidence classes are mandatory for the relevant criteria.

This is not a second Task system and not a second Outcome type. It is a completion contract for the existing Task.

### 3.3 Legacy Tasks

A legacy Task with no explicit completion mode MUST be handled fail-closed.

Deterministic code MUST NOT guess external-vs-internal from free text.

A migration or compatibility rule may mechanically classify clearly non-external existing enum cases such as `VERIFICATION`, `OBSERVATION`, and internal `MAINTENANCE`, but ambiguous generic types such as `TODO`, `FOLLOW_UP`, `SCHEDULED`, `DEADLINE` and `APP` require an explicit completion contract before the universal Outcome requirement can be relaxed.

If a Task already has an Action lineage, it cannot be reclassified to WORLD_EVIDENCE merely to bypass Outcome.

## 4. B — What counts as trustworthy completion evidence

All refs used for a terminal transition MUST:

- be pinned to exact revisions;
- belong to the same subject/private world;
- exist durably in WorldStore;
- be relevant to the Task's explicit completion condition;
- preserve provenance;
- not depend on the Task's own terminal assertion as their source of truth.

### 4.1 Observation — YES, conditionally

A real Observation may directly establish a non-Action completion condition.

Examples:

- user confirms the sister was picked up;
- sensor records the target condition;
- platform reports a receipt/state;
- a photo-derived Observation records the verified real state.

An assistant raw-dialogue Observation is **not** sufficient primary completion evidence merely because the assistant said it.

### 4.2 EvidenceSet — YES as a container, never as magic truth

EvidenceSet is an acceptable completion-evidence wrapper if its pinned members are themselves eligible and actually support the completion condition.

An EvidenceSet does not upgrade weak, circular or assistant-self-authored material into truth.

A stale or materially incomplete EvidenceSet is insufficient for a terminal transition whose condition depends on the missing evidence.

### 4.3 Claim — CONDITIONAL

A Claim may serve as a durable work-product/result for a cognition or analysis Task **only when**:

- producing that evidence-grounded Claim is itself the Task's completion condition;
- the Claim is current and supported by pinned evidence;
- the Task is not using the Claim as a substitute for a missing real-world result.

An unsupported, self-referential or merely model-authored Claim cannot complete a Task.

For a verification Task about reality, the underlying Observation/EvidenceSet remains the primary result evidence; a Claim may explain the conclusion but does not replace the reality evidence.

### 4.4 Review result — YES only through durable outputs

There is no generic free-form "review result" that can be trusted because the model says a review occurred.

A review Task may be completed from its durable outputs, such as:

- pinned EvidenceSet;
- current evidence-grounded Claim;
- validated Summary;
- other typed review artifacts permitted by the Task contract.

A `Wake(COMPLETED)` proves that a review execution loop finished; by itself it does not prove the reviewed proposition is true.

### 4.5 Summary — CONDITIONAL

A current, non-stale Summary may complete a Task whose deliverable is itself a summary/report, provided its source revision/evidence provenance satisfies the Task's completion contract.

A Summary does not prove an external side effect occurred and cannot substitute for Outcome in an ACTION_OUTCOME Task.

### 4.6 World revision — NO, not by itself

A `world_revision` is a provenance/snapshot anchor.

It can prove "this was the world state we evaluated", but it cannot by itself prove that the Task's completion condition was satisfied.

The evidence must still name the relevant typed WorldObjects.

### 4.7 Validated artifact — YES, if durably represented and validated

A generated/checked artifact can be completion evidence for an internal work-product Task when its existence and validation are durably represented in the World by appropriate typed evidence/provenance.

A bare path, filename, model assertion, or transient in-memory object is insufficient.

If the artifact was validated by a platform, tool, user or deterministic validator, that validation must be represented by pinned durable evidence.

### 4.8 Explicit user confirmation — YES as user Observation

Explicit user confirmation is real reported-world evidence and can satisfy a WORLD_EVIDENCE completion condition when the condition is defined that way.

It cannot retroactively authorize an external Action that was never authorized.

If AIOS itself executed an external side effect, user confirmation may supplement the result but does not erase the Action -> Outcome audit trail.

### 4.9 External platform receipt — YES

If the receipt is the result of an AIOS Action, it belongs in the Action-linked Outcome path.

If AIOS did not initiate the external event and the Task is merely observing/verifying it, a trusted platform Observation may satisfy a WORLD_EVIDENCE condition.

### 4.10 OperationExperience — NO as original completion result

OperationExperience is learned, derived cognition about prior cases.

It MUST NOT be the primary/direct evidence used to close the Task whose result produced that experience.

Doing so would create a circular chain:

```text
Task says done
 -> OperationExperience says it worked
 -> OperationExperience used to prove Task was done
```

That is forbidden.

OperationExperience may be produced **after** real completion evidence exists, and may guide future cognition, but it is not the original result credential.

## 5. C — Objects/statements that cannot be completion credentials

The following MUST NOT by themselves justify COMPLETED or FAILED:

1. assistant raw response / assistant raw dialogue;
2. an unverified or unsupported Claim;
3. the Task object itself;
4. the parent Goal itself;
5. the transition request's reason string;
6. "the AI thinks it is done";
7. a synthetic/fake Outcome created only to satisfy schema;
8. an Outcome that is not tied to a real Action execution lineage;
9. OperationExperience as the primary result;
10. world_revision alone;
11. a completed Wake alone when the Task condition is semantic/real-world rather than merely "run this review";
12. a Summary or other derived artifact used as a substitute for missing external execution evidence.

## 6. D — COMPLETED and FAILED rules

### 6.1 COMPLETED

A Task may enter COMPLETED only when all mandatory completion criteria have positive pinned evidence.

For WORLD_EVIDENCE:

- evidence must establish the condition or prove the required internal artifact exists and is valid.

For ACTION_OUTCOME:

- a real Outcome tied to the authorized Action is mandatory;
- the Outcome state must support completion.

For MIXED:

- the internal criteria and the external Action/Outcome criteria must both be satisfied.

### 6.2 FAILED

FAILED is also an evidence-grounded terminal state.

For WORLD_EVIDENCE, FAILED requires pinned evidence of a terminal negative result, such as:

- validation proves the required artifact is invalid and the Task contract defines that as terminal;
- trusted world evidence proves the condition cannot/was not satisfied;
- an explicitly bounded verification concludes a defined negative result.

For ACTION_OUTCOME, FAILED requires a real Action-linked failure Outcome (or equivalent terminal external result represented through the existing Outcome contract).

Absence of evidence is **not** automatically failure.

When evidence is missing or ambiguous, the Task should remain in an appropriate non-terminal state such as WAITING_EVIDENCE / WAITING_USER / WAITING_RESULT / BLOCKED.

Deadline exhaustion should use EXPIRED where that state is the correct contract result; it must not be relabeled FAILED merely to escape evidence requirements.

`OUTCOME_UNKNOWN` must not be converted into a fake success/failure; it normally leaves the Task waiting for resolution unless the Task's explicit contract defines a separate terminal handling path.

## 7. E — Relationship to Action / Outcome

This ruling MUST NOT create an external-action bypass.

The following are invariant:

1. Resident AI cannot authorize its own external Action.
2. If satisfying a Task requires an external side effect initiated by AIOS, the Task is ACTION_OUTCOME or MIXED.
3. Such a Task cannot reach COMPLETED / FAILED without the real Action-linked Outcome required by that mode.
4. A user Observation, Claim, Summary, Review artifact or internal evidence cannot be substituted for a missing required Outcome.
5. A WORLD_EVIDENCE Task must not create a fake Action solely to manufacture an Outcome.
6. Mixed Tasks must retain both sides of the audit chain.
7. Existing Action authorization and T34 cancellation/race rules remain independent and must not be weakened by T35.

## 8. Minimal consistent interpretation of the constitutional ambiguity

### Interpretation A — universal typed Outcome

Support:

- Article 6 heading can be read literally as "all Task completion requires Outcome";
- one sentence says Completed / Failed must reference actual Outcome.

Problem:

- current Outcome structurally requires `action_ref`;
- therefore a pure verification/review/analysis Task would need a fabricated Action lineage;
- that conflicts with the same article's conditional "when a Task involves a real execution result";
- it also conflicts with the prohibition specifically phrased around real-world tasks;
- it would blur the external authorization boundary by making Action/Outcome generic internal paperwork.

### Interpretation B — Outcome mandatory for real external execution; evidence mandatory for every terminal transition

Support:

- operative constitutional wording conditions Action -> Outcome on real execution;
- prohibition is specifically about real-world tasks;
- current Outcome model is Action-bound;
- fused baseline separates fact/evidence/cognition and forbids model output from automatically becoming fact;
- P15 already uses real evidence for internal learning without synthesizing Outcome.

### Ruling

**Interpretation B is adopted.**

It is the smallest reading that preserves every hard safety/audit property while removing the false requirement to invent external execution objects for non-Action work.

## 9. Implementation contract for T35-IMPL-001

T35-IMPL-001, when unblocked by T34, MUST implement this ruling with the smallest compatible change.

It MUST:

1. retain pinned `evidence_refs` for terminal transitions;
2. retain the current strict Outcome requirement for ACTION_OUTCOME;
3. add/consume an explicit structured completion mode; do not infer it from free text;
4. allow WORLD_EVIDENCE completion/failure without `outcome_refs` when eligible evidence satisfies the Task completion contract;
5. require both evidence families for MIXED;
6. reject assistant raw dialogue as sole real-result evidence;
7. reject Task/Goal/self-assertion/circular OperationExperience evidence;
8. preserve forward revisions and history;
9. preserve subject isolation;
10. preserve existing Action authorization and Outcome lineage;
11. avoid a second execution system, second Task model or second Outcome object type;
12. add migration/compatibility handling for legacy Tasks without silently loosening ambiguous external tasks.

It SHOULD normalize terminal evidence into the existing dependency/evidence graph so that the system can answer:

- what condition was evaluated;
- what exact revisions supported it;
- why the Task became COMPLETED or FAILED;
- whether an external Action/Outcome was required;
- what later evidence could challenge the conclusion.

## 10. Examples

### 10.1 Verification Task — valid without Action

Task: "verify whether both the flour delivery and airport pickup succeeded."

Evidence:

- user Observation says both succeeded;
- photo/platform Observation corroborates if available.

Mode: WORLD_EVIDENCE.

Result: Task may become COMPLETED from pinned evidence. No Action/Outcome is invented.

### 10.2 Internal analysis Task

Task: "review the evidence and form a supported conclusion."

Evidence/result:

- EvidenceSet;
- evidence-grounded current Claim.

Mode: WORLD_EVIDENCE.

Result: COMPLETED when the required durable analysis artifact exists and its evidence contract is satisfied.

### 10.3 External send Task

Task: "send the approved report to the team channel."

Mode: ACTION_OUTCOME.

Required chain:

```text
RUNNING Task
 -> PROPOSED Action
 -> authorized/submitted Action
 -> platform execution
 -> Outcome
 -> COMPLETED/FAILED Task
```

A user saying "probably sent" or the assistant saying "done" cannot replace the Outcome.

### 10.4 Mixed Task

Task: "verify the report content, then send it."

Mode: MIXED.

Required:

- world/internal evidence that verification passed;
- authorized Action and real Outcome for sending.

Neither side can substitute for the other.

## 11. Non-goals

This ruling does not:

- implement T35;
- modify `execution/service.py`;
- modify Task schema;
- modify state-machine transitions;
- resolve T34;
- define T33/T28 recall semantics;
- create a generic Outcome;
- allow model self-declared completion.

## 12. Final T35-RULE-001 verdict

The unique rule is:

> **Every Task terminal transition is evidence-grounded. Outcome is a specialized, mandatory completion credential for Tasks whose completion requires authorized external execution; it is not a universal wrapper for all work. Non-Action Tasks may complete/fail from pinned, eligible World evidence or validated durable internal artifacts, while assistant self-assertion, unsupported cognition, circular experience records, and synthetic Outcomes remain invalid.**
