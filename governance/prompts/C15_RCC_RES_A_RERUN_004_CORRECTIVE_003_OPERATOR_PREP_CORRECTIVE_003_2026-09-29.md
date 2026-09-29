# C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Status:

`READY`

Role:

**Resident Launch / Test Infrastructure Corrective Engineer**

You are not:
- Resident A/B/C;
- Independent Acceptance Reviewer;
- PM;
- Core product engineer;
- semantic evaluator.

Your only task:

> Preserve all existing Operator Prep Corrective-002 fixes and close exactly the two fresh IA blockers from review PR #290: exchange mutation concurrency/linearization and fail-closed directory durability. Produce a new frozen Operator Prep candidate and stop at REVIEW_READY. Do not run a real Resident.

## 1. Fresh start

Fresh-fetch live `main`.

Read:
- current task board/checkpoint;
- `governance/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_OPERATOR_PREP_CORRECTIVE_002_IA_FAILURE_ADJUDICATION_2026-09-29.md`;
- Corrective-002 prompt and PM review-ready note;
- review PR #290 report;
- clean-room contract;
- canonical Resident A run contract.

Confirm:

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003 = READY`

Do not run a real Resident.

## 2. Historical exacts

Failed Corrective-002:
- PR #288 H2 `771b200c33dbd6055b1d209935f8e1552f13090f`
- H1 `63c972ad7a19671cbdf809177f7a552aa2c2ecc6`

Fresh failed IA:
- PR #290 exact review `39408137edf77976d0c4833fcde551891d5d081a`
- verdict `ACCEPTANCE_FAIL / blocker=2`

All historical candidate/review PRs remain immutable.

Do not modify #288 or #290.

## 3. Frozen RC remains unchanged

- software `f20f2edfa7af00d0286493fd15196ca9503bc315`
- repository tree `1ac3a675b884167d3a29aa432e7ef3eaff94d404`
- Core tree `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`

No `src/aios_core/**` or product `tests/**` modification is authorized.

## 4. Preserve all existing GREEN

Do not regress:
- response replay on-disk verification;
- pre-download wheel trust root;
- gate enumeration integrity;
- recovery snapshot binding;
- operational ledger validation;
- frozen RC working-tree verification;
- SQLite/OpenSSL exact pins;
- exact four-input startup boundary;
- `run_due_work`;
- no-semantic-script boundary;
- C1–C9;
- full Gates A/B/C/D.

## 5. Freeze targeted probes before implementation

Before changing the carried-forward #288 package, create and freeze targeted probes for exactly:

### C10 / IA288-01 — concurrency

At minimum test:
- two independent `ExchangeLedger` instances appending different legal requests at the same prefix;
- two independent request publishers publishing different requests concurrently;
- duplicate same-request publication concurrently;
- response publication racing another state mutation;
- consume racing another state mutation where meaningful;
- one true interprocess/subprocess case, not only threads.

Expected:
- operations serialize or one fails closed;
- no pair of successful calls may leave an invalid ledger;
- sequence and prev-hash remain monotonic;
- deterministic request identity remains valid;
- no duplicate semantic dispatch.

### C11 / IA288-02 — directory durability

Inject actual failure at the required directory durability primitive while regular file fsync remains successful.

Test:
- request artifact directory fsync failure;
- response artifact directory fsync failure;
- initial durable ledger creation directory fsync failure;
- directory open failure where the platform requires directory fsync;
- retry after a failed durability step.

Expected:
- publication/append operation does not return success;
- no successful semantic dispatch receipt is emitted;
- retry does not silently adopt unproven bytes as a durable prior dispatch;
- after durability is successfully re-established, legal retry converges exactly once.

Freeze:
- source;
- SHA-256;
- enumeration;
- expected outcomes;
before the first baseline execution.

## 6. Preserve baseline RED

Run the frozen targeted probes against exact failed #288.

Preserve raw RED.

Do not change expectations after observing candidate behavior.

If a probe is defective, preserve that revision and create/freeze a corrected revision before execution.

## 7. New corrective branch

Create a new branch from current live main.

Carry forward the exact #288 Operator Prep package/evidence as the starting point.

Do not continue #288 branch.

Apply only the two authorized corrections.

## 8. Concurrency correction requirements

The durable exchange mutation protocol must have an enforceable single-writer transaction boundary shared by independent objects/processes.

The protected critical section must cover every decision derived from the current durable prefix, including as applicable:

- read current records;
- validate chain/state;
- request sequence allocation;
- deterministic request-id allocation;
- duplicate/idempotent state decision;
- sequence/prev-hash allocation;
- artifact publication ordering;
- ledger append;
- required durability completion.

A process-local `threading.Lock` by itself is not sufficient.

A Linux file lock such as `fcntl.flock` on a dedicated lock file, or equivalent cross-process mechanism, is acceptable.

Avoid:
- a second state store;
- generic distributed transactions;
- lock semantics dependent on one Python object instance.

Nested callers must not deadlock. If the same lock is needed at multiple layers, design a clear transaction boundary rather than accidentally taking non-reentrant OS locks recursively.

## 9. Request sequence correctness under concurrency

Do not fix only `ExchangeLedger.append` while leaving request identity allocation outside the serialization boundary.

Two concurrent request publications must not both compute stale request sequence/identity from the same prefix and then emit inconsistent request payload versus ledger sequence.

The full request publication transaction must remain self-consistent.

Test request payload:
- `sequence`;
- `request_id`;
- ledger sequence;
- ledger request digest;
after concurrent publication.

## 10. Response/consume concurrency

Verify legal duplicate/idempotent behavior remains correct under shared locking.

No new lock may cause:
- duplicate `response_published`;
- duplicate `response_consumed`;
- deadlock in normal runner recovery;
- starvation in the bounded synthetic tests.

## 11. Directory durability correction requirements

For the qualified Linux runtime, required directory durability failure must raise/fail closed.

Do not merely return `fsync_directory=false` and ignore it.

The atomic publication layer must make success mean the required durability sequence completed.

At minimum:
- temp file write;
- file flush/fsync;
- replace;
- containing-directory fsync;
must either complete or raise.

## 12. Ledger creation durability

The first ledger creation is itself a new directory entry.

It must not return a successful durable ledger append if required directory fsync failed.

Choose a mechanically sound design, e.g. durable initialization or equivalent, but do not hide the failure.

## 13. Retry after durability failure

A critical case:

- artifact/ledger bytes may remain visible even though the operation returned failure because directory fsync failed.

A later retry must not automatically reinterpret those bytes as a previously proven durable semantic dispatch.

The corrective protocol must:
- re-establish the required durability condition;
- validate exact bytes/digests/state;
- converge without duplicate semantic dispatch;
- only then return success.

Freeze a dedicated regression for this.

## 14. Error propagation

Do not swallow:
- directory open `OSError`;
- directory fsync `OSError`;
- lock acquisition/ownership errors;
- required durability errors.

Translate them into existing mechanical exchange errors where appropriate, preserving fail-closed behavior.

Do not convert an actual durability failure into a warning.

## 15. Reviewer supplemental request-file mutation observation

The #290 report records direct consume after request-file mutation as a non-blocking hardening observation.

You may add a narrow regression that direct state-driving consume validates the durable request file before consumption if this can be done without widening scope.

This is optional for this corrective.

Do not turn it into a Core redesign.

## 16. Same frozen targeted probes must turn GREEN

After implementation, rerun the exact frozen C10/C11 probes.

Expected:
- concurrency GREEN;
- directory-durability GREEN.

Do not change expected outcomes.

## 17. Full regression

Rerun:
- Corrective-001 C1–C3;
- Corrective-002 C4–C9;
- full Gate A;
- full Gate B;
- full Gate C;
- full Gate D;
- due-work synthetic integration;
- packet audit;
- clean bootstrap/verify.

Use:
- CPython 3.12.14;
- Pydantic 2.13.5;
- pytest 8.4.2;
- SQLite 3.45.1;
- OpenSSL 3.0.13.

## 18. Concurrency integration proof

In addition to unit probes, preserve one end-to-end synthetic exchange run demonstrating concurrent publishers cannot corrupt the ledger.

Use disposable synthetic state only.

No C15 fixture.

## 19. Clean bootstrap

Build from a new absent scratch runtime root.

Do not use author/reviewer previous runtime as proof.

Verify:
- wheel trust root;
- exact runtime pins;
- frozen RC identities;
- canonical Core/tests manifests;
- import path.

## 20. Evidence regeneration

Regenerate from the final corrected tree:

- C10/C11 baseline RED;
- C10/C11 candidate GREEN;
- C1–C9 regression;
- full gate collect/raw/results;
- concurrency integration evidence;
- durability fault evidence;
- environment record;
- RC identity;
- harness manifest;
- launch packet;
- packet audit;
- FREEZE_MANIFEST;
- SHA256SUMS.

No covered code edit after final tests without rerun/refreeze.

## 21. Launch packet

Status remains:

`PREP_REVIEW_READY`

It must not become:

`READY_FOR_RESIDENT`

Pin the new corrected:
- harness;
- bootstrap/atomic behavior;
- gate evidence;
- C1–C11 evidence;
- exact contracts/startup set;
- candidate head/parent rule.

## 22. No real Resident

Do not:
- initialize real C15 release-state;
- reveal cursor 1;
- create real Resident World/session;
- run real Phase-A event;
- run cognition against real fixture.

Synthetic/disposable only.

## 23. New evidence-only PR

Create a new PR.

Do not reuse #288.

Mark:

`EVIDENCE-ONLY / DO NOT MERGE AS IMPLEMENTATION`

Pin:
- exact head/parent/tree;
- failed #288 exact;
- failed review #290 exact;
- C10/C11 baseline RED;
- C10/C11 candidate GREEN;
- C1–C9 preserved GREEN;
- full gates;
- clean bootstrap;
- packet/freeze hashes.

## 24. Success disposition

Only when all requirements pass:

`OPERATOR_PREP_CORRECTIVE_003_COMPLETE / REVIEW_READY`

then:

`READY_FOR_INDEPENDENT_ACCEPTANCE`

Do not self-accept.

## 25. Failure disposition

If either blocker cannot be closed inside Operator Prep infrastructure:

`BLOCKED`

Do not widen architecture.

## 26. Prohibitions

Do not:
- modify/merge #288;
- modify/merge #290;
- modify Core;
- run Resident;
- resume persistence;
- run Resident B/C;
- evaluator/C15 close;
- tag/public release.

Stop after publishing the new Corrective-003 evidence candidate.
