# CORE-GAP-FIX-003-CORRECTIVE-001 Independent Acceptance — 2026-09-24

Status: **REBASE_REVALIDATION_REQUIRED**

Task: `CORE-GAP-FIX-003-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`  
Role: Independent Core Runtime / User-Turn Recovery Corrective Acceptance Reviewer  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Candidate: PR #157 — `CORE-GAP-FIX-003: recover user-turn IN_DOUBT safely`

This review is review-only. It does not modify PR #157, candidate Core code, candidate tests, task board, checkpoint, Resident evidence, fixtures, operator state, UI, hardware, or private World state. It does not merge PR #157.

The historical failed review remains authoritative and unchanged:
- review PR: #162
- historical report: `reviews/CORE_GAP_FIX_003_INDEPENDENT_ACCEPTANCE_2026-09-24.md`
- failed exact head: `81d626820cfa31e4f3f1aba0e892eb48cb11e46c`
- verdict: **ACCEPTANCE_FAIL**
- blocker: `CORE-GAP-FIX-003-ACCEPT-BLOCKER-001`

## 1. Review pins and live state

Review began on live main:

`bbc49af373ea7108385abc0549ca99332b7bb043`

The corrective candidate reviewed throughout this window was:

`ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`

PR #157 was independently re-read and remained:
- OPEN
- UNMERGED
- non-draft / ready for review
- head unchanged at `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`

At review start, FIX-001 PR #145 was still OPEN / UNMERGED.

During this review, FIX-001 corrective PR #145 was independently accepted by review PR #171 and then merged into main.

Final report-time live main:

`9cfcd2d7e5293e0596eb1de5c203f61213973494`

FIX-001 integration commit:

`d97a1bfa527caadb4ab22d232fd627c0483e02d8` — `Merge CORE-GAP-FIX-001 temporal read-cut corrective (#145)`

Final main then advanced governance-only to:

`9cfcd2d7e5293e0596eb1de5c203f61213973494` — `Merge FIX-001 integration writeback and FIX-003 revalidation routing (#172)`

That later drift changes only task-board/checkpoint/master-map and FIX-001 integration / FIX-003 rebase-routing governance files; no additional `src/**` change was introduced after the FIX-001 merge.

Integrated FIX-001 exact head:

`a56f113ace3c5e01af3acb724468bc2e0fbd4e98`

PR #145 final state:
- CLOSED
- MERGED
- merged_at: 2026-09-24T10:08:39Z

Therefore the post-FIX002 serialization ruling is now active for PR #157.

## 2. Governance gate

At review start, the live task board/checkpoint authorized:

`CORE-GAP-FIX-003-CORRECTIVE-001 = GATE / REVIEW_READY`

