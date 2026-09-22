# C14 Semantic Repair Sequential Release Contract v1

> Task: `C14-SEM-REPAIR-FIX-001`  
> Fixture: `c14-semantic-repair-fixture-v1`  
> Fixture SHA256: `sha256:1095d5aef52061753db7d9dab558af1361b92976f2ded0e6956d70afe3e6527f`  
> Contract: `c14-semantic-repair-sequential-release-v1`  
> Phase R-A: cursors 1..6  
> Phase R-B: cursors 7..15  
> Timezone: `America/Los_Angeles`

## 1. Scope

This contract releases only the replacement life evidence needed to re-evaluate C14 E1 and E5.

It does not replace, edit, reinterpret, or append to historical Resident A/B evidence. It does not retest E2, E3, E4, or E6.

The Resident model is the only component allowed to make semantic judgments. Infrastructure may reveal, ingest, acknowledge, persist, restore, and audit bytes and mechanical bindings only.

## 2. Resident access boundary

A formal Resident repair run may read:

- this release contract;
- `event_schema.json`;
- `release_operator.py`;
- `mechanical_ingest_adapter.py`;
- `canonical_conversation_ingest.py`;
- its private release state and receipts;
- the single current event projection emitted by `reveal`;
- the current AIOS RuntimeSnapshot and legal capabilities;
- durable AIOS World state already released and ingested.

A formal Resident repair run must not read:

- `../fixture/sealed_fixture.json`;
- `../fixture/fixture_manifest.json`;
- `../evaluator/EVALUATOR_ONLY_design_notes.md`;
- this task's completion evidence before the run;
- any unreleased future event;
- any evaluator expectation or hidden design material.

The release operator may read the sealed fixture internally only to validate and project the current cursor.

## 3. Reuse of frozen v2 release mechanics

The repair release scripts are thin bindings over the already accepted C14 v2 release machinery:

- durable SQLiteWorldStore exact-revision verification;
- reveal-without-advance;
- receipt-chain re-verification;
- canonical USER conversation verification;
- cursor/order/boundary fail-closed behavior.

The repair bindings change only fixture identity, digest, manifest path, version identifiers, and the 6/7 phase boundary.

They do not add semantic scoring, expected answers, Claim generation, evidence selection, revision logic, or hidden model directives.

## 4. Private World

Use one private AIOS SQLite World for the formal repair run.

Every acknowledgement requires `--world-db <private-world.db>` and is verified against the exact durable revision using the existing `SQLiteWorldStore` read surfaces.

A receipt string by itself is insufficient.

## 5. Phase R-A initialization and release

Initialize:

```bash
python reviews/internal_habitation/c14-resident/semantic-repair-v1/release/release_operator.py \
  init --phase A --state <release-state.json>
```

Reveal exactly one current event:

```bash
python reviews/internal_habitation/c14-resident/semantic-repair-v1/release/release_operator.py \
  reveal --phase A --state <release-state.json> > <current-event.json>
```

The reveal projection contains only:

- `event_id`
- `sequence`
- `occurred_at`
- `dimension`
- `source_kind`
- `source_class`
- `modality`
- `resident_visible_payload`

Reveal does not advance the cursor.

For non-conversation events, mechanically ingest the released projection:

```bash
python reviews/internal_habitation/c14-resident/semantic-repair-v1/release/mechanical_ingest_adapter.py \
  --world-db <private-world.db> --event-file <current-event.json>
```

Then acknowledge the exact durable ref:

```bash
python reviews/internal_habitation/c14-resident/semantic-repair-v1/release/release_operator.py \
  ack --phase A --state <release-state.json> --world-db <private-world.db> \
  --sequence <N> --event-id <event-id> --ingest-ref <object_id@revision>
```

Only a valid durable acknowledgement advances the cursor.

After cursor 6 is acknowledged, Phase A is sealed and cannot reveal cursor 7.

## 6. Phase R-B

Using the same release state after the exact 6 -> 7 boundary:

```bash
python reviews/internal_habitation/c14-resident/semantic-repair-v1/release/release_operator.py \
  init --phase B --state <release-state.json>
```

Continue one event at a time through cursor 15.

No cursor may be skipped or reordered.

## 7. Canonical USER conversation

Every repair event with:

- `dimension = dim:conversation`
- `source_kind = conversation`
- `source_class = USER`
- `modality = text`

must use the canonical conversation path. Generic mechanical ingest rejects this envelope.

Persist it with:

```bash
python reviews/internal_habitation/c14-resident/semantic-repair-v1/release/canonical_conversation_ingest.py \
  --world-db <private-world.db> \
  --session-id <resident-session-id> \
  --turn-index <positive-turn-index> \
  --event-file <current-event.json>
```

Then acknowledge with the matching session and turn fields:

```bash
python reviews/internal_habitation/c14-resident/semantic-repair-v1/release/release_operator.py \
  ack --phase B --state <release-state.json> --world-db <private-world.db> \
  --sequence <N> --event-id <event-id> --ingest-ref <object_id@revision> \
  --conversation-session-id <resident-session-id> \
  --conversation-turn-index <positive-turn-index>
```

If that user text is subsequently processed through ordinary `run_turn`, it must use the same subject/session/turn/text/time so the canonical user commit is idempotently reused rather than duplicated.

## 8. Semantic boundary

Infrastructure must not:

- infer what an event means;
- select evidence refs for the Resident;
- create or revise Claims;
- choose confidence;
- decide retain/weaken/retract;
- decide silence;
- map keywords to answers;
- expose evaluator-only notes or future events;
- pre-generate ModelDirectives.

Silence is a legal Resident result.

## 9. Fail-closed requirements

The release chain must reject:

- ack before reveal;
- wrong cursor;
- wrong event id;
- nonexistent or wrong durable ref/revision;
- duplicate ack;
- skip or reorder;
- Phase A access to cursor 7;
- Phase B access before the 6 -> 7 handoff;
- generic ingest of a repair USER conversation;
- missing/wrong canonical session or turn;
- fixture or manifest digest/version mismatch.

## 10. Stop condition

After cursor 15 is acknowledged, the fixture is complete.

This infrastructure task must not run the Resident. The next Resident repair task begins only after governance separately marks `C14-SEM-REPAIR-RES-001 = READY`.
