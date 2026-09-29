# C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-INDEPENDENT-ACCEPTANCE

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Status:

`READY`

Role:

**Independent Fresh Resident A Evidence Acceptance Reviewer**

You are not:
- the Fresh Resident A;
- PR #296 author;
- PM;
- Core engineer;
- Operator Prep corrective engineer;
- persistence engineer;
- Resident B/C;
- final C15 evaluator.

Your only task:

> Independently attempt to falsify exact PR #296 and determine whether it proves a fresh, clean-room, legal and authentic Phase-A Resident run for cursor 1..13 using the accepted frozen RC and Operator Prep harness.

Do not repair the run.
Do not modify PR #296.
Do not merge anything.
Do not run Resident B/C.

## 1. Fresh-fetch and exact pin

Fresh-fetch live `main`, PR #296 metadata/head/diff, task board/checkpoint, this prompt and PM review-ready note.

Exact candidate:

- PR #296
- head `317316299c332d82e0cbd0431b5c7d50f391bc17`
- tree `a64b60ad1e64bcb930003f030246baafdae3eb8a`
- parent `f7bcec4e558ebb4c6a11b7b45afe361cc659ef66`

Evidence root:

`reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003/`

If PR #296 head moved, stop:

`REVALIDATION_REQUIRED`

Do not transfer acceptance to another SHA.

## 2. Relevant contracts and accepted execution identity

Read for review:
- clean-room contract;
- canonical Resident A run contract;
- PM Resident release adjudication;
- accepted Operator Prep packet/candidate identities;
- PR #296 evidence.

Frozen execution identity must be:
- software `f20f2edfa7af00d0286493fd15196ca9503bc315`
- repository tree `1ac3a675b884167d3a29aa432e7ef3eaff94d404`
- Core tree `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`

Accepted harness:
- Operator Prep H1 `77dac70e0cf054c3f0fb7d94a66dba221fe7d5de`
- packet SHA-256 `3c2d04c2de8557c3cb7329df4350c40b2ccc07520a7d3d51db206174b33266cc`

## 3. Evidence-only scope

Mechanically prove PR #296:
- has one commit on the authorized Resident-release parent;
- changes only the new Resident evidence directory;
- changes no `src/**`;
- changes no product `tests/**`;
- changes no Operator Prep harness/bootstrap;
- changes no fixture/evaluator/release source;
- changes no governance/run contracts.

Any hidden implementation modification is a blocker.

## 4. Freshness

Independently test that the run began with all-new:
- World;
- index;
- release-state;
- exchange ledger/root;
- runtime run state;
- Resident process ID;
- Resident session;
- conversation session;
- run identity.

Search evidence for reuse of:
- A-004 historical state;
- A-003/A-002/A-001 state;
- prior claims/summaries/replies;
- old request/response ledgers;
- old object IDs seeded into the World;
- B/C state.

The pre-cursor freshness audit is evidence, not self-proof.

## 5. Clean-room contamination audit

This is binding.

The Resident startup boundary allowed exactly:
1. clean-room contract;
2. canonical Resident run contract;
3. exact accepted Resident-safe launch packet;
4. mechanical environment/harness status.

Attempt to prove or falsify exposure to:
- task board/checkpoint;
- PM adjudications/review-ready reports;
- PR #292/#294 metadata/comments;
- prior Resident evidence;
- prior IA reports;
- Git history concerning prior Resident runs;
- fixture/evaluator/release source;
- future events;
- historical semantic summaries.

Inspect:
- request payloads;
- authored directives;
- evidence files;
- paths/values captured in runtime state;
- shell/tool traces if present;
- semantic echoes that cannot be explained by currently revealed reality.

Any material semantic contamination is a blocker.

Do not use old Resident wording as the expected answer.

## 6. Cursor/release reconstruction

Reconstruct independently from durable evidence.

Verify:
- phase A;
- sequences exactly 1..13;
- one current event per sequence;
- each event legally ingested;
- USER event uses canonical conversation ingest;
- PLATFORM event uses legal mechanical ingest;
- exact durable ACK follows ingest;
- ACK references the actual durable ingest ref;
- no skip/reorder/double reveal;
- release state progresses correctly;
- cursor 14 was never revealed;
- final `last_acked_sequence=13`;
- final `next_sequence=14`;
- `pending_reveal=null`.

Do not accept README assertions without raw receipts.

## 7. Temporal isolation / future leak

