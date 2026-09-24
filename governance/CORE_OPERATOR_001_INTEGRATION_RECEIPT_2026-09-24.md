# CORE-OPERATOR-001 集成收据及 PM 接任核验（2026-09-24）

Role: AIOS Core Delivery PM（接任）。这是普通治理写回，由 PM 明示自审；不是独立工程或语义验收。

## 1. 接任时 live 现场

- live `main` = `e72a63874ed2c28798b00cec51f191caf1594a00`。
- `src/aios_core` tree = `7db4f72e7b3c29c74082f9984141159f8f1d6071`，与 `6924d8b5`（#127 十项修复）相比 `src/` 无 diff。
- PR #128（completion plan + PM handoff）已于 `2026-09-24T04:06:01Z` 合入 main，计划已生效；本收据不另写计划。
- CORE-BASELINE-001 已由 #129 收口（`governance/AIOS_CORE_BASELINE_001_DECISION_2026-09-24.md`）。接任复核：此后 main 仅有治理/审查及 operator 工具变更，未改 Core，baseline 裁决与实验影响矩阵不需要修订。

## 2. CORE-OPERATOR-001 = DONE

| 项 | 证据 |
|---|---|
| 工程候选 | PR #131，exact head `0e1d69eebc801278f93ccc1941b8f066a4ea09ef`（3 commits，26 files，范围 `tools/c15_preflight/**`、`tests/preflight/**`、`.github/workflows/c15-operator-preflight.yml`） |
| 独立验收 | PR #135 `reviews/CORE_OPERATOR_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`：ACCEPTANCE_PASS，blockers 0；merge `fe6f1740eb4e6ab4d1c562373ef5d3554bb2dc54` |
| 集成 | #131 merge `e72a63874ed2c28798b00cec51f191caf1594a00`；集成时 head 未变 |
| 合后 Gate | p16-convergence-gate run `35958610555` SUCCESS（push @ `e72a6387`） |
| Core diff | 0 |

分层表述：代码已合入 + 软件测试通过 + 独立工程验收通过。**不是** B 放行、不是真实 Resident 执行、不是语义 PASS。isolation probe 仍自标 synthetic / `launchable=false`；协议仍为“规则约束＋过程审计”，不宣称硬隔离。

## 3. 其他候选处置

- PR #130 `core/operator-001-20260924-sol` @ `16eb1d40c1013433166b4dd81669abbcc36b95a9`：同一 Task 的竞争候选，未经独立验收 → **SUPERSEDED / NOT INTEGRATED**。保留 OPEN，不合并、不删除。其中 in-doubt model restart 的工具级测试可作为 CORE-GAP-FIX-002 的参考线索，但不是 Core 修复，也不能视为 CG-002 已关闭。
- PR #125 / #126：按 CORE-BASELINE-001 已有裁决保留，不整包合入。
- 三条鹈鹕动画分支（`arena/01a0d1a2-*`、`arena/01a0d1c4-*`，以及本 PM 分支历史提交 `f8edb5d1`）不属于 Core 路线：保留历史，不合入。

## 4. 派工状态

- `CORE-GAP-FIX-001`、`CORE-GAP-FIX-002`：READY / NOT_STARTED。同名分支 `core-gap-fix-001-temporal-read-cut-20260924`、`core-gap-fix-002-20260924` 均停在 `27135e39`，零提交，没有可验证的施工现场。现提供现有提示词给两个新工程窗口，**待启动**，不能声称已经在施工。
- 独立验收使用新增的 `governance/prompts/CORE_GAP_FIX_ACCEPTANCE_2026-09-24.md`，每个 fix 另开一个 reviewer 窗口，不能由作者来做。
- `CORE-GAP-FIX-003` BLOCKED on FIX-002 accepted + integrated.
- 下游 HEADLESS → RECOVERY → SCALE → RC-FREEZE → C15 → C16 → P16 → P17 保持 BLOCKED；Resident 禁止。
