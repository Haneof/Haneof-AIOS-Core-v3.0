# WIP durable freeze — C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001

**FROZEN_WIP / BLOCKED_BY_CORE_RESPONSE_APPLICATION_RECOVERY**

This is a preservation-only engineering freeze, not a completed candidate,
not REVIEW_READY, not an Independent Acceptance request, and not a release.
No new recovery logic or test execution was performed during this freeze.

## Exact baseline and concurrent-write check

- Dedicated session engineering branch: `arena/01a0dce5-haneof-aios-core-v3-0`.
- Tested WIP base: `f0f2eb8a7030b9b56cbec43c09574e056b2f7c61`.
- Freshly fetched main for freeze: `59e3f48b9fe2a75ea9377ed3d75a97939880b695`.
- Main HAS received same-task PM governance updates, including merged PR #214,
  through `59e3f48b9fe2a75ea9377ed3d75a97939880b695`. The task prompt and the
  PM scope amendment were inspected. No other engineering persistence package
  exists on that main tree, and no same-task open engineering PR was found by
  the live PR inventory before creating this freeze PR.
- The main amendment says CONTINUE SAME CORRECTIVE with safety vs liveness
  distinctions. The newer explicit user instruction in this session says to
  freeze WIP and stop. This artifact follows the newer freeze instruction; it
  does not rewrite or supersede the main PM document, declare a Core regression,
  or create/authorize a new Core task.
- No main merge/rebase is included: retain the tested WIP base and original
  evidence verbatim. The two board/checkpoint additions already existed before
  this freeze and record only WIP/BLOCKED. No new board/checkpoint edits were made.

The exact freeze commit SHA, Draft PR number and complete changed-file inventory
are recorded in the Draft PR description after the commit is created. This
avoids a self-referential commit hash inside its own tree.

## PCORE-BLK-001

A provider reply can be durably journaled while the Core model attempt/application boundary remains unresolved. After process death in this interval, current Core correctly enters response-pending/in-doubt fail-closed state, but provides no legal exactly-once continuation path that consumes the already-durable exact ModelDirective without resubmitting the provider or risking duplicate semantic application.

This definition is the requested freeze blocker, not a claim that the prototype
already supplies such a continuation path or that fail-closed Core is defective.
The actual preserved red probe stages opaque synthetic reply bytes and kills
before returning a directive; it does not claim to serialize a validated
production ModelDirective or to execute a capability.

## Preserved implementation and evidence

- Prototype/checkpoints/journal: `tools/c15_persistence/{__init__,journal}.py`.
- Synthetic tests: `tests/c15_persistence/test_journal.py`.
- Red probe: `tests/c15_persistence/probe_core_boundary.py`.
- Existing engineering report: `ENGINEERING_STATUS.md` (unchanged historical
  checkpoint; its statements about no PR/push describe the pre-freeze stage).
- `evidence/persistence-final.log`: **13/13**, exit 0.
- `evidence/frozen-attempt-02.log`: **158/158**, FAILURES=0,
  `CORRECTIVE_013_E2E_PASS`, exit 0, frozen E2E unchanged.
- `evidence/lifecycle-attempt-01.log`: exit 0; cross-document 5,
  executable 18, shell semantics 82 mutation-red cases.
- `evidence/frozen-attempt-01.log`: original dependency failure, exit 1.
- `evidence/persistence-attempt-01.log`: original permission/setup failure,
  exit 1. Neither red attempt was overwritten by later successful attempts.
- `evidence/core-boundary-attempt-01.log`: **exit 2**,
  `CORRECTIVE_CONVERGENCE_BLOCKED`; real child SIGKILL exit **-9**, recovered
  `in_doubt`, ordinary retry refused, explicit retry refused, redispatches **0**.
- `evidence/synthetic-core-boundary/{world.sqlite,index.sqlite,reply.raw,probe-result.json}`:
  exact preserved synthetic red-state bytes. Reply SHA-256:
  `5cfc42b2f36aba93f32045d8a40022ec8b9f99a669b51eab0d8b725cef10421f`.
- All 18 entries in the pre-existing `MANIFEST.json` were rehashed and matched
  before this freeze. That manifest and every covered file are unchanged.

## Boundary confirmations

- `src/aios_core/** = 0 diff` against both the tested base and fetched main.
- Real Resident B / real cursor 14 were never run by this corrective window.
- No sealed fixture, accepted preflight, canonical A/PR #205 evidence, or retired
  run/session/request identity was modified or reused.
- No weakening of `in_doubt`, ledger reset, `response_returned -> admitted`,
  blind provider retry, semantic reply replay, or skipped exactly-once proof.
- Synthetic-only prototype remains disabled for production. Missing proofs
  remain explicitly missing, not converted into green results.
- No Independent Acceptance requested; no RELEASE-003/RERUN-003 entered.
- Draft PR is archival, BLOCKED, DO NOT MERGE. Stop after durable push and PR
  metadata verification.
