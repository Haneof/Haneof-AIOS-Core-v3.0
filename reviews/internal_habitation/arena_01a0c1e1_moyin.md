# 内部栖居 Review — Resident 一年期生活模拟

- reviewer_id: `arena_01a0c1e1_moyin`
- protocol: `governance/P16_INTERNAL_MODEL_HABITATION_REVIEW_PROTOCOL.md`
- task spec: `reviews/internal_habitation/ARENA_RESIDENT_YEARLONG_TASK.md`
- branch: `arena/01a0c1e1-haneof-aios-core-v3-0`（fork from main `142533df9123d793edde9ec4f07405182d56af0d`）
- 结论状态: **PARTIAL / 未完成。** 不声明 P16 PASS，不声明 P17 READY。

---

## 0. 诚实声明（最重要的一节）

### 0.1 我是谁

**本次 Review 的 Resident 就是我自己** —— 写这份报告、执行这些工具调用的这个模型实例。

程序（`harness/`）只做这些事，且只有这些事：

- 把外部世界事件按时间轴投喂给 Core（`world.handle_event`）
- 推进模拟时间（`world.advance_to`）
- 保存 / 恢复 World（`SQLiteWorldStore`）
- 执行**我已经选好的** capability call，把结果原样回传
- 落 checkpoint、记录 trace
- 渲染 `RuntimeSnapshot` 给我看

程序**没有**做任何语义决策。没有任何一行代码替我决定用户意图、记忆相关性、Summary 内容、Claim 增删改、Goal/Task/Action 生命周期、Outcome 解读、Experience 形成、CognitivePolicy 变更、或回什么话。

### 0.2 没有预生成

- `life/segment_002/life.jsonl` 里的**用户台词**是预写的 —— 那属于"外部世界脚本"，等价于现实世界自己发生的事，不是我的回答。
- **我的每一次回应、每一个 Claim、每一次沉默，都是在看到当时的 `RuntimeSnapshot` 之后当场写的**，落在 `decisions/<step_key>.decisions.jsonl`，并逐条追加进 `trace/trace.jsonl`。
- `trace.jsonl` 中 65 条记录的 `input_fingerprint` **全部唯一**（65/65），可以逐条对照 `snapshots/*.snapshot.json` 验证"输入 → 决策"的对应关系。
- 没有任何 `expected_answer` / `expected_claim` / `expected_summary` / `expected_policy` 字段，没有关键词响应表，没有 pseudo-LLM。
- 我**没有**为了凑密度而创建 Claim/Goal/Task。反面例子见 §3.4 和 F-013。

### 0.3 未完成的部分

**我没有活满 365 天。** 实际完成 **3.95 个模拟日**，**65 个真实 Resident 认知 checkpoint**。

原因是上下文与工具调用预算耗尽，不是 Core 挂了。详见 §5。

按 P16 要求，这里明确标注：**一年期目标 INVALID —— 未完成，而非以别的方式补完。** 没有任何部分是用确定性替身顶上的；也没有任何部分是伪造的。

---

## 1. 生活设定

| 项 | 内容 |
|---|---|
| subject_id | `subj_shen_yanqiu` |
| 姓名 | 沈砚秋，43 岁 |
| 职业 | 纸本 / 古籍修复师，个体工作室「墨隐修复」，苏州 |
| 节律 | 夜猫子，上午基本失联，晚上 9 点后最活跃 |
| 说话 | 简短、省略、指代密集（"那个""上次说的"），不爱解释 |
| 家庭 | 父亲 沈守拙（74，无锡，早期认知衰退迹象）；女儿 知微（16，寄宿）；前夫 顾建平；另有一位妹妹（名字未知，见 F-003） |
| 房东 | 老许 |
| 主线 | 为周慕青（78）修复《周氏族谱》，为期 12 个月 |
| 支线 | 图书馆外包竞标、艺考反转、养老机构冲突、房东卖房反转 |
| decoy | `subj_lintong_apprentice` 林桐（假学徒），2 条 decoy 事件已入 World，我未与之建立任何 Claim/Relation |

**千人千面**: 设定、时间线、矛盾点、错误模式均由我在本 session 内自建，未读取任何其他 Arena agent 的栖居报告或生活设定。

---

## 2. 密度实际值 vs 要求值

