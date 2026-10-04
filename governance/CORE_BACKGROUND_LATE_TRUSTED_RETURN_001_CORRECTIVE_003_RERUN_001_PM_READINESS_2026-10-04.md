# WINDOW 22-RERUN-001 PM Readiness / Window 23 Fresh IA Release

Date: 2026-10-04

Task: `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003`

Candidate PR: #318

Fresh PM main: `1541b1ec1a8b40bdc67debd52af986c2869ee00e`

## PM readiness verdict

`WINDOW 22-RERUN-001 = REVIEW_READY / READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE / DO_NOT_MERGE`

This is not an Independent Acceptance verdict and does not authorize merge.

## Exact candidate identity

- PR #318 = OPEN / non-draft / UNMERGED / DO NOT MERGE
- remote engineering branch = `arena/01a101e0-haneof-aios-core-v3-0`
- exact candidate = `7ecb2250a488766915e1042a76472b3cd26d9107`
- parent = `30022b06e2795d20790dd4532bf6987146c1b432`
- tree = `1438a9ea6b8582453f963db5acb7f136e5ac5385`
- PR base = `1541b1ec1a8b40bdc67debd52af986c2869ee00e`

Remote branch tip, PR head and the formal workflow head are identical.

PR #310 remains frozen at `fec30bd1495017bf13f08b0ef5b1e241dfb0e247`.
PR #311 remains REVIEW_ONLY / DO NOT MERGE.

## Formal exact-head CI

Canonical final run = `37166276909`.

- workflow = `core-background-late-trusted-return-001`
- event = push
- attempt = 1
- head = `7ecb2250a488766915e1042a76472b3cd26d9107`
- conclusion = SUCCESS
- jobs = 12 / 12 SUCCESS

Formal environment:
- CPython 3.12.14
- pydantic 2.13.5
- pytest 8.4.2
- SQLite 3.45.1
- OpenSSL 3.0.13

Exact-head assertions:
- git HEAD = candidate
- GITHUB_SHA = candidate
- remote engineering branch head = candidate

## Required gates

PM independently verified from the final run/jobs/comments:

- W20 Suite A SHA-256 = `ec1dc5c2c5406d5d9e74825f62e0a17fb80f8ebd6dc250817fa048511ce292b5`
- W20 Suite B SHA-256 = `769242465817f31734661ba7ba9c3d5f7d06b8d3f5235d72d2026956d9b98eb1`
- W17 probe SHA-256 = `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3`
- failed candidate Suite A = `probes=4 failures=4`
- candidate Suite A = `probes=4 failures=0`
- candidate Suite B = `probes=7 failures=0`
- candidate W17 = `probes=14 failures=0`
- C3 author matrix = 28 pass; same matrix on failed candidate = 17 RED
- full Core = `928 passed / 0 failed / 0 errors`
- real SIGKILL + genuine external return = GREEN
- scope guard = `OUT_OF_SCOPE=0`, `FORBIDDEN_PATHS=0`, reviewer probe bytes unchanged, tracked build artifacts = 0

## Other automatic workflow RED classification

Several older workflows on the same candidate are RED. PM inspected the failed job logs.

Their failures are the already-adjudicated C15 persistence/operator compatibility debt:
the broad run reports `45 failed, 1092 passed`, and failed identities are under
`tests/c15_persistence/**` / `tools/c15_persistence/**`, including
`DurableTrustedReturnMissing` and `ack requires a durable application`.

This class is already frozen as:
`DOWNSTREAM_OPERATOR_COMPATIBILITY_DEBT / OUT_OF_SCOPE_FOR_CORE_CORRECTIVE`.

It does not override the dedicated formal Core gate, which ran
`tests/unit + tests/integration + tests/runtime + tests/habitation` and passed 928/0.

These legacy broad-workflow reds are downstream tooling/operator debt; they do not authorize
restoring the rejected local self-trust path.

## Evidence metadata observation

The committed `SHA256SUMS` contains 32 checksum entries plus four comment/header lines.
The final commit message says "31 entries"; PR #318 body correctly says 32.

Classification:
`OBS-PM-W22R-001 / NON_BLOCKING_METADATA_TYPO`.

Do not move the candidate head merely to correct this prose.

## Fresh IA disclosures

Window 23 must independently inspect:

1. inherited `attach_late_trusted_return` receipt/handoff-before-staging sequencing;
2. disclosed direct `record_response` residual behavior on a dispatching verifier-less attempt;
3. alternate receipt/handoff/staging mint paths not exercised by author probes;
4. the TIGHTEN_ONLY nature of historical test edits;
5. C3 matrix attacker-class blind spots.

Author evidence is navigation and claims-to-falsify only.

## Unique next READY

`WINDOW 23 — CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003-INDEPENDENT-ACCEPTANCE`

Fresh Independent Core Runtime Acceptance Reviewer only.

Window 23 must pin exact candidate `7ecb2250a488766915e1042a76472b3cd26d9107`, reconstruct frozen probes independently, and try to falsify the Route-B boundary.

Window 23 must not repair, merge, enter PM Integration, enter RC-REFREEZE-004, or run Resident.

Only a Fresh IA PASS may release PM Integration.
