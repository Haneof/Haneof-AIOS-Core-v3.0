# CORE-GAP-FIX-003-CORRECTIVE-001 Independent Acceptance — 2026-09-24

Status: **ACCEPTANCE_PASS**  
Task: `CORE-GAP-FIX-003-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`  
Role: Independent Core Runtime / User-Turn Recovery Corrective Acceptance Reviewer  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Candidate: PR #157 — `CORE-GAP-FIX-003: recover user-turn IN_DOUBT safely`

This review is review-only. It does not modify PR #157, Core implementation, candidate tests, task board, checkpoint, fixture, Resident evidence, or private World state, and it does not merge the candidate.

## 1. Pins and live state

- review began on live main: `bbc49af373ea7108385abc0549ca99332b7bb043`
- report-time / final review-time main: `5532772a4bebbe36eb545e690b3b0efe834260b9`
- main drift during review: `bbc49af...` -> `5532772...`, 4 commits ahead / 0 behind, changing only:
  - `AIOS_v3.0_CURRENT_CHECKPOINT.md`
  - `PROJECT_MASTER_MAP.md`
  - `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- the drift is governance-only FIX-001 corrective gate writeback; no `src/**` drift occurred.
- reviewed PR: #157
- failed historical exact candidate: `81d626820cfa31e4f3f1aba0e892eb48cb11e46c`
- corrective exact candidate: `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`
- final PR #157 state: OPEN / UNMERGED / Ready for review
- final GitHub mergeability: `mergeable=true`, `mergeable_state=clean`, `rebaseable=true`
- FIX-001 PR #145 final state: OPEN / UNMERGED at `a56f113ace3c5e01af3acb724468bc2e0fbd4e98`; `mergeable=true`, `mergeable_state=clean`
- therefore the post-FIX002 serialized-integration rule has **not** triggered `REBASE_REVALIDATION_REQUIRED`.

The historical report `reviews/CORE_GAP_FIX_003_INDEPENDENT_ACCEPTANCE_2026-09-24.md` remains unchanged and remains **ACCEPTANCE_FAIL** with blocker `CORE-GAP-FIX-003-ACCEPT-BLOCKER-001`.

## 2. Gate / scope verification

Live governance at report time states:

`CORE-GAP-FIX-003-CORRECTIVE-001 = GATE / REVIEW_READY`

Corrective delta from failed head `81d62682...` to `ac8d5a43...` is exactly four files:

1. `src/aios_core/runtime/turn_execution.py`
2. `src/aios_core/runtime/turn_runtime.py`
3. `tests/runtime/test_turn_execution_recovery.py`
4. `reviews/CORE_GAP_FIX_003_COMPLETION_EVIDENCE_2026-09-24.md`

No corrective governance/task-board/checkpoint/Resident/fixture/operator/UI/hardware file is present.

The complete PR #157 patch contains no added/removed:
- `_search_world`
- `_inspect_world_object`
- `_world_map_context`
- `AS_KNOWN`
- `knowledge_cutoff`
- `run_wake`
- `run_periodic_review`

FIX-001 ownership is therefore not taken over by this candidate.

## 3. Historical blocker reproduction

Blocker:

`CORE-GAP-FIX-003-ACCEPT-BLOCKER-001`

Historical failed head behavior was re-read and independently executed.

At `81d62682...`:
1. `TurnExecutionStore.claim()` durably writes:
   - `state='started'`
   - `attempt_protocol='model_attempt_v1'`
2. only after that commit does `FusedTurnRuntime.run_turn()` call:
   - `background_model_attempts.admit(... work_kind='user_turn', model_round_index=0 ...)`

A process crash between those durability boundaries leaves:
- started turn;
- `model_attempt_v1`;
- zero user-turn attempts;
- zero assistant output;
- provider structurally not called.

Independent executable reproduction:
- review-only probe PR #167
- fixed base: historical failed exact head `81d626820cfa31e4f3f1aba0e892eb48cb11e46c`
- probe head: `dd38b727860021c0b0c2b9f6605956573dca1a0e`
- P16 run: `35984201451`
- job: `107582917968`
- command: `pytest -q`
- result: SUCCESS with the reproduction assertions holding
- observed/asserted state:
  - `recovery_disposition == 'in_doubt'`
  - zero attempts
  - provider calls = 0
  - explicit retry authorization rejected

Probe PR #167 was closed after evidence capture and was **not merged**.

**Old blocker verdict: REAL / REPRODUCIBLE.**

## 4. Corrective pre-admission invariant

The corrective introduces:

`model_attempt_pre_admission_v1`

Its accepted meaning is narrow:

> The exact user-turn execution identity has been durably claimed, but deterministic round-0 provider-attempt admission has not yet become durable; runtime ordering makes provider dispatch unreachable in this state.

Fresh claims now write the pre-admission protocol.

Disposition is fail-closed except for the explicit narrow case:
- protocol = `model_attempt_pre_admission_v1`
- user-turn attempt count = 0
- no durable assistant output

Only that zero-attempt combination is `safe_to_retry`.

Once an attempt row exists, disposition no longer treats the marker as provider truth. Attempt-ledger state controls recovery.

## 5. Zero-attempt negative cases / legacy compatibility

Exact-head regression plus source inspection confirm:

1. legacy `started + protocol=NULL + zero attempt` -> **IN_DOUBT**
2. old `started + model_attempt_v1 + zero attempt` -> **IN_DOUBT**
3. `started + model_attempt_pre_admission_v1 + zero attempt` -> **safe_to_retry**, still requiring explicit authorization before execution

Schema upgrade only adds the nullable `attempt_protocol` column when absent. It does **not** backfill historical rows with `model_attempt_pre_admission_v1`.

No nonexistent non-execution evidence is manufactured for legacy rows.

## 6. Pre-attempt -> attempt-protocol promotion

After deterministic round-0 `background_model_attempts` admission is durable, `mark_initial_attempt_admitted(...)`:

- revalidates the same immutable input hash;
- recomputes the same deterministic execution identity;
- requires the exact round-0 shared attempt row to exist;
- atomically updates only the same turn row from:
  - `model_attempt_pre_admission_v1`
  - to `model_attempt_v1`

It does not change subject/session/turn identity, does not change the input hash, and does not create a second provider-attempt store.

If an attempt exists, recovery is derived from the shared `background_model_attempts` state.

**Promotion verdict: PASS.**

## 7. Repeated-crash recovery

Author regression `test_cg003_claim_to_attempt_crash_is_repeatably_recoverable` covers two consecutive claim->attempt-admission crashes.

This review added a stronger independent crash-x3 probe without changing PR #157:

- review-only probe PR #168
- base: corrective exact head `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`
- probe head: `111a010b35ca5ee05970670183a83d113de872e3`
- P16 run: `35984281832`
- job: `107583182127`
- Python: 3.12.14
- pytest: 8.4.2
- pydantic: 2.13.5
- command: `pytest -q`
- whole-suite result: SUCCESS; 656 progress pass markers, no failure/skip/error marker

Independent crash-x3 assertions:

Crash #1:
- fresh claim durable
- crash before attempt admission
- zero attempts
- zero provider calls
- `safe_to_retry`
- `retry_count=0`

Crash #2:
- explicit authorization written
- claim atomically consumes it
- crash again before attempt admission
- zero attempts
- zero provider calls
- `safe_to_retry`
- `retry_count=1`
- ordinary retry without a new authorization is refused

Crash #3:
- second fresh authorization written
- claim consumes it
- crash again before attempt admission
- zero attempts
- zero provider calls
- `safe_to_retry`
- `retry_count=2`
- ordinary retry without a new authorization is refused

Final continuation:
- third fresh authorization written
- final claim consumes it
- final `retry_count=3`
- provider execution count = **1**
- deterministic round-0 attempt row count = **1**
- assistant output row count = **1**
- final disposition = completed
- attempt ID equals the deterministic `BackgroundModelAttemptStore.attempt_id_for(subject, 'user_turn', execution_id, 0)`

Probe PR #168 was closed after evidence capture and was **not merged**.

**Repeated crash verdict: PASS.**

## 8. Attempt-ledger dominance adversarial probe

The same independent probe PR #168 also manufactured a deliberate inconsistency:

1. fresh turn writes pre-admission marker;
2. deterministic round-0 attempt becomes durable;
3. protocol promotion is fault-injected to crash, leaving:
   - pre-admission marker
   - real attempt row
4. attempt ledger is then driven through dispatching to `in_doubt`.

Expected: attempt ledger must dominate the stale pre-admission marker.

Observed/asserted:
- attempt state = `in_doubt`
- turn recovery disposition = `in_doubt`
- `authorize_turn_retry(...)` raises `TurnExecutionInDoubt`

The pre-admission marker cannot override real attempt truth.

**Attempt-ledger dominance verdict: PASS.**

## 9. Deterministic attempt identity

The shared provider attempt identity remains:

`subject_id + work_kind + work_id/execution_id + model_round_index`

The implementation hashes exactly:

`[subject_id, work_kind, work_id, model_round_index]`

For user turns:
- `work_kind='user_turn'`
- `work_id=execution_id`
- round 0 stays round 0 across retries/restarts
- `INSERT OR IGNORE` plus the uniqueness constraint prevents a second row for the same identity
- `not_submitted` retry re-admits the same row instead of creating a new ID
- later model-round indices remain identity-separated

Crash-x3 independently confirms one round-0 row after repeated restart/retry.

**Attempt identity verdict: PASS.**

## 10. Authorization / A09 at-most-once

Authorization requires non-blank reconciliation evidence.

For the exact same turn/input identity:
- authorization is durable;
- `claim()` consumes it using a conditional `UPDATE ... WHERE retry_authorized=1`;
- the same update clears authorization and increments `retry_count`;
- a consumed authorization cannot be reused;
- each further retry requires a new explicit authorization.

Input identity remains bound to `user_input + occurred_at`. Candidate regression confirms conflicting input raises `TurnInputConflict` on both inspection and authorization.

Crash-x3 independently confirms one-shot authorization across three repeated failures.

**A09 / authorization verdict: PASS.**

## 11. Original CG-003 recovery paths

Exact-head recovery suite contains 11 tests and covers:

- claim->attempt repeated crash recovery;
- legacy/no-protocol and old-v1 zero-attempt negative cases;
- pre-model known failure after admitted attempt;
- `ModelDispatchNotSubmitted -> not_submitted`;
- explicit authorization before retry;
- ambiguous provider interruption -> `IN_DOUBT`;
- explicit reconciliation of an in-doubt attempt to proven `not_submitted`;
- durable `response_returned` with later metering failure -> no retry;
- assistant-output persistence failure -> no reinvocation;
- durable assistant output with lost completion marker -> forward completion recovery;
- completion recovery invoked twice -> idempotent;
- conflicting input -> `TurnInputConflict`;
- FIX-002 attempt-schema upgrade compatibility.

The completion-recovery regression explicitly calls `recover_turn_completion()` twice and then confirms ordinary `run_turn()` raises `TurnAlreadyCompleted`; provider call count remains one.

**Original CG-003 semantics verdict: PASS.**

## 12. FIX-002 compatibility

`background_model_attempts` remains the sole provider-attempt truth store.

The schema extension adds only `user_turn` to the existing work-kind CHECK while preserving existing attempt states:
- admitted
- dispatching
- not_submitted
- in_doubt
- response_returned
- metered

Transactional schema rebuild copies the existing identity/provenance fields including:
- attempt ID
- work identity
- round index
- admission world revision
- state
- provider/model/request ID
- response fingerprint
- meter record ID
- failure fields
- reconciliation evidence

Existing indexes are recreated unchanged.

No candidate patch modifies `run_wake` or `run_periodic_review`, and no metering/budget/background lifecycle module is in the changed-file set.

Exact-head compatibility gates:
- C09 Wake run `35979939212` — SUCCESS
- P15 Periodic Review run `35979939074` — SUCCESS
- C14 runtime run `35979940227` — SUCCESS
- C14 loop run `35979939170` — SUCCESS
- P16 run `35979939137` — SUCCESS

Relevant actual commands were re-read from logs:
- C09: wake + execution world + periodic review + reality ingest + fused turn + cognitive runtime
- P15: periodic review + fused turn + AI world + cognition revision + execution world + long context + cognitive runtime
- C14 targeted suites completed 100%
- no substantive skip/failure marker was observed.

**FIX-002 compatibility verdict: PASS.**

## 13. Exact-head CI

All 13 required workflow runs are tied by GitHub run metadata to PR #157 head:

`ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`

| Gate | Run | Result |
|---|---:|---|
| P16 | 35979939137 | SUCCESS |
| fused-turn-runtime | 35979939118 | SUCCESS |
| C09 Wake | 35979939212 | SUCCESS |
| P15 | 35979939074 | SUCCESS |
| C14 runtime | 35979940227 | SUCCESS |
| C14 loop | 35979939170 | SUCCESS |
| P9 | 35979939152 | SUCCESS |
| P10 | 35979939223 | SUCCESS |
| P11 | 35979939158 | SUCCESS |
| P12 | 35979939191 | SUCCESS |
| P14 | 35979939076 | SUCCESS |
| constitutional cognition closure | 35979939267 | SUCCESS |
| C15 cognition evidence | 35979939165 | SUCCESS |

The P16 checkout log pins the PR synthetic merge:

`7f3d5bb895a85e2cb1238a98311102fb32d4dbe9 = Merge ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d into 838410bc4995e915fd5686098f968120d8ee4e57`

No old green result is substituted for the corrective exact head.

**Exact-head CI verdict: PASS.**

## 14. Full P16 regression

Authoritative exact-head run:
- run: `35979939137`
- job: `107569161737`
- Python: 3.12.14
- pytest: 8.4.2
- pydantic: 2.13.5
- command: `pytest -q`
- job conclusion: SUCCESS
- observed progress: 654 pass markers to 100%
- no failed / skipped / error marker in the test progress

The independent corrective probe run adds two review-only tests on top of the exact candidate and also completes the full suite successfully:
- run `35984281832`
- job `107583182127`
- 656 pass progress markers to 100%
- no failed / skipped / error marker

**Full regression verdict: PASS.**

## 15. FIX-001 serialization decision

At review start, #145 was OPEN / UNMERGED.

Immediately before report creation:
- live main = `5532772a4bebbe36eb545e690b3b0efe834260b9`
- #145 = OPEN / UNMERGED
- #145 exact corrective head = `a56f113ace3c5e01af3acb724468bc2e0fbd4e98`
- #145 mergeability = clean
- main drift during this review was governance-only and did not integrate FIX-001 Core code.

Therefore this review does **not** enter `REBASE_REVALIDATION_REQUIRED`.

If #145 is accepted and merged before PM integrates #157, the active serialization ruling still requires #157 to be rebased/merged onto then-live main, all affected/full gates rerun, and a new independent acceptance performed on the resulting new exact head.

**FIX-001 serialization verdict: PASS for the currently reviewed exact head.**

## 16. Blocker register

New blockers: **0**

Historical blocker:
- `CORE-GAP-FIX-003-ACCEPT-BLOCKER-001`
- independently reproduced on the failed head
- closed by the reviewed corrective exact head

No historical report or blocker record was rewritten.

## 17. Final verdict

**ACCEPTANCE_PASS**

All required conditions are met:
- old blocker independently reproduced;
- pre-admission marker has narrow, mechanically justified semantics;
- legacy zero-attempt states remain fail-closed;
- repeated crash recovery works beyond the author’s two-crash case;
- authorization is explicit and one-shot;
- deterministic round-0 attempt identity remains singular;
- provider executes exactly once in the tested recovery sequence;
- assistant output persists exactly once;
- ambiguous provider state remains `IN_DOUBT`;
- attempt ledger dominates any stale pre-admission marker;
- response/completion safety remains fail-closed/idempotent;
- conflicting input remains fail-closed;
- FIX-002 background recovery compatibility passes;
- FIX-001 ownership boundary passes;
- exact-head CI passes;
- full regression passes;
- #145 has not been integrated first;
- blocker count = 0.

**PR #157 corrected exact candidate is independently accepted for PM integration.**

No merge is performed by this reviewer.
