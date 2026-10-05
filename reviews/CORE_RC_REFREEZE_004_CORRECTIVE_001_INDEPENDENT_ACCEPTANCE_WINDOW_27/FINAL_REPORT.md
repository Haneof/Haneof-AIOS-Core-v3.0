# Window 27 Fresh Independent Acceptance — FINAL REPORT

Task: `CORE-RC-REFREEZE-004-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`  
Candidate: PR #330 exact `2380121639865b1bd29176cf944f5a20afe4112d`  
Evidence PR: #333 — REVIEW_ONLY / DO NOT MERGE

## Verdict

`ACCEPTANCE_FAIL / blocker=2`  
`CORRECTIVE_OR_ADJUDICATION_REQUIRED`  
`DO NOT MERGE`

IA25-BLK-001 is not closed. IA25-BLK-002 is not closed because the full-run immutability invariant still has a mechanically reproducible TOCTOU false-green. IA25-BLK-003 is closed.

No repair was performed. PR #330 and its branch were not modified.

## Fresh ground truth

Fresh main: `5fc78a84d0cf1ccdfe0185ba2cc2f8c7fdeff5c4`.

The task board, checkpoint, Window 25 adjudication, Window 27 release, and Window 27 prompt were read fresh and the task was confirmed `READY`.

The initial reviewer sandbox could not resolve github.com for a direct shell fetch, so no local-shell fetch success is claimed. Fresh refs/objects were obtained through the connected GitHub API, and reviewer-owned GitHub-hosted workflows independently executed real `git fetch --all --prune` before their checks.

## Exact candidate / construction / scope

PR #330 remained OPEN, non-draft, UNMERGED:
- branch `release/core-rc-refreeze-004-corrective-001-window26`
- head `2380121639865b1bd29176cf944f5a20afe4112d`
- parent `04c37f7dd8ba6f20e1c67dad43c0f21087f51eeb`
- tree `72d3cd0da849fae3b1cbfdfb7ae995528e1cfd71`

Fresh ancestry:
`70134269ddfc7c80c4a703a933253bd099746504 -> 04c37f7dd8ba6f20e1c67dad43c0f21087f51eeb -> 2380121639865b1bd29176cf944f5a20afe4112d`.

Failed candidate -> corrective candidate = ahead_by 2 / behind_by 0.

Corrective delta is confined to the RC004 formal workflow and `reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/**`. No Window 26 delta exists in `src/**`, product `tests/**`, `tools/**`, `pyproject.toml`, C15 implementation, or Resident evidence/state.

## Frozen identity / protected drift

Frozen software:
- commit `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`
- root tree `70b2711258567863ea0d93025a6a07e39631726a`
- Core tree `16f1487e291b009c55bee402abfd79fdacbae960`
- tests tree `9db1bfa08143bc99fe03836e2752ee6e05694eb6`
- workflows tree `72cde9d2dc2b35d071bfa36c954dac2faff4a803`
- pyproject blob `b38833c7537fa60d5c2f02ed4bb19158d8995a11`

Frozen -> current main is 24 ahead / 0 behind. Fresh diff is governance/checkpoint/prompt only; no protected product/test/workflow/packaging drift was found.

## Historical RED

Canonical Window 25 probe from `ffa6475fe4dde4b5d06b09a629b059b89f1ff434`:
- blob `c8a9050819440cc10605b08c943d29827f2b76c5`
- SHA-256 `fc7df49fdc80b340d2ddc065ad87c01c81987bef78f13fd6494ab035613796a9`

Identity matched before execution.

Reproduced:
- BLK-001: pytest rc=4, zero normal failed tests, old classifier false-greened.
- BLK-002: old write-bearing test job / persisted checkout credential / no terminal remote-head recheck.
- BLK-003: old HTTP 401 publisher logic exited 0.

## IA25-BLK-001 — NOT CLOSED

Fresh real C15 on Python 3.12.14 / pytest 8.4.2:
`78 tests / 45 failed / 33 passed / 0 errors / rc=1`.

Reviewer-owned real-JUnit audit found all 45 structured failures canonically under `tests/c15_persistence/**`. So the actual current C15 RED remains operator adaptation debt, not a frozen Core regression.

