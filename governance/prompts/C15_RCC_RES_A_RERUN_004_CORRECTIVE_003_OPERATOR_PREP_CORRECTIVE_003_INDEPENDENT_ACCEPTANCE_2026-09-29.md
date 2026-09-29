# C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003-INDEPENDENT-ACCEPTANCE

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Status:

`READY`

Role:

**Independent Resident Launch Infrastructure Acceptance Reviewer**

You are not:
- Corrective-003 author;
- prior Operator Prep corrective author;
- Resident A/B/C;
- PM;
- Core implementation engineer;
- semantic evaluator.

Your only task:

> Independently attempt to make exact PR #292 fail. Verify that the Corrective-003 Operator Prep truly closes IA288-01 and IA288-02 without regression of any C1-C9 or historical #283/#284 guarantees, remains reproducible/frozen/semantically clean, and is safe to hand back to PM. Do not run a real Resident.

## 1. Fresh start

Fresh-fetch live `main`.

Read:
- current task board/checkpoint;
- `governance/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_OPERATOR_PREP_CORRECTIVE_003_PM_REVIEW_READY_2026-09-29.md`;
- PM adjudications for #283/#284/#286/#288/#290;
- clean-room contract;
- canonical Resident A run contract;
- this exact IA prompt.

Confirm:

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003-INDEPENDENT-ACCEPTANCE = READY`

Reviewer may inspect governance/history needed for control-plane acceptance.

Do not open:
- sealed C15 fixture payloads;
- evaluator expected semantics;
- real release-state;
- unreleased future events.

Do not run a real Resident.

## 2. Exact candidate

PR #292.

Required final freeze H2:

`42a63ed4416585fc0a02045e0bd5190f32a01a2b`

Required H2 tree:

`80440bdd70aa658053bc5bf33a902c46cd7138e0`

Required sole parent / corrected H1:

`77dac70e0cf054c3f0fb7d94a66dba221fe7d5de`

Required H1 tree:

`52aa366bc6548e86e805585baddbc0470cb69660`

Required H1 parent / RED freeze:

`083dd9506f01ade04d4cbe805f58bf80d40607b0`

Required pre-baseline probe freeze:

`4b2ca9fd48da2f1f44789c664de66bd471a39ee9`

Required exact #288 carry:

`41de3f6698146661e73f6e43c00143fb63516ef1`

If PR #292 head is not exact H2, stop:

`REVALIDATION_REQUIRED`

Do not hash-swap acceptance.

## 3. Frozen RC

Must remain:

- software `f20f2edfa7af00d0286493fd15196ca9503bc315`
- repository tree `1ac3a675b884167d3a29aa432e7ef3eaff94d404`
- Core tree `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`

No live-main Core substitution.

## 4. Scope and lineage

Independently verify:
- H2 head/tree/parent;
- H1 head/tree/parent;
- probe-freeze/RED chronology;
- H1→H2 contains only evidence/packet/raw freeze artifacts;
- no harness/bootstrap/probe source changed after final code freeze;
- no Core/product tests/fixture/evaluator/release-source/real state artifacts.

Do not trust PR description.

## 5. Freeze reviewer probes before execution

Before first adversarial execution against #292:
- author your own reviewer probes;
- freeze source + SHA-256;
- freeze enumeration;
- freeze expected outcomes;
- durably commit/persist the freeze.

If reviewer probe is defective:
- preserve old revision/result;
- freeze a corrected revision before execution.

Never tune expectations after observing candidate behavior.

## 6. Independent runtime reproduction

Do not use the author's runtime:

`/home/user/.cache/c003/final-runtime-001`

as acceptance evidence.

Build from a fresh reviewer scratch root.

Independently establish:
- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2
- SQLite 3.45.1
- OpenSSL 3.0.13

Record OS/kernel/arch/libc, executable, `aios_core.__file__`, installed distributions, wheel hashes and frozen RC identities.

## 7. Re-attack IA288-01 — cross-process linearization

Do not merely inspect for `flock`.

Independently prove the protocol under adversarial schedules.

At minimum test:

### 7.1 Two independent ledger instances
Force both writers to attempt legal append from the same prefix.

Expected:
- serialization or fail-closed;
- both-success is allowed only if final sequence/prev-hash chain is valid and distinct;
- no duplicate sequence.

### 7.2 True subprocess/interprocess writers
Use separate OS processes.

Verify:
- lock authority is shared cross-process;
- final ledger valid;
- no deadlock/starvation in bounded run.

### 7.3 Concurrent distinct request publication
Two publishers publish different snapshots concurrently.

Verify each:
- request ordinal;
- deterministic request_id;
- payload sequence;
- ledger sequence;
- request digest;
remain self-consistent.

### 7.4 Concurrent duplicate request publication
Same intended request racing from independent publishers.

Verify no duplicate semantic dispatch and deterministic idempotent/fail-closed behavior.

### 7.5 Response/consume races
Race:
- response publish vs response publish;
- response publish vs consume where meaningful;
- consume vs consume.

Verify exactly-once durable chronology and no duplicate ledger events.

### 7.6 Runner race
Two external-session handlers receive the same snapshot concurrently.

Verify:
- one semantic dispatch;
- no deadlock;
- legal recovery/handoff behavior.

### 7.7 Lock failure attacks
Inject:
- lock-file open error;
- `flock` acquisition error;
- lock path symlink/replacement where applicable;
- lock release/ownership anomaly if testable without corrupting the host.

Required failures must fail closed.

## 8. Lock design review

Manually inspect the H1 implementation.

Verify:
- process-local RLock is not the only authority;
- outermost transaction owns a dedicated persistent lock inode;
- independent objects/processes converge on the same lock path;
- nested calls do not self-deadlock;
- lock is not released before prefix-derived artifact+ledger durability completes;
- lock is released before waiting for an external semantic response;
- lock file is not a second truth store.

Check path/symlink/inode assumptions adversarially.

## 9. Re-attack IA288-02 — directory durability

Independently inject actual directory-durability failures while regular file fsync succeeds.

At minimum:

- request artifact directory open failure;
- request directory fsync failure;
- response directory open failure;
- response directory fsync failure;
- initial ledger creation directory open/fsync failure;
- ledger append durability failure where applicable.

Expected:
- no successful publication/dispatch receipt;
- no successful response publication receipt;
- no successful durable ledger append claim.

## 10. Visible-but-unproven retry

Critical attack:

1. cause rename/write to make bytes visible;
2. force required directory durability to fail;
3. operation must return failure;
4. retry with durability restored.

Verify retry:
- does not silently treat visible bytes as already-proven durable dispatch;
- revalidates exact bytes/digests;
- re-establishes durability;
- appends at most one durable event;
- returns success only after durability is re-proven.

Test both request and response sides.

## 11. Initial ledger creation

Verify the first ledger entry cannot become a semantic dispatch record before the ledger path itself has completed required durability.

Attack new empty exchange roots repeatedly and across processes.

## 12. Crash-boundary attacks

Use disposable synthetic state.

Try termination or exception around:
- after artifact file fsync before replace;
- after replace before directory fsync;
- after artifact durability before ledger append;
- after ledger file fsync before required directory durability on first creation;
- after ledger append before receipt return.

Verify restart/retry converges without duplicate dispatch or corrupt chain.

No physical power-loss claim is required, but software-visible crash boundaries must be tested.

## 13. Re-test all historical #283 guarantees

Independently re-attack:
- published response replay over tampered/missing file;
- changed replay bytes;
- intact idempotent replay;
- pre-download wheel trust root;
- wrong/missing/extra wheel;
- gate enumeration/result/execution consistency.

## 14. Re-test all historical #284 guarantees

Independently re-attack:
- recovery snapshot/body binding;
- ambiguity with multiple recovery candidates;
- operational ledger chain/sequence/event uniqueness;
- working-tree frozen-RC verification;
- wrong Core/tests bytes;
- foreign import path;
- exact SQLite/OpenSSL pins;
- exact four-input startup boundary;
- due-work external model exchange.

## 15. Direct request-file mutation observation

Review #290 recorded a non-blocking direct-consume request-file mutation concern.

Re-test it.

Do not automatically promote it to a blocker.

If you can demonstrate:
- approved runner semantic cross-binding;
- acceptance of wrong request bytes into a semantic result;
- or violation of a binding durability/integrity guarantee;

then document as a new blocker with exact reproduction.

Otherwise classify as bounded hardening.

## 16. Full C1-C11 regression

Rerun:
- C1-C3;
- C4-C9;
- C10-C11.

Author expectations:
- C4-C9 = 103 PASS;
- C10-C11 = 18 PASS.

Do not treat author suites as independent proof; use them as regression evidence alongside reviewer attacks.

## 17. Full Gates A/B/C/D

Rerun complete gates under the reviewer-qualified runtime.

Expected author counts:
- A 24
- B 7
- C 2
- D 5.

Verify collect IDs, result IDs and execution totals reconcile.

Gate C must remain non-vacuous:
- real frozen Core capability execution;
- nonempty round-1 CapabilityResult;
- durable external exchange.

Gate D must be corroborated by manual package inspection, not scanner output alone.

## 18. Due-work integration

Independently create disposable synthetic due work that genuinely invokes the model boundary.

Verify:
frozen Core
→ due work
→ ExternalSessionModelHandler
→ durable request
→ external test-only response
→ durable consume
→ legal completion.

No C15 fixture.

## 19. Freeze integrity

Recompute:
- packet SHA;
- package and Corrective-003 SHA256SUMS;
- package and Corrective-003 FREEZE_MANIFEST;
- harness manifest;
- Core/tests manifests;
- wheel trust root;
- C10/C11 baseline RED hash;
- C10/C11 GREEN hash;
- C1-C9 result hashes;
- gate result hashes.

Packet expected SHA:

`3c2d04c2de8557c3cb7329df4350c40b2ccc07520a7d3d51db206174b33266cc`

Packet status must remain:

`PREP_REVIEW_READY`

not:

`READY_FOR_RESIDENT`.

## 20. Checksum/self-reference method

Inspect the two-tier evidence design.

Ensure:
- checksum files do not circularly authenticate themselves;
- final H2 Git identity is external to file-content self-hashes;
- H2 only freezes evidence over unchanged H1 code;
- no covered code changed after final tests.

## 21. No real Resident execution

Search exact PR #292 evidence for:
- real release-state;
- real World/session DB;
- real Phase-A event;
- cursor reveal;
- real Resident cognition;
- fixture/evaluator payload access.

Synthetic evidence is allowed.

Any real Resident run is a blocker.

## 22. Reviewer-authored extra attacks

Do not constrain yourself to C1-C11.

Especially attack:
- lock-path replacement / symlink / inode race;
- stale lock file across process restart;
- abandoned process while holding lock;
- lock ordering under nested request/response/consume calls;
- transaction TOCTOU between durability proof and ledger append;
- retry after partial failure across a different process;
- simultaneous due-work and user-turn handler use of the same exchange root;
- packet/hash coverage omissions.

Use disposable synthetic state only.

## 23. Durable publication required

A chat verdict is not acceptance.

Create:
- review-only branch;
- formal report;
- reviewer probes;
- frozen probe hashes/enumeration;
- raw outputs;
- environment record;
- exact review commit;
- review-only / evidence-only / DO NOT MERGE PR.

Then comment on PR #292 with:
- review PR number;
- exact review SHA;
- verdict;
- blocker count.

Do not modify #292.

## 24. Allowed verdicts

### PASS

`ACCEPTANCE_PASS / blocker=0`

Then:

`READY_FOR_PM_INTEGRATION`

This does not authorize Resident execution.

### FAIL

`ACCEPTANCE_FAIL / blocker=N`

Every blocker must include:
- ID;
- exact path;
- repro;
- observed;
- expected;
- binding reason;
- minimal corrective scope.

Do not repair the candidate in the review window.

### Candidate drift

`REVALIDATION_REQUIRED`

### Publication impossible after completed review

`EVIDENCE_PUBLICATION_BLOCKED`

Preserve exact local review identity/evidence.

## 25. Prohibitions

Do not:
- merge or modify #292;
- run a real Resident;
- initialize real release-state;
- reveal cursor 1;
- resume persistence;
- run Resident B/C;
- run evaluator/C15 close;
- modify/merge #263/#265;
- tag/public release.

Stop immediately after durable IA publication.
