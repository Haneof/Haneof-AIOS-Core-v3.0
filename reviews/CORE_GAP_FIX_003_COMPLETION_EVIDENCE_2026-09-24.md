# CORE-GAP-FIX-003 Completion Evidence — 2026-09-24

Status: REVIEW_READY  
Task: CORE-GAP-FIX-003  
Finding addressed: CG-003 USER_TURN_IN_DOUBT_RECOVERY  
Role: Core Runtime / Recovery Engineer  
Repository: Haneof/Haneof-AIOS-Core-v3.0  
PR: #157

## 1. Construction baseline

- Construction live main: `f8eb271453b12c3896cd55381b8bdb8dc5da5632`
- FIX-002 prerequisite: DONE / independently accepted / integrated as `3d980fadf6beefcdd02ff4367ba834a5b013d871`
- Active ownership ruling: `governance/AIOS_CORE_S2_POST_FIX002_PARALLELISM_RULING_2026-09-24.md`
- FIX-003 scope respected: ordinary user-turn admission/recovery only; no temporal read-cut semantics and no background Wake/Periodic Review flow changes.

## 2. Before-fix reproduction

A test-only reproduction commit was created before implementation:

- reproduction SHA: `56529c399f9b455d9d08ed20ae1c559aaf664e18`
- workflow: `p16-convergence-gate`
- run: `35966719207`
- job: `107526845648`
- conclusion: FAILURE

Observed current-main failures:
- no supported `inspect_turn_execution` API;
- no supported `reconcile_turn_model_not_submitted` API;
- no explicit retry-authorization path;
- no supported completion reconciliation;
- accepted FIX-002 attempt ledger rejected `work_kind='user_turn'`.

The failure was preserved; the reproduction commit was not rewritten.

## 3. Implemented recovery semantics

### A09 admission remains fail-closed

`runtime_turn_executions` remains the ordinary user-turn at-most-once admission gate keyed by:
- subject;
- session;
- turn index;
- immutable input hash.

Same identity + conflicting input still raises `TurnInputConflict`.
A started turn still cannot be blindly rerun.

### Shared durable provider-attempt ledger

FIX-003 extends the accepted FIX-002 `background_model_attempts` ledger with a third work kind:

- `user_turn`

It does not create a second provider-attempt truth store.

Existing Wake / Periodic Review rows are preserved by schema migration, and the existing FIX-002 states remain unchanged:

- `admitted`
- `dispatching`
- `not_submitted`
- `in_doubt`
- `response_returned`
- `metered`

### Pre-model known failure

A user-turn model attempt is admitted before ordinary pre-model preparation work.

If execution fails before `mark_dispatching()`, durable state remains `admitted`.
For user turns, this is accepted as durable proof that the provider boundary was not crossed.

A retry is still not automatic: an explicit authorization transition is required.

### Definitely-not-submitted provider failure

`ModelDispatchNotSubmitted` durably transitions the attempt to `not_submitted`.

Inspection reports `safe_to_retry`, but `run_turn()` remains fail-closed until `authorize_turn_retry(..., evidence=...)` is called.

### Ambiguous provider failure

Any failure after the dispatch boundary without a durable provider response becomes/remains `in_doubt`.

Neither restart nor explicit retry authorization can reinvoke the provider while execution is unproven.

### Durable response, incomplete later work

A returned provider response is durably recorded as `response_returned` before later Core work.

If metering or assistant-output persistence fails afterward, retry remains blocked because provider execution already occurred.

### Durable assistant-output completion recovery

If assistant output is durably present but the turn completion marker was interrupted, inspection reports completion from the durable assistant receipt.

`recover_turn_completion(..., evidence=...)` forward-reconciles the execution to completed without another model call.

No table clearing, history mutation, turn-id swapping, or silent reinvocation is used.

## 4. Required regression coverage

`tests/runtime/test_turn_execution_recovery.py` covers:

1. pre-model known failure;
2. known provider non-submission;
3. ambiguous provider interruption;
4. explicit provider reconciliation to not-submitted;
5. provider response/provenance durable but later meter interruption;
6. assistant-output persistence failure;
7. completed-output recovery without model reinvocation;
8. conflicting input during recovery;
9. restart/reopen behavior;
10. FIX-002 background-attempt schema compatibility.

## 5. Candidate verification

The latest implementation code head before this evidence-only commit:

- `41cefb97a813a5d2575967e18fa5256595364efe`

All 13 triggered workflows completed SUCCESS on that exact code head:

- `p16-convergence-gate` run `35967438925`, job `107529113737`
- `fused-turn-runtime` run `35967438912`, job `107529113445`
- `c09-wake-dispatch` run `35967438990`, job `107529114107`
- `p15-periodic-review` run `35967439068`, job `107529114151`
- `c14-cognitive-derivation-runtime` run `35967439137`
- `c14-cognitive-derivation-loop` run `35967438968`
- `constitutional-cognition-closure` run `35967438909`
- `p9-revision-gate` run `35967439039`
- `p10-ai-world-gate` run `35967439071`
- `p11-dimension-gate` run `35967439146`
- `p12-execution-gate` run `35967438989`
- `p14-long-context` run `35967438953`
- `c15-cognition-evidence-policy` run `35967439021`

The C09/P15/C14 successes are retained as compatibility evidence that FIX-003 did not regress the already-accepted FIX-002 background Wake/Review execution semantics.

## 6. Scope

Implementation/test diff before this evidence file contains exactly:

- `src/aios_core/runtime/__init__.py`
- `src/aios_core/runtime/background_attempt.py`
- `src/aios_core/runtime/turn_execution.py`
- `src/aios_core/runtime/turn_runtime.py`
- `tests/runtime/test_turn_execution_recovery.py`

No task board, checkpoint, historical Resident evidence, fixture, World artifact, operator, or UI files were modified.

## 7. Main drift observed during construction

After the code candidate was green, live main advanced to `09e5b57d665e434679272481ee61b0b6cfbb3dce`.

The drift from construction main consisted of CORE-CI-FIX-001 corrective acceptance/integration and governance/workflow writeback only; no competing `src/**` change was present. Therefore the FIX-001/FIX-003 serialized-integration rebase condition was not triggered by this drift.

If FIX-001 is integrated before FIX-003 independent acceptance/integration, the active ruling still requires FIX-003 to be rebased/merged onto that newer main, all targeted/full gates rerun, and independent acceptance repeated on the rebased exact head.

## 8. Handoff

Author status: REVIEW_READY

This author window does not merge PR #157 and does not write task-board/checkpoint DONE state.
A different Independent Reviewer must perform CORE-GAP-FIX-003 acceptance.
