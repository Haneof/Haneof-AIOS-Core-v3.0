# CORE-GAP-FIX-002 Independent Acceptance — 2026-09-24

Task: `CORE-GAP-FIX-002-INDEPENDENT-ACCEPTANCE`  
Role: Independent Core Runtime / Recovery Acceptance Reviewer  
Candidate: PR #143 — `CORE-GAP-FIX-002: durable background model-attempt recovery`

Final verdict: **ACCEPTANCE_PASS**

## 1. Frozen review identity

- Review-time live `main`: `ce1c90844d5a0da99af4d420096740a0280ae6f7`
- Candidate PR: #143
- Candidate branch: `core-gap-fix-002-20260924`
- Exact candidate head reviewed: `c5382a1653b66654df23d0938d9d19a80a12619c`
- PR construction/current recorded base: `fda1e28231dc6a33ead180003b407aaa5305665a`
- Original construction main recorded by the author: `5ccb51c0bbcc11380887c60e8bfaa5c87f05c110`
- Before-fix reproduction head: `305b70c0d7a90a115989aab71a83f6c11b9d7e55`
- Before-fix Actions merge ref observed in raw log: `3595fa3`
- Candidate Actions merge ref: `caf888b427eee74d3dec973fb6fe2dd86959566c`
- Review-only branch: `review/core-gap-fix-002-independent-acceptance-20260924-sol`

At the final drift check, PR #143 remained OPEN, UNMERGED, Ready for review, with exact head `c5382a1653b66654df23d0938d9d19a80a12619c`. GitHub REST reported `mergeable=true`, `mergeable_state=clean`, and `rebaseable=true`.

## 2. Governance gate admission

The review-time task board and checkpoint still state:

- `CORE-GAP-FIX-002 = GATE / REVIEW_READY`
- PR #143 is the unique FIX-002 candidate at the exact head above.
- `CORE-GAP-FIX-001 = FROZEN_WIP / BLOCKED_ON_FIX_002_INTEGRATION`.
- `CORE-GAP-FIX-003 = BLOCKED`.
- S2 is serialized: FIX-002 acceptance/integration precedes resumption of FIX-001; FIX-003 may not start yet.

Therefore the independent acceptance gate was valid to execute.

## 3. Candidate scope and exact diff

PR #143 has exactly 12 changed files.

Core:

1. `src/aios_core/review/periodic.py`
2. `src/aios_core/runtime/__init__.py`
3. `src/aios_core/runtime/background_attempt.py`
4. `src/aios_core/runtime/cognitive_runtime.py`
5. `src/aios_core/runtime/metering.py`
6. `src/aios_core/runtime/turn_runtime.py`
7. `src/aios_core/wake/service.py`

Tests:

8. `tests/integration/test_core_gap_fix_002_background_attempts.py`
9. `tests/integration/test_v3_background_budget_gate.py`
10. `tests/integration/test_v3_periodic_review.py`
11. `tests/runtime/test_background_model_attempt.py`
12. `tests/runtime/test_metering_ledger.py`

No governance, reviews, operator/preflight, fixture, Resident evidence, private World, or UI file is present in the candidate diff.

The PR has two commits:

- `f7b455a6900fabd3492f8b3e29e03c1b98a3c776` — durable background model-attempt recovery
- `c5382a1653b66654df23d0938d9d19a80a12619c` — keep model attempt id out of the Resident snapshot wire shape

No candidate comments or prior review submissions were present at review time.

## 4. Before-fix reproduction — CG-002 independently confirmed

### 4.1 Reproduction purity

Comparing construction base `5ccb51c0bbcc11380887c60e8bfaa5c87f05c110` to reproduction head `305b70c0d7a90a115989aab71a83f6c11b9d7e55` shows only:

- added `tests/integration/test_core_gap_fix_002_background_attempts.py`
- 146 additions
- **zero `src/**` changes**

This proves the reproduction head did not contain the repair.

### 4.2 Raw Actions evidence

