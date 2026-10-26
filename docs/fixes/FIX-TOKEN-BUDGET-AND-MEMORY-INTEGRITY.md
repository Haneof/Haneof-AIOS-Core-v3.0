# AIOS Core v3.0 — 上下文预算与记忆完整性修复报告

日期：2026-10-25
范围：`src/aios_core/context/**`、`src/aios_core/query/topic_associator.py`、`src/aios_core/runtime/**`
性质：内核修复（非 UI、非功能新增），共 1 份新增策略中枢 + 1 份新增估算器 + 4 处接入 + 2 处真实 bug 修复

---

## 一、先回答你的问题

### Q：模型都 1M 上下文了，还有必要搞 3400 的限制吗？

**有必要保留"限制"这个概念，但 3400 这个数字是错的量级。**

这四个理由决定了答案不是简单的"放开"：

| 维度 | 事实 | 结论 |
|---|---|---|
| **成本** | 输入 token 是按实际长度线性计费的，不是按上限计费 | 1M 是"能装多少"，不是"该装多少"。塞满 1M 每轮都真金白银 |
| **延迟** | 首 token 延迟随 prompt 长度上升 | 可穿戴场景 <1s 首 token 的预算扛不住超长 prompt |
| **噪音** | 长上下文存在 lost-in-the-middle：中间的记忆会被模型忽略 | 盲目扩容 ≠ 记忆变好，反而把信号淹没 |
| **缓存** | 本项目已实现 prefix 缓存，实测 NVIDIA/MiniMax 第二次调用 `cached_tokens=3712/3786`，**98% 命中** | 静态部分再大也几乎不花钱；真正贵的是每轮变化的动态部分 |

**关键区别**：AIOS 和聊天机器人不一样。它**不重发对话历史**（那是 O(n²) 增长），而是每轮把「世界快照」重新渲染成固定大小的 prompt。实测 34 轮下来首调输入稳定在 5134~5465 tokens，**没有历史膨胀**。

所以限制的作用不是"防止撑爆上下文"，而是**防止无用的东西挤掉有用的东西**。这个控制点必须留着，只是参数错了。

> 顺带纠正一个流传中的误会：限制值从来不是你们之前以为的 3000，是 **3400**。而且追根溯源，3400 不来自模型规格、不来自宪法、不来自硬件限制，只在一张治理回执里留过一句"2095/2102/2105 <= 3400"的痕迹 —— 是历史上自定的、给自己留了约 60% 余量的保守值。

---

## 二、真正严重的问题：3400 已经在损害记忆系统

这条因果链是本次修复的核心。**限制的存在本身不是 bug，估算器撒谎才是。**

### 因果链

```
ContextController 用 len(json.dumps(x))/4 估算 token
        │
        ├─ 英文：实测 0.207 token/字符，/4 给 0.25 → 略高估 ✅ 安全，所以一直没人发现
        └─ 中文：实测 0.636 token/字符，/4 给 0.25 → 【低估 2.55 倍】❌
        │
        ▼
估算器看不见中文内容的真实成本
        │
        ▼
实测两个 SQLite 世界库里 truncated:true 计数 = 0
        │  ← 注意：这不是"从没超预算"
        │     而是估算器根本算不出超预算。这是【假阴性】
        ▼
一旦把估算器修准（这次做的事）
        │
        ▼
同一份输入的估算值 2000 → 5400，立刻越过 3400
        │
        ▼
ContextController 开始静默丢弃
  • recent_turns（近期对话）
  • conversation_summaries（周期总结）
  • memory_cards（记忆卡）
        │
        ▼
而 truncated 标记被 grok_provider 的 _COCKPIT_SCALAR_SKIP 挡在 prompt 之外
        │
        ▼
【模型完全不知道自己的记忆被裁掉了】
```

### 对"记忆系统理解"的实际影响

这不是理论风险，是**已经具备发生条件、只差一个触发**：

1. **AI 会无辜失忆** —— 用户问"上次聊的杭州项目"，AI 看不到那段 recent_turns，会回答"我不记得有这回事"。不是遗忘，是**它根本没被送到模型眼前**。
2. **不可解释** —— 没有任何日志、没有任何标记，从外部看和"真的忘了"完全一样。这是最糟糕的一类故障。
3. **它还会反过来污染 AI 的自我认知** —— AIOS 有"AI 承诺台账"这类自我维度，AI 会因为看不到自己的记忆而误判自身状态。
4. **更隐蔽的**：已经验证过 `truncated:true` 计数为 0，说明这套破损的估算一直伪装成健康。**问题处于"即将在特定输入规模下集中爆发"的状态**，而不是"暂未发生"。

