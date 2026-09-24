# CORE-SCALE-001 INDEPENDENT ACCEPTANCE

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Role:
Independent Performance / Scale / Semantic-Equivalence Acceptance Reviewer

Candidate:
- Engineering PR #197 — `CORE-SCALE-001: frozen scale characterization and minimal repair`
- construction main:
  `3fe3c924fd855251e8fe195486a072ddf5d86169`
- tested final exact candidate:
  `ba23767d4c1565fbe494419dd01c32123495884c`
- evidence-only handoff:
  `2c8f16fed52c2a13183870da4ec5dff27892ceb4`

Historical current-main red evidence:
- baseline run: `36007169180`
- baseline head: `4f87f85e8fb942a17b4b3d1a99fc648c4c5ff5a9`

Final exact-head evidence:
- core-scale run: `36010524179`
- full P16 run: `36010524104`

Your task is to independently decide whether the current Core meets the already-frozen S10K / S100K / S1M scale budgets after only semantics-preserving optimization.

You are not:
- PR #197 author
- scale engineer
- AIOS total PM
- Resident
- Semantic Evaluator
- RC-FREEZE engineer
- UI/hardware engineer

This window:
- acceptance only
- no candidate repair
- no merge
- no CORE-RC-FREEZE-001
- no Resident
- no UI/hardware

## 1. Required start

1. Fetch current live `main`.
2. Read:
   - `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`
   - `AIOS_v3.0_CURRENT_CHECKPOINT.md`
   - `PROJECT_MASTER_MAP.md`
   - `governance/AIOS_CORE_COMPLETION_PLAN_2026-09-24.md`
   - `governance/prompts/CORE_SCALE_001_2026-09-24.md`
   - `governance/CORE_RECOVERY_001_INTEGRATION_RECEIPT_2026-09-24.md`
   - `governance/CORE_HEADLESS_001_INTEGRATION_RECEIPT_2026-09-24.md`
   - `reviews/CORE_SCALE_001_COMPLETION_EVIDENCE_2026-09-24.md`
   - historical PR #112 only as old risk evidence
   - PR #197 current body/diff.
3. Confirm:
   `CORE-SCALE-001 = GATE / REVIEW_READY`.
4. Pin:
   - tested exact candidate:
     `ba23767d4c1565fbe494419dd01c32123495884c`
   - evidence-only handoff:
     `2c8f16fed52c2a13183870da4ec5dff27892ceb4`
5. Verify:
   `ba23767d... -> 2c8f16fe...`
   changes only:
   `reviews/CORE_SCALE_001_COMPLETION_EVIDENCE_2026-09-24.md`.

If the tested head changes, do not inherit this evidence.

## 2. Preserve and validate the real red state

Before accepting green results, independently verify the baseline run was genuinely current-main behavior before Core optimization.

Baseline:
- head `4f87f85e8fb942a17b4b3d1a99fc648c4c5ff5a9`
- run `36007169180`

Verify the baseline head differs from construction main only by:
- `.github/workflows/core-scale.yml`
- `tools/core_scale_001_bench.py`

There must be zero `src/aios_core/**` difference.

Independently re-read the red artifacts/logs and confirm at least:

S10K:
- recall SQL = 405 > frozen 200.

S100K:
- core_context p95 = 5.390459 s > 2.0 s;
- snapshot p95 = 18.980603 s > 5.0 s;
- recall SQL = 4007 > 500.

S1M:
- explicit 4 GiB RLIMIT_AS was established;
- core_context = MemoryError;
- snapshot = MemoryError;
- recall p95 = 10.333786 s > 10 s;
- recall SQL = 40005 > 1000.

Backlog baseline must be recorded as PASS and must not be rewritten as a gap.

Historical PR #112 must not substitute for this evidence.

## 3. Frozen budgets — do not move them

The exact frozen acceptance budgets remain those in:
`governance/prompts/CORE_SCALE_001_2026-09-24.md`.

Do not relax any threshold after seeing results.

