# C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-001

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
- Core implementation engineer;
- semantic evaluator.

Your only task:

> Repair exactly the three Operator Prep Independent-Acceptance blockers IA-OP-001, IA-OP-002, IA-OP-003, produce a new frozen Operator Prep candidate, and stop at REVIEW_READY. Do not run a real Resident.

## 1. Fresh start

Fresh-fetch live `main`.

Read:
- current task board/checkpoint;
- `governance/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_OPERATOR_PREP_IA_FAILURE_ADJUDICATION_2026-09-28.md`;
- original Operator Prep prompt;
- Operator Prep IA report at PR #283;
- clean-room Resident contract;
- Resident A safe-run contract.

Confirm:

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-001 = READY`

Do not run the real Resident.

## 2. Historical exacts

Failed Operator Prep:

- PR #281
- exact `10901d467679b70437ae112747eab81f889fd5cb`

Failed IA:

- PR #283
- exact `e3394da5d607e34c0286c16a11837ac7ea173a56`

Both are immutable.

Do not amend, force-push, hash-swap, or modify them.

## 3. Frozen RC remains unchanged

- software `f20f2edfa7af00d0286493fd15196ca9503bc315`
- Core tree `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`

No `src/aios_core/**` or `tests/**` change is authorized.

## 4. Freeze corrective probes before implementation

Before changing the carried-forward Operator Prep package, create a new corrective regression suite covering exactly:

### C1 / IA-OP-001

- publish a valid response;
- tamper the durable response file;
- replay the original exact response;
- expected: publication itself fails closed;
- also test missing durable response file with existing ledger record;
- exact unmodified replay with intact file remains idempotent.

### C2 / IA-OP-002

Mechanically verify bootstrap package trust root:

- complete Python package dependency closure is present in a source-controlled lock;
- each artifact has exact version + exact wheel filename + pre-frozen SHA-256;
- bootstrap does not derive trust-root hashes from newly downloaded bytes;
- an artifact with wrong bytes/hash is rejected before installation;
- unexpected/additional wheel is rejected or ignored with an explicit closed set;
- clean scratch build succeeds using only the locked verified artifacts.

### C3 / IA-OP-003

Verify gate enumeration:

- Gate A/B/C/D collect-only node IDs are parsed;
- result JSON contains the exact node IDs;
- `test_count == len(test_ids)`;
- count matches collected total;
- executed outcome total is consistent;
- empty/malformed collection causes gate-runner failure.

Freeze:
- corrective probe source;
- SHA-256;
- collect-only/enumeration;
- expected outcomes.

Then run these frozen probes against failed exact #281.

Preserve RED evidence.

Do not change expected outcomes after seeing the RED.

## 5. Build new branch from current live main

Create a new Operator Prep corrective branch from current live `main`.

Carry forward the exact Operator Prep package from failed exact #281.

Do not continue the #281 branch.

Do not modify #281.

Apply only the authorized IA-OP-001/002/003 corrections.

## 6. Correct IA-OP-001

In `ResponsePublisher.publish_bytes()` existing-record path:

Before returning `idempotent_replay=True`:

- require response file exists;
- read exact bytes;
- compute SHA-256;
- require on-disk digest == durable ledger response digest;
- require replay input digest == durable ledger response digest;
- require request binding still matches where applicable.

If file is:
- missing;
- tampered;
- mismatched;
- ambiguous;

raise fail-closed publication error.

Do not rewrite or heal the file.

Intact exact replay must remain idempotent.

Add candidate regression tests.

## 7. Correct IA-OP-002

Create a pre-frozen Python wheel trust-root file inside the Operator Prep package.

The full dependency closure for the qualified runtime must be explicit.

At minimum include all distributions required by:

- Pydantic 2.13.5;
- pytest 8.4.2;

including transitive dependencies selected for the target CPython 3.12 / x86_64 Linux environment.

For each locked wheel record:

- normalized project name;
- exact version;
- exact filename;
- SHA-256.

The lock itself is part of the candidate/freeze.

Bootstrap rules:

- never let live index resolution choose an unrecorded artifact;
- never generate the expected artifact hashes from the same bytes just downloaded;
- acquire only locked artifact filenames/versions;
- validate SHA-256 against the pre-existing lock before placing/using the artifact;
- reject hash mismatch;
- reject missing locked dependency;
- reject unexpected dependency closure;
- install from verified local wheelhouse with no live resolution.

A generated wheelhouse `SHA256SUMS` is evidence only, not trust authority.

Clean-scratch bootstrap must be re-run and preserved.

## 8. Correct IA-OP-003

Fix `gate_runner.py` collection parsing.

Do not rely on test node IDs ending in `)`.

Record the exact node IDs emitted by the frozen collect-only command.

Require:

- collection return code = 0;
- at least one test node for each nonempty gate;
- `test_count == len(test_ids)`;
- parsed count matches pytest's collected count;
- executed pass/fail/error/skipped totals reconcile with the frozen enumeration.

If not, Gate status must be FAIL/BLOCKED.

Add a regression test for representative pytest collect-only output.

## 9. Qualified environment

All binding tests and final gates use:

- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2
- intended SQLite 3.45.1 environment

Record actual environment.

The final clean bootstrap must be from an empty scratch runtime root, not merely an already-built author runtime.

## 10. Full post-fix gates

After targeted corrective probes are GREEN, rerun complete:

- Gate A;
- Gate B;
- Gate C;
- Gate D.

Gate A must include the response-tamper idempotent-replay regression.

Gate B/C/D semantics remain unchanged.

Do not weaken any pre-existing test to get GREEN.

## 11. Evidence regeneration

Regenerate from the final corrected tree:

- gate collect-only files;
- gate result JSON;
- raw outputs;
- environment record;
- wheel-lock/trust-root evidence;
- harness manifest;
- packet audit;
- `FREEZE_MANIFEST.json`;
- `SHA256SUMS`.

Verify all hashes after final gate run.

No covered harness/operator-tool edit may occur after the final frozen gate run without rerunning/re-freezing.

## 12. Launch packet

Generate a new:

`RESIDENT_SAFE_LAUNCH_PACKET.json`

Status must remain:

`PREP_REVIEW_READY`

It must pin the new corrected:
- bootstrap;
- wheel trust root;
- harness manifest;
- gates;
- contracts;
- exact Operator Prep parent/head rule.

It must remain semantically clean.

Do not change to `READY_FOR_RESIDENT`.

## 13. Scope

Allowed:
- Operator Prep bootstrap;
- Operator Prep mechanical harness;
- Operator Prep tests/operator tools;
- Operator Prep evidence;
- new launch packet.

Forbidden:
- Core implementation;
- product tests;
- fixture/evaluator/release source;
- real Resident state;
- real release-state;
- real cursor reveal.

## 14. No real Resident

Do not:
- initialize C15 release-state;
- reveal cursor 1;
- create a real Resident World/session;
- run a real Phase-A user turn.

Synthetic disposable tests only.

## 15. Deliverable

Create a new evidence-only PR.

Do not reuse #281.

Pin:
- exact head;
- parent;
- tree;
- frozen RC;
- targeted baseline RED hashes/results;
- targeted candidate GREEN hashes/results;
- wheel trust-root hash;
- clean bootstrap evidence;
- full A/B/C/D result hashes and correct test enumeration;
- launch packet hash/status.

Disposition:

`OPERATOR_PREP_CORRECTIVE_COMPLETE / REVIEW_READY`

then:

`READY_FOR_INDEPENDENT_ACCEPTANCE`

Do not self-accept.

## 16. Stop conditions

If any of the three blockers cannot be closed without Core/Resident changes:

`BLOCKED`

Do not widen architecture.

## 17. Prohibitions

Do not:
- modify/merge #281;
- modify/merge #283;
- run a Resident;
- release Corrective-003 Resident;
- resume persistence;
- run Resident B/C;
- evaluator/C15 close;
- change #263/#265;
- tag/public release.

Stop after publishing the new Operator Prep corrective evidence.
