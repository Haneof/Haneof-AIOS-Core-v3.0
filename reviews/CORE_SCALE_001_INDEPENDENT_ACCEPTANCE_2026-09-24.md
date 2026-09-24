# CORE-SCALE-001 Independent Acceptance — 2026-09-24

Status: **ACCEPTANCE_PASS**  
Blocker count: **0**  
Task: `CORE-SCALE-001-INDEPENDENT-ACCEPTANCE`  
Repository: `Haneof/Haneof-AIOS-Core-v3.0`  
Engineering PR under review: **#197 — OPEN / UNMERGED**  
Reviewer repair authority: **NONE**  
Reviewer merge authority for #197: **NONE**

## 1. Review-time live main

The review began and ended its evidence phase against live `main`:

`3dfed85204935bd8bba557ab97bd8e21c796675e`

This is the merged governance writeback for the SCALE review gate. Compare from construction main
`3fe3c924fd855251e8fe195486a072ddf5d86169` to review-time live main changes only:

- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`
- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
- `governance/prompts/CORE_SCALE_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

There is no intervening drift in `src/aios_core/**`, the SCALE harness/workflow, HEADLESS, or Recovery implementation. The acceptance candidate therefore did not require rebasing for this review.

The task board state was confirmed as `CORE-SCALE-001 = GATE / REVIEW_READY`. `CORE-RC-FREEZE-001` and Resident execution remained outside this window.

## 2. PR #197 and exact pins

PR #197 is still **OPEN** and **UNMERGED**.

Required pins were verified:

- tested exact candidate: `ba23767d4c1565fbe494419dd01c32123495884c`
- evidence-only handoff: `2c8f16fed52c2a13183870da4ec5dff27892ceb4`
- baseline head: `4f87f85e8fb942a17b4b3d1a99fc648c4c5ff5a9`
- baseline run: `36007169180`

Compare `ba23767... -> 2c8f16...` is one commit and changes only
`reviews/CORE_SCALE_001_COMPLETION_EVIDENCE_2026-09-24.md`. No Core, test harness, or workflow file changes in the handoff delta.

PR #197 changed-file scope is exactly the allowed SCALE scope:

1. `.github/workflows/core-scale.yml`
2. `tools/core_scale_001_bench.py`
3. `src/aios_core/storage/sqlite_store.py`
4. `src/aios_core/runtime/turn_runtime.py`
5. `src/aios_core/ai_world/cognition.py`
6. `src/aios_core/query/search.py`
7. `tests/integration/test_core_scale_semantics.py`
8. `reviews/CORE_SCALE_001_COMPLETION_EVIDENCE_2026-09-24.md`

No task-board, checkpoint, Resident, UI, hardware, or RC-FREEZE implementation is part of #197.

## 3. Baseline-red preservation and independent validation

Baseline run `36007169180` was independently re-read from GitHub job logs and artifact metadata.

The baseline head `4f87f85e...` is construction main plus only the benchmark harness/workflow; compare from
`3fe3c924...` contains no `src/aios_core/**` changes. Every baseline artifact reports workflow head
`4f87f85e8fb942a17b4b3d1a99fc648c4c5ff5a9`.

Independent red results:

| Tier | Independent baseline finding | Verdict |
|---|---|---|
| S10K | recall SQL max **405 > 200** | RED preserved |
| S100K | core_context p95 **5.390459 s > 2 s**; snapshot p95 **18.980603 s > 5 s**; recall SQL **4007 > 500** | RED preserved |
| S1M | explicit 4 GiB RLIMIT established; core_context **MemoryError**; snapshot **MemoryError**; recall p95 **10.333786 s > 10 s**; recall SQL **40005 > 1000** | RED preserved |
| 1,000 backlog | discovery p95 **0.033363 s**; 900 remain after batch and restart; ordering preserved | PASS already at baseline |

The backlog was already green at baseline, so no Wake/backlog optimization was justified by SCALE.

Artifact provenance for the baseline also reconciles correctly: artifact metadata pins head
`4f87f85e...`, while JSON `tested_commit` is the GitHub pull-request synthetic merge
`2d303bf54812b3bbbc1518aa2ba18e9575586f34`. GitHub compare
`4f87f85e... -> 2d303bf5...` has **zero file differences**, so the measured source tree is the baseline source tree.

