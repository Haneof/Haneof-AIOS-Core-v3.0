# CORE-GAP-FIX-001 Integration Receipt — 2026-09-24

Status: DONE
Task: CORE-GAP-FIX-001 / CORE-GAP-FIX-001-CORRECTIVE-001
Finding closed: CG-001 — RUNTIME_TEMPORAL_READ_CUT

## Historical path

- Original candidate PR: #145.
- Original reviewed exact head: `b5a50435b3f9048bf94d88e9625b9e5bc2b83f42`.
- Independent review PR #161: ACCEPTANCE_FAIL.
- Historical blocker: `CORE-GAP-FIX-001-ACCEPT-BLOCKER-001 — C14_RUNTIME_DERIVED_LINEAGE_NOT_CUTOFF`.
- Historical failed report remains unchanged at:
  `reviews/CORE_GAP_FIX_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`.

## Corrective

- Corrective red-only head: `e19bc90440ed236709a58bbe6077b5a5b255c29e`.
- C14 run `35978909940`, targeted job `107565857185`: real direct + bundle T2 support-leaf leak.
- Corrective exact head: `a56f113ace3c5e01af3acb724468bc2e0fbd4e98`.
- Independent corrective review PR: #171.
- Review-only head: `b38128a2125863fcce1cbc7c0babc82f106a92cb`.
- Verdict: ACCEPTANCE_PASS.
- Blockers: 0.

Corrective mechanism:
- C14 runtime-derived lineage now uses the existing `_KnowledgeCutoffStoreView`;
- Dependency enumeration and exact leaf traversal both obey the historical knowledge cut;
- direct C14 and bundle/member C14 use the same cutoff-aware lineage reader;
- no second graph, World, or lineage truth store was introduced.

## Accepted exact-head verification

Exact corrective head `a56f113a...`:
- 17/17 workflows SUCCESS;
- P16 run `35979326698`, job `107567178057`;
- Python 3.12.14 / pytest 8.4.2 / pydantic 2.13.5;
- direct `pytest -q`;
- 651 passed / 0 failed / 0 skipped.

Independent corrective review also confirmed:
- old blocker red state was real;
- direct C14 historical lineage PASS;
- bundle/member C14 historical lineage PASS;
- prior FIX-001 surfaces did not regress;
- FIX-002 background recovery semantics remained intact;
- FIX-003 ownership was not crossed.

## Integration

PM merged the independent acceptance evidence first:
- PR #171 merge: `95747cd952ce00374ed6fdbee970e7cf8ea1f584`.

PM then re-read PR #145:
- exact head remained `a56f113ace3c5e01af3acb724468bc2e0fbd4e98`;
- GitHub recomputed `mergeable=true / mergeable_state=clean`;
- the only main drift after review completion was the review-only #171 file.

Candidate #145 was merged with expected-head pin:
- merge: `d97a1bfa527caadb4ab22d232fd627c0483e02d8`.

## Honest post-merge note

At PM writeback time no automatic GitHub Actions run was returned for merge commit
`d97a1bfa527caadb4ab22d232fd627c0483e02d8`.
No post-merge green run is claimed. The authoritative acceptance evidence is the accepted exact-head
17/17 workflow set, P16 651-pass regression, and independent corrective acceptance #171.

## Serialization effect on FIX-003

At the moment FIX-001 was integrated:
- PR #157 remained OPEN / UNMERGED;
- its corrective head was `ac8d5a43993a50caa27fe89a52f55a6e6e69ec9d`.

Per `governance/AIOS_CORE_S2_POST_FIX002_PARALLELISM_RULING_2026-09-24.md`, #157 must now:
1. merge/rebase current live main containing FIX-001;
2. rerun targeted + full gates;
3. produce a new exact head;
4. receive fresh independent acceptance on that new exact head.

No pre-integration #157 review result may authorize direct merge.

## Release effect

CG-001 is closed and CORE-GAP-FIX-001 is DONE.
CORE-HEADLESS-001 remains blocked until FIX-003 is rebased, independently accepted, and integrated.
No Resident is authorized.
