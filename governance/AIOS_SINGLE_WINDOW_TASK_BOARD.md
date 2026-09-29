# AIOS v3.0 单窗口任务执行总表

## 当前控制入口 — 2026-09-30 PERSISTENCE CORRECTIVE-003 IA PASS / PM INTEGRATED / RELEASE-003 READY

- **`C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003 = DONE / ACCEPTED / INTEGRATED`**（`ACCEPTANCE_PASS / blocker=0`，`PM_ACCEPTED / INTEGRATED`，WINDOW `06` PM Integration）。Accepted engineering candidate = PR #299 exact head `19476641be95e666068e6299f42df9a411f4c0ba`，tree `7cd3dd81345f164cd932094cf7f8c98463a9c2f2`，sole parent `2d01ee2a8fe7f74fb8c3f3bf5fe5a94685907260`，construction merge-base `016a2f7db5ed01b41fc614701079c507d2c2c02e`。集成方式 = **标准 merge commit（禁止 squash / rebase）**，accepted exact SHA ancestry 完整保留：candidate merge SHA `PENDING_POST_MERGE`，post-candidate-merge main `PENDING_POST_MERGE`，`git merge-base --is-ancestor 19476641… <post-main>` = PASS。
- Fresh Independent Acceptance：`C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003-INDEPENDENT-ACCEPTANCE = ACCEPTANCE_PASS / blocker=0 / PM_INTEGRATED`，disposition `READY_FOR_PM_INTEGRATION`（PR #299 IA comment `5895090982`）。Accepted exact review `111a25d1f0822bc2b37557aa2364a4030d267082`（sole parent = candidate `19476641…`，tree `a5cb2aa0e7ff190888d24ce5ecb64d57b2a19bb9`）on remote `review/c15-persistence-c003-ia`；review branch 保持 **review-only / DO NOT MERGE / 永不进入 main**（`git merge-base --is-ancestor 111a25d1… <post-main>` = FALSE）。independent frozen probe SHA-256 `2e01947e2194f4eef73ec1b6fc5389bc465a1dfe11a30e769bc7a3ac50b68d72`。IA 不重做、reviewer 证据不修改。
- Scope（PM fresh diff vs `016a2f7db…`）：**`src/aios_core/**` = ZERO DIFF**、**`pyproject.toml` = ZERO DIFF**、**product packaging = ZERO DIFF**；56 文件全部为 additions，仅限 `tools/c15_persistence/**` + `tests/c15_persistence/**` + `reviews/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003/**`。无第二 truth store、无 Core 架构扩张、无真实 Resident B 证据、无 Resident C、无 evaluator、无 fixture future leak、无 release-state 真实消费。
- Formal CI（作者正式环境，fresh 核验全绿）：CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1；full **997/0/0/0**、focused trusted-return 99/99、R5 24/24、scale gates（s10k/s100k/s1m）、semantic-equivalence、due-backlog 全部 SUCCESS（8/8 checks；runs `36597294889/36597294962/36597295058/36597295207` head_sha = exact candidate）。IA 独立证据：probes 15/15、full 997/0/0、persistence 78/78、journal 13/13、killpoints 5/5、binding matrix 23/23、retained regressions 6/6、preflight/operator 131/131、frozen matrix expectation integrity preserved。
- 历史 provenance 保留（不得重写）：PR #251 failed exact `7b2556e738d9c9386ec21c13fec39400c87d0916` historical verdict **`ACCEPTANCE_FAIL / blocker=6`**（6 不改写为 3）；PM narrowed release blockers = `C002-001 / C002-002 / C002-004`，non-blocking hardening = `C002-003 / C002-005 / C002-006`。PR #254 保持 **`CLOSED / DRAFT / UNMERGED / FROZEN`**（closed head `a2d815c9f5154d87a56b152ed7cf5d1eb1baaaae`，PM STOP `5863009559`）；WIP `f7848952b6519fc40f50806f4a4d8d350ac0f38a` = `SCOPE_VIOLATION / NOT_A_CANDIDATE`，不得恢复或 merge。PR #299 线性 RED 历史保留：`d49f5131…` formal CI collection RED（`ModuleNotFoundError: No module named 'tools'`）→ `c73a4471…` import/bootstrap fix（随后 formal 3.12.14 暴露 13 Journal failures）→ `2d01ee2a…` CI diagnostics → `19476641…` workspace portability corrective / formal gates GREEN / accepted exact candidate。不得描述成“PR #299 一直 GREEN”。
- **唯一下一 READY：`C15-RCC-RES-B-RELEASE-003 = READY`**（仅为 release/operator preparation task，**不是 Resident B**；必须在 WINDOW `07` 新窗口执行，本窗口 06 不执行：不 mint 真实 Resident B identity、不 consume cursor、不 reveal cursor 14、不 run Resident、不 build Resident session、不对真实 state 跑 release probes）。下游保持 BLOCKED：`C15-RCC-RES-B-RERUN-003`、`C15-RCC-RES-B-ACCEPT-003`、`RESIDENT_B`、`RESIDENT_C`、`EVALUATOR`、`C15_CLOSE`。`one-window / one-task / one-next-READY` 维持。
- 集成收据：`governance/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003_ACCEPTANCE_INTEGRATION_RECEIPT_2026-09-30.md`。本 PM 治理回写 = GOVERNANCE_ONLY（task board + checkpoint + receipt），治理 PR 为本窗口最后动作之一；merge 后 fresh fetch main 做最终核验，然后停止，不启动 WINDOW `07`。


## 当前控制入口 — 2026-09-29 FRESH RESIDENT A CORRECTIVE-003 IA ACCEPTED / PM INTEGRATED / PERSISTENCE CORRECTIVE-003 RE-RELEASED

- **`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003 = DONE / ACCEPTED`**（PM integration `PM_ACCEPTED / INTEGRATED`）。Accepted evidence candidate = PR #296 exact head `317316299c332d82e0cbd0431b5c7d50f391bc17`, tree `a64b60ad1e64bcb930003f030246baafdae3eb8a`, sole parent `f7bcec4e558ebb4c6a11b7b45afe361cc659ef66`，保持 **OPEN / UNMERGED / EVIDENCE-ONLY**（212 evidence-only files；不 merge、不修改、不 amend/rebase/squash、不 hash-swap）。
- Fresh Independent Acceptance：`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-INDEPENDENT-ACCEPTANCE = ACCEPTANCE_PASS / blocker=0 / READY_FOR_PM_INTEGRATION`。Accepted exact review `7b072340b527a864874208cd58152c9147328a18`（sole parent `e83b1aa7e4321ba48a1cb390828e149350c2be71`，tree `ae1e81be3bc326906460a6fd70c6517f169f813e`，message `review-only: C15 Resident A Corrective-003 independent acceptance (ACCEPTANCE_PASS / blocker=0) — DO NOT MERGE`）on remote `review/c15-res-a-c003-ia`；fresh fetch 确认 remote HEAD exact match / identical / ahead=0 / behind=0；review commit 保持 **DO NOT MERGE**，不进入 main，不再执行第二次 IA。
- Publication：frozen `IA_REPORT.md` 中的 `EVIDENCE_PUBLICATION_BLOCKED` 只是 reviewer 执行沙箱当时（无 GitHub 写权限）的 **historical reviewer publication status**，**不得修改**（修改会破坏 accepted exact review SHA 的 immutable identity）；独立 publication recovery 已完成并经全新空仓库 fresh fetch 核验（remote HEAD exact / sole parent exact / tree exact / `git fsck --full` PASS）。**current authoritative = `EVIDENCE_PUBLICATION_RECOVERED / DURABLE`**。上述旧文本不是当前 blocker。
- PM semantic acceptance 覆盖 reviewer 已接受范围：resident-authored semantics、no prior/future leakage、clean-room contamination absence、cursor/ACK chronology、all 21 exchange chains、Wake/Review/Summary completeness、World/index provenance and coherence、final restart、checksum/freeze integrity、cursor 14 not revealed。PM 确认 accepted IA identity 后集成，不重做 IA。
- Fresh identity：pre-integration live main = `e83b1aa7e4321ba48a1cb390828e149350c2be71`（与派发基线一致，无 governance drift）；main 不含 review commit `7b072340...`，也不含 candidate `31731629...`；PR #296 comment `5891955371` 记录正式 acceptance。
- **`BLOCKED_ON_FRESH_RESIDENT_A_ACCEPTANCE` 解除**（前置已满足）。Mandatory post-Core sequence（`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001` → fresh IA → PM integration → `CORE-RC-REFREEZE-003` → fresh IA → fresh `C15-RCC-RES-A-RERUN-004` → fresh A IA → governance re-release of frozen persistence Corrective-003）步骤 1..7 全部完成；步骤 8 governance re-release 现在生效。
- **唯一下一 READY：`C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003 = READY`**（重新释放冻结任务）。旧 scope 裁决继续继承有效（merged PM scope #255 + `governance/C15_RCC_RES_B_PERSISTENCE_SCOPE_ADJUDICATION_2026-09-28.md` + `governance/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_003_CORE_DEPENDENCY_ADJUDICATION_2026-09-28.md`）：`tools/c15_persistence/**` = C15 Resident B habitation/release persistence harness，**不是** AIOS Core product implementation；仅修 binding blockers `C002-001 / C002-002 / C002-004`；禁止 `src/aios_core/**` 修改、禁止 product packaging 引入 persistence、禁止第二 truth store、禁止把 non-blocking hardening（003/005/006）变成 release gate。PR #254 保持 **CLOSED / DRAFT / UNMERGED / FROZEN**；WIP `f7848952b6519fc40f50806f4a4d8d350ac0f38a` 及 PM STOP 后含 `src/aios_core/**` diff 的后续 head 均为 **SCOPE_VIOLATION / NOT_A_CANDIDATE**，不得直接续用为 candidate；frozen WIP / valid continuation rules 继续执行（从冻结现场继续 scope 合规的 persistence harness work，不得 rewrite 历史 WIP/red/green）。
- Resident B run / Resident C / evaluator / C15 close 继续 **BLOCKED**，直到 Persistence Corrective-003 自身完成 engineering → review → fresh Independent Acceptance → PM integration。`one-window / one-task / one-next-READY` 维持，禁止一次性放开多项。
- 集成收据：`governance/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_ACCEPTANCE_INTEGRATION_RECEIPT_2026-09-29.md`。本 PM 窗口到此停止，不执行 Persistence Corrective-003。


## 当前控制入口 — 2026-09-29 FRESH RESIDENT A CORRECTIVE-003 REVIEW_READY / IA READY

- **`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003 = PHASE_A_COMPLETE / REVIEW_READY`**. Evidence PR #296 remains **OPEN / UNMERGED / EVIDENCE-ONLY** at exact head `317316299c332d82e0cbd0431b5c7d50f391bc17`, tree `a64b60ad1e64bcb930003f030246baafdae3eb8a`, sole parent `f7bcec4e558ebb4c6a11b7b45afe361cc659ef66`.
- PM mechanical readiness: 212 changed files, all within the new Resident evidence package; cursor 1..13 event/ingest/ACK evidence present; no cursor14 event; release-state last_ack=13 / next=14 / pending=null; World/index = 38/38; exchange = COMPLETE 21/21, 63 records, 0 unconsumed/open; package SHA256SUMS covers 211 remaining files; mechanical CI gate green.
- Run pins frozen RC `f20f2ed...` / Core `9adcbe...` / tests `7e33b5...`, accepted harness H1 `77dac70e...`, packet SHA `3c2d04c2...`, and exact runtime 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1 / OpenSSL 3.0.13.
- PM readiness does **not** accept semantic authenticity, clean-room contamination absence, temporal/future isolation, due-work completeness, or cognition quality. Those are binding IA responsibilities.
- **唯一下一 READY：`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-INDEPENDENT-ACCEPTANCE = READY`**. Binding prompt: `governance/prompts/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_INDEPENDENT_ACCEPTANCE_2026-09-29.md`.
- IA must independently verify Resident-authored semantics, no prior/future leakage, all 21 exchange chains, cursor/ACK chronology, Wake/Review/Summary completeness, World/index provenance/coherence, final restart, checksum/freeze integrity, and cursor14 not revealed.
- Persistence Corrective-003, Resident B/C, evaluator and C15 close remain **BLOCKED_ON_FRESH_RESIDENT_A_ACCEPTANCE**.


## 当前控制入口 — 2026-09-29 OPERATOR-PREP CORRECTIVE-003 IA PASS / FRESH RESIDENT A READY

- **`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003 = ACCEPTANCE_PASS / blocker=0 / ACCEPTED_EXACT`**. Accepted candidate PR #292 final H2 = `42a63ed4416585fc0a02045e0bd5190f32a01a2b` (tree `80440bdd70aa658053bc5bf33a902c46cd7138e0`), corrected harness H1 = `77dac70e0cf054c3f0fb7d94a66dba221fe7d5de` (tree `52aa366bc6548e86e805585baddbc0470cb69660`). Fresh IA review-only PR #294 exact = `30955cc7065d0d66cf4de43f833f1b1f9162b635` → `ACCEPTANCE_PASS / blocker=0`.
- Fresh IA independently reproduced reviewer rev3 probes 50/50, C10/C11 18/18, C1-C3 GREEN, C4-C9 103/103, Gates A/B/C/D 24/7/2/5, exact runtime pins and full packet/freeze/checksum integrity. No real Resident was run during Operator Prep acceptance.
- PM-approved Resident-safe launch packet = `RESIDENT_SAFE_LAUNCH_PACKET.json` SHA-256 `3c2d04c2de8557c3cb7329df4350c40b2ccc07520a7d3d51db206174b33266cc`, status remains `PREP_REVIEW_READY`; PM approval is external and does not mutate the accepted artifact.
- **唯一下一 READY：`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003 = READY`** — Real Resident AI / Fresh Corrective Resident A, cursor 1..13 only.
- **Clean-room rule is binding:** the Resident itself MUST NOT read this task board, checkpoint, governance adjudications, #292/#294 metadata/comments, historical Resident runs/reviews, fixture/evaluator/release source, future events, or Git history concerning prior Resident runs. Resident startup input is exactly: clean-room contract + canonical Resident run contract + exact PM-approved launch packet + mechanical environment/harness status.
- The Resident must use the accepted Operator Prep harness and frozen RC, create all-new World/index/release-state/session/process/runtime/exchange state, personally make every semantic decision, never patch harness after cursor 1, stop after cursor 13, and publish evidence-only `PHASE_A_COMPLETE / REVIEW_READY`.
- Persistence Corrective-003, Resident B/C, evaluator and C15 close remain **BLOCKED_ON_FRESH_RESIDENT_A**.


## 当前控制入口 — 2026-09-29 OPERATOR-PREP CORRECTIVE-003 REVIEW_READY / FRESH IA READY

- **`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003 = OPERATOR_PREP_CORRECTIVE_003_COMPLETE / REVIEW_READY`**. Candidate PR #292 remains **OPEN / UNMERGED / EVIDENCE-ONLY** at final H2 `42a63ed4416585fc0a02045e0bd5190f32a01a2b` (tree `80440bdd70aa658053bc5bf33a902c46cd7138e0`), sole parent/corrected H1 `77dac70e0cf054c3f0fb7d94a66dba221fe7d5de` (tree `52aa366bc6548e86e805585baddbc0470cb69660`), H1 parent genuine RED freeze `083dd9506f01ade04d4cbe805f58bf80d40607b0`.
- Fresh PM readiness verified 546 PR paths remain confined to Operator Prep/Corrective evidence trees; zero Core/product-tests/fixture/evaluator/release-source/real Resident state paths. H1→H2 changes only packet/evidence/raw freeze artifacts; no covered harness/bootstrap/probe-source implementation changed after H1.
- Author evidence reports frozen C10/C11 = 18/18 RED on exact #288 H2 and 18/18 GREEN on H1/final packet; C1-C3 GREEN; C4-C9 103/103 GREEN; Gates A/B/C/D = 24/7/2/5 PASS; packet audit 59/59 PASS; clean runtime exact pins PASS. These remain author evidence pending fresh IA.
- PM spot-check confirms cross-process authority uses dedicated `fcntl.flock` plus reentrant same-process protection, and required directory durability failures are propagated rather than silently returned as successful publication.
- Launch packet SHA-256 = `3c2d04c2de8557c3cb7329df4350c40b2ccc07520a7d3d51db206174b33266cc`, status `PREP_REVIEW_READY`.
- **唯一下一 READY：`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003-INDEPENDENT-ACCEPTANCE = READY`**. Binding prompt: `governance/prompts/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_OPERATOR_PREP_CORRECTIVE_003_INDEPENDENT_ACCEPTANCE_2026-09-29.md`.
- Fresh IA must independently attack concurrency/lock/durability/retry/crash boundaries, then re-attack every historical C1-C9 guarantee and full A/B/C/D. Author GREEN is not transferable acceptance.
- `C15-RCC-RES-A-RERUN-004-CORRECTIVE-003` remains **BLOCKED_ON_OPERATOR_PREP**. No real Resident release/run is authorized.
- Persistence Corrective-003, Resident B/C, evaluator and C15 close remain **BLOCKED**.


## 当前控制入口 — 2026-09-29 OPERATOR-PREP CORRECTIVE-002 IA FAIL / CORRECTIVE-003 READY

- **`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-002 = ACCEPTANCE_FAIL / blocker=2 / HISTORICAL_FAILED_EXACT`**. Failed candidate PR #288 final freeze H2 = `771b200c33dbd6055b1d209935f8e1552f13090f` (tree `071b51c5fb37dc59fc8941dee2182637b9f87daa`), corrected H1 = `63c972ad7a19671cbdf809177f7a552aa2c2ecc6`. Fresh IA review-only PR #290 exact = `39408137edf77976d0c4833fcde551891d5d081a`, verdict `ACCEPTANCE_FAIL / blocker=2`.
- Binding blocker `IA288-01`: concurrent independent exchange writers can both return success while allocating from the same ledger prefix and leave an invalid non-monotonic hash chain. Successful mutation must be serialized by an enforceable cross-object/process single-writer transaction boundary.
- Binding blocker `IA288-02`: required directory fsync/open failures are converted to false/ignored, allowing request/ledger publication success after a failed durability primitive. Directory durability failures must propagate fail-closed, including retry/recovery semantics.
- Review #290 independently reproduced the exact pinned runtime, Gates A/B/C/D = 24/7/2/5 PASS, and Corrective-002 C4-C9 = 103 PASS. Therefore the two blockers are additional defects, not environment/setup failures.
- Reviewer supplemental request-file-mutation observation remains non-blocking hardening in this adjudication; no semantic cross-binding through the approved runner was demonstrated.
- **唯一下一 READY：`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-003 = READY`**. Binding prompt: `governance/prompts/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_OPERATOR_PREP_CORRECTIVE_003_2026-09-29.md`.
- Corrective-003 must preserve all C1-C9 GREEN evidence, freeze targeted C10/C11 probes and reproduce RED against exact #288 before implementation, then repair only concurrency linearization and fail-closed directory durability, rerun full gates/bootstrap and publish a new evidence-only candidate.
- `C15-RCC-RES-A-RERUN-004-CORRECTIVE-003` remains **BLOCKED_ON_OPERATOR_PREP**. No real Resident release/run is authorized.
- Persistence Corrective-003, Resident B/C, evaluator and C15 close remain **BLOCKED**.


## 当前控制入口 — 2026-09-29 OPERATOR-PREP CORRECTIVE-002 REVIEW_READY / FRESH IA READY

- **`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-002 = OPERATOR_PREP_CORRECTIVE_002_COMPLETE / REVIEW_READY`**. Candidate PR #288 remains **OPEN / UNMERGED / EVIDENCE-ONLY** at final freeze H2 `771b200c33dbd6055b1d209935f8e1552f13090f` (tree `071b51c5fb37dc59fc8941dee2182637b9f87daa`), sole parent/corrected H1 `63c972ad7a19671cbdf809177f7a552aa2c2ecc6` (tree `8cd4a2d8b4cdf1f85699c5d78166f774741b420b`), H1 parent genuine RED freeze `8e34fba00edf4fdb5b80f04d7a648f6b5bb8c40e`.
- Fresh PM readiness verified 372 PR paths are confined to internal Operator Prep/Corrective evidence trees; zero Core/product-tests/governance/fixture/evaluator/release-source drift and no real World/release-state/resident-run DB artifacts. H2 check `c15-rcc-fixture-mechanical-gate` is green.
- Author evidence reports exact #286 H2 baseline C4-C9 = 23 PASS / 80 FAIL, same frozen v2 candidate probes = 103 PASS; Corrective-001 C1-C3 remains GREEN; Gates A/B/C/D = 24/7/2/5 PASS; clean scratch runtime = CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1 / OpenSSL 3.0.13. These remain author evidence pending fresh IA.
- Launch packet SHA-256 = `f6b61c33dc41d20438ab1b56bd1c8f2e46fcf6593532f3793c3c51ee7fbf7cdc`, status `PREP_REVIEW_READY`; packet pins the exact four-input startup set, user-turn and due-work entrypoints, canonical RC manifests, wheel trust root and full gates.
- **唯一下一 READY：`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE = READY`**. Binding prompt: `governance/prompts/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_OPERATOR_PREP_CORRECTIVE_002_INDEPENDENT_ACCEPTANCE_2026-09-29.md`.
- Fresh IA must independently re-attack every #283/#284 historical blocker, C1-C9 regressions, clean bootstrap/RC identity, operational ledger/recovery, due-work exchange, packet startup boundary and freeze integrity. Author GREEN is not transferable acceptance.
- `C15-RCC-RES-A-RERUN-004-CORRECTIVE-003` remains **BLOCKED_ON_OPERATOR_PREP**. No real Resident release/run is authorized.
- Persistence Corrective-003, Resident B/C, evaluator and C15 close remain **BLOCKED**.


## 当前控制入口 — 2026-09-28 OPERATOR-PREP CORRECTIVE-001 REVIEW_BLOCKED / CORRECTIVE-002 READY

- **`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-001 = OPERATOR_PREP_CORRECTIVE_COMPLETE / REVIEW_READY / PM_REVIEW_BLOCKED / KNOWN_UNRESOLVED_FINDINGS`**. PR #286 final freeze H2 = `c32e544b747cb1f1d9b7418e2163a65ac55ee39c`, parent/corrected candidate H1b = `99af8e268a1f9e8944b163d8087005e0e3698620`. No fresh IA was released for #286.
- Corrective-001 successfully closed the three #283 blockers: response replay on-disk verification, pre-download wheel trust root, and gate enumeration/result consistency.
- During fresh PM readiness, PM discovered a second historical independent review of the same failed #281 exact: review PR #284 @ `dce47c0d8f3ac7e34efb47e22c63c6f9acbea1a6`, verdict `ACCEPTANCE_FAIL / blocker=6`. Its findings were not included in the earlier #283-based adjudication.
- PM independently checked #284 against #286. Remaining valid defects include: recovery request↔snapshot binding/ambiguity; operational ledger chain+uniqueness enforcement; bootstrap frozen-RC verify fail-open / working-tree identity; SQLite exact version verification; launch packet startup-input mismatch; missing due-work model-exchange entrypoint. The wheel-closure portion of historical IA284-OP-04 is already closed by Corrective-001.
- PM ruling for future Resident startup inputs is now exact: clean-room contract + canonical `RESIDENT_A_RUN_CONTRACT.md` + exact PM-approved launch packet + approved mechanical environment/harness status. All historical/alternate Resident contracts/control-plane material remain forbidden.
- **唯一下一 READY：`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-002 = READY`**. Prompt: `governance/prompts/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_OPERATOR_PREP_CORRECTIVE_002_2026-09-28.md`.
- Corrective-002 must preserve all Corrective-001 GREEN fixes, freeze targeted probes against exact #286 before implementation, close only the remaining #284 findings, then rebuild/refreeze Operator Prep evidence.
- `C15-RCC-RES-A-RERUN-004-CORRECTIVE-003` remains **BLOCKED_ON_OPERATOR_PREP**. No real Resident run is authorized.
- Persistence Corrective-003, Resident B/C, evaluator and C15 close remain **BLOCKED**.


## 当前控制入口 — 2026-09-28 OPERATOR-PREP IA FAIL / CORRECTIVE-001 READY

- **`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP = ACCEPTANCE_FAIL / blocker=3 / HISTORICAL_FAILED_EXACT`**. Failed candidate PR #281 exact head = `10901d467679b70437ae112747eab81f889fd5cb` (parent `abb8b435e5187c7c6c2f4332aea37cd805b4a53c`, tree `db79761216529cf83f217ab00c937bc79806a510`). Fresh IA PR #283 exact review = `e3394da5d607e34c0286c16a11837ac7ea173a56`, verdict `ACCEPTANCE_FAIL / blocker=3`.
- Binding blocker `IA-OP-001`: `ResponsePublisher.publish_bytes()` can return idempotent replay success when a durable response ledger record exists but the already-published response file has been tampered; fail-closed verification must occur at publish time.
- Binding blocker `IA-OP-002`: bootstrap pins package versions but computes Python wheel hashes only after live download; the complete wheel/dependency trust root must be source-controlled and verified before acquisition/use.
- Binding blocker `IA-OP-003`: frozen gate results report `test_count=0/test_ids=[]` despite actual collect-only counts 19/7/2/5; gate enumeration/result evidence is internally inconsistent.
- PM independently verified PR #281 PR-wide scope = 56/56 files under the Operator Prep package and zero Core/tests/workflow/fixture/evaluator/release-source drift. Historical #281/#283 remain immutable; no post-hoc rewrite/hash-swap.
- **唯一下一 READY：`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-CORRECTIVE-001 = READY`**. Prompt: `governance/prompts/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_OPERATOR_PREP_CORRECTIVE_001_2026-09-28.md`.
- Corrective scope is strictly IA-OP-001/002/003. Before modifying the carried-forward package, freeze targeted corrective probes and reproduce RED against exact failed #281. Then apply the smallest Operator Prep-only corrections, rebuild from clean scratch, rerun full A/B/C/D, regenerate freeze evidence and a new `PREP_REVIEW_READY` launch packet.
- `C15-RCC-RES-A-RERUN-004-CORRECTIVE-003` remains **BLOCKED_ON_OPERATOR_PREP**. No Resident launch is authorized.
- Persistence Corrective-003, Resident B/C, evaluator and C15 close remain **BLOCKED**.


## 当前控制入口 — 2026-09-28 CORRECTIVE-003 OPERATOR-PREP REVIEW_READY / FRESH IA READY

- **`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP = OPERATOR_PREP_COMPLETE / REVIEW_READY / READY_FOR_INDEPENDENT_ACCEPTANCE`**. Candidate PR #281 remains **OPEN / UNMERGED / EVIDENCE-ONLY** at exact head `10901d467679b70437ae112747eab81f889fd5cb` (parent `abb8b435e5187c7c6c2f4332aea37cd805b4a53c`, tree `db79761216529cf83f217ab00c937bc79806a510`).
- All 56 candidate files are confined to `reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP/**`; zero Core/tests/workflow/fixture/evaluator/release-source drift.
- Launch packet SHA-256 = `dfab9270f811836f1aad77641a1ec007eb741d1c6ce1acb68f51763eb00bad73`, status `PREP_REVIEW_READY`; packet audit PASS. Candidate head's sole parent matches packet `operator_prep_exact_head = abb8b435...`.
- Operator evidence reports unified CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1 and A/B/C/D gates PASS. PM spot-check confirmed Gate C contains a real second-round frozen-Core `CapabilityResult` history and real runner has no semantic callback. These remain author/readiness evidence pending fresh IA.
- **唯一下一 READY：`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP-INDEPENDENT-ACCEPTANCE = READY`**. Prompt: `governance/prompts/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_OPERATOR_PREP_INDEPENDENT_ACCEPTANCE_2026-09-28.md`.
- `C15-RCC-RES-A-RERUN-004-CORRECTIVE-003` remains **BLOCKED_ON_OPERATOR_PREP**. No real Resident release/run is authorized.
- Persistence Corrective-003, Resident B/C, evaluator and C15 close remain **BLOCKED**.


## 当前控制入口 — 2026-09-28 CORRECTIVE-002 PRE-REVEAL CONTAMINATED / CORRECTIVE-003 OPERATOR-PREP READY

