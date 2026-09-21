# C14 Continuous Cognitive Derivation Implementation Plan

> Status: PLANNED / PM-PRIORITIZED  
> Date: 2026-09-21  
> Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
> Baseline: `main@96d62819de32b3f45b1e774329e295241e015f6a`  
> Trigger: P16 Resident habitation evidence shows strong durable factual memory but insufficient continuous conversion from user-world summaries into AI-world cognition.

## 1. Problem statement

AIOS already has the major components required for cognition:

- durable multi-dimensional user/world facts;
- Dimension Summary;
- ALL_DIMENSIONS projection and world search;
- EvidenceSet / Claim / Revision;
- AI-world cognition domains;
- the shared Resident CognitiveRuntime;
- Periodic Review;
- Wake / Background Budget / Attention Bundle.

The missing engineering bridge is a **continuous cognitive derivation path**:

```text
user/world facts
  -> dimension summaries
  -> durable cognition opportunity
  -> same Resident CognitiveRuntime
  -> inspect/search/compare evidence
  -> form/revise/retract AI-world cognition OR silence
  -> later decision/runtime consumes that cognition
```

Today a Summary commit finishes the temporal organization job but does not itself create a durable cognition opportunity. Periodic Review can eventually revisit summaries, but it is a slower consolidation/backstop path, not a direct Summary -> Cognition derivation bridge.

## 2. Constitutional interpretation

This plan does not redefine Summary as cognition and does not allow deterministic code to infer meaning.

The controlling rules remain:

1. Summary answers what happened in one dimension/time window.
2. Cognition answers what those facts mean.
3. Deterministic infrastructure may schedule a model inspection opportunity, but may not write semantic conclusions.
4. The Resident model decides whether to create, strengthen, weaken, revise, retract, or leave cognition unchanged.
5. AI cognition remains in the same WorldStore and uses existing Claim/Evidence/Dependency/Revision machinery.
6. No second AI database, second resident loop, fixed psychological taxonomy, keyword-to-claim mapping, or fixed semantic importance score may be introduced.
7. Observation does not become a direct unrestricted model wake source. The new bridge starts from completed/revised Summary objects, while direct user interaction continues to use the existing turn runtime.

## 3. Target architecture

```text
Observation / Event / Outcome / Conversation
                |
                v
       Dimension Summary
                |
                | deterministic, auditable
                v
   Cognitive Derivation Wake
       (BACKGROUND lane)
                |
        Attention batching
        + budget / Step-0
                |
                v
   SAME Resident CognitiveRuntime
                |
      + inspect summary anchor
      + search related world
      + compare existing claims
      + request all-dimensions projection
      + inspect evidence / outcomes
                |
        model chooses one:
                |
       +--------+---------+------------------+
       |                  |                  |
     SILENCE          WRITE NEW          REVISE/RETRACT
       |              COGNITION            COGNITION
       |                  |                  |
       +------------------+------------------+
                          |
                          v
                  unified AI World
                          |
                          v
           future turns / goals / tasks /
              wakes / periodic review
```

Periodic Review remains a separate longer-window mechanism:

- continuous derivation = near-term opportunity after new temporal structure exists;
- periodic review = slower consolidation, contradiction review, calibration, strategy learning, and recovery backstop.

## 4. Core design decisions

### 4.1 Wake is the derivation queue

Do **not** introduce a new CognitionCandidate database/table.

A durable Wake with pinned Summary evidence is sufficient to represent:

> "the world has been reorganized; Resident AI may inspect whether this changes cognition."

This preserves one World, one scheduler family, one Resident runtime, one metering path, and existing crash/audit semantics.

### 4.2 Dedicated wake source

Introduce a dedicated auditable wake source, tentatively:

`WakeSource.COGNITIVE_DERIVATION`

Default routing:

- attention class: `BACKGROUND`;
- user delivery: false through existing Step-0 background behavior;
- budget: existing background model-call/token budget;
- coalescing: existing AttentionRouter short-window bundling;
- semantic conclusion: always false at trigger time.

A dedicated source is preferred over overloading `MECHANICAL_CHANGE` because it gives exact audit, metering, regression, and long-term policy visibility without creating a semantic judgment.

