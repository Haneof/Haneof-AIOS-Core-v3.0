# CORE-RC-REFREEZE-004 Window 25 Acceptance Failure — PM Adjudication

Date: 2026-10-04

Fresh PM ground truth at adjudication:
- live main: `deacf7d55c4c68fdf4580c02a4838f6c9cda1952`
- failed canonical RC candidate: PR #325 @ `70134269ddfc7c80c4a703a933253bd099746504`
- failed candidate parent: `b295e6a83b345864b40d6a731fb25812c0ed9ad4`
- failed candidate tree: `5727143aa14359d67defb41113b46d6759ad7f2e`
- frozen software remains: `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`
- Window 25 review PR: #328, REVIEW_ONLY / DO NOT MERGE
- exact technical review commit: `ffa6475fe4dde4b5d06b09a629b059b89f1ff434`
- technical review tree: `ff2c098a098a8ff73fcc475b80560045b70b1277`
- review publication head: `5b46b70f1b166a28201b3865d455d6ba0e2afec5`

## Verdict

Historical Window 25 verdict is accepted as binding:

`ACCEPTANCE_FAIL / blocker=3 / CORRECTIVE_OR_ADJUDICATION_REQUIRED`

All three blockers are **BINDING**.

The frozen Core software itself is not adjudicated RED by these findings. The failure is in the RC freeze formal-gate/evidence contract.

## IA25-BLK-001 — BINDING

**C15 pytest exit laundering**

The exact candidate workflow records `rc=${PIPESTATUS[0]}` but does not use that return code to decide whether the downstream classification is admissible.

A pytest usage / collection / interrupt / internal / no-tests exit can therefore emit no parsed `FAILED tests/...` lines and still produce:
- `CORE_FREEZE_NOT_BLOCKED_BY_DOWNSTREAM_OPERATOR_DEBT`
- `C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT`

Required corrective contract:
- only pytest exit `0` or `1` may enter downstream adjudication;
- exits `2/3/4/5` and any unknown value are formal gate failure;
- JUnit XML must exist and be parseable;
- if exit `1`, at least one failed/error testcase must exist and every such testcase must mechanically map to `tests/c15_persistence/**`;
- console-text parsing may be supplemental only, not authoritative;
- the known downstream RED remains preserved; do not make C15 green here.

## IA25-BLK-002 — BINDING

**Write credential exposed across candidate-controlled execution; no terminal immutability check**

The exact candidate workflow grants `contents: write` to the single gate job, uses checkout default credential persistence, and performs its remote-head equality check only before executing repository tests and candidate-carried release probes.

Required corrective contract:
- main test/gate job permissions: `contents: read`, `pull-requests: read`;
- `actions/checkout@v4` must set `persist-credentials: false`;
- no candidate-controlled test/probe may receive a write-capable repository credential;
- if `workflow_dispatch` is retained, assert the canonical corrective branch/ref explicitly;
- after all candidate-controlled executions, perform a terminal fresh remote-head equality check;
- terminally recheck candidate HEAD, frozen SHA/tree/Core/tests/workflows/pyproject identities;
- terminally assert frozen worktree has no tracked mutation;
- fresh terminal protected-drift check against current main;
- repository write authority, if needed for evidence publication, must live in a separate job that does not checkout or execute candidate repository code.

## IA25-BLK-003 — BINDING

**Mandatory external-pin publication can fail while workflow stays GREEN**

The exact candidate step uses `set -uo pipefail` and:
`test "$code" = "201" || cat response`.
A non-201 response can therefore end the step successfully because the diagnostic command returns zero.

Required corrective contract:
- exact pin publication is a mandatory success condition for a successful formal workflow;
- publish only after the read-only formal gate succeeds;
- use a separate publication job with only the minimum write permission required;
- do not checkout or execute candidate code in that publication job;
- explicit non-201 handling must terminate non-zero;
- overall workflow conclusion may be `success` only when both the read-only gate and mandatory exact-pin publication succeed;
- exact comment must bind run id, exact candidate SHA, frozen software SHA, and successful gate identity.

## Scope ruling

`CORE-RC-REFREEZE-004-CORRECTIVE-001 = READY`

This corrective is **release-infrastructure/evidence only**.

Forbidden:
- `src/**` changes;
- product `tests/**` changes;
- `tools/**` changes;
- `pyproject.toml` changes;
- C15 implementation repair;
- restoring local self-trust;
- Resident A/B/C;
- evaluator;
- public release/tag.

PR #325 remains the failed exact candidate and must not be amended/rebased/squashed/force-pushed or repaired in place.

PR #328 remains REVIEW_ONLY / DO NOT MERGE.

The new corrective branch may descend from exact failed candidate `70134269...` with append-only commits, but must use a **new branch and new PR**.

Frozen software remains exactly `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`.

After corrective completion, Fresh Independent Acceptance is required again.
