# NOT_SUBMITTED_WRITE_SITE_AUDIT

Phase A freezes the Route-B truthfulness rules before verifier work.

## Binding definition

not_submitted means Core mechanically knows provider/semantic submission never occurred.

A write is legal only when all are true:

- attempt state is admitted;
- request-binding count is zero;
- verifier/capability count is zero;
- response-receipt count is zero.

Caller booleans, exception type/name, timeout, missing receipt, and operator evidence are never proof.

## Audited write/retry sites

1. BackgroundModelAttemptStore.mark_failure
   - pre-submission admitted + zero artifacts may write not_submitted;
   - post-binding claims are refused and dispatching is durably routed to in_doubt.
2. BackgroundModelAttemptStore.reconcile_not_submitted
   - same mechanical predicate; evidence text is audit metadata only;
   - post-binding calls are refused and cannot unlock retry.
3. BackgroundModelAttemptStore.admit
   - a not_submitted retry is accepted only when the durable-artifact predicate remains empty;
   - historical/corrupt not_submitted rows carrying any dispatch artifact are blocked.
4. BackgroundModelAttemptStore.mark_dispatching
   - first dispatch requires zero prior durable submission artifacts;
   - request binding is INSERT-only. The historical ON-CONFLICT rotation path is removed.

## Route-B consequence

After the first durable request binding exists, no supported path can return the attempt to not_submitted or admitted, so there is no second provider request identity and no stale-verifier rotation lifecycle.