- **`C15-RCC-RES-A-RERUN-004-CORRECTIVE-002 = BLOCKED / CONTAMINATED_BEFORE_RUN / PRE-REVEAL / HISTORICAL_BLOCKED_EXACT`**. Evidence PR #279 exact head = `8e5c1ec76ea973c849c33923ccc818fe1dad49e8` (direct parent `aa13733ae393ec70e0cfc923ad3fb59a4e1ad97a`, tree `af5f7dd273e98f8502ea70556fe80f71e542f37c`). No World/index/release-state/session/ledger/cursor was created.
- Root dispatch defect: the fresh Resident was required to read global task-board/checkpoint/PM adjudication material that preserves historical Resident/review semantics. Those files are **not Resident-safe inputs**. The Resident correctly stopped before run start.
- Environment precondition also failed: no qualified CPython 3.12.14 / Pydantic 2.13.5 environment was established. No A/B/C/D gate ran.
- **唯一下一 READY：`C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP = READY`**. Prompt: `governance/prompts/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_OPERATOR_PREP_2026-09-28.md`.
- Operator Prep is **NOT Resident**. It must pre-provision/reproduce CPython 3.12.14 + Pydantic 2.13.5, build/test/freeze the mechanical harness against real frozen Core, and produce a semantic-free `RESIDENT_SAFE_LAUNCH_PACKET.json`.
- Clean-room Resident contract: `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_CORRECTIVE_003_CLEAN_ROOM_CONTRACT.md`.
- `C15-RCC-RES-A-RERUN-004-CORRECTIVE-003` remains **BLOCKED_ON_OPERATOR_PREP**. It must not read board/checkpoint/adjudications when eventually released.
- Until Operator Prep fresh IA PASS + PM integration + fresh Corrective-003 Resident PASS + PM integration: persistence Corrective-003, Resident B/C, evaluator and C15 close remain **BLOCKED**.


## 当前控制入口 — 2026-09-28 A-004 CORRECTIVE-001 BLOCKED / CORRECTIVE-002 READY

- **`C15-RCC-RES-A-RERUN-004-CORRECTIVE-001 = BLOCKED / HISTORICAL_BLOCKED_EXACT`**. Evidence PR #277 exact head = `2968299beea5fe5ec2dc93418d0fa7f3e035ec40` (parent `c90b585141864f0687f210b05cde8523e00607e6`, tree `e474cd5a3a55959b97c4c3b69400ab258d25f083`). The run correctly refused post-reveal harness patching and stopped after cursor 1.
- Binding defect `CORR001-BLK-001`: frozen runner expected nonexistent `CapabilityResult.arguments/result/error/duration_seconds`; accepted Core exposes only `name/ok/data/error_code/error_message/call_id`. The 14 pre-run tests covered bridge mechanics but not runner↔frozen-Core contract.
- Binding defect `CORR001-BLK-002`: #277's `resident_agent.py` contains keyword/text-driven hard-coded cognition calls and final replies. That is a scripted semantic policy, not Real Resident decision-making, and independently invalidates the run as Resident evidence.
- Additional gate hardening: Corrective-001 pre-run tests ran under CPython 3.11.2; Corrective-002 binding pre-reveal tests must run under the same CPython 3.12.14 / Pydantic 2.13.5 environment used for the real Resident.
- **唯一下一 READY：`C15-RCC-RES-A-RERUN-004-CORRECTIVE-002 = READY`**. Prompt: `governance/prompts/C15_RCC_RES_A_RERUN_004_CORRECTIVE_002_2026-09-28.md`.
- Corrective-002 must be a completely fresh Phase-A rerun. Before cursor 1 it must pass/freeze: exchange bridge tests, real frozen-Core `RuntimeSnapshot/CapabilityResult` serialization tests, an integrated two-round synthetic runtime test with non-empty capability history, and a no-semantic-script guard. Real execution must use the current Resident session to decide each request through a mechanical publisher only.
- Until Corrective-002 + fresh IA PASS + PM integration: persistence Corrective-003, Resident B/C, evaluator and C15 close remain **BLOCKED**.


## 当前控制入口 — 2026-09-28 A-004 IA FAIL / CORRECTIVE-001 READY

- **`C15-RCC-RES-A-RERUN-004 = ACCEPTANCE_FAIL / blocker=2 / HISTORICAL_FAILED_EXACT`**. Failed evidence PR #273 exact head = `f251e9c0026a0f97fdee20397936cb5e3b18c61c`; failed Independent Acceptance PR #275 exact = `ccd5f539714604f5ff5912b90024f28b82618511`. Both remain immutable historical evidence; no hash-swap or post-hoc repair.
- Binding blocker `IA-A004-01`: cursor-1 `not_submitted` reconciliation is not proven because the Resident semantic request had already been published and a semantic response existed; null anonymous-provider fields do not prove non-dispatch.
- Binding blocker `IA-A004-02`: cursor-10 final response/reply hashes agree, but no durable ordered record proves those exact response bytes existed before reconciliation; final consistency is not historical chronology.
- PM adjudication: both findings are **run-harness/recovery-proof defects, not demonstrated Core exactly-once regressions and not demonstrated fabricated cognition**. No Core change is authorized.
- **唯一下一 READY：`C15-RCC-RES-A-RERUN-004-CORRECTIVE-001 = READY`**. Prompt: `governance/prompts/C15_RCC_RES_A_RERUN_004_CORRECTIVE_001_2026-09-28.md`.
- Corrective is a **new fresh Phase-A run**, not an amendment to #273. Before cursor 1, the new run-local exchange bridge must pass synthetic plumbing tests, provide atomic response publication + fsynced ordered exchange ledger, and be frozen by SHA-256; after cursor 1 starts, harness mutation is forbidden.
- Until corrective run + fresh IA PASS + PM integration: persistence Corrective-003, Resident B/C, evaluator and C15 close remain **BLOCKED**.


## 当前控制入口 — 2026-09-28 A-RERUN-004 REVIEW_READY / FRESH IA READY