Workflow: `p16-convergence-gate`  
Run: `35961829535`  
Job: `107511854481`  
Command: `pytest -q`  
Checkout raw log: `HEAD is now at 3595fa3 Merge 305b70c0... into 5ccb51c0...`

Wake failure:

- first provider invocation records `("first", 0)`
- the provider raises `TimeoutError("provider may already have accepted the request")`
- restart invokes the provider again and records `("restart", 0)`
- actual calls: `[("first", 0), ("restart", 0)]`
- required calls: `[("first", 0)]`

Periodic Review reproduced the same defect:

- ambiguous first invocation
- restart reinvokes the provider
- actual calls: `[("first", 0), ("restart", 0)]`
- required calls: `[("first", 0)]`

Both regressions failed for the audited CG-002 reason, not because of a fixture, operator, or test-design failure.

**Before-fix verdict: CG-002 REPRODUCED.**

## 5. Durable model-attempt state machine review

The exact candidate introduces a non-World, same-database `background_model_attempts` state machine with states:

`admitted -> dispatching -> not_submitted / in_doubt -> response_returned -> metered`

### 5.1 Stable attempt identity — PASS

Identity is deterministically derived from:

`subject_id + work_kind + work_id + model_round_index`

using canonical JSON plus SHA-256. The schema also enforces:

`UNIQUE(subject_id, work_kind, work_id, model_round_index)`

Consequences independently verified from source:

- the same Wake/Review round reuses the same attempt identity;
- Wake and Periodic Review are distinguished by `work_kind`;
- different model rounds have different identities;
- restart cannot escape an IN_DOUBT row by silently selecting a new ID.

### 5.2 admitted boundary — PASS

`BackgroundModelAttemptStore.admit()` durably inserts/loads an `admitted` row inside `BEGIN IMMEDIATE` before the provider boundary.

If a pre-dispatch failure occurs, the row remains `admitted`, which is the only safe pre-submission retry state besides explicit `not_submitted`.

### 5.3 dispatching boundary — PASS

`CognitiveRuntime.run_turn()` performs, in order:

1. model-attempt admission;
2. durable dispatch recording;
3. provider/model handler invocation.

`mark_dispatching()` transitions `admitted -> dispatching` before the handler is called.

A restart that encounters durable `dispatching` with no durable response promotes it to `in_doubt` and raises `BackgroundModelExecutionInDoubt` before provider reinvocation.

### 5.4 definitely-not-submitted semantics — PASS

Only the typed `ModelDispatchNotSubmitted` exception is passed to the failure recorder with `definitely_not_submitted=True`.

All other exceptions, including ordinary timeout/transport/unknown exceptions, use `definitely_not_submitted=False` and therefore transition to `in_doubt`.

No generic timeout/socket/exception path was found that is automatically classified as `not_submitted`.

### 5.5 IN_DOUBT recovery — PASS

For an existing `in_doubt` row, `admit()` raises `BackgroundModelExecutionInDoubt` before dispatch recording or provider execution.

There is no:

- attempt-ID swap;
- attempt table clear;
- Wake reset-to-queued bypass;
- runtime-session bypass;
- budget-rollover erase.

The inspection/reconciliation surface is explicit:

- `get`
- `inspect`
- `list_for_work`
- `reconcile_not_submitted`
- `reconcile_response`

Reconciliation requires explicit evidence and preserves the same attempt identity.

## 6. response_returned boundary — PASS

On provider success:

1. the candidate records response identity/fingerprint by transitioning `dispatching -> response_returned`;
2. only then does metering run;
3. only after metering can later capability/completion work continue.

Therefore a crash after the provider returned but before metering cannot safely look like a fresh provider attempt.

On restart, `response_returned` raises `BackgroundModelResponsePending` before provider dispatch. No synthetic response/completion is invented.

## 7. Metering boundary and economic truth — PASS

`ModelMeteringLedger` remains the only token/usage/economic truth.

`background_model_attempts` contains execution/recovery provenance only; it does not contain a second token-usage accounting model.

The candidate adds nullable `background_attempt_id` to `metering_records`.

