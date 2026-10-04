# Window 23 Fresh IA Evidence Publication Completion / PM Integration Release

Date: 2026-10-04

Task:
`CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003-INDEPENDENT-ACCEPTANCE`

Candidate PR: #318

Fresh PM main before this writeback:
`cb75b0bb40b3177e30846a27b88259ab783a09e2`

## Final Window 23 state

`ACCEPTANCE_PASS`

`blocker=0`

`REVIEW_EVIDENCE_PUBLISHED`

`READY_FOR_PM_INTEGRATION`

The earlier publication hold from PR #320 is resolved.

## Candidate identity

- exact candidate: `7ecb2250a488766915e1042a76472b3cd26d9107`
- parent: `30022b06e2795d20790dd4532bf6987146c1b432`
- tree: `1438a9ea6b8582453f963db5acb7f136e5ac5385`
- engineering PR #318: OPEN / non-draft / UNMERGED / DO NOT MERGE
- formal exact-head run `37166276909`: 12/12 SUCCESS
- full Core: 928 passed / 0 failed / 0 errors

## Fresh IA exact reviewer evidence

Reviewer branch:
`arena/review-window23-fresh-ia-01a101e0`

Exact review commit:
`22aa00cb3793c252512142a1eae33ca8aae9d841`

Parent:
`7ecb2250a488766915e1042a76472b3cd26d9107`

Tree:
`28593da131e7026de1de0037a87b6b892a5988ba`

Author/committer:
`Window23 Reviewer <reviewer@arena.ai>`

Timestamp:
`2026-10-04T13:00:07Z`

Review PR:
#321 — REVIEW_ONLY / DO NOT MERGE

#321 is based directly on the exact candidate branch and contains exactly 11 paths under
`reviews/WINDOW23_FRESH_IA/**`, with zero `src/**`, `tests/**`, `.github/**` or `tools/**`
changes.

## Publication provenance

The reviewer sandbox could not push, so PM received the exact reviewer git bundle directly.

Bundle SHA-256:
`47c1bb66ff43805eb2c40690796503917008fdc599806633f3530d4087ecd85b`

PM independently verified:
- `git bundle verify` = OK;
- advertised branch/head = `arena/review-window23-fresh-ia-01a101e0 -> 22aa00cb…`;
- review parent = exact candidate;
- review tree = `28593da…`;
- candidate-to-review scope outside `reviews/WINDOW23_FRESH_IA/**` = empty.

PM then reconstructed all 11 exact blobs on GitHub. Every blob SHA matched the bundle, and the resulting
tree SHA mechanically reproduced `28593da131e7026de1de0037a87b6b892a5988ba`.

Because the GitHub low-level commit wrapper does not expose original author/committer dates, PM did
not create an approximate reviewer commit. Instead a one-time deterministic publication workflow
reconstructed the original commit using its exact tree, parent, message, author, committer and
timestamp.

Exact publisher run:
`37206355171` = SUCCESS.

The job mechanically asserted:
- `staging_tree=28593da131e7026de1de0037a87b6b892a5988ba`
- `rebuilt_commit=22aa00cb3793c252512142a1eae33ca8aae9d841`
- `remote_review_head=22aa00cb3793c252512142a1eae33ca8aae9d841`

Only after all exact checks passed did it publish the reviewer ref.

## Fresh IA verdict

Window 23 independently returned:

`ACCEPTANCE_PASS / blocker=0 / READY_FOR_PM_INTEGRATION`

No corrective engineering was performed by the reviewer.

The review independently covered the frozen W20/W17 probes plus reviewer-owned adversarial probes,
trust-mint writer enumeration, reflection/object-graph attacks, tombstone bypasses, record_response
residual behavior, inherited partial-commit behavior, supersession, C3 non-vacuity, TIGHTEN_ONLY
test audit, full Core regression, side-workflow classification and formal-workflow permission audit.

## Base drift before PM integration

PR #318 is based on `1541b1ec1a8b40bdc67debd52af986c2869ee00e`.

PM compared that base to `cb75b0bb40b3177e30846a27b88259ab783a09e2`.

The drift is only:
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `governance/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_003_RERUN_001_PM_READINESS_2026-10-04.md`
- `governance/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_003_WINDOW23_EVIDENCE_PUBLICATION_HOLD_2026-10-04.md`

No `src/**`, `tests/**`, `.github/**`, or `tools/**` drift exists.

Therefore the accepted candidate must be integrated with a normal merge commit using exact PR head
`7ecb2250…`; it must not be rebased or squashed.

## PM Integration release

PM Integration is now unblocked.

Before merging #318, PM must re-check:
- live main;
- #318 is OPEN / UNMERGED;
- #318 head still exactly `7ecb2250…`;
- review branch still exactly `22aa00cb…`;
- review PR #321 remains REVIEW_ONLY / OPEN / UNMERGED;
- formal run `37166276909` remains SUCCESS;
- mergeability remains true;
- no new semantic base drift exists.

If all hold, merge #318 using merge-commit mode with expected head SHA
`7ecb2250a488766915e1042a76472b3cd26d9107`.

Do not merge #321.
