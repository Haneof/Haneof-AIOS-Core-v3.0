# C15-RCC-RES-A-RERUN-003 — Fresh Resident A Run Evidence

Status: **RUN_COMPLETE / AWAITING_INDEPENDENT_ACCEPTANCE**

Role of author: Real Resident AI — Fresh Resident A (this very session). Every cognitive
decision in this run was made personally by the Resident AI from the current
RuntimeSnapshot and legal AIOS capability evidence at the moment it was requested.
Scripts only transported bytes (release, ingest, ack, headless CLI invocation, and a
file-based model-handler bridge that serializes snapshots verbatim and applies exactly
the directive bytes the Resident wrote back).

---

## 1. Frozen execution software identity

| Item | Value |
|---|---|
| Frozen execution software (checkout SHA) | `27a21db5b656d441248b9240020910b66a223830` |
| Frozen Core tree (`src/aios_core`) | `a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6` |
| Frozen tests tree (`tests`) | `92fcbcc5876833735fb3cb7c73a98c4a8a4a3541` |
| Verified at | `/home/user/a003_exec` detached worktree, pre-run identity check PASS |
| Runtime environment | CPython 3.12.14 (source build; sqlite3 amalgamation 3.53.4 static), pydantic 2.13.5 |

Not used as execution software: governance main `7549322681ada61ab6d3c6eee5082acc00a658d6`,
PR #232 merge SHA `4cadc1a8d7952363e213958c71a63ae7da93f615`, PR #234 governance merge
`7549322...`. The governance main working tree was used only for the two permitted
pre-run governance reads (task board + current checkpoint) and later only as the
evidence host repository.

## 2. Fresh identities (no historical reuse)

| Item | Value |
|---|---|
| Run identity | `a003run-01c3a44b-35b2-4344-a62c-9bd772913308` |
| Resident session identity | `resident-a003-0f5ffeff-3d67-4e06-be86-aa83bbea6ad0` |
| Subject | `user_1` |
| Fresh World path (live) | `/home/user/a003_run/world/resident_a003_world.db` |
| Fresh index path (live) | `/home/user/a003_run/world/resident_a003_world.db.search.sqlite` |
| Fresh release state (live) | `/home/user/a003_run/release/a003_release_state.json` |
| Fresh process identities | one frozen `aios-core-headless` CLI process per operation; PIDs in `trace/ops/*.out` |
| Process model | mechanical bridge module `/home/user/a003_run/driver/resident_bridge.py` (transport only, zero cognition) |

`A-RERUN-002 = NOT REUSED`. No A-002 World, search index, release-state, runtime
state, transcript, claims, revisions, capability choices, or semantic outputs were
accessed, read, or copied. No old World was truncated/reset to masquerade as fresh:
every path above was newly created for A-003. Prior Resident evidence remains
historical prior-RC evidence only.

## 3. Sequential release, ingest, and durable acknowledgement (cursor 1..13)

- Release operator: `init --phase A` then exactly one `reveal` per cursor, strict
  sequential order 1→13, no reorder, no batch reveal, no peeking.
- USER conversation events (c15rcc-001/003/005/006/008/010/012) went through the
  canonical conversation ingest only, bound to the fresh session id and positive
  turn indexes 1..7.
- Non-conversation events (c15rcc-002/004/007/009/011/013) went through the
  mechanical ingest adapter only.
- Each cursor was acknowledged with the exact durable `ingest_ref`; USER
  acknowledgements additionally bound the matching session id and turn index.
- **Durable ack count: 13/13. Final acknowledged cursor: 13 (`c15rcc-013`).**
- Release state after the run: `last_acked_sequence: 13`, `next_sequence: 14`,
  `pending_reveal: null`.
- **CURSOR 14 = NOT REVEALED. Cursor 14+ reveal count: 0. No B-phase request.**

USER canonical ingest result: 7/7 canonical USER Observations created
(`idempotent_replay: false` at ingest); all 7 subsequent ordinary `run_turn`
executions reused the same subject/session/turn/text/event-time and
`user_observation_id` matched the canonical object every time
(`obs_conv_user_4c8e9b2b…`, `…927ee5cc…`, `…f7b830f2…`, `…d146b330…`,
`…393d2be7…`, `…454b6873…`, `…23578647…`). No duplicate USER Observation was
manufactured at any point.

