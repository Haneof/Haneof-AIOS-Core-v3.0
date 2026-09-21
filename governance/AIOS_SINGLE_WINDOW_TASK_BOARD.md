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

> 选择规则：严格从上到下。条件任务在 `AUDIT-001` 后才能激活。

| 顺序 | Task ID | 单窗口任务 | 状态 | Dependencies | 当前现场 / 证据 | 完成定义 |
|---:|---|---|---|---|---|---|
| 1 | `C13-MTR-001` | 完成 C13 non-world Metering Ledger：模型返回后立即落 operations-side meter；token 真值不再依赖 Wake World metadata；crash 后计量不丢；Periodic Review 计费时间不倒带 | **DONE** | — | PR #47; final candidate `47ed2de25cdcb26c8c552a3db0640a59f9a15817`; squash merge `f9baacd5ac7be1646036a4e878934e77965c6640`; required Gates GREEN | 已从冻结 WIP 完成、自审、专项 Gate + P16 full regression GREEN、squash merge；完整证据见 §5 完成记录 |
| 2 | `AUDIT-001` | 对 Issue #30 的 T34/T36/T28/T35/T33 与 PR #37 在**最新 main**逐项重新复核，只做裁决，不修代码 | **DONE** | C13-MTR-001 | `main@e9862103a753be026edf1745c6a5d07fa56c0cf4`; `reviews/AUDIT-001_ISSUE30_CURRENT_MAIN_EVIDENCE_MATRIX_2026-09-21.md` | 五项 current-main 裁决已落库；无 Core 修改 |
| 3 | `T34-EXEC-001` | Action 授权前重新验证父 Task/撤销状态，关闭 cancel→authorize 竞态 | **DONE** | AUDIT-001 | PR #54; candidate `da14638fc0f8cf14bad6b5315988d7c7db691ac8`; squash merge `48f5e29ad564ef7c1687b5a0d81cede1452e82e8`; repro run `35566808198`; candidate gate run `35566890602`; merge-result P12/P16 GREEN | 修复前 current-main 复现；cancel/retry/restart/race/legacy-world/history/normal-authorize 回归 GREEN |
| 4 | `T36-SEARCH-001` | 结构化 Observation scalar 派生索引，不改原 typed fact，不做语义推断 | **DONE** | AUDIT-001 | PR #52; squash merge `07965029285cf3dfc0fdb5e506a65add60c76c29`; before-fix repro run `35566751016`; final candidate `afc62009340f4451d15400c4860ee880296d9c7c`; required Gates GREEN | dict/list/number/bool/null 可检索；rebuild=incremental；subject/current/inactive/tombstone/text 语义不退化；原 typed Observation 不改写 |
| 5 | `T28-REC-001` | 普通推荐与 antecedent 路径统一隔离 assistant raw dialogue，避免把 AI 自己的话当用户事实主动推荐 | **DONE** | AUDIT-001 | PR #49; candidate `2a16d1ffaaec877356f4f281e82d884e6ac97ab5`; squash merge `e159ab30a12b819ca053085d5103460e66ef9f16`; required Gates GREEN | assistant raw dialogue 不再作为普通 proactive user/world memory；raw continuity/search/drill-down 保留；用户/外部 fact 与 evidence-grounded Claim 不退化 |
| 6 | `T35-RULE-001` | 只做“非 Action Task 的可信完成凭据”语义裁决；不改 execution 代码 | **DONE** | AUDIT-001 | `governance/T35_NON_ACTION_TASK_COMPLETION_EVIDENCE_RULING_2026-09-21.md`; PR #53; semantic candidate `b58bbb31a04a119897890452e76461f14fd46288`; squash merge `6fcb51d6e2ecf6e2ab8ff0fa62013f094b32f21c` | 唯一裁决已形成：所有 Task 终态必须真实证据化；外部执行保持 Action→Outcome；非 Action Task 可用合格 pinned World evidence / validated durable artifact；禁止 AI 自述、伪 Outcome、循环 OperationExperience |
| 7 | `T35-IMPL-001` | 按 T35-RULE-001 裁决实现 Task 完成闭环 | **READY** | T35-RULE-001, T34-EXEC-001 | T35-RULE-001 DONE; T34-EXEC-001 DONE via PR #54 / `48f5e29ad564ef7c1687b5a0d81cede1452e82e8`; dependencies satisfied; implementation remains a separate new-window task following `governance/T35_NON_ACTION_TASK_COMPLETION_EVIDENCE_RULING_2026-09-21.md` | 单独 PR；正常 Action/Outcome 不退化；非 Action Task 有合法真实凭据；P12/P15/P16 GREEN |
| 8 | `T33-RECALL-001` | 用自包含表达/跨会话省略/无前文三类对照重新验证 recall 误触；只有复现才修 | **DONE** | AUDIT-001 | PR #51; candidate `91f1eecc1eb1a5aeb3dd2fa4566f045b6abea796`; squash merge `cb8eab12e9747bece41b14d183840e2cf13bd183`; repro run `35566569236`; required Gates GREEN | Case A/B/C、same-session canonical antecedent、assistant-raw exclusion、P14/Fused/P16 回归 GREEN；Core 只暴露候选，不绑定指代 |
| 9 | `P16-TRIAGE-001` | 更新 PR #37 / Issue #30 中央证据分流到当前 segmented protocol；历史无效年度、PARTIAL、机械复现、有效缺陷分开登记 | **BLOCKED** | AUDIT-001, all activated T34/T36/T28/T35/T33 tasks resolved | PR #37 仍 open，base 较旧 | 冻结被评 Core SHA；不把旧“几天统计”冒充当前进度；中央报告进入 main |
| 10 | `P16-CAMPAIGN-001` | 建立/恢复唯一 P16 分段入住 Campaign Ledger：找出当前 canonical life、最后有效 segment、World/checkpoint digest、累计天数/交互/认知 checkpoint | **BLOCKED** | P16-TRIAGE-001 | `reviews/internal_habitation/ARENA_RESIDENT_YEARLONG_TASK.md` | 创建 `reviews/internal_habitation/P16_SEGMENT_PROGRESS_LEDGER.md`；历史 segment 不重复跑；下一 segment ID 唯一 |
| 11 | `P16-RES-NEXT` | **一次只执行一个** Resident habitation segment（7–30 simulated days），模型本人逐次作语义判断 | **BLOCKED** | P16-CAMPAIGN-001 or previous P16-RES segment | Campaign Ledger 决定实际 segment number | 每个窗口只做 1 segment；保存 World/checkpoint/digest/时间/交互/认知计数；更新 ledger；未到 365 天则自动追加下一 `P16-RES-NEXT` |
| 12 | `P16-YEAR-AUDIT-001` | 累计达到协议年度门槛后，对完整 Resident 年度证据做独立有效性审计 | **BLOCKED** | cumulative P16-RES >= protocol thresholds | — | 验证真实模型逐次决定、时间单调、跨窗口仅从 AIOS 恢复、无 future leak / pseudo-LLM；只给 VALID / PARTIAL / INVALID evidence verdict |
| 13 | `P16-PROV-A-001` | 正式 provider/model A 在 sealed scenario bundle 上独立运行，fresh private World | **BLOCKED** | all Core blockers resolved, P16 campaign protocol stable | P16 convergence control | 完整 provider/model/config/timestamps/errors/tool calls/run artifacts；resident 不见 oracle |
| 14 | `P16-PROV-B-001` | 正式 provider/model B 在**同一 resident-visible sealed bundle**独立运行，fresh private World | **BLOCKED** | P16-PROV-A-001 | — | resident-visible fingerprint 与 A 对等；World 独立；完整 provenance |
| 15 | `P16-EVAL-001` | evaluator-only hidden-oracle 评估 A/B；不得把 harness GREEN 当 cognition PASS | **BLOCKED** | P16-PROV-A-001, P16-PROV-B-001 | — | separate evaluator artifacts；错误记忆/无证据强断言/翻案/summary misuse/dimension spam/伪经验全部有证据 |
| 16 | `P16-REDTEAM-001` | 独立红队复审正式 provider runs 与年度 Resident evidence | **BLOCKED** | P16-EVAL-001, P16-YEAR-AUDIT-001 | — | 红队报告；任何 blocker 回流为新的唯一 task row，不在本窗口顺手修 |
| 17 | `P16-CLOSE-001` | 最高 PM 只做 P16 收口裁决与治理更新，不写新 Core 功能 | **BLOCKED** | P16-REDTEAM-001 | — | 若证据满足正式 Gate：P16 PASS；否则明确 remaining blocker；同步 checkpoint/master map |
| 18 | `P17-ENTRY-001` | P17 Core Release Gate 入口审查 | **BLOCKED** | P16-CLOSE-001 = PASS | — | reproducible build、full CI、migration/current schema、release evidence；不在同窗口进入 P18 |

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
