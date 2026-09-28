# CORE-RC-REFREEZE-003 — Historical FIX / Recovery Spot Checks

Status: **FRESH FORMAL RUN PENDING**.

The fresh target suite covers:

- **FIX-001 historical cutoff:** `tests/integration/test_core_headless.py::test_headless_restart_keeps_fix001_historical_knowledge_cut`, plus `test_v3_fused_turn_runtime.py` historical-cut and current-time controls.
- **FIX-002 ambiguous background dispatch:** `tests/integration/test_core_gap_fix_002_background_attempts.py` wake/review ambiguous-failure restart tests, plus headless no-reinvoke coverage.
- **FIX-003 ambiguous user turn:** `tests/runtime/test_turn_execution_recovery.py` and `tests/integration/test_core_headless.py` restart/admission coverage.
- **Current-time control:** `tests/integration/test_v3_fused_turn_runtime.py::test_cg001_current_time_control_keeps_current_fact_visible`.
- **Trusted-return authenticity:** fresh adversarial/transplant/corruption tests and all R1-R5/replay matrices.
- **No second World/cognition truth store:** source-boundary audit and World database recovery/backup checks in `no_second_truth_store.md` and `backup_restore_rebuild_smoke.md`.

Fresh run / exact JUnit counts / result: pending.
