# CORE-CI-FIX-001-CORRECTIVE-001 — remove pipefail/grep-q fail-open

Repository: Haneof/Haneof-AIOS-Core-v3.0

Role: Release / CI Infrastructure Engineer.

You are continuing the same CORE-CI-FIX-001 engineering task after independent acceptance failure.
You are not the PM, not the independent reviewer, not a Core runtime engineer, not a Resident, and not a semantic evaluator.

## Pinned failure evidence

Independent acceptance report:
`reviews/CORE_CI_FIX_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

Review PR #150 was merged as evidence at:
`905ad890e6e63d33c378abdded7682ee96bd82a0`

Failed candidate:
- PR #146
- exact failed head: `1896b3e5257bd0eaea990f2b7a656e9747d899ba`
- verdict: `ACCEPTANCE_FAIL`
- blocker: `CORE-CI-FIX-001-ACCEPT-BLOCKER-001`

PR #144 remains SUPERSEDED / NOT INTEGRATED and must not be revived.

## Before editing

1. Fetch live main and record its SHA.
2. Read:
   - `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
   - `AIOS_v3.0_CURRENT_CHECKPOINT.md`
   - `governance/AIOS_CORE_CI_FINDING_001_2026-09-24.md`
   - `reviews/CORE_CI_FIX_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`
   - this prompt.
3. Confirm `CORE-CI-FIX-001-CORRECTIVE-001 = READY`. If not, stop.
4. Continue the existing PR #146 / branch `core-ci-fix-001-20260924-sol`. Do not open a competing implementation PR.
5. Rebase or merge current live main into that branch before final verification if needed; the final PR diff against live main must remain limited to the three workflow files.

## Exact blocker

All three repaired guards use `set -euo pipefail` and policy predicates of the form:

`if printf '%s\n' "$changed" | grep -q 'PATTERN'; then ... fi`

With an early match and a sufficiently large remaining changed list, `grep -q` exits early, upstream `printf` can receive SIGPIPE, the pipeline returns 141 under `pipefail`, and the `if` condition becomes false. The invariant rejection can therefore be skipped and the guard may exit 0.

The independent reviewer reproduced `GUARD_PASSED`.

## Required minimal correction

Do not redesign the branch-shape fix.

In the same three workflow files only:

- replace every protected-path predicate that uses `printf ... | grep -q` with a non-pipe input form that cannot create upstream SIGPIPE under `pipefail`, e.g. `grep -q PATTERN <<<"$changed"`, or another equally fail-closed construction;
- apply this to every protected-path predicate in those guards, not only `src/aios_core/**`;
- preserve the current PR-event pinned-base logic;
- preserve the workflow_dispatch unshallow/merge-base logic;
- preserve exit class 2 for evaluation failure;
- preserve exit class 1 for invariant rejection;
- do not weaken or delete any protected-path check.

Allowed files only:
- `.github/workflows/c14-resident-fixture-v2.yml`
- `.github/workflows/c14-semantic-repair-fixture.yml`
- `.github/workflows/c15-rcc-fixture.yml`

Forbidden:
- `src/**`
- `tests/**`
- `tools/**`
- `governance/**`
- `reviews/**`
- fixtures/evidence/World/Resident data
- historical result rewriting

## Required verification

You must preserve the historical evidence and add new corrective evidence.

1. Large changed-list / early-match regression:
   - reproduce the failed candidate behavior at `1896b3e5...` or with an equivalent harness;
   - prove the old predicate can return/present the false-negative condition;
   - prove the corrected predicate rejects the same large-list early Core match with explicit `Invariant rejected` and exit 1.

2. Deliberate Core negative probe:
   - use a temporary probe commit/ref containing a `src/aios_core/**` change;
   - all three guards must reject specifically at the invariant check with exit 1;
   - include enough additional changed-path data to exercise the previous SIGPIPE edge;
   - remove the probe from the final candidate.

3. Positive branch-shape proof:
   - exercise a PR-shaped branch whose true merge base is outside the old shallow window;
   - all three repaired guards must evaluate and pass.

4. Final exact-head gates:
   - all three workflows must run on the new exact candidate head and succeed;
   - confirm the guard steps actually executed and were not skipped.

5. Final scope:
   - exactly the three workflow files;
   - no Core/test/tool/governance/review diff.

## Deliverable

Update PR #146 rather than creating a new candidate PR.

PR #146 body must record:
- new live-main/rebase baseline if applicable;
- prior failed candidate `1896b3e5...`;
- blocker ID;
- exact corrective diff;
- large-list regression evidence;
- negative probe SHA and run/job IDs;
- branch-shape proof run/job IDs;
- new final exact head;
- all final exact-head run/job IDs;
- final file scope.

Final author state: **REVIEW_READY**.

Do not merge.
Do not update task board/checkpoint.
Do not self-accept.
Stop after the corrected candidate is ready for a fresh independent review.
