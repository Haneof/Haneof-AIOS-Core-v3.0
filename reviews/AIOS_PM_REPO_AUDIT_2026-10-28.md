# AIOS v3.0 仓库复审核（PM，2026-10-28）

> 对象：`origin/main` = `7f686919`（PR #403 已于 2026-10-26 合并）。
> 前次：`reviews/AIOS_PM_REPO_AUDIT_2026-10-26.md`（已进 main，含被撤回的结论）。
> 本次未修改 `src/`；所有实测在 `origin/main` 的独立 worktree 里进行。

---

## 0. 一屏结论

**写入问题修好了，但代价是每轮慢 7–10 倍，而且开发平台已经跑不起来。**

| # | 发现 | 严重度 | 性质 |
|---|---|---|---|
| F1 | 写入率 0/6 → **6/6**，但单轮耗时 20.2s → **≈200s** | **P0** | 修复有效，成本失控 |
| F2 | 每次对话调用带 **53 个工具 / 34,736 字符（≈11.5k token）** | **P0** | 结构性开销，计划里的 T09 没做 |
| F3 | 抽取轮**每轮无条件执行**，中位 73.1s | **P0** | 计划里的 T4 没做 |
| F4 | `resilient_handler` 硬 `import fcntl` → **Windows 上 `pytest tests` 收集即死** | **P0** | 开发平台不可用 |
| F5 | 真实 NVIDIA key 硬编码在**公开仓库**，治理用 allowlist 放行 | **P0** | 凭证暴露，需 owner 决策 |
| F6 | T10 证据用 **n=1**、另一个模型，并把**已撤回的结论**当证明 | P1 | 证据纪律 |
| F7 | 撤回版审核**没进 main**；main 里仍是错误结论 | P1 | 认知污染 |
| F8 | 85 个开放 PR（37 个 DO NOT MERGE） | P2 | 治理债 |
| F9 | 本地全量测试 49 分钟仍未跑完（10-26 是 16m50s） | P2 | 可观测性 |

---

## 1. 前次审核的两处自我更正

| 前次说法 | 实际 |
|---|---|
| "没有 workflow 跑全量测试" | **错**。`c14-cognitive-derivation-loop.yml` 与 `p16-convergence-gate.yml` 都跑 `pytest -q`（全量）。问题是**只在 Linux 上有效** |
| "60 个开放 PR" | **错**。那是我 `--limit 60` 的截断值。实际 **85** 个 |

其余仍成立：manifest 换行符导致收集失败、并发 attach 不变量失败、能力面 53/28/7、CRLF 入库、README 只有一行标题。

---

## 2. F1（P0）写入修好了，慢了 7–10 倍

在 `origin/main` 上，同一句「我叫老王，在东莞做23cm柔性屏手环」，独立 world，n=6：

```text
R1 [224.1s]: extracted=2 calls_ok=0
R2 [138.0s]: extracted=1 calls_ok=0
R3 [123.4s]: extracted=2 calls_ok=0
R4 [148.7s]: extracted=2 calls_ok=0
R5 [132.1s]: extracted=1 calls_ok=0
R6 [330.2s]: extracted=3 calls_ok=0

=== durable after one memory-worthy turn: 6/6 | median latency 148.7s
```

对比 10-26 同一测法：**0/6**，中位 20.2s。

**写入这一项确实解决了。** 但看 `calls_ok=0`：6 轮里主对话路径**一次都没成功调用**写入能力，全部写入来自抽取轮。也就是说——

> 修好这个问题的是抽取轮（T2'），不是原生 tools（T05–T08）。

这与 main 里 T10 证据报告的结论相反（见 F6）。

### 2.1 耗时拆分（n=3，交替）

```text
R1: dialogue 140.8s | extraction 201.0s | facts=3
R2: dialogue 106.4s | extraction  73.1s | facts=2
R3: dialogue 127.9s | extraction  65.7s | facts=1

=== dialogue median 127.9s | extraction median 73.1s
```

