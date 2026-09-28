# C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-002

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

> Preserve the successful Corrective-001 repairs and close the remaining valid findings from historical review PR #284. Produce a new frozen Operator Prep candidate. Do not run a real Resident.

## 1. Fresh start

Fresh-fetch live `main`.

Read:
- current task board/checkpoint;
- `governance/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_OPERATOR_PREP_CORRECTIVE_001_REVIEW_BLOCKED_ADJUDICATION_2026-09-28.md`;
- Corrective-001 prompt;
- review PR #284 formal report;
- clean-room contract;
- canonical Resident A run contract.

Confirm:

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-002 = READY`

Do not run a real Resident.

## 2. Exact historical identities

Historical failed Operator Prep:
- #281 @ `10901d467679b70437ae112747eab81f889fd5cb`

Historical IA reviews:
- #283 @ `e3394da5d607e34c0286c16a11837ac7ea173a56`
- #284 @ `dce47c0d8f3ac7e34efb47e22c63c6f9acbea1a6`

Review-blocked Corrective-001:
- #286 final freeze H2 `c32e544b747cb1f1d9b7418e2163a65ac55ee39c`
- corrected candidate H1b `99af8e268a1f9e8944b163d8087005e0e3698620`

Do not modify or continue any of those branches/PRs.

Create a new branch from current live main and carry forward exact #286 package/evidence as the starting point.

## 3. Preserve Corrective-001 closures

The following must stay GREEN:

- response idempotent replay detects tampered/missing published bytes at publish time;
- pre-download Python wheel trust root;
- gate enumeration/result/execution consistency;
- clean CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 environment;
- A/B/C/D existing gates;
- semantic-script isolation;
- no real Resident run.

Do not regress them.

## 4. Freeze new targeted probes before implementation

Before modifying the carried-forward #286 package, create/freeze targeted probes for the unresolved findings.

At minimum:

### C4 — recovery snapshot binding
- one outstanding request for snapshot S1, call handler with different snapshot S2 → fail closed;
- one durable-unconsumed response for S1, call handler with S2 → fail closed;
- >1 outstanding or >1 durable-unconsumed candidate → fail closed;
- exactly one candidate with exact matching request body/digest → legal resume.

### C5 — operational ledger integrity
- interior record mutation → runner/recovery/consume fail closed;
- interior record deletion → fail closed;
- duplicate request_published → fail closed;
- duplicate response_published/consumed → fail closed;
- broken chain before append → append refuses;
- valid chain continues normally.

### C6 — frozen RC verify
- default/approved verify command resolves correct repo root;
- missing Git metadata/frozen objects → non-zero BLOCKED;
- working-tree Core byte mutation → non-zero BLOCKED;
- working-tree tests mutation if tests are part of frozen launch identity → non-zero BLOCKED;
- correct frozen working tree → PASS;
- imported `aios_core.__file__` is inside the verified tree;
- canonical content manifest algorithm is deterministic and matches the packet/tooling.

### C7 — runtime library pin
- SQLite != 3.45.1 → verify BLOCKED;
- SQLite 3.45.1 → PASS;
- preserve prelocked wheel trust root;
- if OpenSSL 3.0.13 is declared in environment identity, mismatched runtime OpenSSL → BLOCKED.

### C8 — startup input contract
- launch packet allowed startup set equals exactly:
  1. Corrective-003 clean-room contract;
  2. canonical Resident A run contract;
  3. exact launch packet;
  4. approved mechanical environment/harness status.
- packet audit fails if any is omitted or extra control-plane/history path is added.

### C9 — due-work entrypoint
- run package exposes approved mechanical due-work entrypoint;
- synthetic due work invokes frozen Core through `ExternalSessionModelHandler`;
- at least one synthetic due Wake/Review path reaches external request publication and consumes external test response;
- no semantic callback in real package;
- no real fixture.

Freeze probe sources, SHA-256, enumeration and expected outcomes before running them.

Run them against exact #286 H2/H1b as appropriate and preserve expected RED for unresolved findings.

## 5. Correct recovery binding

In `ExternalSessionModelHandler.__call__`:

- serialize current snapshot once;
- compute canonical current request body digest;
- inspect recovery state;
- if more than one recoverable/outstanding candidate exists: fail closed;
- for exactly one candidate, load its durable request body/digest;
- require exact digest equality with current serialized snapshot;
- only then resume/consume that request.

Never bind a response created for S1 to S2.

Do not choose `[0]` from an ambiguous set.

## 6. Correct operational ledger integrity

Make chain/chronology validation operational, not reporting-only.

Before state-driving reads and writes:

- verify chain;
- verify sequence;
- verify per-request uniqueness;
- verify legal event order;
- verify request/response digest continuity.

Apply fail-closed enforcement to:
- append;
- recovery_state;
- consume_response;
- request/response lookup used by the runner.

Avoid recursive verification design bugs.

Document whole-record tail truncation limitation if no external head anchor is added.

## 7. Correct frozen-RC verify

Fix the approved bootstrap verification path.

Requirements:

- correct repository-root resolution, or require explicit repo root and validate it;
- missing Git metadata is BLOCKED, not WARNING;
- frozen software/Core/tests Git objects must resolve and match;
- working-tree bytes used for import must match frozen identity;
- canonical sorted Core content manifest implementation shared by tooling;
- packet pins that canonical manifest;
- `aios_core.__file__` must resolve inside the verified source root;
- mutated working tree must fail.

Do not modify frozen Core itself.

## 8. Correct SQLite/runtime pin verification

Preserve the Corrective-001 wheel lock.

Additionally require:

- `sqlite3.sqlite_version == 3.45.1`;
- runtime OpenSSL exact expected version when declared as a qualified-environment pin;
- wrong system-library fallback cannot pass verify.

Clean scratch build + verify must still pass.

## 9. Correct startup contract

Use the PM ruling in the adjudication.

Update launch packet generation/audit so allowed startup inputs are exactly the approved four-item set:

1. clean-room contract;
2. canonical Resident A run contract;
3. launch packet itself;
4. mechanical environment/harness status.

Do not add:
- board;
- checkpoint;
- adjudications;
- prior PR/review;
- historical run artifacts.

Use the current main clean-room contract hash after the PM clarification.

## 10. Add due-work entrypoint

Add a mechanical run-package entrypoint using frozen Core's normal due-work processing, such as:

`run_due_work(...)`

Requirements:
- same verified World/index/subject configuration pattern;
- same `ExternalSessionModelHandler`;
- explicit timezone-aware current time;
- drives frozen `HeadlessCore.process_due_work` or the exact supported equivalent;
- captures mechanical status/result/handoff/integrity evidence;
- no semantic rules/callback;
- listed in packet.

Add synthetic integration coverage where due work genuinely invokes the external model exchange.

No C15 fixture content.

## 11. Full regression

After targeted C4–C9 GREEN, rerun:

- Corrective-001 targeted C1/C2/C3 probes;
- full Gate A;
- full Gate B;
- full Gate C;
- full Gate D;
- new due-work integration gate/probe;
- packet audit;
- clean bootstrap verification.

All binding tests under CPython 3.12.14 / Pydantic 2.13.5.

## 12. Freeze evidence

Regenerate from final corrected tree:

- targeted baseline RED against #286;
- targeted candidate GREEN;
- environment record;
- canonical RC identity/content-manifest evidence;
- gate collect-only/raw/results;
- harness manifest;
- packet audit;
- launch packet;
- FREEZE_MANIFEST;
- SHA256SUMS.

No covered code edit after the final frozen gate run without rerun/refreeze.

## 13. Launch packet

Status remains:

`PREP_REVIEW_READY`

Pin:
- corrected bootstrap;
- wheel trust root;
- canonical Core manifest;
- corrected harness;
- user-turn entrypoint;
- due-work entrypoint;
- all gate/probe hashes;
- paired clean-room + canonical run-contract hashes;
- exact parent/head rule.

Do not set `READY_FOR_RESIDENT`.

## 14. Scope

Allowed:
- Operator Prep mechanical harness/bootstrap/tests/tools/evidence/packet;
- only the PM-authorized clean-room contract clarification already present on live main.

Forbidden:
- Core implementation;
- product tests;
- fixture/evaluator/release source;
- real Resident state;
- real C15 release-state/cursor reveal.

## 15. Deliverable

Create a new evidence-only PR.

Pin:
- exact head/parent/tree;
- #286 review-blocked exact;
- #284 review exact;
- C4–C9 baseline RED;
- C4–C9 candidate GREEN;
- preserved C1/C2/C3 GREEN;
- full gates;
- clean bootstrap/RC verify;
- packet hash/status.

Disposition:

`OPERATOR_PREP_CORRECTIVE_002_COMPLETE / REVIEW_READY`

then:

`READY_FOR_INDEPENDENT_ACCEPTANCE`

Do not self-accept or merge.

## 16. Stop

If any finding cannot be closed without Core product changes:

`BLOCKED`

Do not widen architecture.
