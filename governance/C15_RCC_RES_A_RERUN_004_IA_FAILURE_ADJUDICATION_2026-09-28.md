# C15-RCC-RES-A-RERUN-004 Independent Acceptance Failure Adjudication — 2026-09-28

## Status

```text
C15-RCC-RES-A-RERUN-004
= ACCEPTANCE_FAIL / blocker=2
= HISTORICAL_FAILED_EXACT / IMMUTABLE

C15-RCC-RES-A-RERUN-004-CORRECTIVE-001
= READY
```

This is a PM governance adjudication.

It does not repair the failed run.
It does not rewrite historical evidence.
It does not authorize persistence, Resident B/C, evaluator, or C15 close.

## Exact failed evidence

Resident evidence PR:

- PR #273
- exact head: `f251e9c0026a0f97fdee20397936cb5e3b18c61c`
- parent: `0b17c7f35697dc4a24b731185868d29967efcf58`
- tree: `fd312286b7b83cd550ecc49d72b78656e6e91b71`

Independent review:

- review-only PR #275
- exact review head: `ccd5f539714604f5ff5912b90024f28b82618511`
- verdict: `ACCEPTANCE_FAIL / blocker=2`

Failed exact #273 remains immutable historical evidence.

No hash-swap or post-hoc modification may convert it into an accepted run.

## Binding blocker IA-A004-01

### Finding

Cursor 1 was reconciled as `not_submitted` after a local file-handshake echo error.

The evidence shows that:

- a model-decision request had already been published;
- a complete semantic response had already been produced;
- the response failed request-id echo validation;
- provider/model/request/meter fields were null because this was an anonymous local handler path.

Null provider fields do not prove that the Resident/model was never invoked.

A semantic response is positive evidence that semantic dispatch occurred.

### PM adjudication

`IA-A004-01 = VALID_BINDING_BLOCKER`

This is not a demonstrated duplicate World effect and not a Core exactly-once regression.

It is a recovery-classification/evidence failure in the run harness.

Once a semantic request has been published to the Resident/model boundary, the run must not use `reconcile_not_submitted` merely because the response later fails local handshake validation.

### Corrective rule

For the corrective run:

- "request published to Resident" is the semantic-dispatch boundary;
- `not_submitted` reconciliation is allowed only when durable evidence proves failure happened **before request publication**;
- after request publication, null provider fields cannot establish non-dispatch;
- ambiguous post-publication failure must fail closed or follow a recovery path valid for an already-invoked local handler;
- no duplicate model decision may be created merely to recover an uncertain post-publication response.

## Binding blocker IA-A004-02

### Finding

Cursor 10 ultimately had matching final response/reply/assistant digests, but the evidence package did not contain durable ordered evidence proving that the exact Resident reply bytes existed before turn reconciliation.

Final hash equality proves consistency of the final package.

It does not prove historical chronology.

### PM adjudication

`IA-A004-02 = VALID_BINDING_BLOCKER`

This is an evidence chronology failure, not a finding that the reply was actually fabricated.

The historical run cannot manufacture the missing chronology after the fact.

### Corrective rule

The corrective run must durably bind every Resident response **before Core consumes it or any recovery uses it**.

Minimum required response-publication sequence:

1. request is durably published with request ID and request SHA-256;
2. Resident writes complete response to a temporary file;
3. temporary file is flushed/fsynced;
4. response is atomically published with `os.replace`/equivalent;
5. containing directory is fsynced where supported;
6. an append-only exchange ledger records:
   - monotonic sequence;
   - request ID;
   - request SHA-256;
   - response SHA-256;
   - response-published event;
   - wall-clock timestamp;
7. ledger append is flushed/fsynced;
8. only then may the runner consume the response;
9. consumption is separately recorded in the ledger.

A torn/partial response, missing response-published record, digest mismatch, or ambiguous exchange state must fail closed.

A retrospective timestamp or recomputed final hash is not a substitute.

## Corrective scope

The corrective task is:

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-001`

It is a **fresh Phase-A rerun**, not an edit of #273.

It must use the same accepted RC-003 software:

- software: `f20f2edfa7af00d0286493fd15196ca9503bc315`
- Core tree: `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- tests tree: `7e33b5ef8432370234965d3ccd61248c703c4019`

No Core fix is authorized by these findings.

Allowed corrective work is limited to run-local deterministic transport/evidence plumbing needed to make the Resident/model exchange auditable and fail-closed.

## Mandatory pre-run harness freeze

Before release-state initialization or cursor 1 reveal:

- build the corrective run-local bridge/runner;
- run synthetic plumbing-only tests that contain no C15 fixture content and no Resident semantics;
- prove:
  - request-id roundtrip;
  - atomic response publication;
  - no partial JSON consumption;
  - exchange ledger fsync/digest binding;
  - fail-closed torn-write behavior;
  - no `not_submitted` after request publication;
- compute SHA-256 for the runner/bridge;
- freeze it.

After cursor 1 reveal, the runner/bridge is immutable.

If a new harness bug is discovered after the real run starts:

`BLOCKED`

Do not patch the harness mid-run and continue.

## Fresh Resident requirement

The corrective run must create all-new:

- World;
- index;
- release-state;
- runtime/checkpoint;
- Resident session;
- conversation session;
- process/run identity;
- evidence directory.

It must not import semantic state from failed A-004.

The Resident window must not read old A-004 decisions, claims, responses, summaries, or semantic report material.

Knowledge of the abstract transport/recovery blocker is permitted only to enforce mechanical safety.

## Historical evidence preservation

Preserve:

- PR #273 exact failed Resident run;
- PR #275 exact failed Independent Acceptance;
- all reviewer probes/raw logs;
- both blocker IDs and reproduction.

Do not amend, squash, replace, or rewrite them.

## Downstream state

Until corrective run + fresh Independent Acceptance PASS + separate PM integration:

- persistence Corrective-003 = BLOCKED;
- Resident B = BLOCKED;
- Resident C = BLOCKED;
- persona/final evaluator gates do not advance;
- C15 close = BLOCKED.
