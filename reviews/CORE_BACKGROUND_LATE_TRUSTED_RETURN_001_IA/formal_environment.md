# Formal environment (§29) — WINDOW 14

## Reviewer execution environment (this IA)

| component | formal gate requirement | reviewer sandbox | match |
|---|---|---|---|
| CPython | 3.12.14 | **3.11.2** | ✗ disclosed |
| Pydantic | 2.13.5 | 2.13.5 | ✓ exact |
| pytest | 8.4.2 | 8.4.2 | ✓ exact |
| SQLite | 3.45.1 | **3.40.1** | ✗ disclosed |
| OpenSSL | 3.0.13 30 Jan 2024 | **3.0.20 7 Apr 2026** | ✗ disclosed |

The reviewer sandbox provides no CPython 3.12; pydantic/pytest were pinned exactly
in a dedicated venv (`.venv`, not committed). All IA probe and regression results
above were produced on this environment and are labelled as such. No author CI
result was transferred into the IA verdict.

## Author formal CI identity (fresh GitHub query — evidence, not verdict)

workflow `core-background-late-trusted-return-001`, run `36680355119`, job/check
`109774221264`, head_sha `5ad0524c425592210ff184e00ad52abb2c14e366` (exact),
`pull_request`, attempt 1, conclusion `success`. Check-run annotations re-queried
verbatim:

```
Python 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1 / OpenSSL OpenSSL 3.0.13 30 Jan 2024
late    tests=61,   failures=0, errors=0, skipped=0
accepted tests=249, failures=0, errors=0, skipped=0
surface tests=1,   failures=0, errors=0, skipped=0
full    tests=1059, failures=0, errors=0, skipped=0
```

17/17 exact-head workflow runs `success` on `5ad0524…`.

## Evidence-consistency note

Candidate commit message cites run `36679598965` as "the final head formal gate";
fresh query shows that run's `head_sha = a49c1e6874ecb92ae4dc4783d07d733fdc19fa5d`
(the parent). The authoritative exact-head run is `36680355119` (above), which is
what the Window-13 closing comment and PM release cite. Recorded as
`EVIDENCE-CONSISTENCY-001` (self-reference artifact anticipated by the task; not
counted as a product blocker, but the commit message claim is factually wrong and
should be corrected in the corrective round).
