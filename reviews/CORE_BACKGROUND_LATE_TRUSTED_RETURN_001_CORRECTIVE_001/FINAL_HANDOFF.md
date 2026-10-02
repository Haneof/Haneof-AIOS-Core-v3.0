# FINAL_HANDOFF

Task: `CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-001`
Window: 16
PR: #308
Branch: `core-background-late-trusted-return-corrective-001-window16`
Construction base / fresh main at start: `0b883c71d91e5f0772334514925237f1570fa780`

Merge policy: **UNMERGED / DO NOT MERGE**

Engineering result:
- four Window 14 blockers reproduced RED first;
- post-binding not_submitted closed;
- late-return signer/private authority externalized;
- Core recovery verifier-only;
- legacy secret-at-rest material securely purged;
- verifier one-shot consumption + identical replay idempotence;
- S3 Route-B green;
- CA1-CA5 green;
- real SIGKILL green;
- R1-R5 and response-recovery regression green;
- scale/convergence gates green.

The exact final candidate SHA cannot self-reference inside its own commit. PR #308 HEAD is the candidate identity; after exact-head formal CI completes, the terminal PR comment records SHA, parent, tree, workflow run, job ids and exact counts.

Terminal state is not claimed until that exact-head run is green.
