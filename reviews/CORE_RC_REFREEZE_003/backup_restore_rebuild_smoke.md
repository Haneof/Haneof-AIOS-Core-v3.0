# CORE-RC-REFREEZE-003 — Backup / Restore / Index-Rebuild Evidence

Status: **PASS** in fresh formal run [36436264055](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/36436264055), against the exact frozen target.

The probe created a disposable World containing a trusted-return receipt and authority, exact handoff bytes, a dispatched-but-unrecorded later turn, durable meter state, World operations and idempotency rows. It backed up the World, restored it to a new World path, rebuilt the missing index from World truth and recovered the exact authenticated response.

Observed result: **`BACKUP_RESTORE_TRUSTED_RETURN_PASS`**.

- Source World revision before backup: `3`
- Restored World revision before recovery: `3`; after exact-response recovery: `4`
- Restore disposition: `AUTO_RECOVERABLE`
- Index rebuild disposition: `REBUILD_FROM_WORLD`; rebuild watermark `3`
- Post-recovery index watermark: `4`, equal to World revision `4`
- Source backup immutable: `true`; SHA-256 before and after: `686cf3dde9210025813daaa1d9b9ac3fb85abb95f90e2f38f5d329af7f0fd15d`
- Source logical World immutable: `true`
- Trusted-return receipt continuity: `true`
- Restored authority validated: `true`
- World/object/operation continuity: `true`
- Provider redispatch after restore: `0`
- Meter rows after recovery: `2` (one per model attempt)
- Capability side-effect count after recovery: `1` (no duplicate effect)
- Completed-turn replay failed closed without new metering.

Pre-backup logical table row counts were: `background_model_attempts=2`, `background_model_authenticity_authority=1`, `background_model_request_bindings=2`, `background_model_response_receipts=2`, `background_model_return_handoffs=2`, `idempotency_records=3`, `metering_records=1`, `object_revisions=4`, `operations=3`, `world_commits=3`. Per-table logical hashes are preserved in `formal_gate_run.json` and the raw artifact output.

- Raw probe file SHA-256: `106177d8c0d38fc4d9a220979f612054169d0a430d7c5f071ae60329049a6323`
- Hosted artifact: `core-rc-refreeze-003-36436264055`; archive SHA-256 `783b04438acbb982b584c3b6457727604d45695558a46f7d12a3574399bacb71`.
