# AIOS v3.0 当前工程断点

> 用途：新会话 / 新模型 / 新工程师进入仓库后的第一现场状态文件  
> 更新规则：每完成一个可验证节点立即更新；不得靠聊天记忆代替本文件  
> 仓库：`Haneof/Haneof-AIOS-Core-v3.0`  
> 分支：`main`

## 当前快照

- 时间：2026-09-20 14:35 +08:00
- 最后已验证功能代码锚点：`e677de516a2e2b3d785455db36013a74aebf01d4`
- 验证 Gate：`p11-dimension-gate` / run `35491309407` / **success**
- 当前项目阶段：**P11 已完成，进入 P12 Goal / Task / Action / Outcome**
- 当前主干状态：**统一世界、索引、推荐、上下文、认知写回、翻案传播、AI世界、动态维度注册已经闭环**
- 当前 blocker：**未来目标、任务、现实行动与结果仍未接入统一 Resident Runtime；现有 Goal/Task/Action/Outcome 契约需要重新收口**
- 下一主任务：**P12 Goal / Task / Action / Outcome / Scheduler**

## P11 已完成并通过 Gate

- Resident AI 可先 `list_dimensions` 再判断是否需要新观察轴：GREEN
- Resident AI 可 `propose_dimension`：GREEN
- Proposal 必须有 pinned Evidence：GREEN
- 系统仅做 schema / identity / lifecycle / transaction 校验：GREEN
- 无固定 2-domain / 3-day / 30-day / 70% 认知门槛：GREEN
- Candidate / Trial / Active / Dormant / Reactivated / Revised / Rejected / Merged / Split / Archived 状态机：GREEN
- Resident AI 可 `transition_dimension`：GREEN
- 维度 lifecycle 保留 revision 历史：GREEN
- Archived / Rejected / Merged / Split 不进入默认 current retrieval：GREEN
- DimensionDefinition / Derivation 已进入统一世界索引：GREEN
- 动态维度不建立第二 Registry 真相库：GREEN

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
├─ search_world
├─ inspect_world_object
├─ read_ai_world
├─ list_dimensions
├─ request_all_dimensions_projection
├─ commit_claim
├─ commit_ai_world_claim
├─ revise_claim / retract_claim
├─ propose_dimension
└─ transition_dimension
↓
Unified WorldStore
↓
Evidence / Dependency / Revision / Lifecycle
↓
Index catch-up
↓
next turn
```

## P12 当前目标

P12 要让 AI 从“理解世界”进入“持续帮助用户”。

目标闭环：

```text
World / User Intent / AI Cognition
↓
Goal
↓
Task
↓
Condition / Schedule / Authorization
↓
Action proposal
↓
授权后执行
↓
Outcome
↓
World writeback
↓
AI根据 Outcome 学习 / 修正 Goal、Task、Strategy
```

## P12 关键边界

1. Goal = 长期方向；Task = 可执行工作；Action = 一次现实副作用；Outcome = 真实结果。
2. Goal / Task / Action / Outcome 全部进入统一世界，不建第二任务数据库。
3. AI可以主动提出 Goal / Task，但不得伪造用户授权。
4. 外部副作用默认需要 capability-specific authorization。
5. 内部纯世界读写与现实外部动作必须分开。
6. Action 必须引用 Goal / Task / Evidence / 当前世界状态。
7. 执行失败也要形成 Outcome，不能静默消失。
8. Outcome 可作为 AI Strategy / Calibration / User Understanding 的 Evidence。
9. Scheduler 只负责确定性时机和条件，不替 AI 决定“为什么要做”。
10. 不允许为了测试直接给模型固定 expected action 文本。

## P12 首批必读

新仓：
1. `docs/constitution/AIOS_v3.0_Goal_Task_Constitution.md`
2. `docs/constitution/AIOS_v3.0_Action_System_Constitution.md`
3. `src/aios_core/contracts/models.py`
4. `src/aios_core/contracts/enums.py`
5. `src/aios_core/runtime/turn_runtime.py`
6. `src/aios_core/storage/sqlite_store.py`

旧仓择优来源：
7. Goal / Task / Action / Outcome state machines
8. scheduler / conditional engine
9. world operator / operation receipts
10. external side-effect authorization code

## P12 禁止事项

- 不把 Task 当聊天 TODO 文本。
- 不把 Action 执行权默认交给任意模型输出。
- 不因任务完成就删除历史 Goal/Task。
- 不让 Scheduler 自动生成高阶目标。
- 不把 Outcome 只写日志而不进入世界。
- 不用固定 demo 工具证明“行动能力”。
- 不绕过用户授权去执行外部副作用。

## 当前不可推翻的已决事项

- 世界唯一；所有模块都写同一个 WorldStore。
- 索引唯一公共能力。
- AI认知可修正；Observation 不倒写。
- 维度平级。
- AI负责意义，程序负责确定性机制。
- 用户授权与外部副作用必须有独立边界。
- PseudoLLM / 固定题库不得作为认知或行动 Gate。

## 恢复现场规则

接手时先获取 GitHub `main` 实时 HEAD，并审查本文件功能锚点之后的 commits / CI。纯地图/checkpoint文档提交可越过；功能代码必须先确认 Gate 与边界再继续。
