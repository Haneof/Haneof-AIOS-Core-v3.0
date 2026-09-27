# CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Role:

Independent Core Runtime / Exact-Response Authenticity Acceptance Reviewer

Engineering PR:

#219

You are not:

- PR #219 author;
- Corrective-002 engineer;
- PM;
- Resident;
- RC re-freeze engineer.

Your only task is to independently try to falsify the Corrective-002 exact candidate.

## 1. Fetch live state first

Fetch current live `main`.

Read:

1. `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
2. `AIOS_v3.0_CURRENT_CHECKPOINT.md`
3. `PROJECT_MASTER_MAP.md`
4. `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_ACCEPTANCE_FAIL_ADJUDICATION_2026-09-26.md`
5. `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001_ACCEPTANCE_FAIL_ADJUDICATION_2026-09-27.md`
6. `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_002_PY312_ENVIRONMENT_RULING_2026-09-27.md`
7. `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_002_CI_ONLY_VALIDATION_RULING_2026-09-27.md`
8. `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_002_IMPLEMENTATION_GATE_RECORD_2026-09-27.md`
9. `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_002_PY312_GATE_EVIDENCE_2026-09-27.md`
10. PR #219 current body/diff/comments/head.

Confirm:

`CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE = READY`

If not READY, STOP.

## 2. Pin exact identity

Tested exact candidate:

`227327c657788efb1b5de1bc26e69c35c900a85e`

Parent:

`72aed7eddf22d0d7f05e53bb3bd46ed28554f7fc`

Tree:

`01dfa445414543aab41e1b74b813bbff80b21c5c`

Frozen RED-only commit:

`a7678f9b81f4a46e91199c996e2a8091c56a2a4d`

Frozen authenticity probe SHA256:

`35cba59f318b752ed872821961296f35810443c61db6fd98c8c8f5eee4215225`

Frozen probe Git blob at RED and implementation exact:

`6f0c3850368475e166d28d0a6df4b86b610d2c60`

Historical failed exacts remain:

- `3f9ec00d0fa283bc5294574d6da1e84d654d6645 = ACCEPTANCE_FAIL / blocker=2`
- `030acbfe2d935dfc166ff7a9a1760b6ddd46d42d = ACCEPTANCE_FAIL / blocker=1`

Do not relabel historical FAIL evidence.

## 3. Verify provenance before semantics

Independently verify:

- PR #219 is OPEN / UNMERGED;
- remote PR head is exact `227327c...`, or classify drift before testing;
- parent/tree match the pinned values;
- frozen probe bytes are unchanged;
- no implementation/test commit exists after the tested exact;
- the Python 3.12 gate evidence actually corresponds to exact head `227327c...`.

CI-only PR #228 was validation-only and must remain CLOSED / UNMERGED. It has no integration authority.

## 4. Primary adversarial question

The candidate claims that externally staged exact-response recovery now requires a non-caller-forgeable trusted provider-return proof.

Try to disprove that claim.

The central invariant is:

> A caller that knows every public/caller-visible request and response value still cannot cause Core to accept exact response bytes unless the trusted provider/relay return path previously authenticated those exact bytes for that exact attempt/request.

Public/caller-visible values include:

- relay id;
- attempt id;
- subject/work/work-kind;
- model round;
- provider/model/request id;
- outbound request fingerprint if observable;
- directive payload;
- payload SHA256;
- ordinary response fingerprint;
- any public receipt fields.

## 5. Fresh reviewer-authored probes

Do not only run author tests.

At minimum independently attack:

A. provider returns no response; caller knows relay id and fabricates capability directive.

B. same with forged assistant response.

C. same with forged silence.

D. modify one field/byte of a legitimately authenticated response and recompute all caller-computable hashes.

E. copy a valid receipt/proof from attempt A to B.

F. cross work kind.

G. cross subject.

H. round N to M.

I. change provider/model/request identity.

J. missing proof.

K. random proof with correct format/length.

L. proof prefix/version confusion.

M. stale proof after retry/reconciliation state transition.

N. staged response DB row tamper after authentication.

O. trusted receipt DB row tamper after authentication.

P. delete/replace authority row and test fail-closed behavior.

Q. reopen/restart store and verify authority continuity.

R. backup/restore and verify legitimate receipt recovery without silently minting a replacement authority.

S. concurrent/open-race initialization of the authority store.

T. attempt to obtain signing authority through any public RuntimeSnapshot/API/evidence/log/export surface.

For every negative case prove failure occurs before:

- staged response mutation;
- attempt provenance rewrite;
- `response_returned`;
- metering;
- capability effect;
- assistant output;
- World revision.

## 6. Trusted-return boundary review

Independently inspect the exact call order.

Prove or falsify:

1. model/provider returns directive;
2. trusted authenticator captures exact returned bytes;
3. only then response provenance is recorded;
4. only then metering/capability/output/World effects may occur.

Check exception paths too.

Try to find any path that:

- records/stages response before authentication;
- mints receipt after a caller-controlled recovery path;
- allows a public caller to invoke signing authority;
- signs bytes different from the bytes later staged/applied;
- treats metadata-only reconciliation as exact response authenticity.

## 7. HMAC authority review

Do not accept “uses HMAC” as sufficient.

Verify:

- authority is 256-bit;
- authority is generated once per store and durably preserved;
- secret is not exposed through RuntimeSnapshot;
- secret is not part of provider-facing payload;
- secret is not returned by recovery APIs;
- secret is not written to ordinary logs/evidence;
- caller cannot supply/replace authority through normal recovery API;
- proof uses canonical message construction;
- canonical message binds exact attempt/work/round/request/provider/model/payload identity;
- verification uses constant-time comparison where appropriate;
- version/prefix parsing cannot downgrade/bypass;
- missing/corrupt authority fails closed;
- historical unauthenticated staged rows fail closed.

Do not claim resistance to a fully privileged attacker that can arbitrarily read/write the underlying DB unless the design explicitly promises that. Evaluate the actual frozen threat model.

## 8. Preserve historical blocker closures

Freshly re-attack Corrective-001 historical closures:

### Historical BLK-001

- work A -> B;
- wake -> periodic review;
- periodic review -> user turn;
- subject A -> B;
- round N -> M;
- same provider/model transplant.

All must remain rejected.

### Historical BLK-002

Recursive duplicate JSON semantic keys must still fail closed before semantic construction, including:

- response;
- silence;
- capability_calls;
- usage;
- provenance;
- capability call fields;
- nested arguments;
- escaped-key decoded collisions.

## 9. Crash/restart/exactly-once

Freshly exercise:

1. crash after request binding before provider dispatch;
2. crash after dispatch with no trusted response;
3. SIGKILL after trusted receipt commit before response recording;
4. crash after staging before semantic application;
5. crash during capability application;
6. crash after capability result before next model round;
7. crash after terminal response/silence before completion marker;
8. repeated recovery;
9. payload tamper;
10. proof tamper;
11. receipt tamper;
12. cross-attempt replay;
13. normal provider path;
14. `not_submitted` safe retry.

Use real subprocess/process death where practical.

Prove legitimate exact recovery still has:

- same attempt/round;
- zero provider redispatch for the recovered round;
- exactly-once capability/output/metering.

## 10. Fresh execution environment

Use Python 3.12.

Record exact:

- Python;
- pytest;
- pydantic;
- OS/container;
- commands;
- exit codes;
- pass/fail counts.

At minimum run:

- reviewer-authored probes;
- frozen authenticity suite;
- Corrective-001 suite;
- Corrective-002 recovery suite;
- original exact-response recovery suite;
- background-attempt runtime;
- CognitiveRuntime;
- fused runtime;
- metering;
- Wake;
- Periodic Review;
- User Turn;
- full `pytest -q`.

Do not modify candidate implementation or frozen tests.

## 11. CI evidence revalidation

Independently inspect the formal Python 3.12 evidence:

- CI-only PR #228;
- head exact `227327c...`;
- base exact `72aed7ed...`;
- `p16-convergence-gate` run `36307032411`;
- full-core-regression job `108585586234`.

Confirm logs record:

- CPython 3.12.14;
- pytest 8.4.2;
- pydantic 2.13.5;
- `pytest -q` reaches 100%;
- job SUCCESS.

Also confirm #228 is CLOSED / UNMERGED.

Treat CI as supporting gate evidence, not a substitute for your fresh adversarial review.

## 12. Final live-main drift check

Before verdict, fetch live main again.

Compare candidate parent/current main for any relevant:

- `src/**`;
- `tests/**`;
- schema/recovery semantics;
- workflow changes.

If current-main semantic drift invalidates the candidate basis, return:

`REBASE_REVALIDATION_REQUIRED`

Do not accept stale evidence.

## 13. Review-only discipline

Forbidden:

- modify PR #219 implementation;
- fix candidate;
- modify frozen tests;
- merge #219;
- enter RC-REFREEZE-002;
- resume B persistence;
- run Resident;
- create replacement candidate.

## 14. Verdicts

Only:

`ACCEPTANCE_PASS`

`ACCEPTANCE_FAIL`

`REBASE_REVALIDATION_REQUIRED`

If FAIL, report exact blocker count and fresh reproduction evidence.

If PASS, use exact wording:

`PR #219 CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002 tested exact candidate 227327c657788efb1b5de1bc26e69c35c900a85e is independently accepted for PM integration.`

## 15. Review artifact

Write:

`reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_002_INDEPENDENT_ACCEPTANCE_2026-09-27.md`

If GitHub write access exists, publish it via a review-only PR from review-time main.

Do not write review commits to PR #219.

After verdict, STOP.
