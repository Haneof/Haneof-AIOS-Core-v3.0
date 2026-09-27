# CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-001 Independent Acceptance FAIL Adjudication

Date: 2026-09-27

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Engineering PR:
#219

Corrective tested exact candidate:
`030acbfe2d935dfc166ff7a9a1760b6ddd46d42d`

Exact parent:
`b8bc7b32497dc0fdc0a15194256795a7c6771048`

Exact tree:
`b1c39039db6c48e2aa6fb111b03394eb5d0b8f9c`

Evidence-only head:
`a1c6e74de71f783951f2772e2f065880d7146ec5`

Independent Acceptance verdict:
`ACCEPTANCE_FAIL`

Fresh blocker count:
`1`

Historical exact remains:
`3f9ec00d0fa283bc5294574d6da1e84d654d6645 = ACCEPTANCE_FAIL / blocker=2`

## Fresh blocker

### IA-C001-BLK-001 — relay identity proves routing, not provider-response authenticity

The corrective closes the two historical defects:
- cross-work / cross-work-kind / cross-subject / cross-round transplantation is rejected by the durable originating-request binding;
- recursive duplicate JSON keys are rejected before semantic construction.

However, fresh Independent Acceptance found a new candidate-specific provenance gap.

The exact candidate exposes the Core-minted relay identity to the provider handler through `RuntimeSnapshot.outbound_relay_id`. Recovery staging then accepts a response for a dispatching/in_doubt attempt when:
- the supplied provider/model/request identity is self-consistent with the supplied directive;
- the supplied request id equals the pre-existing durable relay id;
- the caller supplies a response fingerprint matching the caller-supplied directive.

The relay id itself is deterministically derived from durable request metadata and the outbound request fingerprint. It is not an authenticity proof over the provider's returned bytes. The response fingerprint is also only a digest of the supplied directive and can be recomputed by a caller that fabricates a different directive.

Therefore a caller that knows the target attempt's relay id can fabricate a different exact directive, recompute the directive fingerprint, present matching provider metadata, and pass the current staging checks even when the provider never returned those bytes.

The reviewer reports a fresh reproduction in which no provider response existed, yet a forged capability directive was staged/applied and created a World Task at revision 1.

Reviewer evidence is local-only / unpublished:
- `reviewer_probes.py`
- `relay_id_forgery_red.log`
- `reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001_INDEPENDENT_ACCEPTANCE_2026-09-27.md`

Do not claim those local artifacts exist remotely unless they are later published.

## PM source revalidation

PM independently re-read the remote exact `030acbfe...` and confirmed the blocker is present in source.

At the exact candidate:

- `BackgroundModelAttemptLedger.relay_id_for(...)` derives `relay_id` by SHA-256 over attempt/work/round/request-fingerprint metadata.
- `TurnRuntime` stores the durable binding before dispatch and then sets `snapshot._outbound_relay_id = binding.relay_id`.
- `CognitiveRuntime` invokes `model_handler(snapshot)`, so the provider adapter can observe that relay id.
- `stage_exact_response(...)` recomputes the response fingerprint from the supplied directive and checks it against the supplied fingerprint.
- for `dispatching` / `in_doubt`, origin validation requires the supplied request id to equal the durable binding's relay id.
- there is no independent provider-authenticated receipt/signature/MAC or other non-caller-forgeable proof binding the exact returned directive bytes to the actual provider boundary crossing.

Accordingly the relay binding is sufficient to stop A→B transplant but insufficient to prove that the staged bytes were actually returned by the provider/relay path for that request.

This source-level confirmation is independent of the reviewer's Python version.

## Reviewer execution record

Reviewer reported:
- 30 fresh reviewer probes, including the exploit reproduction;
- 148 focused regressions PASS;
- full `pytest -q`: 735 PASS;
- Python 3.11.2;
- PR #219 remained OPEN / UNMERGED;
- no implementation or `tests/**` changes;
- review artifact local-only / unpublished.

Python 3.11.2 is below the repository's declared Core minimum of Python 3.12, so the 735-pass full-suite run is not accepted as formal Core gate evidence. It does not weaken the FAIL verdict because the fresh blocker is independently source-confirmed and is sufficient to reject the candidate.

At review time the PR head had no executable check-runs; this is neither CI PASS nor CI FAIL.

## Disposition

PR #219 remains:
- OPEN;
- UNMERGED;
- NOT ACCEPTED.

Corrective exact `030acbfe...` is historical failed evidence for this acceptance round and must never later be described as accepted.

Do not enter `CORE-RC-REFREEZE-002`.

Do not resume B persistence work.

Do not run Resident.

## Next legal task

`CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002`

Reuse PR #219. Do not create a competing implementation PR.

Corrective-002 is strictly limited to closing IA-C001-BLK-001 plus the minimum regression/evidence needed to prove exact-response authenticity without reopening the two historical blockers.

Required invariant:

> An externally staged exact response must carry durable, mechanically verifiable authenticity evidence that could only have been produced by the trusted provider/relay return path for the exact originating attempt/request and exact returned directive bytes. Knowledge of relay id, provider/model/request metadata, payload contents, and self-computable hashes must be insufficient to forge acceptance.

Allowed implementation shape is intentionally not preselected. A minimal cryptographic or mechanically trusted response receipt is acceptable if:
- its authenticity material is not exposed to the recovery caller/provider-facing snapshot in a forgeable form;
- it binds exact attempt/work/round identity and exact response bytes/hash;
- it is durably recorded/preserved at the provider/relay return boundary;
- recovery verifies it before staging/state transition/semantic application;
- missing, forged, replayed, cross-attempt, or payload-mismatched proof fails closed;
- legitimate same-attempt recovery still uses zero provider redispatch;
- no second World/cognition truth store or operator semantic engine is introduced.

Historical blocker closures must remain green.

After Corrective-002 reaches REVIEW_READY, a fresh independent reviewer must re-attack it before any PM integration.
