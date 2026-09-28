# CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001 — Independent Acceptance Failure Adjudication

Date: 2026-09-28

Repository: `Haneof/Haneof-AIOS-Core-v3.0`

Pre-adjudication live main: `a3dab8bcffe83cddc523cac6d8d1e4346b5f33e3`

Engineering PR: #258

Failed exact candidate:

`1ebf51c4cb905e2a2578a09b64007b50bca0d4ac`

Independent review-only PR: #261

Review evidence head:

`b9d692ddca055b13fb29e646186e929a08bf8955`

## Verdict

```text
CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-INDEPENDENT-ACCEPTANCE
= DONE / ACCEPTANCE_FAIL / blocker=1

IA-BLK-TRUSTED-RETURN-001
= BINDING
```

The reviewer-owned evidence is durably published on PR #261. PR #261 is OPEN / DRAFT / UNMERGED and based directly on the tested exact candidate.

## PM source verification

The blocker is independently source-confirmed.

The failed candidate repaired exact R5-C replay for `execution.task.create` by looking up the existing operation identity and reusing the original `operation_id` and `expected_world_revision`, while retaining the unchanged request-fingerprint verifier.

That is not a complete capability-surface solution.

The reviewer reproduced five reachable side-effecting families that reject a legitimate identical replay after the effect is already durable:

- `propose_goal`;
- `form_event`;
- `propose_entity`;
- `propose_dimension`;
- `propose_cognitive_policy`.

The failures include idempotency request-fingerprint mismatch and pre-commit "already exists" guards.

By contrast, `CognitionWritebackService.commit_claim()` already contains a pre-existing exact retry guard that detects the stable claim object and returns `reused_existing=True`. Its PASS therefore does not prove the rest of the capability catalog is replay-safe.

The failure does not show a duplicate durable effect. It shows the inverse failure: an identical deterministic replay is rejected and the logical turn cannot exactly-once converge.

This violates the merged R5 contract.

## Reviewer evidence

Reviewer formal environment:

- CPython 3.12.14;
- pytest 8.4.2;
- Pydantic 2.13.5;
- SQLite 3.51.1, explicitly disclosed as different from the author 3.45.1.

Final binding reviewer suite:

- 59 probes;
- 51 passed;
- 5 failed;
- 3 xfailed trust-root informational probes.

The five failures are the one blocker class above.

Candidate-owned suite independently passed 816/816.

Full reviewer run:

- 867 passed;
- 5 failed;
- 3 xfailed;
- 237.95s.

Reviewer withdrew two harness false positives instead of promoting them to findings.

## Historical candidate disposition

PR #258 / `1ebf51c4...` is a failed exact candidate.

Preserve:

- original later-round baseline RED;
- historical engineering STOP;
- merged R5 clarification;
- author formal greens;
- frozen R5 RED;
- final author handoff;
- reviewer revision history rev1..rev7;
- review-only PR #261.

Do not merge or hash-swap PR #258.

## Corrective disposition

```text
CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001
= READY
```

This is the unique next READY task.

Scope is exactly one blocker: complete R5-C identical replay convergence across the full reachable side-effecting capability surface.

The corrective must first freeze a capability replay matrix and reproduce the reviewer-proven RED on the failed exact candidate.

It must not weaken:

- exact request fingerprint conflict detection;
- durable operation identity;
- trusted-return authenticity;
- R1-R5 crash/recovery semantics;
- stronger terminal-receipt short-circuits.

It must not modify persistence harness or run Residents.

Canonical engineering prompt:

`governance/prompts/CORE_BACKGROUND_TRUSTED_RETURN_RECOVERY_001_CORRECTIVE_001_2026-09-28.md`

## Downstream

Still BLOCKED:

- Corrective-001 Independent Acceptance;
- PR #258 merge;
- CORE-RC-REFREEZE-003;
- CORE-RC-REFREEZE-003 Independent Acceptance;
- C15-RCC-RES-A-RERUN-004;
- fresh A Independent Acceptance;
- persistence Corrective-003 resume;
- RELEASE-003;
- Resident B/C;
- evaluator / closure.
