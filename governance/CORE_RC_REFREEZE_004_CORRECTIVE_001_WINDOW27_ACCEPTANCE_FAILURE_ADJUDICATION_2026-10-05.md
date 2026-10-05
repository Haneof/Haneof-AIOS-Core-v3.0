# CORE-RC-REFREEZE-004-CORRECTIVE-001 — Window 27 Acceptance Failure PM Adjudication

Date: 2026-10-05

## Ground truth

Canonical candidate under Window 27:
- PR #330
- exact head `2380121639865b1bd29176cf944f5a20afe4112d`
- parent `04c37f7dd8ba6f20e1c67dad43c0f21087f51eeb`
- tree `72d3cd0da849fae3b1cbfdfb7ae995528e1cfd71`
- OPEN / non-draft / UNMERGED / DO NOT MERGE

Frozen software remains:
`1cee3c5ad12f4b9098232bae11b51df786c5eb2f`

Window 27 published two REVIEW_ONLY evidence PRs:
- PR #333 = canonical final Window 27 verdict evidence
  - publication head `6e63505175aca3114592a40dd01b1d8bfb95c01f`
  - tree `3a782cd4239404017d16fb5399ce19157f94b341`
  - final verdict `ACCEPTANCE_FAIL / blocker=2`
- PR #332 = secondary/corroborating independent review evidence
  - publication head `4b3db8d9f60a2374ed5b7deaca707d185cf1157f`
  - tree `1e177efb19eecdce71781279b1ddd64231a8c86c`
  - independently corroborates the whole-run TOCTOU blocker
  - does not override the canonical #333 verdict

Both review PRs are REVIEW_ONLY / DO NOT MERGE.

## PM rulings

### IA27-BLK-001 — BINDING

Classification: HIGH / RELEASE-BLOCKING.

The IA25-BLK-001 closure claim is false.

Exact failing classifier:
`reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/probes/c15_junit_classifier.py`

Canonical Window 27 reviewer probe:
`reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001_INDEPENDENT_ACCEPTANCE_WINDOW_27/reviewer_junit_fuzz.py`
at review commit `6e63505175aca3114592a40dd01b1d8bfb95c01f`
git blob `d734f7dcaf7a72f35dee859181fb1789e12066a2`.

Binding false-accept classes include:
- namespaced rc0 XML hiding structured failure;
- failure testcase with summary failures=0;
- testcase containing both failure and error;
- lexical traversal `tests/c15_persistence/../integration/test_core.py`;
- classname-only downstream spoof;
- downstream-looking file conflicting with Core/integration classname.

PM ruling:
The Window 27 entry contract explicitly required namespace, canonicalization, summary consistency, dual-kind, traversal and file/class conflicts to fail closed. These cannot be downgraded to optional hardening merely because stock pytest's current happy-path output does not normally emit them.

Required property:
ambiguous, non-canonical, structurally inconsistent, or unmappable JUnit evidence MUST reject.

### IA27-BLK-002 — BINDING

Classification: CRITICAL / RELEASE-BLOCKING.

The IA25-BLK-002 whole-run immutability closure claim is false.

Exact failing workflow:
`.github/workflows/core-rc-refreeze-004-formal-gate.yml`

Window 27 demonstrated:
- Job A terminal remote equality passes;
- canonical branch moves afterward;
- artifact upload completes;
- Job B has no fresh canonical remote-head recheck;
- old publisher succeeds;
- old overall run can remain SUCCESS.

Canonical #333 model/reproduction reports `TOCTOU_FALSE_GREEN_REPRODUCED=YES`.

Independent corroboration:
PR #332 performed a real disposable GitHub Actions control:
- old event SHA `4fb32d9b94a79e342af770050d71a45a24677008`
- branch advanced after terminal equality to `e4fd46c04c8ad982fa1fa274546dbf0d099343c5`
- old run `37262331480` still concluded SUCCESS
- gate SUCCESS
- publisher SUCCESS

Therefore the binding invariant:
`canonical candidate identity must not permit a stale run to remain formally successful after branch drift before the acceptance publication boundary`
is not closed.

### Closed carry-forward properties

These remain CLOSED and must not regress:
- IA25-BLK-002 credential isolation:
  - read-only Job A;
  - checkout persist-credentials:false;
  - candidate-controlled execution has no repository write credential.
- IA25-BLK-003 mandatory publisher non-201/transport fail-closed semantics.
- Frozen Core correctness/security carry-forward; Window 27 found no frozen-Core blocker.
- C15 current failures remain downstream operator compatibility debt, not frozen-Core regression.

## Failed candidate disposition

PR #330 is now a historical failed Corrective-001 candidate.

DO NOT:
- merge #330;
- repair #330 in place;
- amend/rebase/squash/force-push its branch;
- rewrite its evidence.

## Next task

`WINDOW 28 — CORE-RC-REFREEZE-004-CORRECTIVE-002`

Status:
`READY`

Scope:
RC004 formal-gate/evidence mechanics only.

Corrective-002 must close exactly:
- IA27-BLK-001;
- IA27-BLK-002;

and preserve all already-closed properties.

No Core implementation repair.
No C15 implementation repair.
No Resident.
No evaluator.
No public release/tag.
No Independent Acceptance in Window 28.
