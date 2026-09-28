# C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-INDEPENDENT-ACCEPTANCE

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Role:

**Independent Resident Launch Infrastructure Acceptance Reviewer**

You are not:
- Operator Prep author;
- Resident A/B/C;
- PM;
- Core implementation engineer;
- semantic evaluator.

Your task:

> Independently try to falsify the exact Operator Prep candidate and decide whether it is safe, reproducible, frozen, semantically clean infrastructure for a future fresh Resident launch.

Do not run the real Resident.
Do not reveal any real C15 cursor.
Do not modify PR #281.
Do not merge anything.

## 1. Fresh state and exact pin

Fresh-fetch live `main`.

Read:
- current task board/checkpoint;
- PM REVIEW_READY;
- Operator Prep prompt;
- Corrective-002 pre-reveal contamination adjudication;
- clean-room Resident contract;
- existing Resident A safe-run contract;
- PR #281 exact diff/evidence.

At dispatch, only valid candidate:

- PR #281
- head `10901d467679b70437ae112747eab81f889fd5cb`
- parent `abb8b435e5187c7c6c2f4332aea37cd805b4a53c`
- tree `db79761216529cf83f217ab00c937bc79806a510`

Frozen RC:
- software `f20f2edfa7af00d0286493fd15196ca9503bc315`
- Core tree `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`

If #281 head moved, return:

`REVALIDATION_REQUIRED`

## 2. Role boundary

This is infrastructure acceptance.

You may read Operator Prep governance/evidence and mechanical historical failure adjudications.

Do not:
- open sealed C15 fixture payloads;
- inspect evaluator expected semantics;
- run a real Resident;
- initialize real C15 release-state;
- reveal cursor 1.

Use synthetic/disposable data only.

## 3. Candidate scope

Mechanically verify all changed paths.

Expected:
- exactly operator-prep evidence/harness/bootstrap/package paths;
- zero `src/**`;
- zero `tests/**`;
- zero `.github/**`;
- zero fixture/evaluator/release-source changes;
- zero accepted-RC implementation change.

Any hidden implementation or fixture/evaluator change is a blocker.

## 4. Exact Git identity / packet head rule

Independently verify:
- candidate head;
- parent;
- tree;
- parent is exactly packet `operator_prep_exact_head`;
- launch packet is introduced only in the packet commit, not already present in its recorded parent;
- packet's frozen control-plane/RC identities resolve.

Do not accept self-reported identities without Git-object verification.

## 5. Reproduce qualified runtime

From a clean independent scratch/root, inspect and execute the frozen bootstrap.

Target:
- CPython 3.12.14;
- Pydantic 2.13.5;
- pytest 8.4.2;
- SQLite 3.45.1.

Prefer a clean bootstrap/build path rather than reusing the author's already-provisioned `/opt/aios` tree.

Record actual:
- Python;
- Pydantic;
- pytest;
- SQLite;
- OS/kernel/arch;
- OpenSSL if present;
- `aios_core.__file__`.

Verify the bootstrap pins sources/artifacts sufficiently to be reproducible.

If a clean reproduction is impossible because of reviewer-environment constraints, distinguish:
- package defect;
- external environment limitation.

Do not claim reproducibility without evidence.

## 6. Frozen RC identity

Using the reviewer-qualified runtime, verify:
- frozen software object;
- repository tree;
- Core tree;
- tests tree;
- Core content manifest if provided;
- imported `aios_core` resolves to the intended frozen checkout/source.

No live-main implementation substitution is allowed.

## 7. Gate A — durable exchange

Independently rerun and inspect, not merely read PASS.

Attack:
- request/response SHA mismatch;
- request-id mismatch;
- partial/torn write;
- orphan file without ledger record;
- edit/interior ledger deletion;
- tail truncation handling;
- crash before request publication;
- crash after request publication;
- response durable but not consumed;
- duplicate publication;
- response overwrite;
- response consumed before publication;
- fsync/atomic publication claims.

Confirm:
- `request_published` is the semantic-dispatch boundary;
- after that boundary, the harness never classifies an attempt as `not_submitted` merely because provider fields are null;
- ambiguous exchange states fail closed.

## 8. Gate B — frozen Core type contract

Independently import the actual frozen Core:
- `RuntimeSnapshot`;
- `CapabilityResult`.

Verify `CapabilityResult` exact legal surface:
- name;
- ok;
- data;
- error_code;
- error_message;
- call_id.

Rerun contract tests for:
- empty history;
- successful result;
- failed result;
- multiple results.

Search real-run code for invalid accesses such as:
- arguments;
- result;
- error;
- duration_seconds
on `CapabilityResult`.

