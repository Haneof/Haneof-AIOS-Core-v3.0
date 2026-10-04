# CORE-RC-REFREEZE-004

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

WINDOW:
`24`

Role:
**Release PM / Release Engineer**

Status at dispatch:
`READY`

Your only task is to freeze and prove the exact post-Corrective-003 Core software boundary.

Do not repair Core in this task.
Do not repair C15 operator/persistence in this task.
Do not run any Resident.

## 1. Start gate

Fresh-fetch live `main`.

Read:
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/CORE_BACKGROUND_LATE_TRUSTED_RETURN_001_CORRECTIVE_003_PM_INTEGRATION_2026-10-04.md`
- accepted implementation PR #318
- Window 23 REVIEW_ONLY evidence PR #321
- exact Window 23 review commit `22aa00cb3793c252512142a1eae33ca8aae9d841`
- prior `CORE-RC-REFREEZE-003` prompt, manifest/operator packet/IA/integration evidence as historical template only.

Confirm:
`CORE-RC-REFREEZE-004 = READY`.

Do not run Resident.

## 2. Frozen software target

The canonical software integration point immediately after accepted Corrective-003 merge is:

`1cee3c5ad12f4b9098232bae11b51df786c5eb2f`

This merge must have:
- parent 1 = pre-merge main `fb53cf938b138a67d1890618eed41282c61bce00`
- parent 2 = exact accepted candidate `7ecb2250a488766915e1042a76472b3cd26d9107`
- tree = `70b2711258567863ea0d93025a6a07e39631726a`

At execution time live main may contain later governance-only commits.

Before freeze:
- prove every commit after `1cee3c5a...` is governance/evidence/publication-only;
- require ZERO unaccepted drift in `src/**`, `tests/**`, package metadata, and release-relevant implementation workflows;
- explicitly exclude REVIEW_ONLY PR #321 from software;
- explicitly classify the temporary Window 23 publication staging branch/workflow as publication transport only, not software authority;
- if any unadjudicated implementation drift exists, STOP as `BLOCKED`.

Freeze mechanically:
- exact software SHA;
- repository tree;
- `src/aios_core/**` tree;
- `tests/**` tree;
- release-relevant workflow/config hashes;
- `pyproject.toml`;
- constitution/baseline hashes;
- dependency/environment manifest.

No public tag/release is authorized.

## 3. Open-PR / branch contamination review

Freshly inventory open PRs/branches touching:
- `src/aios_core/**`
- `tests/**`
- `.github/workflows/**`
- `pyproject.toml`
- recovery/runtime/Resident release surfaces.

Explicitly classify at minimum:
- PR #310 failed historical Corrective-002 candidate;
- PR #311 historical REVIEW_ONLY evidence;
- PR #321 Window 23 REVIEW_ONLY evidence — DO NOT MERGE;
- any Window 23 publication staging branch/workflow;
- C15 persistence/operator WIP or historical review branches;
- any newly opened implementation PR.

Do not import anything merely because it is open.

## 4. Formal environment

Use:
- CPython 3.12.14;
- Pydantic 2.13.5;
- pytest 8.4.2;
- record actual SQLite version;
- record OpenSSL version;
- record OS/kernel/architecture.

Use clean package installation where the release smoke requires it.

## 5. Fresh software regression

Run on the exact frozen software target.

At minimum:
- complete Core gate: `tests/unit tests/integration tests/runtime tests/habitation`;
- complete current trusted-return/recovery focused suites;
- Window 20 frozen Suite A/B and Window 17 frozen probes from their canonical reviewer commits;
- Corrective-003 C3 matrix;
- trusted-return authenticity/transplant/corruption;
- genuine external proof and supersession;
- exact replay / changed replay / conflicting replay;
- real process-loss / SIGKILL coverage;
- turn/background recovery;
- World kernel/index;
- C09 Wake;
- P15 Review;
- C14 runtime/scheduler/loop;
- cognition revision/policy;
- headless;
- backup/restore/rebuild;
- bounded SCALE semantic-equivalence.

Historical author/reviewer evidence is provenance only; freeze regression must be freshly executed.

Do not treat `tests/c15_persistence/**` failures as Core regression unless they mechanically expose a failure in the accepted Core contract.

## 6. Corrective-003 security spot checks

Freshly prove:
- caller cannot manufacture trusted-return authority through the retired local live-return surface;
- `live_return.py` remains an inert tombstone and is not consulted by Core authorization;
- `attach_late_trusted_return` remains gated by durable external verifier + genuine proof;
- no alternate receipt/handoff/staging mint path exists;
- verifier-less ambiguous recovery remains fail-closed;
- forged local provenance cannot poison a later genuine proof;
- same-key / changed bytes conflict fails closed;
- exact genuine replay is idempotent/effect-free;
- proof transplant across bound fields is rejected;
- receipt/handoff before staging partial-commit behavior remains recoverable for the winning exact proof and fail-closed for conflicts;
- request fingerprint / expected World revision semantics remain intact;
- exactly-once meter/effect guarantees remain intact.

Do not weaken Route B to make downstream C15 harnesses green.

## 7. Clean-install / headless smoke

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

## 8. Backup / restore / index rebuild

Freshly verify:
- backup of World containing current recovery/receipt/idempotency state;
- restore to new path;
- source backup immutability;
- exact World/object/operation continuity;
- index rebuild;
- trusted-return verifier/receipt/handoff state survives supported backup/restore;
- restored state cannot widen trust authority.

## 9. Writer / restart

Freshly verify:
- canonical same-World writer exclusion;
- lock-path override cannot create second writer;
- clean stop/restart works;
- stale metadata alone does not block restart;
- recovery does not duplicate model dispatch/meter/effect.

## 10. Historical FIX / recovery checks

Freshly spot-check:
- FIX-001 historical cutoff;
- FIX-002 ambiguous background dispatch;
- FIX-003 ambiguous user turn;
- current-time control;
- no second World/cognition truth store;
- current trusted-return authenticity guarantees.

## 11. C15 downstream compatibility adjudication

Current known state:
- broad legacy/downstream run observed `45 failed / 1092 passed`;
- failures are under `tests/c15_persistence/**` / `tools/c15_persistence/**`;
- prior PM classification = `DOWNSTREAM_OPERATOR_COMPATIBILITY_DEBT / OUT_OF_SCOPE_FOR_CORE_CORRECTIVE`.

RC-REFREEZE-004 must fresh verify this classification.

Required disposition:

`CORE_FREEZE_NOT_BLOCKED_BY_DOWNSTREAM_OPERATOR_DEBT`

only if:
- complete Core gate is green;
- failures remain confined to downstream C15 persistence/operator harnesses;
- no downstream failure demonstrates a real violation of the accepted Core contract.

Do not repair those paths here.

Record:
`C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT`.

If a downstream failure reveals a genuine accepted-Core regression, freeze must return `BLOCKED`.

## 12. RC impact adjudication

Corrective-003 materially changes Resident-visible recovery/trusted-return semantics.

Default required disposition:

`FRESH_A_REQUIRED`

All prior Resident A runs are historical for prior RCs only.

Do not hash-swap A-004 or any earlier Resident evidence onto RC-REFREEZE-004.

Also require:

`FRESH_OPERATOR_PREP_REQUIRED`

because the old C15 operator/persistence harness depends on retired local trust behavior and is currently incompatible.

The intended downstream order after a successful RC freeze is:

1. RC-REFREEZE-004 Independent Acceptance;
2. PM integration of accepted freeze;
3. dedicated C15 operator/persistence compatibility corrective against the frozen RC;
4. Fresh Independent Acceptance of that operator corrective;
5. fresh Resident A only after PM explicitly releases it.

Do not run any of these downstream tasks here.

## 13. Deliverables

Create at minimum:
- `release/rc/CORE_RC_REFREEZE_004_MANIFEST.json`
- `release/rc/CORE_RC_REFREEZE_004_OPERATOR_PACKET.md`
- `reviews/CORE_RC_REFREEZE_004/source_manifest.json`
- `reviews/CORE_RC_REFREEZE_004/environment_manifest.txt`
- fresh regression evidence;
- open-PR/branch contamination review;
- clean-install/headless evidence;
- backup/restore/rebuild evidence;
- writer/restart evidence;
- Corrective-003 trusted-return spot checks;
- C15 downstream compatibility adjudication;
- known limitations;
- RC impact adjudication;
- SHA256 checksums.

Freeze tests/evidence before any corrective action.

If any real software blocker appears:
- preserve RED evidence;
- return `BLOCKED`;
- do not fix it in RC-REFREEZE-004.

## 14. Formal CI / exact-head identity

The candidate PR must obtain exact-head formal CI on its final immutable head.

Record:
- candidate head;
- parent;
- tree;
- frozen software SHA;
- formal run id;
- environment;
- all binding job results.

After the final formal CI, do not add candidate commits merely to write evidence. Use PR body/comments for post-CI receipts.

## 15. Exit

Choose exactly one:

### `REVIEW_READY`

Only if all freeze requirements pass and exact RC candidate is pinned.

Then state:
`READY_FOR_INDEPENDENT_ACCEPTANCE`

Open one RC-REFREEZE-004 candidate PR.

Stop.

Do not self-accept.
Do not merge.
Do not run Resident.
Do not repair C15 downstream harnesses.

### `BLOCKED`

If any binding freeze requirement fails.

Preserve evidence and stop.
