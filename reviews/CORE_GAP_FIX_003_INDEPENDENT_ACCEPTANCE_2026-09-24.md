# CORE-GAP-FIX-003 Independent Acceptance — 2026-09-24

Status: **ACCEPTANCE_FAIL**  
Task: `CORE-GAP-FIX-003-INDEPENDENT-ACCEPTANCE`  
Role: Independent Core Runtime / User-Turn Recovery Acceptance Reviewer  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Candidate: PR #157 — `CORE-GAP-FIX-003: recover user-turn IN_DOUBT safely`

This review is review-only. It does not modify PR #157, Core code, tests, task board, checkpoint, fixtures, Resident evidence, or private World state, and it does not merge the candidate.

## 1. Pins and live state

- review-time main: `a424cb9dee37d5fb20d85f4ba03f2bb2f83863a7`
- candidate PR: #157
- reviewed exact head: `81d626820cfa31e4f3f1aba0e892eb48cb11e46c`
- PR state at final recheck: OPEN / UNMERGED / Ready for review / mergeable
- candidate base recorded by GitHub: `f8eb271453b12c3896cd55381b8bdb8dc5da5632`
- FIX-001 PR #145 at final recheck: OPEN / UNMERGED, exact head `b5a50435b3f9048bf94d88e9625b9e5bc2b83f42`
- therefore the post-FIX002 serialized-integration rule has **not** triggered a mandatory rebase during this review.

Required governance state was independently re-read from live main. `CORE-GAP-FIX-003 = GATE / REVIEW_READY` and FIX-002 is already independently accepted/integrated.

## 2. Exact candidate scope

GitHub reports exactly six changed files:

1. `reviews/CORE_GAP_FIX_003_COMPLETION_EVIDENCE_2026-09-24.md`
2. `src/aios_core/runtime/__init__.py`
3. `src/aios_core/runtime/background_attempt.py`
4. `src/aios_core/runtime/turn_execution.py`
5. `src/aios_core/runtime/turn_runtime.py`
6. `tests/runtime/test_turn_execution_recovery.py`

No task board, checkpoint, governance ruling, operator, fixture, historical Resident evidence, private World artifact, UI, or hardware file is changed.

The source diff contains no added/removed `_search_world`, `_inspect_world_object`, `_world_map_context`, `AS_KNOWN`, `knowledge_cutoff`, `run_wake`, or `run_periodic_review` ownership changes. No FIX-001 scope takeover was found.

## 3. Before-fix reproduction

Reproduction-only SHA:

`56529c399f9b455d9d08ed20ae1c559aaf664e18`

Independent GitHub Actions verification:

- workflow: `p16-convergence-gate`
- run: `35966719207`
- job: `107526845648`
- result: **FAILURE**
- Python: 3.12.14
- pytest: 8.4.2
- pydantic: 2.13.5
- command: `pytest -q`

The failure log independently shows the actual pre-fix CG-003 surface:
- `FusedTurnRuntime.inspect_turn_execution` absent;
- `reconcile_turn_model_not_submitted` absent;
- no supported explicit recovery/authorization path;
- durable-output recovery surface absent;
- legacy FIX-002 `background_model_attempts` CHECK rejects `work_kind='user_turn'`.

**Before-fix verdict: CG-003 REPRODUCED.**

## 4. Source and state-machine review

### 4.1 A09 user-turn identity/admission

`runtime_turn_executions` remains the user-turn at-most-once admission truth keyed by subject/session/turn index plus immutable input hash.

The candidate:
- keeps a stable execution identity derived from subject/session/turn;
- keeps input hash bound to `user_input + occurred_at`;
- refuses conflicting input with `TurnInputConflict`;
- does not clear state, rewrite historical input, swap turn identity, or use a new session as a recovery bypass;
- consumes a retry authorization atomically with a conditional update and increments `retry_count`.

A09 safety itself is preserved.

### 4.2 Shared provider-attempt truth

The candidate extends the accepted FIX-002 `background_model_attempts` ledger with:

`work_kind = user_turn`

No parallel `user_turn_model_attempts` truth store is introduced.

Accepted attempt states remain:
- `admitted`
- `dispatching`
- `not_submitted`
- `in_doubt`
- `response_returned`
- `metered`

### 4.3 Supported recovery paths that are correct

The reviewed implementation correctly establishes these paths:

- ordinary pre-model failure **after user-turn attempt admission** leaves the attempt `admitted`; inspection reports safe-to-retry but ordinary `run_turn()` remains blocked until explicit authorization;
- `ModelDispatchNotSubmitted` becomes `not_submitted`; it is not automatically retried;
- ambiguous post-dispatch exception becomes/remains `in_doubt`; restart and retry authorization stay fail-closed;
- provider response is durably recorded as `response_returned` before metering/tool/output work, so later failure cannot become a blind model retry;
- durable assistant output can be forward-reconciled to completed without a second assistant output or provider call;
- legacy `started` rows whose new attempt protocol is absent remain fail-closed / `in_doubt`;
- conflicting input remains fail-closed across recovery surfaces.