### S10K
- core_context p95 <= 0.75 s
- snapshot p95 <= 1.5 s
- recall p95 <= 1.0 s
- retrieval peak-RSS delta <= 512 MiB
- fixed top-k recall SQL <= 200

### S100K
- core_context p95 <= 2.0 s
- snapshot p95 <= 5.0 s
- recall p95 <= 2.5 s
- retrieval RSS delta <= 1.5 GiB
- recall SQL <= 500
- no N+1 growth with candidate hit count

### S1M
- 1,000,000 current Claim payloads in authoritative World
- explicit 4 GiB process/cgroup envelope
- construction + required retrievals complete without OOM
- core_context p95 <= 10 s
- snapshot p95 <= 20 s
- recall p95 <= 10 s
- retrieval peak RSS <= 3.0 GiB
- recall SQL <= 1000

Also preserve cold/restart, backlog and context/token bounds from the frozen prompt.

## 4. Candidate scope and minimality

Independently compare construction main -> tested exact head.

Core runtime changes should be limited to:
- `src/aios_core/storage/sqlite_store.py`
- `src/aios_core/runtime/turn_runtime.py`
- `src/aios_core/ai_world/cognition.py`
- `src/aios_core/query/search.py`

The remaining changes should be benchmark/evidence/equivalence support:
- `.github/workflows/core-scale.yml`
- `tools/core_scale_001_bench.py`
- `tests/integration/test_core_scale_semantics.py`
- completion evidence.

Verify the claimed reverted concurrent optimization is net-zero in final Core source.

Fail if the final candidate introduces:
- second World/cognition truth store;
- materialized cognition authority;
- vector/approximate retrieval replacing required exact retrieval;
- semantic truncation;
- fixed cognition/domain policy to game latency;
- weakened subject isolation;
- weakened revision semantics;
- weakened FIX-001/002/003.

## 5. New bounded authoritative read surfaces

Inspect:
- `iter_latest_payloads(...)`
- `get_payloads_for_ids(...)`

Verify they remain direct reads of authoritative World revisions and are not caches/truth projections.

Check:
- newest-visible revision selection;
- knowledge cutoff;
- object type filters;
- subject semantics where applicable;
- bounded SQLite chunking;
- deterministic ordering;
- no whole-table `fetchall()` reintroduced through another path.

## 6. FIX-001 historical cutoff

This is a mandatory acceptance point because the optimization changed read paths.

Verify `_KnowledgeCutoffStoreView` injects the original active execution cutoff into the new bounded read surfaces.

Fresh adversarial test:
- object rev1 learned at T1;
- rev2 learned at T2;
- resumed historical execution has cutoff T1;
- all optimized current/core-context/snapshot/search verification paths visible to that execution must resolve rev1 / exclude T2-only state;
- current-time control sees rev2.

Fail any “filter after reading current state” implementation.

## 7. Subject isolation / AI-self semantics

Fresh adversarial corpus:
- user A and user B have similarly worded claims;
- shared AI-self data also exists;
- test current/core_context/snapshot/recall.

Verify:
- user A cannot receive user B private current cognition;
- user B cannot receive user A private current cognition;
- legitimate AI-self continuity remains visible according to the existing contract;
- batching does not mix subject authority.

## 8. Revision / active / Evidence / Dependency equivalence

Independently compare optimized behavior against the authoritative pre-optimization reference behavior on deterministic corpora.

Required equality:
- object IDs;
- revisions;
- ordering where contractually defined;
- exact limit;
- active/inactive handling;
- latest-visible revision;
- historical as_of/cutoff;
- EvidenceSet payload visibility;
- Dependency ref/payload visibility;
- index watermark/catch-up result.

Do not accept “same count” as semantic equivalence.

## 9. Search N+1 removal

Inspect `recall_candidates()`.

Verify:
- search index remains candidate projection only;
- authoritative World still validates returned candidates;
- fixed top-k result semantics are unchanged;
- SQL count no longer scales one-or-more SQL calls per hit;
- batching remains bounded at SQLite variable limits;
- historical cutoff/current revision selection remains authoritative.

Fresh adversarial probe should compare SQL count at two different broad-hit corpus sizes and demonstrate sublinear/bounded query count rather than candidate-level N+1.

