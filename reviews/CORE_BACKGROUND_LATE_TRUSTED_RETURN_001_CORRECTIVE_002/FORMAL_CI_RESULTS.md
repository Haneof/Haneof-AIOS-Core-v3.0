# FORMAL_CI_RESULTS — workflow `core-background-late-trusted-return-001`

Formal runtime required by the Window 19 mandate: **CPython 3.12.14**, pydantic
2.13.5, pytest 8.4.2, SQLite 3.45.1, OpenSSL 3.0.13.  That interpreter cannot be
installed in the authoring sandbox (every distribution host is blocked and a source
build is impossible without C development headers), so the formal evidence is the
GitHub Actions run below, which used `actions/setup-python@v6` with
`python-version: "3.12.14"` and `pip install -e . pydantic==2.13.5 pytest==8.4.2` in
every job.

## Exact-head run (code/test head)

| Item | Value |
| --- | --- |
| Workflow | `core-background-late-trusted-return-001` |
| Run id | `37098941757` |
| URL | https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/37098941757 |
| Event | `pull_request` (PR #310) |
| `head_sha` | `7db79da54b26266c5ec519f3e70dd25dff4a95fb` ← exact candidate code/test head |
| `head_branch` | `arena/01a10010-haneof-aios-core-v3-0` |
| Conclusion | **`success`** (all five jobs) |
| Started / finished | `2026-10-03T05:10:02Z` → `2026-10-03T05:15:35Z` |

### Jobs and every step

| Job id | Job | Conclusion | Steps (all `success`) |
| --- | --- | --- | --- |
| `111134485108` | `red-first-window14` | success | checkout / setup-python 3.12.14 / materialize failed candidate + W14 probes / install deps / verify frozen probe SHA-256 / reproduce W14 RED / upload artifact |
| `111134549196` | `phase-a-truthfulness` | success | install deps / compile changed Python / diff hygiene / focused Route-B truthfulness |
| `111134635708` | `phase-bc-verifier-only` | success | install deps / compile / diff hygiene / Route-B and CA1–CA5 (now incl. `test_late_return_canonical_encoding_002.py`) / accepted trusted-return regression / export JUnit |
| `111134709816` | `phase-ef-sigkill-and-focused` | success | install deps / real SIGKILL + fresh-process recovery / focused regression (now incl. `test_core_background_late_trusted_return_corrective_002.py`) / diff hygiene / export JUnit |
| `111134828002` | `phase-f-full-core-regression` | success | install deps / formal environment / compile every changed Python file / full Core regression (`tests/unit tests/integration tests/runtime tests/habitation`) / **resident-visible behavioural gate** / **scope guard** / export final evidence |

Step-level conclusions were read from `api.github.com`; the resident-visible gate and
the scope guard both passed in CI, which independently confirms that the local-only
`test_resident_surface` deviation reported in `GREEN_RESULTS.md` §5 is an artifact of
the authoring sandbox's local `main` ref and not a Corrective-002 regression.

## Artifacts produced by the run (exist, unexpired)

| Artifact id | Name | Size | sha256 digest |
| --- | --- | --- | --- |
| `11265367291` | `window16-phase-bc` | 4194 B | `5ad06d222feba42e5540140928e62ae1b2715ad7c76a5f25327966e0ee0df93b` |
| `11265014065` | `window16-formal-final` | 21581 B | `666d8b68b4cc6bf4d282838e9735f5d558700b0ca2fb6e6c31b8d649e67739f5` |
| `11264809142` | `window16-phase-ef` | 6027 B | `ffab4946ee541372b0a521c5399aba6aeb63a1f38bd9bf9b4211a29e4bd3ea44` |
| `11264769226` | `window16-red-first` | 4481 B | `222d58003dd73fe1cd5c5a6802112cc730f00c5af0ef08be321d0e94580079b3` |

## Disclosed limitation — `OBSERVATION-C002-002`

The authoring sandbox cannot retrieve artifact bytes or job logs: both
`productionresultssa19.blob.core.windows.net` and
`results-receiver.actions.githubusercontent.com` fail to connect (curl exit `000`)
while `api.github.com` and `github.com` work, and the job HTML page served by
`github.com` contains no log text.  Consequently the **byte-level formal JUnit
counts** (`/tmp/window16-core-junit.xml` summary line
`WINDOW16_CORE tests=… failures=… errors=… skipped=…`, `/tmp/window16-core-counts.txt`,
the phase JUnit XMLs and `/tmp/window16-formal-environment.txt` with the formal
Python/pydantic/pytest/SQLite/OpenSSL versions) live inside the artifacts above and
could not be read from the authoring environment.

Nothing is claimed about those byte-level numbers here.  Window 20 Fresh Independent
Acceptance should download the artifacts (they are unexpired, ids and digests above)
for the exact formal counts and the formal runtime banner.  This is a retrieval
limitation only; it is not `FORMAL_CI_NOT_EXACT_HEAD` (the run's `head_sha` equals the
candidate head) and not a CI failure.

## Local pre-flight of the identical phases (CPython 3.11.2, non-formal)

| Phase / step | tests | failures | errors | skipped |
| --- | --- | --- | --- | --- |
| `phase-a-truthfulness` | 35 | 0 | 0 | 0 |
| `phase-bc-verifier-only` Route-B and CA1–CA5 | 85 | 0 | 0 | 0 |
| `phase-bc-verifier-only` accepted regression | 50 | 0 | 0 | 0 |
| `phase-ef` real SIGKILL | 1 | 0 | 0 | 0 |
| `phase-ef` focused regression | 291 | 0 | 0 | 0 |
| `phase-f` full Core regression | 896 | 0 | 0 | 0 |
| new `test_late_return_canonical_encoding_002.py` | 64 | 0 | 0 | 0 |
| new `test_core_background_late_trusted_return_corrective_002.py` | 20 | 0 | 0 | 0 |
| frozen Window 17 probes | 14 | 0 (probe summary `probes=14 failures=0`) | — | — |

## Final candidate head

The final candidate head is the tip commit of PR #310, which adds this file and
`FINAL_HANDOFF.md`.  Its `src/`, `tests/` and `.github/` content is byte-identical to
the CI-validated code/test head (`git diff --name-only 7db79da..HEAD -- src tests .github`
is empty), and the workflow run at that final head is recorded in the PR #310
description.