Required governance and evidence inputs were re-read:
1. `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
2. `AIOS_v3.0_CURRENT_CHECKPOINT.md`
3. `PROJECT_MASTER_MAP.md`
4. `reviews/CORE_GAP_AUDIT_001_2026-09-24.md`
5. `governance/prompts/CORE_GAP_FIX_003_2026-09-24.md`
6. `governance/prompts/CORE_GAP_FIX_003_CORRECTIVE_001_2026-09-24.md`
7. `governance/AIOS_CORE_S2_POST_FIX002_PARALLELISM_RULING_2026-09-24.md`
8. `governance/CORE_GAP_FIX_002_INTEGRATION_RECEIPT_2026-09-24.md`
9. `reviews/CORE_GAP_FIX_003_INDEPENDENT_ACCEPTANCE_2026-09-24.md`
10. `reviews/CORE_GAP_FIX_003_COMPLETION_EVIDENCE_2026-09-24.md`

The controlling serialization rule is explicit: if FIX-001 is accepted and integrated before FIX-003 acceptance completes, the current FIX-003 exact head cannot be accepted directly for PM integration. It must first absorb the new live main, rerun targeted/full gates, produce a new exact head, and receive fresh independent acceptance.

## 3. Corrective scope

Relative to failed head `81d626820cfa31e4f3f1aba0e892eb48cb11e46c`, the corrective delta is limited to:
1. `src/aios_core/runtime/turn_execution.py`
2. `src/aios_core/runtime/turn_runtime.py`
3. `tests/runtime/test_turn_execution_recovery.py`
4. `reviews/CORE_GAP_FIX_003_COMPLETION_EVIDENCE_2026-09-24.md`

No corrective change was found in:
- `background_attempt.py`
- `run_wake`
- `run_periodic_review`
- `_search_world`
- `_inspect_world_object`
- `_world_map_context`
- `AS_KNOWN`
- `knowledge_cutoff`
- governance/task board/checkpoint
- Resident/fixture/operator/UI/hardware surfaces

Corrective scope verdict: **PASS**.

## 4. Historical blocker reproduction

The old exact head was independently re-read and independently executed.

At `81d626820cfa31e4f3f1aba0e892eb48cb11e46c`:
1. `TurnExecutionStore.claim()` durably writes:
   - `state='started'`
   - `attempt_protocol='model_attempt_v1'`
2. only afterward does `FusedTurnRuntime.run_turn()` call the deterministic round-0 `background_model_attempts.admit(... work_kind='user_turn' ...)`.

A crash between those two durability boundaries leaves:
- started turn
- `model_attempt_v1`
- zero user-turn attempts
- no assistant output
- provider never called
- disposition `IN_DOUBT`
- retry authorization rejected
- ordinary rerun blocked by A09

Independent executable reproduction:
- review-only probe PR #167
- base: failed exact head `81d626820cfa31e4f3f1aba0e892eb48cb11e46c`
- probe head: `dd38b727860021c0b0c2b9f6605956573dca1a0e`
- P16 run: `35984201451`
- job: `107582917968`
- command: `pytest -q`
- result: SUCCESS with the blocker-state assertions holding
- PR #167 was closed unmerged after evidence capture

Historical blocker verdict:

**CORE-GAP-FIX-003-ACCEPT-BLOCKER-001 = REAL / REPRODUCIBLE.**

The old #162 ACCEPTANCE_FAIL is preserved as valid historical evidence.

## 5. Corrective pre-admission invariant

The corrective introduces:

`model_attempt_pre_admission_v1`

Its narrow meaning is:

> the exact user-turn identity is durably claimed, but deterministic round-0 provider-attempt admission is not yet durable; by runtime ordering, provider dispatch is structurally unreachable.

Fresh claim ordering is now:
1. claim exact turn identity with `model_attempt_pre_admission_v1`;
2. durably admit deterministic round-0 row in shared `background_model_attempts`;
3. promote the same turn execution to `model_attempt_v1`;
4. use the shared attempt ledger as provider-execution truth from that point onward.

Promotion:
- revalidates the same input hash;
- preserves subject/session/turn identity;
- preserves execution identity;
- requires the same round-0 attempt row to exist;
- changes only the turn protocol marker;
- does not create a second provider-attempt truth store.

Pre-admission invariant verdict: **PASS on reviewed exact head**.

## 6. Zero-attempt negative cases

Source and exact-head regression review confirmed:

1. `started + protocol=NULL + zero attempt` -> **IN_DOUBT**
2. `started + model_attempt_v1 + zero attempt` -> **IN_DOUBT**
3. `started + model_attempt_pre_admission_v1 + zero attempt` -> **safe_to_retry**, but execution still requires explicit authorization

No migration backfills legacy rows with the new pre-admission marker.

Legacy compatibility verdict: **PASS**.

## 7. Attempt-ledger dominance

If any user-turn attempt row exists, recovery disposition evaluates the shared attempt state before the zero-attempt pre-admission rule.

Thus:
- admitted / proven not_submitted may support explicit retry
- dispatching / in_doubt remain fail-closed
- response_returned remains non-retryable
- stale pre-admission marker cannot override a real attempt row

Independent adversarial probe PR #168 deliberately created:
- pre-admission marker
- a real deterministic round-0 attempt
- attempt state driven to `in_doubt`

Observed:
- recovery disposition remained `in_doubt`
- `authorize_turn_retry(...)` raised `TurnExecutionInDoubt`

Attempt-ledger dominance verdict: **PASS**.

## 8. Repeated crash / one-shot authorization

Author regression covers the required double crash.

This review added stronger independent crash-x3 execution without modifying PR #157:

- review-only probe PR #168
- base: corrective exact head `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`
- probe head: `111a010b35ca5ee05970670183a83d113de872e3`
- P16 run: `35984281832`
- job: `107583182127`
- Python 3.12.14
- pytest 8.4.2
- pydantic 2.13.5
- command: `pytest -q`
- result: SUCCESS
- PR #168 was closed unmerged after evidence capture

Crash-x3 assertions:
- each pre-attempt crash restarted with zero attempts and zero provider calls;
- each consumed authorization could not be reused;
- a fresh explicit non-blank authorization was required for each next retry;
- `retry_count` advanced monotonically;
- after three crashes, final continuation invoked provider exactly once;
- deterministic round-0 attempt row count = 1;
- assistant output row count = 1;
- final state = completed.

Repeated crash verdict: **PASS**.

## 9. Deterministic attempt identity / A09

Provider-attempt identity remains the accepted FIX-002 identity:

`subject_id + work_kind + execution_id + model_round_index`

For user-turn round 0:
- `work_kind='user_turn'`
- `work_id=execution_id`
- `model_round_index=0`
- repeated admission cannot create a second identity/row
- restarts point back to the same deterministic attempt

A09 compatibility remains fail-closed:
- ordinary rerun of a started turn is refused without a live authorization;
- authorization requires non-blank evidence;
- claim atomically consumes the one-shot authorization and increments `retry_count`;
- conflicting input remains `TurnInputConflict`;
- durable assistant output/completed state prevents a second provider execution.

A09 verdict: **PASS on reviewed exact head**.

## 10. Original CG-003 recovery paths

The reviewed exact head preserves the previously correct CG-003 paths:

- pre-model known failure after attempt admission: recoverable only through explicit authorization;
- `ModelDispatchNotSubmitted` -> `not_submitted`;
- ambiguous post-dispatch interruption -> `IN_DOUBT`;
- `response_returned` remains non-retryable;
- later metering/output/completion failure after durable response does not re-call provider;
- missing durable assistant output is not treated as completed;
- durable assistant output with lost completion marker can forward-reconcile completed;
- completion recovery is idempotent;
- conflicting input remains fail-closed.

Original CG-003 semantic verdict: **PASS on reviewed exact head**.

## 11. FIX-002 compatibility

The corrective delta does not change `src/aios_core/runtime/background_attempt.py`; its blob is identical between failed head and corrective head.

The shared `background_model_attempts` table remains the sole provider-attempt truth store.

No corrective redesign was found in:
- Wake recovery
- Periodic Review recovery
- background attempt state meanings
- provider provenance
- response fingerprint
- metering linkage
- BudgetGate
- background lifecycle/completion
- migration/reopen semantics

Exact-head affected gates were green:
- C09 Wake — run `35979939212` SUCCESS
- P15 Periodic Review — run `35979939074` SUCCESS
- C14 runtime — run `35979940227` SUCCESS
- C14 loop — run `35979939170` SUCCESS
- full P16 — run `35979939137` SUCCESS

FIX-002 compatibility verdict: **PASS on reviewed exact head**.

## 12. FIX-001 ownership boundary and serialization

The corrective did not modify FIX-001-owned temporal-read semantics.

However, the required final serialization check changed during this review.

At review start:
- PR #145 = OPEN / UNMERGED

Before final report:
- independent FIX-001 corrective acceptance PR #171 = merged
- PR #145 = CLOSED / MERGED
- integrated FIX-001 exact head = `a56f113ace3c5e01af3acb724468bc2e0fbd4e98`
- new live main = `9cfcd2d7e5293e0596eb1de5c203f61213973494`

Current #157 head remains:

`ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`

Comparing the FIX-001-integrated live-main lineage to the current #157 head shows they are diverged from merge base `f8eb271453b12c3896cd55381b8bdb8dc5da5632`.

The live main lineage now contains the integrated FIX-001 Core changes including:
- `src/aios_core/query/search.py`
- `src/aios_core/runtime/turn_runtime.py`
- related temporal-cut consumers/tests

PR #157 also changes `src/aios_core/runtime/turn_runtime.py`.

Therefore the exact-head CI previously obtained for #157 does not validate the required serialized post-FIX001 integration state.

FIX-001 serialization verdict:

**REBASE_REVALIDATION_REQUIRED.**

This is not an implementation failure finding against the reviewed `ac8d5a43...` semantics. It is the mandatory serialized-integration gate. Live governance now also carries `governance/prompts/CORE_GAP_FIX_003_REBASE_AFTER_FIX001_2026-09-24.md`, matching this required next step.

## 13. Exact-head CI

All 13 requested workflows for corrective exact head:

`ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`

completed SUCCESS:

- P16 — `35979939137`
- fused-turn-runtime — `35979939118`
- C09 Wake — `35979939212`
- P15 — `35979939074`
- C14 runtime — `35979940227`
- C14 loop — `35979939170`
- P9 — `35979939152`
- P10 — `35979939223`
- P11 — `35979939158`
- P12 — `35979939191`
- P14 — `35979939076`
- constitutional cognition closure — `35979939267`
- C15 cognition evidence — `35979939165`

The workflows were `pull_request` runs. GitHub Actions checked out the PR synthetic merge ref. P16 checked out:

`7f3d5bb895a85e2cb1238a98311102fb32d4dbe9 = Merge ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d into 838410bc4995e915fd5686098f968120d8ee4e57`

That synthetic merge predates the later integration of FIX-001 into `d97a1bfa...`.

Exact-head CI verdict: **PASS for the reviewed pre-FIX001-merge state; not sufficient for post-FIX001 PM integration**.

## 14. P16 full regression

Run:

`35979939137`

Job:

`107569161737`

Raw log was independently re-read:
- Python 3.12.14
- pytest 8.4.2
- pydantic 2.13.5
- command: `pytest -q`
- progress completed to 100%
- repository author evidence records: 654 passed / 0 failed / 0 skipped / 0 errors
- workflow/job conclusion: SUCCESS

The independent adversarial probe branch also completed a full `pytest -q` P16 run successfully after adding the crash-x3 and ledger-dominance probes.

Full regression verdict: **PASS on reviewed exact head**, but must be rerun after the mandatory rebase/merge of current live main.

## 15. Superseded review-only PRs

During this review, before PR #145 was merged, two intermediate review-only PRs were created with an `ACCEPTANCE_PASS` conclusion:
- PR #169
- PR #170

After FIX-001 merged, those conclusions became invalid for PM integration under the serialization ruling.

Both PR #169 and PR #170 were explicitly marked **SUPERSEDED / UNMERGED** and closed without merge.

They must not be used as acceptance authority for PR #157.

Independent probe PRs:
- #167 — closed / unmerged
- #168 — closed / unmerged

remain evidence-only.

## 16. Required next step

Before PR #157 can return for PM integration:

1. merge/rebase current live main `9cfcd2d7e5293e0596eb1de5c203f61213973494` into the existing PR #157 branch;
2. resolve overlap, especially `src/aios_core/runtime/turn_runtime.py`, without weakening FIX-001 or FIX-003;
3. rerun FIX-003 targeted recovery tests and the affected FIX-001/FIX-002 gates;
4. rerun full P16 `pytest -q`;
5. produce a new exact candidate head;
6. perform a fresh independent acceptance on that new exact head.

Do not reuse the old exact-head CI as PM-integration evidence after the rebase.

## 17. Final verdict

Implementation blocker count found on reviewed corrective exact head: **0**.

Serialization gate condition: **1 — FIX-001 integrated before review completion**.

Final verdict:

# **REBASE_REVALIDATION_REQUIRED**

The corrective exact head `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d` independently demonstrated sound closure of `CORE-GAP-FIX-003-ACCEPT-BLOCKER-001`, preserved A09 safety, preserved FIX-002 provider-attempt truth, and passed the requested exact-head and adversarial checks. However, FIX-001 was independently accepted and merged before this acceptance completed. Under the governing serialization rule, this exact head is no longer eligible for direct PM integration.

PR #157 must remain unmerged until it is rebased/merged onto the new live main, re-tested, given a new exact head, and independently revalidated.
