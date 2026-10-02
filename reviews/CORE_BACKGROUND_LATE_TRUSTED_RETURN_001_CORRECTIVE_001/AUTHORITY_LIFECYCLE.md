# AUTHORITY_LIFECYCLE

T1. **Signer creation** — outside Core, in the trusted external/provider integration. Core never generates the private key.

T2. **Signer holder** — only the external trusted side. The Core process, BackgroundModelAttemptStore, SQLiteWorldStore and FusedTurnRuntime never receive private signing material.

T3. **Core verifier** — `LateReturnVerifier`: key id, RSA modulus, public exponent and algorithm, durably pinned to the exact first-dispatch request scope.

T4. **After process death** — Core retains attempt state, request binding, public verifier and consumed marker only. It has no signing/mint capability.

T5. **Full DB disclosure** — reveals only public verifier and public/durable request/response facts. Historical capability nonce and HMAC authority tables are securely purged with secure-delete plus WAL TRUNCATE.

T6. **Post-restart genuine return** — external side signs `late_return_message(scope + exact provider/model/request id + exact response fingerprint + payload SHA-256)`; recovery submits exact bytes + proof; Core verifies and atomically adopts them.

T7. **Signer invalidation / consumption** — first valid proof atomically sets `consumed_at`. Core will thereafter accept only an exact idempotent replay matching the already durable canonical receipt/handoff. A conflicting valid signature is refused.

T8. **Retry lifecycle** — post-binding retry is structurally unreachable. A genuine pre-submission retry is legal only from admitted with zero binding, zero verifier/capability and zero receipt; the first real dispatch then pins its verifier and request scope.

T9. **Consumed proof replay** — identical bytes/proof converge to the same receipt, handoff, staged response, meter, semantic effect, assistant output and completion. No second provider request or durable effect is produced.

T10. **Conflicting proof** — different attempt/round/subject/work/request fingerprint/relay/provider/model/request id/payload, corrupted proof, missing proof and duplicate JSON all fail closed.