### 4.4 Acceptance blocker: non-atomic initial turn claim / attempt admission

**Blocker ID: `CORE-GAP-FIX-003-ACCEPT-BLOCKER-001`**

#### Reproduction

The exact candidate's `FusedTurnRuntime.run_turn()` performs these as two separately committed operations:

1. `turn_executions.claim(...)`
   - new row becomes `state='started'`
   - `attempt_protocol='model_attempt_v1'`
   - the `TurnExecutionStore` connection context commits when `claim()` returns
2. only afterward, `background_model_attempts.admit(... work_kind='user_turn', model_round_index=0 ...)` is called in a separate SQLite transaction.

Inject process termination **after step 1 commits and before step 2 admits the attempt**.

Durable restart state is then:

- user turn = `started`
- `attempt_protocol = model_attempt_v1`
- user-turn provider-attempt count = **0**
- no assistant output exists
- provider dispatch could not yet have occurred in this path.

The candidate's own disposition logic treats empty `attempt_states` as `in_doubt`, because safe-to-retry requires a non-empty list whose states are all `admitted/not_submitted`.

The supported recovery surfaces cannot resolve this state:
- `authorize_turn_retry(...)` rejects it because there are no attempt states;
- `reconcile_turn_model_not_submitted(...)` cannot reconcile a missing attempt row and reaches the no-attempt path;
- `recover_turn_completion(...)` cannot succeed because there is no durable assistant output;
- ordinary `run_turn()` remains A09 fail-closed.

An independent transaction-level fault injection reproducing the candidate's exact claim/disposition predicates produced:

`state=started, attempt_protocol=model_attempt_v1, attempt_count=0, disposition=in_doubt, authorize_allowed=false`.

#### Expected

A new-protocol crash before provider-attempt admission must remain at-most-once safe **and** have a supported forward recovery. The implementation must not permanently strand the original user-turn identity when the provider boundary has not been crossed.

#### Actual

The candidate creates a new permanent recovery dead-end in the claim-to-attempt-admission crash window.

#### Affected state/path

- `FusedTurnRuntime.run_turn` initial admission path
- `TurnExecutionStore.claim`
- `TurnExecutionStore._disposition`
- `TurnExecutionStore.authorize_retry`
- `reconcile_turn_model_not_submitted`

Durable state signature:

`started + model_attempt_v1 + zero user_turn attempts + no assistant output`

#### Merge impact

CG-003 is not completely closed. PR #157 must not be integrated in this exact state.

#### Minimal corrective scope

Keep the correction inside FIX-003 user-turn recovery ownership. The minimal correction must close only the claim-to-attempt-admission crash gap, for example by making the initial turn claim and initial provider-attempt admission one atomic durable boundary, or by introducing an equivalently safe explicit pre-attempt recovery state/proof. Legacy rows without the new protocol must continue to fail closed. No FIX-001 temporal-read or FIX-002 background-flow redesign is required.

This report does not implement the correction.

## 5. Retry authorization review

The candidate requires non-blank reconciliation evidence and only authorizes when:
- the exact input identity matches;
- the row uses the new attempt protocol;
- at least one attempt exists;
- every attempt state is `admitted` or `not_submitted`;
- no durable assistant output/completed state exists.

`in_doubt` and `response_returned` do not receive blind authorization.

The authorization is represented as a one-shot durable bit and consumed with:

`UPDATE ... SET retry_authorized=0, retry_count=retry_count+1 ... AND retry_authorized=1`

An independent crash/restart probe confirmed:
- authorization survives restart before claim;
- first retry claim consumes it exactly once;
- second restart cannot consume the same authorization again;
- one authorization grants at most one provider-execution slot.

This path passes.

## 6. Durable completion recovery

The candidate requires a durable assistant Observation for completion reconciliation and validates the original input identity.

An independent repeated-recovery probe confirmed:
- first completion recovery -> completed;
- second completion recovery -> completed;
- assistant output row count remains one;
- no model reinvocation is required;
- retry authorization is cleared.

This path passes.

## 7. Legacy started-row probe

A legal legacy `runtime_turn_executions.state='started'` row with no new attempt protocol and no user-turn attempt was reopened through the candidate schema.

Inspection remained:

`IN_DOUBT / fail closed`

It was not promoted to safe-to-retry and no synthetic `not_submitted` evidence was invented.

This path passes.

## 8. FIX-002 schema migration review

The SQLite CHECK expansion is implemented by a transactional rebuild of `background_model_attempts`.

Independent migration probes used existing Wake and Periodic Review rows with full identity/provenance fields and verified:

- Wake rows preserved;
- Periodic Review rows preserved;
- attempt IDs preserved;
- attempt states preserved;
- provider/model/request identity preserved;
- response fingerprint preserved;
- reconciliation/meter fields preserved;
- `idx_background_attempt_work` restored;
- `idx_background_attempt_state` restored;
- repeated initialization is idempotent;
- reopen preserves identical row values;
- `user_turn` becomes accepted by the CHECK;
- an existing metering row linked by the unchanged attempt ID remains linked;
- a synthetic interruption inside the rebuild transaction rolls back to the original table and row.

Schema migration verdict: **PASS**.

## 9. FIX-002 background compatibility

Source-diff review finds no redesign of `run_wake` or `run_periodic_review`.

For background scopes, the accepted FIX-002 provider-attempt and metering path remains active. The candidate's generic model-attempt hooks add the user-turn scope but preserve the background scope as first priority.

Exact-head CI also revalidated the major background surfaces:
- C09 Wake dispatch: SUCCESS
- P15 Periodic Review: SUCCESS
- C14 runtime/loop: SUCCESS
- full P16 regression: SUCCESS

FIX-002 compatibility verdict: **PASS**.

## 10. FIX-001 ownership boundary

No candidate source line was found changing the FIX-001-owned temporal read-cut helpers or the background entrypoint read-cut ordering.

FIX-001 scope verdict: **PASS / no scope violation found**.

## 11. Exact-head CI and full regression

All 13 requested workflow runs are completed SUCCESS with GitHub run metadata pinning:

`head_sha = 81d626820cfa31e4f3f1aba0e892eb48cb11e46c`

Runs:

- p16-convergence-gate — `35968718665`
- fused-turn-runtime — `35968718728`
- c09-wake-dispatch — `35968718796`
- p15-periodic-review — `35968719062`
- c14-cognitive-derivation-runtime — `35968718801`
- c14-cognitive-derivation-loop — `35968718798`
- constitutional-cognition-closure — `35968718911`
- p9-revision-gate — `35968718785`
- p10-ai-world-gate — `35968718671`
- p11-dimension-gate — `35968718757`
- p12-execution-gate — `35968718667`
- p14-long-context — `35968718674`
- c15-cognition-evidence-policy — `35968718711`

Workflow definitions were independently inspected: Python 3.12, direct pytest commands, no relevant `continue-on-error` bypass was found, and the substantive test steps are successful.

For P16:
- run: `35968718665`
- job: `107533138923`
- Python: 3.12.14
- pytest: 8.4.2
- pydantic: 2.13.5
- command: `pytest -q`
- independently counted progress: **652 passed / 0 failed / 0 skipped / 0 errors**

Important CI provenance detail: because these are `pull_request` workflows, checkout used GitHub's synthetic merge ref. P16 checked out:

`7145052... = Merge 81d626820cfa31e4f3f1aba0e892eb48cb11e46c into 09e5b57d665e434679272481ee61b0b6cfbb3dce`

This is consistent with GitHub's run metadata pinning the PR head to the reviewed exact head; it is not represented as a bare-head checkout.

Full regression verdict: **PASS**.

## 12. Current-main compatibility and serialization

Construction main:

`f8eb271453b12c3896cd55381b8bdb8dc5da5632`

Review-time main:

`a424cb9dee37d5fb20d85f4ba03f2bb2f83863a7`

Independent compare shows the drift is CI workflow/governance/review material only; no competing `src/**` Core change exists between construction main and review-time main.

The exact CI merge base `09e5b57d...` to review-time main adds only task-board/checkpoint/project-map writeback.

At final serialization recheck, FIX-001 PR #145 remains OPEN / UNMERGED. Therefore:

**serialization verdict: current #157 exact head does not require rebase solely from FIX-001 integration at this review time.**

This finding does not waive `CORE-GAP-FIX-003-ACCEPT-BLOCKER-001`.

## 13. Adversarial probes

Required probe set:
- Probe A — authorize crash/restart: **PASS**
- Probe B — completion recovery twice: **PASS**
- Probe C — legacy started row: **PASS**

Additional acceptance fault injection:
- claim committed / initial user-turn attempt not yet admitted / process death: **FAIL**
- this additional probe is the acceptance blocker described in §4.4.

The A/B/C transaction/state probes replayed the exact SQLite predicates and transitions from the reviewed exact head. The authoritative repository-wide implementation regression remains the exact-head GitHub Actions evidence in §11.

## 14. Final verdict

Blocker count: **1**

- `CORE-GAP-FIX-003-ACCEPT-BLOCKER-001` — non-atomic initial user-turn claim / attempt admission can strand a new-protocol user turn permanently before the attempt row exists.

### Final

**ACCEPTANCE_FAIL**

The candidate preserves A09 safety, correctly handles the major not-submitted / ambiguous-provider / response-returned / durable-output recovery paths, preserves FIX-002 background semantics, stays inside FIX-003 ownership, and passes exact-head CI. However, CG-003 requires both at-most-once safety and a supported recovery path. The claim-to-attempt-admission crash window leaves the exact original turn in a durable state that no supported recovery API can resolve.

PR #157 exact candidate is **not accepted for PM integration** in this reviewed state.