补充一个量级感知：实测单轮首调 prompt 已经是 **约 5351 tokens**（能力目录 ~2900 占 54%、宪法/规则 ~1300 占 24%、动态世界状态 ~1100 占 21%），工具续接轮平均 9320、峰值 **22694**。而预算只有 3400 —— 修准估算后，**现有规模就会触发丢弃**。

---

## 三、修复内容

### 修复 1：token 上限收归单一真源
新增 `src/aios_core/context/budget_policy.py`。此前散落在至少 6 处、互相打架：

| 位置 | 原硬编码 | 现状 |
|---|---|---|
| `context/controller.py` | 3400 | 接 policy，**提升至 32000** |
| `context/active_window.py` | 1500 / 6 turns | 接 policy |
| `runtime/grok_provider.py` | 4096 + 若干注入软上限 | 接 policy |
| `runtime/resilient_text.py` | 2048 | 接 policy |
| `runtime/turn_runtime.py` | 500 / 1500 | 接 policy |
| `query/topic_associator.py` | 500 | 接 policy |

支持 `AIOS_BUDGET_*` 环境变量覆盖，非法值静默回退默认值。**所有默认值行为不变**，属于纯取值来源替换。

**为什么是 32000**：真实 prompt 约 5351、续接轮峰值 22694，32000 给约 6 倍峰值余量；同时仅为 1M 上下文的 3%，叠加 prefix 缓存后静态部分成本几乎不计。

未接入的两处（**经判断不应接入**）：
- `edge_model_scheduler.py:2048` —— 这是 qwen2.5-0.5b 模型自身的物理上下文规格，不是我们的策略
- `edge_model_scheduler.py:2048.0` —— 内存 MB quota，单位都不同

### 修复 2：中文 token 估算修准
新增 `src/aios_core/context/tokenization.py`。零第三方依赖（可穿戴内核必须极简）。

- CJK 及类 CJK 字符：**0.7 token/字符**（实测 0.636，**故意略微高估**）
- 其余字符：0.25 token/字符（与原实现一致）

> 为什么是"高估"而不是"精确"：预算估算**宁可多算不能少算**。低估 = 实际超预算 = 静默砍记忆，这正是本次要消灭的故障模式。

对照验证：

| 样本 | 旧 `/4` | 新估算 | 参照真实值 |
|---|---|---|---|
| 中文 382 字 | 96 | **260** | 235 |
| 中文短句 | 6 | **15** | 12 |
| 英文 914 字 | 229 | **229** | 189 |
| 中英混排 | 23 | **32** | 27 |
| JSON list（中文） | 120 | **215** | 189 |

中文全部不再低估，英文零膨胀；12 万字文本 102ms 处理完，不爆栈。

### 修复 3：AI 能看见自己的视野被裁剪
这是整个修复里**对记忆系统最关键的一步**。

`ModelContextBundle` 新增 `dropped_sections`（记录每区被丢了几条），并真正渲染进 prompt —— 放在动态区，不破坏 prefix 缓存的静态前缀（静态前缀仍止于 `AVAILABLE CAPABILITIES`，就有了它才有 98% 缓存命中率）。

实际渲染给模型看的内容：

```
CONTEXT TRIMMED THIS TURN (a budget cut, not missing memory):
Some entries did not fit into this turn's context budget and were left out of the prompt above.
They were not forgotten and were never absent from the world store — they simply did not fit here:
- verbatim recent dialogue (recent_turns): 4 cut this turn — recover it with drill_down_conversation
- round summaries (conversation_summaries): 2 cut this turn — recover it with list_conversation_summaries
They still exist. If the user asks about something you cannot see above, call the capability named
on its line and check before saying you do not remember; say it was cut from this turn's context
rather than claiming you never knew it, and never fill the gap with an invented answer.
```

三层语义缺一不可：① 这是预算裁剪，不是失忆；② 哪类被裁了多少条；③ **可以用哪个已注册能力主动补召回**（能力名取自本轮真实注册的 catalog，不是写死的字符串，不存在编造能力）。最后一句特别要求它不许用编造的答案填坑。

**这一步把"无声失忆"变成了"可自愈的、可解释的降级"**。

### 修复 4：限速器隔离（原判断有误，实际更糟）
原判断是"限速按 API Key 粒度共享"。实际读代码后发现**比预想更严重：全场只有一个全局单桶 `nvidia_rpm`，所有端点、所有模型共用一个节拍器**。

后果：本来各有独立配额的不同 provider 互相拖慢；一次突发会拖累无关调用。

