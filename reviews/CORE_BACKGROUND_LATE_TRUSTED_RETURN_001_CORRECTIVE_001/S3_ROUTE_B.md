# S3_ROUTE_B

PR #307 makes C4/C5 durable truthfulness authoritative.

Historical S3 remains immutable RED on failed candidate `5ad0524c...` and is not rewritten.

Corrective Route-B proves:
- durable binding + `mark_failure(definitely_not_submitted=True)` => refused and durable `in_doubt`;
- durable binding + `reconcile_not_submitted(...)` => refused and durable `in_doubt`;
- no transition back to admitted/not_submitted;
- no second provider call;
- no second request identity;
- no binding rotation;
- no stale verifier/capability lifecycle.

True pre-submission retry is separate: admitted + zero dispatch artifacts may become not_submitted and retry. Its first actual dispatch creates the only binding/verifier scope.
