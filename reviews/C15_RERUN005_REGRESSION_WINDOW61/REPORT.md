# Window 61 — existing regression phase

Disposition: REGRESSION_FAILED / FORMAL_VALIDATION_BLOCKED / DO NOT MERGE.

Executed exclusively through browser VS Code terminals in existing Codespace verbose-space-couscous-jx7w7v5qgr6fvr4. No Work Linux execution.
Candidate: 9d3b19b0e7bf090e5d472d9781b9156f73ea2088
Tree: ba3d75c309e144e5e93a32de5582f9b26da925ed
Parent: adf391178d7494ed17e1db802a31f001fb3b5f3b
Fresh origin/main: 271fa28d695efaeb1c888d93024eeddac9c8aa9f

Window60 manifest: 16/16 entries OK. Approved runtime archive bytes, binary, all 4426 materialized regular files and permissions passed revalidation. Gate0 passed before scope was narrowed. Current-stage verification reconfirmed Python 3.12.14, Pydantic 2.13.5, pytest 8.4.2, SQLite 3.45.1, OpenSSL 3.0.13, binary SHA256 09605fdfbe88ca0d45a575ab8179cecd2a7167d95555b7bb8e6f29f29e82d42b.

## Results

| Run | Result | Exit |
|---|---|---|
| Original38, initial permissions | 28 PASS / 10 FAIL / 0 ERROR / 0 SKIP | 1 |
| Window55, initial permissions | unittest ran 33; 13 failure events and 3 errors; original JUnit has 32 cases: 25 pass / 4 failure / 3 error | 1 |
| Window57, initial permissions | 29 PASS: 22 delivery + 7 contract helpers | 0 |
| Original38, frozen manifest permissions | 32 PASS / 6 FAIL / 0 ERROR / 0 SKIP | 1 |
| Window55, frozen manifest permissions | 33 PASS / 0 FAIL / 0 ERROR / 0 SKIP | 0 |
| Window57, frozen manifest permissions | 29 PASS: 22 delivery + 7 contract helpers; no failures/errors/skips | 0 |

The initial Window55 runner/JUnit discrepancy is retained; it is not repaired or described as 33 recorded XML cases. Raw stderr and original XML are included.

## Remaining original38 failures

Five full-process cases expect an authorization line on Runner stdout: crash-recovery and USER/due/Summary/delivered integration. Current implementation sends per-request authorization to controlling TTY. Each receives no matching stdout line and ends with response-wait expiry. All five remain FAIL. The crash case fails before its intended kill/recovery assertion, so proves no completed recovery scenario.

The sixth case expects importing r005.publisher_service to raise ImportError. It does not. This unchanged assertion remains FAIL; passing helpers do not supersede it.

## Source and environment handling

Restored five original test files plus draft_runner.py from 67da1125c4902380dafde98a0ccf01c42e590864; all six hashes rechecked after testing. Sixteen Window55/57 Python sources matched frozen candidate bytes. No assertion, skip, xfail, product source, Harness source or PR367 commit was changed.

Disposable detached worktree: /workspaces/window61-evidence-BeuoJ6pm/candidate. Checkout inherited modes including 0666 on protected files; all initial failures retained. Only this disposable worktree's protected modes were materialized exactly from existing IDENTITY.json, changing no bytes or manifest. Pinned verify then returned HARNESS_IDENTITY_AND_ROUTER_PASS. Mode changes are recorded in pinned-mode-materialization.json. Original Codespace checkout and poetry.lock were preserved. Historical tests are the only untracked addition in candidate worktree.

## Scope and limits

Latest user instruction limits this phase to existing regression/delivery tests. Additional Route B dynamic work, cross-Codespace delivery and full fault matrix: BLOCKED / NOT_EXECUTED under revised scope, never PASS. No private-material extraction, process-memory inspection or supplemental impersonation was performed. Other prior work consisted of source/contract reads and Gate0 on disposable processes.

Historical PM54 blockers remain UNVERIFIED for formal closure. PM contract adjudication remains REQUIRED. This is not independent acceptance or Resident launch authorization.

PR_367_UNCHANGED=YES
REAL_RESIDENT_STARTED=NO
CURSOR_1_REVEALED=NO
INDEPENDENT_ACCEPTANCE=NOT_STARTED
CROSS_SANDBOX_DELIVERY=BLOCKED
REAL_CORE_C15_INTEGRATION=BLOCKED
REAL_SIGKILL_RECOVERY=BLOCKED
LEGACY_IMPORT_ASSERTION=FAIL
FINAL_DISPOSITION=FORMAL_VALIDATION_BLOCKED
REGRESSION_DISPOSITION=FAIL
DO_NOT_MERGE=YES

Raw outputs remain in /workspaces/window61-evidence-BeuoJ6pm. Package includes selected logs, all JUnit files, per-case outcomes, command histories and hashes. No runtime archive or test-state database is published.
