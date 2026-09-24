# CORE-OPERATOR-001 集成收据补充（2026-09-24）

> 主接任核验记录见 `governance/AIOS_CORE_PM_TAKEOVER_S0_REVERIFICATION_2026-09-24.md`（#137，已合入）。本文件只补充其中未登记的项：合后 Gate run、#130 处置、FIX 分支现场、验收提示词。两者结论一致，不构成第二套计划。

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

---

## 5. 集成 PM 窗口的集成时复核（2026-09-24 并入）

> 本节由执行 `fe6f1740eb` / `e72a63874e` 两次 merge 的集成 PM 窗口写入，与上文同一事件、同一结论；两份 PM 写回在此合并为**单一收据**，不保留第二份文件。原 `governance/AIOS_CORE_OPERATOR_001_INTEGRATION_RECEIPT_2026-09-24.md` 已删除，全部内容并入本文件。

独立验收报告没有被仅凭文本接受；集成 PM 从 live 仓库与 GitHub API 重新推导了下列事实（The independent acceptance report was not accepted on its text alone）。

### 5.1 Pin and scope

- PR #131 head at integration time was still exactly `0e1d69ee...`; the pinned reviewed artifact did not change after the report was written.
- Candidate scope against merge base `c8807876...`: exactly **26 changed files**, **0 files under `src/`**.
- Scope is confined to `.github/workflows/c15-operator-preflight.yml`, `tests/preflight/**`, `tools/c15_preflight/**`.

### 5.2 Core ZERO DIFF held across the integration

- `git diff 27135e39... e72a638... -- src/` is **empty**.
- Post-integration `src/aios_core` tree is still `7db4f72e...`, identical to the tree audited by `CORE-GAP-AUDIT-001` and to the tree recorded by `CORE-BASELINE-001`.
- The integration is purely additive: 27 new files (26 candidate files + the acceptance report). No file was modified or deleted.
- The accepted exact head `0e1d69ee...` is an ancestor of `main`; the merge-commit strategy preserves the reviewed SHA in history instead of rewriting it.

### 5.3 CI receipts re-read from the API, not from the report

| Purpose | Run | Workflow | Head SHA | Conclusion |
|---|---|---|---|---|
| Before-fix reproduction | `35955458275` | `c15-operator-preflight` | `3865da8816ccac48e3eda06f329a84f55e2d0bd6` | FAILURE |
| Before-fix full suite | `35955458266` | `p16-convergence-gate` | `3865da8816ccac48e3eda06f329a84f55e2d0bd6` | FAILURE |
| Exact-head candidate gate | `35955695487` | `c15-operator-preflight` | `0e1d69eebc801278f93ccc1941b8f066a4ea09ef` | SUCCESS |
| Exact-head full regression | `35955695492` | `p16-convergence-gate` | `0e1d69eebc801278f93ccc1941b8f066a4ea09ef` | SUCCESS |

The candidate workflow was inspected directly at the candidate head: it checks out `github.event.pull_request.head.sha`, asserts Python >= 3.12, runs plain `python -m pytest` invocations, and contains no `|| true`, no `continue-on-error`, and no narrowed substitute for the full gate.

### 5.4 Independent local re-execution by the PM

The PM re-ran the decisive evidence locally instead of trusting green CI badges.

Environment: CPython 3.11.2, pydantic 2.13.5, pytest 8.4.2, worktree extracted per exact SHA.

| Tree under test | Command | Result |
|---|---|---|
| Reproduction commit `3865da88...` | the three exact regressions | **3 failed** |
| Accepted head `0e1d69ee...` | the three exact regressions | 3 passed |
| Accepted head `0e1d69ee...` | `pytest -q` (whole repository) | **632 passed** |
| Merge result `e72a638...` | the three exact regressions | 3 passed |
| Merge result `e72a638...` | `pytest -q` (whole repository) | **632 passed** |

The locally observed failure symptoms at `3865da88...` match the documented ones exactly:

1. `test_clock_reuses_existing_scheduler_at_intermediate_deadline_without_future_input` — `periodic_reviews` empty, `IndexError` on element 0 (the T+24h Review never ran before T+49h).
2. `test_old_wake_cannot_see_future_input` — the old Wake observed `SYNTHETIC event 1`.
3. `test_budget_deferral_not_forced` — `pre_ingest_wakes` empty (`assert 0 >= 1`).

This confirms the historical defect was genuinely reproduced on a current-main-based candidate and genuinely closed, rather than made green by test edits or CI configuration. The local pass count `632` equals the count independently reported from the CI full-suite log.

### 5.5 Honest limitations of this receipt

- The local runs used CPython **3.11.2**, below the project gate of >= 3.12. They are corroboration only. The authoritative gate evidence remains the CI runs on CPython 3.12.14.
- The PM attempted a fresh re-run of the exact-head gates (`gh run rerun`) and a post-merge `workflow_dispatch` on `main`. Both were refused by the platform for this token (`HTTP 403: Resource not accessible by integration`; "cannot be rerun"). No permission was bypassed and no protection was circumvented. Post-merge CI nevertheless exists and was verified from the API after the fact: push-triggered `p16-convergence-gate` run `35958610555` on `main` @ `e72a63874ed2c28798b00cec51f191caf1594a00`, job `full-core-regression` = SUCCESS. `c15-operator-preflight` is path-triggered and will next run on a PR touching `tools/c15_preflight/**` or `tests/preflight/**`.
- The candidate author window and the independent acceptance window are separate AI windows with separate contexts, but both act through the same GitHub account identity (`Haneof`). There is therefore **no GitHub-native `APPROVE` event from a distinct account**. Independence here is process-level and evidence-level, recorded in `reviews/CORE_OPERATOR_001_INDEPENDENT_ACCEPTANCE_2026-09-24.md`; it is not account-level or cryptographic independence, and this receipt does not claim otherwise.


### 5.6 结论分层

代码已合入 ✓ / 软件测试通过 ✓ / 独立工程验收通过 ✓ / 合后 Gate 通过 ✓。
**不是**真实 Resident 执行，**不是**语义 PASS，**不是** SOFTWARE_RC，**不是** CORE_COMPLETE。
