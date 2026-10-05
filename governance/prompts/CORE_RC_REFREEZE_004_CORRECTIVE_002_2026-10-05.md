# CORE-RC-REFREEZE-004-CORRECTIVE-002

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

WINDOW:
`28`

Role:
**RC Freeze Gate Corrective Engineer**

You are not:
- PM;
- Independent Acceptance Reviewer;
- Window 26 author acting as reviewer;
- Core product corrective engineer;
- C15 persistence/operator corrective engineer;
- Resident A/B/C;
- evaluator;
- public release operator;
- UI/hardware engineer.

Your only task:

> Close the single PM-binding Window 27 blocker: whole-run candidate identity / inter-job TOCTOU false-green in the RC004 formal workflow.

Do not perform Independent Acceptance.
Do not merge.

## 0. Fresh ground truth

Start:
`git fetch --all --prune`

Freshly verify live main and read:
- task board;
- current checkpoint;
- Window 27 PM adjudication;
- PR #330;
- PR #332;
- PR #333;
- run `37262331480`;
- current RC004 workflow.

At PM release:
- failed corrective candidate PR #330 exact head = `2380121639865b1bd29176cf944f5a20afe4112d`
- parent = `04c37f7dd8ba6f20e1c67dad43c0f21087f51eeb`
- tree = `72d3cd0da849fae3b1cbfdfb7ae995528e1cfd71`
- frozen software = `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`

PR #330 is historical failed evidence:
`OPEN / UNMERGED / DO NOT MERGE`

Do not commit to PR #330 branch.
Do not amend/rebase/squash/force-push it.
Create a new branch from exact `2380121639865b1bd29176cf944f5a20afe4112d`.

Recommended:
`release/core-rc-refreeze-004-corrective-002-window28`

Open a NEW PR.

## 1. PM binding

Canonical Window 27 review:
PR #333 REVIEW_ONLY / DO NOT MERGE.

Corroborating review:
PR #332 REVIEW_ONLY / DO NOT MERGE.

Binding blocker:
`IA27-BLK-002 = BINDING / CRITICAL`

Alias note:
PR #332 numbered the same TOCTOU finding as its sole `IA27-BLK-001`; PM canonical numbering follows PR #333: `IA27-BLK-002`.

Non-binding:
PR #333 `IA27-BLK-001` JUnit synthetic fuzz result is `NON_BINDING_HARDENING_OBSERVATION`.
Do not widen this task to JUnit hardening.

## 2. Exact failure to reproduce RED-first

Before editing the workflow, fresh reproduce the whole-run false-green.

Real prior control:
- run `37262331480`
- old event SHA A = `4fb32d9b94a79e342af770050d71a45a24677008`
- post-terminal branch head B = `e4fd46c04c8ad982fa1fa274546dbf0d099343c5`
- gate = SUCCESS
- publisher = SUCCESS
- overall = SUCCESS.

Fresh RED reproduction must demonstrate the same property using a disposable reviewer/control branch or isolated repository:

1. event/run begins on A;
2. formal terminal identity check passes for A;
3. canonical branch moves to B after that check;
4. old run still reaches successful publisher;
5. old overall result can remain SUCCESS.

Record exact control identities and outputs.

Do not mutate PR #330.

## 3. Corrective invariant

After Corrective-002, the following must be mechanically true:

> If the canonical corrective branch moves away from `GITHUB_SHA` at any time after the formal run starts and before the workflow has durably completed its exact-pin publication/identity seal, the stale run must not remain an authoritative SUCCESS.

A mere Job-A terminal check is insufficient.

A static string assertion is insufficient.

A publisher-side check alone is insufficient unless the post-check race is also closed or mechanically invalidated.

The final design must make the Window 27 real control scenario go RED/fail/cancel for the stale run.

## 4. Allowed design space

You may modify only the RC004 formal workflow and Corrective-002 evidence.

At minimum evaluate a combination such as:
- canonical-branch concurrency with stale-run cancellation (for example `cancel-in-progress: true` or an equivalent server-side mechanism);
- publisher-side fresh canonical-ref equality before publication;
- post-publication identity seal / final verifier;
- exact run/candidate pinning that cannot remain authoritative after branch drift.

Do not blindly implement these examples; prove the resulting whole-run property.

The solution must not introduce a broader write surface.

## 5. Write authority

Job A remains read-only:
- `contents: read`
- `pull-requests: read`
- checkout `persist-credentials:false`.

Candidate-controlled tests/probes must never receive write credentials.

Any write-capable publication job:
- no checkout;
- no candidate script/helper/test;
- inline fixed workflow logic only;
- minimum required permission;
- no branch/tag/file/PR/release mutation.

If remote-head checks are added to the publisher, use fixed inline API/remote logic, not candidate-carried executable code.

## 6. Publisher semantics carry-forward

IA25-BLK-003 is already CLOSED and must stay closed.

Preserve:
- only HTTP 201 succeeds for commit-comment publication;
- transport failures fail;
- non-201 fails;
- no `test ... || cat` laundering;
- publisher depends on successful formal gate;
- no candidate code under write token.

Freshly rerun the full publisher fault matrix.

## 7. JUnit classifier scope

