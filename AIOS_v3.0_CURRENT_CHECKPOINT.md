# AIOS v3.0 当前工程断点

> 用途：新会话 / 新模型 / 新工程师进入仓库后的第一现场状态文件  
> 更新规则：每完成一个可验证节点立即更新；不得靠聊天记忆代替本文件  
> 仓库：`Haneof/Haneof-AIOS-Core-v3.0`  
> 分支：`main`

## 2026-09-21 单窗口执行控制

跨窗口施工的“下一任务”唯一来源：

`governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`

规则：一个窗口只执行一个 Task ID；完成后必须写回 task board + 本 checkpoint，然后停止。不得根据下方历史“下一动作”重复施工。

当前审计冻结 main：`e9862103a753be026edf1745c6a5d07fa56c0cf4`。

最近完成任务：`T34-EXEC-001` — **DONE / CORE EXECUTION RACE CLOSED**。

- Started from main：`f8a2f8e4cf53de579bd0bc69cfd85421d109d65b`
- Final clean sync base：`04f3170f5e09c7ab00ffd4233465560c78dc2423`
- Reproduction/WIP branch：`fix/t34-exec-001-cancel-authorize-20260921`
- Final work branch：`fix/t34-exec-001-final-20260921`
- Pre-fix test-only SHA：`d622958dc286bfae816fd4f2e36d9fb063d8252e`
- Current-main reproduction：Actions run `35566808198 / SUCCESS`；pre-fix 两个 T34 用例均真实出现 `Failed: DID NOT RAISE <class 'ValueError'>`，marker=`T34_REPRO_RESULT=BUG_REPRODUCED`
- Candidate：`da14638fc0f8cf14bad6b5315988d7c7db691ac8`
- PR：#54
- Squash merge：`48f5e29ad564ef7c1687b5a0d81cede1452e82e8`
- Exact-candidate Gate：run `35566890602 / SUCCESS`；T34 targeted、P12、fused-turn-runtime、C09、P15、P16 habitation、P16 convergence 全部 GREEN
- Merge-result Gates：p12-execution-gate `35567021266 / SUCCESS`；p12-execution-world `35567021273 / SUCCESS`；p16-convergence-gate `35567021258 / SUCCESS`
- Task-board completion metadata commit：`fe802801fd2f23081ef605b489f73ea831b577ef`
- 修复语义：authorize 前后都要求父 Task 仍为同一 current RUNNING revision；Task CANCELLED 时在同一提交中把仍为 PROPOSED 的子 Action 前向修订为 CANCELLED；历史 Action revision 不删除、不覆写。
- 竞态语义：final eligibility revalidation 后冻结 `expected_world_revision`；其后的并发 World 写入由 WorldStore `VERSION_CONFLICT` fail closed，不能吸收 Task cancel 后继续生成 dispatch envelope。
- restart/retry：新 SQLite store reopen 及 pre-T34 已持久化“Task cancelled / Action proposed”坏世界均被拒绝；拒绝发生在 authorizer 调用前且不增加 world revision。
- normal path：RUNNING Task 的正常 Action authorize 仍通过既有与新增 P12/P16 回归。
- 当前第一个 READY：`T36-SEARCH-001`。
- `T35-IMPL-001` 的 T35-RULE + T34 两个 dependency 现已满足，task board 状态为 READY；必须另开窗口执行，本窗口没有进入 T35 实现。
- `T28-REC-001`、`T33-RECALL-001` 仍为独立 READY；`P16-TRIAGE-001` 继续等待本轮 activated blockers 全部解决。

上一完成任务：`T35-RULE-001` — **DONE / GOVERNANCE CONTRACT ONLY**。

- Started from main：`f8a2f8e4cf53de579bd0bc69cfd85421d109d65b`
- Governance claim commit：`f83438729b7ef0a0ba58b0c3302e1deb5f4ca6bd`
- Work branch：`governance/t35-rule-non-action-completion-20260921`
- Semantic candidate：`b58bbb31a04a119897890452e76461f14fd46288`
- PR：#53
- Merge SHA：`6fcb51d6e2ecf6e2ab8ff0fa62013f094b32f21c`
- Final task-board merge-metadata commit：`f55c47bd892d738852d80f6cb783768659c02b90`
- 正式裁决：`governance/T35_NON_ACTION_TASK_COMPLETION_EVIDENCE_RULING_2026-09-21.md`
- 裁决核心：所有 Task 终态都必须由 pinned durable evidence 支撑；只有需要 AIOS 外部执行的 Task 才强制 `Action → Outcome`；纯验证/分析/Review/内部工作产物不得伪造 Action/Outcome。
- `TaskType` 不承担外部授权分类；完成证据模式与 TaskType 正交，裁决定义 `WORLD_EVIDENCE / ACTION_OUTCOME / MIXED` 三种 completion contract。
- assistant raw response、unsupported Claim、Task/Goal 自引用、AI 自述“完成”、synthetic Outcome、循环 OperationExperience、world_revision 单独存在均不得作为完成凭据。
- 本任务未修改 Runtime/Core/schema/state machine；因此不伪跑无关 Core Gate，只做法源/源码/审计证据复核与 diff-scope 验证。
- `T35-IMPL-001` 在 T35-RULE-001 完成当时保持 **BLOCKED**；现 T34-EXEC-001 已完成，实时状态以 task board 的 **READY** 为准，仍必须另开窗口/PR。

