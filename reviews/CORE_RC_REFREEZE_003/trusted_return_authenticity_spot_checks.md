# CORE-RC-REFREEZE-003 — Trusted-Return Corrective Spot Checks

Status: **FRESH FORMAL RUN PENDING**.

The target test matrix and dedicated registry probe will freshly verify:

1. Runtime registry surface exactly matches the accepted frozen matrix: 43 model-callable capabilities, 22 reachable side-effecting entries.
2. Identical recovered capability replay converges exactly once for every matrix row without a second durable effect.
3. Same-key changed requests and corrupt/skewed operation/idempotency state fail closed; relation/policy changed requests create a distinct operation only where the frozen domain contract permits.
4. Tampered handoff bytes and transplanted authenticity proof are rejected before capability application, provenance rewrite or metering.
5. Provider return/receipt/recovery ordering survives ordinary exception, restart and real SIGKILL coverage; recovery does not call the provider again or duplicate meter/effect/output.
6. `call_id` is not durable authority; canonical request fingerprint and World-revision semantics remain intact.

Fresh evidence inputs:

- `trusted-return-junit.xml` and `trusted-return-regression.txt`
- `trusted-return-registry-inventory.txt`
- test target tree and commit recorded in `source_manifest.json`

Run ID, exact matrix count, JUnit counts and outcome: pending. Historical #261/PM evidence is not reused as a fresh result.
