# AIOS v3.0 仓库审核（PM，2026-10-26 初版 / 2026-10-27 复测修正）

> 审核对象：`Haneof-AIOS-Core-v3.0`，分支 `feat/local-live-model`（= `origin/main` + 9 提交，PR #403）。
> 配套方案：`governance/PM_DEVELOPMENT_PLAN_2026-10-26.md`。
> **本文含一次自我更正。** 初版的核心结论（"协议是根因"）在复测中被推翻，见第 1、2 节。

---

## 0. 一屏结论

| # | 发现 | 严重度 | 复测状态 |
|---|---|---|---|
| F1 | **写入行为不可控**：同一场含 durable 事实的对话，写入率在 0%–65% 之间随传输参数漂移，没有任何我们控制的因素能稳定决定它 | **P0** | 初版结论**已推翻**，此处为修正版 |
| F2 | 真实产品面（`aios-core-headless turn`）一轮对话后**零认知写入** | **P0** | 复现成立（2 次） |
| F3 | 全量测试在 Windows 上**收集即失败**；无统一检查入口；一项并发不变量**稳定失败** | P1 | 三项均复现成立 |
| F4 | 认知写入**无内容级去重** | P1 | 代码成立；行为待写入率提高后暴露 |
| F5 | 53 个能力、28 个写路径，只有 7 个带参数签名 | P2 | 复算一致 |
| F6 | 治理记录与工程现实脱节 | P2 | 部分修正（grok-4.7 现已可用） |
| F7 | 仓库卫生：CRLF 入库、README 只有一行标题、60 个开放 PR | P2 | 复测成立，README 一处数字修正 |

一句话：**不是模型不肯写，也不是协议写错了——是"写不写"这件事根本没有被确定性地控制住。**

---

## 1. 复测记录（先说方法，再说结论）

初版在单样本上下了结论。复测按以下口径重做，所有数字都可重跑。

### 1.1 初版说错了什么

初版的核心证据是一次单样本对照：同一份 5272 字符提示词，加 `tools` 数组后模型第 1 轮就调用了写入能力（1 次），而换接口之前三轮都是 0 次。据此我写下"协议是根因"。

复测用同样脚本再跑一次：**0 次调用**。同一份提示词、同一组工具、同一个模型。

于是做了 n=6 的 A/B（交替执行、提示词固定）：

| 臂 | 接口 | 调用率 |
|---|---|---|
| N | 原生 `tools`（7 个写能力） | **3/6** |
| T | 文本协议（走内核自己的 `_extract_capability_call`） | **4/6** |

**文本协议不差，甚至略高。差异在 n=6 下是噪声。初版结论不成立，作废。**

### 1.2 那么真实路径为什么是 0

| 路径 | n | 结果 |
|---|---|---|
| 真实 provider 路径（流式、temp 0.6），单轮，只到 handler 层 | 6 | **2/6** 带调用 |
| 真实 provider 路径，单轮，跑到落库（`run_turn`） | 6 | **0/6** 有 durable claim |
| 真实 provider 路径，7 轮对话 | 7 轮 | **0/7** 轮有调用 |

把历次"含 durable 事实的首轮"观测合起来：约 **2/19 ≈ 10%**。

同一件事，换个传输参数就能从 0/6 变成 3/6。**这说明写入与否不由我们控制，而由采样决定。** 这比"某个接口写错了"严重得多：接口错可以改，不可控只能靠结构性约束。

### 1.3 复测中被证伪的其它说法

| 初版说法 | 复测结果 |
|---|---|
| grok-4.7 稳定 502，"已验证"不可复现 | **不成立**：4.7 现在返回 200。当时确实 502，但那是端点状态，不是结论 |
| README 是 0 字节 | **不成立**：23 字节，内容是一行标题 `# Haneof-AIOS-Core-v3.0`，没有换行、没有使用说明 |
| 协议是根因 | **不成立**，见 1.1 |

