# CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002-INDEPENDENT_ACCEPTANCE — evidence index

Review-only evidence publication for the completed fresh Independent Acceptance of
PR #219's tested exact implementation:

  227327c657788efb1b5de1bc26e69c35c900a85e
  (parent 72aed7eddf22d0d7f05e53bb3bd46ed28554f7fc, tree 01dfa445414543aab41e1b74b813bbff80b21c5c)

«Independent Acceptance 的 PASS 只适用于该 exact implementation identity.»
Later governance-only/evidence-only heads must never be presented as new tested
exact implementations.

## Contents

- `../CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_002_INDEPENDENT_ACCEPTANCE_2026-09-27.md`
  — formal acceptance report (verdict ACCEPTANCE_PASS / blocker 0 /
  READY_FOR_PM_INTEGRATION).
- `environment.txt` — the reviewer's own formal execution environment.
- `frozen-probe-verification.txt` — frozen 12-probe hash + git-blob re-verification.
- `focused.txt` — focused regression results (17 GREEN / 43 GREEN) and log provenance.
- `full-suite.txt` / `full-suite-raw.txt` — original full-suite outputs
  (763 passed in 252.50s).
- `classification.md` — rev1 probe-harness defect classification record.
- `adversarial-rev1/` — preserved abandoned-with-record probe revision
  (49 collected / 40 passed / 9 failed = PROBE_HARNESS_DEFECT only).
  Status: ABANDONED_WITH_RECORD / HARNESS_DEFECTS_ONLY. Do not delete.
- `adversarial-rev2/` — the frozen executed adversarial revision
  (49 collected / 49 GREEN), incl. per-file and combined SHA-256 manifests,
  collect-only output and execution output.
- `SHA256SUMS.txt` — SHA-256 of every published file in this directory.

## Artifact provenance rules applied

- Probe files in `adversarial-rev1/` and `adversarial-rev2/` are the ORIGINAL
  frozen bytes of the acceptance session; each set was re-verified against its
  original manifest at publication time (per-file and combined hashes match).
  No probe was regenerated, and no expected outcome was altered.
- Where a raw console log was never captured during the acceptance session, the
  file states `ARTIFACT_NOT_RECOVERABLE` instead of fabricating a substitute.
- This publication contains review/evidence material only. It modifies no
  `src/**`, no candidate tests, and no frozen 12-probe.
