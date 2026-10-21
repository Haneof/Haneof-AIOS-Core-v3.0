# P16 召回基准工具

## 这个工具证明什么

AIOS 3.0 的完成标准要求：

> 换掉底层大模型之后，世界、经验和关系仍然继续存在。
> 对话上下文窗口耗尽之后，系统能从世界库恢复记忆，实现无缝衔接。

`tools/p16_recall_bench.py` 把这些要求变成**可复现、可审计**的自动化评测，包含两个场景。

### 场景一：recall（换模型召回）

每个 session 的流程：

1. 向全新世界库写入一条 anchor 事实（含「杭州」「23cm 柔性屏手环」等关键词）。
2. 用**模型 A** 让模型记住该事实。
3. 用**模型 A** 追问「我刚才让你记住的那句话里，我在哪个城市、做什么产品？」
4. 把运行时底层模型换成**模型 B**，再问同样的问题。
5. 判定回复中是否出现任一关键词（杭州 / 手环 / 柔性屏 / 23cm）。

如果 T2（同模型）和 T3（换模型）都能命中，说明记忆不依赖某个特定模型；如果 T3 失败，说明「记住」其实是该模型在替系统兜住。

### 场景二：exhaustion（上下文耗尽恢复）

`FusedTurnRuntime` 只把最近 `recent_turn_limit`（默认 8）轮渲染进提示词的 `RECENT CONVERSATION` 段，更早的历史会被挤出。本场景验证：**anchor 被挤出上下文后，系统仍能靠 `WorldSearchIndex` 检索世界记忆（`RELEVANT WORLD MEMORY` 段）完成召回。**

每个 session 的流程：

1. 向全新世界库写入同一条 anchor 事实。
2. T1：让**模型 A**记住该事实。
3. T2..T(N+1)：灌 N 轮（默认 9）与 anchor 完全无关的 filler 对话（海底火山、四季成因等，确保不含任何关键词），把 anchor 挤出 `RECENT CONVERSATION`。
4. T(N+2)：追问同一个 `RECALL_QUESTION`。
5. 判定回复中是否出现任一关键词。

## 怎么跑

### 前提

- Python 3.11+
- 已安装项目依赖（`pip install -e .` 或虚拟环境已就绪）
- 有效的 Gemini API key（OpenAI 兼容接口）

### 命令

```bash
export AIOS_GEMINI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export AIOS_GEMINI_API_KEY="<your-key>"

# 默认跑 3 个 session，模型 A/B 分别为 gemini-3-flash-preview / gemini-flash-lite-latest
python tools/p16_recall_bench.py

# 自定义
python tools/p16_recall_bench.py \
  --sessions 5 \
  --model-a gemini-3-flash-preview \
  --model-b gemini-flash-lite-latest \
  --out my-evidence.json \
  --timeout 90
```

### 场景选择

```bash
# 只跑换模型召回（recall）
python tools/p16_recall_bench.py --scenario recall

# 只跑上下文耗尽恢复（exhaustion）
python tools/p16_recall_bench.py --scenario exhaustion --filler-rounds 9

# 两个场景都跑（默认 all，--sessions 对每个场景分别生效）
python tools/p16_recall_bench.py --scenario all
```

