# C15-RCC-RES-B-RERUN-002 — OPERATOR STOP REPORT

**Report state: `RUN_STATE_TOUCHED / PM_ADJUDICATION_REQUIRED` — operator STOP, no rewind performed.**

Date: 2026-09-26
Role of reporting window: **B-RERUN Operator / Runtime Transport Engineer (OPERATOR ONLY)**
Run ID: `c15-rcc-res-b-rerun-002-65e6e826`
Session ID: `c15-rcc-res-b-session-002-65e6e826`
Canonical run root: `/tmp/c15-rcc-res-b-rerun-002-65e6e826`

This document is written by the operator window to preserve the forensic record across
windows. It changes nothing: no governance writeback, no Core change, no fixture/evaluator
change, no run-state rebuild, no re-reveal, no replay. It is not a PM adjudication.

## 1. What happened (verbatim operator account)

1. Live `main` was re-fetched and read first: `762d06f628be3665212e034551707005a978bd8a`
   ("C15-RCC: release Resident B rerun 002"). Task board confirms
   `C15-RCC-RES-B-RERUN-002 = READY` as the unique READY task.
2. Consumption audit (before any new reveal): the canonical run root did not exist; no
   release-state/current-event/binding/projection/ingest/dispatch/ack traces anywhere; no
   B-RERUN-002 evidence PR; PR #205 head `d17ae972ad1d312735c355f775ac024bc4cebdf7`
   unpolluted. Verdict: run **not consumed** → proceed authorized.
3. Baseline verified: frozen software `773876f92d5f8e53422f8f5a68cc651953d93052`, Core tree
   `fe77f8a0706acfaf369041d0882b6d0e6de39f22` at frozen commit and at live main, zero Core
   diff; A lineage SHA-256 exact:
   World `626c6bb32c7fdae90a068ee10dd2b4c9cdbc46b6feb2bf5b11cba9363401f6aa`,
   Index `ecfabf4eb8261f306b5c9f8a59dae2ef8a1629ddc2823b4311d6adffc3c1e5f1`,
   release-state `eada20a0bf59d1cf25446c0153d1dc719b280627d9e0170364e690e1523391c8`;
   A boundary last-acked 13 / next 14 / pending null; PR #205 blobs byte-identical.
4. Environment established at exact frozen pins: Debian 12, Python 3.11.2, pydantic 2.13.5,
   pydantic_core 2.46.5, annotated-types 0.8.0, typing-inspection 0.4.4,
   typing_extensions 4.16.0; requirements freeze hash
   `bd7a76d1171c137f9daee9c0a3dbff029b8cbbccef88f0a1aff7907710a82375` (exact pinned
   versions installed; no upgrades); contract/wire/adapter/jail SHA-256 all exact.
5. Release entry procedure executed verbatim:
   - §1 run root + byte-exact lineage copy + digest re-verify: PASS.
     B_PROCESS `54fa14fa002342f124a32b37a39dfd8a` (fresh process evidence only).
   - §2 recovery-status: world_revision 98 / index_watermark 98 / lag 0 /
     AUTO_RECOVERABLE / quick_check ok: PASS.
   - §3 `init --phase B`: `active_phase=B`, `next_sequence=14`, `pending_reveal=null`: PASS.
   - §4 sandbox: `ISOLATION_PASS`.
   - §4a frozen E2E probe: `ALL_CHECKS=158/158 FAILURES=0`, `CORRECTIVE_013_E2E_PASS`.
   - §5 exact released identity set (frozen template random B_SESSION line NOT executed).
   - §6 operator HTTPS broker built (TLS via locally-trusted operator CA,
     SAN `broker.c15-b.internal`, bearer auth, request archive, staged-exact-reply
     rendezvous, whitespace keepalive under the frozen client's 10s socket timeout; smoke
     test held 15.0s and round-tripped exact reply bytes; provenance `UNKNOWN`, usage null).
   - Preconditions asserted: `current-event.json` and binding receipt absent.

## 2. Real consumption events that DID occur (cursor 14)

All of the following genuinely happened in this window before the infrastructure failure:

1. **REVEAL** of cursor 14: event `c15rcc-014` (`dim:work_state` / `monitoring` /
   `PLATFORM` / `structured_text`, occurred_at `2026-11-09T09:03:00-08:00`).
   `release_state.pending_reveal` was set by the frozen release operator.
