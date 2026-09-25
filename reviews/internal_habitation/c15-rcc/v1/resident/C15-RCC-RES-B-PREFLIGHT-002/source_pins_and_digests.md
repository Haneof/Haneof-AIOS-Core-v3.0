# C15-RCC-RES-B-PREFLIGHT-002 — A-002 Source Pins & Digests

Recomputed directly from Git blobs at exact evidence head `d17ae972ad1d312735c355f775ac024bc4cebdf7` (PR #205), plus CORRECTIVE-009 harness digests from the current candidate tip. Commands used:

```
git fetch origin pull/205/head:pr205
git show pr205:reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002/freeze/<file> > /tmp/<file>
sha256sum /tmp/<file>
```

## Core tree identity

| Commit | src/aios_core tree |
| --- | --- |
| frozen software `773876f92d5f8e53422f8f5a68cc651953d93052` | `fe77f8a0706acfaf369041d0882b6d0e6de39f22` |
| PR #205 head `d17ae972ad1d312735c355f775ac024bc4cebdf7` | `fe77f8a0706acfaf369041d0882b6d0e6de39f22` |
| publication base `4d9f04711769737219d921c8187fc8f52e7d0d6a` | `fe77f8a0706acfaf369041d0882b6d0e6de39f22` |
| current main HEAD `811ae85cc34257475d8723f28b82c01bc8f3b405` | `fe77f8a0706acfaf369041d0882b6d0e6de39f22` |

Core identity at all four commits is byte-identical.

## Freeze artifact digests

| File | Bytes | SHA-256 | Expected (from acceptance receipt) | Result |
| --- | ---: | --- | --- | --- |
| `freeze/private_world.sqlite` | 790528 | `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa` | `626c6bb3...01f6aa` | MATCH |
| `freeze/world_index.sqlite` | 811008 | `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1` | `ecfabf4...1e5f1` | MATCH |
| `freeze/release_state.json` | 10841 | `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8` | `eada20a...391c8` | MATCH |

## World content verified

- `PRAGMA quick_check` → `ok`
- `world_meta.world_revision` = 98
- 13 receipts in `release_state.json`, sequences 1..13 contiguous
- `last_acked_sequence` = 13, `next_sequence` = 14, `pending_reveal` = null, `active_phase` = "A"
- last world commit (revision 98) is a mechanical C14 fixture ingest (cursor 13), as documented in the A acceptance report

## Index content verified

- `PRAGMA quick_check` → `ok`
- `search_meta.search_watermark_world_revision` = 98
- Index lag = 0 (verified via headless recovery-status on a disposable copy)
- Index rebuild from World truth yields watermark 98, 245 indexed rows

## Session / identity

See `freeze/identity.json` at the same PR #205 path:
- subject: `user_1`
- session: `c15-rcc-res-a-rerun-002-2079f64af49c`
- process_identity: `2079f64af49c406895541da042bf2192`
- phase: A
- 13 ACK sequences, zero pending reveal

These identities are intentionally NOT reused for Resident B (fresh session/process will be minted at B start).

## Software identity

`freeze/software_identity.json` pins the frozen Core and execution adapter identity. This file is preserved but is not a trusted model-provider attestation (see identity_inventory.md).

## Pinned external identities (unchanged by CORRECTIVE-009)

| Object | SHA-256 |
| --- | --- |
| frozen software (runtime) | `773876f92d5f8e53422f8f5a68cc651953d93052` |
| Core tree `src/aios_core` | `fe77f8a0706acfaf369041d0882b6d0e6de39f22` |
| PR #205 head | `d17ae972ad1d312735c355f775ac024bc4cebdf7` |
| lineage World | `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa` |
| lineage Index | `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1` |
| lineage Release state | `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8` |
| Resident B run contract | `28d3262f56b7ef93a32a842f1d4d66f99748f2b07adcece43e815eb9d5cd18ef` |

Authoritative pin declarations. Every World/Index/Release occurrence above must equal these values; a correct hash elsewhere does not excuse a wrong declaration:

- World: `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa`
- Index: `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1`
- Release: `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8`
| resident wire protocol | `a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a` |

CORRECTIVE-009 and CORRECTIVE-010 did not touch `src/aios_core/**`, the sealed fixture, the evaluator, the governance
directory, the run contract or PR #205. The runtime/Core/lineage pins above are re-asserted by the
probe gate (`PIN_*` checks) on every run.

## Harness digests at the CORRECTIVE-010 tip

| File | Role | Notes |
| --- | --- | --- |
| `harness/bridged_model_handler.py` | Phase B adapter | BLK-04/05/06/08 changes |
| `harness/resident_jail.py` | sandbox wrapper | BLK-07 `_close_inherited_fds()` |
| `harness/bridged_model_handler.py` | Phase B adapter | **byte-identical** across CORRECTIVE-009 and CORRECTIVE-010 (CORRECTIVE-010 changes no code path) |
| `harness/mailbox_bridge.py` | transport binding | unchanged in CORRECTIVE-009 |

Both digests are computed **mechanically** at probe runtime (they are not trusted from this document);
`procedure/b_startup_procedure.md` recomputes `AIOS_ADAPTER_SHA256` with `sha256sum` and fails closed if
it drifts from `environment_manifest.md`.
