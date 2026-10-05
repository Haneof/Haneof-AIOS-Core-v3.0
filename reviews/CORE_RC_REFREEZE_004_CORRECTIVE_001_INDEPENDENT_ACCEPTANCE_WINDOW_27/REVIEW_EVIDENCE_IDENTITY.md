# Window 27 Review Evidence Identity

Task: CORE-RC-REFREEZE-004-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE
Role: Fresh Independent RC Freeze Corrective Acceptance Reviewer
Verdict: ACCEPTANCE_FAIL
Blocker count: 1
Disposition: CORRECTIVE_OR_ADJUDICATION_REQUIRED
DO NOT MERGE

Candidate PR: #330
Exact candidate: 2380121639865b1bd29176cf944f5a20afe4112d
Candidate tree: 72d3cd0da849fae3b1cbfdfb7ae995528e1cfd71

Exact technical review commit: 62d0671b45b139247400f1ee1b71850d0739297b
Exact technical review tree: 1cc99dcafd7e850b2a68ffdd6a366975ab42fde0
Technical review parent: 7793d8f36c0210debcbb8e0cf738bbd54a61fef3

Reviewer workflow run: 37261988648
Reviewer workflow head: 66730aedefa2bedd0b9e0528ca3f5ac5c8320ba8
Reviewer raw artifact: 11325401978
Reviewer raw artifact digest: sha256:1b692973006a61e39fb760ebdee8319d39376f8ce31b5f4a34ad09337b523d22

Formal run: 37217853558
Formal artifact: 11309495093
Formal artifact digest: sha256:02415a0457af3aec5cb50d5195120202aae2c9cb23d3c81cbefaf867b7d216e0
Mandatory exact-pin comment: 203380647

Independent real GitHub TOCTOU control:
run: 37262331480
old event SHA: 4fb32d9b94a79e342af770050d71a45a24677008
post-terminal branch head: e4fd46c04c8ad982fa1fa274546dbf0d099343c5
old run conclusion: SUCCESS

Release blocker:
IA27-BLK-001 = canonical candidate can drift after Job A terminal check while old formal run still reaches SUCCESS because Job B does not recheck canonical remote head.

This branch and its PR are REVIEW_ONLY / DO NOT MERGE.
