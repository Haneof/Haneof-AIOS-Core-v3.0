# C15-RCC-RES-B-PREFLIGHT-002 — Operator Manifest (CORRECTIVE-010 authoritative, CORRECTIVE-003 historical superseded)

Date: 2026-09-25
Role: Release / Resident Infrastructure Engineer (not Resident B/C, not evaluator — per CORRECTIVE-010-FIXUP-001)
Task: C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-010-FIXUP-001
Verdict: **REVIEW_READY / AWAITING_PM_RE-REVIEW** (no B or C run, no merge)

## Current authoritative manifest (CORRECTIVE-010 + FIXUP-001) — this is the ONLY release contract

- **Current Task**: `C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-010-FIXUP-001`
- **Current Verdict**: `REVIEW_READY / AWAITING_PM_RE-REVIEW`
- **Final gate (CORRECTIVE-010 base)**: `ALL_CHECKS=140/140 FAILURES=0`, marker `CORRECTIVE_010_E2E_PASS`
- **New regression marker (CORRECTIVE-010)**: `CANONICAL_RUNBOOK_ORDER_PASS` — proves the documented 1→12 order executes on a disposable Phase-B copy and reaches provider transport only after reveal + receipt installation
- **New gate (FIXUP-001)**: `CANONICAL_PIN_CONSISTENCY_PASS` — proves `operator_manifest.md`, `source_pins_and_digests.md`, `procedure/b_startup_procedure.md` agree on World/Index/Release and equal frozen canonical values; any missing/typo/duplicate contradictory → FAIL
- **Final gate (FIXUP-001)**: `ALL_CHECKS=N/N FAILURES=0` where N is recomputed from the executable (not mechanically retained 140), must include `CANONICAL_RUNBOOK_ORDER_PASS`, `CANONICAL_PIN_CONSISTENCY_PASS`, `CORRECTIVE_010_E2E_PASS` and `CORRECTIVE_010_FIXUP_001_E2E_PASS`
- **Current production transport**: `ExternalBrokerClient` (transport-only HTTPS, no semantic Atlas/silence choice; `FakeProviderClient` unreachable from production entrypoint; `FakeBrokerServer` is test-only)
- **Current final runbook semantics**:
  - **Section 6 is configuration only**: exports/pins `B_PREP`, `HARNESS_DIR`, `AIOS_B_SESSION_ID`, `AIOS_CONTRACT_SHA256`, `AIOS_WIRE_PROTOCOL_SHA256`, `AIOS_ADAPTER_SHA256` (drift grep vs `environment_manifest.md`), `AIOS_REAL_PROVIDER_API_KEY`, `AIOS_REAL_PROVIDER_ENDPOINT` (HTTPS), `AIOS_PROVIDER_ADAPTER=bridged_model_handler:ExternalBrokerClient`, `AIOS_RELEASE_STATE_PATH`, `AIOS_CURRENT_EVENT_PATH`, `AIOS_CURRENT_EVENT_BINDING_PATH`, `AIOS_EVIDENCE_DIR`, `PYTHONPATH="src:$B_PREP/harness"`. Then fail-closed assertions that `current-event.json`, `current-event-binding.json` and non-null `pending_reveal` are absent. States verbatim: «No model dispatch occurs in this section. The first production model turn occurs only inside the per-cursor loop after reveal + binding receipt installation.» No `CURRENT_OCCURRED_AT`, no `--at`, no `turn --session`.
  - **Section 7 is the sole legal per-cursor loop** as numbered steps **7.1–7.12** in exact order: reveal → write `current-event.json` → persist immutable `event-XXX.projection.json` → create `current-event-binding.json` via `create_current_event_binding_receipt(...)` → `write_binding_receipt(...)` → verify receipt/state/event binding via `validate_current_event_binding` → derive `CURRENT_OCCURRED_AT` from current projection's `occurred_at` (after reveal) → ingest current cursor → run exact production headless turn / due/model rounds → finish all model work for cursor → durable ACK → clear current-event + binding → reveal next cursor before any later model invocation.

**Operator MUST NOT mistake historical CORRECTIVE-003 / 26-check material for the current release contract.** Historical sections below are explicitly labelled `historical / superseded`.

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
| private_world.sqlite | 790528 | `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa` | PASS |
| world_index.sqlite | 811008 | `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1` | PASS |
| release_state.json | 10841 | `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8` | PASS |

Source blobs: `git show d17ae972ad1d312735c355f775ac024bc4cebdf7:reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002/freeze/<file>`
Core tree identity verified at all three relevant commits (frozen software `773876f`, publication base, evidence head `d17ae97`) and at current main HEAD `aa19af1`.

