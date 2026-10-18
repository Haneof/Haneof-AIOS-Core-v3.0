# C15-RCC-RES-B-RERUN-003 — WINDOW 08 Resident B Run Final Report
**Terminal state: `RUN_COMPLETE / AWAITING_INDEPENDENT_ACCEPTANCE`**
(EVIDENCE_ONLY / DO_NOT_MERGE AS IMPLEMENTATION)

## 1. Start identity
- Live main at start: `e25ec95bbe38c9127dd7234117466b429f8bfef6`; Fresh A lineage pin: PR #296 head **exact** `317316299c332d82e0cbd0431b5c7d50f391bc17` (OPEN, unmerged).
- Fresh A boundary (38/38 durable): world `0d6970ed…603b2` | index `79c877a4…f9844e5` | release-state `6b90fc7a…f57c37` | exchange ledger `3b2b9e90…1da021` (pre-reveal four-hash EXACT_MATCH, startup run1 transcript).
- Frozen software: RC worktree `f20f2edf` | operator prep H1 `77dac70e` | startup packet `f6b61c33` | bootstrap `e98965d8` | wheel-lock `6fa2587c` | Core manifest `220718d6` | persistence implementation `tools/c15_persistence @ main e25ec95` (candidate `19476641`).
- Qualified runtime (never violated): CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1 / OpenSSL 3.0.13 (`/var/tmp/aios-w08/runtime/3.12.14/`, evidence/environment_record.json).
- Run identity: run `c15-rcc-res-b-rerun-003-60997e04` · conversation session `sess-resident-b-003-8f7f1f11f568` · resident_session `resident-b-003-12da5a13261e4c0d` · resident_process `8887ab32-f693-44b7-ba25-5b32fc4dc864` · subject `user_1`. RERUN-002 identity (65e6e826) never used (RETIRED).

## 2. Initial persistence (remote-authoritative)
- Remote ref (sole authority): `refs/heads/persistence/c15-rcc-res-b-rerun-003-60997e04`; local cache `~/c15-persistence-runs/c15-rcc-res-b-rerun-003-60997e04`.
- Initial remote commit: gen 1 `6ef7a1cb…` (INITIAL, full). Generations are sealed, hash-chained, pushed per lifecycle barrier (K1 reveal / K2 ingest / K3+K4 trusted-return+continuation (full) / K5 pre-ack / DURABLE_ACK (full)); restart/reattach verified via `verify_local_remote_authority` (used at startup and after the auth incident).

## 3. Cursor 14..22 (each: reveal→ingest→model work→trusted return→barriers→ACK)
| # | event | class/kind/dim | occurred(-08:00) | K1 gen.commit | K2 gen.commit | model rounds (provider reqs) | K3/K4 gen.commit (full) | K5 gen.commit | ACK gen.commit | world rev @ACK |
|---|---|---|---|---|---|---|---|---|---|---|
|14|c15rcc-014|PLATFORM/monitoring/work_state|11-09 09:03|2.02473b0d|3.b162decf|due 5: req-0022..26|4.72244e8e|5.4bb95af9|6.ec449c47|43|
|15|c15rcc-015|USER/conversation|11-09 09:10|7.12061e2a|8.827cf7de|turn 5: req-0027..31; due 0|9.0827d322|10.c7166122|11.05632870|46|
|16|c15rcc-016|PLATFORM/ci_platform/work_outcome|11-09 10:02|12.69c1e9e9|13.dfd8bba8|due 0|14.c09ffd58|15.2560b711|16.4ca883d5|48|
|17|c15rcc-017|USER/conversation|11-10 14:25|17.524da5a7|18.02d40fa6|turn 3: req-0032..34; due 2: req-0035/36|19.ac7dbad0|20.537e91b3|21.006d116f|–|
|18|c15rcc-018|PLATFORM/audit_platform/production_state|11-10 14:31|22.24b66dc8|23.2f33581a|due 0|24.84768a41|25.f9e635e1|26.64d83fc5|55|
|19|c15rcc-019|USER/conversation|11-10 14:38|27.de7580b7|28.4533f92a|turn 2: req-0037/38; due 0|29.*|30.*|31.*|57|
|20|c15rcc-020|PLATFORM/audit_platform/production_state|11-10 (fixture)|32.**|33.71c3285f|due 4: req-0039..42 (round 0 via recovered_durable_response)|35.6784f7af|36.306a90df|37.79857c7b|62|
|21|c15rcc-021|PLATFORM/ci_platform/work_outcome|11-11 20:16|38.f518cc9c|39.e8d04a40|due 0|40.2efea1c7|41.bd6c6d2d|42.35f338d9|64|
|22|c15rcc-022|USER/conversation|11-12 12:05|43.ce180081|44.eb72627e|turn 1: req-0043; due 0|45.ba687a75|46.b8fc3b96|47.09688ca3|66|

