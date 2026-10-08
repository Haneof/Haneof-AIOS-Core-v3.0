# PM49-BLK-002S: Final Provider Authority & Zero Static Secret Closure

- **Blocker ID**: `PM49-BLK-002S` (Iterative hardening of `PM49-BLK-002` / `PM49-BLK-002R`)
- **Severity**: `CRITICAL` / `BINDING`
- **Component**: `tools/c15_persistence/provider.py`, `tools/c15_persistence/provider_process.py`, `tools/c15_persistence/operator_session.py`
- **Status**: **RESOLVED / CLOSED**

---

## 1. Finding & Root Cause in Historical Candidate

In PM adjudication `6062257327`, the auditor observed that although `provider_process.py` ran as a separate subprocess:
1. `provider_process.py` contained hardcoded static RSA private key constants (`_RSA_D` and `_RSA_N`) in the source file (`ACTIVE_PROVIDER_PRIVATE_KEY_IN_REPO = YES`).
2. Under the strict AIOS Core security model:
   > **当前 accepted provider identity 对应的 private signing authority，不存在于 operator 可读取的仓库、文件系统、持久化状态、backup、evidence、环境变量或 Python import graph 中。**
3. Static private key constants in the repository violate zero-trust boundaries and allow local callers or attackers to forge trusted provider returns.

---

## 2. Definitive Closure Architecture

### A. Ephemeral CSPRNG RSA Keypair in Memory Heap
- **Zero Static Secrets**: All hardcoded RSA numbers (`_RSA_D`, `_RSA_N`) were completely purged from the repository. `ACTIVE_PROVIDER_PRIVATE_KEY_IN_REPO = NO`.
- **In-Memory Dynamic Generation**: On startup, `ProviderService` (`tools/c15_persistence/provider_process.py`) generates an ephemeral RSA-2048 keypair using CSPRNG (`cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key(public_exponent=65537, key_size=2048)`).
- **Subprocess Isolation**: The private key lives exclusively in the memory heap of `provider_process` (`PROVIDER_PID != OPERATOR_PID`).
- **Hard Import Wall**: `provider_process.py` contains `if __name__ != "__main__": raise ImportError(...)`, forbidding any in-process import into the operator or test process.

### B. Dynamic Public Verifier Descriptor
- On startup, the provider writes its public key parameters to `mailbox/provider-public.json` and a tamper-evident hash binding to `mailbox/provider-binding.json`.
- The operator client module (`tools/c15_persistence/provider.py`) holds **zero private material** and constructs the public `LateReturnVerifier` dynamically via `read_public_descriptor(mailbox)`.
- `read_public_descriptor` cross-validates `provider-public.json` against `provider-binding.json` to detect local verifier substitution attacks.

### C. Ledger Pinning & Fail-Closed Invariants
- `OperatorSession.create()` pins `provider_public_key_fingerprint` and `provider_instance_id` into `journal.sqlite`.
- Attacker substitution of `provider-public.json` is detected and fails closed (`BackendError: Provider fingerprint mismatch: verifier substitution detected`).
- Staged requests during recovery without a durable trusted return fail closed with `DurableTrustedReturnMissing` (0 signing requests made).
- No private key exists in `journal.sqlite`, world store SQLite, git commits, or audit logs.

---

## 3. Regression & Attacker Evidence Matrix

The suite `tests/c15_persistence/test_pm49_blockers.py` executes 12 rigorous attacker scenarios:

1. `test_pm49_blk001r_attacker_multi_commit_pr_with_earlier_drift_fails_closed`: Verifies multi-commit PR base drift detection.
2. `test_pm49_blk001r_unresolvable_base_authority_fails_closed`: Verifies failure when base authority cannot be resolved.
3. `test_pm49_blk001r_candidate_green_authoritative_base_resolution_passes`: Proves valid PR base resolution passes cleanly.
4. `test_pm49_blk002_red_operator_pid_equals_provider_pid`: Proves in-process execution is rejected.
5. `test_pm49_blk002_red_provider_authority_importable`: Proves direct import raises `ImportError`.
6. `test_pm49_blk002_candidate_green_provider_process_isolation_and_ledger_provenance`: Verifies PID separation and dispatch ledger recording.
7. `test_pm49_blk002_candidate_green_fail_closed_recovery_invokes_zero_provider_signing`: Proves recovery never signs or invents returns.
8. `test_pm49_blk002s_red_historical_static_rsa_key_extraction`: Proves zero hardcoded `_RSA_D` or static keys in repo.
9. `test_pm49_blk002s_candidate_green_zero_static_private_keys_in_repo_tree`: Scans all `.py`, `.json`, `.sql`, `.md` files for static RSA keys (0 found).
10. `test_pm49_blk002s_candidate_green_operator_cannot_mint_late_return_without_provider`: Verifies operator cannot forge signatures.
11. `test_pm49_blk002s_candidate_green_provider_service_refuses_generic_signing_oracle`: Verifies provider refuses arbitrary signing requests.
12. `test_pm49_blk002s_candidate_green_verifier_substitution_fails_closed`: Verifies tampered public descriptors fail closed.

---

## 4. Verification Summary

- `tests/c15_persistence/test_pm49_blockers.py`: **12/12 passed** (100% green)
- `tests/c15_persistence/`: **92/92 passed** (100% green)
- `tests/unit/`, `tests/runtime/`, `tests/integration/`: **836/836 passed** (100% green)
- `resident_surface_check`: **`RESIDENT_SURFACE_UNCHANGED`**
- Core Tree: **0 files, 0 lines modified (`src/aios_core/**` completely untouched)**