But mandatory independent fuzz found six false-accepts in exact candidate `c15_junit_classifier.py`:
1. namespaced rc0 document containing a structured failure;
2. rc1 failing testcase with summary failures=0;
3. one testcase containing both failure and error;
4. `tests/c15_persistence/../integration/test_core.py` traversal;
5. classname-only downstream spoof;
6. file/classname conflict where file appears downstream and classname identifies integration/Core.

Exact mapper chooses `file` first, does not canonicalize traversal, ignores conflicting classname when file exists, is namespace-unaware, and accepts raw downstream-prefix membership.

Expected: ambiguous/non-canonical/inconsistent structured JUnit fails closed.  
Actual: classifier returns 0/downstream GREEN for six mandatory adversarial cases.

Author ten-case self-test lacks namespace, traversal/canonicalization, summary consistency, dual failure/error, and conflicting source-identity cases.

`IA25-BLK-001 = NOT CLOSED`.

## IA25-BLK-002 credential isolation — PASS sub-property

Job A is read-only and checkout uses `persist-credentials: false`.

Reviewer-hosted probe found no persisted checkout extraheader and no usable global/system credential helper. A real write attempt with the deliberately step-local read token returned HTTP 403: `Resource not accessible by integration`.

The open-PR inventory token is step-local and is not passed into repository-owned tests/helpers.

## IA25-BLK-002 terminal immutability / TOCTOU — NOT CLOSED

Exact workflow:
- terminal gate: lines 441-479
- artifact upload: 481-487
- write-capable publisher Job B: 490-528

Job A checks canonical remote head at lines 446-447. Job B performs no fresh canonical remote-head recheck.

Formal run timing:
- terminal 16:53:03Z -> 16:53:04Z
- artifact upload 16:53:04Z -> 16:53:06Z
- Job A complete 16:53:09Z
- Job B starts 16:53:11Z
- publisher 16:53:12Z -> 16:53:13Z

Independent exact-workflow reproduction:

```
terminal_before_upload=True
publisher_remote_recheck=false
terminal_pass=True
remote_after_terminal=deadbeefdeadbeefdeadbeefdeadbeefdeadbeef
job_a_success_after_drift=True
job_b_runs_after_drift=True
publisher_success_after_drift=True
overall_success_after_drift=True
TOCTOU_FALSE_GREEN_REPRODUCED=YES
```

A canonical branch can drift after Job A terminal check while the old run still finishes overall SUCCESS and publishes an old-SHA pin. This violates the binding whole-run immutability invariant.

`IA25-BLK-002 = NOT CLOSED`.

## IA25-BLK-003 — CLOSED

Independent publisher matrix:
- only HTTP 201 succeeds;
- 200/202/204/301/302/400/401/403/404/409/422/429/500 fail;
- curl transport failure, empty response and invalid response fail.

The command substitution does not mask curl nonzero.

Job B requires Job A success, has no checkout, executes no candidate script/test/helper, and exact shell exposes only the mandatory commit-comment POST. No refs mutation, push, contents write, tag/release, dispatch, branch deletion or PR mutation path was found.

`IA25-BLK-003 = CLOSED`.

## Exact pin / formal run / artifact

Formal run `37217853558`:
- push event
- exact head `2380121639865b1bd29176cf944f5a20afe4112d`
- overall SUCCESS
- Job A SUCCESS
- Job B SUCCESS

Exactly one candidate commit comment exists: `203380647`, created `2026-10-04T16:53:13Z`, binding correct task/run/candidate/frozen software/gate success.

Formal artifact `11309495093`:
- server/local SHA-256 `02415a0457af3aec5cb50d5195120202aae2c9cb23d3c81cbefaf867b7d216e0`
- bytes downloaded and inspected
- internal runtime hash index: 32 entries / 0 mismatches
- Core JUnit: 928 / 0 fail / 0 error
- C15 JUnit: 78 / 45 fail / 0 error

## Author-helper vacuity

`workflow_security_static_probe.py` checks marker/string presence and Job A ordering, but not a publisher-side canonical-head recheck. Thus exact candidate can report `WORKFLOW_SECURITY_STATIC=PASS` while independent reviewer reproduces `TOCTOU_FALSE_GREEN_REPRODUCED=YES`.

Classifier self-test similarly omits the six adversarial false-accept classes.

## Fresh carry-forward

