# CORE-BACKGROUND-RESPONSE-RECOVERY-001 INDEPENDENT ACCEPTANCE

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Role:
Independent Core Runtime / Exact-Response Recovery Acceptance Reviewer

Candidate:
- Engineering PR #219 — `CORE-BACKGROUND-RESPONSE-RECOVERY-001: exact-response recovery candidate (REVIEW_READY)`
- construction/live base at engineering start:
  `a310bf1202bf41644c2f3e25798053a6636e14be`
- tested exact implementation candidate:
  `3f9ec00d0fa283bc5294574d6da1e84d654d6645`
- PR evidence-only head at PM handoff:
  `b82ae25bcbef0d1d81cc3b7e5f303d75a4f0b507`

The tested exact implementation is one commit directly above the base. The two commits after it are evidence/governance only. Independent acceptance MUST evaluate the exact implementation candidate above, not silently inherit the PR head as the tested implementation.

Your only task is to independently try to make the exact candidate red and decide whether exact externally preserved provider-response recovery is safe, exact, fail-closed, and exactly-once.

You are not:
- PR #219 author
- CORE-BACKGROUND-RESPONSE-RECOVERY-001 engineer
- corrective engineer
- PM integration engineer
- Resident
- Semantic Evaluator
- RC re-freeze engineer

This window:
- acceptance only
- no candidate repair
- no merge
- no `CORE-RC-REFREEZE-002`
- no B persistence corrective work
- no Resident
- no fixture/historical-evidence mutation

## 1. Required start

