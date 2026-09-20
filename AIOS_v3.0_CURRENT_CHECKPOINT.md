# AIOS v3.0 当前工程断点

> 用途：新会话 / 新模型 / 新工程师进入仓库后的第一现场状态文件  
> 更新规则：每完成一个可验证节点立即更新；不得靠聊天记忆代替本文件  
> 仓库：`Haneof/Haneof-AIOS-Core-v3.0`  
> 分支：`main`

## 当前快照

- 时间：2026-09-20 17:40 +08:00
- 最后已验证功能代码锚点：`1fc7b9f5c69b01f01dac8097efd29973bc4dbf4c`
- 验证 Gate：`p16-habitation-harness` merge-result run `35503797730` / **success**（58项，含 long-horizon Task/Review/C09/media/numeric/future-leak Gate）；C09 去重加固 Gate run `35501301595` / **success**
- 当前项目阶段：**P16 多模型独立长期入住测试**
- 当前主干状态：**P0-P15 已闭环；P16 benchmark 已具备真实 Current-Core target、独立 World、严格 oracle 隔离、跨事件中间时钟、P12 Task due→C09 Wake、P15 周期 Review、P13 media/numeric 路径、final horizon 与 future-sample 防泄漏。**
- 当前 blocker：**尚未接入并实际调用 GPT / Claude / Gemini 等真实 provider model；当前确定性 Gate 只能证明 AIOS/harness 机械链正确，不能证明长期认知质量。**
- 下一主任务：**实现 provider-backed ModelHandler / RoundSummaryHandler 与可审计 run provenance，然后执行多个真实模型各自独立入住同一 sealed life；最后才由 evaluator 读取 hidden oracle。**

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
