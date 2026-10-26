# AIOS v3.0 仓库审核（PM，2026-10-26）

> 审核对象：`Haneof-AIOS-Core-v3.0`，分支 `feat/local-live-model`（= `origin/main` + 8 提交，PR #403）。
> 配套方案：`governance/PM_DEVELOPMENT_PLAN_2026-10-26.md`。
> 本次审核**没有修改任何 `src/` 代码**，只读代码、跑测试、对真实端点取证。

---

## 0. 一屏结论

| # | 发现 | 严重度 | 证据类型 |
|---|---|---|---|
| F1 | 内核要求模型用**自创文本协议**写记忆，而前沿模型只会用**原生工具调用** | **P0** | 真实端点对照实验，同一提示词仅换接口：0 次 → 1 次调用 |
| F2 | 真实产品面（`aios-core-headless turn`）一轮对话后**零认知写入** | **P0** | 真实 CLI 回合 + 世界库计数 |
| F3 | 全量测试在 Windows 上**收集即失败**；无统一检查入口；一项并发不变量**稳定失败** | P1 | 实测 `pytest tests` |
| F4 | 认知写入**无去重**，模型会原样重写同一事实 | P1 | 原生工具实验 T4 |
| F5 | 53 个能力、28 个写路径，只有 7 个带参数签名 | P2 | 能力目录统计 |
| F6 | 治理记录与工程现实脱节，含一条**不可复现的"已验证"** | P2 | 任务板 / checkpoint / PR 对照 |
| F7 | 仓库卫生：CRLF 入库、README 为空、60 个开放 PR | P2 | git 检查 |

一句话：**内核是通的，模型是愿意写的，中间那层协议是错的。**

---

## 1. 审核方法

做了什么：

- 全量测试（`pytest tests`，1406 项，16m50s）
- 治理基线校验（`check_baseline.py`）
- 真实端点取证：本机 sub2api 网关 `127.0.0.1:8080`，`grok-4.6`
- 真实产品面取证：`aios-core-headless turn` 跑一轮真实对话，然后直接读世界库
- 两组对照实验（见 F1）
- git / PR / CI / 治理文档交叉核对

没做什么：没改 `src/`，没动证据语义，没提交任何实现变更。

---

## 2. F1（P0）协议不匹配

### 现象

`src/aios_core/runtime/grok_provider.py` 里**没有** `tools`，**没有** `tool_calls`。能力调用靠一个正则从散文里抓 ```json``` 块：

```python
match = re.search(r"\{[\s\S]*\"call\"\s*:\s*\"([^\"]+)\"[\s\S]*\}", text)
```

也就是：让模型在聊天回复里手写一段 JSON，内核再把它抠出来。

### 对照实验（这是本次审核最关键的一组数）

| 实验 | 提示词 | 接口 | 4 轮对话里的能力调用 |
|---|---|---|---|
| 历史 A/B/C（3 轮） | 3807 → 4859 → 5272 字符 | 文本协议 | **0 / 0 / 0** |
| 实验 1 | 手写极简提示词 | 原生 `tools`（2 个） | **9** |
| 实验 2 | **与历史 C 完全相同的 5272 字符提示词** | 原生 `tools`（7 个写能力） | **1（第 1 轮就写）** |

实验 2 是隔离变量后的一刀：**提示词一个字没改，只把接口从"写 JSON 块"换成 `tools` 数组，模型立刻调用了 `commit_ai_world_claim`**，并把姓名、城市、产品合并成一条 statement。

```text
finish=tool_calls tool_calls=1
  -> commit_ai_world_claim({"domain":"user_understanding",
       "statement":"User's name is Lao Wang (老王). He is based in Dongguan
                    and works on developing 23cm flexible screen smart bracelets ..."})
```

### 这意味着什么

此前三轮提示词工程的结论——"模型不想写""提示词修不了根本不想写"——**是错的**。真实原因是：我们要求它用一种它没被训练过的接口表达一个它本来就会的动作。

之前那三轮不是白做，它们排除了"参数名不可见""二选一语义"两个假设；但结论下早了一步。真正的判据是接口，不是措辞。

### 附带收获

实验 1 的第 3 轮，模型在**一次响应里同时**输出写入和回复（`commit_world_claim` + `reply_to_user`）。说明之前讨论的"双通道方案"根本不需要改契约去求模型——原生协议下它本来就这么做。问题在于内核现在**禁止**这种指令（见 T07）。

