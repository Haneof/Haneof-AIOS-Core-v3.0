# C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Status:

`READY`

Role:

**Independent Resident Launch Infrastructure Acceptance Reviewer**

You are not:
- Corrective-002 author;
- Corrective-001 author;
- Resident A/B/C;
- PM;
- Core implementation engineer;
- semantic evaluator.

Your only task:

> Independently attempt to make exact PR #288 fail. Verify that the Corrective-002 Operator Prep truly closes all historical #283/#284 blockers without regression, remains mechanically Resident-safe, reproducible, frozen, and semantically clean. Do not run a real Resident.

## 1. Fresh-fetch and task identity

Fresh-fetch live `main`.

Read:
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`;
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`;
- `governance/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_OPERATOR_PREP_CORRECTIVE_002_PM_REVIEW_READY_2026-09-29.md`;
- historical PM adjudications for #283/#284/#286;
- clean-room contract;
- canonical Resident A run contract;
- this exact IA prompt.

Confirm:

`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE = READY`

The reviewer is control-plane and may read governance/history needed to perform acceptance.

However, do not open:
- sealed C15 fixture payloads;
- evaluator expected semantics;
- real release-state;
- unreleased future events.

Do not run a real Resident.

## 2. Exact candidate to accept

PR #288.

Required exact final freeze H2:

`771b200c33dbd6055b1d209935f8e1552f13090f`

Required H2 tree:

`071b51c5fb37dc59fc8941dee2182637b9f87daa`

Required sole parent / corrected candidate H1:

`63c972ad7a19671cbdf809177f7a552aa2c2ecc6`

Required H1 tree:

`8cd4a2d8b4cdf1f85699c5d78166f774741b420b`

Required H1 parent / RED freeze:

`8e34fba00edf4fdb5b80f04d7a648f6b5bb8c40e`

Task-start main recorded by the candidate:

`b7c9e85014806637f7a01c8fd6695bc9f57672ba`

If PR #288 current head is not exact H2:

`771b200c33dbd6055b1d209935f8e1552f13090f`

stop:

`REVALIDATION_REQUIRED`

Do not transfer acceptance evidence to a different SHA.

## 3. Frozen RC

The Operator Prep must remain bound to:

- software `f20f2edfa7af00d0286493fd15196ca9503bc315`
- repository tree `1ac3a675b884167d3a29aa432e7ef3eaff94d404`
- Core tree `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`

No live-main Core substitution is allowed.

## 4. Scope and lineage

Independently verify:

- #288 H2 head/tree/parent;
- H1 head/tree/parent;
- H2 is evidence/packet-only relative to H1;
- H1 contains the actual corrective implementation;
- the baseline RED commits precede H1;
- no amend/force-push/hash swap is being relied on.

Freshly enumerate all PR #288 changed paths.

Expected:
- Operator Prep package;
- Corrective-001 historical evidence carried forward;
- Corrective-002 probes/evidence.

Must remain zero:
- `src/aios_core/**`;
- product `tests/**`;
- fixture source;
- evaluator source;
- release source;
- real Resident run artifacts;
- real World/release-state DB.

Do not trust the PR description for scope.

## 5. Historical acceptance evidence is binding attack surface

Historical review #283 exact:

`e3394da5d607e34c0286c16a11837ac7ea173a56`

Historical review #284 exact:

`dce47c0d8f3ac7e34efb47e22c63c6f9acbea1a6`

Review-blocked Corrective-001:

- #286 H2 `c32e544b747cb1f1d9b7418e2163a65ac55ee39c`
- #286 H1b `99af8e268a1f9e8944b163d8087005e0e3698620`

Independently re-attack every historical blocker.

Do not infer closure because the author says C1–C9 are GREEN.

## 6. Freeze reviewer probes before candidate execution

Before the first adversarial execution against #288:

- author your own reviewer probe suite;
- freeze source files;
- record SHA-256;
- freeze collect-only/enumeration;
- freeze expected outcomes.

Commit/persist this freeze before using candidate behavior to tune expectations.

