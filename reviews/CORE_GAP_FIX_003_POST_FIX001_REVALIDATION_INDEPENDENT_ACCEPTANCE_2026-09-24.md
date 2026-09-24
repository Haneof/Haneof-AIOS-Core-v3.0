# CORE-GAP-FIX-003 POST-FIX001 Revalidation — Independent Acceptance

Date: 2026-09-24  
Task: `CORE-GAP-FIX-003-POST-FIX001-INDEPENDENT-ACCEPTANCE`  
Role: Independent Core Runtime / User-Turn Recovery Final Acceptance Reviewer  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Review mode: review-only; no candidate repair, no merge, no Resident, no HEADLESS.

## 1. Review pins

Review-time live main:

`b4d26ee29a89844128a63e5b7a99793c1ec8a982`

Candidate:

- PR #157 — `CORE-GAP-FIX-003: recover user-turn IN_DOUBT safely`
- state at final re-pin: OPEN / UNMERGED / non-draft / mergeable
- exact head: `7c0c51a7e9cda41a5aa61357ebba96955948a4a7`
- candidate head remained unchanged throughout this acceptance.

This is a fresh acceptance of the post-FIX001 exact head. The old corrective head
`ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d` and prior review PRs are historical
evidence only and are not reused as acceptance authority.

## 2. Governance gate

The live task board/checkpoint were re-read and authorize:

`CORE-GAP-FIX-003-CORRECTIVE-001 = GATE / REVIEW_READY (POST-FIX001)`

The controlling S2 post-FIX002 ruling requires serialized integration: because FIX-001
integrated first, FIX-003 had to absorb that live main, rerun targeted/full gates, form a
new exact head, and receive fresh independent acceptance. The reviewed head satisfies that
required construction.

## 3. Merge/rebase construction and scope

Independent ancestry checks show both required histories are contained in the exact head:

- `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d -> 7c0c51a7...`: status `ahead`,
  merge-base = `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`;
- FIX-001-integrated `9cfcd2d7e5293e0596eb1de5c203f61213973494 -> 7c0c51a7...`:
  status `ahead`, merge-base = `9cfcd2d7e5293e0596eb1de5c203f61213973494`.

Relative to the FIX-001-integrated baseline `9cfcd2d7...`, the exact candidate changes
exactly six intended FIX-003 files:

1. `reviews/CORE_GAP_FIX_003_COMPLETION_EVIDENCE_2026-09-24.md`
2. `src/aios_core/runtime/__init__.py`
3. `src/aios_core/runtime/background_attempt.py`
4. `src/aios_core/runtime/turn_execution.py`
5. `src/aios_core/runtime/turn_runtime.py`
6. `tests/runtime/test_turn_execution_recovery.py`

No task-board/checkpoint, Resident, fixture, operator, UI, or hardware file is in the
candidate diff.

The `turn_runtime.py` candidate patch is additive/user-turn recovery scoped: it adds
user-turn attempt scope and recovery APIs but does not remove or rewrite the integrated
FIX-001 cutoff machinery, Wake historical-cut logic, Periodic Review historical-cut
logic, or C14 cutoff-lineage implementation.

Construction verdict: **PASS**.

## 4. CG-003 recovery semantic review

Fresh source review of the merged exact head confirms:

1. a fresh turn is durably claimed under
   `model_attempt_pre_admission_v1`;
2. deterministic round-0 `user_turn` attempt admission occurs before ordinary pre-model
   preparation;
3. protocol promotion to `model_attempt_v1` occurs only after that deterministic
   attempt row is durable;
4. zero attempts are mechanically safe only for the explicit pre-admission protocol;
5. legacy/no-protocol zero-attempt rows remain `IN_DOUBT`;
6. old `model_attempt_v1 + zero attempts` rows remain `IN_DOUBT`;
7. once an attempt exists, the shared attempt ledger dominates disposition;
8. `admitted/not_submitted` can support explicit authorization;
9. `dispatching/in_doubt` remain fail-closed;
10. `response_returned` remains non-retryable;
11. retry authorization requires non-blank evidence and is atomically one-shot;
12. durable assistant-output completion recovery remains idempotent;
13. conflicting input is checked by identity hash and remains fail-closed.

The original claim-to-initial-attempt crash dead zone is therefore closed without
generalizing zero-attempt safety.

CG-003 recovery verdict: **PASS**.

## 5. FIX-001 compatibility

The accepted temporal-read-cut family remains present on the exact merged head:

- `_KnowledgeCutoffStoreView` still forces `knowledge_cutoff` into World-store exact
  and list reads;
- user-turn model-visible context is assembled using the turn's historical `occurred_at`
  cut for AI-world context, World map, policy context, proactive recall, and related
  readers before model execution;
- runtime capabilities use `_active_turn_time` during model execution, including
  `search_world(... as_of=_active_turn_time)` and exact-read cutoff enforcement;
- Wake context uses `active_write_time`, then activates the same cut for model/capability
  execution;
- resumed Periodic Review derives `review_write_time` from the original start and uses
  that timestamp for cockpit readers and active runtime cutoff;
- direct and bundle/member C14 paths both invoke
  `_derive_c14_lineage_at_cutoff(..., active_write_time)`, which uses the cutoff Store
  view for dependency enumeration and leaf traversal;
- FIX-003's active user-turn attempt scope neither resets nor bypasses these temporal-cut
  readers.

Exact-head C09/P15/C14/Fused/P16 gates are green.

FIX-001 compatibility verdict: **PASS**.

## 6. FIX-002 compatibility

FIX-003 reuses the accepted `background_model_attempts` ledger as the sole provider-attempt
truth store. It does not create a second ledger.

The storage extension:

