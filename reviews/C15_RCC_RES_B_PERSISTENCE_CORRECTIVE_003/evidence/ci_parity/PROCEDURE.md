# CI-parity corrective — evidence procedure

Corrective-003 candidate `d49f513131d73d208bea0b5da601f435c7386d92` was pushed and opened as draft PR
#299. Three repository formal gates then ran **red**:

| gate | job | observed |
| --- | --- | --- |
| `formal-core-gate` (`core-background-trusted-return-recovery-001`) | 109486347554 | fail after 19 s |
| `formal-python312-full-suite` (`core-rc-refreeze-002-formal-gate`) | 109486343185 | fail after 16 s |
| `full-core-regression` (`p16-convergence-gate`) | 109486345353 | fail after 14 s |

## Root cause

Those gates invoke a **bare** `pytest` (`pytest -q --tb=no --junitxml=...`, and `pytest -o addopts=''
--collect-only -q`). A bare `pytest` does *not* put the current directory on `sys.path`; only
`python -m pytest` does. The probes under `tests/c15_persistence/**` import `tools.c15_persistence` from the
repository root, so collection aborted:

```
tests/c15_persistence/test_operator_wiring.py:32: in <module>
    from tools.c15_persistence.backend import (  # noqa: E402
E   ModuleNotFoundError: No module named 'tools'
!!!!!!!!!!!!!!!! Interrupted: 6 errors during collection !!!!!!!!!!!!!!!!!
```

exit code `2`, i.e. the same signature as the three failing CI jobs (they fail in ~15 s, before any test
runs). Every local GREEN run in `evidence/` had used `python -m pytest`, which inserts the current directory
and therefore masked the defect. The same defect is inherited from the frozen WIP (PR #254's formal gates were
red as well); **no probe semantics, no probe expectation and no blocker conclusion is involved**.

## Fix

`tests/c15_persistence/conftest.py` (new, additive) prepends the repository root and `src` to `sys.path` for
this directory only. Deliberately **not** done: no root `conftest.py`, no global pytest configuration change,
no packaging change, no `.pth` file, no harness installation, no `src/aios_core/**` change. The frozen probe
sources are untouched — the matrix `sources` hashes still match `frozen/CORRECTIVE_003_PROBE_MATRIX.json`
exactly, so no re-freeze was required or performed.

## CI-parity simulation (exact commands)

A CI checkout is a fresh, single-commit, history-less tree, and the namespace probe replaces `/tmp` with a
tmpfs, so the simulation lives outside `/tmp`:

```bash
git archive HEAD | tar -x -C /home/user/c15-ci-sim        # tree of the candidate commit
cd /home/user/c15-ci-sim && git init -q && git add -A && git commit -q -m sim   # depth-1-like history, no main ref
cp <candidate>/tests/c15_persistence/conftest.py tests/c15_persistence/conftest.py
```

then, with the candidate interpreter (CPython 3.11.2 / Pydantic 2.13.5 / pytest 8.4.2, the disclosed delta):

```bash
pytest -o addopts='' --collect-only -q | tail -n 4      # formal-core-gate step 2
pytest -o addopts='' -q tests/c15_persistence           # persistence subset
pytest -q --tb=no --junitxml=<out>.xml                  # formal-python312-full-suite / full-core-regression
```

## Results

| run | result | log |
| --- | --- | --- |
| bare `pytest -q`, pre-fix state (RED) | exit `2`, `ModuleNotFoundError: No module named 'tools'`, 6 collection errors | `RED_bare_pytest_collection_error.log` |
| `pytest -o addopts='' --collect-only -q` | exit `0`, **997 tests collected** | `GREEN_formal_gate_enumerations.log` |
| `pytest -o addopts='' -q tests/c15_persistence` | exit `0`, **78 passed** | `GREEN_bare_pytest_c15_subset.log` |
| `pytest -q --tb=no --junitxml=...` (whole repository) | exit `0`, **tests=997 failures=0 errors=0 skipped=0** | `GREEN_bare_pytest_full_suite.log`, `GREEN_bare_pytest_full_suite_summary.txt` |

The whole-repository JUnit line is byte-identical in meaning to the local GREEN run (997 tests, 0 failures),
so the previously published GREEN evidence remains valid and is now reproducible under the CI invocation as
well. The candidate tree was re-frozen after this corrective and re-published; the three formal gates above
are re-executed by GitHub on the new head to confirm the fix end to end.
