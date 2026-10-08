# PM49-BLK-001 Closure: Hosted Resident-Surface Base Resolution

- **Blocker ID**: `PM49-BLK-001`
- **Severity**: `HIGH`
- **Category**: CI / Hosted Harness Base Resolution
- **File Impacted**: `tools/c15_persistence/resident_surface_check.py`, `tests/c15_persistence/test_resident_surface.py`

---

## 1. Problem Statement
In detached/hosted GitHub Actions checkouts or shallow clones, `git rev-parse --verify main^{commit}` fails because the symbolic reference `main` may not be checked out locally as a local branch. This resulted in:
```
ValueError: base ref 'main' does not resolve to a valid commit
```
which prevented automated non-interactive execution of `tools/c15_persistence/resident_surface_check.py`.

---

## 2. Solution & Architectural Implementation
Implemented `resolve_surface_base(explicit_base, repo_root)` with strict, deterministic fallback ordering:

1. **Explicit Parameter / Environment Variable**:
   - `explicit_base` or `os.environ["C15_SURFACE_BASE"]`.
   - Verified via `git rev-parse --verify <rev>^{commit}`. If specified but invalid, raises `ValueError` immediately.
2. **GitHub Actions PR Event Payload**:
   - Parses `os.environ["GITHUB_EVENT_PATH"]` for `pull_request.base.sha` or `pull_request.base.ref`.
3. **Merge Base with Remote Tracking Refs**:
   - Checks `git merge-base HEAD origin/main` and `git merge-base HEAD origin/HEAD`.
4. **Local Ref Merge Base**:
   - Checks `git merge-base HEAD main`.
5. **Direct Parent Ref**:
   - Falls back to `HEAD~1` (never `HEAD` itself).

---

## 3. Verification & Regressions
Added comprehensive automated test cases in `tests/c15_persistence/test_resident_surface.py`:
- `test_unresolved_symbolic_base_fails_cleanly`: Proves invalid/unresolvable base strings raise `ValueError` without crash.
- `test_exact_base_sha_succeeds_non_vacuously`: Proves passing explicit verified 40-character SHA runs full tree comparison.
- `test_resident_surface_check_against_base`: Proves end-to-end surface check passes with `RESIDENT_SURFACE_UNCHANGED`.