### 1.4 仍然成立的（逐条复核过）

| 项 | 复核方式 | 结果 |
|---|---|---|
| 真实 CLI 回合零 claim | 重跑一轮真实对话并直接读库 | 成立：`observation×2 + communication_experience + dependency`，claim 0 |
| manifest 换行符导致收集失败 | 反向验证：LF → 5 项收集成功；转 CRLF → 复现同一条哈希错误 `07d168d0...`；还原 → 恢复 | 成立，机制确认 |
| 并发 attach 不变量失败 | 再跑，同一条断言 + `attempt to write a readonly database` | 成立 |
| 能力面 53 / 28 / 7 | 重算 | 一致 |
| 两个测试文件 CRLF 入库 | blob 内 CR 计数：302 / 389；假改动 691 行 | 成立 |

---

## 2. F1（P0）写入行为不可控

### 2.1 现象

同一句"我叫老王，在东莞做23cm柔性屏手环，跟我说话别用敬语"，同一份提示词，同一模型：

- 有时写成一条 claim；
- 有时一个字不写，只回一句"老王，收到"；
- 换个传输参数，比例从 0/6 变到 4/6。

### 2.2 为什么提示词改不动它

提示词里 `DURABLE MEMORY DISCIPLINE` 那段写的是**陈述后果**：

> Anything that stays true beyond this conversation … survives only if you persist it with `commit_ai_world_claim`

这是"告诉你后果"，不是"要求你动作"。前沿模型读完会理解，然后继续回答用户——回答用户是它的默认行为，且收益立刻可见；写入的收益在下一场会话才兑现，本轮看不见。**默认行为永远赢。**

三轮提示词工程（3807 → 4859 → 5272 字符）加的都是"更好的解释"和"更全的参数名"，没有一次把写入变成**必须做出的决定**。所以调用数一直在 0 到 1 之间随机。

### 2.3 为什么换接口也不是解

原生 `tools` 3/6，文本协议 4/6。接口不改变"要不要写"，只改变"写的时候格式对不对"——后者仍然重要（见 2.4），但它是第二个问题。

### 2.4 写对了格式也会被拒

handler 层 2/6 的那两次调用，参数是：

```python
commit_ai_world_claim({'domain': 'user_understanding', 'statement': '...'})
```

`evidence_refs` 和 `confidence` 都没有。内核 schema 里这两个是必填 → `CAPABILITY_ARGUMENT_ERROR` → 不落库。

所以端到端是两级衰减：**约 1/5 的轮次会尝试写，尝试写的里面又有一部分因为缺必填参数被拒。** 0/6 是这个链条的自然结果。

### 2.5 诊断

| 层级 | 问题 | 修法 |
|---|---|---|
| 触发 | 写入是"建议"，不是"必须做的决定" | 结构性要求，不是措辞 |
| 格式 | 必填参数缺失 | 原生 `tools` 的 `required` 由模型侧遵守，比散文里的样例可靠 |
| 兜底 | 一次没写 = 永久丢失，没有第二次机会 | 本轮有 durable 内容却零写入时，必须可观测（现在完全静默） |

---

## 3. F2（P0）真实产品面零认知写入

```text
$ aios-core-headless --world w.sqlite \
    --model-handler aios_core.runtime.live_handler:handler \
    turn --session s1 --turn-index 1 \
    --text "我叫老王，在东莞做23cm柔性屏手环，跟我说话别用敬语。"

{"response": "老王，在东莞做23cm柔性屏手环是吧？…", "model_rounds": 1, "world_revision": 2}
```

世界库（两次独立复现，对象类型完全一致）：

```text
object_revisions:  observation × 2, communication_experience × 1, dependency × 1
claim 类对象:       0
```

回答正确，认知为空。第二场会话的身份锚是空的。

CLI 自己的警告也指向同一个洞：

