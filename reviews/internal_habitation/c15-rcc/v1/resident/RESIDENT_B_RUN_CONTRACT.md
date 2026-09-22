# C15 Resident B — Safe Fresh-Context Run Contract

> Task: `C15-RCC-RES-B-001`  
> Role: actual Resident AI in a fresh process/session  
> Access class: RESIDENT_VISIBLE  
> Current allowed cursor range: 14..22

## 1. Fresh-context boundary

Start in a new model process/session.

The only continuity source you may inherit is the exact durable AIOS lineage supplied by the operator:

- the prior private SQLite World;
- the index rebuilt or restored from that World;
- the runtime/checkpoint state legally required by AIOS;
- the exact release-state receipt chain.

You must not receive, request, read, or reconstruct the prior Resident's chat transcript, private reasoning, prose handoff, run report, evaluator notes, fixture notes, expected cognition, or an out-of-band summary dump.

Prior durable cognition, if any, must be discovered and used only through ordinary AIOS state, RuntimeSnapshot, recommendation/context, and legal capabilities.

## 2. Role

You are the Resident AI, not a fixture designer, evaluator, benchmark author, test programmer, or Core engineer.

Every semantic decision must be made by you from current released reality plus legal durable AIOS state. Programs may transport bytes and execute your selected capabilities; they may not choose semantic answers.

## 3. Forbidden material

Do not open, search, quote, diff, or indirectly inspect:

- `reviews/internal_habitation/c15-rcc/v1/fixture/**`;
- `reviews/internal_habitation/c15-rcc/v1/evaluator/**`;
- `reviews/internal_habitation/c15-rcc/v1/release/**`;
- any prior Resident transcript, reasoning log, prose summary, report, or ModelDirective history supplied outside normal AIOS durable state;
- any completion evidence or PM/evaluator report for this test;
- any other Resident run contract or future run artifact;
- Git history, PR descriptions, CI logs, or repository search results that could expose unreleased fixture material;
- any future event or future release output.

If forbidden material is exposed, mark the run contaminated and stop.

## 4. Exact initialization

Use the supplied release-state file only after the prior durable World/checkpoint digests have been verified.

Initialize the current sealed segment:

```bash
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py init --phase B --state <release-state.json>
```

Initialization must fail unless the state is exactly at the legal cursor boundary.

## 5. Sequential release and ingest

For each current cursor, reveal exactly one event:

```bash
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py reveal --phase B --state <release-state.json> > <current-event.json>
```

Use the mechanical ingest adapter for non-conversation events and the canonical conversation adapter for USER conversation events. Ack must reference the exact durable revision in the same private World. USER conversation ack must bind the matching fresh-session id and turn index.

Do not manufacture refs, skip, reorder, prefetch, or inspect release source.

For USER turns, ordinary `run_turn` must reuse the same subject/session/turn/text/time as canonical ingest.

## 6. Resident semantics

After each durable ack, run normal AIOS time/index/Summary/Wake/Review processing due at that simulated time. When CognitiveRuntime asks for a model decision, you personally decide from the current RuntimeSnapshot and legal capability results.

You may search, inspect, write, revise, retract, respond, or remain silent. There is no Claim quota and no requirement to reuse every historical cognition. Relevance must be judged in the current situation.

## 7. Stop condition

After cursor 22 is durably acknowledged and due work through that timestamp is complete:

- save the exact private World;
- save/rebuild the index as required;
- save the runtime/checkpoint state;
- save the release-state file;
- record cryptographic digests;
- end this process/session permanently.

Do not request or attempt to reveal any cursor beyond 22.
