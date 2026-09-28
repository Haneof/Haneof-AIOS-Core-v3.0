# CORE-RC-REFREEZE-003 — Clean-Install / Headless Lifecycle Smoke

Status: **FRESH FORMAL RUN PENDING**.

The workflow builds a wheel from the detached frozen `f20f2edfa7af00d0286493fd15196ca9503bc315` worktree, installs it into a new virtual environment using the exact Pydantic pin, and invokes the installed `aios-core-headless` executable in separate processes.

The disposable deterministic sequence checks: initial World/index status; a mechanical turn using `aios_core.headless.testing:deterministic_model_handler`; stop/restart continuity; a provider-free `recovery-status`; and a final clean reopen. It verifies the same World revision and index watermark, zero index lag, and successful clean close/reopen. A temporary directory owns all generated data and is removed after the result is emitted.

- Real provider: **not used**
- Resident fixture: **not used**
- Expected result marker: `HEADLESS_CLEAN_INSTALL_PASS`
- Raw output: `reviews/CORE_RC_REFREEZE_003/ci-output/clean-install-headless-smoke.txt`
- Clean-install dependency snapshot: `reviews/CORE_RC_REFREEZE_003/ci-output/clean-install-pip-freeze.txt`
- Exact workflow run / output / world revision: pending
