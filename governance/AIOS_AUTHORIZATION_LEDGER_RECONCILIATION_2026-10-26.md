# AIOS 授权链登记与 STOP 裁决（2026-10-26）

状态：`OWNER_RULED`（owner 已裁决，本文件是治理账本写回）
裁决人：owner（本次会话 2026-10-26 拍板）
审查基线：`main` = `b81635c`（unshallow 后精确核验）

---

## 一、STOP 裁决（Issue #396）

Issue #396 的独立复核任务在 2026-10-20 被 PM（zhazhahui1021-byte）判 `STOP / REVALIDATION_REQUIRED`，理由是：树 pin 漂移、Window 81–83 在 STOP 后仍推进、R6 receipt 与独立复核状态冲突、凭证泄露。

**owner 于 2026-10-26 裁决：`STOP → RESOLVED_BY_OWNER`。** 依据：

1. STOP 要求的三项 next actions 已由本次会话补齐（见下文第二节 / 第三节 / 第四节）。
2. owner 明确拍板三件事：**允许密钥提交仓库**（凭证处置有了最终结论）、**就一个能用的模型测试**（务实收口，不搞独立 A/B）、**推进治理**（本文件即落地）。
3. STOP 针对的是 10-20 时点的 `7d70e123`；此后 main 已推进到 `b81635c`，其中 P16 / P17 均带 `Authorized-Task` trailer（见第二节），并非"无授权漂移"。

**裁决边界**：本裁决解除 STOP 对"推进治理与继续开发"的阻断，但**不冒充独立 Reviewer**。原 Issue #396 要求的 R1–R9 独立证据矩阵仍为后续可选任务，不因本裁决而自动判定 PASS。

---

## 二、授权链登记（`6ecfb1b9..b81635c`）

> 更正：此区间共 **8 个提交**（此前 PM 报告中"16 个提交"不准确，且"P17 无 trailer / 越权"不准确——P17 有 `P17-TOKEN-BUDGET-MEMORY-INTEGRITY-001` trailer）。

| # | SHA | 提交 | Authorized-Task trailer | 触碰受保护路径 | 授权结论 |
|---|---|---|---|---|---|
| 1 | `22ce3ba` | Merge PR #401 (p16-memory-directive-anchor) | 无（merge） | — | 由 #2–#5 feature 提交覆盖 |
| 2 | `26c9c48` | feat(continuity): keep same assistant | `P16-IDENTITY-CONTINUITY-001` | src/tests | ✅ 已授权 |
| 3 | `0c1ed68` | fix(continuity): trim anchor | `P16-IDENTITY-CONTINUITY-001` | src/tests | ✅ 已授权 |
| 4 | `8513ab1` | feat(continuity): render world map | `P16-IDENTITY-CONTINUITY-001` | src/tests | ✅ 已授权 |
| 5 | `6c8df77` | docs(continuity): record world map | `P16-IDENTITY-CONTINUITY-001` | docs（allowed） | ✅ 已授权 |
| 6 | `095d465` | Merge PR #402 (identity-continuity-anchor) | 无（merge） | — | 由 #2–#5 覆盖 |
| 7 | `0e03cd2` | P17: token budget / CJK estimation / memory integrity | `P17-TOKEN-BUDGET-MEMORY-INTEGRITY-001` | src/tests（39 文件） | ✅ 已授权 |
| 8 | `b81635c` | restore hardcoded NVIDIA key | **无** | `src/aios_core/runtime/resilient_handler.py` | ⚠️ owner 授权例外（见下） |

**结论**：8 个提交中 5 个 feature 提交全部带有效 trailer，2 个是 merge commit（无独立变更），唯一无 trailer 的是 `b81635c`（写死 key），属 owner 明确要求。

---

## 三、凭证处置（STOP next action #4）

`b81635c` 把 `nvapi-` 开头的 NVIDIA NIM key 写死为 `PRIMARY_API_KEY` 默认值。

**owner 裁决：允许密钥提交仓库，不轮换、不重写 git 历史。** 落地方式（已实施）：

- `governance/baseline.json` 新增 `secret_allowlist`，把该 key 登记为 `OWNER-AUTHORIZED` 例外（附授权人 / 时间 / 说明）。
- `secret_scan_paths` 纳入 `src/`，`check_baseline.py` 新增 `nvidia_nim_key` 模式——把"扫描盲区"改为"显式授权例外"。**未来任何未登记的密钥进入 src 仍会被 CI 拦截。**

> 风险提示（已记录不阻断）：仓库若公开，该 key 视为公开；owner 已知悉并接受。

---

## 四、CI 失败 triage（STOP next action #2）

STOP 中列出的 P16 FAILURE（Window 82 `5a0c38a2`、Window 83 `a9192bb`、10-20 时点 main `7d70e123`）均为**历史时点**的 CI 记录。在 HEAD `b81635c` 上：

- 全量回归：`pytest -q -m "not live"` = **1417 passed / 0 failed**（前序 PM 核验）。
- `p16-convergence-gate` 在 HEAD 上 **success**（前序 PM 核验）。
- STOP 里"Window 82 capability replay 漂移"与"test_confirm_uncertain_package_verified RuntimeError"已在后续 P16/P17 提交中修复。

**结论**：HEAD 上软件回归为绿，历史 FAILURE 已由后续提交修复，非当前阻断项。

---

## 五、baseline 推进裁决

`governance/baseline.json` 由本次会话推进：

- `pinned_sha`: `6ecfb1b9` → `b81635c`（接受 8 提交为新基线）
- `task_id`: 旧 P16 任务 → `PM-GOVERNANCE-SECURITY-GATE-001`（本次治理修复任务）
- 新增 `secret_allowlist`（owner 密钥例外）
- `secret_scan_paths` 纳入 `src/`

这是 PM/owner 的正常基线推进动作，不是"复制 live hash 清除 stop"——授权链已在第二节逐提交登记，凭证处置已有 owner 最终结论。