2. **INSTALL_CURRENT_EVENT**: `current-event.json` installed (mode 0400).
3. **PERSIST_PROJECTION_EVIDENCE**: immutable `event-014.projection.json` written (mode
   0400) and digest appended to `projection_digests.sha256`.
4. **CREATE_BINDING_RECEIPT** written and **VERIFY_BINDING** PASS for session
   `c15-rcc-res-b-session-002-65e6e826`.
5. **INGEST** (mechanical): committed `obs_c14_fixture_4c492ea152d135960e96c2d1@1`,
   World revision **99**.
6. **MODEL_WORK start**: frozen `due --at 2026-11-09T09:03:00-08:00` with
   `bridged_model_handler:headless_production_handler` (`ProductionResidentHandler` +
   `ExternalBrokerClient`) produced **one real production provider request**:
   broker-archived as `request-0001-50746053bb76.json`; envelope round=1,
   request_id `50746053bb76440972803d3a9c572fd7`,
   request_digest prefix `c5d3c74094fc1771…`, wake_reason `cognitive_derivation`,
   event field byte-equal to the installed current event (seq 14), contract/wire pins
   verified; 43-entry capability catalog; empty capability history.
7. The Resident relay bundle for that request was prepared for the fresh Resident B window.

**Nothing semantic ever happened**: no Resident reply was ever received, staged, or
committed; no capability was invoked; **no durable ACK was issued**; the release cursor
never advanced (`next_sequence` remained 14; `pending_reveal` for `c15rcc-014` was still
set; binding/current-event were never cleared).

## 3. Infrastructure failure

While the operator waited for the relayed Resident reply, the execution sandbox restarted
(platform-level event between user turns). `/tmp` was wiped; the **entire canonical run
root `/tmp/c15-rcc-res-b-rerun-002-65e6e826` was destroyed**, including the live World
(rev 99), release-state (cursor-14 pending), current-event, binding receipt,
event-014 projection evidence, mailbox request archive, TLS material, and all operator
logs. The broker and the in-flight `due` process were killed. An un-answered provider
request (round 1, request_id above) was outstanding at destruction.

Whether the in-flight `due` run had committed any further World revisions (e.g. a
background-attempt admission) before destruction **cannot be determined** — those bytes
are unrecoverable.

## 4. What survives

- The repository: frozen Core/materials, the accepted A-002 lineage copies at
  `reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-PREFLIGHT-002/lineage_copy/`
  re-verified intact after the incident (SHA-256 unchanged, see §1.3).
- PR #205 remains OPEN / UNMERGED / PINNED at `d17ae972ad1d312735c355f775ac024bc4cebdf7`.
- This incident record (committed on the operator session branch only).

## 5. Why the operator STOPPED

The operator rules for this task state: once any real reveal / pending_reveal /
current-event / binding receipt / immutable projection / cursor ingest / production
model dispatch exists, the operator must not clean, delete, roll back, overwrite, or
"restart"; it must preserve evidence and report
`RUN_STATE_TOUCHED / PM_ADJUDICATION_REQUIRED`, then STOP; unilateral rewind is
prohibited — even where, as here, the destruction came from infrastructure and no
Resident semantics had yet occurred.

Deterministic re-derivation of the pre-model state (lineage → init → reveal → ingest) was
equally **not** executed, because that is precisely a rewind/restart of a genuinely
consumed run, and because the unknowable pre-destruction World tail (§3) cannot be proven
byte-equivalent. The release-record stop conditions also cover this: "inability to persist
required evidence" — the persisted evidence no longer exists.

## 6. Operator-side environment facts (for the adjudicator)

- All installed packages were the exact frozen pins; Core/fixture/governance/evaluator
  files were never modified (working tree clean at the release commit; only this report
  plus the branch pointer differ).
- The canonical run root path is pinned to `/tmp` by the release record; `/tmp` does not
  survive sandbox restarts in this execution environment. This is the mechanical root
  cause of the state loss and is reported as infrastructure reality, not as a decision.
- The operator minted no second run/session identity; the only identity ever used is the
  released pair above. `B_PROCESS=54fa14fa002342f124a32b37a39dfd8a` was process evidence
  only.

## 7. Explicit non-actions attested

- No re-creation of `/tmp/c15-rcc-res-b-rerun-002-65e6e826`.
- No Phase-B re-init, no second reveal, no re-ingest, no handler restart, no broker restart.
- No contact with any Resident/model window carrying this run's payload after the incident.
- No governance writeback, no task board/checkpoint edit, no PR creation, no merge.

**The operator awaits PM adjudication. Nothing further will be executed from this window.**
