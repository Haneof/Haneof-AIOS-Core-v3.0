# AIOS v3.0 项目全流程总地图

> 文件角色：项目级唯一“全流程地图”入口  
> 用途：跨会话、跨模型、跨工程师断点续传；判断“现在做到哪、下一步做什么、哪些不能重做”  
> 状态：ACTIVE / LIVING DOCUMENT  
> 当前开发仓：`Haneof/Haneof-AIOS-Core-v3.0@main`  
> 当前融合基线：`docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md`  
> 旧代码迁移裁决：`docs/architecture/AIOS_v3.0_Legacy_Code_Migration_Matrix.md`

---

## 1. 项目最终目标

AIOS v3.0 不是一个“聊天机器人外壳”，而是一个可长期运行的 AI-Operated System：

```text
现实 / 用户 / 设备 / App / 对话
        ↓
事实进入统一世界
        ↓
多维世界持续增长
        ↓
快速索引 / 时间总结 / 事件与实体锚点
        ↓
AIOS 根据当前会话主动推荐相关历史
        ↓
上下文中控组装本轮模型上下文
        ↓
真实模型进行理解 / 搜索 / 比较 / 判断
        ↓
可修正认知 Claim / 关系 / AI经验 / 目标 / 任务 / 行动
        ↓
Evidence + Dependency + Revision
        ↓
写回统一世界
        ↓
以后每一次 AI 都面对一个已经成长过的世界
```

最终 Core 必须平台无关；Android / Linux / 手机 / 未来硬件属于承载层。

---

## 2. 不可回退的根原则

1. 所有维度存在于同一个 AIOS 世界，维度之间平级。
2. 全局唯一时间轴。
3. Observation / Evidence / Claim / Summary 边界必须保持。
4. 原始事实不因 AI 后来改变理解而被倒写。
5. Summary 只总结单维度一段时间“发生了什么”，不代替跨维认知。
6. ALL_DIMENSIONS 是跨维观察投影，不是父维度，也不自动产生因果结论。
7. 索引是可重建公共能力，不是真相库。
8. 智能推荐由当前会话主题触发；无相关主题时历史推荐必须允许为 0。
9. 推送记忆为主，模型主动深搜为补充。
10. 程序负责确定性基础设施；高阶意义、因果、用户理解、自我理解由真实模型判断。
11. AI认知必须以 Claim 等可修正对象进入统一世界，不得建立第二真相库。
12. 认知翻案必须向前修正并传播，不能删除过去来伪装“从未犯错”。

根原则解释权以 `AIOS_v3.0_Fused_Baseline_Registry.md` 为准。

---

## 3. 全流程工程地图

