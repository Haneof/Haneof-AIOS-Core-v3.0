# C14 Resident A — Safe Execution Contract

> Task: `C14-RES-A-001`  
> Role: **actual Resident AI**  
> Access class: RESIDENT_VISIBLE  
> Fixture: v2 only  
> Phase: A only  
> Cursor range: 1..24

## 1. Your role

You, the model in this exact chat/agent window, are the Resident AI under test.

You are not a fixture designer, evaluator, benchmark author, or test programmer.

Every semantic decision represented as Resident cognition must be made by you after seeing only the information available at the current simulated time.

## 2. Resident-visible files

You may read:

- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md` only to verify `C14-RES-A-001 = READY`;
- this file;
- `reviews/internal_habitation/c14-resident/v2/release/release_contract.md`;
- `reviews/internal_habitation/c14-resident/v2/release/release_operator.py`;
- `reviews/internal_habitation/c14-resident/v2/release/mechanical_ingest_adapter.py`;
- relevant Core/runtime source needed to execute AIOS correctly.

You may inspect the private World you create through normal AIOS capabilities and exact durable refs.

## 3. Resident-forbidden files

Do not open, read, search, quote, diff, or indirectly inspect:

- `reviews/internal_habitation/c14-resident/v2/fixture/sealed_fixture.json`;
- `reviews/internal_habitation/c14-resident/v2/fixture/fixture_manifest.json`;
- anything under `reviews/internal_habitation/c14-resident/v2/evaluator/**`;
- `C14_RES_FIX_002_COMPLETION_EVIDENCE_2026-09-21.md`;
- `C14_RES_FIX_003_COMPLETION_EVIDENCE_2026-09-21.md`;
- `reviews/C14_RES_FIX_001_PM_REVIEW_2026-09-21.md`;
- `reviews/C14_RES_FIX_002_PM_REVIEW_2026-09-21.md`;
- `reviews/C14_RES_FIX_003_PM_ACCEPTANCE_REVIEW_2026-09-21.md`;
- `governance/C14_REAL_RESIDENT_VALIDATION_PROTOCOL_2026-09-21.md`;
- any Resident-B or evaluator artifact;
- any future fixture payload or future release output;
- other Resident runs/reports that could tell you what cognition is expected.

If any forbidden material is exposed to you, mark the run contaminated and stop. Do not continue as valid Resident evidence.

## 4. No future knowledge

You may learn one life event only through the blind release operator's current `reveal` output.

Never obtain multiple unreleased events in one call.

Never inspect the fixture to "save time".

Do not infer future fixture content from filenames, tests, evaluator files, Git history, PR descriptions, or prior reports.

## 5. Required release path

Use only fixture v2.

For every cursor N from 1 through 24:

1. `release_operator.py reveal --phase A` exposes the current event only.
2. Pass exactly that released projection to `mechanical_ingest_adapter.py --world-db <private-world.db>`.
3. Receive the exact durable Observation ref.
4. Call `release_operator.py ack --phase A --world-db <same-private-world.db> ... --ingest-ref <exact-ref>`.
5. The operator must verify the exact World revision before the cursor advances.

Do not manually manufacture an ingest ref.

Do not bypass the operator.

## 6. AIOS processing after durable ingest

Durable release acknowledgement is only input integrity. It is not the cognitive run itself.

After each released event is durably ingested:

- catch the World index up;
- advance the normal AIOS virtual/runtime time to the event time;
- run normal due Dimension Summary scheduling;
- allow normal C14 Cognitive Derivation scheduling/reconciliation;
- dispatch eligible background Wakes through the real WakeBus/AttentionRouter/BackgroundBudget/CognitiveRuntime path;
- preserve Periodic Review according to the existing runtime policy;
- process only work that is due at the current simulated time.

At cursor 24, after the event is durably acked, also finish any normally due maintenance/C14 work attributable to information available through that time before freezing the handoff.

Do not release cursor 25.

## 7. Model-generated summaries

If AIOS requires a model-generated Dimension Summary or other model-authored maintenance text, you personally author it from the exact current summary input.

A program may:

- choose mechanically due windows/dimensions;
- provide the exact Summary input;
- persist the text you authored.

A program may not write semantic Summary text for you.

Do not read future events when authoring a Summary.

## 8. Resident CognitiveRuntime

Whenever the real CognitiveRuntime requests a model decision:

1. save/show the exact current RuntimeSnapshot/cockpit;
2. inspect only that snapshot and information obtained through legal AIOS capabilities;
3. you personally choose the next `ModelDirective`;
4. if you choose capability calls, execute exactly those calls through the real runtime;
5. inspect the returned capability history;
6. make the next semantic decision yourself.

Programs may transport RuntimeSnapshots and your chosen directives.

Programs may not decide the directive.

## 9. Allowed Resident behavior

You may independently choose to:

- search World;
- inspect exact objects/revisions;
- inspect timeline;
- compare cognition;
- expand recall;
- request ALL_DIMENSIONS;
- inspect Outcomes;
- inspect existing AI-world cognition;
- form/revise/retract legal cognition through authorized capabilities;
- remain silent.

There is no required Claim count.

There is no required conversion rate.

There is no expected wording.

Silence is valid whenever you judge evidence insufficient or understanding should not change.

## 10. Forbidden semantic shortcuts

Do not write a program that:

- maps keywords to cognition;
- counts repetitions and generates a preference/trait;
- chooses search targets;
- chooses capability calls;
- creates Claim text;
- decides revise/retract/silence;
- precomputes later answers;
- acts as a pseudo-LLM;
- scores semantic importance for you.

Do not batch-create future ModelDirectives.

One semantic checkpoint at a time.

## 11. Mechanical interactive bridge

If the repository does not already expose a suitable interactive bridge for the model in this session, you may add a thin test-side bridge under your private evidence directory.

It may only:

- instantiate the real AIOS store/index/runtime;
- serialize the current RuntimeSnapshot or Summary input;
- pause;
- accept the decision/text you personally provide;
- feed that exact decision back into the existing runtime;
- save capability results;
- persist audit evidence.

It must contain no semantic decision rules.

Do not modify `src/aios_core/**`.

## 12. Same-Resident requirement

All model-authored semantics in Phase A must come from you, the actual model in this window.

Do not call another LLM/provider to decide:

- summaries;
- cognition;
- search relevance;
- capability calls;
- responses.

If a provider call made internally by AIOS is unavoidable for bookkeeping, it must not replace your semantic role and must be explicitly disclosed. Prefer the interactive same-window bridge.

## 13. Evidence to record

Keep append-only evidence sufficient to prove the run.

At minimum record:

- exact main SHA;
- your branch;
- actual model identity as exposed by the environment; do not invent provider/model identifiers;
- private World DB path;
- release-state path;
- each reveal projection;
- each mechanical ingest receipt;
- each release ack receipt;
- every model-authored Dimension Summary input/output;
- every Resident RuntimeSnapshot presented to you;
- every ModelDirective you selected;
- capability call/result history;
- C14 Wake refs and states;
- cognition refs/revisions created/revised/retracted;
- Periodic Review refs if any;
- World revision/index watermark checkpoints;
- errors/retries.

Do not save private chain-of-thought. Observable decisions and refs are sufficient.

## 14. Handoff checkpoint

After cursor 24 is durably ingested and acknowledged, and all normally due work through that timestamp is processed:

- do not reveal cursor 25;
- do not inspect Phase-B material;
- stop all Resident semantics;
- freeze the exact private World;
- save the release state showing `last_acked_sequence=24`, `next_sequence=25`, active Phase A;
- save World SHA256;
- save release-state SHA256;
- save current world_revision;
- save index watermark;
- save all current durable cognition refs/revisions;
- save the exact evaluated main SHA;
- save actual model/environment identity;
- save an evidence manifest/digest.

Then stop permanently.

## 15. No self-evaluation

Do not decide whether C14 passed.

Do not label any hidden case positive/negative.

Do not write evaluator conclusions.

Report only what actually occurred, the durable artifacts, semantic decisions you actually made, and any reproducible runtime blocker encountered.

`C14-RES-B-001` remains for a completely separate fresh model window.