### 残余不确定性（如实记录）

实验 1 与实验 2 的提示词不同。实验 2 才是严格的单变量对照，结论以实验 2 为准。

---

## 3. F2（P0）真实产品面零认知写入

跑了一轮真实对话：

```text
$ aios-core-headless --world cli_world.sqlite \
    --model-handler aios_core.runtime.live_handler:handler \
    turn --session s1 --turn-index 1 \
    --text "我叫老王，在东莞做23cm柔性屏手环，跟我说话别用敬语。"

{"model_rounds": 1, "response": "老王，在东莞做23cm柔性屏手环是吧？",
 "status": "turn_completed", "world_revision": 2, "termination_reason": "responded"}
```

回答是对的。但世界库里：

```text
object_revisions:  observation × 2, communication_experience × 1, dependency × 1
claim 表:          不存在（0 条）
```

**这个人的姓名、城市、产品，一条都没有变成认知。** 第二场会话（`recent_turn_limit` 滑出窗口后）身份锚是空的，它就不认识了。

同时 CLI 自己会打一条警告，说明这个洞：

> 未提供 `--round-summary-handler` / `--dimension-summary-handler`，分层记忆将不会产生任何 SUMMARY。`recent_turns` 滑出窗口后，模型既看不到原始对话、也没有总结可读，长会话连续性会断档。

也就是说：即使 F1 修好，只要不接 summary handler，长会话仍然会断档。这条要进产品配置，不能算"轻量运行可忽略"。

---

## 4. F3（P1）仓库健康无法判断

### 4.1 全量测试在 Windows 上收集即失败

```text
ERROR tests/c15_persistence/killpoints/test_killpoints.py
AssertionError: frozen probe manifest was modified after freezing;
  expected a3c2a7c9..., got 07d168d0...
```

查清了：**不是有人改了证据**。

- 该测试对 `PROBE_MANIFEST.json` 的**原始字节**取 sha256；
- 工作区文件被 CRLF 重写（6060 字节 vs blob 5902 字节），哈希自然不同；
- `.gitattributes` 的 `eol=lf` 让 git 在比对时自动归一，所以 **`git status` 看不见这个差异**；
- 重新检出后哈希立刻正确（已验证）。

结论：校验的意图是对的，实现对换行符脆弱。而它一失败就**中断整个收集**，于是"跑全量测试"这条命令在 Windows 上等于不存在。

### 4.2 没有统一检查入口

55 个 workflow 各跑子集（`pytest -q tests/xxx.py tests/yyy.py`），仓库里没有 `Makefile` / `tox.ini` / `noxfile.py` / `scripts/`。

后果：**CI 绿不等于仓库健康**。PR #403 现在 34 项全绿，而 `pytest tests` 跑不起来。

### 4.3 修好收集之后：1285 通过 / 1 失败 / 120 跳过 / 16m50s

失败项 `test_ca2_015_concurrent_attach_yields_one_canonical_winner` **稳定复现（3/3，不是 flake）**：

```text
sqlite3.OperationalError: attempt to write a readonly database
  -> StoreError("SQLite storage operation failed", reason="sqlite_unavailable")
assert sorted(outcomes) == ["accepted", "refused"]
E  AssertionError: assert ['accepted'] == ['accepted', 'refused']
```

两个线程同时 attach 同一个 late return，其中一个线程在 `_connection()` 里炸掉，异常逃出 worker（测试只捕获 `BackgroundModelResponseConflict`），于是只有一个 outcome。

**这正是 C15 的持久化不变量**："一个 canonical winner，另一个必须被明确拒绝"。现在在 Windows 上它既没有拒绝，也没有报错——直接消失。要定性的是：测试写窄了，还是 store 把一次可重试的并发写映射成了不可重试错误。**这个定性我做不了主，交 owner。**

### 4.4 120 项跳过

主要是 `AIOS_LIVE_PROVIDER=1` 才跑的 opt-in live 测试。合理，但意味着**CI 里没有任何一项碰过真实模型**——所有"已验证"的 live 声明都只在某台机器上成立过，不可在 CI 复现。

---

## 5. F4（P1）写入无去重

