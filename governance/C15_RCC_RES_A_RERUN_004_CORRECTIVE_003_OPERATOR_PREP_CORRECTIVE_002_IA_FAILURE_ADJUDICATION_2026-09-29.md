# C15 Corrective-003 Operator Prep Corrective-002 IA Failure Adjudication — 2026-09-29

## Status

```text
C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-002
= ACCEPTANCE_FAIL / blocker=2
= HISTORICAL_FAILED_EXACT / IMMUTABLE

C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003
= READY

C15-RCC-RES-A-RERUN-004-CORRECTIVE-003
= BLOCKED_ON_OPERATOR_PREP
```

This is a PM governance adjudication.

It does not modify or merge PR #288 or review PR #290.
It does not release a Resident.
It does not authorize Core product changes.

## Exact failed candidate

PR #288:

- final freeze H2: `771b200c33dbd6055b1d209935f8e1552f13090f`
- H2 tree: `071b51c5fb37dc59fc8941dee2182637b9f87daa`
- sole parent / corrected H1: `63c972ad7a19671cbdf809177f7a552aa2c2ecc6`
- H1 tree: `8cd4a2d8b4cdf1f85699c5d78166f774741b420b`

Fresh Independent Acceptance:

- review-only PR #290
- exact review head: `39408137edf77976d0c4833fcde551891d5d081a`
- verdict: `ACCEPTANCE_FAIL / blocker=2`

PR #288 and PR #290 are historical exact evidence and must remain immutable.

## IA288-01 — VALID_BINDING_BLOCKER

### Finding

Exact path:

`reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP/harness/aios_exchange/ledger.py`

`ExchangeLedger.append()` performs:

1. validated read of the current ledger;
2. sequence/prev-hash allocation;
3. record construction;
4. append + file fsync;

without a shared inter-writer serialization boundary.

Two independent writers can therefore both validate the same legal prefix, both allocate the same next sequence and predecessor, and both append successfully.

Fresh reviewer probe forces only that legal scheduling interleaving. It does not mutate candidate source or ledger bytes.

Observed:

- both append calls return success;
- resulting ledger contains conflicting duplicate sequence allocation;
- next integrity read reports a non-monotonic chain.

### PM adjudication

`IA288-01 = VALID_BINDING_BLOCKER`

A successful durable exchange mutation must leave the durable state valid at the point success is returned.

Detecting the corruption only on the next operation is insufficient.

### Minimal corrective scope

Introduce an enforceable single-writer/transaction boundary for every exchange mutation whose correctness depends on the current ledger prefix.

At minimum the critical section must cover:

- current durable-state read;
- integrity validation;
- request sequence / request-id allocation where applicable;
- sequence and prev-hash allocation;
- request/response/consume state validation;
- ledger append;
- required file/directory durability operations before success.

The boundary must work across independent objects and processes, not only one Python object instance.

A process-local lock alone is insufficient.

A file lock / OS-level exclusive lock or an equivalent mechanically enforceable single-writer protocol is acceptable.

Tests must include:

- two independent ledger writers;
- two independent request publishers;
- same-request duplicate publication;
- different-request simultaneous publication;
- response/consume overlap where applicable;
- at least one subprocess/interprocess case.

Do not create a second truth store or generic distributed transaction system.

## IA288-02 — VALID_BINDING_BLOCKER

### Finding

Exact paths:

- `harness/aios_exchange/atomic.py`
- `harness/aios_exchange/requests.py`
- `harness/aios_exchange/ledger.py`

Current `fsync_dir()` converts directory-open or directory-fsync `OSError` into `False`.

`atomic_write_bytes()` returns this only as receipt metadata.

`RequestPublisher.publish()` ignores that receipt.

`ExchangeLedger.append()` also calls `fsync_dir()` when the ledger file is newly created and ignores the returned boolean.

Therefore a required directory-durability primitive can fail while request publication or ledger append still returns success.

### PM adjudication

`IA288-02 = VALID_BINDING_BLOCKER`

The approved Operator Prep treats durable request publication as the semantic dispatch boundary.

A visible renamed file is not enough if the required directory fsync failed.

Actual directory durability failure must be fail-closed before success is returned.

### Minimal corrective scope

Required durability failures must propagate.

For the qualified Linux environment:

- failure to open the containing directory for required fsync must fail;
- directory `os.fsync` failure must fail;
- request/response atomic publication must not return success when directory durability failed;
- durable ledger creation/publication must not return success when its required directory durability failed.

The correction must also handle the retry/recovery boundary safely:

- a failed first publication must not later be silently treated as a proven durable dispatch merely because bytes remain visible;
- retry may succeed only after the required durability condition is re-established and all exchange invariants still hold;
- no duplicate semantic dispatch may be introduced.

Tests must include injected directory-open and directory-fsync failure on:
- request publication;
- response publication;
- initial ledger creation;
- retry after failed durability step.

## Supplemental reviewer observation

Review #290 also records request-file mutation before direct `ExchangeBridge.consume_response()` as a hardening concern.

PM does not elevate that observation into a third blocker in this adjudication because the accepted real runner recovery path independently validates the durable request body/snapshot before semantic consumption, and the reviewer did not demonstrate semantic cross-binding through the approved runner.

Corrective-003 may add a narrow integrity regression if convenient, but it must not expand scope or be used to justify architecture changes.

## Preserve all existing GREEN

Corrective-003 must preserve:

- #283 C1–C3 closures;
- #284 C4–C9 closures;
- snapshot binding;
- operational ledger validation;
- frozen RC identity;
- exact runtime pins;
- four-input startup boundary;
- due-work entrypoint;
- Gate A/B/C/D;
- semantic-script isolation;
- packet `PREP_REVIEW_READY`;
- no real Resident execution.

## Corrective discipline

Task:

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003`

must repair only IA288-01 and IA288-02.

Before implementation:

1. author targeted reviewer-style corrective probes;
2. freeze probe source/hash/enumeration/expected outcomes;
3. execute them against exact failed #288 H2/H1 as appropriate;
4. preserve genuine RED evidence.

Then create a new branch from current live main, carry forward the exact #288 Operator Prep package, and apply only the two authorized corrections.

Do not continue or modify PR #288.

## Required post-fix proof

The new candidate must provide:

- targeted IA288-01/02 baseline RED;
- same frozen probes candidate GREEN;
- interprocess concurrency proof;
- directory durability fault-injection proof;
- C1–C9 regression GREEN;
- full Gate A/B/C/D rerun;
- fresh clean bootstrap under exact runtime pins;
- regenerated packet/audit/manifests/checksums;
- packet status `PREP_REVIEW_READY`;
- zero Core/product-test/fixture/evaluator/release-source drift;
- no real Resident execution.

## Downstream

Until Corrective-003 Operator Prep receives fresh Independent Acceptance PASS and PM integration:

- real Corrective-003 Resident = BLOCKED;
- persistence Corrective-003 = BLOCKED;
- Resident B/C = BLOCKED;
- evaluator / C15 close = BLOCKED.