Any mismatch is a blocker.

## 9. Gate C — non-vacuous two-round integration

Independently rerun the synthetic two-round frozen-Core integration.

Must prove:
1. round 0 snapshot has empty history;
2. test-only synthetic responder returns at least one legal capability call;
3. frozen Core actually executes it;
4. round 1 request is generated;
5. round 1 has non-empty real `CapabilityResult` history;
6. runner serializes/publishes that history without exception;
7. runtime reaches a legal terminal result.

Inspect raw evidence, not just pytest count.

The test-only deterministic responder must not use real C15 fixture content.

## 10. Gate D — semantic-script isolation

Independently inspect the real-run package.

Attempt to find:
- keyword-to-capability mapping;
- event-ID/cursor semantic routing;
- hard-coded Claims/goals/policies;
- prewritten assistant replies;
- fallback semantic response;
- hidden semantic callback;
- test responder import/reachability from real-run modules.

Confirm real response mode is exactly:

`EXTERNAL_CURRENT_RESIDENT_SESSION`

and that real-run runner consumes externally published response bytes only.

A test-only responder is allowed only if it is unreachable from real execution.

## 11. Launch packet safety

Independently inspect:

`RESIDENT_SAFE_LAUNCH_PACKET.json`

Verify:
- status remains `PREP_REVIEW_READY`;
- not `READY_FOR_RESIDENT`;
- cursor range is 1..13;
- exact RC/environment/harness hashes;
- clean-room contract and run-contract hashes;
- real response mode;
- allowed startup inputs are minimal;
- forbidden control-plane categories are explicit.

Search packet values and Resident-readable startup artifacts for:
- prior user payload;
- prior assistant text;
- prior Claims/summaries;
- prior cursor-specific semantic decisions;
- evaluator expected semantics;
- descriptions of what the Resident "should learn".

Do not confuse prohibition vocabulary itself with leaked semantic content.

## 12. Clean-room boundary

Independently verify future Resident startup is constrained to:
- clean-room contract;
- exact accepted safe launch packet;
- mechanical environment/harness status.

The Resident must not be instructed to read:
- board;
- checkpoint;
- PM adjudications;
- prior Resident PR/evidence;
- IA reports;
- Git history/search;
- fixture/evaluator/release source.

If accepted package cannot enforce or clearly communicate this boundary, FAIL.

## 13. Freeze integrity

Independently recompute:
- bootstrap SHA;
- harness manifest;
- packet SHA;
- packet audit SHA;
- gate result/raw/enumeration hashes;
- environment record hash;
- clean-room/run-contract hashes;
- `SHA256SUMS`;
- `FREEZE_MANIFEST.json`.

Check for post-gate edits:
- gate run must correspond to the final frozen harness;
- any harness/operator-tool edit after the final gate run that changes covered behavior invalidates the freeze.

## 14. No real Resident execution

Search candidate artifacts and repository-visible evidence for accidental:
- real release-state init;
- real cursor reveal;
- real C15 event payload;
- real Resident World/session;
- real Phase-A USER turn.

Synthetic disposable Gate C state is allowed.

A real Resident run in this Operator Prep task is a blocker.

## 15. Reviewer-authored probes

Add independent probes where useful.

Freeze probes before first candidate execution:
- source SHA-256;
- enumeration;
- expected outcomes.

Preserve any RED/harness correction history.

Do not modify candidate.

## 16. Durable review publication

Do not finish with chat-only verdict.

Create:
- review-only branch;
- formal report;
- reviewer probes/hashes;
- raw outputs;
- exact review commit;
- review-only / evidence-only / DO NOT MERGE PR;
- comment on #281 with exact review SHA + review PR.

## 17. Verdict

Exactly one:

### `ACCEPTANCE_PASS / blocker=0`

Then:
`READY_FOR_PM_INTEGRATION`

This means Operator Prep is acceptable for PM integration.
It does **not** itself release the Resident.

### `ACCEPTANCE_FAIL / blocker=N`

Each blocker must include:
- exact path;
- reproduction;
- observed;
- expected;
- why binding;
- minimal corrective scope.

### `REVALIDATION_REQUIRED`

If #281 head moved.

### `EVIDENCE_PUBLICATION_BLOCKED`

If review completed but durable publication failed.

## 18. Prohibitions

Do not:
- merge #281;
- change packet status;
- release or run Corrective-003 Resident;
- initialize real release-state;
- reveal cursor 1;
- resume persistence;
- run Resident B/C;
- run evaluator;
- close C15;
- modify #263/#265.

Stop after durable IA publication.
