# C15-RCC-RES-A-RERUN-002-ACCEPT-001

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Task:

`C15-RCC-RES-A-RERUN-002-ACCEPT-001`

Role:

**Independent Fresh Resident A Evidence Acceptance Reviewer**

You are not:
- Resident A/B/C;
- the author/operator of PR #205;
- fixture designer;
- Core engineer;
- PM integrator;
- downstream semantic evaluator.

Your only task is to independently decide whether the exact Fresh Resident A-002 Phase-A evidence package is a valid, uncontaminated, contract-compliant run that may become the canonical A evidence for the frozen RC.

Do not repair the run.
Do not modify PR #205.
Do not run Resident B.
Do not release any future cursor.

## 1. Required pins

Start by fetching live latest `main`.

Candidate evidence PR:

- PR #205 — OPEN / UNMERGED
- exact evidence head:
  `d17ae972ad1d312735c355f775ac024bc4cebdf7`
- PR base at run publication:
  `4d9f04711769737219d921c8187fc8f52e7d0d6a`

Frozen execution software:

`773876f92d5f8e53422f8f5a68cc651953d93052`

Frozen Core tree:

`fe77f8a0706acfaf369041d0882b6d0e6de39f22`

Run identity:

- task: `C15-RCC-RES-A-RERUN-002`
- subject: `user_1`
- session:
  `c15-rcc-res-a-rerun-002-2079f64af49c`
- process identity:
  `2079f64af49c406895541da042bf2192`
- allowed Phase A cursors: 1..13
- final World revision: 98
- final index watermark: 98

Evidence root:

`reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002/`

If PR #205 head has moved, stop and return:

`REVALIDATION_REQUIRED`

Do not silently inherit this acceptance scope onto a different evidence head.

## 2. Allowed reviewer access

Unlike the Resident, you are an independent reviewer.

You may inspect:
- the exact PR #205 evidence package;
- Phase-A sealed fixture source necessary to verify released projections;
- evaluator/release contracts necessary to verify provenance;
- frozen RC source necessary to verify mechanical/runtime behavior;
- Git metadata needed to verify exact pins.

Do not use your access to run or answer as Resident.
Do not reveal future fixture contents to any Resident context.

## 3. Evidence-only scope

Verify all PR #205 changes are confined to:

`reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002/**`

Current PM preflight observed:
- 191 changed files;
- zero files outside the run evidence root;
- no Core/tests/workflows/constitution/RC packet changes.

Independently re-check this.

Any production-code or governance mutation inside #205 is a blocker unless it is proven to be evidence-only and inside the authorized run root.

## 4. Frozen software identity

Verify:
- `frozen_software_sha = 773876f...`;
- measured Core tree at start/freeze equals:
  `fe77f8a0706acfaf369041d0882b6d0e6de39f22`;
- current post-freeze governance main did not substitute different Core bytes into the Resident execution;
- no Core modification occurred during the run.

Do not treat branch-name equality as proof.
Use actual tree/file identity.

## 5. Freshness / contamination review

Independently inspect provenance evidence for:

- fresh private World;
- fresh search index;
- fresh release-state;
- fresh Resident session/process identity;
- no copied #117 World/index/release-state/cognition;
- no reused #109/#101 semantic outputs;
- no Resident B/C material;
- no future cursor material in Resident-visible inputs.

The run manifest currently asserts:

- `historical_117_copied = false`
- `cursor_14_plus_revealed = false`
- `resident_b_run = false`
- `core_modified = false`

These assertions are not self-proving. Cross-check them against the evidence package, operator trace, release-state and Git scope.

Mechanical fixture access by the sealed release operator is not itself contamination.
Direct or indirect fixture/evaluator/future-data exposure to the Resident model context is contamination.

If you find Resident-context exposure to forbidden future/fixture material, verdict must be:

`ACCEPTANCE_FAIL / CONTAMINATED`

Do not attempt to cleanse/restart the same evidence.

## 6. Sequential release proof

Independently prove:

- release initialized at Phase A;
- exactly sequences 1 through 13 were revealed;
- every released event was ingested before ACK;
- all 13 ACKs bind to the exact event/ref;
- no sequence skipped;
- no sequence reordered;
- no sequence duplicated as a new reality event;
- final release state has:
  - `last_acked_sequence = 13`
  - `next_sequence = 14`
  - `pending_reveal = null`
- no cursor 14+ reveal occurred.

Cross-check each released projection against the sealed fixture for Phase A sequences 1..13.

Do not reveal or process sequence 14 as part of acceptance.

## 7. USER conversation canonicality

The Phase-A package should contain seven USER conversation events.

Verify for each USER event:

- canonical conversation ingest was used;
- one stable Resident session ID was used;
- turn indices are exactly 1..7 and monotonic;
- matching subject/text/time/event identity is preserved;
- ordinary `run_turn` reuses canonical ingest idempotently;
- no duplicate user Observation is minted for the same turn.

Current PM preflight observed seven `turn_01..07` receipts.

Independently verify actual World state and receipts.

## 8. Non-conversation mechanical ingest

Verify the remaining six Phase-A released events use the allowed mechanical ingest path and preserve the exact released projection.

Programs may transport/ingest bytes.
They may not invent semantic cognition.

Check the resulting Observation identities and source classes against ACK receipts.