For background attempts, `record_model_call()`:

- requires the referenced attempt to exist;
- verifies subject/work/model-round identity;
- requires durable `response_returned` or already-`metered` state;
- writes/replays the meter row;
- transitions the attempt to `metered` with `meter_record_id`;
- performs the meter insert/replay and attempt close in the same SQLite transaction.

The unique partial index on `background_attempt_id` and the existing provider/request identity behavior preserve idempotency.

A meter-after-response crash cannot cause a second provider call. A post-meter/pre-completion restart sees `metered` and blocks provider reinvocation. The dedicated Wake regression also proves exactly one meter row.

## 8. Schema / upgrade review — PASS

The attempt table is created with `CREATE TABLE IF NOT EXISTS`; indexes use `CREATE INDEX IF NOT EXISTS`.

Metering upgrade behavior:

- reads `PRAGMA table_info(metering_records)`;
- conditionally executes `ALTER TABLE ... ADD COLUMN background_attempt_id TEXT`;
- creates the unique partial attempt index idempotently;
- leaves existing rows compatible through a nullable column.

Tests explicitly construct an old meter table, initialize the new ledger, verify the additive column/index, and verify World revision does not advance.

Attempt and meter writes are non-World tables in the same SQLite database. They do not create WorldObjects or advance `world_revision`.

### Legacy RUNNING work

For a pre-FIX-002 RUNNING Wake/Review without an attempt row and without the new protocol marker, the candidate adopts a durable `in_doubt` attempt and fails closed.

For new-code RUNNING work carrying `background_model_attempt_protocol=v1` but no attempt row, the absence of the row means the process crashed after durable work claim but before model-attempt admission; provider dispatch therefore did not start, so admission may safely proceed.

The dedicated legacy Periodic Review regression verifies the pre-upgrade fail-closed path with provider call count zero.

## 9. Legacy runtime-incomplete / next model round — PASS

New runtime-incomplete metadata persists:

`runtime_incomplete_next_model_round_index = prior_offset + model_rounds_returned`

The next execution passes this value as `model_round_offset`, so the new model call uses a new attempt identity rather than replaying the prior round.

For legacy runtime-incomplete work that lacks the new explicit next-round field, the runtime requires durable metering rows for the exact Wake before choosing an offset. If no meter rows exist, it fails closed.

This is consistent with the pre-FIX-002 ordering: runtime-incomplete metadata is persisted only after the model returned, and C13 metering is recorded before the runtime result returns to Wake/Review continuation logic.

Thus `runtime_incomplete=true` alone is not treated as proof that the prior provider round completed.

## 10. Wake / Periodic Review symmetry — PASS

Dedicated exact-candidate regressions cover:

Wake:

- ambiguous possible-submit -> `in_doubt`;
- restart blocks provider;
- pre-dispatch admitted retry;
- explicit definitely-not-submitted same-ID retry;
- response-before-meter;
- meter-before-completion;
- normal success -> `metered`.

Periodic Review:

- ambiguous possible-submit -> `in_doubt`;
- restart blocks provider;
- response-before-meter;
- meter-before-completion;
- normal success -> `metered`;
- legacy RUNNING without attempt -> fail-closed `in_doubt`;
- runtime-incomplete continuation advances to the next model round.

No asymmetric Review path was found that can bypass the background attempt store.

## 11. BackgroundBudgetGate — PASS

The exact-candidate budget regression proves:

- IN_DOUBT Wake remains RUNNING under same-window reservation/defer behavior;
- provider call count remains one;
- after next-window rollover, the durable attempt is still IN_DOUBT and provider reinvocation is blocked.

The attempt rows are not cleared or rewritten by budget rollover. Existing budget workflows and affected suites remain green.

## 12. Exactly-once Wake user delivery — PASS

The existing persisted-delivery recovery path remains logically separate from provider-attempt state.

If a user-facing assistant delivery already exists durably after a process crash, restart completes the RUNNING Wake from that delivery record before any model invocation.

The candidate does not:

