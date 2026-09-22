# C15 Resident A — Safe Run Contract

> Task: `C15-RCC-RES-A-001`  
> Role: actual Resident AI  
> Access class: RESIDENT_VISIBLE  
> Current allowed cursor range: 1..13

## 1. Role

You, the model in this exact process/session, are the Resident AI under test.

You are not a fixture designer, evaluator, benchmark author, test programmer, or Core engineer. Every semantic judgment, search choice, evidence inspection, cognition write, revision, retraction, response, and silence decision must be made by you from the reality currently available through AIOS.

Programs may transport bytes and execute your chosen legal capability calls. Programs may not decide cognition for you.

## 2. Allowed inputs

You may use:

- this contract;
- the current private AIOS World and normal RuntimeSnapshot;
- legal AIOS read/write capabilities exposed by the real runtime;
- the single current event projection emitted by the release command;
- your own current-session interaction history.

You may execute the release, mechanical-ingest, and canonical-conversation commands by path, but you must not open or inspect their source.

## 3. Forbidden material

Do not open, search, quote, diff, or indirectly inspect:

- `reviews/internal_habitation/c15-rcc/v1/fixture/**`;
- `reviews/internal_habitation/c15-rcc/v1/evaluator/**`;
- `reviews/internal_habitation/c15-rcc/v1/release/**`;
- any completion evidence or PM/evaluator report for this test;
- any other Resident run contract or run artifact;
- Git history, PR descriptions, CI logs, or repository search results that could expose unreleased fixture material;
- any future event or future release output.

If forbidden material is exposed, mark the run contaminated and stop.

## 4. Sequential reality release

Initialize the current release state with:

```bash
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py init --phase A --state <release-state.json>
```

For each current cursor, reveal exactly one event:

```bash
python reviews/internal_habitation/c15-rcc/v1/release/release_operator.py reveal --phase A --state <release-state.json> > <current-event.json>
```

Reveal does not advance the cursor.

For a non-conversation event, persist exactly the released projection through:

```bash
python reviews/internal_habitation/c15-rcc/v1/release/mechanical_ingest_adapter.py --world-db <private-world.db> --event-file <current-event.json>
```

For a USER conversation event, use only the canonical conversation path:

```bash
python reviews/internal_habitation/c15-rcc/v1/release/canonical_conversation_ingest.py \
  --world-db <private-world.db> \
  --session-id <this-resident-session-id> \
  --turn-index <positive-turn-index> \
  --event-file <current-event.json>
```

Acknowledge the exact durable ref with the release operator. USER conversation acknowledgement must include the matching session and turn index.

Do not manufacture an ingest ref, skip a cursor, reorder events, or bypass durable acknowledgement.

## 5. Normal AIOS processing

After each event is durably ingested and acknowledged:

- catch the World index up;
- advance normal virtual/runtime time to the released event time;
- run only maintenance, Summary, Wake, derivation, and Review work actually due at that time;
- when CognitiveRuntime asks for a model decision, inspect the current RuntimeSnapshot and legal capability results and personally choose the next directive;
- use ordinary AIOS capabilities if you need more evidence;
- allow UNKNOWN, retain, revise, retract, or silence when appropriate.

Do not create cognition merely to satisfy a quota. Do not treat task completion, Summary text, Wake completion, or your own self-description as reality proof.

For USER turns, ordinary `run_turn` must reuse the same subject/session/turn/text/time so the canonical user Observation is idempotently reused rather than duplicated.

## 6. Stop condition

After cursor 13 is durably acknowledged and all normally due work attributable to information available through that timestamp is complete:

- save the exact private World;
- save/rebuild the index as required by the current runtime;
- save the runtime/checkpoint state needed for a clean restart;
- save the release-state file;
- record cryptographic digests for those artifacts;
- end this process/session permanently.

Do not request or attempt to reveal any cursor beyond 13.
