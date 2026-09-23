# C15 PM risk register — 2026-09-23

Access: **PM / OPERATOR ONLY**. This is not a second task queue. Only `AIOS_SINGLE_WINDOW_TASK_BOARD.md` may authorize active work.

Reviewed baseline: `main@ed07b5890909ae09cb2a0849729662b4235c1e3b`; frozen Core `bcd6bf353126318f9a97076b52ec1740d43f35a4`.

| ID | Priority / status | Evidence and impact | Accountable role / authorized route | Exit criterion |
|---|---|---|---|---|
| B-EXEC | High / blocking acceptance | #121 @ b6e5ac9 has only input ingest increments, no B model metering/trace; prose is not behavior evidence | PM corrective decision → B operator preflight → independent release → fresh B → independent acceptance | Pinned complete runtime evidence, lawful inputs, real model decisions/capability results and honest failures; no quota for new Claims |
| B-INDEX | High / blocking acceptance | Submitted World 97 / index 88 | Same B recovery chain; not a separate Core-fix authorization | Final index synchronized; per-step runtime/index processing observable; no historical backfill |
| R6-ID | High / blocking R6 | Trusted A execution/model attestation absent in current acceptance record | B preflight inventories availability; model-attest task before C release | Trusted platform/provider evidence binds actual sessions and proves different underlying model family/provider; otherwise INSUFFICIENT_EVIDENCE |
| CI-120 | Medium / unresolved | #120 merged despite run 35844880234 failing zero-Core-diff proof with exit 128; earlier mechanical/regression steps green; exact log root cause unavailable | Release PM owns triage. Separate CI-scope task only if evidence justifies a reproducible workflow defect; do not change workflow in this governance task | Obtain exact logs or independently establish cause; record rerun/fix/explicit scoped disposition. No global waiver; new PR checks evaluated separately |
| STATE | Medium / governance merged, state receipt tracked | Main still says B READY although #121 was submitted; historical headings and open issues can mislead | PR #122 merged at 2a68df3; authoring PM self-review and state receipt, no separate integration-window requirement | One current snapshot and unique next READY; immutable historical states clearly labeled; no automatic reimplementation of old issues |
| SCALE | Medium / deferred, unverified benchmark | AIWorldCognitionService.current scans payloads before output limit; #112 benchmark report open/unaccepted | P16 scale/readiness PM; activate measurement task only via board and freeze rules | Reproducible workload, hardware/limits, latency/memory/index/cost budgets; current-main evidence; no unapproved semantic refactor |
| RELEASE | Medium / P17 deferred | pyproject is 0.3.0.dev0; README only title; stable-release evidence pending | P17 entry only after P16 closure | Reproducible build, schema/migration, run/deployment instructions, accepted full CI and release evidence |

## Evidence/PR preservation

- #75 / #79 / #92: accepted historical C14 evidence; keep OPEN / UNMERGED / PINNED under their existing rulings.
- #117: sole canonical A handoff; unchanged.
- #121: rejected current B execution-evidence candidate; OPEN / UNMERGED / PINNED / NON-CANONICAL under the corrective decision after integration.
- #101: historical pre-fix A diagnostic, not a recovery source.
- Other open code/governance PRs require scope/equivalence review; being open is not permission to merge or resume them. No automatic mass closing/merging is authorized.

Do not use this register or the PM review as a blind Resident prompt. Do not treat candidate-report PASS, fixture-CI SUCCESS, independent evidence acceptance and final semantic VALID as interchangeable.
