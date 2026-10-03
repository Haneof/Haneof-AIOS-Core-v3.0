# Window 20 — Historical Test-Modification Audit (`TEST_DIFF_AUDIT.md`)

Scope: every test file modified by `main…fec30bd…` (7 files), audited by
reading the old version at `ca47087…` and the new version at `fec30bd…`, per
task §22. Author claim to adjudicate: *"stricter only"*.

| File | Δ (vs main) | Old expectation removed | New expectation | Weakened? |
|---|---|---|---|---|
| `tests/integration/test_core_gap_fix_002_background_attempts.py` | +16/−20 | `test_definitely_not_submitted_can_retry_same_attempt_identity`: typed `ModelDispatchNotSubmitted` raised inside the handler after `mark_dispatching` → `not_submitted` + `safe_to_retry` + second successful dispatch | `test_typed_not_submitted_after_durable_dispatch_stays_in_doubt`: raises `BackgroundModelResponseConflict`; asserts `in_doubt`, binding preserved, `BackgroundModelExecutionInDoubt` on retry, and `seen_attempt_ids == [attempt_id]` (no second dispatch) | **no — stricter** |
| `tests/runtime/test_turn_execution_recovery.py` | +38/−35 | two retry-authorization tests (`…_known_not_submitted_requires_explicit_retry_authorization`, `…_reconciled_not_submitted_attempt_can_be_authorized_after_restart`) | replacements assert `in_doubt`, `TurnExecutionInDoubt` for `authorize_turn_retry` **and** `run_turn`, single provider call | **no — stricter** |
| `tests/runtime/test_background_model_attempt.py` | +103/−34 | direct `_capture_trusted_response_return` driving + post-binding `not_submitted` expectations | production live-window path; added absence assertion, `live_window=None` refusal, no-receipt assertions | **no — stricter** |
| `tests/runtime/test_cognitive_runtime_trusted_return.py` | +32/−5 | 2-arg authenticator signature | 3-arg authenticator (window threaded through); ordering assertion preserved; new assertions that an anonymous round yields `live_window=None`; new non-serializability/ctor test | **no — stricter** |
| `tests/integration/test_core_background_response_recovery_001.py` | +99/−35 | private-helper relay-return simulation | same via `capture_live_provider_return` helper; assertions retained | **no — equivalent, on the new API** |
| `tests/integration/test_core_background_response_recovery_001_corrective_001.py` | +38/−2 | private-helper relay-return simulation | same via live-window helper, with history note | **no — equivalent, on the new API** |
| `tests/integration/test_core_background_trusted_return_adversarial_001.py` | +50/−7 | private-helper calls | live-window helper + added `not hasattr(...)` and `live_window=None` refusal and zero-receipt assertions | **no — stricter** |

Adjudication:

1. **No security assertion was deleted or relaxed.** Every removed expectation is
   one the PM's Window 15 adjudication (§4.5) explicitly authorized/required
   retiring (post-`mark_dispatching` `not_submitted` + retry convenience).
2. **The PM test-evolution rule is satisfied**: the superseded behaviour is
   documented in the test docstrings (explicit "Corrective-002 history note"
   blocks naming `BLK-W17-001` and the superseded expectation); no expectation was
   altered silently.
3. **Adverse observation for the corrective (supporting `BLK-W20-001`):** the new
   shared helper `capture_live_provider_return(...)` in the modified tests is
   literally `open_live_provider_return_window` + `register_handler_return` +
   `record_live_provider_return`. The author's own "trusted relay return"
   simulation is therefore identical to the reviewer's forgery path — the tests
   were adapted onto an authority that any caller can construct, and they
   simultaneously document that the removed private helper's *capability* was not
   removed, only renamed and re-exported.

Independent regression on the candidate (reviewer-run, `tests/` = 1105 tests):
`231 passed` on the focused trusted-return set, `1104 passed / 1 failed` overall;
the single failure is the C15 resident-surface instrument issue `OBS-W20-002`
(unrelated to this candidate).