## 9. Resident-authored semantic decisions

This is mandatory and cannot be reduced to cursor counting.

Inspect:
- RuntimeSnapshot-bearing mailbox requests;
- Resident mailbox replies;
- capability requests/results;
- due-work checkpoints;
- Wake/Review/Summary decisions;
- USER turn directives/responses;
- cognition writes/revisions/retractions/silence.

Verify that semantic decisions were made by the Resident model from then-current released reality and legal capability results.

Fail if:
- scripts/keyword rules/fixture logic generated semantic decisions;
- an operator invented Resident directives;
- future fixture knowledge appears in reasoning/actions before release;
- required model requests were silently answered by deterministic infrastructure.

Do not require the new Resident to match historical #117 wording or Claim choices.
Behavioral diversity is allowed.
Acceptance is about valid provenance, contract fidelity, and support by then-visible evidence.

## 10. Runtime / due-work completeness

For every cursor:
- verify pre/post due work was run as required;
- inspect any due Wake/Review/Summary/derivation work actually triggered;
- verify no due model request was abandoned at freeze;
- verify no mailbox request remained pending;
- verify cursor 13 post-work completed before phase freeze.

Current operator log ends with:
- cursor 13 ACK;
- cursor 13 post due-work;
- `phase_a_complete` with stop sequence 13.

Independently validate the complete trace.

## 11. World / index integrity

Use the frozen artifacts, not a restarted mutable Resident process.

Validate:

- frozen World SQLite quick_check = ok;
- frozen index SQLite quick_check = ok;
- World revision = 98;
- index watermark = 98;
- index lag = 0;
- object revision count = 245;
- World/index correspond to the same run/session;
- index does not contain unreleased future state.

Inspect the authoritative World directly where needed.

## 12. Freeze integrity and digests

Verify freeze was taken only after cursor 13 ACK and due work completion.

Validate digests for at least:

- `freeze/private_world.sqlite`
- `freeze/world_index.sqlite`
- `freeze/release_state.json`
- `freeze/identity.json`
- `freeze/software_identity.json`
- operator trace / live identity references as recorded.

Current package records:
- freeze World SHA256:
  `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa`
- freeze index SHA256:
  `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1`
- freeze release-state SHA256:
  `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8`

Do not reject merely because a coherent SQLite online backup is not byte-identical to the live mutable DB file.

## 13. Capability / cognition audit

Audit the World and decision traces for at least:

- evidence-bound Claim writes;
- revision selection;
- subject isolation;
- no unsupported certainty where current evidence is incomplete;
- no cognition quota behavior;
- no future knowledge;
- no fabricated task completion;
- no Summary treated as independent reality proof;
- no Wake completion treated as reality proof.

This acceptance is not the later full semantic evaluator.
Do not invent a hidden-answer rubric.
But obvious contract violations or unsupported future-informed cognition are blockers.

## 14. Exact evidence-head CI

Re-read checks on exact PR #205 head:

`d17ae972ad1d312735c355f775ac024bc4cebdf7`

Current PM preflight observed:
- `c15-rcc-fixture` run `36033027900` — SUCCESS.

CI success is supporting evidence only.
It does not replace the independent provenance/World/decision review.

## 15. No downstream execution

This reviewer must not:
- merge PR #205;
- modify the Resident evidence;
- run B preflight;
- run Resident B;
- run Resident C;
- enter C16/broad P16/P17;
- modify Core;
- create a replacement A run.

If a blocker is found, preserve evidence and stop.

## 16. Required verdict

Choose exactly one:

### ACCEPTANCE_PASS / blocker = 0

Only if the exact evidence head is independently proven:
- fresh/uncontaminated;
- exact frozen RC;
- sequential 1..13 only;
- correct ingest/ACK chain;
- valid Resident-authored semantic provenance;
- due work complete;
- World/index/freeze internally consistent;
- no forbidden future leakage;
- no Core modification.

### ACCEPTANCE_FAIL / blocker > 0

For any real provenance, contamination, semantic-execution, sequence, durability, or integrity blocker.

### REVALIDATION_REQUIRED

If evidence head changes or a new material dependency invalidates this exact-head review.

## 17. Report / handoff

Create a review-only report:

`reviews/C15_RCC_RES_A_RERUN_002_INDEPENDENT_ACCEPTANCE_2026-09-25.md`

Create one review-only PR from review-time live main.

Report at minimum:
1. review-time live main;
2. PR #205 exact head;
3. frozen software/Core tree;
4. evidence-only scope;
5. freshness/contamination verdict;
6. sequence 1..13 validation;
7. USER canonical-ingest validation;
8. non-conversation ingest validation;
9. model-decision provenance;
10. due-work completeness;
11. World/index integrity;
12. freeze digest validation;
13. capability/cognition audit;
14. exact-head CI;
15. blockers;
16. final verdict.

Leave PR #205 OPEN / UNMERGED.

If PASS, explicitly state:

`PR #205 @ d17ae972ad1d312735c355f775ac024bc4cebdf7 is independently accepted as the canonical Fresh Resident A-002 Phase-A evidence for frozen software 773876f92d5f8e53422f8f5a68cc651953d93052 / Core tree fe77f8a0706acfaf369041d0882b6d0e6de39f22.`

Stop after publishing the review-only acceptance evidence.
