# C15-RCC-RES-B-PREFLIGHT-002 — B Final Freeze / Evidence Procedure

This procedure is predefined BEFORE B runs, so that evidence capture is deterministic and auditable. It is executed only after cursor 22 is durably ACKed and due-work at that timestamp is complete.

## 1. Quiesce runtime

- Stop any pending mailbox wait; confirm no outstanding model request.
- Close the Core headless process cleanly (releases writer lock; flushes WAL).
- Confirm `release_state.json.pending_reveal = null`, `next_sequence = 23`, `last_acked_sequence = 22`, `active_phase = "B"`.
- Terminate the sandbox namespace.

## 2. Coherent SQLite snapshots

Use the existing Core backup path to produce coherent snapshots (WAL-safe):

```bash
PYTHONPATH=src python3 -m aios_core.headless.cli \
  --world $RUN_ROOT/runtime/world.sqlite \
  --index $RUN_ROOT/runtime/index.sqlite \
  --lock  $RUN_ROOT/runtime/world.writer.lock \
  backup --to $RUN_ROOT/evidence/freeze/private_world.sqlite
```

(This uses SQLite online backup API, which is crash-safe and includes all committed data.)

For the index: either copy the index file as-is after Core closes cleanly, or run `rebuild-index` from the World to a dedicated path. Record which method was used and verify `index_watermark == world_revision` and `index_lag == 0`.

## 3. Copy release_state.json

```bash
cp $RUN_ROOT/runtime/release_state.json $RUN_ROOT/evidence/freeze/release_state.json
```

## 4. Record runtime/restart checkpoint

Copy any required runtime checkpoint files (e.g. writer lock cleared, process/session identity files). At minimum save:

```bash
echo "$B_SESSION"   > $RUN_ROOT/evidence/freeze/b_session_id.txt
echo "$B_PROCESS"   > $RUN_ROOT/evidence/freeze/b_process_id.txt
date -u +"%Y-%m-%dT%H:%M:%SZ" > $RUN_ROOT/evidence/freeze/freeze_time.txt
```

## 5. Record software identity

Capture the frozen software pin, Core tree hash, and model-handler module reference actually used:

```bash
cat > $RUN_ROOT/evidence/freeze/software_identity.json <<EOF
{
  "frozen_software_commit": "773876f92d5f8e53422f8f5a68cc651953d93052",
  "core_tree": "fe77f8a0706acfaf369041d0882b6d0e6de39f22",
  "b_session_id": "$B_SESSION",
  "b_process_id": "$B_PROCESS",
  "model_handler_module": "<module>:<attribute>",
  "preflight_pr": "<this PR number>",
  "preflight_revision": "<commit hash of merged preflight>"
}
EOF
```

## 6. Model/provider identity attestation

Save whatever trusted identity evidence was actually obtained (HTTP response headers, provider response `model` field, request IDs, timing metadata). If the platform does not provide trustworthy attestation, record `{"trusted_model_identity": "UNKNOWN"}` — do NOT invent identity from self-descriptions or config strings.

## 7. Mailbox and due-work archive

Copy the mailbox request/reply archive and due-work ledger into `$RUN_ROOT/evidence/freeze/mailbox/` and `$RUN_ROOT/evidence/freeze/due_work/`. These are execution evidence, not durable state.

## 8. Per-cursor projection receipts

All 9 B event projections (cursors 14..22) should already be in `$RUN_ROOT/evidence/event-*.projection.json`; verify count = 9, sequences 14..22 contiguous.

## 9. Hash manifest

Compute SHA-256 of every freeze artifact and write `freeze/MANIFEST.json` + `freeze/digests.sha256`:

```bash
cd $RUN_ROOT/evidence/freeze
sha256sum private_world.sqlite world_index.sqlite release_state.json \
         software_identity.json b_session_id.txt b_process_id.txt > digests.sha256
cat > digests.json <<EOF
{
  "world_sha256":   "<sha256 of private_world.sqlite>",
  "index_sha256":   "<sha256 of world_index.sqlite>",
  "release_state_sha256": "<sha256 of release_state.json>",
  ...
}
EOF
```

Additionally record:
- final World revision
- final index watermark
- index lag
- number of object revisions
- number of model rounds (mailbox request/reply pairs)
- number of USER turns in B
- number of Wake/Review/Summary cycles processed
- metering totals (token counts, model-call counts per provider/model if available)
- any transparent non-blocking anomalies (e.g. budget-exhausted rounds, retries) and how they were handled

## 10. Verify freeze integrity

- Open the frozen World in a new headless process: `recovery-status` must report `world_quick_check=["ok"]`, `index_lag=0`, `world_revision`/`index_watermark` equal.
- Confirm `release_state.json` shows Phase B completed up to cursor 22, no pending reveal, next_sequence=23 (ready for Phase C).
- Confirm the evidence directory contains NO A transcript/mailbox/log content copied from A-002 (B evidence should contain only B's own mailbox archive plus the shared durable World, which intentionally contains A-era durable cognition).
- Compute final digests once more on a fresh read of the files; they must match the manifest exactly.

## 11. PR preparation

Copy the evidence directory into a new B evidence root (analogous to `C15-RCC-RES-A-RERUN-002/`) in a new PR:

`reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-RERUN-002/freeze/...`
`reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-RERUN-002/mailbox/archive/...`
`reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-RERUN-002/logs/...`
`reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-RERUN-002/freeze/MANIFEST.json`

Do NOT merge this evidence PR. Keep it OPEN / UNMERGED / PINNED, analogous to #205. Independent acceptance (`C15-RCC-RES-B-ACCEPT-002`) will review it before any merge decision.

## 12. STOP

After evidence is written and the PR is opened, report `RUN_COMPLETE / AWAITING_INDEPENDENT_ACCEPTANCE` and stop. Do not proceed to Phase C, semantic evaluation, or any C16/P16/P17 work.