Canonical cross-document pins (must be identical in `operator_manifest.md`, `source_pins_and_digests.md`, `procedure/b_startup_procedure.md`):

- World: `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa`
- Index: `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1`
- Release: `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8`

These are recomputed from the byte-exact lineage copy (`lineage_copy/`) and match the accepted A-002 evidence.

## Deliverable index (CORRECTIVE-010 authoritative)

```
reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/
├── operator_manifest.md                 (this file — CORRECTIVE-010 authoritative, FIXUP-001 current)
├── source_pins_and_digests.md           exact #205 source pins/digests (World/Index/Release canonical)
├── lineage_copy/                        byte-exact copy of accepted A freeze
│   ├── private_world.sqlite             626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa
│   ├── world_index.sqlite               ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1
│   └── release_state.json               eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8
├── copied_lineage_hash_manifest.md
├── resident_safe_packet_manifest.md     sandbox RO/RW/IPC/NET invariants (CORRECTIVE-010)
├── environment_manifest.md              env allowlist + PATH + stripped vars
├── harness/
│   ├── resident_jail.py                 OS sandbox (NEWNS|NEWPID|NEWNET, PID1 supervisor, minimal /dev, fail-closed, _close_inherited_fds)
│   ├── mailbox_bridge.py                transport-only allowlist + path-aware leakage guard + reply binding (strict)
│   ├── bridged_model_handler.py        FROZEN production (ProductionResidentHandler + ExternalBrokerClient + binding receipt) + synthetic probe
│   └── resident_wire_protocol.json      a6bbeaef4aab369ef23659a1ce46df24b970fd48176edc8feb78b9f62228ff3a
├── isolation/
│   ├── isolation_report.md              OS isolation proof
│   ├── probe_isolation.sh               isolation probe (ISOLATION_PASS 58 PASS)
│   └── probe_e2e.sh                     genuine FusedTurnRuntime/CognitiveRuntime→Handler→Bridge→Responder E2E (CORRECTIVE-010 140/140, FIXUP-001 N/N)
├── checks/
│   └── mechanical_checks.md             positive/negative mechanical check results (CORRECTIVE-010 140-check, FIXUP-001 N-check)
├── procedure/
│   ├── b_startup_procedure.md           exact B startup (Section 6 config-only, Section 7 7.1-7.12 per-cursor loop, HTTPS-only, canonical pins)
│   ├── per_cursor_interaction.md        exact per-cursor 14..22 loop — Scheme A (no repair)
│   └── final_freeze_procedure.md        B final freeze/evidence
├── identity_inventory.md                model/provider identity — UNKNOWN or real provider (fake-provider preflight)
├── known_limitations.md                 CORRECTIVE-010 limitations
├── corrective_002_report.md             prior corrective evidence (preserved, historical)
├── corrective_003_report.md             CORRECTIVE-003 E2E evidence (historical, superseded — 26-check, CORRECTIVE_003_E2E_PASS)
├── corrective_009_report.md             CORRECTIVE-009 E2E evidence (closed BLK-01/02/04/05/06/07/08)
├── corrective_010_report.md             CORRECTIVE-010 E2E evidence (closed BLK-03, CORRECTIVE_010_E2E_PASS + CANONICAL_RUNBOOK_ORDER_PASS)
└── completion_report.md
```

## Historical / superseded: CORRECTIVE-003 frozen (26-check) — retained for lineage but NOT current release contract

The following material was the CORRECTIVE-003 frozen deliverable index (26 checks). It is **historical / superseded** and must NOT be mistaken for the current CORRECTIVE-010 authoritative contract.

```
Historical CORRECTIVE-003 (superseded):
├── operator_manifest.md                 (was CORRECTIVE-003 frozen, 26-check)
├── isolation/probe_e2e.sh               (was 26 checks)
├── checks/mechanical_checks.md          (was 26-check)
└── completion_report.md
```

- Old header: `CORRECTIVE-003 frozen`
- Old check count: 26
- Old marker: `CORRECTIVE_003_E2E_PASS`
- Current authoritative is CORRECTIVE-010 (140/140) + FIXUP-001 (N/N), markers `CORRECTIVE_010_E2E_PASS`, `CANONICAL_RUNBOOK_ORDER_PASS`, `CANONICAL_PIN_CONSISTENCY_PASS`, `CORRECTIVE_010_FIXUP_001_E2E_PASS`, transport `ExternalBrokerClient`, runbook Section 6 config-only + Section 7 7.1-7.12.

Per FIXUP-001 task §2, this historical block is explicitly labelled and does NOT represent the current release contract.

