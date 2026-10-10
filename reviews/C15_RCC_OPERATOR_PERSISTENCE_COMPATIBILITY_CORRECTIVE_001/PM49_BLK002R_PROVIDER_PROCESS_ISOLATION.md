# PM49-BLK-002R Closure: True Process-Separated Provider & Zero In-Process Signing Authority

- **Blocker ID**: `PM49-BLK-002R`
- **Severity**: `CRITICAL`
- **Binding**: **YES**
- **Root Cause**: Private RSA key `_RSA_D` was previously located in `_provider_authority.py` in the same Python package, and `OperatorSession` called `provider_module.collect()` in-process, resulting in `PROVIDER_PID == OPERATOR_PID` and import-level reachability of signing authority.
- **Closure Status**: **CLOSED**

---

## 1. Technical Architecture & Isolation Design

1. **Isolated Subprocess Execution (`tools/c15_persistence/provider_process.py`)**:
   - Provider operations (`dispatch`, `collect`, `serve`) execute exclusively as an independent operating system process (`subprocess.run([sys.executable, "-m", "tools.c15_persistence.provider_process", ...])`).
   - `provider_process.py` strictly asserts `if __name__ != "__main__": raise ImportError(...)`, permanently preventing in-process imports by operator, runner, or test processes.
   - Dispatch and collect records include `provider_pid = os.getpid()`, verified to satisfy `PROVIDER_PID != OPERATOR_PID`.

2. **Zero In-Process Signing Material (`tools/c15_persistence/provider.py`)**:
   - Private key constant `_RSA_D` and all signing methods were completely removed from `provider.py`.
   - `_provider_authority.py` was eliminated (replaced with an unconditional `ImportError`).
   - `provider.py` acts purely as a public client exposing `route_b_verifier()` (public `LateReturnVerifier`) and mailbox trigger helpers.

3. **Data-Only Mailbox IPC**:
   - Communication between operator and provider occurs exclusively via filesystem mailbox (`mailbox/outbox/*.request`, `mailbox/inbox/*.reply`, `mailbox/inbox/*.proof`, `mailbox/contexts/*.json`).
   - No signing oracle RPC or generic signing function is exposed.

4. **Fail-Closed Recovery Contract**:
   - In `OperatorSession._recover_with_core()`:
     - If provider dispatch occurred but no Core-owned durable trusted return receipt exists in SQLite, recovery raises `DurableTrustedReturnMissing` and stops fail-closed.
     - Recovery never calls any signing functions.

---

## 2. Attacker Test Evidence in `tests/c15_persistence/test_pm49_blockers.py`

- `test_pm49_blk002r_provider_process_runs_in_separate_pid`: Asserts `dispatch` and `collect` run in a separate subprocess and record `provider_pid != os.getpid()` in `dispatch-ledger.jsonl`.
- `test_pm49_blk002r_operator_process_cannot_import_private_authority`: Proves `import tools.c15_persistence.provider_process` and `import tools.c15_persistence._provider_authority` raise `ImportError`; asserts `OperatorSession` and `provider_module` possess zero private keys or signing functions.
- `test_pm49_blk002r_provider_boundary_rejects_arbitrary_attacker_response_signing`: Proves no public signing oracle exists.
- `test_pm49_blk002r_recovery_path_never_invokes_signing_authority`: Proves recovery with missing receipt raises `DurableTrustedReturnMissing` with zero signing calls.
- `test_pm49_blk002r_positive_live_path_produces_and_verifies_provider_proof`: Proves full live turn executes with provider-produced proof verified by Core's `LateReturnVerifier`.