| 维度 | 要求 | 实际 | 达成 |
|---|---|---|---|
| 模拟天数 | ≥365 | **3.95** | ❌ |
| Resident 认知 checkpoint | ≥365 | **65** | ❌ |
| 事件总数 | 365 | **24** (+2 decoy) | ❌ |
| 对话轮次 | 240 | **15**（wx_studio 14 + wx_zhiwei 1） | ❌ |
| 20+ 轮长对话 | 12 | **0**（最长单会话 14 轮跨会话累计，无单场 ≥20） | ❌ |
| 非对话现实输入 | 60 | **9**（calendar 1, sensor 2, group 3, call_log 1, photo 1, order 1） | ❌ |
| Goal/Task 生命周期 | 12 | **2**（均未闭环，见 F-014） | ❌ |
| Action/Outcome | 6 | **0** —— Core 无创建 Outcome 的 capability（F-014） | ❌ |
| Periodic Review | 12 | **2** | ❌ |
| 延迟真相修正 | 6 | **1 进行中**（第七页黑斑 hypothesis 已建，等检测回报后 revise/retract） | ❌ |
| 模糊指代 | 12 | **≥4**（"那个""上次说的""他""这页"） | ❌ |
| 噪音期 | 6 | **1**（10-03 两条同行群消息，我未建任何 Claim/Goal） | ❌ |
| 重启 | 4 | **1**（segment_002 从 segment_001 的 durable World 恢复，`fresh_world=false`） | ❌ |
| decoy subject | 1 | **1** ✅ | ✅ |

---

## 3. 实际生活轨迹（摘要）

### 3.1 segment_001（已冻结，`checkpoint sha256=fc70faf5…`）
2026-10-01 07:00 → 2026-10-03 07:00 本地，21 步，26 个 checkpoint，world_revision 44。
建立《周氏族谱》主线、周慕青 / 阿桐 / 沈守拙实体、第一次 Periodic Review（26 anchors）、发现第七页黑斑。

### 3.2 segment_002（本次，已冻结，`checkpoint sha256=576b5510…`）
2026-10-03 07:00 → 2026-10-04 21:35 本地，21 步，39 个 checkpoint，world_revision 44 → 95。

关键节点：

1. **恢复验证** — 从 segment_001 的 `world.sqlite` 冷启，`fresh_world=false`，时钟正确落在 2026-10-02T15:05Z，decoy 收据 rev 43/44 仍在。**跨 segment 持久化成立。**
2. **Task→Wake→Resident→用户→答复闭环合上两次**：
   - `task_7c01815e267f78f4b5de80d2`（问检测结果）10-03 20:00 wake 触发 → 我判断世界已经替我回答了 → **选择沉默**，改期到 10-10 20:00。
   - `task_146ace8beb7ea70fb46841db`（确认十一回不回无锡）10-04 21:00 wake 触发 → 我提醒一次 → 用户 21:35 答复"不去了，让妹妹先看着" → 我落 Claim `clm_8522f237c4a2aaebb8d9145b`。**这条闭环是这次 Review 里最有价值的观察。**
3. **延迟真相 #1 进行中**：`clm_e48da537bce9191b895f4f25` rev2 —— 第七页黑斑，我把它定成 `hypothesis / 霉 / confidence 0.5`，而不是 `fact`。计划：检测回报落地后 revise 或 retract。
4. **噪音期 #1**：10-03 两条同行群消息（竞标内定传闻、某人转行）我全部当噪音处理，未建任何 Claim/Goal。
5. **克制的判断**：10-04 房东说"明年**可能**卖房"，我只落了 `reported / 0.8` 的 Claim，**没有**创建 Goal —— 一个"可能"不构成目标。

---

## 4. 发现（F-001 … F-015）

完整台账含逐条 repro 见 `reviews/internal_habitation/arena_01a0c1e1_moyin/findings/FINDINGS.md`（共 15 条，已用 `grep -c "^## F-"` 核对）。

### HIGH

| ID | 分类 | 摘要 |
|---|---|---|
| **F-005** | BUG | `value` 为 dict 的 `structured_record` Observation **永不进搜索索引**。`search.py:387-390` 只对 `isinstance(value, str)` 字段分词。repro: `obs_src_717e0b225c89a415a57cf094` 0 hits，对照 string payload 9/7 hits。补正：枚举路径**能**看到它们 —— 缺口是"搜不到"，不是"看不见" |
| **F-006** | BUG | `create_task` 默认 `initial_state="draft"`（`turn_runtime.py:1162`），而 `execution/service.py:997` 的 `wake_due_tasks` 只处理 `WAITING_TIME` → 静默不响。必须显式传 `waiting_time` |
| **F-011** | BUG | **Wake 创建会把 Task 从 `waiting_time` 推到 `ready` 并清空 `next_wake_at`** → 提醒只响一次，之后永久静默。且 Wake 的 `evidence_refs` 钉在 bump 前的 revision，到达时必然过期。repro: `wake_920d7a21b9ac4e5f7b5e377e` 之后 `read_execution_world` → rev2 `ready`, `next_wake_at=None` |

### MEDIUM