If a reviewer probe is defective:
- preserve the defective revision and result;
- create a new revision;
- freeze the new revision before executing it.

Never silently rewrite history.

## 7. Independent environment reproduction

Do not use the author's final runtime:

`/home/user/.cache/c002/final-runtime-003`

as acceptance evidence.

Build from a fresh reviewer scratch root.

Independently establish:

- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2
- SQLite 3.45.1
- OpenSSL 3.0.13

Record:
- OS;
- kernel;
- architecture;
- glibc/libc;
- Python executable;
- `aios_core.__file__`;
- exact installed distribution set;
- wheel hashes;
- frozen RC identities.

If external network/build limitations prevent reproduction, distinguish environment limitation from candidate defect.

## 8. Re-test historical #283 blocker: published-response replay integrity

Independently attack:

1. publish valid request/response;
2. tamper published response file;
3. replay exact original response;
4. expect publication operation itself to fail closed.

Also:
- missing published response file with durable ledger record → fail closed;
- changed replay bytes → fail closed;
- intact exact replay → legal idempotent success;
- tampered consume remains fail closed.

Verify the existing-record branch checks current on-disk bytes before success.

## 9. Re-test historical #283 blocker: wheel trust root

Inspect and attack the pre-download Python wheel trust root.

Verify:
- complete closed dependency set;
- exact project/version;
- exact filename/tags;
- exact pre-existing SHA-256;
- no expected hash generated from just-downloaded bytes;
- wrong artifact bytes → fail;
- missing locked wheel → fail;
- unexpected wheel → fail/closed set;
- installation is offline/no-index/no resolver;
- clean build uses only verified locked artifacts.

The packet pins wheel-lock SHA:

`6fa2587c98662588e4758ac9b579fee8d800ce4fc2d36e692dbaaabd6f4c8afe`

Do not accept version pinning alone.

## 10. Re-test historical #283 blocker: gate enumeration

Independently rerun A/B/C/D collect-only and execution.

Author expectation:
- A 24
- B 7
- C 2
- D 5

Verify:
- collect command succeeds;
- node IDs are exact/nonempty;
- result JSON IDs match;
- `test_count == len(test_ids)`;
- execution totals reconcile;
- malformed/empty collection fails closed.

Do not assume those counts are correct merely because they are in the packet.

## 11. C4 — recovery snapshot binding and ambiguity

Independently reproduce the old #284 attacks.

Required fail-closed cases:
- outstanding request for snapshot S1 + current handler called with different S2;
- durable-unconsumed response for S1 + current S2;
- multiple outstanding candidates;
- multiple durable-unconsumed candidates;
- conflicting outstanding/durable identities.

Required legal case:
- exactly one recoverable candidate whose exact durable request body matches the current canonical serialized RuntimeSnapshot.

Check both:
- digest equality;
- byte/canonical-body equality.

Ensure a semantic response for S1 can never be applied to S2.

Ensure no arbitrary `[0]` selection remains.

## 12. C5 — operational ledger integrity

Do not accept a reporting-only `verify_chain()`.

Attack operational paths:

- interior record mutation;
- interior deletion;
- duplicate `request_published`;
- duplicate `response_published`;
- duplicate `response_consumed`;
- illegal event ordering;
- broken sequence;
- broken prev-hash;
- record digest mismatch;
- request digest discontinuity;
- response digest discontinuity.

Verify fail-closed behavior before:
- append;
- recovery state;
- consume response;
- runner recovery/state-driving lookup.

Verify legal chain remains operational.

Explicitly document the result of testing complete-valid-tail deletion.

The candidate currently discloses:
> without an external ledger-head anchor, deletion of a complete valid tail record is indistinguishable from a valid prefix.

Do not claim this case is detected unless you independently prove it.

If this limitation violates a binding requirement, make it a blocker.
If it is acceptable, explain the exact boundary in the report.

## 13. C6 — frozen-RC verification

Attack the approved verification command exactly as the packet specifies.

