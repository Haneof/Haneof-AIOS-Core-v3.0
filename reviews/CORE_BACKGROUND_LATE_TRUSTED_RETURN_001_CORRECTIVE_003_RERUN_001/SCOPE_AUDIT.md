# SCOPE_AUDIT — Window 22-RERUN-001

Baseline for every diff: live main `1541b1ec1a8b40bdc67debd52af986c2869ee00e`
(merge base of this branch with main; verified by CI job `scope-discipline-and-identity-guard`).

| verdict | value |
|---|---|
| `out_of_scope` | **0** |
| `forbidden_paths` | **0** |
| build artifacts in the tracked tree | **0** |
| reviewer probe bytes in the tracked tree | **0** (`C3-6`) |
| historical reviewer evidence modified | **0** |
| files changed vs main | 48 (before this evidence batch) |

---

## 1. Areas touched

| area | paths | why in scope |
|---|---|---|
| `src/aios_core/runtime/` | 6 | the Route B corrective itself: `background_attempt.py`, `cognitive_runtime.py`, `turn_runtime.py`, `__init__.py` modified; `late_return.py` and `live_return.py` added (the latter is the inert tombstone) |
| `tests/integration/` | 15 | 6 carried forward from `fec30bd1`, 8 historical files rewritten TIGHTEN_ONLY, 1 new (the section-16 C3 author matrix) |
| `tests/runtime/` | 5 | 2 carried forward, 3 historical files rewritten TIGHTEN_ONLY |
| `.github/workflows/` | 1 | `core-background-late-trusted-return-001.yml` — the section-17 formal gate, replacing the Window 16 version |
| `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_003_RERUN_001/` | 21 + this batch | the section-21 evidence directory for this window |

Nothing else in the repository was touched. In particular: no `src/aios_core/**` module outside
`runtime/`, no `governance/**`, no `AIOS_v3.0_CURRENT_CHECKPOINT.md`, no other workflow, no
`pyproject.toml`, no packaging or release artifact.

## 2. Forbidden paths — each verified untouched

The formal workflow asserts every one of these mechanically against
`git diff --name-status <merge-base> HEAD` and fails the run with `SCOPE_VIOLATION` on any match.

| forbidden path | status |
|---|---|
| root `.gitignore` (never add, never modify) | untouched — not added, not modified |
| `tools/c15_persistence/**` | untouched |
| `tests/c15_persistence/**` | untouched (78 cases exist there; they are **not** part of the Core gate) |
| `tools/c15_preflight/**` | untouched |
| Resident evidence | untouched |
| `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_IA/**` (historical Window 14) | untouched |
| `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_001_IA_WINDOW_17/**` | untouched |
| `reviews/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_002_IA_WINDOW_20/**` | untouched |
| `reviews/C15_*` | untouched |
| `reviews/internal_habitation/**` | untouched |
| unrelated governance / task board / checkpoint | untouched |
| release artifacts | untouched |
| UI / hardware | untouched |
| PR #310 branch (`arena/01a10010-…`, head `fec30bd1`) | read-only — never committed to, force-pushed, rebased, squashed or amended |
| PR #311 branch (head `fd52ea82`) | read-only |

The frozen reviewer probes are re-verified unchanged in the GitHub object graph on every run:
blob id **and** SHA-256 of the bytes at `2203117…` / `e4161dd0…` must equal the pinned values, and
if any probe path exists at `HEAD` its bytes must hash to the same pinned SHA-256.

## 3. Build-artifact hygiene

Root `.gitignore` is forbidden, so build artifacts are handled by **cleaning the tracked tree**,
not by ignoring it. Before every commit in this window:

```
find . -path ./.git -prune -o -name '__pycache__' -type d -print -o -name '.pytest_cache' -type d -print | xargs -r rm -rf
```

and the workflow fails the run if `git ls-files` ever matches
`__pycache__/`, `*.pyc`, `*.egg-info/`, `.pytest_cache/`, `build/` or `dist/`.
Current status: **0** such paths tracked.

Local test runs used `-p no:cacheprovider` so no `.pytest_cache` was created in the first place.

## 4. Role scope

This window acted as **Core Runtime Corrective Engineer only**. It did **not**:

* perform Independent Acceptance;
* merge its own PR (the PR is opened **UNMERGED**, `DO NOT MERGE`);
* enter Window 23 Fresh IA;
* enter `RC-REFREEZE-004`;
* run any Resident;
* act as PM, IA reviewer, governance adjudicator, merge owner, RC freeze owner, C15 persistence
  engineer, C15 operator, Resident A/B/C, evaluator, release operator or UI/hardware engineer.

The stop state is `REVIEW_READY / READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE / DO NOT MERGE`.

## 5. Stop conditions — none raised

| stop condition | status |
|---|---|
| `GROUND_TRUTH_DRIFT` | not raised — live main `1541b1ec…` confirmed |
| `GITHUB_PUBLICATION_CAPABILITY_REQUIRED` | not raised — write capability proven **before** any source edit (`PUBLICATION_CAPABILITY_PREFLIGHT.md`) |
| `FAILED_CANDIDATE_DRIFT` | not raised — `refs/pull/310/head == fec30bd1…` |
| `WINDOW20_REVIEW_IDENTITY_MISMATCH` | not raised — `2203117…` is an ancestor of `refs/pull/311/head` |
| `WINDOW20_PROBE_HASH_MISMATCH` | not raised — Suite A and Suite B blob + SHA-256 match |
| `WINDOW17_PROBE_HASH_MISMATCH` | not raised — W17 blob + SHA-256 match |
| `RED_FIRST_NOT_REPRODUCIBLE` | not raised — Suite A is `probes=4 failures=4` on `fec30bd1` and byte-identical on the carry-forward base |
| `TRUST_AUTHORITY_STILL_CALLER_MANUFACTURABLE` | not raised — C3 matrix 28/28 green; workflow guard steps (a)(b)(c) pass |
| `REFLECTION_MINT_PATH_REMAINS` | not raised — C3-2 all 13 reflection paths green |
| `VERIFIERLESS_FAIL_CLOSED_BROKEN` | not raised — C3-3-01 green, `IA20-MINT-004` refused |
| `CORRECTIVE002_POSITIVE_REGRESSION` | not raised — Suite B `7/0`, W17 `14/0`, migration/RSA/exactly-once/SIGKILL jobs green |
| `CORE_REGRESSION_FAILURE` | not raised — formal CPython 3.12.14 full Core gate `928 passed`, 0 failed, 0 errors |
| `SCOPE_VIOLATION` | not raised — this file |
| `FORMAL_CI_NOT_EXACT_HEAD` | not raised — the workflow asserts `git rev-parse HEAD == GITHUB_SHA == remote engineering branch head` |
| `REMOTE_PUBLICATION_IDENTITY_CONFLICT` | not raised — one engineering branch, one PR, no force-push, no history rewrite |