- **`C15-RCC-RES-A-RERUN-004 = PHASE_A_COMPLETE / REVIEW_READY / READY_FOR_INDEPENDENT_ACCEPTANCE`**. Evidence PR #273 remains **OPEN / UNMERGED / EVIDENCE-ONLY** at exact head `f251e9c0026a0f97fdee20397936cb5e3b18c61c` (parent `0b17c7f35697dc4a24b731185868d29967efcf58`, tree `fd312286b7b83cd550ecc49d72b78656e6e91b71`).
- Frozen RC execution pins: software `f20f2edfa7af00d0286493fd15196ca9503bc315`; Core tree `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`; tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`.
- PR #273 contains 189 evidence files, all under `reviews/internal_habitation/c15-rcc/v1/resident/runs/a004-27bb1fb3da404f4d/**`; **zero src/tests/tools/governance drift**.
- Mechanical run evidence records 13/13 ACK, last ACK c15rcc-013, `next_sequence=14`, `pending_reveal=null`, final World revision 89 and index watermark 89. These remain author/run evidence pending independent verification.
- Fresh IA must attack Resident decision authenticity, future contamination, cursor-1/cursor-10 recovery legality, anonymous local-handler provenance truthfulness, attention-watch step-boundary replay legality, Wake/Review/Summary completeness, World/index coherence and freeze hashes.
- **唯一下一 READY：`C15-RCC-RES-A-RERUN-004-INDEPENDENT-ACCEPTANCE = READY`**. Prompt: `governance/prompts/C15_RCC_RES_A_RERUN_004_INDEPENDENT_ACCEPTANCE_2026-09-28.md`.
- Until fresh IA PASS + separate PM integration: persistence Corrective-003 resume, Resident B/C, evaluator and C15 close remain **BLOCKED**.


## 当前控制入口 — 2026-09-28 RC-REFREEZE-003 INTEGRATED / A-RERUN-004 READY

- **`CORE-RC-REFREEZE-003 = DONE / ACCEPTED / INTEGRATED`**. Frozen software = `f20f2edfa7af00d0286493fd15196ca9503bc315`; frozen Core tree = `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`; frozen tests tree = `7e33b5ef8432370234965d3ccd61248c703c4019`.
- Accepted RC candidate PR #269 exact head = `6f95431036dd0304947d67ec4a8de7229d1d3ba9`; fresh Independent Acceptance PR #271 exact = `6eaf91822c39398c610a80c6985d28b4cab48eed` with `ACCEPTANCE_PASS / blocker=0`; #269 merged as `79ee5161491fb6a9215700f6391281083661b8ca`.
- Independent review verified merge-ref equivalence, 23/23 RC checksums, full 919 regression, 248 trusted-return/recovery tests, 356 Core-systems tests, 5/5 reviewer probes, real SIGKILL recovery, clean-wheel headless, backup/restore/index rebuild and writer/restart.
- Binding RC impact remains **`FRESH_A_REQUIRED`**. A-003 is **`HISTORICAL_FOR_PRIOR_RC_ONLY`** and MUST NOT seed or substitute for A-004.
- **唯一下一 READY：`C15-RCC-RES-A-RERUN-004 = READY`**. Prompt: `governance/prompts/C15_RCC_RES_A_RERUN_004_2026-09-28.md`.
- A-004 must use a fresh private World/index/release-state/session/process on exact frozen software `f20f2ed...`, run only Phase A cursor 1..13, reveal no cursor 14, and create evidence-only output.
- `C15-RCC-RES-A-RERUN-004-INDEPENDENT-ACCEPTANCE`, persistence Corrective-003 resume, Resident B/C, evaluator and C15 close remain **BLOCKED** until their prerequisites pass.


## 当前控制入口 — 2026-09-28 RC-REFREEZE-003 REVIEW_READY / FRESH IA READY

- **`CORE-RC-REFREEZE-003 = REVIEW_READY / READY_FOR_INDEPENDENT_ACCEPTANCE`**. Candidate PR #269 remains **OPEN / UNMERGED** at exact head `6f95431036dd0304947d67ec4a8de7229d1d3ba9` (first parent `f2ef4886cbd7253543e82debbaa14ea387417f03`, tree `a43a761ac3570dfc4aab296818310068f877e881`).
- Frozen software target remains `f20f2edfa7af00d0286493fd15196ca9503bc315`. PR #269 changes freeze evidence/release metadata/formal-gate workflow only; **zero src/tests/package implementation drift** relative to live main at PM review.
- Exact-head formal gate run `36437699641` = **SUCCESS**. Author evidence includes 919 full pytest PASS, 248 trusted-return/recovery PASS, 356 Core systems PASS, registry 43 total / 22 side-effecting, clean-wheel/headless PASS, backup/restore/index rebuild PASS. These are not acceptance proof.
- **唯一下一 READY：`CORE-RC-REFREEZE-003-INDEPENDENT-ACCEPTANCE = READY`**. Prompt: `governance/prompts/CORE_RC_REFREEZE_003_INDEPENDENT_ACCEPTANCE_2026-09-28.md`.
- Fresh IA must independently verify freeze/merge-ref equivalence, manifests/checksums, clean install, backup/restore/rebuild, writer/restart, trusted-return invariants, real recovery/process-loss, open-PR contamination and `FRESH_A_REQUIRED`.
- Until fresh IA PASS + PM integration: PR #269 merge, `C15-RCC-RES-A-RERUN-004`, persistence Corrective-003 resume, Resident B/C, evaluator and C15 close remain **BLOCKED**.


## 当前控制入口 — 2026-09-28 TRUSTED-RETURN CORRECTIVE-001 INTEGRATED / RC-REFREEZE-003 READY

- **`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001 = DONE / ACCEPTED / INTEGRATED`**. Accepted exact candidate = `a73e186d40688f5dc181b1128a62eff37a974409`; fresh IA evidence = `eeda251e057e98b15a919694af4689786faf8c55` with `ACCEPTANCE_PASS / blocker=0`; implementation PR #264 merged as `f20f2edfa7af00d0286493fd15196ca9503bc315`.
- Independent reviewer evidence: 86/86 reviewer probes PASS on candidate, 50 RED on failed exact #258, all five historical IA RED families reproduced, complete 22-side-effect replay convergence, store fail-closed PASS, real SIGKILL PASS, rev5→rev6 = `LEGITIMATE_HARNESS_CORRECTION`.
- Reviewer-local Python 3.12.14 limitation is **CLOSED / NON_BLOCKING** by PM-owned exact replay run **36423849252**: frozen probe SHA manifest all OK, CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.45.1, collect-only 86, **86 passed / 0 failed / 0 errors / 0 skipped**. Earlier PM run 36423769257 is preserved as harness-path failure before probe execution.
- Post-merge equivalence: accepted exact `a73e186d...` → post-merge main `f20f2edf...` differs only in pre-existing governance files; **ZERO src/tests implementation drift**.
- **A-003 = HISTORICAL_FOR_PRIOR_RC_ONLY** for the next lineage. It must not be reused to launch B after this Core integration.
- **唯一下一 READY：`CORE-RC-REFREEZE-003 = READY`**. Formal prompt: `governance/prompts/CORE_RC_REFREEZE_003_2026-09-28.md`. Freeze software boundary begins from accepted post-integration software `f20f2edfa7af00d0286493fd15196ca9503bc315`.
- `CORE-RC-REFREEZE-003-INDEPENDENT-ACCEPTANCE`, `C15-RCC-RES-A-RERUN-004`, persistence Corrective-003 resume, B release/run, Resident C, evaluator and C15 close remain **BLOCKED** until their prerequisites pass.


## 当前控制入口 — 2026-09-28 CORRECTIVE-001 REVIEW_READY / FRESH IA READY

- **`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001 = REVIEW_READY / READY_FOR_INDEPENDENT_ACCEPTANCE`**. Engineering PR #264 remains **OPEN / UNMERGED** at exact head `a73e186d40688f5dc181b1128a62eff37a974409` (parent `71f6d106a697b0c61410d42114545f2645e12510`, tree `352f47ac4e3098b10b1b78e4757543477371548d`). Live main at PM release remained `5288822e751df185f3abab79f969609f31859617`.
- Author evidence: dynamic registry 43 model-callable / 22 side-effecting, all 22 probed; baseline rev5 against failed exact #258 = 20 FAILED / 44 passed; candidate rev7 = 83 passed; store fail-closed = 17 passed; real SIGKILL process-loss = 3 passed; focused = 111 passed; full local = 919 passed. Exact-head fetched PR workflows: **23/23 completed SUCCESS**. These are author/CI evidence only, not acceptance.
- PM mechanically confirmed key trusted-return carry-forward blobs (`background_attempt.py`, `turn_runtime.py`, historical R5 test) are byte-identical to failed #258 exact. PR #258 / #261 remain untouched historical failure evidence.
- **Binding Independent-Acceptance adjudication:** frozen rev5 classified changed-field cases for `upsert_relation`, `update_cognitive_policy`, `rollback_cognitive_policy` as same-key fail-closed conflicts; post-implementation rev6 reclassified them as `identity_shifts`. IA must independently decide whether this is a legitimate correction of an over-specified synthetic expectation or prohibited post-implementation weakening. PM does not pre-approve the reclassification.
- **唯一下一 READY：`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE = READY`**. Prompt: `governance/prompts/CORE_BACKGROUND_TRUSTED_RETURN_RECOVERY_001_CORRECTIVE_001_INDEPENDENT_ACCEPTANCE_2026-09-28.md`.
- PM readiness: `governance/CORE_BACKGROUND_TRUSTED_RETURN_RECOVERY_001_CORRECTIVE_001_PM_REVIEW_READY_2026-09-28.md`.
- Until fresh IA PASS + separate PM integration: PR #264 merge, `CORE-RC-REFREEZE-003`, A-RERUN-004, persistence Corrective-003 resume, B release/run, Resident C, evaluator and C15 close remain **BLOCKED**.
- Historical failed exact #258 `1ebf51c4...` and review-only IA fail #261 `b9d692dd...` remain immutable; no hash-swap.


## 当前控制入口 — 2026-09-28 TRUSTED-RETURN IA FAIL / CORRECTIVE-001 READY

- **`C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003 = FROZEN_WIP / BLOCKED_ON_CORE_TRUSTED_RETURN_RECOVERY`**。PR #254 已 **CLOSED / DRAFT / UNMERGED / FROZEN**。First scope-violating WIP `f7848952b6519fc40f50806f4a4d8d350ac0f38a` 修改了 `src/aios_core/runtime/turn_runtime.py`，违反 merged PM scope #255（persistence corrective 不得修改 Core），因此该 SHA = **SCOPE_VIOLATION / NOT_A_CANDIDATE**。历史 WIP/red/green CI 全部保留，不得 rewrite。
- #255 的 narrowed scope 继续有效：C002 reviewer 六 findings 历史保留；C15 release gate binding blockers 为 `001/002/004`，`003/005/006` 为 non-blocking hardening。当前新问题只来自 binding `002` 的合法闭合路径。
- **Core gap**：accepted Core 可 `stage_exact_background_response(...)`，但只接受已经存在 trusted-return authenticity proof 的 exact response；私有 `_capture_trusted_response_return(...)` 明确只属于正常 trusted provider-return callback，recovery caller 不得调用签名 authority。Later-round provider 已提交/返回但 crash 发生在 trusted-return receipt 持久化前时，当前 Core 没有既避免 provider redispatch、又保持 non-forgeable authenticity 的合法 continuation path。
- `f784...` 新增 public `stage_trusted_returned_background_response(...)` 允许 recovery API 接收外部 directive bytes 后调用私有 receipt minting authority；这会改变已接受的 provider-return trust boundary，不允许作为 persistence harness 修复。
- **`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001 = FAILED EXACT CANDIDATE / CORRECTIVE REQUIRED`**。PR #258 remains **OPEN / UNMERGED / PINNED** at failed exact candidate `1ebf51c4cb905e2a2578a09b64007b50bca0d4ac`; do not merge or hash-swap. Fresh IA review-only PR #261 @ `b9d692ddca055b13fb29e646186e929a08bf8955` is OPEN / DRAFT / UNMERGED and reports `ACCEPTANCE_FAIL / blocker=1`. Author greens (R5 24/24, focused 99/99, full 816/816) remain historical evidence and do not override the blocker.
- R5 binding clarification：exact authenticated directive may be mechanically/idempotently replayed when only metering is durable, but provider request, meter row, capability side effect, semantic/World write, assistant output/delivery and terminal ACK must each remain exactly once. Stronger durable output/delivery receipts must short-circuit runtime replay. No new generic post-application checkpoint is required by this task。
- **Fresh IA verdict：`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-INDEPENDENT-ACCEPTANCE = DONE / ACCEPTANCE_FAIL / blocker=1`**。Binding blocker `IA-BLK-TRUSTED-RETURN-001`：R5-C exact replay was repaired only for `execution.task.create`; at least five other reachable side-effecting capability families reject legitimate identical recovery replay (`propose_goal`, `form_event`, `propose_entity`, `propose_dimension`, `propose_cognitive_policy`). No duplicate durable effect is created; instead the logical turn cannot exactly-once converge. `commit_claim` passes only because it already had a pre-existing exact-retry guard.
- **当前唯一下一 READY：`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001 = READY`**。Scope is only the one IA blocker: make R5-C exact replay converge across the complete reachable side-effecting capability surface without weakening exact request-fingerprint conflicts, trusted-return authenticity, or R1-R5 invariants. First freeze a capability replay matrix and baseline RED against failed exact `1ebf51c4...`; then implement the smallest reusable/per-service correction. Prompt: `governance/prompts/CORE_BACKGROUND_TRUSTED_RETURN_RECOVERY_001_CORRECTIVE_001_2026-09-28.md`. 以下继续 **BLOCKED**：Corrective-001 Independent Acceptance、PR #258 merge、`CORE-RC-REFREEZE-003`、Corrective-003 resume、`C15-RCC-RES-B-RELEASE-003`、Resident A/B/C、evaluator、closure。
- PR #254 PM STOP comment：`5863009559`。
- **Mandatory post-Core sequence**：`CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001` engineering -> fresh Independent Acceptance -> PM integration -> `CORE-RC-REFREEZE-003` -> fresh Independent Acceptance -> fresh `C15-RCC-RES-A-RERUN-004` on the new RC -> fresh Independent Acceptance -> governance re-release of frozen `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003`. Once the new Core is integrated, A-003 remains historical evidence for the prior Core/RC only and MUST NOT be reused as the B launch lineage.
- #254 在 PM STOP 后仍被并行工程窗口继续推进；关闭时 branch head = `a2d815c9f5154d87a56b152ed7cf5d1eb1baaaae`，该 head 仍含 `src/aios_core/**` diff，全部视为 **unauthorized WIP / NOT_A_CANDIDATE**。关闭 PR 仅停止 active PR/CI flood，不删除 branch/history。

## 历史控制入口 — 2026-09-27 C15-RCC-RES-A-RERUN-003 INTEGRATED / C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 READY_TO_RESUME（已被上方 REVIEW_READY writeback supersede）

- `CORE-RC-REFREEZE-002 = DONE / ACCEPTED / INTEGRATED`（PM integration `PM_ACCEPTED / INTEGRATED`）。工程 PR #232 已通过标准 merge commit 合入 `main`：merge SHA = `4cadc1a8d7952363e213958c71a63ae7da93f615`（2026-09-27T11:45:35Z）。Pre-merge live main = `27a21db5b656d441248b9240020910b66a223830`；post-merge live main = `4cadc1a8d7952363e213958c71a63ae7da93f615`。
- Accepted exact RC candidate = `a93972c95356f46d20f5e9e7be82026fe84c0687`（parent `91c93c4eb818960f16b89ca74d16e8ede72fa797`，tree `66d89a0344b68520b840690c43aead629e9f7957`；pin comment `5855296310`；PM acceptance comment `5855536367`）。正式 frozen software 仍是 `27a21db5b656d441248b9240020910b66a223830`（不是 merge commit）；frozen Core tree `src/aios_core` = `a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6`；frozen tests tree = `92fcbcc5876833735fb3cb7c73a98c4a8a4a3541`；source manifest SHA256 = `34b3d8adfad376a9cd7170ebec3e6093d40444b03ffd61130ed79602e63e3883`；environment manifest SHA256 = `d52ba5458014f5828c432bfb2c8a8d28e36b38b9138236d2d178ea8b02904f53`。`27a21db -> a93972c` 与 `27a21db -> 4cadc1a8` 均为 `src/**` / `tests/**` / `pyproject.toml` ZERO DIFF；候选仅含 freeze evidence + governance + release packet + formal gate workflow。
- Fresh IA：`CORE-RC-REFREEZE-002-INDEPENDENT-ACCEPTANCE = ACCEPTANCE_PASS / blocker=0`。Durable review-only PR #233 @ `404925853f23f962265f048b094b58cf3ca5f97e`（保持 review-only / draft / open / unmerged）；正式报告 `reviews/CORE_RC_REFREEZE_002_INDEPENDENT_ACCEPTANCE_2026-09-27.md`。独立全量 `763 passed / 0 failed / 0 errors / 0 skipped in 234.73s`（CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2 / SQLite 3.50.4），与作者 formal gate run `36314755816`（JUnit 763/0/0/0）一致；自建 adversarial probes `17/17 PASS`（`833fdac6...` 11 passed + `e1b746b1...` 6/6 PASS）；`MERGE_REF_EQUIVALENCE PROVEN`（merge-ref `f9e5cdc6f4ec9b26be1722779fb7f7756389bdc9` tree == candidate tree，parents `[27a21db5, a93972c9]`，Core/tests 一致）。
- 新 canonical RC：frozen software `27a21db5...` / Core tree `a9618abe...`。旧 `CORE-RC-FREEZE-001`（`773876f9...` / `fe77f8a0...`）保留为历史 prior RC。`A-RERUN-002 = HISTORICAL_FOR_PRIOR_RC_ONLY`；`FRESH_A-RERUN-003_REQUIRED`；严禁把 A-002 evidence hash-swap 到新 RC。
- **`C15-RCC-RES-A-RERUN-003 = DONE / ACCEPTED / CANONICAL_FOR_NEW_RC`**（PM integration `PM_ACCEPTED / INTEGRATED`）。Resident evidence PR #235 exact `5b6367406c13ea9450b7b2598a5813a64129cbd7`（parent `7549322681ada61ab6d3c6eee5082acc00a658d6`，tree `6402fff8b0c8c834e7b3f6b5d7c7427d0f846933`，pin comment `5856077069`）保持 **OPEN / UNMERGED / PINNED**（evidence-only, 122 files, +30247/-0）。Fresh Resident A run: cursor 1..13 strict sequential, 13/13 durable ACK, cursor 14 NOT REVEALED, World 42 / index 42 / lag 0, fresh World/index/release-state/session (`resident-a003-0f5ffeff-3d67-4e06-be86-aa83bbea6ad0` / `a003run-01c3a44b-35b2-4344-a62c-9bd772913308`), A-002 not reused.
- Fresh IA：`C15-RCC-RES-A-RERUN-003-INDEPENDENT-ACCEPTANCE = ACCEPTANCE_PASS / blocker=0`。Durable review-only PR #236 @ `9fa49c318a0a8f7ce73921bc86de696e166e67f3`（报告 `reviews/C15_RCC_RES_A_RERUN_003_INDEPENDENT_ACCEPTANCE_2026-09-27.md`）→ merge `0684b458fa947f3e5c04d79bd6988dedede19608`（pre-merge live main `7549322681ada61ab6d3c6eee5082acc00a658d6`, review merge parents `[7549322...,9fa49c31...]`）。25 named gates PASS, Q1 bridge `PROVEN` (25/25 digests, limitation preserved), Q2 SQLite `NON_MATERIAL / ACCEPTABLE` (3.53.4 vs 3.50.4 observation, no SQLite pin), cursor-1 double recovery `NON_BLOCKING / LEGITIMATE`, probe `14/14 PASS` (harness `8c0033a5619f7eeaec8826562fc43bc248359be02aaa4539ca04189333485b40`, enumeration `682c3a14bf0cdb11c5a46e1fc7ffd6d065a70c9f970c8767207997ac8620a1f2`, history 0/14,6/14,10/14,14/14 preserved).
- 集成收据：`governance/C15_RCC_RES_A_RERUN_003_ACCEPTANCE_INTEGRATION_RECEIPT_2026-09-27.md`（PM spot-checked digests World `3de9e73883f...862ad`/index `38193612a9ff...e48d4`/backup `6d442d5a...afa95f`/release `7728b12e0ff5...3849e9`/manifest `34bd0be959a9...22eb84`/SHA256SUMS `81d92567551d...459426`）。
- （历史快照：resume 阶段曾设 `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 = READY_TO_RESUME_FROM_FROZEN_WIP`（resume preserved frozen WIP from #216 @ `6db057a5fddbaf403be8377682b81219a074fef6` on now-accepted Core/RC/A-003 chain），IA 曾保持 `BLOCKED`。现已被顶部 REVIEW_READY 控制入口 supersede；当前唯一 READY = `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`。）
- Known limitation 原样保留：«持有底层 trusted store/runtime 对象的进程内 trusted code 可以调用内部 receipt minting path，或直接读取 SQLite 中保存的 HMAC authority secret。»裁决 `NON_BLOCKING TRUST-ROOT LIMITATION`。
- 集成收据：`governance/CORE_RC_REFREEZE_002_INTEGRATION_RECEIPT_2026-09-27.md`。
- `CORE-BACKGROUND-RESPONSE-RECOVERY-001 = DONE`；`CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002 = DONE / ACCEPTED / INTEGRATED`。
- 候选 PR #219 已正式完成 PM integration，通过标准 merge commit 合入 `main`：merge SHA = `89200c55e63ce2251ecc236e25d16c57d998f93c`。Pre-merge live main = `e1b10d86969ada6dd35598bee21cc75579aa92a1`；post-merge live main = `89200c55e63ce2251ecc236e25d16c57d998f93c`。
- Accepted tested exact implementation identity 始终绑定并记录为：`227327c657788efb1b5de1bc26e69c35c900a85e`（parent `72aed7eddf22d0d7f05e53bb3bd46ed28554f7fc`，tree `01dfa445414543aab41e1b74b813bbff80b21c5c`）。Integration-preparation head `3538cc763d636cdbb404721c028b99db7ad23e0b`（parents `227327c...` + `e1b10d8...`）经严格验证：相对 accepted exact 保持 `src/**`、`tests/**`、`.github/workflows/**` 全量 ZERO DIFF，且祖先关系完整。
- 合后验证：`git merge-base --is-ancestor 227327c... 89200c5...` 证明 accepted exact 已进入 post-merge main 历史；post-merge `src/aios_core` tree = `a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6` 与 accepted exact 完全一致；frozen authenticity probe blob `6f0c3850368475e166d28d0a6df4b86b610d2c60`（SHA256 `35cba59f318b752ed872821961296f35810443c61db6fd98c8c8f5eee4215225`）保持不变。
- 历史候选链完整保留：original `3f9ec00d...` 为 ACCEPTANCE_FAIL（blocker=2: IA-BLK-001 跨 work 移植, IA-BLK-002 JSON 重复键覆盖）；corrective-001 `030acbfe...` 为 ACCEPTANCE_FAIL（blocker=1: provider 返回字节防篡改认证缺失）；corrective-002 `227327c...` 为 ACCEPTANCE_PASS（blocker=0）。
- Durable Fresh IA 证据链：review-only PR #230 @ `2c846baa53c113aef7c9be88da27099c6926b2fb` ＋ PR #219 comment `5854998774`；正式报告 `reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_002_INDEPENDENT_ACCEPTANCE_2026-09-27.md`；frozen 12/12 GREEN，adversarial rev2 49/49 GREEN（manifest `8ebdce5dbe8bb10e3cc6210399279cc679393d9f70e5b5fd878f0f91f028874e`），全量 `763 passed in 252.50s`（CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2）。Residual trust-root limitation 判定保持 `NON_BLOCKING TRUST-ROOT LIMITATION`。
- CI 诚实裁决：PR #219 上的 15 项 workflow SUCCESS（含 `p16-convergence-gate` run `36312752392` full-core-regression 3m20s PASS）；2 项历史 fixture zero-Core-diff guard RED 诚实保留并判定为 `KNOWN FIXTURE-SCOPE / BRANCH-SHAPE NON-BLOCKING RED`（`c15-rcc-fixture` run `36312752129` 与 `c14-semantic-repair-fixture` run `36312752208`，其实体测试与回归全部 SUCCESS，仅因真实 Core 修改触发 fixture 任务的 zero Core diff 断言）。
- 集成收据：`governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_002_INTEGRATION_RECEIPT_2026-09-27.md`。
- **`CORE-RC-REFREEZE-002 = DONE / ACCEPTED / INTEGRATED`**. Engineering PR #232 merged as `4cadc1a8d7952363e213958c71a63ae7da93f615`. Frozen software = `27a21db5b656d441248b9240020910b66a223830`; Core tree = `a9618abe0b3d4ac3b08bd23dbd58f3e3f97e05d6`; tests tree = `92fcbcc5876833735fb3cb7c73a98c4a8a4a3541`. Fresh IA `ACCEPTANCE_PASS / blocker=0` (PR #233). **A-003已完成：`C15-RCC-RES-A-RERUN-003 = DONE / ACCEPTED / CANONICAL_FOR_NEW_RC`** (PR #235 `5b636740...` OPEN/UNMERGED/PINNED, IA PR #236 `9fa49c31...` → `0684b458...` PASS).（历史快照：当时 Next task = `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001` (READY_TO_RESUME)；现已被顶部 REVIEW_READY 控制入口 supersede，当前唯一 READY = `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`。）

- PM live verification: engineering PR #219 is OPEN / UNMERGED; tested exact candidate = `3f9ec00d0fa283bc5294574d6da1e84d654d6645`, parent = `a310bf1202bf41644c2f3e25798053a6636e14be`, exact tree = `4e9e3a5685373f46ba56d51259f39af710a3cf53`; PR evidence-only head = `b82ae25bcbef0d1d81cc3b7e5f303d75a4f0b507`. `3f9ec00d... -> b82ae25b...` has no `src/**` or `tests/**` changes. Earlier local-only candidate `2b8242f7834fb34a0ce90a585f847bfa7505fe1e` was never published to GitHub and is NOT the acceptance candidate; do not conflate the two implementations.
- PR #219 remote CI on the evidence-only PR head/merge context: P16/runtime/fused/C09/P15/P9-P14/constitutional/C14/core-scale are SUCCESS. `c14-semantic-repair-fixture` run `36234237680` and `c15-rcc-fixture` run `36234237724` are RED only at their fixture-task zero-Core-diff scope guards because this is a genuine Core-change task; their substantive fixture/regression steps passed. Preserve these reds honestly; IA must classify them, not relabel them green.

- 接任 PM 依 #128 治理接手；接手与 live 复核：`governance/AIOS_CORE_PM_TAKEOVER_S0_REVERIFICATION_2026-09-24.md`。
- **派工基线 = live main `079d7516f195cf6973933acc8cd057d59adc3a9f`**（其后仅治理/审查文档变更）；`CORE-OPERATOR-001` 集成点 = `e72a63874ed2c28798b00cec51f191caf1594a00`；Core tree 自审计以来始终 `7db4f72e7b3c29c74082f9984141159f8f1d6071`。每个新窗口仍须自行重取 live main，不得把本 SHA 当永久施工基线。
- `CORE-BASELINE-001 = DONE（re-verified）`：S0 裁决成立；dev 基线前移至 `e72a63874e...`；历史 pin #117/#121/#125/#126 不变；fresh A 仅在 RC-FREEZE 后。
- `CORE-OPERATOR-001 = DONE`：独立验收 #135（ACCEPTANCE_PASS，0 blocker）`fe6f1740eb`（05:08:01Z）先合，候选 #131 `e72a63874e`（05:08:07Z）后合；报告 `reviews/CORE_OPERATOR_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`。
- `CORE-GAP-AUDIT-001 = DONE`（#132 合 `bc4bf735...`）；RC blockers = CG-001/002/003；14 ALREADY_FIXED / 7 NOT_REPRODUCED / 6 OUT_OF_SCOPE 不得无依据重开。
- **S2 已触发强制串行化**：PR #145（FIX-001）证明完整 CG-001 closure 必须在 `run_wake` / `run_periodic_review` 建立 historical read cutoff，已跨入 FIX-002 的 symbol ownership。依原 parallelism ruling 的 stop-and-report 条款，PM 裁决 **FIX-002 先完成/独立验收/集成，FIX-001 保留现场后从新 main rebase 继续**。绑定裁决：`governance/AIOS_CORE_S2_SERIALIZATION_RULING_2026-09-24.md`。FIX-002 已独立验收 #154 PASS 并集成 #143，merge `3d980fad...`；FIX-001 draft #145 解除冻结，必须从 live main rebase 后继续既有 WIP；FIX-003 的 FIX-002 前置已满足，现 READY。后续符号级并行边界见 `governance/AIOS_CORE_S2_POST_FIX002_PARALLELISM_RULING_2026-09-24.md`。
- PR #136（pelican 动画）= EXCLUDED，永不合入；分支保留，不作关闭/删除（计划未授权）。
- PM 补充（`governance/CORE_OPERATOR_001_INTEGRATION_RECEIPT_2026-09-24.md`）：合后 p16-convergence-gate run `35958610555` @ `e72a6387` SUCCESS；PR #130（`core/operator-001-20260924-sol` @ `16eb1d40`，同 Task 竞争候选、未经独立验收）= **SUPERSEDED / NOT INTEGRATED**，保留不合并；`core-gap-fix-001/002` 分支停在 `27135e39`、零提交，无施工现场。
- Gap fix 独立验收统一提示词：`governance/prompts/CORE_GAP_FIX_ACCEPTANCE_2026-09-24.md`（每个候选另开不同 reviewer 窗口）。
- 集成时复核（由执行两次 merge 的集成 PM 窗口做，不只读验收报告）：exact head 未漂移；4 条 CI 经 API 复核（`35955458275`/`35955458266` 复现 FAILURE，`35955695487`/`35955695492` exact-head SUCCESS）；候选 26 文件、`src/` 0 文件；本地在 repro commit `3865da88` 真实复现三项失败，在 accepted head 与 merge 结果各 `632 passed`（与 CI 计数一致）。细节见收据 §5。
- 诚实限制：本地复算用 CPython 3.11.2（低于 >=3.12 gate），仅佐证；`gh run rerun` 与 `workflow_dispatch` 被平台 403 拒绝（未绕权限），合后证据以 push run `35958610555` 为准；作者与验收为不同窗口但同一 GitHub 账号，无跨账号 APPROVE，不宣称账号级独立。
- **PM 写回并发规则（新增，因本日出现两个 PM 窗口并行写回同一状态）**：同一时刻只保留**一个**集成 PM 写回入口。先合入者为准，后到窗口必须**对账合并**已合入内容，不得覆盖、不得新建同事件的第二份收据/第二条控制入口。本日 #137 / #136 / #138 三份 PM 写回已在此合并，单一收据 = `governance/CORE_OPERATOR_001_INTEGRATION_RECEIPT_2026-09-24.md`。
- S2 两个并行修复窗口的写入范围隔离与 operator 面禁改规则见 `governance/AIOS_CORE_GAP_DISPATCH_2026-09-24.md` 的 "Dispatch update — 2026-09-24"。
- **`CORE-CI-FIX-001 = DONE`**：首轮 review #150 对 head `1896b3e5...` 正确给出 ACCEPTANCE_FAIL（历史 blocker 保留）；corrective review #156 对 exact head `1eb24e101cdb1579c22c69b435cf9f79a3c359ad` 给出 ACCEPTANCE_PASS / 0 blockers；#156 先合 `f3d20c22...`，随后 #146 以 pinned head 合入 `c3ec42214db57864f7951e28b75811b10db8be21`。收据：`governance/CORE_CI_FIX_001_INTEGRATION_RECEIPT_2026-09-24.md`。PR #144 继续 SUPERSEDED / NOT INTEGRATED。历史派工说明：**（release/CI 基础设施）：`c15-rcc-fixture-mechanical-gate` 与 `semantic-repair-mechanical-gate` 的 "prove zero Core diff" 步骤在浅克隆上 `git` 自身 exit 128，随分支形状时红时绿（#133 红 / #137 绿 / #138 #139 红），不是策略违规。发现与 PM 裁决：`governance/AIOS_CORE_CI_FINDING_001_2026-09-24.md`；提示词：`governance/prompts/CORE_CI_FIX_001_2026-09-24.md`。不阻塞 FIX-001/002，但 **必须在 `CORE-RC-FREEZE-001` 之前关闭**。
- #138/#139 两条红检查登记为 **INFRASTRUCTURE_FAILURE**，不登记为通过、也不登记为已接受的违规；PM 已用直接证据独立验证不变式成立（`git diff e72a638..main -- src/` 为空，Core tree 仍 `7db4f72e`），未绕过分支保护（该两项非 required）。
- `CORE-HEADLESS-001 = DONE`；`CORE-RECOVERY-001 = DONE`；`CORE-SCALE-001 = DONE`；旧 RC freeze / A-002 / B preflight/release 历史证据均保留。RERUN-002 因 ephemeral `/tmp` state loss 为 `FAILED / INFRASTRUCTURE_STATE_LOSS / NON-CANONICAL`，旧 identity 永久退休。Persistence corrective 的 reply-staged crash 红证据已冻结在 draft PR #216。PR #219 corrective-001 exact `030acbfe...` fresh IA 为 `ACCEPTANCE_FAIL / fresh blocker=1`：relay binding 能阻止跨 work transplant，但 relay id 暴露给 provider handler，且 staged response 只校验 caller 可自算的 directive fingerprint，因此不能证明 exact bytes 真由 trusted provider/relay return path 产生；PM 已在远端 exact 源码独立确认该 provenance/authenticity gap。Corrective-002 tested exact `227327c...` fresh IA 已 `ACCEPTANCE_PASS / blocker=0`（durable evidence：review-only PR #230 @ `2c846ba...` ＋ PR #219 comment `5854998774`）；PR #219 integration governance conflict 已机械解决（zero `src/**` / `tests/**` / workflow diff），且 PR #219 已正式通过标准 merge commit 合入 main（merge SHA `89200c55e63ce2251ecc236e25d16c57d998f93c`，收据 `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_002_INTEGRATION_RECEIPT_2026-09-27.md`）。`CORE-BACKGROUND-RESPONSE-RECOVERY-001 = DONE`；`CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002 = DONE / ACCEPTED / INTEGRATED`。`CORE-RC-REFREEZE-002 = DONE / ACCEPTED / INTEGRATED`（PR #232 merged `4cadc1a8...`）。**A-003已完成：`C15-RCC-RES-A-RERUN-003 = DONE / ACCEPTED / CANONICAL_FOR_NEW_RC`**（PR #235 `5b636740...` OPEN/UNMERGED/PINNED, IA PR #236 `9fa49c31...` → `0684b458...` PASS; receipt `governance/C15_RCC_RES_A_RERUN_003_ACCEPTANCE_INTEGRATION_RECEIPT_2026-09-27.md`）。（历史快照：当时唯一下一 READY 任务为 `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 = READY_TO_RESUME_FROM_FROZEN_WIP`（resume #216 `6db057a5...`）。现已被顶部 REVIEW_READY 控制入口 supersede；当前唯一 READY = `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE`。）`B-RELEASE-003 → B-RERUN-003 → B-ACCEPT-003` 仍 BLOCKED；严禁直接跳到 RELEASE-003。

## 历史控制入口 — 2026-09-24 CORE-GAP-AUDIT ACCEPTED / S1-S2 ACTIVE

- 独立 Core gap audit PR #132 已由 PM 接受并正常合入；merge = `bc4bf735e15c5c0787fdc533fe3f10d0e17fdac3`，审计 Core tree = `7db4f72e7b3c29c74082f9984141159f8f1d6071`。
- 审计正式确认 3 个 RC blocker：`CG-001 RUNTIME_TEMPORAL_READ_CUT`、`CG-002 BACKGROUND_MODEL_EXECUTION_IN_DOUBT`、`CG-003 USER_TURN_IN_DOUBT_RECOVERY`。其余裁决：14 ALREADY_FIXED / 7 NOT_REPRODUCED / 6 OUT_OF_SCOPE，不得无依据重开。
- `CORE-GAP-FIX-001` 与 `CORE-GAP-FIX-002` 可由两个独立工程窗口并行施工；`CORE-GAP-FIX-003` 先 BLOCKED，待 FIX-002 独立验收并集成后从当时 live main 开始。
- `CORE-OPERATOR-001` 工程候选已在 PR #131 @ `0e1d69eebc801278f93ccc1941b8f066a4ea09ef` 进入 **GATE / REVIEW_READY**；仍必须由不同 Independent Reviewer 验收后才能 PM merge。
- historical #117 A 仍仅是 frozen-Core accepted evidence；新 RC 的 fresh A/B/C 只能在所有 S2 工程独立验收并 `CORE-RC-FREEZE-001` 后开始。当前禁止 Resident。
- PM dispatch：`governance/AIOS_CORE_GAP_DISPATCH_2026-09-24.md`。
- UI / Launcher / 数字人 / 动画 / 硬件 / Android ROM 继续排除。

### 当前优先队列（唯一正式派工表）

| Task ID | 状态 | Owner / 放行出口 |
|---|---|---|
| CORE-BASELINE-001 | **DONE（re-verified）** | S0 ruling 已落 main；接任 PM 于 `e72a63874e...` 复核成立（governance/AIOS_CORE_PM_TAKEOVER_S0_REVERIFICATION_2026-09-24.md） |
| CORE-OPERATOR-001 | **DONE** | 独立验收 #135 先合（fe6f1740eb）→ 候选 #131 后合（e72a63874e）；报告 reviews/CORE_OPERATOR_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md |
| CORE-GAP-AUDIT-001 | **DONE** | PR #132 已接受并合入；报告 `reviews/CORE_GAP_AUDIT_001_2026-09-24.md` |
| CORE-GAP-FIX-001 | **DONE** | 历史 #161 ACCEPTANCE_FAIL 保留；corrective #171 ACCEPTANCE_PASS / 0 blockers；#145 exact `a56f113ace3c5e01af3acb724468bc2e0fbd4e98` merged as `d97a1bfa527caadb4ab22d232fd627c0483e02d8`；receipt `governance/CORE_GAP_FIX_001_INTEGRATION_RECEIPT_2026-09-24.md` |
| CORE-GAP-FIX-001-CORRECTIVE-001 | **DONE** | corrective red `e19bc904...` → accepted exact `a56f113a...`；review #171 ACCEPTANCE_PASS；candidate integrated in #145 merge `d97a1bfa...` |
| CORE-GAP-FIX-002 | **DONE** | Independent review #154 ACCEPTANCE_PASS / 0 blockers；candidate #143 exact `c5382a1653...` merged as `3d980fadf6beefcdd02ff4367ba834a5b013d871`；receipt `governance/CORE_GAP_FIX_002_INTEGRATION_RECEIPT_2026-09-24.md` |
| CORE-CI-FIX-001 | **DONE** | 首轮 #150 ACCEPTANCE_FAIL 历史保留；corrective #156 ACCEPTANCE_PASS / 0 blockers；#146 exact `1eb24e101cdb1579c22c69b435cf9f79a3c359ad` merged as `c3ec42214db57864f7951e28b75811b10db8be21`；receipt `governance/CORE_CI_FIX_001_INTEGRATION_RECEIPT_2026-09-24.md` |
| CORE-CI-FIX-001-CORRECTIVE-001 | **DONE** | blocker `CORE-CI-FIX-001-ACCEPT-BLOCKER-001` closed by the accepted corrective; historical fail evidence remains unchanged |
| CORE-GAP-FIX-003 | **DONE** | 历史 #162 ACCEPTANCE_FAIL 与 #174 REBASE_REVALIDATION_REQUIRED 保留；post-FIX001 review #178 ACCEPTANCE_PASS / 0 blockers；#157 exact `7c0c51a7e9cda41a5aa61357ebba96955948a4a7` merged as `78c103322b14c60cabf92174b0b5a7385752d758`；receipt `governance/CORE_GAP_FIX_003_INTEGRATION_RECEIPT_2026-09-24.md` |
| CORE-GAP-FIX-003-CORRECTIVE-001 | **DONE** | corrective pre-FIX001 `ac8d5a43...` → post-FIX001 exact `7c0c51a7...`；13/13 workflows SUCCESS，P16 662 pass markers；final review #178 ACCEPTANCE_PASS；candidate integrated in #157 merge `78c10332...` |
| CORE-HEADLESS-001 | **DONE** | 历史 #185 ACCEPTANCE_FAIL 保留；corrective review #189 ACCEPTANCE_PASS / 0 blockers；#181 tested corrective exact `16e983a536b124ddb600981fc16326d9db54358f` + evidence-only `f25218aa...` merged as `6ccd79d93f8fa8845bf392bd3c1ef0641ad1cde6`；receipt `governance/CORE_HEADLESS_001_INTEGRATION_RECEIPT_2026-09-24.md` |
| CORE-HEADLESS-001-CORRECTIVE-001 | **DONE** | new exact `16e983a5...`；fresh probe #188 PASS；review #189 ACCEPTANCE_PASS；candidate integrated with #181 merge `6ccd79d9...` |
| CORE-RECOVERY-001 | **DONE** | Independent review #195 ACCEPTANCE_PASS / 0 blockers；#191 tested exact `58b6b5e2e653e258e778a0f2dd3d77978cd585ff` + evidence-only `f90b9360...` merged as `17e3807024359e990890ff4c249e55da93886475`；receipt `governance/CORE_RECOVERY_001_INTEGRATION_RECEIPT_2026-09-24.md` |
| CORE-SCALE-001 | **DONE** | Independent review #200 ACCEPTANCE_PASS / 0 blockers；#197 tested exact `ba23767d4c1565fbe494419dd01c32123495884c` + evidence-only `2c8f16fe...` merged as `46c7cf9771274559b42dade9359e2e2cae5f245f`；receipt `governance/CORE_SCALE_001_INTEGRATION_RECEIPT_2026-09-24.md` |
| CORE-RC-FREEZE-001 | **DONE** | Independent acceptance #203 head `e622437489aac3de04570422043681ac731cf0a6` merged first as `85c0aba5fed826e5058bc8af59180c3d04a96eaa`；candidate #202 exact `b392f73f53180620842a1c25575a8a7567cc8773` merged second as `305aea162cfd53105179b63dd06704aa7bce3ccc`；frozen software `773876f9...` / Core tree `fe77f8a0...`；impact `FRESH_A_REQUIRED`；receipt `governance/CORE_RC_FREEZE_001_INTEGRATION_RECEIPT_2026-09-24.md`；post-REFREEZE-002 = historical prior RC；canonical RC 现为 `27a21db5...` / `a9618abe...`（见 CORE-RC-REFREEZE-002） |
| C15-RCC-RES-A-RERUN-002 | **DONE / ACCEPTED / HISTORICAL_FOR_PRIOR_RC_ONLY** | PR #207 ACCEPTANCE_PASS / blocker=0 merged `c1236bf2fd6ea259fe7d487c5ac0e96abd072141`；canonical evidence PR #205 exact `d17ae972ad1d312735c355f775ac024bc4cebdf7` remains OPEN / UNMERGED / PINNED；receipt `governance/C15_RCC_RES_A_RERUN_002_ACCEPTANCE_INTEGRATION_RECEIPT_2026-09-25.md`；post-REFREEZE-002: evidence valid for prior RC `773876f9...` / `fe77f8a0...` only；must not be hash-swapped to new RC |
| C15-RCC-RES-A-RERUN-002-ACCEPT-001 | **DONE** | review-only PR #207 merged；report `reviews/C15_RCC_RES_A_RERUN_002_INDEPENDENT_ACCEPTANCE_2026-09-25.md` |
| C15-RCC-RES-B-PREFLIGHT-002 | **DONE / ACCEPTED** | PR #209 exact `aab3a30cc48e8c7041ef4b37e0e5f379c3060c93`；PM review `5323959000`；Independent Acceptance `5323972504` = PASS / blocker=0；merge `65e6e8266bb0541d624eb8e5bba825b91145564f`；receipt `governance/C15_RCC_RES_B_PREFLIGHT_002_ACCEPTANCE_INTEGRATION_RECEIPT_2026-09-26.md` |
| C15-RCC-RES-B-RELEASE-002 | **DONE / RELEASED** | release record `governance/C15_RCC_RES_B_RELEASE_002_RELEASE_RECORD_2026-09-26.md`；fresh release validation `36216433668` attempt 2 SUCCESS；exact run/session `c15-rcc-res-b-rerun-002-65e6e826` / `c15-rcc-res-b-session-002-65e6e826`；release review 未运行真实 Resident B、未向 Resident/model 暴露真实 cursor14 payload |
| C15-RCC-RES-B-RERUN-002 | **FAILED / INFRASTRUCTURE_STATE_LOSS / NON-CANONICAL** | cursor14 已 reveal+ingest+production dispatch；无 Resident semantic reply/capability/ACK；canonical /tmp run root 被平台重启销毁。旧 run/session 永久退休，禁止 replay/rewind 冒充原 run。incident + PM ruling 已落库。 |
| C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 | **FAILED EXACT CANDIDATE / CORRECTIVE REQUIRED** | PR #216 tested exact `63ca592359c7e3fd71d6cc4ba349949e4f0b80e3` remains OPEN / DRAFT / UNMERGED / PINNED. IA source-confirmed blockers: `IA-BLK-PERSIST-001` remote durability absent from normal K1-K5 production path; `IA-BLK-PERSIST-002` sealed generation chain not verified by reopen/reattach. Stage A/B completed-cursor proof is preserved but is insufficient for mid-cursor environment-loss contract. |
| CORE-BACKGROUND-RESPONSE-RECOVERY-001 | **DONE** | PR #219 merged as `89200c55e63ce2251ecc236e25d16c57d998f93c`. 历史候选链完整保留：original tested exact `3f9ec00d0fa283bc5294574d6da1e84d654d6645` (blocker=2) 与 corrective-001 `030acbfe...` (blocker=1) 均为 ACCEPTANCE_FAIL；corrective-002 tested exact `227327c657788efb1b5de1bc26e69c35c900a85e` fresh IA ACCEPTANCE_PASS / blocker=0，通过 integration-preparation head `3538cc763d636cdbb404721c028b99db7ad23e0b`（zero Core/test/workflow diff）集成合入 main。集成收据：`governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_002_INTEGRATION_RECEIPT_2026-09-27.md`。 |
| CORE-BACKGROUND-RESPONSE-RECOVERY-001-INDEPENDENT-ACCEPTANCE | **DONE / ACCEPTANCE_FAIL** | blocker=2: exact response can transplant across work/work-kind/subject; duplicate JSON semantic keys are accepted by last-key-wins parsing. Reviewer-local evidence commit `5c59f17658524c0ad23f409a8c108402cea34452` was not pushed due missing credentials; PM source revalidation confirms both root causes. |
| CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-001 | **ACCEPTANCE_FAIL / CORRECTIVE_REQUIRED** | PR #219 historical candidate. Tested exact `030acbfe2d935dfc166ff7a9a1760b6ddd46d42d`; evidence-only head `a1c6e74de71f783951f2772e2f065880d7146ec5`; fresh IA blocker=1: relay/request binding does not authenticate provider-returned bytes. PM source revalidation confirmed. Adjudication: `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001_ACCEPTANCE_FAIL_ADJUDICATION_2026-09-27.md`. Author candidate report (preserved from PR #219 branch): `reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_001_CANDIDATE_REPORT_2026-09-27.md`. |
| CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE | **DONE / ACCEPTANCE_FAIL** | fresh blocker=1: caller with target relay id can forge different directive + self-computed fingerprint and pass current staging authenticity checks. Reviewer reported 30 fresh probes / 148 focused PASS / 735 full PASS under Python 3.11.2; local review artifact remains UNPUBLISHED. Python 3.11 full-suite count is not formal Core gate evidence. PM independently source-confirmed the blocker at remote exact `030acbfe...`. |
| CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002 | **DONE / ACCEPTED / INTEGRATED** | PR #219 accepted exact `227327c657788efb1b5de1bc26e69c35c900a85e` (parent `72aed7ed...`, tree `01dfa445...`); fresh IA `ACCEPTANCE_PASS / blocker=0` (frozen 12/12, adversarial rev2 49/49, full 763 passed, CPython 3.12.14); durable review evidence PR #230 @ `2c846baa53c113aef7c9be88da27099c6926b2fb` + PR #219 comment `5854998774`; integration head `3538cc7...` merged into main as `89200c55e63ce2251ecc236e25d16c57d998f93c`. Receipt: `governance/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_002_INTEGRATION_RECEIPT_2026-09-27.md`. |
| CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE | **DONE / ACCEPTANCE_PASS** | blocker=0: frozen 12-probe 12/12 GREEN (blob `6f0c3850...` unchanged); adversarial rev2 49/49 GREEN; focused/trusted-return/recovery GREEN; full `763 passed in 252.50s` (CPython 3.12.14 / Pydantic 2.13.5 / pytest 8.4.2). Historical IA-BLK-001 / IA-BLK-002 / corrective-001 provenance blocker all CLOSED with no regression. Durable evidence: review-only PR #230 @ `2c846baa53c113aef7c9be88da27099c6926b2fb` (report `reviews/CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_002_INDEPENDENT_ACCEPTANCE_2026-09-27.md`) + PR #219 comment `5854998774`. PASS applies only to tested exact `227327c...`. |
| CORE-RC-REFREEZE-002 | **DONE / ACCEPTED / INTEGRATED** | PR #232 exact `a93972c95356f46d20f5e9e7be82026fe84c0687` (parent `91c93c4e...`, tree `66d89a03...`) merged as `4cadc1a8d7952363e213958c71a63ae7da93f615`；frozen software `27a21db5...` / Core tree `a9618abe...` / tests tree `92fcbcc5...`；fresh IA PR #233 `ACCEPTANCE_PASS / blocker=0` (independent 763/0/0/0, adversarial 17/17, merge-ref equivalence proven)；receipt `governance/CORE_RC_REFREEZE_002_INTEGRATION_RECEIPT_2026-09-27.md` |
| CORE-RC-REFREEZE-002-INDEPENDENT-ACCEPTANCE | **DONE / ACCEPTANCE_PASS** | blocker=0；review-only PR #233 @ `404925853f23f962265f048b094b58cf3ca5f97e` (OPEN / DRAFT / UNMERGED, never merged as implementation)；report `reviews/CORE_RC_REFREEZE_002_INDEPENDENT_ACCEPTANCE_2026-09-27.md`；independent full regression 763/0/0/0 in 234.73s；adversarial 17/17；`MERGE_REF_EQUIVALENCE PROVEN`；known limitation `NON_BLOCKING TRUST-ROOT LIMITATION` preserved |
| C15-RCC-RES-A-RERUN-003 | **DONE / ACCEPTED / CANONICAL_FOR_NEW_RC** | PM integration `PM_ACCEPTED / INTEGRATED` (C15-RCC-RES-A-RERUN-003-PM-INTEGRATION). Resident evidence PR #235 exact `5b6367406c13ea9450b7b2598a5813a64129cbd7` (tree `6402fff8b0c8c834e7b3f6b5d7c7427d0f846933`, parent `7549322681ada61ab6d3c6eee5082acc00a658d6`, pin `5856077069`) remains **OPEN / UNMERGED / PINNED**. 1..13 strict sequential, 13/13 durable ACK, cursor14 NOT REVEALED, World 42 / index 42 / lag 0, fresh World/index/release-state/session (`resident-a003-0f5ffeff...` / `a003run-01c3a44b...`), A-002 not reused. IA PR #236 @ `9fa49c318a0a8f7ce73921bc86de696e166e67f3` → merge `0684b458fa947f3e5c04d79bd6988dedede19608`; `ACCEPTANCE_PASS / 0`. Receipt `governance/C15_RCC_RES_A_RERUN_003_ACCEPTANCE_INTEGRATION_RECEIPT_2026-09-27.md`. Historical A-002 PR #205 remains prior-RC evidence only. |
| C15-RCC-RES-A-RERUN-003-INDEPENDENT-ACCEPTANCE | **DONE / ACCEPTANCE_PASS** | review-only PR #236 @ `9fa49c318a0a8f7ce73921bc86de696e166e67f3` merged `0684b458fa947f3e5c04d79bd6988dedede19608`; report `reviews/C15_RCC_RES_A_RERUN_003_INDEPENDENT_ACCEPTANCE_2026-09-27.md`; `ACCEPTANCE_PASS / blocker=0`, `READY_FOR_PM_INTEGRATION`; 25 gates PASS, Q1 `PROVEN`, Q2 `NON_MATERIAL`, probe `14/14 PASS` (harness `8c0033a5...`, enumeration `682c3a14...`) |
| C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE | **DONE / ACCEPTANCE_FAIL / blocker=2** | Tested exact `63ca592359c7e3fd71d6cc4ba349949e4f0b80e3`; review-only PR #240 remote head `152be2406a05a7d4a2014e409d132a4c1126861b`; workflow `36337769581 = FAILURE`; PM independently source-confirmed `IA-BLK-PERSIST-001` and `IA-BLK-PERSIST-002`. Reviewer local `9d87018` unpublished and not cited as remote evidence. |
| C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-002 | **FAILED EXACT CANDIDATE / CORRECTIVE REQUIRED** | PR #251 tested exact `7b2556e738d9c9386ec21c13fec39400c87d0916` remains OPEN / DRAFT / UNMERGED / PINNED. Independent Acceptance found six source/reproduction-confirmed persistence blockers. Author formal/full-regression greens remain preserved historical evidence but do not constitute acceptance. |
| C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE | **DONE / ACCEPTANCE_FAIL / reviewer blocker=6 / PM binding blocker=3** | Historical reviewer verdict and exact failed candidate `7b2556e738d9c9386ec21c13fec39400c87d0916` preserved. PM scope adjudication classifies `001/002/004` as binding frozen-contract blockers; `003/005/006` as NON-BLOCKING HARDENING outside the C15 state-loss failure model. Local reviewer commit `fe881094...` remains NOT PUSHED. |
| C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003 | **READY（2026-09-29 governance re-release）** | **当前唯一下一 READY。** Fresh Resident A Corrective-003 IA `ACCEPTANCE_PASS / blocker=0` 已 PM integrated，`BLOCKED_ON_FRESH_RESIDENT_A_ACCEPTANCE` 解除，Mandatory post-Core sequence 步骤 8 生效。继承 narrowed scope（merged PM scope #255 + `governance/C15_RCC_RES_B_PERSISTENCE_SCOPE_ADJUDICATION_2026-09-28.md`）：`tools/c15_persistence/**` = C15 habitation/release persistence harness，**不是** AIOS Core product implementation；仅修 `C002-001 / C002-002 / C002-004`；禁止 `src/aios_core/**`。PR #254 保持 CLOSED / DRAFT / UNMERGED / FROZEN；WIP `f7848952...` 及含 Core diff 的后续 head = **SCOPE_VIOLATION / NOT_A_CANDIDATE**，不得直接续用为 candidate；历史 WIP/red/green 全部保留，不得 rewrite。 |
| CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001 | **FAILED EXACT CANDIDATE / CORRECTIVE REQUIRED** | Failed exact `1ebf51c4cb905e2a2578a09b64007b50bca0d4ac` / PR #258. Fresh IA = ACCEPTANCE_FAIL / blocker=1. Keep PR #258 unmerged and pinned; author greens remain historical only. |
| CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-INDEPENDENT-ACCEPTANCE | **DONE / ACCEPTANCE_FAIL / blocker=1** | Review-only PR #261 @ `b9d692ddca055b13fb29e646186e929a08bf8955`; tested exact `1ebf51c4...`; binding blocker `IA-BLK-TRUSTED-RETURN-001` = incomplete R5-C replay coverage across reachable side-effecting capabilities. |
| CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001 | **DONE / ACCEPTED / INTEGRATED** | 历史 READY 标记已于 2026-09-29 PM integration 同步退役（现唯一 READY = `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003`）。已接受/集成：candidate `a73e186d40688f5dc181b1128a62eff37a974409` → merge `f20f2edfa7af00d0286493fd15196ca9503bc315`；receipt `governance/CORE_BACKGROUND_TRUSTED_RETURN_RECOVERY_001_CORRECTIVE_001_INTEGRATION_RECEIPT_2026-09-28.md`。原 scope（只修 `IA-BLK-TRUSTED-RETURN-001`）与历史 RED 保留。 |
| CORE-BACKGROUND-TRUSTED-RETURN-RECOVERY-001-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE | **DONE / ACCEPTANCE_PASS** | `ACCEPTANCE_PASS / blocker=0`，canonical accepted IA evidence `eeda251e057e98b15a919694af4689786faf8c55`；supplemental post-acceptance evidence 无需 revalidation（`governance/CORE_BACKGROUND_TRUSTED_RETURN_RECOVERY_001_CORRECTIVE_001_IA2_SUPPLEMENTAL_EVIDENCE_ADJUDICATION_2026-09-28.md`）。 |
| CORE-RC-REFREEZE-003 | **DONE / ACCEPTED / INTEGRATED** | Frozen software `f20f2edfa7af00d0286493fd15196ca9503bc315`；Core tree `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`；tests tree `7e33b5ef8432370234965d3ccd61248c703c4019`；receipt `governance/CORE_RC_REFREEZE_003_INTEGRATION_RECEIPT_2026-09-28.md`。prior RC `27a21db5...` 转为 pre-fix Core 历史。 |
| CORE-RC-REFREEZE-003-INDEPENDENT-ACCEPTANCE | **DONE / ACCEPTANCE_PASS** | `ACCEPTANCE_PASS / blocker=0`；review-only PR #271（REVIEW-ONLY / DO NOT MERGE）；见 `CORE-RC-REFREEZE-003` 集成收据与控制入口。 |
| C15-RCC-RES-A-RERUN-004 | **DONE / ACCEPTED（Corrective-003 lineage）** | Fresh A 完成于 `C15-RCC-RES-A-RERUN-004-CORRECTIVE-003`：PR #296 exact `317316299c332d82e0cbd0431b5c7d50f391bc17`（tree `a64b60ad...`，parent `f7bcec4e...`）保持 OPEN / UNMERGED / EVIDENCE-ONLY。fresh IA `ACCEPTANCE_PASS / blocker=0`；accepted review `7b072340b527a864874208cd58152c9147328a18`（`review/c15-res-a-c003-ia`，DO NOT MERGE）；publication `EVIDENCE_PUBLICATION_RECOVERED / DURABLE`。A-003 不得 hash-swap 复用为新 lineage。 |
| C15-RCC-RES-A-RERUN-004-INDEPENDENT-ACCEPTANCE | **DONE / ACCEPTANCE_PASS** | `ACCEPTANCE_PASS / blocker=0` / `READY_FOR_PM_INTEGRATION`；accepted exact review `7b072340b527a864874208cd58152c9147328a18`（parent `e83b1aa7...`，tree `ae1e81be...`）；frozen `IA_REPORT.md` 保持不可修改；receipt `governance/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_ACCEPTANCE_INTEGRATION_RECEIPT_2026-09-29.md`。 |
| C15-RCC-RES-B-RELEASE-003 | **BLOCKED** | Waiting on Core trusted-return recovery -> fresh IA -> integration/re-freeze/lineage adjudication -> resumed scope-corrected persistence Corrective-003 -> fresh IA PASS. No Resident B release before that chain closes. |
| C15-RCC-RES-B-RERUN-003 | **BLOCKED** | 等 RELEASE-003；新的 fresh Resident B 仅运行 cursor14..22 |
| C15-RCC-RES-B-ACCEPT-003 → C / EVAL / CLOSE | **BLOCKED** | 等 B-RERUN-003 RUN_COMPLETE / AWAITING_INDEPENDENT_ACCEPTANCE |
| C15-RCC-RES-B-ACCEPT-002 → C / EVAL / CLOSE | **SUPERSEDED / BLOCKED** | RERUN-002 已基础设施失败且 NON-CANONICAL；后续入口改由 B-ACCEPT-003，C/evaluator/close 继续 BLOCKED |
| POST-C15-ISSUE-RECONCILIATION-001 | **BLOCKED** | C15 CLOSE 后先 fresh 对账 #23/#28/#33/#34/#35 与当时 live main；已合入修复不得重复实现；仅当最新 main 可复现时另开新工程 Task |
| C16 → P16 → P17 | **BLOCKED** | `POST-C15-ISSUE-RECONCILIATION-001` 完成后继续原逐项 Gate；只有 P17 PASS 才可进入 P18 平台帮助闭环 |

FIX-001 / FIX-002 / FIX-003 三项 audited Core gap 已全部独立接受并集成；CG-001/002/003 均 CLOSED。`CORE-HEADLESS-001`、`CORE-RECOVERY-001`、`CORE-SCALE-001`、`CORE-RC-FREEZE-001` 均已独立接受并集成。A-002 已接受且 #205 保持 prior-RC evidence；B-PREFLIGHT-002 已接受并合入；`C15-RCC-RES-B-RELEASE-002 = DONE / RELEASED`。PR #219 historical exact `3f9ec00d...` remains ACCEPTANCE_FAIL / blocker=2. Corrective-001 exact `030acbfe...` now also remains ACCEPTANCE_FAIL / fresh blocker=1. Corrective-002 tested exact `227327c...` fresh IA = ACCEPTANCE_PASS / blocker=0 (durable evidence: review-only PR #230 @ `2c846ba...` + PR #219 comment `5854998774`); PR #219 merged `89200c55e63ce2251ecc236e25d16c57d998f93c`; `CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002 = DONE / ACCEPTED / INTEGRATED`, `CORE-RC-REFREEZE-002 = DONE / ACCEPTED / INTEGRATED` (`4cadc1a8...`). **A-003已完成：`C15-RCC-RES-A-RERUN-003 = DONE / ACCEPTED / CANONICAL_FOR_NEW_RC`** (PR #235 `5b636740...` OPEN/UNMERGED/PINNED; IA PR #236 `9fa49c31...` → `0684b458...` `ACCEPTANCE_PASS / 0`; receipt `governance/C15_RCC_RES_A_RERUN_003_ACCEPTANCE_INTEGRATION_RECEIPT_2026-09-27.md`). **`C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 = REVIEW_READY / AWAITING_INDEPENDENT_ACCEPTANCE`** (tested exact PR #216 @ `63ca592359c7e3fd71d6cc4ba349949e4f0b80e3`; formal `36334415401 = SUCCESS`; Stage A `914c960...` -> Stage B `15c75ac...`; writeback receipt `governance/C15_RCC_RES_B_PERSISTENCE_CORRECTIVE_001_PM_REVIEW_READY_WRITEBACK_2026-09-27.md`)。当前唯一下一 READY：**`C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE = READY`**; `B-RELEASE-003 → B-RERUN-003 → B-ACCEPT-003`、Resident C、evaluator、closure 仍 BLOCKED; 严禁直接跳到 RELEASE-003。**（2026-09-29 supersede note：本段为 2026-09-27 历史快照；当前状态只认文件顶部控制入口。Fresh Resident A Corrective-003 已 `DONE / ACCEPTED`（IA `ACCEPTANCE_PASS / blocker=0`，accepted review `7b072340...`，publication `EVIDENCE_PUBLICATION_RECOVERED`）；当前唯一下一 READY = `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-003`（governance re-release，见收据 `governance/C15_RCC_RES_A_RERUN_004_CORRECTIVE_003_ACCEPTANCE_INTEGRATION_RECEIPT_2026-09-29.md`）。）**

> Status: ACTIVE  
> Effective: 2026-09-21  
> Repository truth: `Haneof/Haneof-AIOS-Core-v3.0@main`  
> Current verified main anchor at board creation: `45d6c353b75048197c438ee5384074c5beea94d3`  
> Purpose: one window = one task; every completed task writes durable progress before the next window starts.

---

## 0. 历史 PM 快照 — 2026-09-24 B corrective 已合入、RC completion 之前

**仅供 PM / 工程 / operator 阅读；盲测 Resident 不得读取本板或项目 checkpoint。** 盲测角色只接收独立获准的安全包，不能执行下方通用仓库恢复步骤。

- 治理 PR [#122](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/pull/122) 已合入，真实 merge SHA：`2a68df3f8901138fa3126a91063c430f69102049`。
- 实际审查身份：**原 PM 自审**，不是独立语义评估。普通治理文档集成无需另开 AI 窗口；正常 CI/分支保护仍必须遵守，盲测与协议要求的独立评估不豁免。
- 历史节点：`C15-RCC-RES-B-CORRECTIVE-001 = DONE` 后，当时的**唯一下一 READY 曾是 `C15-RCC-RES-B-PREFLIGHT-001`**；该状态已被后续 Core completion / RC-FREEZE / `FRESH_A_REQUIRED` 裁决 supersede。当前状态只认文件顶部控制入口与 §3 正式任务表。
- Canonical frozen Core：`bcd6bf353126318f9a97076b52ec1740d43f35a4`；与已合入治理的 Core tree 无差异，语义 freeze ACTIVE。
- C14 已 PASS；canonical A #117 @ `3e51f728d7959048b75fea01d405bc837b0e8185` 已接受且未改。
- 旧 B #121 @ `b6e5ac939bef83615292bcf9b9099d76737d82b0` 当前 candidate 验收 FAILED；OPEN / UNMERGED / PINNED / NON-CANONICAL，不得用于初始化 C。
- 下一任务只做 operator 机械预检；**盲测 B 仍 BLOCKED**，需经过环境预检与独立放行。C/EVAL/CLOSE、C16、广泛 P16、P17 继续 BLOCKED。
- 治理合入收据：`governance/C15_RCC_RES_B_CORRECTIVE_INTEGRATION_RECEIPT_2026-09-24.md`。
- 裁决：`governance/C15_RCC_RES_B_CORRECTIVE_DECISION_2026-09-23.md`；审查：`reviews/C15_RCC_RES_B_001_PM_CORRECTIVE_REVIEW_2026-09-23.md`。
- 操作员提示词：`governance/prompts/C15_RES_B_OPERATOR_PREFLIGHT_PROMPT_2026-09-23.md`。历史 PM 集成提示词已完成，不再开重复审查窗口。
- 风险登记不是第二施工队列；#120 历史 CI 异常仍有记录，本次绿灯不抹去旧失败。

---

## 1. 最高执行规则

从本文件生效起，任何 PM / operator / reviewer / programmer 新窗口都不得凭聊天记忆自行选择工作。盲测 Resident 适用 §0 的隔离例外，只读批准的安全包，不读治理材料。

每个窗口必须：

1. 读取本文件。
2. 获取 GitHub `main` 实时 HEAD。
3. 找到**第一个状态为 `READY` 且所有 dependencies 都为 `DONE / ALREADY_FIXED / NOT_REQUIRED`** 的任务。
4. 只执行该一个任务。
5. 不得顺手进入下一任务。
6. 任务完成后必须先：
   - 合入 `main`（如果任务需要代码/文档落库）；
   - 保存 PR / merge SHA / Gate / evidence；
   - 更新本表该任务状态；
   - 更新 `AIOS_v3.0_CURRENT_CHECKPOINT.md`。
7. 完成写回后，本窗口停止。下一任务由**新窗口**继续。

### 禁止

- 一个窗口连续做两个任务；
- 因为“顺手”继续修下一缺口；
- 看到历史 Issue 就直接重做；
- 以旧 branch ahead/diverged 作为“还没合”的证据；
- 以聊天上下文代替仓库进度；
- 任务没有 Gate / evidence 就写 DONE；
- Resident 入住用 Python/if-else/关键词程序代替模型本人认知；
- 未完成的长期入住冒充 365 天完成。

---

## 2. 状态定义

| 状态 | 含义 |
|---|---|
| `READY` | 下一窗口允许执行 |
| `IN_PROGRESS` | 已有窗口正在执行；其他窗口禁止重复 |
| `FROZEN_WIP` | 已有未合并工作，冻结现场；下一专用窗口从该现场继续，不得从头重写 |
| `WAITING_AUDIT` | 先复核最新 main，确认仍存在才施工 |
| `BLOCKED` | 前置依赖未完成 |
| `GATE` | 实现完成，等待规定验收 |
| `DONE` | 已落 main 且证据完整 |
| `ALREADY_FIXED` | 最新 main 已有等价修复；禁止重复实现 |
| `NOT_REQUIRED` | 审查后确认无需实现 |
| `FAILED` | 当前 candidate 未通过，保留证据后由专用修复任务处理 |

---

## 3. 当前唯一施工队列

> 选择规则：严格从上到下。条件任务在 `AUDIT-001` 后才能激活。
> 2026-09-21 PM reprioritization: 77-day Resident evidence exposed a missing continuous User/World → AI-world cognition-derivation bridge. C14 is now inserted before P16 campaign continuation; P16-TRIAGE is paused until C14 closure.
> 2026-09-22 PM roadmap: after a narrow C14 semantic-evidence repair closes the existing E1/E5 blockers, C15 becomes the Resident Cognitive Continuity Gate: durable User Understanding / Relationship-Role / Self-Calibration / Strategy-Experience must survive fresh-session and replacement-model handoff through AIOS, materially affect later behavior, and remain revisable. C16 then validates the separate non-world Resident system-improvement feedback loop before broad P16 resumes.

| 顺序 | Task ID | 单窗口任务 | 状态 | Dependencies | 当前现场 / 证据 | 完成定义 |
|---:|---|---|---|---|---|---|
| 1 | `C13-MTR-001` | 完成 C13 non-world Metering Ledger：模型返回后立即落 operations-side meter；token 真值不再依赖 Wake World metadata；crash 后计量不丢；Periodic Review 计费时间不倒带 | **DONE** | — | PR #47; final candidate `47ed2de25cdcb26c8c552a3db0640a59f9a15817`; squash merge `f9baacd5ac7be1646036a4e878934e77965c6640`; required Gates GREEN | 已从冻结 WIP 完成、自审、专项 Gate + P16 full regression GREEN、squash merge；完整证据见 §5 完成记录 |
| 2 | `AUDIT-001` | 对 Issue #30 的 T34/T36/T28/T35/T33 与 PR #37 在**最新 main**逐项重新复核，只做裁决，不修代码 | **DONE** | C13-MTR-001 | `main@e9862103a753be026edf1745c6a5d07fa56c0cf4`; `reviews/AUDIT-001_ISSUE30_CURRENT_MAIN_EVIDENCE_MATRIX_2026-09-21.md` | 五项 current-main 裁决已落库；无 Core 修改 |
| 3 | `T34-EXEC-001` | Action 授权前重新验证父 Task/撤销状态，关闭 cancel→authorize 竞态 | **DONE** | AUDIT-001 | PR #54; candidate `da14638fc0f8cf14bad6b5315988d7c7db691ac8`; squash merge `48f5e29ad564ef7c1687b5a0d81cede1452e82e8`; repro run `35566808198`; candidate gate run `35566890602`; merge-result P12/P16 GREEN | 修复前 current-main 复现；cancel/retry/restart/race/legacy-world/history/normal-authorize 回归 GREEN |
| 4 | `T36-SEARCH-001` | 结构化 Observation scalar 派生索引，不改原 typed fact，不做语义推断 | **DONE** | AUDIT-001 | PR #52; squash merge `07965029285cf3dfc0fdb5e506a65add60c76c29`; before-fix repro run `35566751016`; final candidate `afc62009340f4451d15400c4860ee880296d9c7c`; required Gates GREEN | dict/list/number/bool/null 可检索；rebuild=incremental；subject/current/inactive/tombstone/text 语义不退化；原 typed Observation 不改写 |
| 5 | `T28-REC-001` | 普通推荐与 antecedent 路径统一隔离 assistant raw dialogue，避免把 AI 自己的话当用户事实主动推荐 | **DONE** | AUDIT-001 | PR #49; candidate `2a16d1ffaaec877356f4f281e82d884e6ac97ab5`; squash merge `e159ab30a12b819ca053085d5103460e66ef9f16`; required Gates GREEN | assistant raw dialogue 不再作为普通 proactive user/world memory；raw continuity/search/drill-down 保留；用户/外部 fact 与 evidence-grounded Claim 不退化 |
| 6 | `T35-RULE-001` | 只做“非 Action Task 的可信完成凭据”语义裁决；不改 execution 代码 | **DONE** | AUDIT-001 | `governance/T35_NON_ACTION_TASK_COMPLETION_EVIDENCE_RULING_2026-09-21.md`; PR #53; semantic candidate `b58bbb31a04a119897890452e76461f14fd46288`; squash merge `6fcb51d6e2ecf6e2ab8ff0fa62013f094b32f21c` | 唯一裁决已形成：所有 Task 终态必须真实证据化；外部执行保持 Action→Outcome；非 Action Task 可用合格 pinned World evidence / validated durable artifact；禁止 AI 自述、伪 Outcome、循环 OperationExperience |
| 7 | `T35-IMPL-001` | 按 T35-RULE-001 裁决实现 Task 完成闭环 | **DONE** | T35-RULE-001, T34-EXEC-001 | PR #55; candidate `07617df8ab87550289c1498cf3df387626d55e40`; squash merge `141dc177be895f9894a05227cbb132207ebf784d`; required candidate Gates GREEN; merge-result P12/P16 GREEN | 外部 Action/Outcome 保持强制链；WORLD_EVIDENCE / MIXED 按结构化 completion contract 校验；真实凭据、subject/current/provenance、幂等/restart/history 与 T34 回归全部 GREEN |
| 8 | `T33-RECALL-001` | 用自包含表达/跨会话省略/无前文三类对照重新验证 recall 误触；只有复现才修 | **DONE** | AUDIT-001 | PR #51; candidate `91f1eecc1eb1a5aeb3dd2fa4566f045b6abea796`; squash merge `cb8eab12e9747bece41b14d183840e2cf13bd183`; repro run `35566569236`; required Gates GREEN | Case A/B/C、same-session canonical antecedent、assistant-raw exclusion、P14/Fused/P16 回归 GREEN；Core 只暴露候选，不绑定指代 |
| 9 | `C14-RULE-001` | 冻结持续认知派生语义：Summary 只产生认知机会；高阶认知证据闭包必须落到合格非 Summary 叶子；定义跨维、silence、new-session 消费、provenance 与 Periodic Review 分工 | **DONE** | T35-IMPL-001 | `governance/C14_CONTINUOUS_COGNITIVE_DERIVATION_RULING_2026-09-21.md`; PR #58; candidate `33effe8a86af3d5a34a6b227618db82caf519c37`; squash merge `f9438cce087a422ad6d2394b8f0c2a22307fe283` | Authoritative ruling frozen: Summary may navigate/compress but not terminate proof; support provenance closure, domain-appropriate leaf grounding, derived lineage, cross-dimensional autonomy, valid silence, matched negative control, new-runtime behavior consumption, and Periodic Review split are binding; no Core/constitution/registry change |
| 10 | `C14-SCHED-001` | 实现 Summary → Cognitive Derivation Wake：递归 leaf provenance、幂等、revision、crash/restart recovery、纯 AI-cognition Summary 防回环 | **DONE** | C14-RULE-001 | PR #59; candidate `5389118b9e37b8f0b33552099e39d5c8a31eaffb`; squash merge `f0b24cda3c76d5170f5f27fb5a94107036e2f2c4`; C14 gate run `35579489466` SUCCESS | Dedicated `COGNITIVE_DERIVATION` BACKGROUND Wake; recursive pinned provenance; REALITY/MIXED eligible; AI_COGNITION_ONLY/MAINTENANCE_ONLY/UNKNOWN fail closed; deterministic per-Summary-revision Wake identity; restart reconciliation; no second provenance/scheduler DB; no Claim/Resident semantic change |
| 11 | `C14-RUNTIME-001` | 将 derivation Wake 接入同一 Resident CognitiveRuntime，装配 pinned Summary、跨维能力、AI-world context；形成/修正认知前必须满足 leaf-grounded evidence 规则，或 silence | **DONE** | C14-SCHED-001 | PR #61; candidate `75cc62ca13169c6ba8752e0562224705fe6f9ac2`; squash merge `a887ba537e9797d4bf5a7b7fb482fa4a55f47df7`; candidate + merge-result required Gates GREEN | 同一 Resident Runtime 完成 derivation cockpit + leaf-grounded create/revise/retract/silence 闭环；Summary-only/AI recursion/T28 assistant-only fail closed；真实 user/Outcome case grounding保持合法；BACKGROUND 不直接投放用户；完整证据见 C14-RUNTIME-001 completion |
| 12 | `C14-RUNTIME-HARDEN-001` | 封闭 COGNITIVE_DERIVATION 的 side-effect 逃逸：该 Wake 只允许 leaf-grounded Claim create/revise/retract 写入；Event/Entity/Relation/Dimension/Goal/Task/Action/AttentionWatch/Experience/Policy 等持久副作用不得从此后台认知入口写入 | **DONE** | C14-RUNTIME-001 | PR #63; candidate `3accaeebe8ee1b3d420d2dfa3528ecb5e7388d86`; squash merge `09002ddf8fd1fd4af08f54ac5b190d4c39c9e25b`; `reviews/C14_RUNTIME_HARDEN_001_COMPLETION_EVIDENCE_2026-09-21.md`; required Gates GREEN | COGNITIVE_DERIVATION 显式 side-effect allowlist 仅含 `commit_claim`, `commit_ai_world_claim`, `revise_claim`, `retract_claim`; 其他 writes 全部 deny；read capabilities 保留；普通 user turn / Periodic Review 不退化；专项+全回归 GREEN |
| 13 | `C14-LOOP-001` | 持续认知派生加固：C14-aware burst bundling、防 contract laundering、自激防护、预算/合并/延迟/恢复、Periodic Review 共存、新 Runtime 检索、长期 provenance reconcile 规模加固 | **DONE** | C14-RUNTIME-HARDEN-001 | PR #65; candidate `f48c3c9cfa8a24fa2e0e0220d7fe20bcda1be34d`; squash merge `a385f7b3fcc71982aae0611a382502c9a37ba71e`; `reviews/C14_LOOP_001_COMPLETION_EVIDENCE_2026-09-21.md`; exact-candidate 14 workflows GREEN | C14-only homogeneous AttentionBundle preserves effective derivation contract/allowlist/no-delivery; model/tool/capability exhaustion durable/resumable; partial-write retry idempotent; unfinished spend remains in C13 budget truth; AI cognition self-excitation blocked; Review coexistence/new-runtime retrieval/reconcile-scale regressions GREEN |
| 14 | `C14-RES-FIX-001` | Life Director 准备 C14 真实 Resident sealed life fixture / sequential release contract；只做测试输入与未来隔离，不运行 Resident 语义 | **DONE** | C14-LOOP-001 | PR #68; candidate `e174a016c25d34c05ef096129d1c537ca5b19de8`; squash merge `796d9c357bb08f3042f103bc66260fdb3cdcd88c`; fixture SHA256 `a0f9dfd0985560ce80f568b6cd11d46b13f5dc352a664c005fcb165ea5a67485`; `reviews/internal_habitation/c14-resident/C14_RES_FIX_001_COMPLETION_EVIDENCE_2026-09-21.md` | 36 条自然人生事件已冻结；Phase A 24 / Phase B 12；cursor 24/25 sealed handoff；逐项 release contract + evaluator-only notes + digest/顺序/时间/泄漏机械校验 PASS；无 Core 修改、无 Resident 语义运行 |
| 15 | `C14-RES-FIX-002` | 加固 C14 真实 Resident fixture：消除单维 conversation 泄题、让 Phase-B 决策对当前事实保持真正可选、增加 executable blind release operator | **DONE** | C14-RES-FIX-001 | PR #70; candidate `aacee04cfa5390f2a63d0a5606acb909291849b6`; squash merge `510290d3b9578cd9425079a22050eb679ddb528a`; v2 SHA256 `1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253`; `reviews/internal_habitation/c14-resident/v2/C14_RES_FIX_002_COMPLETION_EVIDENCE_2026-09-21.md` | v2 36-event fixture preserves v1 history; single-dimension leakage audit PASS; Phase-B underdetermination PASS; exact-byte blind release audit 19/19 PASS; A/B cursor 24/25 fail-closed; Core diff 0; no Resident run |
| 16 | `C14-RES-FIX-003` | 加固 blind release ack：必须机械证明当前 reveal 事件已真实持久化进 AIOS World，不能只校验 `object_id@revision` 字符串格式 | **DONE** | C14-RES-FIX-002 | PR #72; exact candidate `17bd54ed0b64131ded0b70d853cac205d055bdcb`; squash merge `e5c7fefce82a49735575c423da310ca3d9441ab4`; exact-candidate Gate `35598216907` SUCCESS; fixture SHA256 unchanged `1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253`; `reviews/internal_habitation/c14-resident/v2/C14_RES_FIX_003_COMPLETION_EVIDENCE_2026-09-21.md` | ack 通过真实 `SQLiteWorldStore.object_revision_record + get_payload(exact revision)` 核验 durable ref、subject、event binding、commit source_class 与 receipt chain；30/30 real SQLite tests PASS；A 24/25 boundary / future isolation PASS；Core diff 0；Resident runs 0 |
| 17 | `C14-RES-A-001` | 第一真实 Resident 窗口逐事件生活与认知：模型本人基于当前 RuntimeSnapshot 作 search/inspect/Claim/revise/retract/silence；在 sealed handoff boundary 停止 | **DONE** | C14-RES-FIX-003 | PR #75 evidence head `cb9b56b7039272d932158f33bfe979eff6749c9b` (unmerged/pinned); `reviews/C14_RES_A_001_PM_ACCEPTANCE_REVIEW_2026-09-21.md`; World SHA256 `0ee338aa8f2845bb376610da3c450e09ff9cc8bec5184ca60608b2465d7ba72f`; release-state SHA256 `e922d268fbb11364a7bb558aed60b88e7a3c075032f4fa4e1c47a84de3f765f1` | Independent PM PASS: 24/24 sequential durable acks; cursor25 not revealed; same-window Resident authored 43 Summaries + Runtime directives; one cross-dimensional leaf-grounded hypothesis Claim created then revised to rev2; matched negative remained silence; no Core/governance diff or future leak; Python 3.11.2 and unverified exact model identity recorded as non-blocking provenance deviations |
| 18 | `C14-RES-B-FIX-001` | Phase-B canonical conversation ingest preflight：让 blind release 的 USER conversation 直接落成 canonical ConversationIngestor user Observation，并由后续 `run_turn` 幂等复用，避免同一句用户输入在 World 中重复两次 | **DONE** | C14-RES-A-001 | PR #78; exact candidate `cb3a417f3c29b29d6aa2bf364386aec12b17e623`; squash merge `1c7a8c1466911f8617ed39348a50ac8041f23715`; exact-candidate workflow `35631789929` SUCCESS; completion evidence `reviews/internal_habitation/c14-resident/v2/C14_RES_B_FIX_001_COMPLETION_EVIDENCE_2026-09-21.md` | Python 3.12.14；generic 30/30 PASS；canonical conversation 15/15 PASS；现有 conversation/fused-runtime 16/16 PASS；same session/turn/text/time `run_turn` user commit idempotent replay；最终每 turn 仅 1 条 canonical user Observation + 独立 assistant Observation；generic conversation path/错误 session/turn/text/time/subject/role/authority/ref/order 均 fail closed；fixture SHA unchanged；Core diff 0；Resident-A evidence diff 0；Resident-B semantic execution 0 |
| 19 | `C14-RES-B-001` | 全新模型窗口恢复 Phase-A durable AIOS World 后继续人生；禁止注入 Phase-A 对话/总结，验证旧 cognition 在新情境下被 AIOS 正常检索并实际影响未来行为与 Outcome | **DONE** | C14-RES-B-FIX-001 | evidence PR #79 (leave unmerged/pinned), exact head `546449a453e6e6dff3a2eeb2b52e7cf6786927be`; `reviews/C14_RES_B_001_PM_ACCEPTANCE_REVIEW_2026-09-21.md`; final World SHA256 `a288fc5d11a1a73006725efdd906a7ab014d4228085c610b4a32f887cfe3d615`; release-state SHA256 `9281ced5013b45445574698d53ff9a2d57d5308ac5d1221e5db178efcf0c8a4f` | Independent PM accepts run completeness/provenance only: cursors 25..36 complete; 9 mechanical + 3 canonical conversation paths; thin bridge has no semantic rules; old Claim @2 recovered via normal capability, rev3 surfaced as score-10 memory card at cursor26 and pinned into new Task reason_refs; later real work_outcome revised it to rev4; cursor37 artifact empty; evidence PR has no Core/governance diff. Semantic C14 verdict remains exclusively C14-RES-EVAL-001. |
| 20 | `C14-RES-EVAL-001` | 独立 evaluator 审计 C14 Resident A/B 真实语义证据；不修 Core | **DONE** | C14-RES-B-001 | `reviews/C14_RES_EVAL_001_INDEPENDENT_SEMANTIC_EVALUATION_2026-09-22.md`; evaluated main `8e6f9febc5f006605116c526796fa21435b4b22e`; A PR #75 exact head `cb9b56b7039272d932158f33bfe979eff6749c9b`; B PR #79 exact head `546449a453e6e6dff3a2eeb2b52e7cf6786927be` | **Overall NOT VALID**: E1 PARTIAL / E2 VALID / E3 VALID / E4 VALID / E5 INVALID / E6 VALID. Blockers: A Claim rev2 contains unpinned 5h48 sleep fact; B rev4 treats unobserved 09:00 designer plan as executed reality and raises confidence despite cursor30 08:05 drafting start. Evaluator task complete; no evidence repair performed. |
| 21 | `C14-SEM-REPAIR-FIX-001` | 为 C14 E1/E5 blocker 准备最小 sealed semantic-repair fixture；只替换受影响语义证据，不改旧 A/B evidence，不改 Core | **DONE** | C14-RES-EVAL-001 | PR #83; final candidate `11ee54c0ecaca3462fd526f27c2a5b526a6e8295`; squash merge `aacf70e381a78b5955304e894ebce445ce3ffe49`; fixture `reviews/internal_habitation/c14-resident/semantic-repair-v1/fixture/sealed_fixture.json`; SHA256 `1095d5aef52061753db7d9dab558af1361b92976f2ded0e6956d70afe3e6527f`; exact-candidate gate `35678649521` SUCCESS; completion evidence `reviews/internal_habitation/c14-resident/semantic-repair-v1/C14_SEM_REPAIR_FIX_001_COMPLETION_EVIDENCE_2026-09-22.md` | 15-event R-A/R-B repair fixture; E1 material facts independently leaf-groundable; E5 planned/observed/outcome split + later user feedback + external-failure control; 25/25 mechanical checks PASS; canonical/fused regressions 16/16 PASS; Core/v2 diff 0; no Resident run |
| 22 | `C14-SEM-REPAIR-RES-001` | 新真实 Resident 窗口执行最小 repair life；模型本人形成/修订/保持 cognition，不得程序代答 | **DONE** | C14-SEM-REPAIR-FIX-001 | canonical evidence **PR #92 (OPEN/UNMERGED/PINNED, never merge)**; exact evidence head `9e870514b57bf07c00018d7dcf7435f2702f8730`; PM acceptance report `reviews/C14_SEM_REPAIR_RES_001_PM_ACCEPTANCE_REVIEW_2026-09-22.md`; run dir `reviews/internal_habitation/c14-resident/semantic-repair-v1/runs/resident-repair-20260922/`; session `resident-sem-repair-20260922`; final World SHA256 `a7a7cd9f9166eb41d3b93d85820a9c7a4ab0aa57b81787d89f395482742bae57` (rev 83); release-state SHA256 `4f41d709a76e0f40ce5b0093f540cc286dde84a1906a575019199cc7a7970081`; index SHA256 `ae296ee44a000eb7ea5bf122184bfb9dd65c80f14f9e94e9fb64fce039658caf` | PM evidence acceptance 2026-09-22: cursors 15/15 sequential (A=1..6, B=7..15), durable SQLite acks verified; 16 checkpoints, 20 Resident-authored summaries, 18 capability calls (15 inspect / 1 commit_claim / 2 revise_claim), 8 silences, 1 response; final Claim `clm_b4df2179bb8ffec020a39ede@3` with durable revision chain rev1@wr20→rev2@wr44→rev3@wr77 and pinned leaf evidence sets; bridge transport-only, no pseudo-LLM; zero future leak; `src/aios_core/**`=0; v2/PR#75/PR#79 historical evidence untouched; trial PRs #84–#91 dispositioned ABORTED/SCAFFOLD/NON-CANONICAL. **Semantic verdict NOT PERFORMED — E1/E5 validity is exclusively C14-SEM-REPAIR-EVAL-001**; evaluator must use PR #92 exact head only |
| 23 | `C14-SEM-REPAIR-EVAL-001` | 独立 evaluator 只审计 replacement E1/E5 evidence，并与原 E2/E3/E4/E6 VALID 证据组合；不修 Core | **DONE** | C14-SEM-REPAIR-RES-001 | `reviews/C14_SEM_REPAIR_EVAL_001_INDEPENDENT_SEMANTIC_EVALUATION_2026-09-22.md`; evaluated live main `655e1d48c2b53dd4f5a10485a9d530ed13ca69a3` (run's declared main `7611fa5059f5dc8a20835cab5b312be2f43d11e8`); canonical evidence PR #92 @ exact head `9e870514b57bf07c00018d7dcf7435f2702f8730` ONLY (kept OPEN/UNMERGED/PINNED); World/release-state/index SHA256 independently recomputed and matched | **E1 VALID / E5 VALID**；repair 未污染 E2/E3/E4/E6；combined matrix 全 VALID；overall `C14 RESIDENT SEMANTIC EVIDENCE = VALID`；`C14-CLOSE-001 = READY`；禁止使用 #84–#91（未使用）；未修 Core/fixture/evidence |
| 24 | `C14-CLOSE-001` | 独立审计 C14 规则、代码、Gate、原 Resident 证据与 repair evidence；只做收口，不写新 Core 功能 | **DONE** | C14-SEM-REPAIR-EVAL-001 | reviews/C14_CLOSE_001_FINAL_CLOSURE_REVIEW_2026-09-22.md; closure PR opened and merged; C14 PASS; PR #75/#79/#92 kept OPEN/UNMERGED/PINNED | 规则无冲突、main 对齐、341/341 Gates GREEN、Summary 不成终态 proof、reality 叶子闭合、Core 无语义推断、side-effect allowlist 封闭、E1–E6 全 VALID；C14 CLOSURE = PASS |
| 25 | `C15-RCC-RULE-001` | 冻结 Resident Cognitive Continuity 语义：模型可替换，Resident 的 User Understanding / Relationship-Role / Self-Calibration / Strategy-Experience 不得重置 | **DONE** | C14-CLOSE-001 | `governance/C15_RESIDENT_COGNITIVE_CONTINUITY_RULING_2026-09-22.md`; started main `623f8471cdd6ac2d756c15231f65f311e662f9d9`; constitution-change verdict `NO CONSTITUTION CHANGE REQUIRED`; Core diff `src/aios_core/** = 0` | Authoritative RCC ruling frozen: three-layer User World / Resident Cognitive World / Model Runtime; same Resident = durable cognition lineage recoverable, consumed, and still revisable; replacement-model allows style/ability change but forbids silent reset; continuity ≠ freezing; R1–R9 all VALID required for C15 PASS |
| 26 | `C15-RCC-PREFLIGHT-001` | 审计 current main 是否已具备形成、索引、检索、fresh Runtime 恢复 Self/Calibration/Strategy/User Understanding/Experience 的机制；先审计再决定是否施工 | **DONE** | C15-RCC-RULE-001 | `main@fb7921df2231ac8fb6af85f29d6e9eff64272245`; PR #97; `reviews/C15_RCC_PREFLIGHT_001_MECHANISM_AUDIT_2026-09-22.md`; P1–P13 audit: P11 MECHANISM_GAP, P12 INSUFFICIENT_EVIDENCE, others ALREADY_IMPLEMENTED; Core diff `src/aios_core/** = 0` | 发现唯一真实机制缺口：AI-world typed facade 的 user/domain subject isolation；replacement-model identity 仅有 declared/configured provenance，R6 仍证据不足；创建唯一最小 `C15-RCC-MECH-FIX-001`，不在本窗口修 Core |
| 27 | `C15-RCC-MECH-FIX-001` | 最小封闭 AI-world typed facade 的 Subject/User isolation：按 AI-world domain 派生合法 subject，阻止 User A 的 User Understanding / Relationship / Strategy 被 User B read/core-context/snapshot 或 typed revise/retract 访问 | **DONE** | C15-RCC-PREFLIGHT-001 | PR #98; starting main `a6e2adf5d5676f765e40150aa3e21d145d4aef30`; exact gated candidate `de65572d2ce31cc53d5daadc252fe91e94e045d2`; `reviews/C15_RCC_MECH_FIX_001_COMPLETION_EVIDENCE_2026-09-22.md`; p10 `35698883015` SUCCESS; fused `35698882956` SUCCESS; p9 `35698883322` SUCCESS; C14 runtime/loop `35698883045` / `35698882999` SUCCESS; P16 full regression `35698883072` SUCCESS | 起始 main Core 上 test-only repro 明确复现 read/core_context/snapshot 与 typed revise/retract cross-user leak；domain-derived expected subject 已统一封闭 typed facade；AI-self Self/Calibration continuity 与合法 revision 不退化；malformed metadata fail-closed；无第二 DB/runtime；P12 attestation 未触碰；专项 + full Core regression GREEN |
| 28 | `C15-RCC-FIXTURE-001` | Life Director 准备 sealed Resident Cognitive Continuity life：用户理解、关系/角色、真实成功、真实错误、外部失败负对照、反证、fresh-window 与 replacement-model 场景 | **DONE** | C15-RCC-PREFLIGHT-001, C15-RCC-MECH-FIX-001 | PR #99 + corrective PR #100; starting main `d65a7b24366cb612d042a3feedb92f0a3d90b02c`; initial gated candidate `74ff20d06b30847557c25c08e4deabd9d4578c84`; corrective exact candidate `629cf587f37f7cea25595e456d5e4de4c03fa7d5`; fixture SHA256 `7ccb309d207cb6ee240fbc008ee4f535e25571f04ba7ca1b7c95bf9afb5ebf46`; gate runs `35701591095` + `35702939513` SUCCESS; `reviews/internal_habitation/c15-rcc/v1/C15_RCC_FIXTURE_001_COMPLETION_EVIDENCE_2026-09-22.md` | 30-event sealed RCC life frozen；A=1..13/B=14..22/C=23..30；35/35 C15 mechanical Gate + 25/25 mature C14 sealed Gate + subject-isolation/fused/canonical regressions GREEN；duplicate reveal/ack fail closed；future isolation/canonical USER ingest/durable ack/attestation-null boundary enforced；Core diff 0；Resident runs 0 |
| 29 | `C15-RCC-RES-A-001` | Resident A 逐事件生活，基于真实 Outcome/feedback 自主形成或保持 User Understanding / Relationship-Role / Self-Calibration / Strategy-Experience cognition | **BLOCKED / SUPERSEDED** | C15-RCC-FIXTURE-001 | PR #101 **OPEN / UNMERGED / PINNED** @ `bfbfa059e2ac616326eecdfe3ffa7a927bdc7ce2`; PRE-FIX DIAGNOSTIC / SUPERSEDED RESIDENT A RUN; cursor `1..13` complete | Historical repair rejected because corrected Core changes Resident-visible Phase A inputs (`sum0011` 6→8 sources; Periodic Review 18→20 anchors). PR #101 is diagnostic only and must not become canonical RCC A World. |
| 29.1 | `C15-RCC-A-WAKE-DELIVERY-CORRECTIVE-001` | 独立纠偏 PR #102 对 interrupt-Wake user delivery 的治理解释：真实 delivered AI output 属于用户-AI交流 World fact；缺失持久化时不得把 A World 交给 fresh B | **DONE** | C15-RCC-RES-A-001 evidence run | `reviews/C15_RCC_RES_A_WAKE_DELIVERY_CORRECTIVE_REVIEW_2026-09-22.md`; current-main Core audit; PR #101 exact evidence audit | 裁决 `WAKE USER-DELIVERED ASSISTANT OUTPUT PERSISTENCE = MECHANISM_GAP`；A/B 重新 BLOCKED；PR #101 保持 pre-fix diagnostic、OPEN/UNMERGED/PINNED；本窗口 Core diff 0 |
| 29.2 | `C15-RCC-WAKE-DELIVERY-FIX-001` | 最小修复真实 user-delivered non-conversation Wake assistant output 持久化：仅实际允许并返回用户的 assistant response exactly-once 写入统一用户-AI交流维度；绝不伪造 USER input | **DONE** | C15-RCC-A-WAKE-DELIVERY-CORRECTIVE-001 | PR #104; Core merge `fd9ba5de329abb025f52de76f1ab658cdafb4897`; exact final Core candidate `41f2a5da2153c55b137741fdd71983eea2a011f7`; completion evidence `reviews/C15_RCC_WAKE_DELIVERY_FIX_001_COMPLETION_EVIDENCE_2026-09-22.md`; final PR-head Gates GREEN | Delivered Wake assistant output is durable/searchable with exact Wake provenance and stable exactly-once recovery; suppressed/denied/internal/silence write 0; ordinary run_turn unchanged; no synthetic USER; PR #101 untouched. |
| 29.3 | `C15-RCC-RES-A-REPAIR-DECISION-001` | Core 修复后由独立 PM 决定 Resident A evidence 的恢复路径：可验证的纯机械 historical persistence，或 fresh World 重跑 Resident A | **DONE** | C15-RCC-WAKE-DELIVERY-FIX-001 | `reviews/C15_RCC_RES_A_REPAIR_DECISION_2026-09-22.md`; PR #101 exact diagnostic evidence; fixed Core @ `41f2a5da2153c55b137741fdd71983eea2a011f7` | `PATH A = REJECTED`; `PATH B = REQUIRED`. Corrected history changes actual summary/review source sets during Phase A, so old semantic outputs are not historical-equivalent. |
| 29.4 | `C15-RCC-RES-A-RERUN-001` | 在 historical frozen Core 上使用 frozen C15 fixture，从 fresh private World / fresh session 执行 Phase A cursor 1..13 | **DONE / HISTORICAL ONLY FOR OLD CORE** | C15-RCC-RES-A-REPAIR-DECISION-001 | PR #117 @ `3e51f728d7959048b75fea01d405bc837b0e8185` remains OPEN / UNMERGED / PINNED; historical Core anchor `bcd6bf353126318f9a97076b52ec1740d43f35a4`; `governance/C15_FINAL_RELEASE_DECISION_2026-09-23.md` | Historical acceptance remains valid only for old frozen Core. RC-FREEZE impact is `FRESH_A_REQUIRED`; never hash-swap this World into the new RC. |
| 29.5 | `C15-RCC-RES-A-RERUN-002` | 在 frozen RC software `773876f92d5f8e53422f8f5a68cc651953d93052` / Core tree `fe77f8a0706acfaf369041d0882b6d0e6de39f22` 上，从全新 private World / fresh session 重新生活 Phase A cursor 1..13；真实 Resident 本人逐事件判断 | **READY** | CORE-RC-FREEZE-001 | Prompt `governance/prompts/C15_RCC_RES_A_RERUN_002_2026-09-24.md`; safe contract `reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_RUN_CONTRACT.md`; old #117/#109/#101 semantic outputs forbidden | 13/13 sequential durable ack；normal Runtime/Wake/Review/due-work 完整；所有语义判断由真实 Resident 当前 RuntimeSnapshot 作出；冻结 World/index/release-state/raw traces/metering；只开 evidence-only PR；不运行 B；等待独立 acceptance。 |
| 29.6 | `C15-RCC-RES-A-RERUN-002-ACCEPT-001` | 独立验收新 RC Resident A exact evidence head 的执行完整性、隔离、provenance、durable World/index/restart 状态；不替代后续 C15 semantic evaluator | **BLOCKED** | C15-RCC-RES-A-RERUN-002 | fresh reviewer；exact evidence-only head | PASS 后才允许 B operator preflight 绑定新 A World；验收窗口不修 run、不运行 B。 |
| 30 | `C15-RCC-RES-B-001` | 原 fresh-context B 候选执行证据验收 | **FAILED** | C15-RCC-RES-A-RERUN-001 | PR #121 @ `b6e5ac939bef83615292bcf9b9099d76737d82b0`；本处置随纠偏治理集成生效；OPEN / UNMERGED / PINNED / NON-CANONICAL | 仅 9 条输入落库、无 B 模型计量/原始 Runtime 轨迹、World/index 97/88，当前 candidate 不可接受；不是 Core 认知能力失败裁决，不以新 Claim 数量评分 |
| 30.1 | `C15-RCC-RES-B-CORRECTIVE-001` | PM 证据纠偏、地图/队列/检查点同步与隔离角色提示词 | **DONE** | C15-RCC-RES-B-001 candidate disposition | PR #122；accepted head `bbf45baf2e2a6314483d8355c1ee8badc09aa4a9`；merge `2a68df3f8901138fa3126a91063c430f69102049`；integration receipt 2026-09-24 | PM 自审明确记录；exact-head C15/C14 CI SUCCESS；无 Core/fixture/evidence 改动；仅释放 operator preflight，不是实验 PASS |
| 30.2 | `C15-RCC-RES-B-PREFLIGHT-001` | 非盲 operator 准备正常 Runtime 传输桥、实时记录、合法 A 状态与实际隔离；不运行真实 B | **BLOCKED** | CORE-OPERATOR-001 (DONE)；CORE-RC-FREEZE-001 (DONE)；C15-RCC-RES-A-RERUN-002-ACCEPT-001 | operator 资产已由 CORE-OPERATOR-001 合入 main `e72a6387`；最终 preflight 必须绑定 frozen RC `773876f9...` 与 accepted 新 RC A World；历史 #117 不可替代；独立的新 operator 窗口 | 无语义规则/旧答案；合成数据机械检查；operator/safe-packet manifests、entry commands、hash/pin、隔离证据、身份盘点；不得自放行 |
| 30.3 | `C15-RCC-RES-B-RELEASE-001` | 独立 PM 审查 preflight 并放行唯一安全启动包 | **BLOCKED** | C15-RCC-RES-B-PREFLIGHT-001 | 已接受并合入的 operator exact source + 机械证据；新独立 PM | 冻结 Core/A bytes、正常 Runtime 与记录链、实际隔离均通过；pin packet/bridge、run/session；放行治理合入后才释放 rerun；不执行 Resident |
| 30.4 | `C15-RCC-RES-B-RERUN-001` | 全新盲测 Resident 从 accepted A 执行唯一 B 段 cursor 14..22 | **BLOCKED** | C15-RCC-RES-B-RELEASE-001 | 仅批准的 Resident-safe packet / 正常 AIOS 接口；不读治理/旧证据 | 真实模型逐次选择；normal run_turn/due-work；Snapshot/directive/工具结果/计量/输出实时可审计；最终 World/index/restart/receipts/hash 冻结；仅报 RUN_COMPLETE 待独立验收 |
| 30.5 | `C15-RCC-RES-B-ACCEPT-001` | 独立 PM 验收 fresh B 执行完整性与 provenance，不替代语义终评 | **BLOCKED** | C15-RCC-RES-B-RERUN-001 | exact evidence head + raw runtime trace + frozen state | receipt/World/index/计量/行为原始链匹配，无污染；认知可保留/沉默；private World 不合 main；通过并写回后释放身份预检 |
| 30.6 | `C15-RCC-MODEL-ATTEST-001` | operator/PM 核实 A/B 与拟 C 的可信平台/provider 身份绑定，只做跨模型启动前置 | **BLOCKED** | C15-RCC-RES-B-ACCEPT-001 | actual session-bound external identity evidence；自报/配置名/新窗口不算 | 可独立证明不同底层 model family/provider 才释放 C；否则 INSUFFICIENT_EVIDENCE，C 保持 BLOCKED，R6 不得 VALID；禁止造身份库/伪签名 |
| 31 | `C15-RCC-RES-C-001` | replacement-model Resident C 接管同一 AIOS World；验证“模型换、Resident 不重置” | **BLOCKED** | C15-RCC-RES-B-ACCEPT-001, C15-RCC-MODEL-ATTEST-001 | accepted rerun B checkpoint + trusted different-model identity; never PR #121 World | 不要求同措辞/同风格；要求有效 User Understanding、Role、Self/Calibration、Strategy/Experience 仍可恢复和消费；无法证明模型身份则该轴不得判 VALID |
| 32 | `C15-RCC-EVAL-001` | 独立 evaluator 审计 Resident Cognitive Continuity；不修 Core | **BLOCKED** | C15-RCC-RES-C-001 | A/B/C artifacts + World/checkpoint/digests + hidden chronology | 分别裁决 R1 user-understanding、R2 relationship/role、R3 self/calibration、R4 strategy/experience、R5 fresh-window、R6 replacement-model、R7 behavior effect、R8 correction、R9 anti-self-proof；全部 VALID 才可收口 |
| 33 | `C15-RCC-CLOSE-001` | 最高 PM 收口 Resident Cognitive Continuity Gate | **BLOCKED** | C15-RCC-EVAL-001 | C15 full-chain evidence | 只有“形成真实认知 + fresh-window 连续 + replacement-model 连续 + later behavior consumption + 可被新现实修正 + 无循环自证”全部成立才 PASS |
| 33.1 | `POST-C15-ISSUE-RECONCILIATION-001` | 对历史 P16 issues #23/#28/#33/#34/#35 在**届时最新 main**重新做现状对账；只做治理裁决和 issue 状态同步，不重复实现已合入修复 | **BLOCKED** | C15-RCC-CLOSE-001 | historical issues #23/#28/#33/#34/#35；merged fixes PR #24/#49/#51/#54/#55；2026-09-25 PM current-main code/ancestry revalidation | 必须逐项 fresh reproduce / inspect current main；确认已修则记录 merge ancestry + current code evidence 并关闭/更新 stale issue；若仍可复现，创建新的单窗口工程 Task 并停止，本任务不得顺手修 Core；`src/`/tests/fixture/Resident evidence 零修改 |
| 34 | `C16-FEEDBACK-RULE-001` | 冻结 Resident→AIOS 系统改进反馈语义：系统摩擦/缺陷/优化建议与用户人生 World 分离，Resident 可提案但不得自行修改/裁决/合并 Core | **BLOCKED** | POST-C15-ISSUE-RECONCILIATION-001 | C15 closure + issue/current-main reconciliation + Metering/non-world governance patterns | 定义 non-world System Improvement / Habitation Feedback Ledger、证据与严重度/复现字段、去重/聚合/PM 裁决边界；明确 Resident proposal ≠ bug truth ≠ merge authority |
| 35 | `C16-FEEDBACK-IMPL-001` | 实现 non-world Resident 系统改进反馈 Ledger 与提案流水线：持久化 provenance、复现上下文、去重/聚合和 PM handoff，不自动改 Core | **BLOCKED** | C16-FEEDBACK-RULE-001 | C13 non-world ledger patterns + habitation evidence | Resident 反馈不会增加 World truth/污染用户 cognition；proposal 可跨窗口追踪；重复反馈可聚合；无自动代码修改/无自动 main merge；崩溃恢复与审计链完整 |
| 36 | `C16-FEEDBACK-RES-001` | 真实入住发现机制验证：Resident 在正常使用 AIOS 时自行发现摩擦/缺陷/低效，并形成结构化改进 Proposal；禁止向 Resident 注入预期 bug/答案 | **BLOCKED** | C16-FEEDBACK-IMPL-001 | fresh Resident model windows + ordinary AIOS use + feedback ledger | 至少形成可审计的真实体验反馈；Resident 只报告体验/证据/建议，不接触 evaluator oracle，不修改 Core，不以提案数量作为 KPI |
| 37 | `C16-FEEDBACK-PM-001` | 独立 PM/Architect 分流 Resident 改进 Proposal：复现、去重、接受/拒绝/延后，并把被接受项转成正常工程 Task | **BLOCKED** | C16-FEEDBACK-RES-001 | feedback ledger + reproducible evidence | Resident 自述不得直接成为 bug truth；至少一项接受项必须有独立复现和明确工程完成定义；拒绝/重复/证据不足也要可追溯 |
| 38 | `C16-FEEDBACK-ENG-PILOT-001` | 用独立工程 Agent 执行一项经 PM 接受的 Resident 改进 Task，并进行正常 Gate 与回归；原 Resident 不得同时充当实现者/验收者 | **BLOCKED** | C16-FEEDBACK-PM-001 | accepted engineering task from feedback triage | 独立实现→Gate→main→fresh Resident 回归完整闭环；不得自动根据 Resident proposal 直接写代码；修复必须证明未改变无关 runtime 语义 |
| 39 | `C16-FEEDBACK-CLOSE-001` | 最高 PM 收口 Resident 驱动的 AIOS 改进闭环 | **BLOCKED** | C16-FEEDBACK-ENG-PILOT-001 | C16 rule/ledger/resident/PM/engineering/regression evidence | 必须证明“Resident 发现→non-world proposal→独立复现/裁决→独立工程修复→Gate→Resident 再验证”；通过后才恢复大规模 P16 campaign |
| 40 | `P16-TRIAGE-001` | 更新 PR #37 / Issue #30 中央证据分流到当前 segmented protocol；历史无效年度、PARTIAL、机械复现、有效缺陷分开登记 | **BLOCKED** | AUDIT-001, all activated T34/T36/T28/T35/T33 tasks resolved, C16-FEEDBACK-CLOSE-001 | all historical Core blockers resolved; broad P16 paused until C14 + C15 RCC + C16 close | 冻结被评 Core SHA；不把旧“几天统计”冒充当前进度；中央报告进入 main；恢复 campaign 前必须引用 C14 + C15 RCC + C16 closure |
| 41 | `P16-CAMPAIGN-001` | 建立/恢复唯一 P16 分段入住 Campaign Ledger：找出当前 canonical life、最后有效 segment、World/checkpoint digest、累计天数/交互/认知 checkpoint | **BLOCKED** | P16-TRIAGE-001 | `reviews/internal_habitation/ARENA_RESIDENT_YEARLONG_TASK.md` | 创建 `reviews/internal_habitation/P16_SEGMENT_PROGRESS_LEDGER.md`；历史 segment 不重复跑；下一 segment ID 唯一 |
| 42 | `P16-RES-NEXT` | **一次只执行一个** Resident habitation segment（7–30 simulated days），模型本人逐次作语义判断 | **BLOCKED** | P16-CAMPAIGN-001 or previous P16-RES segment | Campaign Ledger 决定实际 segment number | 每个窗口只做 1 segment；保存 World/checkpoint/digest/时间/交互/认知计数；更新 ledger；未到 365 天则自动追加下一 `P16-RES-NEXT` |
| 43 | `P16-YEAR-AUDIT-001` | 累计达到协议年度门槛后，对完整 Resident 年度证据做独立有效性审计 | **BLOCKED** | cumulative P16-RES >= protocol thresholds | — | 验证真实模型逐次决定、时间单调、跨窗口仅从 AIOS 恢复、无 future leak / pseudo-LLM；只给 VALID / PARTIAL / INVALID evidence verdict |
| 44 | `P16-PROV-A-001` | 正式 provider/model A 在 sealed scenario bundle 上独立运行，fresh private World | **BLOCKED** | all Core blockers resolved, P16 campaign protocol stable | P16 convergence control | 完整 provider/model/config/timestamps/errors/tool calls/run artifacts；resident 不见 oracle |
| 45 | `P16-PROV-B-001` | 正式 provider/model B 在**同一 resident-visible sealed bundle**独立运行，fresh private World | **BLOCKED** | P16-PROV-A-001 | — | resident-visible fingerprint 与 A 对等；World 独立；完整 provenance |
| 46 | `P16-EVAL-001` | evaluator-only hidden-oracle 评估 A/B；不得把 harness GREEN 当 cognition PASS | **BLOCKED** | P16-PROV-A-001, P16-PROV-B-001 | — | separate evaluator artifacts；错误记忆/无证据强断言/翻案/summary misuse/dimension spam/伪经验全部有证据 |
| 47 | `P16-REDTEAM-001` | 独立红队复审正式 provider runs 与年度 Resident evidence | **BLOCKED** | P16-EVAL-001, P16-YEAR-AUDIT-001 | — | 红队报告；任何 blocker 回流为新的唯一 task row，不在本窗口顺手修 |
| 48 | `P16-CLOSE-001` | 最高 PM 只做 P16 收口裁决与治理更新，不写新 Core 功能 | **BLOCKED** | P16-REDTEAM-001 | — | 若证据满足正式 Gate：P16 PASS；否则明确 remaining blocker；同步 checkpoint/master map |
| 49 | `P17-ENTRY-001` | P17 Core Release Gate 入口审查 | **BLOCKED** | P16-CLOSE-001 = PASS | — | reproducible build、full CI、migration/current schema、release evidence；不在同窗口进入 P18 |
| 50 | `P18-REALITY-HELP-INTEGRATION-001` | 将已冻结 Core 的 Goal/Task/Action/Outcome 与真实 Android/Linux service、日历/邮件/设备/App adapter 接通；让“AI 判断该帮什么”进入可授权的现实执行闭环 | **BLOCKED** | P17 Core Release Gate = PASS | P12 execution semantics + P17 released Core + platform adapter contracts | 外部副作用只能从已授权 Action dispatch；取消/撤销继续 fail-closed；真实平台结果以 typed Outcome 回写同一 World；exactly-once/retry/restart 可审计；不得在平台层复制第二套任务/认知真相 |
| 51 | `P19-HELP-EXPERIENCE-001` | 建立面向用户的持续帮助体验：授权 UI、主动提醒/打断策略、结果解释、用户纠正入口，以及 Launcher/Voice/Digital Human 等产品表面 | **BLOCKED** | P18-REALITY-HELP-INTEGRATION-001 | P18 real execution/Outcome loop + attention/wake/policy mechanisms | 用户能看见“为什么提醒/准备/执行/失败/完成”，可撤销和纠正；prepared/queued 与 actually completed 严格分离；产品 UI 不反向污染 Core World/cognition；真实帮助效果进入后续 habitation/product acceptance |

---

## 4. 当前已经完成、禁止重做的节点

以下机制已有当前 main 证据，除非出现**最新 main 可复现 blocker**，否则不得再开“重构/重做”任务：

| Node | 状态 | Main evidence |
|---|---|---|
| AttentionWatch：AI 自己注册未来关注条件 | DONE | 已进入 main |
| Reality → Watch → Wake | DONE | 已进入 main |
| INTERRUPT / BACKGROUND / REVIEW_QUEUE | DONE | 已进入 main |
| BACKGROUND 短窗 coalescing + ATTENTION_BUNDLE | DONE | `c6e0d8ed18e5a4daa46a019f6858e2aeb7269c01` |
| Attention scheduling engineering policy | DONE | `b4a07ab827df25ac9e3e1adfe73a4fd7c192eaca` |
| BACKGROUND_DAY Wake/model-call budget enforcement | DONE | `96075ded42d5ad4eeb3a72b55aedfae78ced72d9` |
| Periodic Review budget + crash recovery | DONE | `f4ec92d9397e2d54f8959ccac8ac31d49f524f33` |
| Resident 可读取 routing/budget mechanical state | DONE | `a8b2760154ac01b87c00a1dcae194476ff617d55` |
| Provider exact token telemetry aggregation | DONE | `45d6c353b75048197c438ee5384074c5beea94d3` |
| `main@45d6c353...` merge-result Gates | DONE | cognitive-runtime, C09, P15, habitation harness, P16 convergence 等全部 SUCCESS |

注意：`C13-MTR-001` 不是重做 provider telemetry。它是在修正**计量真值的存储/崩溃边界**：把经济计量从 World/Wake 摘要迁到 non-world operations-side ledger。

---

## 5. 单任务完成写回格式

每个任务 DONE 时，必须把对应 row 更新，并在下面追加一条记录：

```text
Task ID:
Status: DONE | ALREADY_FIXED | NOT_REQUIRED | FAILED
Started from main:
Work branch:
Candidate SHA:
PR:
Merge SHA:
Required gates:
Gate run IDs / conclusions:
Evidence/report paths:
Bugs found:
Deferred issues:
Next READY task:
```

如果任务失败：

- 不要在同窗口继续“顺手修第二版”；
- 保存失败 candidate 和日志；
- 将当前 task 标 `FAILED`；
- 新增一个紧跟其后的 `<TASK>-FIX-001`，状态 `READY`；
- 新窗口修复。

### C13-MTR-001 completion — 2026-09-21

```text
Task ID: C13-MTR-001
Status: DONE
Started from main: 12dfff3868f38f5af85e237cd65f2a441793a548
Frozen WIP: arena/c13-metering-ledger-20260921 @ b6d90f2c8c7d37d0a17ed080c011e24d9e01c805
Work branch: arena/c13-metering-ledger-20260921
Candidate SHA: 47ed2de25cdcb26c8c552a3db0640a59f9a15817
Validated equivalent code tree: 63c3f7b1200028844cd60de6d320996e8e84f361 (candidate 47ed2de2 tree == tested 50f03655 tree)
PR: #47
Merge SHA: f9baacd5ac7be1646036a4e878934e77965c6640
Required gates: cognitive-runtime; fused-turn-runtime; c09-wake-dispatch; p15-periodic-review; p16-habitation-harness; p16-convergence-gate
Gate run IDs / conclusions:
- cognitive-runtime 35564798270 / SUCCESS
- fused-turn-runtime 35564798226 / SUCCESS
- c09-wake-dispatch 35564798233 / SUCCESS
- p15-periodic-review 35564798249 / SUCCESS
- p16-habitation-harness 35564798243 / SUCCESS
- p16-convergence-gate 35564798235 / SUCCESS
Evidence/report paths:
- src/aios_core/runtime/metering.py
- src/aios_core/runtime/cognitive_runtime.py
- src/aios_core/runtime/turn_runtime.py
- src/aios_core/runtime/budget_gate.py
- src/aios_core/review/periodic.py
- src/aios_core/wake/service.py
- tests/runtime/test_metering_ledger.py
- tests/runtime/test_cognitive_runtime.py
- tests/integration/test_v3_background_budget_gate.py
- tests/integration/test_v3_fused_turn_runtime.py
- tests/habitation/provider_runtime.py
- tests/habitation/test_provider_runtime.py
Bugs found:
- frozen WIP lost provider/model/response identity when provider usage was unknown, so unknown-usage replay was not idempotent
- INSERT OR IGNORE replay could hide conflicting reuse of one provider response id; now fails closed
- FusedTurnRuntime frozen WIP referenced ModelMeteringLedger without importing it
- RUNNING Periodic Review budget-window recovery rewrote started_at and collapsed cognition/write time into billing time; now original cognition time is preserved while metering uses actual execution time
- frozen OpenAI provider provenance test expected the wrong model id
Deferred issues: none inside C13-MTR-001; AUDIT-001 and all downstream tasks were intentionally not executed in this window
Next READY task: AUDIT-001 — new window only
```


### AUDIT-001 completion — 2026-09-21

```text
Task ID: AUDIT-001
Status: DONE
Started from main: e9862103a753be026edf1745c6a5d07fa56c0cf4
Work branch: audit/audit-001-issue30-current-main-20260921
Candidate SHA: f92c8b75a2059dc24a8c736a2ec7ae12345388ea
PR: #48
Merge SHA: 0ecacd8204414fd41e7ebda8e8b4521406154d3f
Required gates: audit-only; no Core/runtime implementation gate
Gate run IDs / conclusions: N/A — exact-current-source/test/reproduction evidence matrix
Evidence/report paths:
- reviews/AUDIT-001_ISSUE30_CURRENT_MAIN_EVIDENCE_MATRIX_2026-09-21.md
- governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md
- AIOS_v3.0_CURRENT_CHECKPOINT.md
Bugs found:
- T34 / #34 = STILL_OPEN
- T36 / #36 = STILL_OPEN
- T28 / #28 = STILL_OPEN
- T35 / #35 = STILL_OPEN
- T33 / #33 = STILL_OPEN
Deferred issues:
- no fixes executed in AUDIT-001
- PR #37 remains historical/open; P16-TRIAGE-001 will reconcile it after activated blockers resolve
Next READY task: T34-EXEC-001
```


### T35-RULE-001 completion — 2026-09-21

```text
Task ID: T35-RULE-001
Status: DONE
Started from main: f8a2f8e4cf53de579bd0bc69cfd85421d109d65b
Governance claim commit: f83438729b7ef0a0ba58b0c3302e1deb5f4ca6bd
Work branch: governance/t35-rule-non-action-completion-20260921
Candidate SHA: b58bbb31a04a119897890452e76461f14fd46288
PR: #53
Merge SHA: 6fcb51d6e2ecf6e2ab8ff0fa62013f094b32f21c
Required gates: governance/contract only; no Runtime/Core gate required by task
Gate run IDs / conclusions:
- N/A — source/evidence review and diff-scope verification only
Evidence/report paths:
- governance/T35_NON_ACTION_TASK_COMPLETION_EVIDENCE_RULING_2026-09-21.md
- docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md
- docs/constitution/AIOS_v3.0_Goal_Task_Constitution.md
- reviews/AUDIT-001_ISSUE30_CURRENT_MAIN_EVIDENCE_MATRIX_2026-09-21.md
- Issue #30 / #35
Exact ruling:
- every terminal Task transition must be grounded in pinned durable evidence satisfying an explicit completion contract
- ACTION_OUTCOME remains mandatory for AIOS-initiated external execution
- WORLD_EVIDENCE non-Action tasks may terminate from eligible pinned World evidence / validated durable internal artifacts without synthetic Action/Outcome
- MIXED tasks require both evidence families
- assistant raw response, unsupported Claim, Task/Goal self-reference, AI self-assertion, synthetic Outcome, circular OperationExperience and world_revision alone are not valid completion credentials
Affected files:
- governance/T35_NON_ACTION_TASK_COMPLETION_EVIDENCE_RULING_2026-09-21.md
- governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md
- AIOS_v3.0_CURRENT_CHECKPOINT.md
Runtime/Core/schema changes: none
Deferred issues:
- T35-IMPL-001 remains BLOCKED until T34-EXEC-001 is resolved; it must implement this ruling in a separate window/PR
- T34/T36/T28/T33 were not executed in this window
Next READY task: T34-EXEC-001 (new window only; not executed here)
```


### T34-EXEC-001 completion — 2026-09-21

```text
Task ID: T34-EXEC-001
Status: DONE
Started from main: f8a2f8e4cf53de579bd0bc69cfd85421d109d65b
Final clean sync base: 04f3170f5e09c7ab00ffd4233465560c78dc2423
Reproduction/WIP branch: fix/t34-exec-001-cancel-authorize-20260921
Work branch: fix/t34-exec-001-final-20260921
Pre-fix test-only SHA: d622958dc286bfae816fd4f2e36d9fb063d8252e
Candidate SHA: da14638fc0f8cf14bad6b5315988d7c7db691ac8
PR: #54
Merge SHA: 48f5e29ad564ef7c1687b5a0d81cede1452e82e8
Required gates: T34 targeted execution; P12 execution; fused-turn-runtime; C09 wake dispatch regression; P15 periodic review regression; p16-habitation-harness; p16-convergence-gate
Gate run IDs / conclusions:
- pre-fix reproduction 35566808198 / SUCCESS as evidence harness; exact pre-fix tests produced two expected failures: Failed: DID NOT RAISE <class 'ValueError'>; marker T34_REPRO_RESULT=BUG_REPRODUCED
- exact clean candidate 35566890602 / SUCCESS; T34 targeted, P12, fused-turn-runtime, C09, P15, P16 habitation and P16 convergence steps all SUCCESS
- merge-result p12-execution-gate 35567021266 / SUCCESS
- merge-result p12-execution-world 35567021273 / SUCCESS
- merge-result p16-convergence-gate 35567021258 / SUCCESS
Evidence/report paths:
- src/aios_core/execution/service.py
- tests/integration/test_v3_execution_world.py
- reviews/AUDIT-001_ISSUE30_CURRENT_MAIN_EVIDENCE_MATRIX_2026-09-21.md
- Issue #30 / #34
- PR #54
Exact reproduction:
- pre-fix authorize_action accepted a PROPOSED Action after its parent Task had already reached CANCELLED
- cancel performed inside the external authorizer callback also still returned a dispatch envelope because authorize_action re-read the newer world_revision and did not revalidate the parent
Exact fix:
- authorization now requires the parent Task to remain the exact current RUNNING revision before and after the external authorizer
- Task CANCELLED atomically forward-revises every still-PROPOSED child Action to CANCELLED; historical Action revisions are retained
- authorization freezes expected_world_revision after final revalidation, so a later concurrent write fails closed through WorldStore VERSION_CONFLICT
- restart/retry of cancelled or legacy pre-fix persisted state is rejected without calling the authorizer or writing new World revisions
- normal RUNNING Task authorization remains GREEN
Bugs found:
- parent Task state/revision was not checked during authorization
- Task cancellation did not forward-invalidate pending external Actions
- expected_world_revision was read after the authorizer callback, allowing a cancellation committed during authorization to be absorbed rather than rejected
Deferred issues:
- T35-IMPL-001 was not implemented here; its dependencies are now satisfied and it remains a separate new-window task
- T36-SEARCH-001, T28-REC-001 and T33-RECALL-001 were not executed in this window
Next READY task: T36-SEARCH-001 — new window only
```


### T28-REC-001 completion — 2026-09-21

```text
Task ID: T28-REC-001
Status: DONE
Started from main: f8a2f8e4cf53de579bd0bc69cfd85421d109d65b
Final functional-base revalidation: 48f5e29ad564ef7c1687b5a0d81cede1452e82e8 (T34-EXEC-001 included)
Work branch: fix/t28-rec-assistant-dialogue-20260921
Pre-fix test-only SHA: 6f5d6e1b95b16123a936defe9d5c948238430084
Candidate SHA: 2a16d1ffaaec877356f4f281e82d884e6ac97ab5
PR: #49
Merge SHA: e159ab30a12b819ca053085d5103460e66ef9f16
Required gates: memory-recommendation; fused-turn-runtime; p14-long-context; world-index; p16-habitation-harness; p16-convergence-gate
Gate run IDs / conclusions:
- pre-fix memory-recommendation 35566383722 / FAILURE as intended reproduction evidence; leaked assistant card excerpt: 索引是公共能力，推荐只是调用方。
- memory-recommendation 35567154409 / SUCCESS
- fused-turn-runtime 35567154468 / SUCCESS
- p14-long-context 35567154469 / SUCCESS
- world-index 35567154562 / SUCCESS
- p16-habitation-harness 35567154411 / SUCCESS
- p16-convergence-gate 35567154443 / SUCCESS
Evidence/report paths:
- src/aios_core/recommendation/proactive.py
- tests/integration/test_v3_memory_recommendation.py
- tests/integration/test_v3_fused_turn_runtime.py
- tests/integration/test_v3_long_context_continuity.py
- tests/integration/test_m0_prime_store_delta_and_search.py
- tests/habitation/test_t28_proactive_memory_boundary.py
- reviews/AUDIT-001_ISSUE30_CURRENT_MAIN_EVIDENCE_MATRIX_2026-09-21.md
- Issue #30 / #28
Exact reproduction:
- ordinary lexical proactive recommendation filtered assistant dialogue only when antecedent_fallback=true
- querying an assistant-only phrase emitted the historical assistant Observation as a proactive MemoryCard, allowing AI-authored speculation to re-enter future personalization as if it were independent user/world memory
Exact fix:
- assistant-role raw conversation Observation is excluded from proactive recommendation candidates in both ordinary and antecedent modes
- assistant raw dialogue is not deleted or rewritten; WorldSearchIndex, explicit search_world, raw drill-down and same-session continuity still expose the original text
- user raw dialogue, PLATFORM/external facts and evidence-grounded Claim candidates remain eligible
- P16 regression prevents assistant self-interpretation from recursively becoming personalization evidence
Bugs found:
- the assistant-role boundary was scoped only to antecedent_fallback instead of the proactive candidate source boundary as a whole
Deferred issues:
- T33-RECALL-001, T36-SEARCH-001 and T35-IMPL-001 were intentionally not executed or modified in this window
- no raw dialogue deletion, TopicState redesign, Claim/Summary semantic change or second recommendation engine was introduced
Next READY task: T36-SEARCH-001 — new window only; this T28 window stops
```


### C15-RCC-FIXTURE-001 completion — 2026-09-22

```text
Task ID: C15-RCC-FIXTURE-001
Status: DONE
Started from main: d65a7b24366cb612d042a3feedb92f0a3d90b02c
Initial work branch: test/c15-rcc-fixture-001-20260922-sol
Corrective branch: test/c15-rcc-fixture-001-duplicate-reveal-fix-20260922-sol
Initial gated candidate: 74ff20d06b30847557c25c08e4deabd9d4578c84
Corrective exact candidate: 629cf587f37f7cea25595e456d5e4de4c03fa7d5
PRs: #99; corrective #100
Fixture: reviews/internal_habitation/c15-rcc/v1/fixture/sealed_fixture.json
Fixture SHA256: 7ccb309d207cb6ee240fbc008ee4f535e25571f04ba7ca1b7c95bf9afb5ebf46
Event ranges: A=1..13; B=14..22; C=23..30
Required gates: C15 mechanical fixture gate; mature C14 sealed release gate; C15 subject isolation; fused runtime; canonical conversation ingest; Core-diff=0
Gate run IDs / conclusions:
- 35701591095 / SUCCESS (initial exact fixture candidate)
- 35702939513 / SUCCESS (corrective duplicate-reveal fail-closed candidate)
- C15 RCC mechanical gate: 35/35 PASS
- duplicate reveal + duplicate ack: FAIL CLOSED
- C14 semantic-repair sealed release gate: 25/25 PASS
- subject-isolation + fused runtime: PASS
- canonical conversation ingest: PASS
- src/aios_core/** diff: 0
Evidence/report paths:
- reviews/internal_habitation/c15-rcc/v1/C15_RCC_FIXTURE_001_COMPLETION_EVIDENCE_2026-09-22.md
- reviews/internal_habitation/c15-rcc/v1/evaluator/EVALUATOR_ONLY_design_notes.md
- reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_RUN_CONTRACT.md
- reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md
- reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_C_RUN_CONTRACT.md
Deferred issues:
- P12 replacement-model identity attestation remains unresolved; Phase C requires trusted external execution evidence or R6 cannot be VALID.
- Resident A/B/C semantic execution is explicitly not part of this task.
Next READY task: C15-RCC-RES-A-RERUN-001 — new real Resident A window on fixed Core with fresh private World; do not run Resident B
```

---

## 6. Resident 分段进度规则

`P16-RES-NEXT` 是唯一允许重复生成的任务族，但**每个具体 segment ID 只能执行一次**。

Campaign Ledger 至少记录：

| 字段 | 必填 |
|---|---|
| life_id | yes |
| resident_model | yes |
| core_main_sha | yes |
| segment_id | yes |
| previous_segment_digest | yes, except first |
| start_time / end_time | yes |
| cumulative_days | yes |
| real semantic checkpoints | yes |
| user interactions | yes |
| World revision | yes |
| index watermark | yes |
| World/checkpoint artifact | yes |
| segment digest | yes |
| attestation | yes |
| result | VALID / PARTIAL / INVALID |

新窗口只能执行 ledger 明确指定的 **next_segment_id**。

如果当前窗口无法完成该 segment：

- 冻结真实 checkpoint；
- 标 `PARTIAL`；
- 下一窗口继续**同一个 segment ID**；
- 不得新建下一个 segment，也不得从头重跑人生。

---

## 7. 新窗口最短提示词

工程任务窗口只需要收到：

> 你现在接手 AIOS 3.0 单窗口任务执行。Repository: `Haneof/Haneof-AIOS-Core-v3.0`。先读取 `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`，获取最新 main，严格执行第一个 READY 任务。一个窗口只允许完成一个 Task ID。完成后必须把 PR/merge SHA/Gate/evidence 写回任务表和 `AIOS_v3.0_CURRENT_CHECKPOINT.md`，然后停止，不得继续下一任务。

Resident 入住窗口在上述基础上再读取：

- `reviews/internal_habitation/ARENA_RESIDENT_YEARLONG_TASK.md`
- `governance/P16_INTERNAL_MODEL_HABITATION_REVIEW_PROTOCOL.md`
- `reviews/internal_habitation/P16_SEGMENT_PROGRESS_LEDGER.md`（建立后）

---

## 8. 本表与其他导航文件的关系

- `PROJECT_MASTER_MAP.md`：整个项目阶段地图，低频更新。
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`：当前 main 的施工现场摘要。
- **本文件**：唯一“下一窗口做什么”的执行队列。
- `P16_SEGMENT_PROGRESS_LEDGER.md`：长期入住每一段的细进度。
- `AIOS_v3.0_Fused_Baseline_Registry.md`：架构/法统解释，不承担任务排队。

若这些文件对“下一步做什么”描述不一致，以**本文件 + 最新 main 事实**为准；若涉及架构语义冲突，以 Fused Baseline Registry 为准。

---

## 9. 当前交接现场

C13 冻结现场已经由专用单窗口完成并收口：

- started main: `12dfff3868f38f5af85e237cd65f2a441793a548`
- original frozen WIP: `arena/c13-metering-ledger-20260921@b6d90f2c8c7d37d0a17ed080c011e24d9e01c805`
- final candidate: `47ed2de25cdcb26c8c552a3db0640a59f9a15817`
- PR: **#47**
- C13 squash merge / verified functional main anchor: `f9baacd5ac7be1646036a4e878934e77965c6640`
- next dedicated window action: **只执行 AUDIT-001；本 C13 窗口到此停止，不得继续审计。**


### T33-RECALL-001 completion — 2026-09-21

```text
Task ID: T33-RECALL-001
Status: DONE
Started from main: f8a2f8e4cf53de579bd0bc69cfd85421d109d65b
Work branch: fix/t33-recall-antecedent-gate-20260921
Candidate SHA: 91f1eecc1eb1a5aeb3dd2fa4566f045b6abea796
PR: #51
Merge SHA: cb8eab12e9747bece41b14d183840e2cf13bd183
Required gates: memory-recommendation; p14-long-context; fused-turn-runtime; p16-habitation-harness; p16-convergence-gate
Gate run IDs / conclusions:
- memory-recommendation 35567409150 / SUCCESS
- p14-long-context 35567409136 / SUCCESS
- fused-turn-runtime 35567409167 / SUCCESS
- p16-habitation-harness 35567409218 / SUCCESS
- p16-convergence-gate 35567409187 / SUCCESS
Additional regression gates:
- constitutional-cognition-closure 35567409138 / SUCCESS
- p9-revision-gate 35567409173 / SUCCESS
- p10-ai-world-gate 35567409295 / SUCCESS
- p11-dimension-gate 35567409158 / SUCCESS
- p12-execution-gate 35567409155 / SUCCESS
Reproduction evidence:
- pre-fix reproduction commit e962585a346949dd884e202ffc7cabb5e306161c
- p16-convergence-gate 35566569236 / FAILURE as expected
- exact Case A failure: fresh-session self-contained demonstrative incorrectly produced antecedent_recall_needed=True
Fix evidence:
- cross-session recall no longer opens from arbitrary substring occurrence of local demonstrative/continuation words
- discourse-level continuation/deixis may expose bounded candidates but deterministic Core never binds antecedent identity
- same-session continuity reads canonical P14 user.text and never assistant.text as antecedent
- duplicate substring "继续" history gate removed; discourse-level "继续。" remains supported
- first over-tight candidate was rejected by constitutional-cognition-closure; corrected candidate preserves "那这个怎么实现？" same-session continuity
- final green merge-ref tested candidate 91f1eecc against main@3cd793e3d9325c316d1bcf4beb29a0ab02c195fd; the only later main delta before merge was checkpoint documentation, not Runtime/Core/Test
Evidence/report paths:
- src/aios_core/recommendation/topic_state.py
- tests/integration/test_p16_cross_session_antecedent_recall.py
- tests/integration/test_v3_fused_turn_runtime.py
- tests/integration/test_v3_long_context_continuity.py
- tests/habitation/test_current_core_target.py
Bugs found:
- bare "这个/那个" and embedded "继续" could mechanically open unnecessary history
- P14 canonical recent-turn shape was not consumed by TopicState, so runtime same-session antecedent continuity could be lost
- first fix candidate over-tightened same-session demonstrative continuity; Gate caught and corrected before merge
Deferred issues:
- no WorldSearchIndex/query implementation changes; world-index Gate was not required by impact scope
- T36-SEARCH-001 and T35-IMPL-001 remain separate tasks and were not executed here
Next READY task: T36-SEARCH-001 — new window only; this T33 window stops
```


### T36-SEARCH-001 completion — 2026-09-21

Task ID: `T36-SEARCH-001`

Status: **DONE**

- Started from main: `f8a2f8e4cf53de579bd0bc69cfd85421d109d65b`
- Final synchronization base: `56cf9a5daa2f6873744590c379acb3dff0deb705`
- Work branch: `task/t36-search-001-structured-scalar-20260921`
- Final candidate SHA: `afc62009340f4451d15400c4860ee880296d9c7c`
- PR: #52
- Squash merge SHA: `07965029285cf3dfc0fdb5e506a65add60c76c29`
- Issue #36: closed by PR #52

#### Exact current-main reproduction

Before production code changed, test-only run `35566751016` failed on the structured Observation path:
`recall_candidates("North Mill")` returned no hit for a durable Observation whose legal
`value` was a nested mapping containing `vendor="North Mill"`. A subject-scoped structured
scalar lookup failed for the same mechanism. Root cause remained
`WorldSearchIndex._index_row()` accepting only string values from configured text fields.

#### Exact fix

The repair is confined to the rebuildable search projection:

- only `Observation.value` receives mechanical JSON-like scalar projection;
- mapping keys are emitted deterministically in sorted order;
- list order is preserved;
- string, integer, float, boolean and null scalar content becomes derived searchable text;
- the original typed Observation payload is never rewritten;
- no Claim, Summary or other semantic object is created;
- no health/psychology/causal or other semantic inference is performed by the indexer.

Regression coverage proves nested dict, list, number, boolean, null, mixed payload,
incremental catch-up, full rebuild, legacy projection rebuild/upgrade, incremental=rebuild,
subject isolation, current-version filtering, inactive/retracted/stale/tombstone filtering,
text Observation preservation, and no synthetic semantic inference.

#### Gate evidence

- `world-index` — run `35568085113` — **SUCCESS**
- `memory-recommendation` — run `35568085081` — **SUCCESS**
- `p16-habitation-harness` — run `35568085280` — **SUCCESS**
- `p16-convergence-gate` — run `35568085170` — **SUCCESS**
- `p9-revision-gate` — run `35568085180` — **SUCCESS**
- `dimension-summary` — run `35568085143` — **SUCCESS**
- `constitutional-cognition-closure` — run `35568085182` — **SUCCESS**
- fused-turn equivalent regression — run `35568044160` — **SUCCESS**; temporary
  branch-only workflow was removed before the final candidate and is absent from the PR diff.

#### Affected files

- `src/aios_core/query/search.py`
- `tests/integration/test_m0_prime_store_delta_and_search.py`
- `tests/habitation/test_t36_structured_observation_search.py`

#### Deferred / handoff

- No T33, T28, T34, T35 runtime semantics were changed.
- A transient rebase accidentally dropped the newly merged T28 search regression; final diff
  review caught it, and the candidate was replayed on latest main before acceptance. Final PR
  preserves the T28/T33 main regressions.
- Next READY task by task-board ordering: **T35-IMPL-001** — new window only.
- This T36 window stops here after checkpoint writeback.


### T35-IMPL-001 completion — 2026-09-21

```text
Task ID: T35-IMPL-001
Status: DONE
Started from main: eeb982162e0e553a34039134bde3595abd2f3607
Work branch: task/t35-impl-001-completion-evidence-20260921
Candidate SHA: 07617df8ab87550289c1498cf3df387626d55e40
PR: #55
Merge SHA: 141dc177be895f9894a05227cbb132207ebf784d
Required gates: P12 execution gate; P12 execution-world; P15 periodic review; fused-turn-runtime; C09 wake dispatch; P16 habitation harness; P16 convergence gate
Gate run IDs / conclusions:
- candidate p12-execution-gate 35569370381 / SUCCESS (76 passed across the P12 closure suite)
- candidate p12-execution-world 35569370483 / SUCCESS
- candidate p15-periodic-review 35569370484 / SUCCESS
- candidate fused-turn-runtime 35569370409 / SUCCESS
- candidate c09-wake-dispatch 35569370452 / SUCCESS
- candidate p16-convergence-gate 35569370331 / SUCCESS (full pytest -q: 330 passed)
- candidate-derived p16-habitation-harness 35569485261 / SUCCESS (92 passed); gate-only branch commit d52a51279171d10e074e92f396da03fdee49d3ee had candidate 07617df8... as its parent and only a temporary documentation trigger; branch was reset to candidate after the run
- merge-result p12-execution-world 35569585991 / SUCCESS
- merge-result p12-execution-gate 35569586060 / SUCCESS
- merge-result p15-periodic-review 35569585969 / SUCCESS
- merge-result fused-turn-runtime 35569586033 / SUCCESS
- merge-result c09-wake-dispatch 35569586006 / SUCCESS
- merge-result p16-convergence-gate 35569586008 / SUCCESS
Evidence/report paths:
- governance/T35_NON_ACTION_TASK_COMPLETION_EVIDENCE_RULING_2026-09-21.md
- src/aios_core/execution/service.py
- src/aios_core/runtime/turn_runtime.py
- tests/integration/test_v3_execution_world.py
- PR #55
Implementation evidence:
- existing Task.completion_condition now carries explicit world_evidence / action_outcome / mixed completion mode; TaskType is not overloaded
- ambiguous legacy Tasks remain fail-closed to ACTION_OUTCOME; only legacy VERIFICATION / OBSERVATION receive the ruling's narrow mechanical WORLD_EVIDENCE compatibility when no Action lineage exists
- WORLD_EVIDENCE terminal transitions require pinned current same-subject durable evidence; assistant raw dialogue, stale/retracted evidence, unsupported Claim, Task/Goal/self assertion, synthetic Outcome and Action-lineage bypasses are rejected
- Claim/Summary work-product evidence is accepted only when explicitly allowed by the Task contract and grounded in current pinned supporting evidence
- ACTION_OUTCOME requires a current real Outcome created by the execution-world platform-result path, tied to the Task's authorized terminal Action and durable outcome_reports_action dependency
- MIXED requires both eligible World evidence and real Action-linked Outcome
- COMPLETED and FAILED share the same evidence-grounded terminal boundary; absence/timeout does not create a FAILED credential
- terminal evidence relationships are persisted as typed Dependency edges and in forward-only Task state history
- identical terminal retry is idempotent across same-process and restarted service without advancing world_revision
- Resident create_task capability now exposes structured completion_condition; transition_task description no longer repeats the invalid universal Outcome rule
Regression evidence:
- external Action completion still uses Action -> authorization -> execution -> Outcome -> Task
- ordinary Observation cannot bypass ACTION_OUTCOME
- non-Action verification and internal review/Claim paths complete from eligible evidence without fake Outcome
- assistant self-assertion, synthetic Outcome, unsupported Claim, cross-subject evidence, historical/stale/retracted evidence are rejected
- non-Action FAILED requires eligible durable evidence
- retry/restart and historical revision immutability are covered
- existing T34 cancellation / stale Action / restart / cancel-authorize race tests remain GREEN in P12
Bugs found:
- terminal validation lived too early in TaskTransitionRequest and universally required typed Outcome, forcing non-Action work toward fake execution lineage
- execution service did not distinguish explicit completion evidence modes or validate terminal evidence provenance/currentness
- Resident create_task capability could not supply the structured completion contract required by T35-RULE-001
- terminal retries were not service-level idempotent after the Task revision advanced
Deferred issues:
- none inside T35-IMPL-001
- P16-TRIAGE-001 was not executed in this window and is now the next READY task
Next READY task: P16-TRIAGE-001 — new window only
```


---

## 10. C14 PM reprioritization record — 2026-09-21

A 77-day cumulative Resident run (reported as 810 World revisions with substantial Observation/Summary volume but comparatively sparse durable cognition) exposed a structural gap: Summary and AI-world cognition both exist, but current Runtime does not guarantee a durable Summary → Resident cognition-derivation opportunity.

PM decision:

- treat this as a pre-P16-campaign Core architecture blocker, not as a request to increase Claim counts;
- preserve Summary/Cognition separation;
- reuse Wake + Background Budget + Attention Bundle + the same CognitiveRuntime;
- forbid deterministic semantic-importance scoring, keyword-to-Claim logic, a second cognition database, or a second model loop;
- require real Resident validation before C14 closure;
- pause P16-TRIAGE/Campaign continuation until C14-CLOSE-001.

Canonical implementation plan:

- `governance/C14_CONTINUOUS_COGNITIVE_DERIVATION_IMPLEMENTATION_PLAN_2026-09-21.md`

New first READY task:

- `C14-RULE-001`

This planning window does not execute C14-RULE-001 or any downstream Core task.


### C14 hardening addendum — 2026-09-21

Mandatory input for every C14 window:

`governance/C14_COGNITIVE_DERIVATION_PM_HARDENING_REQUIREMENTS_2026-09-21.md`

A C14 task may not be marked DONE by demonstrating only Summary -> Claim creation. The required end-to-end target is leaf-grounded, cross-dimensional, revisable cognition that survives session/runtime replacement and is later consumed by normal AIOS behavior, with a matched negative control proving correct silence.


### C14-RULE-001 completion — 2026-09-21

```text
Task ID: C14-RULE-001
Status: DONE
Started from main: eae9f6e74f5a51b3869b2151f56ca8875e5c8372
Work branch: governance/c14-rule-001-20260921-sol
Candidate SHA: 33effe8a86af3d5a34a6b227618db82caf519c37
Ruling commit: 57d8e7f854cbcc8f90263977b3c01599e786cf1f
PR: #58
Merge SHA: f9438cce087a422ad6d2394b8f0c2a22307fe283
Required gates: governance-only semantic ruling; no Core/runtime gate required by task
Evidence/report paths:
- governance/C14_CONTINUOUS_COGNITIVE_DERIVATION_RULING_2026-09-21.md
- governance/C14_CONTINUOUS_COGNITIVE_DERIVATION_IMPLEMENTATION_PLAN_2026-09-21.md
- governance/C14_COGNITIVE_DERIVATION_PM_HARDENING_REQUIREMENTS_2026-09-21.md
Constitution / registry changes: NONE; existing Fused Baseline + mechanism constitutions already establish the controlling principles, so authoritative interpretation is sufficient.
Bugs found: no Core bug fixed in this governance task; the unresolved semantic boundary was Summary support closure / derived lineage and is now frozen.
Deferred issues: implementation belongs exclusively to C14-SCHED-001 and later tasks.
Next READY task: C14-SCHED-001
```


### C14-SCHED-001 completion — 2026-09-21

```text
Task ID: C14-SCHED-001
Status: DONE
Started from main: 26d406314850327e4965bd2d4c7e84cf7431372b
Work branch: c14/sched-cognitive-derivation-20260921
Candidate SHA: 5389118b9e37b8f0b33552099e39d5c8a31eaffb
PR: #59
Merge SHA: f0b24cda3c76d5170f5f27fb5a94107036e2f2c4
Core implementation:
- src/aios_core/contracts/enums.py
- src/aios_core/storage/sqlite_store.py
- src/aios_core/summaries/cognitive_derivation.py
- src/aios_core/summaries/scheduler.py
- src/aios_core/summaries/__init__.py
Test / gate support:
- tests/integration/test_v3_c14_cognitive_derivation_scheduler.py
- tests/habitation/current_core.py (stale merged-Wake snapshot compatibility only; no P16 task execution)
- .github/workflows/c14-cognitive-derivation-scheduler.yml
Provenance:
- derived runtime view only: REALITY / AI_COGNITION_ONLY / MAINTENANCE_ONLY / MIXED / UNKNOWN
- recursively walks exact pinned SourceRef, EvidenceSet support/member/context/counter refs, and registered support/source Dependency edges
- exact object revision SourceClass comes from the existing world_commits/object_revisions ledger
- Summary/EvidenceSet/Dependency/Wake maintenance scaffolding does not become terminal reality proof
- legacy combined conversation turns preserve assistant-vs-user provenance using already-persisted Observation role metadata; no prose/NLP/keyword/count/confidence scoring
- any unpinned, missing, corrupt, cyclic, cross-subject, or otherwise unresolved required branch forces UNKNOWN
Wake identity / idempotency:
- WakeSource.COGNITIVE_DERIVATION
- BACKGROUND attention class
- deterministic dedupe scope: c14:cognitive-derivation:<summary_object_id>:<summary_revision>
- observed_at is the durable Summary recorded_at; retry resolves to the same Wake
- revision N+1 receives a distinct opportunity; superseded/stale/partial/missing/inactive/tombstoned Summary revisions do not create new opportunities
Crash recovery:
- each MultiScaleSummaryScheduler run reconciles durable current Summary revisions before new scheduling
- post-commit ensure uses the same deterministic identity
- restart requires no second scheduler DB/cursor; a fresh scheduler over the same World re-creates only a missing opportunity and retry remains idempotent
Self-loop prevention:
- AI_COGNITION_ONLY and MAINTENANCE_ONLY do not immediate self-derive; UNKNOWN fails closed
- C14 Wake carries summary_dimension as audit metadata rather than generic metadata.dimension, so the Wake cannot re-enter future Dimension Summary source selection as same-dimension material
Gates:
- C14 scheduler acceptance workflow 35579489466 / SUCCESS
  - c14-scheduler-targeted SUCCESS
  - dimension-summary SUCCESS
  - world-index SUCCESS
  - c09-wake-dispatch SUCCESS
  - cognitive-runtime SUCCESS
  - fused-turn-runtime SUCCESS
  - p15-periodic-review SUCCESS
  - c13-metering SUCCESS
  - p14-long-context SUCCESS
  - memory-recommendation-t28 SUCCESS
  - p16-habitation-harness SUCCESS
  - p16-convergence-gate SUCCESS
- native c09-wake-dispatch 35579489436 / SUCCESS
- native dimension-summary 35579489555 / SUCCESS
- native world-index 35579489460 / SUCCESS
- native constitutional-cognition-closure 35579489456 / SUCCESS
- native p16-habitation-harness 35579489564 / SUCCESS
- native p16-convergence-gate 35579489485 / SUCCESS
Additional green: world-kernel 35579489440; p9-revision-gate 35579489464
Bugs found:
- C14 Wake audit dimension initially risked re-entering later Summary discovery through generic metadata.dimension; fixed before acceptance by using summary_dimension.
- Required habitation regression exposed stale pending-Wake snapshots after AttentionRouter mechanically merged sibling BACKGROUND Wakes; adapter now re-reads durable current state and skips already MERGED children. Core Resident/runtime semantics were not changed.
Deferred issues:
- Resident semantic consumption belongs exclusively to C14-RUNTIME-001.
- burst/budget/new-runtime loop hardening remains C14-LOOP-001 after Runtime.
Next READY task: C14-RUNTIME-001 — new window only.
```


### C14-SCHED PM acceptance note — provenance reconcile scale

C14-SCHED-001 correctness is accepted. One non-blocking long-horizon hardening item is deferred to C14-LOOP-001:

- current `CognitiveDerivationScheduler.reconcile()` iterates current Summary objects;
- each `ensure()` currently derives lineage by rebuilding the support Dependency view;
- this can cause repeated whole-Dependency scans as Summary count grows.

C14-LOOP-001 must preserve the same mechanical semantics while removing avoidable Summary×Dependency full-graph repetition, using a bounded approach such as one graph build per reconciliation pass, safe caching, or an incremental index. This is a performance/resource-safety requirement only; it must not introduce semantic ranking, a second provenance truth, or a second scheduler database.

### C14-RUNTIME-001 completion — 2026-09-21

```text
Task ID: C14-RUNTIME-001
Status: DONE
Started from main: 461a2289247eeb0cbbc39bbcfbe613022c885311
Work branch: c14/runtime-cognitive-derivation-20260921
Candidate SHA: 75cc62ca13169c6ba8752e0562224705fe6f9ac2
PR: #61
Merge SHA: a887ba537e9797d4bf5a7b7fb482fa4a55f47df7
Required gates: C14 scheduler targeted; C14 runtime targeted; cognition-writeback; cognition-revision; AI-world; cognitive-runtime; constitutional-cognition-closure; C09 wake dispatch; fused-turn-runtime; dimension-summary; world-index; P15 periodic-review; C13 metering/background-budget; P14 long-context; memory recommendation/T28; P12 execution; P16 habitation harness; P16 convergence
Candidate Gate run IDs / conclusions:
- c14-cognitive-derivation-runtime 35582197711 / SUCCESS (all 7 jobs)
- c14-cognitive-derivation-scheduler 35582197425 / SUCCESS
- constitutional-cognition-closure 35582197542 / SUCCESS
- p16-convergence-gate 35582198031 / SUCCESS
- p15-periodic-review 35582197360 / SUCCESS
- dimension-summary 35582197498 / SUCCESS
- p14-long-context 35582197567 / SUCCESS
- c09-wake-dispatch 35582197629 / SUCCESS
- p10-ai-world-gate 35582197450 / SUCCESS
- p9-revision-gate 35582197446 / SUCCESS
- p12-execution-gate 35582197586 / SUCCESS
- fused-turn-runtime 35582197662 / SUCCESS
- p11-dimension-gate 35582197613 / SUCCESS
Merge-result main Gate run IDs / conclusions:
- c14-cognitive-derivation-runtime 35582457482 / SUCCESS
- c14-cognitive-derivation-scheduler 35582457687 / SUCCESS
- p16-convergence-gate 35582457558 / SUCCESS
- p15-periodic-review 35582457662 / SUCCESS
- p10-ai-world-gate 35582457462 / SUCCESS
- dimension-summary 35582457614 / SUCCESS
- c09-wake-dispatch 35582457569 / SUCCESS
- p11-dimension-gate 35582457737 / SUCCESS
- p9-revision-gate 35582457356 / SUCCESS
- fused-turn-runtime 35582457578 / SUCCESS
- all-dimensions-projection 35582457352 / SUCCESS
- p12-execution-gate 35582457490 / SUCCESS
- p14-long-context 35582457564 / SUCCESS
Evidence/report paths:
- src/aios_core/runtime/turn_runtime.py
- src/aios_core/summaries/cognitive_derivation.py
- tests/integration/test_v3_c14_cognitive_derivation_runtime.py
- tests/integration/test_v3_c14_cognitive_derivation_scheduler.py
- .github/workflows/c14-cognitive-derivation-runtime.yml
Implementation evidence:
- COGNITIVE_DERIVATION dispatches through the same existing FusedTurnRuntime -> CognitiveRuntime and the same WakeBus/model handler/capability loop/C13 metering; no second Resident/model/World/database.
- Runtime cockpit exposes exact Wake/Summary anchor, Summary dimension/granularity/window, scheduler + runtime derived-lineage audit, current AI-world snapshot, normal capability catalog, Step-0 and background budget.
- Summary is explicitly a temporal/navigation anchor, not a semantic conclusion or sufficient proof; no expected Claim is hidden.
- Scheduler and Runtime share one lineage resolver. grounding_leaf_refs prevents old AI Claim recursion from certifying new cognition while allowing a Summary whose transitive closure reaches qualifying reality/case leaves.
- C14 guard covers commit_claim, commit_ai_world_claim, revise_claim and retract_claim; alternate experience/policy cognition channels are denied during derivation rather than becoming bypasses.
- assistant-only dialogue remains AI_COGNITION_ONLY and cannot become an independent user fact; legal user raw -> Summary -> inspected Observation can ground cognition.
- OperationExperience -> real Outcome lineage remains legal for Strategy/AI learning.
- background derivation responses are never directly delivered to the user; silence completes Wake with zero semantic write.
- C13 provider/token/model truth remains in the non-world ModelMeteringLedger.
Bugs found:
- derivation Wake used the generic Wake instruction/cockpit and could be folded by generic BACKGROUND bundling, losing the exact dedicated C14 inspection contract.
- Summary/AI cognition support closure was not enforced at the Resident cognition create/revise/retract capability boundary.
- commit_ai_world_claim and revision/retraction paths could bypass a commit_claim-only fix.
Deferred issues:
- C14-LOOP-001 only: burst/budget/merge/restart hardening, Periodic Review coexistence, new-runtime recovery/consumption, and the bounded provenance-reconcile scale item already accepted from C14-SCHED.
- C14-RES-001 and P16 campaign were not started.
Next READY task: C14-LOOP-001 — new window only; this C14-RUNTIME window stops here.
```



### C14 Runtime PM acceptance blocker — 2026-09-21

Independent PM acceptance of PR #61 found an alternate durable-write escape route.

The Claim paths are correctly leaf-grounded, but `COGNITIVE_DERIVATION` currently falls through to the normal side-effect allowlist and may still call Event / Entity / Relation / Dimension / Goal / Task / AttentionWatch / Action write capabilities that do not pass through the C14 grounding validator.

Canonical review:

- `governance/C14_RUNTIME_PM_ACCEPTANCE_REVIEW_2026-09-21.md`

Decision:

- historical `C14-RUNTIME-001` remains DONE as the merged implementation record;
- `C14-RUNTIME-HARDEN-001` is the new first READY task;
- `C14-LOOP-001` is BLOCKED until hardening passes;
- C14-RES and P16 remain blocked.


### C14-RUNTIME-HARDEN-001 completion — 2026-09-21

```text
Task ID: C14-RUNTIME-HARDEN-001
Status: DONE
Started from main: 646c5a3d0cf22cfa99c70667925ad240ea53f663
Work branch: c14/runtime-hardening-side-effects-20260921
Candidate SHA: 3accaeebe8ee1b3d420d2dfa3528ecb5e7388d86
PR: #63
Merge SHA: 09002ddf8fd1fd4af08f54ac5b190d4c39c9e25b
Required gates: C14 runtime targeted; C14 scheduler targeted; cognitive-runtime; cognition-writeback; cognition-revision; AI-world; constitutional cognition closure; fused-turn-runtime; C09 wake; P12 execution; P15 periodic review; C13 metering; P14 long context; T28 memory boundary; Dimension Summary; World Index; P16 habitation harness; P16 convergence
Gate run IDs / conclusions:
- c14-cognitive-derivation-runtime 35586168903 / SUCCESS (all 7 aggregate jobs SUCCESS)
- constitutional-cognition-closure 35586168941 / SUCCESS
- p16-convergence-gate 35586168937 / SUCCESS
- p15-periodic-review 35586168873 / SUCCESS
- fused-turn-runtime 35586168861 / SUCCESS
- c09-wake-dispatch 35586168846 / SUCCESS
- p11-dimension-gate 35586168851 / SUCCESS
- p10-ai-world-gate 35586168898 / SUCCESS
- p9-revision-gate 35586168883 / SUCCESS
- p12-execution-gate 35586168915 / SUCCESS
- p14-long-context 35586168872 / SUCCESS
Evidence/report paths:
- reviews/C14_RUNTIME_HARDEN_001_COMPLETION_EVIDENCE_2026-09-21.md
- src/aios_core/runtime/turn_runtime.py
- tests/integration/test_v3_c14_cognitive_derivation_runtime.py
Bugs found:
- COGNITIVE_DERIVATION denied Experience/Policy but fell through to the ordinary durable-write allowlist, leaving Event/Entity/Relation/Dimension/Goal/Task/Action/AttentionWatch escape routes
Fix:
- explicit C14 side-effect allowlist = commit_claim, commit_ai_world_claim, revise_claim, retract_claim
- every other current/future side-effecting capability default-denied
- read capabilities preserved; user turn / Periodic Review authorization unchanged
Deferred issues:
- C14-LOOP-001 keeps the existing loop/budget/coalescing/restart/reconcile-scale scope
Next READY task: C14-LOOP-001 — new window only
```


### C14-HARDEN PM acceptance / LOOP preflight — 2026-09-21

`C14-RUNTIME-HARDEN-001` independently accepted as PASS.

Canonical preflight:

- `governance/C14_LOOP_PM_PREFLIGHT_2026-09-21.md`

Additional explicit LOOP blockers now frozen:

- C14 derivation Wakes are currently excluded from AttentionBundle; LOOP must add contract-preserving homogeneous C14 bundling instead of naively laundering them into ordinary `ATTENTION_BUNDLE` semantics.
- C14 bundle execution must preserve the C14 cognition-only write allowlist, derivation cockpit, pinned member Summary/Wake refs, and no-user-delivery boundary.
- model/tool/capability budget exhaustion is not semantic completion and must remain durable/resumable through restart.
- previously registered provenance reconcile scale hardening remains mandatory.

`C14-LOOP-001` stays READY; C14-RES and P16 remain blocked.


### C14-LOOP-001 completion — 2026-09-21

```text
Task ID: C14-LOOP-001
Status: DONE
Started from main: c4689fd595fc9308e71332e0c0dda17e49cffb95
Work branch: c14/loop-hardening-20260921-sol
Candidate SHA: f48c3c9cfa8a24fa2e0e0220d7fe20bcda1be34d
PR: #65
Merge SHA: a385f7b3fcc71982aae0611a382502c9a37ba71e
Required gates: C14 loop/runtime/scheduler targeted; CognitiveRuntime; cognition writeback/revision; AI-world; constitutional cognition closure; C13 metering/background budget; C09 wake; Dimension Summary/World Index; P12; P14; P15; T28; P16 habitation; P16 convergence/full core
Gate run IDs / conclusions:
- c14-cognitive-derivation-loop 35591908702 / SUCCESS
- c14-cognitive-derivation-scheduler 35591908713 / SUCCESS
- c14-cognitive-derivation-runtime 35591908736 / SUCCESS
- p16-convergence-gate 35591908701 / SUCCESS
- constitutional-cognition-closure 35591908860 / SUCCESS
- p15-periodic-review 35591908756 / SUCCESS
- p14-long-context 35591908792 / SUCCESS
- p12-execution-gate 35591908744 / SUCCESS
- c09-wake-dispatch 35591908712 / SUCCESS
- fused-turn-runtime 35591908706 / SUCCESS
- dimension-summary 35591908763 / SUCCESS
- p11-dimension-gate 35591908700 / SUCCESS
- p10-ai-world-gate 35591908737 / SUCCESS
- p9-revision-gate 35591908842 / SUCCESS
Evidence/report paths:
- reviews/C14_LOOP_001_COMPLETION_EVIDENCE_2026-09-21.md
- .github/workflows/c14-cognitive-derivation-loop.yml
- src/aios_core/runtime/budget_gate.py
- src/aios_core/runtime/turn_runtime.py
- src/aios_core/summaries/cognitive_derivation.py
- src/aios_core/wake/attention.py
- src/aios_core/wake/service.py
- tests/integration/test_v3_c14_cognitive_derivation_runtime.py
- tests/integration/test_v3_c14_cognitive_derivation_scheduler.py
Bugs found:
- C14 sibling bursts lost the dedicated execution contract through ordinary bundling
- budget/tool/capability exhaustion could be misclassified as semantic completion
- partial successful cognition could be re-bundled under a fresh execution identity and duplicate semantic writes
- queued runtime-incomplete provider spend was invisible to other background budget decisions
- completed retry chains could undercount prior provider calls if only final model_rounds metadata was used
- old AI Claim -> AI Summary could immediately manufacture another C14 opportunity
- reconcile rebuilt the whole support Dependency view once per Summary
Fix:
- homogeneous execution-contract bundling with pinned member refs and effective COGNITIVE_DERIVATION restoration
- durable QUEUED runtime-incomplete lifecycle and in-place resume
- C13 MeteringLedger used as retry-spanning model-call truth
- immediate scheduling requires direct grounding_leaf_refs while mixed new-reality lineage remains eligible
- one support Dependency graph build per reconcile pass
Deferred issues:
- real semantic formation/negative-silence/revision/new-runtime behavior consumption remains exclusively C14-RES-001
- C14-CLOSE-001 remains blocked until Resident evidence is valid
- P16 remains paused until C14 closure
Next READY task: C14-RES-001 — new window only
```


### C14 real Resident validation split — 2026-09-21

The former single-window `C14-RES-001` plan is superseded by a four-window validation chain because rebuilding only FusedTurnRuntime inside one chat does not eliminate residual model/chat context.

Canonical protocol:

- `governance/C14_REAL_RESIDENT_VALIDATION_PROTOCOL_2026-09-21.md`

Required chain:

`C14-RES-FIX-001 -> C14-RES-A-001 -> C14-RES-B-001 -> C14-RES-EVAL-001 -> C14-CLOSE-001`

This changes test methodology only. No Core/runtime semantics are changed.


### C14-RES-FIX-001 completion — 2026-09-21

```text
Task ID: C14-RES-FIX-001
Status: DONE
Started from main: 01ad300bfd8a102e8b2fd5fc9bfbfb6fd5e4ff29
Work branch: c14/res-fixture-20260921-sol
Candidate SHA: e174a016c25d34c05ef096129d1c537ca5b19de8
PR: #68
Merge SHA: 796d9c357bb08f3042f103bc66260fdb3cdcd88c
Required gates: Life Director mechanical fixture/release validation only; no Resident semantic run and no Core/runtime gate required by this task
Gate run IDs / conclusions:
- fixture JSON parse / PASS
- event id uniqueness / PASS
- contiguous sequence 1..36 / PASS
- strict monotonic timestamps / PASS
- Phase A/B unique boundary 24->25 / PASS
- manifest SHA256 exact match / PASS
- sequential cursor simulation 1..36 / PASS
- Resident-visible payload label leak scan / PASS
- Resident-readable release/schema answer-key leak scan / PASS
- src/aios_core diff / NONE
Evidence/report paths:
- reviews/internal_habitation/c14-resident/fixture/sealed_fixture.json
- reviews/internal_habitation/c14-resident/fixture/fixture_manifest.json
- reviews/internal_habitation/c14-resident/release/release_contract.md
- reviews/internal_habitation/c14-resident/release/event_schema.json
- reviews/internal_habitation/c14-resident/evaluator/EVALUATOR_ONLY_design_notes.md
- reviews/internal_habitation/c14-resident/C14_RES_FIX_001_COMPLETION_EVIDENCE_2026-09-21.md
Fixture: 36 events; Phase A 24; Phase B 12; 2026-10-01T07:15:00-07:00 -> 2026-10-29T18:40:00-07:00; handoff cursor 24/25; SHA256 a0f9dfd0985560ce80f568b6cd11d46b13f5dc352a664c005fcb165ea5a67485
Bugs found: Resident-readable release contract initially contained answer-label wording inside a prohibition sentence; removed before merge so Resident-readable artifacts carry no answer-key label text.
Deferred issues: Resident semantics belong exclusively to C14-RES-A-001 / C14-RES-B-001; independent semantic judgment belongs to C14-RES-EVAL-001; no Runtime bug was repaired here.
Next READY task: C14-RES-A-001 — new window only.
```


### C14 fixture v1 PM semantic-design blocker — 2026-09-21

`C14-RES-FIX-001` remains DONE as the historical v1 fixture creation record, but independent PM review found the v1 fixture unsuitable for formal Resident semantic acceptance.

Canonical review:

- `reviews/C14_RES_FIX_001_PM_REVIEW_2026-09-21.md`

Blockers:

- Phase-A conversation dimension itself substantially states the intended positive cognition, so genuine cross-dimensional dependence is not proven.
- Phase-B 09:00 vs 11:30 decision is strongly determined by current deadline/duration facts, so correct-looking behavior would not prove prior cognition materially affected the decision.
- release contract describes but does not commit an executable blind release operator.

Decision:

- `C14-RES-FIX-002 = READY`
- `C14-RES-A-001 = BLOCKED` until v2 fixture passes PM review.


### C14-RES-FIX-002 completion — 2026-09-21

```text
Task ID: C14-RES-FIX-002
Status: DONE
Started from main: 075685b5b9b632988baa4e2de61c6d05aa469d32
Work branch: c14/res-fixture-v2-hardening-20260921-sol
Candidate SHA: aacee04cfa5390f2a63d0a5606acb909291849b6
PR: #70
Merge SHA: 510290d3b9578cd9425079a22050eb679ddb528a
Required gates: single-dimension leakage audit; Phase-B underdetermination audit; executable blind-release fail-closed tests; fixture digest/shape/chronology; main-to-candidate scope audit; no Resident semantic execution
Gate conclusions:
- positive single-dimension leakage audit / PASS: schedule, sleep, work_outcome, device_activity, conversation are each individually insufficient for the hidden high-level longitudinal synthesis
- Phase-B underdetermination audit / PASS: 09:00 early clarification and 11:00 protected initial drafting are both plausible under current Phase-B facts; no fixture-side expected action
- exact-byte blind release operator audit / 19 of 19 PASS
- reveal emits current projection only and does not advance / PASS
- ack exact pending event + durable object_id@revision required before cursor advance / PASS
- digest / version / skip / repeat / reorder / wrong-event / missing-ingest-ref failures close / PASS
- Phase A cursor 24 reveal + ack -> next 25 / PASS
- Phase A reveal 25 rejected / PASS
- Phase B requires exact 24->25 handoff and can reveal 25 / PASS
- hidden phase, evaluator content, and N+1 payload absent from reveal stdout / PASS
- fixture v2 digest / schema / sequence / unique ids / strict time monotonicity / PASS
- src/aios_core diff / NONE
- fixture-v1 mutations / NONE
GitHub Actions note: a reproducible v2 workflow is committed, but GitHub's workflow/status API emitted no run record for the app-authored PR head during this task; no CI GREEN is claimed or fabricated.
Evidence/report paths:
- reviews/internal_habitation/c14-resident/v2/C14_RES_FIX_002_COMPLETION_EVIDENCE_2026-09-21.md
- reviews/internal_habitation/c14-resident/v2/fixture/sealed_fixture.json
- reviews/internal_habitation/c14-resident/v2/fixture/fixture_manifest.json
- reviews/internal_habitation/c14-resident/v2/release/release_contract.md
- reviews/internal_habitation/c14-resident/v2/release/release_operator.py
- reviews/internal_habitation/c14-resident/v2/release/event_schema.json
- reviews/internal_habitation/c14-resident/v2/release/test_release_operator.py
- reviews/internal_habitation/c14-resident/v2/evaluator/EVALUATOR_ONLY_design_notes.md
Fixture: c14-resident-fixture-v2; 36 events; Phase A 24; Phase B 12; 2026-10-01T07:12:00-07:00 -> 2026-10-31T12:03:00-07:00; handoff cursor 24/25; SHA256 1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253
Bugs fixed in test design:
- v1 dim:conversation could substantially disclose the intended positive synthesis
- v1 Phase-B current deadline/duration arithmetic strongly selected one plan without needing durable cognition
- v1 release contract lacked an executable blind release boundary
Deferred issues: real semantic formation/consumption belongs exclusively to C14-RES-A-001 and C14-RES-B-001; independent semantic verdict belongs to C14-RES-EVAL-001; no Core/runtime repair occurred here.
Next READY task: C14-RES-A-001 — new window only.
```


### C14 fixture v2 PM durability blocker — 2026-09-21

Independent PM review accepts fixture v2 semantic design and blind reveal isolation.

Canonical review:

- `reviews/C14_RES_FIX_002_PM_REVIEW_2026-09-21.md`

Remaining blocker:

- `release_operator.py ack` currently validates only the syntax of `object_id@revision`.
- it does not prove that the referenced revision exists in the durable AIOS World or corresponds to the currently revealed event.

Decision:

- preserve fixture v2 bytes/digest unchanged;
- `C14-RES-FIX-003 = READY`;
- `C14-RES-A-001 = BLOCKED` until exact durable-ingest verification passes.


### C14-RES-FIX-003 completion — 2026-09-21

```text
Task ID: C14-RES-FIX-003
Status: DONE
Started from main: 0ec8d8bc16c2b0e572a9ae1de5cdc89c0416ea70
Work branch: c14/res-fixture-v3-durable-ack-20260921-sol
Candidate SHA: 17bd54ed0b64131ded0b70d853cac205d055bdcb
PR: #72
Merge SHA: e5c7fefce82a49735575c423da310ca3d9441ab4
Required gates: frozen fixture SHA; real SQLiteWorldStore exact revision existence/provenance; exact released-event binding; fake/wrong/previous/other/cross-subject/mismatch fail-closed; same-private-World receipt chain; reopen durability; Phase A/B boundary; future isolation; no Core diff; no Resident semantic run
Gate run IDs / conclusions:
- 35597626462 / FAILED during candidate iteration: test-copy bootstrap used fixed parents[5] and failed before durable logic; release scripts made location-independent
- 35597785208 / FAILED during candidate iteration: 27/29 durable tests passed; two wrong-event tests over-specified rejection wording although refs were correctly rejected; assertions corrected to safety state
- 35598032585 / SUCCESS: 30/30 real SQLiteWorldStore tests PASS + frozen fixture SHA PASS + no-Core-diff PASS
- 35598216907 / SUCCESS on exact candidate 17bd54ed0b64131ded0b70d853cac205d055bdcb: 30/30 PASS + frozen fixture SHA PASS + no-Core-diff PASS
Evidence/report paths:
- reviews/internal_habitation/c14-resident/v2/C14_RES_FIX_003_COMPLETION_EVIDENCE_2026-09-21.md
- reviews/internal_habitation/c14-resident/v2/release/release_operator.py
- reviews/internal_habitation/c14-resident/v2/release/mechanical_ingest_adapter.py
- reviews/internal_habitation/c14-resident/v2/release/release_contract.md
- reviews/internal_habitation/c14-resident/v2/release/test_release_operator.py
- reviews/internal_habitation/c14-resident/v2/fixture/fixture_manifest.json
- .github/workflows/c14-resident-fixture-v2.yml
Fixture proof: sealed_fixture.json was not changed; Git blob before/candidate = 7bd1935c9855ee5a71cd74b45bc693e01d21ca1b; SHA256 before/after = 1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253
World verification: existing SQLiteWorldStore object_revision_record(exact revision) + get_payload(exact revision); source_class read from world_commits provenance; prior receipt chain revalidated against the same supplied private World
Mechanical binding: subject, object type/revision, event id, sequence, occurred_at, dimension, source_kind, durable source_class, modality, payload, fixture version/digest/binding version, payload SHA256, projection SHA256
Core changes: NONE
Resident runs: 0
Deferred issues: all semantic cognition work remains exclusively C14-RES-A-001/B/EVAL; no Core/runtime changes were made here
Next READY task: C14-RES-A-001 — new window only
```


### C14-RES-FIX-003 PM acceptance — 2026-09-21

Independent PM review: **PASS**.

Canonical review:

- `reviews/C14_RES_FIX_003_PM_ACCEPTANCE_REVIEW_2026-09-21.md`

Formal exact-candidate Gate:

- run `35598216907`
- head `17bd54ed0b64131ded0b70d853cac205d055bdcb`
- conclusion `SUCCESS`

Resident A must use the Resident-safe contract and must not read fixture/evaluator/PM evidence that exposes hidden test intent.


### C14-RES-A-001 PM acceptance — 2026-09-21

Independent PM verdict: **PASS**.

Canonical review:
- `reviews/C14_RES_A_001_PM_ACCEPTANCE_REVIEW_2026-09-21.md`

Pinned evidence:
- PR #75 (leave unmerged for Resident-B blindness)
- exact head `cb9b56b7039272d932158f33bfe979eff6749c9b`
- World SHA256 `0ee338aa8f2845bb376610da3c450e09ff9cc8bec5184ca60608b2465d7ba72f`
- release-state SHA256 `e922d268fbb11364a7bb558aed60b88e7a3c075032f4fa4e1c47a84de3f765f1`

Resident A passed cross-dimensional cognition, evidence-grounded revision, matched-negative silence, future isolation, and sealed 24->25 handoff.

A narrow Phase-B transport issue was discovered during PM preflight: generic fixture-ingest plus normal `run_turn` would duplicate a user conversation utterance in World.

Therefore:
- `C14-RES-B-FIX-001 = READY`
- `C14-RES-B-001 = BLOCKED` until the canonical conversation pre-ingest/idempotent run-turn boundary is proven.


### C14-RES-B-FIX-001 completion — 2026-09-21

```text
Task ID: C14-RES-B-FIX-001
Status: DONE
Started main: 08ceb9ab3f68d5d3ececaaa26832912323d73851
Work branch: c14/res-b-canonical-conversation-ingest-20260921-sol
Exact candidate: cb3a417f3c29b29d6aa2bf364386aec12b17e623
PR: #78
Merge SHA: 1c7a8c1466911f8617ed39348a50ac8041f23715
Formal Python: 3.12.14
Exact-candidate workflow: 35631789929 / SUCCESS
Pre-evidence GREEN: 35631613259 / SUCCESS
Generic blind-release regressions: 30/30 PASS
Canonical conversation release/idempotency regressions: 15/15 PASS
Existing conversation + fused-runtime regressions: 16/16 PASS
Exact idempotency proof: precommitted canonical user Observation reused by FusedTurnRuntime.run_turn with idempotent_replay=True; no duplicate user Observation; one separate assistant Observation
Fail closed: generic fixture masquerade, missing canonical ack fields, wrong session/turn/text/time/subject/role/AI_COGNITION authority/other event/ref/revision/repeat/skip/reorder/boundary
Fixture SHA256 before/after: 1fb973499664d0d71d94a7b94071e3d7210395ea6a54ec4dcbb1ba115d069253 / unchanged
Core diff: NONE
Resident-A evidence diff: NONE
Resident-B semantic execution: 0
Completion evidence: reviews/internal_habitation/c14-resident/v2/C14_RES_B_FIX_001_COMPLETION_EVIDENCE_2026-09-21.md
Next READY: C14-RES-B-001 — new Resident window only
```


### C14-RES-B-001 PM acceptance — 2026-09-21

Independent PM verdict: **RUN COMPLETE / EVIDENCE ACCEPTED FOR EVALUATION**.

Canonical review:
- `reviews/C14_RES_B_001_PM_ACCEPTANCE_REVIEW_2026-09-21.md`

Pinned evidence:
- PR #79 — leave unmerged
- exact evidence head `546449a453e6e6dff3a2eeb2b52e7cf6786927be`
- final World SHA256 `a288fc5d11a1a73006725efdd906a7ab014d4228085c610b4a32f887cfe3d615`
- final release-state SHA256 `9281ced5013b45445574698d53ff9a2d57d5308ac5d1221e5db178efcf0c8a4f`

This acceptance marks only Resident-B task execution/provenance complete. It does **not** declare C14 semantic PASS. Independent semantic verdict remains exclusively `C14-RES-EVAL-001`.

Next READY task: `C14-RES-EVAL-001` — new independent evaluator window only.


---

## 11. Resident Cognitive Continuity roadmap revision — 2026-09-22

- C14 remains the foundational durable-cognition continuity gate. Existing evaluator verdict is NOT VALID only because E1/E5 need replacement semantic evidence; E2/E3/E4/E6 remain historical VALID findings.
- A minimal three-window C14 semantic repair chain is inserted before closure. Historical PR #75/#79 evidence remains frozen and unedited.
- The former coarse `C15-GROWTH-RULE/IMPL/RES/EVAL/CLOSE` roadmap is superseded by `C15-RCC-*`.
- Canonical C15 plan: `governance/C15_RESIDENT_COGNITIVE_CONTINUITY_TEST_PLAN_2026-09-22.md`.
- C15 is now an acceptance gate for **Resident Cognitive Continuity** rather than only an “AI growth” feature:
  - User Understanding;
  - Relationship / Role;
  - Self / Calibration;
  - Strategy / Experience;
  - fresh-window continuity;
  - replacement-model continuity;
  - later correction by reality.
- `C15-RCC-PREFLIGHT-001` must audit current P15/C14 mechanisms before any Core implementation. Existing mechanisms that already satisfy the contract are marked `ALREADY_IMPLEMENTED`; duplicate architecture is forbidden.
- Broad P16 remains blocked until C14, C15 RCC, and C16 closure.

---

## 12. C14-SEM-REPAIR-RES-001 PM evidence acceptance — 2026-09-22

```text
Task ID: C14-SEM-REPAIR-RES-001
Status: DONE (evidence accepted & frozen by PM; semantic verdict NOT PERFORMED)
Started from main: 7611fa5059f5dc8a20835cab5b312be2f43d11e8
Work branch: arena/01a0c773-haneof-aios-core-v3-0
Canonical evidence PR: #92 (OPEN / UNMERGED / PINNED — do not merge; private World must not enter main)
Exact canonical evidence head: 9e870514b57bf07c00018d7dcf7435f2702f8730
Evaluated main: 7611fa5059f5dc8a20835cab5b312be2f43d11e8
Resident session: resident-sem-repair-20260922
Run ID: resident-repair-20260922
Run directory: reviews/internal_habitation/c14-resident/semantic-repair-v1/runs/resident-repair-20260922/
PM acceptance report: reviews/C14_SEM_REPAIR_RES_001_PM_ACCEPTANCE_REVIEW_2026-09-22.md
Cursors: 15/15 sequential (Phase A = 1..6, Phase B = 7..15); durable SQLite acks independently re-verified
Semantic checkpoints: 16 (cp0001..cp0016)
Resident-authored summaries: 20 (sum0001..sum0020)
Capability calls: 18 (15 inspect_world_object / 1 commit_claim / 2 revise_claim); silences 8; response 1
Final current Claim: clm_b4df2179bb8ffec020a39ede@3 (active, confidence 0.78; durable chain rev1@wr20 -> rev2@wr44 -> rev3@wr77)
Final World revision: 83
Final World SHA256: a7a7cd9f9166eb41d3b93d85820a9c7a4ab0aa57b81787d89f395482742bae57
Release-state SHA256: 4f41d709a76e0f40ce5b0093f540cc286dde84a1906a575019199cc7a7970081
Index SHA256: ae296ee44a000eb7ea5bf122184bfb9dd65c80f14f9e94e9fb64fce039658caf
Fixture SHA256 (pinned, = main sealed fixture): 1095d5aef52061753db7d9dab558af1361b92976f2ded0e6956d70afe3e6527f
Core diff: src/aios_core/** = 0
Historical evidence diff: reviews/internal_habitation/c14-resident/v2/** = 0; PR #75 head cb9b56b7... and PR #79 head 546449a4... untouched
Old trial PR disposition: #84 ABORTED/NON-CANONICAL (closed); #85 ABORTED/NON-CANONICAL (closed); #86 SCAFFOLD ONLY (closed); #87 SCAFFOLD ONLY (closed); #88 NON-CANONICAL parallel trial r8 - DO NOT EVALUATE (closed); #89 ABORTED (confirmed, stays closed); #90 ABORTED (confirmed, stays closed); #91 SCAFFOLD ONLY / SUPERSEDED BY #92 (closed)
Evaluator rule: use PR #92 at exact head 9e870514b57bf07c00018d7dcf7435f2702f8730 ONLY
```

This acceptance covers evidence completeness and provenance only. It does **not** judge E1/E5 semantic validity. Independent semantic verdict remains exclusively `C14-SEM-REPAIR-EVAL-001`.

Next READY task: `C14-SEM-REPAIR-EVAL-001` — new independent evaluator window only.


### C14-SEM-REPAIR-EVAL-001 completion — 2026-09-22

```text
Task ID: C14-SEM-REPAIR-EVAL-001
Status: DONE
Started from main: 655e1d48c2b53dd4f5a10485a9d530ed13ca69a3 (live main re-fetched at window start)
Work branch (independent evaluator branch): arena/01a0c7a7-haneof-aios-core-v3-0
Candidate SHA: (governance/report-only window; no code candidate)
PR: evaluator PR opened from the work branch (report + governance write-back only)
Merge SHA: recorded in the PR/board after merge
Required gates: governance/report-only semantic evaluation; no Runtime/Core gate required by task
Gate run IDs / conclusions: N/A — raw-artifact semantic audit; World SHA256 a7a7cd9f9166eb41d3b93d85820a9c7a4ab0aa57b81787d89f395482742bae57, release-state SHA256 4f41d709a76e0f40ce5b0093f540cc286dde84a1906a575019199cc7a7970081, index SHA256 ae296ee44a000eb7ea5bf122184bfb9dd65c80f14f9e94e9fb64fce039658caf, fixture SHA256 1095d5aef52061753db7d9dab558af1361b92976f2ded0e6956d70afe3e6527f all independently recomputed and matched at exact evidence head 9e870514b57bf07c00018d7dcf7435f2702f8730
Evidence/report paths:
- reviews/C14_SEM_REPAIR_EVAL_001_INDEPENDENT_SEMANTIC_EVALUATION_2026-09-22.md
- governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md
- AIOS_v3.0_CURRENT_CHECKPOINT.md
Canonical evidence used: PR #92 @ 9e870514b57bf07c00018d7dcf7435f2702f8730 ONLY (OPEN/UNMERGED/PINNED, never merged); trial PRs #84-#91 not used
Verdicts issued:
- E1 Phase-A cross-dimensional cognition = VALID (claim clm_b4df2179bb8ffec020a39ede rev1@wr20 -> rev2@wr44 -> rev3@wr77; EvidenceSets evs_8e1339c961f68a7a6b5dabf4@1 (3), evs_revision_6d7a9afcc1fc70278acb2a9c@1 (6), evs_revision_911ec259592b21ccd3944479@1 (12); all 12 pinned non-Summary leaves fact-by-fact closed; hypothesis discipline maintained; confidence 0.65->0.70->0.78 evidence-backed)
- E5 later Outcome / revision behavior = VALID (plan-only window cp0007-cp0009 wrote no meeting-occurrence assertion; observed-semantics upgrade only in rev3 after cursors 10/11/12 reality; explicit Plan/Observed/Outcome labeling; external-failure cursors 13-15 produced no self-blame or unrelated-claim mutation; no semantic write after wr78)
- Repair contamination audit = clean (no pseudo-LLM/keyword->Claim/oracle/future leak in canonical bridge; snapshots+summaries 0 future refs; src/aios_core diff 0; v2 evidence diff 0; PR #75 cb9b56b7 / PR #79 546449a4 heads unchanged; fixture/evaluator/release dirs byte-identical to main)
Combined matrix: E1 VALID / E2 VALID / E3 VALID / E4 VALID / E5 VALID / E6 VALID
Overall: C14 RESIDENT SEMANTIC EVIDENCE = VALID
Bugs found: none in evidence; minor non-blocking observations recorded in the report (interpretive wording inside hypothesis-typed claim; PM report rev3 member count 11 vs durable 12; run-end pending triggers wr81/wr83 never dispatched; silence directives carry no recorded reason)
Deferred issues: none inside this task; C14-CLOSE-001 must keep PR #75/#79/#92 OPEN/UNMERGED/PINNED and respect the report's limitations section
Next READY task: C14-CLOSE-001 — new window only
```

### C14-CLOSE-001 completion — 2026-09-22

```text
Task ID: C14-CLOSE-001
Status: DONE
Final Verdict: C14 CLOSURE = PASS
Started from main: f5866974726c6327ab5a33236eed8912178d0c33
Work branch: arena/01a0c7b3-haneof-aios-core-v3-0
Closure report path: reviews/C14_CLOSE_001_FINAL_CLOSURE_REVIEW_2026-09-22.md
Core diff: src/aios_core/** = 0 files changed, 0 lines modified
Deterministic Gates: 341/341 passed (100% GREEN)
Pinned historical evidence PRs (verified OPEN, UNMERGED, PINNED):
- PR #75 @ cb9b56b7039272d932158f33bfe979eff6749c9b (Resident A)
- PR #79 @ 546449a453e6e6dff3a2eeb2b52e7cf6786927be (Resident B)
- PR #92 @ 9e870514b57bf07c00018d7dcf7435f2702f8730 (Semantic Repair Resident)
Final Semantic Evidence Matrix:
- E1: VALID (PR #92 replacement)
- E2: VALID (PR #75 original)
- E3: VALID (PR #79 original)
- E4: VALID (PR #79 original)
- E5: VALID (PR #92 replacement)
- E6: VALID (PR #75/#79/#92 non-contamination)
Combined Semantic Evidence Verdict: VALID
Limitations disposition: Provider attestation, run-end pending triggers wr81/wr83, minor wording nuances, and closed-trial scaffolding all assessed as non-blocking.
Authoritative Formal Statement:
«AIOS 已证明：durable User/World reality 可触发真实 Resident 高阶认知机会；Resident 能跨维检查真实证据形成或修正 cognition；该 cognition 能跨 fresh runtime/session 恢复并实际影响后续行为；后续真实世界证据能够修正或保留 cognition；整个过程不依赖 Summary 自证、pseudo-LLM、future leak 或 deterministic semantic inference。»
Task board final status: C14-CLOSE-001 = DONE; C15-RCC-RULE-001 = READY; C15-RCC-PREFLIGHT-001 = BLOCKED
Next READY task: C15-RCC-RULE-001 — new window only
```

governance/C15_RESIDENT_COGNITIVE_CONTINUITY_RULING_2026-09-22.md
Required gates: governance-only semantic ruling; no Runtime/Core gate required by task
Gate run IDs / conclusions: N/A — constitution/ruling review and diff-scope verification only
Core diff: src/aios_core/** = 0 files changed, 0 lines modified
Constitution / registry changes: NONE
Exact frozen contract:
- root: model can change; Resident cognition must not silently reset
- same Resident = same durable cognition lineage recoverable through legal AIOS capabilities, actually consumed, and still revisable by reality
- four families: User Understanding / Relationship-Role / Self-Calibration / Strategy-Experience
- three layers: User World / Resident Cognitive World / Current Model Runtime
- replacement-model allows style/ability/search-order change and evidence-grounded correction; forbids silent amnesia of valid cognition
- continuity != freezing; retain/strengthen/weaken/revise/retract/silence require new reality Evidence
- anti-self-proof: AI self-description cannot terminate proof; UNKNOWN is legal; planned->observed lessons must remain retrievable
- no second identity DB / persona prompt / hidden handoff memory
- R1-R9 evaluator matrix; C15 PASS iff all VALID; no averages / Claim counts / “looks smart”
- unproven replacement-model identity => R6 PARTIAL (reason INSUFFICIENT_EVIDENCE), never VALID
Bugs found: none; no Core defect was in scope
Deferred issues: mechanism audit belongs exclusively to C15-RCC-PREFLIGHT-001; fixture/Resident/evaluator remain blocked
Next READY task: C15-RCC-PREFLIGHT-001 — new window only; this window must not execute preflight
```

---

## 历史记录：2026-09-23 — C15 Resident A canonical acceptance / original B release handoff

- `C15-RCC-RES-A-RERUN-001 = DONE / ACCEPTED`.
- `C15-RCC-RES-B-001 = READY`.
- Frozen Core anchor remains exactly `bcd6bf353126318f9a97076b52ec1740d43f35a4`.
- Reviewed main before this governance close: `6abfd4d19d03a60a81b7ca336efbe3c9c726b3bb` (governance-only direct child of the frozen Core anchor; zero `src/aios_core/**` diff).
- Canonical evidence: PR #117 @ `3e51f728d7959048b75fea01d405bc837b0e8185`, retained **OPEN / UNMERGED / PINNED**.
- Anchor anomaly resolved as metadata-only: `30e0dca1f08c49ed9bacc66b49313ac536d512af` is not a resolvable Git object/ref; the evidence branch is rooted at `6abfd4d19d03a60a81b7ca336efbe3c9c726b3bb`, whose Core tree equals the frozen anchor. `ANCHOR_PROVENANCE.md`, manifest, report, and PR description were corrected without changing World, index, release/restart state, cursor/stage/checkpoint/decision, or cognition bytes.
- Phase A acceptance:
  - cursor 1..13 present, ordered, uniquely acknowledged; `next_sequence=14`; no pending reveal;
  - World revision / index watermark = `88 / 88`;
  - fresh session `resident-a-final-rerun-20260923-001`; no PR #101 session, claim, transcript, or World reuse;
  - User Understanding `clm_d95e2508b26a0292b94a7a59` rev1→rev5;
  - Relationship `clm_776c4bbfaab7540a23c418cb` rev1→rev3;
  - Strategy `clm_52276ec49967d10c72861d07` rev1→rev3;
  - Communication Experience `commexp_f3778968f998cd698281e0ee@1`;
  - Operation Experience `opexp_4c982ed6ba398f2a8404e4d0@1`;
  - planned/queued, rejected, completed, and DRAFT states remain distinct; no unsupported completion/acceptance/execution promotion.
- Canonical decision: `governance/C15_FINAL_RELEASE_DECISION_2026-09-23.md`.
- `C15-RCC-RES-C-001`, `C15-RCC-EVAL-001`, and `C15-RCC-CLOSE-001` remain BLOCKED by their declared dependencies.
- **Next unique READY: `C15-RCC-RES-B-001`.**

## 历史记录：2026-09-23 — C15-RCC-RES-B-CORRECTIVE-001 pending integration

- Status: **GATE / PENDING_MAIN_INTEGRATION**. This record is not a claim of merge or experiment completion.
- Started/reviewed main: `ed07b5890909ae09cb2a0849729662b4235c1e3b`.
- Work branch: `arena/01a0cee4-haneof-aios-core-v3-0`.
- Reviewed evidence: #121 @ `b6e5ac939bef83615292bcf9b9099d76737d82b0`; raw hashes and read-only queries recorded in corrective review.
- Candidate disposition: NOT ACCEPTED; historical evidence stays pinned; canonical A unchanged.
- Scope: governance/map/checkpoint/review/prompts only; no Core, fixture-byte, historical-evidence or test changes; no Resident run.
- Gate evidence: local document/diff-scope inspection; historical Core 19 push workflows SUCCESS; new governance PR CI must be recorded separately. PR #120 failure is still tracked, not waived.
- Integration PR: [#122](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/pull/122), OPEN / pending PM self-review and normal protected merge. Actual merge SHA / new CI conclusions must be recorded from GitHub by the integrating PM; none may be invented before merge.
- Handoff: once integrated and this task written DONE, set only `C15-RCC-RES-B-PREFLIGHT-001` READY. Release/rerun/accept/identity/C/EVAL/CLOSE remain BLOCKED.

## 2026-09-24 — C15-RCC-RES-B-CORRECTIVE-001 completed integration

- Status: **DONE**; reviewed/merged governance PR #122.
- Review type: authoring PM self-review, not an independent experiment/semantic verdict. No extra integration window required; normal branch protection honored without admin bypass.
- Accepted candidate: `bbf45baf2e2a6314483d8355c1ee8badc09aa4a9`.
- Actual main merge: `2a68df3f8901138fa3126a91063c430f69102049` at `2026-09-23T16:13:48Z` (2026-09-24 Asia/Shanghai).
- CI: C15 `35887196676` SUCCESS; C14 semantic-repair `35887196757` SUCCESS; no local tests/Resident run.
- Source/evidence scope: zero Core/tests/workflows/sealed-fixture/historical-evidence modification; #117/#121 exact heads unchanged.
- Receipt: `governance/C15_RCC_RES_B_CORRECTIVE_INTEGRATION_RECEIPT_2026-09-24.md`.
- Next unique READY after this state-writeback PR is merged: **C15-RCC-RES-B-PREFLIGHT-001**. No Resident experiment is released.