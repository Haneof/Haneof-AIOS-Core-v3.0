# Trusted-return authenticity RC spot checks — GREEN

Frozen probe:

- path: `tests/integration/test_core_background_response_recovery_001_corrective_002_authenticity.py`
- git blob: `6f0c3850368475e166d28d0a6df4b86b610d2c60`
- SHA256: `35cba59f318b752ed872821961296f35810443c61db6fd98c8c8f5eee4215225`
- still present on live main / freeze candidate tests tree `92fcbcc5876833735fb3cb7c73a98c4a8a4a3541`

Runtime path (not tests-only): `src/aios_core/runtime/background_attempt.py` uses store-private HMAC authority, receipts table, fail-closed missing/malformed authority.

Checks (covered by frozen 12-probe + recovery SIGKILL tests, re-run GREEN on 3.12.14 focused step):

- authority exists
- authority durable across restart / backup
- receipt exact bytes
- proof binds exact payload
- provider/model/request identity bound
- work/subject/round/attempt bound
- staged recovery re-verifies persisted proof
- invalid/tampered proof fails closed
- missing authority fails closed
- malformed authority fails closed