再上一完成任务：`AUDIT-001` — **DONE / AUDIT ONLY**。

- 证据矩阵：`reviews/AUDIT-001_ISSUE30_CURRENT_MAIN_EVIDENCE_MATRIX_2026-09-21.md`
- PR #48 / squash merge：`0ecacd8204414fd41e7ebda8e8b4521406154d3f`
- final governance metadata commit：`05fc6b81ed78a0903915432afe1835e5537a96c7`
- T34 / #34：`STILL_OPEN`
- T36 / #36：`STILL_OPEN`
- T28 / #28：`STILL_OPEN`
- T35 / #35：`STILL_OPEN`
- T33 / #33：`STILL_OPEN`
- AUDIT-001 未修改任何 Core/runtime/test 实现。
- PR #37 仍是旧基线上的历史中央分流证据，不能作为当前 main 的修复证明。
- 当前第一个 READY：`T36-SEARCH-001`。
- 其他已激活 READY：`T28-REC-001`、`T35-IMPL-001`、`T33-RECALL-001`。
- `T35-IMPL-001` 的 `T35-RULE-001` 与 `T34-EXEC-001` 前置均已满足，现为 READY；仍必须独立新窗口执行。
- `P16-TRIAGE-001` 继续 BLOCKED，直到本轮激活缺陷全部解决。

历史段落继续保留为工程证据。任何下方“当前 blocker=0 / 下一动作 / 唯一 blocker”表述若与本节或 task board 冲突，均视为历史快照，以本节 + task board + 最新 main 为准。

## 2026-09-21 C13-MTR-001 — non-world Metering Ledger CLOSED

- MeteringRecord / Metering Ledger 位于 operations-side SQLite table，不是 WorldObject；meter write 不推进 `world_revision`、不进入 World Index、不产生 Wake。
- 模型每轮真实返回后、capability 执行与 Wake/Review completion 前立即持久化 metering。
- Background Budget 的 token 真值来自 Metering Ledger，不再依赖 Wake World metadata。
- provider usage 缺失时记录 unknown（NULL），不伪造 0；OpenAI / Anthropic / Gemini 的 provider/model/response id provenance 可审计。
- 相同 provider response id 重放幂等；冲突重放 fail closed。
- Periodic Review 恢复时保留原 cognition/write `started_at`，实际 provider 调用按恢复当天 `recorded_at` 计费，两个时间轴明确分离。
- Safety Wake 继续绕过 BACKGROUND_DAY budget；既有安全预算语义未退化。
- PR #47 已 squash merge：`f9baacd5ac7be1646036a4e878934e77965c6640`。
- 下一任务仅为新窗口 `AUDIT-001`；本窗口停止。

## 当前快照

- 时间：2026-09-20
- 最后已验证功能代码锚点：`8ddb7a606fda375aad98a0b2545a992c2497d828`
- 验证 Gate：PR #20 accepted head `b8fa56df92fdb928e2168da2054364f6a91161fd` 的 **16 个 workflow 全部 success**；其中 `constitutional-cognition-closure` run `35508439330`、`p16-habitation-harness` run `35508439464`、`p16-convergence-gate` run `35508439468`。
- 当前项目阶段：**P16 多模型独立长期入住测试 / 真实 provider 证据阶段**
- 当前主干状态：**P0-P15 主链 + 2026-09-20 宪法认知代码收口已闭环。Adaptive Cognitive Policy、Event Dimension、CommunicationExperience、Core-owned Topic State、九档模型生成 Summary 调度、深层世界导航、Goal/Task 相关上下文和 PLATFORM provenance 已进入 main。**
- 当前 blocker：**2026-09-20 第二轮完整性复审重新发现代码级 blocker：跨 subject 隔离未统一强制、CognitivePolicy 尚未形成真实运行策略闭环、P6 多尺度 Summary 尚未接入真实 Current-Core 长期调度。另有 stable-ID 编码、fail-open broad exception、Entity/Relation 运行闭环、Event 状态机与 P16 fixture 覆盖等 HIGH 问题。真实 provider artifacts 仍缺，但已不再是唯一 blocker。**
- 下一主任务：**先按 `reviews/AIOS_V3_CODE_COMPLETENESS_REAUDIT_2026-09-20.md` 关闭第二轮代码 blocker，再扩展 P16 sealed-life 覆盖；代码闭环重新通过后才执行付费 provider cognition evidence。P17 继续禁止启动。**

## P13 已完成并通过 Gate

- 通用 SourceAdapterSpec：GREEN
- explicit source dimension：GREEN
- USER / SENSOR reality source boundary：GREEN
- Canonical Observation：GREEN
- 时区统一为 UTC，并保留原始时间表示：GREEN
- adapter_id + external_record_id + external_revision 精确幂等：GREEN
- source identity 内容冲突 fail closed：GREEN
- Payment / Order 保持独立来源维度：GREEN
- 图片/录音长期入口为 descriptor / transcript，不保存 raw binary：GREEN
- raw binary 输入会被拒绝并留下 ingest failure audit：GREEN
- 高频数值流按显式 tolerance/change-threshold 机械压缩：GREEN
- numeric change 只表示数值变化，不生成健康/心理意义：GREEN
- 旧 semantic purifier / keyword evidence classifier 明确禁止迁回：GREEN
- P13 聚合 Gate：GREEN

