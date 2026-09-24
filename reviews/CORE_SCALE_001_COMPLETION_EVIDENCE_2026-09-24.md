# CORE-SCALE-001 Completion Evidence — 2026-09-24

Status: REVIEW_READY  
Task: CORE-SCALE-001  
Role: Performance / Scale Engineer  
Repository: Haneof/Haneof-AIOS-Core-v3.0  
Engineering PR: #197  
Author merge authority: NONE — fresh Independent Acceptance required

## 1. Construction baseline and scope

- Construction live main: `3fe3c924fd855251e8fe195486a072ddf5d86169`
- Live main was re-read after implementation and remained unchanged at the same SHA.
- Task state at construction start: `CORE-SCALE-001 = READY`.
- Historical PR #112 and `reviews/C15_RCC_SCALE_BENCH_REPORT_2026-09-22.md` were read only as risk evidence. No historical benchmark number was reused as current proof.
- First measurement was made before any `src/aios_core/**` change.
- Final tested implementation exact head: `ddc378571393ca2d2e65c9a4754f988a5a2b6278`.
- Current pre-evidence branch head: `f52828c79ebfe58ac770c77bde62f8294b58d233`.
- GitHub compare `ddc378...f52828...` has 2 commits and **0 net file differences**. The two commits preserve and then explicitly revert an untested concurrent extra optimization; current tree is byte-for-byte the tested tree.
- No Resident was run.
- No CORE-RC-FREEZE-001 work, UI, or hardware work was performed.
- Task board/checkpoint were not modified.

GitHub Actions PR workflows use a synthetic merge-test SHA. For the final scale run the job environment reported `GITHUB_SHA=df13ec4c7b76bf455bfa919b895bfd48e2b80956`; the workflow run metadata pins PR head `ddc378571393ca2d2ef8d08c90ce8669edc1fb3`? **No**: the authoritative source head for run 36009277468 is `ddc378571393ca2d2e65c9a4754f988a5a2b6278`. The synthetic merge SHA is not the implementation identity.

## 2. Frozen budgets

These thresholds were frozen before measurement and were not moved after seeing results.

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

Cold/restart:
- S100K current World+index open p95 <= 3 s
- S100K stale-valid index catch-up p95 <= 10 s
- S1M current open must complete without OOM; 20 s safety window

Backlog:
- 1,000 due-item discovery p95 <= 2 s
- bounded 100-item mechanical orchestration <= 5 s
- no loss/duplication/starvation
- restart preserves backlog

## 3. Deterministic benchmark corpus and harness

Harness:
- `tools/core_scale_001_bench.py`
- workflow: `.github/workflows/core-scale.yml`

Properties:
- deterministic synthetic/mechanical data only;
- monotonic clock;
- Linux process RSS sampling;
- SQLite trace callback SQL counts;
- JSON + CSV machine-readable output;
- no Resident semantics;
- no real provider call; provider token/cost = **UNKNOWN**.

Corpus:
- S10K: 10,000 current Claims; 500 EvidenceSets; 200 Dependencies; representative Claim revisions; production `WorldSearchIndex.rebuild/catch_up`.
- S100K: 100,000 current Claims; 5,000 EvidenceSets; 2,000 Dependencies; representative revisions; production `WorldSearchIndex.rebuild/catch_up`.
- S1M: 1,000,000 current Claim payloads plus representative prior revisions. World rows use the real authoritative SQLite World schema. For fixture-construction practicality, the S1M search projection is loaded mechanically into the same rebuildable search schema; **World remains the sole truth**, and the measured `recall_candidates` path is the production query path. Production rebuild is exercised at S10K and S100K.
- domain distribution: round-robin across all eight AI-world domains;
- user-scoped domains use `user_1`; AI-self domains use `ai_agent_self`;
- broad recall token hits 1% of current Claims;
- representative current/inactive/revision filtering is present.

## 4. Current-main H1-H4 reproduction verdicts

Historical #112 risks were re-tested on exact current main before modifying Core.

