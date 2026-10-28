# 已知缺口与未核实项

本文件是**反证据清单**。列在这里的东西，实现方没有独立坐实，或根本没做。
独立 Reviewer 应把它们当作 challenge 入口，而不是当作已解决项。

---

## G1 — 独立复核从未交付（最高优先级）

`reviews/PM_AUDIT_C15_EVIDENCE_RECONCILIATION_001/` 下**只有 `BASELINE.json` 一个文件**，
没有任何 reviewer 目录、没有 R1–R9 的签署记录。

- 任务状态：执行 `NOT_STARTED`，Reviewer `UNASSIGNED`。
- 本包是**实现方产出**，不替代复核，不得被当作 `EVIDENCE_SUPPORTED`。
- 需 owner 指派独立 Reviewer。实现方不能自签。

## G2 — R6 的 "VERIFIED" 不可复现

治理账本里 2026-10-20 段宣称 R6 `VERIFIED_WITH_LIVE_PROVIDER_EVIDENCE`。
本 session 可独立坐实的是：

- `tests/runtime/test_live_multimodel_habitation.py:62` —— `live_only = pytest.mark.skipif(...)`，
  默认跳过，需 `AIOS_LIVE_PROVIDER=1` 且提供可达端点。
- `src/aios_core/runtime/grok_provider.py:75` —— 默认端点是本地 stub
  `http://127.0.0.1:8080/v1`；本环境**未配置任何 `grok-4.7` 端点**。

→ 该 "VERIFIED" 记为 `SUPERSEDED / NOT_REPRODUCIBLE`，不作为派工依据。

**同时声明**：第三方报告中"grok-4.7 现在稳定返回 502"这一条，本 session **未独立核实**，
已从治理文档中删除，不在本包内主张。谁要用它，谁先拿真实端点复验。

## G3 — T04 并发 attach 未定性

- 报告称 Windows 上 3/3 失败，Linux 上 5/5 绿。
- 未做根因定性：是平台差异、时序竞态，还是测试自身问题，未知。
- 已降级为独立调查项，**不挡主线**，但也**未关闭**。

## G4 — CODE HEALTH：没有统一检查入口（已量化）

本 session 实测：

| 指标 | 数值 |
|---|---|
| `.github/workflows/` 下 workflow 总数 | **48** |
| 其中会跑 pytest 的 | **42** |
| 其中跑全量 `tests/` 的（粗匹配） | **3** |

→ 绝大多数 workflow 各跑一个子集。**CI 全绿 ≠ 全量测试通过**。
这是真实的工程风险，不是文档措辞问题。建议：设一个 canonical 入口跑全量，其余改为子集健康度报告。

## G5 — PR 清算：一处转述被证伪，其余待 owner

完整盘点见 `governance/AIOS_PR_LIQUIDATION_SURVEY_2026-10-27.md`。要点：

- **PR #403 是 `MERGED`，不是 OPEN。** 此前"内容已合入但 PR 仍 OPEN、建议关闭"的说法
  来自第三方审查转述，本 session 抓页面核实为 `"state":"MERGED"`。该建议已撤销。
  → 这条本身就是"转述不可信"的实证，Reviewer 应对治理账本里同类断言保持警惕。
- **开放 PR 候选 85 个**：用 `git ls-remote origin 'refs/pull/*/merge'` 计数
  （GitHub 只为 open PR 维护 merge ref）。交叉验证 #101 有 / #326 无 / #394 有且页面 OPEN /
  #403 无且页面 MERGED，四点一致。`refs/pull/*/head` 共 383 个（编号 1–403）。
- `gh` 未登录、`api.github.com` 对本出口 IP 已限流，故**未取到权威 open 数**。
  85 是下界（有冲突的 open PR 会缺 merge ref）。
- **未关闭任何 PR** —— 这是 owner 决策。

## G6 — T10 的取证面很窄

