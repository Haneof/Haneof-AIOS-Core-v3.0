# C15-RCC-RES-A-RERUN-004-CORRECTIVE-001

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Status:

`READY`

Role:

**Real Resident AI — Fresh Corrective Resident A**

This is a fresh Phase-A rerun after A-004 failed Independent Acceptance because of two run-evidence/recovery-proof defects.

You are not repairing the historical A-004 run.

You must not read or imitate its semantic decisions.

Your task:

> Build and freeze a mechanically correct, auditable Resident exchange bridge before any fixture reveal, then live Phase A cursor 1..13 from a completely fresh World using the accepted RC-003 software.

## 1. Start from current governance, execute frozen RC

Fresh-fetch current `main`.

Read:

- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `governance/C15_RCC_RES_A_RERUN_004_IA_FAILURE_ADJUDICATION_2026-09-28.md`
- `governance/CORE_RC_REFREEZE_003_INTEGRATION_RECEIPT_2026-09-28.md`
- `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_RUN_CONTRACT.md`

Confirm:

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-001 = READY`

Execution software remains exactly:

- software `f20f2edfa7af00d0286493fd15196ca9503bc315`
- Core tree `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`

Mechanically verify the detached execution checkout before running.

Do not execute Resident semantics from live main.

## 2. Historical failed run is forbidden semantic material

Historical evidence:

- failed Resident PR #273 @ `f251e9c0026a0f97fdee20397936cb5e3b18c61c`
- failed review PR #275 @ `ccd5f539714604f5ff5912b90024f28b82618511`

These are immutable history.

As the new Resident, do NOT read:

- old A-004 decision requests/responses;
- old A-004 claims;
- old A-004 summaries;
- old A-004 user replies;
- old A-004 operation experiences;
- old A-004 World/index;
- old A-004 semantic report sections;
- A-003/A-002/A-001 semantics.

You may know only the two abstract mechanical corrective rules below.

## 3. Corrective rule A — semantic dispatch boundary

A Resident/model request is considered semantically dispatched once the request is durably published to the Resident exchange boundary.

Therefore:

- `not_submitted` recovery is permitted only when failure is durably proven to occur before request publication;
- after request publication, null provider/model/request/meter fields are not proof of non-dispatch;
- if response state becomes ambiguous after request publication, do not re-invoke the Resident/model merely by classifying it not_submitted;
- fail closed or use only a Core recovery path that is legal for an already-invoked local handler.

## 4. Corrective rule B — atomic durable response publication

Before any response may be consumed or used in recovery:

1. request record is durably published with request ID + request SHA-256;
2. Resident writes response bytes to a temporary file;
3. temporary file is flushed and fsynced;
4. response is atomically renamed/published;
5. containing directory is fsynced where supported;
6. append-only exchange ledger writes a `response_published` record containing:
   - monotonic sequence;
   - request ID;
   - request SHA-256;
   - response SHA-256;
   - wall-clock timestamp;
7. ledger append is flushed/fsynced;
8. runner may only then read/consume the response;
9. runner records a later `response_consumed` event.

Partial JSON, digest mismatch, missing publication record, or ambiguous state => STOP / BLOCKED.

Do not retroactively create publication evidence.

## 5. Mandatory pre-run plumbing test and freeze

Before:
- release-state init;
- fixture reveal;
- World semantic processing;

build the new run-local mechanical runner/bridge.

Synthetic plumbing test must use no C15 fixture content and no semantic expected answers.

Test at minimum:

- correct request-id echo;
- atomic response publication;
- reader cannot observe partial response;
- response hash matches ledger;
- request hash matches ledger;
- monotonic event sequence;
- process crash/torn write before response publication fails closed;
- crash after response publication but before consumption leaves a recoverable, durably ordered response;
- `not_submitted` is impossible once request-published exists.

Freeze:

- runner/bridge source;
- synthetic test source;
- SHA-256 manifest;
- test output.

After real cursor 1 reveal, these files may not change.

If the harness has a defect after cursor 1 starts:

`BLOCKED`

Do not patch and continue.

## 6. Fresh state

Create all-new:

- private World;
- index;
- release-state;
- Resident session ID;
- conversation session ID;
- process/run ID;
- runtime/checkpoint;
- decision exchange directory;
- append-only exchange ledger;
- evidence package.

No reuse from any prior A run.

## 7. Resident contract

Follow:

`reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_RUN_CONTRACT.md`

The actual Resident decides semantics.

The runner may:
- transport bytes;
- persist mechanical evidence;
- execute legal capabilities selected by the Resident;
- perform deterministic ingest/index/runtime plumbing.

It may not:
- select claims based on fixture/event IDs;
- contain expected answers;
- branch semantically on keywords;
- synthesize Resident responses;
- decide retain/revise/retract;
- fabricate provider provenance/usage.

## 8. Strict Phase A

Run exactly:

`cursor 1..13`

For each cursor:

- reveal exactly one event;
- legal ingest;
- exact durable ACK;
- index catch-up;
- advance time only to legal current time;
- execute due Wake/Review/Summary/derivation work;
- Resident personally handles every semantic decision request;
- finish currently due work before advancing.

Never reveal cursor 14.

## 9. Response chronology evidence

For every Resident/model decision request, preserve:

- request bytes/hash;
- request-published ledger record;
- response bytes/hash;
- response-published ledger record;
- response-consumed ledger record;
- resulting capability/response outcome.

The ledger must be append-only and hash chained or otherwise tamper-evident.

Unknown provider/model/token provenance is allowed if truthful.

Do not invent provider receipts.

## 10. Recovery discipline

If any failure occurs:

- first inspect durable exchange ledger and Core attempt/turn state;
- classify only from contemporaneous durable evidence;
- never use absence of provider IDs as proof of non-dispatch;
- never regenerate an uncertain Resident answer;
- never overwrite old response bytes;
- preserve failed artifacts.

If legal recovery cannot be proven:

`BLOCKED`

## 11. Evidence package

Freeze evidence sufficient for a later independent reviewer to verify:

- exact RC identity;
- fresh-state identities;
- harness pre-run freeze/hash/test;
- cursor 1..13 reveal/ingest/ACK chain;
- decision exchange chronology;
- Core attempt/turn recovery state;
- capability results;
- Wake/Review/Summary lifecycle;
- final World/index coherence;
- cursor14 not revealed;
- all critical SHA-256 digests.

Do not expose private chain-of-thought.

## 12. Exit

Choose exactly one:

### `PHASE_A_COMPLETE / REVIEW_READY`

Then:
`READY_FOR_INDEPENDENT_ACCEPTANCE`

Only if:
- all 13 cursors complete;
- no semantic contamination;
- no mid-run harness mutation;
- no unresolved exchange ambiguity;
- evidence is frozen.

### `BLOCKED`

If any binding condition fails.

Create a new evidence-only PR with a new exact head.

Do not modify/reuse #273.

Do not self-accept.
Do not resume persistence.
Do not run B/C/evaluator.
Do not merge #263/#265.
