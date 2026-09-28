# BLOCKED DRAFT — CORE-RC-REFREEZE-003

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Status:
`DRAFT / NOT READY / DO NOT EXECUTE`

Activation prerequisites:
- `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001` accepted by fresh Independent Acceptance;
- PM has integrated the accepted exact Core candidate into live `main`;
- task board explicitly marks `CORE-RC-REFREEZE-003 = READY`.

Role:
Release PM / Release Engineer.

Only after activation, freeze the exact post-corrective software boundary and prove that the RC packet corresponds to the integrated software actually intended for the next Resident lineage.

Required start:
1. fresh-fetch live `main`;
2. read task board, checkpoint, master map;
3. read the accepted corrective implementation, its fresh IA report, and PM integration receipt;
4. verify there is no accepted-but-unmerged Core candidate;
5. verify old RC-REFREEZE-002 is historical only;
6. do not run any Resident.

Required freeze:
- exact live software SHA;
- `src/aios_core/**` tree;
- `tests/**` tree;
- release-relevant workflow/config/package hashes;
- source manifest;
- environment manifest;
- CPython/Pydantic/pytest/SQLite observations;
- clean-install package evidence.

Required regression:
- full Core regression;
- trusted-return recovery exact-replay matrix accepted by the corrective;
- trusted-return authenticity/transplant/fail-closed checks;
- HEADLESS;
- RECOVERY;
- writer/restart;
- backup/restore/index rebuild;
- historical FIX-001/002/003 spot checks;
- relevant SCALE semantic-equivalence checks;
- no second truth store.

Open-PR contamination:
inventory all open PRs touching Core/tests/workflows/package metadata and classify them. Historical failed/review-only PRs must not be imported merely because they are open.

Resident impact:
Because this RC contains accepted Core recovery/replay semantic changes, default disposition is:
`FRESH_A_REQUIRED`.
Any attempt to reuse A-003 carries the burden of proving zero Resident-visible/runtime semantic delta. Do not assume reuse.

Expected deliverables after activation:
- `release/rc/CORE_RC_REFREEZE_003_MANIFEST.json`
- `release/rc/CORE_RC_REFREEZE_003_OPERATOR_PACKET.md`
- `reviews/CORE_RC_REFREEZE_003/**`
- completion report;
- exact candidate pin.

Exit:
`REVIEW_READY` or `BLOCKED` only.
Do not self-accept, merge, run A/B/C, or resume persistence.
