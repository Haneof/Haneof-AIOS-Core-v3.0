# 本地模型接入（llama.cpp / Ollama / vLLM）

这份文档回答一个问题：**怎么让 AIOS 跑在你自己机器上的模型上**，以及接上之后立刻会暴露什么。

## 一、为什么需要一层适配器

内核不肯把「用哪个模型」写死：headless 进程只接受 `--model-handler module:attribute`，加载一个 `RuntimeSnapshot -> ModelDirective` 的可调用对象。这是对的——provider 不该变成宪法的一部分——但代价是每次接一个真实端点，都得先写一个模块。

`aios_core.runtime.live_handler` 就是那个模块。

## 二、一条命令

以 llama.cpp 的 `llama-server` 为例（本机实测配置）：

```bash
llama-server.exe -m Qwen3.8-27B-...gguf -ngl 28 -c 20480 \
    -ctk q8_0 -ctv q8_0 -fa on -t 12 --parallel 1 \
    -b 4096 -ub 2048 --host 127.0.0.1 --port 8081 \
    --alias qwen3.8-27b-coder390-q3lynnstyle16g-mtp --reasoning-budget 0
```

然后：

```bash
export AIOS_LIVE_BASE_URL=http://127.0.0.1:8081/v1
export AIOS_LIVE_MODEL=qwen3.8-27b-coder390-q3lynnstyle16g-mtp

aios-core-headless \
    --world ./world.sqlite \
    --model-handler aios_core.runtime.live_handler:handler \
    turn --session s1 --turn-index 1 \
    --text "我叫老王，在东莞做23cm柔性屏手环，跟我说话别用敬语。"
```

Ollama 用 `http://127.0.0.1:11434/v1`，vLLM / LM Studio 同理——只要说 OpenAI 的 chat-completions 方言、支持 SSE 流式即可。

### 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `AIOS_LIVE_BASE_URL` | `http://127.0.0.1:8080/v1` | 端点，需含 `/v1` |
| `AIOS_LIVE_MODEL` | `grok-4.7` | 模型名，取端点 `/v1/models` 里的 id |
| `AIOS_LIVE_API_KEY` | 空 | 回环地址可留空；远程地址留空会直接拒绝 |
| `AIOS_LIVE_TIMEOUT_SECONDS` | `300` | 本地小模型很慢，60 秒不够 |
| `AIOS_LIVE_MAX_OUTPUT_TOKENS` | `4096` | 见下面第三节的坑 |
| `AIOS_LIVE_TEMPERATURE` | `0.6` | |

**回环可以不带 key，远程不行。** `llama-server` 和 Ollama 不校验凭据，所以 `127.0.0.1` / `localhost` / `[::1]` 允许空 key（内部填一个占位符）。对远程端点空 key 会抛错——宁可失败，也不发一个无凭据的请求出去等对方裁决。

## 三、接上之后立刻暴露的三件事

这三条都是本机实测出来的，不是推演。

### 1. 模型想写认知，但不知道参数叫什么

给一句「记住我是谁」，模型的反应是对的——它立刻尝试调用 `commit_ai_world_claim`。但它写的是：

```json
{"domain": "user_understanding", "claim": "老王，东莞做23cm柔性屏手环",
 "tags": ["core_context"], "evidence": "obs_conv_user_..."}
```

内核要的是 `statement` / `evidence_refs`（对象数组）/ `confidence`。于是调用被拒，claim 数为 0，身份锚是空的，整场对话没有任何东西活下来。

原因是提示词里只列了能力名，没有参数名——**能力目录里明明有 `input_schema`，渲染时被丢掉了**。

修法两步，第二步是被实测逼出来的：

1. `_cockpit_capability_catalog` 为「写入路径」上的七个能力带上必填参数，`_render_capabilities` 把它们渲染成一行签名。其余能力只列名字，不占预算。
2. **再给一个完整的调用样例。** 只写签名时，同一个模型连续四轮仍然用 `claim` / `evidence`——它读到了 `statement`，但没照着用。把形状本身摆出来之后才开始写对。对小模型来说，一个例子比一段 schema 有效。

签名 + 样例合计约 2,200 字符，比修之前（只列 10 个名字）多，但这是唯一让"写认知"这件事真正发生的东西。

### 2. 调用失败时不告诉模型为什么失败

第一版反馈只有：

```
Result of commit_ai_world_claim: ok=False, data=null
```

模型连试三轮，每轮都用同一个错参数——因为它只知道"失败了"，不知道"错在哪"。

修法两处：`_render_capability_result` 带上 `error_code` / `error_message`；`CapabilityRegistry.invoke` 在参数不匹配时，把**必填参数名、可选参数名、被拒绝的键名**一起写进错误信息。

### 3. 输出预算不足会把能力调用降级成聊天

`max_output_tokens` 太小（实测 100）时，模型的 JSON 会被截断，`json.loads` 失败，于是这段 JSON 被当成**普通回复**发给用户，同时永久留在对话历史里。表现是：用户看到一段裸 JSON，而系统什么都没写。

这是产品侧的脆弱点，不是模型问题：**输出预算必须容纳一次完整的能力调用**（`commit_ai_world_claim` 大约需要 150–250 token）。本地调试时尤其容易踩，因为为了等得及会下意识把预算压小。

## 四、复跑取证

`tools/live_continuity_probe.py` 用真实端点跑一段真实对话，报三件事：模型看到了什么、模型决定了什么、什么真的落库了。

```bash
python tools/live_continuity_probe.py \
    --base-url http://127.0.0.1:8081/v1 \
    --model qwen3.8-27b-coder390-q3lynnstyle16g-mtp \
    --recent-turn-limit 2 --max-output-tokens 320 \
    --expect "老王,东莞,23cm"
```

关键判据不是「最后一个回答对不对」，而是 `what became durable` 里的计数。回答对可能是运气——比如模型自己吐出来的 JSON 文本恰好留在了最近几轮里，被下一轮读到了，那不是记忆，是回声。

## 五、本机实测吞吐（Qwen3.8-27B Q3，-ngl 28）

| 指标 | 实测 |
|---|---|
| 预填充 | ~118 tok/s |
| 生成 | ~1.6 tok/s |
| 单轮耗时（回复 100–300 token） | 40–90 秒 |

这个速度不足以支撑手环上的实时对话。接本地模型适合做**取证和回归**，不适合当产品默认端点——除非换更小的量化或更多层卸载到 GPU。
