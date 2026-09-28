# CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001 — PM REVIEW_READY Writeback

Date: 2026-09-28

Pre-writeback live main: `7b207362a0b148c5d49bb586f1c878583661a5a9`

Engineering PR: #258

Pinned exact candidate: `1ebf51c4cb905e2a2578a09b64007b50bca0d4ac`

Final engineering handoff comment: `5864458962`

## Verified engineering state

Fresh remote verification confirmed:

- PR #258 is OPEN / READY / UNMERGED.
- Exact head is unchanged at `1ebf51c4...`.
- Historical STOP `5863435728` is preserved.
- Merged R5 clarification remains authoritative.
- Frozen R5 RED at `d3fa0490...` reproduced the three R5-C execution paths before the minimal correction.
- Formal workflow `36384741145` completed successfully under CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1.
- R5 suite: 24/24 passed.
- Focused trusted-return/authenticity suite: 99/99 passed.
- Complete regression: 816/816 passed, with zero failures, errors, or skips.

## R5 binding

R5 remains defined as exactly-once durable effects, not zero internal function re-entry.

The final engineering candidate demonstrates stable provider request identity, one durable meter record, one durable capability/World effect, one output/delivery identity, and one terminal completion identity across recovery.

Changed or conflicting replay remains fail-closed.

## Disposition

```text
CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001
= REVIEW_READY / AWAITING_INDEPENDENT_ACCEPTANCE

CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-INDEPENDENT-ACCEPTANCE
= READY
```

The Independent Acceptance is the unique next READY task.

It must use a fresh reviewer, pin exact candidate `1ebf51c4...`, freeze reviewer-owned probes before execution, and independently verify R1-R5, trusted-return authenticity, no provider redispatch, R5 durable-identity semantics, replay conflict handling, and full regression.

## Downstream

Still BLOCKED:

- PR #258 merge / PM integration;
- CORE-RC-REFREEZE-003;
- CORE-RC-REFREEZE-003-INDEPENDENT-ACCEPTANCE;
- C15-RCC-RES-A-RERUN-004;
- C15-RCC-RES-A-RERUN-004-INDEPENDENT-ACCEPTANCE;
- persistence Corrective-003 resume;
- RELEASE-003;
- Resident B/C;
- evaluator / closure.
