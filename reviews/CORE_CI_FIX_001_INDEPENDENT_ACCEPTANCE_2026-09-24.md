# CORE-CI-FIX-001 Independent Acceptance — 2026-09-24

Task: `CORE-CI-FIX-001-INDEPENDENT-ACCEPTANCE`  
Role: Independent Release / CI Infrastructure Acceptance Reviewer  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Reviewed PR: #146 — `CORE-CI-FIX-001: make Core-diff guards branch-shape independent`

## Final verdict

**ACCEPTANCE_FAIL**

Blocker count: **1**

The historical defect is real, PR #146 is correctly scoped, its branch-shape positive proofs are real, its deliberate Core-change negative probes are real, and all six inspected final exact-head runs are green on the pinned candidate. However, the exact candidate introduces a fail-open edge case in all three repaired guards: combining `set -o pipefail` with `printf ... | grep -q` can turn a real protected-path match into pipeline status 141 when the changed-file list is sufficiently large. Because the pipeline is used as an `if` condition, the guard then treats the protected-path match as false and can complete successfully.

That weakens the invariant and blocks integration of the exact candidate.

---

## 1. Review pins

- review-time live `main`: `fda1e28231dc6a33ead180003b407aaa5305665a`
- reviewed PR: **#146**
- PR state: **OPEN**
- merged: **false**
- reviewed exact head: `1896b3e5257bd0eaea990f2b7a656e9747d899ba`
- candidate construction main: `5ccb51c0bbcc11380887c60e8bfaa5c87f05c110`
- candidate branch: `core-ci-fix-001-20260924-sol`
- candidate commits: **3**
- candidate changed files: **3**
- PR comments observed: **none**
- PR reviews observed: **none**

The task board and checkpoint both state:

- `CORE-CI-FIX-001 = GATE / REVIEW_READY`
- PR #146 @ `1896b3e5...` is the **unique acceptance candidate**
- PR #144 is **SUPERSEDED / NOT INTEGRATED**

PR #144 was not accepted or re-reviewed as a candidate.

GitHub REST mergeability computation returned `mergeable=null`, `mergeable_state=unknown` during this review. This report does not claim merge clearance from that field. Current-main compatibility was instead checked directly by commit/file comparison below.

---

## 2. Required source review

Read on live main:

