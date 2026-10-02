# Scope Independent Check (`SCOPE_AUDIT.md`)

- **Reviewed Exact Candidate:** `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`PR #308`)
- **Construction Base:** `0b883c71d91e5f0772334514925237f1570fa780`

## 1. Forbidden Scope Verification (`git diff 0b883c71d91e5f0772334514925237f1570fa780..cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd`)

| Forbidden Scope | Diff Count | Status |
|---|---|---|
| `tools/c15_persistence/**` | `0` files | `ZERO DIFF (CLEAN)` |
| `tools/c15_preflight/**` | `0` files | `ZERO DIFF (CLEAN)` |
| `evidence/w08/**` / `evidence/**` | `0` files | `ZERO DIFF (CLEAN)` |
| `reviews/internal_habitation/**` | `0` files | `ZERO DIFF (CLEAN)` |
| `release/**` / sealed fixtures / evaluators | `0` files | `ZERO DIFF (CLEAN)` |
| `governance/**` / `AIOS_v3.0_CURRENT_CHECKPOINT.md` | `0` files | `ZERO DIFF (CLEAN)` |
| `PR #305` (`5ad0524c425592210ff184e00ad52abb2c14e366`) | Unchanged (`OPEN / UNMERGED`) | `CLEAN` |
| Window 14 review branch (`84457badc562416f59fb25ca41103700276e0df2`) | Unchanged (`REVIEW_ONLY`) | `CLEAN` |
| Persistence remote refs (`refs/heads/persistence/*`) | Unchanged | `CLEAN` |

## 2. Non-Blocking Observation on `tests/c15_persistence/test_resident_surface.py` Invocation

In `.github/workflows/core-background-late-trusted-return-001.yml:284-286` (added in final commit `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd`), `pytest tests/c15_persistence/test_resident_surface.py` is invoked without setting `C15_SURFACE_BASE`.
- `test_resident_surface.py` defaults `C15_SURFACE_BASE` to `"main"`, and `tools/c15_persistence/resident_surface_check.py:_pinned_tree_digest` runs `git diff --stat main...HEAD -- src/aios_core` without checking `completed.returncode`.
- In GitHub Actions (`actions/checkout@v5`), local ref `refs/heads/main` does not exist (only `origin/main` exists), so `git diff --stat main...HEAD` fails with exit code `128` and empty `stdout`, which `_pinned_tree_digest` treats as `clean: True`.
- In any local git checkout where local branch `main` exists (`0b883c71...`), running `pytest tests/c15_persistence/test_resident_surface.py` without `C15_SURFACE_BASE=HEAD` fails with `RESIDENT_SURFACE_CHANGED` because `src/aios_core` differs from `main` on a Core PR (`raw/candidate_resident_surface_1.txt` vs `raw/candidate_resident_surface_base_head_1.txt`). All 12 Resident-visible behavioural comparisons themselves are `true`.
