# Pre-final hosted fresh-gate run (not the final PR-head run)

**Status:** full hosted formal workflow completed successfully on an exact pre-final candidate. This proves the fresh gate set ran green at that SHA; it is not the final PR-head run and is not Fresh Independent Acceptance. The candidate will advance for final evidence/PR recording, which invalidates the provisional pin below. The final exact PR head must run the formal workflow again after the PR is OPEN.

## Exact run and seal

| Field | Observed value |
|---|---|
| Workflow | `core-rc-refreeze-004-formal-gate` |
| Event | `push` (`[W30-FINAL-FORMAL] Pre-final hosted fresh-gate run — Corrective-003`) |
| Candidate branch / SHA | `arena/01a10c8c-haneof-aios-core-v3-0` / `f2d4918ae00ea37b1841f3ae91e87cc7b04f313f` |
| Run id / number / attempt | `37333325808` / `41` / `1` |
| Run URL | <https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/37333325808> |
| Run started / completed | `2026-10-05T15:30:05Z` / `2026-10-05T15:39:19Z` |
| Formal Job A id / result | `111841703148` — SUCCESS (`5m55s`) |
| Publisher job id / result | `111844459953` — SUCCESS |
| Whole-run identity seal id / result | `111844509346` — SUCCESS (`3m5s`, including the 180-second barrier) |
| Overall run result | **SUCCESS** |
| Provisional commit-comment pin | comment `203512425`, created `2026-10-05T15:36:08Z` |
| Evidence artifact | id `11355277483`, `core-rc-refreeze-004-corrective-003-evidence`, 207,558 bytes, unexpired |
| Artifact download URL | <https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/37333325808> (Artifacts section) |

The pin binds the run to the exact `f2d4918...` SHA and has `gate_kind: formal`, `gate_result: success`, and `publication_state: PROVISIONAL_PENDING_FINAL_IDENTITY_SEAL`. It is not an acceptance decision; after the branch advances it is stale for the live authority predicate.

## Fresh gate results from hosted step conclusions

Formal Job A completed successfully, and each required hosted step was reported `success` by the Actions API:

- exact-head, frozen software identity, initial-main drift, and candidate scope;
- isolated CPython 3.12.14 environment with pinned Pydantic 2.13.5 and pytest 8.4.2;
- Corrective-003 static workflow/security, protected-drift controls, and publisher fault matrix;
- Full Core regression;
- pinned Window20 A/B and Window17 reviewer probes;
- Corrective-003 trust-root, alternate-mint, replay/conflict, supersession, and partial-commit checks;
- real SIGKILL / fresh-process recovery;
- clean non-editable wheel install and headless lifecycle;
- backup/restore rebuild;
- writer/restart/historical FIX/current-time/SCALE checks;
- C15 classifier matrix and actual pytest/JUnit compatibility-debt classification;
- fresh open-PR contamination inventory;
- runtime source manifest and evidence index;
- terminal immutability/protected-drift check;
- complete evidence artifact upload.

The disposable post-read control jobs were `skipped` on this formal-mode push run; the separate hosted A→B control evidence is in `HOSTED_POSTREAD_CONTROL.md`. No test-count claims are made here; the artifact contains the detailed output.

## Artifact access limitation and raw evidence

The API reported the artifact as present, not expired, and 207,558 bytes. Attempts to download through both `gh run download` and the signed Azure blob URL failed with network `EOF` / `SSL_ERROR_SYSCALL`. Therefore this record uses hosted run/job/step conclusions and artifact metadata; it does not claim to have read the artifact's JUnit or text files locally. The artifact remains attached to the run for review. Raw API snapshots are `raw/PREFINAL_FRESH_RUN.json`, `raw/PREFINAL_FRESH_JOBS.json`, `raw/PREFINAL_FRESH_ARTIFACTS.json`, and `raw/PREFINAL_FRESH_PIN_COMMENT.json`.

## Why this is not final

This run preceded the new Corrective-003 PR and its exact final evidence commit. A direct `gh workflow run ... --ref arena/01a10c8c-haneof-aios-core-v3-0` attempt returned HTTP 403 `Resource not accessible by integration`; therefore this pre-final fresh-gate run was triggered by a push marker and is explicitly **not** a substitute for the required final `workflow_dispatch`. After the final evidence commit is on the new OPEN PR head and GitHub Actions dispatch permission is available, dispatch the full workflow on that exact head; record its run/artifact/pin identity in the PR. Until then, do not label this task acceptance-passed or merge-ready. Final disposition after that exact-head run remains limited to `CORE-RC-REFREEZE-004-CORRECTIVE-003 = READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE`.