## 10. AI-world current/core_context/snapshot optimization

Verify:
- `current()` streaming stops only when contractually safe;
- `core_context()` and `snapshot()` reuse one authoritative stream without changing domain partition semantics;
- output ordering remains unchanged;
- limit is exact;
- inactive/current logic remains unchanged;
- no domain is silently omitted to meet latency.

Fresh small-corpus oracle comparison is mandatory.

## 11. Independent fresh scale probes

Do not rely only on author CI.

Run fresh independent probes from exact candidate `ba23767...` or a probe-only branch rooted exactly there.

Minimum:

### Probe A — S100K
Re-run S100K under the frozen harness and record:
- p50/p95 core_context
- p50/p95 snapshot
- p50/p95 recall
- peak RSS
- recall SQL
- cold open
- stale-index catch-up
- context token bound

All frozen S100K budgets must PASS.

### Probe B — S1M
Re-run the mandatory one-million-Claim capacity path.

Must establish:
- exact corpus count = 1,000,000 current Claims;
- explicit 4 GiB process address-space/cgroup envelope;
- no OOM;
- all three required retrievals finish;
- all S1M p95/RSS/SQL hard budgets pass.

If the CI environment cannot provide the 4 GiB constraint, verdict cannot be ACCEPTANCE_PASS unless an equivalent independently enforced 4 GiB limit is demonstrated.

### Probe C — semantic equivalence
Freshly execute the dedicated semantic-equivalence suite and add at least one reviewer-authored adversarial temporal-cut or subject-isolation case.

### Probe D — SQL scaling
At two corpus sizes with similar broad-token hit ratios, prove recall SQL count is bounded/batched and not N+1.

A probe-only PR is allowed; close it unmerged after evidence capture.

## 12. S1M corpus integrity

This is high priority.

Verify the author did not silently reduce the authoritative 1M corpus.

Confirm:
- authoritative World really contains one million current Claim payloads in the measured retrieval path;
- construction finished inside the enforced memory envelope;
- any mechanically preloaded search projection remains rebuildable/non-authoritative;
- recall still verifies against authoritative World;
- no cached subset is substituted as truth.

Document exactly what is production-generated vs mechanically fixture-loaded.

## 13. Memory accounting

Review RSS measurement methodology.

Confirm:
- process peak RSS is measured, not Python object estimate only;
- steady baseline vs delta are not confused;
- absolute RSS is recorded;
- 4 GiB proof uses actual OS RLIMIT/cgroup mechanics;
- no claim is made about unavailable cgroup/swap values.

If the harness can miss child-process RSS or important allocation due to measurement scope, quantify the limitation and determine whether hard budgets are still proven.

## 14. Cold start / restart

Freshly verify on S100K:
- current World+index open p95 <= 3 s;
- stale valid index catch-up p95 <= 10 s;
- watermark == World revision afterward;
- startup does not deserialize whole World.

On S1M:
- current World+index open completes without OOM;
- record latency/RSS.

## 15. Due backlog

Independently verify the no-change decision was valid.

At 1,000 due durable records:
- discovery p95 <= 2 s;
- bounded 100-item mechanical orchestration <= 5 s excluding deliberate model sleep;
- remaining = 900;
- restart remaining = 900;
- ordering preserved;
- no duplicate/loss/starvation.

Because baseline already passed, any runtime Wake/Review scale optimization beyond what is required for retrieval would be suspicious and must be reviewed.

## 16. Context/token bound

Verify normal runtime context at S10K/S100K/S1M:
- remains <= existing ContextController budget;
- is effectively bounded rather than linear in World size;
- no semantically required pinned evidence was silently removed;
- no policy budget was increased to hide overflow.

Provider token/cost remains UNKNOWN unless independently observed.

## 17. Recovery compatibility

Freshly verify:
- Recovery backup/restore still works with optimized read/index behavior;
- index is still rebuildable from World;
- no restore requires benchmark/cache artifacts;
- future-schema fail-closed remains;
- writer lease remains canonical;
- FIX-002/003 IN_DOUBT semantics unchanged.

