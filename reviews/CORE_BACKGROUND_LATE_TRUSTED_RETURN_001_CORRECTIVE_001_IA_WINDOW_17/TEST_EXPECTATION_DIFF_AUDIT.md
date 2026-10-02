# Audit of Candidate Modifications to Existing Test Files (`TEST_EXPECTATION_DIFF_AUDIT.md`)

- **Reviewed Exact Candidate:** `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`PR #308`)
- **Diff Base:** `0b883c71d91e5f0772334514925237f1570fa780`

## Audited Existing Test Files Modified by PR #308

| File | Changed Tests / Lines | Purpose of Change | Audit Judgment |
|---|---|---|---|
| `tests/integration/test_core_background_response_recovery_001.py` | `test_no_exact_response_can_be_staged_for_a_call_that_never_reached_provider` (`1005-1052`), `test_case_10_normal_path_and_post_binding_fail_closed_regression` (`1280-1337`) | Updates post-`mark_dispatching` `ModelDispatchNotSubmitted` expectation from `not_submitted` / retry to `BackgroundModelResponseConflict` / `in_doubt` per C4/C5 Route B (`PR #307`), with explicit explanatory comments | `LEGITIMATE GOVERNANCE-DRIVEN EXPECTATION UPDATE` |
| `tests/integration/test_core_gap_fix_002_background_attempts.py` | `test_typed_not_submitted_after_durable_dispatch_stays_in_doubt` (`302-336`) | Updates post-binding `ModelDispatchNotSubmitted` expectation to `in_doubt` and verifies no retry or binding rotation occurs | `LEGITIMATE GOVERNANCE-DRIVEN EXPECTATION UPDATE` |
| `tests/runtime/test_background_model_attempt.py` | `test_background_attempt_pre_submission_retry_keeps_identity_and_non_world_revision` (`23-110`), `test_background_attempt_post_binding_not_submitted_is_refused_and_in_doubt` (`112-165`) | Splits pre-submission retry (before `mark_dispatching`) from post-binding refusal (`in_doubt`) per C4/C5 Route B | `LEGITIMATE GOVERNANCE-DRIVEN EXPECTATION UPDATE` |
| `tests/runtime/test_turn_execution_recovery.py` | `test_cg003_typed_not_submitted_after_binding_stays_in_doubt` (`251-281`), `test_cg003_post_binding_reconciliation_is_refused_after_restart` (`314-349`) | Aligns CG003 post-binding typed failure and operator reconciliation tests with C4/C5 Route B (`in_doubt` / refused) | `LEGITIMATE GOVERNANCE-DRIVEN EXPECTATION UPDATE` |

## Conclusion

None of the 4 modified existing test files weakened security assertions; all changes in those 4 files correspond to the C4/C5 Route-B post-binding `not_submitted` prohibition authorized by Window 15 Adjudication §4.5 and PR #307.