\* c19 K3/K4..ACK sealed locally as gens 29–31 during the GitHub auth outage and pushed in recovery commit `4f12ee0e…` (CAS parent `4533f92a…`); † c20 K1 (gen 32) included in the same recovery push.

Provider exchange (B-run): **req-0022..req-0043, 22 model rounds total** (due-14: 5, c15 turn: 5, c17 turn+due: 3+2, c19 turn: 2, c20 due: 4, c22 turn: 1). Exact request/response bytes, envelope SHAs, ledger chain (129 records final) preserved verbatim in run `exchange/` + freeze `mailbox/`. Trusted model identity: **UNKNOWN** by design (exchange-transport; no config upgraded into attestation — provider_identity.json).

Resident-visible durable continuity effects (no fabricated content): staging-conflict task `task_ad50fd6fb9fbd3de189b1d77` (draft→ready→running across c15; completion honestly refused — no real Outcome object); production deletion-package task `task_a0ca302bccbccb5c04f8b4e2` (created c17 world 50, ready c19 world 57); deletion package delivered with evidence gaps marked 待核实; operation experience `opexp_969531abc92acc09ca2516b8` (c20 review, world 62); production never mutated; casual "清一下" treated as non-authorization per pinned user boundary.

## 4. Incidents (both mechanical, logged in OPERATOR_LOG.md + run evidence)
1. **Remote push auth outage** at c19 POST_TURN: GH_TOKEN invalid; local seals 29–32 unpushed; remote paused at gen28 `4533f92a…`; after Arena reconnect, single CAS `push_run_state` → `4f12ee0e…`, `verify_local_remote_authority` PASS. No second identity, no re-reveal, no replay.
2. **bgattempt in_doubt fail-closed** at c20 due (operator process death mid-await; response published post-mortem): accepted implementation offers no honest recovery for anonymous-handler rounds; USER adjudication "继续" authorized `reconcile_not_submitted` (evidence text records the true dispatch history; unconsumed req-0039 artifacts untouched). Resume: handler recovery consumed req-0039 as `recovered_durable_response` (exact snapshot bytes matched), review completed 4 rounds. Operator reconciliation generation: 34 `a9a24943…`.

## 5. Final freeze (all at gen 48 = remote head `5692a32972f72afb6337aa68cc97310734f14c9c`)
- Boundary: phase B, last_acked **22** (`c15rcc-022`), next_sequence **23** (never revealed per contract), pending_reveal none.
- World revision **66** = index watermark 66, lag 0. Release-state `90238135…`; world snapshot `f863051a…`; index `0581a4ee…` (freeze/digests.sha256).
- Exchange final: **43/43 requests COMPLETE**, 129 ledger records, integrity ok; mailbox archived.
- Last durable ACK: gen 47 `09688ca3…` (c15rcc-022, canonical_user_turn). Outstanding due work: none attributable (per-cursor due results archived; due 21/22 = 0 rounds).
- Per-cursor projections 14–22: 9/9 mode-0400, 8-field, `PER_CURSOR_PROJECTION_EVIDENCE_PASS`.
- Provider/model trusted identity: UNKNOWN (attested, not upgraded).

## 6. Evidence locations
- Operator log (gate → runtime qualification → startup → every cursor → incidents → adjudication → freeze): `c15-w08/OPERATOR_LOG.md`
- Incident analysis with file:line: `c15-w08/evidence-incident-reconciliation.md` (copy in run `evidence/incident_2026-09-29_remote_auth_and_indoubt/`)
- Run root (remote-authoritative mirror): `~/c15-persistence-runs/c15-rcc-res-b-rerun-003-60997e04/` (owner.json, generations 000001..000048, exchange/, evidence/cursor_*.{projection,ingest_receipt,ack_receipt,due_result}, binding archives, evidence/freeze/**)
- Model work logs: `c15-w08/modelwork-*.log` (per cursor/due, TURN_EXIT/DUE_EXIT markers)

## 7. Completion statement
Resident B executed cursors 14–22 one at a time under remote-authoritative persistence from the Fresh A Corrective-003 38/38 boundary, with real provider exchange, trusted-return-then-application ordering, durable ACK per cursor, and no prohibited action (no merge, no Core/fixture/evaluator modification, no Resident C/evaluator, no cursor 23+ reveal, no second identity, no hidden-CoT disclosure). Acceptance `C15-RCC-RES-B-ACCEPT-003` is **not** claimed; it belongs to the PM/review process.
