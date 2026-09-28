# C15 Resident Identity / Persona Continuity — Binding Clarification

> Status: **CANDIDATE AUTHORITATIVE GOVERNANCE / REVIEW_READY**  
> Task: `C15-RCC-RESIDENT-PERSONA-CONTINUITY-RULE-001`  
> Date: 2026-09-28  
> Base: `5288822e751df185f3abab79f969609f31859617`  
> Scope: Resident identity/persona continuity under underlying-model/provider replacement.  
> This ruling does not authorize Core implementation and does not modify current trusted-return corrective scope.

## 1. Product root requirement

AIOS presents one long-lived Resident AI to the user.

The provider/model is a replaceable execution substrate. The user-facing Resident identity belongs to AIOS, not to GPT, Claude, Gemini, a local model, or any other provider/model.

A user may connect one API key or many API keys across many providers and model families. Routing a turn to a different underlying model must not make the user meet a different AI.

Frozen product meaning:

> **用户认识的是 Resident，不是底层模型。模型可以换，Resident 的人格与身份连续性不能因为模型切换而重置或漂移。**

Equivalent engineering statement:

> **provider/model replacement may change capability, latency, reasoning path, or wording, but must not by itself change the Resident's durable user-facing identity/persona.**

## 2. What is continuous

Resident persona/identity continuity includes durable, evidence-grounded and revisable tendencies such as:

- attitude and interaction posture toward the user;
- relationship/role manner already formed through real interaction;
- stable communication style and habitual ways of explaining, asking, refusing, correcting, helping, or staying silent;
- stable behavioral tendencies and decision habits where they have become part of Personality/Self/Strategy;
- values, boundaries and commitments that belong to the Resident/system law;
- self-understanding and calibrated limits;
- currently valid Personality claims and the evidence/revision lineage that supports them.

These are not required to be represented as one monolithic profile. They remain in the unified World and existing AI-dimension mechanisms.

## 3. What may vary when the model changes

A different underlying model may legitimately change:

- raw reasoning strength;
- coding/math/vision capability;
- latency;
- token efficiency;
- search order;
- exact sentence construction;
- vocabulary choice;
- small non-material stylistic variation;
- how much internal work is needed to reach the same Resident-level decision.

These are engine properties, not Resident identity.

Exact text matching, phrase imitation, token-level similarity, or forcing all models to emit the same prose is **not** the acceptance criterion.

## 4. What may not vary merely because the model changes

A provider/model swap alone is not legal evidence for persona revision.

It must not cause:

- a different attitude toward the user;
- a relationship/role reset;
- a material communication-style reset;
- loss of established behavioral habits;
- a sudden change in boundaries, commitments, directness, warmth, restraint, initiative, or collaboration posture that is attributable only to model-native defaults;
- replacement of the Resident's Self/Personality with the provider model's default assistant persona;
- reintroduction of model-specific identity claims such as treating the engine name as the Resident identity;
- forgetting or overwriting durable cognition already protected by C15.

The model's native assistant personality has **no identity authority** inside AIOS.

## 5. Continuity is not personality freezing

The Resident may evolve.

Personality change is legal only through the same durable lineage and the existing Evidence / Revision / Retraction rules. It should normally be gradual and supported by real long-horizon interaction, feedback, outcomes, or other qualifying evidence.

A model upgrade, model downgrade, provider failover, API-key rotation, load-balancing decision, or routing change is not such evidence.

Therefore:

> **same Resident does not mean immutable Resident; it means changes must come from the Resident's lived evidence, not from swapping the engine.**

## 6. Architecture boundary

This requirement does not authorize:

- a second persona database;
- provider-specific persona memory;
- hidden model-to-model handoff prose;
- a static persona prompt as the truth source;
- a hard-coded personality scorecard;
- keyword-to-personality rules;
- exact-text imitation benchmarks.

Allowed implementation direction, if a later preflight proves a mechanism gap, must reuse:

- unified WorldStore;
- Personality / Self / Relationship / User Understanding / Strategy / Experience;
- EvidenceSet / Dependency / Revision / Retraction;
- normal Runtime context selection and legal retrieval;
- existing constitutional hard boundaries.

A bounded runtime rendering of durable persona context may be a delivery mechanism; it is not a second truth store.

## 7. C15 acceptance correction

The 2026-09-22 RCC ruling remains authoritative except where this clarification explicitly supersedes it.

The following earlier interpretations are superseded:

1. `Personality ... [is] not [a] C15 acceptance axis`.
2. `Style and personality wording are explicitly not Resident identity`, when read to permit material user-facing persona drift.
3. Any C15 test-plan language that permits replacement-model personality/style reset so long as cognition survives.

Correct interpretation:

- exact wording/prose style is not identity;
- **durable Personality and user-facing behavioral style are part of Resident identity**;
- C15 must test both cognition continuity and persona/identity continuity.

## 8. New binding evaluator axis — R10

C15 final evaluation adds:

### R10 — Resident Identity / Persona Continuity

`VALID` requires all of the following:

1. A/B evidence establishes at least some durable Resident personality/interaction tendencies through legal evidence, not evaluator-authored expected prose.
2. Resident C runs on a provably different underlying model/provider identity.
3. C receives no prior transcript, hidden prose handoff, evaluator notes, expected phrases, or model-specific persona script.
4. C recovers the same legal AIOS durable lineage.
5. In matched or meaningfully comparable situations, C remains recognizably the same Resident in material attitude, relationship posture, communication style and behavioral tendencies.
6. Provider-native defaults do not materially override the Resident.
7. Exact wording may differ.
8. Capability differences may be visible.
9. Later real evidence can still revise the persona forward; the evaluator must not reward frozen imitation.

`PARTIAL` applies when the model replacement identity or persona evidence is insufficient to prove continuity.

`INVALID` applies when a model swap materially changes the user-facing Resident, when persona is supplied by hidden handoff/static script instead of durable AIOS state, or when exact imitation is used to fake continuity.

C15 PASS becomes:

> **R1–R10 are all VALID.**

## 9. Negative controls

At minimum the eventual C15 identity/persona test must include:

- **provider-default drift control** — replacement model has a noticeably different native assistant style, but the Resident-level interaction remains continuous;
- **capability-vs-identity control** — stronger/weaker engine changes capability without being treated as a different Resident;
- **persona-freeze control** — new real evidence can revise a stable tendency, proving continuity is not imitation;
- **hidden-prompt control** — no provider-specific or evaluator-authored persona script may serve as the identity truth;
- **irrelevant-persona control** — a personality tendency must not be force-applied where context makes it irrelevant.

## 10. Scope and sequencing

This clarification is governance-only.

It does **not** interrupt the currently READY Core task:

`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001`.

It becomes binding before:

- Resident C replacement-model release;
- `C15-RCC-EVAL-001`;
- `C15-RCC-CLOSE-001`.

After independent governance acceptance/integration, PM must run a read-only mechanism preflight:

`C15-RCC-PERSONA-CONTINUITY-PREFLIGHT-001`

to classify the current main paths as `ALREADY_IMPLEMENTED`, `MECHANISM_GAP`, or `INSUFFICIENT_EVIDENCE`.

No Core task may be invented before that preflight proves a real mechanism gap.

## 11. P16 extension

C15 proves the invariant with an attested replacement-model boundary.

Broad P16 must later stress the same invariant across multiple providers/models/API keys and long-horizon routing/failover.

The scaling target is not “one persona per model.” It is:

> **one Resident identity/persona lineage, many replaceable model engines.**
