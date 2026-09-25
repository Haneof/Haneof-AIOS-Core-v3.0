# C15-RCC-RES-B-PREFLIGHT-002 — Operator Manifest

Date: 2026-09-25
Role: Release / Test Infrastructure Engineer (Sealed Resident Infrastructure Designer)
Task: C15-RCC-RES-B-PREFLIGHT-002
Verdict: **REVIEW_READY** (see completion_report.md)

## Scope

Non-Resident mechanical preparation of the Phase B handoff from independently accepted Fresh A-002 (PR #205) on the frozen RC. Per section 15 of the preflight prompt, this manifest stops at REVIEW_READY:

- NO Resident B was run
- NO cursor 14 was revealed to a model
- NO Resident C was run
- NO Core was modified
- NO modification was made to PR #205
- NO A transcript / mailbox prose / decisions / evaluator notes are present in the B-safe packet

## Pins

| Item | Value |
| --- | --- |
| frozen execution software | `773876f92d5f8e53422f8f5a68cc651953d93052` |
| frozen Core tree (src/aios_core) | `fe77f8a0706acfaf369041d0882b6d0e6de39f22` |
| canonical A evidence PR | #205 (OPEN / UNMERGED / PINNED) |
| exact A evidence head | `d17ae972ad1d312735c355f775ac024bc4cebdf7` |
| A session | `c15-rcc-res-a-rerun-002-2079f64af49c` |
| A process identity | `2079f64af49c406895541da042bf2192` |
| A World revision at freeze | 98 |
| A index watermark at freeze | 98 |
| index lag at freeze | 0 |
| last ACK sequence | 13 |
| next sequence | 14 |
| pending reveal | null |
| Phase A bounds | cursors 1..13 (7 USER turns + 6 mechanical non-conversation) |
| Phase B bounds (not yet executed) | cursors 14..22 |

## Freeze digests (recomputed from #205 Git blobs — not trusted from filenames)

| Artifact | Bytes | SHA-256 | Verified |
| --- | ---: | --- | --- |
| private_world.sqlite | 790528 | `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa` | PASS |
| world_index.sqlite | 811008 | `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1` | PASS |
| release_state.json | 10841 | `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8` | PASS |

Source blobs: `git show d17ae972ad1d312735c355f775ac024bc4cebdf7:reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002/freeze/<file>`

Core tree identity verified at all three relevant commits (frozen software, publication base, evidence head) and at current main HEAD `811ae85cc34257475d8723f28b82c01bc8f3b405`.

## Deliverable index

```
reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/
├── operator_manifest.md               (this file)
├── source_pins_and_digests.md         exact #205 source pins/digests
├── lineage_copy/
│   ├── private_world.sqlite           byte-exact copy of accepted A freeze
│   ├── world_index.sqlite             byte-exact copy of accepted A freeze
│   └── release_state.json             byte-exact copy (active_phase=A, ack=13, next=14)
├── copied_lineage_hash_manifest.md    hash manifest for the copied lineage
├── resident_safe_packet_manifest.md   what goes into the Resident-visible sandbox
├── isolation/
│   ├── isolation_report.md            OS-level isolation proof
│   └── probe_isolation.sh             sandbox probe used during preflight
├── harness/
│   ├── resident_jail.py               Linux mount-namespace chroot sandbox builder
│   └── mailbox_bridge.py              transport-only mailbox (no semantics)
├── checks/
│   └── mechanical_checks.md           positive/negative mechanical check results
├── procedure/
│   ├── b_startup_procedure.md         exact B startup procedure (not executed)
│   ├── per_cursor_interaction.md      exact per-cursor interaction procedure
│   └── final_freeze_procedure.md      B final freeze/evidence procedure
├── identity_inventory.md              trustworthy model/provider identity (UNKNOWN)
├── known_limitations.md
└── completion_report.md
```

## Preflight rules observed

- operator only; no Resident cognition was executed.
- All mechanical checks used disposable copies of the freeze artifacts; the canonical #205 evidence was read but not modified.
- Sandbox isolation uses Linux mount namespaces + chroot + uid drop (not prompt-only).
- Transport (mailbox bridge) performs zero semantic judgment; validates only JSON shape.
- Cursor 14's resident-visible payload was NOT released or inspected during this preflight. The `init --phase B` command only validates receipt-chain integrity and phase transition; it does not emit or peek at the next event payload.
