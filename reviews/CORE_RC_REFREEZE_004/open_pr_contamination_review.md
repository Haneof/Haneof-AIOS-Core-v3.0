# CORE-RC-REFREEZE-004 — Open-PR / Branch Contamination Review

Snapshot time: **2026-10-04 ~23:2x +0800**, repository `Haneof/Haneof-AIOS-Core-v3.0`, freshly fetched live `main` = `ee4556989fea16a28d2c727eb345d48385a453fe`, frozen software = `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`.

## Method

Fresh GitHub REST inventory (`GET /pulls?state=open&per_page=100`) → **52 open PRs**; every PR's changed paths enumerated via paginated `/pulls/{n}/files`. Full snapshot: `open_pr_snapshot.json`. Classification is a point-in-time contamination screen, **not** a merge authorization; open ≠ accepted.

Protected-surface drift, frozen → live main: `src/**` 0 paths, `tests/**` 0 paths, `pyproject.toml` 0 paths, `.github/workflows/**` 0 paths; the trees are identical at both points (`src/aios_core` `16f1487e…`, `tests` `9db1bfa0…`, `.github/workflows` `72cde9d2…`, `pyproject.toml` blob `b38833c7…`).

## Required classifications

| Item | Live identity | Surface | Disposition for this RC |
|---|---|---|---|
| **#310** | head `fec30bd14950…`; OPEN; `[IA_FAIL / blocker=1 / FROZEN / DO NOT MERGE]` | `reviews/**`, `src/**`, `tests/**`, `workflows` | Failed frozen candidate line; **not imported, not used as target**; its blocker is historical. |
| **#311** | head `fd52ea824397…`; OPEN | reviews/tests/workflows line (Window-20 corrective review chain) | Not imported. Its head commit is the canonical carrier of reviewer commit `220311759e88fb3948ad3f4dba655058e0f392a8`; the §6 probes are extracted **from the reviewer commit identity**, not from the PR as software. |
| **#308** | head `cb8a6b3cdaa6…`; OPEN; `IA_FAIL / blocker=3 / FROZEN / DO NOT MERGE` | `reviews/**`, `src/**`, `tests/**`, `workflows` | Failed frozen candidate line; not imported. |
| **#305** | head `5ad0524c42…`; OPEN; `IA_FAIL / blocker=4 / DO NOT MERGE` | src/tests/tools/workflows/reviews | Failed candidate; not imported. |
| **#321** | head `22aa00cb3793c252512142a1eae33ca8aae9d841`; OPEN; base `arena/01a101e0-…` | `reviews/WINDOW23_FRESH_IA/**` only (11 doc files vs `7ecb2250`) | **REVIEW_ONLY** Window-23 evidence; doc-only, not software; not merged and not part of the frozen tree. |
| **#325** | head `669cb96e1a56…`; OPEN; `[DO NOT MERGE] CORE-RC-REFREEZE-004 — exact candidate pending` | `release/**`, `reviews/**`, `workflows` | The transport line's publication staging candidate for this window. **Not reused** — this window opens a NEW candidate PR from `arena/01a10764-haneof-aios-core-v3-0` per §18. |
| Window-23 publication staging branch/workflow (`publication/window23-review-tree-staging`, `publication/window23-review-exact-publisher`) | refs `db75dcec…`, `d0ee69aa…`; not an open PR | review-evidence publication | Transport only; not software; not imported. |
| **#258 / #216 / #251 / #249 / #261** | OPEN/DRAFT historical | C15 persistence/operator WIP and review-only evidence | Unaccepted historical WIP, **not auto-absorbed**; do not resume or import. |
| Older implementation-touching PRs **#110 #111 #113 #126 #130 #144** | OPEN | `src/**`, `tests/**`, `tools/**`, workflows | Unmerged, unaccepted; not imported; frozen trees unaffected. |

## New PRs

The only new open PR since the prior snapshot is **#325** (RC-REFREEZE-004 transport candidate, classified above). No other newly opened PR touches a protected surface.

## Result

`protected_implementation_drift_count = 0`; `post_target_delta` = 5 governance/checkpoint files (governance + task board + checkpoint + RC-004 prompt/entry decision). No open PR or unmerged branch content is part of the frozen software identity.
