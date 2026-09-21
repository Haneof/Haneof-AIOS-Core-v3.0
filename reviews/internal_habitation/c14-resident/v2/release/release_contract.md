# C14 Resident Sequential Release Contract v2

> Version: `c14-sequential-release-v2`  
> Task: `C14-RES-FIX-002`  
> Fixture: `c14-resident-fixture-v2`  
> Release operator: `c14-blind-release-operator-v2`  
> Timezone: `America/Los_Angeles`

This contract supersedes the v1 release contract for formal C14 Resident validation. The v1 files remain historical evidence and must not be used as the formal Resident input.

## 1. Resident access boundary

Resident A/B may read:

- this contract;
- `event_schema.json`;
- `release_operator.py`;
- their own durable release state/receipts;
- the current event projection printed by the operator.

Resident A/B must not open or read:

- `../fixture/sealed_fixture.json`;
- `../fixture/fixture_manifest.json`;
- `../evaluator/EVALUATOR_ONLY_design_notes.md`;
- any unreleased future event or hidden design material.

Formal fixture SHA256:

`sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253`

If a Resident reads forbidden fixture/design material directly, the affected semantic evidence is invalid.

## 2. Normal command flow

Initialize Phase A once:

```bash
python reviews/internal_habitation/c14-resident/v2/release/release_operator.py init --phase A --state <state-file>
```

Reveal exactly the current event:

```bash
python reviews/internal_habitation/c14-resident/v2/release/release_operator.py reveal --phase A --state <state-file>
```

The `reveal` command prints exactly these event fields and no others:

- `event_id`
- `sequence`
- `occurred_at`
- `dimension`
- `source_kind`
- `source_class`
- `modality`
- `resident_visible_payload`

It does **not** advance the cursor. It records only that the current cursor has been revealed and is awaiting durable ingest acknowledgement.

After that exact event has been durably ingested into the private AIOS World, acknowledge it:

```bash
python reviews/internal_habitation/c14-resident/v2/release/release_operator.py ack \
  --phase A \
  --state <state-file> \
  --sequence <N> \
  --event-id <EVENT_ID> \
  --ingest-ref <OBJECT_ID>@<REVISION>
```

Only a matching pending reveal with a non-empty durable `object_id@revision` reference may advance the cursor.

## 3. Fail-closed guarantees

The operator refuses:

- fixture digest mismatch;
- fixture / schema / contract / operator version mismatch;
- malformed or non-monotonic fixture chronology;
- duplicate ids or non-contiguous sequence;
- cursor skip or state corruption;
- acknowledgement of a non-current event;
- repeat acknowledgement;
- acknowledgement without a valid durable ingest reference;
- Phase A access to cursor 25;
- Phase B initialization before the exact 24 -> 25 handoff;
- Phase B access to Phase-A cursors;
- phase mismatch between command and durable state.

Errors go to stderr and emit no event payload on stdout.

The helper performs no NLP, semantic ranking, search-target selection, Claim selection, cognition generation, revise/retract decision, or Resident response generation.

## 4. Phase-A sealed handoff

Phase A is exactly cursors **1 through 24**.

The final Phase-A event is:

- cursor: `24`
- event id: `c14resv2-024`
- occurred_at: `2026-10-21T11:53:00-07:00`

After cursor 24 is durably ingested and acknowledged:

- `last_acked_sequence = 24`
- `next_sequence = 25`
- Resident A saves the required World/checkpoint/index/model/capability evidence;
- Resident A stops permanently;
- Resident A must not run another `reveal`.

## 5. Phase-B fresh-window start

Resident B must be a completely new ChatGPT/Agent window.

It receives only the legal task/protocol material, the Phase-A durable AIOS World/checkpoint and digests, and the durable release state at cursor 25. It receives no Phase-A chat transcript or prose summary.

Phase B is initialized against the existing handoff state:

```bash
python reviews/internal_habitation/c14-resident/v2/release/release_operator.py init --phase B --state <state-file>
```

That command succeeds only if the state proves cursor 24 was acknowledged and cursor 25 is next.

The first Phase-B reveal is then:

```bash
python reviews/internal_habitation/c14-resident/v2/release/release_operator.py reveal --phase B --state <state-file>
```

Phase B proceeds sequentially through cursor 36 with the same reveal -> durable ingest -> ack discipline.

## 6. Release completion

The final event is cursor `36`, `c14resv2-036`, at `2026-10-31T12:03:00-07:00`.

Chronological release completion is not a cognition verdict. Semantic evaluation remains the responsibility of the later independent evaluator window.
