# C15 RCC Sequential Release Contract v1

> Task: `C15-RCC-FIXTURE-001`  
> Access class: OPERATOR / EVALUATOR ONLY — Resident run contracts are the only Resident-safe instructions.  
> Fixture: `c15-rcc-fixture-v1`  
> Fixture SHA256: `sha256:7ccb309d207cb6ee240fbc008ee4f535e25571f04ba7ca1b7c95bf9afb5ebf46`  
> Contract: `c15-rcc-sequential-release-v1`  
> Timezone: `America/Los_Angeles`

## 1. Scope

This contract defines only mechanical sealed release. It does not define expected cognition, expected Claims, capability calls, confidence, revision text, or evaluator verdicts.

The C15 wrapper reuses the frozen C14 v2 mechanics for durable SQLite exact-revision acknowledgement, receipt-chain re-verification, canonical USER conversation ingest, reveal-without-advance, and fail-closed ordering. The only state-machine extension is a third sealed phase required by C15.

## 2. Access boundary

Resident processes must not read this full operator contract, the sealed fixture, fixture manifest, event schema, bindings implementation, mechanical gate, evaluator notes, completion evidence, or another Resident contract. Each Resident receives only its own safe run contract plus normal AIOS RuntimeSnapshot/capabilities and the single current reveal.

The release operator may read sealed material internally only to validate the exact current cursor and emit the resident-visible projection.

## 3. Private durable lineage

All phases use the same private SQLite AIOS World and one continuous release-state receipt chain. A phase transition is legal only after the previous phase's final cursor has a durable World acknowledgement and there is no pending reveal.

No transcript handoff or prose summary is part of the release state.

## 4. Resident-visible projection

Each reveal emits exactly:

- `event_id`
- `sequence`
- `occurred_at`
- `dimension`
- `source_kind`
- `source_class`
- `modality`
- `resident_visible_payload`

It omits phase, future cursor count, hidden notes, manifest data, semantic labels, expected answers, and attestation fields.

Reveal never advances the cursor. Only exact durable ack does.

## 5. Canonical USER conversation

Any released USER conversation envelope (`dim:conversation`, `conversation`, `USER`, `text`) must be persisted by `canonical_conversation_ingest.py`. Generic mechanical ingest rejects it in every phase.

The same session id / turn index / text / occurred_at must be reused by ordinary runtime turn processing so the canonical user Observation is idempotently reused rather than duplicated.

## 6. Three sealed boundaries

Operator-only ranges are:

- phase A: cursors 1..13
- phase B: cursors 14..22
- phase C: cursors 23..30

A cannot reveal cursor 14. B cannot initialize before ack 13 and cannot reveal cursor 23. C cannot initialize before ack 22. Skip, reorder, duplicate ack, wrong phase, wrong durable ref, wrong canonical session/turn, or digest mismatch all fail closed.

## 7. Mechanical-only rule

The release machinery may reveal, ingest, verify, acknowledge, persist cursor state, compute hashes, and transition a phase. It must not form, revise, retract, retain, weaken, rank, or recommend cognition and must not pre-generate a ModelDirective.

## 8. Replacement-model attestation slot

The manifest intentionally keeps `execution_attestation_ref` and `trusted_model_identity_artifact` null. Fixture metadata, configured model strings, Resident self-report, branch names, or Python constants cannot change that to verified.

A later execution platform may create a separate trusted external artifact outside Resident control. Only the evaluator may use that artifact for R6. If it is absent or insufficient, R6 is not eligible for VALID even if phase C otherwise completes.
