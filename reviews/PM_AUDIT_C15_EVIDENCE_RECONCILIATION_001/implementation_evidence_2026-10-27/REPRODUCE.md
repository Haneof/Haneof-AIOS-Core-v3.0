# 复现手册（给独立 Reviewer）

所有命令在仓库根目录执行。基线 `41f12c7`。

```bash
git checkout 41f12c7
python3.11 -m pip install -e .   # 若尚未安装
```

---

## A. 确定性验证（不需要网络、不需要密钥）

这层是**任何人都能跑**的，也是复核的起点。

```bash
# A1 — 全量 runtime 套件
python3.11 -m pytest tests/runtime -q
# 预期：410 passed, 3 skipped
```

```bash
# A2 — 本次新增的三组契约测试
python3.11 -m pytest tests/runtime/test_json_schema_conversion.py \
                    tests/runtime/test_native_tools_stream.py \
                    tests/runtime/test_model_directive_coexistence.py \
                    tests/runtime/test_claim_deduplication.py -q
# 预期：28 passed（8 + 7 + 8 + 5）
```

```bash
# A3 — 安全门 / 基线漂移
python3.11 tools/governance/check_baseline.py \
  --repo . --baseline governance/baseline.json --head HEAD --json /tmp/drift.json
echo "exit=$?"   # 预期 0
```

```bash
# A4 — 能力目录规模（核对 T05 覆盖范围）
grep -c "registry.register(" src/aios_core/runtime/turn_runtime.py
# 预期：53
```

### 失败判读

| 现象 | 含义 |
|---|---|
| A1 出现 failed | 接线或放宽引入了回归 —— 这是复核的实质发现，请记录 |
| A1 通过但 A2 失败 | 新契约与旧行为冲突 |
| A3 非零退出 | 基线 pin 或密钥扫描异常，**阻断发布** |
| A4 不是 53 | 能力目录已变动，T05 覆盖范围需重新核对 |

---

## B. 真实端点验证（需要网络 + 密钥）

> 密钥已按 owner 决策写入 `src/aios_core/runtime/resilient_handler.py`
> （`PRIMARY_API_KEY`），因此脚本无需额外配置即可跑。
> 若你要换成自己的端点，覆盖 `PRIMARY_BASE_URL` / `PRIMARY_API_KEY` / `PRIMARY_MODEL`。

```bash
python3.11 reviews/PM_AUDIT_C15_EVIDENCE_RECONCILIATION_001/\
implementation_evidence_2026-10-27/verify_native_tools_live.py
```

预期输出（关键行）：

```
[第1轮] 自我介绍
  工具调用历史: ['commit_ai_world_claim', ...]      # 非空 → M1
  [M1] user_understanding claim 数: 1
[第2轮] recent_turn_limit=0 下问「我叫什么」
  [M2] 从锚点答对（老王+东莞）: PASS
[第3轮] 重复自我介绍（验证去重）
  [M3] 第3轮后 claim 数: 1 (第1轮后: 1)
  ==> 总体: PASS
```

### 失败判读

| 现象 | 含义 |
|---|---|
| 第 1 轮工具调用历史为空 | **原生 tools 未生效** —— 这是最严重的失败信号，回到根因 |
| M1 通过但 M2 失败 | 写进去了但读不出来 —— continuity anchor 链路有问题 |
| M3 claim 翻倍 | 去重失效（注意：模型侧不重写是概率性的，程序化去重是第二道闸） |
| 连接错误 / 401 | 端点或凭据问题，**不是代码结论**，换端点重跑 |

---

## C. 单变量对照（验证根因主张）

根因主张是"协议不匹配"。要证伪或坐实它，做这个对照：
**同一份提示词、同一个模型**，唯一变量是有无原生 `tools` 数组。

- 有 tools：走 `as_model_handler()` 的当前主路径 → 预期第 1 轮就有 tool_calls。
- 无 tools：把 `_build_native_tools()` 的返回临时置空，强制走文本协议兜底
  → 预期三轮调用数恒为 0。

若两者结果无差异，则根因主张被证伪，请以你的实测为准并推翻本包的结论。

---

## D. 复核时请重点 challenge 的点

见 [`OPEN_GAPS.md`](OPEN_GAPS.md)。其中若干项本包**明确未核实**，不要把它们当作已证事实。
