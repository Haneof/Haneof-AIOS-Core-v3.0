# AIOS v3.0 开发方案（PM，2026-10-26）

> 依据：`reviews/AIOS_PM_REPO_AUDIT_2026-10-26.md`。
> 这份方案只解决一件事：**让手环真的记得住人**。其他都排在它后面。

---

## 0. 目标定义（先定验收，再排任务）

当前产品状态用一句话说：**一轮对话结束后，世界上没有留下任何关于这个人的认知。**

验收不看"感觉好点了"，看四个数：

| 编号 | 指标 | 现状 | 目标 | 怎么测 |
|---|---|---|---|---|
| M1 | 含 durable 事实的轮次，durable claim 产出率 | **0%**（3 轮提示词实验 + 1 轮真实 CLI 回合，全为 0） | ≥ 90% | 真实端点，同一场四轮对话，数 `object_revisions` 里的 claim |
| M2 | 跨会话可复述率（**关掉逐字对话**） | 0 | 100% | `recent_turn_limit=0`，第二场会话仍答出姓名/城市/产品 |
| M3 | 重复陈述产生的重复 claim | 未测（协议修好后必然出现） | 0 | 连续两轮问同一事实，claim 计数不增 |
| M4 | 单轮回复延迟 | 15–55s（本机网关，含推理） | 不增加 | 同端点前后对比 |

M2 是唯一不能被伪造的指标。M1 可以靠模型"演"，M2 不行——关掉逐字对话之后，它要么从身份锚里读到了，要么就是不知道。

---

## 1. 阶段划分

```text
S0 止血（1 天）      让"仓库健康"变成一个能跑出结论的命令
   ↓
S1 换协议（2–3 天）  用模型被训练过的接口，而不是自创文本协议
   ↓
S2 证明（1 天）      真实端点跑 M1–M4，取证落库
   ↓
S3 治理归位（0.5 天）记录回到与现实一致
```

S1 之前不碰 UI、不碰硬件、不碰 Android 适配、不碰 C16。原因：S1 会改模型面对的输出契约，任何建立在其上的东西都要返工。

---

## 2. S0 — 止血

### T01 让冻结校验不依赖换行符

- **问题**：`tests/c15_persistence/killpoints/test_killpoints.py` 对 `PROBE_MANIFEST.json` 的**原始字节**取 sha256。Windows 上文件被 CRLF 重写后，哈希对不上，而 git 的 `eol=lf` 让 `git status` 看不见这个差异——文件"看起来没改"，测试却收集失败，**整个 `pytest tests` 直接挂掉**。
- **改法**：校验前把 `\r\n` 归一到 `\n` 再取哈希。
- **验收**：Windows 上 `pytest tests/c15_persistence` 能收集并通过。
- **反向验证（必做）**：把 manifest 里改一个字符，测试必须变红。归一化不能把校验变空。

### T02 清理 CRLF 入库的两个测试文件

- **问题**：`tests/unit/test_m1_001r_adv_independent_redteam.py`、`tests/unit/test_m1_001r_high_entropy_audio.py` 的 blob 内含 CR，与 `.gitattributes` 的 `* text=auto eol=lf` 冲突，`git status` 永久显示 691 行假改动。
- **改法**：`git add --renormalize`。
- **验收**：`git status` 干净，`git diff` 无输出。

### T03 加一个统一检查入口

- **问题**：55 个 workflow 各跑子集，仓库里没有 Makefile / tox / nox / scripts。没有任何一条命令能回答"这个仓库现在是健康的吗"。
- **改法**：`tools/check.py`，三步：跑全量测试 → 跑治理基线校验 → 打印跳过原因分布。不引新依赖。
- **验收**：`python tools/check.py` 一条命令输出 PASS/FAIL 与耗时；全量耗时 ≈ 17 分钟（现状基线）。

### T04 并发 attach 的持久化不变量（**需 owner 定性**）

- **现象**：`test_ca2_015_concurrent_attach_yields_one_canonical_winner` 稳定失败（3/3，非偶发）。两个线程同时 attach，其中一个抛 `sqlite3.OperationalError: attempt to write a readonly database`，被包成 `StoreError` 逃出 worker，测试只收到 1 个 outcome，断言 `['accepted'] != ['accepted','refused']` 失败。
- **为什么不能顺手改**：这正是 C15 的持久化不变量（"一个 canonical winner，另一个必须被拒"）。要区分两种情况：
  - **测试写窄了**：worker 只捕获 `BackgroundModelResponseConflict`，`StoreError` 没算 outcome → 改测试。
  - **内核真漏了**：store 把一次可重试的并发写映射成不可重试的 `storage_unavailable`，语义上应该映射成 `VERSION_CONFLICT` → 改 `sqlite_store`。
- **验收**：先给出定性结论，再改；改完后连跑 10 次全绿。

---

## 3. S1 — 换协议（本方案的核心）

### 为什么是这里

