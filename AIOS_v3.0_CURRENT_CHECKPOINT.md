# AIOS v3.0 当前工程断点

> 用途：新会话 / 新模型 / 新工程师进入仓库后的第一现场状态文件  
> 更新规则：每完成一个可验证节点立即更新；不得靠聊天记忆代替本文件  
> 仓库：`Haneof/Haneof-AIOS-Core-v3.0`  
> 分支：`main`

## 当前快照

- 时间：2026-09-20 16:19 +08:00
- 最后已验证功能代码锚点：`76d179d48d1bb222c3d18eb5c435dd6f0c9ba212`
- 验证 Gate：`p14-long-context` / run `35499189697` / **success**；`fused-turn-runtime` / run `35499189641` / **success**；P9-P13 相关合并后回归全部 **success**
- 当前项目阶段：**P14 已完成，进入 P15 周期 Review / AI 成长**
- 当前主干状态：**长单会话 continuity 已由 WorldStore 内生维护；旧轮次可 round summary；summary 可精确 drill-down 到 pinned raw dialogue；重启后无需调用方维护 recent_turns**
- 当前 blocker：**P15 尚缺周期 Review 调度、模型回看输入包、OperationExperience/Strategy 学习写回与 Review 后修正闭环**
- 下一主任务：**P15 periodic review + AI experience / strategy learning + revision-aware growth loop**

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

## P15 当前目标

让 Resident AI 不只在用户说话时被动运行，而能在明确调度边界内周期性回看已经发生的世界，并把“我之前判断得怎么样、行动效果怎么样、策略需不需要修正”写回同一个世界。

目标闭环：

```text
World facts / Claims / Goals / Tasks / Actions / Outcomes
↓
deterministic Review scheduler 只决定何时需要 review
↓
构建 evidence-grounded review input
↓
真实模型回看、比较、判断
↓
可选择：
- revise / retract 旧 Claim
- 形成新的 evidence-grounded Claim
- 记录 OperationExperience
- 更新 Strategy / AI self understanding
↓
Dependency + Revision
↓
统一世界继续增长
```

P15 禁止：
- 用程序规则直接判断“用户成长了/AI成长了”；
- 用固定答案 benchmark 代替模型真实 review；
- 建第二套经验数据库；
- maintenance 自己触发无限 review 循环；
- Outcome 未发生时伪造行动经验；
- 把 Review 文本直接当高阶真相，所有认知仍需 Evidence / Claim / Revision 边界。

## 当前不可推翻的已决事项

- 世界唯一、索引公共。
- 推荐负责“当前要不要给哪些历史”；索引负责“到哪里找”。
- 同一长会话 continuity 是独立机制，不替代跨会话推荐。
- 原始对话是事实，轮总结只是索引。
- 模型负责总结内容，系统负责调度。
- AI认知必须另走 Claim / Evidence / Revision。

## 恢复现场规则

接手时先获取 GitHub `main` 实时 HEAD，并审查本文件功能锚点之后的 commits / CI。纯地图/checkpoint文档提交可越过；功能代码必须先确认 Gate 与边界再继续。