## P13 Post-Gate 红队加固

P13 完成后又做了一轮独立正确性审计，并通过 PR #3 合入主线：

- stable ID 改为结构化 canonical JSON 哈希，消除分隔符边界碰撞：GREEN
- Reality / failure audit / numeric 对象身份加入 `subject_id`，消除跨用户对象碰撞：GREEN
- adapter / external_record / revision 身份文本统一规范化：GREEN
- source digest 覆盖 dimension / source_class / schema / locator / interval，adapter 语义漂移 fail closed：GREEN
- durable read 只把明确 `NOT_FOUND` 当不存在；存储损坏/不可用不再被吞掉：GREEN
- Reality commit 使用确定性 operation identity，竞态窗口 exact retry 可走 WorldStore idempotency：GREEN
- numeric series 对既有对象校验 source digest，偷改 sample / policy / unit / locator 会拒绝：GREEN
- `series_id` 明确定义为一个不可变 compression batch/window 的身份：GREEN
- NaN / Infinity 在 numeric contract 边界拒绝：GREEN
- 通用 RealityRecord 支持时间区间，不再强制把日历/睡眠等区间压成时间点：GREEN
- reused existing 路径也执行 index catch-up，可修复前次提交后投影滞后：GREEN
- 原并行 PR #2 已关闭，禁止形成第二套 reality-ingest 实现：DONE
- 公共 ingest 边界重新验证 Pydantic frozen models，防止 `model_copy(update=...)` 绕过 SourceAdapter / RealityRecord / Numeric Policy 约束：GREEN
- Failure Audit 身份加入 external revision、adapter semantics、locator 与 failure digest，避免不同来源修订/Schema 漂移被错误折叠成同一个失败事件：GREEN
- numeric change 不再跨 `max_gap_seconds` 观测空洞伪造瞬时变化事件：GREEN
- numeric segment provenance 改为 range + digest，避免高频长区间把全部 source ids / locators 再复制一遍而抵消压缩收益：GREEN
- nested binary 检测支持 BaseModel/dataclass/cyclic container，防止二进制通过包装对象绕过长期事实边界或造成递归崩溃：GREEN
- 合并提交：`f21960967431d8a96e3f37de75bdcd2a3b8e81dc`
- 合并后 P13 聚合 Gate：run `35498395468` **success**
- 合并后 P13 reality Gate：run `35498395508` **success**

以上是 P13 的 post-gate hardening，不改变当前主阶段 **P14**。

## P14 已完成并通过 Gate

- `recent_turns` 不再依赖调用方维护，非空外部注入会被拒绝：GREEN
- 当前 session 的最近完整轮次从统一 WorldStore 重建：GREEN
- Conversation identity 纳入 subject，跨用户同 session/turn 不再碰撞：GREEN
- deterministic scheduler 负责选择需要总结的闭合 turn range：GREEN
- summary 内容由注入的真实模型 handler 生成，系统不写固定“认知总结”：GREEN
- round summary 以 Summary 世界对象持久化，并 pin 每条 raw user/assistant Observation：GREEN
- raw dialogue 永久保留，summary 仅作为 continuity index：GREEN
- `drill_down_conversation` 可由 summary source refs 回捞 exact raw dialogue：GREEN
- token budget 裁掉 summary 内容时仍可通过 `list_conversation_summaries` → raw drill-down 恢复：GREEN
- summary 模型失败不阻断当前用户回复，raw facts 保留；重启后待总结区间可重新发现：GREEN
- 新 session 不自动灌入旧 session summaries；跨 session 仍走 recommendation/index：GREEN
- 18 轮长会话回归：1-4 / 5-8 / 9-12 / 13-16 形成顺序 summary windows，17-18 保留 recent raw，36 条原始对话零删除：GREEN
- P14 合并 PR：#4
- P14 功能合并 SHA：`76d179d48d1bb222c3d18eb5c435dd6f0c9ba212`
- 合并后 P14 Gate：run `35499189697` **success**
- 合并后 fused runtime：run `35499189641` **success**
- P9 / P10 / P11 / P12 / P13 / conversation-world 合并后回归：**all success**

## 当前可运行数据链

```text
Phone / App / Sensor / Media
↓
SourceAdapterSpec
↓
RealityRecord / MediaDescriptor / NumericSample
↓
dedupe + UTC normalize + provenance
↓
Canonical Observation
或
mechanical numeric segment/change
↓
WorldStore
↓
WorldSearchIndex / Summary
↓
Resident AI later forms cognition
```

## P14 机制说明（已完成）

解决一个真实模型在单个长会话中超过上下文窗口后“前面聊过什么不知道”的问题。

必须保持：

```text
Raw User/AI Dialogue 永久在 World
↓
当前会话 rolling state
↓
达到 token / turn 阈值
↓
模型生成 round summary
↓
summary 作为快速 continuity index
↓
后续模型默认看：
- 最近原始轮次
- 较早 round summaries
↓
用户引用旧内容时
↓
先命中 summary
↓
再按 summary source refs / session range
   drill-down 到 exact raw dialogue
```

