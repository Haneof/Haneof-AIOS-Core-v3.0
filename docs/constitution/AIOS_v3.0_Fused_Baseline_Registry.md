# AIOS v3.0 双仓融合工作基线注册表

> 状态：FUSED WORKING BASELINE  
> 适用范围：AIOS Core v3.0 当前架构、宪法整理、代码迁移、测试与后续开发  
> 说明：本基线用于双仓择优融合期间的统一开发解释，不等同于最终冻结版。

## 一、双源基线

AIOS v3.0 当前不以任意一个历史仓库单独作为最高依据。

参与融合的两套来源：

1. `Haneof/fantonghui@aios-2.0`
   - 冻结参考提交：`45ee43bbec2b46365d6105155766b9e7c9152af7`
   - 价值：完整旧宪法、R5/R6/ADJ、世界对象契约、SQLite 世界存储、检索、运行时、上下文、任务、修正、模拟与大量测试资产。
2. `Haneof/Haneof-AIOS-Core-v3.0@main`
   - 融合前参考提交：`799bc78f1d1d2943d9084a057fdaf9c85b66e45c`
   - 价值：最新多维世界定义、平级维度、模块化宪法、维度总结、维度注册、智能世界索引、智能记忆推荐、AI维度和闭环规划。

双仓融合遵循：

> 不按仓库新旧决定对错，只按机制是否更符合 AIOS 的理念目标、是否可运行、是否保持事实与认知边界、是否有利于长期演化来择优。

如双方都不完整，则综合形成第三版机制。

---

## 二、当前融合后的根原则

### 2.1 AIOS 是 AI 驾驶的持续多维世界系统

AIOS 的核心不是模型、UI、硬件或某个 App。

核心是：

- 一个持续增长的多维世界；
- 一个能够长期存在、理解、行动、修正和成长的 AI；
- AI 能够主动使用这个世界，而不是只被动读取聊天上下文。

### 2.2 所有维度存在于同一个世界

基础维度、事件维度、认知维度、AI维度以及未来动态生成维度均平级存在于同一世界。

“层”只能用于描述运行职责，不得被实现成维度父子数据库层级。

### 2.3 全局唯一时间轴

所有事实、事件、认知、关系、AI经验、任务和行动都必须可定位到统一时间轴。

### 2.4 事实与认知分离

- Observation：发生了什么；
- Evidence：为什么可以支持某个判断；
- Claim：AI 当前如何理解；
- Summary：某一维度在一段时间发生了什么；
- 认知可以修正；
- 原始事实不得因认知变化被倒写。

### 2.5 确定性基础设施与 AI 高阶认知分工

程序负责：

- 数据结构；
- 时间与版本；
- 原子事务与幂等；
- 索引；
- 引用；
- 权限与硬边界；
- 资源约束；
- 可审计状态机；
- 机械压缩和格式化。

AI负责：

- 理解；
- 归因；
- 跨维意义；
- 用户理解；
- AI自我理解；
- 关系理解；
- 是否形成新 Claim；
- 是否创建认知维度；
- 策略与分寸；
- 是否继续追忆；
- 是否行动、回应或沉默。

禁止用固定词典、固定心理标签、固定人生模板、固定维度白名单或固定认知阈值替 AI 完成高阶认知。

### 2.6 统一世界对象底座

优先继承旧仓已经成熟的对象语义：

- Observation
- Entity
- Event
- Evidence
- Claim
- Relation / Relationship
- Summary
- Goal
- Task
- Action
- Outcome
- Dependency
- Conversation / AI Experience 等

具体字段允许在新实现中重构，但对象间事实、证据、版本和来源关系不得丢失。

### 2.7 总结与认知必须分开

每个维度独立形成日、周、月、季度、半年、年及更长尺度总结。

总结只回答：

> 这个维度在这段时间发生了什么？

跨维度的意义、因果、人生阶段、用户状态判断属于 AI 认知，不得伪装为普通 Summary。

### 2.8 ALL_DIMENSIONS 保留为全维世界投影

旧仓的 `ALL_DIMENSIONS` 能力保留，但重新定义：

> 它不是一个父维度，也不是万能人生总结，而是同一时间窗口内多个维度的全景观察投影。

其职责是对齐不同维度的 Summary、Event、Claim 与世界锚点，向 AI 提供跨维观察材料。

因果结论必须由 AI 形成 Claim，并带 Evidence、置信度与可修正语义。

### 2.9 智能世界索引是公共能力

索引同时供：

- 系统智能推荐；
- AI主动搜索；
- 长会话回捞；
- 任务与行动追溯；
- 认知校验；
- 世界浏览。

索引负责找到世界，不负责最终替 AI 判断世界意味着什么。

### 2.10 智能推荐与主动搜索并存

系统在模型推理前根据当前会话主题主动推荐少量相关历史。

无明确主题或无强关联：

> 推荐 0 条。

模型看到推荐后仍拥有主动 Search / Follow / Compare / Inspect Evidence / Retrieve Original 的权利。

### 2.11 模型上下文由 AIOS 中控装配

模型不直接面对整个世界。

AIOS 在每次模型调用前，按本轮需要装配：

