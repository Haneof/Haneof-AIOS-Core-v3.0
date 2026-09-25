# C15-RCC-RES-B-PREFLIGHT-002 — Per-Cursor Interaction Procedure (CORRECTIVE-005 Scheme A-hard-stop (`_poisoned` + durable `$RUN_ROOT/evidence/failure-*.json`))

This is the exact per-cursor loop that B will run under the frozen `ProductionResidentHandler` + `ExternalBrokerClient` + `resident_wire_protocol.json` (`a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a…`).

Scheme A-hard-stop (`_poisoned` + durable `$RUN_ROOT/evidence/failure-*.json`) — any provider transport, non-JSON, schema, binding failure → fail current runtime, do not advance cursor, save failure evidence, terminate/reconstruct handler, re-enter from same durable sequence/state with new binding, never generate semantic repair hint. No same-handler retry.

## Invariants

- Phase B advances exactly one cursor per iteration (`14→22`, 9 steps).
- Each iteration reveals **only** current 8-field projection to Resident. Future cursors, Phase C, fixture, evaluator, governance, A transcript remain sealed.
- Resident model sees exactly `contract + envelope JSON + wire_protocol schema` (no file path).
- Non-conversation cursors still go through same envelope→provider→validate chain (mechanical wake).
- `PYTHONPATH` frozen `src:reviews/.../harness`, `AIOS_PROVIDER_ADAPTER=bridged_model_handler:ExternalBrokerClient`, exact env pinned; mismatch → STOP.
- Each cursor's `current_event` bound to **exact** release cursor (session, sequence, event_id, payload digest, pending state).


### Binding receipt (operator side, immutable)

Immediately after `release_operator reveal` (capturing exact stdout bytes), operator creates immutable binding receipt:

```bash
# Capture exact reveal stdout (8-field projection)
python3 reviews/internal_habitation/c15-rcc/v1/release/release_operator.py reveal --state $RUN_ROOT/runtime/release_state.json --sequence $SEQ > $RUN_ROOT/reveal.json

# Compute canonical SHA and create receipt via harness helper
python3 -c "
from pathlib import Path
import json, sys
sys.path.insert(0, 'reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/harness')
from bridged_model_handler import create_current_event_binding_receipt, write_binding_receipt
proj = json.loads(Path('$RUN_ROOT/reveal.json').read_bytes())
receipt = create_current_event_binding_receipt(proj, b_session_id='$B_SESSION', release_state_path='$RUN_ROOT/runtime/release_state.json')
write_binding_receipt(receipt, '$RUN_ROOT/binding/current-event-binding.json')
"

# Also copy reveal to current-event.json for handler
cp $RUN_ROOT/reveal.json $RUN_ROOT/current-event.json
chmod 0400 $RUN_ROOT/binding/current-event-binding.json
chmod 0400 $RUN_ROOT/current-event.json
```

Receipt contains: `phase B`, `b_session_id`, `sequence`, `event_id`, `occurred_at`, `source_kind/class/modality/dimension`, `canonical_projection_sha256`, `resident_visible_payload_sha256`, `release_state_path/sha/next_sequence/pending`, `fixture_sha256`, `reveal_timestamp`, `operator_request_id`, `binding_version`.

Handler validates `current-event.json` against `current-event-binding.json` + `release_state` on every call; mismatches fail closed (11 negatives: seq15, wrong id, modified text/dimension/source_kind/modality/occurred_at, wrong session, stale after ACK, missing/malformed receipt).


## Per-cursor lifecycle (operator side, outside jail)

For `seq` from `14` to `22`:

### 1. Reveal (operator only, outside jail)

Operator reads next sealed cursor outside jail and writes **only** 8-field projection to `$RUN_ROOT/current-event.json` and sets `AIOS_CURRENT_EVENT_PATH=$RUN_ROOT/current-event.json` and `AIOS_RELEASE_STATE_PATH=$RUN_ROOT/runtime/release_state.json`:

```
{
  event_id:             <fixture event_id for seq>,
  sequence:             <seq>,
  occurred_at:          <fixture occurred_at>,
  dimension:            <fixture dimension>,
  source_kind:          conversation|mechanical,  # validated
  source_class:         <fixture>,
  modality:             <fixture>,
  resident_visible_payload: { ... }  # non-empty object, validated
}
```

Validation before envelope (fail closed, no file written if envelope would fail, round not advanced):
- Exactly 8 keys, `sequence 14..22`, `source_kind conversation|mechanical`, payload non-empty object, `event_id/occurred_at/dimension/source_class/modality` non-empty strings.
- **Exact binding** to current release cursor (via `validate_current_event_binding`):
  - `current_event.sequence == release_state.next_sequence` (expected=14 → seq15 rejected)
  - `current_event.event_id == expected event_id` (at seq14, another id rejected)
  - `payload digest == expected digest` (`sha256(canonical JSON payload)`; modified payload rejected)
  - `release_state pending_reveal` if present must match (stale previous event after ACK → pending null but next 15, so seq14 stale rejected)
  - `B session` consistency (event is for this `b_session`)
  - File digest must equal in-memory event (file vs object mismatch rejected)
  - Missing file on event-driven turn → fail closed
  - Malformed JSON → fail closed (`except Exception: pass` forbidden, must raise)

No other cursor read; no future `seq+1` buffered.

