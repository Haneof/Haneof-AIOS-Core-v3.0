# Candidate and branch identity

Canonical Corrective-002 branch:
release/core-rc-refreeze-004-corrective-002-window28

Immutable base:
2380121639865b1bd29176cf944f5a20afe4112d

Initial corrective mechanics commit:
7fa74d5a3a979bc5021978c3e8a85b2b5e3296db

Late-race branch-advance evidence commit:
ae0ec67fc1c5fe798f51968b322b22bfabdbd782

All subsequent Window 28 evidence commits are append-only on the same branch.

The final candidate SHA is the SHA256SUMS evidence-freeze commit. It cannot be embedded into its own tracked content without another commit. Therefore final branch HEAD, PR head, formal-run head, tree, artifact, pin, and post-run drift equality are published externally in the new PR body/comment after final hosted CI.

No force-push, amend, rebase, squash, or in-place repair of PR #330 is permitted.
