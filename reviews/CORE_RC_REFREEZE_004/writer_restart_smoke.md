# CORE-RC-REFREEZE-004 — Writer / Restart / No-Duplicate-Effect Evidence

Status: **PASS — `WRITER_RESTART_PASS`** on the frozen target (`raw/local/writer-restart.txt`).

## Fresh probe

`probes/writer_restart_smoke.py` exercises the canonical headless writer boundary:

- first writer holds the canonical OS lease (`world.sqlite.writer.lock`);
- a **second writer is refused in-process and in a fresh OS process** (`World writer already active: ...`);
- a `lock_path` override is refused as validation-only (`HeadlessConfigurationError`); the writer lease identity follows only the resolved canonical World path;
- **stale diagnostic lock metadata does not block a legal restart** (metadata is diagnostic; the OS lease is authoritative): after stop + stale metadata rewrite, a fresh writer starts `ready`;
- clean stop releases the lease; restart preserves World revision `2`, index watermark `2`, lag `0`;
- re-submitting the same completed turn after restart **fails closed** (`TurnAlreadyCompleted`) with **meters unchanged** (1) and **no duplicate effect** (revision unchanged).

## Supplementary test coverage (52 passed, `raw/local/writer_restart_fix_scale.txt`)

`tests/integration/test_core_headless.py`, `tests/integration/test_core_recovery.py`, `tests/integration/test_core_gap_fix_002_background_attempts.py`, `tests/runtime/test_turn_execution_recovery.py`, `tests/integration/test_v3_fused_turn_runtime.py::test_cg001_current_time_control_keeps_current_fact_visible`, `tests/integration/test_core_scale_semantics.py`.

## Boundary

The verified contract is same-World single-writer exclusion and validation-only lock override in the supported local process/filesystem model. No distributed multi-host/HA guarantee is claimed.
