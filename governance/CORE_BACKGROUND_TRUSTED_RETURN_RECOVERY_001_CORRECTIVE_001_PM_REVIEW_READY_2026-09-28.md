# CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001 — PM REVIEW_READY Writeback

Date: 2026-09-28

Status:

```text
CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001
= REVIEW_READY / READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE
```

This is a PM readiness decision only.

It is **not**:
- an acceptance verdict;
- permission to merge PR #264;
- permission to start RC-REFREEZE-003;
- permission to run Resident A/B/C;
- permission to resume persistence Corrective-003.

## 1. Fresh identities

PM re-fetched live state before this writeback.

- live `main`: `5288822e751df185f3abab79f969609f31859617`
- candidate PR: #264
- candidate branch: `arena/01a0e76f-haneof-aios-core-v3-0`
- exact candidate head: `a73e186d40688f5dc181b1128a62eff37a974409`
- candidate parent: `71f6d106a697b0c61410d42114545f2645e12510`
- candidate tree: `352f47ac4e3098b10b1b78e4757543477371548d`
- failed historical candidate PR #258 exact:
  `1ebf51c4cb905e2a2578a09b64007b50bca0d4ac`
- failed IA review-only PR #261 exact:
  `b9d692ddca055b13fb29e646186e929a08bf8955`

PR #264 is OPEN / UNMERGED and reported REVIEW_READY.

## 2. PM mechanical findings

The candidate is based directly on current live main and is ahead by eleven commits with no base drift at review time.

The candidate carries forward the unmerged #258 trusted-return recovery implementation and then adds the capability-surface corrective.

PM independently confirmed byte identity for key trusted-return surfaces between failed #258 exact and #264 exact:

- `src/aios_core/runtime/background_attempt.py`
  blob `f6617aad47dd0b339dd954d9e0e430b733bef2ee`
- `src/aios_core/runtime/turn_runtime.py`
  blob `062f7d8af03e599a39f962c29566a654a1963a13`
- `tests/integration/test_core_background_trusted_return_r5_001.py`
  blob `461d1c8942582615bc8952cd2088753c6985a9db`

Therefore the corrective did not mechanically rewrite those trusted-return authority surfaces.

The candidate dynamically enumerates 43 model-callable capabilities / 22 side-effecting capabilities and claims complete coverage of all 22.

The author preserved a baseline RED against failed exact #258:
- rev5: 20 failed / 44 passed;
- 17 exact-replay failures;
- 3 changed-request conflict failures that previously produced an additional durable revision.

The candidate adds:
- exact-operation replay using the original durable operation identity and expected World revision;
- canonical request identity inside fingerprinted operation arguments;
- pinned-target replay for revision-advancing mutations;
- real process-loss SIGKILL probes in wake / user_turn / periodic_review modes;
- store corruption/skew/fail-closed probes;
- complete regression evidence.

## 3. CI state at PM release

At the exact candidate head, all 23 fetched PR workflow runs were completed successfully, including:

- core-background-trusted-return-recovery-001;
- core-rc-refreeze-002-formal-gate;
- p16-convergence-gate;
- c14 derivation runtime/scheduler/loop;
- core-recovery;
- core-scale;
- world-kernel / world-index;
- C09 Wake;
- P15 Review;
- P9/P10/P11/P12;
- constitutional cognition closure.

The formal 3.12 gate reported:
- CPython 3.12.14;
- Pydantic 2.13.5;
- pytest 8.4.2;
- full JUnit 919 tests / 0 failures / 0 errors / 0 skipped.

These are author/CI evidence only. They do not substitute for fresh Independent Acceptance.

## 4. Binding unresolved IA adjudication — rev5 -> rev6

PM identified one issue that must **not** be silently accepted from the author report.

The first frozen corrective matrix, rev5, classified changed-field cases for:

- `upsert_relation`;
- `update_cognitive_policy`;
- `rollback_cognitive_policy`;

as same-key conflicts that must fail closed.

After implementation, rev6 reclassified those cases to `identity_shifts`, because the new operation key is derived from the complete canonical request. Under rev6, a changed request may become a distinct durable operation/revision rather than fail.

The author preserved rev5 and supplied a rationale plus store-level same-key fail-closed tests.

This may be a legitimate correction of an over-specified synthetic test, because:
- the three service request contracts do not carry a pinned "new revision" identity;
- `CapabilityCall.call_id` is transient correlation, not a durable idempotency identity;
- a genuinely changed policy update or relation upsert may be a legal new operation;
- an authenticated recovered provider directive cannot have its arguments changed without violating the trusted-return payload/receipt binding.

But the governing corrective prompt also says:
- freeze expectations before implementation;
- do not weaken expected outcomes after execution;
- changed/conflicting replay must fail closed;
- test changed args under the same call id/key.

Therefore **fresh IA must independently adjudicate this boundary**.

PM does not classify rev5 -> rev6 as either acceptable harness correction or blocker in this writeback.

If the independent reviewer determines that rev6 weakens a binding frozen recovery expectation, the candidate must fail.

## 5. Fresh IA required

The next legal task is:

`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`

Binding prompt:

`governance/prompts/CORE_BACKGROUND_TRUSTED_RETURN_RECOVERY_001_CORRECTIVE_001_INDEPENDENT_ACCEPTANCE_2026-09-28.md`

The reviewer must create fresh adversarial evidence rather than treating the author's 919 green tests or rev7 matrix as acceptance proof.

## 6. Downstream remains blocked

Until fresh IA returns ACCEPTANCE_PASS and PM separately integrates the exact accepted candidate:

- PR #264 merge = BLOCKED;
- CORE-RC-REFREEZE-003 = BLOCKED;
- A-RERUN-004 = BLOCKED;
- persistence Corrective-003 resume = BLOCKED;
- B release/run = BLOCKED;
- Resident C / evaluator / C15 close = BLOCKED.

Historical #258 / #261 evidence remains immutable and failed.

