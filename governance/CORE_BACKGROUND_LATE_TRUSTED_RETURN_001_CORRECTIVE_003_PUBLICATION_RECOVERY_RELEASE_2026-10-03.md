# WINDOW 22 Completion / Publication-Recovery Release

Date: 2026-10-03

Task: `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003`

Fresh main at PM writeback: `65e1078500eb2b2cf85c5d88a3773c1b8e49fa36`

## PM disposition

Window 22 local engineering is complete enough to leave engineering, but the candidate is not yet
published and has not received exact-head formal CI.

State:

`ENGINEERING_COMPLETE_PENDING_PUBLICATION / GITHUB_PUBLICATION_BLOCKED`

This is **not** `REVIEW_READY` and is **not**
`READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE`.

Window 23 Fresh Independent Acceptance remains blocked.

## Engineer-reported local identity (not yet independently byte-verified by PM)

The Window 22 engineer reports:

- local branch: `core-background-late-trusted-return-corrective-003-window22`
- exact local final head: `39917591f07c2ed1aa679f9098c1fc368c3af42e`
- parent: `96b0f08706aa6e35820cd676976f24c15b62373a`
- tree: `fe17c59c71874423ec7a77cfb4d33b4ffb3e2e64`
- construction base: `65e1078500eb2b2cf85c5d88a3773c1b8e49fa36`
- bundle SHA-256:
  `02e9031e6b9b85328c5151f9e16f8fbbdb09f9ec6d4304c40deb72499d26e238`
- patch SHA-256:
  `ecf33ea5a1db4b600aca3afd592f1e74bcbc18b7fcda0dfae855fe474b921fe1`
- advertised bundle head:
  `39917591f07c2ed1aa679f9098c1fc368c3af42e refs/heads/core-background-late-trusted-return-corrective-003-window22`
- reported local full-Core pre-flight: `911 passed / 0 failed`
- reported frozen probes: Suite A `4/0`, Suite B `7/0`, W17 `14/0`
- reported C3 author matrix: `15 passed`
- reported exact scope: 70 changed paths, 0 out-of-scope, 0 forbidden-path touches
- reported cleanup: root `.gitignore` delta removed; no build artifacts.

PM has **not** independently received or hashed the bundle bytes in this window, so these artifact
identity values remain `ENGINEER_REPORTED_PENDING_PUBLICATION_VERIFICATION` until the publication
recovery window imports and verifies the actual bundle.

## Inherited observation

The reported `attach_late_trusted_return` receipt/handoff-before-staging sequencing is present in
the frozen Corrective-002 candidate `fec30bd1495017bf13f08b0ef5b1e241dfb0e247` and is carried as
`INHERITED_OBSERVATION / NOT_NEW_W22_REGRESSION`. Corrective-003 did not receive scope to repair it.
Fresh IA may independently determine whether it creates a new acceptance finding.

## Unique next READY — WINDOW 22A

`CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-003-PUBLICATION-RECOVERY`

Role: publication/recovery operator only.

Purpose:

1. receive the exact Window 22 bundle bytes;
2. independently verify bundle SHA-256, `git bundle verify`, advertised head, parent, tree,
   construction-base ancestry, patch replay tree and scope;
3. publish the **same exact candidate commit**, without re-creating or modifying it;
4. open a new engineering PR against current fresh main;
5. obtain exact-head formal CPython 3.12.14 GitHub Actions results;
6. stop at PM readiness if all formal gates are green.

22A must not repair code, edit tests, amend/rebase/squash the candidate, merge the PR, perform Fresh
IA, enter RC-REFREEZE-004, or run any Resident.

If the exact bundle bytes are unavailable to the publication window, it must stop:
`PUBLICATION_ARTIFACT_UNAVAILABLE`.

If the actual bundle hash/head/tree differs from the engineer-reported values above, it must stop:
`PUBLICATION_ARTIFACT_IDENTITY_MISMATCH`.

If publication requires changing candidate bytes or adding a commit to make CI pass, 22A must stop
and return to corrective engineering; it must not silently create a new candidate.

## Release condition for Window 23 Fresh IA

Window 23 may be released only after PM verifies:

- exact remote PR head equals the bundle candidate head;
- exact formal CI ran on that head;
- formal CPython 3.12.14 gate is green;
- W20 failed-candidate RED and candidate GREEN identities are exact;
- Suite A/B/W17 and C3 matrix are green;
- full Core regression is zero-failure;
- scope guard is clean;
- PR remains open/unmerged/DO NOT MERGE.

Until then, Window 23 remains BLOCKED.
