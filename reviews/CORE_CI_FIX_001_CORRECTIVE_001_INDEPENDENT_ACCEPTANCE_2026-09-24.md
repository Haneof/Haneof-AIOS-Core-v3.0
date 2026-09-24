# CORE-CI-FIX-001-CORRECTIVE-001 Independent Acceptance — 2026-09-24

Task: `CORE-CI-FIX-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`  
Role: Independent Release / CI Infrastructure Acceptance Reviewer  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Reviewed PR: #146 — `CORE-CI-FIX-001: make Core-diff guards branch-shape independent`

## Final verdict

**ACCEPTANCE_PASS**

Blocker count: **0**

PR #146 corrected exact candidate is independently accepted for PM integration.

This verdict applies only to exact candidate:

`1eb24e101cdb1579c22c69b435cf9f79a3c359ad`

It does not rewrite the prior failed acceptance. The historical report
`reviews/CORE_CI_FIX_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`
remains an `ACCEPTANCE_FAIL` record for exact failed head
`1896b3e5257bd0eaea990f2b7a656e9747d899ba` and blocker
`CORE-CI-FIX-001-ACCEPT-BLOCKER-001`.

---

## 1. Review pins

- review-time live `main`: `f8eb271453b12c3896cd55381b8bdb8dc5da5632`
- reviewed PR: **#146**
- PR state at final pin: **OPEN**
- merged: **false**
- draft: **false**
- GitHub mergeable field at final pin: **false**
- base branch: `main`
- PR-reported base SHA: `6018041972c36e60cb1d6fd3bb52353c449b9a4f`
- branch: `core-ci-fix-001-20260924-sol`
- reviewed exact head: `1eb24e101cdb1579c22c69b435cf9f79a3c359ad`
- commits: **8**
- changed files: **3**
- previous failed head: `1896b3e5257bd0eaea990f2b7a656e9747d899ba`
- historical blocker: `CORE-CI-FIX-001-ACCEPT-BLOCKER-001`

At the final status read, the task board still explicitly records:

`CORE-CI-FIX-001-CORRECTIVE-001 = GATE / REVIEW_READY`

and identifies PR #146 @ `1eb24e10...` as the corrective candidate awaiting a new independent reviewer.

---

## 2. Required source review

Read and applied:

1. `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
2. `AIOS_v3.0_CURRENT_CHECKPOINT.md`
3. `PROJECT_MASTER_MAP.md`
4. `governance/AIOS_CORE_CI_FINDING_001_2026-09-24.md`
5. `governance/prompts/CORE_CI_FIX_001_2026-09-24.md`
6. `governance/prompts/CORE_CI_FIX_001_CORRECTIVE_001_2026-09-24.md`
7. `reviews/CORE_CI_FIX_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

The historical acceptance failure was preserved as evidence and was not edited, superseded, or described as a false alarm.

---

## 3. Original shallow / branch-shape defect remains independently confirmed

Historical PR-shaped head:

`e812184c0887d6ec7fefd330a72d368c6a927400`

### C14 semantic repair

- run: `35956667890`
- job: `107496347623`

Raw log independently rechecked:

- `git fetch origin main --depth=1`
- `changed="$(git diff --name-only origin/main...HEAD)"`
- `fatal: origin/main...HEAD: no merge base`
- exit **128**

### C15 RCC

- run: `35956667966`
- job: `107496347628`

Raw log independently rechecked the same failure class:

- depth-1 main fetch
- three-dot `origin/main...HEAD`
- no merge base
- exit **128**

No invariant-rejection message was emitted in either historical failure.

Verdict: **the original defect class is real and remains the defect that the branch-shape correction must close.**

---

## 4. Corrective candidate scope

Corrective construction baseline:

`6018041972c36e60cb1d6fd3bb52353c449b9a4f`

Candidate:

`1eb24e101cdb1579c22c69b435cf9f79a3c359ad`

Independent compare:

- status: **ahead**
- ahead by: **8**
- behind by: **0**
- merge base: `6018041972c36e60cb1d6fd3bb52353c449b9a4f`

