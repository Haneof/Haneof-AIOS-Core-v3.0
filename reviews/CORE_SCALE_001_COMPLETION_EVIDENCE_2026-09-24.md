# CORE-SCALE-001 Completion Evidence — 2026-09-24

Status: **REVIEW_READY**  
Task: `CORE-SCALE-001`  
Role: Performance / Scale Engineer  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Engineering PR: #197  
Author merge authority: **NONE — fresh Independent Acceptance required**

## 1. Exact pins and scope

- Construction live main: `3fe3c924fd855251e8fe195486a072ddf5d86169`
- Final tested implementation exact head: `ba23767d4c1565fbe494419dd01c32123495884c`
- Evidence-only handoff: the commit that updates only this completion-evidence file from the tested exact head; its exact SHA is pinned in PR #197 metadata/body and the author handoff after GitHub creates the commit.
- Live main was re-fetched before final evidence write and remained `3fe3c924fd855251e8fe195486a072ddf5d86169`.
- Start-state confirmation: `CORE-SCALE-001 = READY`.
- Historical PR #112 was read only as risk evidence. No #112 number was treated as current acceptance evidence.
- Initial scale measurement was performed before any `src/aios_core/**` repair.
- No Resident was run.
- No `CORE-RC-FREEZE-001`, UI, hardware, task-board, or checkpoint work was performed.

The final tested head differs from the previously green implementation head
`ddc378571393ca2d2e65c9a4754f988a5a2b6278` only in scale evidence/tests/workflow
coverage; there is **no Core source diff** between those heads. The final head was
nevertheless re-measured and re-regressed directly.

## 2. Frozen measurement contract

The thresholds below were frozen before current-main measurement and were not moved after seeing results.

### S10K

- `core_context` p95 <= 0.75 s
- `snapshot` p95 <= 1.5 s
- broad `recall_candidates(limit=20)` p95 <= 1.0 s
- no operation peak-RSS delta > 512 MiB
- no fixed top-k search may issue > 200 SQL statements

### S100K

- `core_context` p95 <= 2.0 s
- `snapshot` p95 <= 5.0 s
- broad `recall_candidates(limit=20)` p95 <= 2.5 s
- peak RSS for each measured retrieval <= 1.5 GiB above steady baseline
- broad top-k recall SQL statements <= 500
- SQL count must not grow linearly with candidate hit count in an N+1 pattern

### S1M

- must complete construction and required retrieval probes under a 4 GiB process/cgroup memory envelope without OOM
- `core_context` p95 <= 10 s
- `snapshot` p95 <= 20 s
- broad `recall_candidates(limit=20)` p95 <= 10 s
- retrieval peak RSS <= 3.0 GiB
- fixed top-k recall SQL statements <= 1,000
- an environment unable to provide the declared 4 GiB envelope is an explicit failure; the corpus may not be silently reduced

### Cold/restart

S100K:
- current World+index process open p95 <= 3 s
- stale-valid index catch-up p95 <= 10 s
- World/index revision must remain correct
- startup must not eagerly deserialize the whole World into Python

S1M:
- current World+index cold open must complete without OOM
- recorded against the existing 20 s safety window
- no hidden full-World Python materialization merely to open Core

### Due-work/backlog

- 1,000 due mechanical records minimum
- due discovery p95 <= 2 s
- bounded 100-item mechanical orchestration overhead <= 5 s
- no loss, duplication, or starvation
- backlog durable across restart

## 3. Reproducible benchmark harness and corpus

Harness:
- `tools/core_scale_001_bench.py`
- workflow: `.github/workflows/core-scale.yml`

Measurement properties:
- deterministic synthetic/mechanical data only
- monotonic clock
- SQLite trace callbacks for statement counts
- Linux RSS sampling
- JSON + CSV machine-readable evidence
- no Resident semantics
- no provider/model quality shortcut
- provider tokens/cost: **UNKNOWN**

Corpus:
- **S10K**: 10,000 current Claims, 500 EvidenceSets, 200 Dependencies, representative Claim revisions; production `WorldSearchIndex.rebuild/catch_up`
- **S100K**: 100,000 current Claims, 5,000 EvidenceSets, 2,000 Dependencies, representative Claim revisions; production `WorldSearchIndex.rebuild/catch_up`
- **S1M**: 1,000,000 current Claim payloads plus representative prior revisions in the authoritative World. For fixture-construction practicality the S1M search projection is mechanically loaded into the same rebuildable search schema; the measured recall path is the production `recall_candidates` path and World remains the sole truth.
- AI-world domains: round-robin across all eight `AIWorldDomain` values
- subject distribution: `user_1` for user-scoped domains; `ai_agent_self` for AI-self domains
- broad recall token: deterministic 1% hit distribution
- representative current/inactive/revision filtering
- context output cardinality remains bounded: core_context 9, snapshot 80, recall 20

