# C15-RCC-RES-B-PREFLIGHT-002 — Exact B Startup Procedure (CORRECTIVE-004 frozen)

This procedure is prepared by preflight but NOT executed. It will be carried out by the independent release task `C15-RCC-RES-B-RELEASE-002` after this preflight is independently reviewed and accepted.

This procedure does NOT reveal cursor 14. It prepares the runtime directory, frozen harness, wire protocol, and isolation evidence. Cursor 14 reveal is the first act of the B release task (fresh model process, one cursor at a time).

## 0. Prerequisites (exact, fail closed)

- Live main pinned to the commit that merges this preflight PR (or to a release-review-approved descendant). Current `main HEAD aa19af1` with `software 773876f92d5f8e53422f8f5a68cc651953d93052`, `Core fe77f8a0706acfaf369041d0882b6d0e6de39f22` unchanged.
- #205 still at exact head `d17ae972ad1d312735c355f775ac024bc4cebdf7`; verify with `git fetch origin pull/205/head:pr205 && git rev-parse pr205` before starting.
- **Exact environment** per `environment_manifest.md` — no `pip install` at release:
  - `Python 3.11.2` (`python3 --version` must equal `Python 3.11.2`)
  - `pydantic 2.13.5` (`python3 -c "import pydantic; print(pydantic.__version__)"` must equal `2.13.5`)
  - `harness/resident_wire_protocol.json` sha256 `5067701b003f99c141ecef1874ae8195ea2faf1ef5caa87cae092b57cad38b38`
  - `RESIDENT_B_RUN_CONTRACT.md` `sha256 28d3262f…`
  - `pip freeze` must contain `pydantic==2.13.5` and hash `bd7a76d1171c137f9daee9c0a3dbff029b8cbbccef88f0a1aff7907710a82375`; full freeze at `harness/requirements.freeze.txt`. Mismatch → STOP.
- `sudo` for mount-namespace sandbox (`CAP_SYS_ADMIN|CAP_SYS_CHROOT|CAP_SYS_RESOURCE` for `unshare+mount+chroot`).
- `environment_manifest.md` pinned; `PROBE_MODE/PROBE_ROUNDS` not set in production.
- Real provider adapter pinned: `bridged_model_handler:RealProviderClient` `v1.0.0-frozen`, `provider real-provider` `model real-model-v1`, `wire_protocol 5067701b…`.

## 1. Prepare a fresh B runtime directory (operator side, outside jail)

```bash
RUN_ROOT=/tmp/c15-rcc-res-b-002-$(date +%s)
mkdir -p $RUN_ROOT/{runtime,sandbox,mailbox/{inbox,outbox,archive},evidence/{mailbox,freeze},scratch,inject}

# Copy byte-exact A-002 lineage
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy/private_world.sqlite   $RUN_ROOT/runtime/world.sqlite
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy/world_index.sqlite     $RUN_ROOT/runtime/index.sqlite
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy/release_state.json    $RUN_ROOT/runtime/release_state.json
touch $RUN_ROOT/runtime/world.writer.lock
```

Verify digests:

```bash
cd $RUN_ROOT/runtime
sha256sum world.sqlite index.sqlite release_state.json
# 626c6bb32c7fdae90a068ee10dd2b4c9c9cdbc46b6feb2bf5b11cba9363401f6aa  world.sqlite
# ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1  index.sqlite
# eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8  release_state.json
sha256sum ../harness/resident_wire_protocol.json 5067701b003f99c141ecef1874ae8195ea2faf1ef5caa87cae092b57cad38b38
python3 --version # Python 3.11.2
python3 -c "import pydantic; print(pydantic.__version__)" # 2.13.5
```

If any mismatch, STOP — no `pip install`, no upgrade.

## 2. Verify recovery status (no model invocation)

