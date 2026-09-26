# C15-RCC-RES-B-PREFLIGHT-002 — Exact B Startup Procedure (CORRECTIVE-010 frozen)

This procedure is prepared by preflight but NOT executed. It will be carried out by the independent release task `C15-RCC-RES-B-RELEASE-002` after this preflight is independently reviewed and accepted.

This procedure does NOT reveal cursor 14. It prepares the runtime directory, frozen harness, wire protocol, and isolation evidence. Cursor 14 reveal is the first act of the B release task (fresh model process, one cursor at a time).

## 0. Prerequisites (exact, fail closed)

- Live main pinned to the commit that merges this preflight PR (or to a release-review-approved descendant). Current `main HEAD aa19af1` with `software 773876f92d5f8e53422f8f5a68cc651953d93052`, `Core fe77f8a0706acfaf369041d0882b6d0e6de39f22` unchanged.
- #205 still at exact head `d17ae972ad1d312735c355f775ac024bc4cebdf7`; verify with `git fetch origin pull/205/head:pr205 && git rev-parse pr205` before starting.
- **Exact environment** per `environment_manifest.md` — no `pip install` at release:
  - `Python 3.11.2` (`python3 --version` must equal `Python 3.11.2`)
  - `pydantic 2.13.5` (`python3 -c "import pydantic; print(pydantic.__version__)"` must equal `2.13.5`)
  - `harness/resident_wire_protocol.json` sha256 `a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a`
  - `RESIDENT_B_RUN_CONTRACT.md` `sha256 28d3262f…`
  - `pip freeze` must contain `pydantic==2.13.5` and hash `bd7a76d1171c137f9daee9c0a3dbff029b8cbbccef88f0a1aff7907710a82375`; full freeze at `harness/requirements.freeze.txt`. Mismatch → STOP.
- `sudo` for mount-namespace sandbox (`CAP_SYS_ADMIN|CAP_SYS_CHROOT|CAP_SYS_RESOURCE` for `unshare+mount+chroot`).
- `environment_manifest.md` pinned; `PROBE_MODE/PROBE_ROUNDS` not set in production.
- Real provider adapter pinned: `bridged_model_handler:ExternalBrokerClient` `v1.0.0-frozen`, `provider real-provider` `model real-model-v1`, `wire_protocol a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a…`.

## 1. Prepare a fresh B runtime directory (operator side, outside jail)

```bash
RUN_ROOT=/tmp/c15-rcc-res-b-002-$(date +%s)
mkdir -p $RUN_ROOT/{runtime,sandbox,mailbox/{inbox,outbox,archive},evidence/{mailbox,freeze},scratch,inject}

# Copy byte-exact A-002 lineage
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy/private_world.sqlite   $RUN_ROOT/runtime/world.sqlite
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy/world_index.sqlite     $RUN_ROOT/runtime/index.sqlite
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy/release_state.json    $RUN_ROOT/runtime/release_state.json
touch $RUN_ROOT/runtime/world.sqlite.writer.lock
```

Verify digests:

```bash
cd $RUN_ROOT/runtime
sha256sum world.sqlite index.sqlite release_state.json
# 626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa  world.sqlite
# ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1  index.sqlite
# eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8  release_state.json
echo "a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a  harness/resident_wire_protocol.json" | sha256sum -c -
python3 --version # Python 3.11.2
python3 -c "import pydantic; print(pydantic.__version__)" # 2.13.5
```

Authoritative lineage pin declarations. Every occurrence in this document, including the digest comments above, must equal these values. A correct hash elsewhere does not excuse a wrong declaration:

- World: `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa`
- Index: `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1`
- Release: `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8`

If any mismatch, STOP — no `pip install`, no upgrade.

## 2. Verify recovery status (no model invocation)

```bash
PYTHONPATH=src:reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/harness python3 -m aios_core.headless.cli \
  --world $RUN_ROOT/runtime/world.sqlite \
  --index $RUN_ROOT/runtime/index.sqlite \
  --lock  $RUN_ROOT/runtime/world.sqlite.writer.lock \
  recovery-status
```

Expect `world_revision=98`, `index_watermark=98`, `index_lag=0`, `recovery_disposition=AUTO_RECOVERABLE`, `world_quick_check=["ok"]`. If not, STOP.

