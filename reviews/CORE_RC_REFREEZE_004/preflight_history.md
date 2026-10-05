# CORE-RC-REFREEZE-004 - Preflight history

All REDs are retained. They are release-engineering evidence and are not Independent Acceptance.

## Preflight 1 - run 37210518501

Head: `dde4750bdd64634d628c8bf743309d1b83885b6b`  
Result: **FAIL - RC gate self-defect, not Core software RED**.

Before the failing step:
- frozen identity / post-integration drift / candidate scope: PASS
- CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2: PASS
- Core: **928 passed / 0 failed / 0 errors**
- Window 20 Suite A: **4 / 0**
- Window 20 Suite B: **7 / 0**
- Window 17: **14 / 0**
- trust-writer inventory: PASS

Cause: a textual grep treated the legitimate inert `runtime/__init__.py` reviewer-probe compatibility re-export as if an authorization module consulted `live_return.py`. The RC gate was corrected to a semantic AST import audit. No Core software was changed.

## Preflight 2 - run 37210904177

Head: `3985599938b271028c89a52bd628da46bedf5f4f`  
Result: **FAIL - inherited RC003 backup probe used obsolete trust semantics**.

Fresh passes before RED:
- Core: **928 passed**
- frozen reviewer probes: **4/0, 7/0, 14/0**
- Corrective-003 security matrix: **214 passed**
- real SIGKILL/fresh-process: **9 passed**
- clean non-editable wheel + headless lifecycle: **PASS**

RED:
`AssertionError: trusted provider-return receipt was not durable`.

The inherited RC003 probe expected a normal in-process handler return to create durable trusted-return authority. Corrective-003 Route B intentionally removed that local self-trust behavior. Classification:
`STALE_RELEASE_PROBE_SEMANTICS / NOT_CORE_IMPLEMENTATION_RED`.

The RED remains durable in run 37210904177 and its commit comment/artifact.

## Preflight 3 - run 37211071106

Head: `736e8fb91523d9914b9fb76b9bf9cdeb64a1594d`  
Result: **FAIL at the same inherited RC003 backup probe**.

This run additionally began with the required `git fetch --all --prune` and remote branch snapshot, then freshly re-proved:
- exact identity/drift/scope: PASS
- formal environment: PASS
- Core: **928 passed**
- frozen reviewer probes: PASS
- Corrective-003 security: PASS
- real SIGKILL: PASS
- clean wheel/headless: PASS

It then hit the same known stale RC003 backup-probe assertion. This repeat RED is retained and is not hidden or rewritten.

## Release-probe correction

RC004 replaces only the stale release evidence probe with:
`reviews/CORE_RC_REFREEZE_004/probes/backup_restore_route_b.py`.

That probe follows the accepted Route B contract: durable external verifier + genuine external proof, crash after receipt/handoff commit and before staging, supported backup/restore/rebuild, forged/conflicting proof refusal, exact winning proof retry, no provider redispatch, no duplicate meter/effect, and no restored local authority.

No `src/**`, `tests/**`, package implementation metadata, C15 operator/persistence implementation, or Resident surface is modified by the probe correction.
