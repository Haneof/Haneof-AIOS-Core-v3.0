# Probe 00 — independent clean bootstrap reproduction (frozen BEFORE first execution)

Frozen at: 2026-09-28 (before any candidate code was executed by this reviewer).

Procedure:
1. `git clone` the local repository object store into fresh scratch `/tmp/ia/clone`
   (real `.git` directory), `git checkout --detach 10901d467679b70437ae112747eab81f889fd5cb`.
2. Verify `sha256(bootstrap/bootstrap_runtime.sh) == b496080238d732cf5e90c4e385769a7689214e5bf8901765926cb925e02e4823`.
3. Run `AIOS_RUNTIME_ROOT=/tmp/ia/rt bash <bootstrap> --build` from the empty root `/tmp/ia/rt`
   (no reuse of any author `/opt/aios`; none exists in this sandbox).
4. Run `--verify`.

Expected outcomes (declared before execution):
- E00.1 build exit 0; all upstream tarball SHA-256 pins verify.
- E00.2 venv reports CPython 3.12.14, Pydantic 2.13.5, pytest 8.4.2, SQLite 3.45.1.
- E00.3 `sys.base_prefix` is under `/tmp/ia/rt/runtime/3.12.14/python` (no system Python).
- E00.4 `sqlite3` module links `/tmp/ia/rt/runtime/3.12.14/deps/lib/libsqlite3.so.0` (no system sqlite).
- E00.5 frozen RC identity check logs `frozen RC identity OK`.
- E00.6 source tree `git status --porcelain` in the clone stays empty (bootstrap writes nothing to source tree).
- E00.7 wheel set: record which transitive wheels are pulled; compare with author environment_record wheels.
  (Expectation: pydantic/pytest exact; transitive deps are NOT pinned by the bootstrap and may differ.)
