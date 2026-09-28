# CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001 — INDEPENDENT ACCEPTANCE

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Task:

`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`

Role:

**Independent Core Runtime Recovery Acceptance Reviewer**

You are not:
- PR #264 author;
- Corrective engineer;
- PM integrator;
- persistence engineer;
- Resident A/B/C;
- RC release engineer.

Your only task is:

> Independently attempt to falsify the exact Corrective-001 candidate and decide whether it closes `IA-BLK-TRUSTED-RETURN-001` without weakening request conflict semantics, trusted-return authenticity, or exactly-once durable effects.

Do not repair the candidate.

Do not merge anything.

## 1. Fresh start — never trust this prompt's moving state

Fresh-fetch:
- live `main`;
- PR #264 metadata/head/diff;
- failed PR #258 exact history;
- review-only PR #261;
- current task board/checkpoint;
- the canonical corrective prompt;
- the PM REVIEW_READY writeback.

At dispatch, the expected candidate is:

- PR #264
- exact head:
  `a73e186d40688f5dc181b1128a62eff37a974409`
- parent:
  `71f6d106a697b0c61410d42114545f2645e12510`
- tree:
  `352f47ac4e3098b10b1b78e4757543477371548d`
- base main at author start:
  `5288822e751df185f3abab79f969609f31859617`

If PR #264 head moved, return:

`REVALIDATION_REQUIRED`

Do not inherit acceptance to another SHA.

## 2. Preserve historical RED evidence

The following remain historical failures and must not be rewritten:

- failed exact PR #258:
  `1ebf51c4cb905e2a2578a09b64007b50bca0d4ac`;
- review-only PR #261:
  `b9d692ddca055b13fb29e646186e929a08bf8955`;
- blocker:
  `IA-BLK-TRUSTED-RETURN-001`;
- author's frozen rev5 baseline RED and earlier reviewer REDs.

Do not modify #258 or #261.

## 3. Build your own acceptance suite first

Before executing candidate acceptance probes:

1. dynamically enumerate the actual runtime capability registry;
2. independently identify every reachable side-effecting capability;
3. construct a fresh adversarial replay matrix;
4. freeze the reviewer test/probe files;
5. record SHA-256;
6. record enumeration / `pytest --collect-only` or equivalent static probe list;
7. only then execute.

Do not simply invoke the author's rev7 suite and call that independent acceptance.

The reviewer suite must fail if the runtime registry contains a side-effecting capability the suite did not classify.

## 4. Baseline RED

Run the reviewer matrix, or a mechanically equivalent subset sufficient to prove the same contract, against failed exact:

`1ebf51c4cb905e2a2578a09b64007b50bca0d4ac`

At minimum independently reproduce:
- the five prior IA RED families:
  - propose_goal;
  - form_event;
  - propose_entity;
  - propose_dimension;
  - propose_cognitive_policy;
- at least one revision-advancing duplicate/rejection family;
- one trusted-return authenticity negative control.

Preserve raw baseline output.

The acceptance suite must not be designed only after seeing candidate greens.

## 5. Complete side-effect replay contract

Against the exact candidate, independently exercise **every reachable side-effecting capability**.

For an exact recovered replay after the first durable side effect but before outer completion:

- capability result must converge successfully;
- no provider redispatch for the recovered round;
- no second meter for the recovered round;
- no second operation;
- no second semantic/World side effect;
- no second object revision;
- original object/revision/operation identity must be preserved where defined;
- unrelated later World revisions must not break convergence.

Do not limit testing to create_task or the five historical failures.

Attack create / revise / transition / register / policy / relation / experience families.

## 6. Binding adjudication: rev5 -> rev6 expectation change

This is a first-class acceptance question.

The author froze rev5 before the corrective implementation. Rev5 required changed-field fail-closed behavior for:
- upsert_relation;
- update_cognitive_policy;
- rollback_cognitive_policy.

After implementation, rev6 reclassified those cases from `conflicts` to `identity_shifts` and permits a changed request to become a distinct new durable operation/revision.

Do **not** accept the author's rationale on faith.

Independently determine:

### A. Is rev5's old expectation actually part of the frozen recovery contract?

Trace:
- the service request models;
- operation identity/idempotency contract;
- `CapabilityCall.call_id` semantics;
- recovered provider directive identity;
- trusted handoff payload fingerprint;
- storage request fingerprint;
- user_turn / Wake / Periodic Review recovery paths.

### B. Can an actual recovery path ever present changed arguments while still claiming to be the same recovered logical call?

If yes:
- that changed recovery must fail closed;
- prove no new durable side effect is possible.

If no:
- prove mechanically why authenticated exact response recovery makes such a mutation impossible before capability invocation;
- prove a changed direct service request is a genuinely new operation, not a replay;
- prove call_id alone is not durable authorization.

