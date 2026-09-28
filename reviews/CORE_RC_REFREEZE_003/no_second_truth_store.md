# CORE-RC-REFREEZE-003 — Authoritative World / No Second Cognition Truth Store

Status: **Source-boundary audit PASS; fresh execution and backup/restore evidence PASS.** This remains a candidate evidence packet, not an independent acceptance verdict.

## Boundary checked

- `SQLiteWorldStore` owns authoritative World objects, revisions, operations and idempotency records.
- Trusted-return attempts, request bindings, response receipts, return handoffs and HMAC authenticity authority are persisted in the **same World SQLite file**. The formal backup probe checks those tables in the same `source-world.sqlite` containing `world_commits`, `object_revisions`, `operations` and `idempotency_records`.
- Metering is part of that same durable World database. The probe compared table definitions and logical row hashes, preserved receipt/authority across supported backup/restore, then recovered without provider redispatch or duplicate effect.
- Cognition and policy remain World objects/revisions written through existing World-backed capabilities; RC probes introduce no second cognition database, answer oracle, detached reply store or Resident fixture.
- `WorldSearchIndex` is a separately rebuildable projection. The restored index watermark was checked against World revision; rebuild reconstructed it from World truth.

## Fresh checks

- Full target pytest: 919 passed, 0 failures/errors/skips.
- World/index/cognition/headless/recovery/SCALE focused invocation: 356 passed, 0 failures/errors/skips.
- `backup_restore_trusted_return.py`: `BACKUP_RESTORE_TRUSTED_RETURN_PASS`; source World and backup immutable; receipt/authority continuous and validated; index rebuilt from World; provider redispatch `0`; one capability effect, two model meter rows.
- `clean_install_headless_smoke.py`: `HEADLESS_CLEAN_INSTALL_PASS`; disposable World and index only, deterministic mechanical adapter.
- Run and complete check record: [36436264055](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/36436264055). Per-table hashes and row counts: `formal_gate_run.json`.
- No test in this task enters C15 evaluator/close, executes Resident A/B/C, resumes persistence Corrective-003, or opens `tests/c15_persistence/**` from an unmerged persistence branch.
