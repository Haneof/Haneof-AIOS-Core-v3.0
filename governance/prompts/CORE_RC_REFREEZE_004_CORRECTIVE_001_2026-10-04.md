# CORE-RC-REFREEZE-004-CORRECTIVE-001

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

WINDOW:

`26`

Role:

**RC Freeze Gate Corrective Engineer**

You are not:
- PM;
- Independent Acceptance Reviewer;
- Core product corrective engineer;
- C15 persistence/operator corrective engineer;
- Resident A/B/C;
- evaluator;
- public release operator;
- UI/hardware engineer.

Your only task:

> Repair the three binding Window 25 formal-gate false-green blockers without changing the frozen Core software boundary.

You must stop at:

`REVIEW_READY / READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE / DO NOT MERGE`

or:

`BLOCKED`.

Do not self-accept.
Do not merge.

## 0. Fresh ground truth

Start with:

`git fetch --all --prune`

Freshly verify:
- live main;
- PR #325;
- PR #328;
- task board/checkpoint;
- PM adjudication;
- exact failed candidate/workflow;
- Window 25 review evidence.

At dispatch the failed candidate is:

PR #325

head:
`70134269ddfc7c80c4a703a933253bd099746504`

parent:
`b295e6a83b345864b40d6a731fb25812c0ed9ad4`

tree:
`5727143aa14359d67defb41113b46d6759ad7f2e`

Frozen software remains:
`1cee3c5ad12f4b9098232bae11b51df786c5eb2f`

Window 25 review:
- PR #328 REVIEW_ONLY / DO NOT MERGE;
- technical evidence commit `ffa6475fe4dde4b5d06b09a629b059b89f1ff434`;
- technical evidence tree `ff2c098a098a8ff73fcc475b80560045b70b1277`;
- publication head `5b46b70f1b166a28201b3865d455d6ba0e2afec5`;
- verdict `ACCEPTANCE_FAIL / blocker=3`.

Read:
- `governance/CORE_RC_REFREEZE_004_WINDOW25_ACCEPTANCE_FAILURE_ADJUDICATION_2026-10-04.md`;
- Window 25 review report under PR #328;
- exact failed workflow from `70134269...`.

If identities drift, stop for PM revalidation.

## 1. Failed candidate immutability

PR #325 is historical failed evidence.

Do not:
- commit to its branch;
- amend;
- rebase;
- squash;
- force-push;
- change its body to pretend PASS;
- merge it.

Create a **new branch** for Window 26.

Preferred construction:
- branch from exact failed candidate `70134269...`;
- add append-only corrective commits;
- never mutate the old branch.

Recommended branch:
`release/core-rc-refreeze-004-corrective-001-window26`

Open a **new PR** when ready.

## 2. Strict scope

This corrective is release-infrastructure/evidence only.

Allowed implementation change:
- `.github/workflows/core-rc-refreeze-004-formal-gate.yml`

Allowed new corrective evidence:
- `reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/**`

Allowed release packet text changes only if mechanically required to describe the corrected formal contract:
- `release/rc/CORE_RC_REFREEZE_004_MANIFEST.json`
- `release/rc/CORE_RC_REFREEZE_004_OPERATOR_PACKET.md`

Do not change historical Window 25 review evidence.

Forbidden:
- `src/**`;
- product `tests/**`;
- `tools/**`;
- `pyproject.toml`;
- C15 implementation;
- Resident state/evidence;
- governance adjudication records from prior windows.

If the three blockers cannot be fixed within this scope:
`BLOCKED / PM_ADJUDICATION_REQUIRED`.

## 3. RED-first preservation

Before modifying the workflow, preserve mechanical RED for all three blockers against exact failed candidate `70134269...`.

### BLK-001 RED
Use the exact Window 25 classifier reproduction.

Canonical reviewer probe:
`reviews/CORE_RC_REFREEZE_004_INDEPENDENT_ACCEPTANCE_WINDOW_25/workflow_false_green_probe.py`

at technical review commit:
`ffa6475fe4dde4b5d06b09a629b059b89f1ff434`

expected SHA-256:
`fc7df49fdc80b340d2ddc065ad87c01c81987bef78f13fd6494ab035613796a9`

Fresh-extract and verify hash.

Failed candidate must reproduce that pytest exit 4 can be laundered to GREEN.

### BLK-002 RED
Mechanically preserve:
- top-level `contents: write`;
- checkout lacks `persist-credentials:false`;
- hosted checkout credential persistence;
- only pre-test remote-head equality check;
- no terminal remote-head/frozen-worktree equality check.

Do not claim the historical run maliciously pushed anything. The RED is the admitted authority/false-green path.

