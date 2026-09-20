# AIOS v3.0 当前工程断点

> 用途：新会话 / 新模型 / 新工程师进入仓库后的第一现场状态文件  
> 更新规则：每完成一个可验证节点立即更新；不得靠聊天记忆代替本文件  
> 仓库：`Haneof/Haneof-AIOS-Core-v3.0`  
> 分支：`main`

## 当前快照

- 时间：2026-09-20 14:53 +08:00
- 最后已验证功能代码锚点：`20100f0ddd8774cf53185f0862ff31fcc2c3421e`
- 验证 Gate：`p13-ingest-gate` / run `35495374031` / **success**
- 当前项目阶段：**P13 已完成，进入 P14 长会话连续性完整接线**
- 当前主干状态：**现实数据可通过 cognition-free adapters 进入统一世界；数值流可机械压缩；媒体长期事实只保留 descriptor/transcript；失败可审计**
- 当前 blocker：**长单会话仍主要依赖调用方传入 recent_turns；token 超限后还缺系统内生的轮总结状态与按需 raw drill-down**
- 下一主任务：**P14 rolling conversation state + round summaries + raw dialogue drill-down**

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

## P14 当前目标

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

## 当前不可推翻的已决事项

- 世界唯一、索引公共。
- 推荐负责“当前要不要给哪些历史”；索引负责“到哪里找”。
- 同一长会话 continuity 是独立机制，不替代跨会话推荐。
- 原始对话是事实，轮总结只是索引。
- 模型负责总结内容，系统负责调度。
- AI认知必须另走 Claim / Evidence / Revision。

## 恢复现场规则

接手时先获取 GitHub `main` 实时 HEAD，并审查本文件功能锚点之后的 commits / CI。纯地图/checkpoint文档提交可越过；功能代码必须先确认 Gate 与边界再继续。
