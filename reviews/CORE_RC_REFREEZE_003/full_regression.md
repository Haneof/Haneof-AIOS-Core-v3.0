# CORE-RC-REFREEZE-003 — Full Regression Evidence

Status: **FORMAL GATE PASS** — evidence is ready for independent acceptance; no self-acceptance is claimed.

- Frozen software: `f20f2edfa7af00d0286493fd15196ca9503bc315`
- Repository tree: `1ac3a675b884167d3a29aa432e7ef3eaff94d404`
- Workflow run: [36436264055](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/36436264055)
- Job/check: `108974868566`
- Candidate head checked: `f2ef4886cbd7253543e82debbaa14ea387417f03` (the final PR evidence-only commit receives its own fresh PR gate check)
- Environment: CPython 3.12.14, Pydantic 2.13.5, pytest 8.4.2, SQLite 3.45.1, Ubuntu 24.04.5 LTS, x86_64.

## Result

The complete repository pytest command ran from the detached exact frozen-software worktree with the isolated formal environment:

```text
python -m pytest -o addopts='' -q --tb=no --junitxml="$RC003_OUTPUT/full-regression-junit.xml"
```

**919 tests; 0 failures; 0 errors; 0 skipped.** JUnit testcase-time sum: `202.963 s` (not the job's wall-clock duration). The full formal job completed successfully in 5m 07s and all named regression, smoke, backup/restore, summary and upload steps succeeded.

- JUnit: `ci-output/full-regression-junit.xml` — SHA-256 `b7068ef516256d7380fa5d331817969c44dc1c24498b50997185b495827c2e58`
- Raw pytest console: `ci-output/full-regression.txt` — SHA-256 `254679855d852bee0d94c19ca10fa2e210a265d121641b4862fc0d20c1024bbd`
- Frozen identity record: SHA-256 `4e0cdb68ecff875989b894c288dfed67891d77906cb141a9625fc03aaadeef4b`
- Artifact archive: `core-rc-refreeze-003-36436264055`, ID `10976116271`, 46,758 bytes, server-reported SHA-256 `783b04438acbb982b584c3b6457727604d45695558a46f7d12a3574399bacb71`.

The three JUnit outputs and raw logs are hosted in that Actions artifact. All artifact file checksums are in `formal_gate_run.json`. The sandbox could not download the archive (Actions Blob EOF/SSL failure); its absence locally is disclosed rather than represented as a local verification.

No prior RC/IA/PM test total substitutes for this fresh run. No Core implementation or tests were changed by this re-freeze candidate.
