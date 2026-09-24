# CORE-OPERATOR-001 PM Integration Receipt — 2026-09-24

Task: `CORE-OPERATOR-001`
Role issuing this receipt: Core Delivery PM / Chief Integration Coordinator (successor PM per `governance/prompts/AIOS_CORE_PM_HANDOFF_2026-09-24.md`)
Repository: `Haneof/Haneof-AIOS-Core-v3.0`
Result: **DONE — integrated after independent acceptance**

This receipt records an integration decision. It is not a software test result, not a semantic PASS, and not authorization to run any Resident.

## 1. Integrated artifacts

| Item | Exact identifier |
|---|---|
| Accepted engineering candidate | PR #131, exact head `0e1d69eebc801278f93ccc1941b8f066a4ea09ef` |
| Candidate construction base | `c8807876ba62a4f4180beba8ff974e2342786340` |
| Candidate merge commit | `e72a63874ed2c28798b00cec51f191caf1594a00` |
| Independent acceptance report | PR #135, exact head `50133c2a3348095abf520b4a645ad5a73ca18951` |
| Acceptance report path | `reviews/CORE_OPERATOR_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md` |
| Acceptance report merge commit | `fe6f1740eb4e6ab4d1c562373ef5d3554bb2dc54` |
| Pre-integration main | `27135e39d5123d079e065c8ddfbcb23b2a3e37c8` |
| Post-integration main | `e72a63874ed2c28798b00cec51f191caf1594a00` |
| Core tree before and after | `src/aios_core = 7db4f72e7b3c29c74082f9984141159f8f1d6071` (unchanged) |
| Source WIP harvested from | PR #125 exact head `b14b5d84b6a4c843dc7dc38cde51f08a92fac86b` (not merged) |

Independent reviewer verdict: **ACCEPTANCE_PASS**, 0 blockers, 3 non-blocking observations.

## 2. PM integration-time verification (not a re-review)

The independent acceptance report was not accepted on its text alone. The PM re-derived the following from the live repository and the GitHub API at integration time.

### 2.1 Pin and scope

- PR #131 head at integration time was still exactly `0e1d69ee...`; the pinned reviewed artifact did not change after the report was written.
- Candidate scope against merge base `c8807876...`: exactly **26 changed files**, **0 files under `src/`**.
- Scope is confined to `.github/workflows/c15-operator-preflight.yml`, `tests/preflight/**`, `tools/c15_preflight/**`.

### 2.2 Core ZERO DIFF held across the integration

- `git diff 27135e39... e72a638... -- src/` is **empty**.
- Post-integration `src/aios_core` tree is still `7db4f72e...`, identical to the tree audited by `CORE-GAP-AUDIT-001` and to the tree recorded by `CORE-BASELINE-001`.
- The integration is purely additive: 27 new files (26 candidate files + the acceptance report). No file was modified or deleted.
- The accepted exact head `0e1d69ee...` is an ancestor of `main`; the merge-commit strategy preserves the reviewed SHA in history instead of rewriting it.

### 2.3 CI receipts re-read from the API, not from the report

| Purpose | Run | Workflow | Head SHA | Conclusion |
|---|---|---|---|---|
| Before-fix reproduction | `35955458275` | `c15-operator-preflight` | `3865da8816ccac48e3eda06f329a84f55e2d0bd6` | FAILURE |
| Before-fix full suite | `35955458266` | `p16-convergence-gate` | `3865da8816ccac48e3eda06f329a84f55e2d0bd6` | FAILURE |
| Exact-head candidate gate | `35955695487` | `c15-operator-preflight` | `0e1d69eebc801278f93ccc1941b8f066a4ea09ef` | SUCCESS |
| Exact-head full regression | `35955695492` | `p16-convergence-gate` | `0e1d69eebc801278f93ccc1941b8f066a4ea09ef` | SUCCESS |

The candidate workflow was inspected directly at the candidate head: it checks out `github.event.pull_request.head.sha`, asserts Python >= 3.12, runs plain `python -m pytest` invocations, and contains no `|| true`, no `continue-on-error`, and no narrowed substitute for the full gate.

### 2.4 Independent local re-execution by the PM

The PM re-ran the decisive evidence locally instead of trusting green CI badges.

Environment: CPython 3.11.2, pydantic 2.13.5, pytest 8.4.2, worktree extracted per exact SHA.

| Tree under test | Command | Result |
|---|---|---|
| Reproduction commit `3865da88...` | the three exact regressions | **3 failed** |
| Accepted head `0e1d69ee...` | the three exact regressions | 3 passed |
| Accepted head `0e1d69ee...` | `pytest -q` (whole repository) | **632 passed** |
| Merge result `e72a638...` | the three exact regressions | 3 passed |
| Merge result `e72a638...` | `pytest -q` (whole repository) | **632 passed** |

