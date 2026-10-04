# CORE-RC-REFREEZE-004 — Clean Install / Headless Lifecycle Evidence

Status: **PASS — `HEADLESS_CLEAN_INSTALL_PASS`** from a clean, non-editable install of the frozen source.

## Install

- Clean export of the frozen commit (`git archive 1cee3c5ad12f4b9098232bae11b51df786c5eb2f`) into an empty directory.
- Fresh venv, `pip install --no-build-isolation --no-deps <clean-export>` → `aios-core 0.3.0.dev0` wheel built (`sha256=727e8b26621f1c72f2d91dd819ce37c6a1dcc4300b2c7c80fb0c64f76b98a243`), console script `aios-core-headless` installed.
- No editable install; no network dependency at run time.

## Lifecycle (`raw/local/clean-install-headless.txt`)

Five separate OS processes against a disposable World:

1. initial clean start — revision `0`, writer lease held;
2. one deterministic mechanical turn (`aios_core.headless.testing:deterministic_model_handler`) → revision `2`, `HEADLESS_MECHANICAL_OK`;
3. fresh-process stop/restart — same World, revision `2`, index watermark `2`, lag `0`;
4. provider-free `recovery-status` — `AUTO_RECOVERABLE`, schema `1`, SQLite `quick_check` ok;
5. clean close and final reopen — revision `2`, watermark `2`, files present.

Result line: `status=HEADLESS_CLEAN_INSTALL_PASS`, `separate_cli_processes=5`, `real_provider_used=false`, `resident_fixture_used=false`.

## Boundary

No Resident fixture or Resident semantics were used; this is a disposable World and the deterministic mechanical adapter only.