## P14 关键边界

1. 轮总结只服务同一长会话的 context continuity。
2. 轮总结不等于 AI对用户的认知。
3. raw dialogue 永久保留，不因“已经总结”而删除。
4. 总结由模型生成；系统负责何时要求总结、哪些轮次进入窗口、token预算。
5. 不允许 summary 用新的意义覆盖原始用户/AI原话。
6. summary 必须 pin 它覆盖的 raw conversation Observation refs。
7. 多轮总结可以进一步做 session-level summary，但仍只是 continuity index。
8. 当前会话回捞优先按 session_id / turn range 精确定位，再用文本语义辅助。
9. 新会话不自动加载旧会话全部 round summaries；跨会话仍走智能推荐/世界索引。
10. recent_turns 不应继续依赖外部调用方手工维护。

## P14 首批必读

1. `docs/constitution/AIOS_v3.0_Long_Context_Continuity_Constitution.md`
2. `docs/constitution/AIOS_v3.0_User_AI_Interaction_Dimension_Constitution.md`
3. `src/aios_core/ingest/conversation.py`
4. `src/aios_core/context/controller.py`
5. `src/aios_core/runtime/turn_runtime.py`
6. `src/aios_core/summaries/dimension_summary.py`
7. `src/aios_core/query/search.py`

## P14 禁止事项

- 不删除 raw dialogue 来解决 token 限制。
- 不把 round summary 写成 User Understanding Claim。
- 不让系统用固定模板生成“认知总结”。
- 不跨 session 默认灌入所有历史。
- 不把 long-context continuity 与智能推荐重新混成一个机制。
- 不把 summary 当 source of truth。
- 不因 context budget 截断而静默丢失可回捞路径。

## P15 已完成并通过 Gate

- deterministic scheduler 只决定 review 时间与 bounded candidate window：GREEN
- review anchor 全部使用 pinned world refs：GREEN
- Review Wake 生命周期 NEW → RUNNING → COMPLETED：GREEN
- crash 后 RUNNING review 可在重启后恢复：GREEN
- 无新 world changes 时写 SUPPRESSED marker，不调用模型：GREEN
- 完成边界使用 exclusive-start，review 自己的同刻 writeback 不机械触发下一轮：GREEN
- Periodic Review 复用同一个 Resident Cognitive Runtime 与 CapabilityRegistry：GREEN
- review instruction 不伪造成用户 Conversation Observation：GREEN
- review anchors 通过分页能力按需读取，不把完整世界塞进固定 cockpit：GREEN
- Resident AI 可在 review 中 revise / retract 旧 Claim：GREEN
- Resident AI 可形成 Calibration / Strategy / Self 等 evidence-grounded cognition：GREEN
- OperationExperience 必须引用至少一个 pinned real case：GREEN
- OperationExperience 与 CommunicationExperience 进入统一世界索引：GREEN
- scheduler 本身不生成“用户成长/AI成长/策略更好”等语义结论：GREEN
- P15 宪法：`docs/constitution/AIOS_v3.0_Periodic_Review_Growth_Constitution.md`
- P15 功能锚点：`3261eae4967632ea4ef72669ef53ef3dfe5199a7`
- P15 Gate：run `35499766871` / **success**

## P16 入住测试发现并关闭：C09 Wake 调度闭环

2026-09-20 的严格顺序 blind self-resident habitation 暴露出一个实现缺口；回查旧仓 `Haneof/fantonghui@aios-2.0` 的 v3.0 正式法统后确认：

- Observation **默认只写入世界，不直接唤醒 AI**；
- 第 77~83 条要求机械触发只负责“是否值得叫醒 AI”，不得替 AI 形成语义结论；
- ADJ-003 要求机械命中统一经过 Wake 去重 / 合并 / 冷却；
- Wake Reason 是任务第一指针，不是认知结论；
- Task 到期与 periodic review 都是合法 Wake 来源；
- Step-0 负责确定性安全 / 方便度 / 信道 / 预算门禁。

因此原实验中“RealityIngest 不直接唤醒 AI”不是 bug。真正缺口是 **机械 Trigger → Wake Bus → Step-0 → 通用 Wake Dispatcher → 同一 Resident Runtime** 的中央接线。

现已通过 PR #7 合入：

- 初始闭环 SHA：`6f1e20307cd1ce47aefff281f652da16af635992`
- 当前加固功能 SHA：`02b3f006d77c6396e3f8575e8547a5363582738f`
- `WakeBus`：GREEN
- exact trigger retry 幂等：GREEN
- 连续命中合并：GREEN
- cooldown suppression：GREEN
- Step-0 `OK / QUIET / HARD_BLOCK`：GREEN
- model 暂不可调用时 Wake 保留为 `QUEUED`：GREEN
- 注册 Observation 机械规则：GREEN
- P13 `numeric_change + mechanical_threshold_event` → 注册规则 → Wake：GREEN
- 通用 `FusedTurnRuntime.run_wake()`：GREEN
- `TASK_DUE Wake` → 同一 Resident CognitiveRuntime → Task 后续状态：GREEN
- QUIET 时允许后台认知但禁止对外投放：GREEN
- background Wake 不伪造 Conversation Observation：GREEN
- P15 Review → Task → P12 TASK_DUE → C09 Resident Dispatch 跨阶段闭环：GREEN
- P12 / P14 / P15 / fused runtime / P9-P11 / world kernel/index 回归：全部 GREEN
- 合并后初始 main 验证：`c09-wake-dispatch` run `35501126516` / **success**
- Wake dedupe identity hardening：`wake_source + rule_id + dedupe_key` 共同定义合并作用域；延迟 exact retry 仍幂等；新 out-of-order hit fail closed：Gate run `35501301595` / **success**

