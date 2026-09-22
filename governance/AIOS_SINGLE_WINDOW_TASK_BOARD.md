# AIOS v3.0 单窗口任务执行总表

> Status: ACTIVE  
> Effective: 2026-09-21  
> Repository truth: `Haneof/Haneof-AIOS-Core-v3.0@main`  
> Current verified main anchor at board creation: `45d6c353b75048197c438ee5384074c5beea94d3`  
> Purpose: one window = one task; every completed task writes durable progress before the next window starts.

---

## 1. 最高执行规则

从本文件生效起，任何 ChatGPT / Arena / reviewer / programmer 新窗口都不得凭聊天记忆自行选择工作。

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

> 选择规则：严格从上到下。条件任务在 `AUDIT-001` 后才能激活。\n> 2026-09-21 PM reprioritization: 77-day Resident evidence exposed a missing continuous User/World → AI-world cognition-derivation bridge. C14 is now inserted before P16 campaign continuation; P16-TRIAGE is paused until C14 closure.
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
| 29 | `C15-RCC-RES-A-001` | Resident A 逐事件生活，基于真实 Outcome/feedback 自主形成或保持 User Understanding / Relationship-Role / Self-Calibration / Strategy-Experience cognition | **BLOCKED** | C15-RCC-FIXTURE-001 | PR #101 **OPEN / UNMERGED / PINNED** @ `bfbfa059e2ac616326eecdfe3ffa7a927bdc7ce2`; PRE-FIX / DIAGNOSTIC evidence; session `resident-a-c15-rcc-20260922`; cursor `1..13` run complete | Core Wake-delivery persistence gap is fixed on main, but Resident A evidence acceptance remains deferred pending independent `C15-RCC-RES-A-REPAIR-DECISION-001`; do not mutate/backfill PR #101 here. |
| 29.1 | `C15-RCC-A-WAKE-DELIVERY-CORRECTIVE-001` | 独立纠偏 PR #102 对 interrupt-Wake user delivery 的治理解释：真实 delivered AI output 属于用户-AI交流 World fact；缺失持久化时不得把 A World 交给 fresh B | **DONE** | C15-RCC-RES-A-001 evidence run | `reviews/C15_RCC_RES_A_WAKE_DELIVERY_CORRECTIVE_REVIEW_2026-09-22.md`; current-main Core audit; PR #101 exact evidence audit | 裁决 `WAKE USER-DELIVERED ASSISTANT OUTPUT PERSISTENCE = MECHANISM_GAP`；A/B 重新 BLOCKED；PR #101 保持 pre-fix diagnostic、OPEN/UNMERGED/PINNED；本窗口 Core diff 0 |
| 29.2 | `C15-RCC-WAKE-DELIVERY-FIX-001` | 最小修复真实 user-delivered non-conversation Wake assistant output 持久化：仅实际允许并返回用户的 assistant response exactly-once 写入统一用户-AI交流维度；绝不伪造 USER input | **DONE** | C15-RCC-A-WAKE-DELIVERY-CORRECTIVE-001 | PR #104; Core merge `fd9ba5de329abb025f52de76f1ab658cdafb4897`; exact final Core candidate `41f2a5da2153c55b137741fdd71983eea2a011f7`; completion evidence `reviews/C15_RCC_WAKE_DELIVERY_FIX_001_COMPLETION_EVIDENCE_2026-09-22.md`; final PR-head Gates GREEN | Delivered Wake assistant output is durable/searchable with exact Wake provenance and stable exactly-once recovery; suppressed/denied/internal/silence write 0; ordinary run_turn unchanged; no synthetic USER; PR #101 untouched. |
| 29.3 | `C15-RCC-RES-A-REPAIR-DECISION-001` | Core 修复后由独立 PM 决定 Resident A evidence 的恢复路径：可验证的纯机械 historical persistence，或 fresh World 重跑 Resident A；本任务不得预设 Path A/B | **READY** | C15-RCC-WAKE-DELIVERY-FIX-001 | PR #101 immutable pre-fix diagnostic evidence + fixed Core on main @ `fd9ba5de329abb025f52de76f1ab658cdafb4897` | Independent PM must choose Path A only if immutable exact Wake artifacts permit semantics-free, provenance-preserving, exactly-once historical persistence; otherwise Path B fresh World rerun. This Core window does not choose. |
| 30 | `C15-RCC-RES-B-001` | fresh-context Resident B 只恢复 AIOS durable state，不注入 A 聊天/总结；验证整组 Resident cognition 在新窗口中正常恢复并影响新决策 | **BLOCKED** | C15-RCC-RES-A-001 | A durable World only + normal Resident instruction | Remains blocked until `C15-RCC-RES-A-REPAIR-DECISION-001` completes and independently establishes an acceptable Resident A World; do not run B from PR #101 pre-fix World. |
| 31 | `C15-RCC-RES-C-001` | replacement-model Resident C 接管同一 AIOS World；验证“模型换、Resident 不重置” | **BLOCKED** | C15-RCC-RES-B-001 | B checkpoint + different provable model family/provider where available | 不要求同措辞/同风格；要求有效 User Understanding、Role、Self/Calibration、Strategy/Experience 仍可恢复和消费；无法证明模型身份则该轴不得判 VALID |
| 32 | `C15-RCC-EVAL-001` | 独立 evaluator 审计 Resident Cognitive Continuity；不修 Core | **BLOCKED** | C15-RCC-RES-C-001 | A/B/C artifacts + World/checkpoint/digests + hidden chronology | 分别裁决 R1 user-understanding、R2 relationship/role、R3 self/calibration、R4 strategy/experience、R5 fresh-window、R6 replacement-model、R7 behavior effect、R8 correction、R9 anti-self-proof；全部 VALID 才可收口 |
| 33 | `C15-RCC-CLOSE-001` | 最高 PM 收口 Resident Cognitive Continuity Gate | **BLOCKED** | C15-RCC-EVAL-001 | C15 full-chain evidence | 只有“形成真实认知 + fresh-window 连续 + replacement-model 连续 + later behavior consumption + 可被新现实修正 + 无循环自证”全部成立才 PASS |
| 34 | `C16-FEEDBACK-RULE-001` | 冻结 Resident→AIOS 系统改进反馈语义：系统摩擦/缺陷/优化建议与用户人生 World 分离，Resident 可提案但不得自行修改/裁决/合并 Core | **BLOCKED** | C15-RCC-CLOSE-001 | C15 closure + Metering/non-world governance patterns | 定义 non-world System Improvement / Habitation Feedback Ledger、证据与严重度/复现字段、去重/聚合/PM 裁决边界；明确 Resident proposal ≠ bug truth ≠ merge authority |
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
Next READY task: C15-RCC-RES-A-REPAIR-DECISION-001 — independent PM decision only; do not run Resident B
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

