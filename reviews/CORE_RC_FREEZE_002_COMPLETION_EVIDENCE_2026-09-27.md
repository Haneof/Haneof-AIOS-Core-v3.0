# CORE-RC-REFREEZE-002 Completion Evidence — 2026-09-27

Status: **REVIEW_READY**  
Task: `CORE-RC-REFREEZE-002`  
Engineering PR: **#232 — OPEN / UNMERGED**  
Resident runs: **0**  
Public release/tag: **NO**

## Frozen software (not this PR head)

- live main used: `27a21db5b656d441248b9240020910b66a223830`
- parents: `89200c55e63ce2251ecc236e25d16c57d998f93c` + `f65186e754d545129d0f720008be1afb331fcd73`
- root tree: `a2e6b03b306413a2d82ca4ca8c9fc7099c0dc065`
- Core tree: `a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6` (matches accepted Corrective-002)
- tests tree: `92fcbcc5876833735fb3cb7c73a98c4a8a4a3541`
- authenticity probe blob `6f0c3850368475e166d28d0a6df4b86b610d2c60` SHA256 `35cba59f318b752ed872821961296f35810443c61db6fd98c8c8f5eee4215225`
- accepted exact `227327c657788efb1b5de1bc26e69c35c900a85e` is an ancestor of live main
- PR #219 merge `89200c55e63ce2251ecc236e25d16c57d998f93c` is an ancestor

Exact RC candidate SHA = PR #232 head after this packet is published (no further file mutation after REVIEW_READY). IA must pin `git rev-parse` of that head.

## Source / environment hashes

- source_manifest SHA256: `34b3d8adfad376a9cd7170ebec3e6093d40444b03ffd61130ed79602e63e3883`
- Formal env: CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2
- Formal gate SUCCESS: run `36314420939`
- p16 SUCCESS: run `36313973884` (3m19s)
- headless SUCCESS: `36313973920`
- recovery SUCCESS: `36313973907`
- scale SUCCESS: `36313973913`

## Mutation scope

- `src/aios_core/**` = 0 vs frozen software
- `tests/**` = 0 vs frozen software
- `pyproject.toml` = 0
- added freeze evidence under `reviews/CORE_RC_REFREEZE_002/` and `release/rc/CORE_RC_REFREEZE_002_*`
- added `.github/workflows/core-rc-refreeze-002-formal-gate.yml` (CPython 3.12.14 pin + pytest)
- governance writeback: task board / checkpoint / master map status GATE

## Impact

A-RERUN-002 = HISTORICAL_FOR_PRIOR_RC_ONLY  
FRESH_A-RERUN-003_REQUIRED

B persistence #216 untouched / FROZEN_WIP.

## Next

`CORE-RC-REFREEZE-002-INDEPENDENT-ACCEPTANCE`  
This window does **not** perform Independent Acceptance.