| 阶段 | 目标 | 主要产物 | Gate | 当前状态 |
|---|---|---|---|---|
| P0 融合法统与架构基线 | 统一新旧两套 3.0 理念与工程资产 | Fused Baseline Registry、宪法模块化、134 文件迁移矩阵 | 不再按“旧仓/新仓”机械判断 | ✅ 已完成工作基线 |
| P1 统一世界内核 | 恢复可靠 WorldObject / revision / transaction / idempotency | contracts、SQLiteWorldStore、Dependency | 重启后历史可读；写入原子；版本可追踪 | ✅ 已通过 |
| P2 会话事实入世界 | 用户/AI对话作为事实进入统一世界 | ConversationIngestor、conversation continuity | 对话原文可永久追溯；retry 幂等 | ✅ 已通过 |
| P3 智能世界索引底座 | 世界对象可重建快速检索 | WorldSearchIndex、watermark、candidate recall | Index 可重建；stale 可检测；不成为真相库 | ✅ 已通过 |
| P4 会话主题记忆推荐 | 模型调用前由 AIOS 主动带出相关记忆 | ProactiveMemoryRecommender | 无主题=0；有主题才召回；模型仍可主动搜 | ✅ 已通过 |
| P5 上下文中控 + Cognitive Runtime | 把当前输入、推荐、能力装配给模型 | ContextController、CapabilityRegistry、CognitiveRuntime | 程序不规定固定思维顺序；能力调用可审计 | ✅ 已通过 |
| P6 单维度时间总结 | 日/周/月/年等总结成为世界快速入口 | DimensionSummaryService、Summary.content | 总结由模型生成；来源 pinned；不做跨维因果 | ✅ 已通过 |
| P7 ALL_DIMENSIONS 全维投影 | 同一时间窗观察多个平级维度 | AllDimensionsProjectionService | 保留来源与类型；不产生父维度/自动因果 | ✅ 已通过 |
| P8 认知写回闭环 | AI 将有证据认知写回世界 | EvidenceSet + Claim + Dependency | 无 pinned Evidence 不得写 Claim；原事实不改 | ✅ 已通过 |
| P9 认知翻案与传播 | 新证据出现后让旧认知失效/修正并传播 | Revision / Retraction / Propagation | 依赖旧 Claim 的当前认知不能继续假装有效 | ✅ 已通过 P9 Gate |
| P10 AI 用户理解 / 关系 / 自我世界 | 让 AI 长期理解“用户是什么 / 自己是什么 / 我们是什么关系” | User Understanding、Relationship、Self、Boundary、Calibration、Personality | 全部进入统一世界；可修正；有证据 | ✅ 已通过 P10 Gate |
| P11 维度生命周期与注册 | AI 可提出、维护、合并、退休长期有价值维度 | Dimension proposal / registration / lifecycle | 禁止固定心理维度白名单替 AI 做认知 | ✅ 已通过 P11 Gate |
| P12 Goal / Task / Action / Outcome | AI 从理解走向持续目标与行动 | Goal、Task、Action、Outcome、Scheduler | 行动可授权、可回滚、Outcome 可学习 | 🔵 当前主阶段 |
| P13 数据接入与机械清洗 | 对话外现实持续进入世界 | 手机/App/传感器/相册/麦克风/日历等 adapter | 数据接入不得越权产生高阶认知 | ⏳ 待做 |
| P14 长会话连续性完整接线 | 超长单会话不因 context limit 失忆 | rolling state、轮总结、summary drill-down | raw dialogue 永久保留；summary 只是索引 | 🟡 已有底座，未完整接线 |
| P15 周期 Review / AI 成长 | AI 定期回看世界、修正理解、沉淀经验 | periodic review、operation experience、strategy learning | 不以固定模板替代模型判断 | ⏳ 待做 |
| P16 多 Agent 长期入住测试 | 用真实模型和隐藏人生测试是否真的“活在世界中” | habitation simulator / hidden-life scenarios | 不以关键词题库证明认知能力 | ⏳ 待做 |
| P17 Core Release Gate | 形成第一个稳定可运行 AIOS Core | reproducible build、full CI、migration report | 世界闭环、认知闭环、任务闭环均稳定 | ⏳ 待做 |
| P18 平台适配 | 把同一套 Core 放到真实运行环境 | Android/Linux service、device adapters | Core 语义不因平台重写 | ⏳ 后置 |
| P19 产品层 | AIOS UI、数字人、系统入口、设备体验 | Launcher/UI/Voice/Digital Human | 产品层不得反向污染 Core 世界语义 | ⏳ 后置 |

---

## 4. 当前已经形成的可运行竖链

```text
历史 World
  ↓
WorldSearchIndex
  ↓
Topic-gated proactive recommendation
  ↓
ContextController
  ↓
CognitiveRuntime + real model adapter
  ├─ answer
  ├─ search_world
  ├─ inspect_world_object
  ├─ request_all_dimensions_projection
  └─ commit_claim
           ↓
EvidenceSet + Claim + Dependency
           ↓
SQLiteWorldStore
           ↓
world_revision++
           ↓
index.catch_up()
           ↓
ConversationIngestor
           ↓
本轮用户/AI原始对话继续进入统一世界
```

这条竖链是后续所有认知、关系、任务和行动能力的主干，不得重新另造平行 Runtime。

---

## 5. 当前工程断点

当前可恢复的**功能代码锚点**必须以 `AIOS_v3.0_CURRENT_CHECKPOINT.md` 为准。GitHub `main` 的实时 HEAD 必须现场获取；因为更新 checkpoint 文件本身也会产生新 commit，所以不得要求“文件内 SHA 永远等于实时 HEAD”。

当前阶段：

```text
P8 Evidence-grounded Cognition Writeback  ✅
                    ↓
P9 Revision / Retraction / Dependency Propagation  ✅
                    ↓
P10 AI User Understanding / Relationship / Self / Calibration  ✅
                    ↓
P11 Dynamic Dimension Lifecycle / Registration  ✅
                    ↓
P12 Goal / Task / Action / Outcome  ← 当前下一主任务
```

P9 要解决的核心场景：

```text
旧 Evidence
   ↓
Claim A 成立
   ↓
Claim B / Relationship / User Understanding / Strategy 依赖 A
   ↓
新 Evidence 到来
   ↓
AI判断 A 需要 revise / retract
   ↓
保留历史 A
   ↓
产生新的当前版本
   ↓
Dependency reverse propagation
   ↓
依赖 A 的当前认知被标 stale / pending-review / superseded
   ↓
索引和智能推荐停止把旧错误当“当前有效真相”
```