Reviewer run `37263834603` SUCCESS:
- Python 3.12.14 / pydantic 2.13.5 / pytest 8.4.2
- `aios_core.__file__=/home/runner/work/_temp/frozen/src/aios_core/__init__.py`
- full Core: `928 passed`
- trusted-return security: `214 passed`
- real process-loss/SIGKILL: `9 passed`
- clean wheel/headless: `HEADLESS_CLEAN_INSTALL_PASS`
- backup/restore: `BACKUP_RESTORE_ROUTE_B_PASS`
- writer/restart/FIX/current-time/SCALE: `52 passed`
- C15: `45 failed, 33 passed, rc=1`
- independent real JUnit: `REVIEWER_C15_REAL_JUNIT_ALL_DOWNSTREAM=PASS`

Backup/restore verified receipt/handoff continuity, exact winning-proof retry, conflict refusal, forged-local refusal, zero provider redispatch, exactly one capability side effect, and no trust-authority expansion.

## Frozen reviewer probes

Reviewer run `37263834686` SUCCESS:
- W20 A SHA-256 `ec1dc5c2c5406d5d9e74825f62e0a17fb80f8ebd6dc250817fa048511ce292b5` -> 4/0
- W20 B `769242465817f31734661ba7ba9c3d5f7d06b8d3f5235d72d2026956d9b98eb1` -> 7/0
- W17 `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3` -> 14/0

## C15 downstream

Fresh ruling remains `C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT`.

No C15 repair, local-self-trust restoration or Resident run occurred.

## Contamination / drift

Relevant inventory included #310, #311, #321, #325, #326 closed duplicate, #328, #330, concurrent review-only #332, and this #333. #332 was not trusted or consumed. No open PR content was counted into frozen software.

Entry/mid/final checks kept the candidate at `2380121639865b1bd29176cf944f5a20afe4112d`; no candidate drift occurred.

## Independent evidence

Evidence base before final publication: `d31633a8424cd7ab39be89cc087109216ab55e6a`.

Runs:
- gate attack `37263834648` SUCCESS
- frozen probes `37263834686` SUCCESS
- Core/carry-forward `37263834603` SUCCESS

Artifacts, all downloaded and locally hash-matched:
- gate `11326130132`: `0e26d296a3bd554eaeef32e4f938e777d1d7301cd2956b5e911c562a292ab01a`
- frozen probes `11325900599`: `315e60dbb8327eca240bf7645cbdf90eb35af74c019d7f8ce0d93aa8e754c7a3`
- Core `11326130664`: `f28239fee935988d17caa79f6ae8861d8969d10870b09efc6bc4c1caae5ec8f9`

Final publication commit/tree are recorded in the PR #333 identity comment after this commit.

## Blockers

### IA27-BLK-001 — IA25-BLK-001 closure false

Severity: BLOCKING / HIGH  
Invariant: rc/JUnit classification must fail closed and cannot treat ambiguous/non-canonical/inconsistent structured failure as downstream-only.  
Source: exact `reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/probes/c15_junit_classifier.py`.  
Repro: run `37263834648`, `reviewer_junit_fuzz.py`, six false-accepts.  
Expected: reject/nonzero.  
Actual: classifier 0/downstream GREEN.  
Why author tests missed: no namespace/traversal/summary-conflict/file-class conflict cases.  
Independent: yes, PR #333 + artifact `11326130132`.

### IA27-BLK-002 — IA25-BLK-002 closure false

Severity: BLOCKING / CRITICAL  
Invariant: candidate head/frozen boundary immutable throughout the formal run.  
Source: exact workflow terminal/upload/publisher sequence lines 441-528.  
Repro: run `37263834648`, `reviewer_toctou_probe.py`.  
Expected: post-terminal branch drift prevents old run success/publication.  
Actual: Job A success + Job B success + overall success; `TOCTOU_FALSE_GREEN_REPRODUCED=YES`.  
Why author tests missed: static helper checks Job A terminal marker, not publisher-boundary remote equality.  
Independent: yes, PR #333 + artifact `11326130132`.

## Stop state

`PUBLISHED_REVIEW_ONLY / PR #333 / DO NOT MERGE`  
`ACCEPTANCE_FAIL / blocker=2`  
`CORRECTIVE_OR_ADJUDICATION_REQUIRED`
