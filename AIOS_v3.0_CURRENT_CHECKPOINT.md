# AIOS v3.0 当前工程断点

> 用途：新会话 / 新模型 / 新工程师进入仓库后的第一现场状态文件  
> 更新规则：每完成一个可验证节点立即更新；不得靠聊天记忆代替本文件  
> 仓库：`Haneof/Haneof-AIOS-Core-v3.0`  
> 分支：`main`

## 当前快照

- 时间：2026-09-20 14:47 +08:00
- 最后已验证功能代码锚点：`32fe9681842cd060c18bf1cfd3c2c0c2f5314530`
- 验证 Gate：`p12-execution-gate` / run `35495051476` / **success**
- 当前项目阶段：**P12 已完成，进入 P13 数据接入与机械清洗**
- 当前主干状态：**World → Recall → Model → Cognition → Dynamic Dimensions → Goal/Task → Authorized Action Envelope → Outcome 已形成统一世界闭环**
- 当前 blocker：**对话外现实数据尚未通过统一 adapter 接入；机械清洗规则需要落地且必须严格禁止跨维高阶认知**
- 下一主任务：**P13 多源现实数据接入 + 机械清洗**

## P12 已完成并通过 Gate

- 当前用户输入在模型推理前先写入世界，可作为同轮 pinned Evidence：GREEN
- Goal Proposal / revision lifecycle：GREEN
- Task creation / state machine：GREEN
- Scheduler 对 WAITING_TIME 任务做确定性 wake：GREEN
- RUNNING Task 才能提出外部 Action：GREEN
- Resident Model 可 propose Action，但能力目录不暴露 authorize / record_outcome：GREEN
- 外部 Action 必须经过独立 authorizer：GREEN
- Authorization 产生 SUBMITTED revision 与稳定 execution_id：GREEN
- Core 不直接执行外部副作用，只输出 dispatch envelope：GREEN
- 平台真实结果通过 Outcome 写回统一世界：GREEN
- SUBMITTED Action 不允许重复授权/重复 dispatch：GREEN
- Task Completed / Failed 必须引用真实 Outcome：GREEN
- Goal / Task / Action / Outcome / Wake 已进入统一 WorldStore 和索引：GREEN
- P12 聚合 Gate：GREEN

## 当前可运行主链

```text
Current User Input
↓
Observation (same-turn pinned evidence)
↓
Resident Model
├─ search_world / inspect
├─ read_ai_world
├─ dimensions
├─ cognition
├─ propose_goal / transition_goal
├─ create_task / transition_task
└─ propose_action
↓
Goal / Task / Action(PROPOSED)
↓
Independent Authorization Boundary
↓
Action(SUBMITTED) + execution_id
↓
Platform Connector
↓
Outcome
↓
Task completion / Strategy / Calibration / User Understanding
↓
Unified World + Index
```

## P13 当前目标

把对话外现实持续接入统一世界，但只做机械事实接入与机械清洗。

目标链：

```text
Phone / App / Sensor / Camera / MIC / Calendar / Notes / Payment / Order
↓
Source Adapter
↓
Canonical Observation
↓
Dedup / timestamp normalize / source normalize
↓
机械压缩或阈值事件化（仅适用于明确机制型数据）
↓
统一 WorldStore
↓
Index / Summary
↓
Resident AI 后续观察与认知
```

## P13 关键边界

1. Adapter 只能把现实事实标准化成 Observation / Event 等基础对象。
2. Adapter 不得生成“用户焦虑”“用户喜欢某人”“学习能力提升”等高阶认知。
3. 全部来源使用同一全局时间基准。
4. 原始图片/录音的 AIOS 长期事实入口优先为文本/结构化事实，不把媒体复制成长期世界真相。
5. 相册/社交/App 可作为读取入口；是否形成长期事实由后续合法机制决定。
6. 机制型高频数据允许确定性压缩，例如长时间稳定值只保留区间摘要和阈值事件。
7. 阈值必须属于测量/工程规则，不能偷偷变成心理判断。
8. 去重、时间归一、格式转换都不得改变事实语义。
9. 每个 Observation 必须保留 source_kind / modality / locator / 时间 / provenance。
10. 接入失败必须可审计，不得静默丢数据后假装世界完整。

## P13 首批必读

新仓：
1. 数据采集/清洗相关宪法文件
2. `src/aios_core/contracts/models.py`
3. `src/aios_core/ingest/conversation.py`
4. `src/aios_core/storage/sqlite_store.py`
5. `src/aios_core/query/search.py`

旧仓择优来源：
6. Observation ingest / dedupe
7. sensor compression
8. app adapter
9. media-to-text / location / calendar / payment/order adapters
10. cleaning / normalization / provenance

## P13 禁止事项

- 不恢复旧“清洗阶段跨维推理”。
- 不用关键词把事实自动打成心理标签。
- 不复制整个相册/录音库到 AIOS 世界。
- 不把支付事实与订单语义混成一个维度。
- 不把 App 原始结构直接当高阶 Claim。
- 不因压缩节省空间就丢失阈值异常事件。
- 不让平台 adapter 决定用户意义。

## 当前不可推翻的已决事项

- 世界唯一、时间轴唯一。
- 维度平级。
- 事实与认知分离。
- Summary 不做跨维因果。
- 索引与推荐分离。
- 外部行动授权独立于模型。
- AI负责意义，程序负责确定性机制。

## 恢复现场规则

接手时先获取 GitHub `main` 实时 HEAD，并审查本文件功能锚点之后的 commits / CI。纯地图/checkpoint文档提交可越过；功能代码必须先确认 Gate 与边界再继续。
