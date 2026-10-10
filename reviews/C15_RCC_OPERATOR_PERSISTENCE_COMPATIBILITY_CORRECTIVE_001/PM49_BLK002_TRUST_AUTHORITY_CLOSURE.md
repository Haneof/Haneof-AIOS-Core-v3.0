# PM49-BLK-002 Closure: Private Signing Authority Isolation & Recovery Proof-Minting Elimination

- **Blocker ID**: `PM49-BLK-002`
- **Severity**: `CRITICAL`
- **Category**: Security / Cryptographic Trust Authority Isolation
- **Files Impacted**:
  - `tools/c15_persistence/_provider_authority.py` (New: isolated provider-internal private key store)
  - `tools/c15_persistence/provider.py` (Cleaned: public interface exposes only `route_b_verifier()`)
  - `tools/c15_persistence/operator_session.py` (Cleaned: removed `_external_signer` and late-return minting in recovery)
  - `tests/c15_persistence/test_pm49_blockers.py` (New: dedicated attacker regression suite)
  - `tests/c15_persistence/test_operator_wiring.py` (Updated)

---

## 1. Problem Statement
In previous candidate code:
1. `OperatorSession` held a reference `self._external_signer = RouteBProviderSigner()`, granting the operator session instance direct possession of private key material `_RSA_D`.
2. In `OperatorSession._recover_with_core()`, when recovering an attempt without a durable receipt, the operator executed:
   ```python
   proof = self._external_signer.sign(attempt_id, directive)
   attempts.attach_late_trusted_return(...)
   ```
   This effectively minted cryptographic late-return proofs on the recovery side after a crash, violating the Core security invariant that recovery callers cannot manufacture authenticity for unauthenticated requests.

---

## 2. Solution & Architectural Implementation

### A. Private Cryptographic Key Isolation
- Created `tools/c15_persistence/_provider_authority.py`:
  - Contains private key exponent `_RSA_D` and internal signing closure `rsa_sign_message`.
  - Exposes `ProviderSigningAuthority` with `sign_exact_provider_response(attempt_id, directive)`.
  - Only accessible by provider process/harness.
- Cleaned `tools/c15_persistence/provider.py`:
  - Removed `_RSA_D`, `rsa_sign`, and `RouteBProviderSigner` from the public namespace.
  - Public interface exports `route_b_verifier()` returning a `LateReturnVerifier` with RSA public key only (`_RSA_N`, `_RSA_E`).
  - Implemented `ProviderReturnObserver(ExternalReturnObserver)` to receive public dispatch context on provider dispatch boundary.
  - In `provider.collect()`: The provider process generates its response and signs its own response, writing the proof to `mailbox/inbox/{request_id}.proof`.

### B. Elimination of Operator/Recovery Proof Minting
- Cleaned `tools/c15_persistence/operator_session.py`:
  - Removed `_external_signer` completely from `OperatorSession`.
  - In `probe_recorder` (live path callback): Reads provider-minted proof from `mailbox/inbox/{request_id}.proof` and attaches it via Core's `attach_late_trusted_return`.
  - In `_recover_with_core` (recovery path):
    - Completely removed any calls to signing functions or late-return attachment.
    - If an attempt was dispatched without a durable receipt in Core SQLite, recovery raises `DurableTrustedReturnMissing` and fails closed (exit code 42), recording durable failure evidence without manufacturing unauthentic receipts.

---

## 3. Verification & Attacker Regressions
Implemented automated attacker tests in `tests/c15_persistence/test_pm49_blockers.py`:

1. **Static Inspection Attack Test** (`test_pm49_blk002_operator_session_has_no_private_key_or_signer_object`):
   - Proves `OperatorSession` instance and class have no private key, exponent, or signer object (`_external_signer`, `signer`, `_RSA_D`, `private_key`, `sign`).
   - Proves `operator_session` module does not import `_RSA_D`, `_provider_authority`, or `rsa_sign`.
   - Proves `provider` module does not export `_RSA_D` or `rsa_sign` in its public namespace.

2. **Arbitrary Signing Attack Test** (`test_pm49_blk002_provider_boundary_rejects_arbitrary_attacker_response_signing`):
   - Proves provider module does not expose arbitrary response signing endpoints to callers.

3. **Recovery Path Zero-Signing Attack Test** (`test_pm49_blk002_recovery_path_never_invokes_signing_authority`):
   - Uses monkeypatching to trace all calls to `rsa_sign_message`.
   - Simulates a crashed session where an attempt was dispatched without a durable receipt.
   - Proves `OperatorSession.resume()` fails closed with `DurableTrustedReturnMissing` while calling `rsa_sign_message` exactly 0 times.

4. **Positive Live Path Verification** (`test_pm49_blk002_positive_live_path_produces_and_verifies_provider_proof`):
   - Runs a full live turn through `OperatorSession.process_one_cursor()`.
   - Proves the turn executes end-to-end, producing valid provider proof and Core receipt, converging to `acked`.