```bash
PYTHONPATH=src:reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/harness python3 -m aios_core.headless.cli \
  --world $RUN_ROOT/runtime/world.sqlite \
  --index $RUN_ROOT/runtime/index.sqlite \
  --lock  $RUN_ROOT/runtime/world.writer.lock \
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
  --lock    $RUN_ROOT/runtime/world.writer.lock \
  --mailbox-root $RUN_ROOT/mailbox \
  --inject-dir $RUN_ROOT/inject \
  -- /bin/sh /work/inject/probe.sh
```

Expected `ISOLATION_PASS` (`CLONE_NEWNET` ENETUNREACH, `sandbox-init` PID1 → worker ≥2, `MS_PRIVATE` fail-closed, RO `ro,nosuid,nodev`, `/dev` minimal, mailbox `0755/01733`, privdrop, env allowlist).

If `ISOLATION_FAIL`, STOP.

## 4a. Run the E2E transport probe — genuine + production + adversarial (no cursor 14 reveal)

```bash
# 004 exact gate: EXPECTED_CHECKS=41, requires CHECKS==EXPECTED_CHECKS and zero FAIL
bash reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/probe_e2e.sh
```

Expected `CORRECTIVE_004_E2E_PASS` (41 checks: mailbox 15, isolation, binding 7, synthetic+production genuine, current-event 6, strict, Scheme A, MS_PRIVATE, /dev, signal deterministic with PID map, env exact, real-provider fail-closed, fake fallback fail, import path executable, wire protocol hash, inconsistent telemetry, etc.).

Do NOT proceed if any check fails.

## 5. Mint a fresh B session/process identity

```bash
B_SESSION="c15-rcc-res-b-rerun-002-$(openssl rand -hex 6)"
B_PROCESS="$(openssl rand -hex 16)"
echo "$B_SESSION" > $RUN_ROOT/evidence/b_session_id
echo "$B_PROCESS" > $RUN_ROOT/evidence/b_process_id
```

Must be fresh — no reuse of `c15-rcc-res-a-rerun-002-2079f64af49c`.

## 6. Prepare the operator-side model handler (OUTSIDE the jail) — FROZEN (RealProviderClient)

**Frozen file:** `harness/bridged_model_handler.py` + `harness/resident_wire_protocol.json` (`5067701b…`). **MUST NOT be edited at release.** Only `AIOS_REAL_PROVIDER_*` env selects real broker.

Real B uses `ProductionResidentHandler` with `RealProviderClient` (pinned `bridged_model_handler:RealProviderClient` `v1.0.0-frozen`):

1. `FusedTurnRuntime` → `ProductionResidentHandler(snapshot)` (mechanical `world_map/cockpit/catalog/history/wake_reason`).
2. `build_envelope(snapshot,b_session,contract_sha,current_event,release_state_path)` → envelope `event` is **exact** 8-field projection bound to current release cursor (sequence==next_sequence, event_id==expected, payload digest==expected, release-state `pending_reveal` or operator reveal file). `event=None` only for synthetic probe; real B always has `current_event` per cursor.
3. `validate_current_event_binding` enforces `sequence 14..22`, `source_kind conversation|mechanical`, payload non-empty, and exact binding to `release_state.json` next/pending and `AIOS_CURRENT_EVENT_PATH` file digest. `seq15` when expected `14` → fail closed.
4. Binding `round/request_id/nonce/request_digest` (one-at-a-time, canonical digest).
5. `build_model_request(contract_text,envelope,wire_protocol_text)` → **exact** provider request `{system: contract, wire_protocol: schema, wire_protocol_sha256: 5067701b…, messages: [{role:user, content: JSON(envelope)}]}` — provider sees `contract + envelope + mechanical reply schema`, never fixture.
6. `RealProviderClient.invoke(request)` outside jail (pinned adapter). **Fail closed if `AIOS_REAL_PROVIDER_API_KEY` or `AIOS_REAL_PROVIDER_ENDPOINT` missing, or adapter unresolvable, or `FakeProviderClient` selected from production entrypoint.**
7. Parse provider `content` JSON → `validate_reply` (per-action allowlist) + `verify_binding` (stale/preplay/replay/wrong-id/wrong-digest fail) → `reply_to_directive_production` with **RAW provenance** (`provider/model/request_id` actual or `UNKNOWN`, `usage` raw preserved, inconsistent `total<input+output` → `usage None` not rewritten).
8. On any `provider exception / non-JSON / schema invalid / binding invalid` → **Scheme A-hard-stop**: clear `_outstanding`, save failure evidence, terminate/reconstruct handler, do **not** advance cursor, next request has new binding, never generate semantic repair hint.
9. Capability follow-up uses same `current_event` for same cursor, same adapter/binding round 2 (`capability_history` contains `Atlas` legal `obs_c14_fixture_*`).