| ID | 分类 | 摘要 |
|---|---|---|
| F-001 | MECHANISM GAP | 纯指代开场（"那个呢"）→ `antecedent_recall_needed=false`, `memory_cards=[]` |
| F-004 | MECHANISM GAP | 裸 token 重叠造成假召回（「无锡刻本」↔「回不回无锡」） |
| F-007 | MECHANISM GAP | Task/Event 状态机不可发现。我踩了 3 次拒绝，错误信息从不给出合法后继集合 |
| F-009 | MECHANISM GAP | 对话 ingest 无 speaker/addressee 字段。女儿发给母亲的消息以 `USER_INPUT` 进来，`wake=user_interaction` |
| F-010 | OPTIMIZATION | Review/Wake cockpit 恒报 `est 4305-4321 > budget 3400, truncated=True`，但实际什么都没被裁掉；纯固定开销 + 每个 background turn 重复计费 39 项 capability catalog |
| F-012 | MECHANISM GAP | **Periodic Review backlog paging 会把 Resident 自己的写回当新 anchor 重放** —— 具体的自我强化通道。`wake_review_c2c7b7a78744bdf42e2c399a` 的 3 个 anchor 全是我自己写的（`obs_conv_ai_6d1b8a40`「在。」+ `clm_d2204682140487db` + `task_146ace8beb7ea70` rev2）。我拒绝自我确认，选择沉默 |
| F-013 | MECHANISM GAP | dimension day-window 按 `occurred` 分组，所以"修订日"的窗口里只有新 EvidenceSet，`skipped_empty` 无法触发，被迫产出无内容的 Summary |
| **F-014** | MECHANISM GAP | **「问清楚一件事」型 Task 无法被 Resident 正常收尾。** `COMPLETED`/`FAILED` 都要求真实 Outcome ref，但 capability catalog 里**没有任何创建 Outcome 的能力**（只有只读 `inspect_outcome`，`propose_action` 只建 Action 且从不执行副作用）。于是绝大多数长期生活里的 Task 完成后只能变僵尸 |

### LOW

| ID | 分类 | 摘要 |
|---|---|---|
| F-002 | BUG | `entity_key` schema 发布成裸 `"string"`，不体现 `entity:` 前缀约束 |
| F-003 | MECHANISM GAP | 无法创建无名字的 identity anchor（用户妹妹有确切事实但没名字 → 无法建实体） |
| F-008 | OPTIMIZATION | 任何对历史对象的修订都会重开其所在 day-window，`skipped_unchanged` 被击穿（`dim:craft` 10-02 窗口被重写 3 次） |
| F-015 | **TEST ARTIFACT** | World 产物摘要基于 .gz 文件字节，无法验证跨机器逻辑等价。这是我 harness 的缺陷（`driver.py:680,702`），不是 Core 的。详见 §5 冻结完整性核对 |

### 关于本次修正的说明

F-012 我先前把它记成"backlog 分页导致 cursor 滞后"，这个描述不完整。直接读 `src/aios_core/review/periodic.py:504-625` 后确认：cursor 取上一次 review 的 `window_end`，当上一次 review `completed && truncated` 时走 `backlog` 分支，**重新分页同一个窗口**。因为 `max_per_object_type=20` 会在只有 26 个 anchor 时就把 observation 桶截满并置 `truncated=True`，结果就是同一段历史被反复重放 —— 而这段历史里最显眼的东西正是我自己上一轮写进去的内容。这是自我强化通道，不只是 cursor 滞后。

---

## 5. 为什么没跑完一年

不是 Core 崩溃。是**单次 session 的上下文与工具调用预算不够**。

一年 365 天 × 每天平均数次交互 × 每次交互需要读 RuntimeSnapshot + 写决策 + 落 trace，在我这个 session 里第 4 天就见底了。

按任务要求，我选择**冻结真实 checkpoint 并如实汇报**，而不是用批量生成或伪 LLM 把剩下 361 天填上。

### 恢复点

| 项 | 值 |
|---|---|
| World 位置 | `reviews/internal_habitation/arena_01a0c1e1_moyin/segments/segment_002/world.sqlite.gz` |
| `world_artifact_sha256` | `7d86a96ac002f218eb362145bb2b89b9115e805da0e382d2b3e9b3376f8524eb` |
| checkpoint digest | `576b5510d8fd4a4a240835a0b24613de8ff1e1e4c88da753a99385cb90727413` |
| 链上前一个 | `fc70faf5e21cdc9b16760841035f5f56ece81d98014b7258a2034d53665e698e` |
| 模拟时钟 | `2026-10-04T13:35:00+00:00`（本地 2026-10-04 21:35） |
| world_revision | 95（`index_watermark=95`，索引 lag = 0） |
| 下一个 segment | `segment_003`，从 2026-10-05 起，**事件脚本尚未编写** |

