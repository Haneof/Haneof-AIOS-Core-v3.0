# CORE-RC-REFREEZE-003 Operator Packet

Status: **REVIEW_READY / READY_FOR_INDEPENDENT_ACCEPTANCE** — candidate evidence only; independent acceptance has not been performed.

Repository: `Haneof/Haneof-AIOS-Core-v3.0`
This packet is not an Independent Acceptance verdict, PM integration approval, merge instruction, Resident release, public tag, or public release.

## 1. Frozen software boundary

- Frozen software commit: `f20f2edfa7af00d0286493fd15196ca9503bc315`
- Parent commits: `0df757e9666c2c75571df7a7a3dedf27d44e5b7f`, `a73e186d40688f5dc181b1128a62eff37a974409`
- Repository tree: `1ac3a675b884167d3a29aa432e7ef3eaff94d404`
- `src/aios_core/**` tree: `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- `tests/**` tree: `7e33b5ef8432370234965d3ccd61248c703c4019`
- Historical frozen-target workflow tree: `fb168f8540070ff7b0c521e5990b03c7f3c56bf4`
- Package: `aios-core 0.3.0.dev0`; `requires-python = ">=3.12"`.
- Exact source/config, release workflow, constitution and baseline hashes: `reviews/CORE_RC_REFREEZE_003/source_manifest.json`.
- Live `main` observed by fresh fetch at `2026-09-28T14:34:40Z`: `c532b9fe3dfff594ee0b68bcac4fff6160f8b4b5`. Point-in-time only; seven post-target commits changed governance/evidence, with zero protected implementation drift.

The candidate may add this freeze packet, review evidence and `.github/workflows/core-rc-refreeze-003-formal-gate.yml`. It must not alter the frozen source/test/package/workflow trees. Formal CI checked out the explicit PR head, then ran all software validation in a detached worktree at the exact frozen target.

## 2. Formal environment and evidence

Required and observed runtime: CPython **3.12.14**, Pydantic **2.13.5**, pytest **8.4.2**, SQLite **3.45.1**, Ubuntu **24.04.5 LTS**, kernel `6.17.0-1022-azure`, architecture **x86_64**. Full `pip freeze` for the formal and clean-wheel environments is in the hosted artifact.

Primary fresh run: [36436264055](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/36436264055), job/check `108974868566`, candidate head `f2ef4886cbd7253543e82debbaa14ea387417f03`. The full run, job, environment, per-test counts, probe records, artifact digest and file checksums are captured in `reviews/CORE_RC_REFREEZE_003/formal_gate_run.json`.

- Complete repository pytest: **919 passed, 0 failures, 0 errors, 0 skipped**.
- Trusted-return/recovery focused pytest: **248 passed, 0 failures, 0 errors, 0 skipped**.
- Core systems focused pytest: **356 passed, 0 failures, 0 errors, 0 skipped**.
- Runtime registry: **43 total / 22 side-effecting**, exact match to the 22-row replay matrix.
- Clean wheel install/headless lifecycle: **PASS**, five separate CLI processes, deterministic mechanical handler only.
- Backup/restore/index rebuild/trusted-return recovery: **PASS**, immutable source backup, no provider redispatch or duplicate capability effect, index rebuilt from World.

The artifact is `core-rc-refreeze-003-36436264055`, ID `10976116271`, size `46,758` bytes, server-reported SHA-256 `783b04438acbb982b584c3b6457727604d45695558a46f7d12a3574399bacb71`. The earlier sandbox download attempt failed at GitHub's Azure Blob endpoint with EOF/SSL_ERROR_SYSCALL; the archive is not represented as locally downloaded. Runner-published file hashes and the check annotations allow an independent reviewer to verify it.

The clean release-path smoke builds and installs a wheel from the frozen target into a new virtual environment, then runs `aios-core-headless` with `aios_core.headless.testing:deterministic_model_handler`. It creates only a disposable World/index; no real provider or Resident fixture is used.

## 3. Durable data-path contract

Authoritative durable truth is the SQLite World. World objects, revisions, operations, idempotency records, trusted-return receipts/authority and metering remain in that World. The search index is a rebuildable projection only. Supported backup/restore restores the World to a new path and rebuilds the index from World truth.

The formal backup probe verified receipt/authority and exact handoff continuity, source-backup and source-World immutability, operation/object continuity, zero provider redispatch, no duplicate meter/effect, and a caught-up rebuilt index. Exact table row counts and logical hashes are in `formal_gate_run.json`.

Canonical writer exclusion and validation-only lock override behavior passed the fresh headless/restart regressions. Distributed multi-host/HA coordination is not claimed.

## 4. RC impact and required follow-on

**`FRESH_A_REQUIRED`**. Trusted-return Corrective-001 changed accepted execution/recovery/replay behavior across the reachable 22 side-effecting capability surface.

- A-003: **`HISTORICAL_FOR_PRIOR_RC_ONLY`**.
- A-003 hash-swap onto this RC: **forbidden**.
- Fresh `C15-RCC-RES-A-RERUN-004`: only after this RC receives independent acceptance and PM integration, in a later authorized task.
- No Resident A/B/C was run here; no A-004 was run.

## 5. Explicit exclusions

- No Core bug repair in this RC task. No software blocker was observed by the exact-target gate; an independent reviewer still adjudicates acceptance.
- No persistence Corrective-003 resume or work on persistence WIP branches.
- No C15 evaluator or C15 close.
- No changes/merges to #263 or #265.
- No merge, no self-acceptance, no public tag or release.

## 6. Candidate identity and handoff

The final exact candidate head, first parent and tree are pinned in the PR description/comment after the evidence-only final commit receives its fresh gate run. The repository manifest intentionally avoids a self-referential candidate SHA. The intended terminal state is **`REVIEW_READY / READY_FOR_INDEPENDENT_ACCEPTANCE`**; stop there.
