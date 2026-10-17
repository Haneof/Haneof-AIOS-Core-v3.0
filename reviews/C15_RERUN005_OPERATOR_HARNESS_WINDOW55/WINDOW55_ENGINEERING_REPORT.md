# WINDOW 55 — RED-first execution and blocked engineering handoff

**FORMAL_TASK:** `C15-RCC-RES-A-RERUN-005-OPERATOR-HARNESS-CORRECTIVE-002`  
**STATUS:** `BLOCKED / RED-FIRST_REPRODUCED_WITH_LIMITATIONS / NOT_REVIEW_READY / DO NOT_MERGE`.

This is an **operator-only** engineering report. No approved Resident-safe packet or launch permission is produced.

## Fresh GitHub identity

- Live main: `271fa28d695efaeb1c888d93024eeddac9c8aa9f`
- Historical PR #361 OPEN / UNMERGED; failed head `67da1125c4902380dafde98a0ccf01c42e590864`, tree `5fe6d60cbea2b0725e7f2f7e37ef85611220b9c5`, parent main
- Primary evidence PR #362 OPEN, head `20487ded68081d377de19a03f533e6619b441560`
- Secondary evidence PR #363 OPEN/DRAFT, head `a29b87d32cac24e73716277702ff777b94d674a9`
- Core subtree `16f1487e291b009c55bee402abfd79fdacbae960`; C15 subtree `b8a62370e6ffe80730b2ef4c17d625fab50446d4`
- PR #361 source under `reviews/**`, product trees unchanged. Authenticated GitHub API verified commits, trees and file lists; did not trust author narrative.
- `git fetch --all --prune` attempted and FAILED, exit 128 (`Could not resolve host: github.com`). Prior uploaded workspace ZIP contained OLD git objects; it was never called the approved repo.

## Frozen original-source RED-first tests

- **PM54-BLK-001**: `RED_FIRST/attack_exact_check_imports.py` uses SHA-pinned PR361 `r005/checks.py` with actual CPython3.12.14. Attacked both `r005/checks.so` and `aios_core/headless/core.so` in separate synthetic roots. In BOTH cases original `.py` manifest unchanged, malicious native extension imported and ran, exact candidate `checks.verify()` and `loaded_modules()` still falsely PASS. Script process exit **0 = attack success / defense FAIL**, not security PASS.
- **PM54-BLK-002**: `RED_FIRST/attack_exact_publisher.py` launches actual byte-verified PR361 `publisher_service.py` in separate approved 3.12.14 process with synthetic Core/Bridge stubs. Another same-UID attacker sent forged PID of an idle genuine Runner. Actual Publisher answered `{ok:true,registered:...}` for attacker-chosen attempt context. Process exit **0 = attack success / defense FAIL**. Signing, semantic response application, C15 were **NOT** tested.
- **PM54-BLK-003**: `RED_FIRST/attack_completion_sigkill_git.py` simulates PR361 `safe_runner.py` source sequence; real child writes/fsyncs a `completed` marker, gets `SIGKILL` **-9** before remote CAS; a real disposable bare Git remote retains previous generation head and lacks the operation; the exact candidate recovery predicate returns local `SUCCESS`. Process exit **0 = source-order witness success / defense FAIL**. **Does NOT import the accepted C15 backend/actual full Runner**, so binding acceptance-level RED remains partially unexecuted.

## Reviewer freeze / independent hash audit

- PR #362 Markdown embedded scripts `ia54_a01_native_shadow.py`, `ia54_a05_forged_pid_v3.py`, `ia54_a10_completion_gap.py`, `test_ia54_fail_closed.py`, `ATTACK_PLAN.json` were independently SHA-256 checked on exact bytes and all match report. PR #363 source archive freeze was checked locally for 3 scripts.
- Reran PR #363 two synthetic PoCs on approved Python3.12.14: two tests PASSED / exit0, meaning two attacks established (not defensive regression).

## Prototypes: NOT a corrected candidate

- `corrective_worktree/launch.py` and `r005/checks.py` are test-only import-hardening prototypes. Seven synthetic scenarios PASS (baseline; `.so` shadows for Harness and Core; `.pyc`; symlink; changed bytes; duplicate hardlink), **not** full production/Core/C15 regression.
- Kernel `SO_PEERCRED` probe in this sandbox distinguishes real peer PID from forged JSON PID and rejects same-UID attacker (exit 0). Socket availability in Window51 sandbox is **not proven**. No Publisher and Runner integration or scope-binding closure exists yet.
- Completion durability correction is **NOT implemented**; its five required accepted-C15 failure-injection points remain UNEXECUTED.

## Binding blockers / stop

The environment cannot fetch the exact repository or run the 38 author regressions and full synthetic mechanical chain against approved current Core/C15. No fully corrected Harness Manifest, artifact, safe packet, cross-sandbox verification, or new approved PR candidate exists yet. 38/38 historical author claims are NOT new tests. No false-green result.

**No PR #361/#362/#363 edit; no Core/C15 product change; no real Resident / cursor reveal; no merge.**

`WINDOW_55 = BLOCKED / FULL_CORRECTIVE_AND_DYNAMIC_INTEGRATION_REQUIRED / DO NOT MERGE`.