实验 PR #5 与旧基线 PR #6 已关闭，仅保留历史证据；不得合入。

## P16 Long-Horizon Habitation Hardening 已完成

- PR #10：squash merge
- 合并 SHA：`1fc7b9f5c69b01f01dac8097efd29973bc4dbf4c`
- merge-result Gate：`p16-habitation-harness` run `35503797730` / **success**
- 虚拟时钟按真实中间时间点执行 Task due / C09 Wake / Periodic Review：GREEN
- `end_at` 最终 horizon：GREEN
- P13 `MediaDescriptorRecord` / `NumericSample` 路径：GREEN
- 注册 mechanical marker → C09 Wake：GREEN
- 每个模型 fresh private SQLite World：GREEN
- visible-life fingerprint 不受 evaluator scenario id/version/seed 污染：GREEN
- sensor numeric future sample leak fail closed：GREEN
- 现有 fixture bundle 身份与路径隔离规则保留：GREEN

## P16 当前目标

用多个真实模型、隐藏虚拟人生和长时间跨度数据测试：

> AIOS 中的模型是否真的依靠世界、索引、Summary、认知修正、Goal/Action/Outcome 与周期 Review 逐渐形成连续理解，而不是靠测试脚本偷做认知。

P16 benchmark foundation 已合入 main：

- PR #1：已 squash merge，主线合并 SHA `3e8c9a1ac5da5d342966807cbc3602a48888443d`
- Current-Core adapter：`tests/habitation/current_core.py`
- Harness / fixture / evaluator：`tests/habitation/**`
- 主线 P16 Gate：run `35503409815` / **success**
- PR #5：历史实验证据已关闭，不合并

P16 必须重点验证：

```text
隐藏人生事件流
↓
Reality / Conversation 进入 World
↓
真实 Resident Model 多轮入住
↓
模型自主形成 / 修正 cognition
↓
Goal / Task / Action / Outcome
↓
Periodic Review
↓
跨天 / 跨阶段继续运行
↓
评价：
- 是否记住真正相关历史
- 是否会找错记忆
- 是否会形成错误高阶理解
- 是否会自我强化错误
- 是否会根据新证据翻案
- 是否会创建无意义维度
- 是否会把 summary 当事实
- 是否会在没有 Outcome 时伪造经验
- 是否能在重启/换模型后继续生活在同一个 World
```

## P16 禁止事项

- 不把 expected answer 写进模型可见输入。
- 不用数万道固定题让程序几秒钟字符串匹配“通过”。
- 不写小程序替 Resident AI 做总结、认知、因果或人格判断。
- 测试 harness 可以机械计分事实可追溯性、引用正确性、状态机与泄漏，但不能替模型完成认知任务。
- 隐藏 ground truth 只能用于 reviewer 评分，Resident Model 不得看到。
- 多 Agent 是多个模型分别入住/测试同一套 AIOS 机制，不是让一堆 Agent 在世界里互相协作完成固定答案。
- P16 分支不得重新造第二套 World、Index、Recommendation、Runtime 或 Review 系统。

## 当前工程断点

- 时间：2026-09-20 17:40 +08:00
- 最后已验证功能代码锚点：`6b68cb2953d7747a784c1a5a737c66f9de101f29`
- 最近 Green Gate：`p16-habitation-harness` run `35503409815` / **success**
- 当前阶段：**P16 多模型独立长期入住测试**
- 已完成：**PR #1 对齐/审计/合并；Current-Core target；private world isolation；strict resident/oracle bundle identity validation；main 分支 P16 CI**
- 当前 blocker：**真实 provider model 尚未接入 benchmark runner，因此目前只能证明 harness/隔离/AIOS 接线正确，不能声称长期认知能力已通过。**
- 下一动作：**实现/接入 provider-backed ModelHandler 与 RoundSummaryHandler，运行多个真实模型各自独立入住同一隐藏人生，并保存可审计 artifacts；随后做 evaluator-only 评估。**

## 当前不可推翻的已决事项

- 世界唯一、索引公共。
- 推荐负责“当前要不要给哪些历史”；索引负责“到哪里找”。
- 同一长会话 continuity 是独立机制，不替代跨会话推荐。
- 原始对话是事实，轮总结只是索引。
- 模型负责总结内容，系统负责调度。
- AI认知必须另走 Claim / Evidence / Revision。

## 恢复现场规则

接手时先获取 GitHub `main` 实时 HEAD，并审查本文件功能锚点之后的 commits / CI。纯地图/checkpoint文档提交可越过；功能代码必须先确认 Gate 与边界再继续。


## P16 收口控制（2026-09-20）

