# CORE-RC-REFREEZE-004 - Backup / restore / rebuild evidence

## Preserved RED

Preflight run `37210904177` failed the inherited RC003 release probe with:

`AssertionError: trusted provider-return receipt was not durable`.

This RED is retained. It is **not** classified as a Core regression: the inherited RC003 probe assumed that an ordinary in-process handler return automatically creates durable trusted-return authority. Corrective-003 Route B intentionally removed exactly that local self-trust behavior, while the same run independently passed the 928 Core tests, frozen reviewer probes, 214 security tests, 9 real-SIGKILL tests and clean-wheel headless gate.

Classification: `STALE_RELEASE_PROBE_SEMANTICS / NOT_CORE_IMPLEMENTATION_RED`.

## RC004 Route B probe

RC004 therefore uses `reviews/CORE_RC_REFREEZE_004/probes/backup_restore_route_b.py`, which does not restore local self-trust. It:
- binds a durable external RSA verifier before provider dispatch;
- keeps the private signing key outside Core;
- produces a genuine external proof;
- injects process loss **after receipt/handoff commit but before staging**;
- backs up the World at that partial-commit boundary;
- restores to a new path and rebuilds the index;
- proves source backup and source World immutability;
- proves receipt/handoff/verifier-consumption continuity;
- proves a forged local proof is refused after restore;
- proves a conflicting genuine proof is refused;
- proves the winning exact genuine-proof retry recovers;
- proves zero provider redispatch and no duplicate meter/capability effect;
- proves restore does not resurrect `record_live_provider_return` or expand trusted-return authority.

The final exact-head workflow result for this RC004 probe is binding.
