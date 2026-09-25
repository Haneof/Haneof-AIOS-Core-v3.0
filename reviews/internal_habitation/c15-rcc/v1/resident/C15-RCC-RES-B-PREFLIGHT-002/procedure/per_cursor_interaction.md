# C15-RCC-RES-B-PREFLIGHT-002 — Per-Cursor Interaction Procedure (B)

Phase B covers cursors 14..22. The exact sequence/event mapping is sealed in the fixture and is **not inspected during preflight**. The operator discovers each event only by calling `reveal` for the current sequence; cursor 14 is NOT revealed during preflight.

## Single-cursor loop

For each sequence `s` in 14..22:

### Step 1: Reveal one event (operator only, outside sandbox)

```bash
python3 reviews/internal_habitation/c15-rcc/v1/release/release_operator.py \
  reveal --phase B --state $RUN_ROOT/runtime/release_state.json \
  > $RUN_ROOT/evidence/event-${s}.projection.json
```

This reads the sealed fixture internally and emits ONLY the 8-field resident-visible projection:

- event_id
- sequence
- occurred_at
- dimension
- source_kind
- source_class
- modality
- resident_visible_payload

The projection file must be saved in `$RUN_ROOT/evidence/` as a permanent record.

### Step 2: Classify the event and ingest

Case A: USER conversation event (`dimension=conversation`, `source_kind=conversation`, `source_class=user`, `modality=text`):

1. Run `canonical_conversation_ingest.py` to persist the conversation envelope and obtain the canonical Observation ID.
2. Invoke `aios-core-headless turn` with the exact `--session $B_SESSION --turn-index <n> --text <text> --at <occurred_at>`; this MUST reuse the same Observation ID idempotently (no duplicate user Observation). The turn runtime calls the model handler which transports the RuntimeSnapshot + event into the sandbox and returns the Resident directive.

Case B: mechanical non-conversation event (e.g. platform/release events):

1. Run `mechanical_ingest_adapter.py` to ingest the fact without model cognition; this produces an external-ingest receipt.
2. ACK the event via the release operator (binding the exact durable ref/world revision/sequence).
3. Run `aios-core-headless due --at <event-time>` to process bounded Wake/Review/Summary work due at or after this timestamp; this may invoke the Resident model multiple times (each round through the mailbox bridge).

### Step 3: Acknowledge and verify release-state

After the cursor's durable write + due-work complete, the release operator's ack step updates `release_state.json`:

- `last_acked_sequence = s`
- `last_acked_event_id = <event_id>`
- `next_sequence = s + 1`
- `pending_reveal = null`
- append a receipt entry binding fixture payload/projection digests to the durable ingest ref and world revision

If ack fails (wrong world revision, digest mismatch, wrong phase), STOP — fail closed, do not proceed to the next cursor. Enter reconciliation per Core recovery semantics; do not fake or paper over the failure.

### Step 4: Record evidence

Save in `$RUN_ROOT/evidence/`:

- the 8-field event projection (already saved in step 1)
- the ingest receipt
- any mailbox request/reply JSON files for the cursor (archived by mailbox_bridge)
- the capability call results/errors for the cursor
- the headless CLI JSON output (turn or due result)
- wake/review/summary records produced during due-processing
- post-cursor World revision / index watermark

### Step 5: Loop

Proceed to s+1.

## B-specific invariants

- Fresh B model context started at cursor 14 initialization; carried forward WITHIN B only.
- Session ID stays constant (`$B_SESSION`) for all B USER turns.
- Turn indices for B USER turns are monotonic 1..N within the B session (do NOT reset across phases — the canonical ingest uses turn_index as recorded in the fixture).
- No prefetch: never call `reveal` for s+1 until s is durably ACKed and due work for s has completed.
- No second user Observation for the same turn: `run_turn` must reuse the canonical Observation ID; the headless CLI + canonical_conversation_ingest already enforce this per CORE-OPERATOR-001 acceptance.
- Wake/Summary/Review processing uses the existing Core runtime — do not build a second cognition engine.
- Mailbox pauses on every genuine model request: the bridge blocks on outbox; there is no keyword default. If the Resident returns malformed JSON, re-present the same snapshot (same inbox round, same event projection) for a repair round; record both attempts.
- The operator transports bytes; it does not decide which Claim to write, what entity to use, whether to remain silent, or what the Summary should say.

## Forbidden actions during B run

- Do NOT open fixture/sealed_fixture.json inside the sandbox.
- Do NOT read or quote A-002 mailbox archive, A operator log, A acceptance report, this preflight report, or the task board to the Resident.
- Do NOT reveal cursor 23.
- Do NOT modify #205, Core source, constitution, or RC packet files.
- Do NOT invoke Core recovery commands (backup/restore/rebuild-index) mid-phase unless an actual IN_DOUBT failure occurs — and only per Core recovery procedure.
- Do NOT treat silence as a failure; legal Resident silence is permitted. The operator must still record the silence and continue processing.
