# CORE-CI-FIX-001 Integration Receipt — 2026-09-24

Status: DONE
Task: CORE-CI-FIX-001 / CORE-CI-FIX-001-CORRECTIVE-001
Finding closed: CI Finding 001 — branch-shape-dependent mechanical Core-diff guards

## History preserved

- Original engineering PR: #146.
- First candidate exact head: `1896b3e5257bd0eaea990f2b7a656e9747d899ba`.
- First independent acceptance: PR #150 -> ACCEPTANCE_FAIL.
- Historical blocker: `CORE-CI-FIX-001-ACCEPT-BLOCKER-001` (`pipefail + printf | grep -q` could fail open through SIGPIPE / status 141).
- Historical FAIL report remains unchanged at
  `reviews/CORE_CI_FIX_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`.
- Competing PR #144 remains SUPERSEDED / NOT INTEGRATED.

## Accepted corrective

- Corrected candidate PR: #146.
- Exact accepted head: `1eb24e101cdb1579c22c69b435cf9f79a3c359ad`.
- Corrective independent review PR: #156.
- Review exact head: `27079e9debc15e5de0821ea95befc01803d12cb0`.
- Corrective verdict: ACCEPTANCE_PASS.
- Blockers: 0.
- Review evidence merge: `f3d20c2200d62313719e6cf76861005683256c5b`.
- Candidate merge: `c3ec42214db57864f7951e28b75811b10db8be21`.

## PM integration verification

Before candidate integration PM re-verified:
- #146 remained OPEN / UNMERGED / Ready for review and exact head had not moved;
- GitHub recomputed the PR to `mergeable=true / mergeable_state=clean / rebaseable=true`;
- final candidate scope was exactly three workflow files:
  - `.github/workflows/c14-resident-fixture-v2.yml`
  - `.github/workflows/c14-semantic-repair-fixture.yml`
  - `.github/workflows/c15-rcc-fixture.yml`
- current main advancement since corrective baseline did not modify any `.github/workflows/**` file;
- all six protected-path predicates use non-pipe input;
- the historical SIGPIPE fail-open was independently reproduced;
- large-list Core and non-Core protected-path probes fail closed with explicit invariant rejection;
- divergent branch-shape positive proofs passed;
- final exact-head runs `35963746859`, `35963746913`, and `35963746718` were SUCCESS with guard steps executed.

The independent corrective review evidence was merged first, then the accepted candidate was merged with an expected-head pin.

## Closed behavior

The three mechanical guards no longer depend on a shallow local three-dot merge base for PR evaluation.
They distinguish:
- evaluation failure -> explicit guard-evaluation failure / exit 2;
- invariant violation -> explicit invariant rejection / exit 1;
- valid change -> exit 0.

The prior `pipefail + grep -q` false-negative edge is removed for all protected predicates.

## Honest post-merge note

No automatic GitHub Actions run was returned for merge commit
`c3ec42214db57864f7951e28b75811b10db8be21` at PM writeback time.
No post-merge green run is claimed. The accepted evidence is the exact-head positive/negative/adversarial run set
and the independent review.

## Release effect

The CI-trust prerequisite for `CORE-RC-FREEZE-001` is now satisfied.
This does not make RC-FREEZE READY by itself: remaining gap fixes and later HEADLESS / RECOVERY / SCALE gates
still must close. No Resident is authorized.
