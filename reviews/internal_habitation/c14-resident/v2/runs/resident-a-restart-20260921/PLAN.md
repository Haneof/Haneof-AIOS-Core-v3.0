# C14-RES-A-001 — Resident A restart run plan

> Task: `C14-RES-A-001` (governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md row 17, READY)
> Role: **actual Resident AI** in this window (not test programmer / Life Director / Evaluator)
> Access class: RESIDENT_VISIBLE
> Fixture: v2 only (`sha256:1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253`)
> Phase: A only, cursors 1..24
> Run id: `resident-a-restart-20260921`
> Prior setup attempts explicitly abandoned (not inherited): `c14/resident-a-sol-20260921-2036`,
> `c14/resident-a-sol-run-20260921`, `c14/resident-a-sol-ci-20260921`, draft PR #74.
> This run starts a **fresh private World**, fresh release state and fresh evidence directory.

## 1. Non-negotiable boundaries

- Cursor 1..24 only. `reveal --phase A` at 25 is forbidden and is never called.
- Every event enters the World only through `release_operator.py reveal` → `mechanical_ingest_adapter.py`
  → `release_operator.py ack --world-db <private>`. No fixture reading, no preview, no hand-made refs.
- All semantic decisions (Summary text, capability choice, Claim/revise/retract/silence, Answer or not)
  are made by the Resident model in this window, at explicit checkpoints.
- No program may map keywords to cognition, rank importance, write Summary text, or pick directives.
- Forbidden material is never opened: `v2/fixture/sealed_fixture.json`, `v2/fixture/fixture_manifest.json`,
  `v2/evaluator/**`, `C14_RES_FIX_00{2,3}_COMPLETION_EVIDENCE*`, `reviews/C14_RES_FIX_00{1,2,3}_PM_*`,
  `governance/C14_REAL_RESIDENT_VALIDATION_PROTOCOL_2026-09-21.md`, Resident-B/evaluator artifacts.
- No `main` / task-board mutation: this window never marks `C14-RES-A-001 = DONE` and never touches
  `C14-RES-B-001`. An evidence PR may be opened but must not be merged by this window.

## 2. Mechanism: one synchronous checkpoint at a time (no polling bridge, no daemon)

`bridge/resident_checkpoint.py` is a thin, non-semantic test-side bridge (contract §11). It may only:

1. instantiate the real `SQLiteWorldStore` / `WorldSearchIndex` / `FusedTurnRuntime`;
2. serialize the exact `RuntimeSnapshot` or `DimensionSummaryInput` it is handed;
3. pause;
4. accept the decision the Resident model personally writes to a file;
5. feed that exact decision back into the real runtime;
6. execute exactly the capability calls the Resident chose;
7. persist capability results and audit receipts.

It contains no semantic rule of any kind. There is no HTTP server, no GitHub polling, no RPC,
no background daemon beyond one bounded "process this cursor's due work" command.

### Checkpoint protocol

- A unit of work = one `RuntimeSnapshot` (a wake) or one `DimensionSummaryInput` (a summary).
- When the real runtime needs model output, the bridge writes
  `checkpoints/snapshots/<unit>/round-<n>.json` (exact snapshot) and `round-<n>.md` (readable),
  logs `AWAITING_DECISION`, and waits.
- The Resident writes `checkpoints/decisions/<unit>/round-<n>.json`:
  - `{"capability_calls": [{"name": ..., "arguments": {...}}]}` — request capabilities, **or**
  - `{"response": "..."}` — answer, **or**
  - `{"silence": true}` — valid successful silence.
  No `usage`/`provenance` is fabricated (the platform exposes no provider/session id).
- Summaries: bridge writes `checkpoints/summaries/<key>/INPUT.{json,md}` and waits for
  `checkpoints/summaries/<key>/summary.txt`, which the Resident authors.

## 3. Normal AIOS processing after each durable ack (contract §6)

For simulated time `T` = the released event's `occurred_at`:

1. `index.catch_up()`;
2. run the real reality→watch hook over the exact durable Observation
   (`AttentionWatchService.evaluate_observation`) — this is the same listener the real
   ingest path calls, so Resident-authored AttentionWatch intents stay live; the C14
   release path itself must not be re-routed through `RealityIngestService`;
3. `FusedTurnRuntime.run_due_dimension_summaries(now=T)` — mechanical windows/dimensions,
   Resident-authored text;
4. `CognitiveDerivationScheduler.reconcile()` then drain eligible Wakes with
   `FusedTurnRuntime.dispatch_next_pending_wake(now=T+61s)` (61s = the runtime's own
   BACKGROUND coalescing window, so a Wake created at `T` is dispatchable at `T+61s`),
   repeating until nothing is dispatchable or the bounded cap is hit;
5. `FusedTurnRuntime.run_periodic_review(now=T+61s)` — whatever the normal policy makes due;
6. persist status evidence (world revision, index watermark, wake/summary/cognition refs).

Only work due at the current simulated time is processed. Nothing from the future is precomputed.

## 4. Stage plan (one stage = one durable commit)

| Stage | Content | Stop condition |
|---|---|---|
| S0 | Recon + READY proof + this plan + progress ledger + bridge implementation + bridge self-test on a throwaway World | plan committed |
| S1 | Fresh private World + Phase A init + cursor 1: reveal → ingest → ack → index catch-up → due processing (summary + C14 wakes with real model decisions) → evidence | `reveal/ingest/ack/cursor-001` artifacts exist |
| S2..S24 | One stage per cursor N (2..24): reveal → ingest → ack → due processing → evidence → commit | cursor N fully processed |
| S25 | Handoff freeze: World/release-state SHA256, refs, watermark, manifest, semantic trace, final report | frozen, no cursor 25 |

If cursor 1 cannot run: save the exact blocker and stop (contract §20).

## 5. Evidence layout

```
reviews/internal_habitation/c14-resident/v2/runs/resident-a-restart-20260921/
  PLAN.md                     this plan
  PROGRESS_LEDGER.md          per-stage ledger (append-only)
  SESSION.md                  model identity / environment facts (no fabrication)
  bridge/resident_checkpoint.py
  world/aios_world.db         private SQLite World (+ -wal/-shm while live)
  release/release_state.json  Phase A release state
  checkpoints/snapshots/...   exact RuntimeSnapshots + DimensionSummaryInputs
  checkpoints/decisions/...   Resident-written decisions / summary text
  checkpoints/results/...     capability results per unit
  receipts/reveal|ingest|ack|cursor-<NNN>.json
  audit/session.log           append-only JSONL
  handoff/                    frozen World/state digests, refs, manifest, semantic trace
```

Private chain-of-thought is never saved. Only observable decisions and durable refs are.

## 6. Model identity (contract §13, task §16)

- Declared Resident identity: `GPT-5.6 Sol`.
- Platform-exposed provider/model/session id: `unknown/not exposed` — no provider-signed
  provenance is invented; `ModelUsage`/`ModelCallProvenance` are omitted rather than fabricated.
