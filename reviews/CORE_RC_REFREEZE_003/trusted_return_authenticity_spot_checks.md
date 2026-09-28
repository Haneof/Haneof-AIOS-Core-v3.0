# CORE-RC-REFREEZE-003 — Trusted-Return Corrective / Authenticity Spot Checks

Status: **PASS** in fresh run [36436264055](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/36436264055), with **248 focused tests passed**, zero failures/errors/skips, plus the full 919-test pass.

Freshly verified by the selected test group and registry probe:

1. R1–R5 trusted-return and recovery behavior.
2. Runtime registry surface: **43 total / 22 side-effecting**; the sorted live registry exactly matches all **22** frozen R5-C replay-matrix rows (`REGISTRY_MATRIX_PASS`). The probe never dispatches a model. Exact names are listed in `focused_regressions.md` and the structured run record.
3. Identical recovered capability replay converges exactly once across the matrix; changed/conflicting requests and corrupt/skewed operation/idempotency state fail closed where specified.
4. Authenticity/transplant/corruption cases reject invalid handoff bytes or transplanted proof before capability application, provenance rewrite or metering.
5. Real process-loss and ordinary exception/restart paths preserve trusted-return receipt ordering; recovery does not call the provider again or duplicate meter/effect/output.
6. `call_id` is not durable authority; request fingerprint and World revision semantics remain covered by the frozen matrix.

Exact selected test paths are enumerated in `focused_regressions.md`. These fresh tests and outputs do not reuse historical #261/PM or prior-RC counts.

- Trusted-return JUnit SHA-256: `df0ca41dee7db87fcce248dce1ace81a350dfb5d8040d32b99bcc11ba5faf4a0`
- Trusted-return regression output SHA-256: `cfecb09eb205b283e78c3043b770079384883b1b25c24c7a8484ff8dedae8229`
- Registry inventory output SHA-256: `f6a676ba174cd12a0f1ae63e5df8c7db20ad71b317ee0a998308ca419a9c5ae6`
- Run, hosted artifact digest and all output checksums: `formal_gate_run.json`.