Note: `PYTHONPATH` **must** include `src` **and** the nested harness directory (`reviews/.../harness`) so that `bridged_model_handler` is importable as `import bridged_model_handler` (frozen import contract for `load_model_handler()` which does `importlib.import_module(module_name)` without adding paths).

## 3. Phase-B init (operator side; validates boundary, transitions active_phase to B)

```bash
PYTHONPATH=src:reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/harness python3 reviews/internal_habitation/c15-rcc/v1/release/release_operator.py \
  init --phase B --state $RUN_ROOT/runtime/release_state.json
```

Expect:

```json
{"fixture_sha256":"sha256:7ccb309d...","next_sequence":14,"phase":"B","status":"initialized"}
```

After init, `release_state.json.active_phase == "B"`, `next_sequence==14`, `pending_reveal==null`.

## 4. Build and verify the sandbox BEFORE the model starts

```bash
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/probe_isolation.sh $RUN_ROOT/inject/probe.sh
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/resident_test_responder.py $RUN_ROOT/inject/responder.py
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/harness/mailbox_bridge.py $RUN_ROOT/inject/mailbox_bridge.py
chmod +x $RUN_ROOT/inject/probe.sh

sudo python3 reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/harness/resident_jail.py \
  --sandbox $RUN_ROOT/sandbox \
  --world   $RUN_ROOT/runtime/world.sqlite \
  --index   $RUN_ROOT/runtime/index.sqlite \
  --state   $RUN_ROOT/runtime/release_state.json \
  --lock    $RUN_ROOT/runtime/world.sqlite.writer.lock \
  --mailbox-root $RUN_ROOT/mailbox \
  --inject-dir $RUN_ROOT/inject \
  -- /bin/sh /work/inject/probe.sh
```

Expected `ISOLATION_PASS` (`CLONE_NEWNET` ENETUNREACH, `sandbox-init` PID1 → worker ≥2, `MS_PRIVATE` fail-closed, RO `ro,nosuid,nodev`, `/dev` minimal, mailbox `0755/01733`, privdrop, env allowlist).

If `ISOLATION_FAIL`, STOP.

## 4a. Run the E2E transport probe — genuine + production + adversarial (no cursor 14 reveal)

```bash
# exact current gate: EXPECTED_CHECKS=158, requires CHECKS==EXPECTED_CHECKS and zero FAIL (CORRECTIVE-014-FIXUP-003)
bash reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/probe_e2e.sh
```

Expected `CORRECTIVE_013_E2E_PASS` with `ALL_CHECKS=158/158 FAILURES=0`. Required current markers include `ENVIRONMENT_PASS`, `RAW_USAGE_NO_SYNTHESIS_PASS`, `CANONICAL_PIN_CONSISTENCY_PASS`, `CANONICAL_PIN_MUTATION_RED_PASS`, `CANONICAL_RUNBOOK_EXECUTABLE_PASS`, `CANONICAL_RUNBOOK_ORDER_PASS`, `RUNBOOK_CROSS_DOCUMENT_ORDER_PASS`, `RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS cases=5`, `RUNBOOK_EXECUTABLE_MUTATION_RED_PASS cases=18`, `RUNBOOK_SHELL_SEMANTICS_MUTATION_RED_PASS cases=62`, and final `CORRECTIVE_013_E2E_PASS`. C012 `157/157` evidence is historical only.

Do NOT proceed if any check fails.

## 5. Mint a fresh B session/process identity

```bash
B_SESSION="c15-rcc-res-b-rerun-002-$(openssl rand -hex 6)"
B_PROCESS="$(openssl rand -hex 16)"
echo "$B_SESSION" > $RUN_ROOT/evidence/b_session_id
echo "$B_PROCESS" > $RUN_ROOT/evidence/b_process_id
```

Must be fresh — no reuse of `c15-rcc-res-a-rerun-002-2079f64af49c`.

## 6. Configure the operator-side model handler — CONFIGURATION ONLY (outside the jail)

**Frozen file:** `harness/bridged_model_handler.py` + `harness/resident_wire_protocol.json` (`a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a…`). **MUST NOT be edited at release.** Only `AIOS_REAL_PROVIDER_*` env selects the real broker.

**No model dispatch occurs in this section. The first production model turn occurs only inside the per-cursor loop (Section 7) after reveal + binding receipt installation.**

