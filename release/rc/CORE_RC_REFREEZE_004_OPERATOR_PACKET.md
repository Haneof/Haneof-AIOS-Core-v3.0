# CORE-RC-REFREEZE-004 Operator Packet

Task: `CORE-RC-REFREEZE-004`  
Window: `24`  
Role: Release PM / Release Engineer

This packet is release-candidate evidence only. It is **not** Independent Acceptance, merge authorization, Resident release, evaluator entry, public tag, or public release.

## Frozen software boundary

- software SHA: `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`
- parents: `fb53cf938b138a67d1890618eed41282c61bce00`, `7ecb2250a488766915e1042a76472b3cd26d9107`
- parent 2 is the exact Corrective-003 candidate accepted by Window 23
- repository tree: `70b2711258567863ea0d93025a6a07e39631726a`
- `src/aios_core/**`: `16f1487e291b009c55bee402abfd79fdacbae960`
- `tests/**`: `9db1bfa08143bc99fe03836e2752ee6e05694eb6`
- frozen workflows tree: `72cde9d2dc2b35d071bfa36c954dac2faff4a803`
- `pyproject.toml` blob: `b38833c7537fa60d5c2f02ed4bb19158d8995a11`

Fresh live main immediately before final candidate construction remains `ee4556989fea16a28d2c727eb345d48385a453fe`. The nine post-software commits resolve to governance/checkpoint-only final delta; protected implementation drift is zero.

PR #321 / reviewer commit `22aa00cb3793c252512142a1eae33ca8aae9d841` is REVIEW_ONLY evidence, not frozen software. Window 23 publication staging is transport only.

## Formal environment

Binding environment:
- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2
- Ubuntu 24.04.5 LTS / x86_64 in preflight
- SQLite 3.45.1 in preflight
- OpenSSL 3.0.13 in preflight

The final exact runner values, executable and `aios_core.__file__` are published by the final immutable-head run.

## Fresh evidence already established in preflight

- Core gate: **928 passed / 0 failed / 0 errors**
- Window 20 Suite A: **4/4 green**
- Window 20 Suite B: **7/7 green**
- Window 17: **14/14 green**
- Corrective-003 security matrix: **214 passed**
- real SIGKILL/fresh-process group: **9 passed**
- clean non-editable wheel/headless: **HEADLESS_CLEAN_INSTALL_PASS**
- trust writer inventory: sole trust root remains `attach_late_trusted_return`

All of these are rerun by final exact-head CI.

## Preserved release-engineering REDs

Runs `37210518501`, `37210904177`, and `37211071106` remain durable.

The first exposed a release-gate textual false positive and was corrected only in the gate. The latter two exposed that the inherited RC003 backup probe expected obsolete local trusted-return behavior removed by Corrective-003 Route B. No Core repair was made.

RC004 replaces only that evidence probe with `reviews/CORE_RC_REFREEZE_004/probes/backup_restore_route_b.py`, which uses a durable external verifier + genuine proof, crashes after receipt/handoff commit before staging, then proves backup/restore/rebuild continuity, exact winning proof retry, conflict refusal, zero provider redispatch, no duplicate meter/effect, and no restored self-trust authority.

## C15 ruling

Window 24 does not repair C15. The final CI freshly separates `tests/c15_persistence/**` from the Core gate.

If Core is green and the failures remain downstream only:
- `CORE_FREEZE_NOT_BLOCKED_BY_DOWNSTREAM_OPERATOR_DEBT`
- `C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT`

If downstream tests mechanically prove an accepted Core contract regression, RC004 must be BLOCKED.

Restoring local caller-manufacturable trust merely to make the legacy C15 harness green is forbidden.

## RC impact

- `FRESH_A_REQUIRED`
- `FRESH_OPERATOR_PREP_REQUIRED`
- A-003, A-004 and all earlier A evidence are prior-RC history only
- hash-swap is forbidden

Required downstream order:
1. RC-REFREEZE-004
2. Fresh Independent RC Acceptance
3. PM Integration
4. dedicated C15 operator/persistence compatibility corrective against frozen RC
5. Fresh Independent Acceptance of operator corrective
6. Fresh Resident A only after explicit PM release

Window 24 executes none of steps 2-6.

## Exact-head rule

The tracked manifest is deliberately non-self-referential. The final candidate SHA/parent/tree, formal run id, exact final environment and binding gate results are pinned in the candidate PR body/comment and exact candidate commit comment **after** the immutable-head run. No commit is allowed after that formal run.

Terminal state on all-green final CI:
`REVIEW_READY / READY_FOR_INDEPENDENT_ACCEPTANCE / DO NOT MERGE`.

Otherwise:
`BLOCKED`.

No self-acceptance. No merge. No Resident. No evaluator. No public release/tag.
