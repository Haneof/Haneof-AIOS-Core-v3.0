# Writer / restart smoke — GREEN

Covered by `tests/integration/test_core_headless.py` and recovery suite (formal focused SUCCESS; core-headless SUCCESS).

Invariants:

- single-writer lock at `<canonical-world>.writer.lock`
- second writer rejected
- `--lock` / `AIOS_LOCK_PATH` cannot select a second writer identity (bypass = RED; tests remain GREEN)
- restart after clean stop
- restart after abrupt termination (SIGKILL path in corrective-002 recovery tests)
- DB remains valid; World/indexes reopen
- no duplicate side effects / no corruption
