# Corrective-003 scope audit

## Allowed candidate paths

- `.github/workflows/core-rc-refreeze-004-formal-gate.yml`
- `reviews/CORE_RC_REFREEZE_004_CORRECTIVE_003/**`

The formal Job A diff allowlist is narrowed to exactly these paths.

## Explicitly excluded

- `src/**`, product `tests/**`, `tools/**`, `pyproject.toml`;
- C15 implementation, Resident state/evidence, evaluator, release/tag;
- PR #336 and PR #337 refs/files;
- JUnit hardening expansion or any package/release work.

The only imported test utilities are byte-for-byte copies of previously accepted reviewer probes under the allowed Corrective-003 evidence directory. The C15 classifier's logic is unchanged and continues to classify actual pytest exit code + JUnit output as before.

## Workflow security contract

- Top-level workflow permissions are read-only.
- Formal Job A explicitly has `contents: read`, `pull-requests: read`; checkout has `persist-credentials: false`.
- Formal candidate scripts execute only in Job A; no candidate script gets write credentials.
- The publisher is fixed inline logic with no checkout and no candidate script. It has exactly `contents: write` for commit comments and performs one POST to `/commits/{sha}/comments`.
- Publisher transport errors and any non-201 HTTP response fail.
- Whole-run and control seals are read-only, no-checkout jobs.
- Candidate pin remains provisional; exact run/attempt/branch/SHA/pin and current branch identity are required for any later acceptance decision.

## Branch / pull-request disposition

Arena requires all work on `arena/01a10c8c-haneof-aios-core-v3-0`. The new PR must remain open, non-draft, unmerged, and explicitly DO NOT MERGE for independent acceptance. PR #336 and #337 remain untouched and unmerged.
