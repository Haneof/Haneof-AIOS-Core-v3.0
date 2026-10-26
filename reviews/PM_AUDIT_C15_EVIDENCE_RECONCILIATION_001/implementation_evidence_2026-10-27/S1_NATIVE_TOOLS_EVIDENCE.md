# S1 原生 tools 协议 — 逐项证据（实现方提交，待独立复核）

- 日期：2026-10-27
- 工程基线：`41f12c7`（main HEAD）
- 说明：`governance/baseline.json` 中 `pinned_sha` = `1cad586`，钉住的是 HEAD 的**父提交**
  （`41f12c7` 本身只含治理文档 + pin 推进，无代码）。二者不矛盾，复核时勿误判为漂移。
- 主张：**记忆闭环失效的根因是协议不匹配，不是模型能力不足，也不是提示词不够狠。**

## 0. 根因主张与其判定性对照

旧路径要求模型在散文回复里手写 JSON 块，再由 `_extract_capability_calls` 用正则从文本里抠出来。
这意味着模型必须"即兴发明"一个它没被训练过的输出接口。

新路径把能力目录翻译成 OpenAI 原生 `tools` 数组发给模型 —— 这是它被训练过的接口。

单变量对照（唯一变量 = 是否提供原生 `tools` 数组）：

| | 文本协议（旧） | 原生 tools（新） |
|---|---|---|
| 同一份提示词下第 1 轮工具调用 | 0 | `commit_ai_world_claim` ×2 等，非空 |
| 三轮累计 | 恒为 0 | 见 T10 M1 |

复现方式见 [`REPRODUCE.md`](REPRODUCE.md)。

---

## 1. T05 — `input_schema` 迷你语言 → JSON Schema

- **commit**：`9e6b4ec`（`+155` 源码 / `+243` 测试）
- **代码**：`src/aios_core/runtime/capabilities.py:202` `json_schema_for_arguments()`
- **测试**：`tests/runtime/test_json_schema_conversion.py`（8 项）
- **要点**：与 `required_arguments()`（`capabilities.py:51`）共用同一套解析，避免
  "必填参数" 与 "JSON Schema required" 两侧漂移。
- **规模**：`src/aios_core/runtime/turn_runtime.py` 中 `registry.register(` 出现 **53** 次，
  即默认目录 53 个能力全部经此转换。
- **验证**：
  ```
  python3.11 -m pytest tests/runtime/test_json_schema_conversion.py -q
  ```

## 2. T06 — 从 SSE 流里读出原生 tool calls

- **commit**：`0bd9a25`（`+267` 源码 / `+246` 测试）
- **代码**：`src/aios_core/runtime/grok_provider.py`
  - `:635` `NativeToolCall`
  - `:652` `TurnCompletion`
  - `:849` `stream_chat_with_tools()`
- **要点**：tool_calls 按 `index` **拼接**而非覆盖；`arguments` 分片跨 delta 累积。
  这是纯新增方法，未改动既有 `stream_chat` 签名。
- **验证**：
  ```
  python3.11 -m pytest tests/runtime/test_native_tools_stream.py -q
  ```

## 3. T07 — 放宽 `ModelDirective` 不变量

- **commit**：`1cad586`
- **代码**：`src/aios_core/runtime/cognitive_runtime.py`
  - `:80` `ModelDirective`，`:89` `__post_init__`（放宽）
  - `:448` `needs_continuation` 判定，`:454` 末轮 fail-closed，`:527` 共存终止点
- **为什么必须做**：原不变量是"不能同时请求能力并返回答案"。它**零测试覆盖**，
  是随手加的门，却直接堵死原生 tools —— 因为模型最常见的行为恰恰是"边答边写"。
- **放宽后的规则**：
  | 情形 | 行为 |
  |---|---|
  | 全为写能力 + 有回复 | 执行后终止（`responded`） |
  | 含读能力 | 执行后回灌，再叫一轮 |
  | 末轮仍有待办 | fail-closed（`model_round_budget_exhausted`） |
  | silence | 仍与 response / calls 互斥（这条没放宽） |
- **测试**：`tests/runtime/test_model_directive_coexistence.py`（8 项，新增）
- **验证**：
  ```
  python3.11 -m pytest tests/runtime/test_model_directive_coexistence.py -q
  ```

## 4. T08 — 写入内容级去重

