# Corrective-003 RED-first controls

**Scope:** disposable local controls only; no PR #336/#337 refs, files, branches, or workflows were modified. The hosted post-read green control is required separately and is not claimed by these tests.

## IA27-BLK-002 — exact candidate final-seal shell

Before changing the workflow, the exact formal workflow at #336 head `5a5d384f16798bfff46ffe03f87310b0eafb2321` was read-only retrieved from GitHub and saved temporarily outside the repository. Its SHA-256 was `2d9c7862279b16808a158638841419d065d47730a6ebd819b2de2cd13ee9efc3`. The probe extracts and executes the exact final-seal Bash block with mocked GitHub API responses. The mock advances canonical A→B immediately after returning A to the only branch read; the subsequent run and pin-comment responses still bind A. The old seal exits 0 and emits `WHOLE_RUN_IDENTITY_SEAL=PASS` while the mock ref is B.

Raw result: `raw/RED_FIRST_POSTREAD_LOCAL_MOCK.txt`.

**Limit:** this reproduces the vulnerable check-to-completion logic, but does not simulate GitHub Actions concurrency and is not hosted proof. Corrective-003 requires a separate real hosted Actions barrier control.

## IA28-BLK-001 — exact old terminal ERE

Before changing the workflow, the exact initial and terminal `grep -E` expressions were extracted from that same workflow. The probe creates a disposable Git repository with an initial snapshot and a later commit that changes/adds only `.github/workflows/**`, `pyproject.toml`, and `setup.cfg`, while also confirming existing `src/**` and `tests/**` protected classifications. GNU grep 3.8 and `git diff --name-only` show the initial expression catches the workflow/packaging drift but terminal line 464 misses it; terminal still matches `src/**` and `tests/**`.

Raw result: `raw/RED_FIRST_TERMINAL_DRIFT.txt`.

The disposable repository is under a temporary directory and is removed automatically. No repository ref was changed.
