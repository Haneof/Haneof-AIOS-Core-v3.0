# CORE-RC-REFREEZE-004 - Dependency manifest

Frozen package metadata is the exact `pyproject.toml` blob:
`b38833c7537fa60d5c2f02ed4bb19158d8995a11`.

Declared package contract:
- project: `aios-core 0.3.0.dev0`
- Python: `>=3.12`
- runtime dependency: `pydantic>=2.10,<3`
- dev dependency: `pytest>=8,<9`
- build backend: `setuptools.build_meta`
- build requirements: `setuptools>=75`, `wheel`
- console entry point: `aios-core-headless = aios_core.headless.cli:main`

Formal RC004 execution pins:
- CPython `3.12.14`
- Pydantic `2.13.5`
- pytest `8.4.2`

The final exact-head workflow writes the complete `pip freeze` to `dependency-manifest.txt` in the Actions evidence artifact. No lockfile exists in the frozen tree; therefore that runner-produced exact dependency list plus the frozen package metadata is the formal dependency record.