- 当前用户输入；
- 当前会话状态；
- 长会话必要连续信息；
- AI身份连续性；
- 当前任务与目标；
- 智能推荐记忆；
- 当前可用能力；
- 必要规则；
- 上下文预算。

### 2.12 AI自身世界必须回归统一世界

旧仓 `ai_self_world` 中关于 AI identity、relationship understanding、reflection、communication experience、operation experience、policy learning 的思想保留。

但最终不得继续以独立平行数据库成为第二个世界。

AI自身认知、经验和成长必须作为 AI维度写入统一 AIOS 世界。

### 2.13 认知策略允许学习，但必须可审计

继承 R6 的三类规则：

- Hard Boundary；
- Engineering Parameter；
- Cognitive Policy。

认知策略允许依据长期 Outcome、用户反馈和证据调整，但必须具备：

- scope；
- version；
- evidence；
- previous version；
- rollback；
- evaluation window。

### 2.14 世界写回是正式运行闭环

每次 AI 运行后，只有有长期价值的新增内容才进入世界：

- 新事实；
- 新事件；
- 新 Claim；
- 用户理解变化；
- 关系理解变化；
- AI经验；
- 目标与任务变化；
- 行动 Outcome；
- 用户反馈；
- 认知边界变化。

模型输出本身不得自动被当成事实。

### 2.15 认知修正向前演化

旧事实不改写。

错误 Claim、关系判断、用户理解、AI自我判断应通过新版本、撤回、反证、Retrospective Annotation 等机制向前修正，并传播到当前有效认知、总结入口和索引状态。

### 2.16 触发、Wake 与 Resident 调度

本机制**继承旧仓 v3.0 正式法统语义，不构成新的第二套宪法**。当前融合解释以以下旧仓规范内容为来源：

- `Haneof/fantonghui@aios-2.0:docs/constitution/AIOS核心系统宪法v3.0.md`：第 34 条、第 77～83 条；
- `docs/constitution/v3.0.1_规范裁决集_ADJ-001-012.md`：ADJ-001 / ADJ-002 / ADJ-003；
- `docs/constitution/AIOS宪法v3.0修改案_R5_AI认知执行运行时与驾驶权.md`：WAKE → Resident Cognitive Runtime 运行闭环；
- `docs/constitution/AIOS宪法v3.0修改案_R6_自适应认知策略与阈值主权.md`：主动介入、复盘、反思等触发策略属于可审计 Cognitive Policy。

融合后的法定解释：

1. **Observation 默认只写入统一世界，不直接唤醒 AI。**
2. 机械 Trigger 只判断“是否值得叫 Resident AI 看一眼”，不得写入情绪、关系、人生事件、用户意图等高阶语义结论。
3. 用户交互、Task 到期、周期 Review、已登记 Watch/验证条件、安全与恢复工作等可以形成 Wake；基础 Observation 只能经明确登记的机械规则间接形成 Wake。
4. 重复命中必须经过 Wake 去重、合并、冷却或抑制；不得用连续传感器输入制造 Wake 风暴。
5. Step-0 在模型认知之前执行确定性的安全、方便度、投放信道和预算门禁；其结果只控制能否调用模型/能否对外投放，不替 AI 判断世界含义。
6. Wake Reason 是 Resident 本次运行的第一任务指针，不是最终认知结论。Resident 可继续 Search / Inspect / Compare，并自主选择 Respond / Act / Silence / Writeback。
7. 所有非用户后台 Wake 必须复用同一个 Resident Cognitive Runtime 和统一 World；不得创建第二套“后台 AI 大脑”或第二数据库。
8. `PERIODIC_REVIEW` 保留 P15 专用 anchor/window 入口；`USER_INTERACTION` 保留 Conversation ingest 入口；其他 durable Wake 可走通用 C09 Resident dispatch。
9. 调度频率、冷却、预算和资源水位属于 Engineering Parameter；主动介入、复盘和重新检索的认知策略属于可版本化 Cognitive Policy，不得把默认数字写成永久语义真理。
10. 安全硬件的物理先行动作和最终对外通知/设备投放属于平台/安全承载层；Core C09 只负责世界内 Wake 生命周期与 Resident 认知调度边界。

当前实现落点：

- `src/aios_core/wake/service.py`：机械 Wake Bus、注册 Observation 规则、去重/合并/冷却、Step-0；
- `src/aios_core/runtime/turn_runtime.py::run_wake()`：durable Wake → 同一 Resident CognitiveRuntime；
- P12 `wake_due_tasks()`：Task schedule → `TASK_DUE` Wake；
- P15 `run_periodic_review()`：`PERIODIC_REVIEW` Wake → 同一 Resident Runtime；
- 功能闭环 SHA：`6f1e20307cd1ce47aefff281f652da16af635992`；
- 合并后验证：`c09-wake-dispatch` run `35501126516` / success。

### 2.17 Core 平台无关

AIOS Core 不绑定某一款手环、手机、Linux发行版或 Android ROM。

硬件与系统平台是承载层。

Core 首先在可重复的软件环境中跑通，再逐步接入真实设备。

---

## 三、机制级择优结果