- **commit**：`1cad586`
- **代码**：`src/aios_core/runtime/turn_runtime.py`
  - `:206` `_normalize_statement()`（大小写 / 空格 / 标点折叠，保留 CJK 与字母数字）
  - `:3427`–`:3465` `_commit_ai_world_claim` 内的去重分支，命中时返回
    `claim=None, duplicate=True, matched_object_id=...`
- **为什么需要**：模型侧"看到锚点就不重写"是概率性的；程序化去重是确定性的第二道闸。
- **测试**：`tests/runtime/test_claim_deduplication.py`（5 项，新增）
- **验证**：
  ```
  python3.11 -m pytest tests/runtime/test_claim_deduplication.py -q
  ```

## 5. 接线 — `as_model_handler` 走原生 tools

- **commit**：`1cad586`（`grok_provider.py` `+96`）
- **代码**：`src/aios_core/runtime/grok_provider.py`
  - `:42` `_build_native_tools()` —— 用 T05 转换器把目录翻成 `tools` 数组
  - `:1183` `as_model_handler()`
  - `:1432` 有 tools 时改走 `stream_chat_with_tools`
- **降级链**：原生 tool_calls 为空且仍有轮次预算时，回落到文本协议抽取
  （`_extract_capability_calls`）。**原生为主，文本为兜底。**
- **受影响的既有测试**：5 个 prompt 类测试文件的 fake provider 需补
  `stream_chat_with_tools` stub（`test_durable_fact_extraction.py`、
  `test_identity_continuity_prompt.py`、`test_prompt_cockpit_coverage.py`、
  `test_dropped_sections_prompt.py`、`test_capability_prompt_contract.py`）。
  ⚠️ stub 必须返回 `usage=None, provenance=None`，否则会触发 metering replay 冲突。

## 6. T10 — 真实端点取证

- **commit**：`41f12c7`；报告：`reviews/AIOS_T10_NATIVE_TOOLS_VERIFICATION_2026-10-27.md`
- **模型 / 端点**：`minimaxai/minimax-m3.1-flash` @ `https://integrate.api.nvidia.com/v1`
- **关键构造**：`FusedTurnRuntime(..., model_handler=provider.as_model_handler(),
  recent_turn_limit=0)`，**不注入** `durable_fact_extractor` —— 验证主路径，不是兜底。

| 指标 | 判据 | 实测 | 结论 |
|---|---|---|---|
| M1 写入率 | 自我介绍落地 durable claim | 第 1 轮调用 `commit_ai_world_claim`×2 + `record_ai_promise` + `propose_entity`×2；落地「用户叫老王，在东莞做23cm柔性屏智能手环。」 | PASS |
| M2 关逐字仍答对 | `recent_turn_limit=0` 下答对 | 答「你叫老王，在东莞，做 23cm 柔性屏智能手环。」 | PASS |
| M3 连问两遍不增 | 重复输入后 claim 不翻倍 | 第 3 轮工具调用为空；1 → 1 | PASS |

> **M2 是唯一不可伪造的判据**：逐字对话被完全关掉，模型要么从 continuity anchor 读到，
> 要么答不上来。它答对了，说明锚点路径真实生效。

- **脚本**：[`verify_native_tools_live.py`](verify_native_tools_live.py)
- ⚠️ **给 Reviewer 的诚实提示**：脚本里 M3 的判据是 `len(claims_3) <= len(claims_1) + 1`
  （带 +1 容差），比"严格不增"宽松。本次实测是 **1 → 1**，落在最严格区间内，
  所以 PASS 成立；但判据本身偏松，若你要用"严格不增"作为门槛，需收紧该行。

## 7. 回归与门禁

- **`tests/runtime/` 全量**：`410 passed, 3 skipped`
  ```
  python3.11 -m pytest tests/runtime -q
  ```
- **安全门**：`PASS`（`nvapi-` 识别 / `src/` 扫描 / 逐提交逐路径授权 / allowlist 例外）
  ```
  python3.11 tools/check_baseline.py
  ```

## 8. 提交链

```
9e6b4ec  T05  参数迷你语言 → JSON Schema
0bd9a25  T06  从 SSE 流读原生 tool calls（纯新增）
1cad586  T07 + T08 + 接线，含 13 项新测试
41f12c7  T10 取证报告 + 基线 pin 推进
```