The locally observed failure symptoms at `3865da88...` match the documented ones exactly:

1. `test_clock_reuses_existing_scheduler_at_intermediate_deadline_without_future_input` — `periodic_reviews` empty, `IndexError` on element 0 (the T+24h Review never ran before T+49h).
2. `test_old_wake_cannot_see_future_input` — the old Wake observed `SYNTHETIC event 1`.
3. `test_budget_deferral_not_forced` — `pre_ingest_wakes` empty (`assert 0 >= 1`).

This confirms the historical defect was genuinely reproduced on a current-main-based candidate and genuinely closed, rather than made green by test edits or CI configuration. The local pass count `632` equals the count independently reported from the CI full-suite log.

### 2.5 Honest limitations of this receipt

- The local runs used CPython **3.11.2**, below the project gate of >= 3.12. They are corroboration only. The authoritative gate evidence remains the CI runs on CPython 3.12.14.
- The PM attempted a fresh re-run of the exact-head gates (`gh run rerun`) and a post-merge `workflow_dispatch` on `main`. Both were refused by the platform for this token (`HTTP 403: Resource not accessible by integration`; "cannot be rerun"). No permission was bypassed and no protection was circumvented. Post-merge verification is therefore recorded as **local merge-result verification**, plus exact-head CI receipts, not as a new post-merge CI run. The next PR that touches `tools/c15_preflight/**` or `tests/preflight/**` will exercise `c15-operator-preflight` on the integrated main automatically.
- The candidate author window and the independent acceptance window are separate AI windows with separate contexts, but both act through the same GitHub account identity (`Haneof`). There is therefore **no GitHub-native `APPROVE` event from a distinct account**. Independence here is process-level and evidence-level, recorded in `reviews/CORE_OPERATOR_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`; it is not account-level or cryptographic independence, and this receipt does not claim otherwise.

## 3. Boundary confirmation

- **NO RESIDENT EXECUTED.** No A/B/C run, no semantic evaluation, no provider call.
- No `src/aios_core/**` change; the semantic Core freeze is unaffected.
- No fixture activation, no sealed-future read, no private World access, no historical evidence rewritten.
- PR #117 (historical accepted A), PR #121 (historical failed B), PR #125 and PR #126 remain OPEN, UNMERGED and unmodified; all four pins were re-verified at integration time and still match `CORE-BASELINE-001`.
- Synthetic operator mechanics are not described as Resident cognition. `isolation_probe` remains self-labelled synthetic with `launchable=false`; the owner-selected protocol remains **rules constraints + process audit**, and no hard-isolation claim is made.

## 4. Duplicate candidate disposition

PR #130 (`core/operator-001-20260924-sol`, head `16eb1d40c1013433166b4dd81669abbcc36b95a9`) is a second window's candidate for the same Task ID. It is registered **SUPERSEDED BY #131**.

It is left OPEN and unmodified. The completion plan does not authorize batch close/delete of duplicate work, and the head stays available as a reviewable historical reference. It must not be merged onto the current main operator surface.

## 5. What this receipt does and does not release

Released:

- `CORE-OPERATOR-001 = DONE`.
- The operator/preflight surface (`tools/c15_preflight/**`, `tests/preflight/**`, `c15-operator-preflight` workflow) is now part of `main` and is the single operator bridge. No second bridge may be created.

Not released:

- This is **not** `SOFTWARE_RC` and **not** `CORE_COMPLETE`.
- `CORE-HEADLESS-001`, `CORE-RECOVERY-001`, `CORE-SCALE-001`, `CORE-RC-FREEZE-001` stay BLOCKED.
- No Resident A/B/C is authorized. Fresh A remains required for the future RC and may only start after `CORE-RC-FREEZE-001`.
- The three accepted RC blockers `CG-001` / `CG-002` / `CG-003` are untouched by this integration.

## 6. Next control state

| Task ID | State after this receipt | Exit |
|---|---|---|
| `CORE-BASELINE-001` | DONE | S0 ruling, pins re-verified 2026-09-24 |
| `CORE-GAP-AUDIT-001` | DONE | PR #132 accepted |
| `CORE-OPERATOR-001` | **DONE** | this receipt |
| `CORE-GAP-FIX-001` | READY / NOT_STARTED | one Core Runtime Engineer window; different independent reviewer |
| `CORE-GAP-FIX-002` | READY / NOT_STARTED | one Core Runtime Engineer window; different independent reviewer |
| `CORE-GAP-FIX-003` | BLOCKED | needs FIX-002 accepted + integrated |
| `CORE-HEADLESS-001` | BLOCKED | needs FIX-001/002/003 accepted + integrated |

Dispatch baseline for all newly released work: live `main` at or after `e72a63874ed2c28798b00cec51f191caf1594a00`. Each engineer window must re-fetch live main rather than pinning this SHA.
