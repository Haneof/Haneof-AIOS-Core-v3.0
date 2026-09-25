# C15-RCC-RES-B-PREFLIGHT-002 — Exact B Startup Procedure (CORRECTIVE-003 frozen)

This procedure is prepared by preflight but NOT executed. It will be carried out by the independent release task `C15-RCC-RES-B-RELEASE-002` after this preflight is independently reviewed and accepted.

This procedure does NOT reveal cursor 14. It prepares the runtime directory, frozen harness, and isolation evidence. Cursor 14 reveal is the first act of the B release task (fresh model process, one cursor at a time).

## 0. Prerequisites

- Live main pinned to the commit that merges this preflight PR (or to a release-review-approved descendant). Current `main HEAD aa19af1` with `software 773876f92d5f8e53422f8f5a68cc651953d93052`, `Core fe77f8a0706acfaf369041d0882b6d0e6de39f22` unchanged.
- #205 still at exact head `d17ae972ad1d312735c355f775ac024bc4cebdf7`; verify with `git fetch origin pull/205/head:pr205 && git rev-parse pr205` before starting.
- Python 3.11+ with `pydantic` available.
- `sudo` for mount-namespace sandbox construction (sandbox drops to `nobody` before Resident runs; `CAP_SYS_ADMIN|CAP_SYS_CHROOT|CAP_SYS_RESOURCE` required for `unshare`+`mount`+`chroot`).
- `environment_manifest.md` pinned; `PROBE_MODE/PROBE_ROUNDS` not set in production.

## 1. Prepare a fresh B runtime directory (operator side, outside jail)

```bash
RUN_ROOT=/tmp/c15-rcc-res-b-002-$(date +%s)
mkdir -p $RUN_ROOT/{runtime,sandbox,mailbox/{inbox,outbox,archive},evidence/{mailbox,freeze},scratch,inject}

# Copy byte-exact A-002 lineage from this preflight (or from #205 directly).
# IMPORTANT: copy to world.sqlite / index.sqlite / release_state.json (names headless CLI expects), NOT private_world.sqlite etc.
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy/private_world.sqlite   $RUN_ROOT/runtime/world.sqlite
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy/world_index.sqlite     $RUN_ROOT/runtime/index.sqlite
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy/release_state.json    $RUN_ROOT/runtime/release_state.json
touch $RUN_ROOT/runtime/world.writer.lock
```

Verify digests of the copy match accepted freeze digests:

```bash
cd $RUN_ROOT/runtime
sha256sum world.sqlite index.sqlite release_state.json
# Expect:
# 626c6bb32c7fdae90a068ee10dd2b4c9c9cdbc46b6feb2bf5b11cba9363401f6aa  world.sqlite
# ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1  index.sqlite
# eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8  release_state.json
```

If any digest mismatches, STOP.

## 2. Verify recovery status (no model invocation)

```bash
PYTHONPATH=src python3 -m aios_core.headless.cli \
  --world $RUN_ROOT/runtime/world.sqlite \
  --index $RUN_ROOT/runtime/index.sqlite \
  --lock  $RUN_ROOT/runtime/world.writer.lock \
  recovery-status
```

Expect `world_revision=98`, `index_watermark=98`, `index_lag=0`, `recovery_disposition=AUTO_RECOVERABLE`, `world_quick_check=["ok"]`. If not, STOP.

## 3. Phase-B init (operator side; validates boundary, transitions active_phase to B)

```bash
PYTHONPATH=src python3 reviews/internal_habitation/c15-rcc/v1/release/release_operator.py \
  init --phase B --state $RUN_ROOT/runtime/release_state.json
```

Expect:

```json
{"fixture_sha256":"sha256:7ccb309d...","next_sequence":14,"phase":"B","status":"initialized"}
```

If error, STOP — boundary malformed. After init, `release_state.json.active_phase == "B"`, `next_sequence==14`, `pending_reveal==null`, receipts unchanged.

## 4. Build and verify the sandbox BEFORE the model starts