1. Fetch current live `main`.
2. Read:
   - `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
   - `AIOS_v3.0_CURRENT_CHECKPOINT.md`
   - `PROJECT_MASTER_MAP.md`
   - `governance/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_001_GATE_INTEGRITY_CORRECTION_2026-09-26.md`
   - `governance/C15_RCC_RES_B_RERUN_002_STATE_LOSS_ADJUDICATION_2026-09-26.md`
   - `governance/prompts/CORE_BACKGROUND_RESPONSE_RECOVERY_001_2026-09-26.md`
   - PR #219 body/diff/current refs
   - `reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CANDIDATE_REPORT_2026-09-26.md`
   - all `reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001/red/` evidence
3. Confirm:
   `CORE-BACKGROUND-RESPONSE-RECOVERY-001-INDEPENDENT-ACCEPTANCE = READY`.
4. Pin:
   - exact candidate `3f9ec00d0fa283bc5294574d6da1e84d654d6645`
   - evidence-only head `b82ae25bcbef0d1d81cc3b7e5f303d75a4f0b507`
5. Verify `3f9ec00d... -> b82ae25b...` changes no `src/**` and no `tests/**`; only evidence/governance files are allowed.
6. Verify exact candidate parent is exactly:
   `a310bf1202bf41644c2f3e25798053a6636e14be`.

If tested implementation SHA changes, do not inherit this acceptance task.

## 2. Exact candidate scope

Expected exact implementation delta from base to `3f9ec00d...` is exactly these six files:

1. `src/aios_core/runtime/background_attempt.py`
2. `src/aios_core/runtime/cognitive_runtime.py`
3. `src/aios_core/runtime/metering.py`
4. `src/aios_core/runtime/turn_execution.py`
5. `src/aios_core/runtime/turn_runtime.py`
6. `tests/integration/test_core_background_response_recovery_001.py`

Expected one-commit stats from PM precheck:
- +2191 / -43
- exact tree:
  `4e9e3a5685373f46ba56d51259f39af710a3cf53`

Fail scope review if candidate changes sealed fixture, historical Resident evidence, PR #216 frozen WIP, operator persistence, or introduces another World/cognition authority.

## 3. Core semantic contract

The accepted mechanism must satisfy all of the following simultaneously:

- exact externally durable response resumes the SAME background attempt and SAME model round;
- provider call count on exact-response recovery is zero;
- no semantic reconstruction, fallback, approximation, or defaulted directive;
- exact provider/model/request_id, response fingerprint, and payload bytes are verified;
- missing, corrupted, mismatched, or identity-conflicting response remains fail-closed;
- downstream response/silence/capability handling goes through the normal CognitiveRuntime path;
- capability side effects, assistant output, attempt state, and metering converge exactly once;
- `not_submitted` retry semantics remain unchanged;
- ambiguous dispatch with no exact response remains `in_doubt`;
- ordinary uninterrupted provider behavior remains compatible;
- no new semantic truth store;
- no operator-owned semantic execution engine.

## 4. Exact-response representation

Critically inspect `encode_model_directive` / `decode_model_directive`.

Verify:
- strict complete field set;
- unknown fields rejected;
- missing fields rejected;
- no defaults used to invent semantic content;
- capability call name/arguments/call_id preserved exactly;
- response vs silence invariants preserved;
- usage/provenance identity conflicts rejected;
- integer/bool edge cases do not bypass validation;
- serialized bytes are deterministic enough for payload hash verification;
- decode -> ModelDirective -> fingerprint reproduces the staged fingerprint.

Add malformed/adversarial payloads beyond author tests.

## 5. Durable staging authority

Inspect `background_model_responses`.

Decide whether it is only execution/recovery provenance in the existing canonical runtime SQLite DB, rather than a second World/cognition truth store.

Verify:
- one row per exact attempt;
- staging does not advance World revision;
- staging cannot fabricate a response for `admitted` or `not_submitted` attempts that provably never crossed provider dispatch;
- repeated identical staging is idempotent;
- conflicting restaging fails closed;
- existing `response_returned` / `metered` provenance cannot be silently rewritten;
- DB tampering of directive payload/hash/identity is detected before application.

## 6. Attempt/round ordering

Freshly test multi-round work.

Requirements:
- recovery consumes only the exact stopped round;
- earlier rounds must already be durably metered before a later staged round can resume;
- recovery cannot skip a round;
- recovery cannot apply two staged rounds out of order;
- recovery cannot reuse a response from another work_id/work_kind/subject;
- attempt identity remains stable across restart.

## 7. Normal CognitiveRuntime path

Inspect the recovered-response hook placement.

Verify the recovered directive:
- bypasses only provider admission/dispatch/provider invocation/response recording for the already-returned round;
- still executes normal metering and downstream capability/terminal handling;
- does not create a parallel application loop;
- does not silently bypass model-round budgets or termination semantics;
- subsequent model rounds, when legitimately needed after a capability result, use the ordinary provider path with a NEW correct round attempt, not the recovered reply again.

## 8. Exactly-once capability application

This is a mandatory blocker area.

Fresh fault injection must cover at least:

1. crash after exact response staging before application;
2. crash while the first capability is applying;
3. crash after a capability result is durable but before the next model round;
4. restart and repeated recovery invocation;
5. two capabilities in one recovered directive;
6. capability that writes a revisioned World object;
7. capability failure path.

Prove:
- no duplicate capability side effect;
- no skipped capability;
- no fabricated success;
- no duplicate World revision caused by recovery;
- normal idempotency identity is reused rather than regenerated incorrectly.

Pay special attention to recovered write-time pinning. The same semantic operation must not receive a new identity merely because restart happened later.

## 9. Terminal response / silence exactly once

Freshly fault-inject:
- crash after terminal response is logically available but before durable assistant-output/completion marker;
- crash after silence but before completion marker;
- repeated recovery after durable assistant output exists.

Verify:
- assistant output is not duplicated;
- silence is not converted into output or vice versa;
- completion reconciliation does not call provider again;
- user-turn recovery preserves existing TurnExecution identity and conflict checks.

## 10. Metering exactly once

Verify all work kinds:
- wake
- periodic_review
- user_turn

Requirements:
- recovered response produces exactly one economic meter row;
- meter row is bound to the exact attempt/round;
- repeated recovery creates no second meter row;
- existing normal-path metering idempotency remains intact;
- `metered` attempt cannot be made replayable merely by staging new bytes.

Probe crash boundaries around response application and metering commit.

## 11. not_submitted and ambiguous in_doubt non-regression

Freshly verify:

A. definitely-not-submitted:
- same attempt identity can still safely retry through existing path;
- exact-response staging is rejected for that attempt.

B. ambiguous dispatch, no exact bytes:
- remains `in_doubt`;
- ordinary retry refused;
- no new ID escape;
- no automatic reconciliation.

C. exact bytes later supplied:
- only then may exact-response recovery proceed;
- provider call count remains zero.

## 12. Wake / Periodic Review / User Turn parity

The exact candidate extends recovery across all three.

Independently probe each kind.

For each:
- initial ambiguous provider state;
- exact staging;
- process reopen;
- zero provider call on recovered round;
- correct terminal/capability result;
- exactly one meter;
- repeated invocation fail/no-op according to existing durable state.

Do not accept wake-only correctness as sufficient.

## 13. External recovery surface

The engineering prompt requires an externally durably preserved response to re-enter Core safely.

Inspect the public recovery entry point:
`stage_exact_background_response(...)`.

Verify:
- it can be called by legitimate runtime/operator integration without importing test-only code;
- it requires explicit work kind, work id and round;
- it cannot infer semantic content;
- it cannot stage against the wrong attempt;
- lack of a dedicated headless CLI does not create an impossible production handoff path.

If the only practical production integration would require bypassing public Core contracts or direct SQLite mutation, this is a blocker.

## 14. Existing schema / startup compatibility

The candidate creates an additive runtime table.

Freshly verify:
- existing World DB opens and table creation is idempotent;
- no World schema/version semantic change is falsely advertised;
- no World revision advances merely by initialization;
- backup/restore retains the table because it is in the same SQLite DB;
- index rebuild does not depend on or corrupt staged response state;
- future-schema fail-closed behavior from accepted Recovery remains unchanged.

## 15. Live writer / restart behavior

Fresh process-level probes are required where practical.

At minimum:
- stage exact reply in process A;
- terminate process A;
- reopen the same World in process B;
- recover without provider call;
- verify durable attempt/staging/meter/output state.

Do not rely only on same-process exception simulation.

## 16. Candidate red evidence

Preserve and inspect all six author red mutations:

- red A — recovery hook disabled
- red B — recovered write time unpinned
- red C — fingerprint verification disabled
- red D — identity verification disabled
- red E — staging-state guard disabled
- red F — payload-hash guard disabled

Confirm each was a temporary mutation and final exact candidate reverted the mutation.

Do not turn these historical red logs into green claims.

## 17. Remote CI reality

Important: GitHub Actions were triggered on the PR evidence-only head / PR merge context, not directly on exact commit `3f9ec00d...`.

PM precheck of PR #219 head observed these SUCCESS workflows:
- p16-convergence-gate run `36234237647`
- cognitive-runtime `36234237754`
- fused-turn-runtime `36234237736`
- c09-wake-dispatch `36234237657`
- p15-periodic-review `36234237677`
- p9 `36234237770`
- p10 `36234237664`
- p11 `36234237756`
- p12 `36234237667`
- p14 `36234237671`
- constitutional-cognition-closure `36234237686`
- c15-cognition-evidence-policy `36234237693`
- core-scale `36234237734`
- C14 runtime `36234237740`
- C14 loop `36234237690`

Two workflows are red:
- c14-semantic-repair-fixture run `36234237680`
- c15-rcc-fixture run `36234237724`

PM inspected both logs. Their actual failing steps are the fixture-task invariants:
- `C14-SEM-REPAIR-FIX-001 must not modify src/aios_core/**`
- `C15-RCC-FIXTURE-001 must not modify src/aios_core/**`

Their substantive fixture/mechanical/regression steps before those scope guards passed. These two workflows are not proof that this Core candidate is semantically wrong; they are workflows specialized to fixture-only tasks and reject any genuine Core diff.

Independent reviewer MUST:
- record these two reds explicitly;
- not relabel them SUCCESS;
- determine whether they are non-applicable scope guards for this Core task;
- independently verify the Core/test tree on PR head is identical to exact candidate for `src/**` and `tests/**`.

## 18. Local author evidence vs fresh independent evidence

Author report claims:
- full suite `717 passed`;
- randomized full suite `717 passed`;
- focused subset `93 passed`.

These are author evidence only.

Independent acceptance must run fresh tests against exact candidate or an exact-tree checkout and must not accept solely from the committed log files.

At minimum:
- run the dedicated fault matrix fresh;
- run relevant runtime/background-attempt/turn-execution/metering suites;
- run full repository suite if environment permits;
- record environment versions.

If environment cannot reproduce a required gate, report the limitation rather than inheriting author PASS.

## 19. Required fresh adversarial probes

At minimum add reviewer-authored probes for:

### Probe A — cross-work response transplant
Try to stage exact bytes from attempt A against attempt B with plausible provider identity. Must fail.

### Probe B — multi-round ordering
Stage/recover a later round while an earlier round is not durably metered. Must fail closed.

### Probe C — process kill after staging
Persist exact bytes, SIGKILL before application, reopen, recover with provider-call counter fixed at zero.

### Probe D — capability crash and repeat
Kill/fail after capability durable side effect but before loop continuation; repeated recovery must not duplicate side effect.

### Probe E — tampered staged DB row
Modify payload/hash or identity fields after staging. Application must fail before semantic effect.

### Probe F — user-turn terminal output crash
Crash between recovered terminal response and completion marker; reopen and prove single assistant output / single meter / no provider redispatch.

Strongly recommended:
- two capability calls with different dimensions/identities;
- periodic-review equivalent;
- malformed integer/bool/extra-field payloads;
- metered-attempt restaging conflict.

## 20. Live-main drift

Review-time main may advance.

Classify drift:
- governance/review-only: no automatic rebase required;
- any relevant `src/aios_core/runtime/**`, storage schema, recovery, metering, turn execution, or test-contract change requires explicit revalidation and may yield `REBASE_REVALIDATION_REQUIRED`.

Do not merge or rebase the candidate in this window.

## 21. Verdict

### ACCEPTANCE_PASS
Only if:
- exact candidate identity/scope is pinned;
- exact-response bytes and identity are strictly verified;
- no provider redispatch occurs for recovered round;
- ambiguous no-response remains fail-closed;
- not_submitted semantics remain unchanged;
- wake/review/user-turn all recover correctly;
- capability/output/metering converge exactly once across restart;
- multi-round ordering is correct;
- external staging surface is production-usable without semantic bypass;
- schema/recovery/writer behavior remains compatible;
- fresh adversarial probes pass;
- relevant regressions pass;
- blocker count = 0.

### ACCEPTANCE_FAIL
Any real correctness, identity, exactly-once, or production-recovery blocker.

### REBASE_REVALIDATION_REQUIRED
Only if relevant live-main semantic drift invalidates the pinned exact candidate.

## 22. Report

Create:
`reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001_INDEPENDENT_ACCEPTANCE_2026-09-26.md`

Create one review-only PR from review-time live main.

Report:
1. review-time main
2. engineering PR #219
3. tested exact candidate
4. evidence-only head
5. exact scope/tree
6. evidence-only delta verification
7. exact-response representation verdict
8. staging authority verdict
9. round-ordering verdict
10. CognitiveRuntime-path verdict
11. capability exactly-once verdict
12. output/silence exactly-once verdict
13. metering verdict
14. not_submitted/in_doubt non-regression
15. Wake/Review/UserTurn parity
16. external recovery surface
17. schema/recovery compatibility
18. process-level restart probes
19. author red-evidence review
20. fresh adversarial probes
21. remote CI + two fixture-scope red classifications
22. live-main drift
23. blocker count
24. final verdict

Do not merge PR #219.
Do not repair PR #219.
Do not enter `CORE-RC-REFREEZE-002`.

If PASS, state exactly:

`PR #219 CORE-BACKGROUND-RESPONSE-RECOVERY-001 tested exact candidate 3f9ec00d0fa283bc5294574d6da1e84d654d6645 with evidence-only head b82ae25bcbef0d1d81cc3b7e5f303d75a4f0b507 is independently accepted for PM integration.`
