# CORE-RC-REFREEZE-003 — Writer / Restart / No-Duplicate-Effect Evidence

Status: **FRESH FORMAL RUN PENDING**.

Exact frozen headless regressions include canonical same-World writer exclusion, alternate/overridden lock-path rejection, stale lock metadata without an OS lease, relative/absolute/symlink World identity, clean stop/restart, FIX-002 ambiguous dispatch recovery, and FIX-003 user-turn in-doubt recovery. The clean-install probe separately opens the installed headless package in five independent CLI processes and checks World/index continuity. The trusted-return recovery suites assert that recovery does not redispatch the provider and does not duplicate metering or capability effects.

Relevant exact-target tests:

- `tests/integration/test_core_headless.py`
- `tests/integration/test_core_recovery.py`
- `tests/integration/test_core_gap_fix_002_background_attempts.py`
- `tests/runtime/test_turn_execution_recovery.py`
- trusted-return recovery/process-loss JUnit group

Formal run / JUnit counts / smoke outcome: pending.
