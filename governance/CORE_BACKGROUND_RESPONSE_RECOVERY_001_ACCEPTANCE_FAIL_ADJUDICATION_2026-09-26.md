# CORE-BACKGROUND-RESPONSE-RECOVERY-001 Independent Acceptance FAIL Adjudication

Date: 2026-09-26

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Engineering PR:
#219

Tested exact candidate rejected by Independent Acceptance:
`3f9ec00d0fa283bc5294574d6da1e84d654d6645`

Candidate parent:
`a310bf1202bf41644c2f3e25798053a6636e14be`

Candidate exact tree:
`4e9e3a5685373f46ba56d51259f39af710a3cf53`

Review verdict:
`ACCEPTANCE_FAIL`

Blocker count:
`2`

Reviewer-local evidence commit:
`5c59f17658524c0ad23f409a8c108402cea34452`

The review-only commit was created in the independent-review environment but could not be pushed because that environment had no GitHub write credentials. It is therefore recorded here as reviewer-local / unpublished evidence. This adjudication does not pretend that commit exists in the remote repository.

## PM source revalidation

PM re-read the tested exact source and independently confirmed both reported root causes are present in `3f9ec00d...`.

### IA-BLK-001 — exact response is not bound to the originating work/attempt request

In `src/aios_core/runtime/background_attempt.py`, `stage_exact_response(attempt_id, ...)`:

- looks up the target attempt only by caller-supplied `attempt_id`;
- for `dispatching` / `in_doubt` states verifies that the supplied provider/model/request_id are internally consistent with the supplied directive;
- does not verify durable pre-dispatch request-binding evidence proving that this response originated from that exact attempt/work/subject/model-round;
- then writes the supplied provider/model/request_id/fingerprint into the target attempt.

Therefore an exact response from work A can be staged against an unrelated in-doubt work B if the caller supplies B's attempt id and A's self-consistent response identity. This permits cross-work / cross-work-kind / cross-subject response transplantation.

This violates the frozen exact-response recovery contract.

### IA-BLK-002 — duplicate JSON semantic fields are accepted by last-key-wins parsing

`decode_model_directive()` uses:

`json.loads(payload)`

followed by field-set equality checks.

Python's default JSON decoder accepts duplicate object keys and retains the last value. After parsing, `set(raw)` cannot distinguish a normal object from one that contained duplicate semantic fields.

A payload can therefore contain conflicting repeated fields such as `response` or `silence`; the earlier value is discarded before `ModelDirective` validation. This defeats the claimed strict/lossless exact-response decoder.

The decoder must reject duplicate keys before semantic construction, recursively for every JSON object that contributes to the exact directive.

## Candidate status

PR #219 remains:
- OPEN
- UNMERGED
- NOT ACCEPTED

The tested exact candidate `3f9ec00d...` is permanently historical failed evidence and must never later be described as accepted.

PR #219 currently has later evidence/governance-only commits. Those do not repair the tested exact candidate and do not change this verdict.

## PM corrective ruling

Do not create a competing implementation PR.

Reuse PR #219 / its engineering branch for:

`CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-001`

The corrective is strictly limited to IA-BLK-001 and IA-BLK-002 plus regression tests/evidence needed to prove them closed.

No architecture expansion is authorized.

## IA-BLK-001 required closure invariant

A recovered exact response must be cryptographically or mechanically bound to durable request identity for the exact originating:

- subject
- work kind
- work id
- model round
- background attempt id
- exact outbound provider request / relay binding

Provider/model/request_id self-consistency inside the returned directive is insufficient.

The binding must be durable before response adoption and must prevent:
- work A response -> work B
- wake -> periodic review
- periodic review -> user turn
- subject A -> subject B
- round N -> round M

even when the two works use the same provider/model and have otherwise plausible response metadata.

The implementation may choose the minimal durable request-binding representation, but it may not rely on operator semantic judgment or direct SQLite mutation.

## IA-BLK-002 required closure invariant

Exact directive decoding must reject duplicate JSON object keys before semantic interpretation.

At minimum adversarial coverage must include duplicates in:
- top-level `response`
- top-level `silence`
- top-level `capability_calls`
- nested `usage`
- nested `provenance`
- capability-call object fields
- nested capability `arguments` objects

No duplicate may be silently normalized by last-key-wins behavior.

## Required corrective evidence

Before new REVIEW_READY:

1. preserve historical failed exact candidate `3f9ec00d...`;
2. add red-first reproductions for both blockers;
3. prove cross-work/cross-kind/cross-subject/cross-round transplant is rejected before semantic application;
4. prove same-attempt exact response still recovers with provider call count zero;
5. prove recursive duplicate-key payloads fail closed with zero semantic effect;
6. rerun existing exact-response fault matrix;
7. rerun relevant background-attempt / turn-execution / metering / wake / periodic-review / user-turn regressions;
8. run full repository regression;
9. preserve the two PR #219 fixture-only scope-guard reds honestly if they remain non-applicable to Core-changing PRs;
10. pin a new tested exact candidate SHA and stop at REVIEW_READY.

No Independent Acceptance may be performed by the corrective author window.

## Next legal sequence

`CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-001`
→ fresh independent acceptance
→ only on PASS may PM integrate PR #219
→ `CORE-RC-REFREEZE-002`

Resident / B persistence work remains blocked.
