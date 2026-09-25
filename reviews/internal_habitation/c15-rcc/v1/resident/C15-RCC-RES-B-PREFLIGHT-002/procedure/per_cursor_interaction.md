# C15-RCC-RES-B-PREFLIGHT-002 — Per-Cursor Interaction Procedure (CORRECTIVE-011 exact mirror)

This document is an exact operational mirror/reference of `procedure/b_startup_procedure.md §7`.
**`b_startup_procedure.md §7` is the single authoritative Phase-B cursor lifecycle.**
If any wording, executable snippet, or lifecycle token here diverges from startup §7, execution MUST STOP until the two documents are resynchronized. This file is not an independent second authority.

The frozen production path remains `ProductionResidentHandler + ExternalBrokerClient + resident_wire_protocol.json`.
No Core, fixture, evaluator, governance, or Resident semantics are changed here.

## Machine-readable lifecycle contract

Both active runbooks carry this exact token block. `checks/runbook_lifecycle_checker.py` parses both blocks, requires the exact ordered sequence, and mutation-tests the historical receipt-before-current-event ordering.

<!-- C15_PHASE_B_LIFECYCLE_BEGIN -->
REVEAL
INSTALL_CURRENT_EVENT
PERSIST_PROJECTION_EVIDENCE
CREATE_BINDING_RECEIPT
VERIFY_BINDING
DERIVE_OCCURRED_AT
INGEST
MODEL_WORK
FINISH_CURSOR_MODEL_WORK
DURABLE_ACK
CLEAR_BINDING
NEXT_REVEAL
<!-- C15_PHASE_B_LIFECYCLE_END -->

## Fixed invariants

- Phase B advances exactly one cursor per iteration, sequences `14..22`.
- Only the current 8-field reveal projection may become `current-event.json`; future cursors, Phase C, sealed fixture internals, evaluator material, governance, and A transcript remain unavailable to the Resident/model.
- Every production model invocation requires a live current event + immutable binding receipt. `event=None` is an unconditional STOP with zero provider calls for conversation, periodic review, background/mechanical wake, summary, and capability follow-up paths.
- The writer lock is always `$RUN_ROOT/runtime/world.sqlite.writer.lock`.
- `provider/model/request_id` come from broker provenance or literal `UNKNOWN`.
- Usage is never synthesized. A provider-reported `total_tokens` is required before a `ModelUsage` object can exist. Missing total, invalid values, or inconsistent `total < input + output` produce `usage=None`; missing input/output fields remain missing when total is valid.
- Scheme A remains hard-stop: poison handler, clear outstanding state before evidence I/O, emit collision-safe durable evidence, reconstruct, and retry from the same durable cursor. No semantic repair hint is generated.

## Exact 12-step mirror of startup §7

For each cursor, perform these steps in this order only.

### 1. REVEAL

Operator-only, outside the Resident jail:

```bash
python3 reviews/internal_habitation/c15-rcc/v1/release/release_operator.py \
  reveal --phase B --state "$RUN_ROOT/runtime/release_state.json" > "$RUN_ROOT/reveal.json"
```

Exactly one reveal is legal before ACK. `reveal.json` is the only source of the current projection.

### 2. INSTALL_CURRENT_EVENT

Install the exact reveal bytes before creating any binding receipt:

```bash
install -m 0400 "$RUN_ROOT/reveal.json" "$RUN_ROOT/current-event.json"
```

Set/retain:

```bash
export AIOS_CURRENT_EVENT_PATH="$RUN_ROOT/current-event.json"
export AIOS_RELEASE_STATE_PATH="$RUN_ROOT/runtime/release_state.json"
export AIOS_CURRENT_EVENT_BINDING_PATH="$RUN_ROOT/binding/current-event-binding.json"
```

The production handler refreshes this file on every call.

### 3. PERSIST_PROJECTION_EVIDENCE

Persist the immutable per-cursor projection and digest before receipt creation:

```bash
SEQ="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sequence"])' "$RUN_ROOT/current-event.json")"
install -m 0400 "$RUN_ROOT/current-event.json" "$RUN_ROOT/evidence/event-$(printf '%03d' "$SEQ").projection.json"
sha256sum "$RUN_ROOT/evidence/event-$(printf '%03d' "$SEQ").projection.json" >> "$RUN_ROOT/evidence/projection_digests.sha256"
```

After Phase B this yields exactly `event-014.projection.json` through `event-022.projection.json`, with contiguous sequences and unique event IDs.

### 4. CREATE_BINDING_RECEIPT

Only after steps 1–3, create the immutable receipt from the exact installed projection and live release state:

```bash
mkdir -p "$RUN_ROOT/binding"
PYTHONPATH="$PYTHONPATH" python3 - <<'PY'
import json, os, sys
from pathlib import Path
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[1])
from bridged_model_handler import create_current_event_binding_receipt, write_binding_receipt
projection = json.loads(Path(os.environ["AIOS_CURRENT_EVENT_PATH"]).read_bytes())
receipt = create_current_event_binding_receipt(
    projection,
    b_session_id=os.environ["AIOS_B_SESSION_ID"],
    release_state_path=os.environ["AIOS_RELEASE_STATE_PATH"],
)
write_binding_receipt(receipt, os.environ["AIOS_CURRENT_EVENT_BINDING_PATH"])
print("BINDING_RECEIPT_WRITTEN seq=%s event_id=%s" % (receipt["sequence"], receipt["event_id"]))
PY
chmod 0400 "$RUN_ROOT/binding/current-event-binding.json"
```

Receipt creation fails closed unless the live release state and `pending_reveal` bind to the same sequence/event/fixture.

### 5. VERIFY_BINDING

```bash
PYTHONPATH="$PYTHONPATH" python3 - <<'PY'
import json, os, sys
from pathlib import Path
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[1])
from bridged_model_handler import validate_current_event_binding
event = json.loads(Path(os.environ["AIOS_CURRENT_EVENT_PATH"]).read_bytes())
validate_current_event_binding(
    event,
    os.environ["AIOS_B_SESSION_ID"],
    release_state_path=os.environ["AIOS_RELEASE_STATE_PATH"],
    binding_receipt_path=os.environ["AIOS_CURRENT_EVENT_BINDING_PATH"],
)
print("CURRENT_EVENT_BINDING_VERIFIED", event["sequence"], event["event_id"])
PY
```

Wrong sequence/event/payload/source metadata/session, stale post-ACK state, missing receipt, malformed receipt, missing release state, or modified event all STOP before provider invocation.

### 6. DERIVE_OCCURRED_AT

Derive time only after reveal and binding installation:

```bash
CURRENT_OCCURRED_AT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["occurred_at"])' "$RUN_ROOT/current-event.json")"
[ -n "$CURRENT_OCCURRED_AT" ] || { echo "STOP: cannot derive CURRENT_OCCURRED_AT"; exit 1; }
export CURRENT_OCCURRED_AT
```

Never pre-read or hardcode cursor time.

### 7. INGEST

```bash
SK="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["source_kind"])' "$RUN_ROOT/current-event.json")"
if [ "$SK" = "conversation" ]; then
  python3 reviews/internal_habitation/c15-rcc/v1/release/canonical_conversation_ingest.py \
    --world-db "$RUN_ROOT/runtime/world.sqlite" \
    --session-id "$B_SESSION" \
    --turn-index 1 \
    --event-file "$RUN_ROOT/current-event.json"
else
  python3 reviews/internal_habitation/c15-rcc/v1/release/mechanical_ingest_adapter.py \
    --world-db "$RUN_ROOT/runtime/world.sqlite" \
    --event-file "$RUN_ROOT/current-event.json"
fi
```

### 8. MODEL_WORK

Run the production headless turn and all associated model/capability/due/review work while the same event + receipt remain live:

```bash
python3 -m aios_core.headless.cli \
  --world "$RUN_ROOT/runtime/world.sqlite" \
  --index "$RUN_ROOT/runtime/index.sqlite" \
  --lock "$RUN_ROOT/runtime/world.sqlite.writer.lock" \
  --model-handler bridged_model_handler:headless_production_handler \
  turn --session "$B_SESSION" --turn-index 1 --text "..." --at "$CURRENT_OCCURRED_AT"
```

Periodic review rounds, background/mechanical wakes, summary rounds, and capability follow-ups are not exemptions. If the current event is absent, all of them STOP with zero provider calls.

Production reply translation rules for usage are exact:
- `20/22/42` -> `ModelUsage(total=42,input=20,output=22)`;
- total 42 with only one optional component -> preserve the reported fields without filling the missing component;
- missing `total_tokens`, even with input/output present -> `usage=None`;
- invalid negative/bool/string token values -> `usage=None`;
- `total < input + output` -> `usage=None`.

### 9. FINISH_CURSOR_MODEL_WORK

Do not ACK until every model round, capability follow-up, due unit, periodic review, background wake, and summary unit attributable to this cursor has completed successfully.

On Scheme-A failure:
1. handler is poisoned;
2. `_outstanding` is cleared before evidence I/O;
3. collision-safe `failure-*.json` evidence uses `time_ns + nonce + O_CREAT|O_EXCL`;
4. evidence-write failure remains explicit and cannot leave outstanding protocol state;
5. reconstruct the handler and re-enter from the same durable release cursor.

### 10. DURABLE_ACK

```bash
python3 reviews/internal_habitation/c15-rcc/v1/release/release_operator.py \
  ack --phase B --state "$RUN_ROOT/runtime/release_state.json" \
  --world-db "$RUN_ROOT/runtime/world.sqlite" \
  --sequence "$SEQ" \
  --event-id "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["event_id"])' "$RUN_ROOT/current-event.json")" \
  --ingest-ref "$RUN_ROOT/evidence/event-$(printf '%03d' "$SEQ").projection.json" \
  --conversation-session-id "$B_SESSION" --conversation-turn-index 1
```

ACK must advance `next_sequence` and return `pending_reveal` to null.

### 11. CLEAR_BINDING

Only after durable ACK and completion of cursor-associated model work:

```bash
rm -f "$RUN_ROOT/current-event.json" "$RUN_ROOT/binding/current-event-binding.json"
```

### 12. NEXT_REVEAL

Before any later model invocation, loop back to step 1 and reveal/install the next legal cursor. No unbound wake window exists: a model dispatch attempted between step 11 and the next completed step 2 must fail closed, poison the handler, write durable evidence, and perform zero provider invocations.

## Provider boundary / reply validation

The provider sees only `contract + wire protocol + Resident-safe envelope`. `ExternalBrokerClient` is transport-only and production HTTPS-only; loopback is direct-constructor test-only.

Every provider reply must pass:
- strict per-action schema;
- exact round/request_id/request_digest binding;
- capability membership in the current snapshot catalog;
- broker provenance mapping;
- raw usage no-synthesis rules above.

Any provider exception, non-JSON, schema failure, binding failure, invalid capability, missing live release state, missing event, or evidence failure remains fail closed.

## Forbidden actions

- Do not reveal or buffer `seq+1` before the current cursor is durably ACKed.
- Do not expose fixture/evaluator/governance/A transcript/mailbox archive to Resident/model.
- Do not modify `src/aios_core/**`, fixture, evaluator, governance, or PR #205.
- Do not swap the pinned adapter/wire/contract at runtime.
- Do not run Resident B/C during preflight.
- Do not merge PR #209 from this procedure.

## Mechanical regression

Before B release, both of these must pass from the B-preflight root:

```bash
python3 checks/runbook_lifecycle_checker.py --base . --self-test
bash isolation/probe_e2e.sh
```

Required markers include:
- `CANONICAL_RUNBOOK_ORDER_PASS`
- `RUNBOOK_CROSS_DOCUMENT_ORDER_PASS`
- `RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS`
- `RAW_USAGE_NO_SYNTHESIS_PASS`
- `CORRECTIVE_011_E2E_PASS`