Changed files are exactly:

1. `.github/workflows/c14-resident-fixture-v2.yml`
2. `.github/workflows/c14-semantic-repair-fixture.yml`
3. `.github/workflows/c15-rcc-fixture.yml`

Therefore the final candidate has zero diff under:

- `src/**`
- `tests/**`
- `tools/**`
- `governance/**`
- `reviews/**`

and no fixture, historical evidence, Resident data, World, or Core runtime file is changed by the candidate.

---

## 5. Corrective mechanism review — six predicates complete

The previous failed exact head contains six protected-path predicates implemented as:

`printf ... | grep -q ...`

The corrected exact head contains **zero** remaining `printf ... | grep -q` protected predicates in the three guards.

### C14 resident fixture — 3/3 corrected

`.github/workflows/c14-resident-fixture-v2.yml`

1. `^src/aios_core/`
2. `^reviews/internal_habitation/c14-resident/v2/runs/resident-a-restart-20260921/`
3. `^reviews/internal_habitation/c14-resident/v2/fixture/sealed_fixture.json$`

All three now use non-pipe here-string input:

`grep -q PATTERN <<<"$changed"`

### C14 semantic repair — 2/2 corrected

`.github/workflows/c14-semantic-repair-fixture.yml`

1. `^src/aios_core/`
2. `^reviews/internal_habitation/c14-resident/v2/`

Both use non-pipe here-string input.

### C15 RCC — 1/1 corrected

`.github/workflows/c15-rcc-fixture.yml`

1. `^src/aios_core/`

It uses non-pipe here-string input.

Total: **6/6 corrected, 0 residual protected-path pipe predicates.**

The corrective did not redesign the branch-shape mechanism.

Preserved semantics:

- pull-request path reads event-pinned `github.event.pull_request.base.sha`;
- PR path does not require a local shallow three-dot merge base;
- workflow-dispatch path detects shallow checkout;
- workflow-dispatch unshallows when required;
- workflow-dispatch fetches live main;
- workflow-dispatch computes explicit `git merge-base origin/main HEAD`;
- evaluation failure emits `Guard could not be evaluated` and exits **2**;
- invariant rejection emits `Invariant rejected` and exits **1**;
- normal accept exits **0**;
- no `continue-on-error` or `|| true` was introduced into the guards.

---

## 6. Independent reproduction of historical blocker-001

The failed candidate's exact predicate form was independently re-created with:

- `set -euo pipefail`;
- protected Core path near the beginning of `changed`;
- 200 long trailing paths;
- changed-list size: **126,662 bytes**.

Direct isolated old pipeline status:

**141**

This is the expected SIGPIPE / `pipefail` failure class.

### Old predicate, five repeated trials

Exact control-flow class:

`if printf '%s\n' "$changed" | grep -q '^src/aios_core/'; then ... fi`

Observed five times:

- `GUARD_PASSED`
- exit **0**

Result: **5/5 fail-open reproductions.**

Historical blocker verdict: **CONFIRMED REAL.**

---

## 7. Independent large-list corrective regression

The same changed list was tested against the corrected predicate:

`if grep -q '^src/aios_core/' <<<"$changed"; then ... fi`

Five repeated trials all produced:

- `Invariant rejected`
- exit **1**

Result: **5/5 correct rejection.**

No false negative occurred.

Large-list corrective verdict: **PASS.**

---

## 8. All protected invariants and added adversarial probes

The independent review did not limit testing to the Core path.

### C14 Resident frozen Resident-A evidence

Large list, protected evidence path placed early:

`reviews/internal_habitation/c14-resident/v2/runs/resident-a-restart-20260921/_probe.json`

Observed:

- `Invariant rejected: frozen Resident-A evidence`
- exit **1**

### C14 Resident sealed fixture exact path

Large list, exact sealed fixture path placed first:

`reviews/internal_habitation/c14-resident/v2/fixture/sealed_fixture.json`

Repeated three times:

- `Invariant rejected: sealed fixture bytes`
- exit **1**

