# C. 当前固定head、PR状态及已有测试证据索引 (PM收口 2026-09-24)

## 参考头

- PM指定参考头: `5b5e2306c39b5b09b260de787403567a31d0efbd`
- 该头已包含:
  - 真实A导入成功回执 (Python3.12)
  - 缺陷修正: publication非变异、freeze收据验证、broker结构边界
  - 架构纠正: 真实Resident为新Arena窗口AI本人，暂停外部LLM API
- 本轮不重复真实A导入，登记为执行方实测结果
- 阻断后当前头: `4859d2e6141649fcf0e6715e69dff0635c9734dc` (仅修改 real-a-import-312.yml 触发方式，阻止后续自动获取私有A)

## PR状态

- 分支: `arena/01a0cf25-haneof-aios-core-v3-0`
- PR: #125
- 标题: C15 preflight: synthetic driver, restart, joint freeze + round3 six fixes [BLOCKED / DO NOT MERGE]
- 状态: OPEN (按指令保持OPEN，不合并、不关闭、不自动合并)
- Base: main @ 849bfd41c623fb336b392a3e6e933cfad93620e9
- 最新推送: 4859d2e (security: block automatic private A fetch)

## 已有测试证据索引 (不再以数量增加为目标)

### 固定头 5b5e2306c39b5b09b260de787403567a31d0efbd 的证据

- c15-operator-preflight: 35925311923 SUCCESS (exact-head 5b5e230, 131 preflight + 146 regression, Python 3.12.14, 0 failures, 0 skipped)
- p16-convergence-gate: 35925311892 SUCCESS
- real-a-import-312: 35925311828 SUCCESS (operator_sha 5b5e230, branch_sha 3e51f728, fixed_A_SHA 3e51f728, branch_equals_fixed true, world_revision 88, index_watermark 88, last_acked 13, next_sequence 14, model_requests 0, cross_process PASS)
- 更早: 35925861876 SUCCESS (operator_sha 5f78d4b, 同样证据), 35924990859 SUCCESS (2528c22), 35924742929 SUCCESS (def9174)

### 阻断后头 4859d2e6141649fcf0e6715e69dff0635c9734dc 的证据

- c15-operator-preflight: 35926209461 SUCCESS (exact-head 4859d2e, 131 + 146, Python 3.12.14, 0 failures, 0 skipped)
- p16-convergence-gate: 35926209477 SUCCESS
- real-a-import-312: 未触发 (符合预期，因仅 workflow_dispatch)

### 真实A执行边界核对 (已登记)

- 仓库 public, 运行日志 public, 未输出私有World内容、原始trace、敏感上下文
- 未上传 artifact/cache/可下载副本
- 私有A分支 arena/01a0cca8 已在公开仓库 git 中可 fetch，CI 未新增 git 可访问性，但自动在普通PR上获取不符合限制，已阻断 (仅 workflow_dispatch)
- 收据仅脱敏: sys_version, sys_executable, operator_sha, branch_sha, fixed_A_SHA, branch_equals_fixed, world_revision, index_watermark, last_acked, next_sequence, model_requests, cross_process

### 合成机械结果 (保留)

- synthetic_mechanics: PASS (131 preflight tests)
- regression: PASS (146 tests)
- 包含:
  - test_fault_window_after_publish_before_receipt
  - test_fault_window_receipt_write_and_dir_fsync
  - test_fault_window_receipt_parent_fsync_after_receipt (按新严格协议 UNCERTAIN, BLOCKED 直到显式 confirm)
  - test_fault_window_after_receipt_before_frozen_checkpoint
  - test_no_uncertain_product_considered_confirmed
  - test_confirm_uncertain_package_*
  - test_checkpoint_loss_cannot_bypass_via_accepted_a_import
  - test_broker_emits_only_plain_snapshot_no_canary (合成传输)
  - test_broker_logs_owned_by_operator_not_model
  - test_broker_timeout_fail_closed
  - test_broker_malformed_response_fail_closed
  - test_broker_no_default_silence
  - test_isolation_exception_classification_*

### 隔离与接入

- actual_namespace_probe: INCONCLUSIVE (unshare Operation not permitted, 预期)
- actual_Resident_isolation: BLOCKED (真实Resident需新Arena窗口可验证边界，平台无法提供，见B)
- launch_authorized: false
- 外部LLM API: PAUSED, 不要求 endpoint/API Key, 不实现 provider 原生适配
- 真实B/C: 未运行 (按指令)

### 文件索引

- 完整可读配置及核对: `reviews/C15_RCC_RES_B_PM_CLOSURE_2026-09-24_A_REAL_A_WORKFLOW_AUDIT.md` (含完整workflow yaml与脚本调用部分)
- Arena接入可行性表格: `reviews/C15_RCC_RES_B_PM_CLOSURE_2026-09-24_B_ARENA_RESIDENT_FEASIBILITY.md`
- 本文件: `reviews/C15_RCC_RES_B_PM_CLOSURE_2026-09-24_C_HEAD_EVIDENCE.md`
- 之前详细报告: `reviews/C15_RCC_RES_B_PREFLIGHT_REAL_A_IMPORT_2026-09-24_v2.md`, `reviews/C15_RCC_RES_B_ARENA_RESIDENT_ARCHITECTURE_VERIFICATION_2026-09-24.md`
- 关键源码: `reviews/key_sources_2528c22/` (freeze, publication, resident_broker, driver, restart, audit, real-a-import-312.yml, SHA256SUMS, diff)
- 缺陷修正源码: `tools/c15_preflight/publication.py` (非变异), `tools/c15_preflight/freeze.py` (收据验证), `tools/c15_preflight/resident_broker.py` (结构边界, 暂停外部API)

## 冻结Core

- Core SHA: `bcd6bf353126318f9a97076b52ec1740d43f35a4` (src/aios_core)
- 未改动 (按指令不改冻结Core)

## 停止条件

- 本轮只交三件东西 A/B/C，已交付
- 不写“所有Gap闭环”或“完整预检DONE”
- 不再以测试数量增加作为本轮目标
- 完成后停止，交回PM
- PR保持OPEN