对话轮本身从 20.2s 涨到 127.9s。两个原因都可量化，见 F2 / F3。

---

## 3. F2（P0）53 个工具，每次调用 34,736 字符

```text
tools 个数: 53
tools JSON 字符: 34736
粗估 token: 11578
```

`_build_native_tools(snapshot.capability_catalog)` 把**全部**能力翻译成 JSON Schema，逐轮随请求发送。对话轮带 34.7k 字符工具、抽取轮不带——这与观测到的 127.9s vs 73.1s 方向一致。

严格对照（同消息、只差 tools）本次没跑成：端点返回 503（请求过密）。所以**因果拆分未完成**，只报结构性事实：每次对话调用多出 34.7k 字符输入，这在 10-26 不存在。

这正是原方案里的 **T09 热集选择**，没做。

---

## 4. F3（P0）抽取轮每轮无条件执行

```python
if self.durable_fact_extractor is not None:
    response_now = runtime_result.response or ""
    if response_now.strip():          # ← 唯一的条件
        raw_facts = self.durable_fact_extractor(user_input, response_now)
```

只要回复非空就抽一次。**"今天天气一般" 也会抽。** 单轮固定 +1 次调用，中位 73.1s。

原方案里的 **T4 条件触发 / 延后执行**，没做。

设计上抽取轮本身是干净的：temperature 0.0、`<AIOS_SILENCE>` 表示无事实、evidence 由调用方绑定（模型无法伪造引用）、明确禁止从助手回复推断用户属性。**问题只在触发时机，不在抽取质量。**

---

## 5. F4（P0）`fcntl` 让开发平台失效

```text
tests/runtime/test_resilient_rate_limit_isolation.py:19: in <module>
    from aios_core.runtime import resilient_handler as rh
src/aios_core/runtime/resilient_handler.py:44: in <module>
    import fcntl
E   ModuleNotFoundError: No module named 'fcntl'
```

`resilient_handler.py` 用 `fcntl.flock` 做跨进程限速锁，无 Windows 回退（无 `msvcrt`、无 `os.name` 分支）。

后果：
1. Windows 上 `pytest tests` **收集即失败**，一条命令都跑不了；
2. 生产模型路径在开发平台上不可用；
3. 本地只能靠 CI（Linux）判断健康。

这是 10-26 之后新引入的回归。之前是 manifest 换行符挡路，现在是 `fcntl`。

---

## 6. F5（P0）公开仓库里的真实凭证

`src/aios_core/runtime/resilient_handler.py:70`（**本文不复制明文**，只给位置与形态）：

```python
PRIMARY_API_KEY = os.environ.get(
    "AIOS_PRIMARY_API_KEY",
    "nvapi-<64 字符真实密钥>",     # ← 默认值就是一把可用的 key
)
```

- 仓库是 **public**（`gh api repos/Haneof/Haneof-AIOS-Core-v3.0` → `private: false`）；
- 该 key 已进 git 历史（`b81635c6`），删掉代码也删不掉历史；
- 治理侧**知情并放行**：`governance/baseline.json` 的 `secret_allowlist` 有一条 `authorized_by: owner`、`authorized_at: 2026-10-26` 的显式例外，并把 `src/` 加进了 `secret_scan_paths`。

这是 owner 的明确决定，我不推翻。但要记录两条后果：

1. **任何拿到仓库的人都能用这个 key 花你的钱**。轮换前它一直有效。
2. **CI 现在依赖这个 key 存在**。一旦轮换，测试会失败——所以轮换要连同 `env` 注入一起改。

我**没有**用它调用 NVIDIA 接口验证是否仍有效——验证本身就是在用你的额度。

---

## 7. F6（P1）T10 证据的三个问题

`reviews/AIOS_T10_NATIVE_TOOLS_VERIFICATION_2026-10-27.md`：