Result: **3/3 correct rejection.**

### C14 semantic frozen v2 evidence / fixture path

Large list, frozen v2 path placed early:

`reviews/internal_habitation/c14-resident/v2/fixture/_probe.json`

Observed:

- `Invariant rejected: frozen v2 evidence`
- exit **1**

### Multiple protected paths in one changed list

The changed list contained multiple protected paths with Core first and a large trailing list.

Observed:

- `Invariant rejected: core`
- exit **1**

Protected-invariant adversarial verdict: **PASS.**

No tested protected predicate failed open.

---

## 9. Corrective large-list Core negative probe — real Actions

Temporary probe exact head:

`f9f3adaa29dba1cbc62aeac492d06790b4f45838`

The commit included a deliberate:

`src/aios_core/_core_ci_fix_001_corrective_negative_probe.txt`

plus 200 long trailing temporary paths.

### C14 resident fixture

- run: `35963477813`
- job: `107516841172`
- guard: `Confirm no Core or Resident-A evidence changes`
- job conclusion: **failure**
- guard step conclusion: **failure**
- log shows corrected here-string predicate
- log shows `Invariant rejected: ... src/aios_core/**`
- process exit: **1**

### C14 semantic repair

- run: `35963477836`
- job: `107516841235`
- guard: `Prove fixture task did not modify Core or historical C14 evidence`
- job conclusion: **failure**
- guard step conclusion: **failure**
- log shows corrected here-string predicate
- log shows `Invariant rejected: ... src/aios_core/**`
- process exit: **1**

### C15 RCC

- run: `35963477878`
- job: `107516841457`
- guard: `Prove fixture task has zero Core diff`
- job conclusion: **failure**
- guard step conclusion: **failure**
- log shows corrected here-string predicate
- log shows `Invariant rejected: ... src/aios_core/**`
- process exit: **1**

All preceding substantive steps in each inspected job completed successfully before the guard rejection.

The negative failures therefore came from the protected-path invariant, not an unrelated setup/test failure.

Final candidate baseline-to-head compare contains only the three workflow files, proving that the Core probe and trailing temporary paths are absent from the final candidate.

Negative probe verdict: **PASS.**

---

## 10. Positive branch-shape proof

Corrected verification head:

`c50d0827ea3b733822c5c2b4d820624936740b4a`

Current independent graph check confirms:

- status: **diverged**
- current-main comparison: ahead **1**, behind **62** at the time checked
- true merge base: `bc4bf735e15c5c0787fdc533fe3f10d0e17fdac3`
- branch-side changed files: only the same three workflows

This is a valid divergent branch shape in the original defect class.

The original implementation's defect class is independently tied to the historical exit-128 raw logs in section 3.

### Positive runs

C14 resident:

- run `35963614359`
- job `107517254868`
- guard step: completed / success

C14 semantic:

- run `35963614377`
- job `107517255048`
- guard step: completed / success

C15:

- run `35963614369`
- job `107517255177`
- guard step: completed / success

All three logs show the actual guard script executing.

All three logs show:

`Guard evaluated against PR base 6018041972c36e60cb1d6fd3bb52353c449b9a4f`

No guard step was skipped.

No `continue-on-error` was present.

Positive branch-shape verdict: **PASS.**

---

## 11. Final exact-head Gate

Reviewed exact head:

`1eb24e101cdb1579c22c69b435cf9f79a3c359ad`

The workflow-run API was queried by this exact commit and returned all three required runs as completed / success.

### C14 resident

- run: `35963746859`
- job: `107517673782`
- workflow: `c14-resident-fixture-v2`
- run: completed / success
- guard step: completed / success
- checkout log: synthetic merge of `1eb24e10...` into `60180419...`
- guard log: `Guard evaluated against PR base 6018041972c36e60cb1d6fd3bb52353c449b9a4f`

### C14 semantic

- run: `35963746913`
- job: `107517673795`
- workflow: `c14-semantic-repair-fixture`
- run: completed / success
- guard step: completed / success
- checkout log: synthetic merge of `1eb24e10...` into `60180419...`
- guard log: `Guard evaluated against PR base 6018041972c36e60cb1d6fd3bb52353c449b9a4f`

