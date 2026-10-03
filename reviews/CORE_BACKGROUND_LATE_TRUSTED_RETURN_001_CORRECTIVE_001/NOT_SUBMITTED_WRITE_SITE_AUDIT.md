# NOT_SUBMITTED_WRITE_SITE_AUDIT

Binding definition:

`not_submitted` means Core mechanically knows provider/semantic submission NEVER occurred.

Legal predicate:
- state == admitted
- request binding count == 0
- verifier/capability count == 0
- response receipt count == 0

Caller booleans, exception type/name, timeout, missing receipt and operator evidence are not proof.

Audited write/retry sites:

1. `BackgroundModelAttemptStore.mark_failure`
   - only admitted + zero durable submission artifacts can write not_submitted;
   - any post-binding claim is refused and dispatching is durably routed to in_doubt.

2. `BackgroundModelAttemptStore.reconcile_not_submitted`
   - same mechanical predicate;
   - evidence text is audit metadata only;
   - post-binding reconciliation is refused.

3. `BackgroundModelAttemptStore.admit`
   - not_submitted retry returns to admitted only when durable-artifact predicate remains empty;
   - corrupt/historical not_submitted rows carrying binding/verifier/receipt are blocked.

4. `BackgroundModelAttemptStore.mark_dispatching`
   - admitted attempt may cross provider boundary only with zero existing dispatch artifacts;
   - request binding is INSERT-only; historical rotation/upsert is removed;
   - optional public late-return verifier is pinned in the same dispatch transaction.

5. `CognitiveRuntime.run_turn` typed `ModelDispatchNotSubmitted` route
   - the typed exception is merely a caller assertion once Core has already recorded dispatch;
   - `model_failure_recorder(..., True)` therefore reaches the same store predicate and is refused post-binding.

6. `FusedTurnRuntime._record_background_model_failure`
   - wrapper contains no override/bypass; delegates to `mark_failure`.

7. turn/wake retry authorization and recovery
   - post-binding in_doubt cannot be authorized as safe retry;
   - no supported retry path creates a second provider call/request identity.

8. legacy adoption/internal helpers
   - `adopt_legacy_in_doubt` creates in_doubt, never not_submitted;
   - `_route_post_binding_failure_to_in_doubt` only strengthens uncertainty.

Route-B consequence: after the first durable request binding exists, no supported path can return the attempt to not_submitted/admitted. Binding/verifier rotation and stale-capability lifecycle are structurally unreachable.