Verify:
- default repository-root resolution points at the actual repo;
- explicit repo-root path works;
- missing Git metadata → BLOCKED;
- missing frozen object → BLOCKED;
- wrong Core tree → BLOCKED;
- wrong tests tree → BLOCKED;
- one-byte working-tree Core mutation → BLOCKED;
- one-byte working-tree tests mutation → BLOCKED;
- foreign/stale `aios_core.__file__` → BLOCKED;
- correct frozen working tree → PASS.

Independently recompute canonical content manifests.

Packet expects Core manifest:

`220718d6b5a2650b5e4263bbe8b7e661444cb33b486a7ecd7b5ad3d7d3399caa`

Verify the algorithm is deterministic and shared, rather than bootstrap/tool-specific incompatible formulas.

## 14. C7 — exact runtime pins

Independently prove:

- SQLite 3.45.1 is required, not merely observed;
- wrong SQLite runtime fails verify;
- OpenSSL 3.0.13 is required if it remains a qualified-runtime pin;
- wrong OpenSSL runtime fails;
- correct exact values pass.

Confirm system-library fallback cannot silently qualify.

## 15. C8 — clean-room startup boundary

The PM-approved exact startup set is:

1. `RESIDENT_A_CORRECTIVE_003_CLEAN_ROOM_CONTRACT.md`;
2. canonical `RESIDENT_A_RUN_CONTRACT.md`;
3. exact accepted `RESIDENT_SAFE_LAUNCH_PACKET.json`;
4. approved mechanical environment/harness status.

Independently inspect:
- launch packet generator;
- packet;
- packet audit;
- clean-room contract;
- canonical run contract.

Verify no startup allowance for:
- board/checkpoint;
- PM adjudication;
- prior PR/review;
- prior Resident run evidence;
- fixture/evaluator/release source;
- Git history concerning prior runs.

The packet must include all four approved inputs and no unauthorized control-plane material.

Search actual Resident-readable values for historical semantic leakage, not merely forbidden-category vocabulary.

## 16. C9 — due-work model-exchange entrypoint

Verify the real run package exposes:

`aios_exchange.runner:run_due_work`

Inspect it manually.

It must:
- accept explicit timezone-aware `now`;
- use the same `ExternalSessionModelHandler`;
- drive frozen Core's normal due-work path;
- contain no semantic rules;
- return mechanical result/status/handoff/integrity evidence.

Independently create a disposable synthetic World in which due work genuinely requires a model decision.

At least one synthetic due Wake/Review path must demonstrate:

frozen Core
→ due work
→ external model handler
→ durable request
→ independent test-only external response
→ durable consume
→ legal completion.

Do not use C15 fixture content.

Do not let the synthetic responder become reachable from the real run package.

## 17. Full Gate A/B/C/D review

Rerun complete author gates independently under the reviewer-qualified environment.

Do not merely invoke the author's summary.

Inspect raw evidence for:

### Gate A
durable exchange, crash/recovery, duplicate/tamper/ordering/replay.

### Gate B
actual frozen `RuntimeSnapshot` / `CapabilityResult` contract.

`CapabilityResult` legal fields remain exactly:
- name
- ok
- data
- error_code
- error_message
- call_id

Do not confuse legal `CapabilityCall.arguments` with invalid `CapabilityResult.arguments`.

### Gate C
must be non-vacuous:
- round 0 empty history;
- actual frozen capability execution;
- round 1 nonempty real `CapabilityResult`;
- durable external request/response/consume.

### Gate D
independently audit real package for:
- keyword routing;
- cursor/event matching;
- hard-coded cognition;
- prewritten replies;
- fallback directives/silence;
- hidden semantic callback;
- test responder reachability.

Author scanner PASS is not acceptance evidence by itself.

## 18. Corrective probe history integrity

Inspect Corrective-002 probe history.

Required chronology:
- initial carry/probe freeze;
- v1 result retained;
- v2 scanner-argument correction frozen before v2 execution;
- genuine #286 H2 RED committed before candidate repair;
- H1 correction afterwards;
- H2 final packet/evidence freeze afterwards.

