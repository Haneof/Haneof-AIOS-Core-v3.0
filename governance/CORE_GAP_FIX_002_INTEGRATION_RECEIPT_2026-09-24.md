# CORE-GAP-FIX-002 Integration Receipt — 2026-09-24

Status: DONE
Task: CORE-GAP-FIX-002
Finding closed: CG-002 BACKGROUND_MODEL_EXECUTION_IN_DOUBT

## Accepted candidate

- Candidate PR: #143
- Exact accepted head: `c5382a1653b66654df23d0938d9d19a80a12619c`
- Independent review PR: #154
- Independent review head: `79de04bb043a575f651b7fd4bc09cc6b8df0a161`
- Independent verdict: ACCEPTANCE_PASS
- Blockers: 0
- Review evidence merge: `32177fc38a0c8765d7dfb7a482faaeafcd027650`
- Candidate merge: `3d980fadf6beefcdd02ff4367ba834a5b013d871`

## PM integration verification

Before candidate merge, PM re-verified:
- PR #143 remained OPEN / UNMERGED / Ready for review;
- exact head had not moved;
- REST mergeability recalculated to `mergeable=true / mergeable_state=clean / rebaseable=true`;
- candidate scope remained exactly 12 Core/Test files;
- review-time main drift since candidate base contained governance/review/CI-corrective material only, with no competing `src/**` or candidate-test changes;
- all recorded exact-head workflows remained SUCCESS;
- full P16 gate run `35962673802`, job `107514408639`, used CPython 3.12.14, pytest 8.4.2, pydantic 2.13.5 and direct `pytest -q`;
- the full exact-tree suite completed 643 passed, 0 skipped, 0 failed, 0 errors;
- the independent review confirmed before-fix Wake and Periodic Review duplicate-provider execution, durable attempt state semantics, crash windows, schema/upgrade behavior, budget and exactly-once delivery compatibility, and adversarial restart/identity probes.

The review evidence was merged first, then the exact candidate was merged with an expected-head pin.

## Integrated behavior

The integrated Core now has durable background model-attempt admission/provenance for Wake and Periodic Review, including:
- stable attempt identity before provider dispatch;
- explicit `not_submitted` vs `in_doubt`;
- no blind provider reinvocation after ambiguous dispatch;
- durable `response_returned` and `metered` recovery boundaries;
- same-attempt inspection/reconciliation;
- ModelMeteringLedger remains the sole usage/economic truth;
- legacy RUNNING work without safe proof fails closed;
- runtime-incomplete continuation advances model-round identity only with durable evidence.

## Honest limitation

No new post-merge GitHub Actions run was automatically created for merge commit
`3d980fadf6beefcdd02ff4367ba834a5b013d871` at PM integration time.
No post-merge green result is claimed. The authoritative regression evidence is the independently
accepted exact-tree PR run set, including the 643-pass full gate.

## Scheduling effect

- `CORE-GAP-FIX-002 = DONE`.
- `CORE-GAP-FIX-001` is released from FROZEN_WIP and must resume existing PR #145 from the new live main; it must preserve FIX-002 attempt/recovery semantics.
- `CORE-GAP-FIX-003` dependency on FIX-002 is satisfied and the task becomes READY / NOT_STARTED.
- Fresh Resident A/B/C remains forbidden before CORE-RC-FREEZE-001.
