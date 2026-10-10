# CORE CONTRACT ADAPTATION — C15 DOWNSTREAM OPERATOR / PERSISTENCE

- **Task**: `C15-RCC-OPERATOR-PERSISTENCE-COMPATIBILITY-CORRECTIVE-001`
- **Role**: `C15 Downstream Operator / Persistence Compatibility Corrective Engineer`
- **Core Immutability Invariant**: `src/aios_core/**` was **NOT modified** (0 lines touched, 0 files changed).
- **Adapted Accepted Core Surfaces**:
  - `src/aios_core/runtime/late_return.py` (`LateReturnVerifier`, `LateReturnSigningContext`, `verify_late_return_proof`, `late_return_message`)
  - `src/aios_core/runtime/background_attempt.py` (`BackgroundModelAttemptStore.attach_late_trusted_return`, `BackgroundModelAttemptStore.late_return_signing_context`, `BackgroundModelAttemptStore.response_authenticity_receipt`)
  - `src/aios_core/runtime/turn_runtime.py` (`FusedTurnRuntime.__init__(late_return_verifier=..., external_return_observer=...)`)
  - `src/aios_core/runtime/cognitive_runtime.py` (Route B model handler / response recovery)

---

## 1. Route B Adaptation Summary

In RC004 / Corrective-003, Core adopted **Route B Cryptographic Late-Return Authority**:
1. Live local handler returns no longer mint caller-manufacturable HMAC receipts.
2. An external provider/relay binds an RSA public key verifier (`LateReturnVerifier`) at dispatch time.
3. Durable trusted return receipts (`BackgroundModelResponseReceipt`) and return handoffs (`BackgroundModelReturnHandoff`) are created exclusively via `attach_late_trusted_return` upon presentation of a valid RSA signature over the canonical late-return message.

### C15 Downstream Changes

1. **Synthetic Provider RSA Signer (`tools/c15_persistence/provider.py`)**:
   - Added fixed 2048-bit deterministic test RSA key pair (`PROVIDER_KEY_ID = "c15-synthetic-provider-rsa-key-001"`).
   - Added `route_b_verifier()` returning `LateReturnVerifier` with the public exponent and modulus.
   - Added `RouteBProviderSigner(ExternalReturnObserver)` that captures the `LateReturnSigningContext` dispatched by Core and signs directive payloads using standard PKCS#1 v1.5 SHA-256 signatures.

2. **Relay Journal State Machine (`tools/c15_persistence/relay.py`)**:
   - Updated `mark_applied` to accept `reply-staged` state under Route B live turns, preserving linear forward journal state transitions (`staged` -> `exposed` -> `reply-staged` -> `authenticated` -> `applying` -> `applied` -> `acked`).

3. **Operator Session Runtime Wiring (`tools/c15_persistence/operator_session.py`)**:
   - Wired `late_return_verifier=provider_module.route_b_verifier()` and `external_return_observer=self._external_signer` in `_build_runtime()`.
   - Updated `probe_recorder` to attach late trusted return via `runtime.background_model_attempts.attach_late_trusted_return(...)` and mark the journal authenticated before publishing `K3_TRUSTED_RETURN_DURABLE`.
   - Refined `_recover_with_core` to cleanly reattach and verify durable returns without redispatching providers or fabricating synthetic receipts.
   - Enforced strict DAC permission checks `(stat().st_mode & 0o400) == 0` for `remote-durability.json` so unreadable configurations fail on root accounts in WSL environments.
   - Removed any remaining second-engine helpers (e.g. `encode_model_directive`) from `operator_session.py`.

4. **Resident Surface Checks (`tools/c15_persistence/resident_surface_check.py`)**:
   - Configured `late_return_verifier=provider_module.route_b_verifier()` on `_ControlSession`.
   - Added strict `--base` revision parsing via `git rev-parse` with fallback to `origin/main` / `HEAD`.

5. **Test Harness Updates (`tests/c15_persistence/test_operator_wiring.py`)**:
   - Adapted `test_core_receipt_revalidation_rejects_an_operator_invented_receipt` to Route B semantics: verified that tampering with the authenticity proof or trying to inject a bogus receipt is rejected by Core.
   - Handled root DAC permissions in `test_sealed_generations_are_immutable_and_reverify`.
