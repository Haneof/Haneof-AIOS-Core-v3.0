# CORE-RC-REFREEZE-003 — Clean-Wheel / Headless Lifecycle Smoke

Status: **PASS** in fresh formal run [36436264055](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/36436264055), candidate head `f2ef4886cbd7253543e82debbaa14ea387417f03`.

The gate built a wheel from detached frozen target `f20f2edfa7af00d0286493fd15196ca9503bc315`, installed it into a new virtual environment with `pydantic==2.13.5`, and invoked the installed `aios-core-headless` console entrypoint in separate OS processes. The handler was `aios_core.headless.testing:deterministic_model_handler`.

Observed marker: **`HEADLESS_CLEAN_INSTALL_PASS`**.

- Initial World revision: `0`
- Final World revision: `2`
- Final index watermark: `2`; index lag `0` (verified by the probe)
- Restart continuity: `true`
- Provider-free safe `recovery-status`: `recovery_status`
- Clean close/reopen: `true`
- Separate CLI process count: `5`
- Real provider used: `false`
- Resident fixture used: `false`
- All state lived under disposable temporary World/index paths and was removed after the probe.

Artifact file SHA-256 values:

- `clean-install-headless-smoke.txt`: `e21ae616f760da9689ec58341dba9e2546f2a00d7ad8bc367ac36b773ce0d9b0`
- `wheel-build.txt`: `7730f1f315da51bd9b9822666b65cdb6e600210f700c3d0c797df829408740c9`
- `clean-install-pip-freeze.txt`: `56003b1015e0acef77749ba2f52ba70b7c7b274f8bef048e69d44baef3fa823c`
- `clean-install-pip.txt`: `84cb7fc0fdce7f83716ed42bdc76a62b63582e7d9976a878b1e1ab0dedb89354`

The exact output is in artifact `core-rc-refreeze-003-36436264055`; archive digest and artifact metadata are in `formal_gate_run.json`.
