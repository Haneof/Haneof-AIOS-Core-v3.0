# CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001 Integration Receipt — 2026-09-28

Status: **DONE / ACCEPTED / INTEGRATED**
Task: `CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001`
Implementation PR: #264
Accepted exact candidate: `a73e186d40688f5dc181b1128a62eff37a974409`
Candidate parent: `71f6d106a697b0c61410d42114545f2645e12510`
Candidate tree: `352f47ac4e3098b10b1b78e4757543477371548d`
Pre-merge main: `0df757e9666c2c75571df7a7a3dedf27d44e5b7f`
Merge commit / post-merge main: `f20f2edfa7af00d0286493fd15196ca9503bc315`

## Independent Acceptance

Review-only evidence branch:
`arena/01a0e7d5-haneof-aios-core-v3-0`

Exact review commit:
`eeda251e057e98b15a919694af4689786faf8c55`

Verdict:
`ACCEPTANCE_PASS / blocker=0`

Key independent results:
- 86 reviewer-authored probes frozen and hashed before candidate execution;
- candidate: 86/86 PASS;
- historical failed exact #258: 50 RED / 36 pass;
- all five prior IA RED families reproduced;
- complete reachable side-effecting capability surface independently confirmed at 22/43;
- exact recovery converges across all 22;
- store fail-closed matrix PASS;
- 3 real SIGKILL process-loss probes PASS;
- rev5 -> rev6 adjudication: `LEGITIMATE_HARNESS_CORRECTION`;
- reviewer full candidate regression: 1005 passed (919 candidate-native + 86 reviewer).

## Formal environment closure

Reviewer-local environment was CPython 3.11.2 / SQLite 3.40.1 because the sandbox could not obtain CPython 3.12.14.

PM therefore performed a separate exact-environment replay without modifying #264 or rewriting the IA evidence:

- PM validation branch: `governance/corrective001-ia2-py312-replay-20260928`
- exact reviewer evidence input: `eeda251e057e98b15a919694af4689786faf8c55`
- exact implementation input: `a73e186d40688f5dc181b1128a62eff37a974409`
- successful run: **36423849252**
- CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1
- all frozen probe manifest hashes: OK
- collect-only: 86
- exact JUnit: **86 tests / 0 failures / 0 errors / 0 skipped**

Historical PM replay run **36423769257** failed before probe execution because the manifest was checked from the wrong directory. It is preserved as harness-infrastructure history, not rewritten as green.

Disposition:
`REVIEWER_ENVIRONMENT_LIMITATION = CLOSED / NON_BLOCKING`

## Post-merge equivalence

PM compared accepted exact candidate `a73e186d...` to post-merge main `f20f2edf...`.

Only these pre-existing governance files differ:
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- PM REVIEW_READY writeback
- fresh IA prompt

Therefore:
- `src/**` = ZERO post-acceptance drift;
- `tests/**` = ZERO post-acceptance drift;
- accepted implementation workflow semantics = ZERO post-acceptance drift.

The accepted exact candidate is integrated unchanged into main.

## Historical evidence

Preserve unchanged:
- failed PR #258 exact `1ebf51c4cb905e2a2578a09b64007b50bca0d4ac`;
- review-only failed IA PR #261 exact `b9d692ddca055b13fb29e646186e929a08bf8955`;
- rev5 frozen author RED;
- reviewer harness history, including fake-RED and PM harness failures.

No historical red is rewritten.

## Downstream disposition

The integrated Core changes Resident-visible recovery/replay semantics.

Therefore:
- current prior RC `CORE-RC-REFREEZE-002` remains historical;
- A-003 remains immutable evidence for that prior RC only;
- **A-003 MUST NOT be reused for the next B lineage**;
- `CORE-RC-REFREEZE-003 = READY`;
- after accepted RC-REFREEZE-003, a fresh `C15-RCC-RES-A-RERUN-004` is required;
- persistence Corrective-003, B release/run, Resident C and final C15 evaluation remain BLOCKED.

PM integration verdict:

`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001 = DONE / ACCEPTED / INTEGRATED`