### BLK-003 RED
Mechanically reproduce that non-201 publication response can return shell exit zero under the failed candidate logic.

Freeze these RED probes/hashes before the corrective change.

## 4. Fix IA25-BLK-001 — C15 pytest exit integrity

Replace console-only downstream classification with explicit pytest exit semantics plus structured JUnit adjudication.

Binding rules:

1. Execute `tests/c15_persistence/**` and capture exact pytest exit.
2. Only `rc=0` and `rc=1` are admissible.
3. `rc=2`, `3`, `4`, `5`, or any other value => formal gate failure.
4. JUnit XML must exist, be non-empty, and parse successfully.
5. For `rc=0`:
   - JUnit failures = 0;
   - JUnit errors = 0.
6. For `rc=1`:
   - at least one failed/error testcase must exist;
   - every failed/error testcase must mechanically map to `tests/c15_persistence/**`;
   - any non-downstream failed/error testcase => `ACCEPTED_CORE_REGRESSION_EXPOSED_BY_C15`.
7. Console parsing can be supplemental evidence only.
8. Preserve the downstream RED count/evidence. Do not make C15 green in this task.

Add author-owned regression cases at minimum for:
- rc=0 clean pass;
- rc=1 downstream-only failures accepted as debt;
- rc=1 one non-downstream failure => fail;
- rc=2 => fail;
- rc=3 => fail;
- rc=4 => fail;
- rc=5 => fail;
- missing JUnit => fail;
- malformed JUnit => fail;
- rc=1 but zero structured failures/errors => fail.

## 5. Fix IA25-BLK-002 — credential isolation and terminal immutability

The main formal gate job must be read-only.

Required:
- `permissions: contents: read`;
- `pull-requests: read` only if actually needed;
- `actions/checkout@v4` with `persist-credentials: false`;
- no write token in environment of candidate-controlled tests/probes;
- no repository write authority available through local git config;
- no candidate-controlled code in any job with `contents: write`.

If `workflow_dispatch` remains:
- assert canonical corrective branch/ref explicitly;
- reject dispatch from any other ref.

At the start, retain exact-head checks.

After **all** candidate-controlled test/probe execution and before successful gate completion, add a binding terminal identity step that fresh verifies:
- local candidate HEAD == `GITHUB_SHA`;
- remote canonical corrective branch head == `GITHUB_SHA`;
- frozen worktree HEAD == `FROZEN_SHA`;
- frozen root tree == pinned root tree;
- frozen Core tree == pinned Core tree;
- frozen tests tree == pinned tests tree;
- frozen workflows tree == pinned frozen-workflow tree;
- frozen pyproject blob == pinned blob;
- frozen worktree has no tracked modification;
- fresh current main still has zero protected implementation drift from the frozen software.

A candidate-controlled probe changing a tracked frozen file must make the gate fail.

## 6. Fix IA25-BLK-003 — mandatory exact-pin publication

Do not give the test/gate job write permission merely to publish a comment.

Split publication into a separate job.

Required architecture:

### Job A — formal gate
- read-only permissions;
- checkout with no persisted credentials;
- all tests/probes;
- terminal immutability recheck;
- evidence artifact publication is allowed;
- success only if all binding checks pass.

### Job B — mandatory exact-pin publisher
- `needs: Job A`;
- executes only after Job A succeeds;
- minimum `contents: write` needed for commit comment;
- **no checkout**;
- **no candidate repository code execution**;
- exact comment binds:
  - task;
  - run id;
  - exact candidate SHA;
  - frozen software SHA;
  - gate job success identity.
- explicit HTTP handling:
  - HTTP 201 => success;
  - anything else => print response and `exit 1`.

The overall workflow must be GREEN only if both Job A and Job B are GREEN.

Do not use `if: always()` on the mandatory publisher in a way that can convert failed formal gate into a successful workflow.

## 7. Publication regression / fault injection

Before formal hosted run, mechanically test the corrected workflow contract.

At minimum:
- simulate comment HTTP 500 => publisher logic non-zero;
- simulate comment HTTP 401/403 => non-zero;
- 201 => zero;
- verify publisher job contains no checkout;
- verify publisher job contains no candidate-script execution;
- verify gate job has no `contents: write`;
- verify checkout explicitly disables credential persistence;
- verify terminal remote-head equality exists after all executable probes;
- verify all pytest rc 2-5 are rejected.

Preserve raw outputs.

## 8. Frozen software must remain identical

Recompute and preserve:

Frozen software:
`1cee3c5ad12f4b9098232bae11b51df786c5eb2f`

