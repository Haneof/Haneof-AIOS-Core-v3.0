# CORE-GAP-FIX-003 POST-FIX001 Revalidation Independent Acceptance — 2026-09-24

Status: **ACCEPTANCE_PASS**

Task: `CORE-GAP-FIX-003-POST-FIX001-INDEPENDENT-ACCEPTANCE`  
Role: Independent Core Runtime / User-Turn Recovery Final Acceptance Reviewer  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Candidate: PR #157 — `CORE-GAP-FIX-003: recover user-turn IN_DOUBT safely`

This review is review-only. It does not modify PR #157, Core code, tests, task board, checkpoint, Resident evidence, fixtures, operator state, UI, hardware, or private World state, and it does not merge PR #157.

## 1. Final pins and gate

Review-time and final-recheck live main:

`b4d26ee29a89844128a63e5b7a99793c1ec8a982`

PR #157 final pin:
- OPEN
- UNMERGED
- non-draft
- mergeable
- exact head `7c0c51a7e9cda41a5aa61357ebba96955948a4a7`
- GitHub base `9cfcd2d7e5293e0596eb1de5c203f61213973494`
- changed files: 6

The live task board and checkpoint both authorize:

`CORE-GAP-FIX-003-CORRECTIVE-001 = GATE / REVIEW_READY (POST-FIX001)`

The controlling post-FIX001 acceptance prompt, FIX-001 integration receipt, post-FIX002 parallelism ruling, historical failed review, corrective serialization review, current PR #157 body and current PR diff were independently re-read.

Historical chain is preserved:
- failed reviewed head: `81d626820cfa31e4f3f1aba0e892eb48cb11e46c`
- historical review #162: ACCEPTANCE_FAIL
- historical blocker: `CORE-GAP-FIX-003-ACCEPT-BLOCKER-001`
- corrective pre-FIX001 head: `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`
- historical corrective review #174: REBASE_REVALIDATION_REQUIRED
- only this post-FIX001 head is accepted by this report.

## 2. Candidate scope

Against the FIX-001-integrated base `9cfcd2d7...`, GitHub compare reports exactly six changed files:

1. `reviews/CORE_GAP_FIX_003_COMPLETION_EVIDENCE_2026-09-24.md`
2. `src/aios_core/runtime/__init__.py`
3. `src/aios_core/runtime/background_attempt.py`
4. `src/aios_core/runtime/turn_execution.py`
5. `src/aios_core/runtime/turn_runtime.py`
6. `tests/runtime/test_turn_execution_recovery.py`

No task-board/checkpoint, historical Resident evidence, fixture, operator, UI, hardware, or workflow file is modified by PR #157.

Scope verdict: **PASS**.

## 3. Merge / rebase construction

Exact candidate `7c0c51a7...` is a real two-parent merge commit:

1. `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`
2. `9cfcd2d7e5293e0596eb1de5c203f61213973494`

The second parent contains integrated FIX-001.

Four FIX-001 source files outside the shared `turn_runtime.py` are byte-identical between `9cfcd2d7...` and the exact candidate:

- `src/aios_core/context/continuity.py` → `e3e107bec13e1ac24089ebd8a14631ac06c536eb`
- `src/aios_core/projections/all_dimensions.py` → `af6ee201586e0688a3d1ee0651b5e375d97f2fa6`
- `src/aios_core/query/search.py` → `e33fa1cd578717e98bdc32e4081b66239600ff6d`
- `src/aios_core/recommendation/proactive.py` → `72ca76d01792216b902e1779521bdd3b979f258d`

The shared `src/aios_core/runtime/turn_runtime.py` is a new reconstructed blob:
- corrective parent blob: `a4ffcf5da0a91c3b44c039ea9fc417f1e05d99df`
- FIX-001 main blob: `1ce05ef28ef293c0ff2af1177beea327ddf65690`
- merged exact-head blob: `1b1ce75e1c6f92c253a98a561785bf483d983152`

Fresh review of the merged blob finds both semantic families present and active.

Construction verdict: **PASS**.

## 4. CG-003 corrective semantics

The exact candidate defines:

`TURN_PRE_ATTEMPT_PROTOCOL = "model_attempt_pre_admission_v1"`

and retains:

`TURN_MODEL_ATTEMPT_PROTOCOL = "model_attempt_v1"`

Fresh user-turn ordering is:

1. durable exact user-turn claim under `model_attempt_pre_admission_v1`;
2. deterministic round-0 `background_model_attempts.admit(... work_kind="user_turn" ...)`;
3. promotion with `mark_initial_attempt_admitted(...)` to `model_attempt_v1`;
4. ordinary pre-model work and provider dispatch.

Provider dispatch is structurally unreachable during the zero-attempt pre-admission phase.

`TurnExecutionStore._disposition()` preserves the required negative cases:
- legacy / NULL protocol + zero attempts -> IN_DOUBT
- old `model_attempt_v1` + zero attempts -> IN_DOUBT
- only explicit `model_attempt_pre_admission_v1` + zero attempts -> mechanically safe-to-retry

Once any attempt row exists, attempt state is evaluated before the zero-attempt exception. Thus a stale/forged pre-admission marker cannot override a real attempt ledger.

Retry authorization:
- requires non-blank evidence;
- remains one-shot;
- is atomically consumed by claim;
- increments retry count;
- cannot be reused after a crash.

A09 remains fail-closed:
- exact subject/session/turn identity retained;
- immutable input hash revalidated;
- conflicting input raises `TurnInputConflict`;
- durable completion/output prevents model reinvocation.

Other required recovery behavior remains intact:
- `ModelDispatchNotSubmitted -> not_submitted`;
- ambiguous post-dispatch -> IN_DOUBT;
- `response_returned` -> non-retryable;
- completion recovery from durable assistant output is idempotent;
- deterministic round-0 attempt identity stays unique.

Historical blocker `CORE-GAP-FIX-003-ACCEPT-BLOCKER-001`: **CLOSED**.

CG-003 verdict: **PASS**.

## 5. FIX-002 compatibility

The accepted `background_model_attempts` ledger remains the sole provider-attempt truth store.

FIX-003 extends its work kinds from:
- `wake`
- `periodic_review`

to additionally include:
- `user_turn`

The accepted attempt states are unchanged:
- admitted
- dispatching
- not_submitted
- in_doubt
- response_returned
- metered

No second user-turn attempt ledger is introduced.

The SQLite CHECK expansion preserves existing Wake/Periodic Review rows in a transactional rebuild and recreates the existing indexes.

Fresh `turn_runtime.py` review shows:
- background attempt scope still has priority over user-turn scope;
- user-turn metering does not masquerade as background metering linkage;
- Wake / Periodic Review recovery, budget, lifecycle and completion flows are not redesigned.

Exact-head affected gates are green, including C09, P15, C14 runtime, C14 loop, and full P16.

FIX-002 verdict: **PASS**.

## 6. FIX-001 temporal read-cut and C14 lineage

The merged exact head retains:
- `_KnowledgeCutoffStoreView`;
- `knowledge_cutoff` enforcement on exact/list reads;
- search with `as_of=self._active_turn_time`;
- cutoff-aware AI-world/policy readers;
- active exact-read cutoff enforcement;
- direct C14 `_derive_c14_lineage_at_cutoff(summary_ref, active_write_time)`;
- bundle/member C14 `_derive_c14_lineage_at_cutoff(..., active_write_time)`.

Wake and Periodic Review retain their historical write/read time before model execution:
- Wake model-visible context is built from `active_write_time`, then `_active_turn_time = active_write_time`;
- Periodic Review model-visible context is built from `review_write_time`, then `_active_turn_time = review_write_time`.

The FIX-003 user-turn recovery state uses a separate `_active_user_turn_execution_id` and does not reset or bypass the temporal read-cut machinery.

C14 cutoff-aware lineage remains present in both direct and bundle paths.

FIX-001 / C14 compatibility verdict: **PASS**.

## 7. Exact-head CI

All 13 required workflow runs were independently fetched from GitHub and are `completed / success`, each with:

`head_sha = 7c0c51a7e9cda41a5aa61357ebba96955948a4a7`

Runs:
- P16 `35986286182`
- fused-turn-runtime `35986286308`
- C09 `35986286147`
- P15 `35986286137`
- C14 runtime `35986286215`
- C14 loop `35986286171`
- P9 `35986286173`
- P10 `35986286193`
- P11 `35986286157`
- P12 `35986286175`
- P14 `35986286246`
- constitutional cognition closure `35986286165`
- C15 cognition evidence policy `35986286133`

Exact-head CI verdict: **13/13 SUCCESS**.

## 8. Full P16 raw-log verification

