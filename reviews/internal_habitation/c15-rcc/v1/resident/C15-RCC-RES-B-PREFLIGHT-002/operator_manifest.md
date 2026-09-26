# C15-RCC-RES-B-PREFLIGHT-002 — Operator Manifest (CORRECTIVE-014-FIXUP-005)

Date: 2026-09-26
Role: Release / Test Infrastructure Engineer (not Resident B/C, not evaluator)
Task: `C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-014-FIXUP-005`
Verdict: **CORRECTIVE-014-FIXUP-005 EXACT CANDIDATE — INDEPENDENT ACCEPTANCE REQUIRED BEFORE B RELEASE**. IA review `5320859635` is the source blocker. No B/C run or merge is authorized by this manifest.

## Current authoritative manifest (CORRECTIVE-014-FIXUP-005)

- **Current task**: `C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-014-FIXUP-005`
- **Scope**: close IA-BLK-004 only: shell-dispatch-wrapped duplicate lifecycle operations must count toward exact executable cardinality.
- **C014-FIXUP-005 lifecycle checker blob**: `e031b924db2fa1fd59cda5a2ea52b58b8a86e92b`. The E2E probe and final-freeze procedure remain unchanged from C013.
- **Current exact gate**: `EXPECTED_CHECKS=158`; required `ALL_CHECKS=158/158 FAILURES=0`.
- **Required current markers**: `ENVIRONMENT_PASS`, `RAW_USAGE_NO_SYNTHESIS_PASS`, `CANONICAL_PIN_CONSISTENCY_PASS`, `CANONICAL_PIN_MUTATION_RED_PASS`, `CANONICAL_RUNBOOK_EXECUTABLE_PASS`, `CANONICAL_RUNBOOK_ORDER_PASS`, `RUNBOOK_CROSS_DOCUMENT_ORDER_PASS`, `RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS cases=5`, `RUNBOOK_EXECUTABLE_MUTATION_RED_PASS cases=18`, `RUNBOOK_SHELL_SEMANTICS_MUTATION_RED_PASS cases=82`, final `CORRECTIVE_013_E2E_PASS`.
- **Fresh-run rule**: CORRECTIVE-013 evidence is historical. C014-FIXUP-005 is qualified only by a fresh frozen Debian 12 / Python 3.11.2 run committed byte-exact into `isolation/e2e_probe_output.txt`, with cross-document `5`, executable `18`, shell-semantics `82`, `ALL_CHECKS=158/158 FAILURES=0`, and the zero cursor-14 payload-leak invariant.
- **C012 history**: `corrective_012_report.md` remains unchanged historical `157/157` evidence; its count and old raw-log digest are not current.
- **Local/remote ancestry**: local source `4ad5f980c2a041c88f9c0fdec62753d7f8b38fb4` has tree `a22f14753e0627a95b08cfb8e60ae3ad80304620`; remote parent is `86aafc1937b58071d4780c77cf2e8abe7fcbed5b` with that same tree. PM must build from the remote parent; local ancestry is different.

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

## Historical deliverable index (CORRECTIVE-010 inventory; current gate is CORRECTIVE-014-FIXUP-005)

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
│   ├── mechanical_checks.md             historical evidence + CORRECTIVE-011 exact target
│   ├── canonical_pin_checker.py         strict declaration parser + 11 mutation-red self-tests
│   └── runbook_lifecycle_checker.py     startup/per-cursor ordered-token gate + mutation-red self-tests
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
- At that time, the CORRECTIVE-010/FIXUP-001 gate was recorded as 140/140 + N/N with markers `CORRECTIVE_010_E2E_PASS`, `CANONICAL_RUNBOOK_ORDER_PASS`, `CANONICAL_PIN_CONSISTENCY_PASS`, and `CORRECTIVE_010_FIXUP_001_E2E_PASS`, transport `ExternalBrokerClient`, runbook Section 6 config-only + Section 7 7.1-7.12. This historical claim is not the current gate.

Per FIXUP-001 task §2, this historical block is explicitly labelled and does NOT represent the current release contract.

## Frozen model-handling intent (current invariant, unchanged through CORRECTIVE-014-FIXUP-005)

**Separation:** `SyntheticProbeHandler` (mailbox bridge + inside-jail responder, `sandbox-bridge/synthetic-responder-v1/10 tokens`) vs **`ProductionResidentHandler`** (outside-jail `ProviderClient`, `contract text + envelope` only, real provenance).

**Separation is in code** — not just documentation. Synthetic path is disposable probe; production maps `provider/model/request_id` from the **actual** `ProviderResponse` (or `"UNKNOWN"` where credibly unavailable). Production usage requires provider-reported `total_tokens`; it never computes total from input/output. Missing total, invalid values, or inconsistent totals produce `usage=None`; valid total-only or partial optional fields are preserved exactly.

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

## CORRECTIVE-010-FIXUP-001 fresh run record (historical pre-CORRECTIVE-011 evidence)

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

