# Hosted GitHub Actions post-read A→B control

**Status:** pending hosted execution. This file is committed only after both A and successor B run identities/results are recorded; the final formal workflow is run later against the final evidence head.

## Control design

- Control runs use the same formal workflow file, canonical branch, concurrency group, actual commit-comment publisher, exact run/attempt/SHA checks, and read-only post-read seal path as the candidate workflow.
- A control job reads canonical A as its final branch lookup, emits `POSTREAD_CONTROL_LAST_CANONICAL_READ_COMPLETE`, then waits at a 180-second barrier.
- Only after observing that barrier will the operator push a new B commit to the same candidate branch. The B push creates a successor control run in the same concurrency group.
- A must be `cancelled` by the B run. The explicit post-read Actions run-ledger guard is a second fail-closed mechanism: if A survives long enough to resume, it detects a newer run number and fails instead of sealing success.
- B must complete the control gate, provisional publisher, post-read barrier, and successor seal successfully.
- A and B comments are explicitly control-only provisional pins; neither is a formal release/acceptance pin.

## Required hosted record

The final committed version of this file records:

| Identity/result | Value |
|---|---|
| Workflow | `core-rc-refreeze-004-formal-gate` |
| A SHA | pending |
| A run id / attempt / URL | pending |
| A control gate job id/result | pending |
| A publisher job id/result / HTTP status / comment id | pending |
| A control seal job id/result | pending |
| A overall conclusion | pending |
| A final canonical-read marker and barrier timestamp | pending |
| B SHA | pending |
| B successor run id / attempt / URL | pending |
| B control gate job id/result | pending |
| B publisher job id/result / HTTP status / comment id | pending |
| B control seal job id/result | pending |
| B overall conclusion | pending |
| Old A authority result | pending; must be non-success / non-authoritative |
| A→B ref move timestamp and refs | pending |
| #336/#337 ref non-interference check | pending |

Raw run/job API metadata and log excerpts are committed in `raw/` alongside this summary.