## 4. Normal life: due work actually processed

Virtual/runtime time was advanced exactly to each released event timestamp before
processing; `due` was mechanically executed at every released timestamp (transport
cannot be skipped even when empty).

| Cursor | Released at (UTC) | Due work processed |
|---|---|---|
| 1 | 2026-11-02T17:05Z | turn 1 (5 model rounds); Periodic Review #1 `wake_review_da0d6bc64619…` completed (`responded`) |
| 2 | 2026-11-02T17:14Z | due empty (platform observation durable @ rev 10) |
| 3 | 2026-11-02T17:20Z | turn 2 (2 rounds); due empty |
| 4 | 2026-11-02T20:40Z | due empty (CI merge outcome durable @ rev 15) |
| 5 | 2026-11-02T20:52Z | turn 3 (2 rounds); due empty |
| 6 | 2026-11-03T18:15Z | turn 4 (2 rounds); Periodic Review #2 `wake_review_03edc6752a3d…` completed (found+fixed stale task next_step → `waiting_user`) |
| 7 | 2026-11-04T21:30Z | Periodic Review #3 `wake_review_8901873e11f0…` completed (build READY_FOR_UPLOAD: no completion claim written — queued ≠ uploaded) |
| 8 | 2026-11-04T21:42Z | turn 5 (1 round): answered registry question strictly from evidence |
| 9 | 2026-11-04T22:17Z | due empty (registry rejection durable @ rev 32) |
| 10 | 2026-11-04T22:24Z | turn 6 (2 rounds): evidence-discipline rule fixed into protocol claim rev 6; checksum-mismatch rejection reported |
| 11 | 2026-11-04T23:02Z | due empty (PUBLISHED with tag+digest durable @ rev 36) |
| 12 | 2026-11-04T23:07Z | turn 7 (1 round): timeline reconciliation with full provenance |
| 13 | 2026-11-06T19:10Z | Periodic Review #4 `wake_review_0b6afd10fd74…` completed; final `due` re-check empty |

- **Wake count:** 4 wakes dispatched, all `periodic_review` source, all `completed`
  (12 wake object revisions total). No non-conversation interrupt/background wakes
  fired; no attention watches were created (none were warranted by released reality).
- **Review count:** 4 periodic reviews, all completed with `responded` termination.
- **Summary/derivation records:** 0 round summaries were due (deterministic
  continuity scheduling never triggered a summary window within 7 turns);
  derivation happened through standard ingest (canonical observations) and
  Resident cognition writes (claims/task), all durable in World.
- Final `due` at cursor-13 timestamp: empty. No remaining due work.

## 5. Model decisions — all made personally by the Resident

- **Model request count: 25** (bridge decisions `dec-00003` … `dec-00027`;
  15 `user_interaction` + 10 `periodic_review` per durable metering).
- 11 terminal `response` directives; 14 capability-request rounds; zero `silence`
  (no moment warranted it); UNKNOWN was never needed — every request had sufficient
  released evidence.
- **Capability trace count: 17 executed calls** — `commit_claim` ×1,
  `create_task` ×2 (1 structured enum error used as evidence, then corrected),
  `transition_task` ×5 (2 structured errors — illegal enum / illegal
  `running→ready` — honored, never forced), `revise_claim` ×5,
  `read_periodic_review_anchors` ×4. Failed calls were kept as structured evidence;
  no retry-until-success or state forcing.
