# C15-RCC-RES-B-PREFLIGHT-002 — Exact B Startup Procedure

This procedure is prepared by preflight but NOT executed. It will be carried out by the independent release task `C15-RCC-RES-B-RELEASE-002` after this preflight is independently reviewed and accepted.

This procedure does NOT reveal cursor 14. It prepares the runtime directory and validates isolation. Cursor 14 reveal is the first act of the B release task (with a fresh model process).

## 0. Prerequisites

- Live main pinned to the commit that merges this preflight PR (or to a release-review-approved descendant).
- Frozen software and Core tree pins unchanged from `operator_manifest.md`.
- #205 still at exact head `d17ae972ad1d312735c355f775ac024bc4cebdf7`; verify with `git fetch origin pull/205/head:pr205 && git rev-parse pr205` before starting.
- Python 3.11+ with `pydantic` available.
- sudo for mount-namespace sandbox construction (the sandbox drops to `nobody` before the Resident runs).

## 1. Prepare a fresh B runtime directory (operator side)

```bash
RUN_ROOT=/tmp/c15-rcc-res-b-002-$(date +%s)
mkdir -p $RUN_ROOT/{runtime,sandbox,evidence/{mailbox,freeze},scratch}

# Copy byte-exact A-002 lineage from this preflight (or from #205 directly)
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy/private_world.sqlite   $RUN_ROOT/runtime/world.sqlite
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy/world_index.sqlite     $RUN_ROOT/runtime/index.sqlite
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy/release_state.json    $RUN_ROOT/runtime/release_state.json
touch $RUN_ROOT/runtime/world.writer.lock
```

Verify digests of the copy match the accepted freeze digests:
```bash
cd $RUN_ROOT/runtime
sha256sum private_world.sqlite world_index.sqlite release_state.json
# Expect:
# 626c6bb3...01f6aa  world.sqlite
# ecfabf4...1e5f1   index.sqlite
# eada20a...391c8   release_state.json
```

If any digest mismatches, STOP. The run would not be on the canonical lineage.

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

If init returns any error, STOP — boundary is malformed.

After init, `release_state.json.active_phase` is `"B"`, `next_sequence=14`, `pending_reveal=null`, receipts unchanged.

## 4. Build and verify the sandbox BEFORE the model starts

```bash
# Copy isolation probe into an inject dir
mkdir -p $RUN_ROOT/inject
cp reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/isolation/probe_isolation.sh $RUN_ROOT/inject/probe.sh
chmod +x $RUN_ROOT/inject/probe.sh

sudo python3 reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/harness/resident_jail.py \
  --sandbox $RUN_ROOT/sandbox \
  --world   $RUN_ROOT/runtime/world.sqlite \
  --index   $RUN_ROOT/runtime/index.sqlite \
  --state   $RUN_ROOT/runtime/release_state.json \
  --lock    $RUN_ROOT/runtime/world.writer.lock \
  --scratch $RUN_ROOT/scratch \
  --inject-dir $RUN_ROOT/inject \
  -- /bin/sh /work/inject/probe.sh
```

Expected final line: `ISOLATION_PASS`, exit=0. If `ISOLATION_FAIL` or any `LEAK:` line appears, STOP. Isolation is not proven; do not start the Resident model.

## 5. Mint a fresh B session/process identity

```bash
B_SESSION="c15-rcc-res-b-rerun-002-$(openssl rand -hex 6)"
B_PROCESS="$(openssl rand -hex 16)"
echo "$B_SESSION" > $RUN_ROOT/evidence/b_session_id
echo "$B_PROCESS" > $RUN_ROOT/evidence/b_process_id
```

B session MUST be freshly generated — no reuse of `c15-rcc-res-a-rerun-002-2079f64af49c`, of old B #121 session ids, or of the preflight session.

## 6. Prepare the operator-side model handler (OUTSIDE the sandbox)

The model handler is an adapter that:

1. Is invoked by `FusedTurnRuntime` / `CognitiveRuntime` via Core's normal ModelHandler protocol.
2. Serializes the RuntimeSnapshot + capability catalog/history/wake-reason to JSON.
3. Hands it to the mailbox bridge, which writes it to `/work/inbox/round-NNNN.json` inside the sandbox.
4. Hands the *Resident-safe B run contract* as the system instruction (the literal text of `RESIDENT_B_RUN_CONTRACT.md`).
5. Starts a **fresh model process/context** (new conversation; no prior A transcript, no prior B attempts, no chat history from any prior Resident run).
6. Blocks until a JSON reply appears in `/work/outbox/reply-NNNN.json`.
7. Returns the directive to Core for execution.

The model handler must NOT:

- include any A mailbox reply, A transcript, governance prose, fixture content, evaluator notes, or preflight report text in the model context;
- pre-populate any expected answer, keyword hint, or pre-authored directive;
- log or expose the model's hidden chain-of-thought (none is requested).

The exact model handler implementation is chosen at release time; preflight only requires that it conform to the shape above. See `identity_inventory.md` for attestation of the model/provider.

## 7. Start Core (operator side) and drive B cursors 14..22

The release task drives the sequential release loop exactly per procedure/per_cursor_interaction.md. In short:

For each sequence 14..22:
1. `release_operator.py reveal --phase B --state $RUN_ROOT/runtime/release_state.json > /tmp/current-event.json` (on operator; this is the ONLY point at which the sealed fixture is read, and only the 8-field projection is emitted).
2. If event is a USER conversation event: invoke `canonical_conversation_ingest.py`, then `aios-core-headless turn` with the matching session/turn/text/time; the turn runtime calls the model handler (which transports to the Resident in the sandbox).
3. If event is a mechanical non-conversation event: invoke `mechanical_ingest_adapter.py` which ingests without model cognition; then run `aios-core-headless due` to process any maintenance work that becomes due (which may invoke the Resident for Summary/Wake/Review).
4. After durable ACK and due-work completion, loop.

The Resident model context is kept alive across rounds WITHIN the B session (to preserve working-memory continuity), but is started fresh at B startup with zero history from any prior Resident.

## 8. Stop condition

After sequence 22 is durably ACKed and due work at that timestamp has completed, execute the final freeze (procedure/final_freeze_procedure.md), then terminate the model process and sandbox.

Do not proceed to sequence 23 (Phase C).
