# Corrective-001 IA2 Supplemental Evidence Adjudication — 2026-09-28

Status: **SUPPLEMENTAL POST-ACCEPTANCE EVIDENCE / NO REVALIDATION REQUIRED**

Task lineage:
`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`

Canonical accepted IA evidence remains:

`eeda251e057e98b15a919694af4689786faf8c55`

Later reviewer evidence head:

`f214f9812b474c06d51d5b8fb8ca366e3841424f`

Implementation accepted and merged:

- candidate: `a73e186d40688f5dc181b1128a62eff37a974409`
- merge: `f20f2edfa7af00d0286493fd15196ca9503bc315`
- current main at adjudication: `ba85170958386fa4169b1332b9cada8521dd2a0f`

## 1. Why this adjudication exists

The Independent Acceptance reviewer correctly stopped after issuing:

`ACCEPTANCE_PASS / blocker=0`

at exact review commit `eeda251...`.

After that verdict and after PM integration had already begun, the reviewer continued work to close its originally disclosed CPython 3.12.14 environment limitation.

That later work advanced the review-only branch by three commits to `f214f98...`.

Because AIOS acceptance uses exact evidence identities, the later review branch head must not silently replace the already accepted exact IA evidence.

## 2. Mechanical diff

PM compared:

`eeda251e057e98b15a919694af4689786faf8c55`
→
`f214f9812b474c06d51d5b8fb8ca366e3841424f`

Result:

- 3 commits ahead;
- 9 changed files;
- all changes confined to `reviews/CORRECTIVE_001_IA2/**`;
- ZERO `src/**` change;
- ZERO `tests/**` change;
- ZERO package/runtime/workflow implementation change.

Therefore the later branch head cannot change the implementation under acceptance.

## 3. Supplemental evidence content

The later review work:

- retracts the earlier over-broad claim that CPython 3.12.14 was unobtainable;
- builds CPython 3.12.14 from source;
- uses Pydantic 2.13.5 / pytest 8.4.2;
- records SQLite 3.38.2;
- reruns the same reviewer acceptance surface;
- candidate: 86/86 reviewer probes PASS;
- failed exact #258: 50 failed / 36 passed;
- full candidate regression including reviewer probes: 1005 passed;
- confirms the failed-probe identity set is unchanged;
- preserves the original probe expectations;
- parameterizes only the reviewer runner interpreter selection;
- reruns after pruning the local Python prefix;
- records the current post-merge repository state.

The reviewer verdict remains:

`ACCEPTANCE_PASS / blocker=0`

## 4. Relation to PM-owned formal-environment closure

This supplemental work is corroborative, not a missing prerequisite.

Before implementation merge, PM had already independently closed the reviewer's original Python limitation using exact inputs:

- exact implementation: `a73e186d40688f5dc181b1128a62eff37a974409`
- exact canonical IA evidence: `eeda251e057e98b15a919694af4689786faf8c55`
- PM run: `36423849252`
- CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1
- frozen probe manifest hashes: all OK
- collect-only: 86
- reviewer probes: 86/86 PASS

Therefore PM did not merge #264 on the basis of an unresolved formal-environment gap.

The later reviewer run is a second independent corroboration using a different SQLite version and a source-built interpreter.

## 5. Exact-evidence ruling

The accepted IA exact remains:

`eeda251e057e98b15a919694af4689786faf8c55`

The later head:

`f214f9812b474c06d51d5b8fb8ca366e3841424f`

is classified:

`SUPPLEMENTAL_POST_ACCEPTANCE_EVIDENCE`

It does **not**:
- replace `eeda251...`;
- retroactively become the exact evidence on which #264 was accepted;
- trigger `REVALIDATION_REQUIRED`;
- change the accepted candidate SHA;
- reopen Corrective-001;
- alter the PM integration verdict;
- modify production Core.

## 6. Repository-state correction

The supplemental report correctly records that #264 was merged after the original IA verdict.

PM independently confirms:
- #264 head remained `a73e186d...`;
- accepted implementation is an ancestor of current main;
- production `src/**` is byte-equivalent to the accepted implementation across the integration boundary;
- later main movement is governance-only.

Therefore the post-verdict repository movement is integration, not candidate drift.

## 7. Current control state

No downstream state changes because of this supplemental evidence.

Still binding:

- `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001 = DONE / ACCEPTED / INTEGRATED`
- canonical IA evidence = `eeda251...`
- supplemental IA evidence = `f214f98...`
- `CORE-RC-REFREEZE-003 = READY`
- `CORE-RC-REFREEZE-003-INDEPENDENT-ACCEPTANCE = BLOCKED`
- `C15-RCC-RES-A-RERUN-004 = BLOCKED`
- persistence Corrective-003 resume = BLOCKED
- Resident B/C and C15 evaluator/close = BLOCKED

## 8. Final PM ruling

`SUPPLEMENTAL_EVIDENCE_ACCEPTED / NO_REVALIDATION_REQUIRED`

The later reviewer work strengthens the evidence record but does not alter the exact acceptance lineage.