1. `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
2. `AIOS_v3.0_CURRENT_CHECKPOINT.md`
3. `governance/AIOS_CORE_CI_FINDING_001_2026-09-24.md`
4. `governance/prompts/CORE_CI_FIX_001_2026-09-24.md`
5. `PROJECT_MASTER_MAP.md`

The dispatched requirement is to eliminate the branch-shape/shallow-history dependence without weakening the protected-path invariant, and to distinguish evaluation failure from policy rejection.

---

## 3. Before-state reproduction verdict — CONFIRMED

### C14 semantic repair

- historical PR-shaped head: `e812184c0887d6ec7fefd330a72d368c6a927400`
- run: `35956667890`
- job: `107496347623`
- workflow: `c14-semantic-repair-fixture`
- event: `pull_request`
- run conclusion: **failure**

Raw log confirms:

- `git fetch origin main --depth=1`
- `changed="$(git diff --name-only origin/main...HEAD)"`
- `fatal: origin/main...HEAD: no merge base`
- `Process completed with exit code 128`

No invariant-rejection message was emitted.

### C15 RCC fixture

- historical PR-shaped head: `e812184c0887d6ec7fefd330a72d368c6a927400`
- run: `35956667966`
- job: `107496347628`
- workflow: `c15-rcc-fixture`
- event: `pull_request`
- run conclusion: **failure**

Raw log confirms the same command pair, the same `no merge base` fatal, and exit **128**.

### Before-state classification

**CONFIRMED: Git evaluation failure, not invariant violation.**

The historical red status was caused by inability to evaluate the three-dot diff after the depth-1 main fetch. A real policy rejection uses the workflow's explicit rejection path and exit 1.

---

## 4. Workflow survey — CONFIRMED COMPLETE

The construction baseline contains **36 files** under `.github/workflows/**`.

All 36 were independently scanned for the paired defect pattern:

- `git fetch origin main --depth=1`
- `origin/main...HEAD`

Exactly three occurrences were found:

1. `.github/workflows/c14-resident-fixture-v2.yml`
2. `.github/workflows/c14-semantic-repair-fixture.yml`
3. `.github/workflows/c15-rcc-fixture.yml`

No fourth occurrence was found.

The candidate changes exactly those three files.

---

## 5. Candidate scope — CONFIRMED

Construction-base-to-final-candidate compare:

- base: `5ccb51c0bbcc11380887c60e8bfaa5c87f05c110`
- head: `1896b3e5257bd0eaea990f2b7a656e9747d899ba`
- status: ahead
- ahead by: 3
- merge base: construction base itself

Changed files are exactly:

- `.github/workflows/c14-resident-fixture-v2.yml`
- `.github/workflows/c14-semantic-repair-fixture.yml`
- `.github/workflows/c15-rcc-fixture.yml`

Therefore final candidate has zero diff under:

- `src/**`
- `tests/**`
- `tools/**`
- `governance/**`
- `reviews/**`

No fixture, historical evidence, Resident data, World, or Core runtime file is present in the final candidate diff.

---

## 6. Implementation semantics review

### pull_request path

The candidate reads:

- `github.event_name`
- `github.event.pull_request.base.sha`

For pull-request events it:

1. rejects a missing PR base SHA with `Guard could not be evaluated` / exit 2;
2. checks whether that exact base commit exists;
3. fetches the exact base SHA if absent;
4. diffs `base.sha -> HEAD`;
5. rejects git-diff failure with exit 2.

The inspected final run checkout proves that `actions/checkout@v4` checked out the GitHub PR merge ref:

- checkout: `refs/remotes/pull/146/merge`
- synthetic merge HEAD: `5b41ea67`
- merge message: `Merge 1896b3e5... into 5ccb51c0...`

The same run used PR event base:

- `5ccb51c0bbcc11380887c60e8bfaa5c87f05c110`

Therefore `base.sha -> synthetic merge HEAD` correctly represents the PR-introduced tree delta for the inspected event and does not depend on a traversable local merge base.

### workflow_dispatch path

The candidate:

1. checks `git rev-parse --is-shallow-repository`;
2. unshallows if necessary;
3. fetches main;
4. computes `git merge-base origin/main HEAD`;
5. diffs merge-base to HEAD;
6. maps shallow-state/fetch/merge-base/diff failures to `Guard could not be evaluated` / exit 2.

No fixed future SHA is used. No previous-commit comparison is used.

No `continue-on-error` or `|| true` was introduced in the repaired guard logic.

### Intended error classification

The code explicitly intends:

- evaluation/git failure -> `Guard could not be evaluated` -> exit **2**
- invariant violation -> `Invariant rejected` -> exit **1**
- accepted invariant -> normal exit **0**

The blocker in section 11 shows that the policy-match implementation can nevertheless bypass the intended exit-1 path.

---

## 7. Positive branch-shape verdict — CONFIRMED

Verification head:

`ae30161a605c7121df94d9efa17d499a919c782c`

Independent compare against `5ccb51c0bbcc11380887c60e8bfaa5c87f05c110` confirms:

- status: **diverged**
- behind by: **34**
- ahead by: **1**
- real merge base: `bc4bf735e15c5c0787fdc533fe3f10d0e17fdac3`
- changed files: exactly the same three workflows

This is a valid branch shape for exercising the defect class.

Verified runs:

| Workflow | Run | Job | Head | Guard step | Result |
|---|---:|---:|---|---|---|
| c15-rcc-fixture | 35961737453 | 107511577848 | `ae30161a...` | Prove fixture task has zero Core diff | SUCCESS |
| c14-semantic-repair-fixture | 35961737477 | 107511578175 | `ae30161a...` | Prove fixture task did not modify Core or historical C14 evidence | SUCCESS |
| c14-resident-fixture-v2 | 35961737554 | 107511578415 | `ae30161a...` | Confirm no Core or Resident-A evidence changes | SUCCESS |

All three guard steps were `completed/success`, not skipped.

All three logs show actual guard execution against PR base `5ccb51c0...`.

Positive branch-shape verdict: **CONFIRMED**.

---

## 8. Negative Core probe verdict — CONFIRMED for the tested small changed list

Probe head:

`c9df5bd8f71656582e49026b73b827d56dd17658`

Construction-base-to-probe compare confirms the deliberate additional path:

`src/aios_core/_core_ci_fix_001_negative_probe.txt`

and the same three workflow changes.

Verified runs:

| Workflow | Run | Job | Head | Guard result |
|---|---:|---:|---|---|
| c15-rcc-fixture | 35961434053 | 107510648714 | `c9df5bd8...` | `Invariant rejected`, exit 1 |
| c14-semantic-repair-fixture | 35961434066 | 107510648583 | `c9df5bd8...` | `Invariant rejected`, exit 1 |
| c14-resident-fixture-v2 | 35961434085 | 107510648756 | `c9df5bd8...` | `Invariant rejected`, exit 1 |

All three failing jobs failed specifically at their guard step.

The final candidate compare contains only the three workflow files, so the probe file is not present in `1896b3e5...`.

Negative probe verdict: **CONFIRMED for the tested small changed-file set**.

It does not cover the large changed-list fail-open identified below.

---

## 9. Final exact-head Gate verdict — CONFIRMED GREEN

Reviewed exact head:

`1896b3e5257bd0eaea990f2b7a656e9747d899ba`

### First exact-head set

| Workflow | Run | Job | Head | Guard step |
|---|---:|---:|---|---|
| c15-rcc-fixture | 35961572756 | 107511080768 | `1896b3e5...` | completed / success |
| c14-semantic-repair-fixture | 35961572733 | 107511080789 | `1896b3e5...` | completed / success |
| c14-resident-fixture-v2 | 35961572823 | 107511081046 | `1896b3e5...` | completed / success |

### Repeated exact-head set

| Workflow | Run | Job | Head | Guard step |
|---|---:|---:|---|---|
| c15-rcc-fixture | 35961847741 | 107511909353 | `1896b3e5...` | completed / success |
| c14-semantic-repair-fixture | 35961847809 | 107511909576 | `1896b3e5...` | completed / success |
| c14-resident-fixture-v2 | 35961847815 | 107511909587 | `1896b3e5...` | completed / success |

Every inspected run:

- is a `pull_request` run;
- reports exact head `1896b3e5...`;
- is completed/success;
- actually executes the protected-path guard;
- is not skipped;
- logs `Guard evaluated against PR base 5ccb51c0...`;
- shows no hidden guard failure.

Final exact-head Gate evidence verdict: **CONFIRMED GREEN, but not sufficient for acceptance because of blocker 001**.

---

## 10. Current-main compatibility

Construction main -> review-time live main:

- base: `5ccb51c0bbcc11380887c60e8bfaa5c87f05c110`
- head: `fda1e28231dc6a33ead180003b407aaa5305665a`
- ahead by: **11**
- behind by: **0**
- merge base: construction main

Files changed between construction main and review-time main are limited to governance/project-state material:

- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/AIOS_CORE_GAP_DISPATCH_2026-09-24.md`
- `governance/AIOS_CORE_S2_PARALLELISM_RULING_2026-09-24.md`
- `governance/AIOS_CORE_S2_SERIALIZATION_RULING_2026-09-24.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`

No `.github/workflows/**` file changed.

Review-time live main vs candidate:

- status: diverged
- candidate ahead by: **3**
- candidate behind by: **11**
- merge base: `5ccb51c0bbcc11380887c60e8bfaa5c87f05c110`
- candidate-side changed files: exactly the three repaired workflows

Therefore live-main advancement did not invalidate the candidate by changing the same workflows.

---

## 11. Blocker

### Blocker ID

`CORE-CI-FIX-001-ACCEPT-BLOCKER-001`

### Title

**`pipefail` + `grep -q` can convert a real protected-path match into a false negative**

### Affected workflows

All three candidate-modified guards:

1. `.github/workflows/c14-resident-fixture-v2.yml`
2. `.github/workflows/c14-semantic-repair-fixture.yml`
3. `.github/workflows/c15-rcc-fixture.yml`

### Exact candidate construct

Each guard starts with:

`set -euo pipefail`

and policy tests remain of the form:

`if printf '%s\n' "$changed" | grep -q '^src/aios_core/'; then ... exit 1; fi`

The C14 resident/semantic guards use the same pipeline form for their other protected paths.

### Expected

If `changed` contains any path under `src/aios_core/**`, the guard must always enter the invariant-rejection branch and exit **1**, regardless of how many other paths are present.

### Actual

When the protected path is found early and enough additional changed-path bytes remain, `grep -q` exits immediately after the match. The upstream Bash `printf` can then receive SIGPIPE. Under `set -o pipefail`, the pipeline status becomes **141**, not 0.

Because the pipeline is the condition of an `if`, Bash does not terminate under `set -e`; it simply treats the condition as false. The invariant-rejection branch is skipped.

For the C15 guard, which has no later rejection check after the Core test, the script can then exit **0**.

The same false-negative mechanism exists in the C14 guards.

### Independent reproduction

Using the exact candidate control-flow shape:

```bash
set -euo pipefail

long="$(printf 'x%.0s' $(seq 1 200))"
changed="$(
  printf '.github/workflows/c15-rcc-fixture.yml\n'
  printf 'src/aios_core/_probe.txt\n'
  i=1
  while [ "$i" -le 100 ]; do
    printf 'zzzz/%s/%s/%s/%05d.txt\n' "$long" "$long" "$long" "$i"
    i=$((i+1))
  done
)"

if printf '%s\n' "$changed" | grep -q '^src/aios_core/'; then
  echo 'Invariant rejected: C15-RCC-FIXTURE-001 must not modify src/aios_core/**'
  exit 1
fi

echo 'GUARD_PASSED'
```

Observed result:

```text
GUARD_PASSED
```

A direct isolated pipeline check with the same data returns status **141**.

The issue is not limited to enormous PRs: the reproduction uses only 100 trailing paths, each built from valid 200-character path components.

### Why this blocks merge

The task explicitly requires that a real Core modification always be rejected and that the candidate not weaken the invariant.

The exact candidate can silently accept a changed list that contains `src/aios_core/**`. That is a policy false negative, not merely an infrastructure error and not merely missing evidence.

Therefore the exact candidate cannot be independently accepted for PM integration.

### Minimal corrective scope

Do not redesign the guard.

In the same three workflow files only, replace the pipe-producing policy matches with a form that cannot produce an upstream SIGPIPE under `pipefail`, for example a here-string/input-redirection form such as:

`if grep -q '^src/aios_core/' <<<"$changed"; then ... fi`

and equivalently for each other protected-path predicate.

Then re-run:

1. the deliberate Core negative probe;
2. the positive branch-shape case;
3. an explicit large changed-list / early-match regression that proves the protected-path match still exits 1;
4. all three final exact-head gates.

No Core, fixture, evidence, Resident, governance, or historical-result change is required.

---

## 12. Final acceptance decision

- before-fix exit 128: **CONFIRMED**
- root cause: **CONFIRMED**
- workflow survey: **CONFIRMED — 36 scanned, 3 occurrences**
- candidate scope: **CONFIRMED**
- PR-event base semantics: **ACCEPTABLE**
- workflow_dispatch merge-base semantics: **ACCEPTABLE by code review**
- intended evaluation-failure fail-closed handling: **PRESENT**
- small-list invariant rejection: **CONFIRMED**
- positive branch-shape proof: **CONFIRMED**
- negative Core probe: **CONFIRMED for its tested small changed list**
- probe removed from final candidate: **CONFIRMED**
- final exact-head gates: **6/6 inspected runs SUCCESS**
- current-main workflow compatibility: **CONFIRMED**
- new blockers: **1**

**Final verdict: ACCEPTANCE_FAIL**

PR #146 must remain unmerged until a dedicated corrective candidate removes `CORE-CI-FIX-001-ACCEPT-BLOCKER-001` and is independently revalidated.
