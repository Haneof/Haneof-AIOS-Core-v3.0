# Independent `not_submitted` Write-Site Audit (`NOT_SUBMITTED_WRITE_SITE_AUDIT.md`)

- **Reviewed Exact Candidate:** `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd` (`PR #308`)
- **Governance Clauses:** `C4` (Complete Closure of ALL `not_submitted` Write Sites), `C5` (Caller Boolean / Exception Type Is Not Proof), `C6` (Coherent Retry / Verifier Lifecycle — Route B), PR #307 binding clarification.

## 1. Exhaustive Enumeration of `not_submitted` References & `background_model_attempts` Updates

| File & Lines | Function / SQL Site | Behavior in Candidate `cb8a6b3c...` | Independent Verification |
|---|---|---|---|
| `src/aios_core/runtime/background_attempt.py:1215-1249` | `_durable_submission_artifacts(conn, attempt_id)` | Queries `background_model_request_bindings`, `background_model_return_verifiers`, `background_model_return_capabilities` (schema-aware), and `background_model_response_receipts` | Verified: returns non-empty tuple if any durable dispatch/verifier/capability/receipt row exists |
| `src/aios_core/runtime/background_attempt.py:1251-1277` | `_route_post_binding_failure_to_in_doubt(...)` | Updates `state='in_doubt'` where `attempt_id=? AND state='dispatching'` | Verified |
| `src/aios_core/runtime/background_attempt.py:1279-1360` | `mark_failure(..., definitely_not_submitted=True, error=...)` | Checks `current.state != "admitted" or artifacts`. If post-binding, routes `dispatching -> in_doubt`, commits, and raises `BackgroundModelResponseConflict`. Only writes `state='not_submitted'` when `state == 'admitted'` and `artifacts == ()` | Verified by `IA17-NS-ROUTE-B-001` (`PASS`) |
| `src/aios_core/runtime/background_attempt.py:1476-1552` | `reconcile_not_submitted(...)` | Checks `current.state != "admitted" or artifacts`. If post-binding, routes `dispatching -> in_doubt`, commits, and raises `BackgroundModelResponseConflict`. Only writes `state='not_submitted'` when `state == 'admitted'` and `artifacts == ()` | Verified by `IA17-NS-ROUTE-B-001` (`PASS`) |
| `src/aios_core/runtime/background_attempt.py:971-998` | `admit(...)` retry from `not_submitted` | Before transitioning `not_submitted -> admitted`, checks `if self._durable_submission_artifacts(conn, attempt_id): raise BackgroundModelAttemptBlocked(current)` | Verified: legacy/corrupted `not_submitted` rows with bindings cannot retry |
| `src/aios_core/runtime/background_attempt.py:1066-1119` | `mark_dispatching(...)` | Requires `current.state == "admitted"` AND `not self._durable_submission_artifacts(conn, attempt_id)`; uses plain `INSERT INTO background_model_request_bindings` (no `ON CONFLICT DO UPDATE`) | Verified: binding rotation is structurally impossible |
| `src/aios_core/runtime/turn_runtime.py:1368-1383` | `_record_background_model_failure(...)` | Delegates to `self.background_model_attempts.mark_failure(...)` | Verified |
| `src/aios_core/runtime/turn_runtime.py:3328-3365` | `reconcile_turn_model_not_submitted(...)` | Delegates to `self.background_model_attempts.reconcile_not_submitted(...)` | Verified by `IA17-NS-ROUTE-B-001` (`PASS`) |

## 2. Audit Conclusion for `C4` and `C5`

`C4` and `C5` (`BLK-W14-003` and `BLK-W14-004` Route-B post-binding `not_submitted` closure) are **properly closed** in `cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd`. No post-binding code path can write `state = 'not_submitted'` or rotate `background_model_request_bindings`.
