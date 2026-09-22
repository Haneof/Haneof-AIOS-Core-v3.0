# C15 Resident C — Safe Replacement-Execution Run Contract

> Task: `C15-RCC-RES-C-001`  
> Role: actual Resident AI in a new process/session  
> Access class: RESIDENT_VISIBLE  
> Current allowed cursor range: 23..30

## 1. Durable-lineage-only continuation

Start in a new process/session from the supplied durable AIOS lineage.

You may inherit only the exact private World, its index/rebuildable state, the runtime/checkpoint state legally required by AIOS, and the exact release-state receipt chain. You must not receive or read Resident A/B chat transcripts, private reasoning, prose handoffs, run reports, evaluator notes, expected cognition, or out-of-band summary dumps.

Any prior cognition must be recovered through ordinary AIOS retrieval/context and legal capabilities.

## 2. Model identity is not yours to attest

Do not write, edit, fabricate, infer, or self-report a model/provider identity artifact for evaluation.

A trusted execution platform may independently emit an external attestation that you cannot control. That artifact is evaluator-visible and is not a Resident capability or fixture field.

If no such trusted external artifact exists, continue the life normally; do not claim that replacement-model identity has been proven.

## 3. Forbidden material

Do not open, search, quote, diff, or indirectly inspect:

- `reviews/internal_habitation/c15-rcc/v1/fixture/**`;
- `reviews/internal_habitation/c15-rcc/v1/evaluator/**`;
- `reviews/internal_habitation/c15-rcc/v1/release/**`;
- Resident A/B transcripts, reasoning, reports, directive histories, or prose handoffs supplied outside AIOS durable state;
- any completion evidence or PM/evaluator report for this test;
- any other Resident run contract;
- Git history, PR descriptions, or CI logs that reveal sealed material;
- any unreleased event.

If forbidden material is exposed, mark the run contaminated and stop.

## 4. Exact initialization

Verify the supplied durable artifact digests, then initialize:

```bash
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py init --phase C --state <release-state.json>
```

Initialization must fail unless the durable release state is exactly at the legal boundary.

## 5. Sequential release and ingest

Reveal one current event at a time:

```bash
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py reveal --phase C --state <release-state.json> > <current-event.json>
```

Use the mechanical adapter for non-conversation events and canonical conversation ingest for USER conversation events. Acknowledge only the exact durable revision in the same private World, using matching fresh-session id and turn index for conversation events.

Do not prefetch, skip, reorder, manufacture refs, or inspect sealed/release source.

For USER turns, ordinary `run_turn` must reuse the canonical subject/session/turn/text/time.

## 6. Resident semantics

After each ack, run normal AIOS time/index/Summary/Wake/Review processing due at that timestamp. When the real runtime requests a model directive, you personally choose it from the current RuntimeSnapshot and legal capability history.

You may search, inspect, write, revise, retract, retain, respond, or remain silent. Current reality may support, weaken, refine, contradict, or be irrelevant to prior cognition. There is no fixed answer or Claim quota.

## 7. Stop condition

After cursor 30 is durably acknowledged and due work through that timestamp is complete:

- freeze the exact World, index/rebuild state, runtime/checkpoint, and release-state artifacts;
- record cryptographic digests;
- end the process/session.

Do not attempt to obtain fixture or evaluator material after completion.
