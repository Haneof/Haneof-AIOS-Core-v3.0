# CORE-RC-REFREEZE-002 focused regressions

Formal focused step (CPython 3.12.14) on run `36314420939`: **SUCCESS**.

Files:

- `tests/integration/test_core_background_response_recovery_001_corrective_002_authenticity.py` (frozen blob `6f0c3850368475e166d28d0a6df4b86b610d2c60`, SHA256 `35cba59f318b752ed872821961296f35810443c61db6fd98c8c8f5eee4215225`)
- `tests/integration/test_core_background_response_recovery_001_corrective_002_recovery.py` (includes process-level SIGKILL)
- `tests/integration/test_core_background_response_recovery_001.py`
- `tests/runtime/test_cognitive_runtime_trusted_return.py`
- `tests/integration/test_core_headless.py`
- `tests/integration/test_core_recovery.py`
- `tests/integration/test_core_scale_semantics.py`
- `tests/integration/test_core_gap_fix_002_background_attempts.py`
- `tests/runtime/test_turn_execution_recovery.py`

Probe supporting workflows (same Core tree):

- core-headless `36313973920` SUCCESS
- core-recovery `36313973907` SUCCESS
- core-scale `36313973913` SUCCESS
- c14 runtime/loop/scheduler SUCCESS
- constitutional-cognition-closure SUCCESS
- p16 full suite SUCCESS

Authenticity probes remain GREEN (included in both full and focused SUCCESS steps).