## 4. Current-main H1–H4 reproduction verdicts

Current-main Core was measured before repair. Historical #112 was not copied forward.

| Risk | Verdict | Current-main red evidence |
|---|---|---|
| H1 — AI-world `current()/core_context` full-Claim extraction | **REAL_SCALE_GAP** | S100K core_context p95 5.390459 s > 2 s; S1M core_context MemoryError under explicit 4 GiB |
| H2 — `snapshot()` repeated domain scans | **REAL_SCALE_GAP** | S100K snapshot p95 18.980603 s > 5 s; S1M snapshot MemoryError |
| H3 — `recall_candidates()` candidate-level N+1 SQL | **REAL_SCALE_GAP** | S10K 405 SQL > 200; S100K 4007 SQL > 500; S1M 40005 SQL > 1000 |
| H4 — 1M Claim memory/OOM boundary | **REAL_SCALE_GAP** | 1M construction/open succeeded, but required AI-world reads MemoryError; recall p95 10.333786 s and 40005 SQL also exceeded budget |

Cold open itself was not the blocker and was not redesigned.

## 5. Preserved baseline red evidence

Baseline scale run:
- workflow run `36007169180`
- source PR head: `4f87f85e8fb942a17b4b3d1a99fc648c4c5ff5a9`
- Core source at that head: zero diff from construction main `3fe3c924...`

Red/green baseline jobs:
- S10K job `107658209951`, artifact `10810314921`: **FAIL** — recall SQL 405 > 200
- S100K job `107658209966`, artifact `10811291681`: **FAIL** — core_context 5.390459 s; snapshot 18.980603 s; recall SQL 4007
- S1M job `107658209894`, artifact `10810777415`: **FAIL** under explicit 4 GiB RLIMIT_AS — core_context MemoryError; snapshot MemoryError; recall 10.333786 s; recall SQL 40005
- backlog job `107658209549`, artifact `10811056029`: **PASS** — therefore no Wake/backlog performance repair was justified

These artifacts remain unchanged. No failure was rewritten as green history.

## 6. Minimum semantics-preserving repair

Only paths tied to reproduced H1/H2/H3 were changed.

### `src/aios_core/storage/sqlite_store.py`

Added bounded authoritative read surfaces:
- `iter_latest_payloads(...)`: streams newest visible World revisions instead of whole-World `fetchall`
- `get_payloads_for_ids(...)`: batch newest-visible World lookup in bounded SQLite chunks

Both read the existing authoritative `object_revisions` table. No cognition truth table, second World, or authoritative cache was added.

### `src/aios_core/runtime/turn_runtime.py`

`_KnowledgeCutoffStoreView` forwards both bounded readers while forcibly injecting the same execution-time knowledge cutoff. FIX-001 is preserved rather than bypassed.

### `src/aios_core/ai_world/cognition.py`

- payload-to-view parsing was factored without changing Claim meaning
- `current()` uses the streaming World reader and preserves typed filtering/order/limit
- `core_context()` and `snapshot()` use one partitioned stream instead of repeated full-World extraction
- user-scoped subject authority and AI-self continuity remain unchanged

### `src/aios_core/query/search.py`

`recall_candidates()`:
- retains Search as a rebuildable candidate projection only
- batch-loads projection rows
- batch-verifies current/historical payloads against authoritative World
- preserves current revision selection, historical cutoff, inactive filtering, subject/dimension/object-type/time filters, ordering, limit, and watermark behavior
- removes candidate-count-proportional N+1 World/SQLite queries

### Deliberately rejected extra work

An additional index/alternate read plan was introduced concurrently after the minimum repair was already green. It was explicitly reverted by `f52828c79ebfe58ac770c77bde62f8294b58d233`. The final Core source tree stays on the smaller already-proven repair.

No schema-version bump was made.

## 7. Final exact-head scale results

Final tested exact head:
`ba23767d4c1565fbe494419dd01c32123495884c`

Final dedicated scale workflow:
- run `36010524179` — **SUCCESS**
- semantic-equivalence job `107669725864` — SUCCESS
- S10K job `107669725857` — SUCCESS
- S100K job `107669725608` — SUCCESS
- S1M job `107669726285` — SUCCESS
- backlog job `107669725454` — SUCCESS

