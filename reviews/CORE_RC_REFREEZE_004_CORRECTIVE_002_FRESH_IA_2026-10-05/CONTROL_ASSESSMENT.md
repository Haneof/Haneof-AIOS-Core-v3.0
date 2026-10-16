# Control and scope assessment — REVIEW_ONLY / DO NOT MERGE

## Candidate controls: what they establish

### Corrected candidate's hosted GREEN control

The candidate records a real GitHub control on its canonical Corrective-002 branch:

- old run `37267746540`, event SHA A `7fa74d5a3a979bc5021978c3e8a85b2b5e3296db`;
- branch advanced to B `ae0ec67fc1c5fe798f51968b322b22bfabdbd782` during the whole-run guard;
- old final seal failed on remote-head mismatch; old overall run was `cancelled`;
- successor B run `37268221493` completed successfully.

This is useful live evidence that drift **before** the final branch lookup is detected. It is not a post-read final-seal test.

### Publisher race control

Candidate evidence records old run `37289807023` cancelled while the publisher was cancelled and a successor run `37289888964` succeeded. This supports the publisher's pre/post-ref checks and stale-run cancellation over that tested interval. It does not cover the interval after the final seal's only branch response.

### RED control is not the corrected candidate workflow

Run `37289298552` is real, but GitHub metadata identifies its workflow as `.github/workflows/w28-toctou-red-control.yml`, not the candidate workflow. The reviewer-created control workflow deliberately has `cancel-in-progress: false`, checks terminal remote equality, holds, and then runs a legacy publisher. Its branch moved A `60e53408729efdb29f08c0c2063b37d34fea1f09` → B `dabf9c98d0736869ec95e7d0a34ebbe42213e3ee`; gate, publisher, and old overall run were successful. This is a valid RED reproduction for the earlier inter-job design, but not evidence that the corrected candidate's final seal can be defeated on hosted GitHub.

## Independent source review

- Top-level workflow permissions are read-only; Job A is read-only and checkout sets `persist-credentials: false`.
- Candidate-controlled tests/probes run in Job A, not the write-capable publisher.
- Publisher has `contents: write`, no checkout and no candidate executable; fixed inline code checks the canonical ref before and after commit-comment POST, accepts only HTTP 201, and fails transport/non-201 responses.
- The whole-run seal is read-only (`contents: read`, `actions: read`) and validates run SHA/branch/attempt and the exact provisional comment.
- Candidate diff from failed predecessor is scoped to the one RC004 workflow and the Corrective-002 review evidence directory. No product implementation/test scope changed.

These controls are positive and the publisher carry-forward remains materially intact. They do not override the two binding findings.

## Candidate formal evidence

Latest exact-head run `37320392029` reports overall success and success for Job A `111797678752`, publisher `111800414428`, and whole-run seal `111800463630`. The exact candidate pin comment `203496684` is marked provisional and binds run `37320392029` and candidate SHA `5a5d384...`.

The candidate's evidence reports the full carry-forward results, including Full Core 928 passed, Window 20 A/B, Window 17, Corrective-003 security, process-loss recovery, clean wheel/headless, backup/restore, writer/restart/FIX/SCALE, C15 classification, protected drift, and publisher fault matrix. Hosted artifact metadata was available, but the artifact bytes/logs could not be downloaded here due Azure `EOF`; these detailed counts were not independently rerun locally.

## Conclusion

The candidate's identity, scope, permissions, publisher status, and exact-head hosted run are well pinned. The final-seal mock demonstrates a post-read false-green in the exact shell logic, and the terminal main-drift regex misses required protected paths. Therefore the fresh acceptance fails despite formal CI success.
