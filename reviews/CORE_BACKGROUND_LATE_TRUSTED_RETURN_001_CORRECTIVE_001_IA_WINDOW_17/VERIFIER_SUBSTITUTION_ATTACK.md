# Public Verifier Substitution & Rebinding Audit (`VERIFIER_SUBSTITUTION_ATTACK.md`)

- **Reviewed Exact Candidate:** `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`PR #308`)
- **Audited Source Location:** `src/aios_core/runtime/background_attempt.py:1066-1152, 1821-1865`

## 1. Direct Verifier Table Rebinding (`IA17-VERIFIER-SUB-001` = `PASS`)

- `background_model_return_verifiers` is written only by `mark_dispatching` (`background_attempt.py:1131`) using `INSERT INTO background_model_return_verifiers` (no `REPLACE` or `ON CONFLICT DO UPDATE`), guarded by `current.state == 'admitted'` and `not self._durable_submission_artifacts(conn, attempt_id)`.
- `attach_late_trusted_return` (`background_attempt.py:1821-1865`) loads `LateReturnVerifier` exclusively from the durable `background_model_return_verifiers` row in SQLite, ignoring `FusedTurnRuntime.late_return_verifier` passed to a recovery runtime constructor.
- Probe `IA17-VERIFIER-SUB-001` verified that a recovery caller passing `attacker_verifier` (`key_id="attacker-key-99"`) to `FusedTurnRuntime` or calling `mark_dispatching` post-crash cannot overwrite the stored `legit-key-1` verifier row or attach a proof signed under `attacker-key-99`.

## 2. Complete Bypass of `background_model_return_verifiers` via `_capture_trusted_response_return` (`IA17-MINT-001` = `FAIL` / `BLK-W17-001`)

Although the `background_model_return_verifiers` row itself cannot be overwritten via `mark_dispatching`, `BackgroundModelAttemptStore._capture_trusted_response_return` (`background_attempt.py:2050-2217`) **does not consult `background_model_return_verifiers` at all**.
- Therefore, a recovery caller does not need to substitute the verifier row: calling `recovery.background_model_attempts._capture_trusted_response_return(attempt_id, captured_at=..., directive=forged)` bypasses `background_model_return_verifiers` completely, writes `background_model_response_receipts` + `background_model_return_handoffs` with a keyless `bgresponse_v2_<sha256>` checksum, and completes the turn (`BLK-W17-001`).