Section 6 exports and pins configuration **only** — B session identity, provider endpoint/key/adapter, contract/wire/adapter hashes, the four canonical paths, and `PYTHONPATH`. Section 6 MUST NOT:

- read `$RUN_ROOT/current-event.json` — it does not exist yet; it is produced by reveal (7.1) and installed in 7.2;
- derive `CURRENT_OCCURRED_AT` — it is derived in **7.6, after reveal**, from the current projection;
- execute any model `turn`, `due`, background or periodic-review model round — every one of those happens in 7.7–7.9, strictly inside a live per-cursor binding.

Real B uses `ProductionResidentHandler` with `ExternalBrokerClient` (pinned `bridged_model_handler:ExternalBrokerClient` `v1.0.0-frozen`):

1. `FusedTurnRuntime` → `ProductionResidentHandler(snapshot)` (mechanical `world_map/cockpit/catalog/history/wake_reason`).
2. `build_envelope(snapshot,b_session,contract_sha,current_event,release_state_path)` → envelope `event` is **exact** 8-field projection bound to current release cursor (sequence==next_sequence, event_id==expected, payload digest==expected, release-state `pending_reveal` or operator reveal file). `event=None` is an unconditional STOP on the production path (CORRECTIVE-009 / BLK-05).
3. `validate_current_event_binding` enforces `sequence 14..22`, `source_kind opaque non-empty string from exact frozen reveal projection; value must exactly match immutable binding receipt`, payload non-empty, exact binding to `release_state.json` next/pending and `AIOS_CURRENT_EVENT_PATH` file digest. `seq15` when expected `14` → fail closed.
4. Binding `round/request_id/nonce/request_digest` (one-at-a-time, canonical digest).
5. `build_model_request(contract_text,envelope,wire_protocol_text)` → **exact** provider request `{system: contract, wire_protocol: schema, wire_protocol_sha256: a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a…, messages: [{role:user, content: JSON(envelope)}]}` — provider sees `contract + envelope + mechanical reply schema`, never fixture.
6. `ExternalBrokerClient.invoke(request)` outside jail (pinned adapter). **Fail closed if `AIOS_REAL_PROVIDER_API_KEY` or `AIOS_REAL_PROVIDER_ENDPOINT` missing, or adapter unresolvable, or `FakeProviderClient` selected from production entrypoint.**
7. Parse provider `content` JSON → `validate_reply` (per-action allowlist) + `verify_binding` (stale/preplay/replay/wrong-id/wrong-digest fail) → `reply_to_directive_production` with **RAW provenance** (`provider/model/request_id` actual or `UNKNOWN`). Usage is never synthesized: without provider-reported `total_tokens`, `usage=None`; with a valid total, optional input/output fields are preserved exactly if present; invalid values or `total<input+output` → `usage=None`.
8. On any `provider exception / non-JSON / schema invalid / binding invalid` → **Scheme A-hard-stop**: clear `_outstanding`, save failure evidence, terminate/reconstruct handler, do **not** advance cursor, next request has new binding, never generate semantic repair hint.
9. Capability follow-up uses same `current_event` for same cursor, same adapter/binding round 2 (`capability_history` contains `Atlas` legal `obs_c14_fixture_*`).

The frozen handler MUST NOT: include A transcript/governance/fixture, pre-populate answer, log chain-of-thought, synthesize default on timeout, fabricate `sandbox-bridge/10` for real B, or rewrite `total_tokens`.

Headless wiring for production — **configuration only** (exact documented commands):

