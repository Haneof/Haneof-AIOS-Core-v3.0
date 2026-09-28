# CORE-RC-REFREEZE-003 — Full Regression Evidence

Status: **FORMAL RUN PENDING**. This file will be completed only from the fresh CPython 3.12.14 job bound to exact software `f20f2edfa7af00d0286493fd15196ca9503bc315`. No prior RC/IA counts are substituted.

- Workflow: `.github/workflows/core-rc-refreeze-003-formal-gate.yml`
- Exact target: `f20f2edfa7af00d0286493fd15196ca9503bc315`
- JUnit: `reviews/CORE_RC_REFREEZE_003/ci-output/full-regression-junit.xml`
- Raw console output: `reviews/CORE_RC_REFREEZE_003/ci-output/full-regression.txt`
- Run / job / candidate head: pending GitHub Actions result
- JUnit tests / failures / errors / skipped / time: pending parsed report
- Expected command on target worktree: `python -m pytest -o addopts='' -q --tb=no --junitxml=...`

No Resident A/B/C, real provider, C15 evaluator/close, or persistence WIP branch is part of this gate. If a real software regression is RED, preserve it, set the task `BLOCKED`, and do not patch Core in this task.