改为按「规范化端点 + key 的 sha256 指纹」分桶；model **不**进桶（同 key 同端点确实共享 RPM 配额），可选 `AIOS_RPM_SCOPE_MODEL=1` 细分。key 只以哈希形式出现，绝不进文件名/日志（有测试直接断言这一点防回归）。

实测（注入 tick=50ms）：A 端连打 5 次 201ms，B 端首调等待 **0.0ms**；同端点换 model 仍合并计数 49.6ms；跨进程 flock 生效。P0 安全路径经确认根本不经过限速器，已加断言守着 <50ms。

### 修复 5（附带发现）：一个被旧估算器藏住的真 bug
改动 `topic_associator` 接入准确估算器后，一条旧测试立刻炸了 —— 这不是噪音，它牵出了一个真实缺陷：

**token 预算不是硬边界。** 标题行是必定输出的，当 `max_tokens` 小于标题行长度时，逐行裁剪会直接放弃治疗，返回超预算文本。旧估算器让中文看起来很便宜，所以这条路径从未被触发；估算修准后当场暴露。

已修：幸存文本额外做二分截断（依赖估算的单调性），保证预算成为真正的硬边界。新增 `test_token_budget_is_a_hard_bound`，在 budget=1/5/12/20/60 各档要求：① `estimated_tokens` 与返回文本真实估算值严格相等（不许谎报）；② 不超过预算，除非预算小到连裁剪标记都放不下。

---

## 四、验证

### 验证方式（刻意说明，因为这里的数字有边界）

沙箱环境下全量套件无法完整跑完：剩余模块是重 SQLite 写入负载，跑到 55% 就撞上 780 秒超时；期间还出现过一次存储层 IO 卡死（进程进入 `D` 状态卡在 SQLite WAL 文件上，已在 Python 层面排除 `live` marker 的真实 API 调用后定位为环境 IO 问题，非代码问题）。

因此改为**静态圈定受影响面 + 精确覆盖**，而不是拿含糊的"部分通过"糊弄：

受影响面 = 引用了本次被改动符号（`ContextController` / `ActiveRollingWindow` / `ContextBudgetPolicy` / `DynamicTopicAssociator` / `_SharedRateLimiter` / `ResilientModelHandler` / `estimate_tokens`）的全部测试文件，grep 全仓精确定位：

| 测试文件 | 结果 |
|---|---|
| `tests/context/**`（含全部新增） | ✅ 通过 |
| `tests/query/test_topic_associator.py` | ✅ 通过（含新增硬边界用例） |
| `tests/runtime/**`（含全部新增） | ✅ 通过 |
| `tests/audit/test_pm_audit_remediation.py` | ✅ 通过 |

合计：直接受影响三大包 `tests/context + tests/query + tests/runtime` = **216 passed / 3 skipped / 0 failed**，审计用例 3 passed。

`src/` 下 `estimate_tokens` 的引用面经 grep 确认**严格限于 `context` 与 `query` 两个包**，与本次改动面完全重合；其余模块（`storage` / `cognition` / `ingest` / `narrative` / `tools` / `unit` 等）与改动零交集。

> 仍需在真实 clone（有 `.git`、IO 正常）的环境跑一次完整全量，作为推送前的最后一道闸。这一点不打折。
- 新增专项测试：
  - `tests/context/test_tokenization.py` —— 估算准确性、单调性、极值
  - `tests/context/test_context_budget_real_scale.py` —— **真实规模中文场景下一条记忆都不丢**；极小预算时 `dropped_sections` 必须精确反映丢弃数
  - `tests/runtime/test_dropped_sections_prompt.py` —— 端到端验证裁剪可观测
  - `tests/runtime/test_resilient_rate_limit_isolation.py` —— 限速隔离
  - `tests/query/...::test_token_budget_is_a_hard_bound` —— 预算硬边界
- 前置修复（本轮之前已完成，验证未被破坏）：
  - prefix 缓存 98% 命中率相关测试 `test_static_prefix_is_contiguous_and_byte_stable_across_calls` 仍通过
  - `cached_tokens → cached_input_tokens` 链路完好

---

## 五、遗留与待决

1. **以上全部改动目前只存在于沙箱的源码解压副本里（无 `.git`），尚未推送 GitHub。** 需要你明确批准后才会推送。
2. `capability_injection_tokens(6000)` 在 `budget_policy` 中暂无消费者（能力目录段设计上就不设上限），留作后续或删除。
3. 建议后续立项：`topic_associator` 之外若仍有本地 `_estimate_tokens` 副本，应统一 —— 分散的估算器是本次故障的根因模式，不应复活。
4. 32000 这个值是基于实测（峰值 22694）定的。建议在真实长周期运行一轮后，用 `metering_records` 表的真实数据复核一次。