```bash
# Path constants (repo-root relative; the probe derives the same values mechanically).
B_PREP="reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002"
HARNESS_DIR="$B_PREP/harness"
export AIOS_B_SESSION_ID="$B_SESSION"
export AIOS_CONTRACT_SHA256="$(sha256sum reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md | cut -d' ' -f1)"
export AIOS_WIRE_PROTOCOL_SHA256="a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a"
export AIOS_ADAPTER_SHA256="$(sha256sum "$B_PREP/harness/bridged_model_handler.py" | cut -d' ' -f1)"
# Adapter SHA is computed from the accepted tree and must match the pin in environment_manifest.md.
grep -q "$AIOS_ADAPTER_SHA256" "$B_PREP/environment_manifest.md" || { echo "STOP: adapter SHA drift vs environment_manifest.md"; exit 1; }
export AIOS_REAL_PROVIDER_API_KEY="sk-real-..."   # required, fail closed if missing
export AIOS_REAL_PROVIDER_ENDPOINT="https://broker.trusted/..." # required, HTTPS-only (production)
export AIOS_PROVIDER_ADAPTER="bridged_model_handler:ExternalBrokerClient" # pinned, exact
export AIOS_RELEASE_STATE_PATH="$RUN_ROOT/runtime/release_state.json"
export AIOS_CURRENT_EVENT_PATH="$RUN_ROOT/current-event.json" # per cursor, created by reveal (7.1) + install (7.2)
export AIOS_CURRENT_EVENT_BINDING_PATH="$RUN_ROOT/binding/current-event-binding.json" # immutable 0400, created in 7.4
export AIOS_EVIDENCE_DIR="$RUN_ROOT/evidence" # durable failure receipts
export PYTHONPATH="src:$B_PREP/harness"
```

End-of-section fail-closed assertions (all MUST hold *before* any reveal; otherwise STOP):

```bash
[ -f "$RUN_ROOT/runtime/release_state.json" ] || { echo "STOP: release state missing"; exit 1; }
python3 -c 'import json,sys
s=json.load(open(sys.argv[1]))
sys.exit(0 if (s.get("active_phase")=="B" and s.get("pending_reveal") is None and s.get("next_sequence")==14) else 1)' \
  "$RUN_ROOT/runtime/release_state.json" \
  || { echo "STOP: release state not in pristine Phase-B boundary (pending_reveal must be null before the first reveal)"; exit 1; }
[ ! -e "$RUN_ROOT/current-event.json" ] || { echo "STOP: current-event.json exists before reveal"; exit 1; }
[ ! -e "$RUN_ROOT/binding/current-event-binding.json" ] || { echo "STOP: binding receipt exists before reveal"; exit 1; }
echo "SECTION_6_CONFIGURATION_ONLY_OK: no current event, no binding receipt, no model turn yet"
```

`FakeProviderClient` is **never** reachable from this entrypoint; it is only instantiated explicitly by `probe_e2e.sh` for disposable tests.

See `environment_manifest.md` for exact env, `per_cursor_interaction.md` for Scheme A and the per-cursor event lifecycle, `probe_e2e.sh` for the CORRECTIVE-010 check evidence.

## 7. Drive B cursors 14..22 (sequential; exact canonical order — every step below is mandatory)

For each `seq` 14..22 (exactly one at a time). The order below is the **only** legal order and is
executable verbatim: steps 7.1–7.5 make the cursor legal, step 7.6 derives the canonical time
**after** reveal, steps 7.7–7.9 do the model work, step 7.10 makes it durable, steps 7.11–7.12 close
this cursor and open the next one.

This `b_startup_procedure.md §7` is the **single authoritative Phase-B cursor lifecycle**.
`per_cursor_interaction.md` is an exact operational mirror/reference of `b_startup_procedure.md §7`;
if any wording diverges, startup §7 is authoritative and execution MUST STOP until both documents are resynchronized.

<!-- C15_PHASE_B_LIFECYCLE_BEGIN -->
REVEAL
INSTALL_CURRENT_EVENT
PERSIST_PROJECTION_EVIDENCE
CREATE_BINDING_RECEIPT
VERIFY_BINDING
DERIVE_OCCURRED_AT
INGEST
MODEL_WORK
DURABLE_ACK
CLEAR_BINDING
NEXT_REVEAL
<!-- C15_PHASE_B_LIFECYCLE_END -->

The operator-side evidence loop is closed for every cursor: the exact reveal projection is persisted
**twice** — once as the handler input (`current-event.json`) and once as an immutable per-cursor
evidence artifact that `final_freeze_procedure.md` verifies.

### 7.1 REVEAL — `release_operator reveal` (operator only, outside jail)

```bash
python3 reviews/internal_habitation/c15-rcc/v1/release/release_operator.py \
  reveal --phase B --state "$RUN_ROOT/runtime/release_state.json" > "$RUN_ROOT/reveal.json"
```

Exactly one reveal per cursor. A second reveal before durable ACK is refused by `bindings.py`
(`duplicate reveal before durable ack is forbidden`). The 8-field projection on stdout is the only
legal source of `current-event.json`, the binding receipt and the projection evidence.

