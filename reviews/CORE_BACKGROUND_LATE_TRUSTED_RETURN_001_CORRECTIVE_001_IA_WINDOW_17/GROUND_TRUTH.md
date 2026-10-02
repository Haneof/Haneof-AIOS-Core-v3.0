# WINDOW 17 Ground Truth Verification (`GROUND_TRUTH.md`)

- **Task:** `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE` (`WINDOW 17`)
- **Role:** Fresh Independent Core Runtime Acceptance Reviewer
- **Date:** `2026-10-02`

## 1. Fresh Git & GitHub Ground Truth at Window Start

| Item | Expected / Dispatched | Freshly Verified | Status |
|---|---|---|---|
| `origin/main` SHA | `0b883c71d91e5f0772334514925237f1570fa780` | `0b883c71d91e5f0772334514925237f1570fa780` | `MATCH (0 drift)` |
| `origin/main` subject | `Merge PR #307 governance clarification: S3 vs C4/C5 Corrective-001 entry contract` | Verified | `MATCH` |
| `PR #308` state | `OPEN / Ready for review / UNMERGED / DO NOT MERGE` | `state=OPEN, mergedAt=null` | `MATCH` |
| `PR #308` branch | `core-background-late-trusted-return-corrective-001-window16` | `core-background-late-trusted-return-corrective-001-window16` | `MATCH` |
| `PR #308` head SHA | `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` | `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` | `MATCH` |
| `PR #308` parent SHA | `293d32c683033ba27c11059fd021e68342a82c77` | `293d32c683033ba27c11059fd021e68342a82c77` | `MATCH` |
| `PR #308` tree SHA | `a762df979826d3a599b93d937c53b633d0cb8466` | `a762df979826d3a599b93d937c53b633d0cb8466` | `MATCH` |
| `PR #308` construction base | `0b883c71d91e5f0772334514925237f1570fa780` | `0b883c71d91e5f0772334514925237f1570fa780` | `MATCH` |
| Historical failed `PR #305` state | `OPEN / UNMERGED / FROZEN / DO NOT MERGE` | `state=OPEN, mergedAt=null` | `MATCH (untouched)` |
| Historical failed `PR #305` head SHA | `5ad0524c425592210ff184e00ad52abb2c14e366` | `5ad0524c425592210ff184e00ad52abb2c14e366` | `MATCH (untouched)` |
| Canonical Window 14 review commit | `84457badc562416f59fb25ca41103700276e0df2` | `84457badc562416f59fb25ca41103700276e0df2` | `MATCH (untouched)` |
| Canonical Window 14 review sole parent | `5ad0524c425592210ff184e00ad52abb2c14e366` | `5ad0524c425592210ff184e00ad52abb2c14e366` | `MATCH` |
| Canonical Window 14 review tree | `bd235452c0b78a7fbeedd48d048fc78b331d92bf` | `bd235452c0b78a7fbeedd48d048fc78b331d92bf` | `MATCH` |
| Original local-only object | `1c0510cfe989e832f46aa1e2e070134048440e27` | `LOST_LOCAL_OBJECT / NEVER_REMOTE_DURABLE / NON_AUTHORITATIVE` | `PRESERVED` |

## 2. Stop-Condition Checks

- `ACCEPTANCE_BLOCKED_BY_RELEVANT_GROUND_TRUTH_DRIFT`: **NOT TRIGGERED** (`origin/main` == construction base `0b883c71d91e5f0772334514925237f1570fa780`).
- `ACCEPTANCE_BLOCKED_BY_CANDIDATE_DRIFT`: **NOT TRIGGERED** (`PR #308` head == `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd`).
- `ACCEPTANCE_BLOCKED_BY_BASELINE_REPRODUCTION_FAILURE`: **NOT TRIGGERED** (all 4 historical RED blockers reproduced on `5ad0524c425592210ff184e00ad52abb2c14e366` using canonical Window 14 probes from `84457badc562416f59fb25ca41103700276e0df2`).