```bash
# Copy probes into inject dir
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

Expected final line: `ISOLATION_PASS`, exit 0. This validates:

- `CLONE_NEWNET` ENETUNREACH (github/raw/api/8.8.8.8 blocked, loopback only)
- `CLONE_NEWPID` fresh `/proc`, `sandbox-init` PID1 → worker `PID≥2`, reap
- `CLONE_NEWNS` mount private fail-closed (MS_PRIVATE injection → exit 98), RO bind `ro,nosuid,nodev` + `EROFS`
- Mailbox IPC: `inbox 0755/outbox 01733/archive 0700 not mounted`, `nobody` read/write/no-archive
- `/dev` minimal (`null/zero/urandom/random` + `fd` only, no `sda/tty/mem`)
- Privdrop dual injection (`exit 98` no sentinel), signal strict, env allowlist (PROBE_* stripped)
- Forbidden path guard (`/repo/fixture` blocked, bare `obs_c14_fixture_*` allowed)

If `ISOLATION_FAIL` or any `FAIL:` line appears, STOP.

## 4a. Run the E2E transport probe — genuine + synthetic (no cursor 14 reveal to real model)

```bash
# Disposable E2E (26 checks)
bash reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/probe_e2e.sh
```

Expected final line: `CORRECTIVE_003_E2E_PASS` (or `E2E_PROBE_PASS` for legacy step header, plus 6 explicit binding failure lines).

- Mailbox self-tests (15 including extra reply field)
- Binding negatives (stale/preplay/replay/wrong-id/wrong-digest + future-not-valid-later)
- **Synthetic 2-round:** `FusedTurnRuntime → SyntheticProbeHandler → MailboxBridge → inside-jail responder (nobody)` → `invoke search_world Atlas limit2 (non-empty legal)` → capability OK → second envelope carries `capability_history` with `obs_c14_fixture_*` → `silence`
- **Production 2-round:** `FusedTurnRuntime → ProductionResidentHandler(FakeProviderClient fake-provider/fake-model-v1/42 tokens) → build_model_request(contract+envelope) → FakeProvider invoke → reply validate/binding → ModelDirective with REAL provenance` → `Atlas` non-empty → `silence`
- **Current-event wiring:** `current_event` 8-field seq14 positive + negatives (13/23/extra/missing/phase A) fail closed before write
- **Strict reply:** `silence{capability}` extra field rejected
- **Scheme A:** `round_repair_request` unsupported → fail closed
- **Environment:** `PROBE_MODE` stripped unless `AIOS_ALLOW_PROBE_ENV=1`

Do NOT proceed if any check fails.

## 5. Mint a fresh B session/process identity

```bash
B_SESSION="c15-rcc-res-b-rerun-002-$(openssl rand -hex 6)"
B_PROCESS="$(openssl rand -hex 16)"
echo "$B_SESSION" > $RUN_ROOT/evidence/b_session_id
echo "$B_PROCESS" > $RUN_ROOT/evidence/b_process_id
```

Must be fresh — no reuse of `c15-rcc-res-a-rerun-002-2079f64af49c`.

## 6. Prepare the operator-side model handler (OUTSIDE the jail) — FROZEN (BLOCKER 1 + 3)

**Frozen file:** `harness/bridged_model_handler.py` — contains both `ProductionResidentHandler` (real B) and `SyntheticProbeHandler` (disposable probe). **MUST NOT be edited at release.** Only the `ProviderClient` ctor is swapped.

Real B uses `ProductionResidentHandler` (frozen intent, per `isolation/isolation_report.md`):

1. Core's `FusedTurnRuntime`/`CognitiveRuntime` calls `ProductionResidentHandler(snapshot)` via `ModelHandler` protocol — snapshot is mechanically assembled (`world_map/cockpit/capability_catalog/history/wake_reason/round_index`), not hand-written.
2. `build_envelope(snapshot, b_session, contract_sha256, current_event)` projects to Resident-safe envelope (11-field allowlist, `event` is **exact** 8-field projection `event_id/sequence/occurred_at/dimension/source_kind/source_class/modality/resident_visible_payload` with `14..22`, `phase B`, `allowed_sequences [14,22]`, no extra keys). `event=None` only in synthetic probe; real B always has `current_event` for the revealed cursor.
3. Binding assigns `round/request_id/nonce/request_digest` (one-at-a-time, canonical digest).
4. `build_model_request(contract_text, envelope)` builds the **exact** provider request `{system: <RESIDENT_B_RUN_CONTRACT.md bytes>, messages: [{role:"user", content: JSON(envelope)}]}` — no other file.
5. `provider_client.invoke(request)` executes **outside** the jail (broker sees only `contract+envelope`; `CLONE_NEWNET` remains sealed inside). Preflight uses `FakeProviderClient(provider="fake-provider", model="fake-model-v1", total_tokens=42)`; real B uses `RealProviderClient` (same interface, same file, constructor-only swap).
6. `wait` verifies `round/request_id/request_digest` exactly; stale/preplay/replay/wrong-id/wrong-digest fail closed → `ModelDispatchNotSubmitted` (no semantic default).
7. `reply_to_directive_production(reply, snap, provider_resp)` maps `action` → `ModelDirective` with **REAL** provenance (`provider/model/request_id` from provider, or `"UNKNOWN"` where credibly unavailable; `usage.total_tokens` from provider or `None`, never `10`).
8. Capability follow-up uses **same adapter/binding** for round 2 (`capability_history` now contains `search_world Atlas` legal result `obs_c14_fixture_*`) — proven that one `run_turn` → two handler invocations.

The frozen handler MUST NOT:

- include A mailbox, A transcript, governance, fixture, evaluator, PM report in context;
- pre-populate answer/hint;
- log chain-of-thought;
- synthesize default on timeout/malformed (fail closed);
- fabricate `total_tokens=10` / `sandbox-bridge` for real B.

Headless wiring for production (fake shown, real swaps client):

```bash
export AIOS_B_SESSION_ID="$B_SESSION"
export AIOS_CONTRACT_SHA256="$(sha256sum reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md | cut -d' ' -f1)"
# Fake preflight:
export FAKE_PROVIDER="fake-provider"
export FAKE_MODEL="fake-model-v1"
# Resident still jailed; model runs outside jail via broker:
PYTHONPATH=src python3 -m aios_core.headless.cli \
  --world "$RUN_ROOT/runtime/world.sqlite" \
  --index "$RUN_ROOT/runtime/index.sqlite" \
  --lock  "$RUN_ROOT/runtime/world.writer.lock" \
  --model-handler harness.bridged_model_handler:headless_production_handler \
  turn --session "$B_SESSION" --turn-index 1 --text "..." --at "2026-11-05T09:00:00-08:00"