### 7.2 INSTALL_CURRENT_EVENT — write `current-event.json`

```bash
install -m 0400 "$RUN_ROOT/reveal.json" "$RUN_ROOT/current-event.json"
```

Before this step `$RUN_ROOT/current-event.json` MUST NOT exist (asserted at the end of Section 6).
The handler reads `AIOS_CURRENT_EVENT_PATH` per call and validates `sequence==next_sequence`,
`event_id`, payload digest, `source_kind` and pending status; mismatch/stale/missing/malformed →
fail closed, do not advance.

### 7.3 PERSIST_PROJECTION_EVIDENCE — immutable per-cursor projection

```bash
SEQ="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sequence"])' "$RUN_ROOT/current-event.json")"
install -m 0400 "$RUN_ROOT/current-event.json" "$RUN_ROOT/evidence/event-$(printf '%03d' "$SEQ").projection.json"
sha256sum "$RUN_ROOT/evidence/event-$(printf '%03d' "$SEQ").projection.json" >> "$RUN_ROOT/evidence/projection_digests.sha256"
```

After cursors 14..22 this yields exactly `$RUN_ROOT/evidence/event-014.projection.json` …
`event-022.projection.json` (9 files, sequences 14..22 contiguous, unique `event_id`), plus a SHA
manifest `projection_digests.sha256` that `final_freeze_procedure.md` verifies.

### 7.4 CREATE_BINDING_RECEIPT — immutable binding receipt

The receipt creation command is part of this runbook — it is **not** deferred to another document.
It must run only after steps 7.1–7.3 (reveal, install current-event, persist projection evidence).
Do not create a receipt before `current-event.json` exists.

```bash
mkdir -p "$RUN_ROOT/binding"
PYTHONPATH="$PYTHONPATH" python3 - <<'PY'
import json, os, sys
from pathlib import Path
harness = os.environ["PYTHONPATH"].split(":")[1]
sys.path.insert(0, harness)
from bridged_model_handler import create_current_event_binding_receipt, write_binding_receipt
proj = json.loads(Path(os.environ["AIOS_CURRENT_EVENT_PATH"]).read_bytes())
receipt = create_current_event_binding_receipt(
    proj,
    b_session_id=os.environ["AIOS_B_SESSION_ID"],
    release_state_path=os.environ["AIOS_RELEASE_STATE_PATH"],
)
write_binding_receipt(receipt, os.environ["AIOS_CURRENT_EVENT_BINDING_PATH"])
print("BINDING_RECEIPT_WRITTEN seq=%s event_id=%s"
      % (receipt["sequence"], receipt["event_id"]))
PY
chmod 0400 "$RUN_ROOT/binding/current-event-binding.json"
```

The canonical mechanical chain for every cursor is exactly:

```
release_operator reveal
  → install current-event.json
  → persist event-XXX.projection.json + digest
  → create_current_event_binding_receipt(...)
  → write_binding_receipt(receipt, AIOS_CURRENT_EVENT_BINDING_PATH)
  → validate_current_event_binding
  → derive CURRENT_OCCURRED_AT
  → ingest
  → model work
  → durable ACK
  → clear current-event.json + binding receipt
  → next reveal before any later model invocation
```

`create_current_event_binding_receipt` itself fails closed unless the live release state exists, is
readable, is valid JSON, has `next_sequence`, and carries a `pending_reveal` whose `sequence`,
`event_id` and `fixture_sha256` match the revealed projection exactly.

Receipt contains: `phase B`, `b_session_id`, `sequence`, `event_id`, `occurred_at`, `source_kind/class/modality/dimension`, `canonical_projection_sha256`, `resident_visible_payload_sha256`, `release_state_path/sha/next_sequence/pending`, `fixture_sha256`, `reveal_timestamp`, `operator_request_id`, `binding_version`.

### 7.5 VERIFY_BINDING — receipt / state / event binding