- fabricate a USER Observation;
- use attempt state as delivery state;
- duplicate assistant delivery;
- clear attempt state to force completion.

C09/fused/C15-related exact-tree regressions remain green.

## 13. FIX-001 and FIX-003 boundary review — PASS

### FIX-001

PR #143 does not modify these temporal-read symbols in its patch:

- `_search_world`
- `_inspect_world_object`
- `_world_map_context`

No `AS_KNOWN`, temporal cutoff, or historical read-cut implementation appears in the candidate patch.

CG-001 remains outside this candidate.

### FIX-003

The FusedTurnRuntime ordinary user `run_turn()` path is not modified by PR #143. The candidate does not add a user-turn execution reconciliation state machine, turn-ID swap, user-response reconciliation, or user-delivery repair.

The generic CognitiveRuntime receives reusable background hooks, but those hooks return no background attempt scope outside active Wake/Review execution. This is shared infrastructure, not an implementation of CG-003.

CG-003 remains blocked.

## 14. Before/after regression evidence — PASS

### Before

Reproduction-only head `305b70c0...` on construction base `5ccb51c0...`:

- only the new regression test file differs from base;
- Wake and Periodic Review tests fail with `first -> restart` duplicate provider execution.

### After

Candidate exact head: `c5382a1653b66654df23d0938d9d19a80a12619c`.

The full candidate pull-request Actions merge ref is `caf888b427eee74d3dec973fb6fe2dd86959566c`.

A direct compare from candidate head to that merge ref reports:

- one merge commit ahead;
- **zero changed files**.

Therefore the tested merge-ref tree is identical to the exact candidate tree; the base introduced no content difference into the tested tree.

The exact-tree full suite contains the new FIX-002 regression file and is green.

## 15. Crash-window acceptance — PASS

Verified by exact candidate source plus exact-tree regression coverage:

1. pre-dispatch failure -> durable `admitted`, safe same-ID retry;
2. explicit definitely-not-submitted -> `not_submitted`, safe same-ID retry;
3. possible submit / before response -> `in_doubt`;
4. IN_DOUBT restart -> no provider reinvocation;
5. response returned / before meter -> `response_returned`, no provider reinvocation;
6. meter / before Wake completion -> `metered`, no provider reinvocation or duplicate charge;
7. Periodic Review corresponding response/meter crash windows;
8. exact attempt identity persists across restart;
9. budget same-window behavior / rollover preserves IN_DOUBT;
10. normal Wake and Review success remains green;
11. runtime-incomplete continuation advances model-round identity.

## 16. Independent adversarial probes — PASS

The review environment could read all GitHub source/Actions evidence through the repository connector, but direct local `git clone` could not resolve `github.com`. No local clone/test pass is claimed.

To avoid inventing evidence, the independent probes below were executed as a source-level SQLite/state-transition replay using the exact candidate identity formula and transition predicates. This is supplemental to the authoritative exact-tree GitHub Actions run, not a substitute falsely labeled as repository pytest.

### Probe A — IN_DOUBT restart twice

Starting from one provider call and a durable `in_doubt` row:

- restart #1 observes the same attempt ID and remains `in_doubt`;
- restart #2 observes the same attempt ID and remains `in_doubt`;
- provider call count remains 1.

Observed replay result:

`states=[(1, in_doubt, same_id), (2, in_doubt, same_id)], provider_calls=1`

### Probe C — response_returned restart twice

Starting from one returned provider response durably marked `response_returned`:

- restart #1 remains `response_returned` and blocks provider;
- restart #2 remains `response_returned` and blocks provider;
- provider call count remains 1.

Observed replay result:

`states=[(1, response_returned, same_id), (2, response_returned, same_id)], provider_calls=1`

### Probe D — attempt identity collision

Using the exact candidate identity formula:

- same subject/work-kind/work-id/round -> identical attempt ID;
- same durable work, round 0 vs round 1 -> different attempt IDs;
- same work ID, Wake vs Periodic Review -> different attempt IDs.

Observed:

- same-round equality: true
- round distinction: true
- work-kind distinction: true

