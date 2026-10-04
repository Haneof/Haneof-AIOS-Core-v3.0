# CORE-RC-REFREEZE-004 — Backup / Restore / Index-Rebuild Evidence

Status: **PASS — `BACKUP_RESTORE_REBUILD_PASS`** on the frozen target (`raw/local/backup-restore-rebuild.txt`).

## Fresh probe (this window, Route B semantics)

`probes/backup_restore_rebuild_smoke.py` builds a disposable World containing: one **genuine externally proven trusted return** (durable external-verifier row, response receipt, exact return handoff, staged exact response, meter, completed turn), one **dispatched-but-unproven attempt with a bound verifier**, and one **dispatched attempt with no verifier**. It then backs the World up, restores it into a new path, and rebuilds the projection from World truth.

Observed result (verbatim keys from `RESULT=`):

- `backup_completed` / `restore_completed`; backup SHA-256 `dfc08ea4e31f36df3edb5e8f162dfd14b4299f8754b87e36b12e27a77a5a2c62`; **backup immutable after restore = true**; **source World immutable = true**.
- World revision `4` before backup and `4` restored; **restored per-table logical state identical to source** (`restored_state_matches_source=true`); trust rows `[1,1,1]` preserved; receipt/staged-exact-response/verifier-consumption continuity `true`.
- Restored index is a **separate rebuildable projection** (`restored_index_is_separate_projection=true`); `rebuild_index` → `index_rebuilt`, watermark `4` = World revision, `index_lag=0`, `recovery_status=AUTO_RECOVERABLE`.
- **Restore did not widen trusted-return authority**: after restore, forged proof, transplanted genuine proof and verifier-less attach were all refused (trust rows unchanged); `record_live_provider_return` is absent; a genuine proof still attaches, an exact genuine replay is effect-free, and its turn completes with **no provider redispatch**, exactly one new meter (total `2`) and no duplicate effect; replaying the completed turn fails closed (`TurnAlreadyCompleted`) with meters unchanged; the verifier-less attempt remains unproven (`dispatching`).
- Idempotency rows (`idempotency_records`) are part of the restored per-table equality check.

## Supersession note (stale prior-window probe, kept as RED evidence)

`reviews/CORE_RC_REFREEZE_003/probes/backup_restore_trusted_return.py` (RC-003 window, pre-Corrective-003) **fails by design on the accepted Route B Core**: its crash hook asserts that an ordinary live provider return produced a durable trusted receipt (`AssertionError: trusted provider-return receipt was not durable`). Local-trust minting was removed by the accepted Corrective-003; the probe therefore asserts a rejected behavior and is superseded by the fresh probe above. Raw failure preserved at `raw/local/stale-rc003-backup-probe-on-rc004.txt`. This is a **probe-version staleness finding, not a Core defect**; the CI gate runs the fresh probe as the binding check and records the stale probe's failure separately, non-gating.

## Boundary

Backup/restore is exercised for the same-World SQLite file plus the rebuildable index projection only; no multi-host/HA claim is made.
