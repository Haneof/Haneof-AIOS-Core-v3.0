# REMOTE PROVENANCE & DURABILITY MATRIX

- **Task**: `C15-RCC-OPERATOR-PERSISTENCE-COMPATIBILITY-CORRECTIVE-001`
- **Scope**: Remote-authoritative state synchronization, git backend transport, sealed generation tree hashing, and catastrophic local loss recovery.

---

## 1. Remote-Authoritative Persistence Guarantees

1. **Synchronous Barrier Push**:
   - `_persist_remote_barrier` commits and pushes the backend tree to the authoritative remote git ref *prior* to crossing hazardous kill points or returning to caller.
   - Remote commits contain the full sealed snapshot: `state/`, `mailbox/`, `journal.sqlite`, `runtime/world.sqlite`, and `manifest.json`.

2. **Total Local Loss Recovery (`materialize_and_attach`)**:
   - Tested extensively across:
     - `test_c002_002_a_k3_trusted_return_first_round_remote_only_converges`
     - `test_c002_002_d_k5_push_success_then_total_local_loss_acks_once`
     - `test_c002_001_c_k4_failure_restart_recovers_from_authoritative_state_once`
     - `test_c002_002_e_k5_prepush_crash_recovers_from_prior_authoritative_barrier`
   - In every case, deleting the local directory entirely (`wipe(parent)`) and resuming from a fresh clone (`fresh_parent`) converges with zero duplicate side effects.

3. **Remote Durability Configuration DAC Security**:
   - Strict file mode checking `(st_mode & 0o400) == 0` ensures unreadable configuration files fail immediately even when running with root privileges (e.g. WSL default).