> 未提供 `--round-summary-handler` / `--dimension-summary-handler`，分层记忆将不会产生任何 SUMMARY。`recent_turns` 滑出窗口后，模型既看不到原始对话、也没有总结可读，长会话连续性会断档。

即使 F1 修好，不接 summary handler，长会话仍会断档。这是配置项，不是"轻量运行可忽略"。

---

## 4. F3（P1）仓库健康无法判断

### 4.1 全量测试在 Windows 上收集即失败（反向验证过）

```text
ERROR tests/c15_persistence/killpoints/test_killpoints.py
AssertionError: frozen probe manifest was modified after freezing;
  expected a3c2a7c9..., got 07d168d0...
```

不是篡改。该测试对 `PROBE_MANIFEST.json` 的**原始字节**取 sha256；工作区文件被 CRLF 重写（6060 vs 5902 字节），哈希自然不同；`.gitattributes` 的 `eol=lf` 让 git 比对时自动归一，**`git status` 看不见这个差异**。

反向验证（本次实做）：

| 步骤 | 结果 |
|---|---|
| LF（正常检出） | 5 项收集成功 |
| 转成 CRLF | 复现同一条错误，哈希 `07d168d0...` |
| 还原 | 恢复收集，`git status` 干净 |

它一失败就**中断整个收集**，于是"跑全量测试"这条命令在 Windows 上等于不存在。

### 4.2 没有统一检查入口

55 个 workflow 各跑子集，仓库里没有 `Makefile` / `tox.ini` / `noxfile.py` / `scripts/`。PR #403 现在 34 项全绿，而 `pytest tests` 跑不起来。

### 4.3 修好收集之后：1285 通过 / 1 失败 / 120 跳过 / 16m50s

失败项 `test_ca2_015_concurrent_attach_yields_one_canonical_winner` **复现（多次，非 flake）**：

```text
sqlite3.OperationalError: attempt to write a readonly database
  -> StoreError("SQLite storage operation failed")
assert sorted(outcomes) == ["accepted", "refused"]
E  AssertionError: assert ['accepted'] == ['accepted', 'refused']
```

两个线程同时 attach 同一个 late return，其中一个在 `_connection()` 里炸掉，异常逃出 worker（测试只捕获 `BackgroundModelResponseConflict`），于是只有一个 outcome。

这正是 C15 的持久化不变量："一个 canonical winner，另一个必须被明确拒绝"。现在既没拒绝，也没报错，直接消失。而且失败时**线程可能挂住**（本次复跑一次耗时数分钟）。

定性需要 owner：测试写窄了，还是 store 把可重试的并发写映射成了不可重试错误。

### 4.4 120 项跳过

主要是 `AIOS_LIVE_PROVIDER=1` 才跑的 opt-in live 测试。合理，但意味着 **CI 里没有任何一项碰过真实模型**——所有"已验证"的 live 声明都只在某台机器上成立过。

---

## 5. F4（P1）写入无去重

`_commit_ai_world_claim` 与 `ai_world.commit` 都没有内容级去重。

实测：原生工具实验中，第 4 轮（用户问"还记得我吗"）把前两轮的四条事实**原样重写**（4 次调用）。

**条件性**：这个洞只在模型真的写的时候暴露。按 F1 的现状，它还不是主要矛盾；但写入率一旦提上来，它会立刻变成主要矛盾（世界被重复 claim 填满，revision 链被"每次问到都再写一遍"搞脏）。所以它必须和"提高写入率"同一批上线。

---

## 6. F5（P2）能力面与提示词不匹配

| 项 | 数 |
|---|---|
| 能力总数 | 53 |
| 写路径（`side_effecting`） | 28 |
| 带 `input_schema` | 48 |
| 带 `required_args`（渲染出参数名） | **7** |
| 能力段落渲染字符 | 2168 |

模型看得到 53 个名字，28 个是写操作，其中 21 个不知道参数叫什么。

这也是 F1 第二级衰减的成因之一：7 个写能力里有签名，模型仍会漏必填项（2.4 实测漏了 `evidence_refs`、`confidence`）。

