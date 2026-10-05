# CORE-RC-REFREEZE-004 - Open PR / branch contamination review

Fresh remote inventory was repeated immediately before final-candidate construction.

Fresh live main remains:
`ee4556989fea16a28d2c727eb345d48385a453fe`.

The remote reported **51 open PRs** at this point. Open is not accepted and no open PR is imported by existence alone. The final exact-head CI performs a fresh API snapshot again and records release-relevant file paths.

## Required classifications

- **PR #310** - OPEN / UNMERGED; historical failed Corrective-002 implementation; exact head `fec30bd1495017bf13f08b0ef5b1e241dfb0e247`; touches Core runtime/tests/workflow; **not imported**.
- **PR #311** - OPEN / UNMERGED; historical Window 20 REVIEW_ONLY evidence; exact head `fd52ea8243970187b439208d7061c04c68b6b8ea`; **not software authority**.
- **PR #321** - OPEN / UNMERGED; Window 23 REVIEW_ONLY Fresh IA evidence; exact head `22aa00cb3793c252512142a1eae33ca8aae9d841`; changes only `reviews/WINDOW23_FRESH_IA/**`; **DO NOT MERGE**.
- Window 23 publication branches `publication/window23-review-exact-publisher` and `publication/window23-review-tree-staging` are **transport only**.
- Historical C15 persistence/operator WIP and evidence branches/PRs remain downstream and are **not automatically absorbed**.

## Software-boundary decision

Fresh compare from frozen software `1cee3c5ad12f4b9098232bae11b51df786c5eb2f` to live main remains 9 commits, with final delta limited to five governance/checkpoint files. Protected drift remains zero for:
- `src/**`
- `tests/**`
- `pyproject.toml`
- `.github/workflows/**`

Therefore no open PR or branch is part of the frozen software boundary unless separately accepted and integrated. The RC candidate itself contains only RC workflow/evidence material permitted by the task.