For each cursor, construct the set of reality legally available at that instant.

Compare every model request/snapshot and semantic response against:
- current and past revealed event projections;
- current World state;
- legal capability results;
- current-session interaction history.

Search for:
- future event IDs;
- future exact payload fragments;
- future platform success/failure facts;
- future digest/status values;
- later task outcomes;
- future release-state fields.

Any future semantic leak is a blocker.

## 8. Resident semantic authenticity

There are 21 durable model exchanges.

For all 21, or enough plus automated exhaustive provenance checks to cover all 21, verify:

`RuntimeSnapshot/request -> Resident-authored response -> durable response publication -> consume -> capability/final effect`

Check that:
- response bytes are external-current-Resident-session outputs;
- no test responder or deterministic semantic callback generated real-run responses;
- accepted harness only transports/validates bytes and executes chosen legal calls;
- no keyword-to-capability mapping;
- no fixture/event-ID semantic branching;
- no prewritten final replies;
- no scripted Claims/revisions/policies/silence.

Do not request or require hidden chain-of-thought.

Evaluate authenticity from visible request/result/output provenance.

## 9. Exchange chronology

Independently verify all 21 requests have exactly:

- one `request_published`;
- one `response_published`;
- one `response_consumed`;

with:
- request digest binding;
- response digest binding;
- correct event order;
- monotonic ledger sequence;
- valid prev-hash chain;
- no duplicate semantic dispatch;
- no orphan response;
- no unconsumed durable response.

Expected final:
- 63 ledger records;
- 21/21 COMPLETE;
- 0 unconsumed;
- 0 open dispatched.

Recompute integrity, do not trust `exchange_final_state.json` alone.

## 10. Accepted harness immutability

Verify actual run-time harness/bootstrap bytes equal the accepted Operator Prep identities.

No harness patch after cursor 1 is permitted.

Check:
- packet SHA;
- harness manifest;
- relevant exchange module hashes;
- bootstrap hash;
- RC identity.

If any real-run implementation differs from the accepted harness, FAIL.

## 11. USER canonical conversation audit

For each USER cursor:
- verify canonical observation identity;
- session ID and positive monotonic turn index;
- exact released text/time binding;
- ordinary runtime turn reuses canonical observation rather than duplicating it;
- at most one durable assistant output for the completed turn.

Audit World for duplicate USER observations caused by run_turn re-ingest.

## 12. PLATFORM ingest audit

For each PLATFORM cursor:
- verify event was legally revealed first;
- ingest projection exactly matches current released event;
- no future payload attached;
- durable ingest ref exists;
- ACK matches that ref;
- no fabricated observation.

## 13. Wake / Review / Summary / derivation completeness

Freshly enumerate everything due at each released timestamp.

Verify:
- all due Wake work;
- all Periodic Review work;
- Summary work;
- dimension summaries;
- derivation bundles;
- deferred/queued work;
- final completion state.

For each:
- distinguish prepared/queued/running/completed;
- require durable completion record before calling completed;
- verify no forced future clock jump;
- verify no due work was skipped merely because there was no USER turn.

Cursor-13 confirmation restart must be independently inspected, not treated as self-proof.

## 14. Final restart / recovery proof

Use frozen evidence in a disposable reviewer environment.

Re-open the final World/index/release/exchange state with the accepted harness/frozen Core where possible.

Verify:
- World revision = 38;
- index watermark = 38;
- no index lag;
- exchange classifies COMPLETE;
- no durable-unconsumed/open-dispatched request;
- no additional due work at the frozen cursor-13 timestamp;
- restart does not mutate World merely by recovery;
- cursor 14 remains unrevealed.

## 15. Cognition semantics

Do not compare against old A wording.

Inspect durable cognition from this run and judge only against legally available evidence.

Check:
- every durable Claim is evidence-grounded;
- revisions/retractions have valid lineage;
- cognitive policies are supported by observed USER feedback/reality;
- communication/operation experiences cite real evidence;
- tasks/watches correspond to actual current reality;
- UNKNOWN/HYPOTHESIS/silence used when evidence is insufficient;
- no unsupported completion report;
- no Claim quota or synthetic “growth”;
- Summary/Wake/task completion is not misused as evidence of external reality.

A materially unsupported durable cognition object is a blocker.

## 16. User-facing reply discipline

For every assistant response:
- verify it is supported by current World/evidence;
- verify no future status leakage;
- verify prepared/queued is not called completed;
- verify platform completion is claimed only after a completion record;
- verify silence where no response is needed is legal.

