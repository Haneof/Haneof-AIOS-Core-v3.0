# C15-RCC-RES-A-RERUN-004-INDEPENDENT-ACCEPTANCE

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Role:

**Independent Fresh Resident A Evidence Acceptance Reviewer**

You are not:
- the A-004 Resident;
- PR #273 author;
- PM;
- Core engineer;
- persistence engineer;
- Resident B/C;
- final C15 evaluator.

Your only task:

> Independently attempt to falsify the exact A-004 evidence package and determine whether it proves a fresh, legal, authentic Phase-A Resident run on the accepted RC-003 lineage.

Do not repair the run.
Do not modify PR #273.
Do not merge anything.

## 1. Fresh start and exact pin

Fresh-fetch:
- live `main`;
- PR #273 metadata/head/diff;
- current task board/checkpoint;
- RC-003 integration receipt;
- A-004 run contract;
- exact evidence package.

At dispatch, the only valid A-004 evidence candidate is:

- PR #273
- exact head: `f251e9c0026a0f97fdee20397936cb5e3b18c61c`
- parent: `0b17c7f35697dc4a24b731185868d29967efcf58`
- tree: `fd312286b7b83cd550ecc49d72b78656e6e91b71`
- run directory: `reviews/internal_habitation/c15-rcc/v1/resident/runs/a004-27bb1fb3da404f4d/`

Frozen RC identity:

