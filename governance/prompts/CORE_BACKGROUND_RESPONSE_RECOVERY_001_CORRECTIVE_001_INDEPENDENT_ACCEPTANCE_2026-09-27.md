# CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Role:

Independent Core Runtime / Exact-Response Recovery Corrective Acceptance Reviewer

You are not:
- PR #219 author
- corrective engineer
- PM
- Resident
- RC re-freeze engineer

Your task is to independently try to falsify the corrective exact candidate.

## 1. Fetch live state first

Fetch current live `main`.

Read:

1. `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
2. `AIOS_v3.0_CURRENT_CHECKPOINT.md`
3. `PROJECT_MASTER_MAP.md`
4. `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_ACCEPTANCE_FAIL_ADJUDICATION_2026-09-26.md`
5. `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001_PUBLICATION_RECORD_2026-09-27.md`
6. `governance/prompts/CORE_BACKGROUND_RESPONSE_RECOVERY_001_2026-09-26.md`
7. `governance/prompts/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001_2026-09-26.md`
8. PR #219 current body, diff, comments and current remote head
9. corrective candidate report and all committed red/evidence logs at the evidence-only head

Confirm:

`CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE = READY`

If not READY, STOP.

## 2. Pin exact identities

Engineering PR:

`#219`

Tested exact corrective candidate:

`030acbfe2d935dfc166ff7a9a1760b6ddd46d42d`

Exact parent:

`b8bc7b32497dc0fdc0a15194256795a7c6771048`

Exact tree:

`b1c39039db6c48e2aa6fb111b03394eb5d0b8f9c`

Evidence-only head / expected current PR head:

`a1c6e74de71f783951f2772e2f065880d7146ec5`

Construction main incorporated by the merge parent:

`acf8ac3ea3e8da2b5c77e81534ba62d5166879f2`

Historical failed exact:

`3f9ec00d0fa283bc5294574d6da1e84d654d6645`

Historical verdict:

`ACCEPTANCE_FAIL / blocker=2`

The historical failure must remain preserved.

Before semantic review, independently verify:

- PR #219 is OPEN / UNMERGED;
- its remote head is the pinned evidence-only head or classify any drift;
- exact candidate exists remotely;
- exact parent and tree match the pins;
- `b8bc7b32...` has parents `2ea8dd...` and `acf8ac3...`;
- `a1c6e74d...^ = 030acbfe...`;
- `030acbfe... -> a1c6e74d...` has zero `src/**` and zero `tests/**` changes.

If implementation/test files changed after the pinned exact, STOP with `REBASE_REVALIDATION_REQUIRED` or `ACCEPTANCE_FAIL` as appropriate.

## 3. Historical blockers to attack

The prior exact `3f9ec00d...` failed because:

### IA-BLK-001

An exact response from work A could be transplanted onto unrelated work B / work-kind / subject / model round and be semantically applied.

### IA-BLK-002

Default JSON decoding accepted duplicate semantic keys with last-key-wins behavior, allowing conflicting fields such as response/silence to be discarded before validation.

The corrective is accepted only if both are mechanically closed without weakening existing recovery semantics.

## 4. IA-BLK-001 acceptance focus — originating-request binding

Do not accept merely because a new relay/request string exists.

Prove the corrective establishes durable origin ownership before provider response adoption.

Inspect and test the lifecycle of the binding across:

- subject
- work kind
- work id
- model round
- background attempt id
- exact outbound provider request / relay identity

Required properties:

1. Binding is durably created before provider dispatch can become ambiguous.
2. The binding already belongs to the target attempt before response staging.
3. A caller cannot make B accept A by copying A's:
   - provider
   - model
   - request_id
   - response fingerprint
   - directive payload
   - relay id / receipt / binding token
4. Caller-supplied data alone cannot mint a valid binding for another attempt.
5. Staging failure occurs before attempt provenance is rewritten.
6. Staging failure occurs before semantic application.
7. Same-attempt legitimate recovery still works with recovered-round provider call count 0.
8. Binding survives process death/restart.
9. Existing `in_doubt` semantics remain fail-closed when exact ownership proof is absent.
10. `not_submitted` behavior remains unchanged.
11. No operator semantic engine or second World/cognition truth store is introduced.

### Minimum fresh reviewer-authored transplant probes

Create fresh tests/probes independent of author tests:

A. work A response -> work B

B. wake -> periodic_review

C. periodic_review -> user_turn

D. subject A -> subject B

E. round N -> round M

F. A and B use identical provider/model

G. copy A's complete externally visible response metadata plus A relay id into B

H. caller invents a syntactically valid but nonexistent relay id

I. missing relay id

J. relay id from an already completed/metered unrelated attempt

Every negative transplant must fail before semantic effect and before target attempt provenance is rewritten.

Positive control:
same exact attempt + correct durable origin binding must recover with provider call count 0.

## 5. IA-BLK-002 acceptance focus — strict duplicate-key rejection

Independently verify duplicate keys are rejected before semantic construction.

The check must be recursive.

Fresh probes must include:

