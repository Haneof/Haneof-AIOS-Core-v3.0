# CA1_CA5_MATRIX

| Gate | Attack | Required result | Formal result |
|---|---|---|---|
| CA1 | fresh recovery object graph + reflection/introspection | verifier visible; no signer/secret/capability/mint callable | GREEN |
| CA2 | DB/WAL/dump/backup disclosure | no private key/HMAC key/nonce/preimage; forgery refused | GREEN |
| CA3 | mark_failure, reconcile_not_submitted, retry/wrapper paths after binding | REFUSED / in_doubt; no redispatch / second request id | GREEN |
| CA4-A | true pre-submission failure | legal retry; first real dispatch pins current verifier; genuine late response completes exactly once | GREEN |
| CA4-B / S3-ROUTE-B | post-binding caller boolean/evidence | not_submitted forbidden; no retry; no stale verifier lifecycle | GREEN |
| CA5 | transplant/replay/mutation/wrong identity/corrupt or missing proof/duplicate JSON | fail closed; identical replay idempotent | GREEN |
| SIGKILL | real process death at provider boundary | fresh-process external proof recovery; zero provider redispatch | GREEN |

Primary frozen probes:
- `tests/runtime/test_background_late_return_route_b.py`
- `tests/integration/test_core_background_late_trusted_return_corrective_001.py`
- `tests/integration/test_core_background_late_trusted_return_consumption_001.py`
- `tests/integration/test_core_background_late_trusted_return_secret_upgrade_001.py`
- `tests/integration/test_core_background_late_trusted_return_sigkill_001.py`
