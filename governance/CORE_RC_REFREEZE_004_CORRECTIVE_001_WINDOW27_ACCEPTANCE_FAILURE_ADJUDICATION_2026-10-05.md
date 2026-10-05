# CORE-RC-REFREEZE-004-CORRECTIVE-001 — Window 27 Acceptance Failure PM Adjudication

Date: 2026-10-05

## Fresh PM ground truth

- live main: `5fc78a84d0cf1ccdfe0185ba2cc2f8c7fdeff5c4`
- candidate PR #330 remains OPEN / non-draft / UNMERGED / DO NOT MERGE
- candidate exact head: `2380121639865b1bd29176cf944f5a20afe4112d`
- parent: `04c37f7dd8ba6f20e1c67dad43c0f21087f51eeb`
- tree: `72d3cd0da849fae3b1cbfdfb7ae995528e1cfd71`
- frozen software remains `1cee3c5ad12f4b9098232bae11b51df786c5eb2f`
- Window 27 canonical review evidence: PR #333, REVIEW_ONLY / DO NOT MERGE
- PR #333 publication head: `6e63505175aca3114592a40dd01b1d8bfb95c01f`
- PR #333 final review tree: `3a782cd4239404017d16fb5399ce19157f94b341`
- PR #332 is corroborating REVIEW_ONLY evidence, not the canonical blocker-numbering source.
- PR #332 head: `4b3db8d9f60a2374ed5b7deaca707d185cf1157f`
- real disposable GitHub Actions TOCTOU control run: `37262331480`
- old event SHA: `4fb32d9b94a79e342af770050d71a45a24677008`
- branch advanced after terminal equality to `e4fd46c04c8ad982fa1fa274546dbf0d099343c5`
- old gate job: SUCCESS
- old publisher job: SUCCESS
- old overall run: SUCCESS

## Window 27 disposition

Reported canonical verdict:
`ACCEPTANCE_FAIL / blocker=2 / CORRECTIVE_OR_ADJUDICATION_REQUIRED`

PM adjudicated release-blocking count:
`blocker=1`

### IA27-BLK-001 — JUnit synthetic ambiguity/canonicalization

**PM ruling: NON_BINDING_HARDENING_OBSERVATION / NOT_A_RELEASE_BLOCKER_FOR_RC004**

The reviewer correctly found six synthetic XML inputs that the candidate classifier accepts:
- namespace-hidden failure;
- summary/testcase inconsistency;
- failure+error on one testcase;
- lexical `tests/c15_persistence/../...` path;
- classname-only spoof;
- downstream file vs Core classname conflict.

However, the Window 27 entry contract explicitly required the reviewer to determine whether fail-open behavior exists for **actual pytest 8.4.2 JUnit semantics**, not merely arbitrary hand-authored XML.

Fresh evidence from both independent reviews shows:
- real usage error -> rc4 -> rejected;
- real collection error -> rc2 -> rejected;
- real no-tests -> rc5 -> rejected;
- real downstream failure + downstream setup error -> rc1 and correctly classified downstream;
- real frozen `tests/c15_persistence/**` JUnit contains only downstream structured failures and is correctly classified;
- no actual pytest-generated non-test failure state was shown to become downstream GREEN.

Therefore these six cases are hardening observations, not proof that the binding formal path still launders pytest failure. Do not expand Corrective-002 to repair this unless separately authorized.

### IA27-BLK-002 — whole-run immutability / inter-job TOCTOU

**PM ruling: BINDING / CRITICAL**

Invariant:
The canonical candidate branch must not be able to drift after the final identity check while the stale formal run still completes overall SUCCESS and publishes an exact-pin success for the old SHA.

Exact candidate workflow:
- Job A terminal remote-head equality occurs before artifact upload;
- Job B starts after Job A;
- Job B contains no fresh canonical remote-head equality check.

Independent real GitHub Actions reproduction:
- run `37262331480`
- terminal equality passed for event SHA `4fb32d9...`
- branch then advanced to `e4fd46c...`
- old Job A still SUCCESS
- old publisher still SUCCESS
- old overall run still SUCCESS.

This mechanically proves a stale-run false-green path and violates the Window 25/27 binding whole-run immutability requirement.

### IA25-BLK-003 publisher failure semantics

Remains CLOSED.

## Corrective release

`CORE-RC-REFREEZE-004-CORRECTIVE-002 = READY`

`WINDOW 28 = RELEASED`

Corrective-002 must fix only the binding whole-run identity/TOCTOU defect.

No Core implementation repair.
No product tests repair.
No C15 implementation repair.
No JUnit hardening expansion.
No Resident.
No evaluator.
No public release/tag.

PR #330 becomes historical failed corrective candidate and must not be repaired in place or merged.
PR #332 and #333 remain REVIEW_ONLY / DO NOT MERGE.
