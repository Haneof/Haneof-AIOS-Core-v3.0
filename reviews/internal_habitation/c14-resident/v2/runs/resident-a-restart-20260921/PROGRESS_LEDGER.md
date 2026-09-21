# C14-RES-A-001 — run progress ledger (append-only)

Run id: `resident-a-restart-20260921`
Started from main: `87e52bceea4ee94b823200388a4f79b1b94eb1f3` (verified live main at window start)
Session branch: `arena/01a0c473-haneof-aios-core-v3-0`
Resident model (as declared): `GPT-5.6 Sol`; platform provider/session id: `unknown/not exposed`

## Stage table

| Stage | Scope | Status | Evidence |
|---|---|---|---|
| S0 | Recon, READY proof, plan, ledger, bridge, bridge self-test | DONE | `PLAN.md`, `SESSION.md`, `bridge/resident_checkpoint.py` |
| S1 | Fresh World, Phase A init, cursor 1 end-to-end | NOT_STARTED | — |
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

| Cursor | Event id | Revealed | Ingested (ref) | Acked | Due work processed | World rev | Notes |
|---:|---|---|---|---|---|---|---|
| 1 | — | — | — | — | — | — | — |

## Blockers / contamination

- none