| 问题 | 说明 |
|---|---|
| 样本量 | 三条硬指标（M1/M2/M3）各**一次运行**，无重复、无区间 |
| 模型 | `minimaxai/minimax-m3.1-flash`。我手上唯一可用的是 `grok-4.6`，同一份代码 **0/6 次** 工具调用 |
| 引用 | 报告开头把「同一提示词换成 tools 就写」当作"证明"，而该结论已于 10-27 撤回 |

报告的结论「抽取轮保留为兜底，不再承担主路径职责」在 grok-4.6 上是**反的**：抽取轮就是主路径，原生 tools 一次没触发。

这不是说 T10 造假——minimax 可能确实会调工具。问题是**结论被写成了普适的**，而它只在一个模型、一次运行上成立。

---

## 8. F7（P1）撤回没有进 main

- PR #403 在 `3484a9cf` 合并，main 里是**初版审核**（F1 = "协议是根因"）。
- 我的修正版在 `0327335b`，提交于合并之后，**没有新 PR**，所以只存在于分支。
- 结果：main 的断点续传锚上，挂着一条已被推翻的结论；而新代码的注释、T10 报告都在引用它。

按根原则第 12 条，认知翻案要向前修正——现在连"翻案"本身都没落地。

---

## 9. F8/F9 治理与可观测性

- **85 个开放 PR**，37 个标 `DO NOT MERGE`，最早可追到 9 月。
- README 仍是 23 字节一行标题。

### 9.1 本地全量测试跑不完，而且是卡住不是慢

排除 `fcntl` 那个文件后跑 **53 分钟未结束**；进程 472s CPU / 53min 墙钟 → 基本空闲，**是阻塞不是慢**。10-26 同一命令是 16m50s / 1,406 项。

按目录二分（每段 240s 上限）：

| 目录 | 结果 |
|---|---|
| `tests/c15_persistence` | 1.32s，**106 项全部跳过** |
| `tests/runtime` | 58.6s，400 通过 / 3 跳过 |
| `tests/habitation` | **超时**（17 项后卡住） |
| `tests/integration` | **超时**（34 项后卡住） |

`tests/habitation` 用 `-v` 定位到具体用例：

```text
tests/habitation/test_sol_manual_resident_replay.py::
  test_sol_manual_resident_replay_exposes_learned_custom_policies
```

150 秒无结果。该用例是一次 20 轮的真实 Core 复演，脚本化 handler，不联网。

两条结论：

1. **这是 10-26 之后引入的回归**——那两个目录当时是跑完的（16m50s 全量结束，只有 1 项失败）。
2. **`c15_persistence` 的 106 项全部跳过**。C15 的持久化证据在默认运行里根本没执行，而 C15 是 P16 的前置门。跳过原因需要单独查（缺 fixture 还是缺环境变量）。


---

## 10. 明确不做

1. 不改证据语义、不放宽内核校验。
2. 不为了跑通测试去改 `fcntl` 的**语义**（跨进程互斥必须保留），只补平台实现。
3. 不在延迟问题解决前谈 UI / 硬件。
4. 不用单次运行下模型行为结论——这条我犯过两次。
5. 不动 owner 授权的凭证例外，只报告后果并给出轮换路径。

---

## 11. 附：本次脚本

均在 `%TEMP%\aios_probe\`，未入库：

| 脚本 | 用途 | 状态 |
|---|---|---|
| `exp_main_write_rate.py` | main 上端到端写入率 + 延迟，n=6 | 完成：6/6，中位 148.7s |
| `exp_cost_split.py` | 对话轮 / 抽取轮耗时拆分，n=3 | 完成：127.9s / 73.1s |
| `exp_tools_payload_cost.py` | 工具负载对照 | **失败**：端点 503，因果拆分未完成 |
| `exp_extraction_discipline.py` | 抽取轮是否在闲聊上误写 | 未运行（端点 503） |
| `exp_dedup_e2e.py` | 去重是否被真正触发 | 未运行 |