- software: `f20f2edfa7af00d0286493fd15196ca9503bc315`
- Core tree: `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- tests tree: `7e33b5ef8432370234965d3ccd61248c703c4019`

If PR #273 head moved, return:

`REVALIDATION_REQUIRED`

Do not transfer acceptance to another SHA.

## 2. Review scope

Read the evidence package and legal contracts needed to evaluate it.

Do not use prior A-003 wording/cognition as expected answers.

Different valid cognition is allowed.

Do not expose or require private chain-of-thought. Evaluate decisions by:
- visible inputs;
- legal capability history;
- durable outputs;
- provenance;
- resulting World state.

## 3. Evidence-only scope

Mechanically prove PR #273:
- changes only the A-004 evidence directory;
- changes no `src/**`;
- changes no `tests/**`;
- changes no `tools/**`;
- changes no governance/run contract;
- changes no accepted RC implementation.

Any hidden implementation or contract modification is a blocker.

## 4. Frozen RC identity

Independently verify:
- frozen software Git object exists;
- exact Core/tests trees match the declared RC-003 pins;
- the run evidence identifies that exact software;
- no later main implementation was substituted into execution.

Check import/runtime evidence for `aios_core`.

If the run used another implementation tree, FAIL.

## 5. Freshness and contamination

Attempt to prove or falsify that A-004 started from new:
- World;
- index;
- release-state;
- runtime/checkpoint;
- Resident session;
- conversation session;
- process/run identity.

Search the evidence for:
- A-003/A-002/A-001 state reuse;
- old Resident IDs;
- old claim/object IDs imported as seeds;
- old transcripts/reports/summaries/checkpoints;
- evaluator notes;
- expected-answer material;
- B/C/future fixture content;
- PM prose telling the Resident what previous A learned.

A-003 is historical prior-RC evidence only.

Any material semantic reuse is a blocker.

## 6. Cursor/release audit

Independently reconstruct the Phase-A release chain.

Verify:
- phase = A;
- cursor sequences exactly 1..13;
- each reveal occurs once;
- each event is durably ingested;
- USER events use canonical conversation binding;
- PLATFORM events use legal mechanical ingest;
- each sequence has exact durable ACK;
- no fabricated ingest ref;
- no reorder/skip;
- cursor 14 never revealed;
- `next_sequence=14`;
- `pending_reveal=null`.

Recompute event/receipt hashes where possible.

## 7. Temporal isolation / future leak

This is binding.

For each cursor, verify the Resident/model decision material available at that point did not contain:
- later event IDs;
- later complete payloads;
- later platform outcomes;
- future release-state data;
- evaluator/fixture expectations.

Check decision requests and snapshots temporally against the reveal ledger.

Also inspect Wake/Review/Summary/derivation execution for accidental future visibility.

Any future leak is a blocker.

## 8. Resident decision authenticity

There are approximately 50 decision requests/responses.

Independently determine whether the semantic choices were made by the current Resident session rather than by the runner.

Look for:
- keyword-to-directive rules;
- hard-coded fixture answers;
- scripted Claims;
- automatic semantic branching based on known fixture IDs;
- response templates containing expected cognition;
- post-hoc response creation after later evidence;
- operator code making semantic judgments.

Mechanical serialization/transport is allowed.

The reviewer should inspect enough request/response/result chains across:
- user turns;
- Periodic Review;
- dimension summaries;
- cognitive derivation;
- Wake;
- capability retries;
to support a real authenticity conclusion.

Do not demand hidden chain-of-thought.

## 9. Cursor-1 recovery adversarial review

The run reports an initial file-handshake failure.

Independently verify:
- the first model attempt was not submitted;
- provider/model/request/meter/response fingerprint were absent as claimed;
- the failure occurred before a legal directive was accepted;
- `reconcile_turn_model_not_submitted` was valid;
- retry authorization was legal;
- retry did not duplicate USER observation, claim, meter, operation or assistant output.

If "not submitted" is merely asserted rather than durably supported, FAIL.

## 10. Cursor-10 recovery adversarial review

This is a high-priority attack target.

The run reports:
- round 0 was already applied;
- round 1 became `in_doubt` because a local response file was read mid-write;
- exact reply bytes had already been created by the Resident;
- durable assistant-output recovery was used;
- no model reinvocation occurred.

Independently verify:
- chronology of request/response file creation;
- response file digest;
- reply text digest;
- round-0 durable effect;
- round-1 attempt state;
- whether exact response bytes existed before reconciliation;
- assistant observation identity;
- turn completion transition;
- no duplicate claim/assistant observation/meter/semantic effect;
- no post-hoc fabricated assistant reply.

If recovery depends on unverifiable after-the-fact prose, FAIL.

## 11. Anonymous local handler / provenance

The Resident reports:
- `usage=None`;
- `provenance=None`;
- provider/model/request IDs absent;
- no provider response receipts.

Independently adjudicate whether this is truthful and within the A-004 contract.

Verify:
- no fake provider identity;
- no fake token counts;
- no fake receipt;
- meter unknown is represented honestly;
- actual semantic outputs are bound to the current Resident session/evidence files.

Do not infer replacement-model/R6 provenance from this run.

Lack of provider identity alone is not automatically a blocker unless the A-004 contract requires it for Phase A; overclaiming such identity is a blocker.

## 12. Attention-watch step-boundary replay

This is another high-priority attack target.

The run states that PLATFORM mechanical ingest did not pass through the normal runtime observation listener, so the runner evaluated watches at the step boundary with Core `AttentionWatchService`.

Independently determine:
- exact code/path used;
- whether it is deterministic mechanical plumbing;
- whether it preserves canonical watch predicate semantics;
- whether evaluation happens only after the current event is legally ingested;
- whether it can see future events;
- whether it changes semantic decisions;
- whether it creates a parallel scheduler/truth store;
- whether the same behavior is expected from the accepted Core/runtime contract;
- whether this compensation makes the run noncanonical.

Do not accept the Resident's "mechanical" label without inspection.

If this path materially substitutes for required Core behavior in a way the contract disallows, FAIL.

## 13. Wake / Review / Summary / derivation completeness

Freshly enumerate all due work through the final cursor-13 timestamp.

Verify:
- every due Periodic Review;
- every due Wake;
- Summary jobs;
- dimension summaries;
- cognitive derivation bundles;
- deferred/queued work;
- completion states.

Distinguish:
- queued/prepared;
- running;
- completed.

No completion record means not confirmed.

Check there is no forced clock jump solely to manufacture a successful result.

## 14. Cognition semantics

Independently inspect the durable cognition lineage.

Do not score against old A-003 wording.

Check whether:
- User Understanding claims are evidence-grounded;
- revisions preserve lineage;
- communication experiences have real evidence;
- operation experience records real outcome/miss evidence;
- status discipline corresponds to actual user feedback;
- release failure/success understanding follows observed platform records;
- UNKNOWN/silence is used when appropriate;
- no Claim quota or synthetic "growth" exists.

Flag unsupported durable cognition as a blocker if material.

## 15. World/index coherence

Open the frozen World/index artifacts independently.

Verify:
- final World revision = declared value;
- final index watermark = World revision;
- no index lag;
- canonical conversation observations not duplicated;
- task/watch/claim/review/summary records correspond to the run ledger;
- cursor-1 and cursor-10 recoveries did not duplicate durable effects;
- final World can be opened consistently from frozen evidence.

## 16. Freeze manifest and hashes

Independently recompute:
- `MANIFEST.sha256`;
- `FREEZE_MANIFEST.json` references;
- world.db digest;
- index.db digest;
- release-state digest;
- runtime-state digest;
- checkpoint/step digests;
- recovery receipt hashes;
- decision request/response hashes.

Do not rely on the author-generated manifest as self-proof.

Any unexplained mismatch is a blocker.

## 17. Environment

Record actual review environment separately from run environment.

Run evidence claims:
- CPython 3.12.14;
- Pydantic 2.13.5;
- SQLite 3.40.1;
- frozen `aios_core` import.

Verify these claims mechanically where evidence permits.

A-004 is not RC certification, so SQLite 3.40.1 need not equal formal RC SQLite 3.45.1 unless behavior is shown to be version-sensitive.

## 18. Reviewer-authored probes

Create independent probes where useful.

Freeze each reviewer probe before first use:
- SHA-256;
- enumeration;
- source revision.

Preserve RED and harness corrections.

Suggested probes:
- cursor/ACK/future-leak audit;
- duplicate canonical USER observation audit;
- recovery duplicate-effect audit;
- decision request/response chronology audit;
- World/index/digest audit;
- watch-trigger ordering audit.

## 19. Durable review publication

Do not finish with chat-only verdict.

Create:
- review-only branch;
- formal report;
- reviewer probe sources/hashes;
- raw output/evidence;
- exact review commit;
- review-only / evidence-only / DO NOT MERGE PR;
- comment on PR #273 pointing to review PR + exact review SHA.

If publication fails after technical review, return:

`EVIDENCE_PUBLICATION_BLOCKED`

and do not pretend the gate is complete.

## 20. Verdict

Choose exactly one:

### `ACCEPTANCE_PASS / blocker=0`

Only if the exact A-004 evidence package proves a fresh, legal Phase-A run.

Then state:

`READY_FOR_PM_INTEGRATION`

### `ACCEPTANCE_FAIL / blocker=N`

Give every blocker:
- ID;
- exact evidence path;
- reproduction;
- observed;
- expected;
- why binding;
- minimal corrective scope.

### `REVALIDATION_REQUIRED`

If PR #273 head moved.

### `EVIDENCE_PUBLICATION_BLOCKED`

If review completed but durable publication failed.

## 21. Prohibitions

Do not:
- modify PR #273;
- merge PR #273;
- repair A-004;
- resume persistence Corrective-003;
- release or run Resident B;
- run Resident C;
- run final evaluator;
- close C15;
- merge or modify #263/#265.

Stop immediately after durable Independent Acceptance publication.