- Durable cognition produced: protocol claim `clm_d5f6cb68fdb74636f46360e7`
  (rev 1→6, each revision evidence-ref'd to the exact released observations),
  engagement task `task_835d0a7919485a65096f04ba` (draft→ready→running→waiting_user,
  deadline 2026-11-16T09:05:00-08:00). No cognition was manufactured to satisfy any
  quota; the runbook DRAFT v1 (cursor 13) deliberately produced **no** claim
  (draft ≠ reviewed/executed/accepted).
- Raw request/decision pairs: `trace/model/dec-00003…dec-00027-request.json` /
  `-decision.json` (120 hashed files including ops traces).
- Provenance: every directive carries
  `provider="arena-agent-mode"`, `model="resident-a-fresh-instance"`,
  `request_id="a003run-01c3a44b-decNNNNN"`. Usage token counts were **not** fabricated
  (usage omitted rather than invented). **Metering: 25 durable `metering_records`**
  (15 user_interaction + 10 periodic_review), 25/25 background model attempts in
  `metered` state, **25/25 authenticated response receipts**, all bound to exact
  attempt identities.

## 6. Recovery / restart record (real events, frozen machinery only)

Two real process failures occurred at cursor 1, before any provider bytes crossed
the bridge; both were recovered through the frozen Core recovery APIs only
(`reconcile_turn_model_not_submitted` → `authorize_turn_retry` → ordinary rerun):

1. Bridge counter file missing → handler died pre-serialization; attempt
   `bgattempt_e70cedf7…` reconciled `not_submitted` (`safe_to_retry`), retry
   authorized with truthful evidence.
2. Bridge internal NameError in sequence counter → same reconciliation path,
   bridge unit-verified, retry authorized.

No HMAC authority secret was read; no recovery database was manipulated; no staged
response or receipt was minted; the trusted background response recovery path was
never bypassed (it was never triggered — no dispatch ever became in-doubt after a
submission). Final turn 1 state: `completed`, `retry_count: 2`, full evidence chain
in `trace/ops/cursor-001-*`. All 25 attempts ended `metered`.

## 7. Frozen evidence artifacts (this PR, directory `reviews/internal_habitation/c15-rcc/v1/resident/a003/`)

| Artifact | SHA-256 |
|---|---|
| `world/resident_a003_world.db` (exact fresh private World, final rev 42) | `3de9e73883f2676390436090eed0e4964b2e1ad71c79b5d9cc0ffb03a12862ad` |
| `world/resident_a003_world.db.search.sqlite` (fresh search index, watermark 42, lag 0) | `38193612a9ff256bef9fdd0014db5d0e1faa68745107cb79ef165a6a067e48d4` |
| `release/a003_release_state.json` (13 receipts, next=14) | `7728b12e0ff50f63446966f300ef5fd685668d1a7cf04b911de3d429003849e9` |
| `backup/resident_a003_world_backup.db` (frozen-CLI coherent backup, `AUTO_RECOVERABLE`, quick_check `ok`) | `6d442d5a671e48d7964a8bb4c6ccbd1b9c42a0b276c1b8f73dd21f6912afa95f` |
| `events/cursor-001..013.json` (released projections, byte-exact) | see `SHA256SUMS` |
| `trace/ops/*` (reveal/ingest/ack/turn/due/recovery/inspect logs) | see `SHA256SUMS` |
| `trace/model/*` (raw RuntimeSnapshot requests + Resident decision bytes) | see `SHA256SUMS` |
| `manifest/run_manifest.json` | see `SHA256SUMS` |
| `SHA256SUMS` (120 files) | — |

Final runtime state: world_revision 42, index_watermark 42, index_lag 0,
recovery_disposition `AUTO_RECOVERABLE`, world_quick_check `ok`, schema_version 1.

## 8. Contamination verdict

- Forbidden paths (`fixture/**`, `evaluator/**`, `release/**` sources, historical
  Resident artifacts, evaluator notes, acceptance reports, future cursors, PR/CI
  materials) were never opened, searched, quoted, or diffed. Release tooling was
  executed by path only; only `--help` output was ever displayed.
- No cursor ≥ 14 was revealed or requested. No B-phase material accessed.
- No script decided any cognition: the bridge fails closed (timeout) without a
  Resident-written decision file; every directive byte originated from the Resident.
- No old World/index/release-state/session was reused or reset.
- **RUN_CONTAMINATED: NO.**

## 9. Boundary statement

This Resident run is complete and permanently stops here. No Independent Acceptance,
no self-acceptance, no B/C work, no RELEASE-003, no persistence-corrective resume,
no C15 closure was performed by this window. Next task:
`C15-RCC-RES-A-RERUN-003-INDEPENDENT-ACCEPTANCE` in a new independent window.

READY_FOR_C15-RCC-RES-A-RERUN-003-INDEPENDENT-ACCEPTANCE
