# CORE-RC-REFREEZE-004 — Historical FIX / Recovery Spot Checks

Status: **PASS — 24 passed, 0 failed** (`raw/local/fix_spot_checks.txt`, `raw/local/fix_spot_checks-junit.xml`).

| Check | Fresh node(s) executed |
|---|---|
| FIX-001 historical cutoff | `tests/integration/test_core_headless.py::test_headless_restart_keeps_fix001_historical_knowledge_cut` |
| FIX-002 ambiguous background dispatch | `tests/integration/test_core_gap_fix_002_background_attempts.py` (whole file) + `tests/integration/test_core_headless.py::test_headless_restart_preserves_fix002_background_in_doubt_without_reinvoke` |
| FIX-003 ambiguous user turn | `tests/runtime/test_turn_execution_recovery.py` (whole file: crash, in-doubt, authorization, durable-output restart) |
| Current-time control | `tests/integration/test_v3_fused_turn_runtime.py::test_cg001_current_time_control_keeps_current_fact_visible` |
| Writer/restart & scale | `raw/local/writer_restart_fix_scale.txt` (52 passed) |

These are re-executed fresh against the frozen commit; no prior-window counts were inherited. Trusted-return authenticity guarantees are covered separately in `trusted_return_authenticity_spot_checks.md`; the World-truth boundary in `no_second_truth_store.md`.