| Risk | Current-main verdict | Current evidence |
|---|---|---|
| H1 AI-world current/core full-Claim extraction | **REAL_SCALE_GAP** | S100K core_context p95 5.390459 s > 2 s; S1M core_context MemoryError under 4 GiB |
| H2 snapshot repeated domain scans | **REAL_SCALE_GAP** | S100K snapshot p95 18.980603 s > 5 s; S1M snapshot MemoryError under 4 GiB |
| H3 recall candidate N+1 SQL | **REAL_SCALE_GAP** | S10K 405 SQL > 200; S100K 4007 SQL > 500; S1M 40005 SQL > 1000 |
| H4 1M memory/OOM boundary | **REAL_SCALE_GAP** | 1M World/index construction and cold open succeeded, but required AI-world reads OOM'd; recall p95 10.333786 s and 40005 SQL also exceeded budget |

Cold/open itself was **not** the blocker: the 1M current World+index opened without OOM. The repair therefore did not redesign startup/recovery.

## 5. Preserved baseline red evidence

Baseline scale workflow:
- run: `36007169180`
- construction main: `3fe3c924fd855251e8fe195486a072ddf5d86169`
- baseline workflow verified zero `src/aios_core/**` diff from construction main before benchmark execution.

Jobs/artifacts:
- S10K job `107658209951`, artifact `10810314921`: FAILURE — recall SQL max 405 > 200.
- S100K job `107658209966`, artifact `10811291681`: FAILURE — core_context p95 5.390459 s; snapshot p95 18.980603 s; recall SQL max 4007.
- S1M job `107658209894`, artifact `10810777415`: FAILURE under explicit 4 GiB RLIMIT_AS — core_context MemoryError, snapshot MemoryError, recall p95 10.333786 s, recall SQL max 40005.
- backlog job `107658209549`, artifact `10811056029`: PASS; no Wake/backlog optimization was justified.

No red artifact was rewritten or deleted.

## 6. Minimum semantics-preserving repair

Only the proven H1/H2/H3 scale gaps were changed.

### `src/aios_core/storage/sqlite_store.py`

Added:
- `iter_latest_payloads(...)`: streams latest-visible World revisions instead of `fetchall` materializing the whole World.
- `get_payloads_for_ids(...)`: batch latest-visible World lookup in bounded SQLite chunks.

Both read directly from authoritative `object_revisions`. No materialized cognition truth table, no cache authority, no second database.

### `src/aios_core/runtime/turn_runtime.py`

`_KnowledgeCutoffStoreView` forwards the two new read surfaces while forcibly injecting the same execution-time knowledge cutoff. This preserves FIX-001 rather than bypassing it.

### `src/aios_core/ai_world/cognition.py`

- payload-to-view conversion was factored without changing Claim meaning;
- `current()` uses the streaming World read and preserves the same typed filters/order/limit;
- `core_context()` and `snapshot()` use a single partitioned stream instead of repeated full World extraction per domain;
- subject authority remains `user_id` for user-scoped domains and `AI_SELF_SUBJECT_ID` for AI-self domains.

### `src/aios_core/query/search.py`

`recall_candidates()`:
- still uses Search only for candidate generation;
- batch-loads projection rows;
- batch-verifies current/historical World payloads;
- preserves current revision selection, inactive behavior, subject/dimension/time filters, and exact knowledge cutoff;
- removes candidate-count-proportional World/SQLite N+1 without replacing exact retrieval with approximation.

### Deliberately not kept

A later additional filter/index optimization was not needed after frozen budgets were already green. It was reverted so the final tree stays the minimum proven repair.

A concurrent commit `44a89c96757ceb2ed2ef8d08c90ce8669edc1fb3` later added an extra World index and another read plan after the candidate was already green. It was not part of this window's tested implementation. Commit `f52828c79ebfe58ac770c77bde62f8294b58d233` explicitly restores `sqlite_store.py` to the tested `ddc378...` content. Compare `ddc378...f52828...` = 0 net files.

## 7. Final frozen-envelope results

Final exact-head scale workflow:
- run: `36009277468`
- workflow conclusion: SUCCESS
- source PR head: `ddc378571393ca2d2e65c9a4754f988a5a2b6278`
- semantic-equivalence job `107665459681`: SUCCESS
- S10K job `107665459893`: SUCCESS, artifact `10811688423`
- S100K job `107665460119`: SUCCESS, artifact `10811339666`
- S1M job `107665460001`: SUCCESS, artifact `10812410283`
- backlog job `107665460061`: SUCCESS, artifact `10811986267`

