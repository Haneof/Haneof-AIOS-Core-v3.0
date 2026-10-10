# PM49-BLK-002V Final Secret Isolation & Ephemeral Authority Closure Dossier

- **Formal Task**: `C15-RCC-OPERATOR-PERSISTENCE-COMPATIBILITY-CORRECTIVE-001`
- **Repository**: `Haneof/Haneof-AIOS-Core-v3.0`
- **Window**: `49`
- **PR**: `#352` (`c15-rcc-operator-persistence-compatibility-corrective-001-window49`)
- **PM Adjudication Reference**: Comment `6078680135`
- **Target Blocker**: `PM49-BLK-002V = CLOSED` (Previously `BINDING / CRITICAL`)
- **Architectural Paradigm**: **Model A — Memory-Only Ephemeral Provider Authority**

---

## 1. Blocker Analysis & Historical Root Cause

In historical HEAD `3074b0592d214865b27adc9a7ac300e64bb715a2`, `tools/c15_persistence/provider_process.py` attempted to resolve process re-attachment across directory wipes by serializing the private RSA key components (`n`, `e`, `d`) to `/tmp/.aios_provider_vault/{instance_id}.key` (permission 0600).

As ruled in PM Comment `6078680135`:
1. Because the Operator process and Provider process run under the **exact same OS UID**, any file-based vault (even with 0600 permissions) is directly accessible to rogue operator code.
2. An operator could read `d` directly from disk and forge trusted return proofs without crossing the provider process boundary or invoking the genuine model.
3. This violated the core trust boundary of Route B / Corrective-003: provider private signing authority must remain completely inaccessible to the operator caller.

---

## 2. Model A Architectural Implementation

To permanently eliminate this vulnerability, we implemented **Model A: Memory-Only Ephemeral Provider Authority**:

### A. Strictly Zero Key Material on Disk (No Vault, No Temp, No Persistence)
- Completely deleted all references to `.aios_provider_vault` across the codebase.
- Private key components `(n, e, d)` are generated via CSPRNG purely within `ProviderService.__init__()` and held **exclusively in the Python process memory heap** (`PROVIDER_PID != OPERATOR_PID`).
- The filesystem contains **ZERO** private key files or fields. Public descriptor `provider-public.json` contains only public modulus, exponent, fingerprint, and instance UUID.

### B. OS Kernel File-Lock IPC Runtime Boundary
- Provider service establishes an isolated OS runtime directory:
  `tempfile.gettempdir() / ".aios_provider_runtime" / instance_id`
- Acquires an exclusive `fcntl.flock(LOCK_EX)` on `provider.lock`.
- If the provider process terminates or is killed via `SIGKILL`, the OS kernel automatically releases the flock and the heap private key vaporizes instantly.

### C. Multi-Directory IPC Command Routing
- When tests simulate total local cache wipes (e.g., `wipe(first_parent)` and restore to `fresh_parent`), the provider process continues running in OS background memory.
- `ensure_provider_service()` checks `is_instance_alive(pinned_instance)`:
  - If the pinned provider is alive in memory, it rebinds the running instance's public descriptor to the new session mailbox without generating new keys.
  - Commands pass `mailbox` path in the JSON payload, allowing the memory-resident provider to read requests and output signed responses directly into the new session mailbox.
- If the provider process was truly terminated (SIGKILL/stopped):
  - Post-boundary recovery with pre-crash durable proof completes with **0 provider commands** entirely offline.
  - Post-boundary recovery without durable proof **strictly fails closed** (`PINNED_PROVIDER_UNAVAILABLE` / exit code 42), completely prohibiting rogue provider restarts from minting untrusted proofs.

---

## 3. Dedicated Verification & Regression Evidence

In `tests/c15_persistence/test_pm49_blockers.py`, 5 dedicated regressions were added and 100% verified green:

1. `test_pm49_blk002v_historical_operator_vault_mint_attack_prevented`:
   - Validates that legacy vault `/tmp/.aios_provider_vault` does not exist and no private key file can be inspected by operator.
2. `test_pm49_blk002v_candidate_memory_only_secret_boundary`:
   - Validates that `PROVIDER_PID != OPERATOR_PID`, and recursive scan of all mailbox files confirms zero occurrences of `"d":` or `PRIVATE KEY`.
3. `test_pm49_blk002v_post_sigkill_private_key_vaporization`:
   - Validates that killing provider process via `SIGKILL` vaporizes authority instantly (`is_instance_alive() == False`, lock released, zero key artifacts left on disk).
4. `test_pm49_blk002v_whole_repo_and_filesystem_zero_private_key_scan`:
   - Comprehensive audit verifying zero private keys or static secrets across `tools/`, `tests/`, and `/tmp/.aios_provider_runtime/`.
5. `test_pm49_blk002v_offline_resume_zero_provider_contact_or_fail_closed`:
   - Validates that dead provider with pre-crash proof succeeds offline (0 commands), while dead provider without durable proof fails closed.

---

## 4. Verification Suite Summary

| Test Suite | Total Tests | Passed | Failed | Status |
| :--- | :--- | :--- | :--- | :--- |
| `tests/c15_persistence/test_pm49_blockers.py` | 25 | 25 | 0 | **100% GREEN** |
| `tests/c15_persistence/` (Full Persistence Suite) | 105 | 105 | 0 | **100% GREEN** |
| `tests/unit/`, `tests/runtime/`, `tests/integration/`, `tests/habitation/`, `tests/preflight/` | 1059 | 1059 | 0 | **100% GREEN** |
| **Total Regressions** | **1164** | **1164** | **0** | **100% GREEN** |

---

## 5. Constitutional & Invariant Compliance

- **`src/aios_core/**`**: **0 files modified, 0 lines modified** (100% immutable).
- **`.github/workflows/**`**: **0 files modified, 0 lines modified** (100% immutable).
- **Window 49 Stop Boundary**: `REVIEW_READY` / `READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE` / `DO NOT MERGE`.