---

## 6. 后续开发顺序

除非发现 P0 根原则级 blocker，默认严格按以下顺序推进：

```text
P9 认知翻案传播 ✅
→ P10 AI用户理解 / AI自我 / 关系 / 认知边界 / 校准 ✅
→ P11 动态维度生命周期 ✅
→ P12 Goal / Task / Action / Outcome ← 当前
→ P13 多源现实数据接入
→ P14 长会话连续完整接线
→ P15 周期Review与AI经验成长
→ P16 多Agent长期入住测试
→ P17 Core Release Gate
→ P18 Android/Linux平台适配
→ P19 产品UI/数字人/硬件
```

可并行的只是“不改变主干语义”的测试、文档和机械 adapter；不得并行造第二套世界、第二套索引或第二套认知 Runtime。

---

## 7. 断点续传协议

以后任何新会话、新模型、新工程师接手 AIOS 时，不允许先凭记忆重新设计项目。

必须按以下顺序恢复现场：

1. 读取本文件 `PROJECT_MASTER_MAP.md`。
2. 读取 `AIOS_v3.0_CURRENT_CHECKPOINT.md`。
3. 读取 `docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md`。
4. 若涉及旧代码迁移，再读取 `docs/architecture/AIOS_v3.0_Legacy_Code_Migration_Matrix.md`。
5. 获取 GitHub `main` 当前实时 HEAD。
6. 对比实时 HEAD 与 checkpoint 的“最后已验证功能代码锚点”：
   - 若没有后续功能代码：直接从“当前任务 / 下一动作”继续；
   - 若有后续 commits：先审查锚点之后的 commits 和 CI；纯地图/checkpoint 文档提交不视为功能漂移；
   - 审查完成后更新 checkpoint 的功能代码锚点。
7. 读取当前阶段相关源码与测试，不从旧 conversation 记忆猜实现。
8. 只有在当前阶段 Gate 通过后，才把 Master Map 状态推进到下一阶段。
9. 每次完成一个可验证工程节点，都更新 `AIOS_v3.0_CURRENT_CHECKPOINT.md`。
10. 架构根原则变化必须先更新 Fused Baseline Registry，再修改 Master Map；普通代码进度不得偷偷改宪法。

---

## 8. Checkpoint 最低记录要求

`AIOS_v3.0_CURRENT_CHECKPOINT.md` 每次至少记录：

- 当前时间；
- 最后已验证功能代码锚点（不是要求与实时 HEAD 自指相等）；
- 当前项目阶段；
- 最后一个完成的能力；
- 当前正在做的能力；
- 下一动作；
- 最近 Green CI；
- 已知 blocker / debt；
- 本阶段关键文件；
- 不得重做/不得推翻的已决事项；
- 恢复工作时第一批要读的文件。

这样即使聊天上下文全部丢失，只要仓库还在，就能从 GitHub 恢复项目状态。

---

## 9. 三套项目导航文件的分工

```text
PROJECT_MASTER_MAP.md
= 整个项目从出生到发布的总地图，低频更新

AIOS_v3.0_CURRENT_CHECKPOINT.md
= 当前施工现场，频繁更新，专门用于断点续传

Fused_Baseline_Registry.md
= “为什么这样设计”的当前最高融合架构解释

Legacy_Code_Migration_Matrix.md
= 旧仓每个文件该搬、改、合并、废弃还是后置
```

四者职责不得混淆。

---

## 10. 项目完成定义

AIOS Core v3.0 只有同时满足以下事实才进入 Release Gate：

- 世界能长期增长、重启、回放；
- 原始事实可追溯；
- 索引可重建；
- 单维总结可追溯；
- ALL_DIMENSIONS 可观察多个平级维度；
- AI 能主动得到相关历史，也能主动深搜；
- AI 能形成 Evidence-grounded Claim；
- 错误认知能修正并向依赖认知传播；
- AI 用户理解、AI自身世界、关系认知可长期演化；
- Goal / Task / Action / Outcome 形成可审计闭环；
- 多 Agent 长期入住测试能证明跨天/跨月连续性；
- 不依赖某个特定模型厂商、手机、ROM 或 UI；
- 换模型之后，世界、经验和关系仍然继续存在。

这才是 AIOS v3.0 的 Core 完成，而不是“代码文件很多”或“单元测试数量很多”。
