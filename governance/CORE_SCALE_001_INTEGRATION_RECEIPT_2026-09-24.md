# CORE-SCALE-001 Integration Receipt — 2026-09-24

Status: DONE
Task: CORE-SCALE-001

## Pins

- Construction main: `3fe3c924fd855251e8fe195486a072ddf5d86169`
- Baseline red head: `4f87f85e8fb942a17b4b3d1a99fc648c4c5ff5a9`
- Baseline red run: `36007169180`
- Tested exact candidate: `ba23767d4c1565fbe494419dd01c32123495884c`
- Evidence-only handoff: `2c8f16fed52c2a13183870da4ec5dff27892ceb4`
- Engineering PR: #197
- Independent acceptance PR: #200
- Independent report: `reviews/CORE_SCALE_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`
- Fresh probe PR: #199 — CLOSED / UNMERGED
- Fresh probe head: `8a8b6cc95db46507e2a22cd6078d82255ecbc9dd`
- Fresh scale run: `36013144779`
- Fresh P16 run: `36013144320`
- Fresh Recovery run: `36013143363`

## Preserved current-main red evidence

The baseline head differed from construction main only by the scale harness/workflow and had zero
`src/aios_core/**` changes.

Independent acceptance revalidated the real pre-fix gaps:

- S10K recall SQL: 405 > 200.
- S100K:
  - core_context p95 5.390459 s > 2.0 s
  - snapshot p95 18.980603 s > 5.0 s
  - recall SQL 4007 > 500
- S1M under explicit 4 GiB RLIMIT_AS:
  - core_context MemoryError
  - snapshot MemoryError
  - recall p95 10.333786 s > 10 s
  - recall SQL 40005 > 1000
- baseline 1,000-item backlog already passed and therefore was not optimized.

Historical PR #112 remained only a risk clue and was not used as current proof.

## Accepted repair

The final Core source changes were limited to:
- `src/aios_core/storage/sqlite_store.py`
- `src/aios_core/runtime/turn_runtime.py`
- `src/aios_core/ai_world/cognition.py`
- `src/aios_core/query/search.py`

The repair:
- streams newest-visible authoritative World revisions instead of whole-World materialization;
- batch-loads fixed-id authoritative World payloads;
- lets AI-world core_context/snapshot reuse one authoritative stream;
- replaces recall candidate N+1 verification with bounded batch verification.

No second World, cognition truth store, authoritative cache, vector truth source, semantic truncation,
schema-version bump, FIX-001 weakening, FIX-002/003 weakening, or provider-recovery shortcut was introduced.

## Exact candidate evidence

Original final exact candidate:
`ba23767d4c1565fbe494419dd01c32123495884c`

Original final scale run:
`36010524179` — SUCCESS

Original final P16:
- run `36010524104`
- job `107669725118`
- Python 3.12.14
- pytest 8.4.2
- pydantic 2.13.5
- direct `pytest -q`
- 692 pass markers / 100% / SUCCESS

Original final S1M:
- core_context p95 4.195750 s
- snapshot p95 5.682172 s
- recall p95 0.432998 s
- recall SQL max 54
- explicit RLIMIT_AS = 4,294,967,296
- no OOM

Semantic-equivalence + HEADLESS job:
`107669725864` — 168 pass markers / SUCCESS

Recovery:
`36010524243` — SUCCESS

## Fresh final independent acceptance

PR #200 returned:
`ACCEPTANCE_PASS / blocker=0`.

Fresh independent scale run:
`36013144779` — SUCCESS

Fresh results:
- S10K: core 0.046265 s / snapshot 0.057546 s / recall 0.005819 s / SQL 6
- S100K: core 0.397403 s / snapshot 0.495894 s / recall 0.039264 s / SQL 10
- S1M: core 4.042829 s / snapshot 5.608635 s / recall 0.426988 s / SQL 54

Fresh S1M artifact was independently unpacked and queried:
- 1,000,000 distinct/current Claim IDs
- 1,020,000 Claim revision rows
- 998,000 active / 2,000 retracted
- authoritative World schema is the production World schema

S1M remained under explicit:
`RLIMIT_AS = 4,294,967,296`
with no OOM.

Fresh P16:
- run `36013144320`
- 693 pass markers / 100% / SUCCESS
- the one additional marker is the reviewer-authored adversarial semantic test.

Fresh semantic-equivalence:
- 169 pass markers / SUCCESS
- included reviewer-authored temporal-cut + subject-isolation adversarial coverage.

Fresh Recovery:
`36013143363` — all three recovery jobs SUCCESS.

Fresh independent acceptance also confirmed:
- candidate-level SQL N+1 removed;
- FIX-001 temporal cutoff preserved;
- user subject isolation preserved;
- AI-self continuity preserved;
- newest-visible revision behavior preserved;
- active/inactive behavior preserved;
- Evidence/Dependency visibility preserved;
- exact ordering/limit preserved;
- index watermark/catch-up preserved;
- cold start/stale catch-up budgets passed;
- 1,000 due backlog passed;
- context token bound remained 2095 / 2102 / 2105 <= 3400;
- artifact synthetic-merge provenance matched the candidate source tree.

Fresh probe PR #199 remained CLOSED / UNMERGED.

## Fixture / measurement boundary

The S1M one-million-Claim World was mechanically bulk-loaded into the real authoritative
`world_commits/object_revisions` schema for fixture practicality; it was not generated through one million production write API calls.

The S1M search projection was also mechanically loaded into the production search schema.
Measured retrieval still used production AI-world/search code and authoritative World verification.
Production `WorldSearchIndex.rebuild/catch_up` was independently exercised at S10K/S100K and by World-index gates.

No finite cgroup/swap limit was observable on GitHub runners.
The hard memory acceptance boundary is the explicit 4 GiB process address-space limit.

## Integration

PM merged acceptance evidence first:
- PR #200 merge: `66e518c64b490947af42cf10c880544333d0d360`.

Before candidate integration:
- PR #197 head remained exactly `2c8f16fed52c2a13183870da4ec5dff27892ceb4`;
- `ba23767d... -> 2c8f16fe...` remained exactly one completion-evidence file;
- main drift after final acceptance was the #200 review report only;
- GitHub recomputed #197 as `mergeable=true / mergeable_state=clean / rebaseable=true`.

PM merged #197 with expected-head pin:
- merge: `46c7cf9771274559b42dade9359e2e2cae5f245f`.

## Honest post-merge note

At integration writeback time GitHub returned no automatic workflow runs for merge commit
`46c7cf9771274559b42dade9359e2e2cae5f245f`.

No post-merge green run is claimed.
Authoritative evidence is:
- preserved real current-main red;
- accepted exact-head scale/semantic/P16/Recovery gates;
- fresh independent acceptance #200;
- fresh independent probe #199.

## Release effect

`CORE-SCALE-001 = DONE`.

All S2 prerequisites for RC freeze are now integrated:
- audited Core gap fixes;
- CI corrective prerequisite;
- HEADLESS;
- RECOVERY;
- SCALE.

The next task is:
`CORE-RC-FREEZE-001`.

RC-FREEZE freezes software and evidence; it does not run Resident.
