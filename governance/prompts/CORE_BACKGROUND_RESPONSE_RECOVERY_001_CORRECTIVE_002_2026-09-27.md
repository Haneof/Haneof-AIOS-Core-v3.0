# CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002

Repository:

`Haneof/Haneof-AIOS-Core-v3.0`

Role:

Core Runtime / Exact-Response Authenticity Corrective Engineer

Continue the same engineering PR:

#219

Do NOT create a competing implementation PR.

## 1. Fetch live state first

Fetch current live `main`.

Read:

1. `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
2. `AIOS_v3.0_CURRENT_CHECKPOINT.md`
3. `PROJECT_MASTER_MAP.md`
4. `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_ACCEPTANCE_FAIL_ADJUDICATION_2026-09-26.md`
5. `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001_ACCEPTANCE_FAIL_ADJUDICATION_2026-09-27.md`
6. `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001_PUBLICATION_RECORD_2026-09-27.md`
7. `governance/prompts/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001_2026-09-26.md`
8. `governance/prompts/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001_INDEPENDENT_ACCEPTANCE_2026-09-27.md`
9. PR #219 current body/diff/comments/head
10. committed corrective-001 evidence at the current PR head

Confirm:

`CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002 = READY`

If not READY, STOP.

## 2. Preserve history

Historical failed exact:

`3f9ec00d0fa283bc5294574d6da1e84d654d6645 = ACCEPTANCE_FAIL / blocker=2`

Corrective-001 failed exact:

`030acbfe2d935dfc166ff7a9a1760b6ddd46d42d = ACCEPTANCE_FAIL / fresh blocker=1`

Corrective-001 evidence-only head:

`a1c6e74de71f783951f2772e2f065880d7146ec5`

Do not rewrite either historical FAIL as green.

The fresh review artifact was local-only/unpublished. Do not claim its files or review commit are remote unless they actually appear later.

## 3. Only blocker to fix

### IA-C001-BLK-001 — relay ID is not provider-response authenticity

Current candidate correctly binds a recovery attempt to the originating request, but the proof used at staging is forgeable by a caller that knows the target relay id.

The current shape is insufficient because:
- `relay_id` is exposed to the provider handler via the runtime snapshot;
- the caller can provide that relay id as `provider_request_id`;
- the caller can fabricate a different directive;
- the caller can compute the directive's ordinary response fingerprint;
- provider/model/request metadata can be made internally self-consistent;
- Core has no independent proof that those exact response bytes were actually emitted by the trusted provider/relay return path.

The result is a provenance/authenticity failure even though cross-work transplant is now closed.

## 4. Required closure invariant

An externally staged exact response must carry durable, mechanically verifiable authenticity evidence that could only have been produced by the trusted provider/relay return path for:

- the exact subject;
- work kind;
- work id;
- model round;
- background attempt id;
- originating outbound request / relay binding;
- provider/model identity;
- exact returned directive bytes or a canonical hash of those exact bytes.

Knowledge of all public/caller-visible values must still be insufficient to forge a valid response.

Public/caller-visible values include at minimum:
- relay id;
- attempt id;
- subject/work/round identity;
- provider;
- model;
- request id;
- outbound request fingerprint if observable;
- directive payload;
- an ordinary SHA-256/response fingerprint computed from that payload.

A self-computable digest is integrity metadata, not authenticity.

## 5. Implementation constraints

Use the smallest correct mechanism.

An implementation may use a cryptographic or mechanically trusted response receipt, but it must satisfy all of these:

1. Authenticity material is created only on the trusted provider/relay return path.
2. The recovery caller cannot mint a valid receipt from exposed request metadata.
3. Any secret/key/authenticator used to validate the receipt is not exposed through `RuntimeSnapshot`, provider-facing request payload, ordinary recovery arguments, logs, or caller-controlled durable evidence.
4. The receipt binds exact attempt/request identity and exact response bytes/hash.
5. The receipt is durable before recovery can rely on it after process death.
6. Recovery validates authenticity before:
   - staging a response row;
   - rewriting attempt provenance;
   - entering `response_returned`;
   - metering;
   - capability execution;
   - assistant output;
   - World revision.
7. Missing/invalid proof fails closed.
8. Replaying proof from another attempt fails closed.
9. Replaying proof from another round fails closed.
10. Reusing a valid proof with modified payload fails closed.
11. Reusing a proof with modified provider/model/request metadata fails closed.
12. Legitimate same-attempt exact recovery still performs zero provider redispatch.
13. `in_doubt` remains fail-closed if no authentic exact response exists.
14. `not_submitted` safe retry semantics remain unchanged.
15. No second World/cognition truth store.
16. No operator semantic engine.
17. Do not turn a caller-supplied evidence string into an authority merely by hashing it.

Do not broaden architecture beyond the minimum required authenticity closure.

## 6. Mandatory red-first probes

Before the fix, preserve genuine red evidence for at least:

A. provider returns no response; caller knows relay id; caller forges a capability directive + matching self-computed response fingerprint -> current candidate accepts/applies it

B. same as A but forged assistant response

C. same as A but forged silence

D. caller modifies one byte/field of a legitimately captured response and recomputes the ordinary fingerprint

E. caller copies a valid receipt/proof from attempt A to attempt B

F. copy across work kind

G. copy across subject

H. copy from round N to round M

I. copy proof but change provider/model/request metadata

J. missing authenticity proof

Every forged/missing-proof case must fail before any semantic effect.

Preserve red logs append-only. Do not edit expected outcomes after seeing results.

## 7. Positive controls

Prove:

- a legitimate exact provider response with valid trusted authenticity proof can be staged after process death;
- recovery uses the same attempt/round;
- recovered-round provider call count = 0;
- response/capability/silence follows normal CognitiveRuntime semantics;
- repeated recovery is exactly-once for capability/output/metering;
- a later ordinary model round still uses the normal provider path.

## 8. Preserve the two historical blocker closures

Corrective-002 must not regress Corrective-001's valid fixes.

Freshly prove:

### Historical BLK-001 remains closed
- work A -> B transplant rejected;
- wake -> periodic_review rejected;
- periodic_review -> user_turn rejected;
- subject A -> B rejected;
- round N -> M rejected;
- same provider/model does not weaken ownership.

### Historical BLK-002 remains closed
Recursive duplicate JSON keys fail closed before semantic construction, including:
- response;
- silence;
- capability_calls;
- usage;
- provenance;
- capability call fields;
- nested arguments;
- escaped-key collision.

## 9. Crash/restart / tamper matrix

Freshly exercise at least:

1. crash after request binding before provider dispatch;
2. crash after provider dispatch with no authentic response -> in_doubt / no blind retry;
3. crash after authentic response receipt is durably captured but before Core staging;
4. crash after Core staging before semantic application;
5. crash during capability application;
6. crash after capability result before next model round;
7. crash after terminal output before completion marker;
8. repeated recovery -> no duplicate capability/output/metering;
9. tamper response payload after receipt creation;
10. tamper receipt/authenticator;
11. cross-attempt receipt replay;
12. normal non-recovery provider path;
13. `not_submitted` retry path.

Use real process death/restart where practical.

## 10. Test environment

The prior failed Independent Acceptance used Python 3.11.2, below the repository-declared Core minimum. Its fresh red exploit remains valid because PM independently source-confirmed the defect, but its 735-pass full-suite run is not formal Core gate evidence.

For Corrective-002 use the repository's Python 3.12 Core gate environment.

Record:
- Python version;
- pytest version;
- pydantic version;
- exact commands;
- exit codes;
- pass/fail counts.

Run at minimum:
- new blocker-specific red/green tests;
- Corrective-001 tests;
- original exact-response recovery integration tests;
- background attempt tests;
- turn execution recovery;
- metering;
- Wake;
- Periodic Review;
- User Turn;
- CognitiveRuntime/fused runtime affected tests;
- full `pytest -q`.

Do not weaken or edit unrelated tests to obtain green.

## 11. PR and scope discipline

Continue PR #219.

Do not:
- create a competing implementation PR;
- merge #219;
- self-accept;
- enter `CORE-RC-REFREEZE-002`;
- resume B persistence;
- run Resident;
- modify sealed fixtures;
- rewrite historical evidence;
- redesign unrelated Core areas.

## 12. Completion

Only after the blocker is closed and required regression is complete:

pin a new tested exact candidate with:
- exact SHA;
- parent;
- tree;
- changed files;
- diff stat;
- red-first evidence;
- green evidence;
- Python 3.12 full regression evidence.

Any later evidence-only head must have zero `src/**` and zero `tests/**` changes relative to the tested exact.

Stop at:

`REVIEW_READY`

Next task must be a fresh:

`CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE`

Do not perform that acceptance in this window.
