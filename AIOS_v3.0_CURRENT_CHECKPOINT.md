# AIOS v3.0 当前工程断点

> 用途：新会话 / 新模型 / 新工程师进入仓库后的第一现场状态文件  
> 更新规则：每完成一个可验证节点立即更新；不得靠聊天记忆代替本文件  
> 仓库：`Haneof/Haneof-AIOS-Core-v3.0`  
> 分支：`main`

## 当前快照

- 时间：2026-09-20 13:03 +08:00
- 最后已验证功能代码锚点：`1c2b1cbb858210b6b1da4d3b855c9374c3985c23`
- 验证 Gate：`p9-revision-gate` / run `35490673406` / **success**
- 说明：实时 `main` HEAD 必须接手时从 GitHub 获取；checkpoint 文件自身更新也会产生新 commit，因此这里记录的是**最后完成并通过聚合 Gate 的功能树锚点**。
- 当前项目阶段：**P9 已完成，进入 P10 AI 用户理解 / 关系 / 自我 / 认知边界 / 校准**
- 当前主干状态：**World → Recall → Model → Claim Writeback → Revise/Retract → Dependency Propagation → Summary Rebuild → Current Index 已闭环**
- 当前 blocker：**P10 现有宪法模块有定义但实现仍分散；Relationship / Calibration 还缺统一独立实现**
- 下一主任务：**把 AI 长期认知模块全部落在同一 EvidenceSet + Claim + Dependency + Revision 世界机制上，禁止另建 AI Self 数据库**

## P9 已完成并通过 Gate

- Claim revise：保留旧 revision，产生同 object_id 新 revision：GREEN
- Claim retract：历史保留，当前 status=retracted：GREEN
- reverse Dependency propagation：GREEN
- stale_review_required：GREEN
- 已经前进的 dependent 不被旧依赖倒退覆盖：GREEN
- stale dependent 可由 Resident AI 重新评估并恢复 active：GREEN
- stale / retracted cognition 默认不进入 current retrieval：GREEN
- historical pinned revision 仍可读取：GREEN
- Summary source Dependency：GREEN
- 上游 Claim 修正 → Summary stale → rebuild：GREEN
- AI cognition Claim 进入全局时间轴：GREEN
- Runtime 已提供 revise_claim / retract_claim：GREEN

## 当前可运行主链

```text
WorldStore
→ WorldSearchIndex
→ ProactiveMemoryRecommender
→ ContextController
→ CognitiveRuntime
→ Resident Model
   ├─ search_world
   ├─ inspect_world_object
   ├─ request_all_dimensions_projection
   ├─ commit_claim
   ├─ revise_claim
   └─ retract_claim
→ EvidenceSet + Claim + Dependency
→ CognitionRevisionService
→ reverse Dependency propagation
→ stale_review_required / stale Summary
→ model re-evaluation
→ new active revisions
→ Summary rebuild
→ index.catch_up
→ next turn
```

## P10 当前目标

P10 不再建立新的“认知数据库”。

所有长期 AI 认知都使用同一世界机制：

```text
User World / Conversation / Event / Summary
↓
Resident AI observes/searches
↓
EvidenceSet
↓
Claim in one AI dimension
↓
Dependency
↓
Revision / Calibration
```

P10 需要收口的维度模块：

- AI User Understanding：用户是什么
- AI Relationship：AI与用户当前是什么关系、关系如何演化
- AI Self：AI如何理解自己、自己的经历与能力边界
- AI Cognitive Boundary：已知 / 未知 / 假设 / 待验证
- AI Calibration：过去判断对错、用户纠正、预测/策略命中情况
- AI Strategy / Communication Experience：什么方式对这个用户有效
- AI Personality：长期交互中形成的稳定行为倾向，但不得成为静态 system prompt 假人格

## P10 实施纪律

1. 优先使用已有 `Claim / EvidenceSet / Dependency / Revision`，不得给每个模型造新真相表。
2. 允许薄的 typed service / view / query helper，但真相仍只在 WorldStore。
3. Relationship / Self / User Understanding 必须能引用具体 Evidence。
4. 用户明确纠正后必须走 P9 修正链，不允许“新加一条相反记忆”后两条同时作为当前真相。
5. AI认知边界里的 UNKNOWN / HYPOTHESIS 是合法状态，不强迫模型总给结论。
6. Calibration 必须来自真实 Outcome / 用户反馈 / 后续 Evidence，不得用固定题库命中率冒充长期学习。
7. Personality 是长期行为结果，不做预设人格滑块。
8. AI Self 不得恢复旧 `runtime_ai_self_memory` 第二数据库。

## P10 首批必读与迁移来源

新仓：
1. `docs/constitution/AIOS_v3.0_AI_Dimension_Constitution.md`
2. `docs/constitution/AIOS_v3.0_AI_User_Understanding_Model_Constitution.md`
3. `docs/constitution/AIOS_v3.0_AI_Self_Model_Constitution.md`
4. `docs/constitution/AIOS_v3.0_AI_Strategy_Model_Constitution.md`
5. `docs/constitution/AIOS_v3.0_AI_Cognitive_Boundary_Model_Constitution.md`
6. `docs/constitution/AIOS_v3.0_AI_Personality_Model_Constitution.md`
7. `docs/constitution/AIOS_v3.0_AI_Dimension_Module_Index.md`

旧仓择优来源：
8. `src/aios_core/runtime/ai_self_world.py`
9. `src/aios_core/communication/experience_tracker.py`
10. `src/aios_core/cognition/operation_experience.py`
11. `src/aios_core/runtime/policy_registry.py`

当前主干：
12. `src/aios_core/writeback/cognition.py`
13. `src/aios_core/revision/service.py`
14. `src/aios_core/runtime/turn_runtime.py`

## 当前不可推翻的已决事项

- 不建第二套 AI Self 数据库。
- 不把 ALL_DIMENSIONS 做成父维度。
- 不让 Summary 自动写跨维因果。
- 不让固定关键词/固定阈值替 AI 形成心理、人格、关系结论。
- 无主题时历史推荐允许 0。
- 模型仍拥有主动世界搜索权。
- Claim 可修正，Observation 原文不可倒写。
- stale 只表示“需要重新判断”，不是程序自动判真伪。
- 旧仓代码只按迁移矩阵择优融合，不整仓复制。
- PseudoLLM / 固定关键词题库不得作为最终认知能力 Gate。

## 恢复现场规则

读取本文件后首先获取 GitHub `main` 实时 HEAD，并审查本文件功能锚点之后的 commits / CI。纯 Master Map / Checkpoint 文档提交可直接越过；若包含功能代码，先确认 Gate 和 CI，再续开发。