### 4.3 Every eligible changed Summary gets an opportunity, not a Claim

The deterministic invariant is:

> A newly created or forward-revised eligible Summary must have an idempotent derivation opportunity.

It is **not**:

> Every Summary must produce cognition.

The Resident may inspect and return silence. Zero cognition writes is a valid successful result.

### 4.4 No semantic "importance classifier" in Core

Core must not implement:

- keyword weights;
- psychology labels;
- "3 occurrences means preference";
- fixed domain-count thresholds;
- hard-coded life-stage patterns;
- deterministic claim text;
- semantic confidence scores.

Cost control happens through engineering mechanisms already present:

- summary cadence;
- BACKGROUND routing;
- short-window bundle/coalescing;
- token/model-call budget;
- model silence;
- periodic review fallback.

### 4.5 Prevent AI-world self-excitation

A naive "every Summary wakes cognition" loop can self-amplify:

```text
AI Claim -> AI-dimension Summary -> derivation -> new Claim
        -> new AI-dimension Summary -> ...
```

Therefore eligibility must be based on **mechanical provenance**, not semantic importance.

Required behavior:

- a Summary containing user/reality-facing source lineage may create a derivation opportunity;
- a Summary whose lineage is purely AI-cognition/maintenance material must not recursively schedule immediate cognitive derivation;
- higher-scale Summary objects must propagate enough source-provenance metadata to make the same decision without semantic inference;
- mixed provenance may be eligible, but the trigger itself still carries no conclusion.

The implementation must be fail-closed when provenance cannot be safely established, with Periodic Review remaining the backstop.

### 4.6 Crash/restart semantics

There must be no permanent gap of:

`Summary committed -> process crashed -> derivation opportunity lost forever`.

The scheduling operation must be idempotent and recoverable.

Acceptable implementation patterns include:

- same-transaction Summary + Wake if it can reuse Wake invariants without duplicating WakeBus semantics; or
- post-commit `ensure_derivation_wake(summary_ref)` plus restart reconciliation that re-ensures the latest eligible Summary revision.

The exact implementation is chosen during C14-SCHED-001, but crash recovery is mandatory.

### 4.7 Same Resident, same cognition capabilities

The derivation wake must enter the existing `CognitiveRuntime`.

It must reuse current capabilities such as:

- `search_world`;
- `inspect_world_object`;
- `compare_claims`;
- `expand_recall`;
- `request_all_dimensions_projection`;
- `form_claim`;
- `revise_or_retract_claim`;
- AI-world understanding/relationship/self/strategy/calibration writeback;
- operation experience when real result evidence exists.

No "cognition compiler LLM" or separate hidden model is permitted.

## 5. Required Resident instruction

The derivation wake context must convey a bounded instruction equivalent to:

> A completed/revised world Summary is available. Decide whether it changes any durable understanding. Inspect related world evidence and existing cognition when needed. If evidence supports a durable change, write or revise cognition through existing capabilities. If not, remain silent. The existence of a Summary is not itself evidence that a new Claim is required. Do not invent causality, preference, relationship meaning, or strategy without evidence.

This instruction is not an expected answer and must not encode a benchmark-specific conclusion.

## 6. Task decomposition

### C14-RULE-001 — Cognitive derivation semantic ruling

**Type:** governance / contract, no Core code.

Deliverables:

- freeze the exact Summary -> Cognition boundary;
- define eligible Summary opportunity semantics;
- define no-loop provenance rule;
- define role of Periodic Review vs continuous derivation;
- define valid silence/no-op completion;
- define user-delivery/action boundaries;
- amend the relevant constitution/registry language only where necessary.

Completion evidence:

- one ruling document;
- no duplicate constitution;
- no runtime code changes;
- exact affected constitutional clauses listed.

### C14-SCHED-001 — Summary -> derivation Wake + provenance + recovery

**Type:** Core implementation.

Scope:

- add dedicated derivation wake source/routing;
- mechanically classify/propagate Summary source provenance;
- schedule exactly one idempotent opportunity per eligible Summary revision;
- recover a missing wake after restart;
- preserve unchanged-summary no-op behavior;
- block pure AI-cognition Summary recursion;
- keep Summary content/contracts unchanged.

