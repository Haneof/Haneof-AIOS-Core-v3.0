# C15-RCC-RES-B-PREFLIGHT-002 — Per-Cursor Interaction Procedure (CORRECTIVE-003 Scheme A)

This is the exact per-cursor loop that B will run under the frozen `ProductionResidentHandler`.
Scheme A (fail closed, **no repair**) — `round_repair_request` is **not supported**; any repair-typed reply
fails closed as `ModelDispatchNotSubmitted` and the round is retried without incrementing sequence
(the operator does not inject a repair turn). This resolves the prior contradiction where docs said
"repair not supported" while harness accepted a repair action.

## Invariants

- Phase B advances **exactly one cursor per iteration** (`sequence` 14 → 22 inclusive, 9 steps).
- Each iteration reveals **only** the current 8-field projection to the Resident. Future cursors,
  Phase C (`23..30`), fixture, evaluator, governance, A transcript, PM report remain sealed.
- The Resident model sees **exactly** `contract text + Resident-safe envelope JSON` (no file path).
- Non-conversation cursors (`source_kind != conversation`) produce a mechanical wake reason
  and still go through the same envelope → provider → validate → dispatch chain.
- Environment inside the sandbox is fixed via `environment_manifest.md` (`PYTHONPATH=/repo/src`,
  `LD_*/PYTHON*/SUDO*/PROXY*` stripped, `PROBE_MODE/PROBE_ROUNDS` only when `AIOS_ALLOW_PROBE_ENV=1`).

## Loop (operator side, outside jail)

For `seq` from `14` to `22` inclusive:

### 1. Reveal (operator only)

Operator reads the **next** sealed cursor from the canonical fixture **outside** the jail (not visible to Resident)
and builds the 8-field resident-visible projection:

```
{
  event_id:             <fixture event_id for seq>,
  sequence:             <seq>,                         # 14..22 inclusive, strict
  occurred_at:          <fixture occurred_at>,
  dimension:            <fixture dimension>,
  source_kind:          conversation | mechanical,
  source_class:         <fixture source_class>,
  modality:             <fixture modality>,
  resident_visible_payload: { text | observation | ... }  # ONLY resident-visible subfields
}
```

Validation (fail closed): must have **exactly** those 8 keys, `sequence` in `14..22`,
`source_kind` in `conversation|mechanical`, `resident_visible_payload` is an object.
Any extra key, missing key, `sequence` 13 or 23, or `phase != B` aborts the iteration
before the envelope is built — no file is written, round does not advance.

No other cursor is read; no future `sequence` is buffered.

### 2. Build envelope (mechanical, inside `bridged_model_handler.build_envelope`)

- `snapshot = FusedTurnRuntime.capture()` (or `CognitiveRuntime` in headless probe) — real Core snapshot.
- `current_event =` the 8-field projection from step 1 if `sequence == seq`; else `null` (synthetic case not used for real B).
- `envelope = build_envelope(snapshot, b_session, contract_sha256, current_event)`:
  `phase B`, `allowed_sequences [14,22]`, `runtime_snapshot = cockpit`, `capability_catalog`, `capability_history` (filtered to B-session), `wake_reason`, `is_periodic_review`, `is_summary_request false`, `contract_sha256`, `event = current_event`.
- Binding: `round`/`request_id`/`request_digest` assigned (incremental, random 32-hex nonce, canonical digest).
- Envelope validated by `MailboxBridge.validate_envelope` (B-session only, path-aware leakage guard — bare `fixture` allowed in `obs_c14_fixture_*`, only `/repo/fixture` etc. blocked; top-level allowlist 11 fields).

### 3. Invoke model (production path, outside jail)

```
request = build_model_request(contract_text, envelope)
        = { system: <exact RESIDENT_B_RUN_CONTRACT.md bytes>, messages: [{role:"user", content: JSON(envelope)}] }
provider_resp = provider_client.invoke(request)   # RealProviderClient in real B; FakeProviderClient in preflight
content = provider_resp.content                   # JSON string/dict of Resident reply
reply = JSON.parse(content)
```