No adversarial blocker was found.

## 17. Exact-head CI verification — PASS

The candidate head has the following pull-request workflow runs, all SUCCESS:

- fused-turn-runtime: `35962673697`
- cognitive-runtime: `35962673718`
- c09-wake-dispatch: `35962673728`
- p15-periodic-review: `35962673731`
- c14-cognitive-derivation-runtime: `35962673752`
- c14-cognitive-derivation-loop: `35962673736`
- constitutional-cognition-closure: `35962673707`
- c15-cognition-evidence-policy: `35962673760`
- p9-revision-gate: `35962673720`
- p10-ai-world-gate: `35962673761`
- p11-dimension-gate: `35962673717`
- p12-execution-gate: `35962673732`
- p14-long-context: `35962673682`
- p16-convergence-gate: `35962673802`

### Full gate

Run: `35962673802`  
Job: `107514408639`

Raw log confirms:

- checkout: `caf888b Merge c5382a1653... into fda1e282...`
- tested tree is identical to exact candidate head;
- CPython `3.12.14`;
- pytest `8.4.2`;
- pydantic `2.13.5`;
- command: `pytest -q`;
- shell is normal `bash -e`;
- no `continue-on-error`, `|| true`, or equivalent failure swallowing in the full gate workflow;
- independently counted progress output: **643 pass dots**;
- skips: **0**;
- failures: **0**;
- errors: **0**;
- xfails/xpasses: **0**;
- job conclusion: SUCCESS.

Targeted sampling also confirmed the same candidate merge ref in C09 and P15, with normal direct pytest commands and 100% green output.

## 18. Review-time main compatibility — PASS

The final review-time main advanced from the candidate's recorded base `fda1e282...` to:

`ce1c90844d5a0da99af4d420096740a0280ae6f7`

The compare is 15 commits ahead / 0 behind, but the only changed paths are governance/review/CI-corrective state files:

- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `governance/prompts/CORE_CI_FIX_001_CORRECTIVE_001_2026-09-24.md`
- `reviews/CORE_CI_FIX_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

There are no `src/**` or candidate test changes between the candidate base and review-time main.

GitHub REST at final pin reports PR #143 cleanly mergeable. No current-main Core/Test drift invalidates the exact-head acceptance evidence.

## 19. Historical evidence / experiment impact — PASS

The candidate:

- changes Core runtime semantics;
- does not run a Resident;
- does not rewrite historical Resident evidence;
- does not hash-swap historical packages;
- does not modify fixture/operator evidence;
- explicitly preserves fresh A/B/C for the future RC Freeze process.

No historical experiment evidence is promoted to the new Core tree by this acceptance.

## 20. Findings

### Blockers

Blocker count: **0**.

### Non-blocking execution limitation

The reviewer execution container could not resolve `github.com` for a direct local clone. This report does not claim a local repository pytest pass.

This limitation is non-blocking for this acceptance because:

1. before-fix raw Actions logs independently reproduce CG-002 on a test-only reproduction head;
2. the candidate Actions merge-ref tree was independently verified to have zero file difference from the exact candidate head;
3. the exact-tree full regression is a direct `pytest -q` run with 643 passes and no skips/failures/error-swallowing;
4. state-machine/schema/scope review was performed from exact-head repository source;
5. independent adversarial source-level transition replays add coverage beyond the author's direct regression names.

## 21. Final verdict

# ACCEPTANCE_PASS

CG-002 is independently reproduced on the pre-fix Core and the exact PR #143 candidate establishes a durable background model-attempt identity/state machine that fails closed across ambiguous submission, response-returned, metered, restart, budget rollover, legacy RUNNING, and runtime-incomplete boundaries for both Wake and Periodic Review.

No Core blocker, scope violation, FIX-001 temporal read-cut implementation, FIX-003 user-turn reconciliation implementation, duplicate economic truth store, historical evidence rewrite, or regression failure was found.

**PR #143 exact candidate is independently accepted for PM integration.**

This review does not merge PR #143 and does not update the task board/checkpoint.
