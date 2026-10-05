# CORE-RC-REFREEZE-004 - Fresh Core regression

Frozen software: `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`.

Preflight run `37210904177` executed CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 against the exact detached frozen software worktree and produced:

- `tests/unit tests/integration tests/runtime tests/habitation`: **928 passed / 0 failed / 0 errors**.
- The run later failed in a stale RC003 backup probe, after Core regression, reviewer probes, Corrective-003 security, real SIGKILL and clean-wheel headless had already passed. That later evidence-probe failure does not rewrite the 928-test result.
- Final authority is the final immutable candidate's exact-head workflow run. Its run id and raw artifact are pinned after execution in the candidate PR/commit comment without changing the candidate SHA.

No historical accepted-candidate count is used as RC004 regression evidence.