审核的实测结论（单变量对照）：**同一个模型、同一个 5272 字符的提示词，只把接口从"写 JSON 块"换成 `tools` 数组，模型第 1 轮就调用了 `commit_ai_world_claim`**；换接口之前，同一提示词跑了三轮，调用数恒为 0。

这不是提示词问题，是接口问题。此前三轮提示词工程（3807 → 4859 → 5272 字符）都是在错误的接口上做优化，所以全部无效。

### T05 `input_schema` → JSON Schema 转换器

- **现状**：内核的 `input_schema` 是一门自定义迷你语言（34 种类型串），只有 7 个能力被渲染出参数名，其余 46 个模型只能猜。
- **改法**：表驱动转换，覆盖：`string` / `integer` / `number` / `boolean` / `array[T]` / `array[{object_id:string,revision:integer}]` / `{object_id:string,revision:integer}` / `number[0,1]` / `a|b|c`（→ enum）/ `object?` / `ISO-8601 datetime` / 尾缀 `?`（→ 非 required）。
- **验收**：表驱动测试遍历全部 53 个能力，每个生成的 schema 满足：① `required` 集合 == `required_arguments()` 的结果；② 用 `jsonschema` 对现有 `_example_value()` 生成的样例校验通过。
- **风险**：转换器是"模型看到的世界"和"内核校验的世界"之间的桥。**桥错了，模型会稳定地写错**。所以必须有 53 项全量断言，不能抽样。

### T06 provider 支持原生工具调用

- **现状**：`grok_provider.py` 里没有 `tools`，没有 `tool_calls`，只有一个正则从散文里抓 ```json``` 块（`_extract_capability_call`）。
- **改法**：新增 `stream_chat_with_tools()`，payload 加 `tools`；SSE delta 里按 `index` 聚合 `tool_calls`（name 首帧给，arguments 分片拼接）。**旧的 `stream_chat` 签名不变**，避免一次改动打碎所有调用方和测试。
- **验收**：loopback stub 服务器造分片 `tool_calls`（arguments 拆成 3 段），解析出的参数 JSON 与预期完全一致；现有 `test_05_sse_stream_parsing_against_loopback_stub` 保持绿。

### T07 放宽 `ModelDirective` 不变量（**契约变更，需 owner 拍**）

- **现状**：`ModelDirective.__post_init__` 硬性禁止 `capability_calls` 与 `response` 同时存在（`"directive cannot request capabilities and terminate simultaneously"`）。这个不变量**没有任何测试覆盖**——它不是被验证过的设计，只是当初随手加的一道门。
- **为什么必须改**：原生工具调用下，模型会**一次响应里既写记忆又回答用户**（实测 T3：`commit_world_claim` + `reply_to_user` 同时出现）。不改这个不变量，模型天然给出的双通道会被内核判非法。
- **改法**：允许共存，并在回合循环里定一条规则：
  - 本批调用**全是写**（`side_effecting=True`）→ 执行，然后用 response 终止，**不多一轮**（省一次往返）。
  - 本批调用**含读**（`side_effecting=False`）→ 执行，回灌结果，再叫一轮（否则回复是在没看到读结果的情况下编的）。
- **验收**：两条路径各一个测试；写路径断言 `model_rounds == 1`；读路径断言 `model_rounds == 2` 且第二轮能看到工具结果。

### T08 写入去重

- **问题**：实测 T4 把 T1/T3 的四条事实**原样又写了一遍**（4 次调用）。`_commit_ai_world_claim` 和 `ai_world.commit` 都没有内容级去重。协议一修好，世界会立刻被重复 claim 填满，"每次问到都再写一遍"还会把 revision 链搞脏。
- **改法**：在 (domain, 归一化 statement, subject) 上做内容级去重，命中时返回 `duplicate: true` 而不新建 revision。
- **验收**：连续两轮陈述同一事实，claim 计数不增（M3）。
- **顺序**：**必须和 T06/T07 同一批上线**。它是 T06 的直接后果，不是可选项。

### T09 热集选择

- **问题**：53 个能力、28 个写路径。全给 schema 会挤占上下文并降低选择准确率；只给 7 个又不够用。
- **改法**：advertise 12–15 个（7 个连续性写 + 必要的读），其余仍留在提示词名单里但不给 schema。
- **验收**：对比 12 / 25 / 53 三档的工具选择准确率与单轮延迟，取拐点。**这一条要实测，不靠猜。**

---

## 4. S2 — 证明

### T10 探针切原生模式，跑 M1–M4

- **改法**：`tools/live_continuity_probe.py` 加 `--native-tools` 开关，走 T06 的新方法。
- **验收（三条全过才算过）**：
  1. M1：四轮对话至少 1 条 durable claim，内容含姓名 / 城市 / 产品；
  2. M2：`--recent-turn-limit 0` 重跑，第四轮仍答对（证明是锚不是回声）；
  3. M3：连问两遍，claim 计数不增。

### T11 内核那一半继续无网络可测