## Frozen model-handling intent (current, CORRECTIVE-010)

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
- The disposable reveal projection was never presented to a Resident or model and its payload bytes are not in current evidence (CORRECTIVE-009 / BLK-01).
- Environment manifest frozen; `PYTHONPATH=/repo/src`, `contract_sha256`, `b_session`, `AIOS_MAILBOX_ROOT` pinned.

## CORRECTIVE-010 fresh run record (base, retained)

Two fresh runs of `isolation/probe_e2e.sh` (from the repo root under `sudo`) were used for CORRECTIVE-010:

| Role | Raw log | Raw log SHA-256 | Result |
| --- | --- | --- | --- |
| committed evidence source | `/tmp/probe_c10_run8.log` | `3d0308b6c19bdc2d502f37aca025e586238d61f7e848d817258ecf296147ffc2` | `ALL_CHECKS=140/140 FAILURES=0` |
| final confirmation (with the committed evidence + all docs in place) | `/tmp/probe_c10_run9.log` | `b48fcad7a9869f1708396d1230f70c4e9dc6fc937bd50cb64f11657ab81a5c45` | `ALL_CHECKS=140/140 FAILURES=0` |

| Item | Value |
| --- | --- |
| e2e_probe_output.txt SHA-256 | `1e10d5392efc3c397061850462a2fb8861610fbdd3fe27984df8e13e14254760` |
| probe_output.txt SHA-256 | `a1566ada961426eac1c451a107bd11e213fd8a77482bae5fd6172c77af466ff1` |
| marker | `CORRECTIVE_010_E2E_PASS` |
| new regression marker | `CANONICAL_RUNBOOK_ORDER_PASS` |

`isolation/probe_output.txt` is regenerated from a fresh in-sandbox run of
`isolation/probe_isolation.sh` via `harness/resident_jail.py` (`ISOLATION_PASS`, 58 PASS / 0 FAIL).

The digests above are recomputed on every run and are **not** trusted from this document;
`procedure/b_startup_procedure.md` recomputes the adapter SHA with `sha256sum` and fails closed if it
drifts from `environment_manifest.md`, and `isolation/probe_e2e.sh` re-derives the contract and wire
digests at runtime.

## CORRECTIVE-010-FIXUP-001 fresh run record (current authoritative)

Fresh run of `isolation/probe_e2e.sh` after fixing World SHA typo and adding pin-consistency gate:

| Role | Raw log | Raw log SHA-256 | Result |
| --- | --- | --- | --- |
| FIXUP-001 committed evidence source | `/tmp/probe_fixup1_final.log` | `700c80603b16c07c7cb10ebd4c192f6611a3da89247a749d64bc2044ebc31f7c` | `ALL_CHECKS=144/144 FAILURES=0` |

| Item | Value |
| --- | --- |
| e2e_probe_output.txt SHA-256 | `809107aa1a6a0dffdc248b813ee832ec9aaeecaf775c9fe9876401b954fcef83` |
| probe_output.txt SHA-256 | `ace17baddf9901b56f2d334bd68ede1620be84627c9edda2265dd40d00634473` |
| markers | `CORRECTIVE_010_E2E_PASS`, `CANONICAL_RUNBOOK_ORDER_PASS`, `CANONICAL_PIN_CONSISTENCY_PASS`, `CORRECTIVE_010_FIXUP_001_E2E_PASS` |
| EXPECTED_CHECKS | 144 (recomputed, not mechanically retained 140) |
| Result | `ALL_CHECKS=144/144 FAILURES=0` |

- **Canonical pins verified**:
  - World: `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa` (64-char, byte-exact from `lineage_copy/private_world.sqlite`)
  - Index: `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1`
  - Release: `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8`
- **Cross-document consistency**: `operator_manifest.md`, `source_pins_and_digests.md`, `procedure/b_startup_procedure.md` all contain the three canonical digests and no contradictory/typo/duplicate values → `CANONICAL_PIN_CONSISTENCY_PASS`
- **Production transport**: `ExternalBrokerClient` (HTTPS-only, transport-only, no semantic stub)
- **Runbook**: Section 6 config-only, Section 7 7.1–7.12 per-cursor loop (reveal → event → projection evidence → receipt → verify → derive CURRENT_OCCURRED_AT → ingest → production headless turn → ACK → clear → reveal next)

The previous erroneous World SHA (66-char with extra c9) was a typo and has been corrected to the canonical 64-char value above. The erroneous 66-char value is no longer present in any of the three canonical docs; the pin-consistency gate would FAIL if it reappeared.

This FIXUP-001 run is the current authoritative evidence; the CORRECTIVE-010 base run (140/140) is retained as historical but superseded by this 144/144 run.

