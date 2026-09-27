# Backup / restore / rebuild smoke — GREEN

Covered by `tests/integration/test_core_recovery.py` (`test_r7_backup_restore_preserves_world_execution_attempt_and_metering` and related R1–R10) — core-recovery run `36313973907` SUCCESS; formal focused SUCCESS.

HMAC authority is stored in the same SQLite World (`background_model_authenticity_authority`). Legal backup/restore copies that table with the store:

- historical valid receipts still verify after restore
- restore must not mint a second authority that would invalidate old receipts
- authenticity verification is not silently skipped
- source World hash identity is preserved by the backup API (source not mutated)
- restored store rebuilds search index as projection (`REBUILD_FROM_WORLD`)
