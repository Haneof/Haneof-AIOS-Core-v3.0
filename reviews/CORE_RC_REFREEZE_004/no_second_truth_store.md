# CORE-RC-REFREEZE-004 — Authoritative World / No Second Cognition Truth Store

Status: **Source-boundary audit PASS; fresh execution PASS.**

## Boundary checked

- `SQLiteWorldStore` owns authoritative objects, revisions, operations, commits and idempotency records.
- Trusted-return state — attempt bindings, external return verifiers, response receipts, return handoffs and exact staged responses — is persisted in the **same World SQLite file** as world commits/objects/operations/idempotency/metering. The §10 probe compares per-table logical state before backup and after restore on that single file.
- The search index (`WorldSearchIndex`) is a **separately rebuildable projection**: the restored World file contains no index tables, and `rebuild_index` reconstructs the projection from World truth with watermark == World revision and lag 0.
- Metering is part of the same durable World database (the §10 probe's table set includes `metering_records`).
- Cognition and policy remain World objects/revisions written through the existing World-backed capabilities. No probe or test in this window introduces a second cognition database, answer oracle, detached reply store or Resident fixture.

## Fresh checks

- Core gate 928 passed / 0 failed; §10 probe `BACKUP_RESTORE_REBUILD_PASS` with per-table logical equality across backup/restore; §9 clean-install headless PASS with a disposable World.
- The only failing tests in the full repository run are the downstream operator suites in `tests/c15_persistence/**`; they exercise `tools/c15_persistence/**`, not Core truth, and are classified in `c15_downstream_adjudication.md`.