## 4. Frozen-budget integrity

The acceptance prompt, original CORE-SCALE-001 prompt, baseline harness output, and final harness retain the same thresholds.

### S10K

- core_context p95 <= 0.75 s
- snapshot p95 <= 1.5 s
- broad recall(limit=20) p95 <= 1.0 s
- operation peak-RSS delta <= 512 MiB
- fixed top-k search <= 200 SQL statements

### S100K

- core_context p95 <= 2.0 s
- snapshot p95 <= 5.0 s
- broad recall(limit=20) p95 <= 2.5 s
- measured retrieval RSS delta <= 1.5 GiB
- recall <= 500 SQL statements
- SQL count must not exhibit candidate-level N+1 growth

### S1M

- one million current Claim corpus
- required construction/read probes under explicit 4 GiB process envelope without OOM
- core_context p95 <= 10 s
- snapshot p95 <= 20 s
- recall(limit=20) p95 <= 10 s
- retrieval peak RSS <= 3 GiB
- recall <= 1,000 SQL statements
- no silent corpus reduction if the envelope cannot be established

Cold/restart and backlog limits also remain unchanged: S100K open <= 3 s, stale catch-up <= 10 s, S1M open <= 20 s/no OOM, 1,000 due discovery <= 2 s, 100-item mechanical batch <= 5 s, durable restart and no loss/duplication/starvation.

**Verdict: no post-hoc budget movement found.**

## 5. Candidate minimality and no second truth store

The minimum repaired Core tree was independently inspected.

### Authoritative bounded World readers

`SQLiteWorldStore.iter_latest_payloads(...)`:

- selects the newest **visible** revision from authoritative `object_revisions`;
- applies world-revision / knowledge-cutoff visibility before latest-revision selection;
- supports bounded mechanical pushdown filters;
- streams a SQLite cursor rather than materializing the entire World in Python.

`SQLiteWorldStore.get_payloads_for_ids(...)`:

- reads the same authoritative `object_revisions` table;
- deduplicates IDs;
- uses bounded 400-ID SQLite chunks;
- selects the newest visible revision for each requested ID.

No materialized cognition authority table, alternate World, or schema-version change was introduced.

### Temporal lens

`_KnowledgeCutoffStoreView` forcibly injects the existing execution knowledge cutoff into:

- `get_payload`
- `list_payloads`
- `iter_latest_payloads`
- `get_payloads_for_ids`

The optimized entry points therefore do not bypass FIX-001.

### AI-world subject and revision authority

`AIWorldCognitionService` retains:

- user-scoped domains: `USER_UNDERSTANDING`, `RELATIONSHIP`, `STRATEGY`
- AI-self subject for other AI-world domains
- exact subject equality checks
- active-status checks
- typed domain parsing
- exact order/limit behavior

### Search remains projection-only

`WorldSearchIndex.recall_candidates()` still:

1. catches up a stale projection before current-view retrieval;
2. gets candidate postings from Search;
3. batch-loads projection rows;
4. batch-verifies current/historical payloads against authoritative World;
5. applies revision, active/inactive, subject, dimension, object-type, time and cutoff semantics;
6. performs deterministic score/time/object ordering and exact limit.

Search has not become a second truth store.

### Concurrent extra optimization was net-reverted

The claimed extra concurrent optimization was independently checked:

- `ddc378571393ca2d2e65c9a4754f988a5a2b6278 -> f52828c79ebfe58ac770c77bde62f8294b58d233` has **zero net file differences**.
- `ddc378571393ca2d2e65c9a4754f988a5a2b6278 -> ba23767d4c1565fbe494419dd01c32123495884c` changes only workflow/evidence/semantic-test coverage and has **no Core source diff**.

The final candidate therefore retains the smaller minimum Core repair.

## 6. Fresh independent probe construction

A temporary independent probe branch was created **directly from**
`ba23767d4c1565fbe494419dd01c32123495884c`:

- probe branch: `review/core-scale-001-independent-probe-20260924-sol`
- probe head: `8a8b6cc95db46507e2a22cd6078d82255ecbc9dd`
- temporary probe PR: **#199**
- candidate -> probe diff: **only 120 added test lines in `tests/integration/test_core_scale_semantics.py`**
- no Core/source/harness/workflow modification

