# T10 真实端点取证报告 — 原生 tools 协议端到端验证

- 日期：2026-10-27
- 模型：`minimaxai/minimax-m3.1-flash`
- 端点：`https://integrate.api.nvidia.com/v1`
- 基线：`1cad586`（T05 schema 转换 / T06 原生流 / T07 指令放宽 / T08 去重 / 接线）
- 判定：**PASS（三条硬指标全部通过）**

## 背景

PR #403 的审查用单变量对照证明：同一份提示词，只把「在散文里手写 JSON 块」换成原生 `tools` 数组，模型第 1 轮就调用 `commit_ai_world_claim`；此前文本协议三轮调用数恒为 0。

本取证在**不注入抽取轮兜底**（`durable_fact_extractor=None`）的条件下，验证原生 tools 主路径是否真正端到端工作。

## 三条硬指标实测

### M1 — 写入率（自我介绍落地 durable claim）→ PASS

第 1 轮用户输入「我叫老王，在东莞做23cm柔性屏智能手环，你以后对我别用敬语。」

- 工具调用历史：`commit_ai_world_claim` ×2、`record_ai_promise`、`propose_entity` ×2
- 落地 durable claim：`用户叫老王，在东莞做23cm柔性屏智能手环。`
- 核心事实（名字/地点/工作/偏好）全部被持久化，写入率达标

> 注意：与旧文本协议「三轮 claim=0」形成直接对照。模型不再被要求用没训练过的接口表达写动作。

### M2 — 关掉逐字对话仍答对 → PASS

`recent_turn_limit=0`（RECENT CONVERSATION 不注入），第 2 轮问「我叫什么名字？我在哪个城市？」

- 模型回答：**「你叫老王，在东莞，做 23cm 柔性屏智能手环。」**
- 这是唯一不可伪造的判据：它要么从 continuity anchor（durable claim）读到了，要么就是不知道。答案证明锚点路径真实生效。

### M3 — 连问两遍 claim 不增 → PASS

第 3 轮重复完全相同的自我介绍。

- 工具调用历史：**空**（模型在锚点里已看到该事实，未重复写）
- claim 数：第 1 轮后 = 1，第 3 轮后 = 1，**未翻倍**
- T08 内容级去重在真实端点下生效（模型主动不重写 + 程序化去重双保险）

## 与上一轮（抽取轮）的关系

| | 抽取轮（T2'，上一轮） | 原生 tools（本次） |
|---|---|---|
| claim 落地 | 事后独立 pass 抽取，claim=2/3 | 对话当下主路径写入，claim=1（覆盖全部核心事实） |
| 调用次数 | 主对话 + 额外一次抽取 pass | 一次模型调用，写+回复共存 |
| 符合训练分布 | 否（绕路） | 是（正解） |
| 角色 | 保留为**兜底**（模型漏写时触发） | 主路径 |

## 结论

原生 tools 协议（T05→T06→T07→T08→接线）在真实端点下端到端跑通，三条硬指标全部 PASS。上一轮的抽取轮保留为兜底，不再承担主路径职责。

## 附：验证脚本

`/tmp/test_native_tools_live.py`（临时，不入库）。核心构造：

```python
runtime = FusedTurnRuntime(
    store=store, index=index,
    model_handler=provider.as_model_handler(),  # 原生 tools 接线后
    subject_id="user_1",
    recent_turn_limit=0,  # M2 关逐字
)
```
