# C15-RCC-RES-B-PREFLIGHT-002 — Operator Manifest (CORRECTIVE-003 frozen)

Date: 2026-09-25
Role: Release / Resident Infrastructure Engineer (not Resident B/C, not evaluator — per CORRECTIVE-003)
Task: C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-003
Verdict: **REVIEW_READY** (await PM re-review; no B or C run)

## Scope

Non-Resident mechanical preparation of the Phase B handoff from independently accepted Fresh A-002 (PR #205, Frozen RC) on the frozen RC. Per CORRECTIVE-003 preflight prompt §15, this manifest stops at REVIEW_READY:

- NO Resident B was run
- NO cursor 14 was revealed to a model. Preflight's disposable `reveal --phase B` ran on a copied release state for the mechanical `init → reveal → receipt → handler` proof; the projection was never presented to a Resident/model and its payload bytes are not in current evidence (CORRECTIVE-009 / BLK-01).
- NO Resident C was run
- NO Core (`src/aios_core/`) was modified
- NO modification was made to PR #205 (OPEN / UNMERGED / PINNED)
- NO A transcript / mailbox prose / decisions / evaluator notes are present in the B-safe packet
- NO `src/aios_core` change, no fixture/evaluator/governance change, no merge of PR #209
- PR #209 branch `arena/01a0d692-haneof-aios-core-v3-0` preserves historic candidates `3796377 / 7902367 / ee5e4a4`, live main `aa19af1` — no force/rebase

## Pins (exact — recomputed SHA-256 from #205 artifacts; STOP if diverged)

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
| Phase B bounds (not yet executed) | cursors 14..22 (single cursor revealed per turn) |

## Freeze digests (recomputed from #205 Git blobs — not trusted from filenames)

| Artifact | Bytes | SHA-256 | Verified |
| --- | ---: | --- | --- |
| private_world.sqlite | 790528 | `626c6bb32c7fdae90a068ee10dd2b4c9c9cdbc46b6feb2bf5b11cba9363401f6aa` | PASS |
| world_index.sqlite | 811008 | `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1` | PASS |
| release_state.json | 10841 | `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8` | PASS |

Source blobs: `git show d17ae972ad1d312735c355f775ac024bc4cebdf7:reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002/freeze/<file>`
Core tree identity verified at all three relevant commits (frozen software `773876f`, publication base, evidence head `d17ae97`) and at current main HEAD `aa19af1`.

## Deliverable index (CORRECTIVE-003 frozen)

```
reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/
├── operator_manifest.md                 (this file)
├── source_pins_and_digests.md           exact #205 source pins/digests
├── lineage_copy/                        byte-exact copy of accepted A freeze
│   ├── private_world.sqlite
│   ├── world_index.sqlite
│   └── release_state.json
├── copied_lineage_hash_manifest.md
├── resident_safe_packet_manifest.md     sandbox RO/RW/IPC/NET invariants (CORRECTIVE-003)
├── environment_manifest.md              env allowlist + PATH + stripped vars (NEW)
├── harness/
│   ├── resident_jail.py                 OS sandbox (NEWNS|NEWPID|NEWNET, PID1 supervisor, minimal /dev, fail-closed)
│   ├── mailbox_bridge.py                transport-only allowlist + path-aware leakage guard + reply binding (strict)
│   └── bridged_model_handler.py        FROZEN production + synthetic handlers (ProductionResidentHandler vs SyntheticProbeHandler, ProviderClient, UNKNOWN)
├── isolation/
│   ├── isolation_report.md              OS isolation proof (15 self-tests + 6 binding + minimal /dev + MS_PRIVATE + signal strict)
│   ├── probe_isolation.sh               isolation probe
│   └── probe_e2e.sh                     genuine 2-round FusedTurnRuntime/CognitiveRuntime→Handler→Bridge→Responder E2E (26 checks)
├── checks/
│   └── mechanical_checks.md             positive/negative mechanical check results (26-check)
├── procedure/
│   ├── b_startup_procedure.md           exact B startup (no model peek, env allowlist, frozen adapter)
│   ├── per_cursor_interaction.md        exact per-cursor 14..22 loop — Scheme A (no repair)
│   └── final_freeze_procedure.md        B final freeze/evidence
├── identity_inventory.md                model/provider identity — UNKNOWN or real provider (fake-provider preflight)
├── known_limitations.md                 CORRECTIVE-003 limitations (NET sealed, production roundtrip, etc.)
├── corrective_002_report.md             prior corrective evidence (preserved)
├── corrective_003_report.md             CORRECTIVE-003 E2E evidence (CORRECTIVE_003_E2E_PASS)
└── completion_report.md
```

## Frozen model-handling intent (BLOCKER 1)

**Separation:** `SyntheticProbeHandler` (mailbox bridge + inside-jail responder, `sandbox-bridge/synthetic-responder-v1/10 tokens`) vs **`ProductionResidentHandler`** (outside-jail `ProviderClient`, `contract text + envelope` only, real provenance).

**Separation is in code** — not just documentation. Synthetic path is disposable probe; production path is frozen for real B and maps `provider/model/request_id` from the **actual** `ProviderResponse` (or `"UNKNOWN"` where credibly unavailable) and `usage` from actual `usage.total_tokens` (or `None`, never `10`). PR-approval-time choice phrase removed.

**Phase B adapter is frozen** (`bridged_model_handler.py`) before B run. Operator cannot swap model logic at release. The only production transport is `ExternalBrokerClient`; there is no `RealProviderClient`, and `FakeProviderClient` cannot be instantiated at all (its `__init__` raises), so no fake path is reachable from the production entrypoint.

## Transport authority (fail-closed)

MailboxBridge validates `event` exactly 8 fields + `sequence 14..22` + `phase B` + `allowed_sequences [14,22]` + capability_history B-session only + forbid path prefixes (`/repo/fixture`, `/repo/evaluator`, `/repo/governance`, `/repo/.git`, `/release/`, sealed fixture) — **not bare `fixture`** (legal World `obs_c14_fixture_*` allowed; probe now search `Atlas` non-empty). Top-level allowlist of 11 fields, request binding `round/request_id/nonce/request_digest`, reply strict per-action allowlist and binding echo (`stale/future/replay/wrong-id/wrong-digest/future-becomes-valid` all fail closed).

## Isolation invariants (proven)

- `CLONE_NEWNET` — no public internet (ENETUNREACH), provider via outside broker only.
- `CLONE_NEWPID` fresh `/proc`, PID1 `sandbox-init` reaps/forwards, worker `PID≥2`.
- `CLONE_NEWNS` mount private fail closed; RO bind `ro,nosuid,nodev` (EROFS probe).
- Mailbox IPC: `inbox 0755/outbox 01733/archive 0700 not mounted`, `nobody:nogroup` honors, private MS drop strip.
- `/dev` minimal (tmpfs + `null/zero/urandom/random`), signal strict, env allowlist (PROBE_* stripped unless explicitly passed).
- **Inherited FDs closed** before `execvpe` (`_close_inherited_fds`): operator-held sealed-fixture / evaluator-only descriptors are not readable inside the jail via `/dev/fd/N` (gate `INHERITED_FD_SEALED_PASS`).

## Preflight rules observed

- Operator role transport only; harness env run is `unshare+chroot+drop` (prompt-only never counted).
- Cursor 14 never revealed to a real model during preflight. Synthetic disposable projections (`synthetic-fixture-seq-14`, 8-field shape + negatives) are used for transport tests; the single real disposable reveal is metadata-only in the committed log.
- `init --phase B` validates receipt-chain only, does not emit or peek at payload.
- The one disposable reveal is **not** a Resident reveal: it runs on a copied release state under `/tmp` and is reduced to `DISPOSABLE_REVEAL seq=… event_id=… projection_sha256=… payload_sha256=… field_count=…` in the committed log.
- Environment manifest frozen; `PYTHONPATH=/repo/src`, `contract_sha256`, `b_session`, `AIOS_MAILBOX_ROOT` pinned.

## CORRECTIVE-010 fresh run record

| Item | Value |
| --- | --- |
| probe | `isolation/probe_e2e.sh` (run from the repo root under `sudo`) |
| raw log | `/tmp/probe_c10_run8.log` -> copied to `isolation/e2e_probe_output.txt` |
| raw log SHA-256 | `3d0308b6c19bdc2d502f37aca025e586238d61f7e848d817258ecf296147ffc2` |
| e2e_probe_output.txt SHA-256 | `1e10d5392efc3c397061850462a2fb8861610fbdd3fe27984df8e13e14254760` |
| probe_output.txt SHA-256 | `a1566ada961426eac1c451a107bd11e213fd8a77482bae5fd6172c77af466ff1` |
| result | `ALL_CHECKS=140/140 FAILURES=0` |
| marker | `CORRECTIVE_010_E2E_PASS` |
| new regression marker | `CANONICAL_RUNBOOK_ORDER_PASS` |

`isolation/probe_output.txt` is regenerated from a fresh in-sandbox run of
`isolation/probe_isolation.sh` via `harness/resident_jail.py` (`ISOLATION_PASS`, 58 PASS / 0 FAIL).

The digests above are recomputed on every run and are **not** trusted from this document;
`procedure/b_startup_procedure.md` recomputes the adapter SHA with `sha256sum` and fails closed if it
drifts from `environment_manifest.md`, and `isolation/probe_e2e.sh` re-derives the contract and wire
digests at runtime.