- adds `user_turn` to the existing `work_kind` domain;
- rebuilds the SQLite CHECK-constrained table transactionally for an old FIX-002 schema;
- copies all existing attempt columns/rows into the replacement table;
- recreates the existing work/state indexes;
- leaves attempt state meanings unchanged.

The shared transition semantics remain:

- `admitted/not_submitted -> safe_to_retry`;
- `dispatching/in_doubt -> in_doubt`;
- durable `response_returned` is not blindly retried;
- deterministic identity remains
  `subject_id + work_kind + work_id + model_round_index`.

The candidate regression explicitly preserves a legacy Wake `not_submitted` row through
schema upgrade and admits a user-turn row afterward. Exact-head C09 Wake, P15 Periodic
Review, both C14 suites, and full P16 all pass.

FIX-002 compatibility verdict: **PASS**.

## 7. A09 compatibility

A09 at-most-once / identity safety remains intact:

- input hash is validated before retry/reconciliation action;
- a reused turn identity with conflicting input raises `TurnInputConflict`;
- ordinary rerun of a started/interrupted turn remains refused absent live authorization;
- authorization requires non-blank evidence;
- authorization is consumed atomically in `claim()` and increments `retry_count`;
- repeated retries reuse the deterministic round-0 attempt identity;
- durable assistant output prevents a second provider execution.

A09 compatibility verdict: **PASS**.

## 8. Fresh independent adversarial probes

Fresh probe PR #177 was created from the exact candidate itself:

- base SHA: `7c0c51a7e9cda41a5aa61357ebba96955948a4a7`
- probe commit: `7b1bb70ccf17fdc73b908dd169a92549affc9846`
- changed only:
  `tests/runtime/test_turn_execution_postfix001_independent_probes.py`
- it did not modify PR #157;
- it was closed UNMERGED after evidence capture.

Probe A — three consecutive pre-admission crashes:

- each crash occurred before deterministic initial attempt admission;
- provider calls remained zero through all three crashes;
- each retry required a fresh explicit authorization;
- consumed authorization could not be reused;
- final continuation called provider exactly once;
- final deterministic round-0 attempt rows = 1;
- final assistant-output rows = 1;
- final state = completed.

Probe B — stale pre-admission marker plus a real in-doubt attempt:

- a deterministic round-0 attempt was made durable while the turn still carried the
  pre-admission marker;
- the real attempt was driven through dispatching to `in_doubt`;
- recovery disposition remained `in_doubt`;
- retry authorization was rejected;
- therefore the attempt ledger dominates the stale marker.

Probe P16:

- run `35987509779`
- job `107593533059`
- checkout:
  `Merge 7b1bb70ccf17fdc73b908dd169a92549affc9846 into 7c0c51a7e9cda41a5aa61357ebba96955948a4a7`
- CPython 3.12.14 / pytest 8.4.2 / pydantic 2.13.5
- command: `pytest -q`
- 100%
- independently counted: **664 pass markers / 0 fail / 0 error / 0 skip / 0 xfail/xpass**
  (the exact candidate has 662; the two fresh probes account for the +2)
- conclusion: SUCCESS.

Adversarial-probe verdict: **PASS (2/2)**.

## 9. Exact-head workflow evidence

For exact head `7c0c51a7e9cda41a5aa61357ebba96955948a4a7`, all 13 required
pull-request workflows were independently re-read from GitHub run metadata and are SUCCESS:

- p16-convergence-gate — `35986286182`
- fused-turn-runtime — `35986286308`
- c09-wake-dispatch — `35986286147`
- p15-periodic-review — `35986286137`
- c14-cognitive-derivation-runtime — `35986286215`
- c14-cognitive-derivation-loop — `35986286171`
- p9-revision-gate — `35986286173`
- p10-ai-world-gate — `35986286193`
- p11-dimension-gate — `35986286157`
- p12-execution-gate — `35986286175`
- p14-long-context — `35986286246`
- constitutional-cognition-closure — `35986286165`
- c15-cognition-evidence-policy — `35986286133`.

Workflow verdict: **13/13 SUCCESS**.

## 10. P16 full regression

Authoritative exact-head P16:

- run: `35986286182`
- primary job: `107589604043`
- job: `full-core-regression`
- checkout:
  `Merge 7c0c51a7e9cda41a5aa61357ebba96955948a4a7 into 9cfcd2d7e5293e0596eb1de5c203f61213973494`
- CPython: 3.12.14
- pytest: 8.4.2
- pydantic: 2.13.5
- command: `pytest -q`
- reached 100%;
- independently counted progress: **662 pass markers / 0 fail / 0 error / 0 skip /
  0 xfail/xpass**;
- workflow/job conclusion: SUCCESS.

P16 verdict: **PASS**.

## 11. Live-main drift

Construction baseline absorbed by #157:

`9cfcd2d7e5293e0596eb1de5c203f61213973494`

Final review-time live main:

`b4d26ee29a89844128a63e5b7a99793c1ec8a982`

Independent compare `9cfcd2d7... -> b4d26ee2...` contains only:

- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `governance/prompts/CORE_GAP_FIX_003_POST_FIX001_REVALIDATION_ACCEPTANCE_2026-09-24.md`
- `reviews/CORE_GAP_FIX_003_CORRECTIVE_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`.

There is no `src/**`, test-contract, or workflow change in this drift.

Live-main drift verdict: **REVIEW/GOVERNANCE-ONLY — DOES NOT INVALIDATE CANDIDATE**.

## 12. Blockers and final verdict

Implementation blockers: **0**  
Serialization/revalidation blockers: **0**

# **ACCEPTANCE_PASS**

PR #157 post-FIX001 exact candidate 7c0c51a7e9cda41a5aa61357ebba96955948a4a7 is independently accepted for PM integration.

This review does not merge PR #157.
