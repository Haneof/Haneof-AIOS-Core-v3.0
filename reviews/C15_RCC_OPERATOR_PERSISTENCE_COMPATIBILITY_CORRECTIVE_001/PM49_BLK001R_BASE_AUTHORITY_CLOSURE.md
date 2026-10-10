# PM49-BLK-001R Closure: Authoritative Construction Base Resolution & Multi-Commit PR Drift Protection

- **Blocker ID**: `PM49-BLK-001R`
- **Severity**: `HIGH`
- **Binding**: **YES**
- **Root Cause**: `resolve_surface_base()` contained a final fallback `git rev-parse HEAD~1`. In a multi-commit PR, `HEAD~1` is only the preceding corrective commit rather than the PR construction base (`4b0d0718e016d2bc4088d59ec2dba00b637994db`), creating the risk of comparing only against the latest delta and hiding earlier candidate drift.
- **Closure Status**: **CLOSED**

---

## 1. Technical Fix in `tools/c15_persistence/resident_surface_check.py`

1. **Elimination of Non-Authoritative Fallbacks**:
   - Strictly deleted `HEAD~1`, `HEAD`, and unverified parent references.
   - Authorized base resolution sources only:
     1. Explicit verified commit SHA via CLI `--base` or `C15_SURFACE_BASE` environment variable.
     2. GitHub Actions PR event metadata via `GITHUB_EVENT_PATH` (`pull_request.base.sha`).
     3. Mechanically verified `git merge-base HEAD origin/main` (fetching on-demand if shallow).
     4. Mechanically verified `git merge-base HEAD main`.
     5. Fail-closed exception: `raise ValueError("cannot mechanically resolve a valid resident-surface base commit in current git repository: base authority unresolved")`.

2. **Repository Root Support for Tree Diffing**:
   - `_pinned_tree_digest(base: str, repo_root: Path = REPO_ROOT)` accepts target `repo_root` to support isolated multi-commit test repositories without mutating working directory state.

---

## 2. Attacker Test Evidence in `tests/c15_persistence/test_pm49_blockers.py`

- `test_pm49_blk001r_detached_checkout_fails_closed_without_head_fallback`: Proves that in a multi-commit detached checkout without remote metadata, `resolve_surface_base` fails closed with `ValueError` and refuses to fall back to `HEAD~1`.
- `test_pm49_blk001r_explicit_base_detects_earlier_commit_drift`: Creates a multi-commit PR where commit A introduces drift in `src/aios_core` and commit B modifies C15 files. Proves that diffing against `HEAD~1` would falsely report clean, whereas diffing against the authoritative PR base SHA catches the drift and fails clean verification.
- `test_pm49_blk001r_github_pr_event_base_resolves_correct_sha`: Proves GitHub PR event metadata correctly resolves the exact base commit SHA.