```bash
PYTHONPATH="$PYTHONPATH" python3 - <<'PY'
import json, os, sys
from pathlib import Path
sys.path.insert(0, os.environ["PYTHONPATH"].split(":")[1])
from bridged_model_handler import validate_current_event_binding
ev = json.loads(Path(os.environ["AIOS_CURRENT_EVENT_PATH"]).read_bytes())
validate_current_event_binding(
    ev, os.environ["AIOS_B_SESSION_ID"],
    release_state_path=os.environ["AIOS_RELEASE_STATE_PATH"],
    binding_receipt_path=os.environ["AIOS_CURRENT_EVENT_BINDING_PATH"],
)
print("CURRENT_EVENT_BINDING_VERIFIED seq=%s" % ev["sequence"])
PY
```

Handler validates `current-event.json` against `current-event-binding.json` + `release_state` on
every call; mismatches fail closed (11 negatives: seq15, wrong id, modified
text/dimension/source_kind/modality/occurred_at, wrong session, stale after ACK,
missing/malformed receipt).

### 7.6 DERIVE_OCCURRED_AT — from the current projection (after reveal)

```bash
CURRENT_OCCURRED_AT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["occurred_at"])' "$RUN_ROOT/current-event.json")"
echo "CURRENT_OCCURRED_AT=$CURRENT_OCCURRED_AT"
[ -n "$CURRENT_OCCURRED_AT" ] || { echo "STOP: cannot derive canonical occurred_at from the current projection"; exit 1; }
```

`CURRENT_OCCURRED_AT` is the canonical ingest/run time of **this** cursor, read from the projection
produced by reveal in 7.1. It is never hardcoded and never pre-read in Section 6.

### 7.7 INGEST — the current cursor

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

### 7.8 MODEL_WORK — production headless turn / due / model rounds

```bash
python3 -m aios_core.headless.cli \
  --world "$RUN_ROOT/runtime/world.sqlite" \
  --index "$RUN_ROOT/runtime/index.sqlite" \
  --lock  "$RUN_ROOT/runtime/world.sqlite.writer.lock" \
  --model-handler bridged_model_handler:headless_production_handler \
  turn --session "$B_SESSION" --turn-index 1 --text "..." --at "$CURRENT_OCCURRED_AT"
```

Model/capability rounds for this cursor reuse the **same** `current-event.json` and the same binding
receipt. `due` / wake / periodic-review / background model work for this cursor runs here too — never
between cursors (see `per_cursor_interaction.md` §5a).

### 7.9 Finish all model work for this cursor

Do not ACK until every model round, capability follow-up and `due` unit associated with this cursor
has completed successfully. Any Scheme A hard-stop terminates/reconstructs the handler and re-enters
from the same durable sequence/state with a new binding.

### 7.10 DURABLE_ACK

```bash
python3 reviews/internal_habitation/c15-rcc/v1/release/release_operator.py \
  ack --phase B --state "$RUN_ROOT/runtime/release_state.json" \
  --world-db "$RUN_ROOT/runtime/world.sqlite" \
  --sequence "$SEQ" --event-id "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["event_id"])' "$RUN_ROOT/current-event.json")" \
  --ingest-ref "$RUN_ROOT/evidence/event-$(printf '%03d' "$SEQ").projection.json" \
  --conversation-session-id "$B_SESSION" --conversation-turn-index 1
```

After the ACK, `release_state.json.next_sequence` increments and `pending_reveal` returns to null.

### 7.11 CLEAR_BINDING — current-event + binding (only now)

```bash
rm -f "$RUN_ROOT/current-event.json" "$RUN_ROOT/binding/current-event-binding.json"
```

Only after durable ACK **and** `due` completion for this cursor may the operator clear
`current-event.json` and the binding receipt.

### 7.12 NEXT_REVEAL — next cursor before any later model invocation

Before any further model invocation the next cursor MUST be revealed and the next binding receipt
installed — i.e. loop back to 7.1. Clearing the event never opens a window in which a model wake can
run unbound: any dispatch attempted while `current-event.json` is absent (for **any** `wake_reason`,
at **any** `round_index`, including `periodic_review` at round 1 and round 3) fails closed with
`ModelDispatchNotSubmitted`, poisons the handler, writes a durable receipt, and performs **zero**
provider invocations.

Reconstruct the handler if a Scheme A failure occurred (new binding), then loop.

Resident context kept alive within B session (working memory) but fresh at B startup.

## 8. Stop condition + freeze

After `seq 22` ACKed and due work completed, run `final_freeze_procedure.md`, terminate sandbox. Do not proceed to `seq 23`.