- 只在 **1 个模型**（`minimaxai/minimax-m3.1-flash`）**1 个端点**上验证。
- 未跨模型、未跨 provider、未做多次重复采样来评估稳定性。
- 结论"原生 tools 是正解"在机制上成立，但**跨模型普适性未被证明**。
  Reviewer 若要求，应补多模型矩阵。

## G7 — M3 判据带容差

脚本中 M3 判据是 `len(claims_3) <= len(claims_1) + 1`，比"严格不增"宽松。
本次实测 1 → 1 落在最严格区间，PASS 成立；但判据本身可加固。

## G8 — 五个既有测试文件被适配过（自查披露）

接线后，5 个 prompt 类测试的 fake provider 需要补 `stream_chat_with_tools` stub 才能继续通过：

`test_durable_fact_extraction.py`、`test_identity_continuity_prompt.py`、
`test_prompt_cockpit_coverage.py`、`test_dropped_sections_prompt.py`、
`test_capability_prompt_contract.py`

这是**正常且必要的 mock 同步**，但它意味着这些测试在接线后是被"适配过"的。
Reviewer 应判断：适配是否掩盖了真实回归？建议抽查其中 1–2 个，确认 stub 形态
（`usage=None, provenance=None`）没有让断言失去意义。

## G9 — 发布姿态未升级

当前 `RELEASE_CANDIDATE`。升到 FINAL_RELEASE 需要：独立 R1–R9 复核通过 + owner 授权。
是否打 tag `v3.0.0-rc1` 待 owner 决策。

---

## G10 — 实现方自己的缺陷：T08 去重破坏过 replay 契约（**本 session 亲自复现**）

这一条是打实现方自己脸的，但必须写，而且不能只转述别人的修正。

- **错在哪**：我 10-27 的 T08 把内容级去重放在 **capability path**（`_commit_ai_world_claim` 默认行为）上。
  它撞上一条更强、更老的契约：**capability call 是有自身身份的请求**，参数变了 ——
  哪怕变的只是 `confidence`，文本一模一样 —— 也绝不能被当成原请求吞掉。
- **亲自复现**（把 `1cad586` 的 `turn_runtime.py` 换回当前树后跑 integration 套件）：
  ```
  FAILED ...test_identity_changing_request_is_never_conflated_with_the_original[commit_ai_world_claim]
  FAILED ...test_changed_arguments_under_the_same_call_id_are_never_applied_as_the_original[commit_ai_world_claim]
      AssertionError: a changed request reusing the original call_id was reported as already applied
  ```
  复现后立即还原，工作区已 `git status` 干净。
- **修正**：`dcf21fc`（`PM-T08-DEDUP-SCOPE-CORRECTIVE-001`）—— `dedupe` 改为 **opt-in**，
  只有抽取轮传 `dedupe=True`（它重读每一轮，确实会重新派生锚点已有的事实）；
  capability path 不传，replay 身份得以保留。
- **为什么我的验证没抓到 —— 这才是重点**：那两个测试在 **`tests/integration/`** 下，
  且自 `bc9a6d3`（2026-09-28）就在 main 上，比我的改动早一个月。
  我当时只跑了 `tests/runtime/`，**410 passed 是真的，但它只覆盖了 27 个测试文件中的一部分，
  而 `tests/integration/` 有 52 个**。
- **连带后果**：本目录下的 `REPRODUCE.md` 也因此**不完整** —— 我给 Reviewer 的复现命令
  同样只覆盖 `tests/runtime/`。已补 `@pytest.mark.integration` 一段，但请以修正后的版本为准。
- **教训**：G4（CODE HEALTH，48 个 workflow 各跑子集）不是文档措辞问题。
  这次付出代价的正是我自己 —— 我的验证盲区和 CI 的盲区是同一个盲区。

---

## 一句话总结

技术主线（原生 tools 协议）**已跑通并可复现**；
治理侧（独立复核、PR 清算、跨模型验证）**全部未完成**。
二者不要互相冒充：代码跑通不等于验收通过。
