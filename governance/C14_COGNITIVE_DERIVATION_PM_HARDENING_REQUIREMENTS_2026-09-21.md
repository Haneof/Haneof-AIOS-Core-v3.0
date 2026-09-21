# C14 Continuous Cognitive Derivation — PM Hardening Requirements

> Status: PM-ACCEPTED INPUT TO C14-RULE-001  
> Date: 2026-09-21  
> Baseline: `main@f55349d64c99721bb1b095a26e7d18c2d8a7a36f`  
> Purpose: harden the C14 implementation plan before any C14 Core code is written.

## 1. Summary is not sufficient terminal evidence for durable high-level cognition

A Summary may be used as:

- a trigger anchor;
- a navigation/compression object;
- review context;
- a member/context reference inside an EvidenceSet.

However, a C14-produced durable high-level cognition must not be self-supported by Summary-only provenance.

Required invariant:

> The support provenance closure for a durable C14 cognition must resolve to at least one eligible non-Summary leaf-world source. A chain that terminates only in Summary / AI cognition / maintenance objects is insufficient to prove a user/reality claim.

The implementation must distinguish between:

- using Summary to decide **where to look**;
- using real leaf evidence to decide **what to believe**.

A legal shape may be:

```text
Claim
  -> EvidenceSet
      -> Week Summary
          -> Day Summary
              -> Observation / Event / Outcome / user-world fact
```

An illegal self-closing shape is:

```text
AI Claim
  -> Summary
      -> AI Claim
          -> Summary
```

with no qualifying reality leaf.

This hardening specifically protects against reintroducing the T28 class of error through summarized assistant-authored material.

## 2. C14 must validate real cross-dimensional cognition

C14 must not become a fixed mapping of:

```text
dimension X Summary -> dimension X Claim
```

The Resident must retain freedom to inspect/search/compare multiple dimensions, including `request_all_dimensions_projection`, before deciding whether cognition should change.

C14-RES-001 must include at least one scenario where:

- Dimension A alone is insufficient;
- Dimension B alone is insufficient;
- Dimension C alone is insufficient;
- only the joint multi-week world context can reasonably support a cognition candidate;
- silence remains valid if the Resident judges the combined evidence insufficient.

No deterministic Core code may encode the intended cross-dimensional semantic conclusion.

## 3. Durable cognition must be consumed in a later independent runtime decision

C14 semantic PASS requires more than cognition writeback.

At least one cognition formed during habitation must later be consumed after:

1. the original model session ends;
2. the original runtime instance is discarded;
3. a new `FusedTurnRuntime` / Resident context is created;
4. only durable AIOS World/Index state is restored;
5. a new session id is used;
6. no prior conversation context is manually copied into the new session.

A later analogous but non-identical situation must show that the cognition can be recovered through normal AIOS mechanisms and materially participate in the new decision.

The evaluation must record:

- which cognition revision was recovered;
- what world evidence made it relevant;
- which later Goal/Task/Wake/Response/Strategy decision consumed it;
- subsequent Outcome or user/world feedback;
- whether that result later strengthened, weakened, revised, or left the cognition unchanged.

No hidden chain-of-thought is required or stored; only observable world references and decision/writeback effects are required.

## 4. Positive and negative cognition controls are mandatory

C14-RES-001 must contain both:

### Positive case

Real evidence supports a durable cognition:

```text
repeated but non-identical facts
  -> temporal structure
  -> Resident evidence inspection
  -> cognition
  -> later contradiction
  -> revise/weaken/retract as appropriate
  -> later independent behavior consumes current cognition
```

### Negative control

A superficially similar/repeated pattern exists, but evidence quality is insufficient or contradictory:

```text
same/similar event count
  -> Summary exists
  -> Cognitive Derivation Wake occurs
  -> Resident inspects evidence
  -> silence / UNKNOWN / no unsupported durable cognition
```

The positive and negative cases should, where practical, have comparable event counts so that the test can detect any accidental "N occurrences = preference/strategy/personality" implementation.

Claim count, conversion rate, or wake-to-claim ratio must never be used as a cognition-quality target.

## 5. Provenance must be mechanically derived from existing source truth

Do not introduce a second persisted semantic source-class truth.

Current durable source truth already includes categories such as:

- `SourceClass.USER`
- `SourceClass.SENSOR`
- `SourceClass.PLATFORM`
- `SourceClass.AI_COGNITION`
- `SourceClass.MAINTENANCE`
- `SourceClass.SAFETY`

C14 may define a **derived runtime lineage classification** for routing/eligibility, for example:

- `REALITY`
- `AI_COGNITION_ONLY`
- `MAINTENANCE_ONLY`
- `MIXED`
- `UNKNOWN`

but it must be computed mechanically from transitive pinned source/dependency lineage.

Required routing interpretation:

- reality-facing leaf lineage -> may be eligible;
- AI-cognition-only -> no immediate self-derivation;
- maintenance-only -> no semantic derivation;
- mixed -> may be eligible, but AI-origin material is not promoted into independent user fact;
- unknown/incomplete provenance -> fail closed for immediate derivation, Periodic Review remains the backstop.

Higher-scale Summary lineage must be resolvable through nested Summary provenance to qualifying leaf sources.

## 6. Governance interpretation

C14-RULE-001 should prefer an authoritative runtime/semantic ruling over rewriting the primary constitution.

The existing Fused Baseline already establishes the necessary root principles:

- fact/cognition separation;
- Summary/cognition separation;
- deterministic infrastructure vs AI semantic judgment;
- ALL_DIMENSIONS as cross-dimensional material rather than causal truth;
- AI cognition in the unified World;
- revisable Claim semantics;
- one shared Resident CognitiveRuntime for background cognition.

Constitution/registry text should only be minimally amended if C14-RULE-001 demonstrates an actual normative gap or contradiction that cannot be resolved by interpretation.

Do not create another competing FINAL/amendment/registry authority chain.

## 7. Acceptance impact

These requirements are mandatory inputs to:

- `C14-RULE-001`
- `C14-SCHED-001`
- `C14-RUNTIME-001`
- `C14-LOOP-001`
- `C14-RES-001`
- `C14-CLOSE-001`

C14-CLOSE-001 must fail closure if any of the following is true:

- durable C14 cognition can be supported only by Summary recursion;
- no genuinely cross-dimensional cognition case was validated;
- no new-session/new-runtime cognition consumption was demonstrated;
- no negative-silence control was validated;
- provenance routing relies on semantic heuristics or a second source-truth database;
- Claim count/conversion metrics are used as quality targets.