Provider visibility is **exactly** `system + envelope JSON`; no path leakage (`/repo/fixture` etc. checked in fake).
Provenance mapping: `provider/model/request_id/usage(total/input/output)` from `provider_resp.*` (or `"UNKNOWN"`/`None` if not credibly available) — never synthetic `sandbox-bridge/10`.

### 4. Validate reply (fail closed, Scheme A)

```
validate_reply(reply)  # strict: round/request_id/request_digest required + per-action allowlist
verify_binding(reply)  # round/request_id/request_digest == outstanding; stale/preplay/replay/wrong-id/wrong-digest fail
```

- `action` in `{invoke_capability, end_turn, silence, summary_response}` — `round_repair_request` → `ModelDispatchNotSubmitted` (unsupported).
- `silence` allowlist = `{round,request_id,request_digest,action}` only — extra `capability`/`response` fails.
- `invoke_capability` requires `{capability, arguments}`, `end_turn` requires `response` if present non-blank, `summary_response` requires `response|summary` non-blank.
- Any structural/binding failure → `ModelDispatchNotSubmitted("bridge reply binding failed: ...")`; the round is **not consumed**, consumed set unchanged, future reply with correct binding still works.
- Malformed JSON → fail closed, `rejected-reply-*` archived, outstanding cleared only on success.

**No repair turn** is synthesized; the operator simply logs the failure and retries the same `seq` (or aborts the step after a bounded retry count). The Resident never sees a repair instruction.

### 5. Dispatch capability or end turn (Core path)

- `directive = reply_to_directive_production(reply, snapshot, provider_resp)` maps `action` → `ModelDirective`:
  `silence | response | capability_calls (1..N CapabilityCall)`.
- `usage` and `provenance` taken from real provider metadata (as above).
- `FusedTurnRuntime` executes `capability_calls` via `CapabilityExecutor` (durable World + index + receipt chain), appends results to `capability_history`, then **loops** to the next envelope build **without advancing `seq`** (same cursor, second model round using the same adapter/binding, now with `capability_history` non-empty including the `Atlas` search result `obs_c14_fixture_*`). This is the genuine 2-round path proven in `probe_e2e.sh`.
- If `action` is `silence` or `end_turn` on the first round, the cursor is considered complete and `seq` advances to next reveal.
- If a capability was invoked, the follow-up envelope (round 2) carries the updated `capability_history`; the Resident model is re-prompted for the same `seq` until it emits `silence`/`end_turn`.

## Forbidden actions during this procedure

- Do **not** read any cursor ahead (`seq+1` etc.) or any Phase C cursor.
- Do **not** modify `src/aios_core/` (frozen `fe77f8a`).
- Do **not** swap `bridged_model_handler.py` at runtime (frozen file; only `ProviderClient` ctor differs between fake and real).
- Do **not** expose `mailbox/archive`, A transcript, fixture/evaluator/governance paths, or PM report to the Resident (envelope allowlist + path guard enforce).
- Do **not** advance round while an outstanding request is pending.

## Verbatim probe evidence (synthetic, disposable)

The disposable probe runs this exact loop for a synthetic cursor 14 projection (`synthetic-fixture-seq-14`, 8 fields + sequence 14) using `SyntheticProbeHandler` + `ProductionResidentHandler(FakeProviderClient)`:

- **Negatives:** `sequence 13`, `sequence 23`, extra event field `fixture_hint`, missing `resident_visible_payload`, `phase A` envelope — all **rejected** before inbox write (no file, `ModelDispatchNotSubmitted`).
- **Positive:** `sequence 14` → `build_envelope` with current_event → envelope validated → `FakeProvider` → `search_world Atlas limit2` → second envelope with `capability_history` containing `obs_c14_fixture_*` legal ids → `silence` (non-empty search survived).
- **Strict reply:** `silence{capability}` → `validate_reply` **rejects** extra field.
- **Scheme A:** `round_repair_request` → `ModelDispatchNotSubmitted` (unsupported).