- duplicate top-level `response`
- duplicate top-level `silence`
- duplicate top-level `capability_calls`
- duplicate `usage.provider`
- duplicate `usage.model`
- duplicate `usage.request_id`
- duplicate `provenance.provider`
- duplicate `provenance.model`
- duplicate `provenance.request_id`
- duplicate capability-call `name`
- duplicate capability-call `arguments`
- duplicate capability-call `call_id`
- duplicate key inside nested capability arguments
- duplicate key expressed through JSON escape equivalence, for example a decoded key collision such as `response` versus an escaped spelling that decodes to the same key

For every rejected payload prove:

- no staged response row;
- target attempt does not newly transition to `response_returned`;
- no capability side effect;
- no assistant output;
- no new metering effect;
- no World revision caused by the rejected response.

Also verify ordinary unique-key exact payloads still decode and recover normally.

## 6. Crash/restart / exactly-once matrix

Freshly exercise the corrective against the original recovery invariants, including at least:

1. crash after provider boundary with no exact response -> remains in_doubt / no blind retry
2. correct exact response staged -> recovered provider call count 0
3. crash after durable origin binding but before provider dispatch
4. crash after provider dispatch but before response staging
5. crash after exact response staging before semantic application
6. crash during capability application
7. crash after capability result before next model round
8. crash after terminal response/silence before completion marker
9. repeated recovery -> no duplicate capability/output/metering
10. later model round after recovered capability follows ordinary provider path
11. normal non-recovery provider path remains green
12. `not_submitted` safe retry remains green

At process level, use real process death / restart where practical rather than only in-process exception simulation.

## 7. Durable storage / upgrade / tamper review

Inspect whether the new binding is stored in the existing runtime recovery store rather than a new cognition authority.

Check:

- additive schema compatibility;
- old databases upgrade safely;
- no World revision is spent merely creating recovery provenance;
- backup/reopen behavior remains valid;
- repeated binding creation is idempotent for the same attempt;
- conflicting binding mutation is rejected;
- direct staged-row tampering / payload hash tampering remains detected;
- binding cannot be reassigned across attempts after restart.

## 8. Fresh regression requirements

Do not inherit author test conclusions.

Use the exact candidate `030acbfe...`.

Record exact environment.

At minimum run:

- reviewer-authored blocker probes;
- `tests/integration/test_core_background_response_recovery_001.py`;
- `tests/integration/test_core_background_response_recovery_001_corrective_001.py`;
- relevant background-attempt runtime tests;
- turn-execution recovery tests;
- metering tests;
- Wake regressions;
- Periodic Review regressions;
- User Turn regressions;
- affected CognitiveRuntime / fused runtime tests;
- full repository `pytest -q` under the repository's Python 3.12 Core gate environment where available.

The author evidence reports Python 3.12.14 / pytest 8.4.2 / pydantic 2.13.5 and one full-suite isolation-path failure also reproduced on clean main. Independently verify that classification if it matters to your verdict. Do not simply inherit it.

Do not modify an existing test merely to make the candidate green.

## 9. Current GitHub CI state

At PM handoff, publication of the evidence head created 17 PR workflow runs, but all have GitHub conclusion:

`action_required`

with zero jobs.

Representative:
`p16-convergence-gate` run `36300238046`.

This is neither PASS nor FAIL.

Record this state honestly. If the workflows become executable during review, inspect the fresh exact-head results. Otherwise your acceptance must rely on your own fresh execution plus source/object review and must explicitly record the CI approval limitation.

The exact-object publication workflow itself is not a product regression test. It only proves publication/object integrity:

- run `36300226068`
- job `108566390342`
- SUCCESS
- force push NO

## 10. Main drift classification

Fetch live `main` again before final verdict.

Compare relevant runtime/test drift since construction main `acf8ac3...`.

If live main has semantically overlapping Core changes that invalidate the candidate's basis, return:

`REBASE_REVALIDATION_REQUIRED`

Do not silently accept against stale assumptions.

Governance/docs-only drift may be classified as non-semantic if independently verified.

## 11. Scope prohibitions

Do not:

- repair PR #219;
- change implementation;
- merge #219;
- weaken tests;
- enter `CORE-RC-REFREEZE-002`;
- resume B persistence corrective;
- run Resident;
- modify historical failed evidence;
- self-author a replacement candidate.

This window is review-only.

## 12. Verdicts

Only:

- `ACCEPTANCE_PASS`
- `ACCEPTANCE_FAIL`
- `REBASE_REVALIDATION_REQUIRED`

If FAIL, enumerate exact blockers and preserve fresh red evidence.

If PASS, exact wording:

`PR #219 CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-001 tested exact candidate 030acbfe2d935dfc166ff7a9a1760b6ddd46d42d with evidence-only head a1c6e74de71f783951f2772e2f065880d7146ec5 is independently accepted for PM integration.`

## 13. Review artifact

Write:

`reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001_INDEPENDENT_ACCEPTANCE_2026-09-27.md`

Create one review-only PR from review-time main if your environment has GitHub write access.

If write access is unavailable, report the exact local review commit/artifact as unpublished. Do not pretend it exists remotely.

Do not merge PR #219.

STOP after the verdict.
