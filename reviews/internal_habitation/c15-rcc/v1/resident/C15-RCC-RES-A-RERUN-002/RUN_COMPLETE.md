# C15-RCC-RES-A-RERUN-002 — RUN_COMPLETE

State: `RUN_COMPLETE / AWAITING_INDEPENDENT_ACCEPTANCE`

This is Fresh Resident A, Phase A only (cursors 1..13). The next task is `C15-RCC-RES-A-RERUN-002-ACCEPT-001`. Resident B was not run. Core, tests, workflows, constitution, and the RC packet were not modified.

## Identity

| Field | Value |
| --- | --- |
| task | `C15-RCC-RES-A-RERUN-002` |
| subject_id | `user_1` |
| session_id | `c15-rcc-res-a-rerun-002-2079f64af49c` |
| process_identity | `2079f64af49c406895541da042bf2192` |
| frozen software SHA | `773876f92d5f8e53422f8f5a68cc651953d93052` |
| Core tree | `fe77f8a0706acfaf369041d0882b6d0e6de39f22` |
| world_revision | 98 |
| index_watermark | 98 |
| last clock | `2026-11-06T19:10:00+00:00` |

## Freeze

Immutable copies and digests live under `freeze/`:

- `freeze/MANIFEST.json`
- `freeze/digests.json`
- `freeze/private_world.sqlite` (Core `backup_world`)
- `freeze/world_index.sqlite` (SQLite online backup after `catch_up`)
- `freeze/release_state.json`

Live World SHA-256 and freeze backup SHA-256 may differ; the freeze copy is the coherent snapshot. Both report world revision 98 / index watermark 98 / `PRAGMA quick_check = ok`.

## Sequential ACKs

| seq | event | ingest_ref | path |
| --- | --- | --- | --- |
| 1 | c15rcc-001 | `obs_conv_user_e3f254f5a3f691c9f1ae5870@1` | canonical conversation turn 1 |
| 2 | c15rcc-002 | `obs_c14_fixture_5248cdfd5a23b6ea88ce0a96@1` | mechanical |
| 3 | c15rcc-003 | `obs_conv_user_c4bef35968765b7f621c3ab2@1` | canonical conversation turn 2 |
| 4 | c15rcc-004 | `obs_c14_fixture_5d4dfcf42055c00135a78a54@1` | mechanical |
| 5 | c15rcc-005 | `obs_conv_user_d4953379e0fd7ae84b9a27ee@1` | canonical conversation turn 3 |
| 6 | c15rcc-006 | `obs_conv_user_76b4c03c31db54c18b1f02ee@1` | canonical conversation turn 4 |
| 7 | c15rcc-007 | `obs_c14_fixture_87474a7fb5036c38638a6c37@1` | mechanical |
| 8 | c15rcc-008 | `obs_conv_user_10c0bcfb2f7bf80aa9b324b8@1` | canonical conversation turn 5 |
| 9 | c15rcc-009 | `obs_c14_fixture_b798e2dbd5b0fabdec6680a2@1` | mechanical |
| 10 | c15rcc-010 | `obs_conv_user_fbe20407ffd68ca6f1bc5f5c@1` | canonical conversation turn 6 |
| 11 | c15rcc-011 | `obs_c14_fixture_291beec37165eb34a35f8f85@1` | mechanical |
| 12 | c15rcc-012 | `obs_conv_user_e0dbe4b6cc248f47e013943c@1` | canonical conversation turn 7 |
| 13 | c15rcc-013 | `obs_c14_fixture_e2c76be3450b6e9dc8316b9d@1` | mechanical |

No cursor beyond 13 was revealed. USER acknowledgements reuse session `c15-rcc-res-a-rerun-002-2079f64af49c` and turn indices 1..7.

## Preserved traces

- `receipts/` — ingest, ACK, due-work, and USER turn receipts
- `logs/operator.jsonl` — transport log
- `mailbox/archive/` — mailbox request/reply bytes
- `checkpoints/cursor_01.json` … `cursor_13.json`
- `events/cursor_01.json` … `cursor_13.json` — resident-visible projections only

This process/session is ended. Independent acceptance should use the freeze snapshot, not a live restart of this operator.
