# CORE-RC-REFREEZE-003 — Authoritative World / No Second Cognition Truth Store

Status: **Source-boundary audit PASS; fresh execution evidence is in the formal regression run.**

## Boundary checked

- `SQLiteWorldStore` owns the authoritative World objects, revisions, operations and idempotency records.
- Trusted-return attempts, request bindings, response receipts, return handoffs and HMAC authenticity authority are persisted in the **same World SQLite file**. The recovery probe checks the required table names in the same `source-world.sqlite` that contains `world_commits`, `object_revisions`, `operations` and `idempotency_records`.
- Metering records are part of the same durable World database. The backup/restore probe compares table definitions and logical row hashes before and after restore, then verifies the preserved receipt/authority against the restored runtime.
- Cognition and policy remain World objects/revisions and are written through the Core's existing World-backed capabilities; no second cognition database, answer oracle, detached reply store, or Resident fixture is introduced by the RC probes.
- `WorldSearchIndex` is a separately rebuildable projection. Its watermark is checked against World revision; `rebuild_index` reconstructs it from the restored World rather than treating it as truth.

## Fresh checks

- The exact-target full suite and selected World/index/cognition/headless/recovery/scale gates run in `.github/workflows/core-rc-refreeze-003-formal-gate.yml`.
- `backup_restore_trusted_return.py` checks same-file durable table presence and exact pre/post-restore logical state.
- `clean_install_headless_smoke.py` uses only a disposable World/index and a deterministic mechanical model handler.
- No test in this task enters C15 evaluator/close, executes Resident A/B/C, or opens `tests/c15_persistence/**` from an unmerged persistence branch.

Fresh formal run and test counts: see `full_regression.md`, `focused_regressions.md`, and `SHA256SUMS`.
