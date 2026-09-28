# C15-RCC-RES-A-RERUN-004-CORRECTIVE-002

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Status:

`READY`

Role:

**Real Resident AI — Fresh Corrective Resident A**

Your task:

> Build and freeze a mechanically correct Resident exchange harness that is proven compatible with the actual frozen Core runtime types, then run a completely fresh Phase A cursor 1..13 with semantic decisions made by the actual Resident session rather than by a Python semantic script.

## 1. Fresh start

Fresh-fetch current `main`.

Read:

- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `governance/C15_RCC_RES_A_RERUN_004_CORRECTIVE_001_BLOCKED_ADJUDICATION_2026-09-28.md`
- `governance/C15_RCC_RES_A_RERUN_004_IA_FAILURE_ADJUDICATION_2026-09-28.md`
- `governance/CORE_RC_REFREEZE_003_INTEGRATION_RECEIPT_2026-09-28.md`
- `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_RUN_CONTRACT.md`

Confirm:

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-002 = READY`

## 2. Frozen RC execution identity

Resident execution software remains exactly:

- software `f20f2edfa7af00d0286493fd15196ca9503bc315`
- Core tree `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`

Mechanically verify the detached checkout.

Do not run Resident semantics from live main.

## 3. Historical evidence isolation

Historical exacts:

- failed A-004 PR #273 @ `f251e9c0026a0f97fdee20397936cb5e3b18c61c`
- failed IA PR #275 @ `ccd5f539714604f5ff5912b90024f28b82618511`
- blocked Corrective-001 PR #277 @ `2968299beea5fe5ec2dc93418d0fa7f3e035ec40`

Do not modify them.

As the new Resident, do not read or reuse their semantic:
- decisions;
- claims;
- replies;
- summaries;
- cognition;
- operation experiences;
- World/index.

You may know only the abstract mechanical failure rules in governance.

## 4. Formal runtime environment

Use the same interpreter for:
- pre-run harness tests;
- harness freeze verification;
- real Resident run.

Required:

- CPython 3.12.14
- Pydantic 2.13.5

Record actual:
- SQLite
- OS/kernel/arch
- `aios_core.__file__`

Do not run the binding pre-reveal harness gate under Python 3.11.

## 5. Correct frozen Core types

The harness must treat frozen:

`CapabilityResult`

as exactly:

- `name`
- `ok`
- `data`
- `error_code`
- `error_message`
- `call_id`

Do not access nonexistent:
- `arguments`
- `result`
- `error`
- `duration_seconds`

Serialize the actual frozen dataclass shape, preferably mechanically from the dataclass or an explicitly tested schema.

## 6. Mandatory pre-reveal test layers

Before release-state init and before cursor 1 reveal, run all of the following using CPython 3.12.14.

### Layer A — exchange bridge

Retain the prior atomic/durable tests:

- request-id roundtrip;
- request SHA binding;
- response SHA binding;
- atomic response publish;
- no partial response consumption;
- monotonic ledger;
- hash-chain tamper detection;
- crash before request publication;
- crash after request publication;
- torn response write;
- recovery after response publication;
- publication chronology;
- request-id mismatch;
- digest mismatch.

### Layer B — frozen-Core contract tests

Import the actual frozen Core classes.

At minimum test runner request serialization with:

1. empty `capability_history`;
2. successful `CapabilityResult` with non-empty `data`;
3. failed `CapabilityResult` with `error_code/error_message`;
4. multiple results with distinct `call_id` values.

Assert the serialized request contains the exact legal fields and no exception occurs.

### Layer C — integrated two-round runtime test

Use a disposable synthetic World with no C15 fixture content.

Drive a real frozen Core runtime through:

- round 0 model request;
- deterministic test-only response containing at least one legal capability call;
- capability execution;
- round 1 model request with non-empty `capability_history`;
- deterministic terminal response/silence.

The test must prove the actual runner can serialize and publish the second-round request.

This test is plumbing only.

Its deterministic test callback must not be used during the real Resident run.

### Layer D — real-run no-semantic-script guard

Mechanically assert that the real execution mode:
- has no `resident_agent.py` semantic router;
- has no keyword-to-capability table;
- has no fixture/event-ID semantic branching;
- has no prewritten Resident final reply;
- has no persistent callback that decides cognition.

Real-run model callback must be absent/disabled.

## 7. Freeze before cursor 1

After all pre-run tests pass:

freeze:
- runner;
- bridge;
- response publisher tool;
- ledger implementation/schema;
- all pre-run tests;
- test output;
- environment record;
- SHA256SUMS;
- harness freeze manifest.

Record hashes.

Only after this freeze may you initialize real release-state / reveal cursor 1.

After cursor 1 reveal, these artifacts are immutable.

Any harness defect after cursor 1 => `BLOCKED`.

## 8. Real Resident semantic path

During the real run, the runner must not generate semantic answers.

For every decision:

1. runner durably publishes request;
2. current Resident AI session inspects the legal request;
3. Resident personally decides:
   - capability calls;
   - response;
   - silence;
   - summary text;
4. a mechanical response-publisher publishes the exact bytes through the frozen bridge;
5. runner consumes the durable response.

The publisher may validate:
- request ID;
- hashes;
- schema;
- chronology.

It may not decide meaning.

## 9. Fresh durable state

Create all-new:
- World;
- index;
- release-state;
- runtime/checkpoint;
- Resident session ID;
- conversation session ID;
- process/run ID;
- exchange ledger;
- decision request/response directories;
- evidence directory.

No reuse from prior A runs.

## 10. Strict Phase A

Run exactly:

`cursor 1..13`

For each cursor:
- reveal one event;
- legal ingest;
- exact ACK;
- index catch-up;
- advance only to legal current event time;
- run due Wake/Review/Summary/derivation;
- actual Resident handles each semantic request;
- complete due work before advancing.

Never reveal cursor 14.

## 11. Recovery discipline

The exchange rules from Corrective-001 remain binding:

- request-published = semantic dispatch boundary;
- after request publication, null provider fields do not prove non-dispatch;
- exact response must be atomically published and durably ordered before consumption/recovery;
- partial/torn/ambiguous state fails closed;
- uncertain Resident output is never regenerated merely to continue.

If a real-run harness defect appears after cursor 1:
- preserve state;
- do not patch;
- return `BLOCKED`.

## 12. Attention-watch plumbing

If external canonical/mechanical ingest requires explicit evaluation:

- use accepted Core `AttentionWatchService`;
- current event must already be legally ingested;
- process observations in World-revision order;
- no future visibility;
- no predicate rewrite;
- no second scheduler/truth store.

Record it mechanically.

## 13. Evidence

Freeze evidence sufficient to prove:

- exact RC;
- exact CPython/runtime environment;
- pre-reveal tests and harness hashes;
- no semantic script in real-run execution;
- fresh identities;
- cursor 1..13 release/ingest/ACK chain;
- decision exchange chronology;
- actual Resident responses;
- capability/result history;
- recovery state;
- Wake/Review/Summary lifecycle;
- World/index coherence;
- cursor 14 not revealed;
- final digests.

Do not expose private chain-of-thought.

## 14. Exit

Choose exactly one:

### `PHASE_A_COMPLETE / REVIEW_READY`

Then:

`READY_FOR_INDEPENDENT_ACCEPTANCE`

Only if all binding requirements pass.

### `BLOCKED`

For any binding failure.

Create a new evidence-only PR.

Do not reuse #277.

Do not self-accept.
Do not resume persistence.
Do not run B/C/evaluator.
Do not merge or modify #263/#265.