The v1→v2 change must only fix the disclosed scanner argument bug and must not change expected outcomes to make RED/GREEN convenient.

Independently compare frozen probe source/hashes where practical.

## 19. Corrective-001 regression preservation

Re-attack C1/C2/C3, not just C4–C9.

Verify no regression in:
- response-file replay fail-closed semantics;
- pre-download wheel trust root;
- gate enumeration/result consistency.

## 20. Freeze integrity and non-circular evidence

Recompute:
- packet SHA;
- harness manifest;
- Core/tests canonical manifests;
- wheel lock SHA;
- environment record;
- gate results;
- C1–C3 regression result;
- C4–C9 candidate result;
- package FREEZE_MANIFEST;
- Corrective-002 FREEZE_MANIFEST;
- both SHA256SUMS scopes.

The candidate documents a two-tier evidence method to avoid packet/self-hash cycles.

Independently determine whether that method actually avoids circular self-authentication and whether H2 only freezes evidence/packet over unchanged H1 source.

Any covered code change after final candidate tests invalidates the freeze unless rerun/refrozen.

## 21. Packet status and content

Packet SHA expected:

`f6b61c33dc41d20438ab1b56bd1c8f2e46fcf6593532f3793c3c51ee7fbf7cdc`

Status must remain:

`PREP_REVIEW_READY`

It must not say:

`READY_FOR_RESIDENT`

Verify pins for:
- H1 exact head/parent;
- frozen RC;
- bootstrap;
- wheel trust root;
- canonical Core/tests manifests;
- user-turn entrypoint;
- due-work entrypoint;
- harness manifest;
- gates;
- contracts;
- startup set.

## 22. No real Resident execution

Independently search #288 evidence for signs of:
- real release-state;
- cursor reveal;
- real C15 event projection;
- real Resident World/session;
- real USER Phase-A turn;
- real cognition run.

Synthetic/disposable integration evidence is allowed.

If a real cursor was revealed or a real Resident run started, fail.

## 23. Reviewer-authored extra attacks

Do not constrain yourself to C1–C9.

Try to find new failure classes, especially around:
- crash boundary between validated ledger read and append;
- TOCTOU between request-body validation and response consume;
- duplicate events under concurrent/repeated calls;
- path/symlink attacks in manifest or bootstrap verification;
- stale wheelhouse with valid locked names but wrong bytes;
- foreign import path after verify;
- due-work restart/recovery;
- ambiguous simultaneous user-turn/due-work exchange state;
- packet/hash coverage omissions.

Use synthetic/disposable data only.

## 24. Durable publication required

A chat verdict alone is not acceptance.

Create:
- a new review-only branch;
- formal IA report;
- reviewer probe sources;
- probe freeze/hashes;
- collect-only/enumeration;
- raw outputs;
- environment record;
- exact review commit;
- review-only / evidence-only / DO NOT MERGE PR.

Then comment on PR #288 with:
- review PR number;
- exact review SHA;
- verdict;
- blocker count.

Do not modify #288.

## 25. Allowed final verdicts

### PASS

`ACCEPTANCE_PASS / blocker=0`

Then:

`READY_FOR_PM_INTEGRATION`

This does not make the Resident ready and does not authorize running it.

### FAIL

`ACCEPTANCE_FAIL / blocker=N`

For every blocker include:
- ID;
- exact path;
- reproduction;
- observed;
- expected;
- binding reason;
- minimal corrective scope.

Do not repair the candidate in the review window.

### Candidate drift

`REVALIDATION_REQUIRED`

### Technical review complete but durable publication impossible

`EVIDENCE_PUBLICATION_BLOCKED`

Preserve exact local review identity/evidence and do not pretend the gate completed.

## 26. Prohibitions

Do not:
- merge #288;
- modify #288;
- change packet status;
- run a real Resident;
- initialize real C15 release-state;
- reveal cursor 1;
- resume persistence Corrective-003;
- run Resident B/C;
- run evaluator/C15 close;
- modify/merge #263/#265;
- tag/public release.

Stop immediately after durable IA publication.