Primary job:

`107589604043`

Raw job log was independently re-read.

Confirmed:
- CPython 3.12.14
- pytest 8.4.2
- pydantic 2.13.5
- direct command: `pytest -q`
- reached 100%
- independently counted progress: **662 pass markers**
- F = 0
- E = 0
- skip = 0
- xfail = 0
- xpass = 0
- job conclusion: SUCCESS

The raw checkout proves GitHub tested the PR synthetic merge:

`bc48d52286a5f3cc397ab87f70f58f90fb162e6e = Merge 7c0c51a7e9cda41a5aa61357ebba96955948a4a7 into 9cfcd2d7e5293e0596eb1de5c203f61213973494`

P16 verdict: **PASS**.

## 9. Independent adversarial probes

Because the local container could not resolve GitHub during this review, no local execution result is claimed.

Instead, an evidence-only GitHub probe PR was created without modifying PR #157:

- probe PR: #176
- probe base lineage: exact candidate `7c0c51a7...`, with then-live main containing only later governance/review drift
- probe head: `27f9339c1a53e69fb7129d0ddc752468c5769fa0`
- only added artifact: `tests/runtime/test_core_gap_fix_003_post_fix001_acceptance_probes.py`
- after evidence capture, PR #176 was **CLOSED / UNMERGED**

Two independent executable probes were added.

### Probe A — crash-x3 recovery

Three consecutive claim -> attempt-admission crashes were exercised with restart and fresh explicit authorization between attempts.

Assertions:
- zero provider calls during all three pre-admission crash windows;
- consumed authorization cannot be reused;
- retry_count advances monotonically;
- final continuation invokes provider exactly once;
- deterministic round-0 attempt row count = 1;
- assistant output row count = 1;
- final turn state = completed.

Result: **PASS**.

### Probe B — forged/stale pre-admission marker with real IN_DOUBT ledger

The probe first created a real user-turn provider attempt and drove it to `in_doubt`, then manually forged the turn marker back to `model_attempt_pre_admission_v1`.

Assertions:
- inspection remains `in_doubt`;
- real attempt count remains one;
- real attempt state remains `in_doubt`;
- retry authorization is rejected;
- ordinary rerun is rejected;
- provider is not called a second time.

Result: **PASS**.

Probe PR #176 triggered the same 13 PR workflows and all **13/13 completed SUCCESS**.

Its P16:
- run `35987450415`
- job `107593343933`
- CPython 3.12.14
- pytest 8.4.2
- pydantic 2.13.5
- direct `pytest -q`
- 100%
- **664 pass markers / 0 fail / 0 error / 0 skip / 0 xfail / 0 xpass**

The exact candidate P16 had 662 pass markers; the probe P16 had 664, matching the two added adversarial tests.

Independent adversarial verdict: **PASS**.

## 10. Late-main drift

Candidate absorbed baseline:

`9cfcd2d7e5293e0596eb1de5c203f61213973494`

Final review-time main:

`b4d26ee29a89844128a63e5b7a99793c1ec8a982`

GitHub compare reports only:
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `governance/prompts/CORE_GAP_FIX_003_POST_FIX001_REVALIDATION_ACCEPTANCE_2026-09-24.md`
- `reviews/CORE_GAP_FIX_003_CORRECTIVE_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

No `src/**`, test, or workflow change exists in this drift.

Therefore the late drift is review/governance-only and does **not** require another candidate rebase.

Live-main drift verdict: **NON-SEMANTIC / NO REBASE REQUIRED**.

## 11. Final verdict

Blocker count: **0**

- CG-003 corrective mechanism: PASS
- legacy / old-v1 zero-attempt fail-closed: PASS
- attempt-ledger dominance: PASS
- repeated crash / at-most-once provider execution: PASS
- A09 / conflicting input: PASS
- FIX-002 compatibility: PASS
- FIX-001 temporal read-cut: PASS
- C14 cutoff-aware lineage: PASS
- merge/rebase construction: PASS
- exact-head 13/13 workflows: PASS
- full P16 raw log: PASS
- independent adversarial probes: PASS
- late-main drift: non-semantic

# **ACCEPTANCE_PASS**

**PR #157 post-FIX001 exact candidate 7c0c51a7e9cda41a5aa61357ebba96955948a4a7 is independently accepted for PM integration.**

PR #157 remains OPEN / UNMERGED. This reviewer does not merge it.
