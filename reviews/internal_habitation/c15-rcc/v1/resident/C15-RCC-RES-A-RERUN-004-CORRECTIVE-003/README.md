# C15 Resident A — Corrective-003 run evidence (Phase A, cursors 1..13)

Evidence-only package for task `C15-RCC-RES-A-RERUN-004-CORRECTIVE-003`.
No source, fixture, evaluator or release code is included. No private
chain-of-thought is included: only authored directives, capability calls and
results, user-visible responses, durable ingest/ACK/publication receipts and
mechanical digests.

## Run identity

- run_id: `c15-rcc-res-a-rerun-004-corrective-003-348cdba74f64`
- resident_process_id: `231512c3-d418-45ab-b8f9-a81d68213959`
- resident_session_id: `resident-a-c003-49d55cd93f8341e7`
- conversation_session_id: `sess-resident-a-c003-7089564bdf1d`
- subject_id: `user_1`
- phase A cursors durably acknowledged: 13 of 13 (`c15rcc-001` .. `c15rcc-013`)
- cursor 14: never revealed (`run/release-state.json`: `last_acked_sequence` 13, `pending_reveal` null, receipts only 1..13)
- final world revision: 38; final index watermark: 38
- final exchange classification: `COMPLETE` (21/21 model exchanges complete; 0 unconsumed; 0 dispatched-open; ledger integrity ok)

## Frozen identity

- frozen software SHA: `f20f2edfa7af00d0286493fd15196ca9503bc315` (worktree HEAD re-verified)
- frozen repository tree: `1ac3a675b884167d3a29aa432e7ef3eaff94d404`
- frozen core tree: `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`
- frozen tests tree: `7e33b5ef8432370234965d3ccd61248c703c4019`
- frozen core content manifest: `220718d6b5a2650b5e4263bbe8b7e661444cb33b486a7ecd7b5ad3d7d3399caa`
- accepted packet: `3c2d04c2de8557c3cb7329df4350c40b2ccc07520a7d3d51db206174b33266cc`
- operator-prep exact head: `77dac70e0cf054c3f0fb7d94a66dba221fe7d5de`
- harness manifest (file) `2bc303cdc09ea7fff91dd2340d9be2ac4abc810a01ffacf5f39d6d313e8388e8`
- clean-room contract `ed5140bd9719d028744f50e23737b4185c1f4d6efb1234f7d0da857783c7973b`
- run contract `9b8a6cc5641710bef88943279eedc3c8c88959bece0f7a47d4bba08ead470dab`
- qualified runtime: CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1 / OpenSSL 3.0.13

## Layout

- `run/FREEZE_MANIFEST.json` — freeze manifest: identities, digests, per-cursor timeline.
- `run/SESSION_END.json` — session termination record (Resident session ended permanently here).
- `run/RUN_IDENTITY.json`, `run/release-state.json` — run and release identities.
- `run/events/cursor_*.event.json` — the single current event projection per cursor.
- `run/world/*.sqlite` — final private World store and derived search index.
- `run/exchange/` — durable exchange: ledger, published requests, published responses.
- `run/evidence/` — per-cursor ingest receipts, ACK receipts, turn/due results, authored directives, response envelopes, publish receipts.
- `run/evidence/final/` — final state inventory, exchange final state, freeze manifest, session end.
- `run/runtime/` — environment/RC identity records of the qualified runtime used for this run.
- `SHA256SUMS` — digests of every file in this package.

## How to verify

1. `sha256sum -c SHA256SUMS`.
2. Frozen RC: check `run/FREEZE_MANIFEST.json` against the accepted packet pins; re-run the packet-pinned verification command if desired.
3. Exchange: run the accepted harness integrity checker (`aios_exchange.verify.verify_exchange_integrity`) over `run/exchange/`; every request must be `COMPLETE` with request/response/consumed records.
4. Release state: confirm receipts 1..13, `last_acked_sequence` 13 and absence of any sequence-14 receipt.
5. World: the shipped store is at revision 38; the shipped index watermark is 38.