### 2. Build envelope (mechanical, `build_envelope`)

- `snapshot = FusedTurnRuntime.capture()` (real Core).
- `current_event =` file content at `AIOS_CURRENT_EVENT_PATH` (refreshed per call, not cached at handler init; `headless_production_handler` re-reads file on every `__call__` if handler already exists, and clears after cursor ACK).
- `envelope = build_envelope(snapshot,b_session,contract_sha,current_event,release_state_path)` → `phase B`, `allowed_sequences [14,22]`, `runtime_snapshot`, `capability_catalog`, `capability_history` (B-session only), `wake_reason`, `contract_sha`, `wire_protocol_sha`.
- Binding `round/request_id/request_digest` assigned (incremental, 32-hex nonce, canonical digest).
- Envelope validated by `validate_envelope` (B-session only, path-aware guard, `source_kind` check).

`AIOS_CURRENT_EVENT_PATH` missing/invalid → `ModelDispatchNotSubmitted` (fail closed).

### 3. Invoke model (production, outside jail)

```
request = build_model_request(contract_text,envelope,wire_protocol_text)
        = {system: <RESIDENT_B_RUN_CONTRACT.md>, wire_protocol: <resident_wire_protocol.json>, wire_protocol_sha256: a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a…, messages: [{role:user, content: JSON(envelope)}]}
provider_resp = ExternalBrokerClient.invoke(request)  # requires AIOS_REAL_PROVIDER_API_KEY+ENDPOINT, adapter pinned, Fake forbidden
content = provider_resp.content  # JSON string/dict of reply with round/request_id/request_digest/action
reply = JSON.parse(content)
```

Provider sees `contract+envelope+wire_protocol` (proven via `ExternalBrokerClient.last_request` contains all three, no `/repo/fixture`).

### 4. Validate reply (fail closed, Scheme A-hard-stop (`_poisoned` + durable `$RUN_ROOT/evidence/failure-*.json`))

```
validate_reply(reply)  # capability string only, handler checks `capability in snapshot.capability_catalog`  # strict per-action allowlist
verify_binding(reply)  # round/id/digest == outstanding; stale/preplay/replay/wrong fail
```

- `action` in `invoke_capability|end_turn|silence|summary_response`; `round_repair_request` unsupported → `ValueError` fail closed.
- `silence` allowlist only `round,id,digest,action`; extra `capability` → fail.
- On any `provider exception / non-JSON / schema invalid / binding invalid`:
  1. `ProductionResidentHandler._clear_outstanding_on_failure(reason)` clears `_outstanding`, appends to `_failure_evidence`, **do not** advance release cursor;
  2. Save evidence to `$RUN_ROOT/evidence/failure-round-*.json`;
  3. Terminate/reconstruct handler (`_reset_global()` + new `ProductionResidentHandler` with same `b_session` and `release_state_path`);
  4. Re-enter from same `next_sequence`/durable state;
  5. Next request has new `round/request_id/request_digest` (proven `new round != old`);
  6. Never generate semantic repair hint.

`_assign_binding` leaves `_outstanding` only on success; on failure it is cleared, so next call does **not** hit `cannot send while outstanding`.

### 5. Dispatch capability or end turn

- `directive = reply_to_directive_production(reply,snap,provider_resp)` maps `action` → `ModelDirective` with **RAW provenance** (`provider/model/request_id` actual or `UNKNOWN`, `usage` raw preserved: inconsistent `total<input+output` → `usage None` not rewritten).
- `FusedTurnRuntime` executes `capability_calls`, appends to `capability_history`, then **same cursor** follow-up: next `__call__` re-uses **same** `current_event` (not next cursor) with updated `capability_history` (contains `Atlas` legal `obs_c14_fixture_*`), same adapter/binding new round, until `silence/end_turn`.
- If first round `silence/end_turn`, cursor considered complete → operator ACKs via `release_operator.py ack`, `next_sequence` increments, **clear** `current-event.json` (unlink or overwrite) and set new `AIOS_CURRENT_EVENT_PATH` for next seq; handler's next call will load new event (stale seq14 file now rejected because `next_sequence` is 15).

## Forbidden actions

- Do not read `seq+1` or Phase C.
- Do not modify `src/aios_core` (frozen `fe77f8a`).
- Do not swap `bridged_model_handler.py` or `resident_wire_protocol.json` at runtime (hash pinned).
- Do not expose `mailbox/archive`, A transcript, fixture, governance to Resident.
- Do not advance cursor on failure; do not retry with same handler without reconstruction.
- Do not swallow `except Exception: pass` after event file load — must fail closed.

## Probes (disposable, synthetic event `synthetic-fixture-seq-14` seq14 + adversarial)

- Positive seq14 exact event → accept, second round `Atlas` non-empty legal survives.
- Negatives: `seq13/23`, extra field, missing field, `phase A`, `source_kind` invalid, payload empty, seq15 when expected 14, wrong event_id, modified payload digest, stale after ACK, missing file, malformed JSON — all rejected.
- Strict reply `silence{capability}` rejected, `round_repair_request` unsupported, provider exception→cursor not advanced + new binding, non-JSON→fail, wrong binding→fail, inconsistent tokens→`usage None`, env mismatch→STOP, PID1→worker signal chain proven, exact check count gate `CHECKS==EXPECTED`.