---

## 7. F6（P2）治理记录与工程现实脱节

| 记录 | 声称 | 现实 |
|---|---|---|
| `AIOS_SINGLE_WINDOW_TASK_BOARD.md` CURRENT PM CONTROL | 唯一当前任务 = `PM-AUDIT-C15-EVIDENCE-RECONCILIATION-001 READY_FOR_ASSIGNMENT`；Window81 起 = HOLD | P16-MEMORY-DIRECTIVE-001 / P16-IDENTITY-CONTINUITY-001 已并入 `origin/main`（#401） |
| `AIOS_v3.0_CURRENT_CHECKPOINT.md` | 最新条目 2026-10-20 | 之后 9 个提交未记入 |
| `C15_R6_..._RECEIPT_2026-10-20.md` | "Live HTTP 200 SSE streaming chat against Grok-4.7"，4/4 PASS | **端点侧已可复现**（4.7 现返回 200），但该测试是 opt-in，CI 里永远跳过 → "已验证"仍没有自动化的复现路径 |
| GitHub | 60 个开放 PR | 32 个标 `DO NOT MERGE`；#340–#347 是同一件事的 8 个连续 PR |

处理原则按根原则第 12 条：**向前修正，不删除过去**。

---

## 8. F7（P2）仓库卫生

- `tests/unit/test_m1_001r_adv_independent_redteam.py`、`tests/unit/test_m1_001r_high_entropy_audio.py` 以 **CRLF 入库**（blob 内 CR：302 / 389），与 `.gitattributes` 的 `* text=auto eol=lf` 冲突 → `git status` 永久显示 691 行假改动。
- `README.md` 23 字节，只有一行标题，没有安装、没有一条能跑起来的命令。
- 无统一检查入口（见 4.2）。

---

## 9. 方法教训（这次真正值钱的东西）

1. **n=1 不是证据。** 初版用一个样本下了根因结论，复测直接推翻。凡涉及模型行为，n≥6，且必须交替执行以抵消漂移。
2. **对照实验只能改一个变量。** 初版"手写极简提示词 vs AIOS 提示词"同时改了提示词和接口，两个变量混在一起，结论不可用。
3. **判据要落在端到端。** handler 层 2/6 和端到端 0/6 是两个不同的事实。只有"世界库里有没有 claim"才是产品事实。
4. **不确定的时候，说区间不说点。** "写入率约 10%（2/19），不同传输设置下观测到 0%–65%"比"模型不写"诚实得多，也有用得多。

---

## 10. 明确不做

1. **不再往提示词加字**。三轮实测证伪。
2. **不为弱模型放宽证据语义**（裸 id 自动解析 revision）。测试台的缺陷不进产品。
3. **不在 F1 修好之前动 UI / 硬件 / Android 适配**。
4. **不用"最后一个回答对不对"判断连续性**。模型自己吐的 JSON 留在最近几轮里会被读到——那是回声，不是记忆。判据只能是 `recent_turn_limit=0` 下的跨会话复述，和世界库里的 durable 计数。
5. **不用单次运行下任何关于模型行为的结论。**

---

## 11. 附：本次审核的脚本

均在仓库外（`%TEMP%\aios_probe\`），未入库：

| 脚本 | 用途 |
|---|---|
| `exp_ab_protocol.py` | A/B：原生 tools vs 文本协议，n=6 交替 |
| `exp_runtime_path.py` | 真实传输层、单轮、handler 层调用率 |
| `exp_durable_rate.py` | **端到端写入率**（跑到 `run_turn` + 读库），n=6 |
| `exp_native_tools.py` / `exp_same_prompt_tools.py` | 初版的单样本实验，结论已作废，保留作对照 |

建议把 `exp_durable_rate.py` 的逻辑固化进 `tools/`（方案 T00），让"写入率"变成一条可重复的命令——初版之所以判错，就是因为没有这个命令。