Artifacts:
- S10K `10811919909`, digest `sha256:9d0edc5f4008f5381e0912335b51b046fd6dd07e10b9c425df19a201ab83bdc3`
- S100K `10812028094`, digest `sha256:24873e6450e4bfbeb227c12e9125df028228a449da97c7e27e99b743dada5530`
- S1M `10812297630`, digest `sha256:3e0d01dbef217a02996b7a0f8d0b7c2a254052257695c3a2fc86af63056be5f1`
- backlog `10812900428`, digest `sha256:a66fbae8d05d9d1989bbda74e21ab65580079dfdf737d6458fff1e6bc03815b1`

| Tier | core_context p50 / p95 | snapshot p50 / p95 | broad recall p50 / p95 | recall SQL max | retrieval memory | Result |
|---|---:|---:|---:|---:|---:|---|
| S10K | 0.028651 / 0.028980 s | 0.035100 / 0.035462 s | 0.003435 / 0.003817 s | 6 | max measured delta <= 36,864 B; absolute peak ~66 MB | **PASS** |
| S100K | 0.258031 / 0.263890 s | 0.323743 / 0.328971 s | 0.023533 / 0.024714 s | 10 | max measured delta 36,864 B; absolute peak ~109 MB | **PASS** |
| S1M | 4.149921 / 4.195750 s | 5.651428 / 5.682172 s | 0.428666 / 0.432998 s | 54 | recall delta 44,953,600 B; absolute recall peak 117,997,568 B | **PASS** |

Every frozen latency, SQL, RSS, and OOM budget passes. No threshold moved.

## 8. S1M capacity / 4 GiB proof

Current exact-head S1M:
- explicit `RLIMIT_AS soft = 4,294,967,296`
- explicit `RLIMIT_AS hard = 4,294,967,296`
- `process_4gib_envelope_established = true`
- construction completed in 33.598132 s without OOM
- World DB = `1,187,770,368` bytes
- index DB = `701,693,952` bytes
- current World+index open p50 = 0.001752 s / p95 = 0.002157 s
- no required retrieval OOM
- retrieval peak RSS is far below 3 GiB
- the 1M corpus was not reduced

The GitHub runner did not expose a finite cgroup memory/swap value at the probed paths. The hard memory proof is therefore the explicit 4 GiB process address-space limit; no cgroup limit is invented.

## 9. Cold start / stale-index restart

S100K exact-head:
- current World+index open p50 0.001582 s / p95 0.001618 s
- stale-valid index catch-up p50 0.809572 s / p95 0.830929 s
- post-catch-up index watermark equals World revision
- no eager whole-World Python materialization

S1M exact-head:
- current World+index open p50 0.001752 s / p95 0.002157 s
- no OOM

All cold/restart budgets pass.

## 10. Due-work/backlog

Exact-head backlog job `107669725454`:
- 1,000 durable due Wakes
- discovery p95 0.034517 s
- discovery SQL max 1
- 100-item mechanical claim/complete batch 0.760364 s
- remaining after batch = 900
- remaining after process restart = 900
- restart ordering matches = true
- no duplicate/loss/starvation observed
- provider tokens/cost = UNKNOWN

Because baseline backlog already passed, no Wake/Review scheduling implementation was modified.

## 11. Context/token bound

Existing `ContextController` token budget = 3,400 estimated tokens.

Exact-head normal runtime bundle:
- S10K = 2,095
- S100K = 2,102
- S1M = 2,105

All are below policy budget, `truncated=false`, and effectively constant rather than linear in World size. No required pinned evidence limit was weakened.

## 12. Semantic equivalence proof

Final semantic-equivalence job:
- run `36010524179`
- job `107669725864`
- **168 pass markers / 100% / SUCCESS**

It includes:
- `tests/integration/test_core_scale_semantics.py`
- `tests/integration/test_core_headless.py`
- AI-world regressions
- C14 runtime regressions
- Periodic Review
- FIX-002 background-attempt recovery
- turn-execution recovery
- fused turn runtime

The dedicated scale semantic tests prove:
1. object IDs and revisions returned remain equal to deterministic pre-optimization reference behavior
2. contract ordering remains exact
3. exact `limit` behavior remains exact
4. active/inactive and `include_inactive` filtering remain correct
5. user A/user B subject isolation remains correct
6. shared AI-self continuity remains correct
7. knowledge cutoff / `as_of` selects rev1 at the historical cut and rev2 in current view
8. revision selection remains newest visible, not merely newest physical
9. Claim support EvidenceSet payloads remain unchanged
10. Dependency refs/payloads remain unchanged
11. batch World lookup equals repeated authoritative `get_payload`
12. stale index catch-up leaves `index_watermark == world_revision` and lag 0
13. fixed-limit recall ordering is preserved
14. HEADLESS lifecycle/regression remains green