- 收口控制文件：`governance/P16_CONVERGENCE_CONTROL_2026-09-20.md`
- 当前唯一允许继续施工的目标：**provider-backed real-model habitation**。
- 当前 GitHub open PR：**0**；历史 merge/superseded/experiment 分支全部冻结为证据，不得恢复后直接合入。
- 隔离审查分支：`p15/periodic-review-growth-20260920`、`p16/habitation-integration-20260920`、`hardening/p15-review-growth-redteam-20260920`。这些分支只允许读取以恢复“当前 main 确实缺失”的测试/缺陷证据，禁止整分支 merge/rebase 后继续开发。
- P17 暂停启动，直到 P16 完成真实 provider 入住、可审计 artifacts 与 evaluator-only 红队评估。
- 新施工必须从最新 `main` 创建单一 P16 provider 分支，不得重造 World / Index / CognitiveRuntime / Review。


## P16 Provider / Evaluator 基础设施闭环（2026-09-20）

- 当前 main 功能锚点：`d4e467620fe67e2af681a641176c3773a701e42f`
- 当前 GitHub open PR：**0**
- 唯一 P16 施工分支：`p16/provider-backed-habitation-20260920`；已同步到 main，**ahead=0**。

本轮已完成并进入 main：

1. **P15 correctness hardening**
   - PR #12 / merge `a9a84670a18972e70f0e14f1d09d1a1e685e4bb4`
   - OperationExperience 真实结果/subject 边界；
   - assistant 自己的 Observation 不得作为真实结果；
   - Review backlog 分页，禁止 truncation 永久漏证据；
   - budget exhaustion 保持 RUNNING / resumable；
   - OperationExperience 完整 canonical identity。

2. **restart / model handoff**
   - PR #13 / merge `ffa7fd8f6a46189e8fb38eb908924e2826674cc2`
   - 可重新打开同一个 SQLite World；
   - session turn cursor 从 World 恢复；
   - 周期 Review 调度从 durable Wake / World 恢复；
   - replacement resident model 可继续同一 World；
   - run model identity 与 target model identity 强绑定。

3. **versioned oracle / evaluator contract**
   - PR #14 / merge `63a078521125ca8e011337b83495e6e629e47b7f`
   - `aios.p16.oracle.v1`；
   - evaluator 必须精确覆盖全部 criteria；
   - evaluator provider/model/version/config provenance 进入报告；
   - comparison 不允许混用不同 evaluator provenance。

4. **provider-backed resident protocol adapters**
   - PR #15 / merge `ad77187b8c98c3d29b910889b0c9adcbf1ae2813`
   - OpenAI Responses；
   - Anthropic Messages tool use；
   - Gemini Interactions function calling；
   - AIOS capability shorthand 单向翻译为 JSON Schema；
   - provider-backed RoundSummaryHandler；
   - provider/model/config/request/usage/error provenance；
   - API key 不得进入 artifact。

5. **oracle-free real-provider resident runner**
   - PR #16 / merge `9e6d4979749c8b9316317cfdd621300cbc4cb469`
   - resident runner 只加载 manifest + resident stream；
   - resident 进程不打开 oracle；
   - 输出 `launch.json` / `world.sqlite` / `run.json`；
   - 失败输出 `failure.json`；
   - manual-only Actions workflow，确定性 CI 不自动产生 provider 费用。

6. **separate post-run provider evaluator**
   - PR #17 / merge `7676ad51b2b335178b2f98911775709240dbc979`
   - 独立 evaluator CLI / workflow；
   - 先核对 scenario id / version / resident-visible fingerprint；
   - 只有核对通过后才加载 hidden oracle；
   - evaluator 不重新运行、不修改 resident World。

7. **offline multi-model evidence comparison**
   - PR #19 / merge `d4e467620fe67e2af681a641176c3773a701e42f`
   - 严格加载 provider evaluation artifacts；
   - 拒绝不同 visible-life fingerprint；
   - 拒绝 resident model identity 篡改；
   - 要求相同 evaluator provenance；
   - 只输出 criterion-by-model matrix；
   - 禁止 aggregate score / ranking / winner。

最新 comparison head 的 Gate：

- `p16-habitation-harness` run `35506311307` / **success**
- `p16-convergence-gate` run `35506311297` / **success**

### 当前唯一剩余 P16 blocker

**尚未产生真实付费 provider 的入住 artifacts。**

代码基础设施已经具备从：

`resident-only sealed life -> real provider resident -> private World -> run artifact -> separate oracle evaluator -> offline multi-model comparison`

的完整链路。

P16 仍然是 **CONTINUE / NOT PASS**，因为机械/协议/隔离测试通过不能替代真实 resident cognition 证据。

下一动作不再是写新的 Core 或 benchmark 框架，而是：

1. 为至少两个真实 provider/model 配置 API secret；
2. 对同一 sealed life 分别手动运行 resident workflow；
3. 核对所有候选的 `scenario_public_fingerprint` 完全一致；
4. 保存 provider/run provenance 和 World artifacts；
5. 用同一个 evaluator configuration 分别做 post-run oracle evaluation；
6. 离线 comparison；
7. 独立红队审查实际 cognition：错误记忆、自我强化、revision、summary misuse、dimension spam、无 Outcome 伪经验；
8. 证据成立后才允许宣布 P16 PASS 并进入 P17。


