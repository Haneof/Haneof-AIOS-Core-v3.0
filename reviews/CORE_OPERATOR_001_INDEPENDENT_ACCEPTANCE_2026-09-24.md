# CORE-OPERATOR-001 Independent Acceptance

Date: 2026-09-24  
Task: `CORE-OPERATOR-001-INDEPENDENT-ACCEPTANCE`  
Role: Independent Test Infrastructure Acceptance Reviewer  
Reviewed repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Reviewed candidate: PR #131  
Final verdict: **ACCEPTANCE_PASS**

This review is acceptance-only. It does not modify PR #131, does not modify Core, does not execute a Resident, and does not merge the candidate.

## 1. Review baseline

- Review-time live `main`: `27135e39d5123d079e065c8ddfbcb23b2a3e37c8`.
- PR #131 construction/base SHA: `c8807876ba62a4f4180beba8ff974e2342786340`.
- PR #131 base ref: `main`.
- PR #131 head branch: `core-operator-001-20260924`.
- Reviewed exact candidate head: `0e1d69eebc801278f93ccc1941b8f066a4ea09ef`.
- Candidate state at review: OPEN / UNMERGED / mergeable.
- Candidate commits: 3.
- Candidate changed files: 26.
- Candidate reviews before this report: 0.
- Candidate comments before this report: 0.
- Source WIP: PR #125 exact head `b14b5d84b6a4c843dc7dc38cde51f08a92fac86b`.

The review began while `main` was still `c8807876...`. During review, `main` advanced by 10 commits to `27135e39...`. I therefore re-ran the baseline comparison before issuing this verdict. The `c8807876... -> 27135e39...` change set contains only governance / project-map / review-report files:

- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/AIOS_CORE_GAP_DISPATCH_2026-09-24.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- three `CORE_GAP_FIX` prompts
- `reviews/CORE_GAP_AUDIT_001_2026-09-24.md`

It contains no `src/aios_core/**`, no `tests/**`, no `tools/c15_preflight/**`, and no PR #131 workflow path. There is therefore no file-scope conflict or semantic Core drift introduced by the review-time main advance. The current task board/checkpoint explicitly keep PR #131 in `GATE / REVIEW_READY` pending this independent review.

CI environment used by the candidate gates:
- GitHub-hosted Ubuntu 24.04
- CPython 3.12.14
- pytest 8.4.2
- Pydantic 2.13.5

## 2. Scope verification

### Candidate scope

Base `c8807876...` to exact head `0e1d69ee...` changes exactly 26 files, all under:

- `.github/workflows/c15-operator-preflight.yml`
- `tests/preflight/**`
- `tools/c15_preflight/**`

### Core ZERO DIFF

**PASS.**

There is no `src/aios_core/**` file in the PR diff. The exact-head operator workflow also ran:

`git diff --exit-code c8807876ba62a4f4180beba8ff974e2342786340 HEAD -- src/aios_core`

and the step succeeded.

The same workflow also confirmed no candidate delta under `reviews/internal_habitation` relative to its construction base.

No fixture file, historical Resident evidence, private World, sealed future, or historical World artifact is changed by PR #131.

### Selective provenance from PR #125

**PASS.**

All 26 candidate files were compared by blob identity against PR #125 exact head `b14b5d84...`.

- 24 / 26 candidate blobs are byte-for-byte identical to the same paths at PR #125 exact head.
- Only these two differ:
  1. `tools/c15_preflight/clock.py`
     - PR #125 blob: `d94d49c42fcd957f3738437c47dbfb2dd0f4d05d`
     - PR #131 blob: `fe9951c94b413544a44051a8c4b5169102946078`
  2. `.github/workflows/c15-operator-preflight.yml`
     - PR #125 blob: `a04cc36f1fc0c176a25d71e7ce1c1ae0c4727fca`
     - PR #131 blob: `b612512d82f2dbea50a6d48b0e058ff2421d841f`

PR #125's historical Core is not present in the PR #131 changed-file set. This is a selective port, not a whole-PR inheritance.

## 3. Before-fix reproduction verification

Reproduction commit: `3865da8816ccac48e3eda06f329a84f55e2d0bd6`.

It is the first PR #131 commit and is directly parented by construction main `c8807876...`.

### Reproduction CI