### Final result table

| Tier | core_context p50 / p95 | snapshot p50 / p95 | recall p50 / p95 | recall SQL max | retrieval RSS evidence | Status |
|---|---:|---:|---:|---:|---:|---|
| S10K | 0.044808 / 0.044900 s | 0.056787 / 0.058748 s | 0.005488 / 0.005820 s | 6 | measured deltas <= 36,864 B for core/snapshot and 4,096 B recall; absolute peak ~65.9 MB | PASS |
| S100K | 0.400460 / 0.421304 s | 0.499202 / 0.502302 s | 0.039729 / 0.039857 s | 10 | measured delta max 36,864 B; absolute peak ~108.8 MB | PASS |
| S1M | 2.820950 / 2.826365 s | 3.755738 / 3.790918 s | 0.317646 / 0.328952 s | 54 | recall delta max 45,109,248 B; absolute recall peak 118,108,160 B | PASS |

Output cardinality remained:
- core_context: 9
- snapshot: 80
- recall: 20

No threshold was moved.

## 8. S1M memory envelope

Final S1M:
- `RLIMIT_AS soft = 4,294,967,296`
- `RLIMIT_AS hard = 4,294,967,296`
- explicit 4 GiB envelope established: true
- World DB size: `1,187,770,368` bytes
- index DB size: `701,693,952` bytes
- construction completed in 43.553461 s without OOM
- current open p50 0.001397 s / p95 0.002248 s
- no required retrieval OOM
- required retrieval peak RSS far below 3 GiB
- corpus was not reduced after failure.

GitHub runner did not expose a finite cgroup memory/swap value in the probed paths (`null`); therefore the hard memory proof is the explicit process `RLIMIT_AS=4 GiB`, not an invented cgroup claim.

## 9. Cold start / restart

S100K final:
- current World+current index open p50 0.002004 s / p95 0.002929 s
- stale-valid index catch-up p50 0.183772 s / p95 0.187567 s
- post-catch-up World revision = index watermark
- no eager full-World Python deserialization was required.

S1M final:
- current World+index open p50 0.001397 s / p95 0.002248 s
- no OOM.

All cold/restart budgets PASS.

## 10. Due backlog

Final backlog job `107665460061`:
- 1,000 durable due Wakes discovered
- discovery p50 0.027344 s / p95 0.028298 s
- discovery SQL max = 1
- 100-item mechanical claim/complete batch = 0.592212 s
- remaining after batch = 900
- remaining after process restart = 900
- restart ordering matches = true
- no duplicate/loss/starvation observed
- provider/token/cost = UNKNOWN

Backlog was already within budget on baseline; no Wake/Review scheduling code was changed.

## 11. Context/token bounds

Existing ContextController budget = 3,400 estimated tokens.

Final normal-runtime bundle estimates:
- S10K: 2,095
- S100K: 2,102
- S1M: 2,105

All are bounded, `truncated=false`, and remain essentially constant rather than growing linearly with World size. No semantically required pinned evidence limit was weakened to achieve the result.

## 12. Semantic equivalence proof

Dedicated final semantic-equivalence job:
- run `36009277468`
- job `107665459681`
- conclusion: SUCCESS

New regression file:
- `tests/integration/test_core_scale_semantics.py`

It compares the optimized paths against deterministic reference behavior and covers:
1. AI-world object IDs/revisions and contract ordering;
2. current vs historical knowledge cutoff (rev2 current / rev1 visible at earlier cutoff);
3. user A / user B subject isolation;
4. shared AI-self continuity;
5. active/inactive and include-inactive behavior;
6. exact per-domain snapshot/core partition behavior;
7. batch World lookup equivalence to repeated authoritative `get_payload`;
8. recall revision selection and historical retraction visibility.

