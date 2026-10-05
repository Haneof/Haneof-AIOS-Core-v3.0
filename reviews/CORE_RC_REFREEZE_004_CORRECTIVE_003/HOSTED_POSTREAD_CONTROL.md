# Hosted GitHub Actions post-read A→B control

**Result:** hosted post-read control reproduced and closed mechanically for the tested A→B interval. This is engineering control evidence, not Fresh Independent Acceptance and not a final formal run.

## Control design and observed ordering

The same formal workflow, canonical branch, workflow-level concurrency group, actual fixed inline commit-comment publisher, exact run/attempt/SHA/pin checks, and read-only post-read seal were used. The control pin is explicitly `NOT_A_FORMAL_RELEASE_OR_ACCEPTANCE_PIN` and remains `PROVISIONAL_PENDING_FINAL_IDENTITY_SEAL`.

- A's final canonical-branch read completed at `2026-10-05T15:16:12Z` and read A exactly.
- A entered the controllable 180-second post-read barrier at `15:16:12Z`.
- Only after observing that barrier, B was pushed to the same branch. B's successor run was created at `15:17:23Z`, after A's final branch read.
- The A run ledger contained the newer B workflow run when A left the barrier. A's post-read successor check failed closed; the seal job did not succeed. GitHub reports A's overall run `cancelled` (the seal job itself is `failure`).
- The B successor completed the same control seal successfully and the overall B run succeeded.

This is not a local mock. The canonical ref move, both runs, job conclusions, commit comments, run numbers, and timestamps are from hosted GitHub Actions / GitHub API. Raw run and job JSON, pin comments, and ref snapshot are stored alongside this file. Hosted log ZIP retrieval returned `EOF`; accordingly, the record relies on API run/job/step conclusions and comment/ref identities and does not claim a downloaded log transcript.

## Exact A/B identities

| Identity/result | A | B successor |
|---|---|---|
| Candidate SHA | `26816f41aff855a2d4854c1c3492910a446d8da6` | `0bcfd52944ef983b7656224d29eeca9fd57f5f16` |
| Branch | `arena/01a10c8c-haneof-aios-core-v3-0` | same |
| Run id / number / attempt | `37331400336` / `37` / `1` | `37331604340` / `38` / `1` |
| Run URL | <https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/37331400336> | <https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/37331604340> |
| Run event / created | `push` / `2026-10-05T15:15:53Z` | `push` / `2026-10-05T15:17:23Z` |
| Control gate job id/result | `111835112491` — SUCCESS | `111836675347` — SUCCESS |
| Formal freeze-gate job id/result | `111835161097` — SKIPPED (control mode) | `111836734595` — SKIPPED (control mode) |
| Publisher job id/result | `111835168293` — SUCCESS | `111836711800` — SUCCESS |
| Publisher HTTP/comment id | success path required HTTP 201; comment `203509011` | success path required HTTP 201; comment `203509530` |
| Last-read control-seal job id/result | `111835219787` — FAILURE | `111836760525` — SUCCESS |
| Formal whole-run seal job id/result | `111835261209` — SKIPPED (control mode) | `111836797951` — SKIPPED (control mode) |
| Overall conclusion | **CANCELLED** | **SUCCESS** |
| Artifact | none (control-mode jobs do not upload formal artifacts) | none (control-mode jobs do not upload formal artifacts) |

A's seal steps: exact run/pin/final canonical read **SUCCESS**; post-read barrier **SUCCESS**; fail-stale-A/successor-ledger step **FAILURE**; overall A **CANCELLED**. B's exact run/pin/final read, barrier, and successor seal all **SUCCESS**. B was the successor head at completion of this control round; the updated 180-second formal settle configuration is being revalidated below.

The old A pin is comment `203509011`; it remains provisional and explicitly control-only. The successful B control pin is comment `203509530`; it is likewise control-only. Neither pin is an authoritative formal release/acceptance pin.

## Ref non-interference and branch constraint

- The A→B test used only the session's platform-fixed `arena/01a10c8c-haneof-aios-core-v3-0` branch. The developer/session contract prohibits creating or pushing a separate control branch, so A/B were two controlled commits on the single permitted work branch.
- No PR #336 or #337 ref/file was changed. After the control, their states and exact heads were rechecked: #336 remains OPEN / non-draft / unmerged at `5a5d384f16798bfff46ffe03f87310b0eafb2321`; #337 remains OPEN / non-draft / unmerged at `f2388897afd212febc0d63d87787e730f47540c9`.
- Remote ref snapshot is `raw/POSTREAD_REF_SNAPSHOT.txt`.

## Revalidation against the final 180-second formal settle configuration

Pending run pair on the updated workflow head. It repeats the same hosted A→B barrier after the exact final canonical-branch read. The final committed version replaces this section with A2/B2 run, job, pin, timestamp, ref, and overall conclusions.

## Interpretation

The hosted control advanced A→B **after** the last canonical-branch read and while A was still inside its post-read barrier. The old A run could not leave an authoritative success: its seal failed closed on the newer run lineage and its overall conclusion is not success; the B successor is successful. The commit-comment publisher never promotes a pin; acceptance must additionally check the live canonical ref against the exact candidate SHA at acceptance time. This evidence closes the tested post-read race without treating `cancel-in-progress` as the sole safeguard.