- **改法**：`tests/runtime/test_continuity_end_to_end.py` 的脚本化 handler 改成"原生 tools 形状的假响应"（calls + response 同时给）。
- **验收**：不联网，2 秒内跑完；断言跨会话锚里仍有事实。

---

## 5. S3 — 治理归位

### T12 checkpoint 与现实对齐

- 更新到 2026-10-26；把 WINDOW 84 回执里的 "Live HTTP 200 against grok-4.7 已验证" 标为 `UNREPRODUCIBLE_ON_CURRENT_ENDPOINT`（今天 grok-4.7 稳定 502，该测试是 opt-in 跳过）。
- **不删历史**，只加状态。根原则第 12 条：认知翻案向前修正，不能删除过去。

### T13 PR 清算

- 60 个开放 PR，32 个标 `DO NOT MERGE`；#340–#347 是同一件事的 8 个连续 PR。
- 动作：证据类合成一个索引后关闭；重复的合并成一个。**开放 PR 数量本身是风险**——没人能说清现在到底有什么在飞。

### T14 任务板更新

- 把"唯一当前任务"从 `PM-AUDIT-C15-EVIDENCE-RECONCILIATION-001` 改成 S1 的任务号，并说明 P16-MEMORY-DIRECTIVE-001 / P16-IDENTITY-CONTINUITY-001 已并入 main（#401）。

---

## 6. 任务表

| ID | 任务 | 依赖 | 改动面 | 需 owner 拍 |
|---|---|---|---|---|
| T01 | 冻结校验归一化换行 | — | `tests/c15_persistence` | 否 |
| T02 | CRLF 重归一 | — | 2 个测试文件 | 否 |
| T03 | 统一检查入口 | T01 | `tools/check.py` | 否 |
| T04 | 并发 attach 定性 | — | 测试或 `sqlite_store` | **是**（定性） |
| T05 | schema → JSON Schema | — | `capabilities.py` + 测试 | 否 |
| T06 | provider 原生 tools | T05 | `grok_provider.py` | 否（纯新增） |
| T07 | 放宽指令不变量 | T06 | `cognitive_runtime.py` + 回合循环 | **是**（契约） |
| T08 | 写入去重 | T07 | `turn_runtime.py` / `ai_world` | **是**（语义） |
| T09 | 热集选择 | T06 | 渲染 + 实测 | 否 |
| T10 | 探针切原生模式 | T06–T08 | `tools/live_continuity_probe.py` | 否 |
| T11 | 端到端测试改形状 | T07 | `tests/runtime` | 否 |
| T12 | checkpoint 对齐 | S2 | `AIOS_v3.0_CURRENT_CHECKPOINT.md` | 否 |
| T13 | PR 清算 | — | GitHub | **是**（关闭 PR） |
| T14 | 任务板更新 | T12 | `governance/` | 否 |

关键路径：**T05 → T06 → T07 → T08 → T10**。其余可并行。

---

## 7. 风险与回滚

| 风险 | 表现 | 处置 |
|---|---|---|
| T05 转换器有偏差 | 模型稳定写错某个参数，看起来像"模型笨" | 53 项全量断言；错误必须落在内核而不是模型身上 |
| T07 放宽不变量后出现歧义 | 模型既调用又回复，用户看到重复内容 | 只对"全是写"的批次走快路径；含读一律回灌 |
| T08 去重过激 | 语义相近但不同的陈述被吞 | 只对**归一化后完全相同**的 statement 去重；近似交给模型判断 |
| T09 热集选小 | 模型想调的能力不在工具表里 | 保留提示词名单 + 明确告知"未列出的能力需先查询" |
| 端点不可用 | 502 / 超时（今天已遇到一次） | 探针加重试；取证结论只在完整跑完时才算数 |

**回滚点**：T06 是纯新增方法，`stream_chat` 不动；T07 若引发问题，把 `_native_tools` 开关关掉即回到文本协议，内核其余部分不受影响。

---

## 8. 明确不做

1. **不再往提示词加字**。三轮实测证伪（3807→5272 字符，调用数恒为 0）。
2. **不为弱模型放宽证据语义**（裸 id 自动解析 revision）。测试台的缺陷不进产品。
3. **不跳过 T08 直接上 T06**。协议修好的第一天就会出现重复 claim。
4. **不在 S1 之前动 UI / 硬件 / Android**。契约要变，先变完再往上盖。
5. **不把"最后一个回答对不对"当连续性判据**。那是回声，不是记忆。

---

## 9. 需要 owner 拍的三件事

1. **T07 放宽指令不变量**——允许"同时调用能力并回复"。这是模型面对的输出契约变更。
2. **T08 写入去重**——`commit_ai_world_claim` 命中重复时返回 `duplicate: true` 而不新建 revision。这是认知写入语义变更。
3. **T04 定性**——并发 attach 的失败，是测试写窄了，还是 store 把可重试冲突映射成了不可重试错误。

三件都拍完，S1 可以一次做完；只拍第一件，S1 分两批（T05/T06 先上，T07/T08 随后）。