`c15-operator-preflight`
- run: `35955458275`
- job: `107492719208`
- run head SHA: `3865da8816ccac48e3eda06f329a84f55e2d0bd6`
- checkout ref: exact `3865da8816...`
- Python: 3.12.14
- conclusion: FAILURE

The raw job log independently shows exactly the three required failures:

1. `test_clock_reuses_existing_scheduler_at_intermediate_deadline_without_future_input`
   - verdict: **REPRODUCED**
   - actual: `periodic_reviews` was empty and indexing element 0 raised `IndexError`.
   - expected: T+24h Review occurs before the T+49h target.

2. `test_old_wake_cannot_see_future_input`
   - verdict: **REPRODUCED**
   - actual: the old Wake saw `SYNTHETIC event 1`.
   - expected: unreleased/un-ingested future input is not visible to old due work.

3. `test_budget_deferral_not_forced`
   - verdict: **REPRODUCED**
   - actual: `pre_ingest_wakes` was empty.
   - expected: the pre-ingest scheduler boundary exposes the Core disposition rather than silently losing/forcing the Wake.

The companion full regression:
- run: `35955458266`
- job: `107492719361`
- source run head: `3865da8816...`
- default PR checkout: generated merge commit of `3865da8816...` onto `c8807876...`
- command: `pytest -q`
- conclusion: FAILURE
- raw log shows the same three failures and no different blocker.

The reproduction requirement is independently satisfied.

## 4. Implementation review

### A. Scheduler reuse

**PASS.**

The candidate does not construct a second `CurrentCoreHabitationTarget`, World, index, or `FusedTurnRuntime`.

`ClockAdapter` inherits the existing habitation clock implementation, binds an `ObservedFacade` to the already-existing `RuntimeRecorder.runtime`, and calls `super().advance_to(instant)`.

The PR #125 implementation had bypassed that scheduler by manually setting the clock and returning empty due/review results; the candidate removes that bypass.

### B. Intermediate deadlines

**PASS.**

The inherited scheduler repeatedly selects the earliest due Task or Periodic Review not later than the requested target, advances to that tick, runs due work, then continues. A T0 -> T+49h advance therefore processes the T+24h deadline before reaching T+49h rather than jumping directly to the target and backfilling.

The exact regression verifies the first Periodic Review occurs at T+24h.

### C. Future isolation

**PASS for the operator boundary under review.**

`Driver.step()` ordering is:

1. reveal current event to the operator,
2. call `clock.advance_to(now)`,
3. only after due work returns, ingest the revealed event into World,
4. catch up index,
5. ACK,
6. process the current event.

`ClockAdapter.advance_to()` receives no event payload and uses the existing runtime/World only. Thus prior due work cannot observe the newly revealed event through World/index before ingest. The exact old-Wake regression confirms the previous leak is closed.

This is a rules/process-audit result, not a claim of technical hard isolation.

### D. Old pending Wake

**PASS.**

Pending non-user/non-periodic Wakes are dispatched by the inherited `_dispatch_pending_wakes()`, which re-reads the durable current Wake and calls normal Core `runtime.run_wake(...)`.

The candidate does not directly invoke a model, manufacture a Wake result, or directly mutate Wake state.

After inherited deadline processing, `ClockAdapter` performs one trailing pending-Wake pass before returning to `Driver`, still before the current event is ingested.

### E. Budget denial / deferral

**PASS.**

The operator delegates the disposition to Core and records the resulting state. It does not force completion, fabricate delivery, or manually rewrite the state.

Core semantics distinguish:
- non-hard Step-0/budget block -> `wake_bus.defer()` -> durable `QUEUED`;
- `HARD_DENY` -> `wake_bus.suppress()` -> durable `SUPPRESSED`.

The exact regression uses `HARD_DENY`; therefore its correct Core-native outcome is not “queued forever” but a durable non-completed suppression. The important operator regression is that this result is no longer silently omitted or force-completed. The candidate preserves that distinction.

### Related edge review

No new operator blocker was found in the requested surrounding cases.

Existing candidate tests cover, among other things:
- no pending Wake / normal no-op dispatch;
- intermediate deadline scheduling;
- clock regression rejection;
- duplicate reveal/ACK rejection;
- interrupted ACK and checkpoint-loss fail-closed behavior;
- restart routing and fresh-session constraints;
- deferred/budget-incomplete work not promoted to completion;
- Summary error blocking;
- exact request/reply binding;
- single-writer/WAL/freeze failure windows;
- trace write/flush/fsync poisoning;
- fixture activation denial;
- isolation result classification;
- normal Periodic Review / Summary / Wake paths.

