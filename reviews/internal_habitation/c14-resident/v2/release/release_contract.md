# C14 Resident Sequential Release Contract v2 — Durable Ack Amendment

> Contract identity: `c14-sequential-release-v2`  
> Durable-ack amendment task: `C14-RES-FIX-003`  
> Fixture: `c14-resident-fixture-v2`  
> Frozen fixture SHA256: `sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253`  
> Release operator: `c14-blind-release-operator-v3`  
> Mechanical ingest adapter: `c14-mechanical-ingest-adapter-v1`  
> Binding: `c14-fixture-event-binding-v1`  
> Timezone: `America/Los_Angeles`

The contract identity remains v2 because the sealed fixture embeds `c14-sequential-release-v2` and its bytes are constitutionally frozen for this validation. FIX-003 strengthens only the release/ingest proof. It does not alter any life event, phase, timestamp, semantic design, or fixture digest.

## 1. Resident access boundary

Resident A/B may read and execute:

- this contract;
- `event_schema.json`;
- `release_operator.py`;
- `mechanical_ingest_adapter.py`;
- their own durable release state/receipts;
- the single current event projection emitted by `reveal`;
- the mechanical ingest receipt for that current event.

Resident A/B must not open or read:

- `../fixture/sealed_fixture.json`;
- `../fixture/fixture_manifest.json`;
- `../evaluator/EVALUATOR_ONLY_design_notes.md`;
- any unreleased future event or hidden evaluator/design material.

The release operator may read the sealed fixture internally only to select and validate the exact current cursor. The ingest adapter does **not** read the sealed fixture; it accepts only the already-released projection.

## 2. Required private World

Every formal Resident run uses one private SQLite AIOS World.

The World path is supplied explicitly as:

`--world-db <private-world.db>`

The durable truth queried by ack is the existing AIOS `SQLiteWorldStore`. No sidecar registry, fake receipt database, or second source of truth is legal.

The exact revision is verified through the public WorldStore read surfaces:

- `object_revision_record(object_id, revision=N)`;
- `get_payload(object_id, revision=N)`.

The first read proves exact durable revision/provenance existence; the second retrieves the exact persisted payload.

## 3. Phase-A initialization

Initialize one release state:

```bash
python reviews/internal_habitation/c14-resident/v2/release/release_operator.py \
  init --phase A --state <release-state.json>
```

Phase A always begins at cursor 1.

## 4. Reveal exactly one current event

```bash
python reviews/internal_habitation/c14-resident/v2/release/release_operator.py \
  reveal --phase A --state <release-state.json> \
  > <current-event.json>
```

`reveal` outputs exactly:

- `event_id`
- `sequence`
- `occurred_at`
- `dimension`
- `source_kind`
- `source_class`
- `modality`
- `resident_visible_payload`

It does not output hidden `phase`, manifest content, evaluator content, future payload, remaining-event information, or semantic labels.

It records only a pending reveal. **It does not advance the cursor.**

## 5. Mechanical ingest of the released projection

Only after reveal, mechanically ingest that same projection into the current private World:

```bash
python reviews/internal_habitation/c14-resident/v2/release/mechanical_ingest_adapter.py \
  --world-db <private-world.db> \
  --event-file <current-event.json> \
  > <ingest-receipt.json>
```

The adapter performs no cognition, search, Summary interpretation, importance ranking, preference detection, Claim selection, revision, retraction, or silence decision.

It creates one durable AIOS `Observation` using the existing:

- `Observation` contract;
- `OperationRequest`;
- `SQLiteWorldStore.commit`.

The adapter stores mechanical fixture-binding metadata only:

- fixture version and frozen digest;
- fixture event id;
- fixture sequence;
- deterministic payload SHA256;
- deterministic current-projection SHA256;
- dimension;
- original occurred_at;
- external record identity;
- mechanical-ingest marker.

The actual source authority is committed through the WorldStore `source_class`; ack later reads it from the exact revision's `world_commits` provenance instead of trusting a caller string.

