# FIX-PROMPT-CACHE-ORDER — 静态前缀连续化 + 缓存命中计量

## 状态

- 日期：2026-10-25
- 类别：成本 / 上下文工程（非正确性缺陷，属结构性浪费）
- 触发：PM 成本核算发现 61% 的输入 token 为同一份系统提示词的重复发送

## 背景

模型 API 无会话状态，每次调用都重发完整系统提示词。实测（`w_long2.sqlite`
`metering_records`，225 次调用，输入共 1,962,070 tokens）：

| 指标 | 数值 |
|---|---|
| 每轮首调输入（即系统提示词基准） | 均值 5,351 tokens，34 轮稳定不增长 |
| 工具续轮输入 | 均值 9,320 tokens |
| 系统提示词重复发送总量 | ≈1,203,975 tokens = **全部输入的 61%** |
| 其中逐字不变部分（规则+能力目录） | ≈945,000 tokens = 48% |

## 根因 1：段落排序击碎前缀缓存

OpenAI 兼容端点（NVIDIA NIM / SiliconFlow / DeepSeek）带自动前缀缓存：
请求前缀逐字节相同即命中，命中部分按约一折计价。原排序把**静态**的
能力目录（53 能力 ≈2,900 tokens，进程生命周期内不变）放在**动态**的
世界地图、最近对话之后——中间任何字节变化都使缓存失效，一块都省不到。

### 修复（`runtime/grok_provider.py`）

重排 `_handler` 的拼装顺序，静态内容形成连续前缀：

```
[静态，逐次调用字节相同]
  角色定义 → STANDING CONSTRAINTS → 语言规则 / 记忆纪律 /
  维度发现纪律 / 宪法规则 → AVAILABLE CAPABILITIES（能力目录上移至此）
[动态，每次调用可变]
  CONTINUITY ANCHOR → THIS TURN GROUNDING → WORLD MAP → COCKPIT
  → 已覆盖摘要 → RECENT CONVERSATION → 记忆卡 → 工具轮次提示
```

约束保持：CONSTITUTIONAL RULES 0 提到 "RECENT CONVERSATION block **below**"，
重排后对话标题仍在规则之后，语义不变。

### 回归测试

`tests/runtime/test_identity_continuity_prompt.py::
test_static_prefix_is_contiguous_and_byte_stable_across_calls`：

1. 两个输入完全不同的调用，`CONTINUITY ANCHOR` 之前的全部前缀逐字节相同；
2. 段落顺序 STANDING → CAPABILITIES → ANCHOR → RECENT CONVERSATION。

顺带修正了一处**既有的错误断言**：`test_standing_constraints_precede_dialogue…`
用 `index("RECENT CONVERSATION")` 定位对话标题，但宪法规则第 0 条
（"The RECENT CONVERSATION block below…"）也含该字样且位置更靠前，
断言一直在匹配错误的字符串。已改为匹配标题 `"RECENT CONVERSATION (verbatim"`。

## 根因 2：缓存命中量完全不可见

端点经 `usage.prompt_tokens_details.cached_tokens` 上报命中量，代码从不解析。

### 修复

- `runtime/cognitive_runtime.py`：`ModelUsage` 新增
  `cached_input_tokens: int | None`（None=上游未报告），纳入非负整数校验；
- `runtime/grok_provider.py`：解析 `prompt_tokens_details.cached_tokens`，
  上游未报告 usage 的 fallback 分支初始化为 0（避免 NameError），
  >0 时写入 `ModelUsage`。

## 真机验证（NVIDIA NIM / minimaxai/minimax-m3.1-flash）

同一 ~2,300 token 前缀连续两次调用：

| 调用 | prompt_tokens | cached_tokens | 命中率 |
|---|---|---|---|
| 第 1 次 | 3,786 | 128 | 3% |
| 第 2 次 | 3,786 | **3,712** | **98%** |

第二次调用经改造后的代码路径返回 `ModelUsage.cached_input_tokens=3712`。

## 预期收益

按 225 次调用 / 1.96M 输入 tokens 的实测模型：静态前缀 ≈4,200 tokens/次
（规则 ~1,300 + 能力目录 ~2,900）进入连续前缀后，假设命中（TTL 内）按一折计价，
**输入成本约降 35–40%**。同一会话内的工具续轮天然共享前缀，收益最直接。

## 影响面

- 提示词语义内容零改动，仅段落顺序调整；
- `ModelUsage` 新字段有默认值，向后兼容；
- 全量测试（`tests/`，除依赖 git 历史的 `c15_persistence`）通过。
