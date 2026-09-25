# C15-RCC-RES-B-PREFLIGHT-002 — Model/Provider Identity Inventory

Per release_contract §8 and preflight §11, we inventory trustworthy model/provider identity evidence available for the three Residents.

## Trust standard

Configured model strings, model self-description, branch names, Python constants, and operator prose are **NOT** trusted attestation. Trusted identity would require an external platform/artifact that binds a specific model-provider response to a session/request outside Resident control.

## Accepted A-002

- Evidence PR #205 `freeze/identity.json` records session and process identity but NOT trusted model-provider identity.
- `freeze/software_identity.json` pins Core software identity but not provider.
- The acceptance report notes "model/provider telemetry remains unknown."
- A-002 metering records capture provider response model/request IDs where observed, but these are not independently attested.
- **Trusted model/provider identity: UNKNOWN.**

## Planned fresh B

- The B release operator will record whatever provider metadata comes back from API calls (model name in response, request IDs, HTTP headers) in `$RUN_ROOT/evidence/freeze/`.
- Unless the execution platform adds an external attestation channel that is not under Resident control, B identity will also be **UNKNOWN** at acceptance time.
- This does NOT block B execution-evidence continuity; per release_contract §8 it remains relevant to the later replacement-model gate (R6) for C.

## Replacement-model C (future)

- R6 (replacement-model gate) requires that C be a different model family/provider than A and B.
- Without trusted attestation, R6 cannot be VALID even if phase C otherwise completes.
- This preflight does NOT attempt to solve the identity attestation problem. If the platform later adds a trusted external attestation artifact (e.g. signed provider response headers), a separate `C15-RCC-MODEL-ATTEST-001` task will bind it to the relevant sessions.
- **Status: UNKNOWN / INSUFFICIENT_EVIDENCE for R6 (intentionally left open).**

## Summary

| Phase | Trusted model identity | Blocking for execution-evidence? |
| --- | --- | --- |
| A-002 (accepted) | UNKNOWN | No (already accepted on execution-evidence grounds, not R6) |
| B (planned) | UNKNOWN at preflight time; record whatever platform provides | No |
| C (future, BLOCKED) | INSUFFICIENT_EVIDENCE (for R6) | Yes, for R6; C execution itself is blocked pending B acceptance regardless |