```

Alternative synthetic headless (`headless_handler` → `SyntheticProbeHandler` + mailbox) remains for disposable tests only.

See `environment_manifest.md` for env allowlist, `procedure/per_cursor_interaction.md` for the exact 14..22 loop (Scheme A, no repair), and `probe_e2e.sh` for the 26-check genuine evidence.

## 7. Drive B cursors 14..22 (sequential, per procedure/per_cursor_interaction.md)

For each `seq` 14..22 (exactly one at a time):

1. `release_operator.py reveal --phase B --state $RUN_ROOT/runtime/release_state.json > /tmp/current-event-$seq.json` — operator only, reads sealed fixture outside jail, emits only the 8-field projection (validated before envelope build).
2. If `source_kind==conversation`: `canonical_conversation_ingest.py` then `aios-core-headless turn` (which calls `ProductionResidentHandler` with `current_event` set); if mechanical: `mechanical_ingest_adapter.py` then `due`. Blocks on `MailboxBridge.wait_for_reply`-equiv binding verification inside production handler.
3. After durable ACK + `due` completion, loop.

Resident model context is kept alive across rounds **within** B session (working-memory continuity) but fresh at B startup (zero prior history).

## 8. Stop condition + freeze

After `seq 22` durably ACKed and due work completed at that timestamp, run `procedure/final_freeze_procedure.md` (freeze World/Index/Release + evidence), terminate model process and sandbox. Do not proceed to `seq 23`.

```

