# C15-EXIT-READINESS-001 — Independent Governance Review

Repository:
`Haneof/Haneof-AIOS-Core-v3.0`

Role:
Independent PM/Governance Readiness Reviewer.

Scope:
Review the C15 exit-readiness preparation package only.

This is not authorization to run any blocked task.

Required checks:
1. fresh-fetch live main and current candidate PR/head;
2. verify candidate changes are governance/checkpoint/prompt files only;
3. verify zero `src/**`, zero `tests/**`, zero workflow/package implementation change;
4. verify the sole active engineering READY task on live main is not replaced or duplicated;
5. verify every downstream prompt is explicitly `DRAFT / NOT READY / DO NOT EXECUTE` or equivalent;
6. verify no future exact SHA/run/session identity is fabricated before its prerequisite exists;
7. verify the sequence matches current binding governance:
   current Core corrective → fresh IA → integration → RC-REFREEZE-003 → IA → A-004 → IA → persistence corrective-003 → IA → RELEASE-003 → B-RERUN-003 → B-ACCEPT-003 → C → EVAL → CLOSE;
8. verify A-003 remains historical after new Core integration and is not reusable as A-004;
9. verify PR #254 old head is not revived as a candidate;
10. verify historical failed/review-only PR dispositions are preserved;
11. verify #263 persona governance remains a separate unaccepted candidate and is not silently treated as merged law;
12. verify R10-aware drafts are conditional on accepted persona governance;
13. verify Resident C still requires trusted external different-model/provider attestation;
14. verify no prompt leaks fixture/evaluator answers into Resident-visible instructions.

Verdict:
- `ACCEPTANCE_PASS / blocker=0`
- `ACCEPTANCE_FAIL / blocker=N`

If FAIL, identify the exact file/clause and smallest governance correction.

Do not merge, run Resident, modify Core, or activate any draft task.
