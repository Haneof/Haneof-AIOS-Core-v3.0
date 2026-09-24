# CORE-GAP-FIX-001-RESUME-AFTER-FIX-002 — Temporal Read Cut continuation

Repository: Haneof/Haneof-AIOS-Core-v3.0

Continue the existing CORE-GAP-FIX-001 task in PR #145 / branch
`core-gap-fix-001-temporal-read-cut-20260924-r2`.

Do not restart from scratch and do not open a competing PR.

Before editing:
1. fetch live main;
2. read `governance/CORE_GAP_FIX_002_INTEGRATION_RECEIPT_2026-09-24.md`;
3. read `governance/AIOS_CORE_S2_SERIALIZATION_RULING_2026-09-24.md`;
4. read `governance/AIOS_CORE_S2_POST_FIX002_PARALLELISM_RULING_2026-09-24.md`;
5. read the original FIX-001 prompt and PR #145 evidence;
6. confirm the board says FIX-001 = READY / RESUME_EXISTING_WIP.

Required sequence:
- preserve reproduction SHA `a9a089a65414f9ba3a4b3dd6721edc3f05773834` and prior WIP evidence;
- rebase/merge current live main (which now includes accepted FIX-002) into the existing branch;
- resolve any conflict without changing FIX-002 provider-attempt/recovery semantics;
- complete CG-001 by establishing/passing the historical active read cutoff before model-visible
  cockpit/snapshot construction for resumed C14 and Periodic Review;
- keep the entrypoint change minimal and restricted to read-cut ordering/plumbing;
- rerun the original CG-001 reproduction, targeted regressions, directly affected suites, and full
  repository regression on the final rebased exact head;
- update PR #145 to REVIEW_READY only;
- do not merge, self-accept, run Residents, or modify governance/evidence.

If full CG-001 closure would require changing FIX-002 attempt identity, state transitions, retry,
reconciliation, metering, budget, Wake/Review completion, or user-turn recovery, stop and report PM.
