# CORE-RC-REFREEZE-003 — Historical FIX / Recovery Spot Checks

Status: **FRESH FORMAL GATE PASS** on frozen software `f20f2edfa7af00d0286493fd15196ca9503bc315`, run [36436264055](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/36436264055).

All relevant tests are part of the fresh full-suite run (919 passed, 0 failures/errors/skips); the applicable headless/recovery and trusted-return subsets also passed in the 356- and 248-test focused invocations. No separate FIX-only count is inferred.

- **FIX-001 historical cutoff:** `tests/integration/test_core_headless.py::test_headless_restart_keeps_fix001_historical_knowledge_cut`, plus the fused-turn historical-cut and current-time controls.
- **FIX-002 ambiguous background dispatch:** `tests/integration/test_core_gap_fix_002_background_attempts.py` Wake/Periodic Review ambiguous-failure restart and no-reinvoke tests, plus `tests/integration/test_core_headless.py::test_headless_restart_preserves_fix002_background_in_doubt_without_reinvoke`.
- **FIX-003 ambiguous user turn:** `tests/runtime/test_turn_execution_recovery.py` crash, in-doubt, authorization and durable-output restart coverage; headless admission/restart coverage.
- **Current-time control:** `tests/integration/test_v3_fused_turn_runtime.py::test_cg001_current_time_control_keeps_current_fact_visible`.
- **Trusted-return authenticity:** fresh adversarial/transplant/corruption/process-loss and all R1–R5/replay matrices.
- **World truth boundary:** same-World SQLite backup/restore and index rebuild evidence in `no_second_truth_store.md` and `backup_restore_rebuild_smoke.md`.

The full repository and focused JUnit files are hosted in the Actions artifact documented by `formal_gate_run.json`; checksums are recorded there. Historical evidence is provenance only, not a substitute for this run.
