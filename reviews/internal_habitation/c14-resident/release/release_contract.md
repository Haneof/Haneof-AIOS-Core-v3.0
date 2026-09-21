# C14 Resident Sequential Release Contract

> Version: `c14-sequential-release-v1`  
> Task: `C14-RES-FIX-001`  
> Timezone: `America/Los_Angeles`  
> Purpose: release one natural life event at a time without exposing future events or evaluator-only design.

## 1. Access boundary

The Resident may read this contract and the event schema.

The Resident **must not read or open**:

- `fixture/sealed_fixture.json`;
- `fixture/fixture_manifest.json`;
- `evaluator/EVALUATOR_ONLY_design_notes.md`;
- any unreleased future event;
- any evaluator expectation or hidden design record.

A trusted mechanical Release Operator may read the sealed fixture solely to select the exact current cursor entry. The Release Operator is not a semantic model and must not choose cognition, search targets, claims, revisions, retractions, or responses.

If Resident A or Resident B reads any forbidden future/design material, the semantic run is INVALID.

## 2. Resident-visible event projection

For one released event, the Release Operator may expose exactly these fields:

- `event_id`
- `sequence`
- `occurred_at`
- `dimension`
- `source_kind`
- `source_class`
- `modality`
- `resident_visible_payload`

The orchestrator-only `phase` field is not part of the Resident-visible projection.

No batch listing, next-event preview, future count-by-content, hidden semantic tag, answer-key material, or future payload may be emitted.

## 3. Cursor state

A release receipt/checkpoint must persist at least:

```json
{
  "fixture_sha256": "sha256:a0f9dfd0985560ce80f568b6cd11d46b13f5dc352a664c005fcb165ea5a67485",
  "last_released_sequence": 0,
  "last_released_event_id": null,
  "next_sequence": 1
}
```

The cursor advances only after the current event has been durably ingested and its release receipt has been persisted.

## 4. Mechanical release algorithm

For cursor `N`:

1. Verify the sealed fixture SHA256 equals `sha256:a0f9dfd0985560ce80f568b6cd11d46b13f5dc352a664c005fcb165ea5a67485`.
2. Require `N == last_released_sequence + 1`.
3. Select exactly the fixture entry with `sequence == N`.
4. Verify its `occurred_at` is strictly later than the prior released event.
5. Emit only the Resident-visible projection from §2.
6. Ingest that one event into the current private AIOS World, preserving its stable event id, timestamp, dimension, source kind/class, modality, and payload.
7. Run only the normal mechanical AIOS scheduling/persistence steps permitted by the active Resident task.
8. Persist a release receipt containing `fixture_sha256`, `sequence`, `event_id`, and `occurred_at`.
9. Set `last_released_sequence=N` and `next_sequence=N+1`.

Programs may implement these mechanical steps. Programs may not inspect later events to influence current Resident behavior.

## 5. Phase A boundary

Resident A is allowed to release and process only sequences **1 through 24**.

The final Phase-A released event is mechanically fixed as:

- cursor: `24`
- event id: `c14res-024`
- occurred_at: `2026-10-20T18:20:00-07:00`

After sequence 24 is fully processed, Resident A must save its required World/checkpoint/index/model/capability evidence and stop permanently.

Resident A must not release sequence 25.

## 6. Phase B start

The first Phase-B event remains unreleased at the handoff:

- next cursor: `25`
- event id: `c14res-025`
- occurred_at: `2026-10-22T07:05:00-07:00`

Resident B must be a completely new ChatGPT/Agent window. It resumes from the durable Phase-A AIOS World/checkpoint and cursor 25 without receiving Phase-A chat text, Resident reasoning, prose memory, evaluator notes, or unreleased fixture contents.

Resident B may release and process sequences **25 through 36** sequentially.

## 7. Invalidation conditions

The run is INVALID if any of the following occurs:

- a Resident opens the sealed fixture, manifest, or evaluator-only notes;
- more than one unreleased event is exposed at a time;
- a future payload is previewed;
- sequence order is skipped, repeated, or reordered;
- the fixture digest differs from the frozen digest;
- a program decides semantic capability calls or cognition;
- Resident A crosses cursor 24;
- Resident B receives Phase-A chat/context instead of recovering through durable AIOS state.

## 8. Completion of release

The final event is cursor `36`, `c14res-036`, at `2026-10-29T18:40:00-07:00`.

Completion of release is only chronological completion of the sealed life input. It is not a cognition PASS. Semantic validity belongs to the independent `C14-RES-EVAL-001` task.
