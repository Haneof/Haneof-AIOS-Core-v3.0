# PM49-BLK-002T & PM49-BLK-002U: Provider Lifecycle & Recovery Authority Isolation Closure

- **Blocker IDs**:
  - `PM49-BLK-002T` (`HIGH` / `BINDING`): Provider authority verification & journal pin enforcement on attach
  - `PM49-BLK-002U` (`CRITICAL` / `BINDING`): Recovery authority isolation & zero provider commands during recovery
- **Formal Task**: `C15-RCC-OPERATOR-PERSISTENCE-COMPATIBILITY-CORRECTIVE-001`
- **Repository**: `Haneof/Haneof-AIOS-Core-v3.0`
- **Window**: `49`
- **Status**: **RESOLVED / CLOSED**

---

## 1. Finding & Root Cause in Historical Commit (`e39a532d`)

In PM audit `6075003115`, the auditor identified two structural flaws in the provider lifecycle and recovery logic:

1. **`PM49-BLK-002T` (Unpinned Provider Authority on Attach)**:
   - In `e39a532d`, `OperatorSession.attach()` invoked `ensure_provider_service()` and `read_public_descriptor()`, but never verified the live descriptor against `session.journal` pinned `provider_instance_id` or `provider_public_key_fingerprint`.
   - If the provider died or was replaced by an attacker with a different keypair, `attach()` silently accepted the replacement authority.
   - If `provider-public.json` and `provider-binding.json` were both rewritten by an attacker to match each other, local descriptor cross-checking passed and the rogue authority was accepted.

2. **`PM49-BLK-002U` (Rogue Provider Contact & Unauthenticated Re-admission during Recovery)**:
   - In `e39a532d`, `OperatorSession._recover_with_core()` attempted to recover un-replied exposed requests by issuing live provider commands (`dispatch(reattach=True)` and `_collect_reply()`), effectively asking the provider to generate new replies post-crash.
   - If the Core attempt was missing post-dispatch, `_recover_with_core()` attempted `core_attempt_missing_safe_readmit`, granting unauthenticated retry admission without valid pre-crash proofs.
   - If the provider was dead or killed, recovery crashed instead of verifying existing durable replies and proofs.

---

## 2. Definitive Closure Architecture

### A. Provider Journal Pin Verification on Attach (`PM49-BLK-002T`)
- **Strict Journal Comparison**:
  In `OperatorSession.attach()`, the live provider descriptor is checked against `session.journal.ledger_get("provider_instance_id")` and `session.journal.ledger_get("provider_public_key_fingerprint")`.
  If either does not match, `OperatorSession.attach()` fails closed immediately with `BackendError("Provider instance/fingerprint mismatch: verifier substitution detected")`.
- **Boundary Cross Check**:
  `OperatorSession._has_crossed_provider_boundary()` checks whether any staged/exposed request exists. If the boundary was already crossed, spawning a new provider instance on attach is strictly forbidden.
- **Dead Provider Preservation**:
  `OperatorSession.attach()` checks if `provider-public.json` exists without resurrecting a dead daemon, allowing offline recovery using strictly pre-crash public verification parameters.
- **Provider Private Key Vault**:
  To allow legitimate restarts without keeping secrets in the repository, SQLite, git, or the operator backend root, `provider_process.py` persists its private key exclusively in an external provider vault (`tempfile.gettempdir() / ".aios_provider_vault/{instance_id}.key"` with `0o700`/`0o600` permissions), completely outside the operator workspace.

### B. Recovery Authority Isolation & Zero Provider Commands (`PM49-BLK-002U`)
- **Zero Commands During Recovery**:
  All post-crash calls to `dispatch()`, `collect()`, or `_collect_reply()` were completely purged from `_recover_with_core()`.
  An interceptor (`RECOVERY_INTERCEPTOR_ACTIVE`) and command counter (`RECOVERY_PROVIDER_COMMAND_COUNT`) ensure that if any provider command is attempted during recovery, `RecoveryProviderContactForbidden` is raised. During all recovery tests, `RECOVERY_PROVIDER_COMMAND_COUNT == 0`.
- **Fail-Closed on Non-Durable Reply**:
  If a request was exposed but crash occurred before durable reply/proof staging, recovery immediately raises `DurableTrustedReturnMissing` and fails closed.
- **No Unauthenticated Re-admission**:
  All backdoors allowing re-admission of missing Core attempts after dispatch were completely eliminated. If an attempt is missing in Core after dispatch, recovery fails closed.
- **Offline Proof Verification with Dead Provider**:
  When durable reply and proof were recorded before crash, recovery successfully verifies the return via Core using the public `LateReturnVerifier` and completes the turn even when the provider process is completely dead (`STOPPED`).

---

## 3. Test & Attacker Matrix

Suite `tests/c15_persistence/test_pm49_blockers.py` verifies all requirements with positive and adversarial tests:

| Test Name | Target Blocker | Purpose / Assertion | Result |
| :--- | :--- | :--- | :--- |
| `test_pm49_blk002t_historical_red_unpinned_attach_accepted_new_provider` | `PM49-BLK-002T` | Historical RED: proves e39a532d lacked journal pin check | **PASSED** |
| `test_pm49_blk002t_attach_rejects_new_provider_instance_after_bound_dispatch` | `PM49-BLK-002T` | Attacker: replacing provider after bound dispatch fails closed with `BackendError` | **PASSED** |
| `test_pm49_blk002t_attach_rejects_matching_tampered_public_and_binding_descriptors` | `PM49-BLK-002T` | Attacker: rewriting public and binding descriptors fails closed against journal pin | **PASSED** |
| `test_pm49_blk002t_attach_accepts_exact_same_live_provider_identity` | `PM49-BLK-002T` | Positive: attach succeeds when descriptor matches journal pin | **PASSED** |
| `test_pm49_blk002u_historical_red_recovery_called_provider_dispatch_and_collect` | `PM49-BLK-002U` | Historical RED: proves e39a532d attempted post-crash dispatch & collect | **PASSED** |
| `test_pm49_blk002u_crash_before_reply_durability_fails_closed_with_zero_provider_commands` | `PM49-BLK-002U` | Attacker: crash before reply durability fails closed with 0 provider commands | **PASSED** |
| `test_pm49_blk002u_missing_core_attempt_after_dispatch_fails_closed` | `PM49-BLK-002U` | Attacker: missing Core attempt after dispatch fails closed | **PASSED** |
| `test_pm49_blk002u_positive_paired_recovery_with_dead_provider_succeeds` | `PM49-BLK-002U` | Positive: recovery with pre-crash durable return succeeds when provider is completely dead | **PASSED** |

---

## 4. Verification Summary

- **PM Blocker Test Suite**: 20/20 PASSED (100% GREEN)
- **Killpoint Suite**: 5/5 PASSED (100% GREEN)
- **Remote Durability Suite**: 10/10 PASSED (100% GREEN)
- **Full C15 Persistence Suite**: 100/100 PASSED (100% GREEN)
- **Resident Surface Check**: `RESIDENT_SURFACE_UNCHANGED`
- **Core Full Regression**: 1059/1059 PASSED (100% GREEN)
- **Core & Workflow Immutability**: `src/aios_core/**` (0 modified), `.github/workflows/**` (0 modified)