This FIXUP-001 144/144 run is retained as historical evidence for the parent candidate only. It is NOT fresh execution evidence for CORRECTIVE-011 because the production adapter and probe changed.



## Historical CORRECTIVE-011 implementation delta (retained baseline; unchanged by this fixup)

The three second-acceptance blockers are addressed in code/docs:

1. IA-BLK-001: production usage no longer synthesizes `total_tokens`; `probe_e2e.sh` adds full, missing-total, input-only, output-only, total-only, partial-with-total, inconsistent, invalid-type, and AST source-inspection regressions. Target marker: `RAW_USAGE_NO_SYNTHESIS_PASS`.
2. IA-BLK-002: strict declaration parser factored into `checks/canonical_pin_checker.py`; production gate and self-test invoke the same checker; 9 one-hex mutations plus duplicate-wrong and missing-World cases must all red. Target marker: `CANONICAL_PIN_MUTATION_RED_PASS`.
3. IA-BLK-003: `per_cursor_interaction.md` is synchronized to startup §7, including projection evidence before receipt; both carry identical lifecycle tokens and are checked by `checks/runbook_lifecycle_checker.py`. Target marker: `RUNBOOK_CROSS_DOCUMENT_ORDER_PASS`.

**Evidence rule:** the old committed 144/144 log is historical parent-candidate evidence and is not relabeled as CORRECTIVE-011.

## CORRECTIVE-011 frozen E2E (historical parent evidence, not relabeled)

Parent-candidate run of `isolation/probe_e2e.sh`. The E2E file SHA below is the parent commit's copy, not the current file. The file was later replaced by the CORRECTIVE-012 copy and is now superseded by the fresh CORRECTIVE-013 output. Isolation bytes were not regenerated for this historical C011 record.

| Role | Path | SHA-256 | Result |
| --- | --- | --- | --- |
| raw E2E log | `/tmp/b-preflight-e2e-c011b/e2e.log` | `94f7388ced02512a61a3933648cb520de7cfe74e0ec778887cb7f00a78803ed8` | `ALL_CHECKS=156/156 FAILURES=0` |
| committed E2E copy | `isolation/e2e_probe_output.txt` | `6f860779c08d891bb02c83031e84054481954af3a419207b7063b6df5df34792` | header + raw log |
| raw isolation log | `/tmp/b-preflight-e2e-c011b/isolation_probe.log` | `1bb3a16b97ca61c52a4b7b4a4e31518e7fd5ccfed5c2e146b96a5e73be283c74` | `ISOLATION_PASS` |
| committed isolation copy | `isolation/probe_output.txt` | `167b57e95f8240bca9c3cde7c03eee15fb177f73fc756ccb8b5aebb09858bfe4` | header + raw log |

Markers present in the raw log: `RAW_USAGE_NO_SYNTHESIS_PASS`, `CANONICAL_PIN_CONSISTENCY_PASS`, `CANONICAL_PIN_MUTATION_RED_PASS`, `CANONICAL_RUNBOOK_ORDER_PASS`, `RUNBOOK_CROSS_DOCUMENT_ORDER_PASS`, `RUNBOOK_CROSS_DOCUMENT_MUTATION_RED_PASS`, `CORRECTIVE_011_E2E_PASS`.

Python was `Python 3.11.2`. The disposable reveal printed mechanical metadata only and was never presented to a Resident or model.

## Historical CORRECTIVE-012 fresh frozen E2E (superseded; not current)

Fresh disposable run after closing IA-BLK-003. The lifecycle checker now accepts a projection step only when that step body contains the executable persist commands. The same `check_runbook_lifecycle()` rejects the executable deletions, the post-ACK move, and the comment-hidden receipt-first chain.

| Role | Path | SHA-256 | Result |
| --- | --- | --- | --- |
| raw E2E log | `/tmp/b-preflight-e2e-c012/e2e.log` | `38a414ac1f2600d11efa7eb9179c33bc8133bf06c8668092e032d5b0c86be5a2` | `ALL_CHECKS=157/157 FAILURES=0` |
| historical committed C012 E2E copy (superseded by FIXUP-001) | `isolation/e2e_probe_output.txt` at that time | `8af79734c8e5aebfb10a16c2cb19025f89ff52a1e85c62e60811bf16f91780c9` | historical header + raw log |

Markers present in the raw log: `RAW_USAGE_NO_SYNTHESIS_PASS`, `CANONICAL_PIN_MUTATION_RED_PASS`, `CANONICAL_RUNBOOK_ORDER_PASS`, `RUNBOOK_CROSS_DOCUMENT_ORDER_PASS`, `RUNBOOK_EXECUTABLE_MUTATION_RED_PASS`, `CORRECTIVE_012_E2E_PASS`.

Python was `Python 3.11.2`. The disposable reveal printed mechanical metadata only and was never presented to a Resident or model.

Historical state at the time of C012: `REVIEW_READY / AWAITING_PM_RE-REVIEW`. Current C013 fixup evidence is handoff-ready; PM must rebuild from the remote parent. Do not merge #209, start Independent Acceptance, or enter B release.