| 机制 | 主要来源 | 融合结论 |
|---|---|---|
| AI作为系统驾驶员 | 旧仓 R5/R6 + 新仓世界模型 | 保留 AI 高阶认知主权，同时加入系统前置推荐 |
| 多维世界根定义 | 新仓为主 | 保留统一世界、平级维度、统一时间轴 |
| WorldObject 契约 | 旧仓为主 | 继承并按新语义清理 |
| SQLite世界存储/版本 | 旧仓为主 | 继承 append-only、revision、幂等、引用校验 |
| 基础维度 | 新仓语义 + 旧仓采集组件 | 来源型事实轴，禁止低层认知越权 |
| 数据整理 | 综合 | 机械数据机械压缩；复杂语义由 AI 整理但仍只写事实 |
| 单维度总结 | 新仓边界 + 旧仓时间金字塔 | 总结不做因果 |
| ALL_DIMENSIONS | 旧仓能力 + 新仓边界 | 升级为全维世界投影 |
| 智能世界索引 | 新仓定义 + 旧仓 query 工程资产 | 统一多路索引与世界锚点 |
| 智能记忆推荐 | 新仓为主 + 旧 Proactive Recall 经验 | 会话主题门，0条是正常结果 |
| AI主动深搜 | 旧仓 R5/CognitiveRuntime | 必须保留 |
| 上下文中控 | 旧 context pipeline + 新推荐机制 | 去除固定思维顺序 |
| AI用户理解 | 新仓结构 + 旧 Evidence/Claim | 可修正、可追溯 |
| AI自身世界 | 新仓统一世界 + 旧 AI Self 内容 | 统一入世界，不再另库 |
| AI关系与沟通经验 | 旧仓内容 + 新仓模块化 | 独立认知维度 |
| 策略学习 | 旧仓 R6 + 新仓 Strategy | 结果驱动、版本化、可回滚 |
| 认知修正 | 旧仓 Retrospective/Dependency + 新闭环 | 扩展为传播闭环 |
| 目标/任务/行动 | 旧仓对象体系 | 补 Outcome Evaluation 后继续使用 |
| Trigger / Wake / Resident 调度 | 旧仓 v3 第34、77～83条 + ADJ-001/003 + R5/R6，新仓 P12/P15/P16 实测 | Observation 默认不直唤醒；机械 Trigger → durable Wake → Step-0 → 同一 Resident Runtime；语义仍由 AI 判断 |
| 多Agent认知测试 | 新融合测试方案 | 真实模型入住长期虚拟人生，不再以固定题库证明认知成立 |

---

## 四、明确废弃或降级的旧思想

以下内容不得继续作为 AIOS 认知真理：

1. 固定认知维度白名单；
2. 2域/3天/30天/70% 等固定维度注册真理；
3. 固定关键词 → 固定人格/心理/关系结论；
4. 固定人生场景 → 固定维度；
5. Summary 直接输出跨维因果真相；
6. `ALL_DIMENSIONS` 作为新的父维度；
7. AI自身世界另建独立数据库；
8. 固定 step1→step2→step3→step4 作为模型必须执行的思维链；
9. 用 PseudoLLM、关键词匹配器或 Python 小程序通过“认知测试”；
10. 以几万道带标准答案的题目通过率证明 AI 已经形成长期认知；
11. 把硬件专属产品形态写进 Core 根语义。

---

## 五、测试法统

确定性单元测试继续负责验证：

- Schema；
- 存储；
- 幂等；
- 版本；
- 引用；
- 索引一致性；
- 状态机；
- 权限；
- 机械条件；
- 性能与资源预算。

但凡声称验证以下能力：

- 用户理解；
- AI自我成长；
- 跨维认知；
- 因果假设；
- 新维度发现；
- 关系演化；
- 沟通策略学习；
- 长期记忆使用；
- 世界驱动行动；

必须使用真实大模型在真实运行链中进行长期多Agent入住测试。

> Python 算法只能验证系统骨架，不得冒充 AI 认知本身。

---

## 六、当前法统状态

双仓融合完成前，任何历史文件中出现的 `FINAL`、`唯一最高`、`唯一宪法基线` 等表述，只代表该文件产生时的历史状态。

当前开发解释顺序：

1. 本《双仓融合工作基线注册表》；
2. 已经完成融合重写的独立机制文件；
3. 未重写机制同时参考新仓现有模块与旧仓 R5/R6/ADJ/代码实际能力；
4. 冲突时按“事实与认知边界、AI高阶认知主权、世界可追溯性、长期可演化性、可运行性”裁决；
5. 最终冻结前不得重新制造多个“唯一最高入口”。

---

## 七、融合完成条件

只有当以下事项完成后，才能签发真正的 AIOS v3.0 FINAL：

- 所有核心机制完成双仓对照；
- 保留/改造/废弃代码形成迁移矩阵；
- 最小完整运行链跑通；
- 多Agent长期虚拟人生入住测试通过；
- 认知错误、索引错误、推荐误触、世界写回、修正传播均有实测；
- 不存在固定题库答案逻辑或 benchmark-specific 认知代码；
- 宪法入口、模块索引、代码目录和测试体系一致。

