# Final handoff discipline

The final SHA256SUMS commit after this file is the tracked-evidence freeze.

After the freeze:
- no evidence-only candidate commits
- final hosted CI receipts go only to PR body/comments
- branch HEAD = PR head = final run head is mandatory
- Job A, publisher, and whole-run identity seal must all succeed
- canonical branch must still equal the exact candidate
- no post-run candidate drift is allowed

Failure rule:
If final exact-head CI is not SUCCESS, report BLOCKED / IA27-BLK-002_NOT_CLOSED.

Stop boundary:
- no Independent Acceptance
- no PM Integration
- no merge
- no Resident
- no evaluator
- no public release/tag
