# CORE-RC-REFREEZE-004-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

WINDOW:
`27`

Role:
**Fresh Independent RC Freeze Corrective Acceptance Reviewer**

You are not:
- Window 26 engineering author;
- PR #330 author;
- corrective engineer;
- PM integrator;
- merge owner;
- C15 persistence/operator corrective engineer;
- Resident A/B/C;
- evaluator;
- public release operator;
- UI/hardware engineer.

Your only task:

> Perform Fresh Independent Acceptance of PR #330 exact candidate and try as hard as possible to falsify the claimed closure of IA25-BLK-001 / 002 / 003.

Do not confirm the author report.
Do not repair.
Do not modify PR #330.
Do not merge.

## 0. Fresh ground truth

Start:
`git fetch --all --prune`

Freshly verify:
- live main;
- PR #325;
- PR #328;
- PR #330;
- task board/checkpoint;
- PM Window 25 adjudication;
- Window 26 handoff/evidence;
- formal run and artifact metadata;
- mandatory commit comment.

At PM release the exact candidate is:

PR #330

branch:
`release/core-rc-refreeze-004-corrective-001-window26`

head:
`2380121639865b1bd29176cf944f5a20afe4112d`

parent:
`04c37f7dd8ba6f20e1c67dad43c0f21087f51eeb`

tree:
`72d3cd0da849fae3b1cbfdfb7ae995528e1cfd71`

Expected:
`OPEN / non-draft / UNMERGED / DO NOT MERGE`

If head changes:
`CANDIDATE_DRIFT / REVALIDATION_REQUIRED`
Stop.

Frozen software:
`1cee3c5ad12f4b9098232bae11b51df786c5eb2f`

Failed predecessor:
PR #325 @ `70134269ddfc7c80c4a703a933253bd099746504`

Window 25 review:
PR #328 REVIEW_ONLY
technical evidence `ffa6475fe4dde4b5d06b09a629b059b89f1ff434`
publication head `5b46b70f1b166a28201b3865d455d6ba0e2afec5`

## 1. Independence

Do not trust:
- Window 26 FINAL_HANDOFF;
- PR #330 body;
- author self-tests;
- author static workflow probe;
- formal GREEN alone;
- author RED/GREEN raw outputs.

Use them only as:
- navigation;
- claims to falsify;
- historical context.

Create fresh reviewer-owned attacks before judging.

## 2. Exact construction/scope

Freshly prove:
`70134269... -> 04c37f7d... -> 23801216...`

Require:
- exactly 2 commits ahead / 0 behind relative to failed candidate;
- no history rewrite;
- no change under `src/**`;
- no product `tests/**`;
- no `tools/**`;
- no `pyproject.toml`;
- no C15 implementation;
- no Resident state/evidence.

Window 26 delta may only be:
- `.github/workflows/core-rc-refreeze-004-formal-gate.yml`
- `reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/**`

Remember PR #330 relative to main contains inherited RC packet files; audit the **failed-candidate -> corrective-head** delta separately.

## 3. Frozen software identity

Fresh recompute from Git objects:
- frozen SHA `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`
- root tree `70b2711258567863ea0d93025a6a07e39631726a`
- Core tree `16f1487e291b009c55bee402abfd79fdacbae960`
- tests tree `9db1bfa08143bc99fe03836e2752ee6e05694eb6`
- workflows tree `72cde9d2dc2b35d071bfa36c954dac2faff4a803`
- pyproject blob `b38833c7537fa60d5c2f02ed4bb19158d8995a11`

Freshly compare frozen software to live main for protected drift.

## 4. Historical RED must remain real

Fresh-extract Window 25 canonical workflow false-green probe from:
technical review commit `ffa6475fe4dde4b5d06b09a629b059b89f1ff434`

expected blob:
`c8a9050819440cc10605b08c943d29827f2b76c5`

expected SHA-256:
`fc7df49fdc80b340d2ddc065ad87c01c81987bef78f13fd6494ab035613796a9`

Freshly reproduce against failed candidate:
- BLK-001 rc=4 laundering;
- BLK-002 write-capable persisted checkout / missing terminal gate;
- BLK-003 non-201 diagnostic returning zero.

Do not accept author raw files as independent RED evidence.

## 5. IA25-BLK-001 independent attack — C15 rc/JUnit

Author claim:
- only rc 0/1 admissible;
- rc2/3/4/5/unknown fail;
- missing/empty/malformed JUnit fail;
- rc1 requires structured failure/error;
- all structured failures/errors must map to `tests/c15_persistence/**`.

You must independently fuzz this classifier beyond the 10 author cases.