### C15

- run: `35963746718`
- job: `107517672817`
- workflow: `c15-rcc-fixture`
- run: completed / success
- guard step: completed / success
- checkout log: synthetic merge of `1eb24e10...` into `60180419...`
- guard log: `Guard evaluated against PR base 6018041972c36e60cb1d6fd3bb52353c449b9a4f`

Final exact-head Gate verdict: **3/3 PASS.**

No guard was skipped and no guard failure was swallowed.

---

## 12. Current-main compatibility and mergeability field

The review began while main was moving and therefore repeatedly refreshed live state.

Final review-time main pinned for the completed acceptance:

`f8eb271453b12c3896cd55381b8bdb8dc5da5632`

Relative to corrective baseline `6018041972...`, live main had advanced by **17** commits at the final compatibility check.

Those main-side changes included:

- task-board/checkpoint/master-map state changes;
- independent FIX-002 acceptance evidence;
- accepted/integrated CORE-GAP-FIX-002 Core/runtime and test changes;
- post-FIX-002 governance/writeback material through `f8eb2714...`.

Critically, the baseline-to-current-main file survey found:

- **no `.github/workflows/**` changes**;
- **no changes to any of the three candidate workflow files**;
- no competing CI-guard implementation.

PR #146 remains reported as exactly **3 changed files**, the three workflow files listed in section 4.

The PR API's `mergeable` boolean was **false** at the final pin after main advanced. This report does not treat that boolean alone as proof of a content conflict. The actual path comparison shows candidate-side changes are confined to the three workflows, while current-main advancement does not touch those workflows. No content-level overlap requiring a candidate code change was found.

Therefore current-main advancement does not invalidate the corrective mechanism or exact-head acceptance evidence.

Current-main compatibility verdict: **PASS for PM integration of this exact corrective candidate.**

Normal PM integration should still preserve the repository's ordinary post-integration CI verification; this acceptance does not merge the PR and does not rewrite current project state.

---

## 13. Acceptance matrix

- task state allowed review: **PASS**
- PR #146 OPEN / UNMERGED / ready-for-review: **PASS**
- exact head unchanged: **PASS**
- historical FAIL preserved: **PASS**
- original exit-128 defect independently reconfirmed: **PASS**
- branch-shape mechanism preserved: **PASS**
- workflow-dispatch unshallow + explicit merge-base preserved: **PASS**
- evaluation failure exit 2 preserved: **PASS**
- invariant rejection exit 1 preserved: **PASS**
- normal accept exit 0 preserved: **PASS**
- six protected predicates converted: **6/6 PASS**
- residual `printf | grep -q` protected predicate: **0**
- old blocker independent reproduction: **PASS**
- direct old pipeline status 141: **CONFIRMED**
- large-list corrective repeat: **5/5 PASS**
- real large-list Core negative Actions probe: **3/3 PASS**
- non-Core protected invariants: **PASS**
- added adversarial probes: **PASS**
- positive divergent branch-shape Actions proof: **3/3 PASS**
- final exact-head Gate: **3/3 PASS**
- final candidate scope: **PASS**
- current-main workflow compatibility: **PASS**
- new blockers: **0**

---

## 14. Final decision

**ACCEPTANCE_PASS**

Blocker count: **0**

The prior blocker `CORE-CI-FIX-001-ACCEPT-BLOCKER-001` is independently reproduced on the failed predicate and independently closed by the corrected non-pipe predicates on exact head `1eb24e101cdb1579c22c69b435cf9f79a3c359ad`.

The original shallow / branch-shape defect remains closed, all six protected-path predicates retain fail-closed invariant behavior in the tested adversarial cases, the real negative probes reject with exit 1, the positive divergent branch proof passes, and all three final exact-head gates are green with their guard steps actually executed.

**PR #146 corrected exact candidate is independently accepted for PM integration.**

This review does not merge PR #146 and does not update the task board or checkpoint.
