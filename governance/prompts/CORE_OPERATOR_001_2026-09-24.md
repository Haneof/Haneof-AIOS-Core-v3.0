# CORE-OPERATOR-001 — Test Infrastructure Engineer Prompt

Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Task: `CORE-OPERATOR-001`  
Role: **Test Infrastructure Engineer**  
Independent acceptance: a different reviewer after your candidate is ready.

You are NOT:
- a Resident A/B/C;
- a semantic evaluator;
- a Core feature engineer unless the PM explicitly creates a separate Core gap task;
- the PM closing your own work.

## Start conditions

1. Fetch real-time latest `main`.
2. Read:
   - `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
   - `AIOS_v3.0_CURRENT_CHECKPOINT.md`
   - `governance/AIOS_CORE_BASELINE_001_DECISION_2026-09-24.md`
   - `governance/AIOS_CORE_COMPLETION_PLAN_2026-09-24.md`
3. Confirm `CORE-OPERATOR-001 = READY`. If not READY, stop.
4. Record live main SHA. Handoff reference at task release is `33436565c109c2c47cf2c3150084fcce22810124`, but do not treat it as permanent if main legitimately advanced.
5. Source WIP is immutable PR #125 exact head `b14b5d84b6a4c843dc7dc38cde51f08a92fac86b`. Do not modify or force-push PR #125.

## Required source review

Read PR #125 exact-head implementations and tests needed for the operator:
- `tools/c15_preflight/**`
- `tests/preflight/**`
- `.github/workflows/c15-operator-preflight.yml`
- `reviews/arena_resident_handover_2026-09-24/PROTOCOL_REVISION.md`

Do not merge the whole PR. Its Core tree is historical and must not replace current main.

## First mandatory action: reproduce before fixing

On a fresh branch from live main, port only the minimum operator/test assets required to run the exact three current failures. Before changing behavior, reproduce and preserve evidence for:

1. `tests/preflight/test_driver.py::test_clock_reuses_existing_scheduler_at_intermediate_deadline_without_future_input`
2. `tests/preflight/test_round3_fixes.py::test_old_wake_cannot_see_future_input`
3. `tests/preflight/test_round3_fixes.py::test_budget_deferral_not_forced`

Historical exact-head reference:
- run `35952205324`, job `107482934617`: 128 passed / 3 failed;
- run `35952205318`, job `107482934372`: same three failures.

If any failure does not reproduce on the current-main port, mark it `NOT_REPRODUCED` with exact commands and outputs. Do NOT edit code merely to make the task look complete.

## Allowed write scope

Primary:
- `tools/c15_preflight/**`
- `tests/preflight/**`
- `.github/workflows/c15-operator-preflight.yml`
- task-specific review/evidence files under `reviews/`

Do NOT modify:
- `src/aios_core/**`
- PR #117 / #121 evidence bytes;
- sealed fixture/future events;
- any Resident World;
- UI / hardware / ROM / animation files.

If a reproduced defect demonstrably requires `src/aios_core/**` changes, STOP implementation, preserve reproduction, and report a proposed `CORE-GAP-FIX-NNN` to the PM. Do not mix that Core fix into this task.

## Required behavioral properties

The completed operator candidate must prove mechanically:
- due intermediate ticks are not skipped;
- a Wake cannot observe inputs not yet released at that Wake time;
- legitimate budget denial/deferral remains delayed rather than silently consumed or forced;
- ingest + durable ACK boundaries are explicit;
- restart does not infer that a model request completed when execution state is unknown;
- old trace data is never overwritten to make a new run look clean;
- fixture / hash / pin mismatches fail closed;
- zero-release mechanical checks are separate from real Resident execution;
- sequence 14..22 and session/clock boundaries remain consistent;
- no synthetic mechanics result is mislabeled as a real Resident PASS.

Protocol: owner-selected **rules constraints + process audit**. Do not add a new hard-isolation start requirement, but do not claim hard isolation, and missing audit records cannot prove non-contamination.

## Gates

At minimum:
1. the three exact regression tests above;
2. all directly affected `tests/preflight/**`;
3. the current operator preflight workflow;
4. relevant current-main Core regression needed to show the tooling did not alter Core semantics;
5. no real A/B/C, no provider run, no sealed future consumption.

Report passed / failed / skipped separately. Preserve raw logs.

## Deliverable and stop condition

Open a focused PR from your fresh branch. Include:
- live-main base SHA;
- PR #125 source head;
- exact file provenance of selectively ported assets;
- before-fix reproduction;
- minimal fixes;
- exact commands / CI run IDs and raw evidence;
- explicit statement that no Resident was run and no Core code was changed.

Your own status may be `REVIEW_READY`, never `DONE`. Stop after opening the candidate PR. A different independent reviewer must accept it before PM integration.
