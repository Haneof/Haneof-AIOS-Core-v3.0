# AIOS v3.0 当前工程断点

> 用途：新会话 / 新模型 / 新工程师进入仓库后的第一现场状态文件  
> 更新规则：每完成一个可验证节点立即更新；不得靠聊天记忆代替本文件  
> 仓库：`Haneof/Haneof-AIOS-Core-v3.0`  
> 分支：`main`

## 当前快照

- 时间：2026-09-20 13:12 +08:00
- 最后已验证功能代码锚点：`d84c956e25a28a067e652282975d27711685229b`
- 验证 Gate：`p10-ai-world-gate` / run `35491030461` / **success**
- 当前项目阶段：**P10 已完成，进入 P11 动态维度生命周期与注册**
- 当前主干状态：**统一世界、索引、推荐、上下文、Runtime、Summary、ALL_DIMENSIONS、认知写回、翻案传播、AI用户理解/关系/自我/边界/策略/人格/校准已共用同一世界机制**
- 当前 blocker：**动态维度仍只有宪法与旧实验实现；需要重新实现“AI提出候选 + 系统验证契约/生命周期”，不能恢复固定心理阈值**
- 下一主任务：**P11 Dimension Proposal / Registration / Lifecycle**

## P10 已完成并通过 Gate

- AI User Understanding 使用统一 Claim/Evidence/Dependency：GREEN
- AI Relationship 使用统一世界，不建关系数据库：GREEN
- AI Self 使用统一世界，不恢复 `runtime_ai_self_memory`：GREEN
- AI Intent / Strategy / Cognitive Boundary / Personality / Calibration 共用同一 Claim engine：GREEN
- UNKNOWN / HYPOTHESIS 是合法认知状态：GREEN
- AI-world Claim 复用 P9 revise/retract/propagation：GREEN
- Runtime 提供 `read_ai_world`：GREEN
- Runtime 提供 `commit_ai_world_claim`：GREEN
- 新会话只自动加载显式标记 `core_context` 的最小身份/关系连续信息：GREEN
- 未标记的完整用户画像不会每轮自动灌入：GREEN
- Relationship / Calibration 独立宪法文件已补齐：GREEN
- 所有 AI认知模块均无第二真相库：GREEN

## 当前可运行主链

```text
Reality / Conversation
↓
Observation / Event / Summary
↓
WorldSearchIndex / Recommendation
↓
ContextController
↓
Resident Model
├─ read_ai_world
├─ search_world
├─ request_all_dimensions_projection
├─ commit_ai_world_claim
├─ commit_claim
├─ revise_claim
└─ retract_claim
↓
EvidenceSet + Claim + Dependency
↓
AI User / Relationship / Self / Boundary / Strategy / Personality / Calibration
↓
Revision propagation
↓
Current Index + minimal core continuity
↓
next session
```

## P11 当前目标

维度注册不是固定分类表，也不是程序通过阈值自动发明心理标签。

目标闭环：

```text
AI观察世界
↓
AI认为出现新的长期观察需求
↓
AI提出 Dimension Proposal
↓
附 Evidence + 说明：
- 为什么现有维度不够
- 为什么具有持续观察价值
- 对用户有什么帮助
- 维护成本是否值得
↓
系统只验证：
- Schema
- Evidence refs 存在
- 名称/ID不冲突
- 生命周期状态合法
- 权限与资源边界
↓
进入 Candidate / Trial
↓
真实运行一段时间
↓
AI依据新的 Evidence / Outcome 决定：
activate / revise / merge / dormant / archive / reject
↓
统一世界中留下完整演化历史
```

## P11 禁止事项

- 不恢复旧 `2 domains / 3 days / 30 days / 70%` 为认知真理。
- 不用固定心理维度白名单。
- 不用关键词直接生成维度。
- 系统不得替 AI 判断“这个维度有意义”。
- 一次性事件不能被程序自动升级成长期维度。
- 维度之间继续平级。
- merge / dormant / archive 不允许删除历史来源。
- 维度 proposal 必须有 Evidence。
- 维度状态机可以确定性校验，但“为什么升级/合并/退休”必须来自 AI 判断与 Evidence。

## P11 首批必读

新仓：
1. `docs/constitution/AIOS_v3.0_Dimension_Registration_Constitution.md`
2. `docs/constitution/AIOS_v3.0_Base_Dimension_Constitution.md`
3. `docs/constitution/AIOS_v3.0_High_Level_Cognition_Dimension_Constitution.md`

旧仓择优来源：
4. `src/aios_core/dimensions/evolution_guard.py`
5. `src/aios_core/tools/proposal_pipeline.py`
6. `src/aios_core/tools/proposed_operators.py`

当前世界底座：
7. `src/aios_core/contracts/models.py`
8. `src/aios_core/storage/sqlite_store.py`
9. `src/aios_core/writeback/cognition.py`
10. `src/aios_core/revision/service.py`
11. `src/aios_core/runtime/turn_runtime.py`

## 当前不可推翻的已决事项

- 所有维度平级存在于同一世界。
- 维度是观察轴，不是数据库父子分类。
- AI负责判断新维度的意义；系统只提供注册和状态机制。
- 不建第二套 AI Self / User Profile 数据库。
- 不让 Summary 自动写跨维因果。
- 无主题时推荐允许 0。
- stale 只表示需要重新判断。
- PseudoLLM / 固定题库不得作为认知 Gate。

## 恢复现场规则

接手时先获取 GitHub `main` 实时 HEAD，并审查本文件功能锚点之后的 commits / CI。纯地图/checkpoint文档提交可越过；功能代码必须先确认 Gate 与边界再继续。