## 17. World/index coherence

Open the final SQLite artifacts independently.

Verify:
- World revision 38;
- index watermark 38;
- index corresponds to World;
- object/revision references resolve;
- evidence-set/dependency links are valid;
- no duplicate canonical USER ingest;
- no objects whose provenance points to unrevealed future reality;
- 21 model exchanges' durable effects correspond to the final World.

Record a mechanical inventory independently.

## 18. Release-state and cursor14 proof

Inspect the release-state bytes directly.

Verify:
- 13 receipts and only 13;
- receipts correspond to sequence 1..13;
- no sequence-14 receipt;
- no pending reveal;
- next sequence is 14;
- no cursor14 event projection exists anywhere in candidate evidence.

Search package content for any unreleased event/payload beyond cursor13.

## 19. Freeze/checksum audit

Independently recompute:
- every entry in `SHA256SUMS`;
- ensure it covers every package file except itself;
- World digest;
- index digest;
- release-state digest;
- exchange ledger digest;
- freeze manifest digest;
- runtime identity files;
- per-cursor event/ingest/ACK/result digests.

Expected package checksum file SHA-256:
`1eee5df0650ed03b50bfe0ef558d93076d13ecb32772b036c91b9d8cd8c84bef`

Expected World:
`0d6970ed99367a456e4baa29092bde8f15bc7544496095cc87ad9f029e2603b2`

Expected index:
`79c877a4bf75091fa90ae81076a6bdb2e265cf6376b657c3f195e9e91f9844e5`

Expected release-state:
`6b90fc7a09bce7d575dbcb783dcbe838cab81c2e358515adbb5dca9731f57c37`

Expected exchange ledger:
`3b2b9e902133c31cc583491aae55834ee9cb71a9bea9ca50a36fd7e8b81da021`

Expected final ledger head:
`7f8afff395442a1d926144bfccb51429faf807490660fd95a9df65616ebba691`

Any unexplained mismatch is a blocker.

## 20. Reviewer environment

Build/use a reviewer-qualified environment independently where executable validation is needed.

Do not mutate the candidate evidence.

Record review environment separately from run environment.

The run claims:
- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2
- SQLite 3.45.1
- OpenSSL 3.0.13
- frozen Core import path

Verify mechanically.

## 21. Reviewer-authored probes

Author probes for this exact run.

Freeze source/hash/enumeration before first candidate execution.

Suggested exhaustive probes:
- cursor/reveal/ACK chronology;
- future-leak scan by cursor;
- clean-room forbidden-material scan;
- 21-exchange request/response/result chronology;
- USER canonical-ingest duplicate audit;
- due-work completeness audit;
- World provenance/coherence audit;
- final restart/recovery audit;
- package checksum coverage.

If a reviewer probe is defective:
- preserve old revision/results;
- make a corrected revision;
- freeze before execution.

Never tune expectations silently.

## 22. Durable publication

Chat verdict alone is not acceptance.

Create:
- a review-only evidence directory;
- formal IA report;
- reviewer probes/hashes/enumeration;
- raw outputs;
- environment record;
- exact review commit;
- review-only / evidence-only / DO NOT MERGE PR.

If the Arena session is bound to a preassigned branch, use that review branch and do not alter the candidate branch.

Comment on PR #296 with:
- review PR number;
- exact review SHA;
- verdict;
- blocker count.

## 23. Verdict

Choose exactly one.

### PASS

`ACCEPTANCE_PASS / blocker=0`

Then:

`READY_FOR_PM_INTEGRATION`

This does not authorize Persistence/B/C/evaluator.

### FAIL

`ACCEPTANCE_FAIL / blocker=N`

For every blocker include:
- ID;
- exact evidence path;
- reproduction;
- observed;
- expected;
- binding reason;
- minimal corrective scope.

Do not repair in the IA window.

### Candidate drift

`REVALIDATION_REQUIRED`

### Publication blocked

`EVIDENCE_PUBLICATION_BLOCKED`

Preserve local review identity/evidence.

## 24. Prohibitions

Do not:
- modify/merge PR #296;
- repair Resident A evidence;
- resume Persistence Corrective-003;
- run Resident B;
- run Resident C;
- run evaluator/C15 close;
- alter accepted Operator Prep harness;
- modify/merge #263/#265;
- publish public tag/release.

Stop immediately after durable IA publication.
