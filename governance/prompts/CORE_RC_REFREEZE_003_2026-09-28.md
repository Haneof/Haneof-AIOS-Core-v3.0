# CORE-RC-REFREEZE-003

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Role:
**Release PM / Release Engineer**

Status at dispatch:
`READY`

Your only task is to freeze and prove the exact post-trusted-return-corrective software boundary.

Do not repair Core in this task.

## 1. Start gate

Fresh-fetch live `main`.

Read:
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/CORE_BACKGROUND_TRUSTED_RETURN_RECOVERY_001_CORRECTIVE_001_INTEGRATION_RECEIPT_2026-09-28.md`
- accepted Corrective-001 implementation PR #264
- review-only IA evidence at `eeda251e057e98b15a919694af4689786faf8c55`
- prior `CORE-RC-REFREEZE-002` manifest/operator packet/IA/integration receipt.

Confirm:
`CORE-RC-REFREEZE-003 = READY`.

Do not run Resident.

## 2. Frozen software target

The canonical software integration point immediately after accepted Core merge is:

`f20f2edfa7af00d0286493fd15196ca9503bc315`

At execution time live main may contain later governance-only commits.

Before freeze:
- prove every commit after `f20f2edf...` is governance/evidence-only;
- require ZERO drift in `src/**`, `tests/**`, package metadata, and release-relevant implementation workflows unless separately accepted;
- if any unadjudicated implementation drift exists, STOP as `BLOCKED`.

Freeze mechanically:
- exact software SHA;
- repo tree;
- `src/aios_core/**` tree;
- `tests/**` tree;
- release-relevant workflow/config hashes;
- `pyproject.toml`;
- constitution/baseline hashes;
- dependency/environment manifest.

No public tag/release is authorized.

## 3. Open-PR contamination review

Freshly inventory open PRs touching:
- `src/aios_core/**`
- `tests/**`
- `.github/workflows/**`
- `pyproject.toml`
- recovery/runtime/Resident release surfaces.

Explicitly classify:
- #258 failed historical exact;
- #261 failed review-only evidence;
- #263 persona-governance candidate;
- #265 C15 exit-readiness draft;
- PM reviewer 3.12 validation branch;
- old persistence WIP #254;
- any newly opened PR.

Do not import anything merely because it is open.

## 4. Formal environment

Use:
- CPython 3.12.14;
- Pydantic 2.13.5;
- pytest 8.4.2;
- record actual SQLite version;
- record OS/kernel/architecture.

Use clean package installation where the release smoke requires it.

## 5. Fresh software regression

Run on the exact frozen software target:
- complete repository pytest;
- current trusted-return R1-R5 suites;
- complete 22-capability exact-replay matrix;
- changed/conflicting replay matrix;
- trusted-return authenticity/transplant/corruption;
- real process-loss coverage;
- turn/background recovery;
- world-kernel/index;
- C09 Wake;
- P15 Review;
- C14 runtime/scheduler/loop;
- cognition revision/policy;
- headless;
- recovery;
- bounded SCALE semantic-equivalence.

Historical reviewer evidence is provenance only; freeze regression must be freshly executed.

## 6. Clean-install / headless smoke

From a fresh checkout/install:
- build/install package through normal release path;
- run `aios-core-headless`;
- create disposable World;
- deterministic mechanical turn;
- stop/restart;
- verify same World/index continuity;
- safe recovery-status path;
- clean close.

No Resident fixture and no real provider required.

## 7. Backup / restore / index rebuild

Freshly verify:
- backup of World containing recovery/receipt/idempotency state;
- restore to new path;
- source backup immutability;
- exact World/object/operation continuity;
- index rebuild;
- trusted-return authority/receipt state survives supported backup/restore.

## 8. Writer / restart

Freshly verify:
- canonical same-World writer exclusion;
- lock-path override cannot create second writer;
- clean stop/restart works;
- stale metadata alone does not block restart;
- recovery does not duplicate model dispatch/meter/effect.

## 9. Trusted-return corrective spot checks

At minimum prove on the freeze target:
- complete reachable side-effecting registry still matches the accepted surface;
- identical recovered replay converges exactly once;
- same-key changed request fails closed;
- tampered trusted handoff bytes fail before capability application;
- relation/policy changed request produces a distinct operation only where the domain contract allows;
- `call_id` still has no durable authority;
- request fingerprint and expected World revision semantics remain intact.

## 10. Historical FIX / recovery checks

Freshly spot-check:
- FIX-001 historical cutoff;
- FIX-002 ambiguous background dispatch;
- FIX-003 ambiguous user turn;
- current-time control;
- prior trusted-return authenticity guarantees;
- no second World/cognition truth store.

## 11. RC impact adjudication

The accepted Core integration changed Resident-visible recovery/replay semantics.

Default required disposition:

`FRESH_A_REQUIRED`

A-003 is now:
`HISTORICAL_FOR_PRIOR_RC_ONLY`.

Do not hash-swap A-003 onto this RC.

Only overturn `FRESH_A_REQUIRED` with a mechanical proof that all Resident-visible/execution-relevant semantics are identical. The burden is on reuse.

Do not run A in this task.

## 12. Deliverables

Create at minimum:
- `release/rc/CORE_RC_REFREEZE_003_MANIFEST.json`
- `release/rc/CORE_RC_REFREEZE_003_OPERATOR_PACKET.md`
- `reviews/CORE_RC_REFREEZE_003/source_manifest.json`
- `reviews/CORE_RC_REFREEZE_003/environment_manifest.txt`
- regression evidence;
- open-PR contamination review;
- clean-install/headless evidence;
- backup/restore/rebuild evidence;
- writer/restart evidence;
- trusted-return corrective spot checks;
- known limitations;
- RC impact adjudication;
- SHA256 checksums.

Freeze tests/evidence before any corrective action.

If any real software blocker appears:
- preserve RED evidence;
- return `BLOCKED`;
- do not fix it in RC-REFREEZE-003.

## 13. Exit

Choose exactly one:

`REVIEW_READY`

only if all freeze requirements pass and the exact RC candidate is pinned.

or:

`BLOCKED`

If REVIEW_READY:
- open one RC-REFREEZE-003 candidate PR;
- pin exact candidate head/parent/tree;
- stop at `READY_FOR_INDEPENDENT_ACCEPTANCE`;
- do not self-accept;
- do not merge;
- do not run A-004;
- do not resume persistence;
- do not enter B/C/evaluator/C15 close.