exhaustion 场景相关参数：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--filler-rounds` | 9 | filler 轮数。**必须大于 `--recent-turn-limit`**，anchor 才会被挤出 `RECENT CONVERSATION`；不满足时工具会向 stderr 打印警告。每轮都是一次真实模型调用，默认 9 是够用的最小值，不建议调大。 |
| `--recent-turn-limit` | 8 | 透传给 `FusedTurnRuntime` 的上下文轮数上限，保证测试反映真实配置。 |

缺少必需环境变量时工具会**优雅退出**（返回码 2），不会抛栈或消耗额度。

### 输出

- **控制台**：按场景分组的逐 session 结果 + 各场景召回率（标注为「观测, 非门槛」）+ 宪法符合性结论与违规明细。
- **JSON 证据文件**（默认 `p16-recall-evidence.json`）：
  - `base_url`：端点地址（不含 key）
  - `model_a` / `model_b`
  - `anchor_fact` / `recall_question`
  - `config`：`recent_turn_limit`、`filler_rounds`、`filler_questions`（便于审计 filler 无关键词泄露）、`recommendation_limit`
  - 每条 session 记录带 `scenario` 字段（`recall` / `exhaustion`）
  - 每轮明细：模型、耗时、model_rounds、回复文本、是否命中、`recall_check`（该轮是否参与判定，T1/filler 轮为 false）、异常信息，以及 `constitutional_observation`（`current_topic` / `topic_gate_open` / `memory_cards_count` / `recommendation_reason`，来自 `FusedTurnResult`，运行时未暴露时为 `null`）
  - `constitutional_basis`：本工具判据引用的宪法条款（章节号 + 摘要 + `docs/constitution/AIOS_v3.0_Intelligent_Memory_Recommendation_System_Constitution.md` 路径）
  - `constitutional_compliance`：宪法符合性结论（`status` + 逐项 `checks` + `violations` + 已测/未测轮次数）
  - `observations.recall`：`by_scenario`、`total_recall_attempts`、`successful_recalls`、`recall_rate`，`is_pass_gate: false`
  - exhaustion session 附带 `topic_probe`：指代型追问轮的 `probe_topic` / `anchor_topic` / `topic_inherited` / `topic_state_reason`（宪法 3.2 主题继承观测，纯观测，不参与判定）
  - `verdict` 与 `summary.verdict`：只取 `constitutional_compliance.status`（`PASS` / `FAIL` / `NOT_MEASURED`）
  - `verdict_rationale`：人类可读的一句判定理由

## 判据与宪法的关系

本工具的判据以项目宪法（`docs/constitution/AIOS_v3.0_Intelligent_Memory_Recommendation_System_Constitution.md`）为唯一依据，分两个互不混淆的维度：

### 召回率为什么不是通过门槛

宪法**第二章 2.2「无主题不推荐」**写明：当前会话没有明确主题、或当前主题与历史世界没有足够强关联时，**推荐结果必须为空**，且「0 条推荐」是正常结果，不是失败。**第十四章禁止事项第 7 条**进一步禁止「因推荐结果为空而强行补充无关历史」。

exhaustion 场景的 filler 轮（海底火山、四季成因等）与 anchor 毫无关联，这些轮次 `memory_cards` 为 0 正是宪法要求的正确行为。如果把「召回率 100%」设为通过门槛，唯一能让它变绿的办法就是让系统在所有轮次无脑推送历史——这同时违反禁止事项第 1、3、4、7 条。因此：

- `recall_rate` 保留为**纯观测指标**（置于 `observations.recall`，`is_pass_gate: false`），用于回答「端到端召回链路是否工作」；
- 它**不进入 verdict**，文档与证据 JSON 中均明确标注。

### 宪法符合性才是门槛

`constitutional_compliance.status` 是 verdict 的唯一来源，当前覆盖两类可稳定测到的检查：

| 检查 | 引用条款 | 判定 |
|---|---|---|
| `no_forced_history_injection` | 十四-1 / 2.2 / 十四-7 | 主题门关闭（无当前主题）的轮次出现 `memory_cards > 0` → 违规 |
| `no_full_load_every_turn` | 十四-3 / 十四-4 / 十四-8 | 单轮卡片数超过推荐上限（5）或 `recent_turn_limit` → 违规 |

同时引用 3.2（主题来源可含「最近仍然持续有效的上一主题」）与十四-9（不得让模型必须先搜索才能获得相关历史）作为设计依据；exhaustion 末轮的 `topic_probe` 按 3.2 记录指代型追问是否继承 anchor 话题，仅作证据，不决定 PASS/FAIL。

### 已知局限

- **观测依赖运行时暴露**：`memory_cards` / `topic_gate_open` / `current_topic` 取自 `FusedTurnResult.context` 与 `.recommendation`。若轮次异常或运行时未暴露这些字段，该轮不计入判定；**全部轮次都拿不到时整体标 `NOT_MEASURED`**，绝不伪装成 PASS。
- **NOT_MEASURED 不等于通过**：verdict 为 `NOT_MEASURED` 时工具退出码为 1。
- 宪法符合性目前只覆盖「能稳定测到的检查」；「模型是否被迫先搜索」（十四-9）等语义层条款尚无机械化判据，需后续补充。

## 如何解读结果

| 场景 | 含义 |
|---|---|
| recall: T2 ✅ T3 ✅ | 系统本身可靠地记住了事实，换模型无影响。 |
| recall: T2 ✅ T3 ❌ | 记忆依赖模型 A 的「聪明」，模型 B 兜不住——这是系统缺陷。 |
| recall: T2 ❌ T3 ❌ | 记忆写入或召回链路有根本问题，需先修 bug。 |
| exhaustion: 追问 ✅ | 上下文耗尽后系统从世界库恢复了记忆，全链路成立。 |
| exhaustion: 追问 ❌ | anchor 已被挤出上下文且世界库检索/渲染失败，或索引未及时更新——需查 `RELEVANT WORLD MEMORY` 段渲染。 |
| 任何一轮 💥 | 网络或配置问题，检查 base_url/key/额度。 |
| `constitutional_compliance: FAIL` | 发现违反宪法的推荐行为（无主题推荐/全量加载/强行补历史），需修系统，不是修判据。 |
| `constitutional_compliance: NOT_MEASURED` | 没拿到任何一轮的 memory_cards/主题门观测数据，无法判定宪法符合性；修观测链路后重跑，不要手工填数。 |

## 记忆指代解析（2026-10-21，第 3 层修复）

exhaustion 场景的追问句是「我刚才让你记住的那句话里……」。这句话与 anchor 原文
**没有任何实词重叠**（追问句实词是「城市/产品」，anchor 实词是「杭州/手环」），
所以在修复前它有三层同时失效：

| 层 | 修复前 | 现状 |
|---|---|---|
| 主题门 `history_may_help` | 三张约 20 词的静态词表都不含这类表达 → `False` | 识别「记忆动作 + 前指」组合 → `True` |
| 候选暴露 `antecedent_fallback` | 未触发 | 触发（有界候选集） |
| 候选内容 | 词法检索只能给出 score=1 的并列结果 | **按记忆动作定向解析**，把下指令的那条用户原话排首位 |

关键点：**换检索对象，不扩词表**。这句话指的不是内容，而是一次记忆动作。
所以 Core 按 `记住 / 记下 / 记一下 / remember` 这些**动作标记**去查「谁下过这条指令」，
把那条用户原话作为 `explicit_memory_directive_anchor` 卡片交给模型判断——Core 只暴露
候选，不替模型认定用户指的是哪一句（宪法：认知允许不确定）。

同时锁住三条不许退化的边界：

1. **下指令那一轮不开启召回**（「请记住这句话：X」本身 `history_may_help=False`），
   否则每轮都会灌历史，违反十四-7；
2. **当前这句话不得成为自己的候选**（它自身也含「记住」二字）；
3. **世界里没有记忆指令时不得凭空造出锚点**，只能开主题门，不许假装找到。

回归测试：`tests/integration/test_p16_memory_directive_anchor.py`（9 项，全 hermetic）。
已反向验证：撤掉主题门那一层后，核心 2 项立即 FAIL。

## 已知限制

1. **单厂商**：当前默认只测 Gemini 的两个模型。项目标准要求「不依赖特定厂商」，因此这只是**部分证据**。拿到第二家厂商 key 后，把 `--model-b` 换成另一家即可补全。
2. **免费额度**：Gemini 免费 tier 有 RPM/IP 限制，大规模评测前建议确认额度或换付费 key。
3. **思考模型延迟**：Gemini 3 系列是思考模型，单轮延迟 5–15 秒属正常；`--timeout` 默认 60 秒，若频繁超时请加大。
4. **召回判定是关键词匹配**：不是语义等价判定。若模型说「浙江省会」而不说「杭州」，会被记为未命中——这是保守策略，漏报优于误报。
5. **session 间无状态共享**：每个 session 独立建库，测的是「单 session 内换模型」而非「跨 session 长期入住」。后者需要更长周期的 habitation 测试。
6. **exhaustion 场景成本**：每个 exhaustion session 需 N+2 次模型调用（默认 11 次），调大 filler 轮前请先评估额度。
7. **exhaustion 的「挤出」是轮数推断**：工具不直接解析渲染后的提示词，而是按 `filler_rounds > recent_turn_limit` 推断 anchor 已离开 `RECENT CONVERSATION`；若渲染/压缩策略变化，该推断可能失效（届时可改用 hermetic 测试直接断言提示词内容）。

## 与门禁测试的区别

- **门禁测试**（`tests/runtime/test_live_multimodel_habitation.py`）：hermetic，无网络，验证代码层面的协议解析和字段传递。
- **召回基准**（本工具）：live，需要真实模型，验证**端到端**的写入-索引-召回-提示词渲染全链路。

两者互补：门禁保证代码不变坏，基准保证系统在真实模型上确实能做到它承诺的事。
