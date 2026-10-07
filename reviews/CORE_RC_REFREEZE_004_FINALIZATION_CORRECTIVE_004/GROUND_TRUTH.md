# Ground Truth Evidence for RC004 Finalization Corrective 004

This document defines the exact baseline facts, source derivations, and historical context required for Window 41 formal execution.

| Key | Value / Identity | Meaning / Source |
|---|---|---|
| `LIVE_MAIN` | `9eba4710e3cd841650191cb89f2126ca5c5b11c3` | Current `main` branch tip on remote. |
| `PR338_ACCEPTED_HEAD` | `e35b70e4856abae763145c535d11baaa847be076` | Accepted engineering head from Window 35 PM Integration. |
| `PR338_MERGE_COMMIT` | `9eba4710e3cd841650191cb89f2126ca5c5b11c3` | Merge commit of PR #338 on `main`. |
| `WINDOW34_ACCEPTANCE_COMMENT` | `(Historical)` | The PM's explicit acceptance comment establishing the initial release baseline. |
| `WINDOW35_PM_INTEGRATION` | `9eba4710e3cd841650191cb89f2126ca5c5b11c3` | Integration of PR #338 by PM. |
| `HISTORICAL_PR341` | `(Historical PR)` | Failed/blocked Window 39 PR. |
| `HISTORICAL_RUN49` | `49` | Failed/blocked run from PR #341. |
| `HISTORICAL_PR342` | `(Historical PR)` | Failed/blocked Window 40 PR. |
| `HISTORICAL_RUN56` | `56` | Failed/blocked run from PR #342. |
| `HISTORICAL_PR343` | `73fd8d664e308bfba22d8dbe309bf2e4b09be5f1` | Historical Exact Final Head from Window 40. |
| `HISTORICAL_RUN63` | `63` | Historical Final Run attempt for PR #343. |
| `PM40_AUDIT_COMMENT` | `6028686965` | PM review comment explicitly acknowledging historical technical gate GREEN but failing evidence completeness on Window 40. |
| `ACCEPTED_RELEASE_BASELINE` | `9eba4710e3cd841650191cb89f2126ca5c5b11c3` | Evaluated exact baseline for this formal correctness certification. |

**Verification**: All identities here are exactly matched against the `LIVE_MAIN` derivation, `github API` responses, and explicit inputs from the Window 41 PM adjudication instructions.