The reviewer-authored adversarial test
`test_independent_acceptance_temporal_cutoff_and_subject_isolation` independently created user-A and user-B facts/Claims, revised B after a fixed cutoff, and asserted:

- current B sees B rev2 only;
- cutoff B sees B rev1 through `current()`;
- cutoff B sees B rev1 through `core_context()`;
- cutoff B sees B rev1 through `snapshot()`;
- historical `recall_candidates(as_of=cutoff)` sees B rev1;
- current recall sees B rev2;
- user-A recall sees only A rev1.

PR #199 was used only to obtain fresh CI evidence and was then **closed unmerged**.

## 7. Fresh independent SCALE run

Fresh reviewer probe run:

`36013144779` — **SUCCESS**

Jobs:

- semantic-equivalence `107678720590` — SUCCESS
- S10K `107678720320` — SUCCESS
- S100K `107678720916` — SUCCESS
- S1M `107678720834` — SUCCESS
- 1,000 backlog `107678720652` — SUCCESS

Fresh result table:

| Tier | core_context p95 | snapshot p95 | recall p95 | recall SQL max | max relevant retrieval RSS peak | Verdict |
|---|---:|---:|---:|---:|---:|---|
| S10K | 0.046265 s | 0.057546 s | 0.005819 s | 6 | ~66 MB | PASS |
| S100K | 0.397403 s | 0.495894 s | 0.039264 s | 10 | ~110 MB | PASS |
| S1M | 4.042829 s | 5.608635 s | 0.426988 s | 54 | ~118.1 MB | PASS |

All frozen latency, SQL, and memory gates pass with substantial margin.

## 8. One-million-current-Claim truthfulness

The fresh S1M artifact `10813163998` was not accepted only from harness self-report. Its
`world.sqlite` was independently extracted and queried directly.

Observed authoritative World counts:

- Claim revision rows: **1,020,000**
- distinct Claim object IDs: **1,000,000**
- current Claim objects: **1,000,000**
- current active: **998,000**
- current retracted: **2,000**
- `user_1`: **375,000**
- `ai_agent_self`: **625,000**
- each of 8 AI-world domains: **125,000**

Thus S1M is genuinely a one-million-current-Claim World for the read-path test.

Important fixture boundary: the million-Claim World is **mechanically fixture-loaded** into the real authoritative
`world_commits/object_revisions` schema in 10,000-row batches; it is not one million production Cognition commit API calls. The S1M search projection is also mechanically loaded into the production search schema for fixture practicality. The measured retrieval implementation is production `AIWorldCognitionService` / `WorldSearchIndex.recall_candidates` and authoritative verification returns to World. Production `WorldSearchIndex.rebuild/catch_up` is exercised at S10K/S100K and by the fresh world-index gate.

This limitation is documented and does not convert Search into authority.

## 9. Four-GiB envelope and memory methodology

Fresh S1M proves:

- workflow command uses `prlimit --as=4294967296`
- `RLIMIT_AS soft = 4,294,967,296`
- `RLIMIT_AS hard = 4,294,967,296`
- `process_4gib_envelope_established = true`
- construction completed in **33.217 s**
- no required operation OOM
- World DB ~1.188 GB
- index DB ~0.702 GB

The GitHub runner exposes no finite cgroup memory/swap value at the probed paths, so this review does **not** claim a cgroup limit. The hard envelope proof is the 4 GiB process address-space limit.

Memory sampling uses `/proc/self/status` `VmRSS` every 10 ms with `RUSAGE_SELF.ru_maxrss` fallback. The scale construction/retrieval operations run in that same benchmark process. Cold-open probes run in separate child processes that report their own RSS. No provider/model child process exists in this mechanical SCALE test.

Fresh S1M retrieval RSS peak is far below the frozen 3 GiB ceiling.

## 10. SQL N+1 elimination

Fresh recall SQL counts:

- S10K / 100 common candidates: **6**
- S100K / 1,000 common candidates: **10**
- S1M / 10,000 common candidates: **54**

The path uses 400-ID batching for projection and authoritative World reads. The count grows with bounded chunks, not one World query per candidate. The previous candidate-level N+1 signature was independently reproduced at baseline as 405 / 4007 / 40005 and is absent after repair.

**Verdict: recall candidate-level SQL N+1 is genuinely removed.**

## 11. Temporal cutoff / FIX-001

