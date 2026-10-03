# CA1-CA5 / S3-ROUTE-B Frozen Contract

Task: `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001`

Frozen before verifier-only production implementation.

## Route B

`tests/runtime/test_background_late_return_route_b.py`

- post-binding `mark_failure(... definitely_not_submitted=True ...)` => REFUSED / `in_doubt`
- post-binding `reconcile_not_submitted` => REFUSED / `in_doubt`
- no second dispatch / no binding rotation
- genuine pre-submission `admitted + zero durable submission artifacts` remains the only legal `not_submitted` retry

## CA1-CA5

`tests/integration/test_core_background_late_trusted_return_corrective_001.py`

- CA1: recovery object graph exposes verifier/context only, no signer/capability/mint callable.
- CA2: SQLite/dump/backup contain public verifier only; no signing secret/private key/nonce/preimage.
- CA3: covered by Route-B plus existing exhaustive write-site tests.
- CA4: external proof after process death resumes exact response with no provider redispatch.
- CA5: scope transplant, request/relay/provider identity, mutated payload, corrupt/missing proof, duplicate JSON, replay/conflict all fail closed; identical replay is idempotent.

Security architecture required by these probes:

```
External trusted side: RSA private key -> SIGN
Core durable state: RSA public key/verifier + exact request binding -> VERIFY ONLY
```

The test private exponent is synthetic and exists only inside the test source. Production code and runtime state must never receive it.


## Probe revision log

- Revision 0: frozen at commit `53d145d49991186f81bfe997289106872320405f`.
- First Phase B/C execution: 18 passed / 1 harness error. The `attempt_id`
  attack override collided with the fixture method's own positional parameter,
  raising Python `TypeError` before the product path ran.
- Revision 1: rename only that fixture parameter to `owner_attempt_id`.
  Assertions, attack value, production inputs, and expected fail-closed outcome are
  unchanged.
