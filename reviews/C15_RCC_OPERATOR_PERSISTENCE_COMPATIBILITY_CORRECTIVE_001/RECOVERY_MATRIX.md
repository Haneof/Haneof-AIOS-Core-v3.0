# RECOVERY MATRIX — C15 DOWNSTREAM PERSISTENCE

- **Task**: `C15-RCC-OPERATOR-PERSISTENCE-COMPATIBILITY-CORRECTIVE-001`
- **Scope**: All kill points and recovery behaviors across both local and remote durability architectures.

---

## 1. Kill Point Recovery Table

| Kill Point | Point Name | Failure Injection / Crash Boundary | Recovery Disposition | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **K1** | `K1_AFTER_REVEAL` | After cursor is durably revealed in journal, before ingest | Ingests exactly once, continues turn | **CONVERGED** (1 reveal, 1 ingest, 1 ACK) |
| **K2** | `K2_AFTER_INGEST` | After event is durably ingested into World, before provider dispatch | Replays ingest idempotently without duplicating World Observation | **CONVERGED** (1 reveal, 1 ingest, 1 ACK) |
| **K3** | `K3_AFTER_REQUEST_DISPATCH` | After outbound request is staged/exposed, before reply exists | Hard fail-closed stop: refuses second dispatch, refuses invented receipt | **FAIL-CLOSED** (exit 42, `FAIL_CLOSED_NO_DURABLE_TRUSTED_RETURN`) |
| **K3 Barrier** | `K3_TRUSTED_RETURN_DURABLE` | After Core trusted-return boundary durably committed exact reply | Reattaches exact return from handoff, continues without second dispatch | **CONVERGED** (1 dispatch, 1 receipt, 1 ACK) |
| **K4** | `K4_AFTER_REPLY_AUTHENTICATED` | After Core authenticated exact reply, before downstream capability finish | Replays capability idempotently from ledger, completes turn | **CONVERGED** (1 dispatch, 1 side effect, 1 ACK) |
| **K5** | `K5_AFTER_APPLIED_BEFORE_ACK` | After model/capability work applied to World, before cursor ACK | Acks cursor from published authoritative barrier, zero duplicate work | **CONVERGED** (0 re-dispatch, 0 re-meter, 1 ACK) |
| **ACK** | `ACK_BARRIER` | Authoritative persistence failure during cursor ACK | Fatal error: previous barrier stays published, cursor is never falsely acked | **AUTHORITATIVE_FAILURE** (exit 41) |

---

## 2. Multi-Round Recovery Verification

- **Round 0 Converged -> Round 1 Killed at K3**: First round remains metered/applied; second round fails closed cleanly with attempt state `dispatching`.
- **Multi-Round Restart Idempotency**: Second recovery from same authoritative head yields identical deterministic outcome.
