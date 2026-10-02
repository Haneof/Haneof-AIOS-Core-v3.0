# Real Process Loss (`SIGKILL`) Review (`SIGKILL_REVIEW.md`)

- **Reviewed Exact Candidate:** `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`PR #308`)
- **Reviewer Probe:** `IA17-SIGKILL-001` in `reviewer_probes/window17_independent_attack.py` (frozen SHA-256 `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3`)

## Independent Multi-Process `SIGKILL` Verification (`IA17-SIGKILL-001` = `PASS`)

1. **Process A (Child):** Spawned as a separate OS process, ran `FusedTurnRuntime.run_turn`, durably committed `mark_dispatching` + `background_model_request_bindings` + `background_model_return_verifiers`, emitted public `LateReturnSigningContext` over a pipe to the external observer, and terminated via `os.kill(os.getpid(), signal.SIGKILL)` (`exitcode == -9`).
2. **External Signer (Outside Core):** Signed the exact response (`req-w17-sigkill-1`) using the external test RSA private key after confirming Process A's death.
3. **Process B (Fresh Recovery Runtime):** Reopened the SQLite database with a `model_handler` that raises `AssertionError` on any invocation, called `attach_late_trusted_return(...)`, and invoked `run_turn(...)`.
4. **Verified Outcomes:**
   - Zero provider redispatch (`provider_calls == []`),
   - Same `attempt_id` and round transitioned to `state == 'metered'`,
   - Exactly `1` meter record,
   - Exactly `1` assistant output (`inspection.state == 'completed'`, `assistant_ref` non-null),
   - Subsequent `run_turn(...)` replay raised `TurnAlreadyCompleted` with zero duplicate effects.