Fresh reviewer adversarial test passes and directly covers post-cutoff revision exclusion across:

- AI-world `current()`
- `core_context()`
- `snapshot()`
- historical `recall_candidates(as_of=...)`

The cutoff-store source also independently shows forced cutoff injection into both new optimized reader surfaces.

**Verdict: FIX-001 preserved.**

## 12. Subject isolation and AI-self continuity

Fresh reviewer probe proves user-A/user-B isolation through current AI-world and recall paths.

Existing semantic-equivalence coverage, rerun fresh in the same job, also covers shared AI-self continuity.

**Verdict: user subject isolation preserved; AI-self continuity remains shared only where contractually intended.**

## 13. Revision and active/inactive semantics

Fresh semantic-equivalence suite validates:

- newest current revision selection;
- newest **visible** revision at historical cutoff;
- retraction/inactive exclusion by default;
- `include_inactive` behavior;
- current rev2 vs historical rev1 behavior.

The independently inspected S1M artifact also contains 2,000 current retracted Claims, so inactive state exists in the large corpus rather than only in a toy test.

**Verdict: revision and active/inactive semantics preserved.**

## 14. Evidence / Dependency visibility

Fresh semantic-equivalence includes the batch-authority test that creates a Claim with pinned support EvidenceSet plus a Dependency and compares
`get_payloads_for_ids()` results to repeated authoritative `get_payload()` reads.

It verifies support EvidenceSet refs, dependent refs, dependency refs and pinned revisions survive batched retrieval unchanged.

**Verdict: Evidence / Dependency visibility preserved.**

## 15. Exact ordering, exact limit and index watermark

Fresh semantic-equivalence reruns exact-order / exact-limit regression and stale-index catch-up assertions.

Fresh S100K stale catch-up finishes with World revision == index watermark == **14**.  
Fresh S1M current open reports World revision == index watermark == **102**.

**Verdict: exact order/limit and watermark semantics preserved.**

## 16. Cold start and stale-valid index

Fresh S100K:

- current World+index cold-open p95: **0.002026 s <= 3 s**
- stale-valid index catch-up p95: **0.189962 s <= 10 s**
- post-catch-up watermark equals World revision

Fresh S1M:

- current World+index cold-open p95: **0.002238 s <= 20 s**
- no OOM

The open path does not require eager whole-World Python deserialization.

**Verdict: PASS.**

## 17. One-thousand due backlog

Fresh backlog job:

- 1,000 durable due Wakes
- discovery p95: **0.032499 s <= 2 s**
- discovery SQL max: **1**
- 100-item mechanical claim/complete batch: **0.791929 s <= 5 s**
- remaining after batch: **900**
- remaining after restart: **900**
- initial and restart order match: **true**
- hard failures: none

No loss, duplication, or restart durability failure was observed.

**Verdict: PASS.**

## 18. Context/token bound

Fresh normal runtime bundle:

- S10K: **2,095 / 3,400**
- S100K: **2,102 / 3,400**
- S1M: **2,105 / 3,400**
- `truncated = false` at all three tiers

The bundle is effectively constant as World size grows. No context policy or pinned evidence limit was changed by the SCALE repair.

**Verdict: PASS.**

## 19. Semantic equivalence, HEADLESS, FIX-002 and FIX-003

Fresh semantic-equivalence job `107678720590` produced **169 pass markers / 100% / SUCCESS**. It includes the reviewer-authored probe plus the retained suites for:

- SCALE semantics
- HEADLESS
- AI-world
- C14 cognitive derivation runtime
- Periodic Review
- FIX-002 background-attempt recovery
- turn-execution recovery
- fused turn runtime

The repaired files do not introduce an alternate provider-attempt truth store, duplicate turn truth, or weakened recovery semantics.

**Verdict: semantic equivalence / HEADLESS / FIX-002 / FIX-003 compatibility PASS.**

## 20. Fresh Recovery compatibility

Fresh probe-head Recovery run:

`36013143363` — **SUCCESS**

Jobs:

- recovery-fault-injection `107678718260` — SUCCESS
- retained-recovery-regressions `107678718394` — SUCCESS
- installed-clean-restart-proof `107678718544` — SUCCESS

This is fresh compatibility evidence for the retained R1–R10 recovery/fault-injection surface, restart path, WAL/transaction recovery, backup/restore/future-schema retained regressions, and single-World recovery contract.

