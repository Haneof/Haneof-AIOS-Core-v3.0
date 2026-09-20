# AIOS v3.0 当前工程断点

> 用途：新会话 / 新模型 / 新工程师进入仓库后的第一现场状态文件  
> 更新规则：每完成一个可验证节点立即更新；不得靠聊天记忆代替本文件  
> 仓库：`Haneof/Haneof-AIOS-Core-v3.0`  
> 分支：`main`

## 当前快照

- 时间：2026-09-20 12:50 +08:00
- 最后已验证功能代码锚点：`cff1db594dbd64f29fea5cca909907997bee8352`
- 说明：实时 `main` HEAD 必须接手时从 GitHub 获取；checkpoint 文件自身更新也会产生新 commit，因此这里记录的是**最后完成并通过 CI 的功能代码锚点**，不是自指的实时 HEAD。
- 当前项目阶段：**P8 已完成，准备进入 P9 认知翻案与依赖传播**
- 当前主干状态：**第一条 World → Recall → Model → Cognition Writeback → World 竖链已跑通**
- 当前 blocker：**尚未实现新证据导致旧认知 revise/retract 后的依赖传播**
- 下一主任务：**Revision / Retraction / Dependency Reverse Propagation**

## 已完成并有 Green CI 的关键节点

- WorldObject / SQLiteWorldStore / revision / idempotency 世界内核：GREEN
- Conversation → unified world：GREEN
- WorldSearchIndex / candidate recall：GREEN
- Topic-gated proactive memory recommendation：GREEN
- ContextController：GREEN
- CognitiveRuntime：GREEN
- Single-dimension Summary：GREEN
- ALL_DIMENSIONS projection：GREEN
- Model-driven ALL_DIMENSIONS capability：GREEN
- Evidence-grounded cognition writeback：GREEN
- Search → Evidence → Claim writeback integrated turn：GREEN

当前最新 Green：
- workflow：`fused-turn-runtime`
- commit：`cff1db594dbd64f29fea5cca909907997bee8352`
- conclusion：`success`

## 当前可运行主链

```text
WorldStore
→ WorldSearchIndex
→ ProactiveMemoryRecommender
→ ContextController
→ CognitiveRuntime
→ real model handler
   ├─ search_world
   ├─ inspect_world_object
   ├─ request_all_dimensions_projection
   └─ commit_claim
→ EvidenceSet + Claim + Dependency
→ WorldStore
→ index.catch_up
→ ConversationIngestor
→ next turn
```

## P9 当前要实现的最小闭环

目标不是“允许编辑 Claim 文本”，而是建立完整的向前修正链：

```text
Claim A@1
  ↓ depends_on
Claim B / Relationship / User Understanding / Strategy
  ↓
new Evidence
  ↓
resident AI forms revision decision
  ↓
A@2 or RETRACTED/SUPERSEDED state
  ↓
reverse dependency scan
  ↓
dependents become STALE / REVIEW_REQUIRED / SUPERSEDED
  ↓
AI re-evaluates affected cognition
  ↓
new versions committed
  ↓
index current-view refresh
  ↓
recommendation no longer presents A@1 as current truth
```

## P9 预计首先处理的代码

- `src/aios_core/dependency/graph.py`
  - 已有 `collect_impacted_dependents()`，当前只是确定性内存 helper。
  - 下一步需要接持久化世界对象和 reverse propagation runtime。
- `src/aios_core/writeback/cognition.py`
  - 已有 EvidenceSet + Claim + Dependency 原子写回。
  - 需要支持修正/撤回/后继版本，而不是只有首次 Claim。
- `src/aios_core/storage/sqlite_store.py`
  - 继续作为唯一世界写入底座。
- `src/aios_core/query/search.py`
  - 修正后 current view / recommendation 不能继续把过期认知当当前有效对象。
- 新模块建议落点：
  - `src/aios_core/revision/propagation.py`
  - `src/aios_core/revision/service.py`
- 新集成测试：
  - old claim → dependent claim → contradicting evidence → revise/retract → dependents stale → re-evaluation → index current view

## 当前不可推翻的已决事项

- 不建第二套 AI Self 数据库。
- 不把 ALL_DIMENSIONS 做成父维度。
- 不让 Summary 自动写跨维因果。
- 不让固定关键词/固定阈值替 AI 形成心理、人格、关系结论。
- 不让 recommendation 自己成为另一个世界。
- 无主题时历史推荐允许 0。
- 模型仍拥有主动世界搜索权。
- Cognition 必须与事实分离；Claim 可修正，Observation 原文不可倒写。
- 旧仓代码只按迁移矩阵择优融合，不整仓复制。
- PseudoLLM / 固定关键词题库不得作为最终认知能力 Gate。

## 恢复现场时第一批必读

1. `PROJECT_MASTER_MAP.md`
2. `AIOS_v3.0_CURRENT_CHECKPOINT.md`
3. `docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md`
4. `docs/architecture/AIOS_v3.0_Legacy_Code_Migration_Matrix.md`
5. `src/aios_core/writeback/cognition.py`
6. `src/aios_core/dependency/graph.py`
7. `src/aios_core/runtime/turn_runtime.py`
8. `src/aios_core/query/search.py`

读取后首先获取 GitHub `main` 实时 HEAD，并审查本文件“最后已验证功能代码锚点”之后的 commits / CI。若只是 Master Map / Checkpoint 文档提交，可直接越过；若包含功能代码，先确认 Gate 和 CI，再续开发。