The implementation also re-reads durable current Wake state before dispatch, so already completed/merged Wakes are not dispatched through that pending-Wake path.

## 5. Final Gate verification

### Exact-head operator gate

`c15-operator-preflight`
- run: `35955695487`
- job: `107493434789`
- run head: `0e1d69eebc801278f93ccc1941b8f066a4ea09ef`
- explicit checkout ref: exact same SHA
- Python: 3.12.14
- conclusion: SUCCESS

Independent raw-log receipts:
- exact three regressions: **3 tests / 0 failures / 0 errors / 0 skipped**
- all `tests/preflight/**`: **131 / 0 / 0 / 0**
- related Core regressions: **146 / 0 / 0 / 0**
- receipt assertion: `event_head_sha == tested_sha == 0e1d69e...`
- Core zero-diff step: SUCCESS
- internal habitation evidence zero-diff step: SUCCESS

The workflow contains no `|| true`, no failure swallowing, no fixed historical candidate checkout, and no Resident/provider invocation.

### Full regression

`p16-convergence-gate`
- run: `35955695492`
- job: `107493434777`
- source run head: `0e1d69eebc801278f93ccc1941b8f066a4ea09ef`
- command in workflow: exactly `pytest -q`
- conclusion: SUCCESS

This workflow uses GitHub's default PR merge checkout rather than the exact-head checkout. The generated merge commit was `ee401e9bb97f2aed0b15cf54627f41e5b53f7156`. Its tree SHA is `b9380852f11bac4dd76eb443e9d1deba1acedcc0`, exactly equal to the candidate head tree SHA, because the then-current base was the candidate construction base. Therefore the full suite tested the same file tree.

The quiet pytest log reached 100% with **632 dot/pass markers** and no failure/error/skip markers. The job succeeded. The workflow itself was independently inspected and is not a narrowed test list: the gate command is plain `pytest -q`.

The later review-time main advance to `27135e39...` changes governance/review documents only, so it does not invalidate these software test results.

## 6. Boundary verification

**PASS.**

- NO RESIDENT EXECUTED.
- No Resident A/B/C semantic evaluation was run.
- Synthetic/scripted mechanics are not described as Resident cognition or C15/B semantic PASS.
- Real fixture activation is blocked by the preflight driver by default.
- No sealed future was read for this acceptance.
- No historical Resident evidence was rewritten.
- No private World was modified.
- No provider run was performed.
- No hard-isolation claim is made.
- `isolation_probe` explicitly labels itself synthetic, reports real resources as NOT_TESTED, Resident Arena isolation as BLOCKED, and `launchable=false`.
- Owner-selected protocol remains **rules constraints + process audit**.

Because the connected GitHub identity is the same repository account that authored PR #131, this review does not manufacture a GitHub `APPROVE` event. This review-only report PR is the independent-model acceptance evidence.

## 7. Findings

### Blockers

**None.**

Blocker count: **0**.

### Non-blocking observations

1. The full-suite workflow checks the PR merge ref, not exact head; however its tested tree SHA was independently verified equal to the exact candidate tree. Exact-head binding is separately enforced by `c15-operator-preflight`.
2. The budget regression's fixture uses `HARD_DENY`, whose Core-native outcome is `SUPPRESSED`, while ordinary non-hard deferral remains `QUEUED`. The candidate correctly preserves Core's distinction and does not force-complete either path.
3. The review-time main advanced after candidate CI, but only in disjoint governance/review files; no rebase-triggered software revalidation is required for this acceptance finding. PM should still confirm the exact candidate head has not changed at integration time.

## 8. Final verdict

# ACCEPTANCE_PASS

All required historical failures are independently confirmed, the candidate closes them through the intended operator mechanism, Core is ZERO DIFF, selective provenance is valid, candidate CI is valid, no Resident/evidence/fixture boundary is crossed, and no new operator blocker was found.

**PR #131 exact candidate is independently accepted for PM integration.**

Do not treat this report as authorization to run Resident A/B/C. PM integration of PR #131 and downstream task-state changes remain separate actions.