At minimum attack:
- rc values: -1, 0, 1, 2, 3, 4, 5, 6, 255;
- missing JUnit;
- empty file;
- malformed XML;
- XML namespace on testcase/failure/error;
- nested testsuites;
- duplicate/nested summary counters;
- non-integer failures/errors counters;
- summary says failures>0 but no failing testcase;
- testcase failure exists but summary says zero;
- testcase with both failure and error;
- testcase missing `file`;
- testcase missing `classname`;
- empty file/classname;
- Windows separators;
- leading `./`;
- absolute paths;
- `../` traversal;
- `tests/c15_persistence_evil/**`;
- classname spoofing;
- file path and classname disagreeing;
- non-downstream setup/collection-like structured errors;
- multiple downstream + one non-downstream case.

Determine whether mapping is fail-closed for **actual pytest JUnit semantics**, not merely for hand-authored friendly XML.

Freshly run the real frozen `tests/c15_persistence/**` and independently inspect the produced JUnit and exact pytest exit.

If any pytest non-test-failure state can still become downstream GREEN, blocker.

## 6. IA25-BLK-002 independent attack — credential isolation

Do not rely on string search alone.

Freshly audit exact workflow and hosted job behavior.

Verify Job A:
- `contents: read`;
- checkout `persist-credentials:false`;
- no write-capable token exposed to repository tests/probes;
- step-scoped GH_TOKEN used for open-PR inventory is actually read-only under job permissions and is not passed to repository-owned scripts;
- local git config contains no checkout auth extraheader during candidate-controlled execution;
- no alternate credential source exists via env/config/helper;
- `workflow_dispatch` rejects noncanonical ref.

Attack:
- env variables visible to candidate subprocesses;
- git config/system/global credential helpers;
- checkout token remnants;
- callback/subprocess inheritance;
- candidate helper attempting `git push`;
- REST write attempt from Job-A-equivalent read token if safely reproducible in disposable repo/fork.

No mutation of PR #330.

## 7. IA25-BLK-002 independent attack — terminal immutability and TOCTOU

This is a required fresh attack.

Author terminal check is near the end of Job A.

Independently determine whether the invariant:

> candidate branch remains exact throughout the **entire formal workflow**

is actually closed.

Attack the interval:
1. Job A terminal remote-head check succeeds.
2. Branch moves after that check.
3. Artifact upload / Job A completion occurs.
4. Job B mandatory publisher runs.
5. Overall workflow may still conclude SUCCESS.

The reviewer must determine mechanically, preferably in a disposable fork/reproduction, whether a branch move in that interval can leave the old run GREEN.

Check whether Job B itself re-verifies canonical remote branch head == `GITHUB_SHA`.
At PM release, the publisher does **not appear to perform a remote-head recheck**; do not assume that is acceptable.

If the old run can finish SUCCESS after branch drift occurring after Job A terminal check, evaluate against IA25-BLK-002's binding invariant:
`candidate head must remain immutable throughout formal run`.

If violated, raise a new blocker. Do not repair.

Also attack:
- tracked frozen mutation after terminal check;
- artifact-generation ordering;
- any candidate-controlled step after terminal check;
- post-job action behavior that can mutate state.

## 8. IA25-BLK-003 independent attack — publisher

Author claim:
- separate Job B;
- needs Job A success;
- contents:write only;
- no checkout;
- no candidate helper/test;
- non-201 exits nonzero.

Fresh verify all.

Do not stop at 401/403/500.

Attack:
- 200, 201, 202, 204, 301/302, 400, 401, 403, 404, 409, 422, 429, 500, curl transport failure;
- empty/invalid response;
- curl exits nonzero before `code` assignment;
- command substitution + `set -e` behavior;
- Job A failed/skipped/cancelled;
- Job B skipped semantics and overall workflow conclusion;
- comment created on wrong SHA;
- comment body truncation/substitution;
- workflow_dispatch on wrong ref;
- publisher write authority broader than needed.

Critically inspect that Job B's inline workflow logic is the only code running with write permission and cannot invoke checked-out candidate code.

## 9. Exact-pin semantic binding

Fresh verify comment ID:
`203380647`

Must bind:
- task;
- run `37217853558`;
- exact candidate `2380121639865b1bd29176cf944f5a20afe4112d`;
- frozen software `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`;
- formal gate result success.

Check:
- comment timestamp occurs after Job A success;
- no stale comment from prior run can be mistaken for current pin;
- multiple comments cannot create ambiguity;
- publication failure cannot be hidden by an earlier successful comment.

## 10. Formal run identity

Fresh verify run:
`37217853558`

