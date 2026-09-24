# AIOS Core PM Takeover & CORE-BASELINE-001 Live Re-verification — 2026-09-24

Role: 接任 AIOS 3.0 Core Delivery PM / Chief Integration Coordinator（所有者 2026-09-24 指令）。
Authority: `governance/prompts/AIOS_CORE_PM_HANDOFF_2026-09-24.md` + `governance/AIOS_CORE_COMPLETION_PLAN_2026-09-24.md`，二者已随 PR #128 正常合入 main（state=MERGED，checks SUCCESS）。本文件不重写计划，只登记接任核查事实与派工裁决。

## 1. 接手时读取的基线文件

- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`（live main）
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`
- `PROJECT_MASTER_MAP.md`（经 #133 更新版）
- `governance/AIOS_CORE_COMPLETION_PLAN_2026-09-24.md`
- `docs/constitution/AIOS_v3.0_Fused_Baseline_Registry.md` 入口未变（本文件不改写宪法）
- `governance/AIOS_CORE_BASELINE_001_DECISION_2026-09-24.md`
- `governance/AIOS_CORE_GAP_DISPATCH_2026-09-24.md`
- `reviews/CORE_OPERATOR_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`
- `reviews/CORE_GAP_AUDIT_001_2026-09-24.md`（经 #132 合入）

## 2. Live re-verification（2026-09-24 ≈05:11 UTC，本窗口直接查验）

| 对象 | 查验方式 | 结果 |
|---|---|---|
| live main | `git fetch origin main` + `rev-parse` | `e72a63874ed2c28798b00cec51f191caf1594a00`（05:08:07Z 后） |
| main `src/aios_core` tree | `git ls-tree` | `7db4f72e7b3c29c74082f9984141159f8f1d6071`（与 S0 裁决一致） |
| main `tests` tree | `git ls-tree` | `90c2317299b5d8d7539470cf8360f311bc6358b7` |
| PR #125 | gh api + fetch head | OPEN；head `b14b5d84b6a4c843dc7dc38cde51f08a92fac86b`；Core tree 仍 `eed27d58041dbaf2ceb0a65c1305bb332aef082e`（旧 Core，不得整包合入） |
| PR #126 | gh api + fetch head | OPEN；head `8e31deca02a5062d7bb9ffe6dd840abbaaf6970e`；Core tree = main `7db4f72e...`（重复 Core 路线，不再合入） |
| PR #127 | gh api | MERGED；merge `6924d8b50cf08eb632f9cfa513a3cc49faad0c72`；Core tree = `7db4f72e...` |
| PR #131 (CORE-OPERATOR-001) | gh api + fetch head | **MERGED**；head `0e1d69eebc801278f93ccc1941b8f066a4ea09ef` 未变；merge `e72a63874e...` @ 05:08:07Z；diff 仅 `.github/workflows/c15-operator-preflight.yml`、`tests/preflight/**`、`tools/c15_preflight/**`（26 文件，Core 零 diff） |
| PR #135 (operator 独立验收) | gh api commits/files | MERGED `fe6f1740eb` @ 05:08:01Z；仅新增 `reviews/CORE_OPERATOR_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`；verdict = ACCEPTANCE_PASS，0 blocker |
| PR #132 (gap audit) | gh api | MERGED `bc4bf735e15c5c0787fdc533fe3f10d0e17fdac3` |
| PR #133 (dispatch governance) | gh api | MERGED `27135e39d5...` @ 04:40:57Z |
| PR #136 (pelican 动画) | gh api + fetch head | OPEN；branch `arena/01a0d1cd-...`（非本 PM 会话分支）；**EXCLUDED：鹈鹕动画属排除项，永不合入**；且 base 过旧，merge 将删除 operator 文件。保留分支/PR 现状，不做关闭操作（计划未授权删除/关闭） |

**merge 顺序合法性**：独立验收 #135（05:08:01Z）先于候选 #131（05:08:07Z）合入，满足“作者不得自验收、验收先于集成”的治理要求。board/checkpoint 在 04:40 的 #133 版本仍显示 OPERATOR=GATE，属时滞，由本次写回修正。

**CI/语义证据引用边界**：#125 exact-head 128 passed/3 failed（runs 35952205324/35952205318）、operator 复现 FAILURE（35955458275）、exact-head 绿灯（35955695487/35955695492）等数字引自已合入的 S0 裁决与验收报告；本窗口直接复核的是 head/state/tree/merge 顺序与文件范围，不重复 raw-log 审计。

## 3. CORE-BASELINE-001 确认

前任 S0 裁决（`AIOS_CORE_BASELINE_001_DECISION_2026-09-24.md`）五项内容（基线分离、影响裁决、fresh-A 裁决、固定集成路线、出口）经复核**全部仍成立**，补充登记：

- 开发基线前移：`33436565... → e72a63874e...`；Core tree 未变（`7db4f72e...`），故影响矩阵不变。
- operator 工具链（`tools/c15_preflight/**`、`tests/preflight/**`、workflow）已成为 main 的一部分；后续 FIX/HEADLESS 任务从含 operator 的 live main 起步。
- 历史 pin 不变：A=#117@`3e51f728...`（frozen Core `bcd6bf3...`）、旧 B=#121@`b6e5ac9...` NON-CANONICAL、#125 WIP 只收 operator 资产、#126 不重合。
- fresh A 仍需且仅在 `CORE-RC-FREEZE-001` 后启动；当前 Resident A/B/C 一律禁止。
- `CORE-BASELINE-001 = DONE（re-verified by takeover PM）`。

## 4. 派工裁决（2026-09-24）

| Task | 状态 | 说明 |
|---|---|---|
| CORE-GAP-FIX-001 | **READY / 待启动** | CG-001 temporal read cut；提示词 `governance/prompts/CORE_GAP_FIX_001_2026-09-24.md`；独立工程窗口，起步基线 live main `e72a63874e...`；先复现后修 |
| CORE-GAP-FIX-002 | **READY / 待启动** | CG-002 background model execution IN_DOUBT；提示词 `.../CORE_GAP_FIX_002_2026-09-24.md`；与 FIX-001 并行（不同 owner/分支/路径） |
| CORE-GAP-FIX-003 | **BLOCKED** | 等 FIX-002 独立验收 + PM 集成后从当时 live main 起步 |
| CORE-HEADLESS/RECOVERY/SCALE/RC-FREEZE | **BLOCKED** | 依赖不变 |
| C15 fresh A→B→C / C16 / P16 / P17 | **BLOCKED** | 依赖不变；#117 A 不得 hash-swap |

本窗口未启动任何执行任务；FIX-001/002 的“待启动”单任务提示词随本 PR 同步提供给所有者转交新窗口。工程作者不得自验收；每个候选需不同 independent reviewer；作者只可报 REVIEW_READY。

## 5. 写回

- `governance/AIOS_SINGLE_WINDOW_TASK_BOARD.md`：控制入口与优先队列更新（OPERATOR DONE；BASELINE re-verified）。
- `AIOS_v3.0_CURRENT_CHECKPOINT.md`：控制入口更新（live main `e72a63874e...`；OPERATOR DONE）。
- 本文件为新治理记录；PM 明示自审（普通治理文档），不另设批准环节；CI/分支保护照常。