### C. Same key vs same call_id vs same recovered attempt

Test them separately.

At minimum:
1. exact same durable idempotency key + changed request -> must fail closed;
2. corrupt/skewed operation/idempotency rows -> fail closed;
3. same recovered trusted attempt with modified directive args -> fail before capability application;
4. same `call_id` with changed args -> independently classify from the actual Core contract, not the author test description;
5. changed args that generate a new canonical request identity -> determine whether the domain contract legally permits a new revision.

### D. Governance integrity

Independently decide whether rev5 -> rev6 is:
- a legitimate correction of an over-specified harness expectation, with the binding recovery safety property unchanged;
or
- prohibited post-implementation weakening of the frozen expected outcome.

If it is the latter, return ACCEPTANCE_FAIL even if the candidate's current tests are green.

Your report must give an explicit verdict on this adjudication.

## 7. Trusted-return trust boundary

Verify the corrective did not widen authenticity authority.

Prove:
- only the trusted provider-return boundary can mint authenticity receipt/handoff;
- recovery callers cannot supply arbitrary directive bytes and obtain a trusted receipt;
- cross-work / cross-attempt / provider / model / request-id transplant fails;
- response fingerprint mismatch fails;
- payload digest corruption fails;
- originating-request binding corruption fails;
- terminal output/delivery receipt still short-circuits replay where applicable.

Mechanically compare critical trusted-return files against the intended carried-forward #258 implementation.

Do not infer byte identity from the PR description.

## 8. Storage replay adversarial matrix

Attack `replay_exact_operation()` / `commit_or_replay()` directly and through services.

Required:
- identical exact request returns original durable result with zero new write;
- changed request under existing idempotency key fails with conflict;
- missing committed object revision fails closed;
- corrupt committed payload fails closed;
- corrupt idempotency result fails closed;
- operation/idempotency row skew fails closed;
- reused operation identity under another key fails closed;
- lookup of unused key is read-only;
- request_fingerprint remains unchanged in semantics;
- expected_world_revision remains part of request identity.

## 9. Real process-loss acceptance

Create fresh real process-loss probes, not just unit-level replay.

At minimum cover:
- one Wake side-effect family other than create_task;
- one user_turn revision-advancing family;
- one Periodic Review family;
- actual child/process death or equivalent hard process termination after durable capability effect and before outer completion;
- reopen same World in a new Runtime/process;
- recover the exact authenticated directive;
- prove no provider redispatch for the recovered round;
- prove exactly one meter/effect/operation/object revision for that round;
- prove logical work converges.

If your environment cannot safely implement an actual process kill, document the limitation and do not silently downgrade the requirement.

## 10. Full regression and historical invariants

Freshly run:
- candidate focused trusted-return/recovery tests;
- R1-R5;
- authenticity/transplant/corruption;
- background attempt recovery;
- turn execution recovery;
- full repository pytest.

Formal environment:
- CPython 3.12.14;
- Pydantic 2.13.5;
- pytest 8.4.2;
- record actual SQLite version.

Do not fake SQLite equality with previous runs.

## 11. Candidate lineage

Verify:
- candidate is genuinely based on fresh main;
- #258 and #261 were not rewritten;
- trusted-return carry-forward is complete;
- review-only #261 artifacts were not imported into the implementation candidate;
- no hidden competing implementation is being accepted by accident.

## 12. Required report

Publish durable review-only evidence.

Report at minimum:
1. review-time live main;
2. exact candidate identity;
3. reviewer suite hashes and frozen enumeration;
4. baseline RED results;
5. complete side-effect registry inventory;
6. exact replay results;
7. rev5 -> rev6 adjudication;
8. trusted-return authority/adversarial results;
9. store fail-closed results;
10. process-loss results;
11. full regression;
12. environment;
13. limitations;
14. blocker count;
15. final verdict.

Preserve every reviewer harness revision and raw failing output.

## 13. Verdict

Choose exactly one:

### `ACCEPTANCE_PASS / blocker=0`

Only if:
- the complete reachable side-effecting surface converges under exact recovery;
- changed/conflicting recovery remains fail-closed;
- the rev5 -> rev6 adjudication is independently defensible and does not weaken the binding recovery contract;
- trusted-return authority is unchanged;
- corruption/transplant attacks fail closed;
- process-loss converges exactly once;
- full regression is green.

### `ACCEPTANCE_FAIL / blocker=N`

If any binding defect remains.

### `REVALIDATION_REQUIRED`

If the exact candidate changes.

If PASS, state only:

`READY_FOR_PM_INTEGRATION`

Do not merge PR #264.

Do not start RC-REFREEZE-003, A-004, persistence Corrective-003, Resident B/C, evaluator, or release work.
