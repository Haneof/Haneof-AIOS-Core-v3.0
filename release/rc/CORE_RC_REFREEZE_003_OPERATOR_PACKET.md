# CORE-RC-REFREEZE-003 Operator Packet

Status: **GATE / IN_PROGRESS — not yet ready for independent acceptance**
Repository: `Haneof/Haneof-AIOS-Core-v3.0`
This packet is not an Independent Acceptance verdict, PM integration approval, merge instruction, Resident release, or public release.

## 1. Frozen software boundary

- Frozen software commit: `f20f2edfa7af00d0286493fd15196ca9503bc315`
- Parent commits: `0df757e9666c2c75571df7a7a3dedf27d44e5b7f`, `a73e186d40688f5dc181b1128a62eff37a974409`
- Repository tree: `1ac3a675b884167d3a29aa432e7ef3eaff94d404`
- `src/aios_core/**` tree: `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- `tests/**` tree: `7e33b5ef8432370234965d3ccd61248c703c4019`
- Historical software workflow tree: `fb168f8540070ff7b0c521e5990b03c7f3c56bf4`
- Package: `aios-core 0.3.0.dev0`; `requires-python = ">=3.12"`
- Exact source/config, workflow, constitution and baseline hashes: `reviews/CORE_RC_REFREEZE_003/source_manifest.json`
- Current `main` at the fresh audit was `c532b9fe3dfff594ee0b68bcac4fff6160f8b4b5`; this is a timestamped point-in-time observation, not a permanent baseline. Seven post-target commits changed governance/evidence only; protected source/tests/pyproject/release workflows had zero drift.

The candidate may add this freeze packet, review evidence and `.github/workflows/core-rc-refreeze-003-formal-gate.yml`. It must not alter the frozen source/test/package/workflow trees.

## 2. Formal environment and evidence

Required formal versions: CPython **3.12.14**, Pydantic **2.13.5**, pytest **8.4.2**. The workflow records the actual SQLite library, OS release, kernel, architecture, `pip freeze`, exact target trees and run identity.

The clean release-path smoke builds and installs a wheel from the frozen target into a new virtual environment, then runs `aios-core-headless` with `aios_core.headless.testing:deterministic_model_handler`. It creates only a disposable World and index; no real provider or Resident fixture is used.

Fresh run status and observed outputs are recorded in:

- `reviews/CORE_RC_REFREEZE_003/environment_manifest.txt`
- `reviews/CORE_RC_REFREEZE_003/full_regression.md`
- `reviews/CORE_RC_REFREEZE_003/focused_regressions.md`
- `reviews/CORE_RC_REFREEZE_003/headless_smoke.md`
- `reviews/CORE_RC_REFREEZE_003/backup_restore_rebuild_smoke.md`
- `reviews/CORE_RC_REFREEZE_003/writer_restart_smoke.md`
- `reviews/CORE_RC_REFREEZE_003/trusted_return_authenticity_spot_checks.md`
- `reviews/CORE_RC_REFREEZE_003/legacy_fix_spot_checks.md`
- `reviews/CORE_RC_REFREEZE_003/SHA256SUMS`

Do not substitute historical reviewer/PM/RC-002 totals for a fresh RC-003 run.

## 3. Durable data-path contract

Authoritative durable truth is the SQLite World. World objects, revisions, operations, idempotency records, trusted-return receipts/authority and metering remain in that World. The search index is a rebuildable projection only. Supported backup/restore restores the World to a new path and rebuilds the index from World truth.

The formal backup probe verifies a trusted-return receipt/authority and exact handoff in the World snapshot, source-backup immutability, operation/object continuity, no provider redispatch, no duplicate meter/effect, and a caught-up rebuilt index.

Canonical writer exclusion and validation-only lock override behavior are covered by fresh headless/restart regressions. Distributed multi-host/HA coordination is not claimed.

## 4. RC impact and required follow-on

**`FRESH_A_REQUIRED`**. Trusted-return Corrective-001 changed accepted execution/recovery/replay behavior across the reachable 22 side-effecting capability surface.

- A-003: **`HISTORICAL_FOR_PRIOR_RC_ONLY`**.
- A-003 hash-swap onto this RC: **forbidden**.
- Fresh `C15-RCC-RES-A-RERUN-004`: only after this RC receives independent acceptance and PM integration, in a later authorized task.
- No Resident A/B/C was run here; no A-004 was run.

## 5. Explicit exclusions

- No Core bug repair in this RC task. Any real software blocker remains RED and makes this task `BLOCKED`.
- No persistence Corrective-003 resume or work on the persistence WIP branches.
- No C15 evaluator or C15 close.
- No changes/merges to #263 or #265.
- No merge, no self-acceptance, no public tag or release.

## 6. Candidate identity and handoff

When all gates pass, the fixed session branch will carry one candidate PR. A separate, non-self-referential PR comment will pin the exact candidate head SHA, first parent and tree. The current run/pin fields remain pending until the gate is complete. The intended terminal state is **`REVIEW_READY / READY_FOR_INDEPENDENT_ACCEPTANCE`**; stop there.