The pre-existing HEADLESS integration receipt remains valid because there is no HEADLESS implementation drift, and fresh HEADLESS tests are included in semantic-equivalence.

**Verdict: Recovery / HEADLESS compatibility PASS.**

## 21. Exact-head and fresh regression evidence

Original exact candidate `ba23767...` has successful direct workflow metadata for all required gates, including:

- core-scale `36010524179`
- P16 `36010524104`
- core-recovery `36010524243`
- world-kernel `36010524244`
- world-index `36010524141`
- memory-recommendation `36010524435`
- fused-turn-runtime `36010523850`
- C09 Wake `36010523828`
- P15 Periodic Review `36010524538`
- constitutional cognition closure `36010524066`
- C14 runtime `36010523907`
- C14 scheduler `36010523844`
- C14 loop `36010524373`

The fresh reviewer probe head triggered 21 relevant workflows; all completed with **SUCCESS**, including the corresponding Core/World/C14/Recovery/P16 surfaces.

Original exact-head full P16 `36010524104`: **692 pass markers / 100% / SUCCESS**.  
Fresh probe P16 `36013144320`: **693 pass markers / 100% / SUCCESS**; the extra marker is the reviewer-added independent test. Candidate -> probe contains no Core change.

## 22. Artifact / workflow / source-tree provenance reconciliation

### Baseline

- baseline artifact metadata head SHA: `4f87f85e8fb942a17b4b3d1a99fc648c4c5ff5a9`
- baseline JSON `tested_commit`: synthetic PR merge `2d303bf54812b3bbbc1518aa2ba18e9575586f34`
- compare head -> synthetic: **zero file differences**

### Original accepted-candidate evidence

Final run `36010524179` artifacts all report workflow head SHA exactly:

`ba23767d4c1565fbe494419dd01c32123495884c`

The job JSON `tested_commit` is GitHub's synthetic merge
`4b6658ca24a095713ba285cdade6449354fc1d79`. Compare
`ba23767... -> 4b6658ca...` has **zero file differences**.

Therefore the original final SCALE artifacts measured the exact candidate source tree.

### Fresh independent probe

Fresh artifacts report workflow head:

`8a8b6cc95db46507e2a22cd6078d82255ecbc9dd`

Fresh JSON `tested_commit`:

`736713167a2d07e9bfdc5c88df76b96edd681772`

Provenance chain:

- candidate -> probe head: only reviewer test file
- probe head -> synthetic merge: only four live-main governance/review-gate files
- neither hop changes `src/aios_core/**`, SCALE harness, or SCALE workflow

Thus fresh measurements execute the exact candidate Core implementation while adding only independent test coverage and review-time governance context.

**Verdict: provenance reconciled; no source-tree substitution found.**

## 23. Blockers and final verdict

Blockers found: **0**

No evidence was found of:

- moved SCALE thresholds;
- fabricated baseline red;
- reduced S1M World corpus;
- OOM under the required 4 GiB process envelope;
- residual candidate-level recall N+1;
- FIX-001 temporal-cut bypass;
- cross-user subject leakage;
- revision / inactive semantic drift;
- lost Evidence/Dependency visibility;
- order/limit or index-watermark drift;
- FIX-002 / FIX-003 weakening;
- HEADLESS / Recovery regression;
- cold/stale-index failure;
- backlog loss/duplication/starvation;
- context growth beyond existing policy;
- artifact/workflow/source provenance mismatch;
- a second World or cognition truth store.

Known measurement limitation retained explicitly: no finite cgroup limit was observable, so memory acceptance relies on enforced process `RLIMIT_AS=4 GiB`; S1M World/search fixtures are mechanically loaded into the production schemas rather than generated through one million production write API calls. These are documented fixture/method limits, not hidden acceptance exceptions.

**Final verdict: ACCEPTANCE_PASS / blocker = 0**

PR #197 CORE-SCALE-001 tested exact head ba23767d4c1565fbe494419dd01c32123495884c with evidence-only handoff 2c8f16fed52c2a13183870da4ec5dff27892ceb4 is independently accepted for PM integration.

Review stops here. PR #197 remains unmerged. No CORE-RC-FREEZE-001, Resident, UI, or hardware work was entered.