Required regressions:

- day Summary -> one derivation Wake;
- same Summary revision -> no duplicate;
- Summary revision N+1 -> one new opportunity;
- higher-scale reality Summary -> eligible;
- pure AI cognition Summary -> no immediate derivation wake;
- mixed/reality lineage behaves per ruling;
- crash after Summary commit can recover missing wake;
- subject isolation;
- stale/inactive Summary does not create a new current derivation opportunity;
- world/index semantics remain intact.

### C14-RUNTIME-001 — Resident derivation dispatch

**Type:** Runtime implementation.

Scope:

- dispatch derivation Wake through the same `CognitiveRuntime`;
- provide pinned Summary anchor(s), dimension/window metadata, AI-world context, and capability catalog;
- support existing background coalescing/Attention Bundle;
- ensure background derivation never becomes an unsolicited user-facing response;
- allow Resident to search/inspect/compare and write/revise cognition;
- allow silence without synthetic Claim/Experience;
- preserve metering, model provenance, tool-round limits, and crash behavior.

Required regressions:

- Resident sees exact pinned Summary revision;
- model silence creates no cognition object;
- model can form evidence-grounded AI-world Claim;
- model can revise an existing Claim from new evidence;
- assistant raw dialogue is not elevated into independent user fact;
- no hidden deterministic claim generation;
- no second model/runtime path;
- model-call metering remains non-world C13 truth.

### C14-LOOP-001 — Self-excitation, budget, and consolidation hardening

**Type:** Core hardening.

Scope:

- prove derivation writes cannot recursively create unbounded derivation;
- prove background wake bundling reduces bursts without semantic loss;
- prove budget deny/defer does not lose the durable opportunity;
- verify Periodic Review can still consume the resulting cognition and unresolved evidence;
- ensure derivation Wake/completion objects do not themselves become semantic evidence of user preference/success.

Required regressions:

- cognition-write -> AI summary -> no derivation storm;
- 10+ sibling reality summaries can coalesce under existing bundle policy;
- budget defer/restart preserves pending work;
- budget hard deny has explicit durable disposition;
- periodic review still sees relevant Summary/Claim/Experience anchors;
- no world_revision-only or Wake-completion-only "learning".

### C14-RES-001 — Real Resident cognition-formation habitation

**Type:** semantic evaluation with a real model; no pseudo-LLM.

Run a fresh/private life segment where the Resident encounters:

1. repeated but not identical user-world facts;
2. a pattern that is only visible after temporal Summary;
3. a later contradictory case;
4. a future decision where previous cognition could help.

The Resident must not receive a hidden expected answer.

Evaluation asks only whether the actual world evidence shows:

- the derivation wake was consumed;
- the Resident inspected enough evidence;
- a useful cognition was formed **or a justified silence occurred**;
- later contradictory evidence can weaken/revise/retract cognition;
- future behavior can consume the cognition;
- no unsupported personality/preference/causal label was invented;
- no programmatic keyword logic substituted for model judgment.

This task must save World/checkpoint/model provenance and an independent evaluator report.

### C14-CLOSE-001 — Independent closure audit

**Type:** audit only.

Must verify:

- rule/code alignment;
- deterministic gates green;
- real Resident evidence is valid;
- no second cognition database/runtime;
- no semantic fixed rules;
- no wake storm/self-learning loop;
- no regression in Summary, Review, Wake, C13 metering, T28 assistant boundary, P14 continuity, Goal/Task/Action semantics.

Only after C14-CLOSE-001 passes may the paused P16 campaign resume.

## 7. Gate matrix

Minimum required deterministic gates across the implementation series:

- dimension-summary;
- cognitive-runtime;
- cognition-writeback;
- cognition-revision;
- constitutional-cognition-closure;
- C09 wake dispatch;
- fused-turn-runtime;
- P15 periodic review;
- C13 metering regressions;
- P14 long-context;
- memory-recommendation / T28 boundary;
- P16 habitation harness;
- P16 convergence gate.

C14 semantic success additionally requires the real Resident evidence from C14-RES-001. A green deterministic harness alone is not cognition PASS.

## 8. Non-goals

C14 must not:

- rewrite the multi-dimensional world model;
- merge Summary and Claim;
- add a new "AI memory database";
- add deterministic psychological profiling;
- make every Observation invoke the model;
- require a Claim quota such as "90 claims";
- force a Claim on every Summary;
- replace Periodic Review;
- change external Action authorization or Task completion semantics;
- change the user's raw world facts based on AI cognition.

## 9. Expected result

After C14 closes, AIOS should move from:

```text
world grows -> summaries grow -> cognition occasionally grows
```

to:

```text
world grows
  -> temporal structure changes
  -> Resident gets a bounded cognition opportunity
  -> cognition may evolve or remain unchanged
  -> future decisions can consume that evolution
  -> later outcomes/reviews can correct it
```

The acceptance criterion is not "more Claim count".

The acceptance criterion is:

> **world experience can reliably create an opportunity for evidence-grounded AI-world change, and that change can later affect behavior while remaining revisable.**


## 10. PM hardening requirements adopted before C14-RULE-001

The following document is now a mandatory normative input to every C14 task:

- `governance/C14_COGNITIVE_DERIVATION_PM_HARDENING_REQUIREMENTS_2026-09-21.md`

C14-RULE-001 must explicitly freeze the following additional acceptance boundaries before Core implementation starts:

1. **Summary is trigger/navigation/compression, not sufficient terminal proof.** Durable high-level C14 cognition must have support provenance closure that reaches qualifying non-Summary leaf-world evidence. Summary-only / AI-cognition-only recursive support is insufficient.
2. **Cross-dimensional cognition is mandatory to validate.** C14-RES-001 must include a scenario where no single dimension independently supports the cognition and the Resident must use combined multi-dimensional evidence.
3. **Cognition must survive context replacement and affect later behavior.** At least one cognition must be consumed in a later new-session/new-runtime decision after only durable AIOS World/Index restoration.
4. **Positive and negative controls are mandatory.** Similar event counts but different semantic evidence quality must produce cognition in one case and justified silence/UNKNOWN/no unsupported cognition in the other.
5. **Provenance classification is derived, not a second truth system.** Routing eligibility must be mechanically computed from existing SourceClass plus transitive pinned source/dependency lineage; UNKNOWN fails closed.
6. **Governance-first interpretation.** Prefer an authoritative C14 ruling over changes to the primary constitution; amend registry/constitution only if an actual unresolved normative gap is proven.

### 10.1 Revised semantic acceptance equation

C14 is not accepted merely because:

```text
Summary -> Claim
```

C14 is accepted only when the evidence shows:

```text
world facts
  -> Summary creates cognition opportunity
  -> Resident drills down / crosses dimensions
  -> leaf-grounded EvidenceSet
  -> cognition OR justified silence
  -> new session + new runtime
  -> cognition is recovered through AIOS
  -> later decision materially consumes it
  -> Outcome / new evidence
  -> cognition can be revised or retained
```

### 10.2 Additional deterministic regressions required

C14-SCHED/RUNTIME/LOOP implementation must add deterministic coverage for:

- Summary-only evidence cannot satisfy the C14 durable high-level cognition ground rule;
- nested Summary lineage resolves transitively to leaf source classes;
- pure AI-cognition-only lineage cannot schedule immediate derivation;
- mixed lineage never promotes AI-authored material into independent user fact;
- UNKNOWN/incomplete lineage fails closed for immediate derivation;
- new-runtime restoration can retrieve the same durable AI-world cognition revision through normal context/search capabilities;
- no claim-count or wake-to-claim conversion target exists in runtime policy.

### 10.3 C14-RES-001 semantic test matrix

At minimum the real Resident validation must include four distinct checkpoints:

| Checkpoint | Required evidence |
|---|---|
| Multi-dimensional positive | cognition is only reasonably supportable after combining multiple dimensions |
| Negative silence control | comparable repetition exists but evidence remains insufficient/contradictory and no unsupported durable cognition is written |
| New-session consumption | prior cognition is recovered after model session/runtime replacement and affects a later independent decision |
| Revision feedback | later Outcome/new evidence can weaken, revise, retract, or confirm the previously consumed cognition |

The evaluator must judge evidence quality and behavior, not object counts.