No schema-version change is expected.

## 18. Exact-head CI

Re-read raw logs tied to tested exact candidate:
`ba23767d4c1565fbe494419dd01c32123495884c`.

Required final scale run:
`36010524179`

Jobs:
- semantic equivalence + HEADLESS:
  `107669725864`
- S10K:
  `107669725857`
- S100K:
  `107669725608`
- S1M:
  `107669726285`
- backlog:
  `107669725454`

Required full P16:
- run `36010524104`
- job `107669725118`

PM pre-check observed:
- Python 3.12.14
- pytest 8.4.2
- pydantic 2.13.5
- direct `pytest -q`
- 692 pass markers
- 100%
- SUCCESS

Required compatibility gates:
- Recovery `36010524243`
- World kernel `36010524244`
- World index `36010524141`
- Memory recommendation `36010524435`
- Fused turn `36010523850`
- C09 Wake `36010523828`
- P15 Review `36010524538`
- Constitutional cognition `36010524066`
- C14 runtime `36010523907`
- C14 scheduler `36010523844`
- C14 loop `36010524373`

Do not rely only on PR body/evidence prose.

## 19. Artifact commit provenance

Scale artifacts may report a `tested_commit` corresponding to the workflow checkout/merge context rather than the PR branch SHA.

Explicitly reconcile:
- GitHub workflow run `head_sha`;
- checkout/ref used by the job;
- artifact `tested_commit`;
- candidate source tree.

Do not treat a differing artifact commit field as automatically valid or invalid.
Establish that the measured source tree exactly matches the tested candidate Core tree.

If it does not, FAIL or require revalidation.

## 20. Live-main drift

At author completion, construction/live main was:
`3fe3c924fd855251e8fe195486a072ddf5d86169`.

If review-time main has advanced:
- governance/review-only drift does not automatically require rebase;
- any relevant `src/**`, retrieval/index/runtime, Recovery, HEADLESS, test-contract or scale-workflow change requires explicit compatibility review and may require `REBASE_REVALIDATION_REQUIRED`.

## 21. Verdict

### ACCEPTANCE_PASS
Only if:
- baseline red evidence is genuine current-main behavior;
- frozen budgets were not moved;
- S10K/S100K/S1M all independently satisfy hard budgets;
- S1M is genuinely one million current Claims under enforced 4 GiB limit;
- no OOM;
- SQL N+1 is actually removed;
- semantic equivalence holds for temporal cutoff, subject isolation, revision, active/inactive, Evidence/Dependency, exact limit/order, index watermark;
- FIX-001/002/003 intact;
- Recovery/HEADLESS intact;
- context/backlog/cold-open budgets pass;
- exact-head CI and full P16 pass;
- fresh reviewer probes pass;
- blockers = 0.

### ACCEPTANCE_FAIL
Any real correctness/scale/blocker.

### REBASE_REVALIDATION_REQUIRED
Only for a new relevant semantic main change that materially invalidates the pinned candidate.

## 22. Report

Create:
`reviews/CORE_SCALE_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`

Create one review-only PR from review-time main.

Report:
1. review-time main
2. PR #197
3. tested exact head
4. evidence-only handoff
5. baseline red validation
6. frozen-budget integrity
7. candidate scope/minimality
8. S10K/S100K/S1M verdicts
9. S1M corpus / 4 GiB proof
10. SQL scaling verdict
11. semantic equivalence verdict
12. FIX-001/002/003 compatibility
13. Recovery/HEADLESS compatibility
14. cold/restart verdict
15. backlog verdict
16. context/token verdict
17. fresh adversarial probes
18. exact-head CI
19. full P16 result
20. artifact commit provenance
21. live-main drift
22. blocker count
23. final verdict

Do not merge PR #197.

If PASS, state:

`PR #197 CORE-SCALE-001 tested exact head ba23767d4c1565fbe494419dd01c32123495884c with evidence-only handoff 2c8f16fed52c2a13183870da4ec5dff27892ceb4 is independently accepted for PM integration.`