Require:
- event push;
- exact run head `2380121639865b1bd29176cf944f5a20afe4112d`;
- overall SUCCESS;
- Job A SUCCESS;
- Job B SUCCESS;
- no candidate commit after run;
- branch head and PR head still exact candidate.

Formal artifact:
ID `11309495093`
name `core-rc-refreeze-004-corrective-001-evidence`
digest `sha256:02415a0457af3aec5cb50d5195120202aae2c9cb23d3c81cbefaf867b7d216e0`

Download and inspect if available. If unavailable, disclose limitation.

## 11. Author static/self-tests are not acceptance

Author artifacts:
- `c15_junit_classifier.py`
- `workflow_security_static_probe.py`
- `publisher_http_contract.sh`

Audit them for vacuity:
- are they checking semantics or just strings?
- can workflow rearrangement preserve strings while bypassing properties?
- are candidate-owned helpers themselves trusted too much?
- does `SHA256SUMS` cover only canonical Window25 probe while helpers rely only on Git tree?
- can helper behavior differ from live workflow behavior?

Replay/fuzz reviewer-owned cases independently.

## 12. Carry-forward frozen Core guarantees

Freshly run at minimum:
- full Core `tests/unit tests/integration tests/runtime tests/habitation` — 0 fail/error;
- Window20 A/B canonical probes — 4/0 and 7/0;
- Window17 canonical probe — 14/0;
- Corrective-003 security set;
- real process loss / SIGKILL;
- clean non-editable wheel/headless;
- backup/restore/rebuild;
- writer/restart/FIX/current-time/SCALE.

Do not inherit author counts.

If reviewer environment differs from formal hosted environment, state:
`REVIEWER_ENVIRONMENT_DEVIATION`.

## 13. C15 downstream classification

Fresh real run and JUnit inspection.

Determine whether failures remain downstream operator compatibility debt rather than frozen Core regression.

Do not repair C15.
Do not restore local self-trust.

Expected historical class:
`C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT`

But independently adjudicate.

## 14. Open PR / contamination

Fresh inventory at least:
- #310 historical failed;
- #311 historical REVIEW_ONLY;
- #321 Window23 REVIEW_ONLY;
- #325 failed RC candidate;
- #328 Window25 REVIEW_ONLY;
- #330 current candidate;
- #326 closed duplicate;
- any new release/Core/C15 PR.

No unaccepted implementation enters frozen software.

## 15. Candidate immutability during review

Repeatedly verify PR #330 head remains:
`2380121639865b1bd29176cf944f5a20afe4112d`

If drift:
`CANDIDATE_DRIFT / REVALIDATION_REQUIRED`
Stop.

## 16. Review evidence publication

Publish independent evidence on separate:
`REVIEW_ONLY / DO NOT MERGE`
branch/PR.

Do not commit evidence to PR #330 branch.

Include:
- report;
- reviewer-owned classifier fuzz probes;
- TOCTOU reproduction/analysis;
- publisher fault probes;
- frozen probe hashes;
- raw outputs;
- environment;
- artifact audit;
- exact review commit/tree.

If no write capability:
preserve exact local commit and export exact git bundle + SHA-256.
Do not redo IA.

## 17. Verdict

PASS only if all three Window25 blockers are genuinely closed and no new false-green is found:

`ACCEPTANCE_PASS`
`blocker=0`
`READY_FOR_PM_INTEGRATION`

Do not merge.

FAIL:
`ACCEPTANCE_FAIL`
`blocker=N`
`CORRECTIVE_OR_ADJUDICATION_REQUIRED`

Every blocker:
- ID;
- severity;
- violated invariant;
- exact source/path;
- mechanical reproduction;
- expected;
- actual;
- why Window26 author tests missed it;
- independent reproducibility.

Do not repair.

## 18. Prohibited

Do not:
- modify PR #330;
- modify candidate branch;
- repair workflow;
- repair Core;
- repair C15;
- merge #330;
- merge review PRs;
- PM integrate;
- run Resident;
- enter evaluator;
- public release/tag;
- UI/hardware.

## 19. Final report

Report:
- fresh main;
- PR #330 state/head/parent/tree;
- construction/scope;
- frozen software identity/drift;
- historical RED reproduction;
- BLK-001 independent ruling;
- classifier fuzz results;
- BLK-002 credential ruling;
- terminal immutability + TOCTOU ruling;
- BLK-003 publisher ruling;
- exact-pin ruling;
- formal run/jobs/artifact;
- author-test vacuity audit;
- full Core/frozen probes/security/process-loss/headless/backup/restart results;
- C15 downstream ruling;
- contamination;
- candidate drift;
- exact review evidence publication;
- final verdict;
- blocker count.

Then stop.

DO NOT MERGE.
