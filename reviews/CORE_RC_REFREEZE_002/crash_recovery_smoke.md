# Crash recovery smoke — GREEN

Process-level SIGKILL (not Python exception simulation) is implemented in:

`tests/integration/test_core_background_response_recovery_001_corrective_002_recovery.py`

It uses `os.kill(..., SIGKILL)` in a child process after a trusted provider return + durable receipt and before response-record completion, then restarts and asserts:

- exact staged recovery
- zero redispatch
- metering exactly once
- output/capability exactly once

Formal focused step SUCCESS under CPython 3.12.14 (run `36314420939`).
