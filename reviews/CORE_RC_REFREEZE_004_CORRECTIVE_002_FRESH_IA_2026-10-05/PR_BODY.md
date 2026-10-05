# REVIEW_ONLY / DO NOT MERGE

This PR publishes reviewer-owned Fresh Independent Acceptance evidence for candidate PR #336. It is evidence-only; it does not modify the candidate, repair implementation, authorize PM integration, or authorize merge.

## Verdict

`ACCEPTANCE_FAIL / BINDING_BLOCKERS=2 / IA27-BLK-002_NOT_CLOSED / DO NOT MERGE`

Reviewed exact candidate: PR #336 at `5a5d384f16798bfff46ffe03f87310b0eafb2321` (OPEN / UNMERGED). Fresh `main`: `5927d7917112819c53593149ee8fab1eebdcfda6`.

## Binding findings

1. `IA27-BLK-002` remains BINDING / CRITICAL: the exact final-seal shell can return `WHOLE_RUN_IDENTITY_SEAL=PASS` after its one canonical-branch read even when a mocked ref advances before the shell finishes. The reproduction is local/mocked, not a live hosted final-step race.
2. `IA28-BLK-001`: the terminal protected-drift ERE at workflow line 464 misses late `.github/workflows/**`, `pyproject.toml`, and `setup.cfg` changes. The startup ERE at line 93 detects them, but cannot detect changes introduced after its snapshot.

The candidate's exact-head hosted run `37320392029` and its jobs are green, but that run does not falsify these counterexamples. Candidate #336 remains OPEN / UNMERGED / DO NOT MERGE.

## Evidence

See `reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002_FRESH_IA_2026-10-05/REPORT.md`, its `FINDINGS.md`, exact-source probes, raw results, and `SHA256SUMS`. The PR contains reviewer-owned acceptance evidence only; no `src/**`, `tests/**`, `tools/**`, candidate-branch, or mainline modifications.