## 2026-09-20 宪法认知代码收口 — 已合入 main

历史审查：

- `reviews/AIOS_V3_CONSTITUTION_CODE_ALIGNMENT_AUDIT_2026-09-20.md`

收口报告：

- `reviews/AIOS_V3_CONSTITUTION_CODE_ALIGNMENT_CLOSURE_2026-09-20.md`

合并：

- PR #20：`core: close remaining constitutional cognition gaps`
- accepted head：`b8fa56df92fdb928e2168da2054364f6a91161fd`
- squash merge：`8ddb7a606fda375aad98a0b2545a992c2497d828`

本轮正式关闭旧审查中确认的代码缺口：

1. **Adaptive Cognitive Policy**
   - 进入统一 WorldStore；
   - 版本 / evidence / mutable_by_ai / evaluation_window / rollback_pointer；
   - hard boundary / engineering parameter 不可由普通 AI 更新放宽；
   - rollback 为 forward revision，不改写历史。

2. **Event Dimension**
   - Resident 可 `form_event`；
   - pinned evidence；
   - revise / resolve / reject / merge / split；
   - EvidenceSet / Dependency 同世界持久化。

3. **Generic Multi-Scale Summary**
   - 日 / 周 / 月 / 季 / 半年 / 年 / 3年 / 5年 / 10年九档；
   - deterministic code 只调度窗口/来源；
   - semantic summary 必须由注入模型生成；
   - raw facts 不改写，Summary 仍是 index。

4. **Topic State / Need-History**
   - TopicStateService 进入 Core；
   - 当前输入 + canonical recent turns 可维持“这个/那个/继续”类主题；
   - topic existence 与 history_may_help 分离；
   - P16 adapter 不再替 Core 注入 topic label。

5. **CommunicationExperience**
   - Resident runtime 正式 writeback；
   - 必须有真实 user/world feedback；
   - assistant 自己输出不能单独充当反馈；
   - 只记录 experience，不由 deterministic code 选择未来话术。

6. **World Navigation**
   - `focus_entity`
   - `search_timeline`
   - `follow_relation`
   - `compare_claims`
   - `retrieve_original_observation`
   - `expand_recall`
   - `inspect_outcome`

7. **Execution context**
   - 普通用户轮次自动带入 bounded relevant Goal / Task / Action / Outcome anchors；
   - 不再要求调用方把整个 execution world 手工塞给模型。

8. **Platform provenance**
   - 新增 `SourceClass.PLATFORM`；
   - trusted platform authorization / real Outcome 不再误标为 `AI_COGNITION`；
   - 旧 SQLite World 通过 lossless CHECK-constraint migration 前向兼容。

9. **Context-budget regression hardening**
   - full provider tool schema 不再在 cockpit 内重复占 token；
   - cockpit 只保留 capability name/kind/side-effecting awareness；
   - P14 long context / P16 habitation 回归保持 GREEN。

最终 accepted head 的 16 个 Gate：**全部 SUCCESS**。

### 当前唯一项目级 blocker

现在不再是“缺 Core 认知机制代码”，而是：

**P16 尚无真实模型长期入住证据。**

因此：

- 宪法代码对齐：**PASS for audited findings**
- P16：**CONTINUE / NOT PASS**
- P17：**仍禁止启动**


## 2026-09-20 第二轮代码完整性复审 — REOPENED BLOCKERS

复审报告：

- `reviews/AIOS_V3_CODE_COMPLETENESS_REAUDIT_2026-09-20.md`
- 报告提交：`5a2f569040ab0160923cbd805b2ebcdeaeb3b65b`

本轮不是否定 PR #20；PR #20 确实关闭了第一轮审查明确列出的机制缺口，16 个 Gate 也是真实 green。

但第二轮从 WorldObject 全表、subject isolation、stable identity、真实 P16 Current-Core 接线、Policy consumer/evaluation、Summary backlog、Entity/Relation 生产路径和 fixture coverage 反向审查，发现更深层问题。

### BLOCKER

1. **跨 subject 隔离未形成统一硬边界**
   - WorldStore reference validation 不校验 subject；
   - Claim / Revision / Event / Dimension / Goal / Policy / Communication refs 多数只校验存在；
   - `search_mind()` 无 subject 参数；
   - timeline/entity search、query-less ALL_DIMENSIONS、DimensionSummary 可跨 subject 读入数据。

2. **CognitivePolicy 仍是可版本化账本，不是完整自适应运行策略**
   - Resident 无 propose/register policy；
   - Current-Core / P16 不预注册 policy；
   - active policy 没有 resolver/consumer 真正改变 recommendation/search/communication/review 等行为；
   - evaluation_window 未调度；
   - Periodic Review 不把 CognitivePolicy 作为 review anchor；
   - AI policy update evidence 目前只校验存在，可引用 AI 自己 Claim 或其他 subject。

3. **P6 多尺度 Summary 未接入真实长期运行链**
   - P16 Current-Core 没有 dimension_summary_handler；
   - advance_to() 不运行 `run_due_dimension_summaries()`；
   - 无 missed-window durable backlog；
   - >max_source_objects 时可提交 truncated CURRENT Summary；
   - late data 不会自动重建旧窗口；
   - active_dimensions() 未按 dimension lifecycle 过滤。

