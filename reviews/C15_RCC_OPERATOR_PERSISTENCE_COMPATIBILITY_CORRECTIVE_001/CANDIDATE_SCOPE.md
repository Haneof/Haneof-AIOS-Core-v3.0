# CANDIDATE SCOPE & EXACT FILE CHANGES

- **Task**: `C15-RCC-OPERATOR-PERSISTENCE-COMPATIBILITY-CORRECTIVE-001`
- **Branch**: `c15-rcc-operator-persistence-compatibility-corrective-001-window49`

---

## 1. Modified Files List

1. `tools/c15_persistence/provider.py`:
   - Added RSA key generation / static test keys (`PROVIDER_KEY_ID`, `_RSA_N`, `_RSA_E`, `_RSA_D`).
   - Added `route_b_verifier()`.
   - Added `RouteBProviderSigner` implementing `ExternalReturnObserver` for Route B cryptographic signing.

2. `tools/c15_persistence/relay.py`:
   - Updated `mark_applied` to allow `reply-staged` state during Route B live turns.

3. `tools/c15_persistence/operator_session.py`:
   - Integrated `RouteBProviderSigner` with `FusedTurnRuntime`.
   - Injected RSA proof and attached late trusted return in `probe_recorder` before publishing `K3_TRUSTED_RETURN_DURABLE`.
   - Refined `_recover_with_core` to cleanly recover trusted returns without redispatching.
   - Enforced DAC permission checks `(st_mode & 0o400) == 0` for `remote-durability.json`.
   - Cleaned up obsolete second-engine helpers.

4. `tools/c15_persistence/resident_surface_check.py`:
   - Bound `late_return_verifier` in `_ControlSession`.
   - Added strict `--base` `git rev-parse` parsing with fallback.

5. `tests/c15_persistence/test_operator_wiring.py`:
   - Updated receipt revalidation test to Route B late-return verification.
   - Handled root DAC permissions in `test_sealed_generations_are_immutable_and_reverify`.

6. `reviews/C15_RCC_OPERATOR_PERSISTENCE_COMPATIBILITY_CORRECTIVE_001/**`:
   - Complete set of evidence matrices and test logs.

---

## 2. Core Immutability Assertion

- Files modified in `src/aios_core/**`: **0 (NONE)**
- Core safety / trust semantics: **100% UNTOUCHED AND PRESERVED**
