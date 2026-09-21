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
| 13 | `C14-LOOP-001` | 持续认知派生加固：防 Summary/AI cognition 自证循环；预算/合并/延迟/恢复；Periodic Review 共存；验证 new-runtime 恢复消费路径；加固长期 provenance reconcile 复杂度 | **READY** | C14-RUNTIME-HARDEN-001 | C14 Runtime 已闭环并 merge；复用 BackgroundBudgetGate、Attention Bundle、P15 Review、现有 context/search；禁止 claim conversion rate 成为质量策略；PM 验收发现当前 reconcile 存在 per-Summary 重建 support-dependency 视图的长期重复扫描风险 | cognition-write→AI summary 不制造 storm；10+ sibling summary 可机械合并；budget defer/restart 不丢机会；Wake completion 不成为用户偏好/成功证据；新 Runtime 仅恢复 World/Index 后可正常找回 durable cognition；reconcile 不得随着 Summary×Dependency 规模产生不必要的全图重复扫描，需一次构图/缓存/增量等有界方案并有规模回归 |
| 14 | `C14-RES-001` | 真实 Resident 认知形成入住验证：跨维正例 + 同次数低证据负例 silence + 后续反例 revision + 新 session/new runtime 只恢复 AIOS World 后消费旧认知并影响行为 | **BLOCKED** | C14-LOOP-001 | 禁止 pseudo-LLM / Python 关键词答案；fresh/private World；隐藏语义期望；保存 provider/model/checkpoint/digest | 至少验证：真正跨维 cognition、正确 silence、上下文替换后的 cognition retrieval/behavior consumption、Outcome→revision；不以 Claim 数量/转化率 PASS；必须有 observable refs/decision effects 而非 CoT |
| 15 | `C14-CLOSE-001` | 独立审计 C14 规则、代码、Gate 与真实 Resident 证据；只做收口，不写新 Core 功能 | **BLOCKED** | C14-RES-001 | C14 全链证据 + deterministic gates + Resident evaluator + PM hardening requirements | 任一以下成立即 FAIL：Summary-only 自证 cognition、无跨维正例、无 negative silence、无 new-session/new-runtime 行为消费、provenance 用语义启发式/第二来源库、claim count 成质量目标、存在 wake storm；全部通过才恢复 P16 |
| 16 | `P16-TRIAGE-001` | 更新 PR #37 / Issue #30 中央证据分流到当前 segmented protocol；历史无效年度、PARTIAL、机械复现、有效缺陷分开登记 | **BLOCKED** | AUDIT-001, all activated T34/T36/T28/T35/T33 tasks resolved, C14-CLOSE-001 | all historical Core blockers resolved; C14 是 77-day Resident 新暴露的架构缺口；P16 暂停避免继续测已知缺陷 | 冻结被评 Core SHA；不把旧“几天统计”冒充当前进度；中央报告进入 main；恢复 campaign 前必须引用 C14 closure |
| 17 | `P16-CAMPAIGN-001` | 建立/恢复唯一 P16 分段入住 Campaign Ledger：找出当前 canonical life、最后有效 segment、World/checkpoint digest、累计天数/交互/认知 checkpoint | **BLOCKED** | P16-TRIAGE-001 | `reviews/internal_habitation/ARENA_RESIDENT_YEARLONG_TASK.md` | 创建 `reviews/internal_habitation/P16_SEGMENT_PROGRESS_LEDGER.md`；历史 segment 不重复跑；下一 segment ID 唯一 |
| 18 | `P16-RES-NEXT` | **一次只执行一个** Resident habitation segment（7–30 simulated days），模型本人逐次作语义判断 | **BLOCKED** | P16-CAMPAIGN-001 or previous P16-RES segment | Campaign Ledger 决定实际 segment number | 每个窗口只做 1 segment；保存 World/checkpoint/digest/时间/交互/认知计数；更新 ledger；未到 365 天则自动追加下一 `P16-RES-NEXT` |
| 19 | `P16-YEAR-AUDIT-001` | 累计达到协议年度门槛后，对完整 Resident 年度证据做独立有效性审计 | **BLOCKED** | cumulative P16-RES >= protocol thresholds | — | 验证真实模型逐次决定、时间单调、跨窗口仅从 AIOS 恢复、无 future leak / pseudo-LLM；只给 VALID / PARTIAL / INVALID evidence verdict |
| 20 | `P16-PROV-A-001` | 正式 provider/model A 在 sealed scenario bundle 上独立运行，fresh private World | **BLOCKED** | all Core blockers resolved, P16 campaign protocol stable | P16 convergence control | 完整 provider/model/config/timestamps/errors/tool calls/run artifacts；resident 不见 oracle |
| 21 | `P16-PROV-B-001` | 正式 provider/model B 在**同一 resident-visible sealed bundle**独立运行，fresh private World | **BLOCKED** | P16-PROV-A-001 | — | resident-visible fingerprint 与 A 对等；World 独立；完整 provenance |
| 22 | `P16-EVAL-001` | evaluator-only hidden-oracle 评估 A/B；不得把 harness GREEN 当 cognition PASS | **BLOCKED** | P16-PROV-A-001, P16-PROV-B-001 | — | separate evaluator artifacts；错误记忆/无证据强断言/翻案/summary misuse/dimension spam/伪经验全部有证据 |
| 23 | `P16-REDTEAM-001` | 独立红队复审正式 provider runs 与年度 Resident evidence | **BLOCKED** | P16-EVAL-001, P16-YEAR-AUDIT-001 | — | 红队报告；任何 blocker 回流为新的唯一 task row，不在本窗口顺手修 |
| 24 | `P16-CLOSE-001` | 最高 PM 只做 P16 收口裁决与治理更新，不写新 Core 功能 | **BLOCKED** | P16-REDTEAM-001 | — | 若证据满足正式 Gate：P16 PASS；否则明确 remaining blocker；同步 checkpoint/master map |
| 25 | `P17-ENTRY-001` | P17 Core Release Gate 入口审查 | **BLOCKED** | P16-CLOSE-001 = PASS | — | reproducible build、full CI、migration/current schema、release evidence；不在同窗口进入 P18 |

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
