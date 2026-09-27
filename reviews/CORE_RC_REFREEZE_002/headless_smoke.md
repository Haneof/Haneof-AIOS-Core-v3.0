# Headless smoke — GREEN

- Workflow `core-headless` run `36313973920` SUCCESS (34s) on probe with identical Core.
- Formal focused includes `tests/integration/test_core_headless.py` SUCCESS under 3.12.14.
- CLI entrypoint unchanged: `aios-core-headless = aios_core.headless.cli:main`
- Invariants covered by existing tests: clean startup, no UI dependency, same-World writer exclusion, alternate lock-path cannot bypass canonical `<world>.writer.lock`, restart.
