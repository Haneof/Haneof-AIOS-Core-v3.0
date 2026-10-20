# P16 召回基准工具

## 这个工具证明什么

AIOS 3.0 的完成标准要求：

> 换掉底层大模型之后，世界、经验和关系仍然继续存在。

`tools/p16_recall_bench.py` 把这条要求变成**可复现、可审计**的自动化评测。每个 session 的流程：

1. 向全新世界库写入一条 anchor 事实（含「杭州」「23cm 柔性屏手环」等关键词）。
2. 用**模型 A** 让模型记住该事实。
3. 用**模型 A** 追问「我刚才让你记住的那句话里，我在哪个城市、做什么产品？」
4. 把运行时底层模型换成**模型 B**，再问同样的问题。
5. 判定回复中是否出现任一关键词（杭州 / 手环 / 柔性屏 / 23cm）。

如果 T2（同模型）和 T3（换模型）都能命中，说明记忆不依赖某个特定模型；如果 T3 失败，说明「记住」其实是该模型在替系统兜住。

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

缺少必需环境变量时工具会**优雅退出**（返回码 2），不会抛栈或消耗额度。

### 输出

- **控制台**：每个 session 的逐轮结果 + 总召回率。
- **JSON 证据文件**（默认 `p16-recall-evidence.json`）：
  - `base_url`：端点地址（不含 key）
  - `model_a` / `model_b`
  - `anchor_fact` / `recall_question`
  - 每轮明细：模型、耗时、model_rounds、回复文本、是否命中、异常信息
  - `summary.recall_rate` 与 `verdict`（PASS 需召回率 100%）

## 如何解读结果

| 场景 | 含义 |
|---|---|
| T2 ✅ T3 ✅ | 系统本身可靠地记住了事实，换模型无影响。 |
| T2 ✅ T3 ❌ | 记忆依赖模型 A 的「聪明」，模型 B 兜不住——这是系统缺陷。 |
| T2 ❌ T3 ❌ | 记忆写入或召回链路有根本问题，需先修 bug。 |
| 任何一轮 💥 | 网络或配置问题，检查 base_url/key/额度。 |

## 已知限制

1. **单厂商**：当前默认只测 Gemini 的两个模型。项目标准要求「不依赖特定厂商」，因此这只是**部分证据**。拿到第二家厂商 key 后，把 `--model-b` 换成另一家即可补全。
2. **免费额度**：Gemini 免费 tier 有 RPM/IP 限制，大规模评测前建议确认额度或换付费 key。
3. **思考模型延迟**：Gemini 3 系列是思考模型，单轮延迟 5–15 秒属正常；`--timeout` 默认 60 秒，若频繁超时请加大。
4. **召回判定是关键词匹配**：不是语义等价判定。若模型说「浙江省会」而不说「杭州」，会被记为未命中——这是保守策略，漏报优于误报。
5. **session 间无状态共享**：每个 session 独立建库，测的是「单 session 内换模型」而非「跨 session 长期入住」。后者需要更长周期的 habitation 测试。

## 与门禁测试的区别

- **门禁测试**（`tests/runtime/test_live_multimodel_habitation.py`）：hermetic，无网络，验证代码层面的协议解析和字段传递。
- **召回基准**（本工具）：live，需要真实模型，验证**端到端**的写入-索引-召回-提示词渲染全链路。

两者互补：门禁保证代码不变坏，基准保证系统在真实模型上确实能做到它承诺的事。