The frozen handler MUST NOT: include A transcript/governance/fixture, pre-populate answer, log chain-of-thought, synthesize default on timeout, fabricate `sandbox-bridge/10` for real B, or rewrite `total_tokens`.

Headless wiring for production (exact documented command, must succeed via real import):

```bash
export AIOS_B_SESSION_ID="$B_SESSION"
export AIOS_CONTRACT_SHA256="$(sha256sum reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md | cut -d' ' -f1)"
export AIOS_WIRE_PROTOCOL_SHA256="5067701b003f99c141ecef1874ae8195ea2faf1ef5caa87cae092b57cad38b38"
export AIOS_REAL_PROVIDER_API_KEY="sk-real-..."   # required, fail closed if missing
export AIOS_REAL_PROVIDER_ENDPOINT="https://broker.trusted/..." # required
export AIOS_PROVIDER_ADAPTER="bridged_model_handler:RealProviderClient" # pinned
export AIOS_RELEASE_STATE_PATH="$RUN_ROOT/runtime/release_state.json"
export AIOS_CURRENT_EVENT_PATH="$RUN_ROOT/current-event.json" # per cursor, refreshed each turn
export PYTHONPATH="src:reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/harness"
# Exact documented headless command (must be importable without sys.path.insert):
python3 -m aios_core.headless.cli \
  --world "$RUN_ROOT/runtime/world.sqlite" \
  --index "$RUN_ROOT/runtime/index.sqlite" \
  --lock  "$RUN_ROOT/runtime/world.writer.lock" \
  --model-handler bridged_model_handler:headless_production_handler \
  turn --session "$B_SESSION" --turn-index 1 --text "..." --at "2026-11-05T09:00:00-08:00"
```

`FakeProviderClient` is **never** reachable from this entrypoint; it is only instantiated explicitly by `probe_e2e.sh` for disposable tests.

See `environment_manifest.md` for exact env, `per_cursor_interaction.md` for Scheme A and per-cursor event lifecycle, `probe_e2e.sh` for 41-check evidence.

## 7. Drive B cursors 14..22 (sequential, per procedure/per_cursor_interaction.md)

For each `seq` 14..22 (exactly one at a time, per-cursor file binding):

1. `release_operator.py reveal --phase B --state $RUN_ROOT/runtime/release_state.json > $RUN_ROOT/current-event.json` — operator only, emits 8-field projection; handler reads `AIOS_CURRENT_EVENT_PATH` per call, validates `sequence==next_sequence`, `event_id` and payload digest exact, source_kind, and pending status; mismatch/stale/missing/malformed → fail closed, do not advance.
2. If `source_kind==conversation`: `canonical_conversation_ingest.py` then `headless turn` (via `RealProviderClient`); if mechanical: `mechanical_ingest_adapter.py` then `due`.
3. After durable ACK + `due` completion, **clear** `current-event.json` (or overwrite for next seq), reconstruct handler if Scheme A failure occurred (new binding), loop.

Resident context kept alive within B session (working memory) but fresh at B startup.

## 8. Stop condition + freeze

After `seq 22` ACKed and due work completed, run `final_freeze_procedure.md`, terminate sandbox. Do not proceed to `seq 23`.
