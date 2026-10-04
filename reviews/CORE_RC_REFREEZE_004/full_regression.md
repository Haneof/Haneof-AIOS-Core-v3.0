# CORE-RC-REFREEZE-004 — Fresh Core Regression Evidence

Status: **PASS (local formal run on the exact frozen worktree)**. This is candidate evidence for independent acceptance, not an acceptance verdict.

Target: frozen software `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`, executed from a detached worktree at that exact commit (`/home/user/.local/frozen-rc004`), never from `main` HEAD.

## Binding Core gate

Command: `python -m pytest -o addopts='' -q tests/unit tests/integration tests/runtime tests/habitation --junitxml=...`

- **928 tests; 0 failed; 0 errors; 0 skipped** (summed case time 181.286 s).
- Raw JUnit: `raw/local/core-gate-junit.xml`; raw console log: `raw/local/core_gate_run.log`.
- The Windows-20 / Window-17 reviewer probes and the Corrective-003 focused suites are inside this gate; their raw outputs are separate files in `raw/local/`.
- The prior window's `928 passed` was **not inherited** — this run was executed fresh against the frozen commit in this window.

## Focused supplementary runs (not added to the 928 count)

| Group | Files | Result |
|---|---|---|
| Trusted-return / recovery / Corrective-002/003 / consumption / secret-upgrade / sigkill / Route B | 23 | **388 passed**, 0 failed (`raw/local/trusted-return-junit.xml`) |
| Core systems (World / cockpit / wake / review / cognition / c14 / headless / recovery / scale / habitation boundary) | 33 | **341 passed**, 0 failed (`raw/local/core-systems-junit.xml`) |
| Historical FIX / recovery / writer-restart / scale spot checks | 6 | **52 passed**, 0 failed (`raw/local/writer_restart_fix_scale.txt`) |
| Real process loss (SIGKILL) selection | 4 files + 3 node ids | **9 passed**, 0 failed (`raw/local/real_process_loss.txt`) |
| FIX-001 / FIX-002 / FIX-003 / current-time control | 4 files + 2 node ids | **24 passed**, 0 failed (`raw/local/fix_spot_checks.txt`) |

## Full repository run (including downstream operator suites)

Command: `python -m pytest -q` over the whole `tests/` tree.

- **1137 tests; 45 failed; 0 errors; 0 skipped** (summed case time 262.065 s).
- All 45 failures are confined to `tests/c15_persistence/**` (7 modules). No failure is in a Core-owned test module, and no Core gate test failed. RED evidence is preserved verbatim in `raw/local/full-repo-junit.xml`; the classification and ruling are in `c15_downstream_adjudication.md`. Nothing was repaired in this window.
- This reproduces the pre-existing downstream `45 failed / 1092 passed` signature exactly (1137 − 45 = 1092 passed).

## Environment

Local formal environment is recorded in `environment_manifest.txt`. Interpreter: CPython 3.12.14 (built from source in the sandbox), Pydantic 2.13.5, pytest 8.4.2, SQLite 3.45.1, Debian 12 (bookworm) / Linux 6.1.158+ / x86_64. The GitHub Actions gate additionally records the runner's OpenSSL and OS identity on the same frozen identity.

## Non-claims

- Not independent acceptance; not PM integration; no Resident A/B/C, no evaluator/close, no public release.
- The CI gate in `.github/workflows/core-rc-refreeze-004-formal-gate.yml` re-runs the binding Core gate and the reviewer probes on the candidate head; its outputs are authoritative for the candidate and are published to the commit comment/artifact.