Do not repair the Window 27 synthetic XML hardening observations in this task.

Preserve the current binding formal-path behavior:
- rc only 0/1 admissible;
- rc2/3/4/5/unknown rejected;
- actual pytest usage/collection/no-tests paths fail closed;
- real C15 JUnit remains downstream-only debt when appropriate.

No C15 implementation changes.

## 8. Required real TOCTOU GREEN proof

Static self-test is not enough.

Before REVIEW_READY, run a real GitHub Actions controlled reproduction on a disposable branch that mirrors the corrected identity lifecycle.

Required scenario:
1. run starts on commit A;
2. terminal/identity stage for A passes;
3. branch is deliberately advanced to B while old A run is still active;
4. old A run must end in a non-authoritative state:
   - cancelled, failure, or another mechanically explicit non-success outcome;
5. old A publisher must not produce a valid success pin after drift, or any stale pin must be mechanically invalidated and the overall old run must not be SUCCESS.

Report:
- control branch;
- A SHA;
- B SHA;
- old run id;
- old gate result;
- old publisher result;
- old overall conclusion;
- new B run behavior;
- exact mechanism that prevented stale SUCCESS.

If old A run still ends SUCCESS:
`BLOCKED / IA27-BLK-002_NOT_CLOSED`
Stop.

## 9. Final candidate exact-head formal CI

After all tracked Corrective-002 evidence is committed:
- freeze exact new candidate head;
- run the real RC004 formal workflow on that exact head;
- no commits after final CI.

Require:
- branch head = PR head = run head;
- Job A success;
- mandatory publisher success;
- whole-run identity seal success;
- no stale control false-green.

Formal environment:
- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2
- record SQLite/OpenSSL/OS/kernel/architecture/Python executable/`aios_core.__file__`.

## 10. Full carry-forward RC gates

Fresh rerun:
- Full Core (expected historical count 928, but use fresh result);
- Window20 Suite A 4/0;
- Window20 Suite B 7/0;
- Window17 14/0;
- Corrective-003 security;
- real SIGKILL/process loss;
- clean non-editable wheel/headless;
- backup/restore/rebuild;
- writer/restart/FIX/current-time/SCALE;
- C15 actual pytest/JUnit classification;
- open-PR contamination;
- frozen object identities;
- protected drift;
- publisher fault matrix.

Do not inherit old GREEN.

## 11. Scope

Allowed:
- `.github/workflows/core-rc-refreeze-004-formal-gate.yml`
- `reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/**`

No:
- `src/**`
- product `tests/**`
- `tools/**`
- `pyproject.toml`
- C15 implementation
- Resident state/evidence
- Window 27 review evidence.

If scope cannot close the blocker:
`BLOCKED / PM_ADJUDICATION_REQUIRED`

## 12. Evidence

Create:
`reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/**`

At minimum:
- GROUND_TRUTH.md
- FAILED_CANDIDATE_IDENTITY.md
- WINDOW27_REVIEW_IDENTITY.md
- PM_ADJUDICATION.md
- RED_FIRST_TOCTOU.md
- WHOLE_RUN_IDENTITY_MODEL.md
- CREDENTIAL_PERMISSION_AUDIT.md
- PUBLISHER_CARRY_FORWARD.md
- REAL_GITHUB_TOCTOU_CONTROL.md
- FORMAL_CI_RESULTS.md
- SCOPE_AUDIT.md
- FINAL_HANDOFF.md
- raw control outputs
- SHA256SUMS

All tracked evidence must be committed before final formal CI.

Post-final-CI receipts only via PR body/comments.

## 13. New PR

Do not reuse #330.

New PR:
`OPEN / non-draft / UNMERGED / DO NOT MERGE`

Body must pin:
- failed predecessor #330 exact head;
- Window 27 canonical review #333;
- corroborating #332;
- PM binding blocker `IA27-BLK-002`;
- new head/parent/tree;
- frozen software;
- real TOCTOU control run;
- final formal run;
- Job A/publisher/identity-seal results;
- artifact;
- exact external pin;
- scope;
- `NO CORE IMPLEMENTATION CHANGE`;
- `NO C15 IMPLEMENTATION CHANGE`;
- `NO RESIDENT`.

## 14. Prohibited

Do not:
- repair PR #330 in place;
- merge #330;
- merge #332/#333;
- perform Independent Acceptance;
- PM integrate;
- repair Core;
- repair C15;
- run Resident;
- enter evaluator;
- public release/tag;
- UI/hardware.

## 15. Exit

Success only if the real stale-run control can no longer finish authoritative SUCCESS and all final exact-head gates are green.

Output:
`CORE-RC-REFREEZE-004-CORRECTIVE-002 = REVIEW_READY`
`READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE`
`DO NOT MERGE`

Report:
- fresh main;
- failed #330 identity;
- Window27 review identities;
- PM adjudication;
- new branch/PR/head/parent/tree;
- RED reproduction;
- corrected whole-run identity mechanism;
- real GitHub TOCTOU control;
- permission model;
- publisher carry-forward;
- full RC gates;
- formal environment;
- final run/jobs/artifact/pin;
- scope;
- candidate drift;
- blocker closure claim.

Then stop.