Existing regression workflows on exact tested implementation also passed:
- World kernel: `36009276937` — SUCCESS
- World index: `36009277163` — SUCCESS
- Memory recommendation: `36009277545` — SUCCESS
- Fused turn runtime: `36009277166` — SUCCESS
- C09 Wake: `36009277461` — SUCCESS
- P15 Periodic Review: `36009277796` — SUCCESS
- P10 AI-world: `36009277325` — SUCCESS
- P10 AI-world gate: `36009277613` — SUCCESS
- P9 revision gate: `36009277444` — SUCCESS
- P11 dimension gate: `36009277165` — SUCCESS
- P12 execution gate: `36009277052` — SUCCESS
- P14 long-context: `36009277199` — SUCCESS
- C15 cognition evidence policy: `36009277527` — SUCCESS
- Core Recovery: `36009277169` — SUCCESS
- Dimension summary: `36009277176` — SUCCESS

The direct full P16 run below includes the C14 runtime/scheduler/loop, HEADLESS, FIX-001, FIX-002, FIX-003, and recovery test files even where duplicate path-triggered workflows were still queued.

## 13. FIX-001 / FIX-002 / FIX-003 and recovery compatibility

### FIX-001

Historical/knowledge-cut semantics remain authoritative:
- new World stream/batch readers accept knowledge cutoff;
- `_KnowledgeCutoffStoreView` injects cutoff into the new surfaces;
- historical revision selection is latest **visible at the cutoff**, not latest current;
- semantic regression explicitly proves rev1-at-T1 vs rev2-current behavior.

### FIX-002 / FIX-003

No background model-attempt, user-turn attempt, metering, execution, or Wake lifecycle write path was modified.
Full P16 and Core Recovery passed with existing FIX-002/003 tests.

### Recovery

- no World schema-version bump;
- no new truth cache;
- no second World or cognition store;
- Search remains rebuildable projection;
- backup/restore authority remains World;
- future-schema pre-write fail-closed code was not weakened;
- dedicated Core Recovery workflow `36009277169` = SUCCESS;
- full P16 = SUCCESS.

No optimization requires restoring an index/cache as truth.

## 14. Full P16 / exact-tree verification

Final exact implementation:
`ddc378571393ca2d2e65c9a4754f988a5a2b6278`

P16:
- run `36009277456`
- job `107665459707`
- command: direct `pytest -q`
- Python 3.12.14
- pytest 8.4.2
- pydantic 2.13.5
- 690 pass markers
- reached 100%
- no failure/error/skip marker observed
- job conclusion: SUCCESS

Because `f52828...` has zero net file difference from `ddc378...`, current pre-evidence tree is the exact tested tree.

## 15. Machine/environment

Final scale workflow common environment:
- Linux `6.17.0-1022-azure`
- x86_64
- 4 logical CPUs
- Python 3.12.14
- SQLite 3.45.1
- pydantic 2.13.5
- pytest 8.4.2

Runner CPU model:
- S10K/S100K: AMD EPYC 7763 64-Core Processor
- S1M: Intel Xeon Platinum 8573C

S10K/S100K had unlimited process RLIMIT_AS as provided by the runner.
S1M was explicitly constrained to 4 GiB RLIMIT_AS.
No finite cgroup/swap value was available from the probed Linux cgroup files, so none is invented.

## 16. Known limitations / honest notes

1. S1M uses a mechanically loaded, schema-identical rebuildable search projection for fixture construction to keep million-row generation practical. World truth is real SQLite World data and the measured retrieval path is production. Production index rebuild/catch-up is independently exercised at S10K/S100K.
2. Provider token/cost remains UNKNOWN because no real provider call was part of this mechanical scale task.
3. The first repaired core-scale run had an overall failure solely because two nonexistent regression filenames were listed in the semantic job; benchmark jobs were green. The final run `36009277468` corrected those paths and is fully SUCCESS.
4. A concurrent untested extra optimization appeared after the final green run. It was reverted without force-push; the current tree is verified identical to the tested tree.
5. Performance numbers are GitHub-hosted-runner measurements, not device/hardware forecasts.

## 17. Handoff

Author state: **REVIEW_READY**

- Engineering PR: #197
- Tested implementation exact head: `ddc378571393ca2d2e65c9a4754f988a5a2b6278`
- Current pre-evidence tree head: `f52828c79ebfe58ac770c77bde62f8294b58d233`, tree-identical to tested head
- Final scale run: `36009277468` — SUCCESS
- Final P16 run: `36009277456` — SUCCESS
- Fresh Independent Acceptance is required.
- Author does not self-accept and does not merge.
- Do not start CORE-RC-FREEZE-001 from this author window.
