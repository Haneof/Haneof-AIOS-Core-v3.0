# Hosted GitHub Actions post-read A→B control

**Result:** hosted post-read control reproduced and closed mechanically for the tested A→B interval. This is engineering control evidence, not Fresh Independent Acceptance and not a final formal run.

## Control design and observed ordering

The same formal workflow, canonical branch, workflow-level concurrency group, actual fixed inline commit-comment publisher, exact run/attempt/SHA/pin checks, and read-only post-read seal were used. The control pin is explicitly `NOT_A_FORMAL_RELEASE_OR_ACCEPTANCE_PIN` and remains `PROVISIONAL_PENDING_FINAL_IDENTITY_SEAL`.

- A's final canonical-branch read completed at `2026-10-05T15:16:12Z` and read A exactly.
- A entered the controllable 180-second post-read barrier at `15:16:12Z`.
- Only after observing that barrier, B was pushed to the same branch. B's successor run was created at `15:17:23Z`, after A's final branch read.
- B's successor run existed before A's 180-second barrier ended. A's `Fail stale A or seal stable successor B from workflow-run lineage` step then failed; the seal job did not succeed, and GitHub reports A's overall run `cancelled`. The workflow code rejects a newer successor for A and also fails closed if its run-list request/validation fails. Hosted log ZIP retrieval returned `EOF`, so the exact emitted line from that step is not asserted here.
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

A's seal steps: exact run/pin/final canonical read **SUCCESS**; post-read barrier **SUCCESS**; fail-stale-A/successor-ledger step **FAILURE**; overall A **CANCELLED**. B's exact run/pin/final read, barrier, and successor seal all **SUCCESS**. B was the successor head at completion of the first control round; the A2/B2 revalidation below repeats the hosted control against the final 180-second formal-settle configuration.

The old A pin is comment `203509011`; it remains provisional and explicitly control-only. The successful B control pin is comment `203509530`; it is likewise control-only. Neither pin is an authoritative formal release/acceptance pin.

## Ref non-interference and branch constraint

- The A→B test used only the session's platform-fixed `arena/01a10c8c-haneof-aios-core-v3-0` branch. The developer/session contract prohibits creating or pushing a separate control branch, so A/B were two controlled commits on the single permitted work branch.
- No PR #336 or #337 ref/file was changed. After the control, their states and exact heads were rechecked: #336 remains OPEN / non-draft / unmerged at `5a5d384f16798bfff46ffe03f87310b0eafb2321`; #337 remains OPEN / non-draft / unmerged at `f2388897afd212febc0d63d87787e730f47540c9`.
- Remote ref snapshot is `raw/POSTREAD_REF_SNAPSHOT.txt`.

## Revalidation against the final 180-second formal settle configuration (A2→B2)

This second hosted pair used the updated workflow head, whose formal whole-run seal now holds a 180-second post-read barrier; the control-seal branch held A2 in its corresponding 180-second barrier. The formal gate and formal whole-run seal jobs themselves are skipped in control mode. The workflow file was unchanged between A2 and B2.

| Identity/result | A2 | B2 successor |
|---|---|---|
| Candidate SHA | `73883929bab44dd8592c5e6cbe624a4eba1f24e6` | `ab851cab5fba57dcf6ba03d347dcdad78203de96` |
| Branch | `arena/01a10c8c-haneof-aios-core-v3-0` | same |
| Run id / number / attempt | `37332377614` / `39` / `1` | `37332475904` / `40` / `1` |
| Run URL | <https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/37332377614> | <https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/37332475904> |
| Run event / created | `push` / `2026-10-05T15:23:02Z` | `push` / `2026-10-05T15:23:46Z` |
| Control gate job id/result | `111838442181` — SUCCESS | `111839978790` — SUCCESS |
| Formal freeze-gate job id/result | `111838477693` — SKIPPED (control mode) | `111840019597` — SKIPPED (control mode) |
| Publisher job id/result | `111838482194` — SUCCESS | `111840025185` — SUCCESS |
| Publisher HTTP/comment id | HTTP-201 success path; comment `203510201` | HTTP-201 success path; comment `203510833` |
| Last-read control-seal job id/result | `111838532108` — FAILURE | `111840084430` — SUCCESS |
| Formal whole-run seal job id/result | `111838581190` — SKIPPED (control mode) | `111840139726` — SKIPPED (control mode) |
| Overall conclusion | **CANCELLED** | **SUCCESS** |
| Artifacts | none (`total_count=0`) | none (`total_count=0`) |

A2's final canonical-branch read completed at `15:23:19Z`; its 180-second controllable barrier began immediately. The pre-push observation at `15:23:32Z` records the barrier as active and B2 not yet pushed. B2's successor run was created at `15:23:46Z`, during A2's barrier. A2's barrier completed at `15:26:19Z`; the lineage-check step failed at `15:26:19–20Z`, and the overall run concluded `cancelled` at `15:26:29Z`. B2 then sealed at `15:26:47Z` and its overall control-only run concluded `success` at `15:26:54Z`. As above, the hosted log ZIP was unavailable, so the record relies on exact API run/job/step statuses, run-number ordering, pin comments, and ref identities rather than asserting unobserved step output.

A2 and B2 comments (`203510201`, `203510833`) are both marked `POSTREAD_CONTROL_ONLY`, `PROVISIONAL_PENDING_FINAL_IDENTITY_SEAL`, and `NOT_A_FORMAL_RELEASE_OR_ACCEPTANCE_PIN`. Both control rounds produced no workflow artifacts. The formal gate and formal whole-run seal were skipped on both A2 and B2, so neither successful B control run is a formal acceptance.

A2's pre-push barrier record is `raw/POSTREAD_A2_BARRIER_OBSERVED.txt`; full A2/B2 run, job, artifact, and pin-comment API JSON is in `raw/POSTREAD_A2_*` and `raw/POSTREAD_B2_*`. The current post-control remote-ref snapshot is `raw/POSTREAD_REF_SNAPSHOT.txt`; the first round's snapshot is `raw/POSTREAD_CONTROL1_REF_SNAPSHOT.txt`.

## Interpretation

The hosted control advanced A→B **after** the last canonical-branch read and while A was still inside its post-read barrier. The old A run could not leave an authoritative success: its lineage-seal step failed after the B successor run existed, and its overall conclusion is not success; the B successor is successful. The commit-comment publisher never promotes a pin; acceptance must additionally check the live canonical ref against the exact candidate SHA at acceptance time. This evidence closes the tested post-read race without treating `cancel-in-progress` as the sole safeguard.