### HIGH

- P4 TopicState/Need-History 仍使用固定词表 + `len(topic)>=4` 决定历史价值，过度机械；
- Entity/Relation 没有 Resident 正式创建/维护 capability，图索引主要依赖手工 seed；
- P6/P8/P9/P11/P12 仍有 delimiter-joined stable ID，和 P13 已修的碰撞问题不一致；
- Claim/Summary/Recommendation/ALL_DIMENSIONS 等 durable truth path 仍有 broad `except Exception` 吞存储错误；
- Event service 声称合法 forward lifecycle，但没有 previous->new transition matrix；
- P16 当前四个 sealed lives 每个仅 4-5 个显式事件，未覆盖 Policy / CommunicationExperience / Event lifecycle / Entity-Relation / P6 Summary / 完整 Dimension lifecycle。

### 当前项目裁决

- Architecture direction：**PASS**
- Core spine：**STRONG**
- PR #20 first-order closure：**VALID**
- Second-order code completeness：**NOT PASS**
- P16 paid provider execution：**应等待上述 blocker 收口后再作为 release evidence**
- P17：**BLOCKED**



## 2026-09-20 第二轮代码完整性收口 — CLOSED

第二轮复审：

- `reviews/AIOS_V3_CODE_COMPLETENESS_REAUDIT_2026-09-20.md`
- audit commit：`5a2f569040ab0160923cbd805b2ebcdeaeb3b65b`

正式收口：

- `reviews/AIOS_V3_CODE_COMPLETENESS_CLOSURE_2026-09-20.md`
- PR #21：`core: close second-pass code completeness blockers`
- accepted head：`029d8f6849cdb08e2c784cd3bded0b025d1e03e6`
- squash merge / 当前功能代码锚点：`9d9fb9d82ef42b631d032c488617316c5a2a244c`

PR #21 accepted head 触发的 **20 个 workflow 全部 SUCCESS**，包括：

- constitutional-cognition-closure
- p16-convergence-gate / full-core-regression
- p16-habitation-harness
- p15-periodic-review
- c09-wake-dispatch
- fused-turn-runtime
- world-index
- memory-recommendation
- dimension-summary
- all-dimensions-projection
- cognition-writeback / cognition-revision
- P9 / P10 / P11 / P12
- P14 long-context

本轮关闭：

1. **private-world subject isolation**
   - search / timeline / entity / ALL_DIMENSIONS / Summary 均 subject scoped；
   - direct object-id Runtime 读取也受私有世界边界约束；
   - Claim / Revision / Event / Dimension / Execution / Policy / Communication / Entity / Relation refs 受 scope 校验；
   - AI-self 只通过显式 user + AI-self 例外读取同一私有世界证据，不允许跨其他用户。

2. **CognitivePolicy 真实运行闭环**
   - Resident 可 propose policy；
   - AI policy create/update/rollback 必须是真实结果证据；
   - AI Claim / assistant 自己输出不能递归训练 policy；
   - evaluation_window 变成真实 due time；
   - 到期 policy 进入 Periodic Review；
   - Runtime 已有真实 consumer，不再只是 ledger。

3. **P6 MultiScale Summary 长期调度**
   - P16 Current-Core 已接 dimension summary handler；
   - habitation clock 实际运行多尺度 Summary；
   - durable World 反推已关闭窗口，停机不永久漏窗；
   - late data 重开旧窗口；
   - terminal Dimension 不继续维护；
   - source truncation 不提交 CURRENT；
   - 旧 CURRENT Summary 在后来发现窗口不完整时会 forward-mark STALE。

4. **第二轮 HIGH 项**
   - TopicState 移除 `len(topic)>=4`；
   - Entity / Relation Resident 生产闭环；
   - stable ID 使用 canonical structured hashing；
   - durable truth path fail-closed；
   - Event lifecycle transition matrix；
   - P16 新增 cognition-system-closure 长人生 fixture，覆盖 Policy / CommunicationExperience / Entity-Relation / Event / Summary / 多线程长期变化。

### 当前正式项目状态

- Architecture direction：**PASS**
- Core spine：**STRONG**
- PR #20 first-order closure：**PASS**
- PR #21 second-order code completeness closure：**PASS**
- 当前已知 audited Core code blockers：**0**
- P16：**CONTINUE / NOT PASS**
- P17：**BLOCKED**

### 当前唯一项目级 blocker

再次恢复为：

**缺少真实 provider/model 的长期入住认知证据。**

下一动作：

1. 至少两个真实 provider/model 分别入住同一 sealed life；
2. fresh private World；
3. resident-visible fingerprint 必须一致；
4. 保存 provider / run / World provenance；
5. 用同一 evaluator configuration 做 separate hidden-oracle evaluation；
6. offline criterion-by-model comparison；
7. 独立红队审查错误记忆、自我强化、revision、summary misuse、dimension spam、无 Outcome 伪经验；
8. 证据成立后才允许 P16 PASS / P17。

> 注意：确定性 Gate 只证明机制、隔离、持久化、状态机和接线正确，不能替代真实模型长期认知质量证明。