Required:
- root tree `70b2711258567863ea0d93025a6a07e39631726a`
- Core tree `16f1487e291b009c55bee402abfd79fdacbae960`
- tests tree `9db1bfa08143bc99fe03836e2752ee6e05694eb6`
- frozen workflows tree `72cde9d2dc2b35d071bfa36c954dac2faff4a803`
- pyproject blob `b38833c7537fa60d5c2f02ed4bb19158d8995a11`

Corrective changes to the RC004 candidate workflow do not alter this frozen software boundary.

## 9. Carry-forward validation

Because these blockers are release-gate defects, do not blindly rerun only workflow unit tests.

The final exact corrective candidate formal run must still freshly establish all prior RC004 binding results, including:
- full Core 928/0;
- Window 20 Suite A 4/0;
- Window 20 Suite B 7/0;
- Window 17 14/0;
- Corrective-003 security;
- real SIGKILL/fresh process;
- clean non-editable wheel/headless;
- backup/restore/rebuild Route B probe;
- writer/restart/FIX/current-time/SCALE;
- C15 downstream classification under the **new rc/JUnit rules**;
- open-PR contamination;
- exact frozen object identities;
- protected-drift check.

Do not inherit run `37213157986` as the corrected formal gate.

A fresh exact-head run is mandatory.

## 10. Formal environment

Use:
- CPython 3.12.14;
- Pydantic 2.13.5;
- pytest 8.4.2;
- record exact SQLite;
- record exact OpenSSL;
- OS/kernel/arch.

## 11. New exact candidate and PR

Do not reuse PR #325.

Create a new RC corrective candidate PR.

It must:
- be OPEN;
- non-draft;
- UNMERGED;
- DO NOT MERGE;
- identify failed predecessor PR #325;
- identify Window 25 review PR #328;
- pin exact head/parent/tree;
- pin frozen software;
- pin fresh formal workflow run;
- state blocker closure claims individually;
- state no Core/C15/Resident implementation changes.

The new branch must not rewrite failed historical commits.

## 12. Formal CI after immutable head

Finalize all tracked corrective evidence **before** the final hosted run.

After final candidate head is immutable:
- run the corrected formal workflow;
- no commit afterward merely to add evidence;
- post-run text may use PR body/comment.

Overall workflow must include successful mandatory exact-pin publication.

If the gate job passes but publisher job fails:
`FORMAL_CI_FAIL / IA25-BLK-003_NOT_CLOSED`.

If any terminal immutability check fails:
`FORMAL_CI_FAIL / IA25-BLK-002_NOT_CLOSED`.

If C15 classifier accepts pytest rc 2-5 or malformed/missing JUnit:
`FORMAL_CI_FAIL / IA25-BLK-001_NOT_CLOSED`.

## 13. Required corrective evidence

Create under:
`reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/**`

At minimum:
- `GROUND_TRUTH.md`
- `FAILED_CANDIDATE_IDENTITY.md`
- `WINDOW25_REVIEW_IDENTITY.md`
- `RED_FIRST.md`
- `BLK001_C15_EXIT_JUNIT_REPAIR.md`
- `BLK002_CREDENTIAL_IMMUTABILITY_REPAIR.md`
- `BLK003_MANDATORY_PIN_PUBLICATION_REPAIR.md`
- `WORKFLOW_SECURITY_AUDIT.md`
- `SCOPE_AUDIT.md`
- `FORMAL_CI_RESULTS.md`
- `FINAL_HANDOFF.md`
- frozen regression probe source/hash;
- raw RED/GREEN outputs;
- SHA256SUMS.

## 14. Prohibited actions

Do not:
- modify frozen Core software;
- modify product tests to make gates pass;
- repair `tools/c15_persistence/**` or `tests/c15_persistence/**`;
- restore local self-trust;
- modify PR #328 review evidence;
- merge PR #325 or the new corrective PR;
- perform Independent Acceptance;
- perform PM integration;
- run Resident;
- enter evaluator;
- public release/tag.

## 15. Exit

### Success

Only after a fresh exact-head hosted run proves all three blockers closed:

`CORE-RC-REFREEZE-004-CORRECTIVE-001 = REVIEW_READY`

`READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE`

`DO NOT MERGE`

Report:
- fresh main;
- failed PR #325 exact identity;
- Window 25 review identity;
- new candidate head/parent/tree;
- exact changed files/scope;
- BLK-001 RED → GREEN proof;
- BLK-002 RED → GREEN proof;
- BLK-003 RED → GREEN proof;
- corrected permission/checkout architecture;
- terminal immutability evidence;
- fresh full RC gate results;
- formal environment;
- exact run id;
- mandatory publisher job result;
- external pin identity;
- new PR number/state;
- blocker closure claim;
- no candidate drift.

Then stop.

### Failure

`BLOCKED`

Preserve evidence and stop.
