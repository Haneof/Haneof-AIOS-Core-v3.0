# C15 Resident Cognitive Continuity Test Plan

> Status: PM-PLANNED / GOVERNANCE ONLY  
> Date: 2026-09-22  
> Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
> Purpose: make “model can change, Resident does not reset” an explicit AIOS acceptance gate.

## 1. Root objective

AIOS must not merely preserve user facts after a model/session replacement.

It must preserve the Resident AI's durable cognitive state:

- what the Resident currently understands about the user;
- what it understands about the long-term relationship/role;
- what it has learned about its own mistakes, limits and calibration;
- what strategies and operational lessons have been supported by real outcomes.

The bottom model is replaceable. The Resident cognitive state is not.

A model replacement may change wording, style, latency or raw reasoning ability. It must not silently reset valid durable cognition.

## 2. Existing mechanisms are authoritative

C15 must reuse the current unified AIOS mechanisms:

- WorldStore / WorldSearchIndex;
- Claim / EvidenceSet / Dependency / Revision;
- AI User Understanding;
- AI Self;
- Calibration;
- Strategy;
- OperationExperience / CommunicationExperience;
- Periodic Review;
- FusedTurnRuntime / CognitiveRuntime;
- ordinary AIOS retrieval and context recommendation.

C15 MUST NOT create:

- a second AI-self database;
- a persona prompt as a substitute for durable cognition;
- a benchmark-only memory store;
- a hidden model-to-model handoff summary;
- a deterministic “cognition compiler”.

## 3. Cognitive continuity families

C15 treats Resident cognitive continuity as four related families.

### 3.1 User understanding

Examples include identity, goals, behavioral patterns, preferences, collaboration style and current state.

User understanding is cognition about the user. It is not a copy of raw user facts.

### 3.2 Relationship / role

The Resident may form revisable understanding of how it should relate to and collaborate with this user/project.

This is not license to invent emotional or interpersonal facts without evidence.

### 3.3 Self / calibration

The Resident may learn about:

- mistakes it made;
- uncertainty or capability boundaries;
- cases where it over- or under-confidently interpreted evidence;
- methods that repeatedly failed or succeeded;
- commitments and role continuity.

Learned self cognition must be grounded in real cases. “I think I improved” is not evidence.

### 3.4 Strategy / experience

OperationExperience, CommunicationExperience and evidence-grounded Strategy cognition may capture methods that were supported or contradicted by real outcomes.

Experience does not automatically become policy.

## 4. Required evidence chain

The canonical learning chain is:

```text
Situation
  -> Resident Decision / Action / Communication
  -> real Outcome / user feedback / later world fact
  -> Periodic Review or other legally routed cognition opportunity
  -> OperationExperience / CommunicationExperience where appropriate
  -> Strategy / Calibration / Self / User-Understanding cognition
  -> later ordinary AIOS retrieval
  -> materially affected later behavior
  -> later reality may retain / weaken / revise / retract
```

No durable self-learning conclusion may terminate in:

- AI self-assertion;
- Summary-only recursion;
- old Claim -> new Claim with no new case evidence;
- Wake completion;
- Task completion without qualifying evidence;
- synthetic Outcome;
- evaluator expectation.

## 5. C14 repair prerequisite

C14 already demonstrated VALID fresh-window cognition recovery and material behavioral consumption, but its complete semantic evidence is NOT VALID because E1 is PARTIAL and E5 is INVALID.

C15 must not begin until C14 is closed with valid semantic evidence.

The C14 repair is deliberately narrow:

1. do not edit PR #75 / PR #79 historical evidence;
2. create a new sealed repair fixture targeting only the semantic-evidence defects;
3. obtain new real-Resident evidence for:
   - cross-dimensional Claim support closure with every material factual assertion pinned;
   - later revision/retention that distinguishes planned, observed and outcome facts;
4. independently evaluate the replacement evidence;
5. combine unchanged prior VALID findings with replacement evidence only after independent evaluation.

No Core change is implied by the current evaluator findings.

## 6. C15 task chain

```text
C15-RCC-RULE-001
  -> C15-RCC-PREFLIGHT-001
  -> C15-RCC-FIXTURE-001
  -> C15-RCC-RES-A-001
  -> C15-RCC-RES-B-001
  -> C15-RCC-RES-C-001
  -> C15-RCC-EVAL-001
  -> C15-RCC-CLOSE-001
```

### 6.1 C15-RCC-RULE-001

Freeze the semantic contract in this plan against the current constitutions.

This task writes governance only. It must not redesign Core.

### 6.2 C15-RCC-PREFLIGHT-001

Audit current main before implementing anything.

Prove which of these paths already exist:

- outcome-grounded OperationExperience creation;
- Self / Calibration / Strategy / User Understanding writeback;
- indexing and ordinary search/retrieval;
- runtime recommendation/context exposure;
- fresh Runtime restoration;
- revision / retraction;
- anti-self-proof and subject-isolation boundaries.

Each capability must be classified:

- `ALREADY_IMPLEMENTED`;
- `MECHANISM_GAP`;
- `INSUFFICIENT_EVIDENCE`.

If all required mechanisms already exist, no C15 Core implementation task is created.

If a real mechanism gap exists, PM creates one minimal dedicated implementation task. The test chain resumes only after that task's gates pass.

### 6.3 C15-RCC-FIXTURE-001

Create a sealed naturalistic life fixture.

It must contain unlabeled opportunities for:

- durable user-understanding formation;
- relationship/role learning;
- one genuine AI mistake with later real evidence/feedback;
- one genuinely successful method with later real outcome;
- an external-failure negative control that must not automatically become self-blame;
- later counterevidence capable of revising a strategy or calibration belief;
- a fresh-window decision after the A boundary;
- a different-model decision after the B boundary.

The fixture must not encode expected Claim strings or expected tool calls.

### 6.4 C15-RCC-RES-A-001

Resident A lives the released Phase-A events sequentially.

The model itself decides search/inspect/Claim/Experience/revise/retract/silence.

The test does not require a Claim quota.

However the sealed life must yield, if evidence supports them, enough durable cognition to test both sides of continuity:

- at least one user/relationship-facing cognition candidate;
- at least one self/calibration/strategy/experience candidate grounded in real case evidence.

If the Resident reasonably remains silent, the evaluator records that; fixture design may be rejected if it failed to create a genuine test opportunity.

At the boundary, persist World/checkpoint/index/release digests and stop.

### 6.5 C15-RCC-RES-B-001 — fresh context

Resident B runs in a completely new model conversation/process context.

It receives no Phase-A transcript, prose memory dump, model reasoning, expected cognition, or evaluator note.

Only normal AIOS durable state and legal runtime context are available.

B must face new but related situations where prior cognition is relevant.

PASS evidence requires ordinary AIOS retrieval of prior durable cognition and material participation in at least one later decision.

### 6.6 C15-RCC-RES-C-001 — replacement model

Resident C must use a different underlying model family/provider from A/B when the execution platform can prove model identity.

C receives only the same AIOS durable state and normal Resident instruction.

The evaluation does not require identical wording or personality style.

It requires continuity of valid Resident cognition:

- user understanding is not reset;
- learned role/relationship constraints remain available;
- self/calibration lessons remain available;
- valid strategy/experience can influence decisions;
- stale or contradicted cognition can still be revised.

If the platform cannot prove a different model identity, this axis cannot receive `VALID`; it must be reported as `PARTIAL` or `INSUFFICIENT EVIDENCE`.

## 7. Evaluator matrix

C15-RCC-EVAL-001 must independently rule each axis:

| Axis | Required verdict |
|---|---|
| R1 User-understanding formation and grounding | VALID / PARTIAL / INVALID |
| R2 Relationship/role continuity | VALID / PARTIAL / INVALID |
| R3 Self/calibration formation from real case evidence | VALID / PARTIAL / INVALID |
| R4 Strategy/experience formation from real Outcome/feedback | VALID / PARTIAL / INVALID |
| R5 Fresh-window recovery without hidden chat memory | VALID / PARTIAL / INVALID |
| R6 Replacement-model continuity | VALID / PARTIAL / INVALID |
| R7 Material effect on later behavior | VALID / PARTIAL / INVALID |
| R8 Correction: retain/weaken/revise/retract on later reality | VALID / PARTIAL / INVALID |
| R9 Anti-self-proof / no pseudo-LLM / no future leak | VALID / PARTIAL / INVALID |

All R1-R9 must be VALID for C15 closure PASS.

## 8. What “same AI” means

C15 does not test style imitation.

Different models may:

- phrase responses differently;
- use different search orders;
- have different raw reasoning strength;
- vary in verbosity.

Continuity means that valid durable Resident cognition is available and materially constrains or informs later behavior.

The target user experience is:

> the engine changed, but this is still the Resident that has lived through the same relationship, learned the same validated lessons, and can continue revising them.

## 9. Anti-cheat

Invalid evidence includes:

- pasted prior transcript;
- prose handoff saying what A “learned”;
- expected Claim strings;
- keyword-to-cognition rules;
- if/else Resident simulation;
- precomputed future ModelDirectives;
- evaluator oracle exposed to Resident;
- a static persona prompt used as self cognition;
- claiming continuity merely because the underlying model stayed in one giant chat context.

## 10. Relationship to P16

C15 is a focused pre-P16 gate.

P16 remains the long-horizon stress campaign and must later exercise the same mechanisms over months/year-scale life.

C15 exists so P16 does not spend hundreds of simulated days discovering that Resident cognitive continuity was never proven in the first place.

## 11. Root acceptance statement

C15 PASS means:

> A Resident forms evidence-grounded understanding of the user and of its own validated experience; the originating model/session disappears; fresh and replacement models can recover that durable cognitive state only through AIOS and continue acting consistently with it; later reality can still correct it.

That is the minimum proof required for “model can change, Resident does not reset.”