A faster wrong answer would fail these tests.

## 13. FIX-001 / FIX-002 / FIX-003 and recovery compatibility

### FIX-001 temporal read cut

- bounded World readers accept the existing knowledge cutoff
- `_KnowledgeCutoffStoreView` injects that cutoff into new read surfaces
- historical revision choice remains latest **visible at the cutoff**
- exact semantic regression proves pre/post-cutoff revision behavior

### FIX-002 / FIX-003

No background provider-attempt, turn-execution, metering, or durable recovery write semantics were altered.

### Recovery exact-head gate

Core Recovery run:
- `36010524243` — **SUCCESS**
- R1–R10 focused fault injection job `107669725669` — SUCCESS
- installed clean restart job `107669725947` — SUCCESS
- retained recovery regressions job `107669726104` — SUCCESS

No World schema version bump, second truth store, provider-attempt truth duplication, or cache-as-truth requirement was introduced. Search remains rebuildable from World; future-schema fail-closed remains in place.

## 14. Required regression gates on final exact head

All required directly relevant gates are green at `ba23767...`:

- world-kernel run `36010524244` — SUCCESS
- world-index run `36010524141` — SUCCESS
- memory-recommendation run `36010524435` — SUCCESS
- fused-turn-runtime run `36010523850` — SUCCESS
- C09 Wake run `36010523828` — SUCCESS
- P15 Periodic Review run `36010524538` — SUCCESS
- constitutional cognition closure run `36010524066` — SUCCESS
- Core Recovery run `36010524243` — SUCCESS
- C14 runtime run `36010523907`: targeted job `107669725897` ("C14 scheduler and resident runtime") — SUCCESS
- HEADLESS is included in semantic-equivalence job `107669725864` — SUCCESS
- full P16 run `36010524104`, job `107669725118` — SUCCESS

The separate C14 scheduler workflow was also triggered, but the required scheduler/runtime test surface already completed successfully in `107669725897`; no claim depends on redundant queued matrix work.

## 15. Full P16 exact-head result

- run `36010524104`
- job `107669725118`
- direct command: `pytest -q`
- Python 3.12.14
- pytest 8.4.2
- pydantic 2.13.5
- **692 pass markers**
- **100%**
- no failure/error marker observed
- conclusion: **SUCCESS**

## 16. Machine/environment

GitHub-hosted Linux runner:
- kernel: `6.17.0-1022-azure`
- x86_64
- 4 logical CPUs
- Python 3.12.14
- SQLite 3.45.1
- pydantic 2.13.5
- pytest 8.4.2

Observed CPU examples:
- S10K/S100K/backlog class runner: AMD EPYC 7763 64-Core Processor
- S1M runner: AMD EPYC 9V74 80-Core Processor

S1M was explicitly constrained to 4 GiB RLIMIT_AS. No finite cgroup/swap value was observable, so none is claimed.

## 17. Known limitations

1. S1M fixture construction uses a mechanically loaded schema-identical rebuildable search projection; authoritative World data contains the one million current Claim payloads and the measured recall path is production. Production index rebuild/catch-up is independently exercised at S10K/S100K.
2. Provider token/cost is UNKNOWN because no real provider call is part of this mechanical scale task.
3. GitHub-hosted-runner latency is release-gate evidence for this frozen environment, not a forecast of phone/wearable hardware performance.
4. Historical baseline red artifacts are intentionally retained; final green measurements do not erase them.
5. A redundant concurrent extra optimization was reverted before final testing; the accepted author candidate is the smaller tested tree described above.

## 18. Handoff

Author state: **REVIEW_READY**

- Engineering PR: #197
- Tested implementation exact head: `ba23767d4c1565fbe494419dd01c32123495884c`
- Final scale run: `36010524179` — SUCCESS
- Final P16 run: `36010524104` — SUCCESS
- Baseline red run preserved: `36007169180`
- Fresh Independent Acceptance is required before any integration.
- Author does **not** self-accept.
- Author does **not** merge.
- Do **not** start `CORE-RC-FREEZE-001` from this window.
- Do **not** run Resident.
- Do **not** enter UI/hardware.