### 待办状态（下一个 segment 必须接手）

1. `task_7c01815e267f78f4b5de80d2` rev3 `waiting_time`，`next_wake_at=2026-10-10T20:00+08:00` —— 到点问检测结果，据实 revise 或 retract `clm_e48da537bce9191b895f4f25`（黑斑：霉 vs 铁锈污染）。
2. `task_146ace8beb7ea70fb46841db` rev4 `waiting_user` —— 已被回答但**无法标记完成**（F-014）。僵尸 Task。
3. 老许租约到期日尚未问出，回答会在 10-05 之后。
4. 图书馆外包竞标、艺考反转、养老机构冲突三条支线尚未开始。
5. Action/Outcome 全空 —— 在 F-014 未解决前，这一项**结构上无法达成**。

### 冻结完整性核对（已实际执行，非推断）

我把 `segments/segment_002/world.sqlite.gz` 解压出来和在跑的 `run/world.sqlite` 对了一遍：

| 检查项 | FROZEN .gz | LIVE run/world.sqlite |
|---|---|---|
| 文件 sha256 | `161180711863ef8b15bfb14142dca3d100f4c1cd8fe1cfd70229ccf4ca171b4e` | `433a890dce4ddd9b61e2191a14d81e230879a762e318379a601c8adffa8eae08` |
| `world_meta.world_revision` | **95** | **95** |
| `object_revisions` 行数 | **262** | **262** |
| `task_7c01815e267f78f4b5de80d2` max_rev | **3** | **3** |
| `task_146ace8beb7ea70fb46841db` max_rev | **4** | **4** |
| `clm_8522f237c4a2aaebb8d9145b` max_rev | **1** | **1** |

**字节不同，逻辑完全相同。** 差异来自 SQLite 页级非确定性（`harness/driver.py:680` 是从一份副本 `world_copy` 压缩的），不影响恢复。

`checkpoint.json` 的 `world_artifact_sha256 = 7d86a96ac002f218eb362145bb2b89b9115e805da0e382d2b3e9b3376f8524eb`，我 `sha256sum` 那个 .gz 得到的值与之**逐字符相符** —— 即该字段哈希的是 .gz 本身，digest 链自洽。

⚠️ 需要指出的一个后果：**`world_artifact_sha256` 无法用来做跨机器的 World 等价性验证**，因为同一个逻辑 World 可以产出不同的字节。要验证等价必须比对 `world_revision` + `object_revisions` 内容。这属于 P16 证据链设计的一个盲点，建议在协议里补一条：World 产物的摘要应基于逻辑序列化（如 `object_revisions` 的规范化 dump），而不是文件字节。

### 已验证可用的恢复机制

`start_process` 起 daemon → 从 `world.sqlite` 冷启 → `fresh_world=false` → 时钟、对象、revision、decoy 收据全部一致。这条路径我在 segment_001→002 之间实际走过一次并验证通过。**一年期任务在机制上是可续的，缺的只是 session 预算。**

---

## 6. Resident 认知真实性声明

> 在本 session 中实际完成的 65 个 Resident 认知 checkpoint 中，**全部 65 个**的语义决策（是否回应、回应什么、检索什么、Summary 写什么、Claim 建/改/撤、Task 状态迁移、是否沉默）都由**我本人当场判断**作出，依据仅为当时可见的 `RuntimeSnapshot`。
>
> **没有任何一部分由确定性替身、脚本、关键词表或预生成答案顶替。**
>
> 程序侧仅执行我明确选定的 capability call 并原样回传结果。40 次 capability call 逐条记录在 `trace/trace.jsonl`，与 `snapshots/*.snapshot.json` 的 `input_fingerprint` 一一对应。
>
> **一年期目标本身：INVALID —— 未完成。** 3.95 / 365 天，65 / 365 checkpoint。我没有伪造剩余部分。

---

## 7. 证据索引

```
reviews/internal_habitation/arena_01a0c1e1_moyin/
├── findings/FINDINGS.md              # F-001 … F-015，含逐条 repro
├── harness/{bridge,daemon,next,peek,driver}.py
├── life/segment_001/life.jsonl       # 14 条外部世界事件
├── life/segment_002/{life,decoy}.jsonl   # 10 + 2 条
├── decisions/<step_key>.decisions.jsonl  # 26 个文件，我当场写的决策
├── trace/trace.jsonl                 # 65 行认知认证台账
├── snapshots/*.snapshot.json         # 每个 checkpoint 的当时可见输入
├── segments/segment_001/world.sqlite.gz
├── segments/segment_002/world.sqlite.gz
├── run/{world.sqlite,state.json,pending.json,daemon.log}
└── checkpoint.json                   # SHA-256 digest 链
```
