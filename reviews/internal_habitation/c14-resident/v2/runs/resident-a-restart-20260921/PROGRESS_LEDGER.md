# C14-RES-A-001 — run progress ledger (append-only)

Run id: `resident-a-restart-20260921`
Started from main: `87e52bceea4ee94b823200388a4f79b1b94eb1f3` (verified live main at window start)
Session branch: `arena/01a0c473-haneof-aios-core-v3-0`
Resident model (as declared): `GPT-5.6 Sol`; platform provider/session id: `unknown/not exposed`

## Stage table

| Stage | Scope | Status | Evidence |
|---|---|---|---|
| S0 | Recon, READY proof, plan, ledger, bridge, bridge self-test | DONE | `PLAN.md`, `SESSION.md`, `bridge/resident_checkpoint.py` |
| S1 | Fresh World, Phase A init, cursor 1 end-to-end | DONE | `receipts/{reveal,ingest,ack}/cursor-001.json`, `SEMANTIC_TRACE.md` |
| S2..S24 | Cursor 2..24, one stage each | NOT_STARTED | — |
| S25 | Handoff freeze | NOT_STARTED | — |

### S0 notes

- READY proof: `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md` row 17 `C14-RES-A-001 = READY`
  (dependency `C14-RES-FIX-003 = DONE`); live `origin/main` re-fetched at window start.
- Forbidden material was not opened (fixture / manifest / evaluator / FIX completion evidence /
  PM reviews / validation protocol). `FIXTURE_SHA256` above is the digest published in the
  Resident-visible release contract, not read from the sealed fixture.
- Bridge self-test (throwaway world under `/tmp`, no fixture bytes, not evidence):
  - empty-world `init-world` + `process-due` → clean no-op;
  - synthetic Observation in a `/tmp` world → day Summary paused for Resident text → committed
    `sum_...@1` → C14 `cognitive_derivation` Wake scheduled (REALITY lineage, leaf = the synthetic
    Observation) → Wake dispatched → paused for Resident decision → `silence` → Wake COMPLETED
    (`termination_reason=silence`);
  - Periodic Review mechanically became due (3 anchors) → separate checkpoint unit → completed.
  - Confirms: pause/resume, exact-snapshot persistence, capability execution path, wake
    completion, review path and unit separation all work before any real cursor is released.
- Deliberately NOT built: HTTP server, GitHub polling, daemon, RPC, multi-stage bridge.

## Cursor ledger

| Cursor | Event id | Occurred at | Ingest ref | Acked | Due work processed at that time | World rev | Notes |
|---:|---|---|---|---|---|---|---|
| 1 | `c14resv2-001` | 2026-10-01T07:12:00-07:00 | `obs_c14_fixture_b32d3cded992194438f114a9@1` | yes (`next=2`) | Periodic Review due → Resident inspected anchor → **silence**; no Summary window closed yet; no C14 wake | 4 | dim:sleep wearable fact; 0 Claims (silence is valid) |
| 2 | `c14resv2-002` | 2026-10-01T07:48:00-07:00 | `obs_c14_fixture_3195efa3abad26d259380073@1` | yes (`next=3`) | none due (day window open; review not due until 2026-10-02T14:13Z) | 5 | dim:schedule calendar fact |

## Blockers / contamination

- none
