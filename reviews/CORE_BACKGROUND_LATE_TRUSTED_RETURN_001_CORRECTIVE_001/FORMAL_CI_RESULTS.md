# FORMAL_CI_RESULTS

Required workflow:
`.github/workflows/core-background-late-trusted-return-001.yml`

Formal runtime is pinned to:
- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2

The implementation head before this evidence-only commit passed run `37024480885`.

The workflow now exports exact JUnit/environment artifacts for:
- Route-B + CA1-CA5;
- accepted trusted-return regression;
- real SIGKILL;
- focused trusted-return/recovery regression;
- full Core regression.

Because a commit cannot contain the GitHub run id that will only be allocated after that commit exists, the authoritative exact-final-head run id/job ids/counts are recorded in the PR #308 conversation and Window 16 terminal report after CI completes. No parent run is substituted for final-head CI.
