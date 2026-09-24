# CORE-GAP-FIX-003-CORRECTIVE-001 Independent Acceptance — 2026-09-24

Status: **ACCEPTANCE_PASS**  
Task: `CORE-GAP-FIX-003-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`  
Role: Independent Core Runtime / User-Turn Recovery Corrective Acceptance Reviewer  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Candidate: PR #157 — `CORE-GAP-FIX-003: recover user-turn IN_DOUBT safely`

This review is review-only. It does not modify PR #157, candidate Core code, candidate tests, task board, checkpoint, historical Resident evidence, fixtures, operator state, UI, hardware, or private World state, and it does not merge the candidate.

The historical failed review remains authoritative for the old exact candidate:
- review PR: #162
- old exact candidate: `81d626820cfa31e4f3f1aba0e892eb48cb11e46c`
- verdict: **ACCEPTANCE_FAIL**
- blocker: `CORE-GAP-FIX-003-ACCEPT-BLOCKER-001`

This report does not overwrite or reinterpret that failure.

## 1. Pins and review-time live state

Final review-time main used to create this review-only branch:

`5532772a4bebbe36eb545e690b3b0efe834260b9`

The review began while live main was `bbc49af373ea7108385abc0549ca99332b7bb043`. During review, main advanced by four governance-only commits. The compare from `bbc49af...` to `5532772...` changes only:
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`

No `src/**` file changed in that drift.

PR #157 final pin:
- state: OPEN
- merged: false
- draft: false
- exact head: `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`
- base: `main`
- GitHub-recorded base SHA: `f8eb271453b12c3896cd55381b8bdb8dc5da5632`
- mergeable: true
- commits reported by GitHub: 12
- changed files reported by GitHub: 6
- additions/deletions: 1499 / 62
- synthetic merge SHA associated with current PR state: `7f3d5bb895a85e2cb1238a98311102fb32d4dbe9`

The available connector exposes `mergeable` but does not expose `mergeable_state` or `rebaseable` in its normalized PR result. Therefore this report does not invent those fields. The actual diff was inspected and GitHub reports `mergeable=true`; no conflicting file/content overlap was found.

Final FIX-001 serialization recheck before this report was written:
- PR #145: OPEN / UNMERGED / non-draft
- current #145 head: `a56f113ace3c5e01af3acb724468bc2e0fbd4e98`
- GitHub mergeable: true

Therefore FIX-001 has not been integrated and the serialized-integration ruling does not force a rebase/revalidation of this #157 exact head at review completion.

## 2. Governance gate

The final live task board and checkpoint both identify:

`CORE-GAP-FIX-003-CORRECTIVE-001 = GATE / REVIEW_READY`

with PR #157 pinned at:

`ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`

The same control state preserves:
- `CORE-GAP-FIX-003 = GATE / ACCEPTANCE_FAIL` for the old exact head;
- historical review #162;
- the original blocker;
- FIX-002 as DONE;
- FIX-001 corrective as a separate OPEN / UNMERGED candidate.

The post-FIX002 ruling was re-read. FIX-003 owns ordinary user-turn recovery/admission surfaces and may reuse FIX-002 provider-attempt primitives, but must not take over FIX-001 temporal read-cut semantics or change background Wake/Periodic Review recovery semantics.

Gate verdict: **AUTHORIZED FOR CORRECTIVE INDEPENDENT REVIEW**.

## 3. Candidate scope

Whole PR #157 currently contains six changed files:

1. `reviews/CORE_GAP_FIX_003_COMPLETION_EVIDENCE_2026-09-24.md`
2. `src/aios_core/runtime/__init__.py`
3. `src/aios_core/runtime/background_attempt.py`
4. `src/aios_core/runtime/turn_execution.py`
5. `src/aios_core/runtime/turn_runtime.py`
6. `tests/runtime/test_turn_execution_recovery.py`

The corrective delta specifically from failed exact head `81d62682...` to reviewed exact head `ac8d5a43...` is exactly two commits ahead, zero behind, and changes only four files:

1. `reviews/CORE_GAP_FIX_003_COMPLETION_EVIDENCE_2026-09-24.md`
2. `src/aios_core/runtime/turn_execution.py`
3. `src/aios_core/runtime/turn_runtime.py`
4. `tests/runtime/test_turn_execution_recovery.py`

No governance, task board, checkpoint, fixture, operator, Resident evidence, UI, hardware, second recovery database, or background-attempt implementation file is part of the corrective delta.

Patch inspection found no corrective ownership change involving:
- `_search_world`
- `_inspect_world_object`
- `_world_map_context`
- `AS_KNOWN`
- `knowledge_cutoff`
- `run_wake`
- `run_periodic_review`

Scope verdict: **PASS**.

## 4. Historical blocker reproduction

### 4.1 Old source behavior

The failed exact head `81d626820cfa31e4f3f1aba0e892eb48cb11e46c` was re-read directly.

Its fresh `TurnExecutionStore.claim()` inserted:

`attempt_protocol = model_attempt_v1`

The initial deterministic `background_model_attempts.admit(... work_kind='user_turn', model_round_index=0 ...)` was a later, separately durable operation.

The old disposition logic required:
- protocol = `model_attempt_v1`; and
- a non-empty attempt state list; and
- every attempt state in `admitted/not_submitted`

before returning `safe_to_retry`.

The old authorization logic likewise rejected zero-attempt states.

Therefore a process death after the turn claim committed but before the attempt row was admitted durably left:

- turn state = `started`
- protocol = `model_attempt_v1`
- user-turn attempt count = 0
- assistant output = none
- disposition = `IN_DOUBT`
- authorization = rejected
- reconciliation = no attempt to reconcile
- completion recovery = no durable output
- ordinary rerun = A09 refusal

### 4.2 Independent reproduction

A transaction/state-machine fault probe replaying the reviewed old SQL predicates produced:

- `state=started`
- `attempt_protocol=model_attempt_v1`
- `attempt_count=0`
- disposition = `in_doubt`
- retry authorization = rejected with `provider_execution_not_proven_absent`

No provider execution was necessary to create the stranded state.

Historical blocker verdict:

**CORE-GAP-FIX-003-ACCEPT-BLOCKER-001 = REAL / REPRODUCIBLE.**

The old #162 ACCEPTANCE_FAIL is therefore preserved as a valid historical finding, not an error.

## 5. Corrective pre-admission invariant

The corrective introduces:

`model_attempt_pre_admission_v1`

The source ordering is now:

1. exact user-turn identity is durably claimed with `attempt_protocol=model_attempt_pre_admission_v1`;
2. deterministic round-0 `user_turn` attempt is admitted into the shared `background_model_attempts` ledger;
3. only after that admission is durable, `mark_initial_attempt_admitted(...)` promotes the turn execution to `model_attempt_v1`;
4. all subsequent provider-boundary truth comes from the shared attempt row.

This marker therefore describes only the mechanical phase before a provider-attempt row can exist. Provider dispatch is structurally unreachable before that shared attempt admission.

`mark_initial_attempt_admitted(...)`:
- revalidates the exact input identity;
- requires the original execution row;
- refuses completed/durable-output states;
- refuses unknown protocols;
- requires the same subject/execution identity's round-0 `background_model_attempts` row;
- promotes only `pre_admission_v1 -> model_attempt_v1`;
- is idempotent if already promoted;
- does not create a second attempt store or second attempt identity.

Pre-admission invariant verdict: **PASS**.

## 6. Zero-attempt negative cases

The corrective disposition is intentionally asymmetric.

With zero attempt rows:
- `attempt_protocol = NULL` -> **IN_DOUBT**
- `attempt_protocol = model_attempt_v1` -> **IN_DOUBT**
- `attempt_protocol = model_attempt_pre_admission_v1` -> **safe_to_retry**

The new candidate test explicitly covers the first two negative cases. Independent predicate/state probes confirmed both remain fail-closed.

There is no schema migration that rewrites legacy `runtime_turn_executions` rows to `model_attempt_pre_admission_v1`.

Zero-attempt legacy compatibility verdict: **PASS**.

## 7. Attempt-ledger dominance and protocol promotion

If any user-turn attempt exists, `TurnExecutionStore._disposition(...)` enters the attempt-state branch before applying the zero-attempt pre-admission rule.

For both `model_attempt_pre_admission_v1` and `model_attempt_v1`:
- all attempt states limited to `admitted/not_submitted` -> safe-to-retry;
- any `dispatching/in_doubt/response_returned/metered` state -> IN_DOUBT unless durable output/completion already dominates;
- an unrecognized turn protocol with an attempt row -> IN_DOUBT.

The shared attempt store remains the provider-attempt truth:
- deterministic attempt ID = hash of `subject_id + work_kind + work_id + model_round_index`;
- unique key remains `subject_id, work_kind, work_id, model_round_index`;
- repeated admission cannot create a second round-0 row;
- an existing dispatching attempt is converted to `in_doubt` on restart and blocks;
- an existing `in_doubt` attempt blocks;
- an existing `response_returned` attempt blocks reinvocation.

No second provider-attempt truth store was introduced.

Attempt-ledger dominance verdict: **PASS**.

## 8. Independent repeated-crash adversarial probe

The author regression covers two crashes. This review independently extended the state-machine fault injection to **three consecutive pre-attempt crashes**.

Probe sequence:

### Crash 1

Fresh claim becomes durable as:
- protocol = pre-admission
- attempt count = 0
- provider calls = 0
- disposition = safe-to-retry
- retry_count = 0

Authorization #1 with non-blank evidence becomes durable.

The next claim atomically consumes authorization #1, advances retry_count to 1, and is then terminated again before attempt admission.

### Crash 2

After restart:
- protocol remains pre-admission
- attempt count = 0
- provider calls = 0
- disposition = safe-to-retry
- retry_count = 1
- old authorization bit = consumed

An ordinary claim without a new explicit authorization is refused.

Authorization #2 is then written and atomically consumed by the next claim, advancing retry_count to 2, followed by another synthetic crash before attempt admission.

### Crash 3

After restart:
- protocol remains pre-admission
- attempt count = 0
- provider calls = 0
- disposition = safe-to-retry
- retry_count = 2
- authorization #2 = consumed

A claim without authorization #3 is refused.

Authorization #3 is written. Final continuation:
- consumes authorization #3;
- admits deterministic round-0 attempt;
- repeated admission resolves to the same attempt identity/row;
- promotes protocol;
- provider executes exactly once;
- assistant output becomes durable once;
- turn completes.

Final probe counters:
- provider execution count: **1**
- deterministic round-0 attempt rows: **1**
- durable assistant output rows: **1**
- duplicate attempt IDs: **0**
- final retry_count: **3**

Repeated-crash verdict: **PASS**.

## 9. Independent forged-ledger adversarial probes

### Probe B — pre-admission marker + existing IN_DOUBT attempt

Constructed an inconsistent state containing:
- turn protocol = `model_attempt_pre_admission_v1`
- a real user-turn attempt row already present
- attempt state = `in_doubt`

Result:
- inspection = **IN_DOUBT**
- retry authorization = refused
- the marker did not override the attempt ledger

### Probe C — pre-admission marker + response_returned attempt

Constructed an inconsistent state containing:
- turn protocol = `model_attempt_pre_admission_v1`
- a real user-turn attempt row
- attempt state = `response_returned`

Result:
- inspection = **IN_DOUBT**
- retry authorization = refused
- the marker did not reinterpret a durable provider response as non-execution

These probes directly exercise the required conflict rule: once attempt truth exists, the pre-admission marker cannot fabricate safe non-execution evidence.

Adversarial ledger-dominance verdict: **PASS**.

## 10. Authorization and A09 at-most-once review

Retry authorization continues to require:
- exact turn identity;
- exact immutable input hash;
- non-blank reconciliation evidence;
- no durable assistant output/completed turn;
- either explicit pre-admission zero-attempt proof or a shared attempt ledger containing only admitted/not-submitted states.

The retry claim consumes authorization with a conditional update:

`retry_authorized=1 -> 0`

and atomically advances:

`retry_count = retry_count + 1`.

Independent repeated-crash probing confirmed a consumed authorization cannot be reused after restart. A second or third retry requires a new explicit authorization.

Conflicting input continues to fail through `TurnInputConflict`; retry authorization cannot be used to swap input or turn identity.

A09 verdict: **PASS**.

## 11. Original CG-003 recovery paths

The corrective does not regress the already-correct paths from the first acceptance review.

Re-read source plus exact-head regression coverage confirms:

- pre-model known failure after attempt admission -> attempt remains `admitted`; inspection safe-to-retry; explicit authorization still required;
- `ModelDispatchNotSubmitted` -> `not_submitted`; explicit authorization still required;
- ambiguous provider interruption after dispatch boundary -> `IN_DOUBT`; no blind authorization/retry;
- provider-side proof of not-submitted can reconcile an existing ambiguous attempt to `not_submitted`, then explicit authorization can proceed;
- durable `response_returned` followed by metering failure is non-retryable;
- assistant-output persistence failure after provider response does not cause provider reinvocation;
- durable assistant output with missing completion marker forward-reconciles to completed without model reinvocation;
- completion recovery called twice remains idempotent;
- conflicting input remains fail-closed.

Original CG-003 path verdict: **PASS**.

## 12. FIX-002 compatibility

The corrective delta from old failed head does not modify `background_attempt.py`.

The original FIX-003 extension continues to use the already accepted `background_model_attempts` store as the sole provider-attempt ledger. Existing accepted states remain:
- admitted
- dispatching
- not_submitted
- in_doubt
- response_returned
- metered

The deterministic identity formula, provider provenance, response fingerprint, meter linkage, background indexes, Wake rows, and Periodic Review rows are not changed by this corrective.

The earlier independent #157 review already validated the schema migration/reopen behavior and background row/index/provenance preservation; this corrective does not touch that mechanism.

Exact-head compatibility gates are also green:
- C09 Wake dispatch
- P15 Periodic Review
- C14 runtime
- C14 loop
- full P16

No `run_wake` or `run_periodic_review` source diff is present.

FIX-002 compatibility verdict: **PASS**.

## 13. FIX-001 ownership and serialization

Corrective patch inspection found no change to:
- search/inspect temporal read paths;
- world-map temporal context;
- AS_KNOWN;
- knowledge cutoff;
- historical read ordering;
- C14 temporal lineage/read-cut implementation.

PR #145 was checked at review start and again immediately before this report:
- OPEN
- UNMERGED
- exact corrective head `a56f113ace3c5e01af3acb724468bc2e0fbd4e98`

The task board now marks FIX-001 corrective REVIEW_READY, but the serialized-integration trigger is based on actual accepted/integrated ordering. #145 is not merged.

Therefore:

**FIX-001 serialization verdict: PASS — no rebase/revalidation trigger has fired for #157 in this review.**

If #145 is merged before PM integrates #157, the existing ruling still requires #157 to be rebased/merged onto that then-live main, gates rerun, a new exact head formed, and a new independent acceptance performed.

## 14. Exact-head GitHub Actions verification

GitHub Actions was re-read for exact candidate head:

`ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`

All 13 required pull-request workflow runs are `completed / success`:

| Gate | Run | Primary/targeted job | Result |
|---|---:|---:|---|
| p16-convergence-gate | 35979939137 | 107569161737 | SUCCESS |
| fused-turn-runtime | 35979939118 | 107569162132 | SUCCESS |
| c09-wake-dispatch | 35979939212 | 107569162444 | SUCCESS |
| p15-periodic-review | 35979939074 | 107569162009 | SUCCESS |
| c14-cognitive-derivation-runtime | 35979940227 | 107569166162 | SUCCESS |
| c14-cognitive-derivation-loop | 35979939170 | 107569162108 | SUCCESS |
| p9-revision-gate | 35979939152 | 107569162492 | SUCCESS |
| p10-ai-world-gate | 35979939223 | 107569162168 | SUCCESS |
| p11-dimension-gate | 35979939158 | 107569162197 | SUCCESS |
| p12-execution-gate | 35979939191 | 107569162237 | SUCCESS |
| p14-long-context | 35979939076 | 107569162348 | SUCCESS |
| constitutional-cognition-closure | 35979939267 | 107569162347 | SUCCESS |
| c15-cognition-evidence-policy | 35979939165 | 107569162645 | SUCCESS |

All inspected substantive job steps report `completed / success`; no substantive skipped/continue-on-error bypass was observed in the returned job-step metadata.

Both C14 workflows contain additional affected/full/habitation jobs and those jobs also completed SUCCESS.

Exact-head workflow verdict: **PASS**.

## 15. P16 full regression

P16:
- run: `35979939137`
- job: `107569161737`

Raw job log was independently re-read.

Checkout provenance:
`HEAD is now at 7f3d5bb Merge ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d into 838410bc4995e915fd5686098f968120d8ee4e57`

Environment:
- Python: **3.12.14**
- pytest: **8.4.2**
- pydantic: **2.13.5**

Actual test command:
`pytest -q`

The quiet progress output reaches 100% with **654 pass markers**, and no failed, skipped, or error marker was present. The job conclusion is SUCCESS.

From the synthetic-merge parent `838410bc...` to final review-time main `5532772...`, only the three governance status files listed in §1 changed; no Core source drift occurred after the tested merge parent.

Full regression verdict: **PASS — 654 passed / 0 failed / 0 skipped / 0 errors.**

## 16. Independent-probe execution note

The adversarial probes in §§4, 8 and 9 were independent transaction/state-machine probes replaying the exact reviewed SQLite predicates, keying, and transitions from the pinned source. They were not author tests and were not derived from the author's expected output.

The connector execution environment does not expose a mounted repository checkout, so this review does not claim a second locally executed repository-wide `pytest` run. The authoritative implementation-level full-suite execution is the exact-head GitHub Actions P16 run in §15. This limitation does not affect the direct source review, exact-head CI verification, or the independent crash/ledger state probes.

## 17. Blockers and final verdict

Blocker count: **0**

Acceptance conditions:
- old blocker independently reproduced: PASS
- pre-admission marker semantics: PASS
- legacy zero-attempt fail-closed: PASS
- old `model_attempt_v1 + zero attempts` fail-closed: PASS
- repeated crash x3 recovery: PASS
- one-shot authorization: PASS
- deterministic round-0 attempt identity: PASS
- provider exactly once under tested recovery: PASS
- assistant output exactly once: PASS
- ambiguous provider remains IN_DOUBT: PASS
- response_returned remains non-retryable: PASS
- completion recovery idempotent: PASS
- conflicting input fail-closed: PASS
- A09 compatibility: PASS
- FIX-002 compatibility: PASS
- FIX-001 ownership scope: PASS
- exact-head CI: PASS
- P16 full regression: PASS
- FIX-001 has not been integrated first: PASS
- blockers: 0

# Final verdict

**ACCEPTANCE_PASS**

**PR #157 corrected exact candidate `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d` is independently accepted for PM integration.**

This review does not merge PR #157.