原生工具实验里，第 4 轮（用户问"还记得我吗"）模型把第 1、3 轮的四条事实**原样又写了一遍**：

```text
T4: tool_calls=4
  -> commit_world_claim("User's name is Lao Wang")
  -> commit_world_claim("User is located in Dongguan ... 23cm ...")
  -> commit_world_claim("User prefers casual ... (no 敬语)")
  -> commit_world_claim("User hates meetings that last more than 20 minutes")
```

`_commit_ai_world_claim` 与 `ai_world.commit` 都没有内容级去重。

**这是 F1 的直接后果**：协议修好之前模型根本不写，所以这个洞没暴露；修好的第一天，世界就会被重复 claim 填满，revision 链也会被"每次问到都再写一遍"搞脏。所以去重必须和协议改造同一批上线，不能排后面。

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

原生工具调用会让这个矛盾消失（schema 必须给），但换来一个新问题：**53 个工具全给**会挤占上下文、降低选择准确率。需要选"热集"，而且要实测拐点，不能靠猜。

---

## 7. F6（P2）治理记录与工程现实脱节

| 记录 | 声称 | 现实 |
|---|---|---|
| `AIOS_SINGLE_WINDOW_TASK_BOARD.md` CURRENT PM CONTROL | 唯一当前任务 = `PM-AUDIT-C15-EVIDENCE-RECONCILIATION-001 READY_FOR_ASSIGNMENT`；Window81 起 = HOLD | P16-MEMORY-DIRECTIVE-001 / P16-IDENTITY-CONTINUITY-001 已并入 `origin/main`（#401） |
| `AIOS_v3.0_CURRENT_CHECKPOINT.md` | 最新条目 2026-10-20 | 之后 8 个提交未记入 |
| `C15_R6_REAL_MULTIMODEL_HABITATION_RECEIPT_2026-10-20.md` | "Live HTTP 200 SSE streaming chat against Grok-4.7" 已验证，4/4 PASS | 今天 `grok-4.7` 稳定 502；该测试是 `AIOS_LIVE_PROVIDER=1` 才跑的 opt-in，默认跳过。**"已验证"没有可复现路径** |
| GitHub | 60 个开放 PR | 32 个标 `DO NOT MERGE`；#340–#347 是同一件事的 8 个连续 PR |

第三条最要紧：checkpoint 是断点续传的锚。一条不可复现的"已验证"会被下一个接手的人当成事实继续往上盖。

处理原则按根原则第 12 条：**向前修正，不删除过去**。加状态，不改写历史。

---

## 8. F7（P2）仓库卫生

- `tests/unit/test_m1_001r_adv_independent_redteam.py`、`tests/unit/test_m1_001r_high_entropy_audio.py` 以 **CRLF 入库**（blob 内含 CR），与 `.gitattributes` 的 `* text=auto eol=lf` 冲突 → `git status` 永久显示 691 行假改动，`git diff` 输出无意义。
- `README.md` 是 **0 字节**。新人接手第一眼看到的是空文件。
- 无统一检查入口（见 4.2）。

---

## 9. 明确不做

1. **不再往提示词加字**。三轮实测证伪。
2. **不为弱模型放宽证据语义**（裸 id 自动解析 revision）。测试台的缺陷不进产品。
3. **不在 F1 修好之前动 UI / 硬件 / Android 适配**。输出契约要变，先变完再往上盖。
4. **不用"最后一个回答对不对"判断连续性**。模型自己吐的 JSON 留在最近几轮里会被读到——那是回声，不是记忆。判据只能是 `recent_turn_limit=0` 下的跨会话复述，和世界库里的 durable 计数。

---

## 10. 附：本次审核产生的脚本

均在仓库外（`%TEMP%\aios_probe\`），未入库：

| 脚本 | 用途 |
|---|---|
| `exp_native_tools.py` | 实验 1：原生 tools（2 工具，4 轮） |
| `exp_same_prompt_tools.py` | 实验 2：**同一 5272 字符提示词** + 原生 tools（7 写能力） |
| `exp_mechanism.py` | 早期机制判定（未得出结论，已被实验 2 取代） |

建议把实验 2 的逻辑固化进 `tools/live_continuity_probe.py`（方案 T10），让"协议是否匹配"变成可重复的判据，而不是一次性的实验。
