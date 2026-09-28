# Reviewer environment record

- IA candidate: `10901d467679b70437ae112747eab81f889fd5cb`
- Independent scratch runtime: `/tmp/aios-review-runtime`
- Bootstrap result: clean build exit 0; `CPython 3.12.14`, `Pydantic 2.13.5`, `pytest 8.4.2`, `SQLite 3.45.1`
- OpenSSL: `OpenSSL 3.0.13`
- OS/kernel/architecture: captured by bootstrap at build time; reviewer sandbox Linux x86_64
- frozen import source used for gate rerun: `/tmp/frozen-worktree/src/aios_core` at `f20f2edfa7af00d0286493fd15196ca9503bc315`
- `aios_core.__file__`: Gate B imports from `/tmp/frozen-worktree/src/aios_core` via explicit `PYTHONPATH`; no system package or reviewer branch was used.
- bootstrap `--verify` succeeded, but emitted `WARNING: repo git metadata unavailable` for a standard Git worktree because it tests `[ -d .git ]` and a worktree has a `.git` file. Independent `rc_identity.py` verification separately passed against the frozen worktree.
- full candidate gate rerun: `33 passed in 3.03s` under the qualified interpreter (raw output in `raw/reviewer_gate_run.txt`).
- no real Resident, C15 release-state, cursor reveal, fixture payload, evaluator source, or Phase A run was executed/opened.
