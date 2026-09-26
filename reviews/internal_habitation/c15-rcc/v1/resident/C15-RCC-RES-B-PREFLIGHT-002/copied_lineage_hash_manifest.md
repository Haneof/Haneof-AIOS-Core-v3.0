# C15-RCC-RES-B-PREFLIGHT-002 — Copied Lineage Hash Manifest

The directory `lineage_copy/` contains byte-exact copies of the accepted A-002 freeze artifacts. These are provided as a convenience for the B release operator; the canonical truth remains PR #205 `d17ae972ad1d312735c355f775ac024bc4cebdf7`.

```
$ cd reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy
$ sha256sum *
626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa  private_world.sqlite
ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1  world_index.sqlite
eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8  release_state.json
```

All three digests match the accepted #205 freeze digests exactly.

## Release state critical fields (verified)

```json
{
  "active_phase": "A",
  "last_acked_sequence": 13,
  "next_sequence": 14,
  "pending_reveal": null,
  "last_acked_event_id": "c15rcc-013",
  "receipts": [ /* 13 contiguous sequences 1..13 */ ]
}
```

The receipts bind each sequence to a specific fixture projection SHA-256 and a specific World revision; the final receipt (seq 13) is at world revision 98. The receipts chain is contiguous with no skip, reorder, or duplicate.

## What was NOT copied

The following A-002 material is deliberately excluded from the B lineage copy:

- `logs/operator.jsonl`
- `mailbox/archive/` (A's 56 mailbox request/reply pairs)
- `run_output.json` / A run report
- transcript or model-visible prose from A
- due-work ledger
- metering beyond what's already inside the private World
- acceptance report or reviewer notes

B continuity is the durable World + synchronized index + release-state receipt chain, exactly as release_contract §3 specifies.
