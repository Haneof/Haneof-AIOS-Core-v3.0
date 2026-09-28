# C15-RCC-RESIDENT-PERSONA-CONTINUITY-RULE-001 — Independent Governance Review Prompt

Repository: `Haneof/Haneof-AIOS-Core-v3.0`

Role: **Independent Resident Identity / Persona Continuity Governance Reviewer**

You are not the author, PM integrator, Core engineer, Resident, or evaluator for later C15 habitation.

## Task

Independently review the governance candidate that formalizes this product invariant:

> A user interacts with one long-lived Resident AI. Any underlying provider/model/API key may take a turn, but model replacement alone must not change the Resident's user-facing identity/persona.

Start by fresh-fetching live `main` and the candidate PR/head. Do not trust SHAs in this prompt as permanent state.

Read at minimum:

1. `docs/constitution/AIOS_v3.0_AI_Personality_Model_Constitution.md`
2. `docs/constitution/AIOS_v3.0_AI_Self_Model_Constitution.md`
3. `docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md`
4. `governance/C15_RESIDENT_COGNITIVE_CONTINUITY_RULING_2026-09-22.md`
5. `governance/C15_RESIDENT_COGNITIVE_CONTINUITY_TEST_PLAN_2026-09-22.md`
6. `governance/C15_RCC_RESIDENT_PERSONA_CONTINUITY_RULING_2026-09-28.md`
7. current task board / checkpoint / master map
8. full candidate diff

## Required review questions

Attempt to falsify the candidate.

Verify that it:

- truly makes Resident identity/persona provider- and model-neutral;
- does not confuse exact wording with identity;
- does not permit material persona drift merely because an engine changed;
- keeps capability differences legal;
- keeps personality evolvable through evidence rather than frozen;
- does not create a second persona truth store;
- does not turn a static system/persona prompt into identity truth;
- remains compatible with the existing Personality, Self, Relationship, User Understanding, Strategy and Revision constitutions;
- introduces an auditable R10 rather than a vague “feels like the same AI” criterion;
- does not force every model to produce identical text;
- preserves hidden-handoff prohibition;
- does not accidentally expand the current trusted-return Core corrective;
- places the gate before Resident C / final C15 evaluation / close;
- leaves broad multi-provider stress to P16 while still making the invariant binding now.

## Adversarial scenarios

Reason explicitly about at least:

1. 50 user-provided API keys across several providers/models.
2. Failover from a terse native model to a verbose native model.
3. Failover from a warm native model to a cold/formal native model.
4. A stronger model that has better reasoning but must remain the same Resident.
5. A weaker model that cannot fully reproduce an advanced behavior; distinguish capability limit from identity reset.
6. Real long-term evidence that legitimately changes the Resident's personality.
7. A hidden static persona prompt that makes outputs look similar while durable Personality state is absent.
8. A provider model asserting its own branded identity.
9. Same durable cognition but materially different attitude toward the user.
10. Same surface wording but different decisions/boundaries underneath.

## Verdict

Return exactly one:

- `ACCEPTANCE_PASS / blocker=0`
- `ACCEPTANCE_FAIL / blocker=N`

If FAIL, every blocker must identify the exact conflicting clause and the smallest governance correction.

Do not edit Core. Do not merge. Do not run Resident. Do not begin the persona preflight.