## 6. Durable ack

Ack now requires both the exact ingest ref and the private World:

```bash
python reviews/internal_habitation/c14-resident/v2/release/release_operator.py \
  ack \
  --phase A \
  --state <release-state.json> \
  --world-db <private-world.db> \
  --sequence <N> \
  --event-id <EVENT_ID> \
  --ingest-ref <OBJECT_ID>@<REVISION>
```

Before cursor movement, ack itself reopens/queries the durable World and requires all of the following:

1. exact `object_id@revision` exists;
2. object type is `Observation`;
3. revision kind is content;
4. durable revision subject equals fixture subject `user_1`;
5. payload subject equals the same subject;
6. exact payload object id/revision equal the supplied ref;
7. commit provenance `source_class` equals the released event's source class;
8. stored `source_kind` equals the released event;
9. stored modality equals the released event;
10. stored value exactly equals `resident_visible_payload`;
11. stored point timestamp equals the released `occurred_at` instant;
12. metadata dimension equals the released dimension;
13. metadata fixture event id equals the pending event id;
14. metadata fixture sequence equals the pending sequence;
15. fixture version/digest/binding version match the frozen v2 contract;
16. deterministic payload SHA256 matches;
17. deterministic projection SHA256 matches;
18. original occurred_at metadata matches exactly;
19. mechanical-ingest marker is present.

No semantic similarity, NLP, model judgment, or fuzzy matching is used.

If any equality fails, stdout contains no ack success and the cursor/pending reveal stay unchanged.

## 7. Receipt chain

A successful ack persists a receipt containing at least:

- `fixture_sha256`;
- `event_id`;
- `sequence`;
- `occurred_at`;
- `ingest_ref`;
- `ingest_object_id`;
- `ingest_revision`;
- `ingest_world_revision`;
- durable commit `ingest_source_class`;
- `fixture_payload_sha256`;
- `fixture_projection_sha256`.

This permits a later evaluator to follow:

`release receipt -> exact World revision -> original released event`.

## 8. Fail-closed conditions

Ack refuses, without cursor advancement:

- missing private World DB;
- syntactically valid but nonexistent ref such as `fake_object@1`;
- nonexistent revision of a real object;
- wrong existing revision;
- previous-event ref;
- another/future fixture-event ref;
- cross-subject Observation;
- payload mismatch;
- timestamp mismatch;
- dimension mismatch;
- source-kind mismatch;
- source-class mismatch;
- modality mismatch;
- fixture/binding/version/digest mismatch;
- ack before reveal;
- wrong sequence/event id;
- skip/repeat/reorder;
- malformed state/receipt chain.

All previous future-isolation and phase guards remain binding.

## 9. Phase-A sealed handoff

Phase A is cursors **1 through 24**.

Cursor 24:

- event id: `c14resv2-024`;
- occurred_at: `2026-10-21T11:53:00-07:00`.

Only after cursor 24 has a verified exact durable World revision may ack advance state to:

`next_sequence = 25`.

Resident A then saves the required World/checkpoint/index/model/capability evidence and stops permanently.

Phase A `reveal` at cursor 25 is rejected.

## 10. Phase-B start

Resident B must be a completely new ChatGPT/Agent window and must receive no Phase-A chat transcript or prose memory.

Phase B initializes only from the exact sealed handoff state:

```bash
python reviews/internal_habitation/c14-resident/v2/release/release_operator.py \
  init --phase B --state <release-state.json>
```

It succeeds only after cursor 24 was acknowledged and cursor 25 is next.

Phase B then continues the same:

`reveal -> mechanical ingest -> durable World verified ack`

discipline from cursor 25 onward.

## 11. No semantic verdict in release infrastructure

Successful release/ingest/ack means only that chronological test input was durably persisted and mechanically bound.

It is **not** evidence that the Resident formed correct cognition.

Semantic validity remains exclusively with the later real Resident and independent evaluator tasks.
